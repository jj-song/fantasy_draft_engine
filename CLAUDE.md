# Fantasy Draft Engine - Claude Development Constitution

## Essential Commands

• `python main.py` - Complete pipeline execution
• `python generate_draft_rankings.py` - Generate final rankings
• `pytest tests/` - Run all tests
• `python src/final_evaluation.py` - Model evaluation

## Tech Stack

• **Python**: pandas, numpy, scikit-learn, lightgbm
• **Models**: RandomForest + LightGBM ensemble
• **Data**: nfl_data_py for historical stats (2010-2024)
• **Storage**: Parquet format for all data files

## Scoring System (0.5 PPR) - EXACT VALUES REQUIRED

• Pass: 0.04/yard, 4/TD, -2/INT
• Rush: 0.1/yard, 6/TD
• Rec: 0.5/catch, 0.1/yard, 6/TD
• Fumble: -2
• 2PT: 2

## VOR Baselines - NEVER CHANGE

• QB15, RB36, WR36, TE15

## Code Style & Conventions

### YOU MUST
• Use type hints on ALL functions
• Use time-series aware train/test splits
• Ensemble RandomForest + LightGBM models
• Log all data transformations
• Validate RMSE < 3.0, R² > 0.65, Spearman ρ > 0.75

### NEVER
• Use future data for training (data leakage)
• Train on playoff data
• Modify raw data files
• Commit model files to git
• Implement graceful failures that hide errors

## Key Directories

• `data/raw/` - Raw NFL data (parquet)
• `data/processed/` - Cleaned data (parquet)
• `data/processed/position_specific/` - Position features
• `saved_models/` - Trained models (timestamped)
• `data/draft_lists/` - Final rankings (timestamped)
• `logs/` - All pipeline logs

## Core Files & Critical Functions

• `src/data_acquisition.py` → `fetch_player_season_stats()`
• `src/feature_engineering.py` → `engineer_rb_features()`
• `src/scoring.py` → `calculate_fantasy_points()`, `calculate_vorp()`
• `src/modeling.py` → `train_position_model()`, `ensemble_predictions()`
• `generate_draft_rankings.py` → `generate_draft_rankings()`

## Environment/Terminology

• **VOR**: Value Over Replacement
• **0.5 PPR**: Half-point per reception scoring
• **L1 Features**: Previous season lagged variables
• **Ensemble**: RF + LightGBM combined predictions
• **Baseline Models**: Pre-trained models expecting specific column names

## Do Not Touch

• Fantasy scoring values (must match 0.5 PPR exactly)
• VOR replacement baselines (QB15, RB36, WR36, TE15)
• Baseline model column name mappings
• Time-series validation splits
• Feature mapping compatibility (`age`, `games_played`, `rushing_attempts`)

## CRITICAL Feature Mapping Fix (August 2025)

### Baseline Model Compatibility
• `birth_date` → `age` (calculate from year)
• `games` → `games_played` (direct mapping)
• `carries` → `rushing_attempts` (RB-specific)
• Convert per-game predictions to seasonal totals
• Validate prediction ranges for each position

