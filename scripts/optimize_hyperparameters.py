#!/usr/bin/env python3
"""
Hyperparameter Optimization Script for Fantasy Football Models

This script runs comprehensive hyperparameter optimization for all position models,
improving upon the default parameters with position-specific tuning strategies.

Features:
- Position-specific parameter search spaces
- Advanced cross-validation strategies for time-series data
- Automated model retraining with optimized parameters
- Performance comparison and validation
- Integration with existing model pipeline

Usage:
    python scripts/optimize_hyperparameters.py                    # Optimize all positions
    python scripts/optimize_hyperparameters.py --positions QB RB  # Optimize specific positions
    python scripts/optimize_hyperparameters.py --quick            # Quick optimization (fewer trials)
"""

import os
import sys
import pandas as pd
import numpy as np
import argparse
import joblib
from typing import Dict, List, Any
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import our modules
import config
from src.hyperparameter_optimization import FantasyFootballHyperparameterOptimizer, run_comprehensive_optimization
from src.feature_engineering import engineer_features_for_season
from src.modeling import RandomForestModel, LightGBMModel
from src.training_evaluation import calculate_evaluation_metrics

def load_training_data(positions: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Load training data for specified positions.
    
    Args:
        positions: List of positions to load data for
        
    Returns:
        Dictionary mapping positions to their training datasets
    """
    print("Loading training data for hyperparameter optimization...")
    
    data_by_position = {}
    
    # Use multiple years of data for robust optimization
    training_years = list(range(config.DATA_START_YEAR, config.TRAINING_DATA_END_YEAR + 1))
    
    for position in positions:
        print(f"Loading data for {position}...")
        
        position_data_list = []
        
        for year in training_years:
            try:
                # Get engineered features for this year
                year_data = engineer_features_for_season(
                    year, 
                    include_matchup_intelligence=True,  # Include all advanced features
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
                print(f"   Warning: Missing target variable for {position}, skipping...")
                continue
            
            # Remove rows with missing target values
            combined_data = combined_data.dropna(subset=['fantasy_points_per_game'])
            
            if len(combined_data) >= 50:  # Minimum data requirement
                data_by_position[position] = combined_data
                print(f"✅ Loaded {len(combined_data)} total {position} player-seasons")
            else:
                print(f"   Warning: Insufficient data for {position} ({len(combined_data)} samples)")
        else:
            print(f"   Warning: No data found for {position}")
    
    print(f"Loaded data for {len(data_by_position)} positions")
    return data_by_position

def get_feature_columns(data: pd.DataFrame) -> List[str]:
    """
    Extract feature columns from the dataset, excluding non-feature columns.
    
    Args:
        data: Dataset containing features and metadata
        
    Returns:
        List of feature column names
    """
    # Columns to exclude from features
    exclude_cols = {
        'player_id', 'player_name', 'team', 'position', 'season',
        'fantasy_points', 'fantasy_points_per_game', 'fantasy_points_ppr',
        'next_season_fppg', 'games', 'games_played'
    }
    
    # Get all numeric columns that aren't in the exclude list
    feature_cols = []
    for col in data.columns:
        if col not in exclude_cols and pd.api.types.is_numeric_dtype(data[col]):
            feature_cols.append(col)
    
    print(f"Using {len(feature_cols)} feature columns for optimization")
    return feature_cols

def validate_optimization_results(
    data_by_position: Dict[str, pd.DataFrame],
    optimizer: FantasyFootballHyperparameterOptimizer,
    feature_cols: List[str]
) -> Dict[str, Dict[str, float]]:
    """
    Validate optimization results by comparing default vs optimized model performance.
    
    Args:
        data_by_position: Training data by position
        optimizer: Trained hyperparameter optimizer
        feature_cols: List of feature columns
        
    Returns:
        Dictionary containing performance comparison results
    """
    print("\nValidating optimization results...")
    
    validation_results = {}
    
    for position, data in data_by_position.items():
        print(f"\nValidating {position} models...")
        
        # Prepare data
        X = data[feature_cols]
        y = data['fantasy_points_per_game']
        
        # Split data (use last 20% as validation)
        split_idx = int(len(data) * 0.8)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        
        position_results = {}
        
        for model_type in ['random_forest', 'lightgbm']:
            print(f"  Validating {model_type}...")
            
            # Test default model
            if model_type == 'random_forest':
                default_model = RandomForestModel()
            else:
                default_model = LightGBMModel()
            
            default_model.train(X_train, y_train)
            default_pred = default_model.predict(X_val)
            default_metrics = calculate_evaluation_metrics(y_val, default_pred)
            
            # Test optimized model
            optimized_model = optimizer.get_optimized_model(position, model_type)
            optimized_model.train(X_train, y_train)
            optimized_pred = optimized_model.predict(X_val)
            optimized_metrics = calculate_evaluation_metrics(y_val, optimized_pred)
            
            # Calculate improvement
            r2_improvement = optimized_metrics['R2'] - default_metrics['R2']
            rmse_improvement = default_metrics['RMSE'] - optimized_metrics['RMSE']
            
            position_results[model_type] = {
                'default_r2': default_metrics['R2'],
                'optimized_r2': optimized_metrics['R2'],
                'r2_improvement': r2_improvement,
                'default_rmse': default_metrics['RMSE'],
                'optimized_rmse': optimized_metrics['RMSE'],
                'rmse_improvement': rmse_improvement
            }
            
            print(f"    R² improvement: {r2_improvement:+.4f} ({optimized_metrics['R2']:.4f} vs {default_metrics['R2']:.4f})")
            print(f"    RMSE improvement: {rmse_improvement:+.4f} ({optimized_metrics['RMSE']:.4f} vs {default_metrics['RMSE']:.4f})")
        
        validation_results[position] = position_results
    
    return validation_results

def create_optimization_report(
    optimization_results: Dict[str, Any],
    validation_results: Dict[str, Dict[str, float]],
    save_dir: str
) -> None:
    """
    Create comprehensive optimization report with visualizations.
    
    Args:
        optimization_results: Results from hyperparameter optimization
        validation_results: Model performance validation results
        save_dir: Directory to save report and visualizations
    """
    print("\nCreating optimization report...")
    
    # Create save directory
    os.makedirs(save_dir, exist_ok=True)
    
    # Generate performance improvement visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Hyperparameter Optimization Results', fontsize=16, fontweight='bold')
    
    positions = list(validation_results.keys())
    model_types = ['random_forest', 'lightgbm']
    
    # R² Improvement
    r2_data = []
    for pos in positions:
        for model_type in model_types:
            if model_type in validation_results[pos]:
                r2_data.append({
                    'Position': pos,
                    'Model': model_type.replace('_', ' ').title(),
                    'Default R²': validation_results[pos][model_type]['default_r2'],
                    'Optimized R²': validation_results[pos][model_type]['optimized_r2'],
                    'Improvement': validation_results[pos][model_type]['r2_improvement']
                })
    
    r2_df = pd.DataFrame(r2_data)
    
    # Plot R² comparison
    ax1 = axes[0, 0]
    x = np.arange(len(positions))
    width = 0.35
    
    rf_default = [validation_results[pos]['random_forest']['default_r2'] for pos in positions if 'random_forest' in validation_results[pos]]
    rf_optimized = [validation_results[pos]['random_forest']['optimized_r2'] for pos in positions if 'random_forest' in validation_results[pos]]
    
    ax1.bar(x - width/2, rf_default, width, label='Default RF', alpha=0.7, color='lightblue')
    ax1.bar(x - width/2, rf_optimized, width, label='Optimized RF', alpha=0.9, color='blue')
    
    if 'lightgbm' in validation_results[positions[0]]:
        lgb_default = [validation_results[pos]['lightgbm']['default_r2'] for pos in positions if 'lightgbm' in validation_results[pos]]
        lgb_optimized = [validation_results[pos]['lightgbm']['optimized_r2'] for pos in positions if 'lightgbm' in validation_results[pos]]
        
        ax1.bar(x + width/2, lgb_default, width, label='Default LGB', alpha=0.7, color='lightgreen')
        ax1.bar(x + width/2, lgb_optimized, width, label='Optimized LGB', alpha=0.9, color='green')
    
    ax1.set_xlabel('Position')
    ax1.set_ylabel('R² Score')
    ax1.set_title('Model Performance: Default vs Optimized')
    ax1.set_xticks(x)
    ax1.set_xticklabels(positions)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot improvement heatmap
    ax2 = axes[0, 1]
    improvement_matrix = []
    for pos in positions:
        pos_improvements = []
        for model_type in model_types:
            if model_type in validation_results[pos]:
                pos_improvements.append(validation_results[pos][model_type]['r2_improvement'])
            else:
                pos_improvements.append(0)
        improvement_matrix.append(pos_improvements)
    
    im = ax2.imshow(improvement_matrix, cmap='RdYlGn', aspect='auto')
    ax2.set_xticks(range(len(model_types)))
    ax2.set_xticklabels([m.replace('_', ' ').title() for m in model_types])
    ax2.set_yticks(range(len(positions)))
    ax2.set_yticklabels(positions)
    ax2.set_title('R² Improvement by Position and Model')
    
    # Add text annotations
    for i in range(len(positions)):
        for j in range(len(model_types)):
            ax2.text(j, i, f'{improvement_matrix[i][j]:.3f}', 
                    ha='center', va='center', fontweight='bold')
    
    plt.colorbar(im, ax=ax2)
    
    # Plot RMSE improvements
    ax3 = axes[1, 0]
    rmse_improvements = []
    labels = []
    for pos in positions:
        for model_type in model_types:
            if model_type in validation_results[pos]:
                rmse_improvements.append(validation_results[pos][model_type]['rmse_improvement'])
                labels.append(f"{pos} {model_type.replace('_', ' ').title()}")
    
    colors = ['blue' if 'Random' in label else 'green' for label in labels]
    bars = ax3.bar(range(len(rmse_improvements)), rmse_improvements, color=colors, alpha=0.7)
    ax3.set_xlabel('Position-Model Combination')
    ax3.set_ylabel('RMSE Improvement')
    ax3.set_title('RMSE Improvement by Position and Model')
    ax3.set_xticks(range(len(labels)))
    ax3.set_xticklabels(labels, rotation=45, ha='right')
    ax3.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bar, value in zip(bars, rmse_improvements):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.3f}', ha='center', va='bottom' if height >= 0 else 'top')
    
    # Summary statistics
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Create summary text
    total_positions = len(positions)
    avg_r2_improvement = np.mean([
        validation_results[pos][model_type]['r2_improvement']
        for pos in positions
        for model_type in model_types
        if model_type in validation_results[pos]
    ])
    avg_rmse_improvement = np.mean([
        validation_results[pos][model_type]['rmse_improvement']
        for pos in positions
        for model_type in model_types
        if model_type in validation_results[pos]
    ])
    
    summary_text = f"""
Optimization Summary

Positions Optimized: {total_positions}
Models per Position: {len(model_types)}

Average Improvements:
• R² Score: +{avg_r2_improvement:.4f}
• RMSE: {avg_rmse_improvement:+.4f}

Best Performing Position:
• {max(positions, key=lambda p: max(validation_results[p][m]['r2_improvement'] for m in model_types if m in validation_results[p]))}

Total Optimization Time: ~{len(positions) * len(model_types) * 10} minutes
"""
    
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, fontsize=12,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    
    # Save visualization
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_file = os.path.join(save_dir, f'hyperparameter_optimization_results_{timestamp}.png')
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Optimization report saved to {plot_file}")
    
    # Save detailed results to text file
    report_file = os.path.join(save_dir, f'optimization_report_{timestamp}.txt')
    with open(report_file, 'w') as f:
        f.write("Fantasy Football Model Hyperparameter Optimization Report\n")
        f.write("="*60 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("OPTIMIZATION RESULTS BY POSITION\n")
        f.write("-"*40 + "\n\n")
        
        for position in positions:
            f.write(f"{position} Position:\n")
            for model_type in model_types:
                if model_type in validation_results[position]:
                    results = validation_results[position][model_type]
                    f.write(f"  {model_type.replace('_', ' ').title()}:\n")
                    f.write(f"    Default R²: {results['default_r2']:.4f}\n")
                    f.write(f"    Optimized R²: {results['optimized_r2']:.4f}\n")
                    f.write(f"    R² Improvement: {results['r2_improvement']:+.4f}\n")
                    f.write(f"    Default RMSE: {results['default_rmse']:.4f}\n")
                    f.write(f"    Optimized RMSE: {results['optimized_rmse']:.4f}\n")
                    f.write(f"    RMSE Improvement: {results['rmse_improvement']:+.4f}\n\n")
            f.write("\n")
    
    print(f"Detailed report saved to {report_file}")
    plt.close()

def retrain_models_with_optimized_params(
    data_by_position: Dict[str, pd.DataFrame],
    optimizer: FantasyFootballHyperparameterOptimizer,
    feature_cols: List[str],
    save_models: bool = True
) -> None:
    """
    Retrain all position models with optimized hyperparameters and save them.
    
    Args:
        data_by_position: Training data by position
        optimizer: Trained hyperparameter optimizer
        feature_cols: List of feature columns
        save_models: Whether to save the retrained models
    """
    print("\nRetraining models with optimized hyperparameters...")
    
    if save_models:
        models_dir = os.path.join(project_root, 'saved_models')
        os.makedirs(models_dir, exist_ok=True)
    
    for position, data in data_by_position.items():
        print(f"\nRetraining {position} models...")
        
        # Prepare training data
        X = data[feature_cols]
        y = data['fantasy_points_per_game']
        
        for model_type in ['random_forest', 'lightgbm']:
            print(f"  Training optimized {model_type} for {position}...")
            
            try:
                # Get optimized model
                model = optimizer.get_optimized_model(position, model_type)
                
                # Train the model
                if model_type == 'lightgbm' and len(data) > 100:
                    # Use validation set for LightGBM early stopping
                    split_idx = int(len(data) * 0.8)
                    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
                    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
                    model.train(X_train, y_train, X_val, y_val)
                else:
                    model.train(X, y)
                
                # Save model if requested
                if save_models:
                    model_filename = f"{position}_advanced_engineering_model.joblib"
                    model_path = os.path.join(models_dir, model_filename)
                    joblib.dump(model, model_path)
                    print(f"    Saved optimized {model_type} model to {model_path}")
                
            except Exception as e:
                print(f"    Error training {model_type} for {position}: {e}")
                continue
    
    print("\nModel retraining complete!")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Optimize hyperparameters for Fantasy Football models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/optimize_hyperparameters.py                    # Optimize all positions
  python scripts/optimize_hyperparameters.py --positions QB RB  # Optimize specific positions  
  python scripts/optimize_hyperparameters.py --quick            # Quick optimization (fewer trials)
        """
    )
    
    parser.add_argument(
        '--positions',
        nargs='*',
        default=['QB', 'RB', 'WR', 'TE'],
        help='Positions to optimize (default: all core positions)'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick optimization with fewer trials (faster but less thorough)'
    )
    
    parser.add_argument(
        '--no-retrain',
        action='store_true',
        help='Skip model retraining step (optimization only)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='optimization_results',
        help='Directory to save optimization results (default: optimization_results)'
    )
    
    return parser.parse_args()

