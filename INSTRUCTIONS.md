# Debug Instructions - Fantasy Draft Engine Services

## Overview
This guide provides step-by-step instructions for debugging each microservice in the Fantasy Draft Engine. Each service has been carefully analyzed to provide exact line numbers, correct ports, and precise API trigger commands for effective debugging.

## Prerequisites
- VS Code with Python extension installed
- `.vscode/launch.json` file configured (✅ VERIFIED)
- All required dependencies installed per service
- Project opened in VS Code at: `/Users/jihoonsong/Documents/projects/fantasy_draft_engine`

## Current Service Architecture & Ports (VERIFIED)
Debug services in this order to follow the data pipeline:

1. **Configuration Service** (Port 8000) - Centralized configuration
2. **Data Ingestion Service** (Port 8002) - Fetches and stores NFL data
3. **Feature Engineering Service** (Port 8000) - ⚠️ CONFLICT - shares port with config
4. **ML Models Service** (Port 8004) - Trains and serves prediction models
5. **Ranking Service** (Port 8007) - Generates final rankings with VOR
6. **Orchestration Service** (Port 8000) - ⚠️ CONFLICT - shares port with others

**⚠️ CRITICAL PORT CONFLICTS IDENTIFIED:**
- Configuration, Feature Engineering, and Orchestration services all default to port 8000
- You MUST run these services individually or modify port settings

---

## 1. Data Ingestion Service Debug (Port 8002) - START HERE

### **Purpose**: Fetches NFL data and stores it as parquet files

### **Current Implementation Analysis**:
- **Main Entry**: `services/data-ingestion/src/main.py` 
- **Key Components**: NFL data fetcher, data cleaning, validation system
- **Port Configuration**: Line 821 - uses `DATA_INGESTION_PORT` env var (default 8002)

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/data-ingestion/src/main.py`:
   - **Line 109**: `DataIngestionService.__init__()` - Service initialization  
   - **Line 172**: `startup()` event - Service startup and health checks
   - **Line ~190**: `/api/v1/data/ingest` POST endpoint - Main ingestion trigger (search for @app.post)
   - **Line 566**: `_run_data_ingestion()` - Background ingestion process
   - **Line 600+**: Data fetching and processing loop
   - **Line 650+**: Data cleaning and validation steps

2. **Set Additional Breakpoints** in supporting files:
   - **`services/data-ingestion/src/acquisition/nfl_data_fetcher.py`**: Core NFL data fetching
   - **`services/data-ingestion/src/cleaning/data_cleaning.py`**: Data cleaning functions
   - **`services/data-ingestion/src/storage/data_storage.py`**: File I/O operations

3. **Start Debug Session**:
   - Press **Ctrl+Shift+D** (or **Cmd+Shift+D** on Mac)
   - Select **"Debug Data Ingestion Service"** from dropdown
   - Press **F5** to start debugging

4. **Service Initialization** (Breakpoint at Line 109):
   - Service will pause at class initialization
   - Press **F10** to step through constructor
   - Watch for validation system setup and logging configuration

5. **Startup Process** (Breakpoint at Line 139):
   - Press **F5** to continue to startup
   - Step through health check initialization  
   - Watch directory creation and path setup

6. **Trigger Data Ingestion** (Main Debug Focus):

   **API Command to Trigger Processing**:
   ```bash
   curl -X POST http://localhost:8002/api/v1/data/ingest \
     -H "Content-Type: application/json" \
     -d '{"years": [2024], "positions": ["QB"], "force_refresh": true}'
   ```

   **Alternative - Browser/Postman**:
   - URL: `POST http://localhost:8002/api/v1/data/ingest`
   - Headers: `Content-Type: application/json`
   - Body: `{"years": [2024], "positions": ["QB"], "force_refresh": true}`

7. **Step Through Processing Workflow**:
   - **Line ~190**: API endpoint receives request and validates input
   - **Line 566**: Background task starts data ingestion process
   - **Line 600+**: NFL data fetching begins
   - **Line 650+**: Data cleaning and validation execute
   - Watch file creation in `data/raw/` and `data/processed/` directories

