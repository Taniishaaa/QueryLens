"""
ml_models.py
------------
ML prediction interface for the /estimate pipeline.

CURRENT STATE: Dummy implementations.
These functions return hardcoded/rule-based responses so the rest of
the pipeline can be developed and tested end-to-end.

FUTURE: Replace the bodies of predict_cost_category() and
predict_execution_time() with real model loading + inference.
The function signatures and return shapes must NOT change.

Expected model files (drop into backend/models/ when ready):
  - models/classifier.joblib
  - models/preprocessor.joblib
  - models/regression_model.joblib
  - models/label_encoder.joblib
"""

import os

# ---------------------------------------------------------------------------
# Model loading (real models — loaded once at startup when files exist)
# ---------------------------------------------------------------------------

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

_classifier   = None
_preprocessor = None
_regressor    = None

def _load_models():
    """
    Attempt to load saved models from the models/ directory.
    Called once on first use. Silently skips if files are not present yet.
    """
    global _classifier, _preprocessor, _regressor
    try:
        import joblib
        clf_path  = os.path.join(MODELS_DIR, "classifier.joblib")
        pre_path  = os.path.join(MODELS_DIR, "preprocessor.joblib")
        reg_path  = os.path.join(MODELS_DIR, "regression_model.joblib")

        if os.path.exists(clf_path):
            _classifier = joblib.load(clf_path)
        if os.path.exists(pre_path):
            _preprocessor = joblib.load(pre_path)
        if os.path.exists(reg_path):
            _regressor = joblib.load(reg_path)
    except Exception as e:
        # Non-fatal — fall back to dummy predictions.
        print(f"[ml_models] Could not load models: {e}")

_load_models()


# ---------------------------------------------------------------------------
# Public interface — called by /estimate in main.py
# ---------------------------------------------------------------------------

def predict_cost_category(features: dict) -> dict:
    """
    Predict the cost category of a query.

    Parameters
    ----------
    features : dict
        Combined feature dict from features.extract_all_features().

    Returns
    -------
    dict with keys:
        category   : str  — "Low", "Medium", or "High"
        confidence : float — 0.0 to 1.0
    """
    # -- Real model path (activated once classifier.joblib is present) ------
    if _classifier is not None and _preprocessor is not None:
        return _real_classify(features)

    # -- DUMMY path ---------------------------------------------------------
    return _dummy_classify(features)


def predict_execution_time(features: dict) -> float:
    """
    Predict estimated execution time in milliseconds.

    Parameters
    ----------
    features : dict
        Combined feature dict from features.extract_all_features().

    Returns
    -------
    float — predicted execution time in milliseconds.
    """
    # -- Real model path (activated once regression_model.joblib is present)
    if _regressor is not None and _preprocessor is not None:
        return _real_regress(features)

    # -- DUMMY path ---------------------------------------------------------
    return _dummy_regress(features)


# ---------------------------------------------------------------------------
# Dummy implementations
# Simple rule-based logic driven by estimated_cost from EXPLAIN.
# Mirrors the project-defined thresholds:
#   estimated_cost < 100       -> Low
#   100 <= estimated_cost < 1000 -> Medium
#   estimated_cost >= 1000     -> High
# ---------------------------------------------------------------------------

def _dummy_classify(features: dict) -> dict:
    """DUMMY: derive category from EXPLAIN estimated_cost thresholds."""
    cost = features.get("estimated_cost", 0.0)

    if cost < 100:
        return {"category": "Low",    "confidence": 0.90}
    elif cost < 1000:
        return {"category": "Medium", "confidence": 0.85}
    else:
        return {"category": "High",   "confidence": 0.91}


def _dummy_regress(features: dict) -> float:
    """DUMMY: rough execution time estimate based on cost and row count."""
    cost = features.get("estimated_cost", 0.0)
    rows = features.get("estimated_rows", 1)
    # Very rough heuristic — not meaningful, just a placeholder number.
    return round(max(1.0, cost * 0.05 + rows * 0.001), 2)


# ---------------------------------------------------------------------------
# Real model implementations (stubs — filled in during Phase 6)
# ---------------------------------------------------------------------------

def _real_classify(features: dict) -> dict:
    """Use the loaded preprocessor + classifier to predict cost category."""
    import pandas as pd
    df = pd.DataFrame([features])
    X  = _preprocessor.transform(df)
    pred  = _classifier.predict(X)[0]
    proba = _classifier.predict_proba(X)[0]
    confidence = float(max(proba))
    # pred is expected to be a string label: "Low" / "Medium" / "High"
    return {"category": str(pred), "confidence": round(confidence, 4)}


def _real_regress(features: dict) -> float:
    """Use the loaded preprocessor + regressor to predict execution time."""
    import pandas as pd
    df = pd.DataFrame([features])
    X  = _preprocessor.transform(df)
    pred = _regressor.predict(X)[0]
    return round(float(pred), 2)
