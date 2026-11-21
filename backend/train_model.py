"""
Train the credit PD model on firm-level financial ratios.

Dataset: "Polish companies bankruptcy data" (Zieba, Tomczak & Tomczak, 2016),
UCI Machine Learning Repository #365 — https://archive.ics.uci.edu/dataset/365.
10,503 Polish manufacturing companies, 64 reported financial ratios each, with
a label recording whether the company went bankrupt inside the forecast period.
The five files are five forecast horizons: `1year.arff` holds ratios from the
first year of a five-year observation window and labels bankruptcy within those
five years, down to `5year.arff`, which holds ratios one year before the
outcome. All five are pooled, so the label this model predicts is "entered
bankruptcy within the forecast horizon", not a calendar twelve-month PD. The
per-horizon metrics printed at the end show how the model does at each.

The previous model was trained on the Home Credit Default Risk dataset, which
describes consumer loan applicants, not firms. Every feature was a renamed
consumer field standing in for a corporate ratio — credit amount over income
labelled "current ratio", days since birth labelled "news risk score". This
dataset is firm-level, so the twelve features are the ratios they claim to be.

Usage:
    python train_model.py              # train, evaluate, write the model
    python train_model.py --no-save    # evaluate only

Outputs, into models/xgboost/:
    creditiq_pd_xgboost.pkl  the fitted booster
    metrics.json             held-out ROC-AUC, KS, feature list, data provenance
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.credit_features import FEATURES, clip_frame, ks_statistic  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data", "polish_bankruptcy")
MODELS_DIR = os.path.join(HERE, "models", "xgboost")
MODEL_PATH = os.path.join(MODELS_DIR, "creditiq_pd_xgboost.pkl")
METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")

DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/365/"
    "polish+companies+bankruptcy+data.zip"
)
DATASET_CITATION = (
    "Zieba, M., Tomczak, S. K., & Tomczak, J. M. (2016). Ensemble boosted trees "
    "with synthetic features generation in application to bankruptcy prediction. "
    "Expert Systems with Applications. UCI ML Repository dataset 365."
)
ARFF_FILES = ("1year.arff", "2year.arff", "3year.arff", "4year.arff", "5year.arff")

# Each model feature maps to one documented ratio of the source dataset. The
# attribute numbering is the dataset's own; the comment gives its definition.
#   Attr1  net profit / total assets
#   Attr2  total liabilities / total assets
#   Attr3  working capital / total assets
#   Attr4  current assets / short-term liabilities
#   Attr9  sales / total assets
#   Attr10 equity / total assets
#   Attr19 gross profit / sales
#   Attr23 net profit / sales
#   Attr26 (net profit + depreciation) / total liabilities
#   Attr27 profit on operating activities / financial expenses
#   Attr46 (current assets - inventory) / short-term liabilities
#   Attr49 EBITDA / sales
DIRECT_MAP: Dict[str, Tuple[str, float]] = {
    "current_ratio": ("Attr4", 1.0),
    "quick_ratio": ("Attr46", 1.0),
    "debt_to_assets": ("Attr2", 1.0),
    "interest_coverage": ("Attr27", 1.0),
    "gross_margin_percent": ("Attr19", 100.0),
    "ebitda_margin_percent": ("Attr49", 100.0),
    "net_margin_percent": ("Attr23", 100.0),
    "return_on_assets_percent": ("Attr1", 100.0),
    "asset_turnover": ("Attr9", 1.0),
    "working_capital_to_assets": ("Attr3", 1.0),
    "cash_flow_to_debt": ("Attr26", 1.0),
}


def download_dataset() -> str:
    """Fetch and unpack the dataset once; return the directory holding the ARFFs."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if all(os.path.exists(os.path.join(DATA_DIR, name)) for name in ARFF_FILES):
        return DATA_DIR

    print(f"Downloading {DATASET_URL}")
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "creditiq-training"})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        archive.extractall(DATA_DIR)
    print(f"Extracted {len(payload) / 1e6:.1f} MB into {DATA_DIR}")
    return DATA_DIR


