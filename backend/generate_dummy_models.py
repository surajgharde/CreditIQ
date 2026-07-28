import os
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb

MODELS_DIR = r"c:\Users\HP\OneDrive\Documents\HEMANT\CODEAPEX\Vivriti\backend\models\xgboost"
os.makedirs(MODELS_DIR, exist_ok=True)

# Define the exact features used by the application
features = [
    "current_ratio", "debt_to_equity", "interest_coverage", 
    "revenue_growth_percent", "ebitda_margin_percent", 
    "data_quality_score", "fraud_risk_score", "news_risk_score", 
    "gst_filing_irregularity", "loan_to_revenue_ratio", 
    "debt_service_coverage", "sector_encoded"
]

# Generate dummy data for 100 samples
X = pd.DataFrame(np.random.rand(100, len(features)), columns=features)
y = np.random.randint(0, 2, 100)

# Train a small model
model = xgb.XGBClassifier(n_estimators=10, max_depth=3, random_state=42)
model.fit(X, y)

# Save as base model
base_model_path = os.path.join(MODELS_DIR, "xgboost_creditiq_model.pkl")
joblib.dump(model, base_model_path)
print(f"Saved dummy base model to {base_model_path}")

# Create sector specific copies
sectors = ["manufacturing", "real_estate", "trading", "services", "renewable"]
for sector in sectors:
    path = os.path.join(MODELS_DIR, f"{sector}_model.pkl")
    joblib.dump(model, path)
    print(f"Saved dummy {sector} model to {path}")

print("Dummy models generated successfully!")
