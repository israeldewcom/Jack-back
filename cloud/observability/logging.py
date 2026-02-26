"""
Structured JSON logging.
"""
import logging
import json
from datetime import datetime
import sys

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def _log(self, level, message, **kwargs):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "module": self.logger.name,
            **kwargs
        }
        self.logger.log(level, json.dumps(record))

    def info(self, message, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def error(self, message, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def warning(self, message, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def debug(self, message, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

def setup_logging():
    """Configure root logger to use structured JSON."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    root.handlers = [handler]
    # Override for our modules
    logging.getLogger("cloud").setLevel(logging.DEBUG if os.getenv("DEBUG") else logging.INFO)
