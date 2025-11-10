import pandas as pd
from ta.trend import EMAIndicator
from crypto_trading_signals.core.logger import Logger
from crypto_trading_signals.core.config import Config
from crypto_trading_signals.core.notification import Message
from ccxt.async_support import binanceusdm
from crypto_trading_signals.signals.base import SignalBase
import mplfinance as mpf
import pytz
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt

class EMA200Signal(SignalBase):
    def __init__(self, config: Config, logger: Logger):
        super().__init__(config, logger)
        self.cache = {}  # {(symbol, interval): df}
        self.limit = 500
        self.threshold = 0.002    # 0.2% distance near EMA200
        self.lookback = 21       # candles for mean check

    async def preload(self, exchange: binanceusdm, symbols, intervals):
        """
        Load historical candles and store in self.cache
        """
        for symbol in symbols:
            for interval in intervals:
                try:
                    candles = await exchange.fetch_ohlcv(symbol, interval, limit=self.limit)
                    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    self.cache[(symbol, interval)] = df
                    self.logger.info(f"Preloaded {len(df)} candles for {symbol} {interval}")
                except Exception as e:
                    self.logger.error(f"Error preloading {symbol} {interval}: {e}")

    def evaluate(self, symbol, interval, last_candle):
        """
        Evaluate EMA200 crossover signal
        Return Message if signal detected, else None
        """
        key = (symbol, interval)
        if key not in self.cache:
            return None
        
        df = self.cache[key]

        # Prepare last candle
        last_ts = pd.to_datetime(last_candle[0], unit="ms")
        new_row = pd.DataFrame([{
            "timestamp": last_ts,
            "open": last_candle[1],
            "high": last_candle[2],
            "low": last_candle[3],
            "close": last_candle[4],
            "volume": last_candle[5]
        }])

        if df["timestamp"].iloc[-1] < last_ts:
            # New candle → append
            df = pd.concat([df, new_row], ignore_index=True)
        elif df["timestamp"].iloc[-1] == last_ts:
            # Same candle → update last row
            df.iloc[-1] = new_row.iloc[0]

        # Keep only last limits candles
        df = df.tail(self.limit).reset_index(drop=True)
        self.cache[key] = df

        # Compute EMA200
        ema200 = EMAIndicator(df["close"], window=200).ema_indicator()
        ema_value = ema200.iloc[-1]
        last_close = df["close"].iloc[-1]

        # Compute distance ratio
        distance = abs(last_close - ema_value) / ema_value

        # Only trigger if close is near EMA200
        signal = None
        emoji = "⚪"

        if distance <= self.threshold:
            mean_close = df["close"].tail(self.lookback).mean()
            if mean_close > ema_value:
                signal = "LONG"
                emoji = "🟢"
            elif mean_close < ema_value:
                signal = "SHORT"
                emoji = "🔴"
    
        if signal:
            df_chart = df.tail(self.lookback).copy()
            df_chart["EMA200"] = ema200.tail(self.lookback).values
            df_chart.set_index("timestamp", inplace=True)

            ymin = min(df_chart['low'].min(), df_chart['EMA200'].min())
            ymax = max(df_chart['high'].max(), df_chart['EMA200'].max())

            # Market colors
            mc = mpf.make_marketcolors(
                up='green',
                down='red',
                edge='inherit',
                wick='black',
                volume='in'
            )

            # Style
            s = mpf.make_mpf_style(
                base_mpl_style='bmh',
                marketcolors=mc,
                gridstyle='-.',
                gridcolor='gray'
            )

            # Add EMA200 line
            addplots = [mpf.make_addplot(df_chart["EMA200"], color='orange', width=1.5, label="EMA200")]

            buf = BytesIO()
            fig, axlist = mpf.plot(
                df_chart,
                type='candle',
                style=s,
                addplot=addplots,
                volume=False,
                ylabel="Price",
                figsize=(8, 5),
                returnfig=True,
                tight_layout=True,
                ylim=(ymin * 0.998, ymax * 1.002),
            )
            axlist[0].set_title(f"{symbol} {interval} - Near EMA200 {signal}")
            fig.savefig(buf, format="png", bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)

            # Build message
            body = (
                f"Close Price: **{last_close}**\n"
                f"EMA200: **{ema_value:.6f}**\n"
                f"Distance: **{distance * 100:.2f}%**\n"
                f"Time: **{datetime.now(pytz.timezone(self.config.TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')} {self.config.TIMEZONE}**\n"
                f"[🔗 Open in Binance Chart](https://www.binance.com/en/futures/{symbol})"
            )
            title = f"EMA200 Signal - {symbol} {interval} - {emoji} {signal}"

            return Message(
                body=body,
                chat_id=self.config.TELEGRAM_CHAT_ID,
                title=title,
                image=buf
            )



        return None