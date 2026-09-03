import sys
import os
from datetime import datetime, timezone

# Add parent directory to path to allow imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.core.config import GOLDEN_WINDOW_MINUTES, HIGH_RISK_THRESHOLD
    from app.core.data_store import data_store
    from app.engines.scoring_engine import score_transaction
    from app.engines.case_manager import process_scored_tx
    
    print("All modules imported successfully.")
    
    tx = {
        "tx_id": "TX-TEST-RUNNER",
        "sender_account": "ACC-1001",
        "receiver_account": "ACC-1002",
        "amount": 150.50,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel": "WEB"
    }
    data_store["transactions"][tx["tx_id"]] = tx
    print(f"Created Test Transaction: {tx['tx_id']}")
    print("Test passed.")
    
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Test failed with error: {e}")
    sys.exit(1)
