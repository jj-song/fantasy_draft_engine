# Debug Instructions - Fantasy Draft Engine Services

## Overview
This guide provides step-by-step instructions for debugging each microservice in the Fantasy Draft Engine in the proper workflow order. Follow these instructions sequentially to debug the complete pipeline.

## Prerequisites
- VS Code with Python extension installed
- `.vscode/launch.json` file created (✅ DONE)
- All required dependencies installed per service
- Project opened in VS Code

## Debug Workflow Order
Debug services in this order to follow the data pipeline:
1. **Data Ingestion Service** (Port 8002) - Fetches and stores NFL data
2. **Feature Engineering Service** (Port 8003) - Processes raw data into ML features  
3. **ML Models Service** (Port 8000) - Trains and serves prediction models
4. **Ranking Service** (Port 8007) - Generates final rankings with VOR
5. **Configuration Service** (Port 8001) - Provides system configuration
6. **Orchestration Service** (Port 8005) - Coordinates the full pipeline

---

## 1. Data Ingestion Service Debug (Port 8002) - START HERE

### **Purpose**: Fetches NFL data and stores it as parquet files

### **Step-by-Step Debug Process**:

1. **Open VS Code** in project directory: `/Users/jihoonsong/Documents/projects/fantasy_draft_engine`

2. **Set Key Breakpoints** by clicking in the gutter next to these line numbers in `services/data-ingestion/src/main.py`:
   - **Line 82**: `DataIngestionService.__init__()` - Service initialization
   - **Line 143**: `startup()` - Service startup and directory creation  
   - **Line 225**: `/api/v1/data/ingest` endpoint - Main ingestion trigger
   - **Line 497**: `_run_data_ingestion()` - Background ingestion process
   - **Line 512**: `fetch_player_season_stats()` - NFL data fetching
   - **Line 518**: Data saving to parquet files
   - **Line 522**: `_clean_data()` - Data cleaning process

3. **Start Debug Session**:
   - Press **Ctrl+Shift+D** (or **Cmd+Shift+D** on Mac) to open Run and Debug panel
   - Select **"Debug Data Ingestion Service"** from dropdown
   - Press **F5** to start debugging

4. **Service Initialization** (First Breakpoint at Line 82):
   - Service will pause at initialization
   - Press **F10** to step through constructor
   - Watch for `self.config_service_url` and `self.ingestion_status` setup

5. **Startup Process** (Second Breakpoint at Line 143):
   - Press **F5** to continue to startup
   - Step through directory creation with **F10**
   - Watch `get_data_paths()` create `data/raw/` and `data/processed/` directories

6. **Service Running**: 
   - Press **F5** to complete startup
   - Service now running on **http://localhost:8002**
   - Open browser/Postman to test endpoints

7. **Test Data Status Endpoint**:
   - Browse to: http://localhost:8002/api/v1/data/status
   - Should show current data files and status

8. **Trigger Data Ingestion** (Main Debug Focus):

   **IMPORTANT**: The service runs but waits for API requests. To debug actual data processing:

   **Set Additional Breakpoints**:
   - **Line 497**: `_run_data_ingestion()` - Main data processing function
   - **Line 512**: `fetch_player_season_stats()` - NFL data fetching
   - **Line 522**: `_clean_data()` - Data cleaning process
   - **In `services/data-ingestion/src/acquisition/nfl_data_fetcher.py`**: Core NFL data fetching logic

   **Trigger Data Ingestion via API** (in new terminal):
   ```bash
   curl -X POST http://localhost:8002/api/v1/data/ingest \
     -H "Content-Type: application/json" \
     -d '{"years": [2024], "positions": ["QB"], "force_refresh": true}'
   ```

   **Alternative: Browser/Postman**:
   - URL: `POST http://localhost:8002/api/v1/data/ingest`
   - Headers: `Content-Type: application/json`
   - Body: `{"years": [2024], "positions": ["QB"], "force_refresh": true}`

9. **Step Through Data Processing Workflow**:
   - **Breakpoint 1** (Line 225): API endpoint receives ingestion request
   - **Breakpoint 2** (Line 497): Background data ingestion process starts
   - **Breakpoint 3** (Line 512): NFL data fetching begins (`fetch_player_season_stats`)
   - Use **F11** to step into NFL data API calls
   - **Breakpoint 4** (Line 522): Data cleaning and validation process
   - Watch data transformations and file I/O operations

10. **Monitor Data Flow During Debug**:
    - Watch NFL API calls and raw data structure
    - Observe data cleaning transformations (duplicates, missing values)
    - Monitor file creation in `data/raw/` and `data/processed/` folders
    - Verify player data structure and column mappings
    - Check error handling and logging output

### **Debug Commands Reference**:
- **F5**: Continue to next breakpoint
- **F10**: Step Over (execute current line)
- **F11**: Step Into (go into function calls)
- **Shift+F11**: Step Out (exit current function)
- **Ctrl+Shift+F5**: Restart debug session

### **Expected Results**:
- Service starts successfully on port 8002
- Data directories created at `data/raw/` and `data/processed/`
- NFL data fetched and saved as parquet files
- Basic data cleaning applied

---

## 2. Feature Engineering Service Debug (Port 8003) - RUN AFTER DATA INGESTION

