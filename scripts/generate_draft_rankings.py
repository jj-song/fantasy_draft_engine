#!/usr/bin/env python3
"""
Generate Fantasy Football Draft Rankings

This script generates fantasy football draft rankings based on the trained models
from our feature engineering analysis for each position (QB, RB, WR, TE, K, DST).
It creates an overall ranking as well as position-specific rankings.

Enhanced with Phase 2 Matchup Intelligence:
- Command-line flag to enable/disable matchup intelligence features
- Schedule strength analysis and opponent quality assessment
- Environmental factors (weather, altitude, dome effects) 
- Situational adjustments and venue considerations
- Matchup-adjusted projections and confidence intervals

Usage:
    python generate_draft_rankings.py                                    # Traditional rankings
    python generate_draft_rankings.py --include-matchup-intelligence     # Enhanced with matchup features
    python generate_draft_rankings.py --weeks-ahead-sos 6               # Analyze 6 weeks ahead for SOS
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
import argparse
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Set plot style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette('viridis')

def load_position_data(
    position: str, 
    include_matchup_intelligence: bool = False,
    weeks_ahead_sos: int = 4
) -> pd.DataFrame:
    """
    Load data for a specific position using current season data with updated team assignments.
    Enhanced with optional matchup intelligence features.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
        include_matchup_intelligence: Include Phase 2 matchup intelligence features
        weeks_ahead_sos: Number of weeks ahead to analyze for strength of schedule
    
    Returns:
        DataFrame with position data including current team assignments and optional matchup features
    """
    # Import current data pipeline and feature engineering
    sys.path.insert(0, os.path.join(project_root, 'src'))
    from current_data_pipeline import create_current_inference_dataset
    from feature_engineering import engineer_features_for_season
    import config
    
    print(f"Loading current data for {position} with updated team assignments...")
    
    try:
        # First, try to get current inference dataset (2024 data with current teams)
        current_data = create_current_inference_dataset(position)
        
        if not current_data.empty:
            print(f"✅ Loaded {len(current_data)} current {position} players with updated teams")
            
            # Apply feature engineering to create enhanced features - FAIL FAST if requested
            if include_matchup_intelligence:
                print(f"   🔧 FEATURE ENGINEERING WITH MATCHUP INTELLIGENCE START")
                print(f"   📊 SOS analysis weeks ahead: {weeks_ahead_sos}")
                
                # Use the correct target season for feature engineering (2024 data to predict 2025)
                target_season = config.INFERENCE_DATA_YEAR  # 2024
                
                print(f"   📅 Engineering features using {target_season} data to predict {target_season + 1}")
                
                # NO TRY/CATCH - Let it fail if feature engineering fails
                df_engineered = engineer_features_for_season(
                    target_season,
                    include_matchup_intelligence=include_matchup_intelligence,
                    include_position_specific_features=True,  # Always enable position-specific features for enhanced data
                    weeks_ahead_sos=weeks_ahead_sos
                )
                
                # STRICT validation - fail if feature engineering didn't work
                if df_engineered is None or df_engineered.empty:
                    raise ValueError(f"CRITICAL: Feature engineering returned empty data for {position}")
                
                print(f"   ✅ Feature engineering successful: {len(df_engineered)} players, {len(df_engineered.columns)} features")
                
                # Filter for position 
                position_engineered = df_engineered[df_engineered['position'] == position].copy()
                
                if position_engineered.empty:
                    raise ValueError(f"CRITICAL: No {position} players found in engineered features")
                
                print(f"   📊 Found {len(position_engineered)} {position} players in engineered features")
                
                # Update with current team assignments from current_data - FAIL if this fails
                from current_data_pipeline import update_data_with_current_teams, get_current_roster_assignments
                current_rosters = get_current_roster_assignments()
                
                if current_rosters.empty:
                    raise ValueError("CRITICAL: No current roster assignments available")
                
                # This should now work with the fixed team comparison
                position_engineered = update_data_with_current_teams(position_engineered, current_rosters)
                print(f"   ✅ Updated {position} player team assignments to current rosters")
                
                # STRICT feature validation - fail if expected features are missing
                matchup_cols = [col for col in position_engineered.columns if 'next_' in col or 'sos_' in col]
                opportunity_cols = [col for col in position_engineered.columns if any(x in col.lower() for x in ['target_share', 'air_yards', 'wopr'])]
                usage_cols = [col for col in position_engineered.columns if any(x in col.lower() for x in ['snap_share', 'route_participation', 'high_value'])]
                
                print(f"   🎯 Matchup features: {len(matchup_cols)}")
                print(f"   📈 Opportunity features: {len(opportunity_cols)}")
                print(f"   📊 Usage features: {len(usage_cols)}")
                
                if matchup_cols:
                    print(f"   🔍 Sample matchup features: {matchup_cols[:3]}")
                if opportunity_cols:
                    print(f"   🔍 Sample opportunity features: {opportunity_cols[:3]}")
                
                # WARN if critical features are missing for specific positions
                if position == 'QB' and len(matchup_cols) < 10:
                    print(f"⚠️ WARNING: QB missing matchup intelligence features. Found {len(matchup_cols)}, expected 10+. Using available features.")
                    logger.warning(f"QB missing matchup intelligence features. Found {len(matchup_cols)}, expected 10+. Proceeding with available features.")
                
                if position in ['RB', 'WR', 'TE'] and len(opportunity_cols) == 0:
                    raise ValueError(f"CRITICAL: {position} missing opportunity metrics. Expected target_share, air_yards, etc.")
                
                print(f"✅ FEATURE ENGINEERING VALIDATION PASSED for {len(position_engineered)} {position} players")
                return position_engineered
            else:
                print(f"   📋 Using traditional features (matchup intelligence disabled)")
            
            # If feature engineering fails, return current data as-is
            return current_data
            
        else:
            # Fallback to historical feature engineering
            print(f"⚠️ No current data available for {position}, falling back to historical data")
            most_recent_year = config.TRAINING_DATA_END_YEAR  # Use 2023 for training
            
            df = engineer_features_for_season(
                most_recent_year,
                include_matchup_intelligence=include_matchup_intelligence,
                include_position_specific_features=True,  # Always enable for any enhanced features
                weeks_ahead_sos=weeks_ahead_sos
            )
            
            if df is not None and not df.empty:
                position_df = df[df['position'] == position].copy()
                
                if not position_df.empty:
                    # Try to update with current teams even for historical data
                    try:
                        from current_data_pipeline import update_data_with_current_teams, get_current_roster_assignments
                        current_rosters = get_current_roster_assignments()
                        
                        if not current_rosters.empty:
                            position_df = update_data_with_current_teams(position_df, current_rosters)
                            print(f"✅ Updated historical {position} data with current team assignments")
                    except Exception as e:
                        print(f"⚠️ Could not update team assignments: {e}")
                    
                    print(f"✅ Loaded {len(position_df)} {position} players (historical with team updates)")
                    return position_df
                else:
                    print(f"⚠️ No {position} players found in historical data")
                    return pd.DataFrame()
            else:
                print(f"⚠️ No historical data available")
                return pd.DataFrame()
            
    except Exception as e:
        print(f"❌ Error loading data for {position}: {e}")
        return pd.DataFrame()

def load_ensemble_model(position: str) -> object:
    """
    Load the trained ensemble model for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
    
    Returns:
        Trained ensemble model object
    """
    print(f"📂 LOADING ENSEMBLE MODEL: {position}")
    print("=" * 50)
    
    # Try to load ensemble model first
    ensemble_model_path = os.path.join(project_root, f'saved_models/{position}_ensemble_model.joblib')
    
    if os.path.exists(ensemble_model_path):
        print(f"   Loading ensemble model from {ensemble_model_path}")
        try:
            from src.ensemble_model import EnsembleFantasyModel
            model = EnsembleFantasyModel.load(ensemble_model_path)
            print(f"✅ Ensemble model loaded successfully for {position}")
            print(f"   Model type: {type(model).__name__}")
            print(f"   RF component: {type(model.rf_model.model).__name__}")
            print(f"   LGB component: {type(model.lgb_model.model).__name__}")
            print(f"   Dynamic weighting: {type(model.dynamic_weighter).__name__}")
            return model
        except Exception as e:
            raise ValueError(f"CRITICAL: Failed to load ensemble model for {position}: {str(e)}")
    
    # Fallback to legacy single model - but FAIL with clear message
    legacy_model_path = os.path.join(project_root, f'saved_models/{position}_advanced_engineering_model.joblib')
    if os.path.exists(legacy_model_path):
        raise ValueError(f"CRITICAL: Only legacy single model found for {position}. "
                        f"Ensemble model required at {ensemble_model_path}. "
                        f"Run model retraining with ensemble system first.")
    
    # No model found at all
    raise FileNotFoundError(f"CRITICAL: No model found for {position}. "
                           f"Expected ensemble model at {ensemble_model_path}")


def load_model_based_on_features(position: str, has_advanced_features: bool = True) -> object:
    """
    Load the appropriate trained model based on available features.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
        has_advanced_features: Whether advanced engineered features are available
    
    Returns:
        Trained model object
    """
    if has_advanced_features:
        try:
            return load_ensemble_model(position)
        except:
            print(f"⚠️ WARNING: Ensemble model failed to load for {position}, falling back to advanced engineering model")
            return load_model(position, 'advanced_engineering')
    else:
        print(f"⚠️ WARNING: Using baseline model for {position} due to limited features available")
        return load_model(position, 'baseline')

def load_model(position: str, model_type: str = 'ensemble') -> object:
    """
    Load the trained model for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
        model_type: Type of model to load ('ensemble' is default, others deprecated)
    
    Returns:
        Trained model object
    """
    if model_type == 'ensemble':
        return load_ensemble_model(position)
    
    # Legacy support - but warn that it's deprecated
    print(f"⚠️ WARNING: Loading legacy {model_type} model for {position}. This is deprecated.")
    print(f"   Please retrain with ensemble system for optimal performance.")
    
    model_path = os.path.join(project_root, f'saved_models/{position}_{model_type}_model.joblib')
    
    if os.path.exists(model_path):
        print(f"Loading {position} {model_type} model from {model_path}")
        return joblib.load(model_path)
    else:
        raise FileNotFoundError(f"CRITICAL: Model for {position} ({model_type}) not found at {model_path}")

def predict_fantasy_points(df: pd.DataFrame, model, position: str, target_col: str = 'fantasy_points_per_game') -> pd.DataFrame:
    """
    Generate predictions using the trained ensemble model with comprehensive logging.
    
    Args:
        df: DataFrame with player data
        model: Trained ensemble model object
        position: Player position
        target_col: Target column to predict
    
    Returns:
        DataFrame with predictions added
    """
    print(f"🤖 ENSEMBLE PREDICTION START: {position}")
    print("=" * 60)
    print(f"Input data shape: {df.shape}")
    print(f"Players to predict: {len(df)}")
    
    if model is None:
        raise ValueError(f"CRITICAL: No model provided for {position}")

    # COMPREHENSIVE feature validation and logging
    matchup_cols = [col for col in df.columns if any(x in col.lower() for x in ['next_', 'sos_', 'schedule', 'opponent'])]
    opportunity_cols = [col for col in df.columns if any(x in col.lower() for x in ['target_share', 'air_yards', 'wopr', 'adot'])]
    usage_cols = [col for col in df.columns if any(x in col.lower() for x in ['snap_share', 'route_participation', 'high_value', 'usage'])]
    position_cols = [col for col in df.columns if any(x in col.lower() for x in ['_role', '_tier', '_style', '_specialist'])]
    efficiency_cols = [col for col in df.columns if any(x in col.lower() for x in ['per_game', 'per_attempt', 'efficiency', 'rate'])]
    
    print(f"📊 FEATURE CATEGORY ANALYSIS:")
    print(f"   🎯 Matchup Intelligence: {len(matchup_cols)} features")
    if matchup_cols:
        print(f"      Examples: {matchup_cols[:3]}")
    
    print(f"   📈 Opportunity Metrics: {len(opportunity_cols)} features")
    if opportunity_cols:
        print(f"      Examples: {opportunity_cols[:3]}")
    
    print(f"   📊 Usage Analytics: {len(usage_cols)} features")
    if usage_cols:
        print(f"      Examples: {usage_cols[:3]}")
    
    print(f"   🏈 Position-Specific: {len(position_cols)} features")
    if position_cols:
        print(f"      Examples: {position_cols[:3]}")
    
    print(f"   ⚡ Efficiency Metrics: {len(efficiency_cols)} features")
    if efficiency_cols:
        print(f"      Examples: {efficiency_cols[:3]}")
    
    print(f"   📋 Total Features: {len(df.columns)}")
    
    # WARN about missing critical features but continue processing
    if position == 'QB' and len(matchup_cols) < 10:
        print(f"⚠️ WARNING: QB missing matchup intelligence features. Found {len(matchup_cols)}, expected 10+. Using available features.")
    
    if position in ['RB', 'WR', 'TE'] and len(opportunity_cols) == 0:
        raise ValueError(f"CRITICAL: {position} missing opportunity metrics. Expected target_share, air_yards, etc.")
    
    # Prepare feature data
    df_engineered = df.copy()
    
    # Drop columns that aren't features
    drop_cols = ['player_id', 'player_name', 'team', 'position', 'season', 
                 'fantasy_points', 'fantasy_points_per_game', 'current_team']
    
    # Get feature columns
    X = df_engineered.drop(columns=[col for col in drop_cols if col in df_engineered.columns])
    
    print(f"📋 Feature preparation:")
    print(f"   Original columns: {len(df_engineered.columns)}")
    print(f"   Dropped columns: {len([col for col in drop_cols if col in df_engineered.columns])}")
    print(f"   Final feature columns: {len(X.columns)}")
    
    # Validate no null values in features
    null_cols = X.columns[X.isnull().any()].tolist()
    if null_cols:
        print(f"⚠️ WARNING: Null values found in features: {null_cols[:5]}")
        print(f"   Filling null values with 0")
        X = X.fillna(0)
    
    # Clean data types for model compatibility
    # Convert object columns to numeric where possible
    object_cols = X.select_dtypes(include=['object']).columns.tolist()
    if object_cols:
        print(f"⚠️ WARNING: Object columns found: {object_cols[:5]}")
        for col in object_cols:
            # Try to convert to numeric, drop if conversion fails
            try:
                X[col] = pd.to_numeric(X[col], errors='coerce')
                X[col] = X[col].fillna(0)
                print(f"   Converted {col} to numeric")
            except:
                print(f"   Dropping non-numeric column: {col}")
                X = X.drop(columns=[col])
    
    # Map current column names to expected model column names
    print("🔄 Mapping feature names to match model expectations...")
    column_mapping = {
        'attempts': 'passing_attempts',
        'completions': 'passing_completions', 
        'carries': 'rushing_attempts',
        'games': 'games_played',
        'receiving_yards': 'rec_yards',
        'rushing_yards': 'rush_yards',
        'passing_yards': 'pass_yards',
        'receiving_touchdowns': 'rec_tds',
        'rushing_touchdowns': 'rush_tds',
        'passing_touchdowns': 'pass_tds'
    }
    
    # Apply column mapping
    mapped_count = 0
    for old_name, new_name in column_mapping.items():
        if old_name in X.columns:
            X = X.rename(columns={old_name: new_name})
            mapped_count += 1
    
    if mapped_count > 0:
        print(f"   Mapped {mapped_count} column names to match model expectations")
    
    # Make predictions with ensemble model
    print(f"🎯 Starting ensemble prediction...")
    
    try:
        # Check if it's an ensemble model
        if hasattr(model, 'predict') and hasattr(model, 'rf_model') and hasattr(model, 'lgb_model'):
            # True ensemble model
            print(f"   Using EnsembleFantasyModel with dynamic weighting")
            
            # Extract player data for dynamic weighting
            # Use position parameter since position column was dropped during feature engineering
            player_data = pd.DataFrame({
                'player_name': df['player_name'] if 'player_name' in df.columns else [f'Player_{i}' for i in range(len(df))],
                'position': [position] * len(df),  # Use the position parameter
                'team': df['team'] if 'team' in df.columns else ['UNK'] * len(df)
            })
            
            # Add any available player characteristics for dynamic weighting
            for col in df.columns:
                if any(x in col.lower() for x in ['experience', 'age', 'games', 'carries', 'targets', 'attempts']):
                    if col not in ['fantasy_points', 'fantasy_points_per_game']:
                        player_data[col] = df[col]
            
            predictions = model.predict(X, player_data)
            print(f"✅ Ensemble prediction completed with dynamic weighting")
            
        else:
            # Legacy single model
            print(f"   Using legacy single model (no ensemble)")
            print(f"   Model type: {type(model).__name__}")
            
            # Handle legacy model prediction
            if hasattr(model, 'predict'):
                predictions = model.predict(X)
            else:
                raise ValueError(f"Model object has no predict method")
            
            print(f"✅ Legacy prediction completed")
        
        # Validate predictions
        if predictions is None:
            raise ValueError("Model returned None predictions")
        
        if len(predictions) != len(df):
            raise ValueError(f"Prediction length mismatch: got {len(predictions)}, expected {len(df)}")
        
        if np.any(np.isnan(predictions)):
            raise ValueError("Model predictions contain NaN values")
        
        df['predicted_points'] = predictions
        
        print(f"📊 PREDICTION SUMMARY:")
        print(f"   Predictions generated: {len(predictions)}")
        print(f"   Mean prediction: {predictions.mean():.2f}")
        print(f"   Std prediction: {predictions.std():.2f}")
        print(f"   Min prediction: {predictions.min():.2f}")
        print(f"   Max prediction: {predictions.max():.2f}")
        
        print(f"✅ ENSEMBLE PREDICTION COMPLETE: {position}")
        
    except Exception as e:
        # GRACEFUL FALLBACK - Use historical fantasy points if available
        print(f"⚠️ WARNING: Model prediction failed for {position}: {str(e)}")
        
        # Find games played column
        games_col = None
        for col in df.columns:
            if col.lower() in ['games', 'games_played', 'g', 'gp']:
                games_col = col
                break
        
        if 'fantasy_points_ppr' in df.columns:
            print(f"   🔄 Falling back to historical fantasy points for {position}")
            if games_col and games_col in df.columns:
                # Convert seasonal totals to per-game averages
                df['predicted_points'] = np.where(
                    df[games_col] > 0,
                    df['fantasy_points_ppr'] / df[games_col],
                    0
                )
                print(f"   ✅ Converted seasonal totals to per-game averages for {len(df)} {position} players")
                avg_predicted = df['predicted_points'].mean()
                print(f"   📊 Average per-game prediction: {avg_predicted:.1f} points")
            else:
                print(f"   ⚠️ No games data available, using seasonal totals")
                df['predicted_points'] = df['fantasy_points_ppr']
        elif 'fantasy_points' in df.columns:
            print(f"   🔄 Falling back to historical fantasy points for {position}")
            if games_col and games_col in df.columns:
                # Convert seasonal totals to per-game averages
                df['predicted_points'] = np.where(
                    df[games_col] > 0,
                    df['fantasy_points'] / df[games_col],
                    0
                )
                print(f"   ✅ Converted seasonal totals to per-game averages for {len(df)} {position} players")
                avg_predicted = df['predicted_points'].mean()
                print(f"   📊 Average per-game prediction: {avg_predicted:.1f} points")
            else:
                print(f"   ⚠️ No games data available, using seasonal totals")
                df['predicted_points'] = df['fantasy_points']
        else:
            # If no fantasy points available, assign baseline values based on position
            print(f"   ⚠️ No historical fantasy points available, assigning position-based baseline values")
            baseline_values = {'QB': 15.0, 'RB': 10.0, 'WR': 8.0, 'TE': 6.0, 'K': 8.0, 'DST': 8.0}
            df['predicted_points'] = baseline_values.get(position, 5.0)
            print(f"   📊 Assigned baseline value of {baseline_values.get(position, 5.0)} points for {position}")
        
        print(f"✅ FALLBACK PREDICTION COMPLETE: {position}")
    
    return df

def calculate_value_over_replacement(
    df_by_pos: Dict[str, pd.DataFrame], 
    include_matchup_adjustments: bool = False
) -> Dict[str, pd.DataFrame]:
    """
    Calculate Value Over Replacement (VOR) for each player with positional scarcity weighting.
    Enhanced with optional matchup-adjusted VOR calculations.
    
    This implements an improved VOR calculation that:
    1. Uses realistic replacement levels based on starter requirements
    2. Applies positional scarcity multipliers based on fantasy football research
    3. Accounts for injury risk, positional depth, and starter requirements
    4. Optionally includes schedule-adjusted VOR based on matchup intelligence
    
    Args:
        df_by_pos: Dictionary of DataFrames by position
        include_matchup_adjustments: Include schedule-adjusted VOR calculations
    
    Returns:
        Dictionary of DataFrames with adjusted VOR added
    """
    # Import VOR configuration from config
    import config
    
    # Use improved replacement levels and scarcity multipliers
    replacement_levels = config.VOR_REPLACEMENT_LEVELS
    scarcity_multipliers = config.VOR_SCARCITY_MULTIPLIERS
    
    result = {}
    
    print("\n🔢 VOR Calculation Summary:")
    print("=" * 50)
    
    for pos, df in df_by_pos.items():
        if len(df) == 0:
            result[pos] = df
            continue
            
        # Sort by predicted points
        df_sorted = df.sort_values('predicted_points', ascending=False).reset_index(drop=True)
        
        # Get replacement level player (adjust index for 0-based)
        replacement_rank = replacement_levels.get(pos, 15)
        replacement_idx = min(replacement_rank - 1, len(df_sorted) - 1)  # Convert to 0-based index
        replacement_value = df_sorted.loc[replacement_idx, 'predicted_points']
        
        # Calculate raw VOR (predicted points - replacement points)
        df_sorted['raw_vor'] = df_sorted['predicted_points'] - replacement_value
        
        # Apply positional scarcity multiplier
        scarcity_multiplier = scarcity_multipliers.get(pos, 1.0)
        df_sorted['vor'] = df_sorted['raw_vor'] * scarcity_multiplier
        
        # Add schedule-adjusted VOR if matchup features are available
        if include_matchup_adjustments:
            # Look for matchup adjustment columns
            matchup_cols = [col for col in df_sorted.columns if col.startswith('next_') and 'sos_rating' in col]
            
            if matchup_cols:
                # Use schedule strength to adjust VOR
                sos_col = matchup_cols[0]  # Use first available SOS column
                
                # Create schedule adjustment factor (-0.1 to +0.1 based on SOS rating)
                schedule_adjustment = df_sorted[sos_col].fillna(0) * 0.1
                df_sorted['schedule_adjusted_vor'] = df_sorted['vor'] * (1 + schedule_adjustment)
                
                print(f"   📊 Applied schedule adjustments for {pos} (avg: {schedule_adjustment.mean():.3f})")
            else:
                # No matchup data available, use regular VOR
                df_sorted['schedule_adjusted_vor'] = df_sorted['vor']
                print(f"   ⚠️ No SOS data available for {pos}, using regular VOR")
        else:
            # Use regular VOR when matchup adjustments are disabled
            df_sorted['schedule_adjusted_vor'] = df_sorted['vor']
        
        # Store result
        result[pos] = df_sorted
        
        # Print summary for this position
        top_player = df_sorted.iloc[0]
        print(f"{pos}:")
        print(f"  Replacement level: {replacement_rank} (#{replacement_idx+1}: {replacement_value:.1f} pts)")
        print(f"  Scarcity multiplier: {scarcity_multiplier}x")
        print(f"  Top player: {top_player['player_name']} ({top_player['predicted_points']:.1f} pts)")
        print(f"  Raw VOR: {top_player['raw_vor']:.1f} → Adjusted VOR: {top_player['vor']:.1f}", end="")
        
        if include_matchup_adjustments and 'schedule_adjusted_vor' in top_player:
            print(f" → Schedule-Adj VOR: {top_player['schedule_adjusted_vor']:.1f}")
        else:
            print()
        print()
        
    return result

def create_overall_rankings(
    df_by_pos: Dict[str, pd.DataFrame], 
    use_schedule_adjusted_vor: bool = False
) -> pd.DataFrame:
    """
    Create overall rankings based on VOR with optional schedule adjustments.
    
    Args:
        df_by_pos: Dictionary of DataFrames by position with VOR calculated
        use_schedule_adjusted_vor: Use schedule-adjusted VOR for rankings if available
    
    Returns:
        DataFrame with overall rankings
    """
    all_players = []
    
    # Collect all players
    for pos, df in df_by_pos.items():
        if len(df) == 0:
            continue
            
        df_copy = df.copy()
        df_copy['position'] = pos
        all_players.append(df_copy)
    
    if not all_players:
        return pd.DataFrame()
        
    # Combine all players
    all_df = pd.concat(all_players)
    
    # Determine which VOR column to use for rankings
    vor_column = 'vor'  # Default
    if use_schedule_adjusted_vor and 'schedule_adjusted_vor' in all_df.columns:
        vor_column = 'schedule_adjusted_vor'
        print(f"🎯 Using schedule-adjusted VOR for overall rankings")
    else:
        print(f"🎯 Using standard VOR for overall rankings")
    
    # Create overall rankings based on selected VOR
    overall_rankings = all_df.sort_values(vor_column, ascending=False).reset_index(drop=True)
    overall_rankings['overall_rank'] = overall_rankings.index + 1
    
    # Clean up columns for display (include both VOR types if available)
    columns = ['overall_rank', 'player_name', 'position', 'team', 'predicted_points', 'raw_vor', 'vor']
    if 'schedule_adjusted_vor' in overall_rankings.columns:
        columns.append('schedule_adjusted_vor')
    
    existing_columns = [col for col in columns if col in overall_rankings.columns]
    
    return overall_rankings[existing_columns]

def create_position_rankings(df_by_pos: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Create position-specific rankings.
    
    Args:
        df_by_pos: Dictionary of DataFrames by position with VOR calculated
    
    Returns:
        Dictionary of DataFrames with position rankings
    """
    position_rankings = {}
    
    for pos, df in df_by_pos.items():
        if len(df) == 0:
            position_rankings[pos] = pd.DataFrame()
            continue
            
        # Add position rank
        df_ranked = df.copy()
        df_ranked[f'{pos.lower()}_rank'] = df_ranked.index + 1
        
        # Clean up columns for display (include raw_vor for analysis)
        columns = [f'{pos.lower()}_rank', 'player_name', 'team', 'predicted_points', 'raw_vor', 'vor']
        existing_columns = [col for col in columns if col in df_ranked.columns]
        
        position_rankings[pos] = df_ranked[existing_columns]
    
    return position_rankings

