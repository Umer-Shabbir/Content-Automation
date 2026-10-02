import logging
from PySide6.QtCore import QObject, Signal


class SignaledLogHandler(logging.Handler, QObject):
    """
    Custom logging Handler that inherits from logging.Handler and QObject,
    emitting a Qt Signal whenever a log record is processed.
    """
    new_log = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.new_log.emit(msg)
        except Exception:
            self.handleError(record)
