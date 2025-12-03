from datetime import datetime
from typing import List, Dict
import asyncio

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from constants import (
    PAGE_COUNT_AFTER_FILTER_SET,
    LEADERBOARD_LIMIT,
)
from models.schemas import (
    TestData,
    CreateGroupRequest,
    CreateGroupResponse,
    GroupInfoResponse,
    UserInfo,
    DestinationInfo,
    JoinGroupRequest,
    JoinGroupResponse,
    UserFilter,
    FilterResponse,
    TriggerSearchRequest,
    TriggerSearchResponse,
    PropertyInfo,
    GroupListingsResponse,
    VoteRequest,
    VoteResponse,
    GroupVote,
    GroupVotesResponse,
    LeaderboardEntry,
    LeaderboardVoteSummary,
    LeaderboardResponse,
    # User Management
    UserProfileResponse,
    UpdateUserRequest,
    UserVoteInfo,
    UserVotesResponse,
    # Group Management
    UpdateGroupRequest,
    AddDestinationRequest,
    UserVoteProgress,
    GroupStatsResponse,
    # Voting Queue
    NextToVoteResponse,
    QueuedListing,
    VotingQueueResponse,
    VoteProgressResponse,
    # Listing Detail
    ListingDetailResponse,
    ListingVotesResponse,
    # Search & Discovery
    GroupSearchRequest,
    GroupSearchResponse,
    SearchStatusDestination,
    SearchStatusResponse,
    DestinationSuggestion,
    DestinationAutocompleteResponse,
)
from db import get_cursor
from scrape_utils import trigger_search_for_user_destinations, trigger_search_job, trigger_listing_inquiry

router = APIRouter(prefix="/api")


# =============================================================================
# WEBSOCKET - Real-time Leaderboard Updates
# =============================================================================

class LeaderboardConnectionManager:
    """Manages WebSocket connections for real-time leaderboard updates."""
    
    def __init__(self):
        # Dict of group_id -> set of WebSocket connections
        self.active_connections: Dict[int, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, group_id: int):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, group_id: int):
        if group_id in self.active_connections:
            if websocket in self.active_connections[group_id]:
                self.active_connections[group_id].remove(websocket)
            if not self.active_connections[group_id]:
                del self.active_connections[group_id]
    
    async def broadcast_to_group(self, group_id: int, message: dict):
        """Broadcast a message to all connections in a group."""
        if group_id not in self.active_connections:
            return
        
        dead_connections = []
        for connection in self.active_connections[group_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn, group_id)


# Global connection manager
leaderboard_manager = LeaderboardConnectionManager()


async def get_leaderboard_data_for_ws(group_id: int) -> dict:
    """Get leaderboard data for a group (used by WebSocket)."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            return {"error": "Group not found"}
        
        # Get total user count
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE group_id = %s", (group_id,))
        total_users = cursor.fetchone()["count"]
        
        # Get total listings count
        cursor.execute("SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s", (group_id,))
        total_listings = cursor.fetchone()["count"]
        
        # Get leaderboard from view
        cursor.execute(
            """
            SELECT 
                airbnb_id, title, price_per_night, bnb_rating, bnb_review_count,
                min_bedrooms, min_beds, min_bathrooms, property_type, main_image_url,
                score, filter_matches, veto_count, ok_count, love_count, super_love_count
            FROM leaderboard_scores
            WHERE group_id = %s
            ORDER BY score DESC
            LIMIT %s
            """,
            (group_id, LEADERBOARD_LIMIT),
        )
        rows = cursor.fetchall()
        
        if not rows:
            return {
                "entries": [],
                "total_listings": total_listings,
                "total_users": total_users,
            }
        
        # Batch fetch images and amenities
        airbnb_ids = [r["airbnb_id"] for r in rows]
        
        images_by_bnb: dict[str, list[str]] = {aid: [] for aid in airbnb_ids}
        cursor.execute(
            "SELECT airbnb_id, image_url FROM bnb_images WHERE airbnb_id = ANY(%s)",
            (airbnb_ids,),
        )
        for img in cursor.fetchall():
            images_by_bnb[img["airbnb_id"]].append(img["image_url"])
        
        amenities_by_bnb: dict[str, list[int]] = {aid: [] for aid in airbnb_ids}
        cursor.execute(
            "SELECT airbnb_id, amenity_id FROM bnb_amenities WHERE airbnb_id = ANY(%s)",
            (airbnb_ids,),
        )
        for amenity in cursor.fetchall():
            amenities_by_bnb[amenity["airbnb_id"]].append(amenity["amenity_id"])
        
        # Build response
        entries = []
        for rank, row in enumerate(rows, start=1):
            airbnb_id = row["airbnb_id"]
            images = []
            if row["main_image_url"]:
                images.append(row["main_image_url"])
            images.extend(images_by_bnb.get(airbnb_id, []))
            if not images:
                images = ["https://placehold.co/400x300?text=No+Image"]
            
            entries.append({
                "rank": rank,
                "airbnb_id": airbnb_id,
                "title": row["title"] or "Untitled",
                "price": row["price_per_night"] or 0,
                "rating": float(row["bnb_rating"]) if row["bnb_rating"] else None,
                "review_count": row["bnb_review_count"],
                "images": images,
                "bedrooms": row["min_bedrooms"],
                "beds": row["min_beds"],
                "bathrooms": row["min_bathrooms"],
                "property_type": row["property_type"],
                "amenities": amenities_by_bnb.get(airbnb_id, []),
                "score": row["score"],
                "filter_matches": row["filter_matches"],
                "votes": {
                    "veto_count": row["veto_count"],
                    "ok_count": row["ok_count"],
                    "love_count": row["love_count"],
                    "super_love_count": row["super_love_count"],
                },
            })
        
        return {
            "entries": entries,
            "total_listings": total_listings,
            "total_users": total_users,
        }


async def notify_leaderboard_update(group_id: int):
    """
    Call this function after a vote is cast to notify all connected clients.
    """
    leaderboard_data = await get_leaderboard_data_for_ws(group_id)
    leaderboard_data["type"] = "update"
    await leaderboard_manager.broadcast_to_group(group_id, leaderboard_data)


# =============================================================================
# HTTP ENDPOINTS
# =============================================================================


@router.post("/group/create", response_model=CreateGroupResponse, tags=["Groups"])
async def create_group(request: CreateGroupRequest):
    """Create a new group and return the group ID."""
    with get_cursor() as cursor:
        # Insert the group
        cursor.execute(
            """
            INSERT INTO groups (name, adults, children, infants, pets, date_range_start, date_range_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                request.group_name,
                request.adults,
                request.children,
                request.infants,
                request.pets,
                request.date_start,
                request.date_end,
            ),
        )
        group_row = cursor.fetchone()
        group_id = group_row["id"]
        
        # Insert destinations
        for destination in request.destinations:
            cursor.execute(
                """
                INSERT INTO destinations (group_id, location_name)
                VALUES (%s, %s)
                """,
                (group_id, destination),
            )
    
    return CreateGroupResponse(group_id=group_id)


