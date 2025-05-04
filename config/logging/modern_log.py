import logging
import inspect
import os
from rich.logging import RichHandler

FORMAT = "[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class LoggingConfig:
    def __init__(self, level: str = "DEBUG", level_console: str = "INFO", log_file: str = None):
        os.makedirs("tmp", exist_ok=True) 
        logger = logging.getLogger()

        if log_file is None:
            caller_frame = inspect.stack()[1]
            caller_filename = os.path.basename(caller_frame.filename)
            base_name = os.path.splitext(caller_filename)[0]
            log_file = f"{base_name}.log"
        
        # Console handler
        console_handler = RichHandler(level=level_console, rich_tracebacks=True)
        console_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))

        # File handler
        file_handler = logging.FileHandler(f"tmp/{log_file}", encoding="utf-8")
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(logging.Formatter(fmt=FORMAT, datefmt=DATE_FORMAT))

        if not logger.handlers:
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        
        logger.setLevel(level)
    
    def get_logger(self, name: str = __name__):
        return logging.getLogger(name)