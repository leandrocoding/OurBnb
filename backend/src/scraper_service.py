"""
Service to integrate with the scraper-worker for fetching Airbnb listings.
"""
import sys
import os
import json
import re
from typing import List, Optional
from datetime import date
from decimal import Decimal

# Add scraper-worker to path
scraper_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scraper-worker')
if scraper_path not in sys.path:
    sys.path.insert(0, scraper_path)

try:
    from scrape import search_airbnb
except ImportError:
    # Fallback if scraper not available
    def search_airbnb(*args, **kwargs):
        return "[]"


def parse_rating(rating_str: Optional[str]) -> tuple[Optional[Decimal], int]:
    """Parse rating string like '4.85 (20)' into rating and review count."""
    if not rating_str or rating_str in ['N/A', 'Neu', 'New', None]:
        return None, 0
    
    # Try to match pattern like "4.85 (20)" or just "4.85"
    match = re.match(r'(\d+\.?\d*)\s*\((\d+)\)?', str(rating_str))
    if match:
        rating = Decimal(match.group(1))
        count = int(match.group(2))
        return rating, count
    
    # Try just a number
    try:
        return Decimal(rating_str), 0
    except:
        return None, 0


def fetch_listings_for_group(
    location: str,
    guests: int,
    checkin: date,
    checkout: date,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_pages: int = 2
) -> List[dict]:
    """
    Fetch listings from Airbnb using the scraper.
    
    Returns a list of listing dictionaries with normalized fields.
    """
    try:
        result_json = search_airbnb(
            location=location,
            guests=guests,
            checkin=checkin.isoformat(),
            checkout=checkout.isoformat(),
            min_price=min_price,
            max_price=max_price,
            max_pages=max_pages
        )
        
        listings_raw = json.loads(result_json)
        
        normalized = []
        for listing in listings_raw:
            rating, review_count = parse_rating(listing.get('rating'))
            
            normalized.append({
                'airbnb_id': str(listing.get('id')),
                'title': listing.get('title', 'Untitled'),
                'price_per_night': listing.get('price_int', 0),
                'bnb_rating': rating,
                'bnb_review_count': review_count,
                'main_image_url': listing.get('images', [None])[0] if listing.get('images') else None,
                'images': listing.get('images', []),
                'url': listing.get('url'),
            })
        
        return normalized
        
    except Exception as e:
        print(f"Error fetching listings: {e}")
        return []