@router.get("/group/info/{group_id}", response_model=GroupInfoResponse, tags=["Groups"])
async def get_group_info(group_id: int):
    """Get group information by group ID."""
    with get_cursor() as cursor:
        # Get group info
        cursor.execute(
            """SELECT id, name, date_range_start, date_range_end, adults, children, infants, pets 
               FROM groups WHERE id = %s""",
            (group_id,),
        )
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get destinations
        cursor.execute(
            "SELECT id, location_name FROM destinations WHERE group_id = %s",
            (group["id"],),
        )
        destinations = cursor.fetchall()
        
        destination_list = [
            DestinationInfo(id=dest["id"], name=dest["location_name"])
            for dest in destinations
        ]
        
        # Get users in the group
        cursor.execute(
            "SELECT id, nickname, avatar FROM users WHERE group_id = %s",
            (group["id"],),
        )
        users = cursor.fetchall()
        
        user_list = [
            UserInfo(id=user["id"], nickname=user["nickname"], avatar=user["avatar"])
            for user in users
        ]
    
    return GroupInfoResponse(
        group_id=group["id"],
        group_name=group["name"],
        destinations=destination_list,
        date_start=group["date_range_start"],
        date_end=group["date_range_end"],
        adults=group["adults"],
        children=group["children"],
        infants=group["infants"],
        pets=group["pets"],
        users=user_list,
    )


