"""Pydantic schemas for API request and response models."""

from datetime import date
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class AmenityEnum(str, Enum):
    """Available amenities for filtering Airbnb searches."""
    WIFI = "wifi"
    KITCHEN = "kitchen"
    WASHER = "washer"
    DEDICATED_WORKSPACE = "dedicated_workspace"
    TV = "tv"
    POOL = "pool"
    HOT_TUB = "hot_tub"
    FREE_PARKING = "free_parking"
    EV_CHARGER = "ev_charger"
    CRIB = "crib"
    KING_BED = "king_bed"
    GYM = "gym"
    BBQ_GRILL = "bbq_grill"
    BREAKFAST = "breakfast"
    INDOOR_FIREPLACE = "indoor_fireplace"
    SMOKING_ALLOWED = "smoking_allowed"
    SMOKE_ALARM = "smoke_alarm"
    CARBON_MONOXIDE_ALARM = "carbon_monoxide_alarm"


class RoomTypeEnum(str, Enum):
    """Available room types for filtering."""
    ENTIRE_HOME = "entire_home"
    PRIVATE_ROOM = "private_room"


class SearchRequest(BaseModel):
    """Request model for searching Airbnb listings."""
    
    location: str = Field(..., description="Location to search (e.g., 'Paris', 'Tokyo')")
    checkin: date = Field(..., description="Check-in date (YYYY-MM-DD)")
    checkout: date = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(default=1, ge=1, le=16, description="Number of adults")
    children: int = Field(default=0, ge=0, le=16, description="Number of children")
    infants: int = Field(default=0, ge=0, le=5, description="Number of infants")
    pets: int = Field(default=0, ge=0, le=5, description="Number of pets")
    
    # Filters
    min_price: Optional[int] = Field(default=None, ge=0, description="Minimum price per night")
    max_price: Optional[int] = Field(default=None, ge=0, description="Maximum price per night")
    min_bedrooms: Optional[int] = Field(default=None, ge=0, description="Minimum number of bedrooms")
    min_beds: Optional[int] = Field(default=None, ge=0, description="Minimum number of beds")
    min_bathrooms: Optional[int] = Field(default=None, ge=0, description="Minimum number of bathrooms")
    room_type: Optional[RoomTypeEnum] = Field(default=None, description="Type of room")
    amenities: Optional[list[AmenityEnum]] = Field(default=None, description="Required amenities")
    
    # Pagination
    max_pages: int = Field(default=1, ge=1, le=10, description="Maximum number of pages to scrape (1-10)")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Paris",
                "checkin": "2026-02-02",
                "checkout": "2026-02-05",
                "adults": 2,
                "children": 0,
                "infants": 0,
                "pets": 0,
                "min_price": 50,
                "max_price": 300,
                "min_bedrooms": 1,
                "room_type": "entire_home",
                "amenities": ["wifi", "kitchen"],
                "max_pages": 2
            }
        }


class ListingSummary(BaseModel):
    """Summary of an Airbnb listing from search results."""
    
    id: Optional[str] = Field(None, description="Airbnb listing ID")
    title: Optional[str] = Field(None, description="Listing title")
    price_text: Optional[str] = Field(None, description="Price as displayed text")
    price_per_night: Optional[int] = Field(None, description="Price per night as integer")
    total_price_details: Optional[str] = Field(None, description="Total price accessibility label")
    rating: Optional[str] = Field(None, description="Rating string (e.g., '4.85 (123)')")
    images: list[str] = Field(default_factory=list, description="List of image URLs")
    url: Optional[str] = Field(None, description="Direct URL to the listing")


class SearchResponse(BaseModel):
    """Response model for search results."""
    
    success: bool = Field(..., description="Whether the search was successful")
    location: str = Field(..., description="Searched location")
    checkin: str = Field(..., description="Check-in date")
    checkout: str = Field(..., description="Check-out date")
    total_results: int = Field(..., description="Total number of listings found")
    listings: list[ListingSummary] = Field(default_factory=list, description="List of listings")
    message: Optional[str] = Field(None, description="Additional message or error details")


class PhotoInfo(BaseModel):
    """Photo information from a listing."""
    url: Optional[str] = None
    caption: Optional[str] = None


class ReviewBreakdown(BaseModel):
    """Category breakdown for reviews."""
    category: Optional[str] = None
    rating: Optional[str] = None


class ReviewInfo(BaseModel):
    """Review information for a listing."""
    overall_rating: Optional[float] = None
    total_count: Optional[int] = None
    category_breakdown: list[ReviewBreakdown] = Field(default_factory=list)


class LocationInfo(BaseModel):
    """Location information for a listing."""
    name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_verified: Optional[bool] = None


class HostInfo(BaseModel):
    """Host information for a listing."""
    name: Optional[str] = None
    is_superhost: Optional[bool] = None
    is_verified: Optional[bool] = None
    joined: Optional[str] = None
    about: Optional[str] = None


class BasicInfo(BaseModel):
    """Basic information for a listing."""
    title: Optional[str] = None
    property_type: Optional[str] = None
    person_capacity: Optional[int] = None


class AmenityGroup(BaseModel):
    """Group of amenities."""
    category: Optional[str] = None
    items: list[str] = Field(default_factory=list)


class ListingResponse(BaseModel):
    """Detailed response for a single listing."""
    
    success: bool = Field(..., description="Whether the request was successful")
    room_id: str = Field(..., description="Airbnb room ID")
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    host: HostInfo = Field(default_factory=HostInfo)
    description: Optional[str] = None
    amenities: list[AmenityGroup] = Field(default_factory=list)
    house_rules: list[str] = Field(default_factory=list)
    reviews: ReviewInfo = Field(default_factory=ReviewInfo)
    location: LocationInfo = Field(default_factory=LocationInfo)
    photos: list[PhotoInfo] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if request failed")


class AmenityInfo(BaseModel):
    """Information about an available amenity filter."""
    id: str = Field(..., description="Amenity identifier")
    name: str = Field(..., description="Human-readable name")
    airbnb_id: int = Field(..., description="Airbnb internal amenity ID")


class RoomTypeInfo(BaseModel):
    """Information about an available room type filter."""
    id: str = Field(..., description="Room type identifier")
    name: str = Field(..., description="Human-readable name")
    airbnb_value: str = Field(..., description="Airbnb internal room type value")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "airbnb-api"
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
