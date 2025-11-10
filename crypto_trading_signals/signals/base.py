from abc import ABC, abstractmethod
from crypto_trading_signals.core.logger import Logger
from crypto_trading_signals.core.config import Config

class SignalBase(ABC):
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger

    @abstractmethod
    async def preload(self, exchange, symbols, intervals):
        """Load historical candles. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def evaluate(self, symbol, interval, last_candle):
        """Load historical candles. Must be implemented by subclasses."""
        pass