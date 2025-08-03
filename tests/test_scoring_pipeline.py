"""
Test script to run the scoring pipeline with sample data.
"""
import pandas as pd
import os
from src.scoring import run_scoring_pipeline

def main():
    # Use the most recent features file as a sample
    sample_file = 'data/processed/features_for_2022_predicting_2023.parquet'
    
    # Load the file to check its structure
    df = pd.read_parquet(sample_file)
    
    # Add mock prediction columns if they don't exist
    if 'predicted_lightgbm' not in df.columns:
        print(f"Adding mock 'predicted_lightgbm' column to {sample_file}")
        df['predicted_lightgbm'] = df['next_season_fppg'] if 'next_season_fppg' in df.columns else 10.0
    
    if 'predicted_random_forest' not in df.columns:
        print(f"Adding mock 'predicted_random_forest' column to {sample_file}")
        df['predicted_random_forest'] = df['next_season_fppg'] * 1.1 if 'next_season_fppg' in df.columns else 11.0
    
    # Save the modified file as a temporary file
    temp_file = 'data/processed/temp_predictions.parquet'
    df.to_parquet(temp_file)
    print(f"Saved temporary predictions file with {len(df)} players to {temp_file}")
    
    # Run the scoring pipeline
    print("\nRunning scoring pipeline...")
    output_file = 'data/processed/test_rankings.csv'
    rankings = run_scoring_pipeline(temp_file, output_file, top_n=50)
    
    print(f"\nGenerated rankings for {len(rankings)} players. Top 10:")
    print(rankings.head(10))
    
    # Clean up temporary file
    os.remove(temp_file)
    print(f"\nCleaned up temporary file: {temp_file}")

if __name__ == "__main__":
    main()