### **Purpose**: Converts raw NFL data into ML-ready features

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/feature-engineering/src/main.py`:
   - **Service initialization**
   - **Feature processing endpoints**
   - **Core feature generation logic**

2. **Set Breakpoints** in `services/feature-engineering/src/processors/feature_engineering.py`:
   - **Main feature engineering functions**
   - **Position-specific feature creation**
   - **Data validation steps**

3. **Start Debug Session**:
   - Select **"Debug Feature Engineering Service"** from dropdown
   - Press **F5** to start debugging

4. **Service Startup**:
   - Step through initialization
   - Verify service starts on **http://localhost:8003**

5. **Trigger Feature Generation** (Main Debug Focus):

   **IMPORTANT**: Service runs but waits for API requests. To debug actual feature engineering:

   **Set Additional Breakpoints**:
   - **Line 106**: `_run_feature_generation()` - Main feature processing function
   - **In `services/feature-engineering/src/processors/feature_engineering.py`**: Core feature generation logic
   - **Position-specific feature files**: QB, RB, WR, TE feature creation functions

   **Trigger Feature Generation via API** (in new terminal):
   ```bash
   curl -X POST http://localhost:8003/api/v1/features/generate \
     -H "Content-Type: application/json" \
     -d '{"years": [2024], "positions": ["QB"], "force_regenerate": true, "include_advanced_features": true}'
   ```

   **Alternative: Browser/Postman**:
   - URL: `POST http://localhost:8003/api/v1/features/generate`
   - Headers: `Content-Type: application/json`
   - Body: `{"years": [2024], "positions": ["QB"], "force_regenerate": true, "include_advanced_features": true}`

6. **Step Through Feature Engineering Workflow**:
   - **Breakpoint 1** (Line 91): API endpoint receives feature generation request
   - **Breakpoint 2** (Line 106): Background feature generation process starts
   - **Breakpoint 3**: Core feature engineering logic in processors
   - Use **F11** to step into position-specific feature creation
   - Watch feature transformations and 28 core features generation

7. **Monitor Feature Engineering During Debug**:
   - Watch raw data loading from `data/processed/` files
   - Observe feature calculations (age, games_played, efficiency metrics)
   - Monitor 28 core features vs 144 research features decision logic
   - Verify feature quality validation (no NaN, proper data types)
   - Check feature output to `data/processed/position_specific/` directory

8. **Validation Checkpoints - Feature Engineering**:

   **IMPORTANT**: Validation checkpoints are pre-installed in Feature Engineering Service to analyze:

   **Key Validation Points**:
   - **Input Data Validation**: 81-column NFL dataset loaded correctly
   - **Feature Generation**: 144 → 28 core features transformation
   - **Position-Specific Features**: QB, RB, WR, TE features calculated correctly
   - **Feature Quality**: No NaN values, proper data types, realistic ranges
   - **Output Validation**: 28 features saved to position-specific directories

   **Add Validation Checkpoints** (if not already present):

   **In `services/feature-engineering/src/processors/feature_engineering.py`**:
   ```python
   # Add to imports at top of file
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass

   # In main feature generation function:
   def generate_features_for_position(df, position):
       # VALIDATION CHECKPOINT: Input data
       add_validation_checkpoint('feature-engineering', f'input_data_{position}', df,
                               expected_type=pd.DataFrame,
                               expected_columns=['player_name', 'position', 'games'],
                               expected_shape=(50, 81))  # ~50 players per position, 81 columns

       # ... feature generation logic ...
       
       # VALIDATION CHECKPOINT: Generated features
       add_validation_checkpoint('feature-engineering', f'generated_features_{position}', features_df,
                               expected_type=pd.DataFrame,
                               expected_shape=(50, 28))  # 28 core features expected
       
       return features_df
   ```

   **In `services/feature-engineering/src/main.py`**:
   ```python
   # Add to imports
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint, save_all_validation_reports
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass
       def save_all_validation_reports():
           return {}

   # In feature generation background task:
   async def _run_feature_generation(self, years, positions, force_regenerate, include_advanced):
       # ... existing code ...
       
       # After feature generation completes:
       if VALIDATION_ENABLED:
           validation_reports = save_all_validation_reports()
           logger.info(f"Feature engineering validation reports saved: {validation_reports}")
   ```

   **Expected Validation Results**:
   - **Input**: 81 columns NFL data → **Output**: 28 core features
   - **Feature Quality**: No NaN values, proper numeric types
   - **Position Coverage**: Features generated for all requested positions
   - **Data Integrity**: No feature generation failures or data loss

### **Expected Results**:
- Service processes raw data into 28 core ML features
- Features saved to `data/processed/position_specific/` directory
- Feature quality validation passes

---

## 3. ML Models Service Debug (Port 8000) - RUN AFTER FEATURE ENGINEERING

