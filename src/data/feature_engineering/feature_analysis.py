"""
Feature analysis and engineering utilities.

This module contains functions for analyzing feature importance,
correlation, and other metrics to improve model performance.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Union, Tuple
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


def plot_feature_importance(model, feature_names: List[str], title: str = "Feature Importance", figsize: Tuple[int, int] = (12, 8)):
    """
    Plot feature importance from a trained model.
    
    Args:
        model: Trained model with feature_importances_ attribute
        feature_names: List of feature names
        title: Plot title
        figsize: Figure size (width, height)
    """
    # Get feature importance
    importance = model.feature_importances_
    
    # Create DataFrame for plotting
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    # Plot
    plt.figure(figsize=figsize)
    sns.barplot(x='importance', y='feature', data=feature_importance[:20])
    plt.title(title)
    plt.tight_layout()
    
    return feature_importance


def plot_correlation_matrix(df: pd.DataFrame, target_col: str, threshold: float = 0.1, figsize: Tuple[int, int] = (14, 12)):
    """
    Plot correlation matrix for features with correlation to target above threshold.
    
    Args:
        df: DataFrame with features and target
        target_col: Name of target column
        threshold: Minimum absolute correlation to include
        figsize: Figure size (width, height)
    """
    # Calculate correlation matrix
    corr_matrix = df.corr()
    
    # Get correlations with target
    target_corr = corr_matrix[target_col].sort_values(ascending=False)
    
    # Filter features with correlation above threshold
    high_corr_features = target_corr[abs(target_corr) > threshold].index.tolist()
    
    # Plot correlation matrix for selected features
    plt.figure(figsize=figsize)
    sns.heatmap(
        df[high_corr_features].corr(), 
        annot=True, 
        cmap='coolwarm', 
        vmin=-1, 
        vmax=1, 
        fmt='.2f'
    )
    plt.title(f'Feature Correlation Matrix (|corr| > {threshold} with {target_col})')
    plt.tight_layout()
    
    return target_corr


def calculate_mutual_information(df: pd.DataFrame, target_col: str, figsize: Tuple[int, int] = (12, 8)):
    """
    Calculate mutual information between features and target.
    
    Args:
        df: DataFrame with features and target
        target_col: Name of target column
        figsize: Figure size (width, height)
    """
    # Separate features and target
    X = df.drop(columns=[target_col])
    y = df[target_col]
    
    # Calculate mutual information
    mi_scores = mutual_info_regression(X, y)
    
    # Create DataFrame for plotting
    mi_df = pd.DataFrame({
        'feature': X.columns,
        'mutual_info': mi_scores
    }).sort_values('mutual_info', ascending=False)
    
    # Plot
    plt.figure(figsize=figsize)
    sns.barplot(x='mutual_info', y='feature', data=mi_df[:20])
    plt.title(f'Mutual Information with {target_col}')
    plt.tight_layout()
    
    return mi_df


def plot_feature_distributions(df: pd.DataFrame, target_col: str, top_n: int = 5, figsize: Tuple[int, int] = (15, 10)):
    """
    Plot distributions of top features by correlation with target.
    
    Args:
        df: DataFrame with features and target
        target_col: Name of target column
        top_n: Number of top features to plot
        figsize: Figure size (width, height)
    """
    # Calculate correlation with target
    corr_with_target = df.corr()[target_col].sort_values(ascending=False)
    
    # Get top features (excluding target itself)
    top_features = corr_with_target[corr_with_target.index != target_col][:top_n].index.tolist()
    
    # Plot distributions
    fig, axes = plt.subplots(nrows=len(top_features), figsize=figsize)
    
    for i, feature in enumerate(top_features):
        sns.histplot(df[feature], kde=True, ax=axes[i])
        axes[i].set_title(f'{feature} (corr with {target_col}: {corr_with_target[feature]:.3f})')
    
    plt.tight_layout()


def create_interaction_features(df: pd.DataFrame, feature_pairs: List[Tuple[str, str]]) -> pd.DataFrame:
    """
    Create interaction features from pairs of existing features.
    
    Args:
        df: DataFrame with features
        feature_pairs: List of tuples with feature pairs to interact
        
    Returns:
        DataFrame with interaction features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_new = df.copy()
    
    # Create interaction features
    for f1, f2 in feature_pairs:
        if f1 in df.columns and f2 in df.columns:
            # Multiplication interaction
            df_new[f'{f1}_x_{f2}'] = df[f1] * df[f2]
            
            # Division interaction (with handling for division by zero)
            if (df[f2] != 0).all():
                df_new[f'{f1}_div_{f2}'] = df[f1] / df[f2]
            
            # Addition interaction
            df_new[f'{f1}_plus_{f2}'] = df[f1] + df[f2]
            
            # Subtraction interaction
            df_new[f'{f1}_minus_{f2}'] = df[f1] - df[f2]
    
    return df_new


