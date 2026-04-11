from __future__ import annotations

import logging
from pathlib import Path


def setup_stage_logger(stage_name: str, log_file: Path) -> logging.Logger:
    """
    Setup structured logger for a pipeline stage.

    Args:
        stage_name: Name of the stage (e.g., "stage1", "stage2")
        log_file: Path to log file

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"entity_resolution.{stage_name}")

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Create log directory if needed
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
