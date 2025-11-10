import os
import platform

from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load .env only if it exists (so production won't break)
        load_dotenv(dotenv_path=".env", override=False)
        # Telegram
        self.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_LOG_PEER_ID = int(os.environ.get("TELEGRAM_LOG_PEER_ID", -1))
        self.TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", -1))

        # Binance
        self.BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
        self.BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
        self.BINANCE_TLD = os.environ.get("BINANCE_TLD", "com")
        self.BINANCE_PROXY_URL = os.environ.get("BINANCE_PROXY_URL", "")

        # General
        self.TIMEZONE = os.environ.get("TIMEZONE", "Asia/Ho_Chi_Minh")
        self.TOP_SYMBOLS = int(os.environ.get("TOP_SYMBOLS", 5))
        self.INTERVALS = [interval.strip() for interval in os.environ.get("INTERVALS", "15m 1h 4h").split() if interval.strip()]

    def beautify(self):
        response = {}
        response["platform"] = platform.system()
        response["BINANCE_API_KEY"] = "...."
        response["BINANCE_API_SECRET"] = "...."
        return response