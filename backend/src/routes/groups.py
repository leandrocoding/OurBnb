"""
Group management routes: create, info, join, and demo endpoints.
"""

import os
import httpx

from fastapi import APIRouter, HTTPException

from models.schemas import (
    CreateGroupRequest,
    CreateGroupResponse,
    GroupInfoResponse,
    UserInfo,
    DestinationInfo,
    JoinGroupRequest,
    JoinGroupResponse,
    UserVoteProgress,
    DemoGroupInfo,
    DemoAllGroupsResponse,
)
from db import get_cursor

# Microservice URL for price range lookups
MICROSERVICE_URL = os.getenv("MICROSERVICE_URL", "http://microservice:8081")

router = APIRouter(tags=["Groups"])


@router.post("/group/create", response_model=CreateGroupResponse)
async def create_group(request: CreateGroupRequest):
    """Create a new group and return the group ID."""
    destinations_to_update = []  # List of (dest_id, location_name)
    
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
        
        # Insert destinations and collect their info
        for destination in request.destinations:
            cursor.execute(
                """
                INSERT INTO destinations (group_id, location_name)
                VALUES (%s, %s)
                RETURNING id
                """,
                (group_id, destination),
            )
            dest_row = cursor.fetchone()
            destinations_to_update.append((dest_row["id"], destination))
    
    # Fetch price ranges from microservice and update DB (after commit)
    overall_min = None
    overall_max = None
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for dest_id, location_name in destinations_to_update:
            try:
                response = await client.post(
                    f"{MICROSERVICE_URL}/v1/search/price-range",
                    json={
                        "location": location_name,
                        "checkin": str(request.date_start),
                        "checkout": str(request.date_end),
                        "adults": request.adults,
                        "children": request.children,
                        "infants": request.infants,
                        "pets": request.pets,
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    min_price = data["min_price"]
                    max_price = data["max_price"]
                    
                    # Track overall min/max across all destinations
                    if overall_min is None or min_price < overall_min:
                        overall_min = min_price
                    if overall_max is None or max_price > overall_max:
                        overall_max = max_price
                    
                    print(f"Price range for {location_name}: {min_price}-{max_price}")
                else:
                    print(f"Failed to get price range for {location_name}: {response.status_code}")
            except Exception as e:
                print(f"Error fetching price range for {location_name}: {e}")
    
    # Update group with overall price range
    if overall_min is not None and overall_max is not None:
        with get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE groups 
                SET price_range_min = %s, price_range_max = %s
                WHERE id = %s
                """,
                (overall_min, overall_max, group_id)
            )
        print(f"Group {group_id} overall price range: {overall_min}-{overall_max}")
    
    return CreateGroupResponse(group_id=group_id)


@router.get("/demo/groups", response_model=DemoAllGroupsResponse, tags=["Demo"])
async def get_all_groups_for_demo():
    """Get all groups with their users for demo login page."""
    with get_cursor() as cursor:
        # Get all groups
        cursor.execute(
            """
            SELECT id, name 
            FROM groups 
            ORDER BY id
            """
        )
        groups = cursor.fetchall()
        
        result_groups = []
        for group in groups:
            # Get users for this group
            cursor.execute(
                """
                SELECT id, nickname, avatar 
                FROM users 
                WHERE group_id = %s 
                ORDER BY id
                """,
                (group["id"],),
            )
            users = cursor.fetchall()
            
            result_groups.append(
                DemoGroupInfo(
                    group_id=group["id"],
                    group_name=group["name"],
                    users=[
                        UserInfo(
                            id=u["id"],
                            nickname=u["nickname"],
                            avatar=u["avatar"],
                        )
                        for u in users
                    ],
                )
            )
        
        return DemoAllGroupsResponse(groups=result_groups)


@router.get("/group/info/{group_id}", response_model=GroupInfoResponse)
async def get_group_info(group_id: int):
    """Get group information by group ID, including vote progress per user."""
    with get_cursor() as cursor:
        # Get group info
        cursor.execute(
            """SELECT id, name, date_range_start, date_range_end, adults, children, infants, pets,
                      price_range_min, price_range_max
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
            DestinationInfo(
                id=dest["id"], 
                name=dest["location_name"]
            )
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
        
        # Get total listings count
        cursor.execute("SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s", (group_id,))
        total_listings = cursor.fetchone()["count"]
        
        # Get vote counts per user
        cursor.execute(
            """
            SELECT u.id as user_id, u.nickname, COUNT(v.airbnb_id) as votes_cast
            FROM users u
            LEFT JOIN votes v ON v.user_id = u.id AND v.group_id = %s
            WHERE u.group_id = %s
            GROUP BY u.id, u.nickname
            ORDER BY u.nickname
            """,
            (group_id, group_id),
        )
        user_votes = cursor.fetchall()
        
        user_progress = [
            UserVoteProgress(
                user_id=u["user_id"],
                nickname=u["nickname"],
                votes_cast=u["votes_cast"] or 0,
                total_listings=total_listings,
            )
            for u in user_votes
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
        price_range_min=group["price_range_min"],
        price_range_max=group["price_range_max"],
        users=user_list,
        total_listings=total_listings,
        user_progress=user_progress,
    )


@router.post("/group/join", response_model=JoinGroupResponse)
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
            "SELECT id FROM users WHERE nickname = %s AND group_id = %s",
            (request.username, request.group_id,),
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
