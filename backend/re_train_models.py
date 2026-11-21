"""
Deprecated entry point. Training lives in `train_model.py`.

This script used to call `scoring_service.ensure_models_trained()`, which
downloaded the Home Credit consumer-loan dataset and wrote six model files from
it. That function is gone: the model is now trained on firm-level financial
ratios by `train_model.py`, which also writes its held-out metrics.

    python train_model.py
"""
import sys

print(__doc__)
sys.exit(1)
