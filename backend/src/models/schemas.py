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
    teens: int = 0
    children: int = 0
    pets: int = 0


class CreateGroupResponse(BaseModel):
    invite_code: str


class UserInfo(BaseModel):
    id: int
    nickname: str
    avatar: Optional[str] = None


class GroupInfoResponse(BaseModel):
    group_name: str
    users: List[UserInfo]


class JoinGroupRequest(BaseModel):
    invite_code: str
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


class FilterResponse(BaseModel):
    user_id: int
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_bedrooms: Optional[int] = None
    min_beds: Optional[int] = None
    min_bathrooms: Optional[int] = None
    property_type: Optional[str] = None
    updated_at: Optional[datetime] = None


# Search job schemas
class TriggerSearchRequest(BaseModel):
    user_id: int
    destination_id: int
    page_start: int = 1
    page_end: int = 2


class TriggerSearchResponse(BaseModel):
    job_id: str
    message: str


