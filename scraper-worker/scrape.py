import requests
import json
import re
import base64
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
    }
    return url_path, params

def parse_airbnb_response(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Extract the JSON State
    script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
    if not script_tag:
        return {"error": "Could not find data state script tag."}

    try:
        data = json.loads(script_tag.text)
    except json.JSONDecodeError:
        return {"error": "Failed to decode JSON data."}

    listings = []
    
    # 2. Navigate to results
    niobe_data = data.get('niobeClientData', [])
    search_results = []
    
    for item in niobe_data:
        if len(item) > 1 and isinstance(item[1], dict) and 'data' in item[1]:
            presentation = item[1]['data'].get('presentation', {})
            stays_search = presentation.get('staysSearch', {})
            results = stays_search.get('results', {})
            search_results = results.get('searchResults', [])
            if search_results:
                break

    # 3. Parse each result
    for result in search_results:
        if result.get('__typename') != 'StaySearchResult':
            continue

        # --- FIX: ID Extraction ---
        # The ID is hidden inside 'demandStayListing' -> 'id'
        # It looks like "RGVtYW5kU3RheUxpc3Rpbmc6MTU..." (Base64 encoded)
        encoded_id = result.get('demandStayListing', {}).get('id')
        listing_id = None
        
        if encoded_id:
            try:
                # Decode base64 to get "DemandStayListing:1506252024..."
                decoded_str = base64.b64decode(encoded_id).decode('utf-8')
                # Extract just the number after the colon
                listing_id = decoded_str.split(':')[-1]
            except:
                # Fallback if not base64 or format differs
                listing_id = encoded_id

        # Basic Info
        # Name is localized in your HTML payload
        listing_title = result.get('nameLocalized', {}).get('localizedStringWithTranslationPreference')
        if not listing_title:
             listing_title = result.get('listing', {}).get('name')

        # Prices
        price_obj = result.get('structuredDisplayPrice', {}).get('primaryLine', {})
        price_text = price_obj.get('price', 'N/A')
        price_accessibility = price_obj.get('accessibilityLabel', '')
# https://www.airbnb.ch/s/universit%C3%A4tsstrasse-Z%C3%BCrich/homes?refinement_paths%5B%5D=%2Fhomes&date_picker_type=calendar&checkin=2025-11-28&checkout=2025-11-30&adults=2&query=universit%C3%A4tsstrasse%20Z%C3%BCrich&place_id=EiVVbml2ZXJzaXTDpHRzdHJhc3NlLCBaw7xyaWNoLCBTY2h3ZWl6Ii4qLAoUChIJwWJdJqGgmkcRe-5Y9I6NcmUSFAoSCRmivkmXC5BHEQPcH-fxjW7m&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-12-01&monthly_length=3&monthly_end_date=2026-03-01&price_filter_input_type=2&price_filter_num_nights=2&channel=EXPLORE&federated_search_session_id=d5f70041-c686-4c7b-b54a-8453f22cf3b1&pagination_search=true&cursor=eyJzZWN0aW9uX29mZnNldCI6MCwiaXRlbXNfb2Zmc2V0IjoxOCwidmVyc2lvbiI6MX0%3D
        # https://www.airbnb.ch/s/universit%C3%A4tsstrasse-Z%C3%BCrich/homes?refinement_paths%5B%5D=%2Fhomes&date_picker_type=calendar&checkin=2025-11-28&checkout=2025-11-30&adults=2&query=universit%C3%A4tsstrasse%20Z%C3%BCrich&place_id=EiVVbml2ZXJzaXTDpHRzdHJhc3NlLCBaw7xyaWNoLCBTY2h3ZWl6Ii4qLAoUChIJwWJdJqGgmkcRe-5Y9I6NcmUSFAoSCRmivkmXC5BHEQPcH-fxjW7m&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-12-01&monthly_length=3&monthly_end_date=2026-03-01&price_filter_input_type=2&price_filter_num_nights=2&channel=EXPLORE&pagination_search=true&cursor=eyJzZWN0aW9uX29mZnNldCI6MCwiaXRlbXNfb2Zmc2V0IjoxOCwidmVyc2lvbiI6MX0%3D 
        # --- FIX: Price Integer Parsing ---
        # Use regex to find the first sequence of digits, safer than split()[0]
        price_int = 0
        match = re.search(r'\d+', price_text) # Look at visual price "263 CHF"
        if match:
            price_int = int(match.group())

        # Rating
        rating = result.get('avgRatingLocalized', 'N/A')

        # Images
        pictures = result.get('contextualPictures', [])
        image_urls = [pic.get('picture') for pic in pictures if pic.get('picture')]

        # Badges
        badges = [b.get('text') for b in result.get('badges', []) if b.get('text')]

        listings.append({
            "id": listing_id,
            "title": listing_title,
            "price_text": price_text,
            "price_int": price_int,
            "total_price_details": price_accessibility,
            "rating": rating,
            "badges": badges,
            "images": image_urls,
            "url": f"https://www.airbnb.ch/rooms/{listing_id}" if listing_id else None
        })

    return listings

def scrape_airbnb(location, guests, checkin, checkout):
    url, params = build_airbnb_url(location, guests, checkin, checkout)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-CH,de;q=0.9,en-US;q=0.8,en;q=0.7", # Matched to .ch domain
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
        response.raise_for_status()
        
        data = parse_airbnb_response(response.text)
        return json.dumps(data, indent=4, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    loc = "Madrid"
    ppl = 2
    in_date = "2025-11-28"
    out_date = "2025-11-30"

    result_json = scrape_airbnb(loc, ppl, in_date, out_date)
    print(result_json)