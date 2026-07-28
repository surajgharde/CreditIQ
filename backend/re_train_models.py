import os
import sys
import logging

# Set up logging for output visibility
logging.basicConfig(level=logging.INFO)

# Set up Python path so it can import services
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import the service
from services import scoring_service

print("Triggering re-training of XGBoost models...")
try:
    # Set environment variables for Kaggle if they aren't already set (they should be loaded in scoring_service if it's imported correctly but better safe)
    from dotenv import load_dotenv
    load_dotenv()
    
    scoring_service.ensure_models_trained()
    print("Re-training complete!")
except Exception as e:
    import traceback
    print(f"Error during re-training: {e}")
    traceback.print_exc()
