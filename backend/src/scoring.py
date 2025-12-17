"""Scoring system for ranking Airbnb listings."""

from dataclasses import dataclass
from typing import List, Optional
from db import get_cursor


@dataclass
class ScoredBnb:
    airbnb_id: str
    group_id: int
    destination_id: int
    location_name: Optional[str]
    title: str
    price_per_night: int
    bnb_rating: Optional[float]
    bnb_review_count: int
    main_image_url: Optional[str]
    min_bedrooms: Optional[int]
    min_beds: Optional[int]
    min_bathrooms: Optional[int]
    property_type: Optional[str]
    veto_count: int = 0
    dislike_count: int = 0
    like_count: int = 0
    super_like_count: int = 0
    filter_matches: int = 0
    own_filter_match: bool = False
    score: int = 0


# =============================================================================
# LEADERBOARD SCORING
# =============================================================================

def _leaderboard_filter_score(bnb: dict, user_filter: dict) -> float:
    price_score = 0.0
    if user_filter["max_price"]and user_filter["max_price"] > 0:
        price_per_night = bnb["price_per_night"]
        price_score = min(0, 40 * (user_filter["max_price"] - price_per_night) / user_filter["max_price"])

    attr_checks = [
        ("min_bedrooms", lambda uf, b: b["min_bedrooms"] is None or uf["min_bedrooms"] is None or b["min_bedrooms"] >= uf["min_bedrooms"]),
        ("min_beds", lambda uf, b: b["min_beds"] is None or uf["min_beds"] is None or b["min_beds"] >= uf["min_beds"]),
        ("min_bathrooms", lambda uf, b: b["min_bathrooms"] is None or uf["min_bathrooms"] is None or b["min_bathrooms"] >= uf["min_bathrooms"]),
        ("property_type", lambda uf, b: b["property_type"] is None or uf["property_type"] is None or b["property_type"] == uf["property_type"]),
    ]
    num_selected = sum(1 for attr, _ in attr_checks if user_filter[attr] is not None)

    attributes_score = 0.0
    if num_selected > 0:
        num_fulfilled = sum(1 for attr, check in attr_checks if user_filter[attr] is not None and check(user_filter, bnb))
        attributes_score = min(4 + num_selected, 10) * (num_fulfilled / num_selected)

    return max(-15, min(15, 5 + price_score + attributes_score))


def _leaderboard_vote_score(vote: Optional[int]) -> int:
    if vote is None:
        return 0
    return {1: -10, 2: 15, 3: 25}.get(vote, 0)


