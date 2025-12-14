"""
BnbScorer - Scoring system for ranking Airbnb listings.

Scores all bnbs in a group using the same formula. The difference between
leaderboard and recommendations is just filtering (exclude voted for recommendations).
"""

from dataclasses import dataclass
from typing import List, Optional

from db import get_cursor


# =============================================================================
# SCORING WEIGHTS
# =============================================================================
# These were previously stored in the scoring_config table.
# Now managed as Python constants for simplicity and testability.

SCORE_FILTER_MATCH = 10      # Points for each user filter the listing matches
SCORE_VOTE_VETO = -500       # Points for a veto vote (vote=0)
SCORE_VOTE_OK = 10           # Points for an ok vote (vote=1)
SCORE_VOTE_LOVE = 40         # Points for a love vote (vote=2)
SCORE_VOTE_SUPER_LOVE = 60   # Points for a super love vote (vote=3)


@dataclass
class ScoredBnb:
    """A bnb with its calculated score and vote breakdown."""
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
    # Vote counts
    veto_count: int = 0
    ok_count: int = 0
    love_count: int = 0
    super_love_count: int = 0
    # Filter match count
    filter_matches: int = 0
    # Calculated score
    score: int = 0


class BnbScorer:
    """
    Scores all bnbs in a group using a unified scoring formula.
    
    The scoring formula considers:
    - Vote counts (veto, ok, love, super love) with configurable weights
    - Filter matches (how many users' filters the bnb matches)
    
    Usage:
        scorer = BnbScorer()
        
        # For leaderboard (all bnbs)
        all_scored = scorer.get_scored_bnbs(group_id)
        top_20 = all_scored[:20]
        
        # For recommendations (exclude user's voted bnbs)
        unvoted = scorer.get_scored_bnbs(group_id, exclude_voted_by_user_id=user_id)
        next_20 = unvoted[:20]
    """
    
    def get_scored_bnbs(
        self,
        group_id: int,
        exclude_voted_by_user_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[ScoredBnb]:
        """
        Fetch and score all bnbs for a group.
        
        Args:
            group_id: The group to fetch bnbs for
            exclude_voted_by_user_id: If provided, exclude bnbs this user has voted on
            limit: If provided, limit the number of results
            
        Returns:
            List of ScoredBnb objects sorted by score descending
        """
        with get_cursor() as cursor:
            # Build the query
            # We need: bnb data, vote counts, filter match counts
            
            exclude_clause = ""
            params = [group_id]
            
            if exclude_voted_by_user_id is not None:
                exclude_clause = """
                    AND NOT EXISTS (
                        SELECT 1 FROM votes v 
                        WHERE v.airbnb_id = b.airbnb_id 
                          AND v.group_id = b.group_id 
                          AND v.user_id = %s
                    )
                """
                params.append(exclude_voted_by_user_id)
            
            query = f"""
                WITH 
                -- Aggregate votes per bnb
                vote_counts AS (
                    SELECT
                        v.airbnb_id,
                        v.group_id,
                        COUNT(*) FILTER (WHERE v.vote = 0) AS veto_count,
                        COUNT(*) FILTER (WHERE v.vote = 1) AS ok_count,
                        COUNT(*) FILTER (WHERE v.vote = 2) AS love_count,
                        COUNT(*) FILTER (WHERE v.vote = 3) AS super_love_count
                    FROM votes v
                    WHERE v.group_id = %s
                    GROUP BY v.airbnb_id, v.group_id
                ),
                -- Count how many users' filters each bnb matches
                filter_matches AS (
                    SELECT 
                        b.airbnb_id,
                        b.group_id,
                        COUNT(uf.user_id) AS match_count
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
                SELECT
                    b.airbnb_id,
                    b.group_id,
                    b.destination_id,
                    d.location_name,
                    b.title,
                    b.price_per_night,
                    b.bnb_rating,
                    b.bnb_review_count,
                    b.main_image_url,
                    b.min_bedrooms,
                    b.min_beds,
                    b.min_bathrooms,
                    b.property_type,
                    COALESCE(vc.veto_count, 0) AS veto_count,
                    COALESCE(vc.ok_count, 0) AS ok_count,
                    COALESCE(vc.love_count, 0) AS love_count,
                    COALESCE(vc.super_love_count, 0) AS super_love_count,
                    COALESCE(fm.match_count, 0) AS filter_matches
                FROM bnbs b
                LEFT JOIN destinations d ON d.id = b.destination_id
                LEFT JOIN vote_counts vc ON vc.airbnb_id = b.airbnb_id AND vc.group_id = b.group_id
                LEFT JOIN filter_matches fm ON fm.airbnb_id = b.airbnb_id AND fm.group_id = b.group_id
                WHERE b.group_id = %s
                {exclude_clause}
                ORDER BY b.airbnb_id
            """
            
            # Build params: group_id for vote_counts, group_id for filter_matches, group_id for main WHERE
            query_params = [group_id, group_id, group_id]
            if exclude_voted_by_user_id is not None:
                query_params.append(exclude_voted_by_user_id)
            
            cursor.execute(query, tuple(query_params))
            rows = cursor.fetchall()
        
        # Calculate scores in Python
        scored_bnbs = []
        for row in rows:
            score = self._calculate_score(
                filter_matches=row["filter_matches"],
                veto_count=row["veto_count"],
                ok_count=row["ok_count"],
                love_count=row["love_count"],
                super_love_count=row["super_love_count"],
            )
            
            scored_bnbs.append(ScoredBnb(
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
                score=score,
            ))
        
        # Sort by score descending
        scored_bnbs.sort(key=lambda x: x.score, reverse=True)
        
        # Apply limit if specified
        if limit is not None:
            scored_bnbs = scored_bnbs[:limit]
        
        return scored_bnbs
    
    def _calculate_score(
        self,
        filter_matches: int,
        veto_count: int,
        ok_count: int,
        love_count: int,
        super_love_count: int,
    ) -> int:
        """Calculate the score for a bnb based on votes and filter matches."""
        return (
            filter_matches * SCORE_FILTER_MATCH +
            veto_count * SCORE_VOTE_VETO +
            ok_count * SCORE_VOTE_OK +
            love_count * SCORE_VOTE_LOVE +
            super_love_count * SCORE_VOTE_SUPER_LOVE
        )


# Singleton instance for convenience
bnb_scorer = BnbScorer()