### **Purpose**: Loads trained models and serves predictions

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/ml-models/src/main.py`:
   - **Line 44**: Service initialization
   - **Model loading and registry setup**
   - **Prediction endpoints**

2. **Set Breakpoints** in `services/ml-models/src/serving/model_registry.py`:
   - **Model loading functions**
   - **Model validation**

3. **Set Breakpoints** in `services/ml-models/src/serving/prediction_engine.py`:
   - **Individual prediction functions**
   - **Batch prediction processing**

4. **Start Debug Session**:
   - Select **"Debug ML Models Service"** from dropdown  
   - Press **F5** to start debugging

5. **Model Loading Phase**:
   - Step through model registry initialization
   - Watch for 4 position models loading: QB, RB, WR, TE
   - Verify RandomForest models loaded successfully

6. **Test Individual Predictions** (Main Debug Focus):

   **IMPORTANT**: Service runs but waits for prediction requests. To debug actual ML predictions:

   **Set Additional Breakpoints**:
   - **Line 174**: `predict_single()` - Individual prediction endpoint
   - **Line 199**: `predict_batch()` - Batch prediction endpoint
   - **In `services/ml-models/src/serving/prediction_engine.py`**: Core prediction logic
   - **In `services/ml-models/src/serving/model_registry.py`**: Model loading and validation

   **Test Individual Prediction via API** (in new terminal):
   ```bash
   curl -X POST http://localhost:8000/api/v1/models/predict \
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

   **Test Batch Predictions via API**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/models/predict-batch \
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

7. **Step Through ML Prediction Workflow**:
   - **Breakpoint 1** (Line 174/199): API endpoint receives prediction request
   - **Breakpoint 2**: Model registry retrieves trained RandomForest model
   - **Breakpoint 3**: Feature validation and preprocessing
   - **Breakpoint 4**: Model prediction generation
   - Use **F11** to step into model.predict() calls
   - Watch prediction ranges: QB ~17 FPPG, RB ~11 FPPG, WR ~8 FPPG, TE ~7 FPPG

8. **Monitor ML Predictions During Debug**:
   - Watch model loading from `saved_models/` directory
   - Observe feature validation (28 expected features)
   - Monitor RandomForest ensemble prediction process
   - Verify prediction output format and ranges
   - Check error handling for invalid features or missing models

9. **Validation Checkpoints - ML Models Service**:

   **IMPORTANT**: Validation checkpoints analyze ML model performance and prediction quality:

   **Key Validation Points**:
   - **Model Loading**: 4 position models (QB, RB, WR, TE) load successfully
   - **Feature Compatibility**: 28 features match model expectations exactly
   - **Prediction Quality**: Outputs within realistic fantasy point ranges
   - **Batch Processing**: Multiple player predictions processed correctly
   - **Model Performance**: Predictions consistent with expected R² values

   **Add Validation Checkpoints** (if not already present):

   **In `services/ml-models/src/serving/model_registry.py`**:
   ```python
   # Add to imports at top of file
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass

   # In model loading function:
   async def load_available_models(self):
       # ... existing model loading code ...
       
       # VALIDATION CHECKPOINT: Model registry status
       registry_status = {
           'models_loaded': len(self.models),
           'available_positions': list(self.models.keys()),
           'model_types': {pos: type(model).__name__ for pos, model in self.models.items()}
       }
       add_validation_checkpoint('ml-models', 'model_registry_loaded', registry_status,
                               expected_type=dict)
       
       # Validate 4 position models loaded
       if len(self.models) != 4:
           logger.warning(f"Expected 4 models, loaded {len(self.models)}")
   ```

   **In `services/ml-models/src/serving/prediction_engine.py`**:
   ```python
   # Add to imports
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass

   # In prediction function:
   def predict_single(self, position, features):
       # VALIDATION CHECKPOINT: Input features
       add_validation_checkpoint('ml-models', f'prediction_input_{position}', features,
                               expected_type=dict)
       
       # ... prediction logic ...
       
       # VALIDATION CHECKPOINT: Prediction output
       prediction_ranges = {
           'QB': (5, 25), 'RB': (2, 20), 'WR': (1, 18), 'TE': (1, 15)
       }
       expected_range = prediction_ranges.get(position, (0, 30))
       
       add_validation_checkpoint('ml-models', f'prediction_output_{position}', prediction,
                               expected_type=float)
       
       # Validate prediction range
       if not (expected_range[0] <= prediction <= expected_range[1]):
           logger.warning(f"Prediction {prediction} outside expected range {expected_range} for {position}")
       
       return prediction
   ```

   **In `services/ml-models/src/main.py`**:
   ```python
   # Add to imports
   try:
       from utils.debug_analysis.debug_integration import save_all_validation_reports
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def save_all_validation_reports():
           return {}

   # In startup function:
   async def startup(self):
       # ... existing startup code ...
       
       # Save validation report after model loading
       if VALIDATION_ENABLED:
           validation_reports = save_all_validation_reports()
           logger.info(f"ML Models validation reports saved: {validation_reports}")
   ```

   **Expected Validation Results**:
   - **Model Loading**: 4 RandomForest models loaded successfully
   - **Feature Compatibility**: 28 features accepted by all models
   - **Prediction Ranges**: QB ~17 FPPG, RB ~11 FPPG, WR ~8 FPPG, TE ~7 FPPG
   - **Batch Processing**: Consistent predictions for multiple players
   - **Error Handling**: Proper validation for invalid inputs

### **Expected Results**:
- All 4 position models load successfully
- Predictions generate realistic fantasy point values
- Batch processing works for multiple players

---

## 4. Ranking Service Debug (Port 8007) - RUN AFTER ML MODELS

### **Purpose**: Combines ML predictions with VOR calculations for final rankings

