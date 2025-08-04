"""
Configuration settings for the Fantasy Football AI Draft Tool.

BACKWARD COMPATIBILITY LAYER:
This file maintains all existing variable names for backward compatibility
while integrating with the new modular configuration system.
"""

# Import new modular configuration system
try:
    from src.config import get_config
    _config = get_config()
    _has_new_config = True
except ImportError:
    # Fallback for development/testing
    _config = None
    _has_new_config = False

# Data acquisition settings - now sourced from modular config when available
DATA_START_YEAR = _config.get('data.data_start_year', 2010) if _has_new_config else 2010
DATA_END_YEAR = _config.get('data.data_end_year', 2024) if _has_new_config else 2024

# Hybrid training vs inference settings
TRAINING_DATA_END_YEAR = _config.get('data.training_data_end_year', 2023) if _has_new_config else 2023
INFERENCE_DATA_YEAR = _config.get('data.inference_data_year', 2024) if _has_new_config else 2024
CURRENT_SEASON = _config.get('data.current_season', 2025) if _has_new_config else 2025

# Player positions to include in analysis - now sourced from modular config when available
# Note: K and DST have limited historical data in nfl_data_py
POSITIONS = _config.get('data.positions', ['QB', 'RB', 'WR', 'TE', 'K']) if _has_new_config else ['QB', 'RB', 'WR', 'TE', 'K']
CORE_POSITIONS = _config.get('data.core_positions', ['QB', 'RB', 'WR', 'TE']) if _has_new_config else ['QB', 'RB', 'WR', 'TE']

# File paths - now sourced from modular config when available
RAW_DATA_DIR = _config.get('data.raw_data_dir', 'data/raw') if _has_new_config else 'data/raw'
PROCESSED_DATA_DIR = _config.get('data.processed_data_dir', 'data/processed') if _has_new_config else 'data/processed'

# League settings - now sourced from modular config when available
LEAGUE_SIZE = _config.get('league.league_size', 12) if _has_new_config else 12
PPR_SCORING = _config.get('scoring.ppr_scoring', 0.5) if _has_new_config else 0.5

# Value Over Replacement (VOR) settings - now sourced from modular config when available
# Replacement levels based on starter requirements in a 12-team league
# FIXED: Adjusted to properly value RB scarcity and QB replaceability
_default_vor_replacement = {
    'QB': 15,   # Was 13 - QBs are more replaceable, streaming viable
    'RB': 24,   # Was 30 - RBs are scarcer, only 2 per team + flex
    'WR': 36,   # Was 30 - WRs have more depth
    'TE': 12,   # Was 13 - Slight adjustment for elite TE advantage
    'K': 13,    # Was 12 - Kickers are highly replaceable
    'DST': 13   # Was 12 - Defenses are streamable
}
VOR_REPLACEMENT_LEVELS = _config.get('league.vor_replacement_levels', _default_vor_replacement) if _has_new_config else _default_vor_replacement

# Positional scarcity multipliers based on fantasy football research
# These account for starter requirements, injury risk, and positional depth
# FIXED: Increased RB scarcity multiplier to reflect true positional value
_default_scarcity_multipliers = {
    'RB': 1.8,  # Was 1.5 - RBs are most scarce and injury-prone
    'TE': 1.3,  # Was 1.4 - Slight reduction, only elite TEs matter
    'WR': 1.0,  # Was 1.2 - WRs are deep, reduced multiplier
    'QB': 0.7,  # Was 0.9 - QBs highly replaceable in 1QB leagues
    'K': 0.6,   # Was 0.8 - Kickers are nearly worthless
    'DST': 0.6  # Was 0.8 - Defenses are streamable
}
VOR_SCARCITY_MULTIPLIERS = _config.get('league.vor_scarcity_multipliers', _default_scarcity_multipliers) if _has_new_config else _default_scarcity_multipliers

# League format settings that affect VOR calculations
_default_league_settings = {
    'team_count': 12, 'qb_starters': 1, 'rb_starters': 2, 'wr_starters': 2, 
    'te_starters': 1, 'flex_spots': 1, 'superflex': False
}
VOR_LEAGUE_SETTINGS = _config.get('league.vor_league_settings', _default_league_settings) if _has_new_config else _default_league_settings

# Legacy compatibility (deprecated - use VOR_REPLACEMENT_LEVELS instead)
REPLACEMENT_RANKS = VOR_REPLACEMENT_LEVELS

# Fantasy point calculation settings - now sourced from modular config when available
_default_fantasy_points = {
    'passing_yards': 0.04, 'passing_tds': 4, 'interceptions': -2,
    'rushing_yards': 0.1, 'rushing_tds': 6, 'receptions': 0.5,
    'receiving_yards': 0.1, 'receiving_tds': 6, 'fumbles_lost': -2,
    'two_point_conversions': 2
}
FANTASY_POINTS = _config.get('scoring.fantasy_points', _default_fantasy_points) if _has_new_config else _default_fantasy_points

