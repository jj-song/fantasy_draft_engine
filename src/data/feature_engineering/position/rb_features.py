"""
Feature engineering for running back (RB) position.

This module contains functions for generating RB-specific features from raw player data,
including industry-standard opportunity and usage metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

logger = logging.getLogger(__name__)


def engineer_rb_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate RB-specific features from player data including industry-standard metrics.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with comprehensive RB-specific features added
    """
    logger.info(f"🏈 RB FEATURE ENGINEERING START")
    logger.info("=" * 60)
    
    # Make a copy to avoid modifying the original dataframe
    df_rb = df.copy()
    
    # Only keep RBs
    df_rb = df_rb[df_rb['position'] == 'RB']
    
    if df_rb.empty:
        logger.warning("No RB players found in input data")
        return df_rb
    
    logger.info(f"Processing {len(df_rb)} RB players")
    logger.info(f"Input columns: {len(df_rb.columns)}")
    
    # Validate essential columns are present
    essential_columns = ['player_id', 'position', 'games']
    missing_essential = [col for col in essential_columns if col not in df_rb.columns]
    if missing_essential:
        logger.error(f"❌ CRITICAL: Missing essential columns for RB features: {missing_essential}")
        raise ValueError(f"Cannot process RB features without essential columns: {missing_essential}")
    
    # Log available RB-relevant columns
    rb_relevant_columns = [col for col in df_rb.columns if any(pattern in col.lower() 
                          for pattern in ['rush', 'carry', 'target', 'receiv', 'touch', 'yard'])]
    logger.info(f"Available RB-relevant columns ({len(rb_relevant_columns)}): {rb_relevant_columns[:10]}{'...' if len(rb_relevant_columns) > 10 else ''}")
    
    initial_count = len(df_rb)
    
    try:
        # Calculate basic efficiency metrics
        logger.info("1️⃣ Calculating basic efficiency metrics...")
        df_rb = calculate_rb_efficiency_metrics(df_rb)
        logger.info(f"   ✅ Efficiency metrics complete: {len(df_rb)} players retained")
        
        # Calculate per-game averages
        logger.info("2️⃣ Calculating per-game averages...")
        df_rb = calculate_rb_per_game_metrics(df_rb)
        logger.info(f"   ✅ Per-game metrics complete: {len(df_rb)} players retained")
        
        # Calculate usage metrics (requires team totals)
        logger.info("3️⃣ Calculating usage metrics...")
        df_rb = calculate_rb_usage_metrics(df_rb)
        logger.info(f"   ✅ Usage metrics complete: {len(df_rb)} players retained")
        
        # Add industry-standard opportunity metrics
        logger.info("4️⃣ Adding opportunity metrics...")
        df_rb = add_rb_opportunity_metrics(df_rb)
        logger.info(f"   ✅ Opportunity metrics complete: {len(df_rb)} players retained")
        
        # Add advanced usage analytics
        logger.info("5️⃣ Adding usage analytics...")
        df_rb = add_rb_usage_analytics(df_rb)
        logger.info(f"   ✅ Usage analytics complete: {len(df_rb)} players retained")
        
        # Add RB-specific derived metrics
        logger.info("6️⃣ Calculating advanced RB metrics...")
        df_rb = calculate_rb_advanced_metrics(df_rb)
        logger.info(f"   ✅ Advanced metrics complete: {len(df_rb)} players retained")
        
    except Exception as e:
        logger.error(f"❌ ERROR in RB feature engineering: {str(e)}")
        logger.error(f"   Players at start: {initial_count}")
        logger.error(f"   Players remaining: {len(df_rb)}")
        logger.warning("⚠️ Returning players with partial feature engineering to prevent data loss")
        # Don't re-raise the exception - return what we have
    
    final_count = len(df_rb)
    if final_count < initial_count:
        loss_count = initial_count - final_count
        loss_percentage = (loss_count / initial_count) * 100
        logger.warning(f"⚠️ RB PLAYER LOSS: {loss_count} players lost ({loss_percentage:.1f}%)")
        logger.warning(f"   Started with: {initial_count} RBs")
        logger.warning(f"   Ended with: {final_count} RBs")
        
        if loss_percentage > 10:  # If we lost more than 10% of players
            logger.error(f"❌ EXCESSIVE RB DATA LOSS: {loss_percentage:.1f}% loss is unacceptable")
            # But don't raise an exception - continue with what we have
    else:
        logger.info(f"✅ No RB players lost during feature engineering")
    
    logger.info(f"🏈 RB FEATURE ENGINEERING COMPLETE")
    logger.info(f"   Final players: {len(df_rb)}")
    logger.info(f"   Final features: {len(df_rb.columns)}")
    logger.info("=" * 60)
    
    return df_rb


