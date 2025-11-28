import requests
import json
import re
import base64
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote
from enum import IntEnum, Enum

class Amenities(IntEnum):
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
    ENTIRE_HOME = "Entire home/apt"
    PRIVATE_ROOM = "Private room"

def build_airbnb_url(location, guests, checkin, checkout, price_min=None, price_max=None, amenities=None, room_type=None, min_bedrooms=None, min_beds=None, min_bathrooms=None):
    base_url = "https://www.airbnb.ch/s"
    url_path = f"{base_url}/homes"
    # TODO: Fix üöä etc. Currently not working e.g. Zürich
    # TODO: This is a bad fix that might work for now.

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
        "adults": guests,
        "search_type": "search_query",
        "query": sanitized_location,
        # "pagination_search": "true", # Only needed for page 2+
        # "cursor": "..." # Only needed for page 2+
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
        # If we have multiple filters or specific combinations, this might need to be true/false
        # Based on observation: single amenity -> false, multiple amenities -> true.
        # price only -> false/true depending on if it's both min/max.
        # Let's set it to true if we have more than one filter condition in selected_filter_order
        if len(selected_filter_order) > 1:
             params["update_selected_filters"] = "true"
        else:
             params["update_selected_filters"] = "false"
             
        if selected_filter_order:
            params["selected_filter_order[]"] = selected_filter_order

    return url_path, params

def parse_airbnb_response(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
    if not script_tag:
        with open("script_not_found.html", "w") as f:
            f.write(html_content)
        return {"error": "Could not find data state script tag (data-deferred-state-0)., see script_not_found.html"}, None

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
        price_accessibility = price_obj.get('accessibilityLabel', '')

        # Price Integer
        price_int = int(price_accessibility.split()[0])
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
# TODO add support for additional search params
def search_airbnb(location, guests, checkin, checkout, min_price=None, max_price=None, amenities=None, room_type=None, min_bedrooms=None, min_beds=None, min_bathrooms=None, max_pages=2):
    url_path, params = build_airbnb_url(location, guests, checkin, checkout, price_min=min_price, price_max=max_price, amenities=amenities, room_type=room_type, min_bedrooms=min_bedrooms, min_beds=min_beds, min_bathrooms=min_bathrooms)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-CH,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Alt-Used": "www.airbnb.ch",
        "Priority": "u=0, i"
    }

    all_listings = []
    current_cursor = None

    for page in range(1, max_pages + 1):
        print(f"--- Scraping Page {page} ---")

        # Prepare params for pagination
        current_params = params.copy()
        if current_cursor:
            current_params['pagination_search'] = 'true'
            current_params['cursor'] = current_cursor

        try:
            response = requests.get(url_path, params=current_params, headers=headers)
            print(response.url)
            with open("testout.html", "w", encoding="utf-8") as f:

                f.write(response.text)
            response.raise_for_status()

            listings, next_cursor = parse_airbnb_response(response.text)

            if isinstance(listings, dict) and "error" in listings:
                print(f"Error on page {page}: {listings['error']}")
                break

            all_listings.extend(listings)
            print(f"Found {len(listings)} listings on page {page}.")

            # Logic to stop or continue
            if not next_cursor:
                print("No more pages available.")
                break

            current_cursor = next_cursor

            # Important: Sleep to behave like a browser and avoid blocking
            if page < max_pages:
                time.sleep(2)

        except requests.exceptions.RequestException as e:
            print(f"Request error on page {page}: {e}")
            break

    return json.dumps(all_listings, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    loc = "Zürich"
    ppl = 2
    in_date = "2025-11-28"
    out_date = "2025-11-30"

    # Example with filters
    result_json = search_airbnb(
        loc, ppl, in_date, out_date, 
        min_price=100, 
        max_price=500, 
        amenities=[Amenities.WIFI, Amenities.KITCHEN], 
        room_type=RoomType.ENTIRE_HOME,
        min_bedrooms=2,
        min_bathrooms=1,
        max_pages=1
    )

    # Optional: Write to file to inspect easier
    with open("airbnb_results.json", "w", encoding="utf-8") as f:
        f.write(result_json)
    print(result_json)

    print("Scraping complete. Results saved to airbnb_results.json")