# Rookie projection settings for feature engineering - now sourced from modular config when available
_default_rookie_baseline = {
    'QB': {1: 15.0, 2: 12.0, 3: 10.0, 4: 8.0, 5: 7.0, 6: 6.0, 7: 5.0, 'UDFA': 3.0},
    'RB': {1: 12.0, 2: 9.0, 3: 7.0, 4: 5.0, 5: 4.0, 6: 3.5, 7: 3.0, 'UDFA': 2.0},
    'WR': {1: 11.0, 2: 8.0, 3: 6.0, 4: 4.5, 5: 3.5, 6: 3.0, 7: 2.5, 'UDFA': 1.5},
    'TE': {1: 9.0, 2: 7.0, 3: 5.0, 4: 4.0, 5: 3.0, 6: 2.0, 7: 1.5, 'UDFA': 1.0}
}
ROOKIE_BASELINE_FPPG = _config.get('position.rookie_baseline_fppg', _default_rookie_baseline) if _has_new_config else _default_rookie_baseline

# Baseline FPPG for players with minimal recent NFL data - now sourced from modular config when available
_default_minimal_baseline = {'QB': 5.0, 'RB': 3.0, 'WR': 2.5, 'TE': 1.5, 'K': 8.0, 'DST': 6.0}
MINIMAL_DATA_BASELINE_FPPG = _config.get('position.minimal_data_baseline_fppg', _default_minimal_baseline) if _has_new_config else _default_minimal_baseline

# Minimum games threshold for considering a player to have sufficient data - now sourced from modular config when available
MIN_GAMES_THRESHOLD = _config.get('data.min_games_threshold', 4) if _has_new_config else 4

# Model ensemble weights (default - can be overridden by dynamic weighting) - now sourced from modular config when available
_default_model_weights = {'lightgbm': 0.5, 'random_forest': 0.5}
MODEL_WEIGHTS = _config.get('model.ensemble_weights', _default_model_weights) if _has_new_config else _default_model_weights

# Position-specific optimized hyperparameters - now sourced from modular config when available
# These are the result of comprehensive hyperparameter optimization
_default_hyperparameters = {
    'random_forest': {
        'QB': {'n_estimators': 400, 'max_depth': 10, 'min_samples_split': 5, 'min_samples_leaf': 4, 'max_features': 'sqrt', 'bootstrap': True, 'oob_score': True, 'random_state': 42, 'n_jobs': -1},
        'RB': {'n_estimators': 300, 'max_depth': 12, 'min_samples_split': 8, 'min_samples_leaf': 2, 'max_features': 0.8, 'bootstrap': True, 'oob_score': True, 'random_state': 42, 'n_jobs': -1},
        'WR': {'n_estimators': 400, 'max_depth': 12, 'min_samples_split': 5, 'min_samples_leaf': 2, 'max_features': 'sqrt', 'bootstrap': True, 'oob_score': True, 'random_state': 42, 'n_jobs': -1},
        'TE': {'n_estimators': 300, 'max_depth': 8, 'min_samples_split': 8, 'min_samples_leaf': 5, 'max_features': 'sqrt', 'bootstrap': True, 'oob_score': True, 'random_state': 42, 'n_jobs': -1}
    },
    'lightgbm': {
        'QB': {'objective': 'regression_l1', 'metric': 'rmse', 'boosting_type': 'gbdt', 'n_estimators': 1000, 'learning_rate': 0.08, 'num_leaves': 64, 'max_depth': 8, 'min_data_in_leaf': 40, 'feature_fraction': 0.8, 'bagging_fraction': 0.85, 'bagging_freq': 1, 'lambda_l1': 0.1, 'lambda_l2': 0.2, 'min_gain_to_split': 0.01, 'verbose': -1, 'n_jobs': -1, 'seed': 42, 'force_col_wise': True},
        'RB': {'objective': 'regression_l1', 'metric': 'rmse', 'boosting_type': 'gbdt', 'n_estimators': 1000, 'learning_rate': 0.1, 'num_leaves': 96, 'max_depth': 10, 'min_data_in_leaf': 25, 'feature_fraction': 0.75, 'bagging_fraction': 0.8, 'bagging_freq': 1, 'lambda_l1': 0.2, 'lambda_l2': 0.1, 'min_gain_to_split': 0.02, 'verbose': -1, 'n_jobs': -1, 'seed': 42, 'force_col_wise': True},
        'WR': {'objective': 'regression_l1', 'metric': 'rmse', 'boosting_type': 'gbdt', 'n_estimators': 1000, 'learning_rate': 0.08, 'num_leaves': 96, 'max_depth': 10, 'min_data_in_leaf': 30, 'feature_fraction': 0.7, 'bagging_fraction': 0.85, 'bagging_freq': 1, 'lambda_l1': 0.1, 'lambda_l2': 0.1, 'min_gain_to_split': 0.01, 'verbose': -1, 'n_jobs': -1, 'seed': 42, 'force_col_wise': True},
        'TE': {'objective': 'regression_l1', 'metric': 'rmse', 'boosting_type': 'gbdt', 'n_estimators': 800, 'learning_rate': 0.08, 'num_leaves': 64, 'max_depth': 8, 'min_data_in_leaf': 50, 'feature_fraction': 0.8, 'bagging_fraction': 0.9, 'bagging_freq': 1, 'lambda_l1': 0.1, 'lambda_l2': 0.3, 'min_gain_to_split': 0.02, 'verbose': -1, 'n_jobs': -1, 'seed': 42, 'force_col_wise': True}
    }
}
OPTIMIZED_HYPERPARAMETERS = _config.get('model.hyperparameters', _default_hyperparameters) if _has_new_config else _default_hyperparameters

