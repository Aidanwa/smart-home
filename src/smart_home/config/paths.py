# src/smart_home/config/paths.py
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR    = Path(os.getenv("SMART_HOME_DATA_DIR", PROJECT_ROOT / "data"))
MODELS_DIR  = Path(os.getenv("SMART_HOME_MODELS_DIR", PROJECT_ROOT / "models"))
LOG_DIR     = DATA_DIR / "logs"
CACHE_DIR   = DATA_DIR / "cache"
for p in (DATA_DIR, LOG_DIR, CACHE_DIR): p.mkdir(parents=True, exist_ok=True)