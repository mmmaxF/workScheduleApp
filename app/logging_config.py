import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "logs/app.log")
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "1048576"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
