"""
Tests for RB feature engineering migration.

This module tests the migration from legacy rb_features.py to the new
RBFeatureEngineer class, ensuring backward compatibility and correctness.
"""

import pytest
import pandas as pd
import numpy as np

# Import both old and new implementations
from src.data.feature_engineering.position.rb_features_v2 import RBFeatureEngineer, engineer_rb_features as new_engineer_rb_features


class TestRBFeaturesMigration:
    """Test suite for RB features migration."""
    
    @pytest.fixture
    def sample_rb_data(self):
        """Create sample RB data for testing."""
        return pd.DataFrame({
            'player_id': ['RB1', 'RB2', 'RB3'],
            'player_name': ['Christian McCaffrey', 'Derrick Henry', 'Austin Ekeler'],
            'position': ['RB', 'RB', 'RB'],
            'season': [2023, 2023, 2023],
            'games': [16, 14, 15],
            'rushing_attempts': [300, 280, 200],
            'rushing_yards': [1500, 1400, 800],
            'rushing_touchdowns': [15, 12, 5],
            'targets': [100, 20, 120],
            'receptions': [85, 15, 100],
            'receiving_yards': [800, 150, 900],
            'receiving_touchdowns': [8, 2, 10],
            'fantasy_points': [420.5, 310.2, 385.8]
        })
    
    @pytest.fixture
    def empty_rb_data(self):
        """Create empty RB data for edge case testing."""
        return pd.DataFrame(columns=[
            'player_id', 'player_name', 'position', 'season', 'games',
            'rushing_attempts', 'rushing_yards', 'rushing_touchdowns',
            'targets', 'receptions', 'receiving_yards', 'receiving_touchdowns'
        ])
    
    @pytest.fixture
    def missing_columns_data(self):
        """Create RB data with missing columns for testing robustness."""
        return pd.DataFrame({
            'player_id': ['RB1'],
            'player_name': ['Test RB'],
            'position': ['RB'],
            'season': [2023],
            'games': [16],
            'rushing_attempts': [200],
            # Missing: rushing_yards, touchdowns, receiving stats
        })
    
    def test_rb_feature_engineer_initialization(self):
        """Test that RBFeatureEngineer initializes correctly."""
        engineer = RBFeatureEngineer()
        
        assert engineer.position == 'RB'
        assert engineer.column_mapper is not None
        assert engineer.feature_calculator is not None
        assert engineer.logger is not None
    
    def test_data_validation_valid_data(self, sample_rb_data):
        """Test data validation with valid RB data."""
        engineer = RBFeatureEngineer()
        
        assert engineer.validate_data(sample_rb_data) is True
    
    def test_data_validation_empty_data(self, empty_rb_data):
        """Test data validation with empty data."""
        engineer = RBFeatureEngineer()
        
        assert engineer.validate_data(empty_rb_data) is False
    
    def test_data_validation_missing_position_column(self, sample_rb_data):
        """Test data validation with missing position column."""
        engineer = RBFeatureEngineer()
        data_no_position = sample_rb_data.drop('position', axis=1)
        
        assert engineer.validate_data(data_no_position) is False
    
    def test_data_validation_no_rb_data(self, sample_rb_data):
        """Test data validation with no RB position data."""
        engineer = RBFeatureEngineer()
        data_no_rbs = sample_rb_data.copy()
        data_no_rbs['position'] = 'QB'  # Change all to QB
        
        assert engineer.validate_data(data_no_rbs) is False
    
    def test_feature_engineering_basic_functionality(self, sample_rb_data):
        """Test basic feature engineering functionality."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(sample_rb_data)
        
        # Check that result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Check that only RB data is returned
        assert len(result) == 3
        assert all(result['position'] == 'RB')
        
        # Check that key features are present
        expected_features = [
            'yards_per_carry', 'yards_per_reception', 'yards_per_touch',
            'catch_rate', 'rushing_yards_per_game', 'receiving_yards_per_game',
            'carries_per_game', 'touches_per_game', 'workhorse_score'
        ]
        
        for feature in expected_features:
            assert feature in result.columns, f"Missing feature: {feature}"
    
    def test_efficiency_metrics_calculation(self, sample_rb_data):
        """Test that efficiency metrics are calculated correctly."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(sample_rb_data)
        
        # Test first RB (Christian McCaffrey): 1500 yards / 300 carries = 5.0 YPC
        assert abs(result.iloc[0]['yards_per_carry'] - 5.0) < 0.01
        
        # Test yards per reception: 800 yards / 85 receptions = 9.41 YPR
        assert abs(result.iloc[0]['yards_per_reception'] - (800/85)) < 0.01
        
        # Test catch rate: 85 receptions / 100 targets = 85%
        assert abs(result.iloc[0]['catch_rate'] - 0.85) < 0.01
        
        # Test yards per touch: (1500 + 800) / (300 + 85) = 5.97
        expected_ypt = (1500 + 800) / (300 + 85)
        assert abs(result.iloc[0]['yards_per_touch'] - expected_ypt) < 0.01
    
    def test_per_game_metrics_calculation(self, sample_rb_data):
        """Test that per-game metrics are calculated correctly."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(sample_rb_data)
        
        # Test rushing yards per game: 1500/16 = 93.75
        assert abs(result.iloc[0]['rushing_yards_per_game'] - 93.75) < 0.01
        
        # Test carries per game: 300/16 = 18.75
        assert abs(result.iloc[0]['carries_per_game'] - 18.75) < 0.01
        
        # Test receiving yards per game: 800/16 = 50.0
        assert abs(result.iloc[0]['receiving_yards_per_game'] - 50.0) < 0.01
        
        # Test touches per game: (300+85)/16 = 24.0625
        expected_tpg = (300 + 85) / 16
        assert abs(result.iloc[0]['touches_per_game'] - expected_tpg) < 0.01
    
    def test_role_classification_features(self, sample_rb_data):
        """Test that role classification features are calculated."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(sample_rb_data)
        
        # Workhorse score should be high for McCaffrey (18.75 carries/game > 15)
        assert result.iloc[0]['workhorse_score'] > 0.8
        
        # Committee back score should be low for McCaffrey
        assert result.iloc[0]['committee_back_score'] == 0.0
        
        # Pass-catching back score should be high for McCaffrey (100 targets)
        assert result.iloc[0]['pass_catching_back_score'] > 0.5
        
        # Versatility score should be high for McCaffrey
        assert result.iloc[0]['rb_versatility_score'] > 0.8
    
    def test_missing_columns_handling(self, missing_columns_data):
        """Test graceful handling of missing columns."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(missing_columns_data)
        
        # Should not crash and should return some result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        
        # Missing data columns should result in 0 values for some metrics
        assert result.iloc[0]['yards_per_carry'] == 0.0
        assert result.iloc[0]['yards_per_reception'] == 0.0
        assert result.iloc[0]['catch_rate'] == 0.0
    
    def test_get_required_columns(self):
        """Test that get_required_columns returns expected columns."""
        engineer = RBFeatureEngineer()
        required_cols = engineer.get_required_columns()
        
        assert isinstance(required_cols, list)
        assert 'position' in required_cols
        assert 'games' in required_cols
    
    def test_get_generated_features(self):
        """Test that get_generated_features returns expected features."""
        engineer = RBFeatureEngineer()
        feature_names = engineer.get_generated_features()
        
        # Check that it returns a list
        assert isinstance(feature_names, list)
        
        # Check that key features are included
        expected_features = [
            'yards_per_carry', 'yards_per_reception', 'yards_per_touch',
            'rushing_yards_per_game', 'workhorse_score', 'pass_catching_back_score'
        ]
        
        for feature in expected_features:
            assert feature in feature_names
        
        # Should have a substantial number of features
        assert len(feature_names) > 30
    
    def test_legacy_compatibility_function(self, sample_rb_data):
        """Test that the legacy compatibility function works."""
        result = new_engineer_rb_features(sample_rb_data)
        
        # Should produce the same type of result as the class method
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert 'yards_per_carry' in result.columns
        assert 'workhorse_score' in result.columns
    
    def test_zero_touches_handling(self):
        """Test handling of RBs with zero touches."""
        data = pd.DataFrame({
            'player_id': ['RB_ZERO'],
            'player_name': ['Zero Touches RB'],
            'position': ['RB'],
            'season': [2023],
            'games': [1],
            'rushing_attempts': [0],
            'rushing_yards': [0],
            'rushing_touchdowns': [0],
            'targets': [0],
            'receptions': [0],
            'receiving_yards': [0],
            'receiving_touchdowns': [0]
        })
        
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(data)
        
        # Should handle gracefully without errors
        assert len(result) == 1
        assert result.iloc[0]['yards_per_carry'] == 0.0
        assert result.iloc[0]['yards_per_touch'] == 0.0
        assert result.iloc[0]['catch_rate'] == 0.0
    
    def test_mixed_position_data(self):
        """Test handling of data with mixed positions."""
        mixed_data = pd.DataFrame({
            'player_id': ['RB1', 'QB1', 'RB2'],
            'player_name': ['Test RB1', 'Test QB', 'Test RB2'],
            'position': ['RB', 'QB', 'RB'],
            'season': [2023, 2023, 2023],
            'games': [16, 16, 15],
            'rushing_attempts': [200, 50, 150],
            'rushing_yards': [1000, 300, 600],
            'rushing_touchdowns': [8, 3, 4],
            'targets': [50, 0, 80],
            'receptions': [40, 0, 65],
            'receiving_yards': [400, 0, 500],
            'receiving_touchdowns': [3, 0, 5]
        })
        
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(mixed_data)
        
        # Should only return RB data
        assert len(result) == 2
        assert all(result['position'] == 'RB')
        assert 'Test RB1' in result['player_name'].values
        assert 'Test RB2' in result['player_name'].values
        assert 'Test QB' not in result['player_name'].values
    
    def test_feature_values_are_numeric(self, sample_rb_data):
        """Test that all generated features have numeric values."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(sample_rb_data)
        
        # Get all generated feature columns
        generated_features = engineer.get_generated_features()
        
        for feature in generated_features:
            if feature in result.columns:
                # Check that all values are numeric
                assert pd.api.types.is_numeric_dtype(result[feature]), f"Feature {feature} is not numeric"
                
                # Check that there are no NaN values
                assert not result[feature].isna().any(), f"Feature {feature} contains NaN values"
    
    def test_high_volume_rb_classification(self, sample_rb_data):
        """Test that high-volume RBs are classified correctly."""
        engineer = RBFeatureEngineer()
        result = engineer.engineer_features(sample_rb_data)
        
        # McCaffrey (300 carries, 100 targets) should be classified as workhorse and pass-catcher
        mccaffrey_row = result[result['player_name'] == 'Christian McCaffrey'].iloc[0]
        
        assert mccaffrey_row['workhorse_score'] > 0.9
        assert mccaffrey_row['pass_catching_back_score'] > 0.7  # 100 targets / 16 games = 6.25, scaled by 8.0 = 0.78  
        assert mccaffrey_row['rb_versatility_score'] > 0.9
        
        # Henry (280 carries, 20 targets) should be workhorse but not pass-catcher
        henry_row = result[result['player_name'] == 'Derrick Henry'].iloc[0]
        
        assert henry_row['workhorse_score'] > 0.8
        assert henry_row['pass_catching_back_score'] < 0.5


if __name__ == '__main__':
    pytest.main([__file__])