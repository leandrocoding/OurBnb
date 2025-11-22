import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote

def build_airbnb_url(location, guests, checkin, checkout):
    """
    Constructs the search URL based on parameters.
    Easily expandable for future filters (price_min, room_types, etc).
    """
    base_url = "https://www.airbnb.ch/s"
    
    # URL Encode the location string (e.g., "Zürich" -> "Z%C3%BCrich")
    safe_location = quote(location)
    
    # Construct the path
    url_path = f"{base_url}/{safe_location}/homes"
    
    # Construct query parameters
    params = {
        "refinement_paths[]": "/homes",
        "date_picker_type": "calendar",
        "checkin": checkin,   # Format: YYYY-MM-DD
        "checkout": checkout, # Format: YYYY-MM-DD
        "adults": guests,
        "search_type": "search_query"
    }
    
    # Request library handles parameter encoding automatically, 
    # but we return the base and params dict separately for the request function
    return url_path, params

def parse_airbnb_response(html_content):
    """
    Extracts the embedded JSON state from the HTML and parses listings.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Airbnb stores the initial state in a script tag with this specific ID
    # based on the HTML provided.
    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
    
    if not script_tag:
        return {"error": "Could not find data state script tag. Airbnb format may have changed."}

    try:
        data = json.loads(script_tag.text)
    except json.JSONDecodeError:
        return {"error": "Failed to decode JSON data."}

    listings = []
    
    # Navigate the deep JSON structure to find search results
    # Path based on provided HTML: 
    # niobeClientData -> [Find StaysSearch] -> data -> presentation -> staysSearch -> results -> searchResults
    
    niobe_data = data.get('niobeClientData', [])
    
    search_results = []
    
    # The niobeClientData is an array of arrays. We need to find the one containing "StaysSearch"
    for item in niobe_data:
        # The first element is the query signature, the second is the data
        if len(item) > 1 and isinstance(item[1], dict) and 'data' in item[1]:
            presentation = item[1]['data'].get('presentation', {})
            stays_search = presentation.get('staysSearch', {})
            results = stays_search.get('results', {})
            search_results = results.get('searchResults', [])
            if search_results:
                break

    for result in search_results:
        # Skip items that aren't actual listings (sometimes they inject ads or map info)
        if result.get('__typename') != 'StaySearchResult':
            continue

        # Extract listing details safely
        listing_obj = result.get('listing', {}) # Sometimes listed directly or nested
        
        # Based on your HTML, the ID is inside 'demandStayListing' or 'listing'
        # Note: Your HTML shows IDs inside `demandStayListing`. 
        # However, the main object usually has `structuredDisplayPrice`.
        
        # Basic Info
        listing_id = result.get('listingId') # Or try looking deeper if null
        
        # Getting the price
        price_obj = result.get('structuredDisplayPrice', {}).get('primaryLine', {})
        price_text = price_obj.get('price', 'N/A')
        price_accessibility = price_obj.get('accessibilityLabel', 'N/A')

        # Getting the title/name
        listing_title = result.get('listing', {}).get('name') 
        # Fallback based on your HTML specific structure:
        if not listing_title:
             listing_title = result.get('nameLocalized', {}).get('localizedStringWithTranslationPreference')

        # Rating
        rating = result.get('avgRatingLocalized', 'N/A')

        # Image
        pictures = result.get('contextualPictures', [])
        image_url = [pic.get('picture') for pic in pictures ] if pictures  else None

        # Badges (e.g., Guest Favorite)
        badges = [b.get('text') for b in result.get('badges', []) if b.get('text')]
        price_int = int(price_accessibility.split()[0])
        listings.append({
            "id": listing_id,
            "title": listing_title,
            "price_text": price_text,
            "total_price_details": price_accessibility,
            "price_int":price_int,
            "rating": rating,
            "badges": badges,
            "image": image_url,
            "url": f"https://www.airbnb.ch/rooms/{listing_id}" if listing_id else None
        })

    return listings

def scrape_airbnb(location, guests, checkin, checkout):
    url, params = build_airbnb_url(location, guests, checkin, checkout)
    
    # Headers matching your browser request to avoid 403/Blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Alt-Used": "www.airbnb.ch",
        "Priority": "u=0, i"
    }

    print(f"Fetching: {url} with params {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status() # Raise error for 404 or 500
        
        # Parse the response
        data = parse_airbnb_response(response.text)
        return json.dumps(data, indent=4, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})

# --- Example Usage ---
if __name__ == "__main__":
    # Inputs
    loc = "universitätsstrasse Zürich"
    ppl = 2
    in_date = "2025-11-28"
    out_date = "2025-11-30"

    result_json = scrape_airbnb(loc, ppl, in_date, out_date)
    print(result_json)