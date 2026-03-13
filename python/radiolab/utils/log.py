"""Logging helpers for the RadioLab multiprocessing pipeline.

Call configure_logging() at the top of every worker function (after fork)
so each process gets its own named logger with a consistent format.
"""

import logging
import sys


def configure_logging(level: str = "INFO", process_name: str = "main") -> None:
    """Configure the root logger for the calling process.

    Args:
        level: Log level string: DEBUG, INFO, WARNING, ERROR, CRITICAL.
        process_name: Short name embedded in every log line, e.g. "rx", "dsp".
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    fmt = f"[%(asctime)s] [{process_name}] %(levelname)-8s %(name)s: %(message)s"
    logging.basicConfig(
        level=numeric_level,
        format=fmt,
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True,  # override any previously-set handlers (safe after fork)
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.  Call after configure_logging()."""
    return logging.getLogger(name)