# Dynamic ensemble weighting based on player context - now sourced from modular config when available
# These weights are applied based on player characteristics and performance patterns
_default_dynamic_weights = {
    'QB': {'veteran_stable': {'random_forest': 0.6, 'lightgbm': 0.4}, 'young_developing': {'random_forest': 0.4, 'lightgbm': 0.6}, 'high_volatility': {'random_forest': 0.5, 'lightgbm': 0.5}, 'default': {'random_forest': 0.5, 'lightgbm': 0.5}},
    'RB': {'workhorse': {'random_forest': 0.6, 'lightgbm': 0.4}, 'committee_back': {'random_forest': 0.4, 'lightgbm': 0.6}, 'pass_catching': {'random_forest': 0.45, 'lightgbm': 0.55}, 'goal_line': {'random_forest': 0.65, 'lightgbm': 0.35}, 'default': {'random_forest': 0.5, 'lightgbm': 0.5}},
    'WR': {'target_hog': {'random_forest': 0.55, 'lightgbm': 0.45}, 'big_play': {'random_forest': 0.4, 'lightgbm': 0.6}, 'possession': {'random_forest': 0.6, 'lightgbm': 0.4}, 'rookie_developing': {'random_forest': 0.35, 'lightgbm': 0.65}, 'default': {'random_forest': 0.5, 'lightgbm': 0.5}},
    'TE': {'elite_tier': {'random_forest': 0.55, 'lightgbm': 0.45}, 'receiving_specialist': {'random_forest': 0.45, 'lightgbm': 0.55}, 'blocking_hybrid': {'random_forest': 0.6, 'lightgbm': 0.4}, 'matchup_dependent': {'random_forest': 0.4, 'lightgbm': 0.6}, 'default': {'random_forest': 0.5, 'lightgbm': 0.5}}
}
DYNAMIC_ENSEMBLE_WEIGHTS = _config.get('model.dynamic_ensemble_weights', _default_dynamic_weights) if _has_new_config else _default_dynamic_weights

# Player archetype classification thresholds - now sourced from modular config when available
# Used to determine which dynamic ensemble weights to apply
_default_archetype_thresholds = {
    'QB': {'veteran_stable': {'min_experience': 3, 'max_cv_fppg': 0.3}, 'young_developing': {'max_experience': 2, 'min_games': 8}, 'high_volatility': {'min_cv_fppg': 0.4}},
    'RB': {'workhorse': {'min_carries_per_game': 15, 'min_touch_share': 0.6}, 'committee_back': {'max_carries_per_game': 12, 'max_touch_share': 0.45}, 'pass_catching': {'min_targets_per_game': 4, 'min_target_share': 0.1}, 'goal_line': {'min_red_zone_carries': 3, 'max_carries_per_game': 10}},
    'WR': {'target_hog': {'min_target_share': 0.25, 'min_targets_per_game': 8}, 'big_play': {'min_adot': 12, 'min_yards_per_target': 8}, 'possession': {'max_adot': 8, 'min_catch_rate': 0.7}, 'rookie_developing': {'max_experience': 1, 'min_draft_round': 1, 'max_draft_round': 3}},
    'TE': {'elite_tier': {'min_target_share': 0.15, 'min_targets_per_game': 6}, 'receiving_specialist': {'min_routes_per_snap': 0.7, 'max_blocking_snaps': 0.3}, 'blocking_hybrid': {'min_blocking_snaps': 0.4, 'max_targets_per_game': 4}, 'matchup_dependent': {'min_cv_targets': 0.5, 'max_target_share': 0.12}}
}
PLAYER_ARCHETYPE_THRESHOLDS = _config.get('model.archetype_thresholds', _default_archetype_thresholds) if _has_new_config else _default_archetype_thresholds

# Default scoring system to use for target variable calculation - now sourced from modular config when available
DEFAULT_SCORING_SYSTEM = _config.get('scoring.default_scoring_system', 'HalfPPR') if _has_new_config else 'HalfPPR'

# Mapping of scoring system names to actual column names in the raw data - now sourced from modular config when available
# 'fantasy_points' is calculated based on FANTASY_POINTS settings in this config
# 'fantasy_points_ppr' is the default full PPR column from nfl_data_py
_default_fantasy_columns = {'PPR': 'fantasy_points_ppr', 'HalfPPR': 'fantasy_points', 'Standard': 'fantasy_points'}
FANTASY_POINTS_COLUMNS = _config.get('scoring.fantasy_points_columns', _default_fantasy_columns) if _has_new_config else _default_fantasy_columns

# Target variable name for model training - now sourced from modular config when available
TARGET_VARIABLE = _config.get('model.target_variable', 'next_season_fppg') if _has_new_config else 'next_season_fppg'

