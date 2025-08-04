"""
Tests for WR feature engineering migration.

This module tests the migration from legacy wr_features.py to the new
WRFeatureEngineer class, ensuring backward compatibility and correctness.
"""

import pytest
import pandas as pd
import numpy as np

# Import both old and new implementations
from src.data.feature_engineering.position.wr_features_v2 import WRFeatureEngineer, engineer_wr_features as new_engineer_wr_features


class TestWRFeaturesMigration:
    """Test suite for WR features migration."""
    
    @pytest.fixture
    def sample_wr_data(self):
        """Create sample WR data for testing."""
        return pd.DataFrame({
            'player_id': ['WR1', 'WR2', 'WR3'],
            'player_name': ['Cooper Kupp', 'Davante Adams', 'Tyreek Hill'],
            'position': ['WR', 'WR', 'WR'],
            'season': [2023, 2023, 2023],
            'games': [16, 15, 14],
            'targets': [160, 140, 120],
            'receptions': [120, 110, 85],
            'receiving_yards': [1500, 1400, 1200],
            'receiving_touchdowns': [12, 14, 8],
            'fantasy_points': [395.5, 410.2, 315.8]
        })
    
    @pytest.fixture
    def empty_wr_data(self):
        """Create empty WR data for edge case testing."""
        return pd.DataFrame(columns=[
            'player_id', 'player_name', 'position', 'season', 'games',
            'targets', 'receptions', 'receiving_yards', 'receiving_touchdowns'
        ])
    
    @pytest.fixture
    def missing_columns_data(self):
        """Create WR data with missing columns for testing robustness."""
        return pd.DataFrame({
            'player_id': ['WR1'],
            'player_name': ['Test WR'],
            'position': ['WR'],
            'season': [2023],
            'games': [16],
            'targets': [100],
            # Missing: receptions, yards, touchdowns
        })
    
    def test_wr_feature_engineer_initialization(self):
        """Test that WRFeatureEngineer initializes correctly."""
        engineer = WRFeatureEngineer()
        
        assert engineer.position == 'WR'
        assert engineer.column_mapper is not None
        assert engineer.feature_calculator is not None
        assert engineer.logger is not None
    
    def test_data_validation_valid_data(self, sample_wr_data):
        """Test data validation with valid WR data."""
        engineer = WRFeatureEngineer()
        
        assert engineer.validate_data(sample_wr_data) is True
    
    def test_data_validation_empty_data(self, empty_wr_data):
        """Test data validation with empty data."""
        engineer = WRFeatureEngineer()
        
        assert engineer.validate_data(empty_wr_data) is False
    
    def test_data_validation_missing_position_column(self, sample_wr_data):
        """Test data validation with missing position column."""
        engineer = WRFeatureEngineer()
        data_no_position = sample_wr_data.drop('position', axis=1)
        
        assert engineer.validate_data(data_no_position) is False
    
    def test_data_validation_no_wr_data(self, sample_wr_data):
        """Test data validation with no WR position data."""
        engineer = WRFeatureEngineer()
        data_no_wrs = sample_wr_data.copy()
        data_no_wrs['position'] = 'RB'  # Change all to RB
        
        assert engineer.validate_data(data_no_wrs) is False
    
    def test_feature_engineering_basic_functionality(self, sample_wr_data):
        """Test basic feature engineering functionality."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Check that result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Check that only WR data is returned
        assert len(result) == 3
        assert all(result['position'] == 'WR')
        
        # Check that key features are present
        expected_features = [
            'catch_rate', 'yards_per_reception', 'yards_per_target',
            'targets_per_game', 'receiving_yards_per_game',
            'primary_receiver_score', 'deep_threat_score'
        ]
        
        for feature in expected_features:
            assert feature in result.columns, f"Missing feature: {feature}"
    
    def test_efficiency_metrics_calculation(self, sample_wr_data):
        """Test that efficiency metrics are calculated correctly."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Test first WR (Cooper Kupp): 120 receptions / 160 targets = 75% catch rate
        assert abs(result.iloc[0]['catch_rate'] - 0.75) < 0.01
        
        # Test yards per reception: 1500 yards / 120 receptions = 12.5 YPR
        assert abs(result.iloc[0]['yards_per_reception'] - 12.5) < 0.01
        
        # Test yards per target: 1500 yards / 160 targets = 9.375 YPT
        assert abs(result.iloc[0]['yards_per_target'] - 9.375) < 0.01
        
        # Test touchdowns per reception: 12 TDs / 120 receptions = 0.1
        assert abs(result.iloc[0]['touchdowns_per_reception'] - 0.1) < 0.01
        
        # Test touchdowns per target: 12 TDs / 160 targets = 0.075
        assert abs(result.iloc[0]['touchdowns_per_target'] - 0.075) < 0.01
    
    def test_per_game_metrics_calculation(self, sample_wr_data):
        """Test that per-game metrics are calculated correctly."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Test targets per game: 160/16 = 10.0
        assert abs(result.iloc[0]['targets_per_game'] - 10.0) < 0.01
        
        # Test receptions per game: 120/16 = 7.5
        assert abs(result.iloc[0]['receptions_per_game'] - 7.5) < 0.01
        
        # Test receiving yards per game: 1500/16 = 93.75
        assert abs(result.iloc[0]['receiving_yards_per_game'] - 93.75) < 0.01
        
        # Test receiving TDs per game: 12/16 = 0.75
        assert abs(result.iloc[0]['receiving_tds_per_game'] - 0.75) < 0.01
    
    def test_role_classification_features(self, sample_wr_data):
        """Test that role classification features are calculated."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Primary receiver score should be high for Kupp (10 targets/game)
        assert result.iloc[0]['primary_receiver_score'] > 0.8
        
        # Deep threat score should be reasonable for Kupp (9.375 YPT)
        assert result.iloc[0]['deep_threat_score'] > 0.0
        
        # Possession receiver score should be high for Kupp (75% catch rate, 10 targets/game)
        assert result.iloc[0]['possession_receiver_score'] > 0.7
        
        # Versatility score should be high for Kupp
        assert result.iloc[0]['wr_versatility_score'] > 0.6
    
    def test_target_quality_calculation(self, sample_wr_data):
        """Test that target quality is calculated correctly."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Target quality combines yards per target and TD rate
        # For Kupp: (9.375 * 0.7) + (0.075 * 30) = 6.5625 + 2.25 = 8.8125
        expected_quality = (9.375 * 0.7) + (0.075 * 30)
        assert abs(result.iloc[0]['target_quality'] - expected_quality) < 0.01
    
    def test_missing_columns_handling(self, missing_columns_data):
        """Test graceful handling of missing columns."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(missing_columns_data)
        
        # Should not crash and should return some result
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        
        # Missing data columns should result in 0 values for some metrics
        assert result.iloc[0]['catch_rate'] == 0.0
        assert result.iloc[0]['yards_per_reception'] == 0.0
        assert result.iloc[0]['yards_per_target'] == 0.0
    
    def test_get_required_columns(self):
        """Test that get_required_columns returns expected columns."""
        engineer = WRFeatureEngineer()
        required_cols = engineer.get_required_columns()
        
        assert isinstance(required_cols, list)
        assert 'position' in required_cols
        assert 'games' in required_cols
    
    def test_get_generated_features(self):
        """Test that get_generated_features returns expected features."""
        engineer = WRFeatureEngineer()
        feature_names = engineer.get_generated_features()
        
        # Check that it returns a list
        assert isinstance(feature_names, list)
        
        # Check that key features are included
        expected_features = [
            'catch_rate', 'yards_per_reception', 'yards_per_target',
            'targets_per_game', 'primary_receiver_score', 'deep_threat_score'
        ]
        
        for feature in expected_features:
            assert feature in feature_names
        
        # Should have a substantial number of features
        assert len(feature_names) > 35
    
    def test_legacy_compatibility_function(self, sample_wr_data):
        """Test that the legacy compatibility function works."""
        result = new_engineer_wr_features(sample_wr_data)
        
        # Should produce the same type of result as the class method
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert 'catch_rate' in result.columns
        assert 'primary_receiver_score' in result.columns
    
    def test_zero_targets_handling(self):
        """Test handling of WRs with zero targets."""
        data = pd.DataFrame({
            'player_id': ['WR_ZERO'],
            'player_name': ['Zero Targets WR'],
            'position': ['WR'],
            'season': [2023],
            'games': [1],
            'targets': [0],
            'receptions': [0],
            'receiving_yards': [0],
            'receiving_touchdowns': [0]
        })
        
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(data)
        
        # Should handle gracefully without errors
        assert len(result) == 1
        assert result.iloc[0]['catch_rate'] == 0.0
        assert result.iloc[0]['yards_per_target'] == 0.0
        assert result.iloc[0]['touchdowns_per_target'] == 0.0
    
    def test_mixed_position_data(self):
        """Test handling of data with mixed positions."""
        mixed_data = pd.DataFrame({
            'player_id': ['WR1', 'RB1', 'WR2'],
            'player_name': ['Test WR1', 'Test RB', 'Test WR2'],
            'position': ['WR', 'RB', 'WR'],
            'season': [2023, 2023, 2023],
            'games': [16, 16, 15],
            'targets': [100, 50, 80],
            'receptions': [70, 40, 60],
            'receiving_yards': [900, 300, 700],
            'receiving_touchdowns': [6, 2, 5]
        })
        
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(mixed_data)
        
        # Should only return WR data
        assert len(result) == 2
        assert all(result['position'] == 'WR')
        assert 'Test WR1' in result['player_name'].values
        assert 'Test WR2' in result['player_name'].values
        assert 'Test RB' not in result['player_name'].values
    
    def test_feature_values_are_numeric(self, sample_wr_data):
        """Test that all generated features have numeric values."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Get all generated feature columns
        generated_features = engineer.get_generated_features()
        
        for feature in generated_features:
            if feature in result.columns:
                # Check that all values are numeric
                assert pd.api.types.is_numeric_dtype(result[feature]), f"Feature {feature} is not numeric"
                
                # Check that there are no NaN values
                assert not result[feature].isna().any(), f"Feature {feature} contains NaN values"
    
    def test_high_target_wr_classification(self, sample_wr_data):
        """Test that high-target WRs are classified correctly."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Kupp (160 targets, 120 receptions) should be classified as primary receiver
        kupp_row = result[result['player_name'] == 'Cooper Kupp'].iloc[0]
        
        assert kupp_row['primary_receiver_score'] > 0.8
        assert kupp_row['possession_receiver_score'] > 0.7
        assert kupp_row['wr_versatility_score'] > 0.6
        
        # Adams (140 targets, 110 receptions) should also be classified as primary
        adams_row = result[result['player_name'] == 'Davante Adams'].iloc[0]
        
        assert adams_row['primary_receiver_score'] > 0.7
        assert adams_row['possession_receiver_score'] > 0.6
    
    def test_efficiency_vs_volume_trade_offs(self, sample_wr_data):
        """Test that efficiency vs volume trade-offs are captured."""
        engineer = WRFeatureEngineer()
        result = engineer.engineer_features(sample_wr_data)
        
        # Hill has fewer targets but higher efficiency (per sample data)
        hill_row = result[result['player_name'] == 'Tyreek Hill'].iloc[0]
        kupp_row = result[result['player_name'] == 'Cooper Kupp'].iloc[0]
        
        # Hill should have higher yards per target due to fewer games/targets but similar yards
        # Hill: 1200 yards / 120 targets = 10.0 YPT
        # Kupp: 1500 yards / 160 targets = 9.375 YPT
        assert hill_row['yards_per_target'] > kupp_row['yards_per_target']
        
        # But Kupp should have higher volume-based scores
        assert kupp_row['primary_receiver_score'] > hill_row['primary_receiver_score']


if __name__ == '__main__':
    pytest.main([__file__])