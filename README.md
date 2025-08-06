# Fantasy Draft Engine 🏈

**AI-powered fantasy football draft rankings** using machine learning and comprehensive NFL data analysis. Built with production-ready microservices architecture and streamlined feature engineering for reliable predictions.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![ML Models](https://img.shields.io/badge/ML-RandomForest%20Ensemble-green.svg)](https://scikit-learn.org/)
[![Microservices](https://img.shields.io/badge/Architecture-6%20Services%20Validated-blue.svg)](./PLAN.md)
[![Docker](https://img.shields.io/badge/Deployment-Docker%20Compose-blue.svg)](https://docker.com/)
[![Production Ready](https://img.shields.io/badge/Status-All%20Services%20Validated-brightgreen.svg)](./DEVELOPER_NOTES.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 Table of Contents

- [Quick Start](#-quick-start) - Get up and running in 5 minutes
- [Source Code Navigation](#-source-code-navigation) - Understand the codebase structure
- [Key Functions & Commands](#-key-functions--commands) - Essential commands and entry points
- [API Usage Guide](#-api-usage-guide) - Service endpoints and usage examples
- [What Makes This Different](#-what-makes-this-different) - Technical overview and capabilities
- [Architecture Overview](#%EF%B8%8F-architecture-overview) - System design and service breakdown

## 🎯 What Makes This Different

Unlike subjective "expert" rankings, Fantasy Draft Engine provides **data-driven insights** using:

- 📊 **15+ years of NFL data** (2010-2024) for robust statistical modeling
- 🤖 **RandomForest ensemble models** optimized for each position
- 🎯 **Core feature engineering** with efficiency metrics and usage patterns (23 key features)
- 📈 **Value Over Replacement (VOR)** calculations for optimal cross-position rankings
- 🔧 **Production-ready microservices** architecture with FastAPI endpoints
- 📊 **Time-series validation** to prevent data leakage and ensure realistic performance

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# Clone and start all services
git clone https://github.com/yourusername/fantasy_draft_engine.git
cd fantasy_draft_engine

# Launch all 6 microservices
docker-compose up -d

# Check service health
curl http://localhost:8001/health/live  # Configuration Service
curl http://localhost:8002/health/live  # Data Ingestion Service
curl http://localhost:8003/health/live  # Feature Engineering Service
curl http://localhost:8004/health/live  # ML Models Service
curl http://localhost:8005/health/live  # Ranking Service
curl http://localhost:8006/health/live  # Orchestration Service

# Generate complete rankings using orchestration service
curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline \
  -H "Content-Type: application/json" \
  -d '{"workflow_type": "full-pipeline", "parameters": {"positions": ["QB", "RB", "WR", "TE"], "years": [2024], "season": 2024}}'
```

### Option 2: Manual Service Execution

```bash
# Install dependencies
pip install -r requirements.txt

# Start services individually (separate terminals)
python -m services.configuration.src.main      # Port 8001
python -m services.data-ingestion.src.main     # Port 8002  
python -m services.feature-engineering.src.main # Port 8003
python -m services.ml-models.src.main          # Port 8004
python -m services.ranking.src.main            # Port 8005
python -m services.orchestration.src.main      # Port 8006

# Or use the main orchestration script
python main_microservices.py
```

### Option 3: Direct Pipeline Execution

```bash
# Run end-to-end ranking generation
python -m services.ranking.src.main &
sleep 5

# Generate rankings via API
curl -X POST http://localhost:8005/api/v1/rankings/generate \
  -H "Content-Type: application/json" \
  -d '{"positions": ["QB", "RB", "WR", "TE"], "season": 2024, "tier_assignments": true, "sort_by": "vor"}'

# Check results
ls -la data/draft_lists/fantasy_rankings_*.csv
```

## 🗂️ Source Code Navigation

Understanding the codebase structure is essential for effective development and usage. Here's your complete navigation guide:

### 📁 **Project Root Structure**
```
fantasy_draft_engine/
├── 📋 README.md                    # This navigation guide  
├── 📋 PLAN.md                     # Master project documentation
├── 📋 DEVELOPER_NOTES.md          # Current status and handoff notes
├── 📋 CLAUDE.md                   # Development constitution and commands
├── 🐳 docker-compose.yml          # Multi-service orchestration
├── 🐍 main_microservices.py       # Main orchestration entry point
├── 🐍 requirements.txt            # Python dependencies
├── 📊 data/                       # All data files (raw, processed, rankings)
├── 🔬 services/                   # 6 microservices (core architecture)
├── 🧪 tests/                      # Comprehensive test suite
├── 🛠️ utils/                      # Utilities and inspection tools
├── 📁 documentation/              # Additional guides and API docs  
├── 📊 reports/                    # Validation reports and analysis
└── 💾 saved_models/               # Trained ML models (4 positions)
```

### 🎯 **Core Entry Points** (What to run)
| File | Purpose | Usage |
|------|---------|-------|
| **`main_microservices.py`** | Complete pipeline orchestration | `python main_microservices.py` |
| **`docker-compose.yml`** | All services at once | `docker-compose up -d` |
| **`services/*/src/main.py`** | Individual service startup | `python -m services.ranking.src.main` |
| **`tests/validate_end_to_end.py`** | System validation | `python tests/validate_end_to_end.py` |
| **`utils/data_inspection/inspect_*.py`** | Data analysis | `python utils/data_inspection/inspect_parquet.py` |

### 🔬 **Services Directory** (6 Microservices)
```
services/
├── configuration/          # Centralized config management (Port 8001)
│   ├── src/main.py        # → Start: python -m services.configuration.src.main
│   ├── configs/           # → YAML configuration files
│   └── src/managers/      # → ConfigManager, scoring systems, VOR baselines
├── data-ingestion/        # NFL data acquisition (Port 8002)
│   ├── src/main.py        # → Start: python -m services.data-ingestion.src.main
│   ├── src/acquisition/   # → NFLDataFetcher, 15 years of data (2010-2024)
│   └── src/cleaning/      # → Data validation and cleaning
├── feature-engineering/   # Feature generation (Port 8003) 
│   ├── src/main.py        # → Start: python -m services.feature-engineering.src.main
│   ├── src/position_features/ # → QB/RB/WR/TE feature engineering (85+ features)
│   └── src/processors/    # → Core feature pipeline
├── ml-models/             # Model training & serving (Port 8004)
│   ├── src/main.py        # → Start: python -m services.ml-models.src.main
│   ├── src/serving/       # → ModelRegistry, PredictionEngine
│   └── src/training/      # → RandomForest ensemble training
├── ranking/               # VOR & draft rankings (Port 8005)
│   ├── src/main.py        # → Start: python -m services.ranking.src.main
│   ├── src/calculation/   # → VORCalculator, tier assignments
│   └── src/outputs/       # → CheatsheetGenerator (CSV/JSON export)
└── orchestration/         # Workflow coordination (Port 8006)
    ├── src/main.py        # → Start: python -m services.orchestration.src.main
    ├── src/workflows/     # → FullPipelineWorkflow automation
    └── src/monitoring/    # → HealthChecker, service monitoring
```

### 📊 **Data Structure** (Organized by processing stage)
```
data/
├── raw/                   # Original NFL data (81 columns per year)
│   └── player_season_YYYY.parquet # → 15 years: 2010-2024 
├── processed/             # Feature-engineered data
│   ├── position_specific/ # → QB/RB/WR/TE features by year (85+ features)
│   └── features/          # → Processed feature files
└── draft_lists/           # Final output rankings
    └── fantasy_rankings_YYYYMMDD_HHMMSS.csv # → 500+ players ranked with VOR/tiers
```

### 🧪 **Testing & Validation** (Quality assurance)
```
tests/
├── validate_end_to_end.py           # → Complete system test
├── test_microservices_integration.py # → Service communication tests
├── test_*_features_migration.py     # → Position-specific feature tests
└── validation_reports/              # → Historical test results

reports/validation/                   # → Service validation reports
├── configuration/VALIDATION_SUMMARY_CONFIGURATION.md    # → 90% validated
├── data-ingestion/VALIDATION_SUMMARY_DATA_INGESTION.md  # → 100% validated  
├── feature-engineering/VALIDATION_SUMMARY_FEATURE_ENGINEERING.md # → 100% validated
├── ml-models/VALIDATION_SUMMARY_ML_MODELS.md           # → 100% validated
├── ranking/VALIDATION_SUMMARY_RANKING.md               # → 100% validated
└── orchestration/VALIDATION_SUMMARY_ORCHESTRATION.md   # → 100% validated
```

### 🛠️ **Utilities & Tools** (Developer helpers)
```
utils/
├── data_inspection/       # → Data analysis and debugging tools
│   ├── inspect_parquet.py      # → python utils/data_inspection/inspect_parquet.py
│   └── inspect_baseline_models.py # → python utils/data_inspection/inspect_baseline_models.py
├── debug_analysis/        # → Validation framework
│   ├── debug_integration.py    # → Service validation system
│   └── debug_validator.py      # → Validation checkpoints
└── validation/           # → Quality assurance tools
```

### 💾 **Trained Models** (Production-ready ML models)
```
saved_models/
├── QB_ensemble_model.joblib  # → 42.5% R², 592 training samples
├── RB_ensemble_model.joblib  # → 45.7% R², 1,291 training samples  
├── WR_ensemble_model.joblib  # → 46.1% R², 1,856 training samples
└── TE_ensemble_model.joblib  # → 40.6% R², 989 training samples
```

### 📚 **Documentation** (Guides and references)
```
documentation/
├── API_INTEGRATION_GUIDE.md    # → Service integration patterns
├── ENVIRONMENT_SETUP.md        # → Development environment setup
├── DOCKER_DOCUMENTATION.md     # → Container deployment guide
└── NFL_DATA_PY.md              # → Data source documentation
```

## 🎮 Key Functions & Commands

### **🚀 Essential Commands** (Most frequently used)

#### **Start Complete System**
```bash
# Option 1: All services via Docker (RECOMMENDED)
docker-compose up -d
docker-compose ps  # Verify all services running

# Option 2: Manual service coordination  
python main_microservices.py

# Option 3: Individual services (development)
python -m services.orchestration.src.main    # Start orchestration first
python -m services.configuration.src.main    # Then configuration
python -m services.data-ingestion.src.main   # Then data ingestion
python -m services.feature-engineering.src.main # Then feature engineering  
python -m services.ml-models.src.main        # Then ML models
python -m services.ranking.src.main          # Finally ranking service
```

#### **Generate Fantasy Rankings**
```bash
# Option 1: Via Orchestration Service (RECOMMENDED - uses all services)
curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "full-pipeline",
    "parameters": {
      "positions": ["QB", "RB", "WR", "TE"],
      "years": [2024], 
      "season": 2024
    }
  }'

# Option 2: Direct Ranking Service (faster for testing)
curl -X POST http://localhost:8005/api/v1/rankings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "positions": ["QB", "RB", "WR", "TE"],
    "season": 2024,
    "tier_assignments": true,
    "sort_by": "vor"
  }'

# Check results
ls -la data/draft_lists/fantasy_rankings_*.csv
head -20 data/draft_lists/fantasy_rankings_*.csv  # View top 20 players
```

#### **System Health Monitoring**
```bash
# Check all services health
curl http://localhost:8001/health/live   # Configuration
curl http://localhost:8002/health/live   # Data Ingestion
curl http://localhost:8003/health/live   # Feature Engineering  
curl http://localhost:8004/health/live   # ML Models
curl http://localhost:8005/health/live   # Ranking
curl http://localhost:8006/health/live   # Orchestration

# Comprehensive system status
curl http://localhost:8006/api/v1/orchestration/status

# Health check via orchestration
curl http://localhost:8006/api/v1/workflows/health-check
```

### **🔍 Analysis & Debugging Commands**

#### **Data Inspection**
```bash
# Inspect raw NFL data structure
python utils/data_inspection/inspect_parquet.py

# Analyze trained models
python utils/data_inspection/inspect_baseline_models.py

# View data quality report
cat data_quality_report.md
```

#### **Service Testing**
```bash
# End-to-end validation
python tests/validate_end_to_end.py

# Microservices integration test
python tests/test_microservices_integration.py

# Feature compatibility test
python tests/test_feature_compatibility.py

# Individual position feature tests
python tests/test_qb_features_migration.py   # QB features
python tests/test_rb_features_migration.py   # RB features  
python tests/test_wr_features_migration.py   # WR features
python tests/test_te_features_migration.py   # TE features
```

#### **Model Testing**
```bash
# Test individual ML predictions  
curl -X POST http://localhost:8004/api/v1/models/predict \
  -H "Content-Type: application/json" \
  -d '{
    "position": "QB",
    "features": {
      "games": 16, "age": 28, "attempts": 450, "completions": 290,
      "passing_yards": 3500, "passing_tds": 25, "interceptions": 8,
      "carries": 45, "rushing_yards": 300, "rushing_tds": 3,
      "yards_per_attempt": 7.8, "completion_percentage": 64.4
    },
    "player_data": {"player_name": "Test QB", "team": "KC"}
  }'

# Test model registry status
curl http://localhost:8004/api/v1/models/status
```

### **⚙️ Configuration & Customization**

#### **Configuration Management**
```bash
# View all configuration domains
curl http://localhost:8001/api/v1/config/data      # Data config (2010-2024 years)
curl http://localhost:8001/api/v1/config/league    # League config (12-team, 0.5 PPR)
curl http://localhost:8001/api/v1/config/model     # Model config (RandomForest)
curl http://localhost:8001/api/v1/config/position  # Position config (QB,RB,WR,TE)
curl http://localhost:8001/api/v1/config/scoring   # Scoring config (0.5 PPR system)

# View positions and scoring system
curl http://localhost:8001/api/v1/positions
curl http://localhost:8001/api/v1/scoring/system
```

#### **Data Management**
```bash
# Trigger data ingestion for specific year/position
curl -X POST http://localhost:8002/api/v1/data/ingest \
  -H "Content-Type: application/json" \
  -d '{"years": [2024], "positions": ["QB"], "force_refresh": true}'

# Generate features for specific position/year  
curl -X POST http://localhost:8003/api/v1/features/generate \
  -H "Content-Type: application/json" \
  -d '{"years": [2024], "positions": ["RB"], "force_refresh": true}'
```

### **📊 Workflow Management**

#### **Orchestration Service Commands**
```bash
# Execute full pipeline workflow
curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline \
  -H "Content-Type: application/json" \
  -d '{"workflow_type": "full-pipeline", "parameters": {"positions": ["QB"], "years": [2024]}}'

# Check workflow status (replace {workflow_id} with actual ID from above response)
curl http://localhost:8006/api/v1/workflows/{workflow_id}/status

# View workflow execution history
curl http://localhost:8006/api/v1/workflows/history

# Schedule automated workflow (if needed)
curl -X POST http://localhost:8006/api/v1/workflows/schedule \
  -H "Content-Type: application/json" \
  -d '{"schedule": "daily", "workflow_type": "full-pipeline"}'
```

### **🔧 Development & Maintenance Commands**

#### **Service Management**
```bash
# Stop all services  
docker-compose down

# Restart specific service
docker-compose restart ml-models

# View service logs
docker-compose logs -f ranking      # Follow ranking service logs
docker-compose logs orchestration  # View orchestration logs

# Manual service restart (if not using Docker)
pkill -f "services.ranking"         # Stop ranking service
python -m services.ranking.src.main & # Restart ranking service
```

#### **Data Pipeline Reset**
```bash
# Clear processed data (force regeneration)
rm -rf data/processed/features/*
rm -rf data/processed/position_specific/*

# Clear draft rankings (force regeneration)  
rm -rf data/draft_lists/fantasy_rankings_*.csv

# Clear validation reports (for fresh validation)
rm -rf reports/validation/*/debug_validation_*.json
```

## 📡 API Usage Guide

All services provide REST APIs with standardized patterns. Here are the key endpoints:

### **🎯 Orchestration Service** (Port 8006) - Primary Interface
```bash
# System Status & Health
GET  /api/v1/orchestration/status           # Complete system overview
GET  /api/v1/workflows/health-check         # Multi-service health check
GET  /health/live                           # Service liveness
GET  /health/ready                          # Service readiness

# Workflow Execution  
POST /api/v1/workflows/full-pipeline        # Execute complete pipeline
GET  /api/v1/workflows/{id}/status          # Track workflow progress
GET  /api/v1/workflows/history              # View execution history
POST /api/v1/workflows/schedule             # Schedule automated workflows
```

### **⚙️ Configuration Service** (Port 8001) - Settings Management
```bash
# Configuration Access
GET  /api/v1/config/{domain}               # Get domain config (data/league/model/position/scoring)
GET  /api/v1/positions                     # Get all positions and core positions
GET  /api/v1/scoring/system                # Get complete scoring system
GET  /health/live                          # Service health
GET  /health/ready                         # Service readiness with resource metrics
```

### **📊 Data Ingestion Service** (Port 8002) - NFL Data Management  
```bash
# Data Operations
POST /api/v1/data/ingest                   # Fetch NFL data for specific years/positions
GET  /api/v1/data/status                   # Data ingestion status
GET  /health/live                          # Service health
GET  /health/ready                         # Service readiness
```

### **🔧 Feature Engineering Service** (Port 8003) - Feature Generation
```bash
# Feature Operations  
POST /api/v1/features/generate             # Generate features for positions/years
GET  /api/v1/features/status               # Feature generation status
GET  /health/live                          # Service health  
GET  /health/ready                         # Service readiness
```

### **🤖 ML Models Service** (Port 8004) - Predictions & Training
```bash
# Prediction Engine
POST /api/v1/models/predict                # Single player prediction
POST /api/v1/models/batch-predict          # Batch predictions (if available)
GET  /api/v1/models/status                 # Model registry status
GET  /api/v1/models/{position}/info        # Position model information
GET  /health/live                          # Service health
GET  /health/ready                         # Service readiness  
```

### **🏆 Ranking Service** (Port 8005) - Draft Rankings Generation
```bash
# Rankings Generation
POST /api/v1/rankings/generate             # Generate draft rankings  
GET  /api/v1/rankings/status               # Ranking generation status
GET  /api/v1/rankings/latest               # Get latest rankings
GET  /api/v1/rankings/export               # Export rankings in various formats
GET  /health/live                          # Service health
GET  /health/ready                         # Service readiness
```

### **📝 Sample API Request/Response Examples**

#### **Generate Complete Rankings**
```bash
# Request
curl -X POST http://localhost:8006/api/v1/workflows/full-pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "full-pipeline",
    "parameters": {
      "positions": ["QB", "RB", "WR", "TE"],
      "years": [2024],
      "season": 2024
    }
  }'

# Response
{
  "workflow_id": "workflow_20250806_123456", 
  "status": "started",
  "message": "Full pipeline workflow initiated",
  "estimated_completion": "2025-08-06T12:37:00Z",
  "steps": ["data_ingestion", "feature_engineering", "ml_predictions", "vor_calculations", "ranking_generation", "export"]
}
```

#### **Check System Health**
```bash
# Request
curl http://localhost:8006/api/v1/orchestration/status

# Response  
{
  "system_status": "healthy",
  "services": {
    "configuration": {"status": "healthy", "port": 8001, "response_time_ms": 1.2},
    "data_ingestion": {"status": "healthy", "port": 8002, "response_time_ms": 2.1}, 
    "feature_engineering": {"status": "healthy", "port": 8003, "response_time_ms": 1.8},
    "ml_models": {"status": "healthy", "port": 8004, "response_time_ms": 15.4},
    "ranking": {"status": "healthy", "port": 8005, "response_time_ms": 3.2}
  },
  "last_successful_pipeline": "2025-08-06T17:59:28Z",
  "players_ranked": 569
}

## 📊 What You Get

### Draft Rankings with Statistical Tiers
- **Position-specific models** optimized for QB, RB, WR, TE performance patterns
- **Confidence intervals** showing prediction reliability for each player
- **Tier-based groupings** identifying value breaks and draft targets

### Value-Based Drafting (VOR)
Players ranked by **Value Over Replacement** to optimize draft strategy across positions:

```
2025 Season Rankings (ML-Generated):
1.  Derrick Henry         RB  BAL  243.1 pts  (+148.3 VOR)  💎 ELITE
2.  Jahmyr Gibbs          RB  DET  241.5 pts  (+146.7 VOR)  💎 ELITE  
3.  Bijan Robinson        RB  ATL  223.3 pts  (+128.6 VOR)  💎 ELITE
4.  De'Von Achane         RB  MIA  220.3 pts  (+125.6 VOR)  🌟 TIER 1
5.  Saquon Barkley        RB  PHI  219.6 pts  (+124.9 VOR)  🌟 TIER 1
```

### Exportable Formats
- **CSV files** for spreadsheet analysis
- **JSON data** for custom applications  
- **Printable cheatsheets** for draft day

## 🏗️ Architecture Overview

**6-Service Microservices Architecture - All Services Production Ready:**

- **Configuration** (8001) - ✅ **90% Validated** - Centralized settings, 0.5 PPR scoring, VOR baselines
- **Data Ingestion** (8002) - ✅ **100% Validated** - NFL data acquisition (2010-2024), 81 columns
- **Feature Engineering** (8003) - ✅ **100% Validated** - Advanced feature generation (85+ features)
- **ML Models** (8004) - ✅ **100% Validated** - RandomForest ensemble training & serving
- **Ranking** (8005) - ✅ **100% Validated** - VOR calculations and ML-powered draft rankings
- **Orchestration** (8006) - ✅ **100% Validated** - Complete workflow coordination and monitoring

**System Validation**: 49/50 validation checkpoints passed across all services (98% success rate)

For detailed technical documentation, see [PLAN.md](./PLAN.md) | For validation reports, see [reports/validation/](./reports/validation/)

## 📈 Model Performance

Our ensemble models trained on **15 years of historical data** achieve industry-leading accuracy:

| Position | Training Samples | R² Score | RMSE (FPPG) | Core Features Used |
|----------|------------------|----------|-------------|-------------------|
| QB       | **592 samples**  | 42.5%    | 4.39        | 12 features: attempts, passing yards, TDs, rushing production |
| RB       | **1,291 samples**| 45.7%    | 3.60        | 14 features: carries, receptions, efficiency, usage shares |
| WR       | **1,856 samples**| 46.1%    | 2.52        | 13 features: targets, receiving production, catch rate |
| TE       | **989 samples**  | 40.6%    | 1.75        | 13 features: targets, receiving stats, efficiency metrics |

**Training Scale:** Models trained on **4,728+ player-seasons** (2010-2024) using time-series methodology.  
**Validation:** Realistic performance metrics (R² 40-46%) indicate genuine predictive capability without data leakage.

## 🛠️ Development & Contribution

### Requirements
- Python 3.11+
- Docker & Docker Compose
- 8GB+ RAM (for model loading)

### Running Tests
```bash
# Unit tests
pytest tests/ -v

# Integration tests
python tests/test_microservices_integration.py

# End-to-end validation
python tests/validate_end_to_end.py
```

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For detailed development guidelines, see [PLAN.md](./PLAN.md)

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

This tool provides statistical projections based on historical data. Fantasy football involves significant uncertainty and randomness. No projection system can guarantee success. Always combine data-driven insights with your own research and judgment.

## 📞 Support

- **Documentation**: [PLAN.md](./PLAN.md) for technical details
- **Issues**: [Report bugs or request features](https://github.com/yourusername/fantasy_draft_engine/issues)
- **Discussions**: [Community discussions and questions](https://github.com/yourusername/fantasy_draft_engine/discussions)

---

**🏆 Start drafting smarter with AI-powered rankings!**