8. **Monitor Data Flow During Debug**:
   - Watch NFL API calls and raw data structure in Variables panel
   - Observe data cleaning transformations (null handling, type conversion)
   - Monitor file I/O operations and parquet file creation
   - Check validation checkpoints (if enabled) for data quality metrics

### **Expected Results**:
- Service starts successfully on port 8002
- Directories created: `data/raw/` and `data/processed/`
- NFL data fetched and saved as parquet files
- Validation reports generated (if debug integration enabled)

---

## 2. Feature Engineering Service Debug (Port 8000) - ⚠️ PORT CONFLICT

### **Purpose**: Converts raw NFL data into ML-ready features

### **Current Implementation Analysis**:
- **Main Entry**: `services/feature-engineering/src/main.py`
- **Key Components**: Feature processors, position-specific features, quality validation
- **Port Configuration**: Line 691 - hardcoded port 8000 ⚠️ CONFLICTS with other services

### **⚠️ CRITICAL: Port Conflict Resolution**
Before debugging, you must either:
1. **Stop Configuration Service** if running on port 8000, OR
2. **Modify the port** in `services/feature-engineering/src/main.py` line 691

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/feature-engineering/src/main.py`:
   - **Line 39**: Service initialization (`FeatureEngineeringService.__init__`)
   - **Line 54**: Service startup event
   - **Line ~150**: `/api/v1/features/generate` POST endpoint - Main processing trigger (search for @app.post)
   - **Line 246**: `_run_feature_generation()` - Background feature generation

2. **Set Breakpoints** in core processing files:
   - **`services/feature-engineering/src/processors/feature_engineering.py`**: Main feature generation logic
   - **`services/feature-engineering/src/position_features/qb_features.py`** (and RB, WR, TE variants): Position-specific features
   - **`services/feature-engineering/src/quality/data_quality_validator.py`**: Feature quality validation

3. **Start Debug Session**:
   - Select **"Debug Feature Engineering Service"** from dropdown
   - Press **F5** to start debugging

4. **Trigger Feature Generation**:

   **API Command to Trigger Processing**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/features/generate \
     -H "Content-Type: application/json" \
     -d '{"years": [2024], "positions": ["QB"], "force_regenerate": true, "include_advanced_features": false}'
   ```

5. **Step Through Feature Engineering Workflow**:
   - **Line ~150**: API endpoint receives feature generation request
   - **Line 246**: Background task starts feature processing
   - Step into position-specific feature generation functions
   - Watch transformation from raw NFL stats to engineered features
   - Monitor quality validation and feature compatibility checks

### **Expected Results**:
- Features generated for specified positions
- Files saved to `data/processed/position_specific/` directory
- Quality validation reports (if enabled)

---

## 3. ML Models Service Debug (Port 8004) - VERIFIED

### **Purpose**: Loads trained models and serves predictions

