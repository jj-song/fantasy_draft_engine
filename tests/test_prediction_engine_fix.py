#!/usr/bin/env python3
"""
Test Prediction Engine Feature Mapping Fix

This script directly tests the updated prediction engine to verify that the
feature mapping fix resolves the "10 expected vs 5 provided" error.
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
import asyncio
from unittest.mock import Mock

# Add project paths
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
ml_models_path = os.path.join(project_root, 'services', 'ml-models', 'src')
sys.path.insert(0, ml_models_path)

# Import the updated prediction engine
from serving.prediction_engine import PredictionEngine
from serving.model_registry import ModelRegistry

class MockModelRegistry:
    """Mock model registry for testing."""
    
    def __init__(self):
        self.models = {}
        self._load_baseline_models()
    
    def _load_baseline_models(self):
        """Load actual baseline models for testing."""
        models_dir = os.path.join(project_root, 'saved_models')
        
        for position in ['QB', 'RB', 'WR', 'TE']:
            model_path = os.path.join(models_dir, f'{position}_baseline_model.joblib')
            if os.path.exists(model_path):
                model = joblib.load(model_path)
                self.models[f"{position}_baseline"] = model
                print(f"✅ Loaded {position} baseline model")
    
    async def get_model(self, position: str, model_type: str = "baseline"):
        """Get model by position and type."""
        key = f"{position}_{model_type}"
        return self.models.get(key)
    
    async def get_registry_status(self):
        """Get registry status."""
        available_positions = []
        for key in self.models.keys():
            position = key.split('_')[0]
            if position not in available_positions:
                available_positions.append(position)
        
        return {
            "models_loaded": len(self.models),
            "available_positions": available_positions
        }

async def test_prediction_engine_with_feature_mapping():
    """Test the prediction engine with feature mapping."""
    print("🎯 TESTING PREDICTION ENGINE WITH FEATURE MAPPING")
    print("=" * 70)
    
    # Create mock model registry
    model_registry = MockModelRegistry()
    
    # Create prediction engine (this should include our feature mapper)
    engine = PredictionEngine(model_registry)
    
    # Test data that simulates what feature engineering service provides
    test_features = {
        # Current column names (what feature engineering provides)
        'age': 25,
        'games': 16,  # Should map to games_played
        'carries': 200,  # Should map to rushing_attempts  
        'rushing_yards': 1000,
        'rushing_tds': 8,
        'targets': 50,
        'receptions': 40,
        'receiving_yards': 400,
        'receiving_tds': 2,
        # Extra features that would be ignored
        'fantasy_points': 200,
        'air_yards_share': 0.15,
        'wopr': 0.20
    }
    
    player_data = {
        'player_id': 'test_rb_1',
        'player_name': 'Test RB Player',
        'team': 'KC'
    }
    
    # Test RB prediction (the position that was failing)
    print(f"🏃 Testing RB prediction (the problematic position):")
    print(f"   Input features: {len(test_features)} features")
    print(f"   Key features: games={test_features['games']}, carries={test_features['carries']}")
    
    try:
        # This should now work with feature mapping
        result = await engine.predict_single('RB', test_features, player_data)
        
        print(f"✅ Prediction successful!")
        print(f"   Position: {result['position']}")
        print(f"   Prediction: {result['prediction']:.2f} points")
        print(f"   Model type: {result['model_type']}")
        print(f"   Features used: {result['features_count']}")
        print(f"   Confidence: {result['confidence']['score']:.3f}")
        
        # Validate prediction is reasonable
        prediction_value = result['prediction']
        reasonable_range = (5.0, 25.0)
        
        if reasonable_range[0] <= prediction_value <= reasonable_range[1]:
            print(f"✅ Prediction {prediction_value:.2f} is within reasonable range {reasonable_range}")
            return True
        else:
            print(f"⚠️ Prediction {prediction_value:.2f} outside reasonable range {reasonable_range}")
            return False
            
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        import traceback
        print(f"   Full error: {traceback.format_exc()}")
        return False

async def test_all_positions():
    """Test predictions for all positions."""
    print(f"\n🌟 TESTING ALL POSITIONS WITH FEATURE MAPPING")
    print("=" * 70)
    
    model_registry = MockModelRegistry()
    engine = PredictionEngine(model_registry)
    
    # Position-specific test data
    position_features = {
        'QB': {
            'age': 28,
            'games': 16,
            'attempts': 500,  # Should map to passing_attempts
            'completions': 350,  # Should map to passing_completions
            'passing_yards': 4200,
            'passing_tds': 30,
            'interceptions': 12,
            'carries': 40,  # Should map to rushing_attempts
            'rushing_yards': 200,
            'rushing_tds': 3
        },
        'RB': {
            'age': 25,
            'games': 16,
            'carries': 250,  # Should map to rushing_attempts
            'rushing_yards': 1200,
            'rushing_tds': 10, 
            'targets': 60,
            'receptions': 50,
            'receiving_yards': 400,
            'receiving_tds': 3
        },
        'WR': {
            'age': 26,
            'games': 16,
            'targets': 120,
            'receptions': 80,
            'receiving_yards': 1100,
            'receiving_tds': 8,
            'carries': 5,  # Should map to rushing_attempts
            'rushing_yards': 40,
            'rushing_tds': 1
        },
        'TE': {
            'age': 27,
            'games': 16,
            'targets': 90,
            'receptions': 65,
            'receiving_yards': 750,
            'receiving_tds': 6
        }
    }
    
    results = {}
    
    for position, features in position_features.items():
        print(f"\n📊 Testing {position} position:")
        
        try:
            result = await engine.predict_single(position, features)
            prediction = result['prediction']
            
            print(f"   ✅ Success: {prediction:.2f} points")
            print(f"   Model: {result['model_type']}")
            print(f"   Confidence: {result['confidence']['score']:.3f}")
            
            results[position] = {
                'success': True,
                'prediction': prediction,
                'model_type': result['model_type']
            }
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results[position] = {
                'success': False,
                'error': str(e)
            }
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('success', False))
    print(f"\n📋 SUMMARY:")
    print(f"   Successful predictions: {successful}/4 positions")
    
    for position, result in results.items():
        if result.get('success'):
            print(f"   ✅ {position}: {result['prediction']:.2f} points ({result['model_type']})")
        else:
            print(f"   ❌ {position}: Failed")
    
    return successful == 4

async def test_batch_predictions():
    """Test batch predictions with feature mapping."""
    print(f"\n📦 TESTING BATCH PREDICTIONS")
    print("=" * 70)
    
    model_registry = MockModelRegistry()
    engine = PredictionEngine(model_registry)
    
    # Create batch data for RB position
    batch_data = [
        {
            "features": {
                'age': 24,
                'games': 16,
                'carries': 280,
                'rushing_yards': 1400,
                'rushing_tds': 12,
                'targets': 45,
                'receptions': 35,
                'receiving_yards': 350,
                'receiving_tds': 2
            },
            "player_data": {
                'player_id': 'rb1',
                'player_name': 'Elite RB',
                'team': 'KC'
            }
        },
        {
            "features": {
                'age': 26,
                'games': 14,
                'carries': 180,
                'rushing_yards': 800,
                'rushing_tds': 6,
                'targets': 65,
                'receptions': 50,
                'receiving_yards': 500,
                'receiving_tds': 3
            },
            "player_data": {
                'player_id': 'rb2',
                'player_name': 'Receiving RB',
                'team': 'BUF'
            }
        }
    ]
    
    print(f"   Testing batch of {len(batch_data)} RB players")
    
    try:
        results = await engine.predict_batch('RB', batch_data)
        
        print(f"✅ Batch prediction successful!")
        print(f"   Results: {len(results)} predictions")
        
        for i, result in enumerate(results):
            player_name = result['player_info']['player_name']
            prediction = result['prediction']
            print(f"   Player {i+1} ({player_name}): {prediction:.2f} points")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch prediction failed: {e}")
        return False

async def main():
    """Main test function."""
    print("🔧 PREDICTION ENGINE FEATURE MAPPING TEST")
    print("=" * 80)
    print("Testing the fix for the '10 expected vs 5 provided' feature mismatch")
    print("=" * 80)
    
    # Test 1: Single RB prediction (the failing case)
    rb_test = await test_prediction_engine_with_feature_mapping()
    
    # Test 2: All positions
    all_positions_test = await test_all_positions()
    
    # Test 3: Batch predictions
    batch_test = await test_batch_predictions()
    
    # Final results
    print(f"\n🎯 FINAL TEST RESULTS")
    print("=" * 70)
    print(f"✅ RB prediction test: {'Pass' if rb_test else 'Fail'}")
    print(f"✅ All positions test: {'Pass' if all_positions_test else 'Fail'}")
    print(f"✅ Batch prediction test: {'Pass' if batch_test else 'Fail'}")
    
    if rb_test and all_positions_test and batch_test:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"   Feature mapping fix is working correctly")
        print(f"   The '10 vs 5' feature mismatch issue is resolved")
        print(f"   RB predictions should now work in the microservices pipeline")
    else:
        print(f"\n⚠️ SOME TESTS FAILED")
        print(f"   Review errors above before proceeding")
    
    return rb_test and all_positions_test and batch_test

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)