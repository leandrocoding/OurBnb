"""
Core scraping functionality for the Airbnb API.

This module provides the main interface for scraping Airbnb listings.
It wraps the scraping logic to provide a clean API for the routes.
"""

import json
import logging
import random
from typing import Optional
from dataclasses import dataclass

import requests
import time

# Import from local scraper modules (copied from scraper-worker)
from scraper.scrape import (
    build_airbnb_url,
    parse_airbnb_response,
    Amenities as AirbnbAmenities,
    RoomType as AirbnbRoomType,
)
from scraper.scrape_listing import get_listing_data
from scraper.proxy import get_proxy_manager
from scraper.headers import get_random_headers, get_random_delay

logger = logging.getLogger(__name__)


# Map our API amenity names to Airbnb amenity IDs
AMENITY_MAP = {
    "wifi": {"id": AirbnbAmenities.WIFI, "name": "WiFi"},
    "kitchen": {"id": AirbnbAmenities.KITCHEN, "name": "Kitchen"},
    "washer": {"id": AirbnbAmenities.WASHER, "name": "Washer"},
    "dedicated_workspace": {"id": AirbnbAmenities.DEDICATED_WORKSPACE, "name": "Dedicated Workspace"},
    "tv": {"id": AirbnbAmenities.TV, "name": "TV"},
    "pool": {"id": AirbnbAmenities.POOL, "name": "Pool"},
    "hot_tub": {"id": AirbnbAmenities.HOT_TUB, "name": "Hot Tub"},
    "free_parking": {"id": AirbnbAmenities.FREE_PARKING, "name": "Free Parking"},
    "ev_charger": {"id": AirbnbAmenities.EV_CHARGER, "name": "EV Charger"},
    "crib": {"id": AirbnbAmenities.CRIB, "name": "Crib"},
    "king_bed": {"id": AirbnbAmenities.KING_BED, "name": "King Bed"},
    "gym": {"id": AirbnbAmenities.GYM, "name": "Gym"},
    "bbq_grill": {"id": AirbnbAmenities.BBQ_GRILL, "name": "BBQ Grill"},
    "breakfast": {"id": AirbnbAmenities.BREAKFAST, "name": "Breakfast"},
    "indoor_fireplace": {"id": AirbnbAmenities.INDOOR_FIREPLACE, "name": "Indoor Fireplace"},
    "smoking_allowed": {"id": AirbnbAmenities.SMOKING_ALLOWED, "name": "Smoking Allowed"},
    "smoke_alarm": {"id": AirbnbAmenities.SMOKE_ALARM, "name": "Smoke Alarm"},
    "carbon_monoxide_alarm": {"id": AirbnbAmenities.CARBON_MONOXIDE_ALARM, "name": "Carbon Monoxide Alarm"},
}

# Map our API room type names to Airbnb room types
ROOM_TYPE_MAP = {
    "entire_home": {"enum": AirbnbRoomType.ENTIRE_HOME, "name": "Entire Home/Apartment"},
    "private_room": {"enum": AirbnbRoomType.PRIVATE_ROOM, "name": "Private Room"},
}


@dataclass
class SearchParams:
    """Parameters for an Airbnb search."""
    location: str
    checkin: str
    checkout: str
    adults: int = 1
    children: int = 0
    infants: int = 0
    pets: int = 0
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = None
    min_beds: Optional[int] = None
    min_bathrooms: Optional[int] = None
    room_type: Optional[str] = None  # "entire_home" or "private_room"
    amenities: Optional[list[str]] = None  # List of amenity keys
    max_pages: int = 1


