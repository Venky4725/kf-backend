import logging
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    log_level = "DEBUG" if settings.ENVIRONMENT.lower() == "development" else "INFO"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": log_level,
                }
            },
            "root": {
                "handlers": ["default"],
                "level": log_level,
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