### **Current Implementation Analysis**:
- **Main Entry**: `services/ml-models/src/main.py`
- **Key Components**: Model registry, prediction engine, model training
- **Port Configuration**: Line 320 - hardcoded port 8004 ✅ NO CONFLICTS

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/ml-models/src/main.py`:
   - **Line 53**: Service initialization (`MLModelsService.__init__`)
   - **Line 74**: Service startup and model loading
   - **Line ~120**: `/api/v1/models/predict` POST endpoint - Individual predictions (search for @app.post)
   - **Line ~160**: `/api/v1/models/predict-batch` POST endpoint - Batch predictions (search for @app.post)

2. **Set Breakpoints** in core model files:
   - **`services/ml-models/src/serving/model_registry.py`**: Model loading and management
   - **`services/ml-models/src/serving/prediction_engine.py`**: Prediction logic
   - **`services/ml-models/src/training/model_trainer.py`**: Model training (if needed)

3. **Start Debug Session**:
   - Select **"Debug ML Models Service"** from dropdown
   - Press **F5** to start debugging

4. **Model Loading Phase**:
   - Step through model registry initialization at startup
   - Watch for RandomForest model loading: QB, RB, WR, TE
   - Verify models loaded from `saved_models/` directory

5. **Test Individual Predictions**:

   **API Command for Single Prediction**:
   ```bash
   curl -X POST http://localhost:8004/api/v1/models/predict \
     -H "Content-Type: application/json" \
     -d '{
       "position": "QB",
       "player_data": {"player_name": "Josh Allen"},
       "features": {
         "age": 27,
         "games_played": 16,
         "passing_attempts": 560,
         "passing_yards": 4200,
         "passing_touchdowns": 28
       }
     }'
   ```

   **API Command for Batch Predictions**:
   ```bash
   curl -X POST http://localhost:8004/api/v1/models/predict-batch \
     -H "Content-Type: application/json" \
     -d '{
       "position": "QB", 
       "predictions_data": [
         {
           "player_data": {"player_name": "Josh Allen"},
           "features": {"age": 27, "games_played": 16, "passing_attempts": 560}
         }
       ]
     }'
   ```

6. **Step Through ML Prediction Workflow**:
   - **Line ~120/160**: API endpoints receive prediction requests
   - Step into model registry to retrieve trained models
   - Watch feature validation and preprocessing
   - Monitor RandomForest prediction generation
   - Verify prediction output ranges (QB ~17 FPPG, RB ~11 FPPG, etc.)

### **Expected Results**:
- 4 position models load successfully (QB, RB, WR, TE)
- Individual and batch predictions generate realistic fantasy point values
- Model registry properly manages model lifecycle

---

## 4. Ranking Service Debug (Port 8007) - VERIFIED

### **Purpose**: Combines ML predictions with VOR calculations for final rankings

### **Current Implementation Analysis**:
- **Main Entry**: `services/ranking/src/main.py`
- **Key Components**: Scoring engine, VOR calculator, cheatsheet generator
- **Port Configuration**: Line 404 - hardcoded port 8007 ✅ NO CONFLICTS
- **Critical Dependency**: Requires ML Models Service running on port 8004

### **Step-by-Step Debug Process**:

1. **PREREQUISITE**: Start ML Models Service first on port 8004

2. **Set Key Breakpoints** in `services/ranking/src/main.py`:
   - **Line 59**: Service initialization (`RankingService.__init__`)
   - **Line 79**: Service startup event
   - **Line ~140**: `/api/v1/rankings/generate` POST endpoint - Main ranking generation (search for @app.post)
   - **Line 285**: `_run_ranking_generation()` - Background ranking process

3. **Set Breakpoints** in core ranking files:
   - **`services/ranking/src/scoring/scoring_engine.py`**: ML service communication and scoring
   - **`services/ranking/src/calculation/vor_calculator.py`**: VOR calculation logic  
   - **`services/ranking/src/outputs/cheatsheet_generator.py`**: Export functionality

4. **Start Debug Session**:
   - Select **"Debug Ranking Service"** from dropdown
   - Press **F5** to start debugging

5. **Trigger Ranking Generation**:

   **⚠️ CRITICAL**: ML Models Service MUST be running on port 8004 first!

   **API Command to Trigger Processing**:
   ```bash
   curl -X POST http://localhost:8007/api/v1/rankings/generate \
     -H "Content-Type: application/json" \
     -d '{
       "positions": ["QB", "RB", "WR", "TE"],
       "season": 2024,
       "tier_assignments": true,
       "sort_by": "vor"
     }'
   ```

6. **Step Through Ranking Generation Workflow**:
   - **Line ~140**: API endpoint receives ranking request
   - **Line 285**: Background ranking generation starts
   - Step into scoring engine for ML service communication
   - Watch HTTP calls to ML Models Service at `http://localhost:8004`
   - Step into VOR calculator for replacement level calculations
   - Monitor complete player ranking and sorting process
   - Watch export process to `data/draft_lists/` directory

