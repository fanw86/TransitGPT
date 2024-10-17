import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as install_rich_traceback


def setup_logger(log_file):
    # Install rich traceback handler
    install_rich_traceback()

    # Create a Rich console
    console = Console(force_terminal=True)

    # Create or get logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Generate a new log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_log_file = f"{os.path.splitext(log_file)[0]}_{timestamp}.log"

    # Create RichHandler for console output
    rich_handler = RichHandler(
        console=console, rich_tracebacks=True, tracebacks_show_locals=True
    )
    rich_handler.setLevel(logging.DEBUG)

    # Create a RotatingFileHandler for file output
    file_handler = RotatingFileHandler(
        new_log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # Use the same formatter for both handlers
    rich_formatter = logging.Formatter("%(message)s")
    rich_handler.setFormatter(rich_formatter)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Add the new handlers to the logger
    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)

    logger.info(f"New log file created: {new_log_file}")

    return logger


def reset_logger(logger, log_file):
    # Remove all handlers from the logger
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # Remove the logger from the logging module's dict
    if logger.name in logging.Logger.manager.loggerDict:
        del logging.Logger.manager.loggerDict[logger.name]

    # Create a new logger instance
    new_logger = setup_logger(log_file)
    new_logger.info("Logger reset and reinitialized")

    return new_logger