### **Step-by-Step Debug Process**:

1. **CRITICAL: Start ML Models Service First**:
   - ML Models Service MUST be running on port 8000
   - Ranking Service calls ML service for predictions

2. **Set Key Breakpoints** in `services/ranking/src/main.py`:
   - **Line 50**: Service initialization
   - **Ranking generation endpoints**

3. **Set Breakpoints** in `services/ranking/src/scoring/scoring_engine.py`:
   - **Line 139**: ML service communication (CRITICAL - recently fixed)
   - **Prediction fetching logic**
   - **Fantasy scoring calculations**

4. **Set Breakpoints** in `services/ranking/src/calculation/vor_calculator.py`:
   - **VOR calculation logic**
   - **Replacement level calculations** 
   - **Position-specific baselines (QB15, RB36, WR36, TE15)**

5. **Start Debug Session**:
   - Select **"Debug Ranking Service"** from dropdown
   - Press **F5** to start debugging

6. **Trigger Ranking Generation** (Main Debug Focus):

   **CRITICAL PREREQUISITE**: ML Models Service MUST be running on port 8000 first!

   **Set Additional Breakpoints**:
   - **Line 147**: `generate_rankings()` - Main ranking generation endpoint
   - **Line 152**: `_run_ranking_generation()` - Background ranking process
   - **Line 233**: VOR calculation for each position
   - **In `services/ranking/src/scoring/scoring_engine.py` Line 139**: ML service communication
   - **In `services/ranking/src/calculation/vor_calculator.py`**: VOR calculation logic

   **Trigger Ranking Generation via API** (in new terminal):
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

   **Alternative: Browser/Postman**:
   - URL: `POST http://localhost:8007/api/v1/rankings/generate`
   - Headers: `Content-Type: application/json`
   - Body: `{"positions": ["QB", "RB", "WR", "TE"], "season": 2024, "tier_assignments": true, "sort_by": "vor"}`

7. **Step Through Ranking Generation Workflow**:
   - **Breakpoint 1** (Line 147): API endpoint receives ranking request
   - **Breakpoint 2** (Line 152): Background ranking generation starts
   - **Breakpoint 3** (Line 139 in scoring_engine.py): HTTP call to ML Models Service at `http://localhost:8000`
   - **Breakpoint 4** (Line 233): VOR calculation for each position
   - Use **F11** to step into VOR calculations and ML service calls
   - Watch complete 569 player ranking process

8. **Monitor Ranking Generation During Debug**:
   - **Service Communication**: Verify HTTP calls to ML Models Service succeed
   - **ML Predictions**: Watch predictions being fetched for all players
   - **VOR Calculations**: Monitor baselines (QB15, RB36, WR36, TE15) and VOR formula
   - **Replacement Levels**: Watch replacement level calculations per position
   - **Final Rankings**: Observe complete ranking and sorting by VOR
   - **Export Process**: Check CSV/JSON export to `data/draft_lists/` directory

