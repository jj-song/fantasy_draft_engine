import pytest
import pandas as pd
import numpy as np
import re # Import re for escaping
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.training_evaluation import calculate_evaluation_metrics, perform_rolling_window_cv, ensemble_predictions, evaluate_ensembled_predictions
from src.modeling import RandomForestModel, LightGBMModel, BaseModel # Added LightGBMModel

# --- Tests for calculate_evaluation_metrics --- 

def test_calculate_evaluation_metrics_perfect_prediction():
    y_true = np.array([1, 2, 3, 4, 5])
    y_pred = np.array([1, 2, 3, 4, 5])
    metrics = calculate_evaluation_metrics(y_true, y_pred)
    assert metrics['MAE'] == 0.0
    assert metrics['RMSE'] == 0.0
    assert metrics['R2'] == 1.0

def test_calculate_evaluation_metrics_imperfect_prediction():
    y_true = np.array([1, 2, 3, 4, 5])
    y_pred = np.array([1.1, 1.8, 3.2, 3.9, 5.3])
    metrics = calculate_evaluation_metrics(y_true, y_pred)
    # Manual calculation for verification (approx)
    # MAE = (|1-1.1| + |2-1.8| + |3-3.2| + |4-3.9| + |5-5.3|) / 5 = (0.1+0.2+0.2+0.1+0.3)/5 = 0.9/5 = 0.18
    # RMSE = sqrt(((0.1^2)*5)/5) = 0.1 if all diffs were 0.1. Here it's more complex.
    # R2 will be < 1
    expected_mae = mean_absolute_error(y_true, y_pred)
    expected_rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    expected_r2 = r2_score(y_true, y_pred)
    assert metrics['MAE'] == round(expected_mae, 4)
    assert metrics['RMSE'] == round(expected_rmse, 4)
    assert metrics['R2'] == round(expected_r2, 4)
    assert metrics['R2'] < 1.0

def test_calculate_evaluation_metrics_with_negatives():
    y_true = np.array([-1, -2, 0, 1, 2])
    y_pred = np.array([-1.5, -1.5, 0.5, 0.5, 2.5])
    metrics = calculate_evaluation_metrics(y_true, y_pred)
    expected_mae = mean_absolute_error(y_true, y_pred)
    expected_rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    expected_r2 = r2_score(y_true, y_pred)
    assert metrics['MAE'] == round(expected_mae, 4)
    assert metrics['RMSE'] == round(expected_rmse, 4)
    assert metrics['R2'] == round(expected_r2, 4)

# --- Fixture for perform_rolling_window_cv tests --- 

@pytest.fixture
def sample_cv_data():
    # Create a more extensive dataset for CV testing
    data = {
        'season': [2018]*20 + [2019]*20 + [2020]*20 + [2021]*20 + [2022]*20,
        'player_id': list(range(20))*5,
        'feature1': np.random.rand(100),
        'feature2': np.random.rand(100) * 10,
        'target_points': np.random.rand(100) * 300 # Target variable
    }
    df = pd.DataFrame(data)
    # Add some variance to target based on features and season to make it somewhat predictable
    df['target_points'] = df['target_points'] + df['feature1']*10 + df['feature2']*5 + df['season']*0.1
    df.set_index('player_id', inplace=True) # Example of a meaningful index
    return df

# --- Tests for perform_rolling_window_cv --- 

def test_perform_rolling_window_cv_normal_case(sample_cv_data):
    data = sample_cv_data
    model_class = RandomForestModel
    model_params = {'n_estimators': 5, 'random_state': 42, 'min_samples_leaf': 5}
    feature_cols = ['feature1', 'feature2']
    target_col = 'target_points'
    season_col = 'season'

    results = perform_rolling_window_cv(
        data=data,
        model_class=model_class,
        model_params=model_params,
        feature_cols=feature_cols,
        target_col=target_col,
        season_col=season_col,
        min_predict_season=2019 # Predict for 2019, 2020, 2021, 2022
    )

    assert isinstance(results, dict)
    assert 'per_season_metrics' in results
    assert 'overall_metrics' in results
    assert 'all_predictions' in results

    # Check seasons predicted
    predicted_seasons = [2019, 2020, 2021, 2022]
    assert all(s in results['per_season_metrics'] for s in predicted_seasons)
    assert len(results['per_season_metrics']) == len(predicted_seasons)

    for season, metrics in results['per_season_metrics'].items():
        assert 'MAE' in metrics and 'RMSE' in metrics and 'R2' in metrics
        assert not np.isnan(metrics['MAE'])

    assert 'MAE' in results['overall_metrics']
    assert not np.isnan(results['overall_metrics']['MAE'])
    
    assert isinstance(results['all_predictions'], pd.DataFrame)
    assert not results['all_predictions'].empty
    assert 'actual_target' in results['all_predictions'].columns
    assert 'predicted_target' in results['all_predictions'].columns
    assert season_col in results['all_predictions'].columns
    assert all(f in results['all_predictions'].columns for f in feature_cols)
    # Check if original index (player_id) was added
    assert data.index.name in results['all_predictions'].columns 
    assert len(results['all_predictions']) == len(data[data[season_col] >= 2019])

