"""
Leaderboard routes: WebSocket manager, leaderboard endpoint, and real-time updates.
"""

import asyncio
from typing import Dict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from constants import LEADERBOARD_LIMIT
from models.schemas import (
    LeaderboardEntry,
    LeaderboardVoteSummary,
    LeaderboardResponse,
)
from db import get_cursor
from scoring import get_leaderboard_scores
from .helpers import get_images_and_amenities_for_bnbs, build_booking_link

router = APIRouter(tags=["Leaderboard"])


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
        cursor.execute(
            """SELECT id, adults, children, infants, pets, date_range_start, date_range_end 
               FROM groups WHERE id = %s""",
            (group_id,),
        )
        group = cursor.fetchone()
        if not group:
            return {"error": "Group not found"}
        
        # Get total user count
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE group_id = %s", (group_id,))
        total_users = cursor.fetchone()["count"]
        
        # Get total listings count
        cursor.execute("SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s", (group_id,))
        total_listings = cursor.fetchone()["count"]
        
        # Get scored bnbs for leaderboard
        scored_bnbs = get_leaderboard_scores(group_id, limit=LEADERBOARD_LIMIT)
        
        if not scored_bnbs:
            return {
                "entries": [],
                "total_listings": total_listings,
                "total_users": total_users,
            }
        
        # Batch fetch images and amenities
        airbnb_ids = [bnb.airbnb_id for bnb in scored_bnbs]
        images_by_bnb, amenities_by_bnb = get_images_and_amenities_for_bnbs(cursor, group_id, airbnb_ids)
        
        # Build response
        entries = []
        for rank, bnb in enumerate(scored_bnbs, start=1):
            airbnb_id = bnb.airbnb_id
            images = []
            if bnb.main_image_url:
                images.append(bnb.main_image_url)
            images.extend(images_by_bnb.get(airbnb_id, []))
            if not images:
                images = ["https://placehold.co/400x300?text=No+Image"]
            
            # Build Airbnb booking link
            booking_link = build_booking_link(airbnb_id, group)
            
            # Get location name (extract first part before comma for display)
            location = bnb.location_name.split(',')[0] if bnb.location_name else None
            
            entries.append({
                "rank": rank,
                "airbnb_id": airbnb_id,
                "title": bnb.title,
                "price": bnb.price_per_night,
                "rating": bnb.bnb_rating,
                "review_count": bnb.bnb_review_count,
                "location": location,
                "images": images,
                "bedrooms": bnb.min_bedrooms,
                "beds": bnb.min_beds,
                "bathrooms": bnb.min_bathrooms,
                "property_type": bnb.property_type,
                "amenities": amenities_by_bnb.get(airbnb_id, []),
                "score": bnb.score,
                "filter_matches": bnb.filter_matches,
                "votes": {
                    "veto_count": bnb.veto_count,
                    "ok_count": bnb.ok_count,
                    "love_count": bnb.love_count,
                    "super_love_count": bnb.super_love_count,
                },
                "booking_link": booking_link,
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

@router.get("/group/{group_id}/leaderboard", response_model=LeaderboardResponse)
async def get_group_leaderboard(group_id: int):
    """
    Get the leaderboard for a group with dynamically calculated scores.
    
    Scores are calculated by the BnbScorer based on:
    - How many users' filters the listing matches
    - Votes received (veto, ok, love, super love)
    
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
        total_users = cursor.fetchone()["count"]
        
        # Get total listings count
        cursor.execute(
            "SELECT COUNT(*) as count FROM bnbs WHERE group_id = %s",
            (group_id,),
        )
        total_listings = cursor.fetchone()["count"]
        
        if total_listings == 0:
            return LeaderboardResponse(entries=[], total_listings=0, total_users=total_users)
        
        # Get scored bnbs for leaderboard
        scored_bnbs = get_leaderboard_scores(group_id, limit=LEADERBOARD_LIMIT)
        
        # Get airbnb_ids for batch queries
        airbnb_ids = [bnb.airbnb_id for bnb in scored_bnbs]
        
        # Batch fetch images and amenities
        images_by_bnb, amenities_by_bnb = get_images_and_amenities_for_bnbs(cursor, group_id, airbnb_ids)
        
        # Build response
        entries = []
        for rank, bnb in enumerate(scored_bnbs, start=1):
            airbnb_id = bnb.airbnb_id
            
            # Build images list (main image first)
            images = []
            if bnb.main_image_url:
                images.append(bnb.main_image_url)
            images.extend(images_by_bnb.get(airbnb_id, []))
            if not images:
                images = ["https://placehold.co/400x300?text=No+Image"]
            
            # Build Airbnb booking link
            booking_link = build_booking_link(airbnb_id, group)
            
            # Get location name (extract first part before comma for display)
            location = bnb.location_name.split(',')[0] if bnb.location_name else None
            
            entries.append(LeaderboardEntry(
                rank=rank,
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
                votes=LeaderboardVoteSummary(
                    veto_count=bnb.veto_count,
                    ok_count=bnb.ok_count,
                    love_count=bnb.love_count,
                    super_love_count=bnb.super_love_count,
                ),
                booking_link=booking_link,
            ))
    
    return LeaderboardResponse(
        entries=entries,
        total_listings=total_listings,
        total_users=total_users,
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