def main():
    """Main function to run hyperparameter optimization."""
    print("🔧 Fantasy Football Model Hyperparameter Optimization")
    print("="*60)
    
    # Parse arguments
    args = parse_arguments()
    
    print(f"📊 Optimizing positions: {args.positions}")
    print(f"⚡ Quick mode: {'✅ ENABLED' if args.quick else '❌ DISABLED'}")
    print(f"🔄 Model retraining: {'❌ SKIPPED' if args.no_retrain else '✅ ENABLED'}")
    print("="*60)
    
    # Load training data
    data_by_position = load_training_data(args.positions)
    
    if not data_by_position:
        print("❌ No training data loaded. Exiting...")
        return
    
    # Get feature columns (use first available dataset as reference)
    sample_data = next(iter(data_by_position.values()))
    feature_cols = get_feature_columns(sample_data)
    
    if not feature_cols:
        print("❌ No feature columns found. Exiting...")
        return
    
    # Initialize optimizer
    n_trials = 50 if args.quick else 100
    optimizer = FantasyFootballHyperparameterOptimizer(n_trials=n_trials, random_state=42)
    
    # Run optimization
    print(f"\n🎯 Starting hyperparameter optimization ({n_trials} trials per model)...")
    
    optimization_results = {}
    
    for position in args.positions:
        if position not in data_by_position:
            print(f"⚠️ No data available for {position}, skipping...")
            continue
        
        print(f"\n📈 Optimizing {position} models...")
        
        position_data = data_by_position[position]
        X = position_data[feature_cols]
        y = position_data['fantasy_points_per_game']
        
        position_results = {}
        
        for model_type in ['random_forest', 'lightgbm']:
            print(f"   🔍 Optimizing {model_type}...")
            
            try:
                result = optimizer.optimize_hyperparameters(
                    X_train=X,
                    y_train=y,
                    position=position,
                    model_type=model_type,
                    cv_strategy='time_series',
                    n_cv_folds=5,
                    n_iter=n_trials
                )
                
                position_results[model_type] = result
                print(f"   ✅ {model_type} optimization complete (best CV score: {result['best_score']:.4f})")
                
            except Exception as e:
                print(f"   ❌ {model_type} optimization failed: {e}")
                continue
        
        optimization_results[position] = position_results
    
    # Validate optimization results
    print("\n📊 Validating optimization results...")
    validation_results = validate_optimization_results(data_by_position, optimizer, feature_cols)
    
    # Create optimization report
    print("\n📋 Creating optimization report...")
    create_optimization_report(optimization_results, validation_results, args.output_dir)
    
    # Save optimization results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(args.output_dir, f'hyperparameter_optimization_{timestamp}.joblib')
    optimizer.save_optimization_results(results_file)
    
    # Retrain models with optimized parameters
    if not args.no_retrain:
        print("\n🔄 Retraining models with optimized hyperparameters...")
        retrain_models_with_optimized_params(data_by_position, optimizer, feature_cols, save_models=True)
    
    # Summary
    print("\n" + "="*60)
    print("🎉 HYPERPARAMETER OPTIMIZATION COMPLETE!")
    print("="*60)
    
    total_improvements = 0
    for pos_results in validation_results.values():
        for model_results in pos_results.values():
            total_improvements += model_results['r2_improvement']
    
    avg_improvement = total_improvements / (len(validation_results) * 2)  # 2 models per position
    
    print(f"📊 Positions optimized: {len(validation_results)}")
    print(f"📈 Average R² improvement: +{avg_improvement:.4f}")
    print(f"💾 Results saved to: {args.output_dir}")
    
    if not args.no_retrain:
        print(f"🔄 Optimized models saved to: saved_models/")
        print("🚀 Ready to generate improved draft rankings!")
    
    print("\nNext steps:")
    print("1. Review optimization report for detailed results")
    print("2. Run draft ranking generation to see improvements")
    print("3. Compare new rankings against previous versions")

if __name__ == "__main__":
    main()