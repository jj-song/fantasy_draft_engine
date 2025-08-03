# Fantasy Draft Engine - Development Constitution

## Essential Commands

### Core Pipeline Commands
• `python src/data_acquisition.py` - **REQUIRED** - Fetch historical NFL data (2010-2023)
• `python src/data_cleaning.py` - Clean and prepare raw data for feature engineering
• `python src/feature_engineering.py` - Generate position-specific features
• `python generate_draft_rankings.py` - Create draft rankings with VOR calculations
• `python main.py` - Run complete pipeline from data to rankings

### Model Training & Evaluation
• `python run_feature_engineering_analysis.py` - Train position-specific models with feature analysis
• `python src/final_evaluation.py` - Run comprehensive model evaluation with cross-validation
• `python src/model_persistence.py` - Save/load trained models
• `python test_scoring_pipeline.py` - Test fantasy scoring calculations

### Testing & Validation
• `pytest tests/` - Run all unit tests
• `pytest tests/test_utils.py -v` - Test fantasy point calculations
• `pytest tests/test_scoring.py -v` - Validate scoring system
• `pytest tests/test_modeling.py -v` - Test model training pipeline
• `python -m pytest --cov=src --cov-report=html` - Generate coverage report

### Utility Commands
• `python -m src.data_storage --validate` - Validate data storage integrity
• `python -m src.utils --calculate-fantasy-points` - Test fantasy point calculations
• `tail -f logs/fantasy_football.log` - Monitor pipeline logs

## IMPORTANT - Fantasy Football Domain Knowledge

### Scoring System (0.5 PPR)
**YOU MUST use these exact scoring values for all calculations:**
• Passing: 0.04 pts/yard (1 pt per 25 yards), 4 pts/TD, -2 pts/INT
• Rushing: 0.1 pts/yard (1 pt per 10 yards), 6 pts/TD
• Receiving: 0.5 pts/reception, 0.1 pts/yard, 6 pts/TD
• Fumbles Lost: -2 pts
• 2-Point Conversions: 2 pts

### Position Strategy & Draft Theory
• **RB Priority**: RBs are most valuable due to scarcity and workload concentration
• **WR Depth**: WRs have more depth, making mid-round WRs valuable
• **QB Replaceability**: QBs score most but are replaceable (wait on QB strategy)
• **TE Cliff**: Elite TEs (top 3-5) provide significant advantage
• **Zero RB Strategy**: Load up on WRs early, grab RBs in middle rounds
• **Robust RB**: Balance RBs and WRs in early rounds

### Value Over Replacement (VOR) Calculations
**CRITICAL**: VOR determines draft value across positions
• QB Replacement: QB15 (streaming QBs viable)
• RB Replacement: RB36 (3 per team in 12-team league)
• WR Replacement: WR36 (similar depth to RB)
• TE Replacement: TE15 (significant dropoff after top tier)

## Machine Learning Best Practices

### IMPORTANT - Model Development Rules
• YOU MUST use time-series aware splits for validation
• YOU MUST ensemble RandomForest + LightGBM models
• YOU MUST validate on held-out future season data
• YOU MUST calculate confidence intervals for predictions
• NEVER use future data for training (no data leakage)
• NEVER train on playoff data (different dynamics)

### Feature Engineering Standards
• **Position-Specific Features**: Each position has unique predictive features
• **Lagged Variables**: Use L1 (last season) features for predictions
• **Efficiency Metrics**: Yards per attempt/target/carry are crucial
• **Usage Metrics**: Target share, rush attempt share, red zone usage
• **Team Context**: Offensive line ratings, defensive matchups
• **Consistency Scores**: Player volatility affects draft value

