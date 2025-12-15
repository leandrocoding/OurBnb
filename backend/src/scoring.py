"""Scoring system for ranking Airbnb listings."""

from dataclasses import dataclass
from typing import List, Optional
from db import get_cursor


# Scoring weights (shared by leaderboard and recommendations)
WEIGHT_FILTER_MATCH = 10
WEIGHT_OWN_FILTER_BONUS = 40  # Extra points for matching own filters (recommendations only)
WEIGHT_VOTE_VETO = -500
WEIGHT_VOTE_OK = 10
WEIGHT_VOTE_LOVE = 40
WEIGHT_VOTE_SUPER_LOVE = 60


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
    ok_count: int = 0
    love_count: int = 0
    super_love_count: int = 0
    filter_matches: int = 0
    own_filter_match: bool = False
    score: int = 0


def _fetch_bnb_data(group_id: int, user_id: Optional[int] = None) -> List[dict]:
    """Fetch raw BnB data with votes and filter matches."""
    with get_cursor() as cursor:
        own_filter_select = ""
        own_filter_join = ""
        user_voted_select = ""
        user_voted_join = ""
        
        if user_id is not None:
            own_filter_select = ", CASE WHEN own_fm.user_id IS NOT NULL THEN 1 ELSE 0 END AS own_filter_match"
            own_filter_join = f"""
                LEFT JOIN (
                    SELECT uf.user_id, b2.airbnb_id, b2.group_id
                    FROM bnbs b2
                    JOIN user_filters uf ON uf.user_id = {user_id}
                    WHERE b2.group_id = %s
                      AND (uf.min_price IS NULL OR b2.price_per_night >= uf.min_price)
                      AND (uf.max_price IS NULL OR b2.price_per_night <= uf.max_price)
                      AND (uf.min_bedrooms IS NULL OR b2.min_bedrooms IS NULL OR b2.min_bedrooms >= uf.min_bedrooms)
                      AND (uf.min_beds IS NULL OR b2.min_beds IS NULL OR b2.min_beds >= uf.min_beds)
                      AND (uf.min_bathrooms IS NULL OR b2.min_bathrooms IS NULL OR b2.min_bathrooms >= uf.min_bathrooms)
                      AND (uf.property_type IS NULL OR b2.property_type IS NULL OR b2.property_type = uf.property_type)
                ) own_fm ON own_fm.airbnb_id = b.airbnb_id AND own_fm.group_id = b.group_id
            """
            user_voted_select = ", CASE WHEN uv.user_id IS NOT NULL THEN 1 ELSE 0 END AS user_has_voted"
            user_voted_join = f"""
                LEFT JOIN (
                    SELECT user_id, airbnb_id, group_id FROM votes WHERE user_id = {user_id}
                ) uv ON uv.airbnb_id = b.airbnb_id AND uv.group_id = b.group_id
            """
        
        query = f"""
            WITH vote_counts AS (
                SELECT v.airbnb_id, v.group_id,
                    COUNT(*) FILTER (WHERE v.vote = 0) AS veto_count,
                    COUNT(*) FILTER (WHERE v.vote = 1) AS ok_count,
                    COUNT(*) FILTER (WHERE v.vote = 2) AS love_count,
                    COUNT(*) FILTER (WHERE v.vote = 3) AS super_love_count
                FROM votes v WHERE v.group_id = %s
                GROUP BY v.airbnb_id, v.group_id
            ),
            filter_matches AS (
                SELECT b.airbnb_id, b.group_id, COUNT(uf.user_id) AS match_count
                FROM bnbs b
                LEFT JOIN users u ON u.group_id = b.group_id
                LEFT JOIN user_filters uf ON uf.user_id = u.id
                    AND (uf.min_price IS NULL OR b.price_per_night >= uf.min_price)
                    AND (uf.max_price IS NULL OR b.price_per_night <= uf.max_price)
                    AND (uf.min_bedrooms IS NULL OR b.min_bedrooms IS NULL OR b.min_bedrooms >= uf.min_bedrooms)
                    AND (uf.min_beds IS NULL OR b.min_beds IS NULL OR b.min_beds >= uf.min_beds)
                    AND (uf.min_bathrooms IS NULL OR b.min_bathrooms IS NULL OR b.min_bathrooms >= uf.min_bathrooms)
                    AND (uf.property_type IS NULL OR b.property_type IS NULL OR b.property_type = uf.property_type)
                WHERE b.group_id = %s
                GROUP BY b.airbnb_id, b.group_id
            )
            SELECT b.airbnb_id, b.group_id, b.destination_id, d.location_name, b.title,
                b.price_per_night, b.bnb_rating, b.bnb_review_count, b.main_image_url,
                b.min_bedrooms, b.min_beds, b.min_bathrooms, b.property_type,
                COALESCE(vc.veto_count, 0) AS veto_count,
                COALESCE(vc.ok_count, 0) AS ok_count,
                COALESCE(vc.love_count, 0) AS love_count,
                COALESCE(vc.super_love_count, 0) AS super_love_count,
                COALESCE(fm.match_count, 0) AS filter_matches
                {own_filter_select}
                {user_voted_select}
            FROM bnbs b
            LEFT JOIN destinations d ON d.id = b.destination_id
            LEFT JOIN vote_counts vc ON vc.airbnb_id = b.airbnb_id AND vc.group_id = b.group_id
            LEFT JOIN filter_matches fm ON fm.airbnb_id = b.airbnb_id AND fm.group_id = b.group_id
            {own_filter_join}
            {user_voted_join}
            WHERE b.group_id = %s
        """
        
        params = (group_id, group_id, group_id, group_id) if user_id else (group_id, group_id, group_id)
        cursor.execute(query, params)
        return cursor.fetchall()


