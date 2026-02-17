import os
from dotenv import load_dotenv

load_dotenv()

# Binance API
API_KEY = os.getenv('BINANCE_API_KEY', 'dummy_key')
API_SECRET = os.getenv('BINANCE_API_SECRET', 'dummy_secret')

# Settings
SYMBOL = 'BTCUSDT'
LEVERAGE = 10
