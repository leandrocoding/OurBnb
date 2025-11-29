PAGE_COUNT_AFTER_FILTER_SET = 4

# Number of listings to return in leaderboard
LEADERBOARD_LIMIT = 20

# =============================================================================
# LEADERBOARD SCORING CONFIGURATION
# =============================================================================
# Scoring values are now stored in the database 'scoring_config' table.
# This allows changing scores without code deployment.
# 
# To update scoring values, run SQL like:
#   UPDATE scoring_config SET value = 50 WHERE key = 'vote_love';
#
# Default values (set in init.sql):
#   filter_match: 10 points per user filter match
#   vote_veto: -500 points
#   vote_ok: 10 points  
#   vote_love: 40 points
#   vote_super_love: 60 points
