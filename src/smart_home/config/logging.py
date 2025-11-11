# src/smart_home/config/logging.py
import logging
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra context fields if present
        for field in ['agent_id', 'tool_name', 'provider', 'model']:
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        # Include exception info if present
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)

        return json.dumps(payload)

def configure(level=None, log_file=None):
    """
    Configure logging with JSON formatting and optional file output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
               Defaults to LOG_LEVEL env var or INFO.
        log_file: Optional file path for persistent logs.
                  Defaults to data/logs/app.log if not specified.
    """
    # Determine log level from env var or parameter
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Determine log file path
    if log_file is None:
        from smart_home.config.paths import DATA_DIR
        log_dir = DATA_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"

    # JSON formatter for structured logging
    json_formatter = JsonFormatter()

    # Console handler - outputs JSON for structured logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(level)

    handlers = [console_handler]

    # File handler with rotation (10MB max, 5 backups = ~60MB total)
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(json_formatter)
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        handlers.append(file_handler)

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # Capture everything, handlers filter by level
    root.handlers[:] = handlers

    # Silence noisy third-party libraries (unless user explicitly wants DEBUG for everything)
    # These libraries spam debug logs with internal operations
    if level == "DEBUG":
        # In DEBUG mode, still silence extremely verbose libraries
        logging.getLogger("comtypes").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.INFO)
        logging.getLogger("requests").setLevel(logging.INFO)
        logging.getLogger("charset_normalizer").setLevel(logging.INFO)
