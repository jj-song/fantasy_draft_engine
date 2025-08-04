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

# Model ensemble weights (default - can be overridden by dynamic weighting)
MODEL_WEIGHTS = {
    'lightgbm': 0.5,
    'random_forest': 0.5,
}

# Position-specific optimized hyperparameters
# These are the result of comprehensive hyperparameter optimization
OPTIMIZED_HYPERPARAMETERS = {
    'random_forest': {
        'QB': {
            'n_estimators': 400,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 4,
            'max_features': 'sqrt',
            'bootstrap': True,
            'oob_score': True,
            'random_state': 42,
            'n_jobs': -1
        },
        'RB': {
            'n_estimators': 300,
            'max_depth': 12,
            'min_samples_split': 8,
            'min_samples_leaf': 2,
            'max_features': 0.8,
            'bootstrap': True,
            'oob_score': True,
            'random_state': 42,
            'n_jobs': -1
        },
        'WR': {
            'n_estimators': 400,
            'max_depth': 12,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'bootstrap': True,
            'oob_score': True,
            'random_state': 42,
            'n_jobs': -1
        },
        'TE': {
            'n_estimators': 300,
            'max_depth': 8,
            'min_samples_split': 8,
            'min_samples_leaf': 5,
            'max_features': 'sqrt',
            'bootstrap': True,
            'oob_score': True,
            'random_state': 42,
            'n_jobs': -1
        }
    },
    'lightgbm': {
        'QB': {
            'objective': 'regression_l1',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'n_estimators': 1000,
            'learning_rate': 0.08,
            'num_leaves': 64,
            'max_depth': 8,
            'min_data_in_leaf': 40,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.85,
            'bagging_freq': 1,
            'lambda_l1': 0.1,
            'lambda_l2': 0.2,
            'min_gain_to_split': 0.01,
            'verbose': -1,
            'n_jobs': -1,
            'seed': 42,
            'force_col_wise': True,
        },
        'RB': {
            'objective': 'regression_l1',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'n_estimators': 1000,
            'learning_rate': 0.1,
            'num_leaves': 96,
            'max_depth': 10,
            'min_data_in_leaf': 25,
            'feature_fraction': 0.75,
            'bagging_fraction': 0.8,
            'bagging_freq': 1,
            'lambda_l1': 0.2,
            'lambda_l2': 0.1,
            'min_gain_to_split': 0.02,
            'verbose': -1,
            'n_jobs': -1,
            'seed': 42,
            'force_col_wise': True,
        },
        'WR': {
            'objective': 'regression_l1',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'n_estimators': 1000,
            'learning_rate': 0.08,
            'num_leaves': 96,
            'max_depth': 10,
            'min_data_in_leaf': 30,
            'feature_fraction': 0.7,
            'bagging_fraction': 0.85,
            'bagging_freq': 1,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'min_gain_to_split': 0.01,
            'verbose': -1,
            'n_jobs': -1,
            'seed': 42,
            'force_col_wise': True,
        },
        'TE': {
            'objective': 'regression_l1',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'n_estimators': 800,
            'learning_rate': 0.08,
            'num_leaves': 64,
            'max_depth': 8,
            'min_data_in_leaf': 50,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.9,
            'bagging_freq': 1,
            'lambda_l1': 0.1,
            'lambda_l2': 0.3,
            'min_gain_to_split': 0.02,
            'verbose': -1,
            'n_jobs': -1,
            'seed': 42,
            'force_col_wise': True,
        }
    }
}

# Dynamic ensemble weighting based on player context
# These weights are applied based on player characteristics and performance patterns
DYNAMIC_ENSEMBLE_WEIGHTS = {
    'QB': {
        'veteran_stable': {'random_forest': 0.6, 'lightgbm': 0.4},  # Experienced QBs with consistent patterns
        'young_developing': {'random_forest': 0.4, 'lightgbm': 0.6},  # Young QBs with complex development patterns
        'high_volatility': {'random_forest': 0.5, 'lightgbm': 0.5},  # QBs with inconsistent performance
        'default': {'random_forest': 0.5, 'lightgbm': 0.5}
    },
    'RB': {
        'workhorse': {'random_forest': 0.6, 'lightgbm': 0.4},  # High-volume, consistent usage RBs
        'committee_back': {'random_forest': 0.4, 'lightgbm': 0.6},  # RBs in committee situations
        'pass_catching': {'random_forest': 0.45, 'lightgbm': 0.55},  # Pass-catching specialists
        'goal_line': {'random_forest': 0.65, 'lightgbm': 0.35},  # TD-dependent RBs
        'default': {'random_forest': 0.5, 'lightgbm': 0.5}
    },
    'WR': {
        'target_hog': {'random_forest': 0.55, 'lightgbm': 0.45},  # High target share WRs
        'big_play': {'random_forest': 0.4, 'lightgbm': 0.6},  # Deep threat WRs with volatile performance
        'possession': {'random_forest': 0.6, 'lightgbm': 0.4},  # Reliable possession receivers
        'rookie_developing': {'random_forest': 0.35, 'lightgbm': 0.65},  # Rookies with development potential
        'default': {'random_forest': 0.5, 'lightgbm': 0.5}
    },
    'TE': {
        'elite_tier': {'random_forest': 0.55, 'lightgbm': 0.45},  # Top-tier TEs with consistent usage
        'receiving_specialist': {'random_forest': 0.45, 'lightgbm': 0.55},  # TEs primarily used in passing
        'blocking_hybrid': {'random_forest': 0.6, 'lightgbm': 0.4},  # TEs with significant blocking duties
        'matchup_dependent': {'random_forest': 0.4, 'lightgbm': 0.6},  # TEs with volatile weekly usage
        'default': {'random_forest': 0.5, 'lightgbm': 0.5}
    }
}

# Player archetype classification thresholds
# Used to determine which dynamic ensemble weights to apply
PLAYER_ARCHETYPE_THRESHOLDS = {
    'QB': {
        'veteran_stable': {'min_experience': 3, 'max_cv_fppg': 0.3},
        'young_developing': {'max_experience': 2, 'min_games': 8},
        'high_volatility': {'min_cv_fppg': 0.4}
    },
    'RB': {
        'workhorse': {'min_carries_per_game': 15, 'min_touch_share': 0.6},
        'committee_back': {'max_carries_per_game': 12, 'max_touch_share': 0.45},
        'pass_catching': {'min_targets_per_game': 4, 'min_target_share': 0.1},
        'goal_line': {'min_red_zone_carries': 3, 'max_carries_per_game': 10}
    },
    'WR': {
        'target_hog': {'min_target_share': 0.25, 'min_targets_per_game': 8},
        'big_play': {'min_adot': 12, 'min_yards_per_target': 8},
        'possession': {'max_adot': 8, 'min_catch_rate': 0.7},
        'rookie_developing': {'max_experience': 1, 'min_draft_round': 1, 'max_draft_round': 3}
    },
    'TE': {
        'elite_tier': {'min_target_share': 0.15, 'min_targets_per_game': 6},
        'receiving_specialist': {'min_routes_per_snap': 0.7, 'max_blocking_snaps': 0.3},
        'blocking_hybrid': {'min_blocking_snaps': 0.4, 'max_targets_per_game': 4},
        'matchup_dependent': {'min_cv_targets': 0.5, 'max_target_share': 0.12}
    }
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