def test_perform_rolling_window_cv_min_predict_season_none(sample_cv_data):
    data = sample_cv_data
    model_class = RandomForestModel
    model_params = {'n_estimators': 5, 'random_state': 42}
    feature_cols = ['feature1', 'feature2']
    target_col = 'target_points'

    results = perform_rolling_window_cv(
        data=data,
        model_class=model_class,
        model_params=model_params,
        feature_cols=feature_cols,
        target_col=target_col,
        min_predict_season=None # Should default to predicting seasons after the first
    )
    predicted_seasons = sorted(data['season'].unique())[1:]
    assert all(s in results['per_season_metrics'] for s in predicted_seasons)
    assert len(results['per_season_metrics']) == len(predicted_seasons)

def test_perform_rolling_window_cv_not_enough_seasons():
    data = pd.DataFrame({
        'season': [2020]*10,
        'feature1': np.random.rand(10),
        'target_points': np.random.rand(10)
    })
    with pytest.raises(ValueError, match="Not enough seasons for rolling window CV"):
        perform_rolling_window_cv(
            data=data, model_class=RandomForestModel, model_params={},
            feature_cols=['feature1'], target_col='target_points'
        )

def test_perform_rolling_window_cv_min_predict_season_too_high(sample_cv_data):
    data = sample_cv_data
    # Expect error because 2025 is not in the list of available seasons in sample_cv_data
    expected_min_season = 2025
    all_data_seasons = sorted(data['season'].unique())
    expected_error_msg = f"min_predict_season {expected_min_season} not found in data seasons: {all_data_seasons}"
    with pytest.raises(ValueError, match=re.escape(expected_error_msg)):
        perform_rolling_window_cv(
            data=data, model_class=RandomForestModel, model_params={},
            feature_cols=['feature1', 'feature2'], target_col='target_points',
            min_predict_season=expected_min_season # Higher than any season in data
        )

def test_perform_rolling_window_cv_min_predict_season_invalid(sample_cv_data):
    data = sample_cv_data
    with pytest.raises(ValueError, match="min_predict_season 2000 not found in data seasons"):
        perform_rolling_window_cv(
            data=data, model_class=RandomForestModel, model_params={},
            feature_cols=['feature1', 'feature2'], target_col='target_points',
            min_predict_season=2000 # Not in data
        )

def test_perform_rolling_window_cv_empty_train_fold(sample_cv_data):
    data = sample_cv_data
    # Test case where a prediction season has no prior data (e.g., min_predict_season is the first season)
    first_season = data['season'].min()
    results = perform_rolling_window_cv(
        data=data, model_class=RandomForestModel, model_params={'n_estimators': 5},
        feature_cols=['feature1', 'feature2'], target_col='target_points',
        min_predict_season=first_season
    )
    # Metrics for the first season should be NaN as no training data was available
    assert np.isnan(results['per_season_metrics'][first_season]['MAE'])
    assert np.isnan(results['per_season_metrics'][first_season]['RMSE'])
    assert np.isnan(results['per_season_metrics'][first_season]['R2'])
    # Overall metrics should still compute for other valid seasons if any
    # In this setup, all subsequent seasons will have training data
    valid_overall_metrics = [s for s in results['per_season_metrics'] if s > first_season and not np.isnan(results['per_season_metrics'][s]['MAE'])]
    if valid_overall_metrics:
         assert not np.isnan(results['overall_metrics']['MAE'])
    else: # If only first_season was attempted
        assert np.isnan(results['overall_metrics']['MAE'])

