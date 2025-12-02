from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.db import Vote, User, Bnb, BnbQueue
from models.schemas import VoteCreate, VoteResponse

router = APIRouter(prefix="/votes", tags=["Votes"])


@router.post("", response_model=VoteResponse)
async def create_vote(vote_data: VoteCreate, db: AsyncSession = Depends(get_db)):
    """Submit a vote for a listing."""
    
    # Validate user exists
    result = await db.execute(select(User).where(User.id == vote_data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate BNB exists and belongs to user's group
    result = await db.execute(
        select(Bnb).where(
            Bnb.airbnb_id == vote_data.airbnb_id,
            Bnb.group_id == user.group_id
        )
    )
    bnb = result.scalar_one_or_none()
    if not bnb:
        raise HTTPException(status_code=404, detail="Listing not found in this group")
    
    # Check if user already voted on this listing
    result = await db.execute(
        select(Vote).where(
            Vote.user_id == vote_data.user_id,
            Vote.airbnb_id == vote_data.airbnb_id
        )
    )
    existing_vote = result.scalar_one_or_none()
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote = vote_data.vote
        existing_vote.reason = vote_data.reason
        vote = existing_vote
    else:
        # Create new vote
        vote = Vote(
            user_id=vote_data.user_id,
            airbnb_id=vote_data.airbnb_id,
            vote=vote_data.vote,
            reason=vote_data.reason
        )
        db.add(vote)
    
    # Remove from queue after voting
    result = await db.execute(
        select(BnbQueue).where(
            BnbQueue.user_id == vote_data.user_id,
            BnbQueue.airbnb_id == vote_data.airbnb_id
        )
    )
    queue_entry = result.scalar_one_or_none()
    if queue_entry:
        await db.delete(queue_entry)
    
    await db.commit()
    
    return VoteResponse(
        user_id=vote.user_id,
        airbnb_id=vote.airbnb_id,
        vote=vote.vote,
        created_at=vote.created_at,
        reason=vote.reason
    )


