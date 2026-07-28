import sys, os, traceback, logging
logging.disable(logging.CRITICAL)
import warnings; warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

print("Testing main.py imports...")
errors = []

mods = [
    "database",
    "models.company",
    "models.analysis",
    "models.ews",
    "routers.upload",
    "routers.analyze",
    "routers.fraud",
    "routers.scoring",
    "routers.cam",
    "routers.ews",
    "routers.health",
    "routers.ws",
    "utils.demo_data",
]

for m in mods:
    try:
        __import__(m)
        print(f"  OK   {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")
        errors.append((m, str(e)))

print()
if errors:
    print(f"ERRORS ({len(errors)}):")
    for mod, err in errors:
        print(f"  {mod}: {err}")
        traceback.print_exc()
else:
    print("ALL IMPORTS OK")