def _fetch_leaderboard_data(group_id: int) -> tuple[List[dict], List[dict], List[dict]]:
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT b.airbnb_id, b.group_id, b.destination_id, d.location_name, b.title,
                b.price_per_night, b.bnb_rating, b.bnb_review_count, b.main_image_url,
                b.min_bedrooms, b.min_beds, b.min_bathrooms, b.property_type
            FROM bnbs b
            LEFT JOIN destinations d ON d.id = b.destination_id
            WHERE b.group_id = %s
              AND NOT EXISTS (
                  SELECT 1 FROM votes v 
                  WHERE v.airbnb_id = b.airbnb_id AND v.group_id = b.group_id AND v.vote = 0
              )
        """, (group_id,))
        bnbs = cursor.fetchall()

        cursor.execute("""
            SELECT u.id AS user_id, uf.max_price, uf.min_bedrooms, uf.min_beds, 
                   uf.min_bathrooms, uf.property_type
            FROM users u
            LEFT JOIN user_filters uf ON uf.user_id = u.id
            WHERE u.group_id = %s
        """, (group_id,))
        user_filters = cursor.fetchall()

        cursor.execute("""
            SELECT user_id, airbnb_id, vote FROM votes WHERE group_id = %s
        """, (group_id,))
        votes = cursor.fetchall()

        return bnbs, user_filters, votes


def get_leaderboard_scores(group_id: int, limit: Optional[int] = None) -> List[ScoredBnb]:
    bnbs, user_filters, votes = _fetch_leaderboard_data(group_id)

    vote_lookup = {(v["user_id"], v["airbnb_id"]): v["vote"] for v in votes}

    vote_counts = {}
    for v in votes:
        key = v["airbnb_id"]
        if key not in vote_counts:
            vote_counts[key] = {"veto": 0, "dislike": 0, "like": 0, "super_like": 0}
        vote_type = {0: "veto", 1: "dislike", 2: "like", 3: "super_like"}.get(v["vote"])
        if vote_type:
            vote_counts[key][vote_type] += 1

    scored_bnbs = []
    for bnb in bnbs:
        total_score = 0.0
        filter_matches = 0
        for uf in user_filters:
            user_filter = {
                "min_price": None,  # leaderboard doesn't use min_price penalty
                "max_price": uf["max_price"],
                "min_bedrooms": uf["min_bedrooms"],
                "min_beds": uf["min_beds"],
                "min_bathrooms": uf["min_bathrooms"],
                "property_type": uf["property_type"],
            }
            total_score += _leaderboard_filter_score(bnb, user_filter)
            total_score += _leaderboard_vote_score(vote_lookup.get((uf["user_id"], bnb["airbnb_id"])))
            # Count how many users' filters this bnb matches
            if _check_filter_match(bnb, user_filter):
                filter_matches += 1

        bnb_votes = vote_counts.get(bnb["airbnb_id"], {"veto": 0, "dislike": 0, "like": 0, "super_like": 0})
        scored_bnbs.append(ScoredBnb(
            airbnb_id=bnb["airbnb_id"],
            group_id=bnb["group_id"],
            destination_id=bnb["destination_id"],
            location_name=bnb["location_name"],
            title=bnb["title"] or "Untitled",
            price_per_night=bnb["price_per_night"],
            bnb_rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
            bnb_review_count=bnb["bnb_review_count"] or 0,
            main_image_url=bnb["main_image_url"],
            min_bedrooms=bnb["min_bedrooms"],
            min_beds=bnb["min_beds"],
            min_bathrooms=bnb["min_bathrooms"],
            property_type=bnb["property_type"],
            veto_count=bnb_votes["veto"],
            dislike_count=bnb_votes["dislike"],
            like_count=bnb_votes["like"],
            super_like_count=bnb_votes["super_like"],
            filter_matches=filter_matches,
            score=round(total_score),
        ))

    scored_bnbs.sort(key=lambda x: x.score, reverse=True)
    return scored_bnbs[:limit] if limit else scored_bnbs


# =============================================================================
# RECOMMENDATION SCORING
# =============================================================================

def _recommendation_filter_score(bnb: dict, user_filter: dict) -> float:
    price_per_night = bnb["price_per_night"]

    max_price_score = 0.0
    if user_filter["max_price"] and user_filter["max_price"] > 0:
        max_price_score = min(0, 60 * (user_filter["max_price"] - price_per_night) / user_filter["max_price"])

    min_price_score = 0.0
    if user_filter["min_price"] and user_filter["min_price"] > 0:
        min_price_score = min(0, 20 * (price_per_night - user_filter["min_price"]) / user_filter["min_price"])

    price_score = min(max_price_score, min_price_score)

    attr_checks = [
        ("min_bedrooms", lambda uf, b: b["min_bedrooms"] is None or uf["min_bedrooms"] is None or b["min_bedrooms"] >= uf["min_bedrooms"]),
        ("min_beds", lambda uf, b: b["min_beds"] is None or uf["min_beds"] is None or b["min_beds"] >= uf["min_beds"]),
        ("min_bathrooms", lambda uf, b: b["min_bathrooms"] is None or uf["min_bathrooms"] is None or b["min_bathrooms"] >= uf["min_bathrooms"]),
        ("property_type", lambda uf, b: b["property_type"] is None or uf["property_type"] is None or b["property_type"] == uf["property_type"]),
    ]
    num_selected = sum(1 for attr, _ in attr_checks if user_filter[attr] is not None)

    attributes_score = 0.0
    if num_selected > 0:
        num_fulfilled = sum(1 for attr, check in attr_checks if user_filter[attr] is not None and check(user_filter, bnb))
        attributes_score = (num_fulfilled / num_selected) * 30

    return price_score + attributes_score


def _recommendation_votes_score(num_likes: int, num_super_likes: int, num_dislikes: int, num_other_users: int) -> float:
    if num_other_users <= 0:
        return 0.0
    raw_score = 5 * num_likes + 8 * num_super_likes - 5 * num_dislikes
    normalized_score = 20 * (num_likes + num_super_likes - num_dislikes) / num_other_users
    return max(raw_score, normalized_score)


def _check_filter_match(bnb: dict, user_filter: dict) -> bool:
    price = bnb["price_per_night"]
    if user_filter["min_price"] is not None and price < user_filter["min_price"]:
        return False
    if user_filter["max_price"] is not None and price > user_filter["max_price"]:
        return False
    if user_filter["min_bedrooms"] is not None and bnb["min_bedrooms"] is not None:
        if bnb["min_bedrooms"] < user_filter["min_bedrooms"]:
            return False
    if user_filter["min_beds"] is not None and bnb["min_beds"] is not None:
        if bnb["min_beds"] < user_filter["min_beds"]:
            return False
    if user_filter["min_bathrooms"] is not None and bnb["min_bathrooms"] is not None:
        if bnb["min_bathrooms"] < user_filter["min_bathrooms"]:
            return False
    if user_filter["property_type"] is not None and bnb["property_type"] is not None:
        if bnb["property_type"] != user_filter["property_type"]:
            return False
    return True


def _fetch_recommendation_data(group_id: int, user_id: int) -> tuple[List[dict], dict, List[dict], int]:
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT b.airbnb_id, b.group_id, b.destination_id, d.location_name, b.title,
                b.price_per_night, b.bnb_rating, b.bnb_review_count, b.main_image_url,
                b.min_bedrooms, b.min_beds, b.min_bathrooms, b.property_type
            FROM bnbs b
            LEFT JOIN destinations d ON d.id = b.destination_id
            WHERE b.group_id = %s
              AND NOT EXISTS (
                  SELECT 1 FROM votes v 
                  WHERE v.airbnb_id = b.airbnb_id AND v.group_id = b.group_id AND v.vote = 0
              )
              AND NOT EXISTS (
                  SELECT 1 FROM votes v 
                  WHERE v.airbnb_id = b.airbnb_id AND v.group_id = b.group_id AND v.user_id = %s
              )
        """, (group_id, user_id))
        bnbs = cursor.fetchall()

        cursor.execute("""
            SELECT min_price, max_price, min_bedrooms, min_beds, min_bathrooms, property_type
            FROM user_filters WHERE user_id = %s
        """, (user_id,))
        row = cursor.fetchone()
        user_filter = {
            "min_price": row["min_price"] if row else None,
            "max_price": row["max_price"] if row else None,
            "min_bedrooms": row["min_bedrooms"] if row else None,
            "min_beds": row["min_beds"] if row else None,
            "min_bathrooms": row["min_bathrooms"] if row else None,
            "property_type": row["property_type"] if row else None,
        }

        cursor.execute("""
            SELECT user_id, airbnb_id, vote FROM votes WHERE group_id = %s AND user_id != %s
        """, (group_id, user_id))
        other_votes = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS count FROM users WHERE group_id = %s", (group_id,))
        num_other_users = cursor.fetchone()["count"] - 1

        return bnbs, user_filter, other_votes, num_other_users


