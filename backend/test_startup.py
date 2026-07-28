import sys, traceback, logging
logging.disable(logging.CRITICAL)
import warnings; warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

print("Starting CreditIQ app...")
try:
    import main
    print("main.py loaded OK")
    print("App title:", main.app.title)
except Exception as e:
    print("\n=== STARTUP ERROR ===")
    traceback.print_exc()
