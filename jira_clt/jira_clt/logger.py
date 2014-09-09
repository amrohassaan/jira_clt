## @package jira_clt.logger
#
# Setting up the logger.

import os
import logging.handlers
import time


logger = logging.getLogger('jira_clt')
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter("(%(asctime)s):%(levelname)s:%(name)s :: %(message)s")

console_handler = None
file_handler = None


def enable_file_logging(log_dir=None, log_file=None, log_level=logging.DEBUG):
    """Setup logging module to output logged messages to a file.

    @param log_dir Destination folder path for log file. Default: None - Use current folder.
    @param log_file Name of log file. Default: None - Create a filename using timestamp.
    @param log_level Log level for messages output to log file. Default: logging.DEBUG

    @return The log file path
    """
    global file_handler
    if log_dir is None:
        log_dir = os.getcwd()

    if log_file:
        log_file = '%s_%s.log' % (log_file, time.strftime('%d-%B_%H-%M'))
    else:
        log_file = 'efforts_%s.log' % time.strftime('%d-%B_%H-%M')

    log_path = os.path.join(log_dir, log_file)

    file_handler = logging.handlers.RotatingFileHandler(log_path, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
    return log_path


def enable_console_logging(log_level=logging.INFO):
    """Setup logging module to output logged messages to console.

    @param log_level Log level for messages output to console.
        Default: logging.INFO
    """
    global console_handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)


def set_console_level(log_level):
    """Set the console log level

    @param log_level The level to set (ie. logging.DEBUG, logging.WARN, etc...)
    """
    global console_handler
    if console_handler:
        console_handler.setLevel(log_level)
    else:
        logger.warn('Console logger has not been enabled')


def set_console_format(format_string):
    """Set the format of the console log handler

    @param format_string The format string for the log
    """
    global console_handler
    log_formatter = logging.Formatter(format_string)
    if console_handler:
        console_handler.setFormatter(log_formatter)
    else:
        logger.warn('Console logger has not been enabled')
