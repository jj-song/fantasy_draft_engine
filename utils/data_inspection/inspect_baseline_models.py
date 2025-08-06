#!/usr/bin/env python3
"""
Baseline Model Feature Inspector

This script inspects the saved baseline models to understand what features they expect
vs. what the current feature engineering service provides. This will help diagnose the
"10 expected vs 5 provided" feature mismatch issue mentioned in the developer notes.

Usage:
    python inspect_baseline_models.py
"""

import os
import sys
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def inspect_model_features(model_path: str, position: str, model_type: str):
    """
    Inspect a single model to understand its expected features.
    
    Args:
        model_path: Path to the model file
        position: Position name (QB, RB, etc.)
        model_type: Model type (baseline, ensemble, etc.)
    
    Returns:
        Dictionary with model feature information
    """
    print(f"\n🔍 INSPECTING {position} {model_type.upper()} MODEL")
    print("=" * 60)
    
    try:
        # Load the model
        print(f"Loading model from: {model_path}")
        model = joblib.load(model_path)
        
        # Initialize result dictionary
        result = {
            'position': position,
            'model_type': model_type,
            'model_path': model_path,
            'features': [],
            'feature_count': 0,
            'model_class': str(type(model).__name__),
            'has_feature_names': False,
            'error': None
        }
        
        # Try different ways to get feature names
        print(f"Model class: {type(model).__name__}")
        
        # Method 1: Check for feature_names_in_ (scikit-learn standard)
        if hasattr(model, 'feature_names_in_'):
            features = list(model.feature_names_in_)
            result['features'] = features
            result['feature_count'] = len(features)
            result['has_feature_names'] = True
            print(f"✅ Found feature_names_in_: {len(features)} features")
            print(f"Features: {features}")
            
        # Method 2: Check for n_features_in_ (number only)
        elif hasattr(model, 'n_features_in_'):
            feature_count = model.n_features_in_
            result['feature_count'] = feature_count
            print(f"✅ Found n_features_in_: {feature_count} features")
            print("⚠️ Feature names not available, only count")
            
        # Method 3: Check if it's a wrapped model
        elif hasattr(model, 'model') and hasattr(model.model, 'feature_names_in_'):
            features = list(model.model.feature_names_in_)
            result['features'] = features
            result['feature_count'] = len(features)
            result['has_feature_names'] = True
            print(f"✅ Found feature_names_in_ in wrapped model: {len(features)} features")
            print(f"Features: {features}")
            
        # Method 4: Try to introspect other attributes
        else:
            print("⚠️ No standard feature information found")
            print("Available attributes:")
            attrs = [attr for attr in dir(model) if not attr.startswith('_')]
            for attr in attrs[:10]:  # Show first 10 attributes
                print(f"  - {attr}")
            if len(attrs) > 10:
                print(f"  ... and {len(attrs) - 10} more")
        
        return result
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return {
            'position': position,
            'model_type': model_type,
            'model_path': model_path,
            'features': [],
            'feature_count': 0,
            'model_class': 'Unknown',
            'has_feature_names': False,
            'error': str(e)
        }

def analyze_current_feature_engineering():
    """
    Analyze what features the current feature engineering service provides.
    """
    print(f"\n🔧 ANALYZING CURRENT FEATURE ENGINEERING OUTPUT")
    print("=" * 60)
    
    # Look for sample feature engineering output
    processed_data_dir = os.path.join(project_root, 'data', 'processed', 'position_specific')
    
    if os.path.exists(processed_data_dir):
        print(f"Looking for sample data in: {processed_data_dir}")
        
        # Look for any processed data files
        for file in os.listdir(processed_data_dir):
            if file.endswith('.parquet') and 'features' in file:
                file_path = os.path.join(processed_data_dir, file)
                try:
                    print(f"\nFound sample data: {file}")
                    df = pd.read_parquet(file_path)
                    print(f"Shape: {df.shape}")
                    print(f"Columns ({len(df.columns)}): {list(df.columns)}")
                    
                    # Show sample of key columns
                    key_cols = ['position', 'player_name', 'team'] 
                    available_key_cols = [col for col in key_cols if col in df.columns]
                    if available_key_cols:
                        print(f"\nSample data preview:")
                        print(df[available_key_cols].head(3).to_string())
                    
                    return {
                        'current_features': list(df.columns),
                        'current_feature_count': len(df.columns),
                        'sample_file': file,
                        'sample_shape': df.shape
                    }
                    
                except Exception as e:
                    print(f"Error reading {file}: {e}")
    
    print("⚠️ No sample feature engineering output found")
    return {
        'current_features': [],
        'current_feature_count': 0,
        'sample_file': None,
        'sample_shape': None
    }

def compare_features(model_results, current_features):
    """
    Compare model expected features vs current feature engineering.
    """
    print(f"\n🔬 FEATURE COMPATIBILITY ANALYSIS")
    print("=" * 60)
    
    # Group results by position
    positions_with_features = {}
    for result in model_results:
        if result['has_feature_names'] and result['features']:
            positions_with_features[result['position']] = result['features']
    
    print(f"Positions with known feature requirements: {list(positions_with_features.keys())}")
    print(f"Current feature engineering provides: {current_features['current_feature_count']} features")
    
    # Analyze each position
    for position, expected_features in positions_with_features.items():
        print(f"\n📊 {position} Position Analysis:")
        print(f"   Expected features: {len(expected_features)}")
        print(f"   Expected: {expected_features}")
        
        if current_features['current_features']:
            # Find matches
            current_set = set(current_features['current_features'])
            expected_set = set(expected_features)
            
            matching = expected_set.intersection(current_set)
            missing = expected_set - current_set  
            extra = current_set - expected_set
            
            print(f"   ✅ Matching features ({len(matching)}): {list(matching)}")
            print(f"   ❌ Missing features ({len(missing)}): {list(missing)}")
            print(f"   ➕ Extra features ({len(extra)}): {list(extra)[:5]}{'...' if len(extra) > 5 else ''}")
            
            # Calculate compatibility score
            compatibility = len(matching) / len(expected_features) * 100
            print(f"   🎯 Compatibility: {compatibility:.1f}%")
        else:
            print(f"   ⚠️ Cannot compare - no current feature data available")