def get_recommendation_scores(group_id: int, user_id: int, limit: Optional[int] = None) -> List[ScoredBnb]:
    bnbs, user_filter, other_votes, num_other_users = _fetch_recommendation_data(group_id, user_id)

    vote_counts = {}
    for v in other_votes:
        key = v["airbnb_id"]
        if key not in vote_counts:
            vote_counts[key] = {"dislike": 0, "like": 0, "super_like": 0}
        vote_type = {1: "dislike", 2: "like", 3: "super_like"}.get(v["vote"])
        if vote_type:
            vote_counts[key][vote_type] += 1

    scored_bnbs = []
    for bnb in bnbs:
        filter_score = _recommendation_filter_score(bnb, user_filter)
        bnb_votes = vote_counts.get(bnb["airbnb_id"], {"dislike": 0, "like": 0, "super_like": 0})
        votes_score = _recommendation_votes_score(
            bnb_votes["like"], bnb_votes["super_like"], bnb_votes["dislike"], num_other_users
        )

        scored_bnbs.append(ScoredBnb(
            airbnb_id=bnb["airbnb_id"],
            group_id=bnb["group_id"],
            destination_id=bnb["destination_id"],
            location_name=bnb["location_name"],
            title=bnb["title"] or "Untitled",
            price_per_night=bnb["price_per_night"],
            bnb_rating=float(bnb["bnb_rating"]) if bnb["bnb_rating"] else None,
            bnb_review_count=bnb["bnb_review_count"] or 0,
            main_image_url=bnb["main_image_url"],
            min_bedrooms=bnb["min_bedrooms"],
            min_beds=bnb["min_beds"],
            min_bathrooms=bnb["min_bathrooms"],
            property_type=bnb["property_type"],
            dislike_count=bnb_votes["dislike"],
            like_count=bnb_votes["like"],
            super_like_count=bnb_votes["super_like"],
            own_filter_match=_check_filter_match(bnb, user_filter),
            score=round(filter_score + votes_score),
        ))

    scored_bnbs.sort(key=lambda x: x.score, reverse=True)
    return scored_bnbs[:limit] if limit else scored_bnbs
