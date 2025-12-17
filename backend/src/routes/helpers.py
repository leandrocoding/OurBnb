"""
Shared helper functions for route handlers.
"""

from typing import Dict
from models.schemas import GroupVote


def get_images_and_amenities_for_bnbs(cursor, group_id: int, airbnb_ids: list[str]) -> tuple[dict, dict]:
    """Helper to batch fetch images and amenities for a list of bnbs."""
    images_by_bnb: dict[str, list[str]] = {aid: [] for aid in airbnb_ids}
    amenities_by_bnb: dict[str, list[int]] = {aid: [] for aid in airbnb_ids}
    
    if not airbnb_ids:
        return images_by_bnb, amenities_by_bnb
    
    # Fetch images (with composite key)
    cursor.execute(
        "SELECT airbnb_id, image_url FROM bnb_images WHERE group_id = %s AND airbnb_id = ANY(%s)",
        (group_id, airbnb_ids),
    )
    for img in cursor.fetchall():
        images_by_bnb[img["airbnb_id"]].append(img["image_url"])
    
    # Fetch amenities (with composite key)
    cursor.execute(
        "SELECT airbnb_id, amenity_id FROM bnb_amenities WHERE group_id = %s AND airbnb_id = ANY(%s)",
        (group_id, airbnb_ids),
    )
    for amenity in cursor.fetchall():
        amenities_by_bnb[amenity["airbnb_id"]].append(amenity["amenity_id"])
    
    return images_by_bnb, amenities_by_bnb


def get_other_votes_for_bnbs(cursor, group_id: int, airbnb_ids: list[str], exclude_user_id: int = None) -> dict[str, list[GroupVote]]:
    """Helper to get other users' votes for a list of bnbs."""
    votes_by_bnb: dict[str, list[GroupVote]] = {aid: [] for aid in airbnb_ids}
    
    if not airbnb_ids:
        return votes_by_bnb
    
    if exclude_user_id is not None:
        cursor.execute(
            """
            SELECT v.airbnb_id, v.user_id, u.nickname as user_name, v.vote, v.reason
            FROM votes v
            JOIN users u ON u.id = v.user_id
            WHERE v.group_id = %s AND v.airbnb_id = ANY(%s) AND v.user_id != %s
            """,
            (group_id, airbnb_ids, exclude_user_id),
        )
    else:
        cursor.execute(
            """
            SELECT v.airbnb_id, v.user_id, u.nickname as user_name, v.vote, v.reason
            FROM votes v
            JOIN users u ON u.id = v.user_id
            WHERE v.group_id = %s AND v.airbnb_id = ANY(%s)
            """,
            (group_id, airbnb_ids),
        )
    
    for v in cursor.fetchall():
        votes_by_bnb[v["airbnb_id"]].append(GroupVote(
            user_id=v["user_id"],
            user_name=v["user_name"],
            airbnb_id=v["airbnb_id"],
            vote=v["vote"],
            reason=v["reason"],
        ))
    
    return votes_by_bnb


def build_booking_link(airbnb_id: str, group: dict) -> str:
    """Build an Airbnb booking link from group data."""
    check_in = group["date_range_start"].strftime("%Y-%m-%d")
    check_out = group["date_range_end"].strftime("%Y-%m-%d")
    adults = group["adults"]
    children = group["children"]
    infants = group["infants"]
    pets = group["pets"]
    
    booking_link = f"https://www.airbnb.ch/rooms/{airbnb_id}?adults={adults}&check_in={check_in}&check_out={check_out}"
    if children > 0:
        booking_link += f"&children={children}"
    if infants > 0:
        booking_link += f"&infants={infants}"
    if pets > 0:
        booking_link += f"&pets={pets}"
    
    return booking_link
