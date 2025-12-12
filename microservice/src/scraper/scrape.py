"""
Airbnb Search Scraper

This code is originally from scraper-worker/scrape.py
Copied here to allow the airbnb-api microservice to function independently.

Original purpose: Scrape Airbnb search results with filters.
"""

import requests
import json
import re
import base64
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote
from enum import IntEnum, Enum
from typing import Callable, Literal


class Amenities(IntEnum):
    """Airbnb amenity IDs for filtering search results."""
    WIFI = 4
    KITCHEN = 8
    WASHER = 33
    DEDICATED_WORKSPACE = 47
    TV = 58
    POOL = 7
    HOT_TUB = 25
    FREE_PARKING = 9
    EV_CHARGER = 97
    CRIB = 286
    KING_BED = 1000
    GYM = 15
    BBQ_GRILL = 99
    BREAKFAST = 16
    INDOOR_FIREPLACE = 27
    SMOKING_ALLOWED = 11
    SMOKE_ALARM = 35
    CARBON_MONOXIDE_ALARM = 36


class RoomType(Enum):
    """Airbnb room type values for filtering."""
    ENTIRE_HOME = "Entire home/apt"
    PRIVATE_ROOM = "Private room"


def build_airbnb_url(
    location,
    adults,
    children,
    infants,
    pets,
    checkin,
    checkout,
    price_min=None,
    price_max=None,
    amenities=None,
    room_type=None,
    min_bedrooms=None,
    min_beds=None,
    min_bathrooms=None
):
    """Build Airbnb search URL with all parameters."""
    base_url = "https://www.airbnb.ch/s"
    url_path = f"{base_url}/homes"
    
    # Handle special characters in location
    replacements = {
        'ä': 'a', 'Ä': 'A',
        'ö': 'o', 'Ö': 'O',
        'ü': 'u', 'Ü': 'U',
        'ß': 'ss'
    }
    sanitized_location = location
    for char, replacement in replacements.items():
        sanitized_location = sanitized_location.replace(char, replacement)

    params = {
        "refinement_paths[]": "/homes",
        "date_picker_type": "calendar",
        "checkin": checkin,
        "checkout": checkout,
        "adults": adults,
        "children": children,
        "infants": infants,
        "pets": pets,
        "search_type": "search_query",
        "query": sanitized_location,
    }

    # Calculate number of nights for price filter
    try:
        d1 = datetime.strptime(checkin, "%Y-%m-%d")
        d2 = datetime.strptime(checkout, "%Y-%m-%d")
        num_nights = (d2 - d1).days
    except (ValueError, TypeError):
        num_nights = None

    selected_filter_order = []
    has_filters = False

    if price_min is not None or price_max is not None:
        has_filters = True
        params["price_filter_input_type"] = "2"
        params["channel"] = "EXPLORE"
        if num_nights:
            params["price_filter_num_nights"] = str(num_nights)

        if price_min is not None:
            params["price_min"] = str(price_min)
            selected_filter_order.append(f"price_min:{price_min}")

        if price_max is not None:
            params["price_max"] = str(price_max)
            selected_filter_order.append(f"price_max:{price_max}")

    if amenities:
        has_filters = True
        if not isinstance(amenities, list):
            amenities = [amenities]

        # Convert Enum members to their values if necessary
        clean_amenities = []
        for a in amenities:
            if isinstance(a, IntEnum):
                clean_amenities.append(a.value)
            else:
                clean_amenities.append(a)

        params["amenities[]"] = clean_amenities
        for amenity in clean_amenities:
            selected_filter_order.append(f"amenities:{amenity}")

    if room_type is not None:
        has_filters = True
        room_type_value = room_type.value if isinstance(room_type, Enum) else room_type
        params["room_types[]"] = room_type_value
        selected_filter_order.append(f"room_types:{room_type_value}")

    if min_bedrooms is not None:
        has_filters = True
        params["min_bedrooms"] = str(min_bedrooms)
        selected_filter_order.append(f"min_bedrooms:{min_bedrooms}")

    if min_beds is not None:
        has_filters = True
        params["min_beds"] = str(min_beds)
        selected_filter_order.append(f"min_beds:{min_beds}")

    if min_bathrooms is not None:
        has_filters = True
        params["min_bathrooms"] = str(min_bathrooms)
        selected_filter_order.append(f"min_bathrooms:{min_bathrooms}")

    if has_filters:
        params["search_type"] = "filter_change"
        params["search_mode"] = "regular_search"
        if len(selected_filter_order) > 1:
            params["update_selected_filters"] = "true"
        else:
            params["update_selected_filters"] = "false"

        if selected_filter_order:
            params["selected_filter_order[]"] = selected_filter_order
            
    return url_path, params


def parse_airbnb_response(html_content):
    """Parse Airbnb search response HTML and extract listings."""
    soup = BeautifulSoup(html_content, 'html.parser')

    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
    if not script_tag:
        return {"error": "Could not find data state script tag (data-deferred-state-0)"}, None

    try:
        data = json.loads(script_tag.text)
    except json.JSONDecodeError:
        return {"error": "Failed to decode JSON data."}, None

    listings = []
    next_cursor = None

    # Navigate to results
    niobe_data = data.get('niobeClientData', [])
    search_results = []

    for item in niobe_data:
        if len(item) > 1 and isinstance(item[1], dict) and 'data' in item[1]:
            presentation = item[1]['data'].get('presentation', {})
            stays_search = presentation.get('staysSearch', {})

            # 1. Get Listings
            results = stays_search.get('results', {})
            search_results = results.get('searchResults', [])

            # 2. Get Cursor for Next Page
            pagination_info = results.get('paginationInfo', {})
            next_cursor = pagination_info.get('nextPageCursor')

            if search_results:
                break

    for result in search_results:
        if result.get('__typename') != 'StaySearchResult':
            continue

        # ID Extraction with Base64 Decode
        encoded_id = result.get('demandStayListing', {}).get('id')
        listing_id = None

        if encoded_id:
            try:
                decoded_str = base64.b64decode(encoded_id).decode('utf-8')
                listing_id = decoded_str.split(':')[-1]
            except:
                listing_id = encoded_id

        # Basic Info
        listing_title = result.get('nameLocalized', {}).get('localizedStringWithTranslationPreference')
        if not listing_title:
            listing_title = result.get('listing', {}).get('name')

        # Prices
        price_obj = result.get('structuredDisplayPrice', {}).get('primaryLine', {})
        price_text = price_obj.get('price', 'N/A')
        if price_text == 'N/A':
            price_text = price_obj.get('discountedPrice', 'N/A')
        price_accessibility = price_obj.get('accessibilityLabel', '')

        price_int = 0
        if price_text and price_text != 'N/A':
            try:
                clean_price = price_text.replace("'", "").replace("CHF", "").strip()
                price_int = int(clean_price)
            except (ValueError, AttributeError):
                price_int = 0

        # Rating
        rating = result.get('avgRatingLocalized', 'N/A')

        # Images
        pictures = result.get('contextualPictures', [])
        image_urls = [pic.get('picture') for pic in pictures if pic.get('picture')]

        listings.append({
            "id": listing_id,
            "title": listing_title,
            "price_text": price_text,
            "price_int": price_int,
            "total_price_details": price_accessibility,
            "rating": rating,
            "images": image_urls,
            "url": f"https://www.airbnb.ch/rooms/{listing_id}" if listing_id else None
        })

    return listings, next_cursor