def _calculate_base_score(row: dict) -> int:
    """Calculate base score from votes and filter matches."""
    return (
        row["filter_matches"] * WEIGHT_FILTER_MATCH +
        row["veto_count"] * WEIGHT_VOTE_VETO +
        row["ok_count"] * WEIGHT_VOTE_OK +
        row["love_count"] * WEIGHT_VOTE_LOVE +
        row["super_love_count"] * WEIGHT_VOTE_SUPER_LOVE
    )


def _row_to_scored_bnb(row: dict, score: int, own_match: bool = False) -> ScoredBnb:
    """Convert a database row to a ScoredBnb."""
    return ScoredBnb(
        airbnb_id=row["airbnb_id"],
        group_id=row["group_id"],
        destination_id=row["destination_id"],
        location_name=row["location_name"],
        title=row["title"] or "Untitled",
        price_per_night=row["price_per_night"] or 0,
        bnb_rating=float(row["bnb_rating"]) if row["bnb_rating"] else None,
        bnb_review_count=row["bnb_review_count"] or 0,
        main_image_url=row["main_image_url"],
        min_bedrooms=row["min_bedrooms"],
        min_beds=row["min_beds"],
        min_bathrooms=row["min_bathrooms"],
        property_type=row["property_type"],
        veto_count=row["veto_count"],
        ok_count=row["ok_count"],
        love_count=row["love_count"],
        super_love_count=row["super_love_count"],
        filter_matches=row["filter_matches"],
        own_filter_match=own_match,
        score=score,
    )


def get_leaderboard_scores(group_id: int, limit: Optional[int] = None) -> List[ScoredBnb]:
    """Get all BnBs scored for leaderboard (group consensus)."""
    rows = _fetch_bnb_data(group_id)
    scored = [_row_to_scored_bnb(row, _calculate_base_score(row)) for row in rows]
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:limit] if limit else scored


def get_recommendation_scores(group_id: int, user_id: int, limit: Optional[int] = None) -> List[ScoredBnb]:
    """Get unvoted BnBs scored for recommendations (personalized with own filter bonus)."""
    rows = _fetch_bnb_data(group_id, user_id=user_id)
    unvoted = [r for r in rows if not r.get("user_has_voted", 0)]
    
    scored = []
    for row in unvoted:
        own_match = bool(row.get("own_filter_match", 0))
        score = _calculate_base_score(row) + (WEIGHT_OWN_FILTER_BONUS if own_match else 0)
        scored.append(_row_to_scored_bnb(row, score, own_match))
    
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:limit] if limit else scored
