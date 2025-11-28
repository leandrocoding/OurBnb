import secrets
from datetime import datetime

from fastapi import APIRouter, HTTPException

from models.schemas import (
    TestData,
    CreateGroupRequest,
    CreateGroupResponse,
    GroupInfoResponse,
    UserInfo,
    JoinGroupRequest,
    JoinGroupResponse,
    UserFilter,
    FilterResponse,
    TriggerSearchRequest,
    TriggerSearchResponse,
)
from db import get_cursor
from scrape_utils import trigger_search_job

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/test-data", response_model=TestData)
async def test_data():
    return TestData(some_text="Hello World!", random_number="42")


def generate_invite_code(length: int = 8) -> str:
    """Generate a random invite code."""
    return secrets.token_urlsafe(length)[:length].upper()


@router.post("/group/create", response_model=CreateGroupResponse)
async def create_group(request: CreateGroupRequest):
    """Create a new group and return the invite code."""
    invite_code = generate_invite_code()
    
    with get_cursor() as cursor:
        # Check if invite code already exists (unlikely but possible)
        cursor.execute("SELECT id FROM groups WHERE invite_code = %s", (invite_code,))
        while cursor.fetchone():
            invite_code = generate_invite_code()
            cursor.execute("SELECT id FROM groups WHERE invite_code = %s", (invite_code,))
        
        # Insert the group
        cursor.execute(
            """
            INSERT INTO groups (invite_code, name, adults, teens, child, pets, date_range_start, date_range_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                invite_code,
                request.group_name,
                request.adults,
                request.teens,
                request.children,
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
    
    return CreateGroupResponse(invite_code=invite_code)


@router.get("/group/info/{g_code}", response_model=GroupInfoResponse)
async def get_group_info(g_code: str):
    """Get group information by invite code."""
    with get_cursor() as cursor:
        # Get group info
        cursor.execute(
            "SELECT id, name FROM groups WHERE invite_code = %s",
            (g_code,),
        )
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
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
    
    return GroupInfoResponse(group_name=group["name"], users=user_list)


@router.post("/group/join", response_model=JoinGroupResponse)
async def join_group(request: JoinGroupRequest):
    """Join a group and return the user ID."""
    with get_cursor() as cursor:
        # Get group by invite code
        cursor.execute(
            "SELECT id FROM groups WHERE invite_code = %s",
            (request.invite_code,),
        )
        group = cursor.fetchone()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Create user
        cursor.execute(
            """
            INSERT INTO users (group_id, nickname, avatar)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (group["id"], request.username, request.avatar),
        )
        user_row = cursor.fetchone()
        user_id = user_row["id"]
    
    return JoinGroupResponse(user_id=user_id)


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
            return FilterResponse(
                user_id=filter_row["user_id"],
                min_price=filter_row["min_price"],
                max_price=filter_row["max_price"],
                min_bedrooms=filter_row["min_bedrooms"],
                min_beds=filter_row["min_beds"],
                min_bathrooms=filter_row["min_bathrooms"],
                property_type=filter_row["property_type"],
                updated_at=filter_row["updated_at"],
            )
        
        # Return default filter if none exists
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
    
    return FilterResponse(
        user_id=filter_row["user_id"],
        min_price=filter_row["min_price"],
        max_price=filter_row["max_price"],
        min_bedrooms=filter_row["min_bedrooms"],
        min_beds=filter_row["min_beds"],
        min_bathrooms=filter_row["min_bathrooms"],
        property_type=filter_row["property_type"],
        updated_at=filter_row["updated_at"],
    )


@router.post("/search/trigger", response_model=TriggerSearchResponse)
async def trigger_search(request: TriggerSearchRequest):
    """Trigger a search job for the scraper worker."""
    with get_cursor() as cursor:
        # Verify user exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (request.user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify destination exists
        cursor.execute("SELECT id FROM destinations WHERE id = %s", (request.destination_id,))
        destination = cursor.fetchone()
        if not destination:
            raise HTTPException(status_code=404, detail="Destination not found")
    
    # Trigger the search job
    job_id = trigger_search_job(
        user_id=request.user_id,
        destination_id=request.destination_id,
        page_start=request.page_start,
        page_end=request.page_end,
    )
    
    return TriggerSearchResponse(
        job_id=job_id,
        message=f"Search job triggered for user {request.user_id} and destination {request.destination_id}"
    )

