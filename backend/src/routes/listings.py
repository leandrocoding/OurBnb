from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from database import get_db
from models.db import Group, Bnb, BnbImage, BnbAmenity, BnbQueue, Vote, User
from models.schemas import BnbResponse, LeaderboardResponse, LeaderboardEntry

router = APIRouter(tags=["Listings"])


@router.get("/groups/{group_id}/listings/next", response_model=Optional[BnbResponse])
async def get_next_listing(
    group_id: int, 
    user_id: int = Query(..., description="The user ID to get next listing for"),
    db: AsyncSession = Depends(get_db)
):
    """Get the next listing from the user's queue that they haven't voted on yet."""
    
    # Verify user exists and belongs to group
    result = await db.execute(
        select(User).where(User.id == user_id, User.group_id == group_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this group")
    
    # Get next BNB from queue that user hasn't voted on
    # Join queue with bnbs, exclude already voted
    subquery = select(Vote.airbnb_id).where(Vote.user_id == user_id)
    
    result = await db.execute(
        select(Bnb)
        .join(BnbQueue, BnbQueue.airbnb_id == Bnb.airbnb_id)
        .where(
            BnbQueue.user_id == user_id,
            Bnb.group_id == group_id,
            ~Bnb.airbnb_id.in_(subquery)
        )
        .order_by(BnbQueue.queued_at)
        .limit(1)
    )
    bnb = result.scalar_one_or_none()
    
    if not bnb:
        return None
    
    # Get images and amenities
    images_result = await db.execute(
        select(BnbImage.image_url).where(BnbImage.airbnb_id == bnb.airbnb_id)
    )
    images = images_result.scalars().all()
    
    amenities_result = await db.execute(
        select(BnbAmenity.amenity_id).where(BnbAmenity.airbnb_id == bnb.airbnb_id)
    )
    amenities = amenities_result.scalars().all()
    
    return BnbResponse(
        airbnb_id=bnb.airbnb_id,
        group_id=bnb.group_id,
        destination_id=bnb.destination_id,
        title=bnb.title,
        price_per_night=bnb.price_per_night,
        bnb_rating=bnb.bnb_rating,
        bnb_review_count=bnb.bnb_review_count,
        main_image_url=bnb.main_image_url,
        description=bnb.description,
        min_bedrooms=bnb.min_bedrooms,
        min_beds=bnb.min_beds,
        min_bathrooms=bnb.min_bathrooms,
        property_type=bnb.property_type,
        images=list(images),
        amenities=list(amenities)
    )


@router.get("/groups/{group_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(group_id: int, db: AsyncSession = Depends(get_db)):
    """Get the leaderboard of listings ranked by group votes."""
    
    # Check if group exists
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get all BNBs with vote aggregation
    # Vote values: 0=veto, 1=skip, 2=ok, 3=love
    # Scoring: love=+3, ok=+1, skip=0, veto=-5
    
    result = await db.execute(
        select(
            Bnb,
            func.count(Vote.user_id).label('total_votes'),
            func.sum(case((Vote.vote == 3, 1), else_=0)).label('love_count'),
            func.sum(case((Vote.vote == 2, 1), else_=0)).label('ok_count'),
            func.sum(case((Vote.vote == 1, 1), else_=0)).label('skip_count'),
            func.sum(case((Vote.vote == 0, 1), else_=0)).label('veto_count'),
            func.sum(
                case(
                    (Vote.vote == 3, 3),  # love
                    (Vote.vote == 2, 1),  # ok
                    (Vote.vote == 1, 0),  # skip
                    (Vote.vote == 0, -5), # veto
                    else_=0
                )
            ).label('score')
        )
        .outerjoin(Vote, Vote.airbnb_id == Bnb.airbnb_id)
        .where(Bnb.group_id == group_id)
        .group_by(Bnb.airbnb_id)
        .order_by(func.sum(
            case(
                (Vote.vote == 3, 3),
                (Vote.vote == 2, 1),
                (Vote.vote == 1, 0),
                (Vote.vote == 0, -5),
                else_=0
            )
        ).desc().nullslast())
    )
    
    rows = result.all()
    
    entries = []
    for i, row in enumerate(rows):
        bnb = row[0]
        
        # Get images for this BNB
        images_result = await db.execute(
            select(BnbImage.image_url).where(BnbImage.airbnb_id == bnb.airbnb_id)
        )
        images = images_result.scalars().all()
        
        entries.append(LeaderboardEntry(
            airbnb_id=bnb.airbnb_id,
            title=bnb.title,
            price_per_night=bnb.price_per_night,
            bnb_rating=bnb.bnb_rating,
            main_image_url=bnb.main_image_url,
            images=list(images),
            total_votes=row.total_votes or 0,
            love_count=row.love_count or 0,
            ok_count=row.ok_count or 0,
            veto_count=row.veto_count or 0,
            score=row.score or 0,
            rank=i + 1
        ))
    
    return LeaderboardResponse(
        group_id=group_id,
        entries=entries,
        total_listings=len(entries)
    )


@router.get("/groups/{group_id}/listings", response_model=List[BnbResponse])
async def get_all_listings(group_id: int, db: AsyncSession = Depends(get_db)):
    """Get all listings for a group."""
    
    result = await db.execute(
        select(Group).where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    result = await db.execute(
        select(Bnb).where(Bnb.group_id == group_id)
    )
    bnbs = result.scalars().all()
    
    responses = []
    for bnb in bnbs:
        # Get images
        images_result = await db.execute(
            select(BnbImage.image_url).where(BnbImage.airbnb_id == bnb.airbnb_id)
        )
        images = images_result.scalars().all()
        
        # Get amenities
        amenities_result = await db.execute(
            select(BnbAmenity.amenity_id).where(BnbAmenity.airbnb_id == bnb.airbnb_id)
        )
        amenities = amenities_result.scalars().all()
        
        responses.append(BnbResponse(
            airbnb_id=bnb.airbnb_id,
            group_id=bnb.group_id,
            destination_id=bnb.destination_id,
            title=bnb.title,
            price_per_night=bnb.price_per_night,
            bnb_rating=bnb.bnb_rating,
            bnb_review_count=bnb.bnb_review_count,
            main_image_url=bnb.main_image_url,
            description=bnb.description,
            min_bedrooms=bnb.min_bedrooms,
            min_beds=bnb.min_beds,
            min_bathrooms=bnb.min_bathrooms,
            property_type=bnb.property_type,
            images=list(images),
            amenities=list(amenities)
        ))
    
    return responses


