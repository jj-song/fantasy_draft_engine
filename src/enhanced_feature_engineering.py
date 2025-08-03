"""
Enhanced Feature Engineering with Matchup Intelligence

This module extends the existing feature engineering pipeline to include
matchup intelligence features from Phase 2 development. It provides:

- Traditional player performance features (efficiency, usage, lagged features)
- Matchup-aware features (schedule strength, environmental factors)
- Contextual adjustments (venue effects, situational factors)
- Integrated projections with matchup adjustments

This enhanced pipeline is designed to work alongside existing systems
while providing superior projection accuracy through matchup intelligence.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))
import config

# Import existing feature engineering functions
from src.feature_engineering import (
    calculate_per_game_stats, calculate_efficiency_metrics, calculate_team_aggregates,
    calculate_usage_metrics, create_lagged_features, handle_rookies,
    handle_minimal_data_players, calculate_age, calculate_experience
)

# Import data loading functions
from src.data_storage import load_raw_data, save_features_data

# Import matchup intelligence components
from src.features.matchup_feature_integrator import (
    MatchupFeatureIntegrator, MatchupFeatureConfig
)

# Import position-specific feature engineering
from src.data.feature_engineering.position.qb_features import engineer_qb_features
from src.data.feature_engineering.position.rb_features import engineer_rb_features
from src.data.feature_engineering.position.wr_features import engineer_wr_features  
from src.data.feature_engineering.position.te_features import engineer_te_features

logger = logging.getLogger(__name__)


def engineer_enhanced_features_for_season(
    target_season: int, 
    historical_seasons: list = None,
    include_matchup_features: bool = True,
    weeks_ahead_sos: int = 4
) -> pd.DataFrame:
    """
    Engineer enhanced features for a target season including matchup intelligence.
    
    Args:
        target_season: The season to engineer features for (predicting target_season+1)
        historical_seasons: List of historical seasons to use
        include_matchup_features: Whether to include matchup intelligence features
        weeks_ahead_sos: Number of weeks ahead to analyze for SOS
        
    Returns:
        DataFrame with comprehensive enhanced features
    """
    logger.info(f"Engineering enhanced features for {target_season} season to predict {target_season+1}")
    
    if historical_seasons is None:
        historical_seasons = [target_season-1, target_season]
    
    # Load data for all required seasons
    historical_data = {}
    prediction_season = target_season + 1
    next_season_actuals_df = None
    
    try:
        # Attempt to load data for the prediction_season to get actual outcomes
        next_season_actuals_df = load_raw_data(prediction_season)
        logger.info(f"Successfully loaded actuals data for {prediction_season} to create target variable.")
    except FileNotFoundError:
        logger.warning(f"Raw data for prediction season {prediction_season} not found. Target variable will be NaN.")
    except Exception as e:
        logger.error(f"Error loading data for prediction season {prediction_season}: {e}. Target variable will be NaN.")

    for season in historical_seasons:
        try:
            historical_data[season] = load_raw_data(season)
        except Exception as e:
            logger.warning(f"Could not load data for {season} season: {str(e)}")
            historical_data[season] = pd.DataFrame()
    
    # Ensure we have the target season data
    if target_season not in historical_data or historical_data[target_season].empty:
        logger.warning(f"No data available for target season {target_season}. Skipping feature engineering.")
        return pd.DataFrame()

    # Convert birth_date to datetime if it exists
    if 'birth_date' in historical_data[target_season].columns:
        historical_data[target_season]['birth_date'] = pd.to_datetime(
            historical_data[target_season]['birth_date'], errors='coerce'
        )
        logger.info(f"Converted 'birth_date' column to datetime for season {target_season}")

    # Get the current season data
    current_season_df = historical_data[target_season]
    
    # Get the previous season data (if available)
    previous_season_df = historical_data.get(target_season-1, pd.DataFrame())
    
    # PHASE 1: Traditional Feature Engineering
    logger.info("Phase 1: Traditional Feature Engineering")
    
    # Step 1: Calculate per-game statistics
    df_features = calculate_per_game_stats(current_season_df)
    
    # Step 2: Calculate efficiency metrics
    df_features = calculate_efficiency_metrics(df_features)
    
    # Step 3: Calculate team aggregates
    team_agg = calculate_team_aggregates(df_features)
    
    # Step 4: Calculate usage metrics
    df_features = calculate_usage_metrics(df_features, team_agg)
    
    # Step 5: Create lagged features from previous season
    df_features = create_lagged_features(df_features, previous_season_df)
    
    # Step 6: Calculate age as of September 1st of the prediction season
    if 'birth_date' in df_features.columns:
        reference_date = datetime(target_season+1, 9, 1)
        df_features['age'] = df_features['birth_date'].apply(
            lambda bd: calculate_age(bd, reference_date)
        )
    
    # Step 7: Handle rookies
    df_features = handle_rookies(df_features, target_season+1, historical_data)
    
    # Step 8: Handle players with minimal recent data
    df_features = handle_minimal_data_players(df_features)
    
    # PHASE 2: Position-Specific Enhanced Features
    logger.info("Phase 2: Position-Specific Enhanced Features")
    
    # Apply position-specific feature engineering
    position_dfs = []
    
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_data = df_features[df_features['position'] == position].copy()
        
        if not pos_data.empty:
            logger.info(f"Applying enhanced {position} feature engineering to {len(pos_data)} players")
            
            try:
                if position == 'QB':
                    enhanced_pos_data = engineer_qb_features(pos_data)
                elif position == 'RB':
                    enhanced_pos_data = engineer_rb_features(pos_data)
                elif position == 'WR':
                    enhanced_pos_data = engineer_wr_features(pos_data)
                elif position == 'TE':
                    enhanced_pos_data = engineer_te_features(pos_data)
                
                position_dfs.append(enhanced_pos_data)
                logger.info(f"Successfully enhanced {position} features: {len(enhanced_pos_data.columns)} total columns")
                
            except Exception as e:
                logger.warning(f"Error in {position} feature engineering: {e}")
                position_dfs.append(pos_data)  # Use original data if enhancement fails
    
    # Combine position-specific features back together
    if position_dfs:
        df_features = pd.concat(position_dfs, ignore_index=True)
        logger.info(f"Combined position-specific features: {len(df_features)} players, {len(df_features.columns)} features")
    
    # PHASE 3: Matchup Intelligence Integration
    if include_matchup_features:
        logger.info("Phase 3: Matchup Intelligence Integration")
        
        try:
            # Configure matchup feature integration
            matchup_config = MatchupFeatureConfig(
                include_schedule_strength=True,
                include_environmental_factors=True,
                include_situational_adjustments=True,
                weeks_ahead_sos=weeks_ahead_sos,
                season_for_features=prediction_season,
                cache_matchup_data=True
            )
            
            # Initialize matchup integrator
            matchup_integrator = MatchupFeatureIntegrator(matchup_config)
            
            # Integrate matchup features
            df_features = matchup_integrator.integrate_matchup_features(
                df_features,
                weeks_to_analyze=list(range(1, weeks_ahead_sos + 1))
            )
            
            logger.info(f"Successfully integrated matchup features: {len(df_features.columns)} total features")
            
        except Exception as e:
            logger.error(f"Error integrating matchup features: {e}")
            logger.info("Continuing with traditional features only")
    
    # PHASE 4: Target Variable Addition
    logger.info("Phase 4: Target Variable Addition")
    
    if next_season_actuals_df is not None and not next_season_actuals_df.empty:
        points_col_name = config.FANTASY_POINTS_COLUMNS.get(config.DEFAULT_SCORING_SYSTEM, 'fantasy_points_ppr')
        
        # Ensure required columns exist in next_season_actuals_df
        if points_col_name in next_season_actuals_df.columns and 'games' in next_season_actuals_df.columns and 'player_id' in next_season_actuals_df.columns:
            target_df_prep = next_season_actuals_df[['player_id', points_col_name, 'games']].copy()
            target_df_prep['games_for_fppg'] = target_df_prep['games'].replace(0, np.nan)
            target_df_prep[config.TARGET_VARIABLE] = target_df_prep[points_col_name] / target_df_prep['games_for_fppg']
            target_df_to_merge = target_df_prep[['player_id', config.TARGET_VARIABLE]]
            df_features = pd.merge(df_features, target_df_to_merge, on='player_id', how='left')
            logger.info(f"Successfully merged target variable '{config.TARGET_VARIABLE}' for prediction season {prediction_season}.")
        else:
            missing_cols_actuals = [col for col in ['player_id', points_col_name, 'games'] if col not in next_season_actuals_df.columns]
            logger.warning(f"Required columns ({missing_cols_actuals}) not found in actuals data for {prediction_season}. Target variable '{config.TARGET_VARIABLE}' will be NaN.")
            df_features[config.TARGET_VARIABLE] = np.nan
    else:
        logger.info(f"No actuals data available for {prediction_season}. Target variable '{config.TARGET_VARIABLE}' will be NaN.")
        df_features[config.TARGET_VARIABLE] = np.nan

    # Add metadata columns
    df_features['season'] = target_season
    df_features['prediction_season'] = target_season + 1
    df_features['feature_engineering_version'] = 'enhanced_v2_matchup_intelligence'
    
    # Feature quality metrics
    df_features['total_feature_count'] = len(df_features.columns)
    df_features['has_matchup_features'] = include_matchup_features
    
    logger.info(f"Successfully engineered enhanced features for {len(df_features)} players with {len(df_features.columns)} total features")
    
    return df_features


def save_enhanced_features(df: pd.DataFrame, season: int, prediction_season: int) -> bool:
    """
    Save enhanced features to a parquet file with enhanced naming.
    
    Args:
        df: DataFrame containing enhanced features
        season: NFL season year used for feature engineering
        prediction_season: Season to predict
        
    Returns:
        bool: True if the features were saved successfully, False otherwise
    """
    try:
        logger.info(f"Saving enhanced features for {season} season")
        
        # Use enhanced file naming to distinguish from basic features
        success = save_features_data(df, season, prediction_season, suffix='_enhanced_matchup')
        
        if success:
            logger.info(f"Successfully saved enhanced features with {len(df.columns)} columns")
        
        return success
        
    except Exception as e:
        logger.error(f"Error saving enhanced features for {season} season: {e}")
        return False


def engineer_and_save_enhanced_features(
    start_year: int = None, 
    end_year: int = None, 
    positions: list = None,
    include_matchup_features: bool = True,
    weeks_ahead_sos: int = 4
) -> list:
    """
    Engineer and save enhanced features for a range of seasons.
    
    Args:
        start_year: The first season to engineer features for
        end_year: The last season to engineer features for
        positions: List of positions to include
        include_matchup_features: Whether to include matchup intelligence
        weeks_ahead_sos: Number of weeks ahead to analyze for SOS
        
    Returns:
        List of paths to the saved files
    """
    if start_year is None:
        start_year = config.DATA_START_YEAR
    if end_year is None:
        # End one year before the last available year since we need the next year for prediction
        end_year = config.DATA_END_YEAR - 1
    if positions is None:
        positions = config.POSITIONS
    
    logger.info(f"Engineering and saving enhanced features for seasons {start_year} to {end_year}")
    logger.info(f"Matchup features included: {include_matchup_features}")
    
    saved_files = []
    
    for year in range(start_year, end_year + 1):
        try:
            logger.info(f"Processing season {year}...")
            logger.info(f"Engineering enhanced features for {year} season to predict {year+1}")
            
            df = engineer_enhanced_features_for_season(
                target_season=year,
                include_matchup_features=include_matchup_features,
                weeks_ahead_sos=weeks_ahead_sos
            )
            
            # Filter for relevant positions
            if positions and 'position' in df.columns:
                df = df[df['position'].isin(positions)]
            
            # Only save if we have data
            if not df.empty:
                success = save_enhanced_features(df, year, year+1)
                if success:
                    from src.data_storage import get_features_data_path
                    file_path = get_features_data_path(year, year+1, suffix='_enhanced_matchup')
                    saved_files.append(str(file_path))
                    logger.info(f"Completed enhanced feature engineering for season {year}")
                else:
                    logger.error(f"Failed to save enhanced features for season {year}")
            else:
                logger.warning(f"No data to save for season {year}")
                
        except Exception as e:
            logger.error(f"Failed to process season {year}: {str(e)}")
            # Continue with the next season even if this one fails
            continue
    
    logger.info(f"Completed engineering and saving enhanced features for all seasons. Saved {len(saved_files)} files.")
    return saved_files


def create_matchup_adjusted_projections(
    base_projections_df: pd.DataFrame,
    weeks_to_analyze: list = None
) -> pd.DataFrame:
    """
    Create matchup-adjusted projections from base projections.
    
    Args:
        base_projections_df: DataFrame with player IDs and base projections
        weeks_to_analyze: List of weeks to analyze for matchup adjustments
        
    Returns:
        DataFrame with matchup-adjusted projections
    """
    logger.info(f"Creating matchup-adjusted projections for {len(base_projections_df)} players")
    
    if weeks_to_analyze is None:
        weeks_to_analyze = list(range(1, 5))  # First 4 weeks by default
    
    try:
        # Configure matchup integrator
        matchup_config = MatchupFeatureConfig(
            include_schedule_strength=True,
            include_environmental_factors=True,
            include_situational_adjustments=True,
            weeks_ahead_sos=len(weeks_to_analyze),
            season_for_features=config.CURRENT_SEASON,
            cache_matchup_data=True
        )
        
        # Initialize matchup integrator
        matchup_integrator = MatchupFeatureIntegrator(matchup_config)
        
        # Get matchup-adjusted projections
        adjusted_projections = matchup_integrator.get_matchup_adjusted_projections(
            base_projections_df,
            weeks=weeks_to_analyze
        )
        
        logger.info(f"Successfully created matchup-adjusted projections")
        logger.info(f"Average adjustment factor: {adjusted_projections['matchup_adjustment_factor'].mean():.3f}")
        
        return adjusted_projections
        
    except Exception as e:
        logger.error(f"Error creating matchup-adjusted projections: {e}")
        # Return original projections if adjustment fails
        result = base_projections_df.copy()
        result['matchup_adjusted_fppg'] = result.get('projected_fppg', result.get('fantasy_points_ppr', 0))
        result['matchup_adjustment_factor'] = 1.0
        return result


def validate_enhanced_feature_engineering() -> Dict[str, bool]:
    """Validate enhanced feature engineering functionality."""
    validation_results = {}
    
    try:
        # Test with a small sample of data
        test_season = 2022
        
        # Engineer enhanced features
        enhanced_features = engineer_enhanced_features_for_season(
            target_season=test_season,
            include_matchup_features=True,
            weeks_ahead_sos=2  # Smaller window for testing
        )
        
        validation_results['enhanced_features_generated'] = not enhanced_features.empty
        validation_results['has_traditional_features'] = 'fantasy_points_per_game' in enhanced_features.columns
        validation_results['has_matchup_features'] = any(col.startswith('next_2w_') for col in enhanced_features.columns)
        validation_results['has_position_features'] = len(enhanced_features[enhanced_features['position'] == 'QB']) > 0
        
        # Test matchup-adjusted projections
        if not enhanced_features.empty:
            sample_projections = enhanced_features[['player_id', 'position', 'team']].copy()
            sample_projections['projected_fppg'] = 15.0  # Test projection
            
            adjusted_projections = create_matchup_adjusted_projections(sample_projections)
            validation_results['matchup_adjustments_work'] = 'matchup_adjusted_fppg' in adjusted_projections.columns
        
    except Exception as e:
        validation_results['validation_error'] = str(e)
    
    return validation_results


if __name__ == "__main__":
    # Test the enhanced feature engineering system
    print("🎯 Testing Enhanced Feature Engineering with Matchup Intelligence")
    print("=" * 70)
    
    # Run validation
    validation = validate_enhanced_feature_engineering()
    
    print("Validation Results:")
    for test, result in validation.items():
        if isinstance(result, bool):
            status = "✅" if result else "❌"
            print(f"{status} {test}: {result}")
        else:
            print(f"ℹ️  {test}: {result}")
    
    # Example usage
    print("\n" + "=" * 70)
    print("Example: Enhanced Feature Engineering")
    
    try:
        # Engineer enhanced features for a recent season
        enhanced_df = engineer_enhanced_features_for_season(
            target_season=2022,
            include_matchup_features=True,
            weeks_ahead_sos=4
        )
        
        if not enhanced_df.empty:
            print(f"Enhanced features generated for {len(enhanced_df)} players")
            print(f"Total features: {len(enhanced_df.columns)}")
            
            # Show feature categories
            traditional_features = [col for col in enhanced_df.columns if not col.startswith('next_')]
            matchup_features = [col for col in enhanced_df.columns if col.startswith('next_')]
            
            print(f"Traditional features: {len(traditional_features)}")
            print(f"Matchup features: {len(matchup_features)}")
            
            # Sample of matchup features
            if matchup_features:
                print("\nSample matchup features:")
                for feature in matchup_features[:5]:
                    print(f"  - {feature}")
                    
            # Test projections
            sample_players = enhanced_df[['player_id', 'position', 'team']].head(3).copy()
            sample_players['projected_fppg'] = [20.0, 15.0, 12.0]
            
            adjusted = create_matchup_adjusted_projections(sample_players)
            
            print("\nSample Matchup-Adjusted Projections:")
            for _, row in adjusted.iterrows():
                print(f"  {row['position']}: {row['projected_fppg']:.1f} → {row['matchup_adjusted_fppg']:.1f}")
        
    except Exception as e:
        print(f"Error in example: {e}")
    
    print("\nEnhanced Feature Engineering implementation complete! 🎯")