# fantasy_football_ai_tool/src/modeling.py

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
import lightgbm as lgb
import numpy as np # Will be needed for data handling
import pandas as pd # Will be needed for data handling

class BaseModel:
    """Base class for all models."""
    def __init__(self, model_params=None):
        self.model_params = model_params if model_params is not None else {}
        self.model = None

    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        """Trains the model."""
        raise NotImplementedError("Train method not implemented.")

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        """Makes predictions with the trained model."""
        raise NotImplementedError("Predict method not implemented.")

    def get_model_name(self) -> str:
        """Returns the name of the model."""
        return self.__class__.__name__


class RandomForestModel(BaseModel):
    """Random Forest Regressor model."""
    def __init__(self, model_params=None):
        super().__init__(model_params)
        default_rf_params = {
            'n_estimators': 100,  # A common default
            'random_state': 42,
            'n_jobs': -1  # Use all available cores
        }
        # User-provided params override defaults
        merged_params = {**default_rf_params, **self.model_params}
        self.model = RandomForestRegressor(**merged_params)

    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        if self.model is None:
            # This case should ideally be prevented by __init__ always creating a model instance
            raise ValueError("Model object not initialized. Call __init__ with model_params first.")
        self.model.fit(X_train, y_train)
        print(f"{self.get_model_name()} trained.")

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        # NotFittedError will be raised by sklearn if predict is called before fit
        return self.model.predict(X_test)


class LightGBMModel(BaseModel):
    """LightGBM Regressor model."""
    def __init__(self, model_params=None):
        super().__init__(model_params)
        # Default LightGBM parameters, can be overridden by model_params
        default_lgbm_params = {
            'objective': 'regression_l1', # MAE, as RMSE can be sensitive to outliers
            'metric': 'rmse', # Evaluation metric
            'n_estimators': 1000,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 1,
            'verbose': -1,
            'n_jobs': -1,
            'seed': 42,
            'boosting_type': 'gbdt',
        }
        # Merge default with user-provided params, user params take precedence
        merged_params = {**default_lgbm_params, **self.model_params}
        self.model = lgb.LGBMRegressor(**merged_params)

    def train(self, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame = None, y_val: pd.Series = None):
        eval_set = []
        callbacks = []
        if X_val is not None and y_val is not None:
            eval_set = [(X_val, y_val)]
            callbacks.append(lgb.early_stopping(100, verbose=False))
        
        self.model.fit(
            X_train, 
            y_train, 
            eval_set=eval_set,
            callbacks=callbacks
        )
        print(f"{self.get_model_name()} trained.")

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("LightGBM model object not initialized.")
        # The predict method of LGBMRegressor will raise LightGBMError if not fitted.
        return self.model.predict(X_test)


class RidgeBaselineModel(BaseModel):
    """Ridge Regression baseline model."""
    def __init__(self, model_params=None):
        super().__init__(model_params)
        # Default Ridge parameters, can be overridden by model_params
        default_ridge_params = {
            'alpha': 1.0, # Regularization strength
            'random_state': 42
        }
        merged_params = {**default_ridge_params, **self.model_params}
        self.model = Ridge(**merged_params)

    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        self.model.fit(X_train, y_train)
        print(f"{self.get_model_name()} trained.")

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            # For sklearn models, check __dict__ for fitted attributes or use check_is_fitted
            # For simplicity here, we'll rely on the fit method being called.
            raise ValueError("Model has not been trained yet.")
        return self.model.predict(X_test)

# Placeholder for "previous year's FPPG" baseline
# This might not fit the BaseModel structure exactly as it's more of a direct lookup
# or a very simple model. For MVP, Ridge is the primary ML baseline.
class PreviousYearFPPGBaseline(BaseModel):
    def __init__(self, model_params=None):
        super().__init__(model_params)
        self.model_name = "PreviousYearFPPGBaseline"
        if model_params and 'previous_year_fppg_column' in model_params:
            self.previous_year_fppg_column = model_params['previous_year_fppg_column']
        else:
            # Provide a default or raise an error if this column is essential
            # For now, let's raise an error to make it explicit it needs to be provided.
            raise ValueError("'previous_year_fppg_column' must be provided in model_params for PreviousYearFPPGBaseline.")
        self.model = None # No underlying scikit-learn model

    def train(self, X_train: pd.DataFrame, y_train: pd.Series):
        """This baseline model does not require training."""
        pass # No training needed

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        if self.previous_year_fppg_column not in X_test.columns:
            raise ValueError(f"Column '{self.previous_year_fppg_column}' (specified as previous_year_fppg_column) not found in X_test features.")
        return X_test[self.previous_year_fppg_column].values

    # get_model_name is inherited from BaseModel if we make it inherit
    # If not inheriting, keep it. Let's make it inherit from BaseModel for consistency.
    # def get_model_name(self) -> str:
    #     return self.model_name