def suggest_feature_mapping(model_results):
    """
    Suggest feature mappings based on model requirements.
    """
    print(f"\n💡 FEATURE MAPPING SUGGESTIONS")
    print("=" * 60)
    
    # Common feature mappings based on the codebase analysis
    common_mappings = {
        'age': ['birth_date', 'player_age'],
        'games_played': ['games', 'games_started'],
        'rushing_attempts': ['carries', 'rushing_att'],
        'passing_attempts': ['attempts', 'pass_att'],
        'passing_completions': ['completions', 'comp'],
        'passing_yards': ['pass_yds', 'passing_yds'],
        'passing_tds': ['pass_td', 'passing_touchdowns'],
        'interceptions': ['int', 'pass_int'],
        'rushing_yards': ['rush_yds', 'rushing_yds'],
        'rushing_tds': ['rush_td', 'rushing_touchdowns'],
        'targets': ['tgt', 'receiving_targets'],
        'receptions': ['rec', 'receiving_receptions'],
        'receiving_yards': ['rec_yds', 'receiving_yds'],
        'receiving_tds': ['rec_td', 'receiving_touchdowns']
    }
    
    # Analyze which mappings are needed
    all_expected_features = set()
    for result in model_results:
        if result['has_feature_names']:
            all_expected_features.update(result['features'])
    
    print("Suggested mappings for missing features:")
    for expected_feature in sorted(all_expected_features):
        if expected_feature in common_mappings:
            possible_sources = common_mappings[expected_feature]
            print(f"   {expected_feature} ← {possible_sources}")
        else:
            print(f"   {expected_feature} ← [needs investigation]")

def main():
    """Main function to inspect all baseline models."""
    print("🔍 BASELINE MODEL FEATURE INSPECTOR")
    print("=" * 80)
    print("This script analyzes the feature mismatch between baseline models")
    print("and the current feature engineering service.")
    print("=" * 80)
    
    # Find all baseline model files
    saved_models_dir = os.path.join(project_root, 'saved_models')
    print(f"Looking for models in: {saved_models_dir}")
    
    if not os.path.exists(saved_models_dir):
        print(f"❌ Models directory not found: {saved_models_dir}")
        return
    
    # Find all model files (baseline and ensemble)
    model_files = []
    for file in os.listdir(saved_models_dir):
        if file.endswith('.joblib'):
            if '_baseline_model.joblib' in file:
                position = file.replace('_baseline_model.joblib', '')
                model_type = 'baseline'
            elif '_ensemble_model.joblib' in file:
                position = file.replace('_ensemble_model.joblib', '')
                model_type = 'ensemble'
            else:
                continue
            model_path = os.path.join(saved_models_dir, file)
            model_files.append((position, model_path, model_type))
    
    print(f"Found {len(model_files)} models: {[(pos, mtype) for pos, _, mtype in model_files]}")
    
    # Inspect each model
    model_results = []
    for position, model_path, model_type in model_files:
        result = inspect_model_features(model_path, position, model_type)
        model_results.append(result)
    
    # Analyze current feature engineering
    current_features = analyze_current_feature_engineering()
    
    # Compare and analyze
    compare_features(model_results, current_features)
    suggest_feature_mapping(model_results)
    
    # Summary report
    print(f"\n📋 SUMMARY REPORT")
    print("=" * 60)
    
    successful_inspections = [r for r in model_results if not r['error']]
    failed_inspections = [r for r in model_results if r['error']]
    
    print(f"✅ Successfully inspected: {len(successful_inspections)} models")
    print(f"❌ Failed to inspect: {len(failed_inspections)} models")
    
    if successful_inspections:
        feature_counts = [r['feature_count'] for r in successful_inspections if r['feature_count'] > 0]
        if feature_counts:
            print(f"📊 Feature counts: {feature_counts}")
            print(f"   Average: {np.mean(feature_counts):.1f}")
            print(f"   Range: {min(feature_counts)} - {max(feature_counts)}")
        
        # Show detailed feature list for RB (the problematic position)
        rb_result = next((r for r in successful_inspections if r['position'] == 'RB'), None)
        if rb_result and rb_result['features']:
            print(f"\n🎯 RB MODEL FEATURE REQUIREMENTS (THE CRITICAL CASE):")
            print(f"   Expected features ({len(rb_result['features'])}): {rb_result['features']}")
    
    if failed_inspections:
        print(f"\n❌ Failed inspections:")
        for result in failed_inspections:
            print(f"   {result['position']}: {result['error']}")
    
    print(f"\n🚀 NEXT STEPS:")
    print("1. Update feature engineering service to provide all required features")
    print("2. Implement feature mapping in the ML models service")
    print("3. Test the fixed pipeline with Docker services")
    print("4. Validate end-to-end predictions work correctly")

if __name__ == "__main__":
    main()