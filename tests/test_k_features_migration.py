"""
Tests for K feature engineering migration.

This module tests the KFeatureEngineer class, ensuring proper functionality
and BaseFeatureEngineer interface compliance for kicker position.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

# Import the new K feature engineer implementation
from src.data.feature_engineering.position.k_features_v2 import KFeatureEngineer


class TestKFeaturesMigration:
    """Test suite for K features migration."""
    
    @pytest.fixture
    def sample_k_data(self):
        """Create sample K data for testing."""
        return pd.DataFrame({
            'player_id': ['K1', 'K2', 'K3'],
            'player_name': ['Justin Tucker', 'Harrison Butker', 'Daniel Carlson'],
            'position': ['K', 'K', 'K'],
            'season': [2023, 2023, 2023],
            'games_played': [16, 15, 14],
            'fg_attempts': [35, 28, 32],
            'fg_made': [32, 25, 29],
            'xp_attempts': [45, 38, 42],
            'xp_made': [44, 37, 41],
            'fg_attempts_0_19': [2, 1, 3],
            'fg_made_0_19': [2, 1, 3],
            'fg_attempts_20_29': [8, 6, 7],
            'fg_made_20_29': [8, 6, 7],
            'fg_attempts_30_39': [12, 10, 11],
            'fg_made_30_39': [11, 9, 10],
            'fg_attempts_40_49': [10, 8, 9],
            'fg_made_40_49': [9, 7, 8],
            'fg_attempts_50_plus': [3, 3, 2],
            'fg_made_50_plus': [2, 2, 1],
            'fantasy_points': [138.5, 115.2, 122.8]
        })
    
    @pytest.fixture
    def empty_k_data(self):
        """Create empty K data for edge case testing."""
        return pd.DataFrame(columns=[
            'player_id', 'player_name', 'position', 'season', 'games_played',
            'fg_attempts', 'fg_made', 'xp_attempts', 'xp_made'
        ])
    
    @pytest.fixture
    def missing_columns_data(self):
        """Create K data with missing columns for testing robustness."""
        return pd.DataFrame({
            'player_id': ['K1'],
            'player_name': ['Test K'],
            'position': ['K'],
            'season': [2023],
            'games_played': [16],
            'fg_attempts': [30],
            # Missing: fg_made, xp_attempts, xp_made
        })
    
    def test_k_feature_engineer_initialization(self):
        """Test that KFeatureEngineer initializes correctly."""
        engineer = KFeatureEngineer()
        
        assert engineer.position == 'K'
        assert engineer.column_mapper is not None
        assert engineer.feature_calculator is not None
        assert engineer.logger is not None
    
    def test_data_validation_valid_data(self, sample_k_data):
        """Test data validation with valid K data."""
        engineer = KFeatureEngineer()
        
        assert engineer.validate_data(sample_k_data) is True
    
    def test_data_validation_empty_data(self, empty_k_data):
        """Test data validation with empty data."""
        engineer = KFeatureEngineer()
        
        assert engineer.validate_data(empty_k_data) is False
    
    def test_data_validation_missing_position_column(self, sample_k_data):
        """Test data validation with missing position column."""
        engineer = KFeatureEngineer()
        data_no_position = sample_k_data.drop('position', axis=1)
        
        assert engineer.validate_data(data_no_position) is False
    
    def test_data_validation_no_k_data(self, sample_k_data):
        """Test data validation with no K position data."""
        engineer = KFeatureEngineer()
        data_no_ks = sample_k_data.copy()
        data_no_ks['position'] = 'RB'  # Change all to RB
        
        assert engineer.validate_data(data_no_ks) is False
    
    def test_feature_engineering_basic_functionality(self, sample_k_data):
        """Test basic feature engineering functionality."""
        engineer = KFeatureEngineer()
        
        # Process the data
        result = engineer.engineer_features(sample_k_data)
        
        # Check that we got a DataFrame back
        assert isinstance(result, pd.DataFrame)
        
        # Check that original columns are preserved
        for col in sample_k_data.columns:
            assert col in result.columns
        
        # Check that K players are still there
        k_players = result[result['position'] == 'K']
        assert len(k_players) == 3
    
    def test_efficiency_metrics_calculation(self, sample_k_data):
        """Test that efficiency metrics are calculated correctly."""
        engineer = KFeatureEngineer()
        result = engineer.engineer_features(sample_k_data)
        
        k_players = result[result['position'] == 'K']
        
        # Check that FG percentage is calculated
        assert 'fg_percentage' in k_players.columns
        
        # Verify FG percentage calculation for first player
        first_k = k_players.iloc[0]
        expected_fg_pct = (32 / 35) * 100  # fg_made / fg_attempts * 100
        assert abs(first_k['fg_percentage'] - expected_fg_pct) < 0.01
        
        # Check XP percentage
        assert 'xp_percentage' in k_players.columns
        expected_xp_pct = (44 / 45) * 100
        assert abs(first_k['xp_percentage'] - expected_xp_pct) < 0.01
    
    def test_per_game_metrics_calculation(self, sample_k_data):
        """Test that per-game metrics are calculated correctly."""
        engineer = KFeatureEngineer()
        result = engineer.engineer_features(sample_k_data)
        
        k_players = result[result['position'] == 'K']
        
        # Check that per-game stats exist
        assert 'fg_attempts_per_game' in k_players.columns
        assert 'fg_made_per_game' in k_players.columns
        assert 'k_fantasy_points_per_game' in k_players.columns
        
        # Verify calculation for first player
        first_k = k_players.iloc[0]
        expected_attempts_per_game = 35 / 16  # fg_attempts / games_played
        assert abs(first_k['fg_attempts_per_game'] - expected_attempts_per_game) < 0.01
    
    def test_advanced_metrics_calculation(self, sample_k_data):
        """Test that advanced metrics are calculated correctly.""" 
        engineer = KFeatureEngineer()
        result = engineer.engineer_features(sample_k_data)
        
        k_players = result[result['position'] == 'K']
        
        # Check for advanced metrics
        assert 'high_volume_kicker' in k_players.columns
        assert 'volume_adjusted_accuracy' in k_players.columns
        
        # Check distance-based percentages if data is available
        if 'fg_attempts_0_19' in sample_k_data.columns:
            assert 'fg_percentage_0_19' in k_players.columns
    
    def test_reliability_scores_calculation(self, sample_k_data):
        """Test that reliability scores are calculated correctly."""
        engineer = KFeatureEngineer()
        result = engineer.engineer_features(sample_k_data)
        
        k_players = result[result['position'] == 'K']
        
        # Check for reliability metrics
        assert 'clutch_score' in k_players.columns
        assert 'consistency_score' in k_players.columns
        assert 'weather_reliability' in k_players.columns
    
    def test_mixed_position_data(self, sample_k_data):
        """Test feature engineering with mixed position data."""
        engineer = KFeatureEngineer()
        
        # Add some non-K players
        mixed_data = sample_k_data.copy()
        non_k_row = {
            'player_id': 'QB1',
            'player_name': 'Test QB',
            'position': 'QB',
            'season': 2023,
            'games_played': 16,
            'fg_attempts': 0,
            'fg_made': 0,
            'xp_attempts': 0,
            'xp_made': 0,
            'fantasy_points': 300.0
        }
        mixed_data = pd.concat([mixed_data, pd.DataFrame([non_k_row])], ignore_index=True)
        
        result = engineer.engineer_features(mixed_data)
        
        # Check that K players were processed
        k_players = result[result['position'] == 'K']
        assert len(k_players) == 3
        assert 'fg_percentage' in k_players.columns
        
        # Check that non-K player was preserved but not processed
        non_k_players = result[result['position'] != 'K']
        assert len(non_k_players) == 1
    
    def test_missing_columns_handling(self, missing_columns_data):
        """Test handling of missing columns."""
        engineer = KFeatureEngineer()
        
        # Should not crash, should handle gracefully
        result = engineer.engineer_features(missing_columns_data)
        
        # Should return the original data since validation fails
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
    
    def test_zero_games_handling(self, sample_k_data):
        """Test handling of zero games played."""
        engineer = KFeatureEngineer()
        
        # Set games played to 0 for one player
        test_data = sample_k_data.copy()
        test_data.loc[0, 'games_played'] = 0
        
        result = engineer.engineer_features(test_data)
        
        # Should not crash and should handle division by zero
        assert isinstance(result, pd.DataFrame)
        k_players = result[result['position'] == 'K']
        assert len(k_players) == 3
    
    def test_get_required_columns(self):
        """Test that required columns are returned correctly."""
        engineer = KFeatureEngineer()
        required_cols = engineer.get_required_columns()
        
        assert isinstance(required_cols, list)
        assert 'position' in required_cols
        assert any('games' in col for col in required_cols)
        assert any('fg_attempts' in col for col in required_cols)
        assert any('fg_made' in col for col in required_cols)
    
    def test_get_generated_features(self):
        """Test that generated features are returned correctly."""
        engineer = KFeatureEngineer()
        generated_features = engineer.get_generated_features()
        
        assert isinstance(generated_features, list)
        assert 'fg_percentage' in generated_features
        assert 'xp_percentage' in generated_features
        assert 'k_fantasy_points_per_game' in generated_features
        assert 'clutch_score' in generated_features
    
    def test_base_feature_engineer_interface(self):
        """Test that KFeatureEngineer follows BaseFeatureEngineer interface."""
        engineer = KFeatureEngineer()
        
        # Check required methods exist
        assert hasattr(engineer, 'engineer_features')
        assert hasattr(engineer, 'validate_data')
        assert hasattr(engineer, 'get_required_columns')
        assert hasattr(engineer, 'get_generated_features')
        
        # Check required attributes exist
        assert hasattr(engineer, 'position')
        assert hasattr(engineer, 'logger')
        
        # Check position is set correctly
        assert engineer.position == 'K'


def test_k_features_standalone():
    """Test K feature engineering as a standalone function.""" 
    # Create minimal test data
    test_data = pd.DataFrame({
        'player_id': ['K1'],
        'player_name': ['Test Kicker'],
        'position': ['K'],
        'season': [2023],
        'games_played': [16],
        'fg_attempts': [30],
        'fg_made': [27],
        'xp_attempts': [40],
        'xp_made': [39],
        'fantasy_points': [120.0]
    })
    
    engineer = KFeatureEngineer()
    result = engineer.engineer_features(test_data)
    
    # Basic functionality test
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert result.iloc[0]['position'] == 'K'


if __name__ == '__main__':
    pytest.main([__file__])