### Model Validation Requirements
• Cross-validation RMSE < 3.0 fantasy points per game
• R² > 0.65 for seasonal projections
• Rank correlation (Spearman's ρ) > 0.75
• Separate validation for each position
• Test on multiple seasons (2021-2023)

## Code Standards

### IMPORTANT - Python Rules
• YOU MUST use type hints for ALL functions
• YOU MUST use pandas for data manipulation
• YOU MUST use numpy for numerical operations
• YOU MUST document all feature engineering steps
• YOU MUST log all data transformations
• NEVER modify raw data files
• NEVER commit model files to git (too large)

### Data Pipeline Standards
• Raw data stored in `data/raw/` (parquet format)
• Processed data in `data/processed/` (parquet format)
• Features stored by position in `data/processed/position_specific/`
• Models saved in `saved_models/` with timestamp
• Draft lists in `data/draft_lists/` with timestamp

## Development Workflow

### Before Every Model Training
• YOU MUST verify data completeness (no missing seasons)
• YOU MUST check for data quality issues
• YOU MUST validate feature distributions
• YOU MUST ensure proper train/test splits

### Integration with Past Project
**Incorporate team unit analysis concepts:**
• Offensive line impact on RB performance
• Defensive unit strength for opponent adjustments
• Team passing volume affects WR/TE value
• Coaching tendencies and play-calling patterns

## File Structure

### Data Pipeline
• `src/data_acquisition.py` - NFL data fetching via nfl_data_py
• `src/data_cleaning.py` - Data quality and standardization
• `src/feature_engineering.py` - Feature creation pipeline
• `src/data/feature_engineering/position/` - Position-specific features

### Modeling
• `src/modeling.py` - Base model classes (RF, LightGBM, Ridge)
• `src/models/model_comparison.py` - Feature engineering comparison
• `src/training_evaluation.py` - Cross-validation and metrics
• `src/final_evaluation.py` - Comprehensive model evaluation

### Draft Tools
• `generate_draft_rankings.py` - Create draft rankings with VOR
• `src/scoring.py` - Fantasy point calculations and rankings
• `main.py` - Complete pipeline orchestration

## Critical Functions

### Data Processing
• `fetch_player_season_stats()` - Get NFL data by season
• `calculate_fantasy_points()` - Apply scoring system
• `engineer_rb_features()` - RB-specific feature engineering
• `calculate_vorp()` - Value over replacement calculations

### Model Training
• `train_position_model()` - Position-specific model training
• `ensemble_predictions()` - Combine model predictions
• `evaluate_model_performance()` - Calculate metrics
• `save_model_artifacts()` - Persist models and scalers

### Draft Rankings
• `generate_draft_rankings()` - Create overall rankings
• `calculate_auction_values()` - Convert to dollar values
• `create_position_tiers()` - Group players by value tiers
• `export_draft_cheatsheet()` - Generate printable rankings

## Testing Requirements

### Model Validation
• YOU MUST test fantasy point calculations for edge cases
• YOU MUST validate VOR calculations across positions
• YOU MUST ensure rookie projections are reasonable
• YOU MUST test model predictions on previous seasons

### Integration Testing
• Test complete pipeline from data fetch to rankings
• Validate that rankings follow logical constraints
• Ensure position scarcity is properly reflected
• Test draft list generation for different formats

## Quality Standards

### Code Quality
• Type hints on all functions
• Docstrings with examples
• Unit tests for critical functions
• Integration tests for pipeline
• Performance benchmarks documented

### Model Quality
• Track prediction accuracy by position
• Monitor feature importance stability
• Validate against actual draft results
• Compare to expert consensus rankings

## Refactoring Priorities

### Phase 1: Code Quality
• Abstract position-specific features to base classes
• Implement proper error handling and retries
• Add comprehensive logging throughout
• Create data validation framework

### Phase 2: Advanced Features
• Multi-task learning across positions
• Injury impact modeling
• Schedule strength adjustments
• Real-time data integration

### Phase 3: Production Features
• API layer for draft tools
• Web interface for rankings
• Mobile app support
• Live draft assistance

## Performance Rules

• Data processing should complete in < 5 minutes
• Model training per position < 2 minutes
• Draft ranking generation < 30 seconds
• API response times < 500ms
• Memory usage < 4GB for full pipeline

## Fantasy Football Algorithms

### Auction Value Calculation
• Total auction budget: $200 for 15 players
• Starter budget: ~88% ($176)
• Bench budget: ~12% ($24)
• Top player value: ~$65-70 (elite RB/WR)
• Replacement player: $1

### Dynasty/Keeper Adjustments
• Age curve: Peak at 24-27, decline after 29
• Rookie premium: +15% for high draft capital
• Contract years: Adjust for keeper costs
• Trade calculator: 3-year weighted projections

## Do Not Touch

• NEVER modify fantasy scoring without updating all calculations
• NEVER change VOR baselines without full revalidation
• NEVER mix playoff and regular season data
• NEVER use weather data without game-time updates
• NEVER predict season-long injuries (only current status)

## Monitoring & Analytics

### Pipeline Health
• Track data freshness (last update time)
• Monitor feature generation success rates
• Log model training convergence
• Validate prediction distributions
• Alert on anomalous projections

### Model Performance
• Weekly accuracy tracking during season
• Position-specific error analysis
• Feature drift detection
• Prediction confidence tracking
• Compare to betting lines for validation

## Integration Guidelines

### External Data Sources
• **Injury Data**: Use official injury reports only
• **Weather Data**: Integrate for weekly projections
• **Vegas Lines**: Validate team totals and game scripts
• **Beat Reporter News**: Sentiment analysis for usage changes
• **Depth Charts**: Official team depth charts only

### Team Unit Analysis (From Past Project)
• Map offensive line grades to RB efficiency multipliers
• Use defensive DVOA for opponent adjustments
• Track coordinator changes for scheme impacts
• Monitor personnel groupings for usage patterns

## Draft Strategy Implementation

### Upside vs Floor Calculation
• **Floor**: 20th percentile projection
• **Ceiling**: 80th percentile projection  
• **Upside Score**: (Ceiling - Median) / Median
• **Consistency**: 1 - (StdDev / Mean)
• Balance based on roster construction

### Position Scarcity Modeling
• Calculate drop-off rates between tiers
• Identify position runs in draft tendencies
• Adjust for league scoring settings
• Model supply/demand dynamics

## Future Enhancement Checklist

- [ ] Real-time injury status integration
- [ ] Weather impact on game totals
- [ ] Coaching tendency analysis
- [ ] Stacking strategies for DFS
- [ ] Trade analyzer with fair values
- [ ] Waiver wire priority rankings
- [ ] Playoff schedule optimization
- [ ] Keeper league value projections