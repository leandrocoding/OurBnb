from typing import Optional, List
from datetime import date, datetime

from pydantic import BaseModel


# Group schemas
class CreateGroupRequest(BaseModel):
    group_name: str
    destinations: List[str]
    date_start: date
    date_end: date
    adults: int
    children: int = 0
    infants: int = 0
    pets: int = 0


class CreateGroupResponse(BaseModel):
    group_id: int


class UserInfo(BaseModel):
    id: int
    nickname: str
    avatar: Optional[str] = None


class DestinationInfo(BaseModel):
    id: int
    name: str


class UserVoteProgress(BaseModel):
    """Vote progress for a single user"""
    user_id: int
    nickname: str
    votes_cast: int
    total_listings: int


class GroupInfoResponse(BaseModel):
    group_id: int
    group_name: str
    destinations: List[DestinationInfo]
    date_start: date
    date_end: date
    adults: int
    children: int
    infants: int
    pets: int
    price_range_min: Optional[int] = None
    price_range_max: Optional[int] = None
    users: List[UserInfo]
    total_listings: int = 0
    user_progress: List[UserVoteProgress] = []


class JoinGroupRequest(BaseModel):
    group_id: int
    username: str
    avatar: Optional[str] = None


class JoinGroupResponse(BaseModel):
    user_id: int


# Filter schemas
class UserFilter(BaseModel):
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = None
    min_beds: Optional[int] = None
    min_bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []


class FilterResponse(BaseModel):
    user_id: int
    min_price: Optional[int] = 0
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = 0
    min_beds: Optional[int] = 0
    min_bathrooms: Optional[int] = 0
    property_type: Optional[str] = None
    updated_at: Optional[datetime] = None
    amenities: List[int] = []


# Search job schemas
class TriggerSearchRequest(BaseModel):
    user_id: int
    destination_id: int
    page_start: int = 1
    page_end: int = 2


class TriggerSearchResponse(BaseModel):
    job_id: str
    message: str


# Listing/Property schemas
class PropertyInfo(BaseModel):
    id: str  # airbnb_id
    title: str
    price: int  # price_per_night
    rating: Optional[float] = None
    review_count: Optional[int] = None
    images: List[str]
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []


class GroupListingsResponse(BaseModel):
    listings: List[PropertyInfo]


class VoteRequest(BaseModel):
    user_id: int
    airbnb_id: str
    vote: int  # 0 = veto, 1 = ok, 2 = love, 3 = super love
    reason: Optional[str] = None


class VoteResponse(BaseModel):
    user_id: int
    airbnb_id: str
    vote: int
    reason: Optional[str] = None


class GroupVote(BaseModel):
    user_id: int
    user_name: str
    airbnb_id: str
    vote: int
    reason: Optional[str] = None


class GroupVotesResponse(BaseModel):
    votes: List[GroupVote]


class NextToVoteResponse(BaseModel):
    """Response for next listing to vote on. All fields optional when no listings available."""
    airbnb_id: Optional[str] = None
    title: Optional[str] = None
    price: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    location: Optional[str] = None
    images: List[str] = []
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []
    # Other users' votes on this listing
    other_votes: List[GroupVote] = []
    # Booking link with all parameters
    booking_link: Optional[str] = None
    # Meta info
    has_listing: bool = False
    total_remaining: int = 0  # Unvoted listings for this user
    total_listings: int = 0   # Total listings in the group (for detecting "no listings yet" vs "all voted")


class VoteWithNextResponse(BaseModel):
    """Response after voting that includes the next listing to vote on."""
    # Vote confirmation
    user_id: int
    airbnb_id: str
    vote: int
    reason: Optional[str] = None
    # Next listing (same structure as NextToVoteResponse)
    next_listing: Optional[NextToVoteResponse] = None


# Leaderboard schemas
class LeaderboardVoteSummary(BaseModel):
    """Summary of votes for a listing"""
    veto_count: int = 0
    dislike_count: int = 0
    like_count: int = 0
    super_like_count: int = 0


class LeaderboardEntry(BaseModel):
    """A single entry in the leaderboard"""
    rank: int
    airbnb_id: str
    title: str
    price: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
    location: Optional[str] = None
    images: List[str]
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []
    # Scoring breakdown
    score: int
    filter_matches: int  # how many users' filters this listing matches
    votes: LeaderboardVoteSummary
    # Booking link to Airbnb
    booking_link: str


class LeaderboardResponse(BaseModel):
    """Response containing the ranked listings"""
    entries: List[LeaderboardEntry]
    total_listings: int  # total listings in the group (not just top 20)
    total_users: int  # total users in the group





# =============================================================================
# Demo Schemas
# =============================================================================

class DemoGroupInfo(BaseModel):
    """Group info for demo page"""
    group_id: int
    group_name: str
    users: List[UserInfo]


class DemoAllGroupsResponse(BaseModel):
    """All groups with users for demo login"""
    groups: List[DemoGroupInfo]


# =============================================================================
# Recommendations Schemas (Batch Fetching)
# =============================================================================

class RecommendationListing(BaseModel):
    """A single listing in the recommendations batch"""
    airbnb_id: str
    title: str
    price: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
    location: Optional[str] = None
    images: List[str]
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []
    # Scoring info
    score: int
    filter_matches: int
    # Other users' votes on this listing
    other_votes: List[GroupVote] = []
    # Booking link with all parameters
    booking_link: Optional[str] = None


class RecommendationsResponse(BaseModel):
    """Batch of recommendations for a user"""
    recommendations: List[RecommendationListing]
    total_remaining: int  # Unvoted listings for this user
    has_more: bool