9. **Validation Checkpoints - Ranking Service**:

   **IMPORTANT**: Validation checkpoints analyze VOR calculations and ranking quality:

   **Key Validation Points**:
   - **Service Communication**: ML Models Service responds correctly
   - **ML Predictions**: All players receive realistic predictions
   - **VOR Calculations**: Replacement levels calculated correctly (QB15, RB36, WR36, TE15)
   - **Ranking Quality**: Top players have highest VOR, realistic hierarchy
   - **Export Data**: 569 players ranked and exported correctly
   - **Data Integrity**: No players lost during ranking process

   **Add Validation Checkpoints** (if not already present):

   **In `services/ranking/src/scoring/scoring_engine.py`**:
   ```python
   # Add to imports at top of file
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass

   # In ML service communication function:
   def fetch_ml_predictions(self, players_data):
       # VALIDATION CHECKPOINT: Input data for ML predictions
       add_validation_checkpoint('ranking', 'ml_prediction_input', players_data,
                               expected_type=list)
       
       # ... ML service HTTP calls ...
       
       # VALIDATION CHECKPOINT: ML predictions received
       add_validation_checkpoint('ranking', 'ml_predictions_received', predictions,
                               expected_type=list)
       
       # Validate prediction counts match player counts
       if len(predictions) != len(players_data):
           logger.warning(f"Prediction count mismatch: {len(predictions)} != {len(players_data)}")
       
       return predictions
   ```

   **In `services/ranking/src/calculation/vor_calculator.py`**:
   ```python
   # Add to imports
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass

   # In VOR calculation function:
   def calculate_vor(self, predictions_df):
       # VALIDATION CHECKPOINT: Input predictions
       add_validation_checkpoint('ranking', 'vor_input_predictions', predictions_df,
                               expected_type=pd.DataFrame,
                               expected_columns=['player_name', 'position', 'predicted_points'])
       
       # ... VOR calculation logic ...
       
       # VALIDATION CHECKPOINT: Replacement levels
       replacement_levels = {
           'QB': predictions_df[predictions_df['position'] == 'QB']['predicted_points'].nlargest(15).iloc[-1],
           'RB': predictions_df[predictions_df['position'] == 'RB']['predicted_points'].nlargest(36).iloc[-1],
           'WR': predictions_df[predictions_df['position'] == 'WR']['predicted_points'].nlargest(36).iloc[-1],
           'TE': predictions_df[predictions_df['position'] == 'TE']['predicted_points'].nlargest(15).iloc[-1]
       }
       add_validation_checkpoint('ranking', 'replacement_levels', replacement_levels,
                               expected_type=dict)
       
       # ... continue VOR calculations ...
       
       # VALIDATION CHECKPOINT: Final VOR results
       add_validation_checkpoint('ranking', 'vor_calculations', vor_df,
                               expected_type=pd.DataFrame,
                               expected_columns=['player_name', 'position', 'predicted_points', 'vor_value'],
                               expected_shape=(569, 5))  # ~569 players expected
       
       return vor_df
   ```

   **In `services/ranking/src/main.py`**:
   ```python
   # Add to imports
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint, save_all_validation_reports
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass
       def save_all_validation_reports():
           return {}

   # In ranking generation background task:
   async def _run_ranking_generation(self, positions, season, tier_assignments, include_overrides, sort_by):
       # ... existing ranking generation code ...
       
       # VALIDATION CHECKPOINT: Final rankings
       add_validation_checkpoint('ranking', 'final_rankings', final_rankings_df,
                               expected_type=pd.DataFrame,
                               expected_columns=['player_name', 'position', 'rank', 'vor_value'])
       
       # Validate top 10 players have positive VOR
       top_10_vor = final_rankings_df.head(10)['vor_value']
       if any(vor <= 0 for vor in top_10_vor):
           logger.warning("Top 10 players should have positive VOR values")
       
       # After ranking generation completes:
       if VALIDATION_ENABLED:
           validation_reports = save_all_validation_reports()
           logger.info(f"Ranking validation reports saved: {validation_reports}")
   ```

   **In `services/ranking/src/outputs/cheatsheet_generator.py`**:
   ```python
   # Add to imports
   try:
       from utils.debug_analysis.debug_integration import add_validation_checkpoint
       VALIDATION_ENABLED = True
   except ImportError:
       VALIDATION_ENABLED = False
       def add_validation_checkpoint(*args, **kwargs):
           pass

   # In export function:
   def export_rankings(self, rankings_df, format='csv'):
       # VALIDATION CHECKPOINT: Export data
       add_validation_checkpoint('ranking', f'export_data_{format}', rankings_df,
                               expected_type=pd.DataFrame)
       
       # ... export logic ...
       
       # VALIDATION CHECKPOINT: Export file created
       export_info = {
           'format': format,
           'player_count': len(rankings_df),
           'file_size_mb': os.path.getsize(export_path) / 1024 / 1024 if os.path.exists(export_path) else 0
       }
       add_validation_checkpoint('ranking', f'export_completed_{format}', export_info,
                               expected_type=dict)
       
       return export_path
   ```

   **Expected Validation Results**:
   - **Service Communication**: ML Models Service responds with predictions for all players
   - **VOR Calculations**: Replacement levels (QB15: ~17 FPPG, RB36: ~4.5 FPPG, etc.)
   - **Player Coverage**: ~569 players processed and ranked
   - **Ranking Quality**: Top players are elite RBs/WRs, positive VOR values
   - **Export Success**: CSV/JSON files created with complete rankings

### **Expected Results**:
- Successful communication with ML Models Service
- VOR calculations using correct baselines
- 569 players ranked and exported
- Top players have realistic VOR values

---

## 5. Configuration Service Debug (Port 8001) - SUPPORT SERVICE

