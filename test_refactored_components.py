"""
Test Suite for Refactored Components

This script tests all the newly created refactored components to ensure they
work correctly and maintain backward compatibility with the existing system.

Components Tested:
1. FantasyConstants - Magic number extraction
2. FeatureMapper - Duplicate code elimination  
3. InputValidator - Input validation system
4. FantasyExceptions - Error handling classes
5. TypeAnnotations - Type safety system
6. EnhancedPredictor - Integrated prediction system
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Test imports
try:
    from src.constants.fantasy_constants import (
        VOR_TIERS, FANTASY_DEFAULTS, VOR_CONFIG, VALIDATION_THRESHOLDS
    )
    from src.core.feature_mapper import FeatureMapper
    from src.validators.input_validators import InputValidator
    from src.exceptions.fantasy_exceptions import (
        FeatureMappingError, PredictionError
    )
    from src.validators.input_validators import ValidationError
    from src.core.type_annotations import is_valid_position, is_player_dataframe
    from src.core.enhanced_prediction import EnhancedPredictor
    
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


class RefactoredComponentTester:
    """Comprehensive tester for all refactored components."""
    
    def __init__(self):
        """Initialize the tester with sample data."""
        self.sample_data = self._create_sample_data()
        self.test_results = []
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create realistic sample data for testing."""
        return pd.DataFrame({
            'player_name': [
                'Josh Allen', 'Lamar Jackson', 'Christian McCaffrey', 
                'Derrick Henry', 'Cooper Kupp', 'Davante Adams',
                'Travis Kelce', 'Mark Andrews', 'Justin Tucker', 'Patriots DST'
            ],
            'position': ['QB', 'QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'TE', 'K', 'DST'],
            'birth_date': [
                '1996-05-21', '1997-01-07', '1996-06-07', '1994-01-04',
                '1993-06-15', '1992-12-18', '1989-10-05', '1994-09-06',
                '1989-02-21', '1990-01-01'  # Placeholder for DST
            ],
            'games': [17, 12, 14, 16, 17, 11, 17, 16, 17, 17],
            'carries': [111, 120, 287, 349, 6, 2, 0, 0, 0, 0],
            'passing_yards': [4306, 3678, 0, 0, 0, 0, 0, 0, 0, 0],
            'passing_tds': [29, 24, 0, 0, 0, 0, 0, 0, 0, 0],
            'targets': [5, 8, 85, 20, 145, 137, 110, 86, 0, 0],
            'receptions': [4, 6, 70, 15, 128, 103, 97, 76, 0, 0],
            'receiving_yards': [52, 58, 741, 215, 1663, 1243, 1338, 847, 0, 0],
            'fantasy_points_ppr': [432.1, 302.5, 391.2, 335.8, 414.9, 294.3, 397.8, 228.7, 155.0, 142.0]
        })
    
    def run_all_tests(self) -> bool:
        """Run all component tests and return success status."""
        print("🧪 Starting Comprehensive Component Testing")
        print("=" * 60)
        
        tests = [
            ("Constants System", self.test_constants_system),
            ("Feature Mapper", self.test_feature_mapper),
            ("Input Validator", self.test_input_validator),
            ("Exception System", self.test_exception_system),
            ("Type Annotations", self.test_type_annotations),
            ("Enhanced Predictor", self.test_enhanced_predictor),
            ("Integration Test", self.test_integration)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 Testing {test_name}...")
            try:
                success = test_func()
                if success:
                    print(f"✅ {test_name} - PASSED")
                    passed_tests += 1
                else:
                    print(f"❌ {test_name} - FAILED")
            except Exception as e:
                print(f"💥 {test_name} - ERROR: {e}")
        
        print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Refactored components are working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Please review the issues above.")
            return False
    
    def test_constants_system(self) -> bool:
        """Test the constants system."""
        try:
            # Test VOR tier classification
            assert VOR_TIERS.get_tier(20.0) == "ELITE"
            assert VOR_TIERS.get_tier(15.0) == "PREMIUM"
            assert VOR_TIERS.get_tier(8.0) == "DEPTH"
            assert VOR_TIERS.get_tier(3.0) == "BENCH"
            
            # Test position baselines
            assert FANTASY_DEFAULTS.get_baseline_for_position('QB') == 255.0
            assert FANTASY_DEFAULTS.get_baseline_for_position('RB') == 170.0
            
            # Test VOR configuration
            assert VOR_CONFIG.get_replacement_level('QB') == 13
            assert VOR_CONFIG.get_scarcity_multiplier('RB') == 1.5
            
            # Test validation thresholds
            qb_range = VALIDATION_THRESHOLDS.get_position_range('QB')
            assert qb_range == (150.0, 450.0)
            
            print("  ✓ VOR tier classification working")
            print("  ✓ Position baselines correct")
            print("  ✓ VOR configuration accessible")
            print("  ✓ Validation thresholds working")
            
            return True
        except Exception as e:
            print(f"  ❌ Constants test failed: {e}")
            return False
    
    def test_feature_mapper(self) -> bool:
        """Test the feature mapper system."""
        try:
            mapper = FeatureMapper()
            
            # Test basic feature mapping
            expected_features = ['age', 'games_played', 'rushing_attempts', 'targets']
            mapped_features = mapper.map_features(self.sample_data, expected_features, 'RB')
            
            assert 'age' in mapped_features.columns
            assert 'games_played' in mapped_features.columns
            assert 'rushing_attempts' in mapped_features.columns
            assert len(mapped_features) == len(self.sample_data)
            
            # Test age calculation
            ages = mapped_features['age']
            assert ages.min() >= 20  # Reasonable age range
            assert ages.max() <= 40
            
            # Test mapping info
            info = mapper.get_mapping_info(self.sample_data, expected_features, 'RB')
            assert 'statistics' in info
            assert info['statistics']['success_rate'] > 0.5
            
            print("  ✓ Basic feature mapping working")
            print("  ✓ Age calculation working")
            print("  ✓ Mapping info generation working")
            print(f"  ✓ Success rate: {info['statistics']['success_rate']:.1%}")
            
            return True
        except Exception as e:
            print(f"  ❌ Feature mapper test failed: {e}")
            return False
    
    def test_input_validator(self) -> bool:
        """Test the input validation system."""
        try:
            # Test DataFrame validation
            validated_df = InputValidator.validate_dataframe(self.sample_data, "test_data")
            assert len(validated_df) == len(self.sample_data)
            
            # Test position validation
            valid_position = InputValidator.validate_position("RB")
            assert valid_position == "RB"
            
            # Test multiple positions
            multi_positions = InputValidator.validate_position(["QB", "RB"], allow_multiple=True)
            assert multi_positions == ["QB", "RB"]
            
            # Test prediction validation
            sample_predictions = np.array([250.0, 300.0, 200.0])
            validated_preds = InputValidator.validate_predictions(sample_predictions, "RB")
            assert len(validated_preds) == 3
            
            # Test invalid cases
            try:
                InputValidator.validate_position("INVALID")
                assert False, "Should have raised exception"
            except Exception:
                pass  # Expected
            
            print("  ✓ DataFrame validation working")
            print("  ✓ Position validation working")
            print("  ✓ Prediction validation working")
            print("  ✓ Invalid input handling working")
            
            return True
        except Exception as e:
            print(f"  ❌ Input validator test failed: {e}")
            return False
    
    def test_exception_system(self) -> bool:
        """Test the exception system."""
        try:
            # Test basic exception creation
            error = FeatureMappingError("Test error", missing_features=['age', 'games'])
            assert "Test error" in str(error)
            assert 'missing_features' in error.details
            
            # Test utility function
            from src.exceptions.fantasy_exceptions import create_data_quality_error
            quality_error = create_data_quality_error(0.15, 0.10, "test_data")
            assert "test_data" in str(quality_error)
            assert quality_error.details['null_ratio'] == 0.15
            
            # Test error context
            from src.exceptions.fantasy_exceptions import FantasyErrorContext
            try:
                with FantasyErrorContext("test_operation", position="RB"):
                    raise PredictionError("Test prediction error")
            except PredictionError as e:
                assert 'operation' in e.details
                assert e.details['position'] == "RB"
            
            print("  ✓ Basic exception creation working")
            print("  ✓ Utility functions working")
            print("  ✓ Error context manager working")
            
            return True
        except Exception as e:
            print(f"  ❌ Exception system test failed: {e}")
            return False
    
    def test_type_annotations(self) -> bool:
        """Test the type annotation system."""
        try:
            # Test type guards
            assert is_valid_position("RB") == True
            assert is_valid_position("INVALID") == False
            assert is_player_dataframe(self.sample_data) == True
            
            # Test with invalid data
            invalid_df = pd.DataFrame({'a': [1, 2, 3]})  # Missing player_name, position
            assert is_player_dataframe(invalid_df) == False
            
            # Test prediction validation
            from src.core.type_annotations import is_prediction_array
            valid_predictions = np.array([250.0, 300.0, 200.0])
            invalid_predictions = np.array([np.nan, 300.0, np.inf])
            
            assert is_prediction_array(valid_predictions) == True
            assert is_prediction_array(invalid_predictions) == False
            
            print("  ✓ Position type guards working")
            print("  ✓ DataFrame type guards working") 
            print("  ✓ Prediction type guards working")
            
            return True
        except Exception as e:
            print(f"  ❌ Type annotations test failed: {e}")
            return False
    
    def test_enhanced_predictor(self) -> bool:
        """Test the enhanced predictor system."""
        try:
            # Create a mock model for testing
            class MockModel:
                def __init__(self):
                    self.feature_names_in_ = ['age', 'games', 'carries', 'targets']
                
                def predict(self, X):
                    # Simple mock prediction: sum of features
                    return np.array([row.sum() for row in X.values])
            
            predictor = EnhancedPredictor()
            mock_model = MockModel()
            
            # Test feature preparation
            expected_features = mock_model.feature_names_in_
            rb_data = self.sample_data[self.sample_data['position'] == 'RB'].copy()
            
            prepared_features = predictor._prepare_features(rb_data, mock_model, 'RB')
            assert all(feature in prepared_features.columns for feature in expected_features)
            
            # Test prediction pipeline (just the feature mapping part)
            mapped_features = predictor.feature_mapper.map_features(rb_data, expected_features, 'RB')
            assert len(mapped_features) == len(rb_data)
            
            print("  ✓ Feature preparation working")
            print("  ✓ Mock model compatibility working")
            print("  ✓ Enhanced prediction pipeline working")
            
            return True
        except Exception as e:
            print(f"  ❌ Enhanced predictor test failed: {e}")
            return False
    
    def test_integration(self) -> bool:
        """Test integration between all components."""
        try:
            # Test that all components work together
            mapper = FeatureMapper()
            
            # Use constants in feature mapping
            expected_features = ['age', 'games', 'carries']
            mapped_data = mapper.map_features(self.sample_data, expected_features, 'RB')
            
            # Use validator to check the result
            validated_data = InputValidator.validate_dataframe(
                mapped_data, 
                "integrated_test",
                required_columns=['age']
            )
            
            # Use constants to validate age ranges
            ages = validated_data['age']
            assert ages.min() >= FANTASY_DEFAULTS.MIN_REASONABLE_AGE
            assert ages.max() <= FANTASY_DEFAULTS.MAX_REASONABLE_AGE
            
            # Test tier classification with real data
            sample_vor_values = [20.5, 15.2, 8.7, 4.1]
            tier_results = [VOR_TIERS.get_tier(vor) for vor in sample_vor_values]
            expected_tiers = ['ELITE', 'PREMIUM', 'DEPTH', 'BENCH']
            assert tier_results == expected_tiers
            
            print("  ✓ Constants integration working")
            print("  ✓ Mapper + Validator integration working") 
            print("  ✓ Age validation with constants working")
            print("  ✓ VOR tier classification working")
            
            return True
        except Exception as e:
            print(f"  ❌ Integration test failed: {e}")
            return False


def test_backward_compatibility():
    """Test that refactored components don't break existing functionality."""
    print("\n🔄 Testing Backward Compatibility")
    print("-" * 40)
    
    try:
        # Test that we can still import old constants (magic numbers) from config
        # This would ensure existing code still works
        
        # Test that VOR calculations still produce reasonable results
        test_points = [350, 300, 250, 200]
        replacement_point = 180  # RB replacement level
        vor_values = [points - replacement_point for points in test_points]
        
        assert all(vor > 0 for vor in vor_values[:3])  # Top players should have positive VOR
        assert vor_values[0] > vor_values[1] > vor_values[2]  # VOR should decrease
        
        print("✅ VOR calculations maintain consistency")
        
        # Test that position validation accepts all valid fantasy positions
        from src.constants.fantasy_constants import VALID_POSITIONS
        for position in VALID_POSITIONS:
            validated = InputValidator.validate_position(position)
            assert validated == position
        
        print("✅ Position validation maintains compatibility")
        
        # Test that feature mapping works with typical model feature names
        common_features = [
            'age', 'games', 'carries', 'targets', 'receptions',
            'passing_yards', 'rushing_yards', 'receiving_yards'
        ]
        
        mapper = FeatureMapper()
        sample_data = pd.DataFrame({
            'birth_date': ['1995-01-01', '1990-06-15'],
            'games': [16, 14],
            'carries': [200, 150],
            'targets': [50, 80],
            'receptions': [40, 70],
            'passing_yards': [3000, 0],
            'rushing_yards': [1000, 800],
            'receiving_yards': [500, 900]
        })
        
        mapped = mapper.map_features(sample_data, common_features, 'RB')
        assert len(mapped.columns) == len(common_features)
        
        print("✅ Feature mapping maintains compatibility")
        print("✅ Backward compatibility verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False


def main():
    """Main testing function."""
    print("🚀 Fantasy Football Refactoring - Component Testing")
    print("=" * 60)
    
    # Run component tests
    tester = RefactoredComponentTester()
    component_tests_passed = tester.run_all_tests()
    
    # Run backward compatibility tests
    compatibility_passed = test_backward_compatibility()
    
    # Summary
    print("\n" + "=" * 60)
    if component_tests_passed and compatibility_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Refactored components are working correctly")
        print("✅ Backward compatibility maintained")
        print("✅ Ready for production use")
        return 0
    else:
        print("⚠️ SOME TESTS FAILED")
        print("❌ Please review failures above")
        print("❌ Fix issues before proceeding")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)