@router.post("/group/join", response_model=JoinGroupResponse, tags=["Groups"])
async def join_group(request: JoinGroupRequest):
    """Join a group and return the user ID."""
    with get_cursor() as cursor:
        # Check group exists
        cursor.execute(
            "SELECT id FROM groups WHERE id = %s",
            (request.group_id,),
        )
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Check if nickname already taken
        cursor.execute(
            "SELECT id FROM users WHERE nickname = %s",
            (request.username,),
        )
        existing_user = cursor.fetchone()
        if existing_user:
            raise HTTPException(status_code=400, detail="Nickname already taken")
        
        # Create user
        cursor.execute(
            """
            INSERT INTO users (group_id, nickname, avatar)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (request.group_id, request.username, request.avatar),
        )
        user_row = cursor.fetchone()
        user_id = user_row["id"]
    
    return JoinGroupResponse(user_id=user_id)


@router.get("/filter/{u_id}", response_model=FilterResponse, tags=["Filters"])
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
        
        # Return default filter if none exists
        # TODO adjust max_price based on what airbnb has as max. Currently using 1000 (per night)
        return FilterResponse(user_id=u_id, max_price=1000)


@router.patch("/filter/{u_id}", response_model=FilterResponse, tags=["Filters"])
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


# @router.post("/search/trigger", response_model=TriggerSearchResponse)
# async def trigger_search(request: TriggerSearchRequest):
#     """Trigger a search job for the scraper worker."""
#     with get_cursor() as cursor:
#         # Verify user exists
#         cursor.execute("SELECT id FROM users WHERE id = %s", (request.user_id,))
#         user = cursor.fetchone()
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         # Verify destination exists
#         cursor.execute("SELECT id FROM destinations WHERE id = %s", (request.destination_id,))
#         destination = cursor.fetchone()
#         if not destination:
#             raise HTTPException(status_code=404, detail="Destination not found")
    
#     # Trigger the search job
#     job_id = trigger_search_job(
#         user_id=request.user_id,
#         destination_id=request.destination_id,
#         page_start=request.page_start,
#         page_end=request.page_end,
#     )
    
#     return TriggerSearchResponse(
#         job_id=job_id,
#         message=f"Search job triggered for user {request.user_id} and destination {request.destination_id}"
#     )



@router.get("/group/{group_id}/listings", response_model=GroupListingsResponse, tags=["Listings"])
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
        
        listings = []
        for bnb in bnbs:
            # Get additional images for this bnb
            cursor.execute(
                "SELECT image_url FROM bnb_images WHERE airbnb_id = %s",
                (bnb["airbnb_id"],),
            )
            extra_images = cursor.fetchall()
            
            # Get amenities for this bnb
            cursor.execute(
                "SELECT amenity_id FROM bnb_amenities WHERE airbnb_id = %s",
                (bnb["airbnb_id"],),
            )
            amenities = cursor.fetchall()
            
            # Build images list (main image first, then extras)
            images = []
            if bnb["main_image_url"]:
                images.append(bnb["main_image_url"])
            images.extend([img["image_url"] for img in extra_images])
            
            listings.append(PropertyInfo(
                id=bnb["airbnb_id"],
                title=bnb["title"] or "Untitled Property",
                price=bnb["price_per_night"] or 0,
                rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
                review_count=bnb["bnb_review_count"],
                images=images if images else ["https://placehold.co/400x300?text=No+Image"],
                bedrooms=bnb["min_bedrooms"],
                beds=bnb["min_beds"],
                bathrooms=bnb["min_bathrooms"],
                property_type=bnb["property_type"],
                amenities=[a["amenity_id"] for a in amenities],
            ))
    
    return GroupListingsResponse(listings=listings)


@router.post("/vote", response_model=VoteResponse, tags=["Voting"])
async def submit_vote(request: VoteRequest):
    """Submit a vote for a bnb."""
    group_id = None
    with get_cursor() as cursor:
        # Verify user exists
        cursor.execute("SELECT id, group_id FROM users WHERE id = %s", (request.user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        group_id = user["group_id"]
        
        # Verify bnb exists
        cursor.execute("SELECT airbnb_id FROM bnbs WHERE airbnb_id = %s", (request.airbnb_id,))
        bnb = cursor.fetchone()
        if not bnb:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Upsert vote (composite primary key: user_id, airbnb_id)
        cursor.execute(
            """
            INSERT INTO votes (user_id, airbnb_id, vote, reason)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, airbnb_id) DO UPDATE SET
                vote = EXCLUDED.vote,
                reason = EXCLUDED.reason,
                created_at = now()
            RETURNING user_id, airbnb_id, vote, reason
            """,
            (request.user_id, request.airbnb_id, request.vote, request.reason),
        )
        vote_row = cursor.fetchone()
    
    # Notify WebSocket clients of the leaderboard update
    if group_id:
        asyncio.create_task(notify_leaderboard_update(group_id))
    
    return VoteResponse(
        user_id=vote_row["user_id"],
        airbnb_id=vote_row["airbnb_id"],
        vote=vote_row["vote"],
        reason=vote_row["reason"],
    )

# TODO Remove this should not be needed as we should have all the info in the leaderboard page. 
@router.get("/group/{group_id}/votes", response_model=GroupVotesResponse, tags=["Voting"])
async def get_group_votes(group_id: int):
    """Get all votes for bnbs in a group."""
    with get_cursor() as cursor:
        # Verify group exists
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all votes from users in this group for bnbs in this group
        cursor.execute(
            """
            SELECT v.user_id, u.nickname as user_name, v.airbnb_id, v.vote, v.reason
            FROM votes v
            INNER JOIN users u ON u.id = v.user_id
            INNER JOIN bnbs b ON b.airbnb_id = v.airbnb_id AND b.group_id = u.group_id
            WHERE u.group_id = %s
            ORDER BY v.created_at DESC
            """,
            (group_id,),
        )
        votes = cursor.fetchall()
    
    return GroupVotesResponse(
        votes=[
            GroupVote(
                user_id=v["user_id"],
                user_name=v["user_name"],
                airbnb_id=v["airbnb_id"],
                vote=v["vote"],
                reason=v["reason"],
            )
            for v in votes
        ]
    )


@router.get("/group/{group_id}/leaderboard", response_model=LeaderboardResponse, tags=["Leaderboard"])
async def get_group_leaderboard(group_id: int):
    """
    Get the leaderboard for a group with dynamically calculated scores.
    
    Scores are calculated by a PostgreSQL view based on:
    - How many users' filters the listing matches
    - Votes received (veto, ok, love, super love)
    
    Scoring values are configurable in the 'scoring_config' table.
    Returns the top listings ordered by score descending.
    """
    with get_cursor() as cursor:
        # Get group info for booking link generation
        cursor.execute(
            """SELECT id, adults, children, infants, pets, date_range_start, date_range_end 
               FROM groups WHERE id = %s""",
            (group_id,),
        )
        group = cursor.fetchone()
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get user count
        cursor.execute(
            "SELECT COUNT(*) as count FROM users WHERE group_id = %s",
            (group_id,),
        )
        user_count = cursor.fetchone()
        total_users = user_count["count"]
        
        # Get total listings count
        cursor.execute(
            "SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s",
            (group_id,),
        )
        total_listings = cursor.fetchone()["count"]
        
        if total_listings == 0:
            return LeaderboardResponse(entries=[], total_listings=0, total_users=total_users)
        
        # Query the leaderboard view - scores calculated by PostgreSQL
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
                property_type,
                filter_matches,
                veto_count,
                ok_count,
                love_count,
                super_love_count,
                score
            FROM leaderboard_scores
            WHERE group_id = %s
            ORDER BY score DESC
            LIMIT %s
            """,
            (group_id, LEADERBOARD_LIMIT),
        )
        scored_bnbs = cursor.fetchall()
        
        # Get airbnb_ids for batch queries
        airbnb_ids = [bnb["airbnb_id"] for bnb in scored_bnbs]
        
        # Batch fetch images
        images_by_bnb: dict[str, list[str]] = {aid: [] for aid in airbnb_ids}
        if airbnb_ids:
            cursor.execute(
                "SELECT airbnb_id, image_url FROM bnb_images WHERE airbnb_id = ANY(%s)",
                (airbnb_ids,),
            )
            for img in cursor.fetchall():
                images_by_bnb[img["airbnb_id"]].append(img["image_url"])
        
        # Batch fetch amenities
        amenities_by_bnb: dict[str, list[int]] = {aid: [] for aid in airbnb_ids}
        if airbnb_ids:
            cursor.execute(
                "SELECT airbnb_id, amenity_id FROM bnb_amenities WHERE airbnb_id = ANY(%s)",
                (airbnb_ids,),
            )
            for amenity in cursor.fetchall():
                amenities_by_bnb[amenity["airbnb_id"]].append(amenity["amenity_id"])
        
        # Build booking link parameters from group data
        check_in = group["date_range_start"].strftime("%Y-%m-%d")
        check_out = group["date_range_end"].strftime("%Y-%m-%d")
        adults = group["adults"]
        children = group["children"]
        infants = group["infants"]
        pets = group["pets"]
        
        # Build response
        entries = []
        for rank, bnb in enumerate(scored_bnbs, start=1):
            airbnb_id = bnb["airbnb_id"]
            
            # Build images list (main image first)
            images = []
            if bnb["main_image_url"]:
                images.append(bnb["main_image_url"])
            images.extend(images_by_bnb.get(airbnb_id, []))
            if not images:
                images = ["https://placehold.co/400x300?text=No+Image"]
            
            # Build Airbnb booking link
            booking_link = f"https://www.airbnb.ch/rooms/{airbnb_id}?adults={adults}&check_in={check_in}&check_out={check_out}"
            if children > 0:
                booking_link += f"&children={children}"
            if infants > 0:
                booking_link += f"&infants={infants}"
            if pets > 0:
                booking_link += f"&pets={pets}"
            
            entries.append(LeaderboardEntry(
                rank=rank,
                airbnb_id=airbnb_id,
                title=bnb["title"] or "Untitled Property",
                price=bnb["price_per_night"] or 0,
                rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
                review_count=bnb["bnb_review_count"],
                images=images,
                bedrooms=bnb["min_bedrooms"],
                beds=bnb["min_beds"],
                bathrooms=bnb["min_bathrooms"],
                property_type=bnb["property_type"],
                amenities=amenities_by_bnb.get(airbnb_id, []),
                score=bnb["score"],
                filter_matches=bnb["filter_matches"],
                votes=LeaderboardVoteSummary(
                    veto_count=bnb["veto_count"],
                    ok_count=bnb["ok_count"],
                    love_count=bnb["love_count"],
                    super_love_count=bnb["super_love_count"],
                ),
                booking_link=booking_link,
            ))
    
    return LeaderboardResponse(
        entries=entries,
        total_listings=total_listings,
        total_users=total_users,
    )