class DummyModel(BaseModel):
    """A dummy model that predicts the mean of a feature or a constant."""
    def __init__(self, model_params=None):
        super().__init__(model_params)
        self.value_to_predict = self.model_params.get('value', 0) if self.model_params else 0
        self.feature_to_use = self.model_params.get('feature', None) if self.model_params else None
        self._is_fitted = False

    def train(self, X_train, y_train):
        if self.feature_to_use and self.feature_to_use in X_train.columns:
            self.value_to_predict = X_train[self.feature_to_use].mean()
        self._is_fitted = True
        print(f"{self.get_model_name()} trained. Value to predict: {self.value_to_predict}")

    def predict(self, X_test):
        if not self._is_fitted:
            raise ValueError("DummyModel not fitted.")
        return np.full(len(X_test), self.value_to_predict)

def test_perform_rolling_window_cv_with_dummy_model(sample_cv_data):
    data = sample_cv_data
    model_class = DummyModel
    # Predict a constant value
    model_params = {'value': 5.0}
    feature_cols = ['feature1', 'feature2']
    target_col = 'target_points'

    results = perform_rolling_window_cv(
        data=data, model_class=model_class, model_params=model_params,
        feature_cols=feature_cols, target_col=target_col, min_predict_season=2020
    )
    assert 'per_season_metrics' in results
    assert 2020 in results['per_season_metrics']
    # Check if predictions are all 5.0 for a season
    preds_2020 = results['all_predictions'][results['all_predictions']['season'] == 2020]['predicted_target']
    assert np.allclose(preds_2020, 5.0)

    # Predict mean of 'feature1' from train set
    model_params_mean = {'feature': 'feature1'}
    results_mean = perform_rolling_window_cv(
        data=data, model_class=model_class, model_params=model_params_mean,
        feature_cols=feature_cols, target_col=target_col, min_predict_season=2020
    )
    assert 2020 in results_mean['per_season_metrics']
    # The predicted value for 2020 should be the mean of 'feature1' from 2018+2019 data
    train_data_for_2020 = data[data['season'] < 2020]
    expected_pred_for_2020 = train_data_for_2020['feature1'].mean()
    preds_2020_mean = results_mean['all_predictions'][results_mean['all_predictions']['season'] == 2020]['predicted_target']
    assert np.allclose(preds_2020_mean, expected_pred_for_2020)


# --- Fixtures for ensembling tests ---
@pytest.fixture
def sample_prediction_dfs_for_ensemble():
    # DataFrame 1 (Model 1)
    df1_data = {
        'season': [2020, 2020, 2021, 2021],
        'player_id': [1, 2, 1, 2],
        'actual_target': [10, 12, 15, 18],
        'predicted_target': [9, 13, 14, 17] # Model 1 predictions
    }
    df1 = pd.DataFrame(df1_data)

    # DataFrame 2 (Model 2)
    df2_data = {
        'season': [2020, 2020, 2021, 2021],
        'player_id': [1, 2, 1, 2],
        'actual_target': [10, 12, 15, 18], # Actuals must be consistent
        'predicted_target': [11, 11, 16, 19] # Model 2 predictions
    }
    df2 = pd.DataFrame(df2_data)
    return [df1, df2]

# --- Tests for ensemble_predictions --- 

def test_ensemble_predictions_basic(sample_prediction_dfs_for_ensemble):
    dfs = sample_prediction_dfs_for_ensemble
    weights = [0.5, 0.5]
    join_on_cols = ['season', 'player_id']
    
    ensembled_df = ensemble_predictions(dfs, weights, join_on_cols)

    assert isinstance(ensembled_df, pd.DataFrame)
    assert 'ensembled_prediction' in ensembled_df.columns
    assert len(ensembled_df) == 4 # Should match number of unique season-player_id pairs

    # Check calculation for a specific entry (season=2020, player_id=1)
    # Model 1 pred: 9, Model 2 pred: 11. Ensemble: (9*0.5) + (11*0.5) = 4.5 + 5.5 = 10
    entry1 = ensembled_df[(ensembled_df['season'] == 2020) & (ensembled_df['player_id'] == 1)]
    assert np.isclose(entry1['ensembled_prediction'].iloc[0], 10.0)
    assert entry1['actual_target'].iloc[0] == 10

    # Check calculation for another entry (season=2021, player_id=2)
    # Model 1 pred: 17, Model 2 pred: 19. Ensemble: (17*0.5) + (19*0.5) = 8.5 + 9.5 = 18
    entry2 = ensembled_df[(ensembled_df['season'] == 2021) & (ensembled_df['player_id'] == 2)]
    assert np.isclose(entry2['ensembled_prediction'].iloc[0], 18.0)
    assert entry2['actual_target'].iloc[0] == 18

