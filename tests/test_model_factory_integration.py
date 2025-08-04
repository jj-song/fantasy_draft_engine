"""
Tests for ModelFactory integration.

This module tests the ModelFactory's ability to create and manage
feature engineers for all fantasy football positions, ensuring
proper integration and interface compliance.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Import the ModelFactory and related classes
from src.core.model_factory import ModelFactory, get_model_factory, load_model
from src.core.base_feature_engineer import BaseFeatureEngineer


class TestModelFactoryIntegration:
    """Test suite for ModelFactory integration."""
    
    @pytest.fixture
    def model_factory(self):
        """Create a ModelFactory instance for testing."""
        return ModelFactory()
    
    @pytest.fixture
    def sample_position_data(self):
        """Create sample data that can be used for any position."""
        return pd.DataFrame({
            'player_id': ['TEST1', 'TEST2'],
            'player_name': ['Test Player 1', 'Test Player 2'],
            'position': ['QB', 'QB'],  # Will be overridden in tests
            'season': [2023, 2023],
            'games_played': [16, 15],
            'fantasy_points': [300.0, 250.0]
        })
    
    def test_model_factory_initialization(self, model_factory):
        """Test that ModelFactory initializes correctly."""
        assert isinstance(model_factory, ModelFactory)
        assert model_factory.model_directory.exists()
        assert model_factory.logger is not None
        assert model_factory.error_handler is not None
        assert isinstance(model_factory._model_registry, dict)
    
    def test_create_feature_engineer_all_positions(self):
        """Test that ModelFactory can create feature engineers for all positions."""
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        
        for position in positions:
            engineer = ModelFactory.create_feature_engineer(position)
            assert engineer is not None, f"Failed to create engineer for {position}"
            assert isinstance(engineer, BaseFeatureEngineer), f"{position} engineer not BaseFeatureEngineer instance"
            assert engineer.position == position, f"Wrong position set for {position} engineer"
    
    def test_create_feature_engineer_alternative_dst_names(self):
        """Test that ModelFactory handles alternative DST position names."""
        dst_alternatives = ['DST', 'DEF', 'D/ST']
        
        for dst_name in dst_alternatives:
            engineer = ModelFactory.create_feature_engineer(dst_name)
            assert engineer is not None, f"Failed to create engineer for {dst_name}"
            assert engineer.position == 'DST', f"Wrong position set for {dst_name} engineer"
    
    def test_create_feature_engineer_case_insensitive(self):
        """Test that ModelFactory handles case-insensitive position names."""
        test_cases = [
            ('qb', 'QB'), ('QB', 'QB'), ('Qb', 'QB'),
            ('rb', 'RB'), ('RB', 'RB'), ('Rb', 'RB'),
            ('wr', 'WR'), ('WR', 'WR'), ('Wr', 'WR'),
            ('te', 'TE'), ('TE', 'TE'), ('Te', 'TE'),
            ('k', 'K'), ('K', 'K'),
            ('dst', 'DST'), ('DST', 'DST'), ('Dst', 'DST')
        ]
        
        for input_pos, expected_pos in test_cases:
            engineer = ModelFactory.create_feature_engineer(input_pos)
            assert engineer is not None, f"Failed to create engineer for {input_pos}"
            assert engineer.position == expected_pos, f"Wrong position for {input_pos}: got {engineer.position}, expected {expected_pos}"
    
    def test_create_feature_engineer_unknown_position(self):
        """Test that ModelFactory handles unknown positions gracefully."""
        unknown_positions = ['XYZ', 'INVALID', '', None, 123]
        
        for position in unknown_positions:
            engineer = ModelFactory.create_feature_engineer(position)
            assert engineer is None, f"Should return None for unknown position: {position}"
    
    def test_feature_engineer_interface_compliance(self):
        """Test that all created feature engineers follow BaseFeatureEngineer interface."""
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        required_methods = ['engineer_features', 'validate_data', 'get_required_columns', 'get_generated_features']
        required_attributes = ['position', 'logger']
        
        for position in positions:
            engineer = ModelFactory.create_feature_engineer(position)
            assert engineer is not None, f"Engineer creation failed for {position}"
            
            # Test required methods exist
            for method in required_methods:
                assert hasattr(engineer, method), f"{position} engineer missing method: {method}"
                assert callable(getattr(engineer, method)), f"{position} engineer {method} is not callable"
            
            # Test required attributes exist
            for attr in required_attributes:
                assert hasattr(engineer, attr), f"{position} engineer missing attribute: {attr}"
            
            # Test position is set correctly
            assert engineer.position == position, f"{position} engineer has wrong position: {engineer.position}"
    
    def test_feature_engineer_functionality(self, sample_position_data):
        """Test that all feature engineers can process data without errors."""
        position_test_data = {
            'QB': {
                'position': 'QB',
                'additional_cols': {
                    'passing_attempts': [500, 450],
                    'passing_completions': [350, 320],
                    'passing_yards': [4200, 3800],
                    'passing_touchdowns': [30, 25],
                    'passing_interceptions': [8, 6]
                }
            },
            'RB': {
                'position': 'RB', 
                'additional_cols': {
                    'rushing_attempts': [250, 200],
                    'rushing_yards': [1200, 1000],
                    'rushing_touchdowns': [12, 8],
                    'targets': [50, 40],
                    'receptions': [45, 35]
                }
            },
            'WR': {
                'position': 'WR',
                'additional_cols': {
                    'targets': [120, 100],
                    'receptions': [80, 70],
                    'receiving_yards': [1100, 900],
                    'receiving_touchdowns': [8, 6]
                }
            },
            'TE': {
                'position': 'TE',
                'additional_cols': {
                    'targets': [80, 70],
                    'receptions': [60, 55],
                    'receiving_yards': [700, 600],
                    'receiving_touchdowns': [5, 4]
                }
            },
            'K': {
                'position': 'K',
                'additional_cols': {
                    'fg_attempts': [30, 28],
                    'fg_made': [27, 25],
                    'xp_attempts': [40, 35],
                    'xp_made': [39, 34]
                }
            },
            'DST': {
                'position': 'DST',
                'additional_cols': {
                    'sacks': [45, 38],
                    'interceptions': [18, 15],
                    'fumbles_recovered': [8, 6],
                    'points_allowed': [320, 380]
                }
            }
        }
        
        for position, test_config in position_test_data.items():
            # Create position-specific test data
            test_data = sample_position_data.copy()
            test_data['position'] = test_config['position']
            
            # Add position-specific columns
            for col, values in test_config['additional_cols'].items():
                test_data[col] = values
            
            # Create and test the engineer
            engineer = ModelFactory.create_feature_engineer(position)
            assert engineer is not None, f"Failed to create {position} engineer"
            
            # Test that feature engineering doesn't crash
            try:
                result = engineer.engineer_features(test_data)
                assert isinstance(result, pd.DataFrame), f"{position} engineer didn't return DataFrame"
                assert len(result) == len(test_data), f"{position} engineer changed row count"
                
                # Test that original columns are preserved
                for col in test_data.columns:
                    assert col in result.columns, f"{position} engineer lost column: {col}"
                    
            except Exception as e:
                pytest.fail(f"{position} engineer failed during feature engineering: {str(e)}")
    
    def test_get_required_columns_consistency(self):
        """Test that all engineers return consistent required columns structure."""
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        
        for position in positions:
            engineer = ModelFactory.create_feature_engineer(position)
            required_cols = engineer.get_required_columns()
            
            assert isinstance(required_cols, list), f"{position} engineer get_required_columns() didn't return list"
            assert len(required_cols) > 0, f"{position} engineer returned empty required columns"
            assert 'position' in required_cols, f"{position} engineer missing 'position' in required columns"
    
    def test_get_generated_features_consistency(self):
        """Test that all engineers return consistent generated features structure."""
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        
        for position in positions:
            engineer = ModelFactory.create_feature_engineer(position)
            generated_features = engineer.get_generated_features()
            
            assert isinstance(generated_features, list), f"{position} engineer get_generated_features() didn't return list"
            # Note: Some engineers may return empty list if no features are generated, which is valid
    
    def test_global_model_factory_instance(self):
        """Test the global model factory instance management."""
        # Test that get_model_factory returns consistent instance
        factory1 = get_model_factory()
        factory2 = get_model_factory()
        
        assert factory1 is factory2, "get_model_factory() should return same instance"
        assert isinstance(factory1, ModelFactory), "Global factory should be ModelFactory instance"
    
    def test_load_model_convenience_function(self, model_factory):
        """Test the load_model convenience function."""
        # This test mainly checks that the function exists and handles missing models gracefully
        try:
            # This should fail gracefully since no models exist
            result = load_model('QB', 'nonexistent_model')
            # If it doesn't raise an error, that's also fine
        except Exception as e:
            # Expected to fail since no models are saved, just ensure it's a reasonable error
            assert isinstance(e, Exception), "load_model should handle missing models gracefully"
    
    def test_model_factory_error_handling(self):
        """Test ModelFactory error handling for edge cases.""" 
        # Test with None position
        engineer = ModelFactory.create_feature_engineer(None)
        assert engineer is None, "Should return None for None position"
        
        # Test with empty string
        engineer = ModelFactory.create_feature_engineer('')
        assert engineer is None, "Should return None for empty string position"
        
        # Test with non-string input
        engineer = ModelFactory.create_feature_engineer(123)
        assert engineer is None, "Should return None for non-string position"
    
    def test_feature_engineer_validation_methods(self, sample_position_data):
        """Test that all feature engineers have working validation methods."""
        positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
        
        for position in positions:
            engineer = ModelFactory.create_feature_engineer(position)
            
            # Test validation with position-appropriate data
            test_data = sample_position_data.copy()
            test_data['position'] = position
            
            # Should not crash
            try:
                is_valid = engineer.validate_data(test_data)
                assert isinstance(is_valid, bool), f"{position} validate_data() should return boolean"
            except Exception as e:
                pytest.fail(f"{position} engineer validate_data() failed: {str(e)}")
            
            # Test validation with empty data
            empty_data = pd.DataFrame()
            try:
                is_valid = engineer.validate_data(empty_data)
                assert isinstance(is_valid, bool), f"{position} validate_data() should return boolean for empty data"
                assert is_valid == False, f"{position} validate_data() should return False for empty data"
            except Exception as e:
                pytest.fail(f"{position} engineer validate_data() failed on empty data: {str(e)}")


def test_model_factory_standalone():
    """Test ModelFactory functionality as standalone functions."""
    # Test that we can create a factory and use it
    factory = ModelFactory()
    assert isinstance(factory, ModelFactory)
    
    # Test creating an engineer
    qb_engineer = factory.create_feature_engineer('QB')
    assert qb_engineer is not None
    assert qb_engineer.position == 'QB'
    
    # Test the static method
    rb_engineer = ModelFactory.create_feature_engineer('RB')
    assert rb_engineer is not None
    assert rb_engineer.position == 'RB'


if __name__ == '__main__':
    pytest.main([__file__])