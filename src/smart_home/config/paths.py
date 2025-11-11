# src/smart_home/config/paths.py
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR    = Path(os.getenv("SMART_HOME_DATA_DIR", PROJECT_ROOT / "data"))
MODELS_DIR  = Path(os.getenv("SMART_HOME_MODELS_DIR", PROJECT_ROOT / "models"))
AGENT_LOGS_DIR = PROJECT_ROOT / "logs"  # Top-level logs directory for agent conversations
for p in (DATA_DIR, MODELS_DIR, AGENT_LOGS_DIR): p.mkdir(parents=True, exist_ok=True)