### **Purpose**: Provides centralized configuration for all services

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/configuration/src/main.py`:
   - Service initialization
   - Configuration endpoints

2. **Start Debug Session**:
   - Select **"Debug Configuration Service"** from dropdown
   - Press **F5** to start debugging

3. **Test Configuration Endpoints**:
   - GET configuration data
   - Verify YAML config loading
   - Test configuration updates

### **Expected Results**:
- Configuration service provides settings to other services
- YAML configurations load correctly

---

## 6. Orchestration Service Debug (Port 8005) - WORKFLOW COORDINATOR

### **Purpose**: Coordinates the complete pipeline workflow

### **Step-by-Step Debug Process**:

1. **Set Key Breakpoints** in `services/orchestration/src/main.py`:
   - Service initialization
   - Workflow coordination logic

2. **Start Debug Session**:
   - Select **"Debug Orchestration Service"** from dropdown
   - Press **F5** to start debugging

3. **Test Full Pipeline**:
   - Trigger complete workflow
   - Step through service coordination
   - Monitor inter-service communication

### **Expected Results**:
- Orchestration service coordinates all other services
- Complete pipeline executes successfully

---

## Validation System Integration

### **Automatic Variable & Output Analysis**

Each service now includes validation checkpoints that automatically analyze:
- **Data types, shapes, and column names** at each processing step
- **Value ranges and data quality** (nulls, outliers, realistic values)
- **Pipeline integrity** (data loss, transformations, consistency)
- **Expected outputs** based on your developer notes specifications

### **Validation Reports Location**
All validation reports are saved to: `reports/debug_validation_[service]_[timestamp].json`

### **How to Enable Validation**
Validation checkpoints are already integrated into all services. Simply run your debug sessions normally and validation reports will be automatically generated.

---

## Complete Debug Session Workflow

### **How to Run the Complete Debug Workflow**:

1. **Start with Data Ingestion Service** (Port 8002)
   - Follow Section 1 above
   - Verify data files created in `data/raw/` and `data/processed/`

2. **Continue with Feature Engineering Service** (Port 8003)  
   - Follow Section 2 above
   - Verify 28 core features generated

3. **Then ML Models Service** (Port 8000)
   - Follow Section 3 above  
   - Verify 4 position models loaded and serving predictions

4. **Next Ranking Service** (Port 8007)
   - **IMPORTANT**: Keep ML Models Service running!
   - Follow Section 4 above
   - Verify complete rankings generated with VOR

5. **Optional Support Services**:
   - Configuration Service (Port 8001)
   - Orchestration Service (Port 8005)

### **Key Validation Checkpoints**:

After debugging each service, verify:

**✅ Data Ingestion**: 
- Files exist: `data/raw/player_stats_2024.parquet`
- Files exist: `data/processed/player_stats_2024.parquet`
- Data contains NFL player stats with correct columns

**✅ Feature Engineering**:
- 28 core features generated (not 144)
- No missing values in critical features
- Features saved to `data/processed/position_specific/`

**✅ ML Models Service**:
- 4 models loaded: QB, RB, WR, TE
- Individual predictions work (realistic FPPG values)
- Batch predictions process multiple players

**✅ Ranking Service**:  
- Successfully calls ML Models Service
- VOR calculations use correct baselines (QB15, RB36, WR36, TE15)
- 569 players ranked and exported to CSV
- Top players have realistic rankings

### **Debug Session Management**:

**Starting Multiple Services**:
1. Start first service in debug mode
2. Let it complete initialization 
3. Open **new VS Code window** for next service
4. OR use **Ctrl+Shift+F5** to restart with different configuration

**Service Dependencies**:
- **Ranking Service** requires **ML Models Service** running
- Other services are independent
- Configuration Service is optional but recommended

**Port Reference** (All Services):
- Data Ingestion: 8002
- Feature Engineering: 8003  
- ML Models: 8000
- Ranking: 8007
- Configuration: 8001
- Orchestration: 8005

### **API Trigger Commands Quick Reference**:

**Data Ingestion Service** (Port 8002) - ✅ Validation Enabled:
```bash
curl -X POST http://localhost:8002/api/v1/data/ingest \
  -H "Content-Type: application/json" \
  -d '{"years": [2024], "positions": ["QB"], "force_refresh": true}'
```
*Generates validation report: `reports/debug_validation_data-ingestion_[timestamp].json`*

**Feature Engineering Service** (Port 8003) - 🔧 Add Validation Checkpoints:
```bash
curl -X POST http://localhost:8003/api/v1/features/generate \
  -H "Content-Type: application/json" \
  -d '{"years": [2024], "positions": ["QB"], "force_regenerate": true, "include_advanced_features": true}'
```
*After adding checkpoints, generates: `reports/debug_validation_feature-engineering_[timestamp].json`*

**ML Models Service** (Port 8000) - 🔧 Add Validation Checkpoints:
```bash
curl -X POST http://localhost:8000/api/v1/models/predict \
  -H "Content-Type: application/json" \
  -d '{"position": "QB", "player_data": {"player_name": "Josh Allen"}, "features": {"age": 27, "games_played": 16, "passing_attempts": 560}}'
```
*After adding checkpoints, generates: `reports/debug_validation_ml-models_[timestamp].json`*

**Ranking Service** (Port 8007) - 🔧 Add Validation Checkpoints - **Requires ML Models Service running**:
```bash
curl -X POST http://localhost:8007/api/v1/rankings/generate \
  -H "Content-Type: application/json" \
  -d '{"positions": ["QB", "RB", "WR", "TE"], "season": 2024, "tier_assignments": true, "sort_by": "vor"}'
```
*After adding checkpoints, generates: `reports/debug_validation_ranking_[timestamp].json`*

### **Validation Report Analysis**:

After running each service with validation checkpoints, check:

1. **View validation summary**: `cat reports/debug_validation_[service]_[timestamp].json | head -10`
2. **Check success rate**: Look for `"success_rate": 100.0` in the report
3. **Review issues**: Check `"issues": []` arrays for any data quality problems
4. **Data shapes**: Verify expected DataFrame shapes match reality
5. **Create summary reports**: Use the detailed JSON for comprehensive analysis

---

## Complete Validation Workflow

### **Step-by-Step Validation Setup**

**Phase 1: Data Ingestion Service** (✅ Already Complete)
1. Service already has validation checkpoints
2. Run debug session and trigger data ingestion
3. Validation report automatically generated in `reports/`

**Phase 2: Feature Engineering Service** (🔧 Setup Required)
1. Add validation checkpoints using code examples above
2. Run debug session and trigger feature generation
3. Verify 81 columns → 28 features transformation

**Phase 3: ML Models Service** (🔧 Setup Required) 
1. Add validation checkpoints to model loading and prediction functions
2. Run debug session and test predictions
3. Verify 4 models loaded, realistic prediction ranges

**Phase 4: Ranking Service** (🔧 Setup Required)
1. Add validation checkpoints to VOR calculations and service communication
2. Run debug session with ML Models Service running
3. Verify 569 players ranked, correct VOR baselines

### **Validation Success Metrics**

**Data Ingestion**: ✅ 100% success rate achieved
- 81 columns NFL data with advanced metrics
- 78 QBs for single position test
- All merge steps successful

**Feature Engineering** (Target Metrics):
- 81 input columns → 28 output features
- No NaN values in critical features
- Features saved to position-specific directories

**ML Models** (Target Metrics):
- 4 position models loaded successfully
- Predictions within expected ranges (QB ~17 FPPG, etc.)
- 28 features accepted by all models

**Ranking** (Target Metrics):
- Service communication with ML Models successful
- VOR baselines calculated correctly (QB15, RB36, WR36, TE15)
- 569 players ranked and exported
- Top players have positive VOR values

### **Debugging with Validation Reports**

**Real-Time Analysis**: As you debug each service, validation checkpoints provide immediate feedback on:
- Data quality at each processing step
- Expected vs actual data shapes and types
- Realistic value ranges and calculations
- Pipeline integrity and data flow

**Post-Debug Analysis**: Validation reports provide comprehensive analysis for:
- Comparing expected vs actual results
- Identifying data quality issues
- Verifying pipeline performance
- Documenting system behavior

---

## Technical Reference (Advanced Debugging)

### Service Debug Configurations
1. Create/update `.vscode/launch.json` with this configuration:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug ML Models Service",
            "type": "python",
            "request": "launch",
            "module": "services.ml-models.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services",
                "ML_MODELS_PORT": "8000"
            },
            "args": [],
            "justMyCode": false
        }
    ]
}
```

