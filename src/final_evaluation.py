"""
Runs the final model evaluation pipeline.

This script loads data (currently placeholder), defines configurations for various models
(RandomForest, LightGBM, RidgeBaseline, PreviousYearFPPGBaseline), performs rolling
window cross-validation with hyperparameter tuning for specified models, evaluates
an ensemble of RandomForest and LightGBM, and prints a summary of performance metrics
(MAE, RMSE, R²) for all models.

To run: `python -m src.final_evaluation` from the `fantasy_football_ai_tool` directory.
"""
import pandas as pd
import numpy as np

from src.modeling import (
    RandomForestModel,
    LightGBMModel,
    RidgeBaselineModel,
    PreviousYearFPPGBaseline
)
from src.training_evaluation import (
    perform_rolling_window_cv,
    ensemble_predictions,
    evaluate_ensembled_predictions
)

# Placeholder for actual data loading and preprocessing
def load_and_prepare_data():
    """Simulates loading and preparing data for modeling."""
    # This data structure should be similar to what sample_cv_data provides in tests
    # Including 'player_id', 'season', features, 'target_points', and 'previous_fppg'
    data = {
        'player_id': np.repeat(np.arange(20), 5), # 20 players, 5 seasons each
        'season': np.tile(np.arange(2018, 2023), 20),
        'feature1': np.random.rand(100),
        'feature2': np.random.randn(100) * 10,
        'previous_fppg': np.random.rand(100) * 20, # Previous year's FPPG for baseline
        'target_points': np.random.rand(100) * 300 # Target: next season's FPPG
    }
    df = pd.DataFrame(data)
    # Ensure player_id is string for consistency if it's used as index elsewhere
    df['player_id'] = df['player_id'].astype(str)
    df = df.set_index(['player_id', 'season'])
    df.sort_index(inplace=True)
    # For rolling window, ensure 'season' is also a column
    df.reset_index(inplace=True)
    return df

