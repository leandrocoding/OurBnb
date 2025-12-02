from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models.db import Group, Destination, User, Bnb, BnbQueue, BnbImage
from models.schemas import (
    GroupCreate, GroupResponse, UserCreate, UserResponse, 
    DestinationResponse
)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("", response_model=GroupResponse)
async def create_group(group_data: GroupCreate, db: AsyncSession = Depends(get_db)):
    """Create a new group with destinations."""
    
    # Validate dates
    if group_data.date_range_start >= group_data.date_range_end:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    if not group_data.destinations:
        raise HTTPException(status_code=400, detail="At least one destination is required")
    
    # Create the group
    group = Group(
        name=group_data.name,
        adults=group_data.adults,
        teens=group_data.teens,
        children=group_data.children,
        pets=group_data.pets,
        date_range_start=group_data.date_range_start,
        date_range_end=group_data.date_range_end,
    )
    db.add(group)
    await db.flush()  # Get the group ID
    
    # Create destinations
    for dest_data in group_data.destinations:
        destination = Destination(
            group_id=group.id,
            location_name=dest_data.location_name
        )
        db.add(destination)
    
    await db.commit()
    
    # Reload with destinations
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.destinations))
        .where(Group.id == group.id)
    )
    group = result.scalar_one()
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        adults=group.adults,
        teens=group.teens,
        children=group.children,
        pets=group.pets,
        date_range_start=group.date_range_start,
        date_range_end=group.date_range_end,
        created_at=group.created_at,
        destinations=[
            DestinationResponse(
                id=d.id,
                group_id=d.group_id,
                location_name=d.location_name
            ) for d in group.destinations
        ]
    )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int, db: AsyncSession = Depends(get_db)):
    """Get a group by ID."""
    result = await db.execute(
        select(Group)
        .options(selectinload(Group.destinations))
        .where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        adults=group.adults,
        teens=group.teens,
        children=group.children,
        pets=group.pets,
        date_range_start=group.date_range_start,
        date_range_end=group.date_range_end,
        created_at=group.created_at,
        destinations=[
            DestinationResponse(
                id=d.id,
                group_id=d.group_id,
                location_name=d.location_name
            ) for d in group.destinations
        ]
    )


@router.post("/{group_id}/join", response_model=UserResponse)
async def join_group(group_id: int, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Join a group by creating a new user."""
    
    # Check if group exists
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Create user
    user = User(
        group_id=group_id,
        nickname=user_data.nickname,
        avatar=user_data.avatar or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_data.nickname}"
    )
    db.add(user)
    await db.flush()
    
    # Add all existing BNBs to user's queue
    bnb_result = await db.execute(
        select(Bnb.airbnb_id).where(Bnb.group_id == group_id)
    )
    bnb_ids = bnb_result.scalars().all()
    
    for airbnb_id in bnb_ids:
        queue_entry = BnbQueue(user_id=user.id, airbnb_id=airbnb_id)
        db.add(queue_entry)
    
    await db.commit()
    
    return UserResponse(
        id=user.id,
        group_id=user.group_id,
        nickname=user.nickname,
        joined_at=user.joined_at,
        avatar=user.avatar
    )


@router.get("/{group_id}/members", response_model=List[UserResponse])
async def get_members(group_id: int, db: AsyncSession = Depends(get_db)):
    """Get all members of a group."""
    
    # Check if group exists
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get all users in group
    result = await db.execute(
        select(User).where(User.group_id == group_id).order_by(User.joined_at)
    )
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=u.id,
            group_id=u.group_id,
            nickname=u.nickname,
            joined_at=u.joined_at,
            avatar=u.avatar
        ) for u in users
    ]


