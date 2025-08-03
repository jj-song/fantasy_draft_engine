"""
Tests for the scoring module.

This module tests the functionality of the scoring.py module, including:
- Player score calculation from ensemble predictions
- VORP calculation
- Player ranking generation
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add the project root to the path so we can import the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.scoring import calculate_player_scores, calculate_vorp, generate_player_rankings


class TestScoring(unittest.TestCase):
    """Test cases for scoring functions."""

    def setUp(self):
        """Set up test data."""
        # Create a sample predictions DataFrame
        self.predictions_df = pd.DataFrame({
            'player_id': [1, 2, 3, 4, 5, 6, 7, 8],
            'player_name': ['Player A', 'Player B', 'Player C', 'Player D', 
                           'Player E', 'Player F', 'Player G', 'Player H'],
            'position': ['QB', 'QB', 'RB', 'RB', 'RB', 'WR', 'WR', 'TE'],
            'team': ['Team1', 'Team2', 'Team3', 'Team4', 'Team5', 'Team6', 'Team7', 'Team8'],
            'age': [25, 30, 22, 28, 24, 26, 29, 27],
            'experience': [3, 8, 1, 6, 2, 4, 7, 5],
            'season': [2025] * 8,
            'predicted_lightgbm': [20.5, 18.2, 15.7, 14.3, 12.8, 16.5, 14.9, 13.2],
            'predicted_random_forest': [19.8, 17.5, 16.2, 13.9, 13.1, 15.8, 15.3, 12.7]
        })
        
        # Define model weights for testing
        self.model_weights = {'lightgbm': 0.6, 'random_forest': 0.4}
        
        # Define replacement ranks for testing
        self.replacement_ranks = {'QB': 2, 'RB': 3, 'WR': 2, 'TE': 1}

    def test_calculate_player_scores(self):
        """Test the calculate_player_scores function."""
        # Calculate player scores
        scores_df = calculate_player_scores(
            self.predictions_df,
            model_weights=self.model_weights,
            prediction_cols={'lightgbm': 'predicted_lightgbm', 'random_forest': 'predicted_random_forest'}
        )
        
        # Check that the output has the expected columns
        self.assertIn('projected_fppg', scores_df.columns)
        
        # Check that the scores are calculated correctly
        # For Player A: 0.6 * 20.5 + 0.4 * 19.8 = 20.22
        expected_score_player_a = 0.6 * 20.5 + 0.4 * 19.8
        self.assertAlmostEqual(scores_df.loc[0, 'projected_fppg'], expected_score_player_a, places=2)

    def test_calculate_vorp(self):
        """Test the calculate_vorp function."""
        # First calculate player scores
        scores_df = calculate_player_scores(
            self.predictions_df,
            model_weights=self.model_weights,
            prediction_cols={'lightgbm': 'predicted_lightgbm', 'random_forest': 'predicted_random_forest'}
        )
        
        # Then calculate VORP
        vorp_df = calculate_vorp(
            scores_df,
            replacement_ranks=self.replacement_ranks
        )
        
        # Check that the output has the expected columns
        self.assertIn('vorp', vorp_df.columns)
        
        # Check VORP calculation for QB position
        # QB replacement level should be the score of QB2 (Player B)
        qb_replacement = scores_df[scores_df['position'] == 'QB'].sort_values(
            by='projected_fppg', ascending=False
        ).iloc[1]['projected_fppg']
        
        # VORP for Player A (QB1) should be their score minus QB replacement level
        expected_vorp_player_a = scores_df.loc[0, 'projected_fppg'] - qb_replacement
        self.assertAlmostEqual(vorp_df.loc[0, 'vorp'], expected_vorp_player_a, places=2)
        
        # VORP for Player B (QB2) should be 0 as they are the replacement level
        self.assertAlmostEqual(vorp_df.loc[1, 'vorp'], 0, places=2)

    def test_generate_player_rankings(self):
        """Test the generate_player_rankings function."""
        # Calculate player scores and VORP
        scores_df = calculate_player_scores(
            self.predictions_df,
            model_weights=self.model_weights,
            prediction_cols={'lightgbm': 'predicted_lightgbm', 'random_forest': 'predicted_random_forest'}
        )
        vorp_df = calculate_vorp(
            scores_df,
            replacement_ranks=self.replacement_ranks
        )
        
        # Generate rankings
        rankings_df = generate_player_rankings(vorp_df, top_n=5)
        
        # Check that the output has the expected columns
        expected_columns = ['overall_rank', 'position_rank_display', 'player_name', 
                           'position', 'team', 'age', 'experience', 
                           'projected_fppg', 'vorp']
        for col in expected_columns:
            self.assertIn(col, rankings_df.columns)
        
        # Check that rankings are sorted by VORP in descending order
        self.assertTrue(rankings_df['vorp'].equals(rankings_df['vorp'].sort_values(ascending=False)))
        
        # Check that overall_rank starts at 1 and is sequential
        self.assertEqual(rankings_df['overall_rank'].min(), 1)
        self.assertEqual(len(rankings_df), rankings_df['overall_rank'].max())
        
        # Check that position_rank_display is formatted correctly (e.g., "QB1")
        # Check each row individually to avoid Series comparison issues
        for idx, row in rankings_df.iterrows():
            self.assertTrue(row['position'] in row['position_rank_display'])


if __name__ == '__main__':
    unittest.main()
