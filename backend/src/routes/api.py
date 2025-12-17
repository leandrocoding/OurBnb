"""
Main API router that combines all route modules.

This module serves as the central routing point for the backend API.
All routes are prefixed with /api to maintain backwards compatibility.
"""

from fastapi import APIRouter

from .groups import router as groups_router
from .filters import router as filters_router
from .listings import router as listings_router
from .voting import router as voting_router, set_notify_leaderboard_callback
from .leaderboard import router as leaderboard_router, notify_leaderboard_update
from .users import router as users_router

# Create main router with /api prefix
router = APIRouter(prefix="/api")

# Include all sub-routers (they don't have their own prefix since /api is the common prefix)
router.include_router(groups_router)
router.include_router(filters_router)
router.include_router(listings_router)
router.include_router(voting_router)
router.include_router(leaderboard_router)
router.include_router(users_router)

# Wire up the leaderboard notification callback for voting
set_notify_leaderboard_callback(notify_leaderboard_update)
