import logging
import os
from datetime import datetime
from rich.logging import RichHandler
from rich.traceback import install as install_rich_traceback
import pytz

install_rich_traceback()

class CSTFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        cst_tz = pytz.timezone("America/Chicago")
        return dt.astimezone(cst_tz)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%B %d, %Y %H:%M:%S %Z")


def setup_logger(log_file):
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create and configure file handler separately
    file_handler = logging.FileHandler(log_file, mode="w")
    formatter = CSTFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    
    # Configure rich handler separately
    rich_handler = RichHandler(markup=True, rich_tracebacks=True)
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[rich_handler, file_handler],
        force=True,
    )

    logger = logging.getLogger(__name__)
    return logger


def reset_logger(logger, log_file):
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    if logger.name in logging.Logger.manager.loggerDict:
        del logging.Logger.manager.loggerDict[logger.name]

    new_logger = setup_logger(log_file)
    new_logger.info("Logger reset and reinitialized")

    return new_logger
