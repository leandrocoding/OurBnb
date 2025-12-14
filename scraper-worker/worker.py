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
    get_filter_amenities,
    get_destination,
    update_filter_request_progress,
    insert_bnb,
    insert_bnb_images,
    insert_bnb_amenities,
)
from proxy import get_proxy_manager

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

app = Celery("airbnb_workers", broker=REDIS_URL)

# Initialize proxy manager and log status
proxy_manager = get_proxy_manager()
if proxy_manager.has_proxies:
    print(f"Proxy support enabled with {proxy_manager.proxy_count} proxies")
else:
    print("No proxies configured, using direct connection")


def parse_rating(rating_str: str) -> tuple:
    """Parse rating string like '4.85 (123)' into (rating, review_count)."""
    if not rating_str or rating_str == "N/A":
        return None, 0
    
    # Try to extract rating and review count
    match = re.match(r"([\d.]+)\s*\((\d+)\)?", str(rating_str))
    if match:
        return float(match.group(1)), int(match.group(2))
    
    # Try just the rating
    try:
        return float(rating_str), 0
    except (ValueError, TypeError):
        return None, 0
    

def import_listings(result_json : str, user_id, user_filter, group_id, destination_id, filter_amenities):

    try:
        listings = json.loads(result_json)
    except json.JSONDecodeError:
        print("Failed to parse search results")
        return 0
    
    bnbs_inserted = 0
    for listing in listings:
        rating, review_count = parse_rating(listing.get("rating"))
        
        # Prepare bnb data - now includes group_id and destination_id
        bnb_data = {
            "airbnb_id": listing.get("id"),
            "group_id": group_id,
            "destination_id": destination_id,
            "title": listing.get("title"),
            "price_per_night": listing.get("price_int", 0),
            "rating": rating,
            "review_count": review_count or 0,
            "main_image_url": listing.get("images", [None])[0] if listing.get("images") else None,
            # Set filter-based constraints since property matched the search
            "min_bedrooms": user_filter.get("min_bedrooms"),
            "min_beds": user_filter.get("min_beds"),
            "min_bathrooms": user_filter.get("min_bathrooms"),
            "property_type": user_filter.get("property_type"),
        }
        
        try:
            # insert_bnb now returns (airbnb_id, group_id) tuple for composite PK
            airbnb_id, returned_group_id = insert_bnb(bnb_data)
            
            # Insert additional images (skip first one as it's main_image_url)
            # Now requires group_id for composite key
            extra_images = listing.get("images", [])[1:]
            if extra_images:
                insert_bnb_images(airbnb_id, group_id, extra_images)
            
            # Insert filter amenities (since the search matched, the bnb must have these)
            # Now requires group_id for composite key
            if filter_amenities:
                insert_bnb_amenities(airbnb_id, group_id, filter_amenities)
            
            bnbs_inserted += 1
        except Exception as e:
            print(f"Failed to insert bnb {listing.get('id')}: {e}")
    
    return bnbs_inserted

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
    bnbs_inserted = 0
    
    if not user_id or not destination_id:
        print("Missing required data: user_id or destination_id")
        return "Failed: missing user_id or destination_id"
    
    # Get filter from database
    user_filter = get_user_filter(user_id)
    filter_amenities = get_filter_amenities(user_id)
    
    # Get destination info from database (includes group_id)
    destination = get_destination(destination_id)
    if not destination:
        print(f"Destination {destination_id} not found")
        return "Failed: destination not found"
    
    location = destination.get("location_name")
    group_id = destination.get("group_id")
    
    # Calculate total guests
    guests = (
        destination.get("adults", 0) + 
        destination.get("children", 0) + 
        destination.get("infants", 0)
    )
    checkin = str(destination.get("date_range_start"))
    checkout = str(destination.get("date_range_end"))
    
    if not (location and guests and checkin and checkout):
        print(f"Missing required destination data: {destination}")
        return "Failed: incomplete destination data"
    
    if not group_id:
        print(f"No group_id for destination {destination_id}")
        return "Failed: no group_id"
    
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
    bnbs_inserted = search_airbnb(
        location=location,
        adults=destination.get("adults", 0),
        children = destination.get("children", 0),
        infants = destination.get("infants", 0),
        pets= destination.get("pets", 0),
        checkin=checkin,
        checkout=checkout,
        min_price=user_filter.get("min_price"),
        max_price=user_filter.get("max_price"),
        min_bedrooms=user_filter.get("min_bedrooms"),
        min_beds=user_filter.get("min_beds"),
        min_bathrooms=user_filter.get("min_bathrooms"),
        room_type=room_type,
        max_pages=max_pages,
        import_function = lambda result_json: import_listings(result_json=result_json, user_id=user_id, user_filter=user_filter, group_id=group_id, destination_id=destination_id, filter_amenities=filter_amenities),
    )
    
        # Update progress - all pages fetched
    update_filter_request_progress(user_id, destination_id, max_pages)
    
    
    print(f"Done: Inserted {bnbs_inserted} bnbs for destination {location}")
    time.sleep(randint(1, 4))
    return f"Done: inserted {bnbs_inserted} bnbs"



@app.task(name='scraper.listing_job')
def listing_worker(room_id):
    print(f"Scraping listing {room_id}")
    get_listing_data(room_id)
    time.sleep(randint(1, 4))
    
    return "Done"