def search_listings(params: SearchParams) -> dict:
    """
    Search for Airbnb listings based on the given parameters.
    
    Args:
        params: SearchParams object containing search criteria
        
    Returns:
        Dictionary containing search results with listings
    """
    # Convert amenities to Airbnb format
    amenity_ids = None
    if params.amenities:
        amenity_ids = []
        for amenity_key in params.amenities:
            if amenity_key in AMENITY_MAP:
                amenity_ids.append(AMENITY_MAP[amenity_key]["id"])
    
    # Convert room type to Airbnb format
    room_type_enum = None
    if params.room_type and params.room_type in ROOM_TYPE_MAP:
        room_type_enum = ROOM_TYPE_MAP[params.room_type]["enum"]
    
    # Build the URL with parameters
    url_path, url_params = build_airbnb_url(
        location=params.location,
        adults=params.adults,
        children=params.children,
        infants=params.infants,
        pets=params.pets,
        checkin=params.checkin,
        checkout=params.checkout,
        price_min=params.min_price,
        price_max=params.max_price,
        amenities=amenity_ids,
        room_type=room_type_enum,
        min_bedrooms=params.min_bedrooms,
        min_beds=params.min_beds,
        min_bathrooms=params.min_bathrooms,
    )
    
    # Use randomized headers to reduce fingerprinting
    headers = get_random_headers()
    
    # Get proxy manager for rotating proxies
    proxy_manager = get_proxy_manager()
    
    all_listings = []
    current_cursor = None
    
    for page in range(1, params.max_pages + 1):
        # Prepare params for pagination
        current_params = url_params.copy()
        if current_cursor:
            current_params['pagination_search'] = 'true'
            current_params['cursor'] = current_cursor

        last_error: Optional[Exception] = None

        # Try proxies first (skipping those on cooldown). If all fail, fall back to direct.
        max_proxy_attempts = proxy_manager.proxy_count
        attempted = 0
        response = None

        while attempted < max_proxy_attempts:
            proxy = proxy_manager.get_healthy_proxy(strategy="round_robin")
            if not proxy:
                break
            attempted += 1

            try:
                response = requests.get(
                    url_path,
                    params=current_params,
                    headers=headers,
                    proxies=proxy,
                    timeout=30,
                )
                response.raise_for_status()
                last_error = None
                break
            except requests.exceptions.RequestException as e:
                last_error = e
                proxy_manager.mark_failed(proxy)
                logger.warning(f"Request failed with proxy (cooldown applied): {e}")

        if response is None:
            try:
                response = requests.get(
                    url_path,
                    params=current_params,
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                last_error = e

        if response is None:
            return {
                "success": False,
                "error": f"Request failed: {str(last_error)}",
                "listings": all_listings,
            }
            
        listings, next_cursor = parse_airbnb_response(response.text)
        
        if isinstance(listings, dict) and "error" in listings:
            return {
                "success": False,
                "error": listings["error"],
                "listings": all_listings,
            }
        
        # Transform listings to our API format
        for listing in listings:
            all_listings.append({
                "id": listing.get("id"),
                "title": listing.get("title"),
                "price_text": listing.get("price_text"),
                "price_per_night": listing.get("price_int", 0),
                "total_price_details": listing.get("total_price_details"),
                "rating": listing.get("rating"),
                "images": listing.get("images", []),
                "url": listing.get("url"),
            })
        
        # Check if we should continue
        if not next_cursor:
            break
        
        current_cursor = next_cursor
        
        # Rate limiting between pages (randomized to appear more human)
        if page < params.max_pages:
            time.sleep(get_random_delay(1, 4.0))
    
    return {
        "success": True,
        "listings": all_listings,
    }


def find_price_range(params: SearchParams) -> tuple[int, int]:
    """
    Find the price range for a given search location/dates.
    
    Airbnb returns a price histogram with min/max values. This fetches that
    data and returns the range.
    
    Args:
        params: SearchParams object containing search criteria
        
    Returns:
        Tuple of (min_price, max_price). Returns (0, 25000) as fallback.
    """
    from bs4 import BeautifulSoup
    import json
    
    DEFAULT_MIN, DEFAULT_MAX = 0, 25000
    
    # Build URL without room_type (it breaks the price histogram)
    url_path, url_params = build_airbnb_url(
        location=params.location,
        adults=params.adults,
        children=params.children,
        infants=params.infants,
        pets=params.pets,
        checkin=params.checkin,
        checkout=params.checkout,
        price_min=None,
        price_max=None,
        amenities=None,
        room_type=None,
        min_bedrooms=None,
        min_beds=None,
        min_bathrooms=None,
    )
    
    headers = get_random_headers()
    proxy_manager = get_proxy_manager()
    proxy = proxy_manager.get_healthy_proxy(strategy="random")
    
    response = None
    try:
        response = requests.get(url_path, params=url_params, headers=headers, proxies=proxy, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        if proxy:
            logger.warning(f"Proxy failed for price range: {e}. Retrying direct.")
            proxy_manager.mark_failed(proxy)
            try:
                response = requests.get(url_path, params=url_params, headers=headers, timeout=30)
                response.raise_for_status()
            except Exception:
                return (DEFAULT_MIN, DEFAULT_MAX)
        else:
            return (DEFAULT_MIN, DEFAULT_MAX)
    
    if not response:
        return (DEFAULT_MIN, DEFAULT_MAX)
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
        if not script_tag:
            return (DEFAULT_MIN, DEFAULT_MAX)
        
        data = json.loads(script_tag.text)
        niobe_data = data.get('niobeClientData', [])
        
        if len(niobe_data) > 0 and len(niobe_data[0]) > 1:
            presentation = niobe_data[0][1].get('data', {}).get('presentation', {})
            stays_search = presentation.get('staysSearch', {})
            results = stays_search.get('results', {})
            filters = results.get('filters', {})
            filter_panel = filters.get('filterPanel', {})
            sections = filter_panel.get('filterPanelSections', {}).get('sections', [])
            
            for section in sections:
                section_data = section.get('sectionData', {})
                discrete_items = section_data.get('discreteFilterItems', [])
                for item in discrete_items:
                    if 'priceHistogram' in item:
                        min_val = item.get('minValue', DEFAULT_MIN)
                        max_val = item.get('maxValue', DEFAULT_MAX)
                        return (min_val, max_val)
    except Exception as e:
        logger.warning(f"Error extracting price range: {e}")
    
    return (DEFAULT_MIN, DEFAULT_MAX)


def get_listing_details(room_id: str) -> dict:
    """
    Get detailed information about a specific Airbnb listing.
    
    Args:
        room_id: The Airbnb room ID
        
    Returns:
        Dictionary containing detailed listing information
    """
    proxy_manager = get_proxy_manager()

    last_error: Optional[Exception] = None
    result = None

    max_proxy_attempts = proxy_manager.proxy_count
    attempted = 0

    while attempted < max_proxy_attempts:
        proxy = proxy_manager.get_healthy_proxy(strategy="round_robin")
        if not proxy:
            break
        attempted += 1

        result = get_listing_data(room_id, proxy=proxy)
        if isinstance(result, dict) and "error" in result:
            err = result.get("error", "")
            # Don't punish proxies for a genuine missing-data page structure.
            if "Could not find" not in err:
                proxy_manager.mark_failed(proxy)
                last_error = Exception(err)
                result = None
                continue
        last_error = None
        break

    if result is None:
        try:
            result = get_listing_data(room_id, proxy=None)
            last_error = None
        except Exception as e:
            last_error = e
            result = {"error": str(e)}
        
        if isinstance(result, dict) and "error" in result:
            # Mark proxy as failed if we got an error
            return {
                "success": False,
                "error": result["error"],
            }
        
        return {
            "success": True,
            "data": result,
        }
        