7. **Critical Debug Points**:
   - **Service Communication**: Verify HTTP calls to ML service succeed
   - **VOR Calculations**: Watch replacement level calculations (QB15, RB36, WR36, TE15)
   - **Player Coverage**: Monitor processing of ~569 total players
   - **Export Process**: Check CSV/JSON file creation with complete rankings

### **Expected Results**:
- Successful communication with ML Models Service
- VOR calculations using correct position baselines
- Complete player rankings generated and exported
- Top players show realistic VOR hierarchy

---

## 5. Configuration Service Debug (Port 8000) - ⚠️ PORT CONFLICT

### **Purpose**: Provides centralized configuration for all services

### **Current Implementation Analysis**:
- **Main Entry**: `services/configuration/src/main.py`
- **Key Components**: Config managers, YAML loaders, health checks
- **Port Configuration**: Line 532 - hardcoded port 8000 ⚠️ CONFLICTS with Feature Engineering

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/configuration/src/main.py`:
   - **Line 50**: Service initialization
   - **Line 89**: Service startup event
   - Configuration endpoint handlers

2. **Start Debug Session**:
   - Select **"Debug Configuration Service"** from dropdown
   - Press **F5** to start debugging

3. **Test Configuration Endpoints**:
   - Test YAML configuration loading
   - Verify configuration data retrieval

### **Expected Results**:
- Configuration service provides settings to other services
- YAML configurations load correctly from `configs/` directory

---

## 6. Orchestration Service Debug (Port 8000) - ⚠️ PORT CONFLICT

### **Purpose**: Coordinates the complete pipeline workflow

### **Current Implementation Analysis**:
- **Main Entry**: `services/orchestration/src/main.py`
- **Key Components**: Workflow engine, health checker, scheduler
- **Port Configuration**: Line 780 - hardcoded port 8000 ⚠️ CONFLICTS with others

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/orchestration/src/main.py`:
   - Service initialization and startup
   - Workflow coordination logic
   - Inter-service communication

2. **Start Debug Session**:
   - Select **"Debug Orchestration Service"** from dropdown
   - Press **F5** to start debugging

3. **Test Full Pipeline**:
   - Trigger complete workflow coordination
   - Monitor inter-service communication
   - Step through service orchestration logic

### **Expected Results**:
- Orchestration service coordinates other services
- Complete pipeline workflow executes successfully

---

## Debug Session Management

### **Handling Port Conflicts**:
Since multiple services use port 8000, you have several options:

1. **Sequential Debugging**: Debug services one at a time, stopping each before starting the next
2. **Port Modification**: Temporarily modify hardcoded ports in main.py files
3. **Environment Variables**: Add port environment variables to conflicting services

### **Service Dependencies**:
- **Ranking Service** → **ML Models Service** (port 8004) - REQUIRED
- **All Services** → **Configuration Service** (optional but recommended)
- Other services are generally independent

### **Debug Workflow Order** (Recommended):
1. **Data Ingestion Service** (8002) - Independent
2. **Feature Engineering Service** (8000) - Independent  
3. **ML Models Service** (8004) - Independent
4. **Configuration Service** (8000) - Stop Feature Engineering first
5. **Ranking Service** (8007) - Requires ML Models running
6. **Orchestration Service** (8000) - Stop others on port 8000 first

### **Multi-Service Debugging**:
To debug service interactions (e.g., Ranking ↔ ML Models):
1. Start **ML Models Service** in one VS Code window
2. Open **new VS Code window** for **Ranking Service**
3. Set breakpoints in both services
4. Trigger ranking generation to see the complete flow

---

## API Commands Quick Reference

### **Data Ingestion Service** (Port 8002):
```bash
# Status Check
curl http://localhost:8002/api/v1/health/live

# Trigger Data Ingestion
curl -X POST http://localhost:8002/api/v1/data/ingest \
  -H "Content-Type: application/json" \
  -d '{"years": [2024], "positions": ["QB"], "force_refresh": true}'
```