def test_ensemble_predictions_different_weights(sample_prediction_dfs_for_ensemble):
    dfs = sample_prediction_dfs_for_ensemble
    weights = [0.7, 0.3]
    join_on_cols = ['season', 'player_id']
    ensembled_df = ensemble_predictions(dfs, weights, join_on_cols)
    
    # Check calculation for (season=2020, player_id=1)
    # Model 1 pred: 9, Model 2 pred: 11. Ensemble: (9*0.7) + (11*0.3) = 6.3 + 3.3 = 9.6
    entry1 = ensembled_df[(ensembled_df['season'] == 2020) & (ensembled_df['player_id'] == 1)]
    assert np.isclose(entry1['ensembled_prediction'].iloc[0], 9.6)

def test_ensemble_predictions_input_validation(sample_prediction_dfs_for_ensemble):
    dfs = sample_prediction_dfs_for_ensemble
    join_on_cols = ['season', 'player_id']

    with pytest.raises(ValueError, match="model_prediction_dfs list cannot be empty"):
        ensemble_predictions([], [0.5,0.5], join_on_cols)
    
    with pytest.raises(ValueError, match="Length of model_prediction_dfs and weights must be the same"):
        ensemble_predictions(dfs, [0.5], join_on_cols)

    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        ensemble_predictions(dfs, [0.4, 0.7], join_on_cols)

    # Missing column in one df
    df_missing_col = dfs[0].drop(columns=['predicted_target'])
    with pytest.raises(ValueError, match="missing one or more required columns"):
        ensemble_predictions([df_missing_col, dfs[1]], [0.5,0.5], join_on_cols)

    # Non-aligned data for join (should result in empty or error)
    df_non_aligned = dfs[0].copy()
    df_non_aligned['player_id'] = df_non_aligned['player_id'] + 10 # Make player_ids not match
    with pytest.raises(ValueError, match="Merging prediction DataFrames resulted in an empty DataFrame"):
        ensemble_predictions([df_non_aligned, dfs[1]], [0.5,0.5], join_on_cols)

# --- Tests for evaluate_ensembled_predictions --- 

@pytest.fixture
def sample_ensembled_df():
    data = {
        'season': [2020, 2020, 2021, 2021],
        'player_id': [1, 2, 1, 2],
        'actual_target': [10, 12, 15, 18],
        'ensembled_prediction': [10, 12, 15, 18] # Perfect predictions
    }
    return pd.DataFrame(data)

def test_evaluate_ensembled_predictions_perfect(sample_ensembled_df):
    results = evaluate_ensembled_predictions(sample_ensembled_df)
    assert results['overall_metrics']['MAE'] == 0.0
    assert results['overall_metrics']['RMSE'] == 0.0
    assert results['overall_metrics']['R2'] == 1.0
    assert results['per_season_metrics'][2020]['MAE'] == 0.0
    assert results['per_season_metrics'][2021]['R2'] == 1.0

def test_evaluate_ensembled_predictions_imperfect():
    data = {
        'season': [2020, 2020, 2021, 2021],
        'player_id': [1, 2, 1, 2],
        'actual_target':      [10, 12, 15, 18],
        'ensembled_prediction': [9,  13, 14, 19] 
    }
    df = pd.DataFrame(data)
    results = evaluate_ensembled_predictions(df)
    
    expected_overall_mae = mean_absolute_error(df['actual_target'], df['ensembled_prediction'])
    assert results['overall_metrics']['MAE'] == round(expected_overall_mae, 4)
    assert results['overall_metrics']['R2'] < 1.0

    # Season 2020
    s2020_actual = df[df['season']==2020]['actual_target']
    s2020_pred = df[df['season']==2020]['ensembled_prediction']
    expected_s2020_mae = mean_absolute_error(s2020_actual, s2020_pred)
    assert results['per_season_metrics'][2020]['MAE'] == round(expected_s2020_mae, 4)

