import logging.handlers

from roster_agent_runtime import constants, settings

logger = logging.getLogger(constants.LOGGER_NAME)
logger.setLevel(settings.LOG_LEVEL)

logs_enabled = False


def setup_logging():
    global logs_enabled
    if logs_enabled:
        # logging already setup,
        # don't add new handlers
        return
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_log_format = "%(levelname)s:\t [log] %(message)s"
    console_format = logging.Formatter(console_log_format)
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(settings.LOG, maxBytes=1000000)
    file_handler.setLevel(logging.DEBUG)
    file_log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_format = logging.Formatter(file_log_format)
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    logs_enabled = True


def app_logger():
    setup_logging()
    return logger
