"""
Performs feature importance analysis for specified models.

This script trains models (e.g., RandomForest, LightGBM) on data (currently placeholder),
extracts feature importances, prints them to the console, and generates bar plots
visualizing the top N most important features for each model.

To run: `python -m src.feature_importance` from the `fantasy_football_ai_tool` directory.
(Note: Plots are displayed sequentially; close each plot window to proceed to the next model.)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from src.modeling import RandomForestModel, LightGBMModel
# Uses a placeholder function from final_evaluation.py for data loading.
# In a full application, this would point to a dedicated data loading/preprocessing module.
from src.final_evaluation import load_and_prepare_data 

def get_feature_importances(model, feature_names):
    """Extracts feature importances from a trained model."""
    if hasattr(model.model, 'feature_importances_'):
        return pd.Series(model.model.feature_importances_, index=feature_names)
    elif hasattr(model.model, 'coef_'):
        # For linear models, coef_ might be multi-dimensional for multi-class, take first row or average
        if model.model.coef_.ndim > 1:
            return pd.Series(model.model.coef_[0], index=feature_names) 
        return pd.Series(model.model.coef_, index=feature_names)
    else:
        print(f"Model type {type(model.model)} does not have standard feature_importances_ or coef_ attribute.")
        return None

def plot_feature_importances(importances_series, model_name, top_n=20):
    """Plots the top N feature importances."""
    if importances_series is None or importances_series.empty:
        print(f"No feature importances to plot for {model_name}.")
        return

    plt.figure(figsize=(10, max(6, top_n / 2))) # Adjust height based on number of features
    top_importances = importances_series.sort_values(ascending=False).head(top_n)
    sns.barplot(x=top_importances.values, y=top_importances.index)
    plt.title(f'Top {min(top_n, len(top_importances))} Feature Importances - {model_name}')
    plt.xlabel('Importance')
    plt.ylabel('Feature')
    plt.tight_layout()
    plt.show()

def run_feature_importance_analysis():
    """Runs the feature importance analysis pipeline."""
    print("Starting Feature Importance Analysis...")
    data = load_and_prepare_data()

    feature_cols = ['feature1', 'feature2'] # As defined in final_evaluation
    target_col = 'target_points'

    # For feature importance, typically train on all available historical data
    # (or a relevant recent subset if time-series nature is strictly maintained for this step)
    # Here, we'll use all data for simplicity, as rolling window isn't the focus for importance extraction itself.
    X_train = data[feature_cols]
    y_train = data[target_col]

    models_to_analyze = {
        "RandomForest": RandomForestModel(model_params={'random_state': 42, 'n_jobs': 1}),
        "LightGBM": LightGBMModel(model_params={'random_state': 42, 'n_jobs': 1, 'verbose': -1})
    }

    for model_name, model_instance in models_to_analyze.items():
        print(f"\n--- Analyzing {model_name} ---")
        try:
            model_instance.train(X_train, y_train)
            print(f"{model_name} trained.")
            importances = get_feature_importances(model_instance, feature_cols)
            if importances is not None:
                print("Feature Importances:")
                print(importances.sort_values(ascending=False))
                plot_feature_importances(importances, model_name)
        except Exception as e:
            print(f"Could not analyze {model_name}: {e}")

if __name__ == "__main__":
    run_feature_importance_analysis()
