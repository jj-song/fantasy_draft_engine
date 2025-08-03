"""
Provides core functions for model training, evaluation, and ensembling.

This module includes:
- `calculate_evaluation_metrics`: Computes MAE, RMSE, and R2.
- `perform_rolling_window_cv`: Implements rolling window cross-validation with optional
  hyperparameter tuning (using RandomizedSearchCV) and generates per-season and overall
  performance metrics, along with prediction DataFrames.
- `ensemble_predictions`: Combines predictions from multiple models using a weighted average.
- `evaluate_ensembled_predictions`: Calculates metrics for ensembled predictions.

These functions are designed to be used by higher-level scripts like `final_evaluation.py`.
"""
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV
import warnings
# Assuming src is in PYTHONPATH, allowing direct import from src.modeling
from src.modeling import RandomForestModel # Example, will be passed as arg
from src.modeling import PreviousYearFPPGBaseline # Import for type checking

def calculate_evaluation_metrics(y_true, y_pred):
    """Calculates MAE, RMSE, and R2."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {'MAE': round(mae, 4), 'RMSE': round(rmse, 4), 'R2': round(r2, 4)}

def perform_rolling_window_cv(
    data: pd.DataFrame,
    model_class, # e.g., RandomForestModel from src.modeling
    model_params: dict,
    feature_cols: list,
    target_col: str,
    season_col: str = 'season',
    min_predict_season: int = None,
    perform_tuning: bool = False,
    param_distributions: dict = None,
    search_cv_options: dict = None
):
    """
    Performs rolling window cross-validation.

    Args:
        data (pd.DataFrame): DataFrame containing features, target, and season column.
        model_class: The model class to instantiate (e.g., RandomForestModel).
        model_params (dict): Base parameters for the model. If tuning, these can be overridden by tuned parameters.
        feature_cols (list): List of feature column names.
        target_col (str): Name of the target column.
        season_col (str): Name of the column indicating the season.
        min_predict_season (int, optional): The first season for which predictions are made.
                                            Training data will be all seasons *before* this.
                                            If None, inferred: predicts for all seasons after the first.
        perform_tuning (bool): Whether to perform hyperparameter tuning. Defaults to False.
        param_distributions (dict, optional): Parameter distributions for RandomizedSearchCV.
                                            Required if perform_tuning is True.
        search_cv_options (dict, optional): Options for RandomizedSearchCV 
                                            (e.g., n_iter, cv, scoring, random_state, n_jobs_search).

    Returns:
        dict: Contains per-season metrics, overall metrics, and all predictions.
    """
    all_seasons = sorted(data[season_col].unique())
    
    if not all_seasons:
        raise ValueError("No seasons found in data.")

    if min_predict_season is None:
        if len(all_seasons) < 2:
            raise ValueError("Not enough seasons for rolling window CV. Need at least 2 (1 for train, 1 for test).")
        min_predict_season = all_seasons[1]
    elif min_predict_season not in all_seasons:
        raise ValueError(f"min_predict_season {min_predict_season} not found in data seasons: {all_seasons}")
    
    predict_seasons = [s for s in all_seasons if s >= min_predict_season]
    if not predict_seasons:
        # This case should ideally be caught by min_predict_season check or len(all_seasons) < 2
        raise ValueError(f"No seasons available to predict for. min_predict_season: {min_predict_season}, all_seasons: {all_seasons}")

    per_season_metrics = {}
    all_true_values_list = []
    all_predicted_values_list = []
    all_predictions_df_list = []

    print(f"Starting rolling window CV. Predicting for seasons: {predict_seasons}\n")

    for current_predict_season in predict_seasons:
        print(f"-- Processing prediction for season: {current_predict_season} --")
        train_data = data[data[season_col] < current_predict_season].copy()
        test_data = data[data[season_col] == current_predict_season].copy()

        if train_data.empty:
            print(f"Warning: No training data available for seasons < {current_predict_season}. Skipping prediction for {current_predict_season}.")
            per_season_metrics[current_predict_season] = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}
            continue
        
        if test_data.empty: # Should not happen if current_predict_season is in predict_seasons
            print(f"Warning: No test data found for season {current_predict_season}. Skipping.")
            continue

        X_train = train_data[feature_cols]
        y_train = train_data[target_col]
        X_test = test_data[feature_cols]
        y_test = test_data[target_col]

        # Special handling for PreviousYearFPPGBaseline to ensure it gets its specific column
        # This assumes model_class has a __name__ attribute or similar for identification
        if hasattr(model_class, '__name__') and model_class.__name__ == 'PreviousYearFPPGBaseline':
            if model_params and 'previous_year_fppg_column' in model_params:
                prev_fppg_col = model_params['previous_year_fppg_column']
                if prev_fppg_col not in X_test.columns and prev_fppg_col in test_data.columns:
                    # Add the required column to X_test if it's not already there
                    # This happens if prev_fppg_col is not in the main feature_cols
                    X_test = test_data[X_test.columns.tolist() + [prev_fppg_col]].copy()
                elif prev_fppg_col not in test_data.columns:
                    raise ValueError(f"PreviousYearFPPGBaseline's required column '{prev_fppg_col}' not found in test_data.")

        if X_train.empty or y_train.empty:
             print(f"Warning: Training data (features or target) is empty for predicting season {current_predict_season}. Skipping.")
             per_season_metrics[current_predict_season] = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}
             continue
        
        print(f"Training model using data from {len(train_data[season_col].unique())} season(s) (up to {train_data[season_col].max()}) to predict for {current_predict_season}...")
        
        current_fold_model_params = model_params.copy()

        if perform_tuning and param_distributions:
            if not search_cv_options:
                search_cv_options = {
                    'n_iter': 10, 
                    'cv': 3, 
                    'random_state': 42, 
                    'scoring': 'neg_mean_squared_error',
                    'n_jobs_search': 1 # n_jobs for RandomizedSearchCV itself
                }
            
            # The estimator for RandomizedSearchCV should be the raw scikit-learn compatible model.
            # Our model wrapper classes (e.g., RandomForestModel) are expected to expose the underlying
            # scikit-learn model via a `.model` attribute for this purpose.
            # Initialize a base model from model_class for the search.
            # The model_params passed to perform_rolling_window_cv can serve as fixed params
            # if they are not in param_distributions, or as initial points if the search algo uses them.
            # For RandomizedSearchCV, it picks from distributions, so model_params are more like fixed settings.
            base_estimator_for_search = model_class(model_params=current_fold_model_params).model

            search = RandomizedSearchCV(
                estimator=base_estimator_for_search,
                param_distributions=param_distributions,
                n_iter=search_cv_options.get('n_iter', 10),
                cv=search_cv_options.get('cv', 3),
                scoring=search_cv_options.get('scoring', 'neg_mean_squared_error'),
                random_state=search_cv_options.get('random_state', 42),
                n_jobs=search_cv_options.get('n_jobs_search', 1)
            )
            
            print(f"  Starting hyperparameter tuning for predicting season {current_predict_season}...")
            search.fit(X_train, y_train)
            best_fold_params = search.best_params_
            print(f"  Best params for predicting season {current_predict_season} (trained on seasons up to {train_data[season_col].max()}): {best_fold_params}")
            
            # Update current_fold_model_params with the best params found, overriding any conflicts
            current_fold_model_params.update(best_fold_params)
        
        model_instance = model_class(model_params=current_fold_model_params)
        model_instance.train(X_train, y_train) # Train on the full training data for this fold

        # Make predictions
        predictions = model_instance.predict(X_test)
        
        metrics = calculate_evaluation_metrics(y_test, predictions)
        per_season_metrics[current_predict_season] = metrics
        print(f"Season {current_predict_season} Metrics: MAE={metrics['MAE']:.4f}, RMSE={metrics['RMSE']:.4f}, R2={metrics['R2']:.4f}")

        all_true_values_list.extend(y_test.values)
        all_predicted_values_list.extend(predictions)
        
        # Construct DataFrame with predictions and actuals for the current season.
        # This DataFrame must include 'player_id' (or equivalent unique identifier)
        # and the 'season_col' for correct ensembling and detailed analysis later.
        # The target column is renamed to `target_col` (e.g. 'target_points') and predictions to 'prediction'.
        if 'player_id' not in test_data.columns: # Check if 'player_id' is a regular column
            # This might happen if player_id was an index and not reset, or not present.
            # For robustness, try to get it from index if it's named 'player_id'
            if test_data.index.name == 'player_id': # Check if 'player_id' is the index name
                season_preds_df = pd.DataFrame({
                    'player_id': test_data.index,
                    season_col: test_data[season_col].values,
                    target_col: y_test.values,
                    'prediction': predictions
                })
            else:
                # If 'player_id' is not found as a column or as the index name, it's problematic for ensembling.
                # The code proceeds but issues a warning. The resulting DataFrame will lack 'player_id'.
                # An 'original_index' column is added if the index seems meaningful (not a default RangeIndex)
                # to aid potential debugging or manual alignment if 'player_id' is missing.
                print("Warning: 'player_id' column not found directly in test_data columns or as index name. Ensembling might be affected.")
                season_preds_df = pd.DataFrame({
                    season_col: test_data[season_col].values,
                    target_col: y_test.values,
                    'prediction': predictions
                })
                # Add original index if player_id is missing, for potential manual inspection
                if not test_data.index.equals(pd.RangeIndex(start=0, stop=len(test_data.index), step=1)):
                    try:
                        season_preds_df['original_index'] = test_data.index.values
                    except Exception as e:
                         print(f"Could not automatically add original index: {e}")

        else: # 'player_id' is in test_data.columns
            season_preds_df = test_data[['player_id', season_col]].copy()
            season_preds_df[target_col] = y_test.values
            season_preds_df['prediction'] = predictions

        all_predictions_df_list.append(season_preds_df)
        print("-- End processing for season: {current_predict_season} --\n")

    overall_metrics = {}
    if all_true_values_list and all_predicted_values_list:
        valid_indices = ~np.isnan(all_predicted_values_list) # Ensure no NaNs if a season was skipped for preds
        y_true_overall = np.array(all_true_values_list)[valid_indices]
        y_pred_overall = np.array(all_predicted_values_list)[valid_indices]
        if len(y_true_overall) > 0:
            overall_metrics = calculate_evaluation_metrics(y_true_overall, y_pred_overall)
            print(f"Overall Metrics (across all predicted seasons): MAE={overall_metrics['MAE']:.4f}, RMSE={overall_metrics['RMSE']:.4f}, R2={overall_metrics['R2']:.4f}")
        else:
            print("No predictions were made across all seasons, cannot compute overall metrics.")
            overall_metrics = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}
    else:
        print("No predictions available to compute overall metrics.")
        overall_metrics = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}

    all_predictions_df = pd.DataFrame()
    if all_predictions_df_list:
        all_predictions_df = pd.concat(all_predictions_df_list, ignore_index=True)

    return {
        'per_season_metrics': per_season_metrics,
        'overall_metrics': overall_metrics,
        'all_predictions': all_predictions_df
    }

def ensemble_predictions(
    model_prediction_dfs: list[pd.DataFrame],
    weights: list[float],
    join_on_cols: list[str],
    actual_target_col: str = 'actual_target',
    model_pred_col: str = 'predicted_target'
) -> pd.DataFrame:
    """
    Ensembles predictions from multiple models using a weighted average.

    Args:
        model_prediction_dfs (list[pd.DataFrame]): A list of DataFrames, where each DataFrame
            contains predictions from one model. Each DataFrame must include the join_on_cols,
            the actual_target_col, and the model_pred_col.
        weights (list[float]): A list of weights corresponding to each model in model_prediction_dfs.
                               Must sum to 1.0 and have the same length as model_prediction_dfs.
        join_on_cols (list[str]): List of column names to join the prediction DataFrames on.
                                  These columns, along with actual_target_col, must uniquely identify each instance.
        actual_target_col (str): Name of the column containing the true target values.
        model_pred_col (str): Name of the column containing the model's predicted values.

    Returns:
        pd.DataFrame: A DataFrame containing join_on_cols, actual_target_col, and 'ensembled_prediction'.
    """
    if not model_prediction_dfs:
        raise ValueError("model_prediction_dfs list cannot be empty.")
    if len(model_prediction_dfs) != len(weights):
        raise ValueError("Length of model_prediction_dfs and weights must be the same.")
    if not np.isclose(sum(weights), 1.0):
        raise ValueError(f"Weights must sum to 1.0. Current sum: {sum(weights)}")

    # Select necessary columns and rename prediction column for each model before merging
    merged_df = None
    for i, df in enumerate(model_prediction_dfs):
        if not all(col in df.columns for col in join_on_cols + [actual_target_col, model_pred_col]):
            raise ValueError(f"DataFrame for model {i} is missing one or more required columns: {join_on_cols + [actual_target_col, model_pred_col]}")
        
        # Ensure join_on_cols and actual_target_col are present for the first df
        # and then only model_pred_col for subsequent ones to avoid duplicate actual_target after merge
        cols_to_select = join_on_cols + [actual_target_col, model_pred_col]
        if merged_df is not None:
            cols_to_select = join_on_cols + [model_pred_col] # Avoid duplicate actual_target

        temp_df = df[cols_to_select].rename(columns={model_pred_col: f'pred_model_{i}'})
        
        if merged_df is None:
            merged_df = temp_df
        else:
            # Validate that actual_target values are consistent if they were accidentally included and merged
            # This setup tries to avoid that, but as a safeguard:
            # common_cols_for_merge_check = [col for col in join_on_cols if col in merged_df.columns and col in temp_df.columns]
            merged_df = pd.merge(merged_df, temp_df, on=join_on_cols, how='inner')
    
    if merged_df is None or merged_df.empty:
        # This can happen if join_on_cols don't align across dataframes, leading to an empty result after inner join.
        raise ValueError("Merging prediction DataFrames resulted in an empty DataFrame. Check join_on_cols and data alignment.")

    # Calculate ensembled prediction
    ensembled_prediction = np.zeros(len(merged_df))
    for i, weight in enumerate(weights):
        ensembled_prediction += merged_df[f'pred_model_{i}'] * weight
    
    merged_df['ensembled_prediction'] = ensembled_prediction
    
    # Return only essential columns
    final_cols = join_on_cols + [actual_target_col, 'ensembled_prediction']
    return merged_df[final_cols]

def evaluate_ensembled_predictions(
    ensembled_preds_df: pd.DataFrame,
    season_col: str = 'season',
    actual_target_col: str = 'actual_target',
    ensembled_pred_col: str = 'ensembled_prediction'
) -> dict:
    """
    Evaluates ensembled predictions per season and overall.

    Args:
        ensembled_preds_df (pd.DataFrame): DataFrame from ensemble_predictions, containing
                                         season_col, actual_target_col, and ensembled_pred_col.
        season_col (str): Name of the column indicating the season.
        actual_target_col (str): Name of the column containing the true target values.
        ensembled_pred_col (str): Name of the column containing the ensembled predicted values.

    Returns:
        dict: Contains per-season and overall evaluation metrics (MAE, RMSE, R2).
    """
    if ensembled_preds_df.empty:
        print("Ensembled predictions DataFrame is empty. Cannot evaluate.")
        nan_metrics = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}
        return {'per_season_metrics': {}, 'overall_metrics': nan_metrics}

    per_season_metrics = {}
    all_seasons = sorted(ensembled_preds_df[season_col].unique())

    for s in all_seasons:
        season_data = ensembled_preds_df[ensembled_preds_df[season_col] == s]
        if not season_data.empty:
            metrics = calculate_evaluation_metrics(season_data[actual_target_col], season_data[ensembled_pred_col])
            per_season_metrics[s] = metrics
            print(f"Ensemble Metrics for Season {s}: MAE={metrics['MAE']:.4f}, RMSE={metrics['RMSE']:.4f}, R2={metrics['R2']:.4f}")
        else:
            per_season_metrics[s] = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}

    overall_metrics = {}
    if not ensembled_preds_df.empty:
        overall_metrics = calculate_evaluation_metrics(ensembled_preds_df[actual_target_col], ensembled_preds_df[ensembled_pred_col])
        print(f"Overall Ensemble Metrics: MAE={overall_metrics['MAE']:.4f}, RMSE={overall_metrics['RMSE']:.4f}, R2={overall_metrics['R2']:.4f}")
    else:
        overall_metrics = {metric: np.nan for metric in ['MAE', 'RMSE', 'R2']}
        print("No ensembled predictions available to compute overall metrics.")
        
    return {
        'per_season_metrics': per_season_metrics,
        'overall_metrics': overall_metrics
    }
