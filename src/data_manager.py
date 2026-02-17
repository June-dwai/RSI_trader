import pandas as pd
from binance.client import Client
from loguru import logger

class DataManager:
    def __init__(self, api_key=None, api_secret=None, symbol='BTCUSDT', timeframe='1m', testnet=False):
        self.client = Client(api_key, api_secret, testnet=testnet)
        self.symbol = symbol
        self.timeframe = timeframe

    def fetch_historical_data(self, start_date, end_date):
        """
        Fetch historical kline data from Binance
        """
        logger.info(f"Fetching {self.timeframe} data for {self.symbol} from {start_date} to {end_date}")
        
        # Map timeframe to client constant
        interval_map = {
            '1m': Client.KLINE_INTERVAL_1MINUTE,
            '4h': Client.KLINE_INTERVAL_4HOUR,
            '1d': Client.KLINE_INTERVAL_1DAY
        }
        interval = interval_map.get(self.timeframe, Client.KLINE_INTERVAL_1MINUTE)

        klines = self.client.futures_historical_klines(
            self.symbol,
            interval,
            start_str=start_date,
            end_str=end_date
        )

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
        ])

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Convert numeric columns
        cols = ['open', 'high', 'low', 'close', 'volume']
        for col in cols:
            df[col] = pd.to_numeric(df[col])

        return df
