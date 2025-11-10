import logging.handlers
import queue

from .notification import NotificationHandler
from .config import Config
import datetime
import pytz
import sys
class Logger:
    Logger = None

    # Update: use async logging to improve performence, log messages are queued and processed in a separate thread.
    def __init__(self, config: Config, notificationHandler: NotificationHandler, logging_service="crypto_trading"):
        # Logger setup
        log_queue = queue.SimpleQueue() # shared Queue, infinite size
        queue_handler = logging.handlers.QueueHandler(log_queue)
        self.Logger = logging.getLogger(logging_service)
        self.Logger.setLevel(logging.INFO)
        self.Logger.propagate = False
        self.Logger.addHandler(queue_handler)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        formatter.converter = lambda *args: datetime.datetime.now(tz=pytz.timezone(config.TIMEZONE)).timetuple()
        # default is "logs/crypto_trading.log"
        fh = logging.FileHandler(f"logs/{logging_service}.log")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        # self.Logger.addHandler(fh)

        # logging to console
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)
        # self.Logger.addHandler(ch)

        queue_listener = logging.handlers.QueueListener(
            log_queue, fh, sh
        )
        queue_listener.start()
        # notification handler
        self.NotificationHandler = notificationHandler

    def log(self, level, msg, *args, **kwargs):
        # Extract `notification` if provided, default False
        notification = kwargs.pop("notification", False)

        # Call the actual logger method
        log_method = getattr(self.Logger, level.lower(), None)
        if callable(log_method):
            log_method(str(msg), *args, **kwargs)

        # Optional notification
        if notification and self.NotificationHandler.enabled:
            self.NotificationHandler.send_notification(msg)

    def info(self, msg, *args, **kwargs):
        self.log("info", msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log("warning", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log("error", msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log("debug", msg, *args, **kwargs)