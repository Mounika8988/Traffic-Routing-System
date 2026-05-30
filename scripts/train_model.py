"""
train_model.py
--------------
Trains a Random Forest classifier to predict traffic congestion levels.

Why Random Forest?
  ✓ Handles both numerical and categorical features well
  ✓ Robust to outliers and missing values
  ✓ Gives feature importance — great for interviews
  ✓ No need for feature scaling
  ✓ Works well on small-to-medium datasets
  ✓ Easy to explain conceptually

What this script does:
  1. Loads the simulated traffic CSV
  2. Preprocesses categorical features (one-hot + label encoding)
  3. Splits data into train / test sets (80/20)
  4. Trains a Random Forest with tuned hyperparameters
  5. Evaluates accuracy, prints classification report
  6. Saves the trained model + label encoder using joblib
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix
)

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_PATH   = os.path.join(BASE_DIR, "..", "backend", "data", "traffic_data.csv")
MODEL_DIR   = os.path.join(BASE_DIR, "..", "backend", "saved_models")
MODEL_PATH  = os.path.join(MODEL_DIR, "traffic_model.pkl")
ENC_PATH    = os.path.join(MODEL_DIR, "label_encoders.pkl")

# ─── Feature Engineering ──────────────────────────────────────────────────────
# We encode the categorical columns so sklearn can use them.
CATEGORICAL_COLS = ["day_of_week", "weather", "road_id", "road_type"]
FEATURE_COLS = [
    "hour", "day_of_week", "weather", "road_id",
    "road_type", "vehicle_count", "is_weekend"
]
TARGET_COL = "congestion_level"


def load_and_preprocess(path: str):
    """
    Loads CSV, label-encodes categoricals, returns X, y and encoders dict.
    
    Label encoding vs one-hot:
      We use label encoding here because Random Forest can handle ordinal-like
      integer codes; it doesn't assume ordinality in splits. For linear models
      we'd use one-hot, but RF splits on thresholds anyway.
    """
    df = pd.read_csv(path)
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")

    encoders = {}
    df_enc   = df.copy()

    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df_enc[col] = le.fit_transform(df_enc[col])
        encoders[col] = le

    # Encode target
    le_target = LabelEncoder()
    df_enc[TARGET_COL] = le_target.fit_transform(df_enc[TARGET_COL])
    encoders["congestion_level"] = le_target

    X = df_enc[FEATURE_COLS].values
    y = df_enc[TARGET_COL].values

    return X, y, encoders, df_enc


def train(X_train, y_train):
    """
    Trains a Random Forest Classifier.

    Key hyperparameters explained:
      n_estimators=200  — 200 decision trees in the forest; more = better accuracy,
                          but diminishing returns above ~200 for small datasets.
      max_depth=12      — Each tree can go 12 levels deep; prevents overfitting.
      min_samples_leaf=4 — A leaf must have ≥4 samples; smooths noisy splits.
      class_weight='balanced' — Handles class imbalance automatically.
      random_state=42   — Reproducibility.
    """
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=4,
        class_weight="balanced",
        n_jobs=-1,          # Use all CPU cores
        random_state=42
    )
    model.fit(X_train, y_train)
    return model


def evaluate(model, X_test, y_test, encoders):
    y_pred    = model.predict(X_test)
    acc       = accuracy_score(y_test, y_pred)
    le_target = encoders["congestion_level"]
    labels    = le_target.classes_          # ["High", "Low", "Medium"]

    print("\n" + "="*60)
    print(f"  TEST ACCURACY : {acc * 100:.2f}%")
    print("="*60)
    print("\nClassification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=labels
    ))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Feature importances
    importances = model.feature_importances_
    feat_df = pd.DataFrame({
        "feature": FEATURE_COLS,
        "importance": importances
    }).sort_values("importance", ascending=False)
    print("\nFeature Importances:")
    print(feat_df.to_string(index=False))


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    # 1. Load & preprocess
    X, y, encoders, _ = load_and_preprocess(DATA_PATH)

    # 2. Train / test split — stratified to maintain class proportions
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"\nTrain size: {len(X_train)} | Test size: {len(X_test)}")

    # 3. Train
    print("\nTraining Random Forest …")
    model = train(X_train, y_train)

    # 4. Cross-validation for robust accuracy estimate
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"\n5-Fold Cross-Val Accuracy: {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%")

    # 5. Evaluate on held-out test set
    evaluate(model, X_test, y_test, encoders)

    # 6. Save model and encoders
    joblib.dump(model,    MODEL_PATH)
    joblib.dump(encoders, ENC_PATH)
    print(f"\n✅  Model saved    → {MODEL_PATH}")
    print(f"✅  Encoders saved → {ENC_PATH}")


if __name__ == "__main__":
    main()
