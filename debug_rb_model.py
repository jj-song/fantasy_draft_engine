#!/usr/bin/env python3
"""
Debug script to investigate RB model prediction issues.
The top RB (Kenneth Walker III) is only getting 95.7 points instead of 250+.
"""

import os
import sys
import pandas as pd
import joblib
import numpy as np

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def test_rb_model_directly():
    """Test RB model prediction directly."""
    print("🔍 DEBUGGING RB MODEL PREDICTIONS")
    print("=" * 50)
    
    try:
        # Load the RB model
        model_path = "saved_models/RB_ensemble_model.joblib"
        print(f"Loading model from: {model_path}")
        
        model_dict = joblib.load(model_path)
        print(f"Model type: {type(model_dict)}")
        print(f"Model keys: {list(model_dict.keys()) if isinstance(model_dict, dict) else 'Not a dict'}")
        
        # Get expected features
        rf_model = model_dict['rf_model']
        expected_features = list(rf_model.model.feature_names_in_)
        print(f"Expected features: {len(expected_features)}")
        print(f"First 10 features: {expected_features[:10]}")
        
        # Load some RB data to test with
        from scripts.generate_draft_rankings import load_position_data
        
        print(f"\nLoading RB data...")
        rb_data = load_position_data('RB', include_matchup_intelligence=True)
        print(f"Loaded RB data: {len(rb_data)} players")
        print(f"Available columns: {len(rb_data.columns)}")
        
        # Focus on Kenneth Walker III
        walker = rb_data[rb_data['player_name'] == 'Kenneth Walker III'].copy()
        if len(walker) == 0:
            print("❌ Kenneth Walker III not found in data")
            return
        
        print(f"\n🏃 KENNETH WALKER III DATA:")
        print(f"  Fantasy Points PPR: {walker['fantasy_points_ppr'].iloc[0] if 'fantasy_points_ppr' in walker.columns else 'N/A'}")
        print(f"  Games: {walker['games'].iloc[0] if 'games' in walker.columns else 'N/A'}")
        print(f"  Carries: {walker['carries'].iloc[0] if 'carries' in walker.columns else 'N/A'}")
        print(f"  Rushing Yards: {walker['rushing_yards'].iloc[0] if 'rushing_yards' in walker.columns else 'N/A'}")
        print(f"  Targets: {walker['targets'].iloc[0] if 'targets' in walker.columns else 'N/A'}")
        print(f"  Receptions: {walker['receptions'].iloc[0] if 'receptions' in walker.columns else 'N/A'}")
        
        # Prepare features for prediction using our compatibility system
        from src.feature_compatibility import create_model_compatible_features
        
        print(f"\n🔧 Creating compatible features...")
        walker_compatible = create_model_compatible_features(
            walker, 
            expected_features,
            'RB'
        )
        
        print(f"Compatible features created: {len(walker_compatible.columns)}")
        print(f"Feature compatibility: {len(walker_compatible.columns)}/{len(expected_features)}")
        
        # Make prediction using RF model directly
        print(f"\n🎯 Making prediction with RF model...")
        rf_prediction = rf_model.model.predict(walker_compatible)[0]
        print(f"RF prediction: {rf_prediction:.2f}")
        
        # Try LGB model if available
        if 'lgb_model' in model_dict:
            lgb_model = model_dict['lgb_model']
            lgb_prediction = lgb_model.model.predict(walker_compatible)[0]
            print(f"LGB prediction: {lgb_prediction:.2f}")
            
            # Ensemble average
            ensemble_pred = (rf_prediction + lgb_prediction) / 2
            print(f"Ensemble average: {ensemble_pred:.2f}")
        
        # Check if prediction is per-game vs seasonal
        games_played = walker['games'].iloc[0] if 'games' in walker.columns else 17
        seasonal_pred = rf_prediction * games_played
        print(f"\nPer-game prediction: {rf_prediction:.2f}")
        print(f"Seasonal prediction: {seasonal_pred:.2f}")
        print(f"Games played: {games_played}")
        
        # Compare to actual fantasy points
        if 'fantasy_points_ppr' in walker.columns:
            actual_points = walker['fantasy_points_ppr'].iloc[0]
            print(f"Actual 2024 fantasy points: {actual_points:.2f}")
            print(f"Prediction vs Actual: {seasonal_pred:.2f} vs {actual_points:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def compare_rb_vs_wr_features():
    """Compare RB vs WR feature availability to understand the issue."""
    print("\n" + "=" * 50)
    print("🔍 COMPARING RB vs WR FEATURE AVAILABILITY")
    print("=" * 50)
    
    try:
        from scripts.generate_draft_rankings import load_position_data
        
        # Load both RB and WR data
        rb_data = load_position_data('RB', include_matchup_intelligence=True)
        wr_data = load_position_data('WR', include_matchup_intelligence=True)
        
        print(f"RB players: {len(rb_data)}")
        print(f"WR players: {len(wr_data)}")
        
        # Compare top players
        if 'fantasy_points_ppr' in rb_data.columns:
            top_rb = rb_data.nlargest(1, 'fantasy_points_ppr').iloc[0]
            print(f"\nTop RB: {top_rb['player_name']} - {top_rb['fantasy_points_ppr']:.1f} pts")
        
        if 'fantasy_points_ppr' in wr_data.columns:
            top_wr = wr_data.nlargest(1, 'fantasy_points_ppr').iloc[0]
            print(f"Top WR: {top_wr['player_name']} - {top_wr['fantasy_points_ppr']:.1f} pts")
        
        # Compare feature availability
        rb_features = set(rb_data.columns)
        wr_features = set(wr_data.columns)
        
        print(f"\nRB unique features: {len(rb_features - wr_features)}")
        print(f"WR unique features: {len(wr_features - rb_features)}")
        print(f"Common features: {len(rb_features & wr_features)}")
        
        # Check key RB features
        key_rb_features = ['carries', 'rushing_yards', 'rushing_tds', 'touches']
        print(f"\nKey RB features availability:")
        for feature in key_rb_features:
            rb_has = feature in rb_data.columns
            wr_has = feature in wr_data.columns
            print(f"  {feature}: RB={rb_has}, WR={wr_has}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_rb_model_directly()
    compare_rb_vs_wr_features()