"""
Airbnb Listing Scraper

This code is originally from scraper-worker/scrape_listing.py
Copied here to allow the airbnb-api microservice to function independently.

Original purpose: Scrape detailed Airbnb listing data by room ID.
"""

import random
import requests
from bs4 import BeautifulSoup
import json
from typing import Optional

# Inline header randomization for listing scraper (keep it self-contained)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]
_ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "de-CH,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
]


def get_listing_data(room_id, proxy: Optional[dict] = None):
    """
    Fetch and parse detailed listing data from Airbnb.
    
    Args:
        room_id: The Airbnb room/listing ID
        proxy: Optional proxy dict for requests (can include auth in URL)
        
    Returns:
        Dictionary containing parsed listing data or error
    """
    url = f"https://www.airbnb.ch/rooms/{room_id}"
    
    # Randomized headers to reduce fingerprinting
    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    try:
        response = requests.get(url, headers=headers, proxies=proxy, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Extract the raw JSON blob from the <script> tag
        script_tag = soup.find('script', {'id': 'data-deferred-state-0'})
        if not script_tag:
            return {"error": "Could not find data-deferred-state-0"}
            
        raw_data = json.loads(script_tag.text)
        
        # 2. Locate the specific 'StayProductDetailPage' data within the Niobe client cache
        pdp_data = None
        niobe_data = raw_data.get('niobeClientData', [])
        
        for entry in niobe_data:
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

        if not s_data:
            continue

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
                "name": s_data.get('subtitle'),
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
                "joined": s_data.get('overviewItems', [{}])[0].get('title'),
                "about": s_data.get('about')
            }

        # --- House Rules ---
        elif s_id == 'POLICIES_DEFAULT':
            rule_sections = s_data.get('houseRulesSections', [])
            for rs in rule_sections:
                items = [item.get('title') for item in rs.get('items', [])]
                clean_data['house_rules'].extend(items)

    return clean_data
