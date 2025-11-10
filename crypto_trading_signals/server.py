from .core.logger import Logger
from .core.config import Config
from .core.notification import NotificationHandler
from .signal_engine import SignalEngine
import asyncio

async def main():
    config = Config()
    notification = NotificationHandler(config)
    logger = Logger(config, notification, "signals_trade_server")

    try:
        signal_engine = SignalEngine(config, logger)
        task1 = asyncio.create_task(notification.process_queue())
        task2 = asyncio.create_task(signal_engine.run())

        await asyncio.gather(task1, task2)
    finally:
        await signal_engine.close()
        logger.info("Exchange connection closed cleanly.")
        
