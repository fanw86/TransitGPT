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
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create a RichHandler
    rich_handler = RichHandler(rich_tracebacks=True)
    rich_handler.setLevel(logging.INFO)

    # Create a file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create a formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(rich_handler)
    logger.addHandler(file_handler)

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
        return cst_tz.localize(dt)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
