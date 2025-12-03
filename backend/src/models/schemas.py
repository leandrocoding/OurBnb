from typing import Optional, List
from datetime import date, datetime

from pydantic import BaseModel


class TestData(BaseModel):
    some_text: Optional[str] = None
    random_number: Optional[str] = None


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
    users: List[UserInfo]


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
    max_price: Optional[int] = 1000
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
    airbnb_id: str
    title: str
    price: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
    images: List[str]
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []
    # Other users' votes on this listing
    other_votes: List[GroupVote] = []


# Leaderboard schemas
class LeaderboardVoteSummary(BaseModel):
    """Summary of votes for a listing"""
    veto_count: int = 0
    ok_count: int = 0
    love_count: int = 0
    super_love_count: int = 0


class LeaderboardEntry(BaseModel):
    """A single entry in the leaderboard"""
    rank: int
    airbnb_id: str
    title: str
    price: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
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
# User Management Schemas
# =============================================================================

class UserProfileResponse(BaseModel):
    """Full user profile"""
    id: int
    nickname: str
    avatar: Optional[str] = None
    group_id: int
    group_name: str
    joined_at: Optional[datetime] = None


class UpdateUserRequest(BaseModel):
    """Update user profile"""
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserVoteInfo(BaseModel):
    """Vote info for user's votes endpoint"""
    airbnb_id: str
    title: str
    vote: int
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


class UserVotesResponse(BaseModel):
    """All votes by a user"""
    user_id: int
    votes: List[UserVoteInfo]
    total_votes: int


# =============================================================================
# Group Management Schemas
# =============================================================================

class UpdateGroupRequest(BaseModel):
    """Update group settings"""
    name: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    infants: Optional[int] = None
    pets: Optional[int] = None


class AddDestinationRequest(BaseModel):
    """Add a destination to a group"""
    location_name: str


class UserVoteProgress(BaseModel):
    """Vote progress for a single user"""
    user_id: int
    nickname: str
    votes_cast: int
    total_listings: int
    completion_percent: float


class GroupStatsResponse(BaseModel):
    """Group statistics"""
    group_id: int
    total_listings: int
    total_users: int
    user_progress: List[UserVoteProgress]
    overall_completion_percent: float


# =============================================================================
# Voting Queue Schemas
# =============================================================================

class QueuedListing(BaseModel):
    """A listing in the user's voting queue"""
    airbnb_id: str
    title: str
    price: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
    images: List[str]
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []
    # Other users' votes on this listing
    other_votes: List[GroupVote] = []


class VotingQueueResponse(BaseModel):
    """User's voting queue"""
    user_id: int
    queue: List[QueuedListing]
    total_unvoted: int


class VoteProgressResponse(BaseModel):
    """User's voting progress"""
    user_id: int
    votes_cast: int
    total_listings: int
    remaining: int
    completion_percent: float


# =============================================================================
# Listing Detail Schemas
# =============================================================================

class ListingDetailResponse(BaseModel):
    """Full listing details"""
    airbnb_id: str
    title: str
    description: Optional[str] = None
    price: int
    rating: Optional[float] = None
    review_count: Optional[int] = None
    images: List[str]
    bedrooms: Optional[int] = None
    beds: Optional[int] = None
    bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    amenities: List[int] = []
    group_id: int
    destination_id: int


class ListingVotesResponse(BaseModel):
    """All votes for a listing"""
    airbnb_id: str
    votes: List[GroupVote]
    vote_summary: LeaderboardVoteSummary


# =============================================================================
# Search & Discovery Schemas
# =============================================================================

class GroupSearchRequest(BaseModel):
    """Trigger search for a group"""
    page_count: int = 4  # pages per destination


class GroupSearchResponse(BaseModel):
    """Response after triggering group search"""
    job_ids: List[str]
    destinations_count: int
    message: str


class SearchStatusDestination(BaseModel):
    """Search status for a destination"""
    destination_id: int
    location_name: str
    pages_fetched: int
    pages_total: int
    is_complete: bool


class SearchStatusResponse(BaseModel):
    """Search status for a group"""
    group_id: int
    destinations: List[SearchStatusDestination]
    overall_progress_percent: float


class DestinationSuggestion(BaseModel):
    """Autocomplete suggestion"""
    name: str
    # Could add more fields like country, popularity, etc.


class DestinationAutocompleteResponse(BaseModel):
    """Autocomplete results"""
    query: str
    suggestions: List[DestinationSuggestion]