def read_arff(path: str) -> pd.DataFrame:
    """
    Minimal ARFF reader for this dataset: numeric attributes, a nominal class
    column, and '?' for a value the source did not report.
    """
    columns: List[str] = []
    rows: List[List[str]] = []
    in_data = False
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            lowered = line.lower()
            if not in_data:
                if lowered.startswith("@attribute"):
                    columns.append(line.split()[1])
                elif lowered.startswith("@data"):
                    in_data = True
                continue
            rows.append(line.split(","))

    frame = pd.DataFrame(rows, columns=columns)
    return frame.replace("?", np.nan).apply(pd.to_numeric, errors="coerce")


def build_matrix(data_dir: str) -> pd.DataFrame:
    """Pool the five horizons and map the source ratios onto the model features."""
    frames = []
    for name in ARFF_FILES:
        frame = read_arff(os.path.join(data_dir, name))
        frame["horizon_file"] = name
        frames.append(frame)
    raw = pd.concat(frames, ignore_index=True)
    print(f"Loaded {len(raw):,} company-years from {len(ARFF_FILES)} horizon files")

    mapped = pd.DataFrame(index=raw.index)
    for feature, (attribute, scale) in DIRECT_MAP.items():
        mapped[feature] = raw[attribute] * scale

    # Total liabilities / equity, from the two ratios the dataset does report:
    # (total liabilities / total assets) divided by (equity / total assets).
    equity_to_assets = raw["Attr10"].replace(0.0, np.nan)
    mapped["debt_to_equity"] = raw["Attr2"] / equity_to_assets

    mapped = clip_frame(mapped)
    mapped["target"] = raw["class"].astype(float)
    mapped["horizon_file"] = raw["horizon_file"]

    labelled = mapped.dropna(subset=["target"]).copy()
    labelled["target"] = labelled["target"].astype(int)

    # A row with no usable ratio at all carries no signal either way.
    usable = labelled[list(FEATURES)].notna().sum(axis=1) > 0
    dropped = int((~usable).sum())
    if dropped:
        print(f"Dropped {dropped} rows with no computable ratio")
    return labelled[usable].reset_index(drop=True)