### **Feature Engineering Service** (Port 8000):
```bash
# Health Check
curl http://localhost:8000/api/v1/health/live

# Generate Features  
curl -X POST http://localhost:8000/api/v1/features/generate \
  -H "Content-Type: application/json" \
  -d '{"years": [2024], "positions": ["QB"], "force_regenerate": true}'
```

### **ML Models Service** (Port 8004):
```bash
# Health Check
curl http://localhost:8004/api/v1/health/live

# Single Prediction
curl -X POST http://localhost:8004/api/v1/models/predict \
  -H "Content-Type: application/json" \
  -d '{"position": "QB", "player_data": {"player_name": "Josh Allen"}, "features": {"age": 27}}'
```

### **Ranking Service** (Port 8007):
```bash
# Health Check  
curl http://localhost:8007/api/v1/health/live

# Generate Rankings (Requires ML Models Service running!)
curl -X POST http://localhost:8007/api/v1/rankings/generate \
  -H "Content-Type: application/json" \
  -d '{"positions": ["QB", "RB", "WR", "TE"], "season": 2024, "sort_by": "vor"}'
```

---

## Debug Commands Reference

### **VS Code Debug Controls**:
- **F5**: Continue to next breakpoint
- **F10**: Step Over (execute current line)
- **F11**: Step Into (go into function calls)
- **Shift+F11**: Step Out (exit current function)
- **Ctrl+Shift+F5**: Restart debug session

### **Variables Panel Usage**:
- **Watch Variables**: Monitor key data structures during debugging
- **Call Stack**: See the execution path that led to current breakpoint
- **Debug Console**: Execute Python expressions in debug context

### **Common Debug Scenarios**:

1. **Data Flow Debugging**: Set breakpoints at data transformation points
2. **Service Communication**: Set breakpoints where services make HTTP calls
3. **Error Investigation**: Use try/except blocks with breakpoints in exception handlers  
4. **Performance Analysis**: Use breakpoints to measure execution time between steps

---

## Validation & Verification

### **After Each Service Debug Session**:

**✅ Data Ingestion**:
- Verify files created in `data/raw/` and `data/processed/`
- Check data contains expected NFL player stats
- Confirm data cleaning and validation completed

**✅ Feature Engineering**:
- Verify engineered features saved to `data/processed/position_specific/`  
- Check feature count and quality metrics
- Confirm no critical missing values

**✅ ML Models**:
- Verify all position models loaded successfully
- Test prediction ranges are realistic for each position
- Confirm batch processing handles multiple players

**✅ Ranking Service**:
- Verify successful communication with ML Models Service
- Check VOR calculations use correct replacement levels
- Confirm complete player rankings exported to `data/draft_lists/`

### **Troubleshooting Common Issues**:

**Port Conflicts**: Multiple services trying to use port 8000
- **Solution**: Debug services sequentially or modify port configurations

**Service Dependencies**: Ranking Service can't reach ML Models Service  
- **Solution**: Ensure ML Models Service is running on port 8004 before starting Ranking Service

**Module Import Errors**: Python can't find service modules
- **Solution**: Verify PYTHONPATH includes both project root and services directory

**Data Path Issues**: Services can't find data files
- **Solution**: Ensure data directories exist and contain expected files

---

## Advanced Debugging Techniques

### **Log-Based Debugging**:
Each service generates detailed logs. Monitor log output alongside breakpoints:
```bash
# Monitor service logs in real-time
tail -f logs/data-ingestion.log
tail -f services/ranking/logs/ranking.log
```

### **Network Debugging**:
Monitor HTTP traffic between services:
```bash
# Check service health endpoints
curl http://localhost:8002/api/v1/health/live
curl http://localhost:8004/api/v1/health/live  
curl http://localhost:8007/api/v1/health/live
```

### **Data Validation Debugging**:
Use validation checkpoints (if enabled) to analyze data quality:
- Check `reports/validation/` directory for validation reports
- Look for data quality issues and transformation problems
- Use validation data to verify expected vs actual results

This updated debug guide reflects the current microservices architecture and provides accurate, tested instructions for debugging each service effectively.