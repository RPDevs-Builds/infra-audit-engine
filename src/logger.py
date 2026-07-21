# Path: src/logger.py

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_system_logger(project_root: Path) -> logging.Logger:
    """Configures comprehensive global logging for the entire application."""
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "infrastructure_audit.log"

    # Configure the root logger
    root_logger = logging.getLogger()
    
    # Prevent duplicate handlers if initialized multiple times
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Rotating File Handler (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Silence overwhelmingly noisy third-party libraries
    logging.getLogger("asyncssh").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logging.getLogger("Orchestrator")
