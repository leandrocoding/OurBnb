from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db
from models.db import User, UserFilter, FilterAmenity
from models.schemas import UserFilterUpdate, UserFilterResponse

router = APIRouter(tags=["Filters"])


@router.get("/users/{user_id}/filters", response_model=UserFilterResponse)
async def get_user_filters(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user's filter preferences."""
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get filter
    result = await db.execute(
        select(UserFilter).where(UserFilter.user_id == user_id)
    )
    user_filter = result.scalar_one_or_none()
    
    if not user_filter:
        # Return empty filter
        return UserFilterResponse(
            user_id=user_id,
            amenities=[]
        )
    
    # Get amenities
    result = await db.execute(
        select(FilterAmenity.amenity_id).where(FilterAmenity.user_id == user_id)
    )
    amenities = result.scalars().all()
    
    return UserFilterResponse(
        user_id=user_filter.user_id,
        min_price=user_filter.min_price,
        max_price=user_filter.max_price,
        min_bedrooms=user_filter.min_bedrooms,
        min_beds=user_filter.min_beds,
        min_bathrooms=user_filter.min_bathrooms,
        property_type=user_filter.property_type,
        updated_at=user_filter.updated_at,
        amenities=list(amenities)
    )


@router.put("/users/{user_id}/filters", response_model=UserFilterResponse)
async def update_user_filters(
    user_id: int, 
    filter_data: UserFilterUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Update user's filter preferences."""
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create filter
    result = await db.execute(
        select(UserFilter).where(UserFilter.user_id == user_id)
    )
    user_filter = result.scalar_one_or_none()
    
    if user_filter:
        # Update existing
        user_filter.min_price = filter_data.min_price
        user_filter.max_price = filter_data.max_price
        user_filter.min_bedrooms = filter_data.min_bedrooms
        user_filter.min_beds = filter_data.min_beds
        user_filter.min_bathrooms = filter_data.min_bathrooms
        user_filter.property_type = filter_data.property_type
    else:
        # Create new
        user_filter = UserFilter(
            user_id=user_id,
            min_price=filter_data.min_price,
            max_price=filter_data.max_price,
            min_bedrooms=filter_data.min_bedrooms,
            min_beds=filter_data.min_beds,
            min_bathrooms=filter_data.min_bathrooms,
            property_type=filter_data.property_type
        )
        db.add(user_filter)
        await db.flush()
    
    # Update amenities - delete old ones first
    await db.execute(
        delete(FilterAmenity).where(FilterAmenity.user_id == user_id)
    )
    
    # Add new amenities
    for amenity_id in filter_data.amenities:
        amenity = FilterAmenity(user_id=user_id, amenity_id=amenity_id)
        db.add(amenity)
    
    await db.commit()
    
    return UserFilterResponse(
        user_id=user_filter.user_id,
        min_price=user_filter.min_price,
        max_price=user_filter.max_price,
        min_bedrooms=user_filter.min_bedrooms,
        min_beds=user_filter.min_beds,
        min_bathrooms=user_filter.min_bathrooms,
        property_type=user_filter.property_type,
        updated_at=user_filter.updated_at,
        amenities=filter_data.amenities
    )


