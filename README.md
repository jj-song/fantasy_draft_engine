# Fantasy Draft Engine 🏈

**AI-powered fantasy football draft rankings** using machine learning and comprehensive NFL data analysis. Built with production-ready microservices architecture and streamlined feature engineering for reliable predictions.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![ML Models](https://img.shields.io/badge/ML-RandomForest%20Ensemble-green.svg)](https://scikit-learn.org/)
[![Microservices](https://img.shields.io/badge/Architecture-Microservices-blue.svg)](./PLAN.md)
[![Docker](https://img.shields.io/badge/Deployment-Docker%20Compose-blue.svg)](https://docker.com/)
[![Production Ready](https://img.shields.io/badge/Status-Ranking%20Service%20Integration%20Complete-brightgreen.svg)](./DEVELOPER_NOTES.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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

# Launch microservices
docker-compose up -d

# Generate ML-powered rankings
python generate_draft_rankings.py
```

### Option 2: Direct Execution

```bash
# Install dependencies
pip install -r requirements.txt

# Test ML models integration
python test_ranking_service_integration.py

# Generate draft rankings with ML predictions
python generate_draft_rankings.py
```

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

**6-Service Microservices Architecture:**

- **Configuration** (8001) - Centralized settings and league configurations
- **Data Ingestion** (8002) - ✅ **Production Ready** - NFL data acquisition and cleaning
- **Feature Engineering** (8003) - ✅ **Production Ready** - Core statistical feature generation
- **ML Models** (8004) - ✅ **Production Ready** - RandomForest model training and prediction serving
- **Ranking** (8005) - ✅ **Production Ready** - VOR calculations and ML-powered draft rankings
- **Orchestration** (8006) - 🔄 Development Phase - Workflow coordination and monitoring

For detailed technical documentation, see [PLAN.md](./PLAN.md)

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