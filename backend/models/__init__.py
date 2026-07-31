"""Re-export every model so importing this package registers all tables on
Base.metadata. main.py calls create_all() before the routers are imported, so
any model not reachable from here would never get its table created."""
from models.company import Company
from models.analysis import Analysis
from models.fraud import FraudSignal
from models.ews import EWSSignal, EWSTrajectory
from models.user import User
from models.draft import FormDraft

__all__ = [
    "Company",
    "Analysis",
    "FraudSignal",
    "EWSSignal",
    "EWSTrajectory",
    "User",
    "FormDraft",
]