def test_evaluate_ensembled_predictions_empty_df():
    empty_df = pd.DataFrame(columns=['season', 'actual_target', 'ensembled_prediction'])
    results = evaluate_ensembled_predictions(empty_df)
    assert np.isnan(results['overall_metrics']['MAE'])
    assert not results['per_season_metrics'] # Empty dict


# --- Tests for perform_rolling_window_cv with Hyperparameter Tuning ---

def test_perform_rolling_window_cv_with_tuning(sample_cv_data, capsys):
    data = sample_cv_data
    model_class = RandomForestModel
    # Base model params, some of which might be overridden by tuning
    model_params = {'random_state': 42, 'n_jobs': 1} 
    feature_cols = ['feature1', 'feature2']
    target_col = 'target_points'

    param_distributions_rf = {
        'n_estimators': [5, 10], # Small values for quick test
        'max_depth': [None, 3, 5]
    }
    search_cv_options_test = {
        'n_iter': 2, # Test fewer iterations to speed up test
        'cv': 2,     # Smaller CV folds for speed
        'random_state': 42,
        'scoring': 'neg_mean_squared_error',
        'n_jobs_search': 1 # Ensure no complex parallel processing in test
    }

    results = perform_rolling_window_cv(
        data=data,
        model_class=model_class,
        model_params=model_params,
        feature_cols=feature_cols,
        target_col=target_col,
        perform_tuning=True,
        param_distributions=param_distributions_rf,
        search_cv_options=search_cv_options_test
    )

    # Check that the main structure of results is still there
    assert 'per_season_metrics' in results
    assert 'overall_metrics' in results
    assert 'all_predictions' in results
    assert len(results['per_season_metrics']) > 0
    assert not results['all_predictions'].empty

    # Check captured stdout for evidence of tuning
    captured = capsys.readouterr()
    assert "Starting hyperparameter tuning for predicting season" in captured.out
    assert "Best params for predicting season" in captured.out
    
    # Example: Check if one of the tuned parameters is mentioned in the logs
    # This confirms that RandomizedSearchCV did its job and reported params from the distribution
    assert "'n_estimators':" in captured.out 
    # Check if a value from the distribution is present (e.g., 5 or 10 for n_estimators)
    # This is a bit fragile as it depends on the exact output of RandomizedSearchCV
    # A more robust check might involve mocking RandomizedSearchCV or inspecting model_instance params if possible
    assert ("'n_estimators': 5" in captured.out or "'n_estimators': 10" in captured.out)


def test_perform_rolling_window_cv_with_tuning_lightgbm(sample_cv_data, capsys):
    data = sample_cv_data
    model_class = LightGBMModel # Use LightGBMModel
    model_params = {'random_state': 42, 'n_jobs': 1} 
    feature_cols = ['feature1', 'feature2']
    target_col = 'target_points'

    param_distributions_lgbm = {
        'n_estimators': [5, 10],
        'learning_rate': [0.01, 0.1],
        'num_leaves': [5, 10]
    }
    search_cv_options_test = {
        'n_iter': 2, 
        'cv': 2, 
        'random_state': 42,
        'scoring': 'neg_mean_squared_error',
        'n_jobs_search': 1
    }

    results = perform_rolling_window_cv(
        data=data,
        model_class=model_class,
        model_params=model_params,
        feature_cols=feature_cols,
        target_col=target_col,
        perform_tuning=True,
        param_distributions=param_distributions_lgbm,
        search_cv_options=search_cv_options_test
    )

    assert 'per_season_metrics' in results
    assert 'overall_metrics' in results
    assert 'all_predictions' in results
    assert len(results['per_season_metrics']) > 0
    assert not results['all_predictions'].empty

    captured = capsys.readouterr()
    assert "Starting hyperparameter tuning for predicting season" in captured.out
    assert "Best params for predicting season" in captured.out
    assert "'n_estimators':" in captured.out 
    assert ("'learning_rate': 0.01" in captured.out or "'learning_rate': 0.1" in captured.out)
