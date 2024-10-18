import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as install_rich_traceback
from rich.text import Text
import pytz  # Add this import


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

    # Create RichHandler for console output
    rich_handler = RichHandler(
        console=console, rich_tracebacks=True, tracebacks_show_locals=True,
        markup=True  # Enable markup parsing
    )
    rich_handler.setLevel(logging.DEBUG)

    # Use the custom formatter for RichHandler
    rich_formatter = RichColorFormatter("%(message)s")
    rich_handler.setFormatter(rich_formatter)

    # Create a RotatingFileHandler for file output
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # Create formatters
    file_formatter = CSTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = CSTFormatter('%(message)s')

    # Set formatters for handlers
    file_handler.setFormatter(file_formatter)
    rich_handler.setFormatter(console_formatter)

    # Add the new handlers to the logger
    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)

    logger.info(f"Logging to file: {log_file}")

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


class RichColorFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return Text.from_markup(message)


class CSTFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp)
        cst_tz = pytz.timezone('America/Chicago')
        return dt.replace(tzinfo=pytz.UTC).astimezone(cst_tz)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
