"""
Tests for DST feature engineering migration.

This module tests the DSTFeatureEngineer class, ensuring proper functionality
and BaseFeatureEngineer interface compliance for defense/special teams position.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

# Import the new DST feature engineer implementation
from src.data.feature_engineering.position.dst_features_v2 import DSTFeatureEngineer


class TestDSTFeaturesMigration:
    """Test suite for DST features migration."""
    
    @pytest.fixture
    def sample_dst_data(self):
        """Create sample DST data for testing."""
        return pd.DataFrame({
            'player_id': ['DST1', 'DST2', 'DST3'],
            'player_name': ['Patriots Defense', 'Cowboys Defense', 'Bills Defense'],
            'position': ['DST', 'DST', 'DST'],
            'season': [2023, 2023, 2023],
            'games_played': [16, 15, 14],
            'sacks': [45, 38, 52],
            'interceptions': [18, 12, 22],
            'fumbles_recovered': [8, 6, 10],
            'defensive_tds': [3, 1, 4],
            'special_teams_tds': [2, 0, 1],
            'safeties': [1, 0, 2],
            'points_allowed': [320, 380, 290],
            'yards_allowed': [4800, 5200, 4600],
            'pass_yards_allowed': [3200, 3600, 3000],
            'rush_yards_allowed': [1600, 1600, 1600],
            'fantasy_points': [185.5, 142.2, 220.8]
        })
    
    @pytest.fixture
    def empty_dst_data(self):
        """Create empty DST data for edge case testing."""
        return pd.DataFrame(columns=[
            'player_id', 'player_name', 'position', 'season', 'games_played',
            'sacks', 'interceptions', 'fumbles_recovered', 'points_allowed'
        ])
    
    @pytest.fixture
    def missing_columns_data(self):
        """Create DST data with missing columns for testing robustness."""
        return pd.DataFrame({
            'player_id': ['DST1'],
            'player_name': ['Test Defense'],
            'position': ['DST'],
            'season': [2023],
            'games_played': [16],
            'sacks': [40],
            # Missing: interceptions, fumbles_recovered, points_allowed, etc.
        })
    
    def test_dst_feature_engineer_initialization(self):
        """Test that DSTFeatureEngineer initializes correctly."""
        engineer = DSTFeatureEngineer()
        
        assert engineer.position == 'DST'
        assert engineer.column_mapper is not None
        assert engineer.feature_calculator is not None
        assert engineer.logger is not None
    
    def test_data_validation_valid_data(self, sample_dst_data):
        """Test data validation with valid DST data."""
        engineer = DSTFeatureEngineer()
        
        assert engineer.validate_data(sample_dst_data) is True
    
    def test_data_validation_empty_data(self, empty_dst_data):
        """Test data validation with empty data."""
        engineer = DSTFeatureEngineer()
        
        assert engineer.validate_data(empty_dst_data) is False
    
    def test_data_validation_missing_position_column(self, sample_dst_data):
        """Test data validation with missing position column."""
        engineer = DSTFeatureEngineer()
        data_no_position = sample_dst_data.drop('position', axis=1)
        
        assert engineer.validate_data(data_no_position) is False
    
    def test_data_validation_no_dst_data(self, sample_dst_data):
        """Test data validation with no DST position data."""
        engineer = DSTFeatureEngineer()
        data_no_dsts = sample_dst_data.copy()
        data_no_dsts['position'] = 'RB'  # Change all to RB
        
        assert engineer.validate_data(data_no_dsts) is False
    
    def test_data_validation_alternative_dst_names(self, sample_dst_data):
        """Test data validation with alternative DST position names."""
        engineer = DSTFeatureEngineer()
        
        # Test with 'DEF' position name
        data_def = sample_dst_data.copy()
        data_def['position'] = 'DEF'
        assert engineer.validate_data(data_def) is True
        
        # Test with 'D/ST' position name
        data_dst = sample_dst_data.copy()
        data_dst['position'] = 'D/ST'
        assert engineer.validate_data(data_dst) is True
    
    def test_feature_engineering_basic_functionality(self, sample_dst_data):
        """Test basic feature engineering functionality."""
        engineer = DSTFeatureEngineer()
        
        # Process the data
        result = engineer.engineer_features(sample_dst_data)
        
        # Check that we got a DataFrame back
        assert isinstance(result, pd.DataFrame)
        
        # Check that original columns are preserved
        for col in sample_dst_data.columns:
            assert col in result.columns
        
        # Check that DST players are still there
        dst_players = result[result['position'] == 'DST']
        assert len(dst_players) == 3
    
    def test_defensive_efficiency_calculation(self, sample_dst_data):
        """Test that defensive efficiency metrics are calculated correctly."""
        engineer = DSTFeatureEngineer()
        result = engineer.engineer_features(sample_dst_data)
        
        dst_players = result[result['position'] == 'DST']
        
        # Check that efficiency metrics are calculated
        assert 'points_allowed_per_game' in dst_players.columns
        assert 'yards_allowed_per_game' in dst_players.columns
        assert 'sacks_per_game' in dst_players.columns
        
        # Verify points allowed per game calculation for first defense
        first_dst = dst_players.iloc[0]
        expected_pa_per_game = 320 / 16  # points_allowed / games_played
        assert abs(first_dst['points_allowed_per_game'] - expected_pa_per_game) < 0.01
    
    def test_per_game_metrics_calculation(self, sample_dst_data):
        """Test that per-game metrics are calculated correctly."""
        engineer = DSTFeatureEngineer()
        result = engineer.engineer_features(sample_dst_data)
        
        dst_players = result[result['position'] == 'DST']
        
        # Check that per-game stats exist
        assert 'interceptions_per_game' in dst_players.columns
        assert 'fumbles_recovered_per_game' in dst_players.columns
        assert 'defensive_tds_per_game' in dst_players.columns
        
        # Verify calculation for first defense
        first_dst = dst_players.iloc[0]
        expected_ints_per_game = 18 / 16  # interceptions / games_played
        assert abs(first_dst['interceptions_per_game'] - expected_ints_per_game) < 0.01
    
    def test_turnover_metrics_calculation(self, sample_dst_data):
        """Test that turnover metrics are calculated correctly."""
        engineer = DSTFeatureEngineer()
        result = engineer.engineer_features(sample_dst_data)
        
        dst_players = result[result['position'] == 'DST']
        
        # Check for turnover metrics
        assert 'total_turnovers' in dst_players.columns
        assert 'turnover_differential' in dst_players.columns
        assert 'turnovers_per_game' in dst_players.columns
        assert 'ball_hawking_score' in dst_players.columns
        
        # Verify total turnovers calculation for first defense
        first_dst = dst_players.iloc[0]
        expected_turnovers = 18 + 8  # interceptions + fumbles_recovered
        assert first_dst['total_turnovers'] == expected_turnovers
    
    def test_special_teams_metrics_calculation(self, sample_dst_data):
        """Test that special teams metrics are calculated correctly."""
        engineer = DSTFeatureEngineer()
        result = engineer.engineer_features(sample_dst_data)
        
        dst_players = result[result['position'] == 'DST']
        
        # Check for special teams metrics
        assert 'st_tds_per_game' in dst_players.columns
        assert 'return_td_total' in dst_players.columns
        assert 'special_plays_total' in dst_players.columns
    
    def test_strength_indicators_calculation(self, sample_dst_data):
        """Test that strength indicators are calculated correctly."""
        engineer = DSTFeatureEngineer()
        result = engineer.engineer_features(sample_dst_data)
        
        dst_players = result[result['position'] == 'DST']
        
        # Check for strength indicators
        assert 'elite_defense' in dst_players.columns
        assert 'bend_dont_break' in dst_players.columns
        assert 'big_play_defense_score' in dst_players.columns
        assert 'td_upside_score' in dst_players.columns
        assert 'consistency_score' in dst_players.columns
        
        # Test elite defense classification
        first_dst = dst_players.iloc[0]
        # First defense allows 320/16 = 20 points per game (should be bend_dont_break)
        assert first_dst['bend_dont_break'] == 1
        assert first_dst['elite_defense'] == 0
    
    def test_mixed_position_data(self, sample_dst_data):
        """Test feature engineering with mixed position data."""
        engineer = DSTFeatureEngineer()
        
        # Add some non-DST players
        mixed_data = sample_dst_data.copy()
        non_dst_row = {
            'player_id': 'QB1',
            'player_name': 'Test QB',
            'position': 'QB',
            'season': 2023,
            'games_played': 16,
            'sacks': 0,
            'interceptions': 0,
            'points_allowed': 0,
            'fantasy_points': 300.0
        }
        mixed_data = pd.concat([mixed_data, pd.DataFrame([non_dst_row])], ignore_index=True)
        
        result = engineer.engineer_features(mixed_data)
        
        # Check that DST players were processed
        dst_players = result[result['position'] == 'DST']
        assert len(dst_players) == 3
        assert 'points_allowed_per_game' in dst_players.columns
        
        # Check that non-DST player was preserved but not processed for DST features
        non_dst_players = result[result['position'] != 'DST']
        assert len(non_dst_players) == 1
    
    def test_missing_columns_handling(self, missing_columns_data):
        """Test handling of missing columns."""
        engineer = DSTFeatureEngineer()
        
        # Should not crash, should handle gracefully
        result = engineer.engineer_features(missing_columns_data)
        
        # Should return the original data since validation passes but features may not be calculated
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
    
    def test_zero_games_handling(self, sample_dst_data):
        """Test handling of zero games played."""
        engineer = DSTFeatureEngineer()
        
        # Set games played to 0 for one defense
        test_data = sample_dst_data.copy()
        test_data.loc[0, 'games_played'] = 0
        
        result = engineer.engineer_features(test_data)
        
        # Should not crash and should handle division by zero
        assert isinstance(result, pd.DataFrame)
        dst_players = result[result['position'] == 'DST']
        assert len(dst_players) == 3
    
    def test_get_required_columns(self):
        """Test that required columns are returned correctly."""
        engineer = DSTFeatureEngineer()
        required_cols = engineer.get_required_columns()
        
        assert isinstance(required_cols, list)
        assert 'position' in required_cols
        assert any('games' in col for col in required_cols)
        assert any('sacks' in col for col in required_cols)
        assert any('interceptions' in col for col in required_cols)
    
    def test_get_generated_features(self):
        """Test that generated features are returned correctly."""
        engineer = DSTFeatureEngineer()
        generated_features = engineer.get_generated_features()
        
        assert isinstance(generated_features, list)
        assert 'points_allowed_per_game' in generated_features
        assert 'total_turnovers' in generated_features
        assert 'big_play_defense_score' in generated_features
        assert 'elite_defense' in generated_features
    
    def test_base_feature_engineer_interface(self):
        """Test that DSTFeatureEngineer follows BaseFeatureEngineer interface."""
        engineer = DSTFeatureEngineer()
        
        # Check required methods exist
        assert hasattr(engineer, 'engineer_features')
        assert hasattr(engineer, 'validate_data')
        assert hasattr(engineer, 'get_required_columns')
        assert hasattr(engineer, 'get_generated_features')
        
        # Check required attributes exist
        assert hasattr(engineer, 'position')
        assert hasattr(engineer, 'logger')
        
        # Check position is set correctly
        assert engineer.position == 'DST'


def test_dst_features_standalone():
    """Test DST feature engineering as a standalone function."""
    # Create minimal test data
    test_data = pd.DataFrame({
        'player_id': ['DST1'],
        'player_name': ['Test Defense'],
        'position': ['DST'],
        'season': [2023],
        'games_played': [16],
        'sacks': [40],
        'interceptions': [15],
        'fumbles_recovered': [8],
        'points_allowed': [340],
        'fantasy_points': [180.0]
    })
    
    engineer = DSTFeatureEngineer()
    result = engineer.engineer_features(test_data)
    
    # Basic functionality test
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]['position'] == 'DST'


if __name__ == '__main__':
    pytest.main([__file__])