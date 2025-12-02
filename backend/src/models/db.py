from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Date, DateTime, SmallInteger, 
    Numeric, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    adults: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    teens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    children: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    date_range_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_range_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    destinations: Mapped[List["Destination"]] = relationship("Destination", back_populates="group")
    users: Mapped[List["User"]] = relationship("User", back_populates="group")
    bnbs: Mapped[List["Bnb"]] = relationship("Bnb", back_populates="group")

    __table_args__ = (
        CheckConstraint("date_range_start < date_range_end"),
        CheckConstraint("adults >= 0"),
        CheckConstraint("teens >= 0"),
        CheckConstraint("children >= 0"),
        CheckConstraint("pets >= 0"),
    )


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False)
    location_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="destinations")
    bnbs: Mapped[List["Bnb"]] = relationship("Bnb", back_populates="destination")
    filter_requests: Mapped[List["FilterRequest"]] = relationship("FilterRequest", back_populates="destination")

    __table_args__ = (
        Index("destinations_group_id_idx", "group_id"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="users")
    filters: Mapped[Optional["UserFilter"]] = relationship("UserFilter", back_populates="user", uselist=False)
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="user")
    bnb_queue: Mapped[List["BnbQueue"]] = relationship("BnbQueue", back_populates="user")
    filter_requests: Mapped[List["FilterRequest"]] = relationship("FilterRequest", back_populates="user")

    __table_args__ = (
        Index("users_group_id_idx", "group_id"),
    )


class UserFilter(Base):
    __tablename__ = "user_filters"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    min_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    property_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="filters")
    amenities: Mapped[List["FilterAmenity"]] = relationship("FilterAmenity", back_populates="user_filter")

    __table_args__ = (
        CheckConstraint("min_price <= max_price OR max_price IS NULL"),
        CheckConstraint("min_price >= 0 OR min_price IS NULL"),
        CheckConstraint("max_price >= 0 OR max_price IS NULL"),
        CheckConstraint("min_bedrooms >= 0 OR min_bedrooms IS NULL"),
        CheckConstraint("min_beds >= 0 OR min_beds IS NULL"),
        CheckConstraint("min_bathrooms >= 0 OR min_bathrooms IS NULL"),
    )


class FilterAmenity(Base):
    __tablename__ = "filter_amenities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_filters.user_id"), nullable=False)
    amenity_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    user_filter: Mapped["UserFilter"] = relationship("UserFilter", back_populates="amenities")

    __table_args__ = (
        Index("filter_amenities_user_id_idx", "user_id"),
    )


class FilterRequest(Base):
    __tablename__ = "filter_request"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"), primary_key=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_total: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="filter_requests")
    destination: Mapped["Destination"] = relationship("Destination", back_populates="filter_requests")

    __table_args__ = (
        CheckConstraint("pages_fetched <= pages_total"),
        CheckConstraint("pages_fetched >= 0"),
        CheckConstraint("pages_total >= 0"),
        Index("filter_request_user_id_idx", "user_id"),
    )


class Bnb(Base):
    __tablename__ = "bnbs"

    airbnb_id: Mapped[str] = mapped_column(Text, primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False)
    destination_id: Mapped[int] = mapped_column(Integer, ForeignKey("destinations.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price_per_night: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bnb_rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    bnb_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    main_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    min_bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    property_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="bnbs")
    destination: Mapped["Destination"] = relationship("Destination", back_populates="bnbs")
    images: Mapped[List["BnbImage"]] = relationship("BnbImage", back_populates="bnb")
    amenities: Mapped[List["BnbAmenity"]] = relationship("BnbAmenity", back_populates="bnb")
    votes: Mapped[List["Vote"]] = relationship("Vote", back_populates="bnb")
    queue_entries: Mapped[List["BnbQueue"]] = relationship("BnbQueue", back_populates="bnb")

    __table_args__ = (
        CheckConstraint("bnb_rating >= 0 AND bnb_rating <= 5 OR bnb_rating IS NULL"),
        CheckConstraint("price_per_night >= 0"),
        CheckConstraint("bnb_review_count >= 0"),
        CheckConstraint("min_bedrooms >= 0 OR min_bedrooms IS NULL"),
        CheckConstraint("min_beds >= 0 OR min_beds IS NULL"),
        CheckConstraint("min_bathrooms >= 0 OR min_bathrooms IS NULL"),
        Index("bnbs_group_id_idx", "group_id"),
        Index("bnbs_group_id_airbnb_id_idx", "group_id", "airbnb_id"),
        Index("bnbs_group_id_price_per_night_idx", "group_id", "price_per_night"),
    )


class BnbAmenity(Base):
    __tablename__ = "bnb_amenities"

    airbnb_id: Mapped[str] = mapped_column(Text, ForeignKey("bnbs.airbnb_id"), primary_key=True)
    amenity_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Relationships
    bnb: Mapped["Bnb"] = relationship("Bnb", back_populates="amenities")


class BnbImage(Base):
    __tablename__ = "bnb_images"

    airbnb_id: Mapped[str] = mapped_column(Text, ForeignKey("bnbs.airbnb_id"), primary_key=True)
    image_url: Mapped[str] = mapped_column(Text, primary_key=True)

    # Relationships
    bnb: Mapped["Bnb"] = relationship("Bnb", back_populates="images")


class Vote(Base):
    __tablename__ = "votes"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    airbnb_id: Mapped[str] = mapped_column(Text, ForeignKey("bnbs.airbnb_id"), primary_key=True)
    vote: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="votes")
    bnb: Mapped["Bnb"] = relationship("Bnb", back_populates="votes")

    __table_args__ = (
        CheckConstraint("vote >= 0 AND vote <= 3"),
        Index("votes_airbnb_id_idx", "airbnb_id"),
    )


class BnbQueue(Base):
    __tablename__ = "bnb_queue"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    airbnb_id: Mapped[str] = mapped_column(Text, ForeignKey("bnbs.airbnb_id"), primary_key=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bnb_queue")
    bnb: Mapped["Bnb"] = relationship("Bnb", back_populates="queue_entries")

    __table_args__ = (
        Index("bnb_queue_user_id_queued_at_idx", "user_id", "queued_at"),
    )