# =============================================================================
# USER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/user/{user_id}", response_model=UserProfileResponse, tags=["Users"])
async def get_user_profile(user_id: int):
    """Get user profile with group info."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.nickname, u.avatar, u.group_id, u.joined_at, g.name as group_name
            FROM users u
            JOIN groups g ON g.id = u.group_id
            WHERE u.id = %s
            """,
            (user_id,),
        )
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfileResponse(
        id=user["id"],
        nickname=user["nickname"],
        avatar=user["avatar"],
        group_id=user["group_id"],
        group_name=user["group_name"],
        joined_at=user["joined_at"],
    )


@router.patch("/user/{user_id}", response_model=UserProfileResponse, tags=["Users"])
async def update_user_profile(user_id: int, request: UpdateUserRequest):
    """Update user profile (nickname and/or avatar)."""
    with get_cursor() as cursor:
        # Check user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build dynamic update
        updates = []
        values = []
        if request.nickname is not None:
            # Check nickname not taken by another user
            cursor.execute(
                "SELECT id FROM users WHERE nickname = %s AND id != %s",
                (request.nickname, user_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Nickname already taken")
            updates.append("nickname = %s")
            values.append(request.nickname)
        if request.avatar is not None:
            updates.append("avatar = %s")
            values.append(request.avatar)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(user_id)
        cursor.execute(
            f"""
            UPDATE users SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, nickname, avatar, group_id, joined_at
            """,
            tuple(values),
        )
        user = cursor.fetchone()
        
        # Get group name
        cursor.execute("SELECT name FROM groups WHERE id = %s", (user["group_id"],))
        group = cursor.fetchone()
    
    return UserProfileResponse(
        id=user["id"],
        nickname=user["nickname"],
        avatar=user["avatar"],
        group_id=user["group_id"],
        group_name=group["name"],
        joined_at=user["joined_at"],
    )


@router.delete("/user/{user_id}", tags=["Users"])
async def delete_user(user_id: int):
    """Delete a user (leave group)."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user's votes first (FK constraint)
        cursor.execute("DELETE FROM votes WHERE user_id = %s", (user_id,))
        # Delete user's filter
        cursor.execute("DELETE FROM user_filters WHERE user_id = %s", (user_id,))
        # Delete user's filter amenities
        cursor.execute("DELETE FROM filter_amenities WHERE user_id = %s", (user_id,))
        # Delete user's filter requests
        cursor.execute("DELETE FROM filter_request WHERE user_id = %s", (user_id,))
        # Delete user's queue entries
        cursor.execute("DELETE FROM bnb_queue WHERE user_id = %s", (user_id,))
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    
    return {"message": "User deleted successfully"}


@router.get("/user/{user_id}/votes", response_model=UserVotesResponse, tags=["Users"])
async def get_user_votes(user_id: int):
    """Get all votes by a specific user."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        cursor.execute(
            """
            SELECT v.airbnb_id, b.title, v.vote, v.reason, v.created_at
            FROM votes v
            JOIN bnbs b ON b.airbnb_id = v.airbnb_id
            WHERE v.user_id = %s
            ORDER BY v.created_at DESC
            """,
            (user_id,),
        )
        votes = cursor.fetchall()
    
    return UserVotesResponse(
        user_id=user_id,
        votes=[
            UserVoteInfo(
                airbnb_id=v["airbnb_id"],
                title=v["title"] or "Untitled",
                vote=v["vote"],
                reason=v["reason"],
                created_at=v["created_at"],
            )
            for v in votes
        ],
        total_votes=len(votes),
    )


# =============================================================================
# GROUP MANAGEMENT ENDPOINTS
# =============================================================================

@router.patch("/group/{group_id}", response_model=GroupInfoResponse, tags=["Groups"])
async def update_group(group_id: int, request: UpdateGroupRequest):
    """Update group settings."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Build dynamic update
        updates = []
        values = []
        if request.name is not None:
            updates.append("name = %s")
            values.append(request.name)
        if request.date_start is not None:
            updates.append("date_range_start = %s")
            values.append(request.date_start)
        if request.date_end is not None:
            updates.append("date_range_end = %s")
            values.append(request.date_end)
        if request.adults is not None:
            updates.append("adults = %s")
            values.append(request.adults)
        if request.children is not None:
            updates.append("children = %s")
            values.append(request.children)
        if request.infants is not None:
            updates.append("infants = %s")
            values.append(request.infants)
        if request.pets is not None:
            updates.append("pets = %s")
            values.append(request.pets)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(group_id)
        cursor.execute(
            f"UPDATE groups SET {', '.join(updates)} WHERE id = %s",
            tuple(values),
        )
    
    # Return updated group info using existing endpoint logic
    return await get_group_info(group_id)


@router.delete("/group/{group_id}", tags=["Groups"])
async def delete_group(group_id: int):
    """Delete a group and all associated data."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all users in group
        cursor.execute("SELECT id FROM users WHERE group_id = %s", (group_id,))
        user_ids = [u["id"] for u in cursor.fetchall()]
        
        # Get all bnbs in group
        cursor.execute("SELECT airbnb_id FROM bnbs WHERE group_id = %s", (group_id,))
        bnb_ids = [b["airbnb_id"] for b in cursor.fetchall()]
        
        # Delete in order respecting FK constraints
        if user_ids:
            cursor.execute("DELETE FROM votes WHERE user_id = ANY(%s)", (user_ids,))
            cursor.execute("DELETE FROM filter_amenities WHERE user_id = ANY(%s)", (user_ids,))
            cursor.execute("DELETE FROM user_filters WHERE user_id = ANY(%s)", (user_ids,))
            cursor.execute("DELETE FROM filter_request WHERE user_id = ANY(%s)", (user_ids,))
            cursor.execute("DELETE FROM bnb_queue WHERE user_id = ANY(%s)", (user_ids,))
        
        if bnb_ids:
            cursor.execute("DELETE FROM bnb_images WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM bnb_amenities WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM votes WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM bnb_queue WHERE airbnb_id = ANY(%s)", (bnb_ids,))
        
        cursor.execute("DELETE FROM bnbs WHERE group_id = %s", (group_id,))
        cursor.execute("DELETE FROM users WHERE group_id = %s", (group_id,))
        cursor.execute("DELETE FROM destinations WHERE group_id = %s", (group_id,))
        cursor.execute("DELETE FROM groups WHERE id = %s", (group_id,))
    
    return {"message": "Group deleted successfully"}


@router.post("/group/{group_id}/destinations", response_model=DestinationInfo, tags=["Destinations"])
async def add_destination(group_id: int, request: AddDestinationRequest):
    """Add a destination to a group."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        cursor.execute(
            """
            INSERT INTO destinations (group_id, location_name)
            VALUES (%s, %s)
            RETURNING id, location_name
            """,
            (group_id, request.location_name),
        )
        dest = cursor.fetchone()
    
    return DestinationInfo(id=dest["id"], name=dest["location_name"])


@router.delete("/group/{group_id}/destinations/{destination_id}", tags=["Destinations"])
async def remove_destination(group_id: int, destination_id: int):
    """Remove a destination from a group."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM destinations WHERE id = %s AND group_id = %s",
            (destination_id, group_id),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Destination not found")
        
        # Delete related filter requests
        cursor.execute("DELETE FROM filter_request WHERE destination_id = %s", (destination_id,))
        # Delete bnbs for this destination
        cursor.execute(
            "SELECT airbnb_id FROM bnbs WHERE destination_id = %s",
            (destination_id,),
        )
        bnb_ids = [b["airbnb_id"] for b in cursor.fetchall()]
        
        if bnb_ids:
            cursor.execute("DELETE FROM bnb_images WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM bnb_amenities WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM votes WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM bnb_queue WHERE airbnb_id = ANY(%s)", (bnb_ids,))
            cursor.execute("DELETE FROM bnbs WHERE destination_id = %s", (destination_id,))
        
        cursor.execute("DELETE FROM destinations WHERE id = %s", (destination_id,))
    
    return {"message": "Destination removed successfully"}


@router.get("/group/{group_id}/stats", response_model=GroupStatsResponse, tags=["Groups"])
async def get_group_stats(group_id: int):
    """Get group statistics including vote progress per user."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get total listings
        cursor.execute("SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s", (group_id,))
        total_listings = cursor.fetchone()["count"]
        
        # Get users and their vote counts
        cursor.execute(
            """
            SELECT u.id as user_id, u.nickname, COUNT(v.airbnb_id) as votes_cast
            FROM users u
            LEFT JOIN votes v ON v.user_id = u.id
            LEFT JOIN bnbs b ON b.airbnb_id = v.airbnb_id AND b.group_id = u.group_id
            WHERE u.group_id = %s
            GROUP BY u.id, u.nickname
            ORDER BY u.nickname
            """,
            (group_id,),
        )
        users = cursor.fetchall()
    
    user_progress = []
    total_votes_possible = total_listings * len(users)
    total_votes_cast = 0
    
    for u in users:
        votes_cast = u["votes_cast"] or 0
        total_votes_cast += votes_cast
        completion = (votes_cast / total_listings * 100) if total_listings > 0 else 0
        user_progress.append(UserVoteProgress(
            user_id=u["user_id"],
            nickname=u["nickname"],
            votes_cast=votes_cast,
            total_listings=total_listings,
            completion_percent=round(completion, 1),
        ))
    
    overall_completion = (total_votes_cast / total_votes_possible * 100) if total_votes_possible > 0 else 0
    
    return GroupStatsResponse(
        group_id=group_id,
        total_listings=total_listings,
        total_users=len(users),
        user_progress=user_progress,
        overall_completion_percent=round(overall_completion, 1),
    )


# =============================================================================
# VOTING QUEUE ENDPOINTS
# =============================================================================

@router.get("/user/{user_id}/nextToVote", response_model=NextToVoteResponse, tags=["Voting"])
async def get_user_next_to_vote(user_id: int, exclude_bnb: int = Query(default=None)):
    """Returns the next airbnb to vote on except exclude_bnb """
    # TODO Implement this
    return NextToVoteResponse()

# Legacy, prefere nexttovote
@router.get("/user/{user_id}/queue", response_model=VotingQueueResponse, tags=["Voting"], deprecated=True)
async def get_user_voting_queue(user_id: int, limit: int = Query(default=10, le=50)):
    """Get unvoted listings for a user (their voting queue). Prefere nextToVote"""
    with get_cursor() as cursor:
        cursor.execute("SELECT id, group_id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        group_id = user["group_id"]
        
        # Get unvoted listings for this user
        cursor.execute(
            """
            SELECT 
                b.airbnb_id, b.title, b.price_per_night, b.bnb_rating, 
                b.bnb_review_count, b.main_image_url, b.min_bedrooms,
                b.min_beds, b.min_bathrooms, b.property_type
            FROM bnbs b
            WHERE b.group_id = %s
            AND NOT EXISTS (
                SELECT 1 FROM votes v WHERE v.airbnb_id = b.airbnb_id AND v.user_id = %s
            )
            ORDER BY b.airbnb_id
            LIMIT %s
            """,
            (group_id, user_id, limit),
        )
        unvoted = cursor.fetchall()
        
        # Get total unvoted count
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM bnbs b
            WHERE b.group_id = %s
            AND NOT EXISTS (
                SELECT 1 FROM votes v WHERE v.airbnb_id = b.airbnb_id AND v.user_id = %s
            )
            """,
            (group_id, user_id),
        )
        total_unvoted = cursor.fetchone()["count"]
        
        if not unvoted:
            return VotingQueueResponse(user_id=user_id, queue=[], total_unvoted=0)
        
        # Get airbnb_ids for batch queries
        airbnb_ids = [b["airbnb_id"] for b in unvoted]
        
        # Batch fetch images
        images_by_bnb: dict[str, list[str]] = {aid: [] for aid in airbnb_ids}
        cursor.execute(
            "SELECT airbnb_id, image_url FROM bnb_images WHERE airbnb_id = ANY(%s)",
            (airbnb_ids,),
        )
        for img in cursor.fetchall():
            images_by_bnb[img["airbnb_id"]].append(img["image_url"])
        
        # Batch fetch amenities
        amenities_by_bnb: dict[str, list[int]] = {aid: [] for aid in airbnb_ids}
        cursor.execute(
            "SELECT airbnb_id, amenity_id FROM bnb_amenities WHERE airbnb_id = ANY(%s)",
            (airbnb_ids,),
        )
        for amenity in cursor.fetchall():
            amenities_by_bnb[amenity["airbnb_id"]].append(amenity["amenity_id"])
        
        # Get other users' votes on these listings
        votes_by_bnb: dict[str, list[GroupVote]] = {aid: [] for aid in airbnb_ids}
        cursor.execute(
            """
            SELECT v.airbnb_id, v.user_id, u.nickname as user_name, v.vote, v.reason
            FROM votes v
            JOIN users u ON u.id = v.user_id
            WHERE v.airbnb_id = ANY(%s) AND v.user_id != %s
            """,
            (airbnb_ids, user_id),
        )
        for v in cursor.fetchall():
            votes_by_bnb[v["airbnb_id"]].append(GroupVote(
                user_id=v["user_id"],
                user_name=v["user_name"],
                airbnb_id=v["airbnb_id"],
                vote=v["vote"],
                reason=v["reason"],
            ))
        
        # Build queue
        queue = []
        for bnb in unvoted:
            airbnb_id = bnb["airbnb_id"]
            images = []
            if bnb["main_image_url"]:
                images.append(bnb["main_image_url"])
            images.extend(images_by_bnb.get(airbnb_id, []))
            if not images:
                images = ["https://placehold.co/400x300?text=No+Image"]
            
            queue.append(QueuedListing(
                airbnb_id=airbnb_id,
                title=bnb["title"] or "Untitled",
                price=bnb["price_per_night"] or 0,
                rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
                review_count=bnb["bnb_review_count"],
                images=images,
                bedrooms=bnb["min_bedrooms"],
                beds=bnb["min_beds"],
                bathrooms=bnb["min_bathrooms"],
                property_type=bnb["property_type"],
                amenities=amenities_by_bnb.get(airbnb_id, []),
                other_votes=votes_by_bnb.get(airbnb_id, []),
            ))
    
    return VotingQueueResponse(
        user_id=user_id,
        queue=queue,
        total_unvoted=total_unvoted,
    )


