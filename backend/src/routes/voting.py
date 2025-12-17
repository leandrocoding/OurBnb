"""
Voting routes: submit votes and get next listing recommendations.
"""

import asyncio

from fastapi import APIRouter, HTTPException

from models.schemas import (
    VoteRequest,
    VoteWithNextResponse,
    NextToVoteResponse,
    GroupVote,
)
from db import get_cursor
from scoring import get_recommendation_scores
from .helpers import build_booking_link

router = APIRouter(tags=["Voting"])

# Import notify function from leaderboard module (to avoid circular imports, we'll use a callback)
_notify_leaderboard_callback = None


def set_notify_leaderboard_callback(callback):
    """Set the callback function for notifying leaderboard updates."""
    global _notify_leaderboard_callback
    _notify_leaderboard_callback = callback


@router.post("/vote", response_model=VoteWithNextResponse)
async def submit_vote(request: VoteRequest):
    """
    Submit a vote for a bnb and get the next listing to vote on.
    
    This endpoint:
    1. Records the vote
    2. Uses the scorer to get the next recommended listing
    3. Returns the vote confirmation along with the next listing
    
    This allows single round-trip voting with instant next-card display.
    """
    group_id = None
    next_listing = None
    
    with get_cursor() as cursor:
        # Verify user exists
        cursor.execute("SELECT id, group_id FROM users WHERE id = %s", (request.user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        group_id = user["group_id"]
        
        # Verify bnb exists in this group
        cursor.execute(
            "SELECT airbnb_id FROM bnbs WHERE airbnb_id = %s AND group_id = %s",
            (request.airbnb_id, group_id),
        )
        bnb = cursor.fetchone()
        if not bnb:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Upsert vote (composite primary key: user_id, airbnb_id, group_id)
        cursor.execute(
            """
            INSERT INTO votes (user_id, airbnb_id, group_id, vote, reason)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, airbnb_id, group_id) DO UPDATE SET
                vote = EXCLUDED.vote,
                reason = EXCLUDED.reason,
                created_at = now()
            RETURNING user_id, airbnb_id, vote, reason
            """,
            (request.user_id, request.airbnb_id, group_id, request.vote, request.reason),
        )
        vote_row = cursor.fetchone()
        
        # Get the next listing using the scorer
        next_listing = _get_next_listing_for_user(cursor, request.user_id, group_id)
    
    # Notify WebSocket clients of the leaderboard update
    if group_id and _notify_leaderboard_callback:
        asyncio.create_task(_notify_leaderboard_callback(group_id))
    
    return VoteWithNextResponse(
        user_id=vote_row["user_id"],
        airbnb_id=vote_row["airbnb_id"],
        vote=vote_row["vote"],
        reason=vote_row["reason"],
        next_listing=next_listing,
    )


def _get_next_listing_for_user(cursor, user_id: int, group_id: int, exclude_airbnb_ids: list[str] = None) -> NextToVoteResponse:
    """
    Get the next listing for a user using the scorer.
    Returns a fully populated NextToVoteResponse or an empty one if no listings.
    
    Args:
        cursor: Database cursor
        user_id: The user to get the next listing for
        group_id: The group the user belongs to
        exclude_airbnb_ids: Optional list of airbnb_ids to skip (e.g., currently displayed + prefetched cards)
    """
    # Get total listings count
    cursor.execute(
        "SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s",
        (group_id,),
    )
    total_listings = cursor.fetchone()["count"]
    
    # Get group info for booking link generation
    cursor.execute(
        """SELECT adults, children, infants, pets, date_range_start, date_range_end 
           FROM groups WHERE id = %s""",
        (group_id,),
    )
    group = cursor.fetchone()
    
    # Convert to set 
    exclude_set = set(exclude_airbnb_ids) if exclude_airbnb_ids else set()
    
    # Get personalized recommendations for this user
    # Fetch len(exclude_set) + 1 to ensure we have at least one non-excluded result
    limit = len(exclude_set) + 1 if exclude_set else 1
    scored_bnbs = get_recommendation_scores(group_id, user_id, limit=limit)
    
    # Filter out excluded listings (already shown in frontend)
    if exclude_set:
        scored_bnbs = [bnb for bnb in scored_bnbs if bnb.airbnb_id not in exclude_set]
    
    # Count total remaining
    cursor.execute(
        """
        SELECT COUNT(*) as count FROM bnbs b
        WHERE b.group_id = %s
          AND NOT EXISTS (
              SELECT 1 FROM votes v WHERE v.airbnb_id = b.airbnb_id AND v.group_id = b.group_id AND v.user_id = %s
          )
        """,
        (group_id, user_id),
    )
    total_remaining = cursor.fetchone()["count"]
    
    if not scored_bnbs:
        return NextToVoteResponse(has_listing=False, total_remaining=total_remaining, total_listings=total_listings)
    
    bnb = scored_bnbs[0]
    airbnb_id = bnb.airbnb_id
    
    # Get images
    cursor.execute(
        "SELECT image_url FROM bnb_images WHERE airbnb_id = %s AND group_id = %s",
        (airbnb_id, group_id),
    )
    extra_images = cursor.fetchall()
    
    images = []
    if bnb.main_image_url:
        images.append(bnb.main_image_url)
    images.extend([img["image_url"] for img in extra_images])
    if not images:
        images = ["https://placehold.co/400x300?text=No+Image"]
    
    # Get amenities
    cursor.execute(
        "SELECT amenity_id FROM bnb_amenities WHERE airbnb_id = %s AND group_id = %s",
        (airbnb_id, group_id),
    )
    amenities = [a["amenity_id"] for a in cursor.fetchall()]
    
    # Get other users' votes on this listing
    cursor.execute(
        """
        SELECT v.user_id, u.nickname as user_name, v.airbnb_id, v.vote, v.reason
        FROM votes v
        JOIN users u ON u.id = v.user_id
        WHERE v.airbnb_id = %s AND v.group_id = %s AND v.user_id != %s
        """,
        (airbnb_id, group_id, user_id),
    )
    other_votes = [
        GroupVote(
            user_id=v["user_id"],
            user_name=v["user_name"],
            airbnb_id=v["airbnb_id"],
            vote=v["vote"],
            reason=v["reason"],
        )
        for v in cursor.fetchall()
    ]
    
    # Build booking link
    booking_link = build_booking_link(airbnb_id, group)
    
    # Get location name (extract first part before comma for display)
    location = bnb.location_name.split(',')[0] if bnb.location_name else None
    
    return NextToVoteResponse(
        airbnb_id=airbnb_id,
        title=bnb.title,
        price=bnb.price_per_night,
        rating=bnb.bnb_rating,
        review_count=bnb.bnb_review_count,
        location=location,
        images=images,
        bedrooms=bnb.min_bedrooms,
        beds=bnb.min_beds,
        bathrooms=bnb.min_bathrooms,
        property_type=bnb.property_type,
        amenities=amenities,
        other_votes=other_votes,
        booking_link=booking_link,
        has_listing=True,
        total_remaining=total_remaining,
        total_listings=total_listings,
    )
