"""Search routes for the Airbnb API."""

from fastapi import APIRouter, HTTPException
from fastapi_versioning import version

from models.schemas import (
    SearchRequest,
    SearchResponse,
    ListingSummary,
    AmenityInfo,
    RoomTypeInfo,
    ErrorResponse,
)
from scraper import search_listings, AMENITY_MAP, ROOM_TYPE_MAP, get_proxy_manager
from scraper.core import SearchParams

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "",
    response_model=SearchResponse,
    responses={
        200: {"description": "Successful search"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Search Airbnb listings",
    description="""
    Search for Airbnb listings based on location, dates, and optional filters.
    
    **Note:** This endpoint performs live scraping, so response times may vary.
    For best results, limit max_pages to 1-3 for faster responses.
    """,
)
@version(1)
async def search_airbnb_listings(request: SearchRequest) -> SearchResponse:
    """Search for Airbnb listings with the given parameters."""
    
    # Validate date range
    if request.checkout <= request.checkin:
        raise HTTPException(
            status_code=400,
            detail="Checkout date must be after checkin date"
        )
    
    # Convert amenity enums to string keys
    amenity_keys = None
    if request.amenities:
        amenity_keys = [a.value for a in request.amenities]
    
    # Convert room type enum to string key
    room_type_key = None
    if request.room_type:
        room_type_key = request.room_type.value
    
    # Create search params
    params = SearchParams(
        location=request.location,
        checkin=str(request.checkin),
        checkout=str(request.checkout),
        adults=request.adults,
        children=request.children,
        infants=request.infants,
        pets=request.pets,
        min_price=request.min_price,
        max_price=request.max_price,
        min_bedrooms=request.min_bedrooms,
        min_beds=request.min_beds,
        min_bathrooms=request.min_bathrooms,
        room_type=room_type_key,
        amenities=amenity_keys,
        max_pages=request.max_pages,
    )
    
    # Perform search
    result = search_listings(params)
    
    # Build response
    listings = [
        ListingSummary(
            id=listing.get("id"),
            title=listing.get("title"),
            price_text=listing.get("price_text"),
            price_per_night=listing.get("price_per_night"),
            total_price_details=listing.get("total_price_details"),
            rating=listing.get("rating"),
            images=listing.get("images", []),
            url=listing.get("url"),
        )
        for listing in result.get("listings", [])
    ]
    
    return SearchResponse(
        success=result.get("success", False),
        location=request.location,
        checkin=str(request.checkin),
        checkout=str(request.checkout),
        total_results=len(listings),
        listings=listings,
        message=result.get("error"),
    )


@router.get(
    "/amenities",
    response_model=list[AmenityInfo],
    summary="List available amenities",
    description="Get a list of all available amenity filters that can be used in search requests.",
)
@version(1)
async def list_amenities() -> list[AmenityInfo]:
    """Get all available amenity filters."""
    return [
        AmenityInfo(
            id=key,
            name=value["name"],
            airbnb_id=int(value["id"]),
        )
        for key, value in AMENITY_MAP.items()
    ]


@router.get(
    "/room-types",
    response_model=list[RoomTypeInfo],
    summary="List available room types",
    description="Get a list of all available room type filters that can be used in search requests.",
)
@version(1)
async def list_room_types() -> list[RoomTypeInfo]:
    """Get all available room type filters."""
    return [
        RoomTypeInfo(
            id=key,
            name=value["name"],
            airbnb_value=value["enum"].value,
        )
        for key, value in ROOM_TYPE_MAP.items()
    ]


@router.get(
    "/proxy-status",
    summary="Get proxy status",
    description="Check the current proxy configuration and status.",
)
@version(1)
async def get_proxy_status() -> dict:
    """Get current proxy configuration status."""
    pm = get_proxy_manager()
    return {
        "proxies_configured": pm.has_proxies,
        "proxy_count": pm.proxy_count,
        "cooldown_seconds": pm.cooldown_seconds,
        "cooldown_active": pm.cooldown_active_count,
        "mode": "rotating_proxy" if pm.has_proxies else "direct_connection",
    }


@router.get(
    "/proxies",
    summary="List all proxies with their status",
    description="""
    Check all configured proxies and return their external IP and location.
    
    This endpoint makes a request through each proxy to determine:
    - Whether the proxy is reachable
    - The external IP address it provides
    - The geographic location of that IP
    
    **Note:** This endpoint may take several seconds if many proxies are configured,
    as each proxy is checked sequentially with a timeout.
    """,
)
@version(1)
async def list_proxies() -> dict:
    """List all proxies with their external IP and status."""
    pm = get_proxy_manager()
    
    if not pm.has_proxies:
        return {
            "proxies_configured": False,
            "message": "No proxies configured. Set PROXY_URLS environment variable.",
            "proxies": [],
        }
    
    # Check all proxies (this may take a while)
    proxy_info = pm.check_all_proxies(timeout=10)
    
    # Count stats
    up_count = sum(1 for p in proxy_info if p["status"] == "up")
    
    return {
        "proxies_configured": True,
        "total": pm.proxy_count,
        "up": up_count,
        "down": pm.proxy_count - up_count,
        "proxies": proxy_info,
    }