2. **Set Breakpoints**: Open `services/ml-models/src/main.py` and click in the gutter next to line numbers
3. **Start Debug**: Press F5 or use Debug → Start Debugging
4. **Service runs on**: http://localhost:8000

#### **Command Line Debug (pdb)**
```bash
# Navigate to project root
cd /Users/jihoonsong/Documents/projects/fantasy_draft_engine

# Add pdb breakpoint in code where you want to debug:
# import pdb; pdb.set_trace()

# Run with Python debugger
python -m pdb -m services.ml-models.src.main
```

#### **Key Debug Points in ML Models Service**
- `services/ml-models/src/main.py:44` - Service initialization
- `services/ml-models/src/serving/model_registry.py` - Model loading
- `services/ml-models/src/serving/prediction_engine.py` - Prediction logic
- `services/ml-models/src/training/model_trainer.py` - Model training

---

### 2. Ranking Service (Port 8007)

#### **VS Code Debug Setup**
Add this to `.vscode/launch.json`:
```json
{
    "name": "Debug Ranking Service",
    "type": "python",
    "request": "launch",
    "module": "services.ranking.src.main",
    "cwd": "${workspaceFolder}",
    "console": "integratedTerminal",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services",
        "RANKING_PORT": "8007"
    },
    "args": [],
    "justMyCode": false
}
```

#### **Command Line Debug (pdb)**
```bash
cd /Users/jihoonsong/Documents/projects/fantasy_draft_engine
python -m pdb -m services.ranking.src.main
```

#### **Key Debug Points in Ranking Service**
- `services/ranking/src/main.py:50` - Service initialization
- `services/ranking/src/scoring/scoring_engine.py:139` - ML service communication
- `services/ranking/src/calculation/vor_calculator.py` - VOR calculations
- `services/ranking/src/outputs/cheatsheet_generator.py` - Export functionality

---

### 3. Feature Engineering Service (Port 8003)

#### **VS Code Debug Setup**
Add this to `.vscode/launch.json`:
```json
{
    "name": "Debug Feature Engineering Service",
    "type": "python",
    "request": "launch",
    "module": "services.feature-engineering.src.main",
    "cwd": "${workspaceFolder}",
    "console": "integratedTerminal",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services",
        "FEATURE_ENG_PORT": "8003"
    },
    "args": [],
    "justMyCode": false
}
```

#### **Command Line Debug (pdb)**
```bash
cd /Users/jihoonsong/Documents/projects/fantasy_draft_engine
python -m pdb -m services.feature-engineering.src.main
```

#### **Key Debug Points in Feature Engineering**
- `services/feature-engineering/src/main.py` - Service initialization
- `services/feature-engineering/src/processors/feature_engineering.py` - Core feature logic
- `services/feature-engineering/src/position_features/` - Position-specific features
- `services/feature-engineering/src/quality/data_quality_validator.py` - Quality checks

---

### 4. Configuration Service (Port 8001)

#### **VS Code Debug Setup**
Add this to `.vscode/launch.json`:
```json
{
    "name": "Debug Configuration Service",
    "type": "python",
    "request": "launch",
    "module": "services.configuration.src.main",
    "cwd": "${workspaceFolder}",
    "console": "integratedTerminal",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services",
        "CONFIG_PORT": "8001"
    },
    "args": [],
    "justMyCode": false
}
```

#### **Command Line Debug (pdb)**
```bash
cd /Users/jihoonsong/Documents/projects/fantasy_draft_engine
python -m pdb -m services.configuration.src.main
```

---

### 5. Data Ingestion Service (Port 8002)

#### **VS Code Debug Setup**
Add this to `.vscode/launch.json`:
```json
{
    "name": "Debug Data Ingestion Service",
    "type": "python",
    "request": "launch",
    "module": "services.data-ingestion.src.main",
    "cwd": "${workspaceFolder}",
    "console": "integratedTerminal",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services",
        "DATA_INGESTION_PORT": "8002"
    },
    "args": [],
    "justMyCode": false
}
```