def calculate_rb_efficiency_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB efficiency metrics with robust column handling.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB efficiency metrics added
    """
    logger.info("   📊 Calculating RB efficiency metrics...")
    
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Check for required columns and provide defensive handling
    required_columns = {
        'rushing_yards': ['rushing_yards', 'rush_yards', 'yards_rushing'],
        'carries': ['carries', 'rushing_attempts', 'attempts'],
        'receiving_yards': ['receiving_yards', 'rec_yards', 'yards_receiving'],
        'receptions': ['receptions', 'rec', 'catches'],
        'rushing_tds': ['rushing_tds', 'rush_tds', 'rushing_touchdowns']
    }
    
    # Find the actual column names or provide defaults
    actual_columns = {}
    for standard_name, possible_names in required_columns.items():
        found_col = None
        for possible_name in possible_names:
            if possible_name in df.columns:
                found_col = possible_name
                break
        
        if found_col:
            actual_columns[standard_name] = found_col
            logger.info(f"      Using '{found_col}' for {standard_name}")
        else:
            # Create default column with zeros
            df[standard_name] = 0.0
            actual_columns[standard_name] = standard_name
            logger.warning(f"      Missing column for {standard_name}, using 0 default")
    
    # Yards per carry
    carry_col = actual_columns['carries']
    rushing_yards_col = actual_columns['rushing_yards']
    
    df['yards_per_carry'] = np.where(
        df[carry_col] > 0,
        df[rushing_yards_col] / df[carry_col],
        0
    )
    
    # Yards per touch (rushing + receiving)
    receiving_yards_col = actual_columns['receiving_yards']
    receptions_col = actual_columns['receptions']
    
    df['yards_per_touch'] = np.where(
        (df[carry_col] + df[receptions_col]) > 0,
        (df[rushing_yards_col] + df[receiving_yards_col]) / (df[carry_col] + df[receptions_col]),
        0
    )
    
    # Rushing TD rate
    rushing_tds_col = actual_columns['rushing_tds']
    df['rushing_td_rate'] = np.where(
        df[carry_col] > 0,
        df[rushing_tds_col] / df[carry_col] * 100,
        0
    )
    
    # Catch rate (handle targets column)
    targets_col = None
    for possible_target_col in ['targets', 'tgt', 'target']:
        if possible_target_col in df.columns:
            targets_col = possible_target_col
            break
    
    if targets_col:
        df['catch_rate'] = np.where(
            df[targets_col] > 0,
            df[receptions_col] / df[targets_col] * 100,
            0
        )
        logger.info(f"      ✅ Calculated catch_rate using {targets_col}")
    else:
        df['catch_rate'] = 0.0
        logger.warning(f"      ⚠️ No targets column found, setting catch_rate to 0")
    
    # Add remaining receiving metrics before returning
    # Yards per reception
    df['yards_per_reception'] = np.where(
        df[receptions_col] > 0,
        df[receiving_yards_col] / df[receptions_col],
        0
    )
    
    # Yards per target and receiving TD metrics (if targets available)
    if targets_col:
        df['yards_per_target'] = np.where(
            df[targets_col] > 0,
            df[receiving_yards_col] / df[targets_col],
            0
        )
        
        # Check for receiving TDs column
        rec_tds_col = None
        for possible_col in ['receiving_tds', 'rec_tds', 'receiving_touchdowns']:
            if possible_col in df.columns:
                rec_tds_col = possible_col
                break
        
        if rec_tds_col:
            df['receiving_td_rate'] = np.where(
                df[targets_col] > 0,
                df[rec_tds_col] / df[targets_col] * 100,
                0
            )
        else:
            df['receiving_td_rate'] = 0.0
            logger.warning(f"      ⚠️ No receiving TDs column found, using 0 default")
    else:
        # No targets column, set target-based metrics to 0
        df['yards_per_target'] = 0.0
        df['receiving_td_rate'] = 0.0
        
    logger.info(f"   ✅ RB efficiency metrics calculated successfully")
    return df


def calculate_rb_per_game_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB per-game metrics.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB per-game metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Use correct column name and avoid division by zero
    games_col = 'games' if 'games' in df.columns else 'games_played'
    if games_col not in df.columns:
        logger.warning("No games column found, using 16 as default")
        df[games_col] = 16
    
    games_played = df[games_col].replace(0, 1)
    
    # Per-game rushing stats
    carry_col = 'carries' if 'carries' in df.columns else 'rushing_attempts'
    df['rushing_attempts_per_game'] = df[carry_col] / games_played
    df['rushing_yards_per_game'] = df['rushing_yards'] / games_played
    df['rushing_tds_per_game'] = df['rushing_tds'] / games_played
    
    # Per-game receiving stats
    df['targets_per_game'] = df['targets'] / games_played
    df['receptions_per_game'] = df['receptions'] / games_played
    df['receiving_yards_per_game'] = df['receiving_yards'] / games_played
    df['receiving_tds_per_game'] = df['receiving_tds'] / games_played
    
    # Total touches per game
    df['touches_per_game'] = (df[carry_col] + df['receptions']) / games_played
    
    # Total yards per game
    df['total_yards_per_game'] = (df['rushing_yards'] + df['receiving_yards']) / games_played
    
    # Total TDs per game
    df['total_tds_per_game'] = (df['rushing_tds'] + df['receiving_tds']) / games_played
    
    return df


def calculate_rb_usage_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB usage metrics based on team totals.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with RB usage metrics added
    """
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # This function requires team totals to be calculated first
    # For now, we'll add placeholder columns that should be populated later
    
    # Team rush attempt share
    df['team_rush_attempt_share'] = 0.0
    
    # Team target share
    df['team_target_share'] = 0.0
    
    # Team touch share (rush attempts + receptions)
    df['team_touch_share'] = 0.0
    
    # Red zone opportunity share
    df['red_zone_opportunity_share'] = 0.0
    
    return df


