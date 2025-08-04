"""
Tests for QB feature engineering migration.

This module tests the migration from legacy qb_features.py to the new
QBFeatureEngineer class, ensuring backward compatibility and correctness.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

# Import both old and new implementations
from src.data.feature_engineering.position.qb_features import engineer_qb_features as legacy_engineer_qb_features
from src.data.feature_engineering.position.qb_features_v2 import QBFeatureEngineer, engineer_qb_features as new_engineer_qb_features


class TestQBFeaturesMigration:
    """Test suite for QB features migration."""
    
    @pytest.fixture
    def sample_qb_data(self):
        """Create sample QB data for testing."""
        return pd.DataFrame({
            'player_id': ['QB1', 'QB2', 'QB3'],
            'player_name': ['Aaron Rodgers', 'Josh Allen', 'Tom Brady'],
            'position': ['QB', 'QB', 'QB'],
            'season': [2023, 2023, 2023],
            'games_played': [16, 15, 14],
            'passing_attempts': [500, 550, 450],
            'passing_completions': [350, 380, 320],
            'passing_yards': [4200, 4500, 3800],
            'passing_touchdowns': [30, 35, 25],
            'passing_interceptions': [8, 12, 6],
            'rushing_attempts': [20, 80, 5],
            'rushing_yards': [100, 800, 10],
            'rushing_touchdowns': [2, 8, 0],
            'fantasy_points': [320.5, 410.2, 285.8]
        })
    
    @pytest.fixture
    def empty_qb_data(self):
        """Create empty QB data for edge case testing."""
        return pd.DataFrame(columns=[
            'player_id', 'player_name', 'position', 'season', 'games_played',
            'passing_attempts', 'passing_completions', 'passing_yards',
            'passing_touchdowns', 'passing_interceptions'
        ])
    
    @pytest.fixture
    def missing_columns_data(self):
        """Create QB data with missing columns for testing robustness."""
        return pd.DataFrame({
            'player_id': ['QB1'],
            'player_name': ['Test QB'],
            'position': ['QB'],
            'season': [2023],
            'games_played': [16],
            'passing_attempts': [500],
            # Missing: completions, yards, touchdowns, interceptions
        })
    
    def test_qb_feature_engineer_initialization(self):
        """Test that QBFeatureEngineer initializes correctly."""
        engineer = QBFeatureEngineer()
        
        assert engineer.position == 'QB'
        assert engineer.column_mapper is not None
        assert engineer.feature_calculator is not None
        assert engineer.logger is not None
    
    def test_data_validation_valid_data(self, sample_qb_data):
        """Test data validation with valid QB data."""
        engineer = QBFeatureEngineer()
        
        assert engineer.validate_data(sample_qb_data) is True
    
    def test_data_validation_empty_data(self, empty_qb_data):
        """Test data validation with empty data."""
        engineer = QBFeatureEngineer()
        
        assert engineer.validate_data(empty_qb_data) is False
    
    def test_data_validation_missing_position_column(self, sample_qb_data):
        """Test data validation with missing position column."""
        engineer = QBFeatureEngineer()
        data_no_position = sample_qb_data.drop('position', axis=1)
        
        assert engineer.validate_data(data_no_position) is False
    
    def test_data_validation_no_qb_data(self, sample_qb_data):
        """Test data validation with no QB position data."""
        engineer = QBFeatureEngineer()
        data_no_qbs = sample_qb_data.copy()
        data_no_qbs['position'] = 'RB'  # Change all to RB
        
        assert engineer.validate_data(data_no_qbs) is False
    
    def test_feature_engineering_basic_functionality(self, sample_qb_data):
        """Test basic feature engineering functionality."""
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(sample_qb_data)
        
        # Check that result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Check that only QB data is returned
        assert len(result) == 3
        assert all(result['position'] == 'QB')
        
        # Check that key features are present
        expected_features = [
            'completion_percentage', 'yards_per_attempt', 'touchdown_percentage',
            'interception_percentage', 'passer_rating', 'passing_yards_per_game',
            'passing_tds_per_game', 'qb_efficiency'
        ]
        
        for feature in expected_features:
            assert feature in result.columns, f"Missing feature: {feature}"
    
    def test_efficiency_metrics_calculation(self, sample_qb_data):
        """Test that efficiency metrics are calculated correctly."""
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(sample_qb_data)
        
        # Test first QB (Aaron Rodgers): 350/500 completions = 70%
        assert abs(result.iloc[0]['completion_percentage'] - 70.0) < 0.01
        
        # Test yards per attempt: 4200/500 = 8.4
        assert abs(result.iloc[0]['yards_per_attempt'] - 8.4) < 0.01
        
        # Test touchdown percentage: 30/500 * 100 = 6.0%
        assert abs(result.iloc[0]['touchdown_percentage'] - 6.0) < 0.01
        
        # Test interception percentage: 8/500 * 100 = 1.6%
        assert abs(result.iloc[0]['interception_percentage'] - 1.6) < 0.01
    
    def test_per_game_metrics_calculation(self, sample_qb_data):
        """Test that per-game metrics are calculated correctly."""
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(sample_qb_data)
        
        # Test passing yards per game: 4200/16 = 262.5
        assert abs(result.iloc[0]['passing_yards_per_game'] - 262.5) < 0.01
        
        # Test passing TDs per game: 30/16 = 1.875
        assert abs(result.iloc[0]['passing_tds_per_game'] - 1.875) < 0.01
        
        # Test rushing yards per game: 100/16 = 6.25
        assert abs(result.iloc[0]['rushing_yards_per_game'] - 6.25) < 0.01
    
    def test_passer_rating_calculation(self, sample_qb_data):
        """Test that passer rating is calculated correctly."""
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(sample_qb_data)
        
        # Passer rating should be reasonable (0-158.3 range)
        for i in range(len(result)):
            rating = result.iloc[i]['passer_rating']
            assert 0 <= rating <= 158.3, f"Invalid passer rating: {rating}"
            assert not pd.isna(rating), "Passer rating should not be NaN"
    
    def test_missing_columns_handling(self, missing_columns_data):
        """Test graceful handling of missing columns."""
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(missing_columns_data)
        
        # Should not crash and should return some result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        
        # Missing data columns should result in 0 values
        assert result.iloc[0]['completion_percentage'] == 0.0
        assert result.iloc[0]['yards_per_attempt'] == 0.0
        assert result.iloc[0]['touchdown_percentage'] == 0.0
        assert result.iloc[0]['interception_percentage'] == 0.0
    
    def test_feature_names_method(self):
        """Test that get_feature_names returns expected features."""
        engineer = QBFeatureEngineer()
        feature_names = engineer.get_feature_names()
        
        # Check that it returns a list
        assert isinstance(feature_names, list)
        
        # Check that key features are included
        expected_features = [
            'completion_percentage', 'yards_per_attempt', 'passer_rating',
            'passing_yards_per_game', 'qb_efficiency'
        ]
        
        for feature in expected_features:
            assert feature in feature_names
    
    def test_legacy_compatibility_function(self, sample_qb_data):
        """Test that the legacy compatibility function works."""
        result = new_engineer_qb_features(sample_qb_data)
        
        # Should produce the same type of result as the class method
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert 'completion_percentage' in result.columns
        assert 'passer_rating' in result.columns
    
    def test_zero_attempts_handling(self):
        """Test handling of QBs with zero passing attempts."""
        data = pd.DataFrame({
            'player_id': ['QB_ZERO'],
            'player_name': ['Zero Attempts QB'],
            'position': ['QB'],
            'season': [2023],
            'games_played': [1],
            'passing_attempts': [0],
            'passing_completions': [0],
            'passing_yards': [0],
            'passing_touchdowns': [0],
            'passing_interceptions': [0]
        })
        
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(data)
        
        # Should handle gracefully without errors
        assert len(result) == 1
        assert result.iloc[0]['completion_percentage'] == 0.0
        assert result.iloc[0]['yards_per_attempt'] == 0.0
        assert result.iloc[0]['passer_rating'] == 0.0
    
    def test_mixed_position_data(self):
        """Test handling of data with mixed positions."""
        mixed_data = pd.DataFrame({
            'player_id': ['QB1', 'RB1', 'QB2'],
            'player_name': ['Test QB1', 'Test RB', 'Test QB2'],
            'position': ['QB', 'RB', 'QB'],
            'season': [2023, 2023, 2023],
            'games_played': [16, 16, 15],
            'passing_attempts': [500, 0, 400],
            'passing_completions': [350, 0, 280],
            'passing_yards': [4200, 0, 3500],
            'passing_touchdowns': [30, 0, 25],
            'passing_interceptions': [8, 0, 6]
        })
        
        engineer = QBFeatureEngineer()
        result = engineer.engineer_features(mixed_data)
        
        # Should only return QB data
        assert len(result) == 2
        assert all(result['position'] == 'QB')
        assert 'Test QB1' in result['player_name'].values
        assert 'Test QB2' in result['player_name'].values
        assert 'Test RB' not in result['player_name'].values


if __name__ == '__main__':
    pytest.main([__file__])