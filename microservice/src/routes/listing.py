"""Listing routes for the Airbnb API."""

from fastapi import APIRouter, HTTPException
from fastapi_versioning import version

from models.schemas import (
    ListingResponse,
    BasicInfo,
    HostInfo,
    LocationInfo,
    ReviewInfo,
    ReviewBreakdown,
    AmenityGroup,
    PhotoInfo,
    ErrorResponse,
)
from scraper import get_listing_details

router = APIRouter(prefix="/listing", tags=["Listing"])


@router.get(
    "/{room_id}",
    response_model=ListingResponse,
    responses={
        200: {"description": "Listing details retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get listing details",
    description="""
    Get detailed information about a specific Airbnb listing.
    
    The room_id can be found in the listing URL, e.g., 
    for `https://www.airbnb.ch/rooms/12345678`, the room_id is `12345678`.
    """,
)
@version(1)
async def get_listing(room_id: str) -> ListingResponse:
    """Get detailed information about a specific Airbnb listing."""
    
    # Validate room_id format (should be numeric)
    if not room_id.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Invalid room_id format. Room ID should be numeric."
        )
    
    # Fetch listing details
    result = get_listing_details(room_id)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error occurred")
        
        # Check if it's a "not found" type error
        if "Could not find" in error_msg or "Could not locate" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        
        raise HTTPException(status_code=500, detail=error_msg)
    
    data = result.get("data", {})
    
    # Parse basic info
    basic_info_data = data.get("basic_info", {})
    basic_info = BasicInfo(
        title=basic_info_data.get("title"),
        property_type=basic_info_data.get("property_type"),
        person_capacity=basic_info_data.get("person_capacity"),
    )
    
    # Parse host info
    host_data = data.get("host", {})
    host = HostInfo(
        name=host_data.get("name"),
        is_superhost=host_data.get("is_superhost"),
        is_verified=host_data.get("is_verified"),
        joined=host_data.get("joined"),
        about=host_data.get("about"),
    )
    
    # Parse location info
    location_data = data.get("location", {})
    location = LocationInfo(
        name=location_data.get("name"),
        lat=location_data.get("lat"),
        lng=location_data.get("lng"),
        is_verified=location_data.get("is_verified"),
    )
    
    # Parse reviews
    reviews_data = data.get("reviews", {})
    category_breakdown = [
        ReviewBreakdown(
            category=item.get("category"),
            rating=item.get("rating"),
        )
        for item in reviews_data.get("category_breakdown", [])
    ]
    reviews = ReviewInfo(
        overall_rating=reviews_data.get("overall_rating"),
        total_count=reviews_data.get("total_count"),
        category_breakdown=category_breakdown,
    )
    
    # Parse amenities
    amenities = [
        AmenityGroup(
            category=group.get("category"),
            items=group.get("items", []),
        )
        for group in data.get("amenities", [])
    ]
    
    # Parse photos
    photos = [
        PhotoInfo(
            url=photo.get("url"),
            caption=photo.get("caption"),
        )
        for photo in data.get("photos", [])
    ]
    
    return ListingResponse(
        success=True,
        room_id=room_id,
        basic_info=basic_info,
        host=host,
        description=data.get("description"),
        amenities=amenities,
        house_rules=data.get("house_rules", []),
        reviews=reviews,
        location=location,
        photos=photos,
    )
