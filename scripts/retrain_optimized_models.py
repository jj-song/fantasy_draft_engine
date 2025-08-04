#!/usr/bin/env python3
"""
Retrain Models with Optimized Hyperparameters

This script retrains all position models using the optimized hyperparameters
defined in config.py, providing improved performance without requiring
extensive hyperparameter search.

Usage:
    python scripts/retrain_optimized_models.py                # Retrain all positions
    python scripts/retrain_optimized_models.py --positions QB RB  # Retrain specific positions
"""

import os
import sys
import pandas as pd
import numpy as np
import argparse
import joblib
from typing import Dict, List
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import our modules
import config
from src.modeling import RandomForestModel, LightGBMModel
from src.feature_engineering import engineer_features_for_season
from src.training_evaluation import calculate_evaluation_metrics

def load_training_data_for_position(position: str) -> pd.DataFrame:
    """
    Load training data for a specific position.
    
    Args:
        position: Player position to load data for
        
    Returns:
        DataFrame with training data
    """
    print(f"Loading training data for {position}...")
    
    position_data_list = []
    training_years = list(range(config.DATA_START_YEAR, config.TRAINING_DATA_END_YEAR + 1))
    
    for year in training_years:
        try:
            # Get engineered features for this year
            year_data = engineer_features_for_season(
                year, 
                include_matchup_intelligence=True,
                include_position_specific_features=True
            )
            
            if year_data is not None and not year_data.empty:
                # Filter for position
                position_year_data = year_data[year_data['position'] == position].copy()
                
                if not position_year_data.empty:
                    position_data_list.append(position_year_data)
                    print(f"   Loaded {len(position_year_data)} {position} players from {year}")
                
        except Exception as e:
            print(f"   Warning: Could not load {position} data for {year}: {e}")
            continue
    
    if position_data_list:
        # Combine all years
        combined_data = pd.concat(position_data_list, ignore_index=True)
        
        # Ensure we have the target variable
        if 'fantasy_points_per_game' not in combined_data.columns:
            print(f"   Warning: Missing target variable for {position}")
            return pd.DataFrame()
        
        # Remove rows with missing target values
        combined_data = combined_data.dropna(subset=['fantasy_points_per_game'])
        
        print(f"✅ Loaded {len(combined_data)} total {position} player-seasons")
        return combined_data
    else:
        print(f"   Warning: No data found for {position}")
        return pd.DataFrame()

def get_feature_columns(data: pd.DataFrame) -> List[str]:
    """Extract feature columns from the dataset."""
    exclude_cols = {
        'player_id', 'player_name', 'team', 'position', 'season',
        'fantasy_points', 'fantasy_points_per_game', 'fantasy_points_ppr',
        'next_season_fppg', 'games', 'games_played'
    }
    
    feature_cols = []
    for col in data.columns:
        if col not in exclude_cols and pd.api.types.is_numeric_dtype(data[col]):
            feature_cols.append(col)
    
    return feature_cols

def train_optimized_model(position: str, model_type: str, X: pd.DataFrame, y: pd.Series) -> object:
    """
    Train a model with optimized hyperparameters for the given position.
    
    Args:
        position: Player position
        model_type: 'random_forest' or 'lightgbm'
        X: Training features
        y: Training targets
        
    Returns:
        Trained model object
    """
    print(f"   Training optimized {model_type} for {position}...")
    
    # Get optimized hyperparameters from config
    if hasattr(config, 'OPTIMIZED_HYPERPARAMETERS'):
        optimized_params = config.OPTIMIZED_HYPERPARAMETERS.get(model_type, {}).get(position, {})
    else:
        optimized_params = {}
    
    # Create model with optimized parameters
    if model_type == 'random_forest':
        model = RandomForestModel(model_params=optimized_params)
    elif model_type == 'lightgbm':
        model = LightGBMModel(model_params=optimized_params)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    
    # Train the model
    if model_type == 'lightgbm' and len(X) > 100:
        # Use validation set for LightGBM early stopping
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        model.train(X_train, y_train, X_val, y_val)
    else:
        model.train(X, y)
    
    return model

