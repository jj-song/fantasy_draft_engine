"""
Demonstrates model persistence by training, saving, and loading a model.

This script trains a RandomForestModel (using placeholder data), saves the trained model
object to a file using `joblib` (in the `saved_models/` directory), loads the model
from the file, and verifies that the loaded model can make predictions identical to
the original model.

To run: `python -m src.model_persistence` from the `fantasy_football_ai_tool` directory.
"""
import pandas as pd
import numpy as np
import joblib
import os

from src.modeling import RandomForestModel 
# Uses a placeholder function from final_evaluation.py for data loading.
# In a full application, this would point to a dedicated data loading/preprocessing module.
from src.final_evaluation import load_and_prepare_data

# Directory to store saved model files (relative to project root if script is run as a module from project root)
MODEL_DIR = 'saved_models'
# Default filename for the example saved model
MODEL_FILENAME = 'trained_random_forest.joblib'

def train_and_save_model(data, feature_cols, target_col, model_path):
    """Trains a RandomForest model and saves it to the specified path."""
    print(f"Training model with features: {feature_cols} and target: {target_col}")
    X_train = data[feature_cols]
    y_train = data[target_col]

    # Using simple default parameters for RandomForest for this example
    model = RandomForestModel(model_params={'random_state': 42, 'n_jobs': 1})
    model.train(X_train, y_train)
    print("Model trained.")

    # Ensure directory exists
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")
    return model

def load_model(model_path):
    """Loads a model from the specified path."""
    if not os.path.exists(model_path):
        print(f"Model file not found at {model_path}")
        return None
    model = joblib.load(model_path)
    print(f"Model loaded from {model_path}")
    return model

def run_model_persistence_example():
    """Demonstrates saving and loading a model."""
    print("Starting Model Persistence Example...")
    data = load_and_prepare_data()

    # Use a small subset of data for quick example if needed, or all data
    # For simplicity, using all data as 'training' data here.
    sample_data_for_prediction = data.sample(min(5, len(data)), random_state=42)
    X_sample = sample_data_for_prediction[['feature1', 'feature2']]
    
    model_full_path = os.path.join(MODEL_DIR, MODEL_FILENAME)

    # 1. Train and Save Model
    print("\n--- Training and Saving Model ---")
    trained_model = train_and_save_model(data, ['feature1', 'feature2'], 'target_points', model_full_path)

    # 2. Load Model
    print("\n--- Loading Model ---")
    loaded_model = load_model(model_full_path)

    # 3. Verify Loaded Model by Making Predictions
    if loaded_model:
        print("\n--- Verifying Loaded Model ---")
        try:
            predictions_from_loaded = loaded_model.predict(X_sample)
            print(f"Sample predictions from loaded model ({type(loaded_model.model).__name__}):\n{predictions_from_loaded}")
            
            # Optional: Compare with predictions from original model if still in memory
            if trained_model:
                 predictions_from_original = trained_model.predict(X_sample)
                 if np.array_equal(predictions_from_loaded, predictions_from_original):
                     print("Predictions from loaded model match predictions from original model.")
                 else:
                     print("Warning: Predictions from loaded model DO NOT match original model.")
        except Exception as e:
            print(f"Error making predictions with loaded model: {e}")
    else:
        print("Skipping verification as model loading failed.")

if __name__ == "__main__":
    run_model_persistence_example()
