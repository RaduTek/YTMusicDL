import logging
import os
from typing import cast
from ytmusicdl.config import Config

STATUS_LEVEL_NUM = 25
SUCCESS_LEVEL_NUM = 35


class CustomLogger(logging.getLoggerClass()):
    STATUS = STATUS_LEVEL_NUM
    SUCCESS = SUCCESS_LEVEL_NUM

    def status(self, msg: object, *args: object, **kwargs: object) -> None:
        """
        Log 'msg % args' with severity 'STATUS'.
        """
        if self.isEnabledFor(self.STATUS):
            self._log(self.STATUS, msg, args, **kwargs)

    def success(self, msg: object, *args: object, **kwargs: object) -> None:
        """
        Log 'msg % args' with severity 'SUCCESS'.
        """
        if self.isEnabledFor(self.SUCCESS):
            self._log(self.SUCCESS, msg, args, **kwargs)


logging.setLoggerClass(CustomLogger)
logging.addLevelName(STATUS_LEVEL_NUM, "STATUS")
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


class CustomStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelname == "STATUS":
                # End with carriage return and no newline
                if self.level <= logging.DEBUG:
                    # If debug level, overwrite the line
                    msg += "\n"
                self.stream.write("\r\x1b[2K" + msg)
                self.flush()
            else:
                # Default behavior: newline at the end
                self.stream.write("\x1b[2K\r" + msg + "\n")
                self.flush()
        except Exception:
            self.handleError(record)


class EmojiFormatter(logging.Formatter):
    EMOJI_MAP = {
        "DEBUG": "🐛",
        "INFO": "ℹ️ ",
        "STATUS": "🔄",
        "SUCCESS": "✅",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }

    def format(self, record: logging.LogRecord) -> str:
        emoji = self.EMOJI_MAP.get(record.levelname, "")
        # Customize the format here
        formatted_message = super().format(record)
        return f"{emoji} {formatted_message}"


class CountingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.error_count = 0
        self.warning_count = 0
        self.success_count = 0

    def emit(self, record):
        if record.levelno == logging.ERROR:
            self.error_count += 1
        elif record.levelno == logging.WARNING:
            self.warning_count += 1
        elif record.levelno == CustomLogger.SUCCESS:
            self.success_count += 1

    def reset_counts(self):
        """Reset the counts for errors, warnings, and successes."""
        self.error_count = 0
        self.warning_count = 0
        self.success_count = 0


def init_logger(config: Config) -> CustomLogger:
    """Initialize the logger for YTMusicDL."""

    log = cast(CustomLogger, logging.getLogger("YTMusicDL"))
    log.propagate = False
    log.setLevel(
        logging.DEBUG if config["log_verbose"] or config["verbose"] else logging.INFO
    )

    # Configure logger to show info messages on stdout
    console_handler = CustomStreamHandler()
    console_handler.setLevel(logging.DEBUG if config["verbose"] else logging.INFO)
    if config["emojis"]:
        console_formatter = EmojiFormatter("%(message)s")
    else:
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)

    # Add a counting handler to track errors and warnings
    counting_handler = CountingHandler()
    counting_handler.setLevel(logging.WARNING)
    log.addHandler(counting_handler)
    log.counting_handler = counting_handler

    # Setup logging to file
    if type(config["log"]) is str:
        log_file = config["log"]
        log_file = os.path.join(config["base_path"], log_file)
        log_level = logging.DEBUG if config["log_verbose"] else logging.INFO

        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        log_file_handler = logging.FileHandler(log_file)
        log_file_handler.setLevel(log_level)
        log_file_formatter = logging.Formatter(
            "%(asctime)s: %(levelname)s: %(message)s"
        )
        log_file_handler.setFormatter(log_file_formatter)
        log.addHandler(log_file_handler)

    return log


def get_logger() -> CustomLogger:
    """Get the logger instance for YTMusicDL."""
    return logging.getLogger("YTMusicDL")


def print_stats(print_success: bool = True):
    """Print the statistics of the logger."""

    log = get_logger()

    if not hasattr(log, "counting_handler"):
        log.warning("No statistics available.")
        return

    counting_handler = cast(CountingHandler, log.counting_handler)

    success_count = counting_handler.success_count
    error_count = counting_handler.error_count
    warning_count = counting_handler.warning_count

    message = "Download "
    message += "completed " if success_count > 0 else "failed "
    message += "with " if error_count > 0 or warning_count > 0 else ""
    message += f"{error_count} errors " if error_count > 0 else ""
    message += f"{warning_count} warnings " if warning_count > 0 else ""
    message = message.strip() + "."

    if error_count > 0 or success_count == 0:
        log.error(message)
    elif warning_count > 0:
        log.warning(message)
    elif success_count > 0 and print_success:
        log.success(message)