#### **Command Line Debug (pdb)**
```bash
cd /Users/jihoonsong/Documents/projects/fantasy_draft_engine
python -m pdb -m services.data-ingestion.src.main
```

---

### 6. Orchestration Service (Port 8005)

#### **VS Code Debug Setup**
Add this to `.vscode/launch.json`:
```json
{
    "name": "Debug Orchestration Service",
    "type": "python",
    "request": "launch",
    "module": "services.orchestration.src.main",
    "cwd": "${workspaceFolder}",
    "console": "integratedTerminal",
    "env": {
        "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services",
        "ORCHESTRATION_PORT": "8005"
    },
    "args": [],
    "justMyCode": false
}
```

#### **Command Line Debug (pdb)**
```bash
cd /Users/jihoonsong/Documents/projects/fantasy_draft_engine
python -m pdb -m services.orchestration.src.main
```

---

## Complete VS Code Debug Configuration

Create this complete `.vscode/launch.json` file:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug ML Models Service",
            "type": "python",
            "request": "launch",
            "module": "services.ml-models.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services"
            },
            "justMyCode": false
        },
        {
            "name": "Debug Ranking Service",
            "type": "python",
            "request": "launch",
            "module": "services.ranking.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services"
            },
            "justMyCode": false
        },
        {
            "name": "Debug Feature Engineering Service",
            "type": "python",
            "request": "launch",
            "module": "services.feature-engineering.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services"
            },
            "justMyCode": false
        },
        {
            "name": "Debug Configuration Service",
            "type": "python",
            "request": "launch",
            "module": "services.configuration.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services"
            },
            "justMyCode": false
        },
        {
            "name": "Debug Data Ingestion Service",
            "type": "python",
            "request": "launch",
            "module": "services.data-ingestion.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services"
            },
            "justMyCode": false
        },
        {
            "name": "Debug Orchestration Service",
            "type": "python",
            "request": "launch",
            "module": "services.orchestration.src.main",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}:${workspaceFolder}/services"
            },
            "justMyCode": false
        }
    ]
}
```

## Debugging Workflow

### **Step-by-Step Process**

1. **Choose Your Service**: Select which service you want to debug
2. **Set Breakpoints**: Click in the gutter next to line numbers where you want to pause execution
3. **Start Debugging**: 
   - **VS Code**: Select the appropriate debug configuration and press F5
   - **Command Line**: Use the `python -m pdb` commands above
4. **Step Through Code**:
   - **F10**: Step Over (execute current line)
   - **F11**: Step Into (go into function calls)
   - **Shift+F11**: Step Out (exit current function)
   - **F5**: Continue (run until next breakpoint)

### **Common Debug Commands (pdb)**
When using command-line debugging:
```
(Pdb) l          # List current code
(Pdb) n          # Next line (step over)
(Pdb) s          # Step into function
(Pdb) c          # Continue execution
(Pdb) p variable # Print variable value
(Pdb) pp variable # Pretty print variable
(Pdb) h          # Help
(Pdb) q          # Quit debugger
```

## Service Communication Testing

### **Test Service Integration**
1. **Start ML Models Service** in debug mode first (port 8000)
2. **Start Ranking Service** in debug mode (port 8007)
3. **Set breakpoints** in ranking service where it calls ML service
4. **Trigger ranking generation** to see the full flow

### **Key Integration Points to Debug**
- `services/ranking/src/scoring/scoring_engine.py:139` - Where ranking service calls ML service
- `services/ml-models/src/serving/prediction_engine.py` - Where predictions are generated
- `services/ranking/src/calculation/vor_calculator.py` - Where VOR calculations happen

## Recommended Debug Targets

### **Critical Validation Points**
Based on developer notes, focus debugging on:

1. **Feature Engineering Quality** - Debug `services/feature-engineering/src/processors/feature_engineering.py`
2. **ML Model Predictions** - Debug `services/ml-models/src/serving/prediction_engine.py`
3. **VOR Calculations** - Debug `services/ranking/src/calculation/vor_calculator.py`
4. **Service Communication** - Debug `services/ranking/src/scoring/scoring_engine.py`

### **Expected Values to Validate**
While debugging, check for:
- **Feature Count**: Should generate 28 core features
- **Player Count**: Should process ~569 players
- **Prediction Ranges**: QB ~17 FPPG, RB ~11 FPPG, WR ~8 FPPG, TE ~7 FPPG
- **VOR Baselines**: QB15, RB36, WR36, TE15

## Troubleshooting

### **Common Issues**
1. **Module Import Errors**: Ensure PYTHONPATH includes project root and services directory
2. **Port Conflicts**: Each service uses a different port (see above)
3. **Service Dependencies**: Some services depend on others being running
4. **Data Path Issues**: Services expect data files in specific locations

### **Port Reference**
- ML Models Service: 8000
- Configuration Service: 8001
- Data Ingestion Service: 8002
- Feature Engineering Service: 8003
- Orchestration Service: 8005
- Ranking Service: 8007

Start with the ML Models Service and Ranking Service as these are the core integration points mentioned in the developer notes.