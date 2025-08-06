# Scikit-learn Reference Documentation

This document contains comprehensive scikit-learn documentation focused on RandomForestRegressor, feature names, and prediction functionality.

## Key Topics Covered

### Feature Names and Compatibility
- `feature_names_in_` attribute: Stores feature names when fitting on pandas DataFrames
- `get_feature_names_out()` method: Provides string names for output features 
- Feature name consistency checks: Inconsistent names raise warnings/errors
- Feature mapping and compatibility between different data sources

### RandomForestRegressor
- Basic usage and prediction methods
- Feature importance computation (now parallelized)
- Support for missing values (with specific criteria)
- Monotonic constraints support
- `max_features` parameter updates (default changed from 'auto' to 1.0)
- Performance improvements (~15% faster fitting)
- Poisson criterion support
- `estimators_samples_` property for training sample indices

### Prediction Methods
- `predict()` method behavior and requirements
- Feature name validation during prediction
- Handling missing values in predictions
- Batch vs single predictions
- Error handling for incompatible features

## Important Notes for Our ML Models Service

### Feature Name Matching
Our RandomForestRegressor models expect specific feature names as seen during training:

**QB Model Features:**
- `games` (not `games_played`)
- `attempts` (not `passing_attempts`) 
- `completions` (not `passing_completions`)
- `passing_yards`, `passing_tds`, `interceptions`
- `carries` (not `rushing_attempts`)
- `rushing_yards`, `rushing_tds`

### Feature Compatibility Mapping
The feature compatibility mapper in our service needs to correctly transform input feature names to match what the models expect. The error we encountered shows this mapping isn't working properly:

```
The feature names should match those that were passed during fit.
Feature names unseen at fit time:
- age, games_played, passing_attempts, passing_completions, rushing_attempts
Feature names seen at fit time, yet now missing:
- attempts, carries, completions, games
```

### Solution
1. Update feature compatibility mapper to use correct mappings
2. Ensure feature names match exactly what models were trained with
3. Validate feature names before making predictions
4. Consider retraining models with standardized feature names if needed

---

## Full Documentation Content

========================
CODE SNIPPETS
========================
TITLE: Fix: MLPClassifier/Regressor Feature Names Warnings
DESCRIPTION: Suppresses spurious warnings in `neural_network.MLPClassifier` and `neural_network.MLPRegressor` that were previously raised when fitting data that included feature names.

SOURCE: https://github.com/scikit-learn/scikit-learn/blob/main/doc/whats_new/v1.2.rst#_snippet_29

LANGUAGE: APIDOC
CODE:
```
sklearn.neural_network.MLPClassifier, MLPRegressor:
  - No longer raise warnings when fitting data with feature names.
```

----------------------------------------

TITLE: DummyRegressor Prediction Strategies
DESCRIPTION: This section outlines the different prediction strategies available in Scikit-learn's `DummyRegressor` class. These strategies provide simple baseline predictions that ignore the input features, useful for establishing a baseline performance for regression tasks.

SOURCE: https://github.com/scikit-learn/scikit-learn/blob/main/doc/modules/model_evaluation.rst#_snippet_99

LANGUAGE: APIDOC
CODE:
```
class DummyRegressor:
  Strategies:
    mean: Always predicts the mean of the training targets.
    median: Always predicts the median of the training targets.
    quantile: Always predicts a user-provided quantile of the training targets.
    constant: Always predicts a constant value that is provided by the user.
  Methods:
    predict(): In all these strategies, the predict method completely ignores the input data.
```

----------------------------------------

TITLE: Enhance get_feature_names_out for Scikit-learn RandomTreesEmbedding
DESCRIPTION: The `ensemble.RandomTreesEmbedding` class now provides an informative `get_feature_names_out` function, which includes both tree index and leaf index in the generated output feature names.

SOURCE: https://github.com/scikit-learn/scikit-learn/blob/main/doc/whats_new/v1.1.rst#_snippet_86

LANGUAGE: APIDOC
CODE:
```
Class: ensemble.RandomTreesEmbedding
Method: get_feature_names_out()
Description: Provides informative feature names including tree and leaf indices.
```

----------------------------------------

TITLE: Add get_feature_names_out to Scikit-learn Ensemble Classifiers/Regressors
DESCRIPTION: The `get_feature_names_out` method has been added to `ensemble.VotingClassifier`, `ensemble.VotingRegressor`, `ensemble.StackingClassifier`, and `ensemble.StackingRegressor` to provide informative output feature names for combined estimators.

SOURCE: https://github.com/scikit-learn/scikit-learn/blob/main/doc/whats_new/v1.1.rst#_snippet_85

LANGUAGE: APIDOC
CODE:
```
Class: ensemble.VotingClassifier
Method: get_feature_names_out()
Description: Returns output feature names.

Class: ensemble.VotingRegressor
Method: get_feature_names_out()
Description: Returns output feature names.

Class: ensemble.StackingClassifier
Method: get_feature_names_out()
Description: Returns output feature names.

Class: ensemble.StackingRegressor
Method: get_feature_names_out()
Description: Returns output feature names.
```

[... continued with all the remaining documentation content ...]