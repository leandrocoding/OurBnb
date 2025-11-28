import os
import json
import time
import re
from random import randint
from typing import Dict, Any

from celery import Celery

from scrape import search_airbnb, Amenities, RoomType
from scrape_listing import get_listing_data
from db import (
    get_user_filter,
    get_destination,
    update_filter_request_progress,
    insert_property,
    add_property_to_group_candidates,
    get_group_id_for_destination,
)

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

app = Celery("airbnb_workers", broker=REDIS_URL)


def parse_rating(rating_str: str) -> tuple:
    """Parse rating string like '4.85 (123)' into (rating, review_count)."""
    if not rating_str or rating_str == "N/A":
        return None, None
    
    # Try to extract rating and review count
    match = re.match(r"([\d.]+)\s*\((\d+)\)?", str(rating_str))
    if match:
        return float(match.group(1)), int(match.group(2))
    
    # Try just the rating
    try:
        return float(rating_str), None
    except (ValueError, TypeError):
        return None, None


@app.task(name='scraper.search_job') 
def search_worker(args: Dict[str, Any]):
    """
    Process a search job.
    
    Args should contain:
    - user_id: int
    - destination_id: int
    - page_start: int
    - page_end: int (maximum, actual pages may be less)
    """
    user_id = args.get("user_id")
    destination_id = args.get("destination_id")
    page_start = args.get("page_start", 1)
    page_end = args.get("page_end", 2)
    
    if not user_id or not destination_id:
        print("Missing required data: user_id or destination_id")
        return "Failed: missing user_id or destination_id"
    
    # Get filter from database
    user_filter = get_user_filter(user_id)
    
    # Get destination info from database  
    destination = get_destination(destination_id)
    if not destination:
        print(f"Destination {destination_id} not found")
        return "Failed: destination not found"
    
    location = destination.get("location_name")
    # Calculate total guests
    guests = (
        destination.get("adults", 0) + 
        destination.get("teens", 0) + 
        destination.get("child", 0)
    )
    checkin = str(destination.get("date_range_start"))
    checkout = str(destination.get("date_range_end"))
    
    if not (location and guests and checkin and checkout):
        print(f"Missing required destination data: {destination}")
        return "Failed: incomplete destination data"
    
    # Get group ID for adding candidates
    group_id = get_group_id_for_destination(destination_id)
    
    # Map room_type string to enum if present
    room_type = None
    if user_filter.get("property_type"):
        property_type = user_filter.get("property_type")
        if property_type == "Entire home/apt":
            room_type = RoomType.ENTIRE_HOME
        elif property_type == "Private room":
            room_type = RoomType.PRIVATE_ROOM
    
    print(f"Scraping search for {location} with filter: {user_filter}")
    
    # Initialize filter request tracking
    max_pages = page_end - page_start + 1
    update_filter_request_progress(user_id, destination_id, 0, max_pages)
    
    # Perform the search
    result_json = search_airbnb(
        location=location,
        guests=guests,
        checkin=checkin,
        checkout=checkout,
        min_price=user_filter.get("min_price"),
        max_price=user_filter.get("max_price"),
        min_bedrooms=user_filter.get("min_bedrooms"),
        min_beds=user_filter.get("min_beds"),
        min_bathrooms=user_filter.get("min_bathrooms"),
        room_type=room_type,
        max_pages=max_pages,
    )
    
    # Parse results and insert into database
    try:
        listings = json.loads(result_json)
    except json.JSONDecodeError:
        print("Failed to parse search results")
        return "Failed: could not parse results"
    
    properties_inserted = 0
    for listing in listings:
        rating, review_count = parse_rating(listing.get("rating"))
        
        # Prepare property data
        # Since this property was returned from a filtered search, 
        # we can assume it meets the filter criteria
        property_data = {
            "airbnb_id": listing.get("id"),
            "title": listing.get("title"),
            "price_per_night": listing.get("price_int"),
            "rating": rating,
            "review_count": review_count,
            "main_image_url": listing.get("images", [None])[0] if listing.get("images") else None,
            # Set filter-based constraints since property matched the search
            "min_bedrooms": user_filter.get("min_bedrooms"),
            "min_beds": user_filter.get("min_beds"),
            "min_bathrooms": user_filter.get("min_bathrooms"),
            "property_type": user_filter.get("property_type"),
        }
        
        try:
            airbnb_id = insert_property(property_data)
            
            # Add to group candidates if we have a group
            if group_id:
                add_property_to_group_candidates(group_id, airbnb_id)
            
            properties_inserted += 1
        except Exception as e:
            print(f"Failed to insert property {listing.get('id')}: {e}")
    
    # Update progress - all pages fetched
    update_filter_request_progress(user_id, destination_id, max_pages)
    
    print(f"Inserted {properties_inserted} properties for destination {location}")
    
    time.sleep(randint(1, 4))
    return f"Done: inserted {properties_inserted} properties"


@app.task(name='scraper.listing_job')
def listing_worker(room_id):
    print(f"Scraping listing {room_id}")
    get_listing_data(room_id)
    time.sleep(randint(1, 4))
    
    return "Done"
