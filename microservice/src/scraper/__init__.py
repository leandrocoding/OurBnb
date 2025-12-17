"""
Scraper module for the Airbnb API.

This module provides a clean interface to the scraping functionality,
wrapping the core scraping logic from the scraper-worker.
"""

from .core import (
    search_listings,
    get_listing_details,
    find_price_range,
    SearchParams,
    AMENITY_MAP,
    ROOM_TYPE_MAP,
)
from .proxy import (
    get_proxy_manager,
    configure_proxies,
    ProxyManager,
)

__all__ = [
    "search_listings",
    "get_listing_details",
    "find_price_range",
    "SearchParams",
    "AMENITY_MAP",
    "ROOM_TYPE_MAP",
    "get_proxy_manager",
    "configure_proxies",
    "ProxyManager",
]