def validate_model_improvement(
    old_model_path: str,
    new_model: object,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    position: str,
    model_type: str
) -> Dict[str, float]:
    """
    Compare performance of old vs new model.
    
    Args:
        old_model_path: Path to the old model file
        new_model: New trained model
        X_test: Test features
        y_test: Test targets
        position: Player position
        model_type: Model type
        
    Returns:
        Dictionary with performance comparison
    """
    results = {
        'position': position,
        'model_type': model_type,
        'old_model_available': False,
        'new_r2': 0.0,
        'new_rmse': 0.0,
        'old_r2': 0.0,
        'old_rmse': 0.0,
        'r2_improvement': 0.0,
        'rmse_improvement': 0.0
    }
    
    # Test new model
    try:
        new_predictions = new_model.predict(X_test)
        new_metrics = calculate_evaluation_metrics(y_test, new_predictions)
        results['new_r2'] = new_metrics['R2']
        results['new_rmse'] = new_metrics['RMSE']
    except Exception as e:
        print(f"   Warning: Could not test new model: {e}")
        return results
    
    # Test old model if it exists
    if os.path.exists(old_model_path):
        try:
            old_model = joblib.load(old_model_path)
            old_predictions = old_model.predict(X_test)
            old_metrics = calculate_evaluation_metrics(y_test, old_predictions)
            results['old_r2'] = old_metrics['R2']
            results['old_rmse'] = old_metrics['RMSE']
            results['old_model_available'] = True
            
            # Calculate improvements
            results['r2_improvement'] = results['new_r2'] - results['old_r2']
            results['rmse_improvement'] = results['old_rmse'] - results['new_rmse']
            
        except Exception as e:
            print(f"   Warning: Could not load/test old model: {e}")
    
    return results

def retrain_position_models(position: str, save_models: bool = True) -> Dict[str, Dict[str, float]]:
    """
    Retrain both RandomForest and LightGBM models for a specific position.
    
    Args:
        position: Player position to retrain
        save_models: Whether to save the retrained models
        
    Returns:
        Dictionary with performance results for both model types
    """
    print(f"\n🔄 Retraining models for {position} position...")
    
    # Load training data
    data = load_training_data_for_position(position)
    
    if data.empty:
        print(f"   ❌ No training data available for {position}")
        return {}
    
    # Prepare features and target
    feature_cols = get_feature_columns(data)
    if not feature_cols:
        print(f"   ❌ No feature columns found for {position}")
        return {}
    
    X = data[feature_cols]
    y = data['fantasy_points_per_game']
    
    # Split data for validation (use last 20% as test set)
    split_idx = int(len(data) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"   📊 Training set: {len(X_train)} samples")
    print(f"   📊 Test set: {len(X_test)} samples")
    print(f"   📊 Features: {len(feature_cols)}")
    
    position_results = {}
    models_dir = os.path.join(project_root, 'saved_models')
    os.makedirs(models_dir, exist_ok=True)
    
    for model_type in ['random_forest', 'lightgbm']:
        try:
            # Train optimized model
            model = train_optimized_model(position, model_type, X_train, y_train)
            
            # Validate improvement
            old_model_path = os.path.join(models_dir, f"{position}_advanced_engineering_model.joblib")
            validation_results = validate_model_improvement(
                old_model_path, model, X_test, y_test, position, model_type
            )
            
            position_results[model_type] = validation_results
            
            # Print results
            print(f"   📈 {model_type.replace('_', ' ').title()}:")
            print(f"      New R²: {validation_results['new_r2']:.4f}")
            print(f"      New RMSE: {validation_results['new_rmse']:.4f}")
            
            if validation_results['old_model_available']:
                print(f"      R² improvement: {validation_results['r2_improvement']:+.4f}")
                print(f"      RMSE improvement: {validation_results['rmse_improvement']:+.4f}")
            else:
                print(f"      (No previous model for comparison)")
            
            # Save model if requested
            if save_models:
                # Save as advanced_engineering model (the highest tier)
                model_filename = f"{position}_advanced_engineering_model.joblib"
                model_path = os.path.join(models_dir, model_filename)
                joblib.dump(model, model_path)
                print(f"   💾 Saved model to: {model_filename}")
                
        except Exception as e:
            print(f"   ❌ Failed to train {model_type} for {position}: {e}")
            continue
    
    return position_results

