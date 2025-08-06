#!/usr/bin/env python3
"""
Test Feature Compatibility Integration

This script tests that the feature mapping fixes the "10 expected vs 5 provided"
issue by simulating the ML models service prediction flow with actual baseline models.
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# Add project paths
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services', 'ml-models', 'src'))

# Import our feature compatibility module
ml_models_path = os.path.join(project_root, 'services', 'ml-models', 'src')
sys.path.insert(0, ml_models_path)
from utils.feature_compatibility import FeatureCompatibilityMapper

def test_baseline_model_compatibility():
    """Test that feature mapping works with actual baseline models."""
    print("🧪 TESTING BASELINE MODEL COMPATIBILITY")
    print("=" * 60)
    
    # Initialize feature mapper
    mapper = FeatureCompatibilityMapper()
    
    # Create sample current data (like what feature engineering provides)
    sample_current_data = pd.DataFrame({
        'player_id': ['player_1', 'player_2', 'player_3'],
        'player_name': ['Test Player 1', 'Test Player 2', 'Test Player 3'],
        'position': ['RB', 'RB', 'RB'],
        'team': ['KC', 'BUF', 'SF'],
        'age': [25, 27, 24],
        'games': [16, 14, 12],  # This should map to games_played
        'carries': [200, 150, 100],  # This should map to rushing_attempts
        'rushing_yards': [1000, 800, 500],
        'rushing_tds': [8, 6, 3],
        'targets': [50, 40, 30],
        'receptions': [40, 35, 25],
        'receiving_yards': [400, 300, 200],
        'receiving_tds': [2, 3, 1],
        # Add many extra features (like current data has 177 features)
        'fantasy_points': [200, 150, 100],
        'air_yards_share': [0.1, 0.08, 0.05],
        'wopr': [0.15, 0.12, 0.08],
        'target_share': [0.2, 0.18, 0.15]
    })
    
    print(f"Sample current data shape: {sample_current_data.shape}")
    print(f"Sample columns: {list(sample_current_data.columns)}")
    
    # Test RB position (the one that was failing)
    position = 'RB'
    print(f"\n🏃 Testing {position} position mapping:")
    
    try:
        # Map features for RB
        mapped_features = mapper.map_features_for_position(sample_current_data, position)
        print(f"✅ Mapping successful!")
        print(f"   Mapped shape: {mapped_features.shape}")
        print(f"   Mapped columns: {list(mapped_features.columns)}")
        
        # Validate the mapping
        validation = mapper.validate_mapped_features(mapped_features, position)
        print(f"   Validation passed: {validation['validation_passed']}")
        
        if not validation['validation_passed']:
            print(f"   Missing features: {validation['missing_features']}")
            print(f"   Features with nulls: {validation['features_with_nulls']}")
        
        # Show sample mapped data
        print(f"\n📊 Sample mapped data:")
        print(mapped_features.head(2).to_string())
        
        return mapped_features, True
        
    except Exception as e:
        print(f"❌ Mapping failed: {e}")
        return None, False

def test_with_actual_baseline_model():
    """Test predictions with actual baseline model."""
    print(f"\n🤖 TESTING WITH ACTUAL BASELINE MODEL")
    print("=" * 60)
    
    # Try to load actual RB baseline model
    model_path = os.path.join(project_root, 'saved_models', 'RB_baseline_model.joblib')
    
    if not os.path.exists(model_path):
        print(f"❌ Baseline model not found: {model_path}")
        return False
    
    try:
        # Load the model
        print(f"Loading model from: {model_path}")
        model = joblib.load(model_path)
        print(f"✅ Model loaded: {type(model).__name__}")
        
        # Check expected features
        if hasattr(model, 'feature_names_in_'):
            expected_features = list(model.feature_names_in_)
            print(f"   Expected features ({len(expected_features)}): {expected_features}")
        else:
            print(f"   No feature_names_in_ attribute found")
            return False
        
        # Get mapped features from the previous test
        mapped_features, mapping_success = test_baseline_model_compatibility()
        
        if not mapping_success:
            print(f"❌ Cannot test model - mapping failed")
            return False
        
        # Test prediction
        print(f"\n🎯 Testing model prediction:")
        print(f"   Input shape: {mapped_features.shape}")
        print(f"   Expected features: {len(expected_features)}")
        print(f"   Provided features: {len(mapped_features.columns)}")
        
        # Make prediction
        predictions = model.predict(mapped_features)
        print(f"✅ Predictions successful!")
        print(f"   Predictions: {predictions}")
        print(f"   Prediction range: {predictions.min():.2f} - {predictions.max():.2f}")
        
        # Validate predictions are reasonable for RB
        reasonable_range = (1.0, 25.0)  # Reasonable range for RB fantasy points per game
        if all(reasonable_range[0] <= pred <= reasonable_range[1] for pred in predictions):
            print(f"✅ Predictions are within reasonable range {reasonable_range}")
        else:
            print(f"⚠️ Some predictions outside reasonable range {reasonable_range}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model prediction failed: {e}")
        import traceback
        print(f"   Full error: {traceback.format_exc()}")
        return False

def test_all_positions():
    """Test feature mapping for all positions."""
    print(f"\n🌟 TESTING ALL POSITIONS")
    print("=" * 60)
    
    mapper = FeatureCompatibilityMapper()
    positions = ['QB', 'RB', 'WR', 'TE']
    
    results = {}
    
    for position in positions:
        print(f"\n📊 Testing {position}:")
        
        # Create position-appropriate sample data
        sample_data = pd.DataFrame({
            'age': [26],
            'games': [16],
            'attempts': [400] if position == 'QB' else [0],
            'completions': [250] if position == 'QB' else [0],
            'passing_yards': [3500] if position == 'QB' else [0],
            'passing_tds': [25] if position == 'QB' else [0],
            'interceptions': [10] if position == 'QB' else [0],
            'carries': [50] if position in ['QB', 'RB', 'WR'] else [0],
            'rushing_yards': [300] if position in ['QB', 'RB', 'WR'] else [0],
            'rushing_tds': [3] if position in ['QB', 'RB', 'WR'] else [0],
            'targets': [80] if position in ['RB', 'WR', 'TE'] else [0],
            'receptions': [60] if position in ['RB', 'WR', 'TE'] else [0],
            'receiving_yards': [800] if position in ['RB', 'WR', 'TE'] else [0],
            'receiving_tds': [6] if position in ['RB', 'WR', 'TE'] else [0],
        })
        
        try:
            mapped = mapper.map_features_for_position(sample_data, position)
            validation = mapper.validate_mapped_features(mapped, position)
            
            results[position] = {
                'mapping_success': True,
                'validation_passed': validation['validation_passed'],
                'expected_features': validation['expected_feature_count'],
                'provided_features': validation['actual_feature_count'],
                'missing_features': validation['missing_features']
            }
            
            print(f"   ✅ Mapping: Success")
            print(f"   ✅ Validation: {'Pass' if validation['validation_passed'] else 'Fail'}")
            print(f"   📊 Features: {validation['actual_feature_count']}/{validation['expected_feature_count']}")
            
        except Exception as e:
            results[position] = {
                'mapping_success': False,
                'error': str(e)
            }
            print(f"   ❌ Failed: {e}")
    
    # Summary
    print(f"\n📋 SUMMARY:")
    successful = sum(1 for r in results.values() if r.get('mapping_success', False))
    print(f"   Successful mappings: {successful}/{len(positions)}")
    
    for position, result in results.items():
        if result.get('mapping_success'):
            status = "✅" if result.get('validation_passed') else "⚠️"
            print(f"   {status} {position}: {result.get('provided_features', 0)}/{result.get('expected_features', 0)} features")
        else:
            print(f"   ❌ {position}: Failed")
    
    return results

def main():
    """Main test function."""
    print("🧪 FEATURE COMPATIBILITY INTEGRATION TEST")
    print("=" * 80)
    print("This tests the fix for the '10 expected vs 5 provided' feature mismatch")
    print("=" * 80)
    
    # Test 1: Basic feature mapping
    mapping_results = test_all_positions()
    
    # Test 2: Integration with actual baseline model
    model_test_success = test_with_actual_baseline_model()
    
    # Final summary
    print(f"\n🎯 FINAL TEST RESULTS")
    print("=" * 60)
    
    mapping_success_count = sum(1 for r in mapping_results.values() if r.get('mapping_success', False))
    validation_success_count = sum(1 for r in mapping_results.values() if r.get('validation_passed', False))
    
    print(f"✅ Feature mapping: {mapping_success_count}/4 positions")
    print(f"✅ Feature validation: {validation_success_count}/4 positions")
    print(f"✅ Baseline model test: {'Pass' if model_test_success else 'Fail'}")
    
    if mapping_success_count == 4 and validation_success_count == 4 and model_test_success:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"   The feature mismatch issue should now be resolved.")
        print(f"   RB predictions should work in the microservices pipeline.")
    else:
        print(f"\n⚠️ SOME TESTS FAILED")
        print(f"   Review the errors above and fix before proceeding.")
    
    return mapping_success_count == 4 and validation_success_count == 4 and model_test_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)