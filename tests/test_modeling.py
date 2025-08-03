# fantasy_football_ai_tool/tests/test_modeling.py

import pytest
import pandas as pd
import numpy as np
from sklearn.exceptions import NotFittedError
from lightgbm.basic import LightGBMError # Attempting import from lightgbm.basic
from src.modeling import (
    RandomForestModel, 
    LightGBMModel, 
    RidgeBaselineModel,
    PreviousYearFPPGBaseline,
    BaseModel
)

# Sample data for testing model training and prediction
N_SAMPLES = 100
N_FEATURES = 5

@pytest.fixture
def sample_data():
    X = pd.DataFrame(np.random.rand(N_SAMPLES, N_FEATURES), columns=[f'feature_{i}' for i in range(N_FEATURES)])
    y = pd.Series(np.random.rand(N_SAMPLES) * 10) # Target variable, e.g., FPPG
    X_test = pd.DataFrame(np.random.rand(N_SAMPLES // 2, N_FEATURES), columns=[f'feature_{i}' for i in range(N_FEATURES)])
    X['previous_fppg'] = np.random.rand(N_SAMPLES) * 10 # For PreviousYearFPPGBaseline
    X_test['previous_fppg'] = np.random.rand(N_SAMPLES // 2) * 10
    return X, y, X_test

def test_base_model_not_implemented():
    base_model = BaseModel()
    with pytest.raises(NotImplementedError):
        base_model.train(None, None)
    with pytest.raises(NotImplementedError):
        base_model.predict(None)

@pytest.mark.parametrize("ModelClass,params", [
    (RandomForestModel, {'n_estimators': 10}),
    (LightGBMModel, {'n_estimators': 10, 'num_leaves': 5}),
    (RidgeBaselineModel, {'alpha': 0.5})
])
def test_model_instantiation_and_basic_methods(ModelClass, params, sample_data):
    """Test model instantiation, training, and prediction for ML models."""
    X_train, y_train, X_test = sample_data
    model_instance = ModelClass(model_params=params)
    
    assert model_instance.model is not None, f"{ModelClass.__name__} model not initialized."
    assert model_instance.get_model_name() == ModelClass.__name__

    # Test train method
    if ModelClass == LightGBMModel:
        model_instance.train(X_train, y_train, X_val=X_train, y_val=y_train) # LGBM can take eval_set
    else:
        model_instance.train(X_train, y_train)
    
    # Test predict method
    predictions = model_instance.predict(X_test)
    assert isinstance(predictions, np.ndarray), f"{ModelClass.__name__} predictions should be numpy array."
    assert len(predictions) == len(X_test), f"{ModelClass.__name__} predictions length mismatch."

    # Test predict before train raises error (except for models that don't require fitting like PreviousYearFPPG)
    fresh_model_instance = ModelClass(model_params=params)
    if ModelClass == RandomForestModel or ModelClass == RidgeBaselineModel:
        with pytest.raises(NotFittedError, match=r"This .* instance is not fitted yet\."):
            fresh_model_instance.predict(X_test)
    elif ModelClass == LightGBMModel:
        # Newer LightGBM versions raise NotFittedError for consistency with scikit-learn
        with pytest.raises(NotFittedError, match=r"(?i)Estimator not fitted|model is not fitted yet|booster is not initialized"):
            fresh_model_instance.predict(X_test)

def test_previous_year_fppg_baseline_instantiation_and_predict(sample_data):
    """Test PreviousYearFPPGBaseline instantiation and predict method."""
    X_train, y_train, X_test = sample_data
    fppg_col = 'previous_fppg'
    model_params = {'previous_year_fppg_column': fppg_col}
    model = PreviousYearFPPGBaseline(model_params=model_params)
    
    assert model.get_model_name() == "PreviousYearFPPGBaseline"
    assert model.previous_year_fppg_column == fppg_col

    # Test train method (should do nothing)
    model.train(X_train, y_train) # Should execute without error
    
    # Test predict method
    predictions = model.predict(X_test)
    assert isinstance(predictions, np.ndarray)
    assert len(predictions) == len(X_test)
    assert np.array_equal(predictions, X_test[fppg_col].values)

    # Test predict with missing feature column in X_test
    X_test_missing_col = X_test.drop(columns=[fppg_col])
    with pytest.raises(ValueError, match=f"Column '{fppg_col}' .* not found in X_test features."):
        model.predict(X_test_missing_col)

def test_previous_year_fppg_baseline_missing_param():
    """Test PreviousYearFPPGBaseline raises error if 'previous_year_fppg_column' is missing."""
    with pytest.raises(ValueError, match="'previous_year_fppg_column' must be provided in model_params for PreviousYearFPPGBaseline."):
        PreviousYearFPPGBaseline(model_params={}) # Empty params
    with pytest.raises(ValueError, match="'previous_year_fppg_column' must be provided in model_params for PreviousYearFPPGBaseline."):
        PreviousYearFPPGBaseline() # No params

# Example of how you might test specific model parameters or behavior later
# def test_random_forest_specific_param():
#     model = RandomForestModel(model_params={'n_estimators': 5, 'max_depth': 3})
#     assert model.model.get_params()['n_estimators'] == 5
#     assert model.model.get_params()['max_depth'] == 3