def run_final_evaluation():
    """Runs the final evaluation pipeline for all models."""
    print("Starting Final Model Evaluation...")
    data = load_and_prepare_data()

    feature_cols = ['feature1', 'feature2'] # Core features for ML models
    # Note: 'previous_fppg' will be in data and accessible by PreviousYearFPPGBaseline
    # even if not in this core feature_cols list for other models.
    target_col = 'target_points'
    season_col = 'season'
    # Determine the first season to predict; requires at least one prior season for training.
    min_predict_season = data[season_col].unique()[1] if len(data[season_col].unique()) > 1 else data[season_col].min()

    all_model_results = {}

    # --- Model Configurations ---
    # RandomizedSearchCV options (kept small for quick runs, expand for real tuning)
    search_cv_options = {
        'n_iter': 5, 
        'cv': 2, # Inner CV folds for tuning
        'random_state': 42,
        'scoring': 'neg_mean_squared_error',
        'n_jobs_search': 1
    }

    # 1. Random Forest (Tuned)
    print("\n--- Evaluating RandomForestModel (Tuned) ---")
    rf_params = {'random_state': 42, 'n_jobs': 1}
    rf_param_dist = {
        'n_estimators': [50, 100],
        'max_depth': [None, 10, 20],
        'min_samples_split': [2, 5],
        'min_samples_leaf': [1, 2]
    }
    rf_results = perform_rolling_window_cv(
        data=data.copy(), model_class=RandomForestModel, model_params=rf_params,
        feature_cols=feature_cols, target_col=target_col, season_col=season_col,
        min_predict_season=min_predict_season,
        perform_tuning=True, param_distributions=rf_param_dist, search_cv_options=search_cv_options
    )
    all_model_results['RandomForest_Tuned'] = rf_results['overall_metrics']
    rf_predictions_df = rf_results['all_predictions']
    print("RandomForest (Tuned) Overall Metrics:", rf_results['overall_metrics'])

    # 2. LightGBM (Tuned)
    print("\n--- Evaluating LightGBMModel (Tuned) ---")
    lgbm_params = {'random_state': 42, 'n_jobs': 1, 'verbose': -1} # verbose -1 to suppress LightGBM output
    lgbm_param_dist = {
        'n_estimators': [50, 100],
        'learning_rate': [0.01, 0.05, 0.1],
        'num_leaves': [10, 20, 31],
        'max_depth': [-1, 10, 20]
    }
    lgbm_results = perform_rolling_window_cv(
        data=data.copy(), model_class=LightGBMModel, model_params=lgbm_params,
        feature_cols=feature_cols, target_col=target_col, season_col=season_col,
        min_predict_season=min_predict_season,
        perform_tuning=True, param_distributions=lgbm_param_dist, search_cv_options=search_cv_options
    )
    all_model_results['LightGBM_Tuned'] = lgbm_results['overall_metrics']
    lgbm_predictions_df = lgbm_results['all_predictions']
    print("LightGBM (Tuned) Overall Metrics:", lgbm_results['overall_metrics'])

    # 3. Ensemble (Random Forest + LightGBM)
    print("\n--- Evaluating Ensemble (RF + LGBM) ---")
    if not rf_predictions_df.empty and not lgbm_predictions_df.empty:
        ensemble_pred_df = ensemble_predictions(
            model_prediction_dfs=[rf_predictions_df, lgbm_predictions_df],
            weights=[0.5, 0.5],
            join_on_cols=['player_id', season_col], # Use season_col variable
            actual_target_col=target_col, 
            model_pred_col='prediction'
        )
        ensemble_metrics = evaluate_ensembled_predictions(
            ensembled_preds_df=ensemble_pred_df, # Corrected DataFrame argument name
            actual_target_col=target_col,       # Corrected actual target column argument name
            ensembled_pred_col='ensembled_prediction', # Corrected prediction column argument name
            season_col=season_col
        )
        all_model_results['Ensemble_RF_LGBM'] = ensemble_metrics['overall_metrics']
        print("Ensemble (RF+LGBM) Overall Metrics:", ensemble_metrics['overall_metrics'])
    else:
        print("Skipping ensemble evaluation due to empty predictions from base models.")
        all_model_results['Ensemble_RF_LGBM'] = {'MAE': np.nan, 'RMSE': np.nan, 'R2': np.nan}

    # 4. Ridge Baseline
    print("\n--- Evaluating RidgeBaselineModel ---")
    ridge_params = {'random_state': 42}
    ridge_results = perform_rolling_window_cv(
        data=data.copy(), model_class=RidgeBaselineModel, model_params=ridge_params,
        feature_cols=feature_cols, target_col=target_col, season_col=season_col,
        min_predict_season=min_predict_season,
        perform_tuning=False # No tuning for Ridge baseline in this setup
    )
    all_model_results['RidgeBaseline'] = ridge_results['overall_metrics']
    print("RidgeBaseline Overall Metrics:", ridge_results['overall_metrics'])

    # 5. Previous Year FPPG Baseline
    print("\n--- Evaluating PreviousYearFPPGBaseline ---")
    prev_fppg_col_name = 'previous_fppg'
    # Ensure this column is in data and used as a feature by the baseline
    # The `perform_rolling_window_cv` will pass all columns of `data` to the model's predict method
    # if `feature_cols` is used for slicing X_train/X_test for other models.
    # The baseline itself picks the 'previous_fppg' column from X_test.
    prev_year_params = {'previous_year_fppg_column': prev_fppg_col_name}
    prev_year_results = perform_rolling_window_cv(
        data=data.copy(), # Pass the full data, baseline will select its 'feature'
        model_class=PreviousYearFPPGBaseline, 
        model_params=prev_year_params,
        feature_cols=feature_cols, # These are for standard models, baseline ignores them
        target_col=target_col, 
        season_col=season_col,
        min_predict_season=min_predict_season,
        perform_tuning=False
    )
    all_model_results['PreviousYearFPPG'] = prev_year_results['overall_metrics']
    print("PreviousYearFPPG Overall Metrics:", prev_year_results['overall_metrics'])

    # --- Summary of Results ---
    print("\n--- Final Model Evaluation Summary ---")
    summary_df = pd.DataFrame(all_model_results).T # Transpose for models as rows
    print(summary_df)

if __name__ == "__main__":
    run_final_evaluation()
