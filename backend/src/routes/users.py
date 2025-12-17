"""
User management routes: delete user (leave group).
"""

from fastapi import APIRouter, HTTPException

from db import get_cursor

router = APIRouter(tags=["Users"])


@router.delete("/user/{user_id}")
async def delete_user(user_id: int):
    """Delete a user (leave group)."""
    with get_cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user's votes first (FK constraint)
        cursor.execute("DELETE FROM votes WHERE user_id = %s", (user_id,))
        # Delete user's filter amenities (must be before user_filters due to FK)
        cursor.execute("DELETE FROM filter_amenities WHERE user_id = %s", (user_id,))
        # Delete user's filter
        cursor.execute("DELETE FROM user_filters WHERE user_id = %s", (user_id,))
        # Delete user's filter requests
        cursor.execute("DELETE FROM filter_request WHERE user_id = %s", (user_id,))
        # Delete the user
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    
    return {"message": "User deleted successfully"}
