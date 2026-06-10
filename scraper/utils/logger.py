"""
Logging setup for the JamesAllen scraper.
Uses Python's logging module with Rich for beautiful console output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from rich.logging import RichHandler
from rich.console import Console

import config

console = Console()

def setup_logger(name: str = "scraper", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with both console (Rich) and file handlers.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # ── Console handler (Rich) ────────────────────────────────────────────
    console_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(level)
    console_fmt = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # ── File handler ──────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = config.LOG_DIR / f"scrape_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    logger.info(f"Log file: {log_file}")
    return logger