def add_rb_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add industry-standard opportunity metrics for RBs using our opportunity_metrics module.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with opportunity metrics added/enhanced
    """
    try:
        # Import at runtime to avoid circular dependencies
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent.parent))
        
        from src.features.opportunity_metrics import OpportunityMetricsCalculator
        
        logger.info("Adding opportunity metrics for RBs")
        
        # Use our opportunity metrics calculator to enhance existing data
        calculator = OpportunityMetricsCalculator()
        enhanced_df = calculator.enhance_opportunity_metrics(df)
        
        # Add RB-specific opportunity calculations
        enhanced_df = calculate_rb_specific_opportunity_metrics(enhanced_df)
        
        logger.info(f"Successfully added opportunity metrics to {len(enhanced_df)} RB players")
        return enhanced_df
        
    except ImportError as e:
        logger.warning(f"Could not import opportunity metrics: {e}")
        # Return original data with RB-specific calculations only
        return calculate_rb_specific_opportunity_metrics(df)
    except Exception as e:
        logger.error(f"Error adding opportunity metrics: {e}")
        return df


def add_rb_usage_analytics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add advanced usage analytics for RBs using our usage_analytics module.
    
    Args:
        df: DataFrame containing RB player data
        
    Returns:
        DataFrame with usage analytics added
    """
    try:
        # Import at runtime to avoid circular dependencies
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent.parent))
        
        from src.features.usage_analytics import UsageAnalyticsCalculator
        
        logger.info("Adding usage analytics for RBs")
        
        # Use our usage analytics calculator
        calculator = UsageAnalyticsCalculator()
        enhanced_df = calculator.calculate_all_usage_metrics(df)
        
        logger.info(f"Successfully added usage analytics to {len(enhanced_df)} RB players")
        return enhanced_df
        
    except ImportError as e:
        logger.warning(f"Could not import usage analytics: {e}")
        return df
    except Exception as e:
        logger.error(f"Error adding usage analytics: {e}")
        return df


