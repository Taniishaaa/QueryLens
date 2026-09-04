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
# TEMPORARY CLASSIFICATION PLACEHOLDER
# ============================================================

def predict_cost_category(
    features: dict
) -> dict:

    """
    Temporary classification implementation.

    We will replace this later with your actual
    classification model.
    """

    cost = features.get(
        "estimated_cost",
        0.0
    )

    if cost < 100:

        return {
            "category": "Low",
            "confidence": 0.90
        }

    elif cost < 1000:

        return {
            "category": "Medium",
            "confidence": 0.85
        }

    else:

        return {
            "category": "High",
            "confidence": 0.91
        }