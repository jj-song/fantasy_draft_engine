#!/usr/bin/env python3
"""
Simple Model Training Script

Trains position-specific models for fantasy football predictions.
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import lightgbm as lgb

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Removed old dummy data function - now using centralized data.loaders module

def train_position_model(position):
    """Train a model for a specific position using real NFL data."""
    print(f"Training model for {position}...")
    
    # Use feature engineering to get real data
    sys.path.insert(0, str(project_root / 'src'))
    from feature_engineering import engineer_features_for_season
    import config
    
    # Collect data from multiple seasons for training
    all_data = []
    
    # Use multiple years of data for better training (2020-2022)
    training_years = [2020, 2021, 2022]
    
    for year in training_years:
        try:
            print(f"Loading real data for {position} from {year} season...")
            df_year = engineer_features_for_season(year)
            
            if df_year is not None and not df_year.empty:
                # Filter for position and ensure we have target variable
                position_df = df_year[df_year['position'] == position].copy()
                
                # Only use data where we have the target variable
                if 'fantasy_points_per_game' in position_df.columns:
                    position_df = position_df.dropna(subset=['fantasy_points_per_game'])
                    
                if not position_df.empty:
                    all_data.append(position_df)
                    print(f"✅ Added {len(position_df)} {position} players from {year}")
                else:
                    print(f"⚠️ No {position} players with valid target data from {year}")
            else:
                print(f"⚠️ No feature data available for {year}")
                
        except Exception as e:
            print(f"⚠️ Could not load data for {year}: {e}")
    
    if not all_data:
        print(f"❌ No training data available for {position}")
        return None
        
    # Combine all years
    df = pd.concat(all_data, ignore_index=True)
    print(f"✅ Combined training data: {len(df)} {position} player-seasons")
    
    # Filter for position
    df = df[df['position'] == position].copy()
    
    if len(df) < 10:
        print(f"Not enough data for {position} ({len(df)} samples)")
        return None
    
    # Prepare features
    feature_cols = [col for col in df.columns if col not in [
        'player_id', 'player_name', 'position', 'team', 'season', 'fantasy_points',
        'fantasy_points_per_game'
    ]]
    
    X = df[feature_cols].fillna(0)
    y = df['fantasy_points_per_game']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train models
    models = {}
    
    # Baseline: Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_r2 = r2_score(y_test, rf_pred)
    models['baseline'] = {'model': rf, 'r2': rf_r2}
    
    # Advanced: LightGBM
    lgb_model = lgb.LGBMRegressor(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        n_jobs=-1
    )
    lgb_model.fit(X_train, y_train)
    lgb_pred = lgb_model.predict(X_test)
    lgb_r2 = r2_score(y_test, lgb_pred)
    models['advanced_engineering'] = {'model': lgb_model, 'r2': lgb_r2}
    
    # Basic engineering (just feature selection)
    # Use top 10 features by importance
    feature_importance = lgb_model.feature_importances_
    top_features_idx = np.argsort(feature_importance)[-10:]
    top_features = [feature_cols[i] for i in top_features_idx]
    
    X_train_basic = X_train[top_features]
    X_test_basic = X_test[top_features]
    
    basic_model = lgb.LGBMRegressor(
        n_estimators=150,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        n_jobs=-1
    )
    basic_model.fit(X_train_basic, y_train)
    basic_pred = basic_model.predict(X_test_basic)
    basic_r2 = r2_score(y_test, basic_pred)
    models['basic_engineering'] = {'model': basic_model, 'r2': basic_r2}
    
    # Save models
    models_dir = project_root / 'saved_models'
    models_dir.mkdir(exist_ok=True)
    
    for model_type, model_info in models.items():
        model_path = models_dir / f'{position}_{model_type}_model.joblib'
        joblib.dump(model_info['model'], model_path)
        print(f"Saved {position} {model_type} model (R²: {model_info['r2']:.3f})")
    
    return models

def main():
    """Train models for all positions."""
    # Import config for consistent position handling
    sys.path.insert(0, str(project_root))
    import config
    
    # Use core positions + K (DST training to be added later)
    positions = config.CORE_POSITIONS + ['K']
    
    print("Training position-specific models...")
    
    all_results = {}
    for position in positions:
        try:
            results = train_position_model(position)
            if results:
                all_results[position] = results
                print(f"✅ {position} models trained successfully")
            else:
                print(f"❌ Failed to train {position} models")
        except Exception as e:
            print(f"❌ Error training {position}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("MODEL TRAINING SUMMARY")
    print("="*60)
    
    for position, models in all_results.items():
        print(f"\n{position}:")
        for model_type, model_info in models.items():
            print(f"  {model_type:20} R²: {model_info['r2']:.3f}")
    
    print(f"\n✅ Training complete! Models saved to saved_models/")

if __name__ == "__main__":
    main()