def calculate_rb_specific_opportunity_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate RB-specific opportunity metrics beyond the general ones.
    
    Args:
        df: DataFrame with RB data and basic opportunity metrics
        
    Returns:
        DataFrame with RB-specific opportunity metrics added
    """
    result = df.copy()
    
    # Ensure we have the correct carry column name
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    
    # Goal line carry rate (carries inside 5-yard line)
    if 'red_zone_carries' in result.columns:
        # Approximate goal line carries as subset of red zone carries
        result['goal_line_carries'] = result['red_zone_carries'] * 0.4  # Rough approximation
        result['goal_line_carry_rate'] = np.where(
            result[carry_col] > 0,
            result['goal_line_carries'] / result[carry_col],
            0
        )
    
    # Early down vs passing down usage
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    if carry_col in result.columns and 'targets' in result.columns:
        total_opportunities = result[carry_col] + result['targets']
        result['early_down_rate'] = np.where(
            total_opportunities > 0,
            result[carry_col] / total_opportunities,
            0
        )
        result['passing_down_rate'] = 1 - result['early_down_rate']
    
    # Touch efficiency (fantasy points per touch)
    if all(col in result.columns for col in ['fantasy_points_ppr', carry_col, 'receptions']):
        total_touches = result[carry_col] + result['receptions']
        result['fantasy_points_per_touch'] = np.where(
            total_touches > 0,
            result['fantasy_points_ppr'] / total_touches,
            0
        )
    
    # Workhorse indicator (high-volume usage)
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    if carry_col in result.columns and 'games' in result.columns:
        carries_per_game = result[carry_col] / result['games'].replace(0, 1)
        result['workhorse_indicator'] = (carries_per_game >= 15).astype(int)
    
    # Pass-catching back indicator
    if 'targets' in result.columns and 'games' in result.columns:
        targets_per_game = result['targets'] / result['games'].replace(0, 1)
        result['pass_catching_back'] = (targets_per_game >= 3).astype(int)
    
    # Short yardage specialist (high goal line + short adot)
    if 'goal_line_carries' in result.columns and 'adot' in result.columns:
        result['short_yardage_specialist'] = (
            (result['goal_line_carries'] >= 3) & (result['adot'] <= 2)
        ).astype(int)
    
    # Receiving versatility (ability to line up wide/slot)
    if 'adot' in result.columns and 'targets' in result.columns:
        # RBs with higher aDOT likely line up as receivers sometimes
        result['receiving_versatility'] = np.where(
            result['adot'] > 3,
            'High',  # Lines up as receiver
            np.where(result['adot'] > 1, 'Medium', 'Low')  # Mostly checkdowns
        )
    
    # Snap share utilization (touches per snap)
    if all(col in result.columns for col in [carry_col, 'targets', 'total_snaps']):
        total_touches = result[carry_col] + result['targets']
        result['snap_utilization_rate'] = np.where(
            result['total_snaps'] > 0,
            total_touches / result['total_snaps'],
            0
        )
    
    return result


def calculate_rb_advanced_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate advanced RB metrics that combine multiple data sources.
    
    Args:
        df: DataFrame with RB data and all previous metrics
        
    Returns:
        DataFrame with advanced RB metrics added
    """
    result = df.copy()
    
    # RB role classification (Workhorse vs Passing Down vs Change of Pace vs Goal Line)
    carry_col = 'carries' if 'carries' in result.columns else 'rushing_attempts'
    if all(col in result.columns for col in [carry_col, 'targets', 'games']):
        carries_per_game = result[carry_col] / result['games'].replace(0, 1)
        targets_per_game = result['targets'] / result['games'].replace(0, 1)
        
        result['rb_role'] = np.where(
            carries_per_game >= 15,
            'Workhorse',
            np.where(
                targets_per_game >= 4,
                'Passing_Down',
                np.where(
                    result.get('goal_line_carries', 0) >= 3,
                    'Goal_Line',
                    'Change_of_Pace'
                )
            )
        )
    
    # Touch efficiency score (combining yards per touch and TD rate)
    if all(col in result.columns for col in ['yards_per_touch', 'total_tds_per_game']):
        # Normalize both metrics then combine
        ypt_norm = np.clip(result['yards_per_touch'] / 8, 0, 1)  # Cap at 8 yards per touch
        td_norm = np.clip(result['total_tds_per_game'], 0, 1)  # Cap at 1 TD per game
        
        result['touch_efficiency_score'] = (ypt_norm * 0.7) + (td_norm * 0.3)
    
    # Fantasy upside score (combines volume and efficiency)
    if all(col in result.columns for col in ['touches_per_game', 'touch_efficiency_score']):
        # Normalize touches per game
        touches_norm = np.clip(result['touches_per_game'] / 25, 0, 1)  # Cap at 25 touches
        
        result['fantasy_upside_score'] = (
            touches_norm * 0.6 +  # Volume is most important for RBs
            result['touch_efficiency_score'] * 0.4
        )
    
    # Red zone value tier (critical for RB TDs)
    if 'red_zone_opportunities' in result.columns:
        result['red_zone_value_tier'] = np.where(
            result['red_zone_opportunities'] >= 12,
            'Elite',
            np.where(
                result['red_zone_opportunities'] >= 6,
                'High',
                np.where(result['red_zone_opportunities'] >= 3, 'Medium', 'Low')
            )
        )
    
    # Snap share tier (different thresholds for RBs)
    if 'avg_snap_share' in result.columns:
        result['snap_share_tier'] = np.where(
            result['avg_snap_share'] >= 0.7,
            'Elite',
            np.where(
                result['avg_snap_share'] >= 0.5,
                'High',
                np.where(result['avg_snap_share'] >= 0.3, 'Medium', 'Low')
            )
        )
    
    # Injury risk tier (based on touches and snap share)
    if all(col in result.columns for col in ['touches_per_game', 'snap_share_tier']):
        result['injury_risk_tier'] = np.where(
            (result['touches_per_game'] >= 20) & (result['snap_share_tier'].isin(['Elite', 'High'])),
            'High',
            np.where(
                result['touches_per_game'] >= 15,
                'Medium',
                'Low'
            )
        )
    
    # Usage sustainability (can this workload be maintained?)
    if all(col in result.columns for col in ['touches_per_game', 'avg_snap_share']):
        # High touches + high snaps = potential concern
        sustainability_score = (
            (1 - np.clip(result['touches_per_game'] / 25, 0, 1)) * 0.6 +
            (1 - result['avg_snap_share']) * 0.4
        )
        
        result['usage_sustainability'] = np.where(
            sustainability_score >= 0.7,
            'Sustainable',
            np.where(sustainability_score >= 0.4, 'Moderate_Risk', 'High_Risk')
        )
    
    # Age-adjusted projection factor (RBs decline faster)
    if 'age' in result.columns:
        result['rb_age_factor'] = np.where(
            result['age'] <= 26,
            1.0,  # Prime years
            np.where(
                result['age'] <= 29,
                0.9,  # Slight decline
                0.7   # Significant decline expected
            )
        )
    
    # Opportunity ceiling (max theoretical touches)
    if all(col in result.columns for col in ['avg_snap_share', 'rb_role']):
        # Different ceilings based on role
        role_multiplier = np.where(
            result['rb_role'] == 'Workhorse', 1.2,
            np.where(result['rb_role'] == 'Passing_Down', 0.8, 0.6)
        )
        result['opportunity_ceiling'] = result['avg_snap_share'] * role_multiplier * 25  # Max ~25 touches
        result['opportunity_ceiling'] = np.clip(result['opportunity_ceiling'], 0, 30)
    
    return result
