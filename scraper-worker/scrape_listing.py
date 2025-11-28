import requests
from bs4 import BeautifulSoup
import json

def get_listing_data(room_id):
    url = f"https://www.airbnb.ch/rooms/{room_id}"
    
    # headers are critical to avoid bot detection
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract the raw JSON blob from the <script> tag
        script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
        if not script_tag:
            return {"error": "Could not find data-deferred-state-0"}
            
        raw_data = json.loads(script_tag.text)
        
        # 2. Locate the specific 'StayProductDetailPage' data within the Niobe client cache
        # The structure is usually: niobeClientData -> List of entries -> Entry is [QueryString, DataObject]
        pdp_data = None
        niobe_data = raw_data.get('niobeClientData', [])
        
        for entry in niobe_data:
            # We look for the entry that contains 'stayProductDetailPage'
            if len(entry) > 1 and isinstance(entry[1], dict):
                potential_data = entry[1].get('data', {}).get('presentation', {}).get('stayProductDetailPage')
                if potential_data:
                    pdp_data = potential_data
                    break
        
        if not pdp_data:
            return {"error": "Could not locate PDP data in JSON structure"}

        # 3. Parse and Clean the Data
        return parse_pdp_sections(pdp_data)

    except Exception as e:
        return {"error": str(e)}

def parse_pdp_sections(pdp_data):
    """
    Iterates through the specific UI sections (Reviews, Location, Description)
    and extracts only the human-readable data.
    """
    clean_data = {
        "basic_info": {},
        "host": {},
        "description": "",
        "amenities": [],
        "house_rules": [],
        "reviews": {},
        "location": {},
        "photos": []
    }

    # Airbnb splits data into "sections"
    sections = pdp_data.get('sections', {}).get('sections', [])

    for section in sections:
        s_id = section.get('sectionId')
        s_data = section.get('section')

        if not s_data: continue

        # --- Title & Basic Stats ---
        if s_id == 'TITLE_DEFAULT':
            clean_data['basic_info']['title'] = s_data.get('title')
            clean_data['basic_info']['property_type'] = s_data.get('sharingConfig', {}).get('propertyType')
            clean_data['basic_info']['person_capacity'] = s_data.get('embedData', {}).get('personCapacity')

        # --- Photos ---
        elif s_id == 'PHOTO_TOUR_SCROLLABLE_MODAL':
            media_items = s_data.get('mediaItems', [])
            clean_data['photos'] = [
                {
                    "url": item.get('baseUrl'),
                    "caption": item.get('accessibilityLabel')
                } for item in media_items
            ]

        # --- Description ---
        elif s_id == 'DESCRIPTION_DEFAULT':
            clean_data['description'] = s_data.get('htmlDescription', {}).get('htmlText')

        # --- Amenities ---
        elif s_id == 'AMENITIES_DEFAULT':
            # Groups: Bathroom, Bedroom, Internet, etc.
            groups = s_data.get('seeAllAmenitiesGroups', [])
            for group in groups:
                group_name = group.get('title')
                items = [item.get('title') for item in group.get('amenities', []) if item.get('available')]
                if items:
                    clean_data['amenities'].append({
                        "category": group_name,
                        "items": items
                    })

        # --- Reviews & Ratings ---
        elif s_id == 'REVIEWS_DEFAULT':
            clean_data['reviews'] = {
                "overall_rating": s_data.get('overallRating'),
                "total_count": s_data.get('overallCount'),
                "category_breakdown": [
                    {
                        "category": r.get('label'),
                        "rating": r.get('localizedRating')
                    } for r in s_data.get('ratings', [])
                ]
            }

        # --- Location ---
        elif s_id == 'LOCATION_DEFAULT':
            clean_data['location'] = {
                "name": s_data.get('subtitle'), # e.g., "Zürich, Switzerland"
                "lat": s_data.get('lat'),
                "lng": s_data.get('lng'),
                "is_verified": s_data.get('listingLocationVerificationDetails', {}).get('isVerified')
            }

        # --- Host Info ---
        elif s_id == 'MEET_YOUR_HOST':
            card = s_data.get('cardData', {})
            clean_data['host'] = {
                "name": card.get('name'),
                "is_superhost": card.get('isSuperhost'),
                "is_verified": card.get('isVerified'),
                "joined": s_data.get('overviewItems', [{}])[0].get('title'), # e.g. "Hosted for 1 year"
                "about": s_data.get('about')
            }

        # --- House Rules ---
        elif s_id == 'POLICIES_DEFAULT':
             # Looking into houseRulesSections for detail
            rule_sections = s_data.get('houseRulesSections', [])
            for rs in rule_sections:
                items = [item.get('title') for item in rs.get('items', [])]
                clean_data['house_rules'].extend(items)

    return clean_data

if __name__ == "__main__":

# --- EXECUTION ---
    room_id = "1289024964833416671"
    result = get_listing_data(room_id)

    result_json = json.dumps(result, indent=2, ensure_ascii=False)
    with open("airbnb_results_listing.json", "w", encoding="utf-8") as f:
            f.write(result_json)
    # print()