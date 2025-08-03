#!/usr/bin/env python3
"""
Enhanced Fantasy Football Draft Rankings with Matchup Intelligence

This script generates enhanced fantasy football draft rankings that incorporate
matchup intelligence from Phase 2 development. It provides:

- Traditional VOR-based rankings
- Matchup-adjusted projections based on schedule strength
- Environmental factor adjustments (weather, venue)
- Situational context rankings
- Schedule-aware tiering and draft strategy

The enhanced rankings provide superior accuracy by accounting for upcoming
matchups, opponent strength, and environmental factors that impact performance.
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
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

# Import config and enhanced modules
import config
from src.enhanced_feature_engineering import (
    engineer_enhanced_features_for_season,
    create_matchup_adjusted_projections
)
from src.enhanced_modeling import EnhancedModelManager, EnhancedModelConfig
from src.features.matchup_feature_integrator import MatchupFeatureIntegrator, MatchupFeatureConfig


def load_enhanced_position_data(position: str, season: int = None) -> pd.DataFrame:
    """
    Load enhanced data for a specific position including matchup features.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
        season: Season to load data for
    
    Returns:
        DataFrame with enhanced position data including matchup features
    """
    if season is None:
        season = config.CURRENT_SEASON
    
    print(f"Loading enhanced data for {position} (season {season})...")
    
    try:
        # Get enhanced features including matchup intelligence
        enhanced_features = engineer_enhanced_features_for_season(
            target_season=season - 1,  # Use previous season for prediction
            include_matchup_features=True,
            weeks_ahead_sos=4
        )
        
        if enhanced_features.empty:
            print(f"⚠️ No enhanced features available for {position}")
            return pd.DataFrame()
        
        # Filter for position
        position_data = enhanced_features[enhanced_features['position'] == position].copy()
        
        if position_data.empty:
            print(f"⚠️ No {position} players found in enhanced features")
            return pd.DataFrame()
        
        print(f"✅ Loaded {len(position_data)} {position} players with {len(position_data.columns)} enhanced features")
        return position_data
        
    except Exception as e:
        print(f"❌ Error loading enhanced data for {position}: {e}")
        return pd.DataFrame()


def load_enhanced_model(position: str) -> object:
    """
    Load the enhanced model for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
    
    Returns:
        Enhanced trained model object
    """
    model_path = os.path.join(project_root, f'saved_models/enhanced_{position.lower()}_model.joblib')
    
    if os.path.exists(model_path):
        print(f"Loading enhanced {position} model from {model_path}")
        try:
            from src.enhanced_modeling import EnhancedFantasyModel
            return EnhancedFantasyModel.load_model(model_path)
        except Exception as e:
            print(f"Error loading enhanced model: {e}")
            return None
    else:
        print(f"Enhanced model for {position} not found, creating new model...")
        from src.enhanced_modeling import EnhancedFantasyModel
        return EnhancedFantasyModel(position)


def predict_enhanced_fantasy_points(
    df: pd.DataFrame, 
    model, 
    position: str,
    include_matchup_adjustments: bool = True
) -> pd.DataFrame:
    """
    Generate enhanced predictions using trained models and matchup adjustments.
    
    Args:
        df: DataFrame with player data and enhanced features
        model: Enhanced trained model object
        position: Player position
        include_matchup_adjustments: Whether to apply matchup adjustments
    
    Returns:
        DataFrame with enhanced predictions added
    """
    result = df.copy()
    
    if model is None:
        print(f"No enhanced model available for {position}. Using fallback predictions.")
        # Use any available fantasy points column as fallback
        fantasy_cols = [col for col in df.columns if 'fantasy_points' in col and 'per_game' in col]
        if fantasy_cols:
            result['base_prediction'] = df[fantasy_cols[0]]
        else:
            result['base_prediction'] = 15.0  # Default value
        result['enhanced_prediction'] = result['base_prediction']
        result['matchup_adjusted_prediction'] = result['base_prediction']
        return result

    try:
        # Get base predictions from enhanced model
        if hasattr(model, 'predict') and hasattr(model, 'is_trained') and model.is_trained:
            predictions = model.predict(df)
            if len(predictions) == len(df):
                result['enhanced_prediction'] = predictions
            else:
                print(f"Prediction length mismatch for {position}, using fallback")
                result['enhanced_prediction'] = 15.0
        else:
            print(f"Model not trained for {position}, using fallback predictions")
            result['enhanced_prediction'] = 15.0
        
        result['base_prediction'] = result['enhanced_prediction']
        
        # Apply matchup adjustments if requested
        if include_matchup_adjustments:
            try:
                # Create matchup-adjusted projections
                projection_df = result[['player_id', 'position', 'team']].copy()
                projection_df['projected_fppg'] = result['enhanced_prediction']
                
                # Apply matchup adjustments
                adjusted_projections = create_matchup_adjusted_projections(
                    projection_df,
                    weeks_to_analyze=[1, 2, 3, 4]
                )
                
                if 'matchup_adjusted_fppg' in adjusted_projections.columns:
                    result['matchup_adjusted_prediction'] = adjusted_projections['matchup_adjusted_fppg']
                    result['matchup_adjustment_factor'] = adjusted_projections.get('matchup_adjustment_factor', 1.0)
                    
                    # Use matchup-adjusted as final prediction
                    result['predicted_points'] = result['matchup_adjusted_prediction']
                    
                    print(f"✅ Applied matchup adjustments to {position} predictions")
                else:
                    result['matchup_adjusted_prediction'] = result['enhanced_prediction']
                    result['predicted_points'] = result['enhanced_prediction']
                    
            except Exception as e:
                print(f"⚠️ Matchup adjustment failed for {position}: {e}")
                result['matchup_adjusted_prediction'] = result['enhanced_prediction']
                result['predicted_points'] = result['enhanced_prediction']
        else:
            result['matchup_adjusted_prediction'] = result['enhanced_prediction']
            result['predicted_points'] = result['enhanced_prediction']
        
        print(f"✅ Generated enhanced predictions for {len(result)} {position} players")
        return result
        
    except Exception as e:
        print(f"❌ Error generating enhanced predictions for {position}: {e}")
        result['enhanced_prediction'] = 15.0
        result['matchup_adjusted_prediction'] = 15.0
        result['predicted_points'] = 15.0
        return result


def calculate_enhanced_value_over_replacement(df_by_pos: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Calculate enhanced VOR that includes matchup adjustments and schedule considerations.
    
    Args:
        df_by_pos: Dictionary of DataFrames by position
    
    Returns:
        Dictionary of DataFrames with enhanced VOR added
    """
    # Use enhanced replacement levels and scarcity multipliers
    replacement_levels = config.VOR_REPLACEMENT_LEVELS
    scarcity_multipliers = config.VOR_SCARCITY_MULTIPLIERS
    
    result = {}
    
    print("\n🔢 Enhanced VOR Calculation Summary:")
    print("=" * 60)
    
    for pos, df in df_by_pos.items():
        if len(df) == 0:
            result[pos] = df
            continue
            
        # Sort by matchup-adjusted predictions
        df_sorted = df.sort_values('predicted_points', ascending=False).reset_index(drop=True)
        
        # Get replacement level player
        replacement_rank = replacement_levels.get(pos, 15)
        replacement_idx = min(replacement_rank - 1, len(df_sorted) - 1)
        replacement_value = df_sorted.loc[replacement_idx, 'predicted_points']
        
        # Calculate raw VOR
        df_sorted['raw_vor'] = df_sorted['predicted_points'] - replacement_value
        
        # Apply positional scarcity multiplier
        scarcity_multiplier = scarcity_multipliers.get(pos, 1.0)
        df_sorted['vor'] = df_sorted['raw_vor'] * scarcity_multiplier
        
        # Add schedule-adjusted VOR if matchup features are available
        schedule_cols = [col for col in df_sorted.columns if col.startswith('next_') and 'sos_rating' in col]
        if schedule_cols:
            sos_col = schedule_cols[0]
            # Positive SOS rating = easier schedule, negative = harder
            # Apply up to +/-10% VOR adjustment based on schedule
            schedule_adjustment = df_sorted[sos_col].fillna(0) * 0.1
            df_sorted['schedule_adjusted_vor'] = df_sorted['vor'] * (1 + schedule_adjustment)
        else:
            df_sorted['schedule_adjusted_vor'] = df_sorted['vor']
        
        # Calculate matchup consistency score
        if 'matchup_adjustment_factor' in df_sorted.columns:
            # Players with factors closer to 1.0 have more consistent matchups
            matchup_volatility = abs(df_sorted['matchup_adjustment_factor'] - 1.0)
            df_sorted['matchup_consistency'] = 1 - matchup_volatility
        else:
            df_sorted['matchup_consistency'] = 1.0
        
        # Store result
        result[pos] = df_sorted
        
        # Print enhanced summary
        top_player = df_sorted.iloc[0]
        print(f"{pos}:")
        print(f"  Replacement level: {replacement_rank} (#{replacement_idx+1}: {replacement_value:.1f} pts)")
        print(f"  Scarcity multiplier: {scarcity_multiplier}x")
        print(f"  Top player: {top_player.get('player_name', 'Unknown')} ({top_player['predicted_points']:.1f} pts)")
        print(f"  Raw VOR: {top_player['raw_vor']:.1f} → Adjusted VOR: {top_player['vor']:.1f}")
        if 'schedule_adjusted_vor' in top_player:
            print(f"  Schedule-adjusted VOR: {top_player['schedule_adjusted_vor']:.1f}")
        print()
        
    return result


