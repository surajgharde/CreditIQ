import joblib
import os
import xgboost as xgb

MODELS_DIR = r"c:\Users\HP\OneDrive\Documents\HEMANT\CODEAPEX\Vivriti\backend\models\xgboost"
model_path = os.path.join(MODELS_DIR, "xgboost_creditiq_model.pkl")

if os.path.exists(model_path):
    try:
        model = joblib.load(model_path)
        if hasattr(model, 'n_features_in_'):
            print(f"Base model n_features_in_: {model.n_features_in_}")
        elif hasattr(model, 'feature_names_in_'):
             print(f"Base model feature_names_in_ len: {len(model.feature_names_in_)}")
        else:
             print("Model has no metadata on input features.")
    except Exception as e:
        print(f"Error loading model: {e}")
else:
    print("Model not found.")
