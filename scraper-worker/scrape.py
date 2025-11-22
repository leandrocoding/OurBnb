import requests
import json
import re
import base64
import time
from bs4 import BeautifulSoup
from urllib.parse import quote

def build_airbnb_url(location, guests, checkin, checkout):
    base_url = "https://www.airbnb.ch/s"
    safe_location = quote(location)
    url_path = f"{base_url}/{safe_location}/homes"
    
    params = {
        "refinement_paths[]": "/homes",
        "date_picker_type": "calendar",
        "checkin": checkin,
        "checkout": checkout,
        "adults": guests,
        "search_type": "search_query"
        # "pagination_search": "true", # Only needed for page 2+
        # "cursor": "..." # Only needed for page 2+
    }
    return url_path, params

def parse_airbnb_response(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
    if not script_tag:
        return {"error": "Could not find data state script tag."}, None

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
        price_int = 0
        match = re.search(r'\d+', price_text)
        if match:
            price_int = int(match.group())

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

def scrape_airbnb(location, guests, checkin, checkout, max_pages=2):
    url_path, params = build_airbnb_url(location, guests, checkin, checkout)
    
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
    loc = "Berlin"
    ppl = 2
    in_date = "2025-11-28"
    out_date = "2025-11-30"

    result_json = scrape_airbnb(loc, ppl, in_date, out_date, max_pages=1)
    
    # Optional: Write to file to inspect easier
    with open("airbnb_results.json", "w", encoding="utf-8") as f:
        f.write(result_json)
    print(result_json)
        
    print("Scraping complete. Results saved to airbnb_results.json")