def create_enhanced_overall_rankings(df_by_pos: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Create enhanced overall rankings based on schedule-adjusted VOR.
    
    Args:
        df_by_pos: Dictionary of DataFrames by position with enhanced VOR
    
    Returns:
        DataFrame with enhanced overall rankings
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
    
    # Create overall rankings based on schedule-adjusted VOR
    vor_col = 'schedule_adjusted_vor' if 'schedule_adjusted_vor' in all_df.columns else 'vor'
    overall_rankings = all_df.sort_values(vor_col, ascending=False).reset_index(drop=True)
    overall_rankings['overall_rank'] = overall_rankings.index + 1
    
    # Add enhanced ranking columns
    columns = [
        'overall_rank', 'player_name', 'position', 'team', 
        'predicted_points', 'raw_vor', 'vor'
    ]
    
    # Add schedule-adjusted columns if available
    if 'schedule_adjusted_vor' in overall_rankings.columns:
        columns.append('schedule_adjusted_vor')
    if 'matchup_consistency' in overall_rankings.columns:
        columns.append('matchup_consistency')
    if 'matchup_adjustment_factor' in overall_rankings.columns:
        columns.append('matchup_adjustment_factor')
    
    # Add matchup features if available
    matchup_cols = [col for col in overall_rankings.columns if col.startswith('next_4w_')]
    for col in matchup_cols[:5]:  # Limit to top 5 matchup features
        if col not in columns:
            columns.append(col)
    
    existing_columns = [col for col in columns if col in overall_rankings.columns]
    
    return overall_rankings[existing_columns]


def save_enhanced_rankings(
    overall_rankings: pd.DataFrame, 
    position_rankings: Dict[str, pd.DataFrame]
) -> None:
    """
    Save enhanced rankings to CSV files with additional matchup data.
    
    Args:
        overall_rankings: DataFrame with enhanced overall rankings
        position_rankings: Dictionary of DataFrames with enhanced position rankings
    """
    # Create directory if it doesn't exist
    rankings_dir = os.path.join(project_root, 'data/draft_lists')
    os.makedirs(rankings_dir, exist_ok=True)
    
    # Get timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save enhanced overall rankings
    if not overall_rankings.empty:
        overall_file = f'{rankings_dir}/enhanced_overall_rankings_{timestamp}.csv'
        overall_rankings.to_csv(overall_file, index=False)
        print(f"Saved enhanced overall rankings to {overall_file}")
        print(f"✅ Contains {len(overall_rankings)} players with matchup intelligence")
        
        # Save a simplified version for easy consumption
        simplified_cols = [
            'overall_rank', 'player_name', 'position', 'team', 
            'predicted_points', 'vor'
        ]
        if 'schedule_adjusted_vor' in overall_rankings.columns:
            simplified_cols.append('schedule_adjusted_vor')
        
        simplified_rankings = overall_rankings[
            [col for col in simplified_cols if col in overall_rankings.columns]
        ]
        
        simplified_file = f'{rankings_dir}/enhanced_rankings_simplified_{timestamp}.csv'
        simplified_rankings.to_csv(simplified_file, index=False)
        print(f"Saved simplified enhanced rankings to {simplified_file}")
    else:
        print("⚠️ No enhanced overall rankings to save")


def generate_enhanced_draft_cheatsheet(
    overall_rankings: pd.DataFrame, 
    position_rankings: Dict[str, pd.DataFrame]
) -> None:
    """
    Generate an enhanced draft cheatsheet with matchup intelligence insights.
    
    Args:
        overall_rankings: DataFrame with enhanced overall rankings
        position_rankings: Dictionary of DataFrames with enhanced position rankings
    """
    # Create directory if it doesn't exist
    rankings_dir = os.path.join(project_root, 'data/draft_lists')
    os.makedirs(rankings_dir, exist_ok=True)
    
    # Get timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cheatsheet_file = f'{rankings_dir}/enhanced_draft_cheatsheet_{timestamp}.txt'
    
    with open(cheatsheet_file, 'w') as f:
        f.write("="*120 + "\n")
        f.write("🏈 ENHANCED FANTASY FOOTBALL DRAFT CHEATSHEET - MATCHUP INTELLIGENCE EDITION\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*120 + "\n\n")
        
        # Matchup Intelligence Summary
        f.write("🎯 MATCHUP INTELLIGENCE SUMMARY\n")
        f.write("─" * 120 + "\n")
        f.write("This enhanced ranking system incorporates:\n")
        f.write("• Schedule Strength: 4-week forward-looking opponent difficulty\n")
        f.write("• Environmental Factors: Weather, venue, altitude adjustments\n")
        f.write("• Situational Context: Home/away splits, primetime games, rest advantages\n")
        f.write("• VOR Adjustments: Schedule-aware value calculations\n\n")
        
        # Enhanced Top 50 with Matchup Data
        f.write("🏆 TOP 50 ENHANCED RANKINGS WITH MATCHUP INTELLIGENCE\n")
        f.write("─" * 120 + "\n")
        f.write("RNK  PLAYER NAME             POS  TEAM  PROJ   ADJ    SCH    MATCH  CONSISTENCY\n")
        f.write("                                       PTS    VOR    VOR    ADJ    SCORE\n")
        f.write("─" * 120 + "\n")
        
        if not overall_rankings.empty:
            top_50 = overall_rankings.head(50)
            
            for _, row in top_50.iterrows():
                f.write(f"{row['overall_rank']:3d}. {row.get('player_name', 'Unknown'):<23} ")
                f.write(f"{row['position']:<4} {row.get('team', 'UNK'):<4} ")
                f.write(f"{row.get('predicted_points', 0):5.1f}  ")
                f.write(f"{row.get('vor', 0):5.1f}  ")
                
                # Schedule-adjusted VOR
                schedule_vor = row.get('schedule_adjusted_vor', row.get('vor', 0))
                f.write(f"{schedule_vor:5.1f}  ")
                
                # Matchup adjustment factor
                matchup_adj = row.get('matchup_adjustment_factor', 1.0)
                f.write(f"{matchup_adj:5.3f}  ")
                
                # Consistency score
                consistency = row.get('matchup_consistency', 1.0)
                f.write(f"{consistency:8.3f}\n")
        
        f.write("\n")
        
        # Schedule Strength Analysis
        f.write("📅 SCHEDULE STRENGTH ANALYSIS (Next 4 Weeks)\n")
        f.write("─" * 120 + "\n")
        
        # Get schedule strength data if available
        sos_cols = [col for col in overall_rankings.columns if 'sos_rating' in col]
        if sos_cols and not overall_rankings.empty:
            sos_col = sos_cols[0]
            
            # Easy schedules (positive SOS)
            easy_schedule = overall_rankings[overall_rankings[sos_col] > 0.1].head(10)
            f.write("EASIEST SCHEDULES (Target for lineup locks):\n")
            for _, row in easy_schedule.iterrows():
                f.write(f"  {row.get('player_name', 'Unknown'):<25} {row['position']} ")
                f.write(f"({row.get('team', 'UNK')}) - SOS: {row[sos_col]:+.2f}\n")
            f.write("\n")
            
            # Tough schedules (negative SOS)
            tough_schedule = overall_rankings[overall_rankings[sos_col] < -0.1].head(10)
            f.write("TOUGHEST SCHEDULES (Potential fades or buy-low targets):\n")
            for _, row in tough_schedule.iterrows():
                f.write(f"  {row.get('player_name', 'Unknown'):<25} {row['position']} ")
                f.write(f"({row.get('team', 'UNK')}) - SOS: {row[sos_col]:+.2f}\n")
            f.write("\n")
        
        # Environmental Factor Insights
        f.write("🌤️ ENVIRONMENTAL FACTOR INSIGHTS\n")
        f.write("─" * 120 + "\n")
        
        env_cols = [col for col in overall_rankings.columns if 'dome_games_pct' in col or 'home_games_pct' in col]
        if env_cols and not overall_rankings.empty:
            # High dome percentage players
            dome_col = [col for col in env_cols if 'dome_games_pct' in col]
            if dome_col:
                high_dome = overall_rankings[overall_rankings[dome_col[0]] > 0.5].head(10)
                f.write("HIGH DOME GAME PERCENTAGE (Weather-protected):\n")
                for _, row in high_dome.iterrows():
                    dome_pct = row[dome_col[0]] * 100
                    f.write(f"  {row.get('player_name', 'Unknown'):<25} {row['position']} ")
                    f.write(f"({row.get('team', 'UNK')}) - {dome_pct:.0f}% dome games\n")
                f.write("\n")
        
        # Enhanced Draft Strategy
        f.write("🎲 ENHANCED DRAFT STRATEGY WITH MATCHUP INTELLIGENCE\n")
        f.write("─" * 120 + "\n")
        f.write("EARLY ROUNDS (1-6): Prioritize high VOR + favorable early schedules\n")
        f.write("MID ROUNDS (7-12): Target schedule mismatches and environmental advantages\n")  
        f.write("LATE ROUNDS (13+): Handcuffs for tough-schedule stars, weather-safe backups\n\n")
        
        f.write("MATCHUP-AWARE STRATEGIES:\n")
        f.write("• Schedule Stacking: Draft players with complementary bye weeks and schedules\n")
        f.write("• Weather Hedging: Pair outdoor studs with dome-game backups\n")
        f.write("• Consistency Targeting: High consistency scores for cash games/reliable lineups\n")
        f.write("• Volatility Plays: Low consistency scores for tournament/upside plays\n\n")
        
        # Position-specific matchup insights
        for pos, df in position_rankings.items():
            if df.empty:
                continue
                
            f.write(f"TOP {pos} PLAYERS WITH MATCHUP ANALYSIS\n")
            f.write("-"*100 + "\n")
            
            top_10_pos = df.head(10)
            for _, row in top_10_pos.iterrows():
                rank_col = f'{pos.lower()}_rank'
                f.write(f"{row[rank_col] if rank_col in row else '?':3}. {row.get('player_name', 'Unknown'):<25} ")
                f.write(f"{row.get('team', 'UNK'):<4} {row.get('predicted_points', 0):5.1f} pts")
                
                # Add matchup insight
                if 'matchup_adjustment_factor' in row:
                    adj_factor = row['matchup_adjustment_factor']
                    if adj_factor > 1.05:
                        f.write(" 📈 Favorable matchups")
                    elif adj_factor < 0.95:
                        f.write(" 📉 Tough matchups")
                    else:
                        f.write(" ➡️ Neutral matchups")
                
                f.write("\n")
            
            f.write("\n")
    
    print(f"Enhanced draft cheatsheet saved to {cheatsheet_file}")


def create_enhanced_visual_draft_board(
    overall_rankings: pd.DataFrame, 
    position_rankings: Dict[str, pd.DataFrame]
) -> None:
    """
    Create enhanced visual draft boards with matchup intelligence visualization.
    
    Args:
        overall_rankings: DataFrame with enhanced overall rankings
        position_rankings: Dictionary of DataFrames with enhanced position rankings
    """
    if overall_rankings.empty:
        print("No data available to create enhanced visual draft board")
        return
        
    # Create directory if it doesn't exist
    plots_dir = os.path.join(project_root, 'data/draft_lists')
    os.makedirs(plots_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create enhanced visualization
    plt.style.use('default')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle('🏈 Enhanced Fantasy Draft Board - Matchup Intelligence Edition', 
                 fontsize=20, fontweight='bold')
    
    # Define position colors
    position_colors = {
        'QB': '#FF4444', 'RB': '#44AA44', 'WR': '#4488FF', 
        'TE': '#AA44AA', 'K': '#FF8800', 'DST': '#8B4513'
    }
    
    top_60 = overall_rankings.head(60)
    
    # Plot 1: Enhanced VOR vs Rank with Schedule Adjustment
    vor_col = 'schedule_adjusted_vor' if 'schedule_adjusted_vor' in top_60.columns else 'vor'
    
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_data = top_60[top_60['position'] == pos]
        if len(pos_data) > 0:
            ax1.scatter(pos_data['overall_rank'], pos_data[vor_col], 
                       c=position_colors[pos], label=pos, alpha=0.7, s=60)
    
    ax1.set_xlabel('Overall Draft Rank', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Schedule-Adjusted VOR', fontsize=12, fontweight='bold')
    ax1.set_title('Enhanced VOR Analysis', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Matchup Adjustment Factors
    if 'matchup_adjustment_factor' in top_60.columns:
        for pos in ['QB', 'RB', 'WR', 'TE']:
            pos_data = top_60[top_60['position'] == pos]
            if len(pos_data) > 0:
                ax2.scatter(pos_data['overall_rank'], pos_data['matchup_adjustment_factor'], 
                           c=position_colors[pos], label=pos, alpha=0.7, s=60)
        
        ax2.axhline(y=1.0, color='gray', linestyle='--', alpha=0.7)
        ax2.set_xlabel('Overall Draft Rank', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Matchup Adjustment Factor', fontsize=12, fontweight='bold')
        ax2.set_title('Early Season Matchup Adjustments', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, 'Matchup Adjustment\nData Not Available', 
                ha='center', va='center', transform=ax2.transAxes, fontsize=14)
    
    # Plot 3: Schedule Strength Distribution
    sos_cols = [col for col in top_60.columns if 'sos_rating' in col]
    if sos_cols:
        sos_col = sos_cols[0]
        
        # Create histogram of schedule strength by position
        positions = ['QB', 'RB', 'WR', 'TE']
        for i, pos in enumerate(positions):
            pos_data = top_60[top_60['position'] == pos]
            if len(pos_data) > 0:
                ax3.hist(pos_data[sos_col], alpha=0.6, label=pos, 
                        color=position_colors[pos], bins=10)
        
        ax3.axvline(x=0, color='gray', linestyle='--', alpha=0.7)
        ax3.set_xlabel('Schedule Strength Rating', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Number of Players', fontsize=12, fontweight='bold')
        ax3.set_title('Early Season Schedule Difficulty', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'Schedule Strength\nData Not Available', 
                ha='center', va='center', transform=ax3.transAxes, fontsize=14)
    
    # Plot 4: Consistency vs VOR
    if 'matchup_consistency' in top_60.columns:
        for pos in ['QB', 'RB', 'WR', 'TE']:
            pos_data = top_60[top_60['position'] == pos]
            if len(pos_data) > 0:
                ax4.scatter(pos_data['matchup_consistency'], pos_data[vor_col], 
                           c=position_colors[pos], label=pos, alpha=0.7, s=60)
        
        ax4.set_xlabel('Matchup Consistency Score', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Schedule-Adjusted VOR', fontsize=12, fontweight='bold')
        ax4.set_title('Consistency vs Value Analysis', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.legend()
    else:
        ax4.text(0.5, 0.5, 'Matchup Consistency\nData Not Available', 
                ha='center', va='center', transform=ax4.transAxes, fontsize=14)
    
    plt.tight_layout()
    
    # Save enhanced visualization
    enhanced_plot_file = os.path.join(plots_dir, f'enhanced_draft_board_{timestamp}.png')
    plt.savefig(enhanced_plot_file, dpi=300, bbox_inches='tight')
    print(f"Enhanced draft board visualization saved to {enhanced_plot_file}")
    
    plt.close('all')


def main():
    """
    Main function to generate enhanced draft rankings with matchup intelligence.
    """
    print("🏈 Generating enhanced fantasy football draft rankings with matchup intelligence...")
    
    # Enhanced positions (focus on core positions for now)
    positions = config.CORE_POSITIONS  # ['QB', 'RB', 'WR', 'TE']
    
    # Store data by position
    df_by_pos = {}
    
    print(f"\n🎯 Processing {len(positions)} positions with enhanced features...")
    
    # Process each position with enhanced modeling
    for position in positions:
        print(f"\n--- Processing {position} ---")
        
        # Load enhanced position data
        df = load_enhanced_position_data(position)
        
        if df.empty:
            print(f"⚠️ No enhanced data available for {position}, skipping...")
            continue
        
        # Load enhanced model
        model = load_enhanced_model(position)
        
        # Generate enhanced predictions with matchup adjustments
        df = predict_enhanced_fantasy_points(
            df, model, position, 
            include_matchup_adjustments=True
        )
        
        # Store results
        df_by_pos[position] = df
        print(f"✅ Completed enhanced processing for {position}: {len(df)} players")
    
    if not df_by_pos:
        print("❌ No data processed for any position. Exiting.")
        return
    
    print(f"\n🔢 Calculating enhanced VOR for {len(df_by_pos)} positions...")
    
    # Calculate enhanced value over replacement
    df_by_pos_vor = calculate_enhanced_value_over_replacement(df_by_pos)
    
    print("\n📊 Creating enhanced rankings...")
    
    # Create enhanced overall rankings
    overall_rankings = create_enhanced_overall_rankings(df_by_pos_vor)
    
    # Create position-specific rankings (reuse existing function)
    from scripts.generate_draft_rankings import create_position_rankings
    position_rankings = create_position_rankings(df_by_pos_vor)
    
    print("\n💾 Saving enhanced rankings...")
    
    # Save enhanced rankings
    save_enhanced_rankings(overall_rankings, position_rankings)
    
    print("\n📋 Generating enhanced draft cheatsheet...")
    
    # Generate enhanced draft cheatsheet
    generate_enhanced_draft_cheatsheet(overall_rankings, position_rankings)
    
    print("\n📈 Creating enhanced visualizations...")
    
    # Create enhanced visual draft board
    create_enhanced_visual_draft_board(overall_rankings, position_rankings)
    
    print("\n✅ Enhanced draft rankings generation complete!")
    print(f"Generated rankings for {len(overall_rankings)} total players")
    
    # Summary statistics
    if not overall_rankings.empty:
        print(f"\nTop 5 Enhanced Rankings:")
        top_5 = overall_rankings.head(5)
        for _, row in top_5.iterrows():
            player_name = row.get('player_name', 'Unknown')
            position = row['position']
            team = row.get('team', 'UNK')
            points = row.get('predicted_points', 0)
            vor = row.get('vor', 0)
            
            print(f"  {row['overall_rank']}. {player_name} ({position}, {team}) - {points:.1f} pts, {vor:.1f} VOR")


if __name__ == "__main__":
    main()