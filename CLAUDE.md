# Fantasy Draft Engine - Claude Development Constitution

## Essential Commands

• `docker-compose up -d` - Start all services with proper port management (RECOMMENDED)
• `docker-compose ps` - Check service status and ports
• `python -m services.ranking.src.main` - Start ranking service manually (port conflicts possible)
• `python -m services.ml-models.src.main` - Start ML models service manually (port conflicts possible)

## Orchestration Service Commands (NEW)

• `curl http://localhost:8006/api/v1/orchestration/status` - Complete system status and health
• `curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline -H "Content-Type: application/json" -d '{"workflow_type": "full-pipeline", "parameters": {"positions": ["QB", "RB", "WR", "TE"], "years": [2024], "season": 2024}}'` - Execute full pipeline
• `curl http://localhost:8006/api/v1/workflows/health-check` - Comprehensive health check across all services
• `curl http://localhost:8006/api/v1/workflows/{workflow_id}/status` - Check specific workflow progress

## Ranking Generation Verification

• **ALWAYS verify file timestamps**: Check creation time of files in `data/draft_lists/` against when ranking generation was triggered
• **Use**: `ls -lt data/draft_lists/fantasy_rankings_*.csv` to find most recent rankings
• **Docker container files**: May need `docker cp` from container to host if volume mapping issues occur

## Service Port Assignments (Docker Compose)

• **Configuration**: localhost:8001
• **Data Ingestion**: localhost:8002  
• **Feature Engineering**: localhost:8003
• **ML Models**: localhost:8004
• **Ranking**: localhost:8005
• **Orchestration**: localhost:8006
• **Redis**: localhost:6379
• `pytest tests/` - Run all tests

## Utilities

• `python utils/data_inspection/inspect_parquet.py` - Inspect parquet file structure and data
• `python utils/data_inspection/inspect_baseline_models.py` - Analyze model features and compatibility
• `utils/wait-for-services.sh` - Docker utility for service startup coordination

## Tech Stack

• **Python**: pandas, numpy, scikit-learn
• **Models**: RandomForest ensemble (production), LightGBM (planned)
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
• RandomForest ensemble models (LightGBM integration planned)
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
• **Ensemble**: RandomForest models (production), LightGBM integration planned
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
• **Feature set**: 23 core features (simplified from 100+ research blueprint)
• **Model architecture**: RandomForest ensemble per position
• **Realistic predictions**: QB ~17 FPPG, RB ~11 FPPG, WR ~8 FPPG, TE ~7 FPPG
• **Proper hierarchy**: Top RBs dominate VOR rankings (scarcity-based)

### Current vs Planned Feature Engineering
• **PRODUCTION (Current)**: Core 23 features focused on reliability and consistency
  - Basic stats: attempts, yards, touchdowns, games played, age
  - Efficiency metrics: yards per attempt, completion %, catch rate
  - Usage metrics: target share, rushing share
• **RESEARCH BLUEPRINT**: 100+ advanced features documented in services/feature-engineering/
  - Advanced metrics: WOPR, ADOT, air yards, YAC analysis
  - Matchup intelligence: strength of schedule, weather factors
  - Historical patterns: lagged features, trend analysis
• **ROADMAP**: Gradual integration of research features with production validation

