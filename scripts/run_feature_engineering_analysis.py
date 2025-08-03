#!/usr/bin/env python3
"""
Run feature engineering analysis and model comparison.

This script runs the model comparison with different feature engineering approaches
and generates visualizations to show the impact on model performance.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Union, Tuple
import joblib

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import our model comparison class
from src.models.model_comparison import ModelComparison

# Set plot style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette('viridis')


def create_dummy_data(position: str) -> None:
    """
    Create dummy data for a position.
    
    Args:
        position: Player position
    """
    print(f"Creating dummy data for {position} position...")
    
    # Set random seed for reproducibility
    np.random.seed(42)
    n_samples = 500
    
    # Common data for all positions
    data = {
        'player_id': [f'{position}{i}' for i in range(n_samples)],
        'player_name': [f'Player {i}' for i in range(n_samples)],
        'team': np.random.choice(['NE', 'KC', 'SF', 'DAL', 'GB'], n_samples),
        'position': [position] * n_samples,
        'season': np.random.choice([2018, 2019, 2020, 2021, 2022], n_samples),
        'age': np.random.randint(21, 35, n_samples),
        'experience': np.random.randint(0, 12, n_samples),
        'games_played': np.random.randint(1, 17, n_samples),
        'fumbles': np.random.randint(0, 5, n_samples),
    }
    
    # Position-specific data
    if position == 'QB':
        # QB-specific stats
        data.update({
            'passing_attempts': np.random.randint(100, 700, n_samples),
            'passing_completions': np.random.randint(50, 450, n_samples),
            'passing_yards': np.random.randint(500, 5000, n_samples),
            'passing_tds': np.random.randint(0, 50, n_samples),
            'interceptions': np.random.randint(0, 25, n_samples),
            'rushing_attempts': np.random.randint(0, 100, n_samples),
            'rushing_yards': np.random.randint(0, 500, n_samples),
            'rushing_tds': np.random.randint(0, 10, n_samples),
            'sacks': np.random.randint(0, 50, n_samples),
        })
    
    elif position == 'RB':
        # RB-specific stats
        data.update({
            'rushing_attempts': np.random.randint(0, 300, n_samples),
            'rushing_yards': np.random.randint(0, 1500, n_samples),
            'rushing_tds': np.random.randint(0, 15, n_samples),
            'targets': np.random.randint(0, 100, n_samples),
            'receptions': np.random.randint(0, 80, n_samples),
            'receiving_yards': np.random.randint(0, 800, n_samples),
            'receiving_tds': np.random.randint(0, 8, n_samples),
        })
    
    elif position in ['WR', 'TE']:
        # WR/TE-specific stats
        data.update({
            'targets': np.random.randint(0, 150, n_samples),
            'receptions': np.random.randint(0, 120, n_samples),
            'receiving_yards': np.random.randint(0, 1500, n_samples),
            'receiving_tds': np.random.randint(0, 15, n_samples),
            'rushing_attempts': np.random.randint(0, 10, n_samples),
            'rushing_yards': np.random.randint(0, 100, n_samples),
            'rushing_tds': np.random.randint(0, 3, n_samples),
        })
        
        # Adjust values for TE (typically lower than WR)
        if position == 'TE':
            for key in ['targets', 'receptions', 'receiving_yards', 'receiving_tds']:
                data[key] = np.array(data[key]) * 0.7  # Scale down TE stats
    
    elif position == 'K':
        # K-specific stats
        data.update({
            'field_goals_made': np.random.randint(0, 40, n_samples),
            'field_goals_attempted': np.random.randint(0, 45, n_samples),
            'extra_points_made': np.random.randint(0, 60, n_samples),
            'extra_points_attempted': np.random.randint(0, 65, n_samples),
            'fg_0_19': np.random.randint(0, 5, n_samples),
            'fg_20_29': np.random.randint(0, 10, n_samples),
            'fg_30_39': np.random.randint(0, 15, n_samples),
            'fg_40_49': np.random.randint(0, 12, n_samples),
            'fg_50_plus': np.random.randint(0, 8, n_samples),
        })
    
    elif position == 'DST':
        # DST-specific stats
        data.update({
            'sacks': np.random.randint(0, 60, n_samples),
            'interceptions': np.random.randint(0, 25, n_samples),
            'fumble_recoveries': np.random.randint(0, 20, n_samples),
            'touchdowns': np.random.randint(0, 10, n_samples),
            'safeties': np.random.randint(0, 5, n_samples),
            'points_allowed': np.random.randint(0, 500, n_samples),
            'yards_allowed': np.random.randint(1000, 6000, n_samples),
            'kick_return_tds': np.random.randint(0, 3, n_samples),
            'punt_return_tds': np.random.randint(0, 3, n_samples),
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Calculate derived features based on position
    if position == 'QB':
        df['completion_percentage'] = np.where(df['passing_attempts'] > 0, 
                                              df['passing_completions'] / df['passing_attempts'] * 100, 0)
        df['yards_per_attempt'] = np.where(df['passing_attempts'] > 0, 
                                          df['passing_yards'] / df['passing_attempts'], 0)
        df['td_to_int_ratio'] = np.where(df['interceptions'] > 0, 
                                         df['passing_tds'] / df['interceptions'], df['passing_tds'])
        df['passing_yards_per_game'] = df['passing_yards'] / df['games_played']
        df['passing_tds_per_game'] = df['passing_tds'] / df['games_played']
        
        # Calculate fantasy points for QB
        base_fantasy_points = (
            df['passing_yards'] * 0.04 + 
            df['passing_tds'] * 4 + 
            df['rushing_yards'] * 0.1 + 
            df['rushing_tds'] * 6 - 
            df['interceptions'] * 2 - 
            df['fumbles'] * 2 - 
            df['sacks'] * 0.5
        )
    
    elif position == 'K':
        df['field_goal_percentage'] = np.where(df['field_goals_attempted'] > 0,
                                              df['field_goals_made'] / df['field_goals_attempted'] * 100, 0)
        df['extra_point_percentage'] = np.where(df['extra_points_attempted'] > 0,
                                               df['extra_points_made'] / df['extra_points_attempted'] * 100, 0)
        df['fg_50_plus_made'] = df['fg_50_plus']
        df['fg_50_plus_attempted'] = df['fg_50_plus']
    
    elif position == 'DST':
        df['points_allowed_per_game'] = df['points_allowed'] / df['games_played']
        df['yards_allowed_per_game'] = df['yards_allowed'] / df['games_played']
    
    # Calculate derived features for WR/TE
    if position in ['WR', 'TE']:
        df['yards_per_reception'] = np.where(df['receptions'] > 0,
                                           df['receiving_yards'] / df['receptions'], 0)
        df['yards_per_target'] = np.where(df['targets'] > 0,
                                          df['receiving_yards'] / df['targets'], 0)
        df['catch_rate'] = np.where(df['targets'] > 0,
                                    df['receptions'] / df['targets'], 0)
        df['receiving_yards_per_game'] = df['receiving_yards'] / df['games_played']
        df['targets_per_game'] = df['targets'] / df['games_played']
        
    # Create target variable with some noise but correlated with key features
    if position == 'QB':
        base_fantasy_points = (
            df['passing_yards'] * 0.04 + 
            df['passing_tds'] * 4 + 
            df['rushing_yards'] * 0.1 + 
            df['rushing_tds'] * 6 - 
            df['interceptions'] * 2 - 
            df['fumbles'] * 2
        )
    elif position == 'RB':
        base_fantasy_points = (
            df['rushing_yards'] * 0.1 + 
            df['rushing_tds'] * 6 + 
            df['receiving_yards'] * 0.1 + 
            df['receptions'] * 0.5 + 
            df['receiving_tds'] * 6 - 
            df['fumbles'] * 2
        )
    elif position in ['WR', 'TE']:
        ppr_value = 1.0 if position == 'TE' else 0.5  # PPR for TE, half-PPR for WR
        base_fantasy_points = (
            df['receiving_yards'] * 0.1 + 
            df['receptions'] * ppr_value + 
            df['receiving_tds'] * 6 + 
            df['rushing_yards'] * 0.1 + 
            df['rushing_tds'] * 6 - 
            df['fumbles'] * 2
        )
    elif position == 'K':
        base_fantasy_points = (
            df['field_goals_made'] * 3 + 
            df['fg_50_plus'] * 1 + # Bonus for 50+ yard FGs
            df['extra_points_made'] * 1
        )
    elif position == 'DST':
        base_fantasy_points = (
            df['sacks'] * 1 + 
            df['interceptions'] * 2 + 
            df['fumble_recoveries'] * 2 + 
            df['touchdowns'] * 6 + 
            df['safeties'] * 2 + 
            df['kick_return_tds'] * 6 + 
            df['punt_return_tds'] * 6
        )
        
        # Adjust for points allowed
        points_allowed = df['points_allowed_per_game']
        points_allowed_score = np.zeros(n_samples)
        points_allowed_score[points_allowed == 0] = 10
        points_allowed_score[(points_allowed > 0) & (points_allowed <= 6)] = 7
        points_allowed_score[(points_allowed > 6) & (points_allowed <= 13)] = 4
        points_allowed_score[(points_allowed > 13) & (points_allowed <= 20)] = 1
        points_allowed_score[(points_allowed > 20) & (points_allowed <= 27)] = 0
        points_allowed_score[(points_allowed > 27) & (points_allowed <= 34)] = -1
        points_allowed_score[points_allowed > 34] = -4
        
        base_fantasy_points += points_allowed_score
    
    # Add some noise
    df['fantasy_points'] = base_fantasy_points + np.random.normal(0, base_fantasy_points.std() * 0.2, n_samples)
    df['fantasy_points'] = df['fantasy_points'].clip(0)  # No negative fantasy points
    
    # Calculate per-game
    df['fantasy_points_per_game'] = df['fantasy_points'] / df['games_played']
    # Create directory if it doesn't exist
    data_dir = os.path.join(project_root, f'data/processed/position_specific/{position.lower()}')
    os.makedirs(data_dir, exist_ok=True)
    
    # Ensure directory exists
    data_path = f'{data_dir}/{position.lower()}_features.parquet'
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    
    # Save to parquet file
    df.to_parquet(data_path)
    print(f"Saved dummy data to {data_path}")
    
    return df

# ... (rest of the code remains the same)
def run_position_analysis(position: str):
    """
    Run feature engineering analysis for a specific position.
    
    Args:
        position: Player position (QB, RB, WR, TE, K, DST)
    """
    print(f"\n{'='*80}")
    print(f"Running analysis for {position} position")
    print(f"{'='*80}")
    
    # Initialize model comparison
    comparison = ModelComparison(position=position)
    
    # Set data path
    data_path = os.path.join(project_root, f'data/processed/position_specific/{position.lower()}/{position.lower()}_features.parquet')
    
    # Check if data exists, if not create dummy data
    if not os.path.exists(data_path):
        print(f"Data file {data_path} not found. Creating dummy data.")
        create_dummy_data(position)
    
    # Load data
    df = comparison.load_data(data_path)
    print(f"Loaded data with {len(df)} samples and {len(df.columns)} features.")
    
    # Compare models
    print("Comparing models with different feature engineering approaches...")
    results = comparison.compare_models(df)
    
    # Print results
    print("\nModel comparison results:")
    for model_name, model_results in results.items():
        metrics = model_results['metrics']
        print(f"  {model_name.replace('_', ' ').title()}:")
        print(f"    RMSE: {metrics['rmse']:.4f}")
        print(f"    R²: {metrics['r2']:.4f}")
        print(f"    MAE: {metrics['mae']:.4f}")
        print(f"    CV R² (mean ± std): {metrics['cv_r2_mean']:.4f} ± {metrics['cv_r2_std']:.4f}")
    
    # Plot comparison
    print("\nGenerating performance comparison plot...")
    comparison.plot_comparison()
    
    # Plot feature importance for best model
    print("Generating feature importance plot...")
    feature_importance = comparison.plot_feature_importance()
    
    # Save models
    print("Saving models...")
    models_dir = os.path.join(project_root, 'saved_models')
    comparison.save_models(output_dir=models_dir)
    
    return results


def main():
    """
    Main function to run feature engineering analysis for all positions.
    """
    print("Starting feature engineering analysis...")
    
    # Create output directory for plots
    plots_dir = os.path.join(project_root, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    # Positions to analyze
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
    
    # Run analysis for each position
    all_results = {}
    for position in positions:
        all_results[position] = run_position_analysis(position)
    
    # Create summary plot comparing improvement across positions
    print("\nGenerating summary plot...")
    
    # Extract R² improvement for each position
    improvements = []
    for position, results in all_results.items():
        baseline_r2 = results['baseline']['metrics']['r2']
        advanced_r2 = results['advanced_engineering']['metrics']['r2']
        improvement = (advanced_r2 - baseline_r2) / baseline_r2 * 100  # percentage improvement
        improvements.append({
            'position': position,
            'baseline_r2': baseline_r2,
            'advanced_r2': advanced_r2,
            'improvement': improvement
        })
    
    # Create DataFrame for plotting
    improvement_df = pd.DataFrame(improvements)
    
    # Plot improvement
    plt.figure(figsize=(12, 8))
    
    # Bar plot for R² values
    ax1 = plt.subplot(111)
    x = np.arange(len(positions))
    width = 0.35
    
    baseline_bars = ax1.bar(x - width/2, improvement_df['baseline_r2'], width, label='Baseline Model', color='#1f77b4')
    advanced_bars = ax1.bar(x + width/2, improvement_df['advanced_r2'], width, label='Advanced Feature Engineering', color='#2ca02c')
    
    # Add value labels
    for i, bar in enumerate(baseline_bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom')
    
    for i, bar in enumerate(advanced_bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}', ha='center', va='bottom')
    
    # Add improvement percentage as text
    for i, pos in enumerate(positions):
        improvement = improvement_df.loc[improvement_df['position'] == pos, 'improvement'].values[0]
        ax1.text(i, 0.05, f'+{improvement:.1f}%', ha='center', va='bottom', color='black',
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3'))
    
    ax1.set_ylabel('R² Score')
    ax1.set_title('Model Performance Improvement with Feature Engineering by Position')
    ax1.set_xticks(x)
    ax1.set_xticklabels(positions)
    ax1.legend()
    
    plt.tight_layout()
    plot_path = os.path.join(project_root, 'plots/feature_engineering_improvement_summary.png')
    os.makedirs(os.path.dirname(plot_path), exist_ok=True)
    plt.savefig(plot_path)
    
    print("\nAnalysis complete! Check the output directory for plots and saved models.")


if __name__ == "__main__":
    main()
