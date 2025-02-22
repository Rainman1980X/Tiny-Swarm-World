import logging
import os

class LoggerFactory:
    """
    A central logger factory class for logging within the application.
    This class ensures that loggers are instance-bound and do not have duplicate FileHandlers.
    It can be used in any other class via dependency injection.
    """

    @staticmethod
    def get_logger(cls, log_dir: str = "logs", level: int = logging.INFO):
        """
        Creates or returns a logger for the given class.

        :param cls: The class reference or class name as a string.
        :param log_dir: Directory for log files.
        :param level: Logging level.
        :return: Configured logger.
        """
        class_name = cls.__name__ if isinstance(cls, type) else str(cls)
        log_file = os.path.join(log_dir, f"{class_name}.log")

        # Ensure the log directory exists
        os.makedirs(log_dir, exist_ok=True)

        logger = logging.getLogger(class_name)
        logger.setLevel(level)

        # Remove duplicate FileHandlers
        if logger.hasHandlers():
            for handler in logger.handlers[:]:  # Copy the list to iterate safely
                if isinstance(handler, logging.FileHandler):
                    logger.removeHandler(handler)

        # Add file handler if none exists
        file_handler = logging.FileHandler(log_file, mode="a")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger
