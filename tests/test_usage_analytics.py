"""
Unit tests for usage_analytics module.

Tests the calculation of advanced usage analytics including
Snap Counts, Route Participation, Usage Efficiency, and Situational Usage.
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.features.usage_analytics import (
    UsageAnalyticsCalculator,
    validate_usage_metrics,
    get_usage_analytics_for_season
)


class TestUsageAnalyticsCalculator(unittest.TestCase):
    """Test the UsageAnalyticsCalculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = UsageAnalyticsCalculator(2024)
        
        # Create sample player data
        self.sample_data = pd.DataFrame({
            'player_name': ['Player A', 'Player B', 'Player C'],
            'team': ['KC', 'BUF', 'DAL'],
            'position': ['WR', 'RB', 'TE'],
            'targets': [100, 50, 80],
            'receptions': [70, 35, 55],
            'carries': [0, 200, 5],
            'games': [16, 15, 14],
            'fantasy_points_ppr': [250, 280, 180]
        })
        
        # Create sample snap count data
        self.sample_snap_data = pd.DataFrame({
            'player': ['Player A', 'Player A', 'Player B', 'Player B'],
            'team': ['KC', 'KC', 'BUF', 'BUF'],
            'offense_snaps': [65, 70, 45, 50],
            'offense_pct': [0.8, 0.85, 0.6, 0.65]
        })
        
        # Create sample play-by-play data
        self.sample_pbp = pd.DataFrame({
            'receiver_player_name': ['Player A', 'Player A', 'Player C'],
            'posteam': ['KC', 'KC', 'DAL'],
            'play_type': ['pass', 'pass', 'pass'],
            'yardline_100': [25, 15, 10],  # For red zone testing
            'down': [1, 3, 2],
            'qtr': [2, 4, 3],
            'quarter_seconds_remaining': [90, 100, 200]
        })
    
    def test_calculator_initialization(self):
        """Test calculator initialization."""
        calc = UsageAnalyticsCalculator(2023)
        self.assertEqual(calc.season, 2023)
        self.assertIsNone(calc.snap_data)
        self.assertIsNone(calc.pbp_data)
    
    def test_calculate_snap_metrics_no_data(self):
        """Test snap metrics calculation with no snap data."""
        self.calculator.snap_data = None
        
        result = self.calculator.calculate_snap_metrics(self.sample_data)
        
        # Should add empty snap metrics
        expected_columns = ['total_snaps', 'avg_snap_share', 'snaps_per_game']
        for col in expected_columns:
            self.assertIn(col, result.columns)
            self.assertTrue((result[col] == 0).all())
    
    def test_calculate_snap_metrics_with_data(self):
        """Test snap metrics calculation with snap data."""
        self.calculator.snap_data = self.sample_snap_data
        
        result = self.calculator.calculate_snap_metrics(self.sample_data)
        
        # Should have snap metrics
        expected_columns = ['total_snaps', 'avg_snap_share', 'snaps_per_game']
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # Player A should have total_snaps = 65 + 70 = 135
        player_a_snaps = result[result['player_name'] == 'Player A']['total_snaps'].iloc[0]
        self.assertEqual(player_a_snaps, 135)
        
        # Snap share should be between 0 and 1
        self.assertTrue((result['avg_snap_share'] >= 0).all())
        self.assertTrue((result['avg_snap_share'] <= 1).all())
    
    def test_calculate_usage_efficiency_metrics(self):
        """Test usage efficiency metrics calculation."""
        # Add snap data
        test_data = self.sample_data.copy()
        test_data['total_snaps'] = [800, 600, 500]
        
        result = self.calculator.calculate_usage_efficiency_metrics(test_data)
        
        # Should have efficiency metrics
        expected_columns = ['targets_per_snap', 'total_touches', 'touches_per_snap']
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # Test targets per snap calculation
        expected_targets_per_snap_0 = test_data['targets'].iloc[0] / test_data['total_snaps'].iloc[0]
        actual_targets_per_snap_0 = result['targets_per_snap'].iloc[0]
        self.assertAlmostEqual(actual_targets_per_snap_0, expected_targets_per_snap_0, places=4)
        
        # Total touches should be targets + carries
        expected_touches_0 = test_data['targets'].iloc[0] + test_data['carries'].iloc[0]
        actual_touches_0 = result['total_touches'].iloc[0]
        self.assertEqual(actual_touches_0, expected_touches_0)
    
    def test_calculate_route_participation_no_pbp(self):
        """Test route participation with no play-by-play data."""
        self.calculator.pbp_data = None
        
        result = self.calculator.calculate_route_participation_advanced(self.sample_data)
        
        # Should add empty route participation
        self.assertIn('route_participation_advanced', result.columns)
        self.assertTrue((result['route_participation_advanced'] == 0).all())
    
    @patch('nfl_data_py.import_pbp_data')
    def test_calculate_route_participation_with_pbp(self, mock_pbp):
        """Test route participation with play-by-play data."""
        mock_pbp.return_value = self.sample_pbp
        self.calculator.pbp_data = None  # Force reload
        
        result = self.calculator.calculate_route_participation_advanced(self.sample_data)
        
        # Should have route participation data
        self.assertIn('route_participation_advanced', result.columns)
        
        # Values should be between 0 and 1
        route_participation = result['route_participation_advanced']
        self.assertTrue((route_participation >= 0).all())
        self.assertTrue((route_participation <= 1).all())
    
    def test_calculate_situational_usage_no_pbp(self):
        """Test situational usage with no play-by-play data."""
        self.calculator.pbp_data = None
        
        result = self.calculator.calculate_situational_usage(self.sample_data)
        
        # Should add empty situational usage columns
        expected_columns = ['red_zone_usage', 'goal_line_usage', 'third_down_usage', 'two_minute_usage']
        for col in expected_columns:
            self.assertIn(col, result.columns)
            self.assertTrue((result[col] == 0).all())
    
    @patch('nfl_data_py.import_pbp_data')
    def test_calculate_situational_usage_with_pbp(self, mock_pbp):
        """Test situational usage with play-by-play data."""
        mock_pbp.return_value = self.sample_pbp
        self.calculator.pbp_data = None  # Force reload
        
        result = self.calculator.calculate_situational_usage(self.sample_data)
        
        # Should have situational usage columns
        expected_columns = ['red_zone_usage', 'goal_line_usage', 'third_down_usage', 'two_minute_usage']
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # Values should be non-negative
        for col in expected_columns:
            self.assertTrue((result[col] >= 0).all())
    
    def test_calculate_all_usage_metrics(self):
        """Test the comprehensive usage metrics calculation."""
        result = self.calculator.calculate_all_usage_metrics(self.sample_data)
        
        # Should have more columns than original
        self.assertGreater(len(result.columns), len(self.sample_data.columns))
        
        # Should have key usage metrics (even if empty due to no snap data)
        expected_metrics = ['total_snaps', 'avg_snap_share', 'snaps_per_game']
        for metric in expected_metrics:
            self.assertIn(metric, result.columns)


class TestUsageMetricsValidation(unittest.TestCase):
    """Test usage metrics validation functions."""
    
    def setUp(self):
        """Set up test data."""
        self.valid_data = pd.DataFrame({
            'player_name': ['Player A', 'Player B', 'Player C'],
            'avg_snap_share': [0.8, 0.6, 0.4],
            'total_snaps': [800, 600, 400],
            'snaps_per_game': [50, 40, 30],
            'targets_per_snap': [0.12, 0.08, 0.15],
            'utilization_rate': [15, 10, 18],
            'route_participation_advanced': [0.75, 0.65, 0.55]
        })
        
        self.invalid_data = pd.DataFrame({
            'player_name': ['Player X', 'Player Y'],
            'avg_snap_share': [1.5, -0.1],  # Invalid: >1 and negative
            'total_snaps': [3000, -50],  # Invalid: too high and negative
            'targets_per_snap': [1.5, -0.1],  # Invalid: >1 and negative
            'utilization_rate': [150, -10],  # Invalid: >100 and negative
            'route_participation_advanced': [1.5, -0.2]  # Invalid: >1 and negative
        })
    
    def test_validate_usage_metrics_valid_data(self):
        """Test validation with valid data."""
        result = validate_usage_metrics(self.valid_data)
        
        # Should find metrics and validate them
        self.assertGreater(len(result), 0)
        
        # All validations should pass for valid data
        for metric, valid in result.items():
            self.assertTrue(valid, f"Metric {metric} failed validation")
    
    def test_validate_usage_metrics_invalid_data(self):
        """Test validation with invalid data."""
        result = validate_usage_metrics(self.invalid_data)
        
        # Should find validation failures
        failing_metrics = [metric for metric, valid in result.items() if not valid]
        self.assertGreater(len(failing_metrics), 0)


class TestUsageAnalyticsIntegration(unittest.TestCase):
    """Test integration with real data pipeline."""
    
    @patch('src.current_data_pipeline.create_current_inference_dataset')
    def test_get_usage_analytics_for_season(self, mock_create_dataset):
        """Test getting usage analytics for a season."""
        # Mock the data creation
        mock_data = pd.DataFrame({
            'player_name': ['Test Player'],
            'team': ['KC'],
            'position': ['WR'],
            'targets': [100],
            'receptions': [70],
            'games': [16]
        })
        mock_create_dataset.return_value = mock_data
        
        result = get_usage_analytics_for_season(2024, ['WR'])
        
        # Should return enhanced data
        self.assertFalse(result.empty)
        self.assertIn('player_name', result.columns)
        
        # Should have called create_current_inference_dataset
        mock_create_dataset.assert_called()


class TestUsageAnalyticsCalculations(unittest.TestCase):
    """Test specific calculation logic."""
    
    def test_snap_share_aggregation(self):
        """Test snap share aggregation logic."""
        snap_data = pd.DataFrame({
            'player': ['Player A', 'Player A', 'Player A'],
            'team': ['KC', 'KC', 'KC'],
            'offense_snaps': [60, 65, 70],
            'offense_pct': [0.75, 0.80, 0.85]
        })
        
        calculator = UsageAnalyticsCalculator(2024)
        calculator.snap_data = snap_data
        
        player_data = pd.DataFrame({
            'player_name': ['Player A'],
            'team': ['KC'],
            'games': [3]
        })
        
        result = calculator.calculate_snap_metrics(player_data)
        
        # Total snaps should be sum: 60 + 65 + 70 = 195
        self.assertEqual(result['total_snaps'].iloc[0], 195)
        
        # Average snap share should be mean: (0.75 + 0.80 + 0.85) / 3 = 0.8
        self.assertAlmostEqual(result['avg_snap_share'].iloc[0], 0.8, places=2)
        
        # Snaps per game: 195 / 3 = 65
        self.assertAlmostEqual(result['snaps_per_game'].iloc[0], 65, places=1)
    
    def test_utilization_rate_calculation(self):
        """Test utilization rate calculation."""
        test_data = pd.DataFrame({
            'player_name': ['Player A'],
            'targets': [80],
            'carries': [20],
            'total_snaps': [500]
        })
        
        calculator = UsageAnalyticsCalculator(2024)
        result = calculator.calculate_usage_efficiency_metrics(test_data)
        
        # Total touches: 80 + 20 = 100
        self.assertEqual(result['total_touches'].iloc[0], 100)
        
        # Touches per snap: 100 / 500 = 0.2
        self.assertAlmostEqual(result['touches_per_snap'].iloc[0], 0.2, places=3)
        
        # Utilization rate: 0.2 * 100 = 20%
        self.assertAlmostEqual(result['utilization_rate'].iloc[0], 20, places=1)
    
    def test_fantasy_points_per_snap(self):
        """Test fantasy points per snap calculation."""
        test_data = pd.DataFrame({
            'player_name': ['Player A'],
            'fantasy_points_ppr': [300],
            'total_snaps': [800]
        })
        
        calculator = UsageAnalyticsCalculator(2024)
        result = calculator.calculate_usage_efficiency_metrics(test_data)
        
        # Fantasy points per snap: 300 / 800 = 0.375
        expected_fps = 300 / 800
        self.assertAlmostEqual(result['fantasy_points_per_snap'].iloc[0], expected_fps, places=3)
    
    def test_edge_cases(self):
        """Test edge cases in calculations."""
        # Test with zero snaps
        test_data = pd.DataFrame({
            'player_name': ['Player A'],
            'targets': [50],
            'total_snaps': [0]  # Edge case: zero snaps
        })
        
        calculator = UsageAnalyticsCalculator(2024)
        result = calculator.calculate_usage_efficiency_metrics(test_data)
        
        # Should handle division by zero gracefully
        self.assertEqual(result['targets_per_snap'].iloc[0], 0)
        
        # Test with missing columns
        minimal_data = pd.DataFrame({
            'player_name': ['Player A']
        })
        
        result = calculator.calculate_usage_efficiency_metrics(minimal_data)
        # Should not crash and should return the data
        self.assertIn('player_name', result.columns)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)