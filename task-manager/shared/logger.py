import os
import logging
from datetime import datetime

# Pattern 2: Structured Logging — daily log files in logs/
def get_logger(name="task-manager"):
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, f"task-manager-{datetime.now().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(fh)
    return logger

log = get_logger()
