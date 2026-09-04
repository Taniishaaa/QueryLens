"""
ml_models.py
------------
Machine-learning prediction interface.

Regression model:
    HistGradientBoostingRegressor

The regression model was trained on:
    log1p(actual_execution_time)

Therefore the backend converts predictions back to milliseconds
using expm1().
"""

import os
import joblib
import numpy as np
import pandas as pd


# ============================================================
# MODEL LOCATION
# ============================================================

MODELS_DIR = os.path.join(
    os.path.dirname(__file__),
    "models"
)

REGRESSION_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "model_histogram_gradient_boosting.pkl"
)
CLASSIFICATION_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "best_classification_model.pkl"
)

# ============================================================
# FEATURE ORDER
# ============================================================

REGRESSION_FEATURES = [
    "num_tables",
    "num_joins",
    "num_filters",
    "has_group_by",
    "has_order_by",
    "has_aggregation",
    "num_aggregations",
    "num_selected_columns",
    "num_subqueries",
    "query_depth",
    "total_rows",
    "total_table_size",
    "num_indexes",
    "column_cardinality",
    "estimated_rows",
    "estimated_cost",
    "plan_depth",
    "num_sequential_scans",
    "num_index_scans",
    "num_plan_joins",
]


# ============================================================
# LOAD REGRESSION MODEL
# ============================================================

_regressor = None
_classifier = None
_classification_preprocessor = None
_classification_label_encoder = None
_classification_feature_columns = None

def _load_regression_model():

    global _regressor

    if not os.path.exists(
        REGRESSION_MODEL_PATH
    ):

        print(
            "[ml_models] Regression model not found:"
        )

        print(
            REGRESSION_MODEL_PATH
        )

        return

    try:

        _regressor = joblib.load(
            REGRESSION_MODEL_PATH
        )

        print(
            "[ml_models] Regression model loaded:"
        )

        print(
            type(_regressor).__name__
        )

    except Exception as e:

        print(
            f"[ml_models] Failed to load regression model: {e}"
        )

        _regressor = None


_load_regression_model()
# ============================================================
# LOAD CLASSIFICATION MODEL
# ============================================================

def _load_classification_model():

    global _classifier
    global _classification_preprocessor
    global _classification_label_encoder
    global _classification_feature_columns

    if not os.path.exists(CLASSIFICATION_MODEL_PATH):

        print(
            "[ml_models] Classification model not found:"
        )

        print(
            CLASSIFICATION_MODEL_PATH
        )

        return

    try:

        bundle = joblib.load(
            CLASSIFICATION_MODEL_PATH
        )

        # Your PKL is a dictionary containing
        # model + preprocessor + label encoder.
        _classifier = bundle["model"]

        _classification_preprocessor = bundle["preprocessor"]

        _classification_label_encoder = bundle["label_encoder"]

        _classification_feature_columns = bundle["feature_columns"]

        print(
            "[ml_models] Classification model loaded:"
        )

        print(
            type(_classifier).__name__
        )

        print(
            "[ml_models] Classification features:"
        )

        print(
            _classification_feature_columns
        )

        print(
            "[ml_models] Classification classes:"
        )

        print(
            list(_classification_label_encoder.classes_)
        )

    except Exception as e:

        print(
            f"[ml_models] Failed to load classification model: {e}"
        )

        _classifier = None
        _classification_preprocessor = None
        _classification_label_encoder = None
        _classification_feature_columns = None


_load_classification_model()

# ============================================================
# PUBLIC API
# ============================================================

def predict_execution_time(
    features: dict
) -> float:

    """
    Predict SQL execution time in milliseconds.

    The trained model predicts:

        log1p(actual_execution_time)

    Therefore:

        actual_execution_time =
            expm1(model_prediction)
    """

    if _regressor is None:

        raise RuntimeError(
            "Regression model is not loaded."
        )

    # --------------------------------------------------------
    # Build DataFrame in EXACT training feature order
    # --------------------------------------------------------

    missing = [
        feature
        for feature in REGRESSION_FEATURES
        if feature not in features
    ]

    if missing:

        raise ValueError(
            "Missing regression features: "
            + ", ".join(missing)
        )

    X = pd.DataFrame(
        [
            {
                feature: features[feature]
                for feature in REGRESSION_FEATURES
            }
        ]
    )

    # --------------------------------------------------------
    # Model prediction
    # --------------------------------------------------------

    predicted_log_time = _regressor.predict(X)[0]

    print(f"[ml_models] Raw log prediction: {predicted_log_time}")

    # --------------------------------------------------------
    # Convert log1p prediction back to milliseconds
    # --------------------------------------------------------

    predicted_time_ms = np.expm1(
        predicted_log_time
    )

    print(f"[ml_models] Prediction after expm1: {predicted_time_ms}")

    # Never return a negative execution time.
    predicted_time_ms = max(
        0.0,
        float(predicted_time_ms)
    )

    return round(
        predicted_time_ms,
        2
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def predict_cost_category(
    features: dict,
    query_text: str,
    source_dataset: str = "JOB"
) -> dict:

    """
    Predict SQL cost category using the trained XGBoost model.

    The single PKL file contains:
        - XGBoost classifier
        - preprocessing pipeline
        - label encoder
        - feature column information
    """

    if _classifier is None:

        raise RuntimeError(
            "Classification model is not loaded."
        )

    # --------------------------------------------------------
    # Build input using the exact training feature columns
    # --------------------------------------------------------

    classification_input = {}

    for feature in _classification_feature_columns:

        if feature == "query_text":

            classification_input[feature] = query_text

        elif feature == "source_dataset":

            classification_input[feature] = source_dataset

        elif feature in features:

            classification_input[feature] = features[feature]

        else:

            raise ValueError(
                "Missing classification feature: "
                + feature
            )

    X = pd.DataFrame(
        [classification_input]
    )

    # --------------------------------------------------------
    # Apply the SAME preprocessing used during training
    # --------------------------------------------------------

    X_processed = _classification_preprocessor.transform(
        X
    )

    # --------------------------------------------------------
    # Predict encoded class
    # --------------------------------------------------------

    predicted_encoded = _classifier.predict(
        X_processed
    )[0]

    # Convert encoded value back to:
    # Low / Medium / High
    predicted_category = (
        _classification_label_encoder
        .inverse_transform(
            [predicted_encoded]
        )[0]
    )

    # --------------------------------------------------------
    # Calculate confidence
    # --------------------------------------------------------

    probabilities = _classifier.predict_proba(
        X_processed
    )[0]

    confidence = float(
        np.max(probabilities)
    )

    print(
        "[ml_models] Classification prediction:",
        predicted_category
    )

    print(
        "[ml_models] Classification confidence:",
        confidence
    )

    return {
        "category": str(predicted_category),
        "confidence": round(confidence, 4)
    }