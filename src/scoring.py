"""
Player scoring and ranking functionality for fantasy football draft preparation.

This module implements:
- `calculate_player_scores`: Calculates player scores based on ensemble model predictions
- `calculate_vorp`: Calculates Value Over Replacement Player (VORP) scores
- `generate_player_rankings`: Generates overall player rankings based on VORP

These functions help translate model predictions into actionable draft rankings.
"""

import pandas as pd
import numpy as np
import logging
import os
from typing import Dict, List, Optional, Tuple, Union

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_player_scores(
    predictions_df: pd.DataFrame,
    model_weights: Optional[Dict[str, float]] = None,
    prediction_cols: Optional[Dict[str, str]] = None,
    player_info_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Calculate overall player scores based on ensemble model predictions.
    
    Args:
        predictions_df: DataFrame containing predictions from different models
        model_weights: Dictionary mapping model names to their weights in the ensemble
                      If None, uses weights from config.MODEL_WEIGHTS
        prediction_cols: Dictionary mapping model names to their prediction column names
                        If None, assumes columns are named 'predicted_{model_name}'
        player_info_cols: List of columns to keep in the output (player identifiers, etc.)
                         If None, keeps standard player info columns
                         
    Returns:
        DataFrame with player information and their calculated scores
    """
    logger.info("Calculating player scores from ensemble predictions")
    
    if predictions_df.empty:
        logger.warning("Empty predictions DataFrame provided")
        return pd.DataFrame()
    
    # Use default weights from config if not provided
    if model_weights is None:
        model_weights = config.MODEL_WEIGHTS
        logger.info(f"Using default model weights from config: {model_weights}")
    
    # Default player info columns to keep
    if player_info_cols is None:
        player_info_cols = [
            'player_id', 'player_name', 'position', 'team', 'age', 
            'experience', 'season'
        ]
        # Filter to only include columns that exist in the DataFrame
        player_info_cols = [col for col in player_info_cols if col in predictions_df.columns]
        logger.info(f"Using player info columns: {player_info_cols}")
    
    # Default prediction column naming convention
    if prediction_cols is None:
        prediction_cols = {model_name: f'predicted_{model_name}' 
                          for model_name in model_weights.keys()}
        logger.info(f"Using prediction columns: {prediction_cols}")
    
    # Validate that all prediction columns exist
    missing_cols = [col for col in prediction_cols.values() 
                   if col not in predictions_df.columns]
    if missing_cols:
        logger.error(f"Missing prediction columns: {missing_cols}")
        raise ValueError(f"Prediction columns not found in DataFrame: {missing_cols}")
    
    # Create a copy to avoid modifying the original DataFrame
    result_df = predictions_df[player_info_cols].copy()
    
    # Calculate the weighted ensemble score
    result_df['projected_fppg'] = 0.0
    total_weight = sum(model_weights.values())
    
    if total_weight == 0:
        logger.warning("Total model weight is 0, setting equal weights")
        # If total weight is 0, use equal weights
        equal_weight = 1.0 / len(model_weights)
        for model_name, pred_col in prediction_cols.items():
            result_df['projected_fppg'] += predictions_df[pred_col] * equal_weight
    else:
        # Normalize weights to sum to 1
        normalized_weights = {k: v/total_weight for k, v in model_weights.items()}
        for model_name, pred_col in prediction_cols.items():
            if model_name in normalized_weights:
                weight = normalized_weights[model_name]
                result_df['projected_fppg'] += predictions_df[pred_col] * weight
    
    logger.info(f"Player scores calculated for {len(result_df)} players")
    return result_df


def calculate_vorp(
    player_scores_df: pd.DataFrame,
    replacement_ranks: Optional[Dict[str, int]] = None,
    position_col: str = 'position',
    score_col: str = 'projected_fppg'
) -> pd.DataFrame:
    """
    Calculate Value Over Replacement Player (VORP) for each player.
    
    Args:
        player_scores_df: DataFrame with player scores from calculate_player_scores
        replacement_ranks: Dictionary mapping positions to their replacement ranks
                          If None, uses ranks from config.REPLACEMENT_RANKS
        position_col: Name of the column containing player positions
        score_col: Name of the column containing player scores (FPPG)
        
    Returns:
        DataFrame with player information, scores, and VORP values
    """
    logger.info("Calculating VORP scores")
    
    if player_scores_df.empty:
        logger.warning("Empty player scores DataFrame provided")
        return pd.DataFrame()
    
    # Use default replacement ranks from config if not provided
    if replacement_ranks is None:
        replacement_ranks = config.REPLACEMENT_RANKS
        logger.info(f"Using default replacement ranks from config: {replacement_ranks}")
    
    # Create a copy to avoid modifying the original DataFrame
    result_df = player_scores_df.copy()
    
    # Calculate replacement level FPPG for each position
    replacement_fppg = {}
    
    for position, rank in replacement_ranks.items():
        # Filter players by position and sort by score in descending order
        pos_players = result_df[result_df[position_col] == position].sort_values(
            by=score_col, ascending=False
        )
        
        if len(pos_players) >= rank:
            # Get the FPPG of the player at the replacement rank
            replacement_fppg[position] = pos_players.iloc[rank-1][score_col]
            logger.info(f"Replacement level for {position}: {replacement_fppg[position]:.2f} FPPG (rank {rank})")
        else:
            # If not enough players at this position, use the lowest score
            if not pos_players.empty:
                replacement_fppg[position] = pos_players[score_col].min()
                logger.warning(
                    f"Not enough {position} players ({len(pos_players)}) to determine replacement at rank {rank}. "
                    f"Using minimum value: {replacement_fppg[position]:.2f}"
                )
            else:
                replacement_fppg[position] = 0.0
                logger.warning(f"No {position} players found. Setting replacement level to 0.")
    
    # Calculate VORP for each player
    def calculate_player_vorp(row):
        position = row[position_col]
        if position in replacement_fppg:
            return max(0, row[score_col] - replacement_fppg[position])
        else:
            logger.warning(f"Unknown position: {position}. Setting VORP to 0.")
            return 0.0
    
    result_df['vorp'] = result_df.apply(calculate_player_vorp, axis=1)
    
    logger.info(f"VORP calculated for {len(result_df)} players")
    return result_df


def generate_player_rankings(
    player_vorp_df: pd.DataFrame,
    vorp_col: str = 'vorp',
    score_col: str = 'projected_fppg',
    top_n: int = 200
) -> pd.DataFrame:
    """
    Generate overall player rankings based on VORP scores.
    
    Args:
        player_vorp_df: DataFrame with player VORP from calculate_vorp
        vorp_col: Name of the column containing VORP values
        score_col: Name of the column containing player scores (FPPG)
        top_n: Number of top players to include in the rankings
        
    Returns:
        DataFrame with player rankings sorted by VORP
    """
    logger.info(f"Generating player rankings (top {top_n})")
    
    if player_vorp_df.empty:
        logger.warning("Empty player VORP DataFrame provided")
        return pd.DataFrame()
    
    # Create a copy to avoid modifying the original DataFrame
    result_df = player_vorp_df.copy()
    
    # Sort by VORP in descending order
    result_df = result_df.sort_values(by=vorp_col, ascending=False)
    
    # Add overall rank
    result_df['overall_rank'] = range(1, len(result_df) + 1)
    
    # Add positional rank
    result_df['position_rank'] = result_df.groupby('position').cumcount() + 1
    
    # Format the position rank (e.g., RB1, RB2, etc.)
    result_df['position_rank_display'] = result_df['position'] + result_df['position_rank'].astype(str)
    
    # Select columns for the final output
    columns_to_include = [
        'overall_rank', 'position_rank_display', 'player_name', 'position', 
        'team', 'age', 'experience', score_col, vorp_col
    ]
    
    # Filter to only include columns that exist
    columns_to_include = [col for col in columns_to_include if col in result_df.columns]
    
    # Limit to top N players
    if top_n and len(result_df) > top_n:
        result_df = result_df.head(top_n)
    
    logger.info(f"Generated rankings for {len(result_df)} players")
    return result_df[columns_to_include]


def run_scoring_pipeline(
    predictions_file: str,
    output_file: Optional[str] = None,
    top_n: int = 200
) -> pd.DataFrame:
    """
    Run the complete scoring pipeline from predictions to final rankings.
    
    Args:
        predictions_file: Path to the CSV/parquet file with model predictions
        output_file: Path to save the final rankings (if None, doesn't save)
        top_n: Number of top players to include in the rankings
        
    Returns:
        DataFrame with final player rankings
    """
    logger.info(f"Running scoring pipeline on {predictions_file}")
    
    # Load predictions
    file_ext = os.path.splitext(predictions_file)[1].lower()
    if file_ext == '.csv':
        predictions_df = pd.read_csv(predictions_file)
    elif file_ext in ['.parquet', '.pq']:
        predictions_df = pd.read_parquet(predictions_file)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Use .csv or .parquet")
    
    # Calculate player scores
    player_scores = calculate_player_scores(predictions_df)
    
    # Calculate VORP
    player_vorp = calculate_vorp(player_scores)
    
    # Generate rankings
    rankings = generate_player_rankings(player_vorp, top_n=top_n)
    
    # Save rankings if output file is specified
    if output_file:
        directory = os.path.dirname(output_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        file_ext = os.path.splitext(output_file)[1].lower()
        if file_ext == '.csv':
            rankings.to_csv(output_file, index=False)
        elif file_ext in ['.parquet', '.pq']:
            rankings.to_parquet(output_file, index=False)
        else:
            rankings.to_csv(output_file, index=False)
            logger.warning(f"Unknown output format: {file_ext}. Defaulting to CSV.")
            
        logger.info(f"Rankings saved to {output_file}")
    
    return rankings


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate player rankings from model predictions")
    parser.add_argument("--predictions", required=True, help="Path to predictions file (CSV or Parquet)")
    parser.add_argument("--output", default="data/processed/player_rankings.csv", 
                        help="Path to save rankings (default: data/processed/player_rankings.csv)")
    parser.add_argument("--top", type=int, default=200, help="Number of top players to include (default: 200)")
    
    args = parser.parse_args()
    
    rankings_df = run_scoring_pipeline(args.predictions, args.output, args.top)
    print(f"Generated rankings for {len(rankings_df)} players. Top 10:")
    print(rankings_df.head(10))
