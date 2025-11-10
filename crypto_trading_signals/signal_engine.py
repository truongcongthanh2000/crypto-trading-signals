import asyncio
import ccxt.pro
import ccxt.async_support
from .core.config import Config
from .core.logger import Logger
from .signals.base import SignalBase
from .signals.ema200 import EMA200Signal
import pytz
from datetime import datetime
from .util import convert_to_seconds

class SignalEngine:
    def __init__(self, config: Config, logger: Logger):
        self.exchange_ws = ccxt.pro.binanceusdm({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET
        })
        self.exchange = ccxt.async_support.binanceusdm({
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_API_SECRET
        })
        self.config = config
        self.logger = logger
        self.signals: list[SignalBase] = [] # list of SignalBase
        self.symbol_ids = []
        self.map_symbol = {}
        self.last_signal_time = {}  # {(symbol, interval): datetime}

    # ---------------- Step 1: Get top symbols ----------------
    async def get_top_symbols(self):
        markets = await self.exchange.load_markets()
        tickers = await self.exchange.fetch_tickers()
        
        # build map_symbol: market_symbol -> market_id
        self.map_symbol = {m["symbol"]: m["id"] for m in markets.values()}

        symbol_ids = sorted(
            [m["id"] for m in markets.values()
             if m.get("quote") == "USDT" and m.get("active") and m.get("contract")],
            key=lambda s: tickers[s]["quoteVolume"] if s in tickers else 0,
            reverse=True
        )[:self.config.TOP_SYMBOLS]
        self.symbol_ids = symbol_ids
        self.logger.info(f"Loaded top {len(symbol_ids)} symbols: {symbol_ids}")

    # ---------------- Step 2: Preload historical candles ----------------
    async def preload_historical(self):
        self.signals = [EMA200Signal(self.config, self.logger)]
        for signal in self.signals:
            await signal.preload(self.exchange, self.symbol_ids, self.config.INTERVALS)

    # ---------------- Step 3: Run realtime watch_ohlcv_for_symbols ----------------
    async def run_realtime(self):
        subscriptions = [[symbol, interval] for symbol in self.symbol_ids for interval in self.config.INTERVALS]

        while True:
            try:
                ohlcvs = await self.exchange_ws.watch_ohlcv_for_symbols(subscriptions)
                # format: {symbol: {interval: list_of_candles}}
                for symbol, intervals_dict in ohlcvs.items():
                    symbol_id = self.map_symbol[symbol]
                    for interval, candles in intervals_dict.items():
                        last_candle = candles[-1]
                        for signal in self.signals:
                            msg = signal.evaluate(symbol_id, interval, last_candle)
                            if msg:
                                # ---------- Throttle message ----------
                                key = (symbol_id, interval)
                                tz = pytz.timezone(self.config.TIMEZONE)
                                now = datetime.now(tz)

                                last_sent: datetime = self.last_signal_time.get(key)
                                if last_sent and (now - last_sent).total_seconds() < convert_to_seconds(interval):
                                    continue  # only send 1 signal during interval

                                self.last_signal_time[key] = now
                                # ---------- End Throttle ----------
                                self.logger.info(msg, notification=True)
            except Exception as e:
                self.logger.error(f"watch_ohlcv_for_symbols error: {e}")
                await asyncio.sleep(5)  # reconnect delay

    # ---------------- Step 4: Run engine ----------------
    async def run(self):
        await self.get_top_symbols()
        await self.preload_historical()
        await self.run_realtime()

    async def close(self):
        await self.exchange_ws.close()
        await self.exchange.close()