@router.get("/user/{user_id}/vote-progress", response_model=VoteProgressResponse, tags=["Voting"])
async def get_user_vote_progress(user_id: int):
    """Get user's voting progress."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id, group_id FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        group_id = user["group_id"]
        
        # Get total listings
        cursor.execute("SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s", (group_id,))
        total_listings = cursor.fetchone()["count"]
        
        # Get votes cast
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM votes v
            JOIN bnbs b ON b.airbnb_id = v.airbnb_id AND b.group_id = %s
            WHERE v.user_id = %s
            """,
            (group_id, user_id),
        )
        votes_cast = cursor.fetchone()["count"]
    
    remaining = total_listings - votes_cast
    completion = (votes_cast / total_listings * 100) if total_listings > 0 else 0
    
    return VoteProgressResponse(
        user_id=user_id,
        votes_cast=votes_cast,
        total_listings=total_listings,
        remaining=remaining,
        completion_percent=round(completion, 1),
    )


# =============================================================================
# LISTING DETAIL ENDPOINTS
# =============================================================================

@router.get("/listing/{airbnb_id}", response_model=ListingDetailResponse, tags=["Listings"])
async def get_listing_detail(airbnb_id: str):
    """Get full listing details."""
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT airbnb_id, group_id, destination_id, title, description,
                   price_per_night, bnb_rating, bnb_review_count, main_image_url,
                   min_bedrooms, min_beds, min_bathrooms, property_type
            FROM bnbs
            WHERE airbnb_id = %s
            """,
            (airbnb_id,),
        )
        bnb = cursor.fetchone()
        
        if not bnb:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Get images
        cursor.execute(
            "SELECT image_url FROM bnb_images WHERE airbnb_id = %s",
            (airbnb_id,),
        )
        extra_images = cursor.fetchall()
        
        # Get amenities
        cursor.execute(
            "SELECT amenity_id FROM bnb_amenities WHERE airbnb_id = %s",
            (airbnb_id,),
        )
        amenities = cursor.fetchall()
        
        images = []
        if bnb["main_image_url"]:
            images.append(bnb["main_image_url"])
        images.extend([img["image_url"] for img in extra_images])
        if not images:
            images = ["https://placehold.co/400x300?text=No+Image"]
    
    return ListingDetailResponse(
        airbnb_id=bnb["airbnb_id"],
        title=bnb["title"] or "Untitled",
        description=bnb["description"],
        price=bnb["price_per_night"] or 0,
        rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
        review_count=bnb["bnb_review_count"],
        images=images,
        bedrooms=bnb["min_bedrooms"],
        beds=bnb["min_beds"],
        bathrooms=bnb["min_bathrooms"],
        property_type=bnb["property_type"],
        amenities=[a["amenity_id"] for a in amenities],
        group_id=bnb["group_id"],
        destination_id=bnb["destination_id"],
    )


@router.get("/listing/{airbnb_id}/votes", response_model=ListingVotesResponse, tags=["Listings"])
async def get_listing_votes(airbnb_id: str):
    """Get all votes for a specific listing."""
    with get_cursor() as cursor:
        cursor.execute("SELECT airbnb_id FROM bnbs WHERE airbnb_id = %s", (airbnb_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Listing not found")
        
        cursor.execute(
            """
            SELECT v.user_id, u.nickname as user_name, v.airbnb_id, v.vote, v.reason
            FROM votes v
            JOIN users u ON u.id = v.user_id
            WHERE v.airbnb_id = %s
            ORDER BY v.created_at DESC
            """,
            (airbnb_id,),
        )
        votes = cursor.fetchall()
    
    # Calculate vote summary
    veto_count = sum(1 for v in votes if v["vote"] == 0)
    ok_count = sum(1 for v in votes if v["vote"] == 1)
    love_count = sum(1 for v in votes if v["vote"] == 2)
    super_love_count = sum(1 for v in votes if v["vote"] == 3)
    
    return ListingVotesResponse(
        airbnb_id=airbnb_id,
        votes=[
            GroupVote(
                user_id=v["user_id"],
                user_name=v["user_name"],
                airbnb_id=v["airbnb_id"],
                vote=v["vote"],
                reason=v["reason"],
            )
            for v in votes
        ],
        vote_summary=LeaderboardVoteSummary(
            veto_count=veto_count,
            ok_count=ok_count,
            love_count=love_count,
            super_love_count=super_love_count,
        ),
    )


@router.post("/listing/{airbnb_id}/refresh", tags=["Listings"])
async def refresh_listing(airbnb_id: str):
    """Trigger a re-scrape of listing details."""
    with get_cursor() as cursor:
        cursor.execute("SELECT airbnb_id FROM bnbs WHERE airbnb_id = %s", (airbnb_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Listing not found")
    
    job_id = trigger_listing_inquiry(airbnb_id, high_prio=True)
    
    return {"job_id": job_id, "message": f"Refresh triggered for listing {airbnb_id}"}


# =============================================================================
# SEARCH & DISCOVERY ENDPOINTS
# =============================================================================

@router.post("/group/{group_id}/search", response_model=GroupSearchResponse, tags=["Search"])
async def trigger_group_search(group_id: int, request: GroupSearchRequest):
    """Trigger a search for all destinations in a group."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all destinations and a user from the group
        cursor.execute("SELECT id FROM destinations WHERE group_id = %s", (group_id,))
        destinations = cursor.fetchall()
        
        if not destinations:
            raise HTTPException(status_code=400, detail="No destinations in group")
        
        # Get any user from the group to use for filter reference
        cursor.execute("SELECT id FROM users WHERE group_id = %s LIMIT 1", (group_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=400, detail="No users in group")
    
    # Trigger search for each destination
    job_ids = []
    for dest in destinations:
        job_id = trigger_search_job(
            user_id=user["id"],
            destination_id=dest["id"],
            page_start=1,
            page_end=request.page_count,
            high_prio=True,
        )
        job_ids.append(job_id)
    
    return GroupSearchResponse(
        job_ids=job_ids,
        destinations_count=len(destinations),
        message=f"Search triggered for {len(destinations)} destination(s)",
    )


@router.get("/group/{group_id}/search/status", response_model=SearchStatusResponse, tags=["Search"])
async def get_search_status(group_id: int):
    """Get the search/scraping status for a group."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM groups WHERE id = %s", (group_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Get all destinations with their scrape progress
        cursor.execute(
            """
            SELECT d.id as destination_id, d.location_name,
                   COALESCE(fr.pages_fetched, 0) as pages_fetched,
                   COALESCE(fr.pages_total, 0) as pages_total
            FROM destinations d
            LEFT JOIN filter_request fr ON fr.destination_id = d.id
            WHERE d.group_id = %s
            """,
            (group_id,),
        )
        destinations = cursor.fetchall()
    
    dest_statuses = []
    total_fetched = 0
    total_pages = 0
    
    for d in destinations:
        pages_fetched = d["pages_fetched"]
        pages_total = d["pages_total"]
        total_fetched += pages_fetched
        total_pages += pages_total
        
        dest_statuses.append(SearchStatusDestination(
            destination_id=d["destination_id"],
            location_name=d["location_name"],
            pages_fetched=pages_fetched,
            pages_total=pages_total,
            is_complete=pages_fetched >= pages_total if pages_total > 0 else False,
        ))
    
    overall_progress = (total_fetched / total_pages * 100) if total_pages > 0 else 0
    
    return SearchStatusResponse(
        group_id=group_id,
        destinations=dest_statuses,
        overall_progress_percent=round(overall_progress, 1),
    )




@router.websocket("/ws/leaderboard/{group_id}")
async def websocket_leaderboard(websocket: WebSocket, group_id: int):
    """
    WebSocket endpoint for real-time leaderboard updates.
    
    Connect to receive leaderboard updates whenever votes change.
    
    Messages sent to client:
    - Initial connection: Full leaderboard data
    - On update: Full leaderboard data with "type": "update"
    """
    await leaderboard_manager.connect(websocket, group_id)
    
    try:
        # Send initial leaderboard data
        initial_data = await get_leaderboard_data_for_ws(group_id)
        initial_data["type"] = "initial"
        await websocket.send_json(initial_data)
        
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for messages from client (e.g., ping/pong or refresh requests)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                # Handle refresh request
                if data.get("action") == "refresh":
                    leaderboard_data = await get_leaderboard_data_for_ws(group_id)
                    leaderboard_data["type"] = "update"
                    await websocket.send_json(leaderboard_data)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    finally:
        leaderboard_manager.disconnect(websocket, group_id)