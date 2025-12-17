"""
Listing routes: get group listings and user recommendations.
"""

from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    PropertyInfo,
    GroupListingsResponse,
    RecommendationListing,
    RecommendationsResponse,
)
from db import get_cursor
from scoring import get_recommendation_scores
from .helpers import (
    get_images_and_amenities_for_bnbs,
    get_other_votes_for_bnbs,
    build_booking_link,
)

router = APIRouter(tags=["Listings"])


@router.get("/group/{group_id}/listings", response_model=GroupListingsResponse)
async def get_group_listings(group_id: int):
    """Get all bnb listings for a group."""
    with get_cursor() as cursor:
        # Verify group exists
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all bnbs for this group
        cursor.execute(
            """
            SELECT 
                airbnb_id,
                title,
                price_per_night,
                bnb_rating,
                bnb_review_count,
                main_image_url,
                min_bedrooms,
                min_beds,
                min_bathrooms,
                property_type
            FROM bnbs
            WHERE group_id = %s
            ORDER BY airbnb_id
            """,
            (group_id,),
        )
        bnbs = cursor.fetchall()
        
        if not bnbs:
            return GroupListingsResponse(listings=[])
        
        # Batch fetch images and amenities
        airbnb_ids = [bnb["airbnb_id"] for bnb in bnbs]
        images_by_bnb, amenities_by_bnb = get_images_and_amenities_for_bnbs(cursor, group_id, airbnb_ids)
        
        listings = []
        for bnb in bnbs:
            airbnb_id = bnb["airbnb_id"]
            
            # Build images list (main image first, then extras)
            images = []
            if bnb["main_image_url"]:
                images.append(bnb["main_image_url"])
            images.extend(images_by_bnb.get(airbnb_id, []))
            
            listings.append(PropertyInfo(
                id=airbnb_id,
                title=bnb["title"] or "Untitled Property",
                price=bnb["price_per_night"] or 0,
                rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
                review_count=bnb["bnb_review_count"],
                images=images if images else ["https://placehold.co/400x300?text=No+Image"],
                bedrooms=bnb["min_bedrooms"],
                beds=bnb["min_beds"],
                bathrooms=bnb["min_bathrooms"],
                property_type=bnb["property_type"],
                amenities=amenities_by_bnb.get(airbnb_id, []),
            ))
    
    return GroupListingsResponse(listings=listings)


@router.get("/user/{user_id}/recommendations", response_model=RecommendationsResponse, tags=["Voting"])
async def get_user_recommendations(
    user_id: int,
    limit: int = Query(default=10, le=50),
    exclude_ids: str = Query(default=None, description="Comma-separated list of airbnb_ids to exclude"),
):
    """
    Get a batch of recommended listings for the user to vote on.
    
    Returns listings scored and sorted by recommendation score, excluding
    any the user has already voted on.
    
    Args:
        user_id: The user requesting recommendations
        limit: Maximum number of recommendations to return (default 10, max 50)
        exclude_ids: Comma-separated airbnb_ids to also exclude (e.g., already shown in frontend)
    
    Returns:
        RecommendationsResponse with scored listings and metadata
    """
    with get_cursor() as cursor:
        # Verify user exists and get group_id
        cursor.execute("SELECT id, group_id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        group_id = user["group_id"]
        
        # Get group info for booking link generation
        cursor.execute(
            """SELECT adults, children, infants, pets, date_range_start, date_range_end 
               FROM groups WHERE id = %s""",
            (group_id,),
        )
        group = cursor.fetchone()
        
        # Get personalized recommendations for this user (excludes already voted)
        scored_bnbs = get_recommendation_scores(group_id, user_id)
        
        # Apply exclude_ids filter if provided (already shown in frontend buffer)
        if exclude_ids:
            exclude_set = set(exclude_ids.split(","))
            scored_bnbs = [bnb for bnb in scored_bnbs if bnb.airbnb_id not in exclude_set]
        
        # Calculate total remaining before limiting
        total_remaining = len(scored_bnbs)
        
        # Apply limit
        scored_bnbs = scored_bnbs[:limit]
        
        if not scored_bnbs:
            return RecommendationsResponse(
                recommendations=[],
                total_remaining=0,
                has_more=False,
            )
        
        # Batch fetch images, amenities, and other votes
        airbnb_ids = [bnb.airbnb_id for bnb in scored_bnbs]
        images_by_bnb, amenities_by_bnb = get_images_and_amenities_for_bnbs(cursor, group_id, airbnb_ids)
        votes_by_bnb = get_other_votes_for_bnbs(cursor, group_id, airbnb_ids, exclude_user_id=user_id)
        
        # Build response
        recommendations = []
        for bnb in scored_bnbs:
            airbnb_id = bnb.airbnb_id
            
            # Build images list
            images = []
            if bnb.main_image_url:
                images.append(bnb.main_image_url)
            images.extend(images_by_bnb.get(airbnb_id, []))
            if not images:
                images = ["https://placehold.co/400x300?text=No+Image"]
            
            # Get location name (extract first part before comma for display)
            location = bnb.location_name.split(',')[0] if bnb.location_name else None
            
            # Build Airbnb booking link
            booking_link = build_booking_link(airbnb_id, group)
            
            recommendations.append(RecommendationListing(
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
                amenities=amenities_by_bnb.get(airbnb_id, []),
                score=bnb.score,
                filter_matches=bnb.filter_matches,
                other_votes=votes_by_bnb.get(airbnb_id, []),
                booking_link=booking_link,
            ))
        
        return RecommendationsResponse(
            recommendations=recommendations,
            total_remaining=total_remaining,
            has_more=total_remaining > limit,
        )
