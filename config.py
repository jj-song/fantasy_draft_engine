"""
Configuration settings for the Fantasy Football AI Draft Tool.
"""

# Data acquisition settings
DATA_START_YEAR = 2010     # First season to fetch data for
DATA_END_YEAR = 2024       # Last season to fetch data for (inclusive)

# Hybrid training vs inference settings
TRAINING_DATA_END_YEAR = 2023    # Use up to 2023 for model training (complete seasons)
INFERENCE_DATA_YEAR = 2024       # Use 2024 for current predictions and team assignments
CURRENT_SEASON = 2025           # Season we're projecting for

# Player positions to include in analysis
# Note: K and DST have limited historical data in nfl_data_py
POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K']  # DST handled separately
CORE_POSITIONS = ['QB', 'RB', 'WR', 'TE']  # Positions with full feature engineering

# File paths
RAW_DATA_DIR = 'data/raw'
PROCESSED_DATA_DIR = 'data/processed'

# League settings
LEAGUE_SIZE = 12
PPR_SCORING = 0.5  # Half-point PPR

# Value Over Replacement (VOR) settings
# Replacement levels based on starter requirements in a 12-team league
VOR_REPLACEMENT_LEVELS = {
    'QB': 13,   # QB13 (12 teams × 1 starter = 12, plus bench depth)
    'RB': 30,   # RB30 (12 teams × 2.5 starters = 30, accounting for FLEX usage)  
    'WR': 30,   # WR30 (12 teams × 2.5 starters = 30, accounting for FLEX usage)
    'TE': 13,   # TE13 (12 teams × 1 starter = 12, plus minimal FLEX usage)
    'K': 12,    # K12 (12 teams × 1 starter = 12)
    'DST': 12,  # DST12 (12 teams × 1 starter = 12)
}

# Positional scarcity multipliers based on fantasy football research
# These account for starter requirements, injury risk, and positional depth
VOR_SCARCITY_MULTIPLIERS = {
    'RB': 1.5,   # Highest scarcity: injury risk, limited elite tier, need multiple starters
    'TE': 1.4,   # Very top-heavy position, huge advantage for elite TEs over replacement
    'WR': 1.2,   # Moderate scarcity: need multiple starters, but deeper talent pool  
    'QB': 0.9,   # Lowest scarcity: deepest position, most predictable, only need 1 starter
    'K': 0.8,    # Very replaceable position
    'DST': 0.8,  # Very replaceable position
}

# League format settings that affect VOR calculations
VOR_LEAGUE_SETTINGS = {
    'team_count': 12,          # Number of teams in league
    'qb_starters': 1,          # QBs started per team per week
    'rb_starters': 2,          # RBs started per team per week  
    'wr_starters': 2,          # WRs started per team per week
    'te_starters': 1,          # TEs started per team per week
    'flex_spots': 1,           # FLEX positions (RB/WR/TE)
    'superflex': False,        # Whether league has superflex (QB eligible for FLEX)
}

# Legacy compatibility (deprecated - use VOR_REPLACEMENT_LEVELS instead)
REPLACEMENT_RANKS = VOR_REPLACEMENT_LEVELS

# Fantasy point calculation settings
FANTASY_POINTS = {
    'passing_yards': 0.04,      # 1 point per 25 yards
    'passing_tds': 4,
    'interceptions': -2,
    'rushing_yards': 0.1,       # 1 point per 10 yards
    'rushing_tds': 6,
    'receptions': 0.5,          # Half-point PPR
    'receiving_yards': 0.1,     # 1 point per 10 yards
    'receiving_tds': 6,
    'fumbles_lost': -2,
    'two_point_conversions': 2,
}

# Rookie projection settings for feature engineering
ROOKIE_BASELINE_FPPG = {
    'QB': {
        1: 15.0,  # 1st round
        2: 12.0,  # 2nd round
        3: 10.0,  # 3rd round
        4: 8.0,   # 4th round
        5: 7.0,   # 5th round
        6: 6.0,   # 6th round
        7: 5.0,   # 7th round
        'UDFA': 3.0,  # Undrafted free agent
    },
    'RB': {
        1: 12.0,  # 1st round
        2: 9.0,   # 2nd round
        3: 7.0,   # 3rd round
        4: 5.0,   # 4th round
        5: 4.0,   # 5th round
        6: 3.5,   # 6th round
        7: 3.0,   # 7th round
        'UDFA': 2.0,  # Undrafted free agent
    },
    'WR': {
        1: 11.0,  # 1st round
        2: 8.0,   # 2nd round
        3: 6.0,   # 3rd round
        4: 4.5,   # 4th round
        5: 3.5,   # 5th round
        6: 3.0,   # 6th round
        7: 2.5,   # 7th round
        'UDFA': 1.5,  # Undrafted free agent
    },
    'TE': {
        1: 9.0,   # 1st round
        2: 7.0,   # 2nd round
        3: 5.0,   # 3rd round
        4: 4.0,   # 4th round
        5: 3.0,   # 5th round
        6: 2.0,   # 6th round
        7: 1.5,   # 7th round
        'UDFA': 1.0,  # Undrafted free agent
    },
}

# Baseline FPPG for players with minimal recent NFL data
MINIMAL_DATA_BASELINE_FPPG = {
    'QB': 5.0,
    'RB': 3.0,
    'WR': 2.5,
    'TE': 1.5,
    'K': 8.0,    # Kickers are more consistent
    'DST': 6.0,  # Defenses have moderate baseline
}

# Minimum games threshold for considering a player to have sufficient data
MIN_GAMES_THRESHOLD = 4

# Model ensemble weights
MODEL_WEIGHTS = {
    'lightgbm': 0.5,
    'random_forest': 0.5,
}

# Default scoring system to use for target variable calculation
DEFAULT_SCORING_SYSTEM = 'HalfPPR' # Options: 'PPR', 'HalfPPR', 'Standard'

# Mapping of scoring system names to actual column names in the raw data
# 'fantasy_points' is calculated based on FANTASY_POINTS settings in this config
# 'fantasy_points_ppr' is the default full PPR column from nfl_data_py
FANTASY_POINTS_COLUMNS = {
    'PPR': 'fantasy_points_ppr',
    'HalfPPR': 'fantasy_points',    # Uses the 'fantasy_points' col which is based on current FANTASY_POINTS settings
    'Standard': 'fantasy_points', # Assumes FANTASY_POINTS would be set to standard (e.g., receptions: 0) if this is chosen
}

# Target variable name for model training
TARGET_VARIABLE = 'next_season_fppg'