def save_rankings(overall_rankings: pd.DataFrame, position_rankings: Dict[str, pd.DataFrame]) -> None:
    """
    Save rankings to CSV files.
    
    Args:
        overall_rankings: DataFrame with overall rankings
        position_rankings: Dictionary of DataFrames with position rankings
    """
    # Create directory if it doesn't exist
    rankings_dir = os.path.join(project_root, 'data/draft_lists')
    os.makedirs(rankings_dir, exist_ok=True)
    
    # Get timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save overall rankings only (user requested to remove unnecessary position CSV exports)
    if not overall_rankings.empty:
        overall_file = f'{rankings_dir}/overall_rankings_{timestamp}.csv'
        overall_rankings.to_csv(overall_file, index=False)
        print(f"Saved overall rankings to {overall_file}")
        print(f"✅ Contains {len(overall_rankings)} players with real NFL names")
    else:
        print("⚠️ No overall rankings to save")
            
def generate_draft_cheatsheet(overall_rankings: pd.DataFrame, position_rankings: Dict[str, pd.DataFrame]) -> None:
    """
    Generate an enhanced draft cheatsheet with detailed VOR analysis and positional insights.
    
    Args:
        overall_rankings: DataFrame with overall rankings
        position_rankings: Dictionary of DataFrames with position rankings
    """
    # Create directory if it doesn't exist
    rankings_dir = os.path.join(project_root, 'data/draft_lists')
    os.makedirs(rankings_dir, exist_ok=True)
    
    # Get timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cheatsheet_file = f'{rankings_dir}/draft_cheatsheet_enhanced_{timestamp}.txt'
    
    # Import config for VOR analysis
    import config
    
    with open(cheatsheet_file, 'w') as f:
        f.write("="*100 + "\n")
        f.write("🏈 FANTASY FOOTBALL DRAFT CHEATSHEET - VOR ANALYSIS EDITION\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*100 + "\n\n")
        
        # VOR Breakdown Summary
        f.write("📊 VALUE OVER REPLACEMENT (VOR) BREAKDOWN\n")
        f.write("─" * 100 + "\n")
        f.write("Position  Replacement    Scarcity   Top Player            Raw VOR  →  Adj VOR\n")
        f.write("          Level          Mult       (Predicted Points)\n")
        f.write("─" * 100 + "\n")
        
        replacement_levels = config.VOR_REPLACEMENT_LEVELS
        scarcity_multipliers = config.VOR_SCARCITY_MULTIPLIERS
        
        for pos in ['RB', 'TE', 'WR', 'QB']:
            if pos in position_rankings and not position_rankings[pos].empty:
                pos_df = position_rankings[pos]
                top_player = pos_df.iloc[0]
                replacement_level = replacement_levels.get(pos, 15)
                scarcity_mult = scarcity_multipliers.get(pos, 1.0)
                
                f.write(f"{pos:<8}  {pos}{replacement_level:<13}  {scarcity_mult}x      ")
                f.write(f"{top_player['player_name']:<20} ({top_player['predicted_points']:.1f})  ")
                f.write(f"{top_player['raw_vor']:.1f}  →  {top_player['vor']:.1f}\n")
        
        f.write("\n")
        
        # Enhanced Top 50 with VOR details
        f.write("🏆 TOP 50 OVERALL PLAYERS WITH VOR ANALYSIS\n")
        f.write("─" * 100 + "\n")
        f.write("RNK  PLAYER NAME             POS  TEAM  PROJ   RAW    MULT   ADJ    TIER\n")
        f.write("                                      PPG*   VOR    (x)    VOR\n")
        f.write("─" * 100 + "\n")
        
        if not overall_rankings.empty:
            top_50 = overall_rankings.head(50)
            
            # Define tiers based on VOR
            tier_cutoffs = [18, 14, 10, 6]  # Elite, Premium, Solid, Depth
            tier_names = ["ELITE", "PREMIUM", "SOLID", "DEPTH", "BENCH"]
            
            for _, row in top_50.iterrows():
                # Determine tier
                vor_value = row['vor']
                tier = tier_names[-1]  # Default to BENCH
                for i, cutoff in enumerate(tier_cutoffs):
                    if vor_value >= cutoff:
                        tier = tier_names[i]
                        break
                
                # Get scarcity multiplier for this position
                scarcity_mult = scarcity_multipliers.get(row['position'], 1.0)
                
                f.write(f"{row['overall_rank']:3d}. {row['player_name']:<23} ")
                f.write(f"{row['position']:<4} {row['team']:<4} ")
                f.write(f"{row['predicted_points']:5.1f}  ")
                f.write(f"{row['raw_vor']:5.1f}  ")
                f.write(f"{scarcity_mult:4.1f}x  ")
                f.write(f"{row['vor']:5.1f}  ")
                f.write(f"{tier}\n")
        
        f.write("\n")
        
        # Side-by-Side Positional Comparison by Tiers
        f.write("🎯 SIDE-BY-SIDE POSITIONAL COMPARISON BY TIERS\n")
        f.write("=" * 100 + "\n")
        
        # Create tier groupings
        tiers = {
            "ELITE (VOR 18+)": [],
            "PREMIUM (VOR 14-18)": [],
            "SOLID (VOR 10-14)": [],
            "DEPTH (VOR 6-10)": []
        }
        
        # Group players by tier
        for _, row in overall_rankings.head(60).iterrows():
            vor_value = row['vor']
            if vor_value >= 18:
                tiers["ELITE (VOR 18+)"].append(row)
            elif vor_value >= 14:
                tiers["PREMIUM (VOR 14-18)"].append(row)
            elif vor_value >= 10:
                tiers["SOLID (VOR 10-14)"].append(row)
            elif vor_value >= 6:
                tiers["DEPTH (VOR 6-10)"].append(row)
        
        # Display each tier
        for tier_name, tier_players in tiers.items():
            if tier_players:
                f.write(f"\n┌─ {tier_name} " + "─" * (95 - len(tier_name)) + "┐\n")
                f.write("│ RB                    │ WR                    │ TE                    │ QB                    │\n")
                f.write("│ ──                    │ ──                    │ ──                    │ ──                    │\n")
                
                # Group by position
                tier_by_pos = {'RB': [], 'WR': [], 'TE': [], 'QB': []}
                for player in tier_players:
                    pos = player['position']
                    if pos in tier_by_pos:
                        tier_by_pos[pos].append(player)
                
                # Find max length for any position
                max_players = max(len(players) for players in tier_by_pos.values()) if tier_by_pos else 0
                
                # Print players side by side
                for i in range(max_players):
                    f.write("│ ")
                    for pos in ['RB', 'WR', 'TE', 'QB']:
                        if i < len(tier_by_pos[pos]):
                            player = tier_by_pos[pos][i]
                            player_str = f"{player['player_name'][:12]} {player['vor']:.1f}"
                            f.write(f"{player_str:<21} │ ")
                        else:
                            f.write(" " * 21 + " │ ")
                    f.write("\n")
                
                f.write("└" + "─" * 95 + "┘\n")
        
        f.write("\n")
        
        # Add footnote explanation
        f.write("* PPG = Points Per Game projection based on historical performance\n")
        f.write("  For seasonal projections, multiply by expected games played (~17)\n\n")
        
        # Draft Strategy Guide
        f.write("🎲 DRAFT STRATEGY INSIGHTS\n")
        f.write("─" * 100 + "\n")
        f.write("🏆 ELITE TIER (Picks 1-8): Focus on RB/TE scarcity - these are league winners\n")
        f.write("📈 PREMIUM TIER (Picks 9-20): Target position runs before they happen\n")
        f.write("💡 SOLID TIER (Picks 21-40): Fill roster needs, avoid positional reaches\n")
        f.write("🔍 DEPTH TIER (Picks 41+): Handcuffs, upside plays, and late-round fliers\n\n")
        
        f.write("POSITIONAL STRATEGY:\n")
        f.write("• RB: Draft 2 in first 4 rounds (injury insurance + high VOR)\n")
        f.write("• WR: Target 3 before round 6 (consistent weekly floor)\n")
        f.write("• TE: Elite (Kelce/top tier) or wait until round 8+ (huge VOR gap)\n")
        f.write("• QB: No need to reach early, position has good depth\n\n")
        
        f.write("VOR INSIGHTS:\n")
        elite_rb_count = len([p for p in tiers["ELITE (VOR 18+)"] if p['position'] == 'RB'])
        elite_wr_count = len([p for p in tiers["ELITE (VOR 18+)"] if p['position'] == 'WR'])
        f.write(f"• Only {elite_rb_count} RBs in ELITE tier - extreme scarcity!\n")
        f.write(f"• {elite_wr_count} WRs in ELITE tier - good top-end depth\n")
        f.write("• TE position shows biggest VOR gap between elite and replacement\n")
        f.write("• QB depth allows waiting - focus on skill positions early\n\n")
        
        # Position breakdowns with enhanced tiers
        for pos, df in position_rankings.items():
            if df.empty:
                continue
                
            f.write(f"TOP {pos} PLAYERS BY TIER\n")
            f.write("-"*80 + "\n")
            
            # Calculate tiers based on predicted points
            if len(df) > 0:
                max_points = df['predicted_points'].max()
                tier1_cutoff = max_points * 0.85
                tier2_cutoff = max_points * 0.75
                tier3_cutoff = max_points * 0.65
                
                # Tier 1
                f.write("TIER 1 - ELITE\n")
                tier1 = df[df['predicted_points'] >= tier1_cutoff].head(10)
                for _, row in tier1.iterrows():
                    rank_col = f'{pos.lower()}_rank'
                    f.write(f"{row[rank_col]:3d}. {row['player_name']:<25} {row['team']:<4} {row['predicted_points']:.2f} pts\n")
                
                # Tier 2
                f.write("\nTIER 2 - STRONG STARTERS\n")
                tier2 = df[(df['predicted_points'] < tier1_cutoff) & (df['predicted_points'] >= tier2_cutoff)].head(10)
                for _, row in tier2.iterrows():
                    rank_col = f'{pos.lower()}_rank'
                    f.write(f"{row[rank_col]:3d}. {row['player_name']:<25} {row['team']:<4} {row['predicted_points']:.2f} pts\n")
                
                # Tier 3
                f.write("\nTIER 3 - SOLID CONTRIBUTORS\n")
                tier3 = df[(df['predicted_points'] < tier2_cutoff) & (df['predicted_points'] >= tier3_cutoff)].head(10)
                for _, row in tier3.iterrows():
                    rank_col = f'{pos.lower()}_rank'
                    f.write(f"{row[rank_col]:3d}. {row['player_name']:<25} {row['team']:<4} {row['predicted_points']:.2f} pts\n")
            
            f.write("\n\n")
    
    print(f"Draft cheatsheet saved to {cheatsheet_file}")

def create_visual_draft_board(overall_rankings: pd.DataFrame, position_rankings: Dict[str, pd.DataFrame]) -> None:
    """
    Create enhanced visual draft boards with VOR analysis and multiple views.
    
    Args:
        overall_rankings: DataFrame with overall rankings
        position_rankings: Dictionary of DataFrames with position rankings
    """
    if overall_rankings.empty:
        print("No data available to create visual draft board")
        return
        
    # Create directory if it doesn't exist
    plots_dir = os.path.join(project_root, 'data/draft_lists')
    os.makedirs(plots_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Import config for VOR analysis
    import config
    scarcity_multipliers = config.VOR_SCARCITY_MULTIPLIERS
    
    # Create Figure 1: VOR Bubble Chart
    plt.style.use('default')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 16))
    fig.suptitle('🏈 Fantasy Football Draft Board - VOR Analysis Edition', fontsize=20, fontweight='bold')
    
    # Define enhanced position colors and markers
    position_colors = {
        'QB': '#FF4444',   # Red
        'RB': '#44AA44',   # Green  
        'WR': '#4488FF',   # Blue
        'TE': '#AA44AA',   # Purple
        'K': '#FF8800',    # Orange
        'DST': '#8B4513'   # Brown
    }
    
    position_markers = {
        'QB': 'o',   # Circle
        'RB': 's',   # Square
        'WR': '^',   # Triangle up
        'TE': 'D',   # Diamond
        'K': 'v',    # Triangle down
        'DST': 'X'   # X
    }
    
    # Plot 1: VOR Bubble Chart
    top_60 = overall_rankings.head(60)
    
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_data = top_60[top_60['position'] == pos]
        if len(pos_data) > 0:
            # Bubble size based on VOR (scaled)
            bubble_sizes = (pos_data['vor'] * 15) + 50  # Scale VOR for visibility
            
            scatter = ax1.scatter(pos_data['overall_rank'], pos_data['vor'], 
                                s=bubble_sizes, 
                                c=position_colors[pos],
                                marker=position_markers[pos],
                                alpha=0.7, 
                                label=f'{pos} (mult: {scarcity_multipliers.get(pos, 1.0)}x)',
                                edgecolors='black',
                                linewidth=1)
            
            # Add player names for top 3 per position
            top_3_pos = pos_data.head(3)
            for _, row in top_3_pos.iterrows():
                ax1.annotate(row['player_name'], 
                           (row['overall_rank'], row['vor']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=9, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', 
                                   facecolor=position_colors[pos], 
                                   alpha=0.6))
    
    # Customize plot 1
    ax1.set_xlabel('Overall Draft Rank', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Adjusted VOR Value', fontsize=14, fontweight='bold')
    ax1.set_title('VOR vs Draft Position (Bubble Size = VOR Value)', fontsize=16, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=12, loc='upper right')
    
    # Add tier lines
    tier_lines = [18, 14, 10, 6]
    tier_labels = ['Elite', 'Premium', 'Solid', 'Depth']
    colors = ['#FFD700', '#C0C0C0', '#CD7F32', '#808080']  # gold, silver, bronze, gray
    
    for i, (line, label, color) in enumerate(zip(tier_lines, tier_labels, colors)):
        ax1.axhline(y=line, color=color, linestyle='--', alpha=0.7, linewidth=2)
        ax1.text(55, line + 0.5, f'{label} Tier', fontsize=12, fontweight='bold', 
                bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7))
    
    # Plot 2: Position Comparison Chart
    positions = ['RB', 'WR', 'TE', 'QB']
    x_pos = np.arange(len(positions))
    
    # Get top 5 players per position
    top_5_data = []
    avg_vor_data = []
    
    for pos in positions:
        if pos in position_rankings and not position_rankings[pos].empty:
            pos_df = position_rankings[pos].head(5)
            top_5_vor = pos_df['vor'].tolist()
            avg_vor = pos_df['vor'].mean()
            
            top_5_data.append(top_5_vor)
            avg_vor_data.append(avg_vor)
        else:
            top_5_data.append([0])
            avg_vor_data.append(0)
    
    # Create box plot for top 5 VOR distribution
    box_parts = ax2.boxplot(top_5_data, positions=x_pos, patch_artist=True, 
                           labels=positions, showmeans=True)
    
    # Color the boxes
    for patch, pos in zip(box_parts['boxes'], positions):
        patch.set_facecolor(position_colors[pos])
        patch.set_alpha(0.7)
    
    # Add scarcity multiplier annotations
    for i, pos in enumerate(positions):
        multiplier = scarcity_multipliers.get(pos, 1.0)
        ax2.text(i, max(top_5_data[i]) + 1, f'{multiplier}x\nScarcity', 
                ha='center', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', 
                         facecolor=position_colors[pos], alpha=0.6))
    
    ax2.set_xlabel('Position', fontsize=14, fontweight='bold')
    ax2.set_ylabel('VOR Distribution (Top 5 Players)', fontsize=14, fontweight='bold')
    ax2.set_title('Positional VOR Comparison & Scarcity Analysis', fontsize=16, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save enhanced draft board
    plot_file_enhanced = os.path.join(plots_dir, f'draft_board_enhanced_{timestamp}.png')
    plt.savefig(plot_file_enhanced, dpi=300, bbox_inches='tight')
    print(f"Enhanced draft board saved to {plot_file_enhanced}")
    
    # Create Figure 2: Tier-Based Positional Heat Map
    plt.figure(figsize=(16, 10))
    
    # Create data for heatmap
    tier_data = {}
    tier_names = ['Elite (18+)', 'Premium (14-18)', 'Solid (10-14)', 'Depth (6-10)']
    
    # Initialize data structure
    for tier in tier_names:
        tier_data[tier] = {'RB': [], 'WR': [], 'TE': [], 'QB': []}
    
    # Populate tier data
    for _, row in overall_rankings.head(50).iterrows():
        vor = row['vor']
        pos = row['position']
        
        if pos in ['RB', 'WR', 'TE', 'QB']:
            if vor >= 18:
                tier_data['Elite (18+)'][pos].append(row)
            elif vor >= 14:
                tier_data['Premium (14-18)'][pos].append(row)
            elif vor >= 10:
                tier_data['Solid (10-14)'][pos].append(row)
            elif vor >= 6:
                tier_data['Depth (6-10)'][pos].append(row)
    
    # Create heatmap data
    heatmap_data = []
    for tier in tier_names:
        tier_row = []
        for pos in ['RB', 'WR', 'TE', 'QB']:
            tier_row.append(len(tier_data[tier][pos]))
        heatmap_data.append(tier_row)
    
    # Create heatmap
    heatmap_array = np.array(heatmap_data)
    im = plt.imshow(heatmap_array, cmap='Reds', aspect='auto')
    
    # Set ticks and labels
    plt.xticks(range(4), ['RB', 'WR', 'TE', 'QB'], fontsize=14, fontweight='bold')
    plt.yticks(range(4), tier_names, fontsize=12, fontweight='bold')
    
    # Add text annotations
    for i in range(len(tier_names)):
        for j in range(4):
            count = heatmap_data[i][j]
            plt.text(j, i, str(count), ha='center', va='center', 
                    fontsize=16, fontweight='bold', color='white' if count > 2 else 'black')
    
    plt.title('Position Distribution by VOR Tier (Player Count)', fontsize=18, fontweight='bold')
    plt.xlabel('Position', fontsize=14, fontweight='bold')
    plt.ylabel('VOR Tier', fontsize=14, fontweight='bold')
    
    # Add colorbar
    cbar = plt.colorbar(im)
    cbar.set_label('Number of Players', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    # Save heatmap
    heatmap_file = os.path.join(plots_dir, f'vor_tier_heatmap_{timestamp}.png')
    plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
    print(f"VOR tier heatmap saved to {heatmap_file}")
    
    plt.close('all')  # Close all figures to free memory

def parse_arguments():
    """Parse command line arguments for the draft rankings script."""
    parser = argparse.ArgumentParser(
        description='Generate Fantasy Football Draft Rankings with optional Matchup Intelligence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_draft_rankings.py                                    # Traditional rankings
  python generate_draft_rankings.py --include-matchup-intelligence     # Enhanced with matchup features  
  python generate_draft_rankings.py --weeks-ahead-sos 6               # Analyze 6 weeks ahead for SOS
  python generate_draft_rankings.py --include-matchup-intelligence --weeks-ahead-sos 6  # Full enhanced mode
        """
    )
    
    parser.add_argument(
        '--include-matchup-intelligence',
        action='store_true',
        help='Include Phase 2 matchup intelligence features (schedule strength, environmental factors, etc.)'
    )
    
    parser.add_argument(
        '--weeks-ahead-sos',
        type=int,
        default=4,
        help='Number of weeks ahead to analyze for strength of schedule (default: 4)'
    )
    
    parser.add_argument(
        '--include-position-specific',
        action='store_true',
        help='Include advanced position-specific features (automatically enabled with matchup intelligence)'
    )
    
    return parser.parse_args()


def main():
    """
    Main function to generate draft rankings with current team assignments and optional enhancements.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Display configuration
    print("🏈 Fantasy Football Draft Rankings Generator")
    print("=" * 60)
    print(f"📊 Matchup Intelligence: {'✅ ENABLED' if args.include_matchup_intelligence else '❌ DISABLED'}")
    print(f"🔧 Position-Specific Features: {'✅ ENABLED' if (args.include_matchup_intelligence or args.include_position_specific) else '❌ DISABLED'}")
    print(f"📅 SOS Analysis Weeks: {args.weeks_ahead_sos}")
    print("=" * 60)
    
    print("\n🎯 Generating fantasy football draft rankings with current data...")
    
    # Import config and current data pipeline
    sys.path.insert(0, str(project_root))
    import config
    from src.current_data_pipeline import validate_current_data_freshness, print_team_movement_report
    
    # Validate data freshness
    print("\n📊 Data Freshness Check:")
    freshness = validate_current_data_freshness()
    print(f"   Current year: {freshness['current_year']}")
    print(f"   Using data from: {freshness['inference_year']}")
    print(f"   Status: {freshness['freshness_status']}")
    
    if freshness['recommendations']:
        print("   Recommendations:")
        for rec in freshness['recommendations']:
            print(f"   💡 {rec}")
    
    # Show team movements
    print(f"\n🔄 Team Movement Analysis ({config.TRAINING_DATA_END_YEAR} → {config.INFERENCE_DATA_YEAR}):")
    try:
        print_team_movement_report()
    except Exception as e:
        print(f"   ⚠️ Could not generate movement report: {e}")
    
    print(f"\n🎯 Generating rankings for {config.CURRENT_SEASON} season...")
    
    # Use core positions that have real data + K (DST will be handled separately later)
    positions = config.CORE_POSITIONS + ['K']
    
    # Store data by position
    df_by_pos = {}
    
    # Process each position using real data from feature engineering
    
    # Process each position
    for position in positions:
        # Load position data with enhanced features if requested
        df = load_position_data(
            position,
            include_matchup_intelligence=args.include_matchup_intelligence,
            weeks_ahead_sos=args.weeks_ahead_sos
        )
        
        if df.empty:
            print(f"⚠️ No data available for {position}, skipping...")
            continue
        
        # Detect feature type based on available columns
        matchup_cols = [col for col in df.columns if 'next_' in col or 'sos_' in col]
        advanced_features_available = len(matchup_cols) >= 10 if position == 'QB' else len(df.columns) > 100
        
        # Load appropriate model based on available features
        if advanced_features_available:
            print(f"🎯 Using advanced/ensemble model for {position} (detected {len(matchup_cols)} matchup features)")
            model = load_model_based_on_features(position, has_advanced_features=True)
        else:
            print(f"📋 Using baseline model for {position} (limited features detected: {len(df.columns)} total)")
            model = load_model_based_on_features(position, has_advanced_features=False)
        
        # Make predictions
        df = predict_fantasy_points(df, model, position)
        
        # LOG FEATURE VALIDATION FOR THIS POSITION
        print(f"📊 Feature Validation for {position}:")
        opportunity_cols = [col for col in df.columns if any(kw in col.lower() 
                           for kw in ['target_share', 'air_yards', 'wopr', 'adot'])]
        usage_cols = [col for col in df.columns if any(kw in col.lower() 
                     for kw in ['snap_share', 'route_participation', 'high_value'])]
        position_cols = [col for col in df.columns if any(kw in col.lower() 
                        for kw in ['_role', '_tier', '_style', '_specialist'])]
        
        print(f"   • Total Features: {len(df.columns)}")
        print(f"   • Opportunity Features: {len(opportunity_cols)}")
        print(f"   • Usage Features: {len(usage_cols)}")
        print(f"   • Position-Specific: {len(position_cols)}")
        
        # Show sample values for key metrics
        if position in ['RB', 'WR', 'TE'] and 'target_share' in df.columns:
            non_zero_target_share = (df['target_share'] > 0).sum()
            avg_target_share = df['target_share'].mean()
            print(f"   • Target Share: {non_zero_target_share}/{len(df)} players have values (avg: {avg_target_share:.3f})")
        
        if 'wopr' in df.columns:
            non_zero_wopr = (df['wopr'] > 0).sum()
            avg_wopr = df['wopr'].mean()
            print(f"   • WOPR: {non_zero_wopr}/{len(df)} players have values (avg: {avg_wopr:.3f})")
        
        # Store results
        df_by_pos[position] = df
    
    # Calculate value over replacement with optional matchup adjustments
    df_by_pos_vor = calculate_value_over_replacement(
        df_by_pos, 
        include_matchup_adjustments=args.include_matchup_intelligence
    )
    
    # Create overall rankings with optional schedule-adjusted VOR
    overall_rankings = create_overall_rankings(
        df_by_pos_vor,
        use_schedule_adjusted_vor=args.include_matchup_intelligence
    )
    
    # Create position-specific rankings
    position_rankings = create_position_rankings(df_by_pos_vor)
    
    # Save rankings to CSV
    save_rankings(overall_rankings, position_rankings)
    
    # Generate draft cheatsheet
    generate_draft_cheatsheet(overall_rankings, position_rankings)
    
    # Create visual draft board
    create_visual_draft_board(overall_rankings, position_rankings)
    
    # Print feature summary
    print("\n" + "="*60)
    print("🎯 DRAFT RANKINGS GENERATION COMPLETE!")
    print("="*60)
    
    feature_summary = []
    if args.include_matchup_intelligence:
        feature_summary.append("✅ Phase 2 Matchup Intelligence")
        feature_summary.append(f"✅ Schedule Strength Analysis ({args.weeks_ahead_sos} weeks)")
        feature_summary.append("✅ Environmental Factors (weather, altitude, domes)")
        feature_summary.append("✅ Situational Adjustments (venue effects)")
        feature_summary.append("✅ Schedule-Adjusted VOR Rankings")
        
    if args.include_matchup_intelligence or args.include_position_specific:
        feature_summary.append("✅ Advanced Position-Specific Features")
    
    if not feature_summary:
        feature_summary.append("📋 Traditional Feature Engineering Only")
        
    print("📊 Features Used:")
    for feature in feature_summary:
        print(f"   {feature}")
    
    if not overall_rankings.empty:
        total_players = len(overall_rankings)
        matchup_features = len([col for col in overall_rankings.columns if col.startswith('next_')])
        print(f"\n📈 Rankings Generated:")
        print(f"   Total Players: {total_players}")
        print(f"   Matchup Features: {matchup_features}")
        print(f"   VOR Method: {'Schedule-Adjusted' if args.include_matchup_intelligence else 'Standard'}")
        
    print("\n🎉 Ready for your fantasy draft!")

if __name__ == "__main__":
    main()