def create_retraining_report(all_results: Dict[str, Dict[str, Dict[str, float]]]) -> None:
    """
    Create a summary report of the retraining results.
    
    Args:
        all_results: Dictionary containing all retraining results
    """
    print("\n" + "="*80)
    print("📊 MODEL RETRAINING SUMMARY REPORT")
    print("="*80)
    
    if not all_results:
        print("No results to report.")
        return
    
    total_positions = len(all_results)
    positions_with_improvements = 0
    total_r2_improvement = 0
    total_rmse_improvement = 0
    model_count = 0
    
    print(f"\nPositions Retrained: {total_positions}")
    print("\nDetailed Results:")
    print("-" * 60)
    
    for position, position_results in all_results.items():
        print(f"\n{position} Position:")
        
        position_has_improvement = False
        
        for model_type, results in position_results.items():
            print(f"  {model_type.replace('_', ' ').title()}:")
            print(f"    R²: {results['new_r2']:.4f}")
            print(f"    RMSE: {results['new_rmse']:.4f}")
            
            if results['old_model_available']:
                print(f"    R² improvement: {results['r2_improvement']:+.4f}")
                print(f"    RMSE improvement: {results['rmse_improvement']:+.4f}")
                
                if results['r2_improvement'] > 0:
                    position_has_improvement = True
                
                total_r2_improvement += results['r2_improvement']
                total_rmse_improvement += results['rmse_improvement']
                model_count += 1
            else:
                print(f"    (New model - no comparison available)")
        
        if position_has_improvement:
            positions_with_improvements += 1
    
    # Calculate averages
    if model_count > 0:
        avg_r2_improvement = total_r2_improvement / model_count
        avg_rmse_improvement = total_rmse_improvement / model_count
        
        print(f"\nOverall Performance:")
        print(f"  Positions with improvements: {positions_with_improvements}/{total_positions}")
        print(f"  Average R² improvement: {avg_r2_improvement:+.4f}")
        print(f"  Average RMSE improvement: {avg_rmse_improvement:+.4f}")
        
        # Determine overall success
        if avg_r2_improvement > 0 and positions_with_improvements > total_positions / 2:
            print(f"  🎉 Overall Status: SUCCESSFUL OPTIMIZATION")
        elif avg_r2_improvement > 0:
            print(f"  ✅ Overall Status: MODEST IMPROVEMENTS")
        else:
            print(f"  ⚠️ Overall Status: MIXED RESULTS")
    else:
        print(f"\nNo comparison data available (all new models)")
    
    print(f"\nNext Steps:")
    print(f"  1. Run draft ranking generation to see impact on player rankings")
    print(f"  2. Compare new rankings against previous versions")
    print(f"  3. Validate that enhanced features are being utilized correctly")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Retrain Fantasy Football models with optimized hyperparameters',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--positions',
        nargs='*',
        default=['QB', 'RB', 'WR', 'TE'],
        help='Positions to retrain (default: all core positions)'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save retrained models (validation only)'
    )
    
    return parser.parse_args()

def main():
    """Main function to retrain models with optimized hyperparameters."""
    print("🔧 Fantasy Football Model Retraining with Optimized Hyperparameters")
    print("="*80)
    
    # Parse arguments
    args = parse_arguments()
    
    print(f"📊 Retraining positions: {args.positions}")
    print(f"💾 Save models: {'❌ NO' if args.no_save else '✅ YES'}")
    print("="*80)
    
    # Retrain models for each position
    all_results = {}
    
    for position in args.positions:
        try:
            position_results = retrain_position_models(position, save_models=not args.no_save)
            if position_results:
                all_results[position] = position_results
        except Exception as e:
            print(f"❌ Failed to retrain {position}: {e}")
            continue
    
    # Create summary report
    create_retraining_report(all_results)
    
    print(f"\n🎉 Model retraining complete!")
    
    if not args.no_save and all_results:
        print(f"✅ Optimized models have been saved and are ready for use")
        print(f"🚀 Run 'python scripts/generate_draft_rankings.py --include-matchup-intelligence' to generate improved rankings")

if __name__ == "__main__":
    main()