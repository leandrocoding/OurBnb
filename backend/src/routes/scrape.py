"""
Routes for triggering scraping operations.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.db import Group, Destination, Bnb, BnbImage, BnbQueue, User
from scraper_service import fetch_listings_for_group

router = APIRouter(prefix="/scrape", tags=["Scraping"])


async def _scrape_and_store_listings(
    group_id: int,
    destination_id: int,
    location: str,
    guests: int,
    checkin,
    checkout,
    db: AsyncSession
):
    """Background task to scrape and store listings."""
    listings = fetch_listings_for_group(
        location=location,
        guests=guests,
        checkin=checkin,
        checkout=checkout,
        max_pages=2
    )
    
    # Get all users in the group for queue population
    result = await db.execute(
        select(User.id).where(User.group_id == group_id)
    )
    user_ids = result.scalars().all()
    
    for listing_data in listings:
        airbnb_id = listing_data['airbnb_id']
        
        # Check if listing already exists
        result = await db.execute(
            select(Bnb).where(Bnb.airbnb_id == airbnb_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            continue
        
        # Create BNB
        bnb = Bnb(
            airbnb_id=airbnb_id,
            group_id=group_id,
            destination_id=destination_id,
            title=listing_data['title'],
            price_per_night=listing_data['price_per_night'],
            bnb_rating=listing_data['bnb_rating'],
            bnb_review_count=listing_data['bnb_review_count'],
            main_image_url=listing_data['main_image_url'],
        )
        db.add(bnb)
        
        # Add images
        for image_url in listing_data.get('images', []):
            if image_url:
                img = BnbImage(airbnb_id=airbnb_id, image_url=image_url)
                db.add(img)
        
        # Add to all users' queues
        for user_id in user_ids:
            queue_entry = BnbQueue(user_id=user_id, airbnb_id=airbnb_id)
            db.add(queue_entry)
    
    await db.commit()


@router.post("/groups/{group_id}/destinations/{destination_id}")
async def trigger_scrape(
    group_id: int,
    destination_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger scraping for a specific destination in a group."""
    
    # Verify group exists
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Verify destination exists and belongs to group
    result = await db.execute(
        select(Destination).where(
            Destination.id == destination_id,
            Destination.group_id == group_id
        )
    )
    destination = result.scalar_one_or_none()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found in this group")
    
    # Calculate guests (adults + teens count as full guests)
    guests = group.adults + group.teens
    if guests < 1:
        guests = 1
    
    # Scrape synchronously for now (can be made async with celery later)
    listings = fetch_listings_for_group(
        location=destination.location_name,
        guests=guests,
        checkin=group.date_range_start,
        checkout=group.date_range_end,
        max_pages=2
    )
    
    # Get all users in the group for queue population
    result = await db.execute(
        select(User.id).where(User.group_id == group_id)
    )
    user_ids = result.scalars().all()
    
    added_count = 0
    for listing_data in listings:
        airbnb_id = listing_data['airbnb_id']
        
        # Check if listing already exists
        result = await db.execute(
            select(Bnb).where(Bnb.airbnb_id == airbnb_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            continue
        
        # Create BNB
        bnb = Bnb(
            airbnb_id=airbnb_id,
            group_id=group_id,
            destination_id=destination_id,
            title=listing_data['title'],
            price_per_night=listing_data['price_per_night'],
            bnb_rating=listing_data['bnb_rating'],
            bnb_review_count=listing_data['bnb_review_count'],
            main_image_url=listing_data['main_image_url'],
        )
        db.add(bnb)
        await db.flush()
        
        # Add images
        for image_url in listing_data.get('images', []):
            if image_url:
                img = BnbImage(airbnb_id=airbnb_id, image_url=image_url)
                db.add(img)
        
        # Add to all users' queues
        for user_id in user_ids:
            queue_entry = BnbQueue(user_id=user_id, airbnb_id=airbnb_id)
            db.add(queue_entry)
        
        added_count += 1
    
    await db.commit()
    
    return {
        "status": "completed",
        "listings_found": len(listings),
        "listings_added": added_count,
        "destination": destination.location_name
    }


