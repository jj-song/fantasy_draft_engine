# Fantasy Draft Engine - Claude Development Constitution

## Essential Commands

• `python -m services.ranking.src.main` - Start ranking service (microservices)
• `python -m services.ml-models.src.main` - Start ML models service (microservices)
• `pytest tests/` - Run all tests

## Utilities

• `python utils/data_inspection/inspect_parquet.py` - Inspect parquet file structure and data
• `python utils/data_inspection/inspect_baseline_models.py` - Analyze model features and compatibility
• `utils/wait-for-services.sh` - Docker utility for service startup coordination

## Tech Stack

• **Python**: pandas, numpy, scikit-learn, lightgbm
• **Models**: RandomForest + LightGBM ensemble
• **Data**: nfl_data_py for historical stats (2010-2024) with advanced metrics
• **Storage**: Parquet format for all data files
• **Architecture**: Microservices with FastAPI

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
• Validate realistic performance metrics (R² 40-46%, no data leakage)

### NEVER
• Use future data for training (data leakage)
• Train on playoff data
• Modify raw data files
• Commit model files to git
• Implement graceful failures that hide errors

## Key Directories

### Data (Project Root - Shared Across Services)
• `data/raw/` - Raw NFL data (parquet) - **15 years (2010-2024) with 81+ columns including advanced metrics**
• `data/processed/` - Cleaned data (parquet)
• `data/processed/position_specific/` - Position features
• `saved_models/` - ✅ **PRODUCTION READY** ensemble models (QB, RB, WR, TE)
• `data/draft_lists/` - ✅ **GENERATED** ML-powered rankings exports
• `logs/` - All pipeline logs

### Microservices
• `services/data-ingestion/` - NFL data fetching with play-by-play & snap counts
• `services/feature-engineering/` - Position-specific feature creation
• `services/ml-models/` - Model training and prediction serving
• `services/ranking/` - ✅ **INTEGRATION COMPLETE** VOR + ML predictions + export
• `services/configuration/` - Centralized configuration management
• `services/orchestration/` - Workflow coordination

### Utilities
• `utils/data_inspection/` - Data and model inspection tools
• `utils/validation/` - Pipeline validation utilities (future)
• `utils/core_scripts/` - Essential scripts (future)
• `utils/` - Docker and infrastructure utilities

## Data Structure (Current as of August 2025)

### Raw Data Files (data/raw/)
• **player_season_2010.parquet** through **player_season_2024.parquet**
• **81+ columns** per file including:
  - **Core Stats**: passing_yards, rushing_yards, receiving_yards, fantasy_points
  - **Advanced Play-by-Play**: air_yards_per_target, epa_per_target, yac_per_reception
  - **Usage Metrics**: total_offense_snaps, avg_offense_snap_pct (2012+)
  - **Player Info**: birth_date, college_name, draft_number
• **~500-600 players per year** across QB, RB, WR, TE, K positions

### Enhanced Data Features
• **Play-by-Play Data (2010-2024)**: Advanced receiving metrics, EPA, air yards
• **Snap Count Data (2012-2024)**: Offensive/defensive snap percentages  
• **Historical Depth**: 15 years for robust trend analysis
• **Consistent Schema**: Same 81 columns across all years for time-series modeling

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

## ML Integration Status (August 2025)

### ✅ RANKING SERVICE INTEGRATION COMPLETE
• **562 players ranked** with ML predictions from 2024 data
• **4 trained models** operational: QB (R²=42.5%), RB (45.7%), WR (46.1%), TE (40.6%) 
• **VOR calculations** applied with proper baselines (QB15, RB36, WR36, TE15)
• **Export functionality** working: CSV and JSON formats
• **Time-series methodology** prevents data leakage
• **Complete pipeline**: 2024 features → ML predictions → VOR rankings → draft export

### Key Model Performance
• **Training samples**: 4,728 total (QB:592, RB:1,291, WR:1,856, TE:989)
• **Realistic predictions**: QB ~17 FPPG, RB ~11 FPPG, WR ~8 FPPG, TE ~7 FPPG
• **Proper hierarchy**: Top RBs dominate VOR rankings (scarcity-based)

