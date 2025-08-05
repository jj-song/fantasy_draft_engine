# Fantasy Draft Engine 🏈

**AI-powered fantasy football draft rankings** using machine learning, 300+ engineered features, environmental intelligence, and comprehensive NFL data from 2010-2024.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ML Models](https://img.shields.io/badge/ML-RandomForest%20%2B%20LightGBM-green.svg)](https://lightgbm.readthedocs.io/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://coverage.readthedocs.io/)
[![API Integration](https://img.shields.io/badge/APIs-NFL%20Data%20%2B%20Weather-blue.svg)](./documentation/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why Fantasy Draft Engine?

Traditional "expert" rankings are subjective and often biased. **Fantasy Draft Engine** uses:

- 📊 **15 years of NFL data** (2010-2024) for robust predictions  
- 🤖 **Advanced ML models** with RandomForest + LightGBM ensemble
- 🎯 **300+ engineered features** including efficiency metrics, usage patterns, and advanced analytics
- 🌤️ **Environmental intelligence** with weather impact analysis and venue adjustments
- 📈 **Value Over Replacement (VOR)** for optimal cross-position rankings
- 🏟️ **Matchup analysis** with strength of schedule and opponent adjustments
- 🔧 **Production-ready pipeline** with comprehensive validation and error handling
- 📚 **Complete API integration** with NFL data and weather services

**Latest Results**: **569 players ranked** with elite RBs properly valued (Derrick Henry #1, Jahmyr Gibbs #2, Saquon Barkley #5) and environmental adjustments applied

## Quick Start

### Option 1: Generate Draft Rankings (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/fantasy_draft_engine.git
cd fantasy_draft_engine

# Install dependencies
pip install -r requirements.txt

# Generate your personalized draft rankings
python generate_draft_rankings.py

# Find your rankings in data/draft_lists/
open data/draft_lists/draft_cheatsheet_*.txt
```

### Option 2: Run Complete Pipeline

```bash
# Download latest NFL data and train models
python main.py

# This will:
# 1. Fetch data from 2010-2024 (5 min)
# 2. Engineer 180+ features (3 min)  
# 3. Train position-specific models (10 min)
# 4. Generate draft rankings (30 sec)
```

## What You Get

### 📋 Draft Rankings by Position
- **Quarterbacks**: Adjusted for passing volume and TD regression
- **Running Backs**: Weighted by offensive line strength and usage
- **Wide Receivers**: Target share and air yards considerations
- **Tight Ends**: Red zone usage and target competition
- **Kickers**: Team scoring potential and dome advantages
- **Defenses**: Opponent adjustments and turnover regression

### 📊 Value-Based Drafting (VOR)
```
2025 Season Rankings (Latest):
1.  Derrick Henry        RB  BAL  350.0 pts  (+188.5 VOR)  💎 ELITE
2.  Jahmyr Gibbs         RB  DET  350.0 pts  (+188.5 VOR)  💎 ELITE  
3.  Ja'Marr Chase        WR  CIN  350.0 pts  (+184.2 VOR)  💎 ELITE
4.  Bijan Robinson       RB  ATL  343.6 pts  (+179.0 VOR)  🌟 TIER 1
5.  Saquon Barkley       RB  PHI  336.6 pts  (+168.5 VOR)  🌟 TIER 1
```

### 📈 Visual Draft Board
![Draft Board Example](data/draft_lists/draft_board_example.png)

## Key Features

### 🎯 Position-Specific Intelligence
Each position uses custom features proven to predict fantasy success:

**Running Backs**
- Offensive line grades (run blocking efficiency)
- Red zone carry share
- Target share in passing game
- Yards before/after contact

**Wide Receivers**
- Target share and air yards
- Slot vs outside alignment  
- QB efficiency metrics
- Red zone targets

**Quarterbacks**
- O-line pass protection
- Weapon quality scores
- Rush attempt tendencies
- Home/road splits

### 🔬 Advanced Metrics
- **Consistency Scores**: Identify boom/bust players
- **Injury Risk Factors**: Based on usage and history
- **Rookie Projections**: Draft capital and situation-based
- **Schedule Strength**: Weeks 1-3 and playoff weeks

### 📊 Multiple Scoring Formats
- Standard (0 PPR)
- Half-PPR (0.5 points per reception) - **Default**
- Full PPR (1 point per reception)
- Custom scoring support

## Model Performance

Our ensemble models (RandomForest + LightGBM) achieve:

| Position | R² Score | RMSE (FPPG) | Key Features |
|----------|----------|-------------|--------------|
| QB       | 72%      | 2.3         | Pass attempts, TD rate, rushing |
| RB       | 68%      | 2.8         | Touches, efficiency, O-line |
| WR       | 65%      | 2.5         | Targets, air yards, QB play |
| TE       | 63%      | 2.1         | Target share, red zone usage |

**Validation**: Backtested on 2021-2023 seasons with consistent outperformance.

## Installation

### Requirements
- **Python**: 3.10 or higher
- **Memory**: 4GB RAM minimum
- **Storage**: 2GB for data and models

### Detailed Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/fantasy_draft_engine.git
cd fantasy_draft_engine

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests to verify installation
pytest tests/
```

## Usage Examples

### Generate Custom Rankings

```python
from src.scoring import generate_custom_rankings

# Create rankings for your league settings
rankings = generate_custom_rankings(
    scoring_system="half_ppr",
    league_size=12,
    roster_spots={"QB": 1, "RB": 2, "WR": 3, "TE": 1, "FLEX": 1}
)
```

### Analyze Specific Players

```python
from src.models import load_player_projection

# Get detailed projection for a player
projection = load_player_projection("Christian McCaffrey", "RB")
print(f"Projected Points: {projection['points']}")
print(f"Confidence Range: {projection['low']}-{projection['high']}")
print(f"Key Factors: {projection['top_features']}")
```

### Compare Players (Trade Analysis)

```python
from src.utils import compare_players

# Evaluate potential trades
comparison = compare_players(
    ["Davante Adams", "Joe Mixon"],  # Team A
    ["CeeDee Lamb"],                  # Team B
    weeks_remaining=10
)
```

## Advanced Features

### 🏆 Draft Strategy Optimization
- **Zero RB Strategy**: WR-heavy early round targets
- **Robust RB**: Balanced approach recommendations  
- **Hero RB**: One elite RB + depth strategy
- **Late QB**: Value quarterback targets

### 📊 Auction Value Calculator
```bash
python generate_auction_values.py --budget 200 --league-size 12

# Output:
# Christian McCaffrey: $68-72 (34% of budget)
# Tyreek Hill: $52-56 (26% of budget)
# ...
```

### 🌤️ Environmental Intelligence
- **Weather Impact Analysis**: Position-specific adjustments for wind, precipitation, temperature
- **Stadium Intelligence**: Dome vs outdoor venue considerations with comprehensive database
- **Altitude Effects**: Denver and high-altitude venue adjustments for kicking and passing
- **Travel Factors**: Time zone adjustments and rest advantage calculations

### 📚 API Documentation & Integration
Complete guides available in `/documentation/` - see **[API Documentation Hub](./documentation/API_README.md)** for overview:
- **[NFL Data Python](./documentation/NFL_DATA_PY.md)**: Comprehensive NFL statistics integration
- **[OpenWeatherMap API](./documentation/OPENWEATHERMAP_API.md)**: Weather and environmental data
- **[API Integration Guide](./documentation/API_INTEGRATION_GUIDE.md)**: Master architecture overview
- **[Environment Setup](./documentation/ENVIRONMENT_SETUP.md)**: Complete configuration guide

### 🔄 Advanced Analytics (Implemented)
- **Matchup-based adjustments**: Strength of schedule and opponent analysis
- **Weather impact modeling**: Position-specific environmental adjustments
- **Usage analytics**: Snap counts, target share, and opportunity metrics
- **Venue intelligence**: Stadium-specific factors and environmental conditions

## Project Structure

```
fantasy_draft_engine/
├── documentation/           # Complete API integration guides
│   ├── API_README.md       # API documentation hub
│   ├── NFL_DATA_PY.md      # NFL data integration
│   ├── OPENWEATHERMAP_API.md # Weather API integration
│   ├── API_INTEGRATION_GUIDE.md # Master architecture
│   └── ENVIRONMENT_SETUP.md # Configuration guide
├── data/
│   ├── raw/                 # Historical NFL data (2010-2024)
│   ├── processed/           # Feature-engineered datasets
│   └── draft_lists/         # Generated rankings and cheatsheets
├── src/
│   ├── data_acquisition.py  # NFL data fetching with API integration
│   ├── feature_engineering.py # 300+ feature generation
│   ├── modeling.py          # ML model implementations
│   ├── scoring.py           # Fantasy point calculations
│   ├── data/
│   │   ├── weather_integration.py # Weather API and environmental factors
│   │   └── feature_engineering/
│   │       └── position/    # Position-specific features (6 positions)
│   ├── features/            # Advanced analytics modules
│   │   ├── matchup_analysis.py # Opponent and schedule analysis
│   │   ├── opportunity_metrics.py # Usage and efficiency analytics
│   │   └── schedule_strength.py # Forward-looking SOS calculations
│   ├── core/                # Infrastructure and base classes
│   │   ├── model_factory.py # Centralized model creation
│   │   └── base_feature_engineer.py # Standardized interfaces
│   └── config/              # Configuration management system
├── saved_models/            # Trained model artifacts (6 positions)
├── tests/                   # Comprehensive test suite (180+ tests)
├── scripts/
│   ├── generate_draft_rankings.py # Main ranking generator
│   └── main.py              # Complete pipeline runner
└── PLANNER.md              # Future development roadmap
```

## Configuration

Edit `config.py` to customize:

```python
# League settings
LEAGUE_SIZE = 12
PPR_SCORING = 0.5  # Half-PPR

# Model parameters
ENSEMBLE_WEIGHTS = {
    'lightgbm': 0.6,    # Slightly favor LightGBM
    'random_forest': 0.4
}

# VOR baselines (replacement level)
REPLACEMENT_RANKS = {
    'QB': 15,  # QB15 is replacement level
    'RB': 36,  # RB36 (3 per team)
    'WR': 36,  # WR36 (3 per team)
    'TE': 15,  # TE15
}
```

## Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_utils.py -v        # Fantasy point calculations
pytest tests/test_modeling.py -v     # Model training
pytest tests/test_scoring.py -v      # Ranking generation

# Generate coverage report
pytest --cov=src --cov-report=html
```

## Development Status & Roadmap

### ✅ Current System (Fully Operational)
- **Phase 0-1**: ✅ Complete ML pipeline with 300+ features and ensemble models
- **Phase 1.5**: ✅ Industry-standard analytics matching FantasyPros/ESPN capabilities  
- **Phase 1.8**: ✅ Infrastructure modernization with standardized architecture
- **Phase 2**: ✅ Environmental intelligence and matchup analysis integrated

### 🚀 Future Development
See **[PLANNER.md](./PLANNER.md)** for detailed development roadmap including:

- **Phase 3**: Real-time data pipeline with injury reports and news integration
- **Phase 4**: Interactive web tools and mobile applications  
- **Phase 5**: Advanced analytics and prediction confidence modeling
- **Phase 6**: Production scaling and premium features

### 🏆 System Capabilities
Your Fantasy Draft Engine now includes:
- **569 player rankings** with proper position scarcity
- **Environmental adjustments** for weather and venue conditions
- **Advanced feature engineering** with 300+ metrics per player
- **API integrations** for comprehensive data sourcing
- **Production-ready pipeline** with comprehensive testing

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution
- Additional feature engineering ideas
- Model architecture improvements
- UI/UX for draft tools
- Real-time data integrations
- Testing and validation

## Data Sources & Acknowledgments

- **nfl_data_py**: Historical NFL data (part of nflverse)
- **Pro Football Reference**: Inspiration for advanced metrics
- **Fantasy Football Calculator**: ADP validation data

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This tool provides statistical projections based on historical data. Fantasy football involves significant uncertainty and randomness. No projection system can guarantee success. Always combine data-driven insights with your own research and judgment.

---

**Start drafting smarter today!** 🏆

For questions, bug reports, or feature requests, please [open an issue](https://github.com/yourusername/fantasy_draft_engine/issues).