def evaluate(y_true: np.ndarray, y_score: np.ndarray) -> Dict[str, float]:
    return {
        "roc_auc": round(float(roc_auc_score(y_true, y_score)), 4),
        "ks": round(ks_statistic(y_true, y_score), 4),
        "average_precision": round(float(average_precision_score(y_true, y_score)), 4),
        "brier": round(float(brier_score_loss(y_true, y_score)), 4),
        "n": int(len(y_true)),
        "n_default": int(np.sum(y_true)),
        "default_rate_percent": round(100.0 * float(np.mean(y_true)), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-save", action="store_true", help="evaluate without writing the model")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data_dir = download_dataset()
    data = build_matrix(data_dir)

    X = data[list(FEATURES)]
    y = data["target"].to_numpy()
    horizons = data["horizon_file"].to_numpy()

    # Held-out test set, stratified on the label. Early stopping needs its own
    # validation slice carved out of the training data: watching the test set
    # while fitting tunes the model to it and the reported AUC stops being a
    # held-out number.
    X_train_full, X_test, y_train_full, y_test, _, horizons_test = train_test_split(
        X, y, horizons, test_size=0.2, stratify=y, random_state=args.seed
    )
    X_train, X_valid, y_train, y_valid = train_test_split(
        X_train_full, y_train_full, test_size=0.2, stratify=y_train_full, random_state=args.seed
    )

    # The dataset is heavily imbalanced (roughly 5% bankrupt). Weighting the
    # positive class by the negative/positive ratio stops the booster from
    # minimising loss by predicting "no default" for everyone.
    n_pos = int(np.sum(y_train))
    n_neg = int(len(y_train) - n_pos)
    scale_pos_weight = n_neg / max(n_pos, 1)
    print(
        f"Train {len(X_train):,} ({n_pos:,} default) · validation {len(X_valid):,} · "
        f"test {len(X_test):,} · scale_pos_weight {scale_pos_weight:.2f}"
    )

    model = xgb.XGBClassifier(
        n_estimators=600,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_lambda=2.0,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        early_stopping_rounds=40,
        random_state=args.seed,
        n_jobs=4,
    )
    model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)

    # scale_pos_weight buys recall on a 5%-default sample, but it also pushes
    # predict_proba far above the real default frequency — the raw output ranks
    # well and is not a probability. A probability of default is quoted to a
    # credit committee and priced off, so the raw score is mapped back onto
    # observed frequencies by an isotonic fit on the validation slice. Isotonic
    # regression is monotone, so ranking metrics (ROC-AUC, KS) are unchanged
    # and only the calibration metric (Brier) moves.
    valid_raw = model.predict_proba(X_valid)[:, 1]
    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(valid_raw, y_valid)

    test_raw = model.predict_proba(X_test)[:, 1]
    test_scores = calibrator.predict(test_raw)
    overall = evaluate(y_test, test_scores)
    overall["brier_uncalibrated"] = round(float(brier_score_loss(y_test, test_raw)), 4)
    overall["roc_auc_uncalibrated"] = round(float(roc_auc_score(y_test, test_raw)), 4)
    valid = evaluate(y_valid, calibrator.predict(valid_raw))

    per_horizon = {}
    for name in ARFF_FILES:
        mask = horizons_test == name
        if mask.sum() > 0 and 0 < y_test[mask].sum() < mask.sum():
            per_horizon[name] = evaluate(y_test[mask], test_scores[mask])

    importances = sorted(
        zip(FEATURES, (float(v) for v in model.feature_importances_)),
        key=lambda pair: pair[1],
        reverse=True,
    )

    print("\nHeld-out test set")
    print(f"  ROC-AUC {overall['roc_auc']}   KS {overall['ks']}   "
          f"AP {overall['average_precision']}   Brier {overall['brier']} "
          f"(uncalibrated {overall['brier_uncalibrated']})")
    print(f"  {overall['n']:,} companies, {overall['n_default']:,} defaults "
          f"({overall['default_rate_percent']}%)")
    print("\nPer forecast horizon (held-out)")
    for name, scores in per_horizon.items():
        print(f"  {name}: ROC-AUC {scores['roc_auc']}  KS {scores['ks']}  n={scores['n']:,}")
    print("\nFeature importance (gain-weighted)")
    for name, value in importances:
        print(f"  {value:6.3f}  {name}")

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {
            "name": "Polish companies bankruptcy data",
            "url": "https://archive.ics.uci.edu/dataset/365",
            "citation": DATASET_CITATION,
            "files_pooled": list(ARFF_FILES),
            "label": "company entered bankruptcy within the file's forecast horizon",
            "rows_used": int(len(data)),
        },
        "features": list(FEATURES),
        "feature_source_map": {
            **{name: attribute for name, (attribute, _scale) in DIRECT_MAP.items()},
            "debt_to_equity": "Attr2 / Attr10",
        },
        "hyperparameters": {
            "n_estimators_requested": 600,
            "best_iteration": int(getattr(model, "best_iteration", 0) or 0),
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "reg_lambda": 2.0,
            "scale_pos_weight": round(scale_pos_weight, 4),
            "early_stopping_rounds": 40,
            "seed": args.seed,
        },
        "split": {"train": 0.64, "validation": 0.16, "test": 0.20, "stratified": True},
        "calibration": {
            "method": "isotonic regression",
            "fitted_on": "validation slice (16% of all rows), never the test set",
            "reason": (
                "scale_pos_weight makes predict_proba exceed the real default "
                "frequency; the PD quoted downstream is the calibrated value"
            ),
        },
        "test": overall,
        "validation": valid,
        "test_per_horizon": per_horizon,
        "feature_importance": {name: round(value, 4) for name, value in importances},
    }

    if args.no_save:
        print("\n--no-save given; model and metrics not written")
        return 0

    os.makedirs(MODELS_DIR, exist_ok=True)
    # One bundle, so inference cannot load a booster without the calibrator that
    # turns its score into a probability, or without the feature order it was
    # fitted on.
    joblib.dump(
        {
            "model": model,
            "calibrator": calibrator,
            "features": list(FEATURES),
            "trained_at": metrics["trained_at"],
            "test_metrics": overall,
        },
        MODEL_PATH,
    )
    with open(METRICS_PATH, "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print(f"\nWrote {MODEL_PATH}")
    print(f"Wrote {METRICS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
