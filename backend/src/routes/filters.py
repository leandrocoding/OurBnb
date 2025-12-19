"""
Filter management routes: get and set user filters.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from constants import PAGE_COUNT_AFTER_FILTER_SET
from models.schemas import UserFilter, FilterResponse
from db import get_cursor
from scrape_utils import trigger_search_for_user_destinations

router = APIRouter(tags=["Filters"])


@router.get("/filter/{u_id}", response_model=FilterResponse)
async def get_filter(u_id: int):
    """Get user filter by user ID. Returns default values if no filter exists."""
    with get_cursor() as cursor:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (u_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get filter
        cursor.execute(
            """
            SELECT user_id, min_price, max_price, min_bedrooms, min_beds, min_bathrooms, property_type, updated_at
            FROM user_filters
            WHERE user_id = %s
            """,
            (u_id,),
        )
        filter_row = cursor.fetchone()
        
        if filter_row:
            # Get filter amenities
            cursor.execute(
                "SELECT amenity_id FROM filter_amenities WHERE user_id = %s",
                (u_id,),
            )
            amenities = [row["amenity_id"] for row in cursor.fetchall()]
            
            return FilterResponse(
                user_id=filter_row["user_id"],
                min_price=filter_row["min_price"],
                max_price=filter_row["max_price"],
                min_bedrooms=filter_row["min_bedrooms"],
                min_beds=filter_row["min_beds"],
                min_bathrooms=filter_row["min_bathrooms"],
                property_type=filter_row["property_type"],
                updated_at=filter_row["updated_at"],
                amenities=amenities,
            )
        
        # Return default filter values if none exists (max 25000/night)
        return FilterResponse(user_id=u_id)


@router.patch("/filter/{u_id}", response_model=FilterResponse)
async def set_filter(u_id: int, filter_data: UserFilter):
    """Set or update user filter."""
    with get_cursor() as cursor:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (u_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        now = datetime.now()
        
        # Upsert filter (insert or update)
        cursor.execute(
            """
            INSERT INTO user_filters (user_id, min_price, max_price, min_bedrooms, min_beds, min_bathrooms, property_type, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                min_price = EXCLUDED.min_price,
                max_price = EXCLUDED.max_price,
                min_bedrooms = EXCLUDED.min_bedrooms,
                min_beds = EXCLUDED.min_beds,
                min_bathrooms = EXCLUDED.min_bathrooms,
                property_type = EXCLUDED.property_type,
                updated_at = EXCLUDED.updated_at
            RETURNING user_id, min_price, max_price, min_bedrooms, min_beds, min_bathrooms, property_type, updated_at
            """,
            (
                u_id,
                filter_data.min_price,
                filter_data.max_price,
                filter_data.min_bedrooms,
                filter_data.min_beds,
                filter_data.min_bathrooms,
                filter_data.property_type,
                now,
            ),
        )
        filter_row = cursor.fetchone()
        
        # Delete existing filter amenities and insert new ones
        cursor.execute("DELETE FROM filter_amenities WHERE user_id = %s", (u_id,))
        
        if filter_data.amenities:
            for amenity_id in filter_data.amenities:
                cursor.execute(
                    "INSERT INTO filter_amenities (user_id, amenity_id) VALUES (%s, %s)",
                    (u_id, amenity_id),
                )
    
    trigger_search_for_user_destinations(user_id=u_id, page_count=PAGE_COUNT_AFTER_FILTER_SET)

    
    return FilterResponse(
        user_id=filter_row["user_id"],
        min_price=filter_row["min_price"],
        max_price=filter_row["max_price"],
        min_bedrooms=filter_row["min_bedrooms"],
        min_beds=filter_row["min_beds"],
        min_bathrooms=filter_row["min_bathrooms"],
        property_type=filter_row["property_type"],
        updated_at=filter_row["updated_at"],
        amenities=filter_data.amenities,
    )
