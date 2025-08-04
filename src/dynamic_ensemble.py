"""
Dynamic Ensemble Weighting System for Fantasy Football Models

This module implements intelligent ensemble weighting that adapts based on player
characteristics, position, and performance patterns. Rather than using static
50/50 weighting, it dynamically adjusts RandomForest and LightGBM weights to
optimize predictions for different player archetypes.

Key Features:
- Player archetype classification based on usage patterns
- Position-specific ensemble weight optimization
- Context-aware model selection (veteran vs rookie, workhorse vs committee, etc.)
- Fallback to default weights for edge cases
- Integration with existing model pipeline
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging

# Import configuration
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicEnsembleWeighter:
    """
    Dynamic ensemble weighting system that adapts model weights based on player context.
    
    This class analyzes player characteristics and performance patterns to determine
    the optimal weighting between RandomForest and LightGBM models for each player.
    """
    
    def __init__(self):
        """Initialize the dynamic ensemble weighter with configuration."""
        self.dynamic_weights = config.DYNAMIC_ENSEMBLE_WEIGHTS
        self.archetype_thresholds = config.PLAYER_ARCHETYPE_THRESHOLDS
        self.default_weights = config.MODEL_WEIGHTS
        
    def classify_player_archetype(self, player_data: pd.Series, position: str) -> str:
        """
        Classify a player into an archetype based on their statistics and characteristics.
        
        Args:
            player_data: Series containing player statistics and metadata
            position: Player position (QB, RB, WR, TE)
            
        Returns:
            String representing the player's archetype
        """
        if position not in self.archetype_thresholds:
            return 'default'
        
        position_thresholds = self.archetype_thresholds[position]
        
        # Check each archetype in order of specificity
        for archetype, thresholds in position_thresholds.items():
            if self._meets_archetype_criteria(player_data, thresholds):
                return archetype
        
        return 'default'
    
    def _meets_archetype_criteria(self, player_data: pd.Series, thresholds: Dict[str, Any]) -> bool:
        """
        Check if a player meets the criteria for a specific archetype.
        
        Args:
            player_data: Player statistics and metadata
            thresholds: Dictionary of threshold criteria for the archetype
            
        Returns:
            Boolean indicating if player meets all criteria
        """
        for criterion, threshold_value in thresholds.items():
            if criterion.startswith('min_'):
                # Minimum threshold check
                stat_name = criterion[4:]  # Remove 'min_' prefix
                if stat_name not in player_data or pd.isna(player_data[stat_name]):
                    return False
                if player_data[stat_name] < threshold_value:
                    return False
                    
            elif criterion.startswith('max_'):
                # Maximum threshold check
                stat_name = criterion[4:]  # Remove 'max_' prefix
                if stat_name not in player_data or pd.isna(player_data[stat_name]):
                    return False
                if player_data[stat_name] > threshold_value:
                    return False
                    
            else:
                # Direct equality check
                if criterion not in player_data or pd.isna(player_data[criterion]):
                    return False
                if player_data[criterion] != threshold_value:
                    return False
        
        return True
    
    def get_ensemble_weights(self, player_data: pd.Series, position: str) -> Dict[str, float]:
        """
        Get optimal ensemble weights for a specific player.
        
        Args:
            player_data: Series containing player statistics and metadata
            position: Player position
            
        Returns:
            Dictionary with RandomForest and LightGBM weights
        """
        # Classify the player's archetype
        archetype = self.classify_player_archetype(player_data, position)
        
        # Get weights for this archetype
        if position in self.dynamic_weights and archetype in self.dynamic_weights[position]:
            weights = self.dynamic_weights[position][archetype]
            logger.debug(f"Player {player_data.get('player_name', 'Unknown')} ({position}) classified as {archetype}: RF={weights['random_forest']:.2f}, LGB={weights['lightgbm']:.2f}")
        else:
            # Fallback to default weights
            weights = self.default_weights
            logger.debug(f"Player {player_data.get('player_name', 'Unknown')} ({position}) using default weights: RF={weights['random_forest']:.2f}, LGB={weights['lightgbm']:.2f}")
        
        return weights
    
    def apply_dynamic_ensemble(
        self,
        rf_predictions: np.ndarray,
        lgb_predictions: np.ndarray,
        player_data: pd.DataFrame,
        position: str
    ) -> np.ndarray:
        """
        Apply dynamic ensemble weighting to predictions.
        
        Args:
            rf_predictions: RandomForest predictions
            lgb_predictions: LightGBM predictions
            player_data: DataFrame with player data for weight calculation
            position: Player position
            
        Returns:
            Array of dynamically weighted ensemble predictions
        """
        if len(rf_predictions) != len(lgb_predictions) or len(rf_predictions) != len(player_data):
            raise ValueError("All input arrays must have the same length")
        
        ensemble_predictions = np.zeros(len(rf_predictions))
        archetype_counts = {}
        
        for i, (rf_pred, lgb_pred) in enumerate(zip(rf_predictions, lgb_predictions)):
            # Get player-specific weights
            player_row = player_data.iloc[i]
            weights = self.get_ensemble_weights(player_row, position)
            
            # Apply weights
            ensemble_pred = (weights['random_forest'] * rf_pred + 
                           weights['lightgbm'] * lgb_pred)
            ensemble_predictions[i] = ensemble_pred
            
            # Track archetype usage for reporting
            archetype = self.classify_player_archetype(player_row, position)
            archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
        
        # Log archetype distribution
        total_players = len(player_data)
        logger.info(f"Dynamic ensemble weighting applied to {total_players} {position} players:")
        for archetype, count in sorted(archetype_counts.items()):
            percentage = (count / total_players) * 100
            logger.info(f"  {archetype}: {count} players ({percentage:.1f}%)")
        
        return ensemble_predictions
    
    def get_archetype_summary(self, player_data: pd.DataFrame, position: str) -> Dict[str, Any]:
        """
        Get a summary of player archetype distribution and characteristics.
        
        Args:
            player_data: DataFrame with player data
            position: Player position
            
        Returns:
            Dictionary containing archetype analysis
        """
        archetype_summary = {
            'total_players': len(player_data),
            'position': position,
            'archetype_distribution': {},
            'archetype_characteristics': {}
        }
        
        for i, player_row in player_data.iterrows():
            archetype = self.classify_player_archetype(player_row, position)
            
            # Count distribution
            if archetype not in archetype_summary['archetype_distribution']:
                archetype_summary['archetype_distribution'][archetype] = 0
            archetype_summary['archetype_distribution'][archetype] += 1
            
            # Collect characteristics for analysis
            if archetype not in archetype_summary['archetype_characteristics']:
                archetype_summary['archetype_characteristics'][archetype] = {
                    'players': [],
                    'avg_stats': {}
                }
            
            archetype_summary['archetype_characteristics'][archetype]['players'].append(
                player_row.get('player_name', f'Player_{i}')
            )
        
        # Calculate percentages
        total = archetype_summary['total_players']
        for archetype, count in archetype_summary['archetype_distribution'].items():
            archetype_summary['archetype_distribution'][archetype] = {
                'count': count,
                'percentage': (count / total) * 100
            }
        
        return archetype_summary
    
    def validate_dynamic_weighting(
        self,
        player_data: pd.DataFrame,
        position: str,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Validate the dynamic weighting system and provide diagnostics.
        
        Args:
            player_data: DataFrame with player data
            position: Player position
            verbose: Whether to print detailed validation info
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            'position': position,
            'total_players': len(player_data),
            'archetype_coverage': {},
            'weight_distribution': {},
            'validation_errors': []
        }
        
        try:
            # Get archetype summary
            archetype_summary = self.get_archetype_summary(player_data, position)
            validation_results['archetype_coverage'] = archetype_summary['archetype_distribution']
            
            # Analyze weight distribution
            weight_combinations = {}
            for i, player_row in player_data.iterrows():
                weights = self.get_ensemble_weights(player_row, position)
                weight_key = f"RF:{weights['random_forest']:.2f}_LGB:{weights['lightgbm']:.2f}"
                weight_combinations[weight_key] = weight_combinations.get(weight_key, 0) + 1
            
            validation_results['weight_distribution'] = weight_combinations
            
            # Check for potential issues
            if len(archetype_summary['archetype_distribution']) == 1 and 'default' in archetype_summary['archetype_distribution']:
                validation_results['validation_errors'].append(
                    "All players classified as 'default' - archetype thresholds may need adjustment"
                )
            
            # Check weight sum validation
            for i, player_row in player_data.iterrows():
                weights = self.get_ensemble_weights(player_row, position)
                weight_sum = weights['random_forest'] + weights['lightgbm']
                if abs(weight_sum - 1.0) > 0.001:  # Allow for floating point precision
                    validation_results['validation_errors'].append(
                        f"Weights don't sum to 1.0 for player {i}: {weight_sum:.3f}"
                    )
            
            if verbose:
                print(f"\nDynamic Ensemble Validation for {position}:")
                print(f"Total players: {validation_results['total_players']}")
                print("\nArchetype Distribution:")
                for archetype, data in validation_results['archetype_coverage'].items():
                    print(f"  {archetype}: {data['count']} players ({data['percentage']:.1f}%)")
                
                print("\nWeight Combinations Used:")
                for weights, count in validation_results['weight_distribution'].items():
                    print(f"  {weights}: {count} players")
                
                if validation_results['validation_errors']:
                    print("\nValidation Errors:")
                    for error in validation_results['validation_errors']:
                        print(f"  • {error}")
                else:
                    print("\n✅ No validation errors found")
        
        except Exception as e:
            validation_results['validation_errors'].append(f"Validation failed: {str(e)}")
            logger.error(f"Dynamic weighting validation failed for {position}: {e}")
        
        return validation_results


def apply_dynamic_ensemble_to_dataframe(
    df: pd.DataFrame,
    rf_predictions: np.ndarray,
    lgb_predictions: np.ndarray,
    position_col: str = 'position'
) -> np.ndarray:
    """
    Apply dynamic ensemble weighting to a DataFrame with mixed positions.
    
    Args:
        df: DataFrame containing player data with position information
        rf_predictions: RandomForest predictions
        lgb_predictions: LightGBM predictions
        position_col: Name of the column containing position information
        
    Returns:
        Array of dynamically weighted ensemble predictions
    """
    if len(rf_predictions) != len(lgb_predictions) or len(rf_predictions) != len(df):
        raise ValueError("All input arrays must have the same length")
    
    ensemble_predictions = np.zeros(len(rf_predictions))
    weighter = DynamicEnsembleWeighter()
    
    # Group by position for efficient processing
    positions = df[position_col].unique()
    
    for position in positions:
        position_mask = df[position_col] == position
        position_indices = df.index[position_mask].tolist()
        
        if not position_indices:
            continue
        
        # Get position-specific data and predictions
        position_data = df.loc[position_mask]
        position_rf_preds = rf_predictions[position_mask]
        position_lgb_preds = lgb_predictions[position_mask]
        
        # Apply dynamic weighting for this position
        position_ensemble_preds = weighter.apply_dynamic_ensemble(
            position_rf_preds,
            position_lgb_preds,
            position_data,
            position
        )
        
        # Store results back in the main array
        ensemble_predictions[position_mask] = position_ensemble_preds
    
    return ensemble_predictions


def create_ensemble_weights_report(
    data_by_position: Dict[str, pd.DataFrame],
    save_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a comprehensive report on dynamic ensemble weighting patterns.
    
    Args:
        data_by_position: Dictionary mapping positions to their data
        save_path: Optional path to save the report
        
    Returns:
        Dictionary containing the complete ensemble weights report
    """
    weighter = DynamicEnsembleWeighter()
    report = {
        'report_timestamp': pd.Timestamp.now().isoformat(),
        'positions_analyzed': list(data_by_position.keys()),
        'position_summaries': {},
        'overall_statistics': {}
    }
    
    total_players = 0
    all_archetypes = set()
    
    print("Creating Dynamic Ensemble Weights Report")
    print("=" * 50)
    
    for position, data in data_by_position.items():
        print(f"\nAnalyzing {position} position ({len(data)} players)...")
        
        # Get validation results for this position
        validation = weighter.validate_dynamic_weighting(data, position, verbose=False)
        archetype_summary = weighter.get_archetype_summary(data, position)
        
        report['position_summaries'][position] = {
            'total_players': len(data),
            'archetype_distribution': validation['archetype_coverage'],
            'weight_distribution': validation['weight_distribution'],
            'validation_errors': validation['validation_errors'],
            'archetype_details': archetype_summary['archetype_characteristics']
        }
        
        total_players += len(data)
        all_archetypes.update(validation['archetype_coverage'].keys())
        
        # Print summary for this position
        print(f"  Archetypes found: {len(validation['archetype_coverage'])}")
        print(f"  Weight combinations: {len(validation['weight_distribution'])}")
        if validation['validation_errors']:
            print(f"  Validation errors: {len(validation['validation_errors'])}")
    
    # Calculate overall statistics
    report['overall_statistics'] = {
        'total_players_analyzed': total_players,
        'total_archetypes_found': len(all_archetypes),
        'positions_with_errors': sum(1 for pos_data in report['position_summaries'].values() 
                                   if pos_data['validation_errors']),
        'archetype_usage_across_positions': {}
    }
    
    # Calculate archetype usage across all positions
    for archetype in all_archetypes:
        usage_count = 0
        total_possible = 0
        for pos_data in report['position_summaries'].values():
            total_possible += pos_data['total_players']
            if archetype in pos_data['archetype_distribution']:
                usage_count += pos_data['archetype_distribution'][archetype]['count']
        
        report['overall_statistics']['archetype_usage_across_positions'][archetype] = {
            'total_players': usage_count,
            'percentage_of_all_players': (usage_count / total_players) * 100 if total_players > 0 else 0
        }
    
    # Save report if requested
    if save_path:
        import json
        with open(save_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {save_path}")
    
    print(f"\nReport Summary:")
    print(f"  Total players analyzed: {total_players}")
    print(f"  Unique archetypes found: {len(all_archetypes)}")
    print(f"  Positions with validation errors: {report['overall_statistics']['positions_with_errors']}")
    
    return report


if __name__ == "__main__":
    # Example usage and testing
    print("Dynamic Ensemble Weighting System for Fantasy Football")
    print("=" * 60)
    print("This module provides intelligent ensemble weighting based on player characteristics.")
    print("Import this module and use DynamicEnsembleWeighter class for dynamic weighting.")