def create_polynomial_features(df: pd.DataFrame, features: List[str], degree: int = 2) -> pd.DataFrame:
    """
    Create polynomial features from existing features.
    
    Args:
        df: DataFrame with features
        features: List of features to create polynomials from
        degree: Polynomial degree
        
    Returns:
        DataFrame with polynomial features added
    """
    # Make a copy to avoid modifying the original dataframe
    df_new = df.copy()
    
    # Create polynomial features
    for feature in features:
        if feature in df.columns:
            for d in range(2, degree + 1):
                df_new[f'{feature}_pow_{d}'] = df[feature] ** d
    
    return df_new


def perform_pca_analysis(df: pd.DataFrame, n_components: int = 5, plot: bool = True, figsize: Tuple[int, int] = (10, 6)):
    """
    Perform PCA analysis on features.
    
    Args:
        df: DataFrame with features
        n_components: Number of PCA components
        plot: Whether to plot explained variance
        figsize: Figure size (width, height)
        
    Returns:
        Tuple of (PCA model, DataFrame with PCA components, explained variance ratio)
    """
    # Standardize features
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df)
    
    # Perform PCA
    pca = PCA(n_components=n_components)
    pca_result = pca.fit_transform(scaled_data)
    
    # Create DataFrame with PCA components
    pca_df = pd.DataFrame(
        data=pca_result,
        columns=[f'PC{i+1}' for i in range(n_components)]
    )
    
    # Plot explained variance
    if plot:
        plt.figure(figsize=figsize)
        plt.bar(
            range(1, n_components + 1),
            pca.explained_variance_ratio_,
            alpha=0.8
        )
        plt.step(
            range(1, n_components + 1),
            np.cumsum(pca.explained_variance_ratio_),
            where='mid',
            label='Cumulative Explained Variance'
        )
        plt.xlabel('Number of Components')
        plt.ylabel('Explained Variance Ratio')
        plt.title('PCA Explained Variance')
        plt.legend()
        plt.tight_layout()
    
    return pca, pca_df, pca.explained_variance_ratio_


def plot_feature_target_relationships(df: pd.DataFrame, features: List[str], target_col: str, figsize: Tuple[int, int] = (15, 10)):
    """
    Plot relationships between features and target.
    
    Args:
        df: DataFrame with features and target
        features: List of features to plot
        target_col: Name of target column
        figsize: Figure size (width, height)
    """
    # Calculate number of rows and columns for subplots
    n_features = len(features)
    n_cols = 2
    n_rows = (n_features + n_cols - 1) // n_cols
    
    # Create subplots
    fig, axes = plt.subplots(nrows=n_rows, ncols=n_cols, figsize=figsize)
    axes = axes.flatten()
    
    # Plot each feature
    for i, feature in enumerate(features):
        if i < len(axes):
            sns.regplot(x=feature, y=target_col, data=df, ax=axes[i])
            axes[i].set_title(f'{feature} vs {target_col}')
    
    # Hide unused subplots
    for j in range(n_features, len(axes)):
        axes[j].set_visible(False)
    
    plt.tight_layout()


def identify_outliers(df: pd.DataFrame, features: List[str], threshold: float = 3.0) -> pd.DataFrame:
    """
    Identify outliers in features using z-score.
    
    Args:
        df: DataFrame with features
        features: List of features to check for outliers
        threshold: Z-score threshold for outliers
        
    Returns:
        DataFrame with outlier flags
    """
    # Make a copy to avoid modifying the original dataframe
    df_outliers = df.copy()
    
    # Calculate z-scores
    for feature in features:
        if feature in df.columns:
            z_scores = np.abs((df[feature] - df[feature].mean()) / df[feature].std())
            df_outliers[f'{feature}_is_outlier'] = z_scores > threshold
    
    return df_outliers


def compare_model_performance(models: Dict[str, object], X: pd.DataFrame, y: pd.Series, metric_name: str = 'R²', figsize: Tuple[int, int] = (10, 6)):
    """
    Compare performance of multiple models.
    
    Args:
        models: Dictionary of model name to model object
        X: Feature DataFrame
        y: Target Series
        metric_name: Name of metric to display
        figsize: Figure size (width, height)
    """
    # Calculate scores for each model
    scores = {}
    for name, model in models.items():
        scores[name] = model.score(X, y)
    
    # Create DataFrame for plotting
    scores_df = pd.DataFrame({
        'model': list(scores.keys()),
        metric_name: list(scores.values())
    }).sort_values(metric_name, ascending=False)
    
    # Plot
    plt.figure(figsize=figsize)
    sns.barplot(x=metric_name, y='model', data=scores_df)
    plt.title(f'Model Performance Comparison ({metric_name})')
    plt.tight_layout()
    
    return scores_df
