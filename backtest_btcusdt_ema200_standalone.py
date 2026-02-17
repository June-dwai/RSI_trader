from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


SYMBOL = "BTCUSDT"
INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
ENTRY_SCALE = 0.50
DATA_DIR = Path("historical_data_mainnet")
BACKTEST_START = "2022-01-01"
BACKTEST_END = "2026-02-12"


def _load_cached_df(symbol: str, timeframe: str, periods: list[tuple[str, str]]) -> pd.DataFrame:
    frames = []
    for start_date, end_date in periods:
        path = DATA_DIR / f"{symbol}_{timeframe}_{start_date}_{end_date}.pkl"
        if not path.exists():
            raise FileNotFoundError(f"Missing cache file: {path}")
        df = pd.read_pickle(path)
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames)
    out = out[~out.index.duplicated(keep='first')].sort_index()
    return out


def _clean_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = df.copy()

    q1 = out["close"].quantile(0.25)
    q3 = out["close"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    out = out[(out["close"] >= lower) & (out["close"] <= upper)]
    out = out[(out["high"] >= lower) & (out["high"] <= upper)]
    out = out[(out["low"] >= lower) & (out["low"] <= upper)]

    if timeframe == "1m" and len(out) > 1:
        prev_close = out["close"].shift(1).replace(0, np.nan)
        open_gap = ((out["open"] - prev_close) / prev_close).abs() * 100
        close_gap = ((out["close"] - prev_close) / prev_close).abs() * 100
        body_gap = ((out["close"] - out["open"]) / out["open"].replace(0, np.nan)).abs() * 100
        range_gap = ((out["high"] - out["low"]) / out["low"].replace(0, np.nan)).abs() * 100
        high_gap = ((out["high"] - prev_close) / prev_close).abs() * 100
        low_gap = ((out["low"] - prev_close) / prev_close).abs() * 100

        jump = (
            (open_gap > 10)
            | (close_gap > 10)
            | (body_gap > 10)
            | (range_gap > 10)
            | (high_gap > 10)
            | (low_gap > 10)
        )
        jump.iloc[0] = False
        out = out[~jump]

    return out.sort_index()


def load_data():
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", BACKTEST_END)]
    periods_4h = [("2021-07-01", "2021-12-31"), ("2022-01-01", "2024-12-31"), ("2025-01-01", BACKTEST_END)]
    df_1m = _clean_data(_load_cached_df(SYMBOL, "1m", periods_1m), "1m")
    df_4h = _clean_data(_load_cached_df(SYMBOL, "4h", periods_4h), "4h")
    return df_1m, df_4h


class RSIAveragingBacktestStandalone:
    def __init__(
        self,
        symbol: str,
        initial_capital: float = INITIAL_CAPITAL,
        commission: float = COMMISSION,
        entry_scale: float = ENTRY_SCALE,
    ):
        self.symbol = symbol
        self.initial_capital = float(initial_capital)
        self.capital = float(initial_capital)
        self.commission = float(commission)
        self.entry_scale = float(entry_scale)

        self.current_position = None
        self.rsi_period = 6
        self.rsi_oversold = 15
        self.rsi_overbought = 85
        self.ema_period = 200
        self.stop_loss_pct = 0.03
        self.stop_reentry_trigger_pct = 0.03
        self.stop_partial_close_ratio = 0.8
        self.enable_stop_reentry = True
        self.use_margin_pct_stop = False
        self.margin_stop_loss_pct = 0.20
        self.take_profit_pct = 0.01
        self.base_cooldown = 5
        self.cooldown_time = self.base_cooldown
        self.initial_entry_capital_ratio = 1.0
        self.allow_long_entries = True
        self.allow_short_entries = True
        self.enable_trend_break_close = False
        self.enable_adx_regime_filter = False
        self.entry_adx_limit = 35.0
        self.enable_ema_stack_filter = False
        self.max_entry_count = 5
        self.reverse_close_ratio_trend = 0.2
        self.reverse_close_ratio_mixed = 0.4
        self.ema_buffer = 0.001
        self.require_ema_trend_for_entry = True
        self.skip_entry_when_ema_touch = True
        self.reentry_requires_rsi_signal = False
        self.use_adx_multiplier = True
        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0, 0]
        self.last_order_time = -10**9
        self.recent_trade = [0.0, None]
        self.bankrupt = False
        self.trades = []
        self.equity_curve = []
        self.current_trend = None

    def calculate_rsi(self, closes, period=6):
        delta = closes.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        rsi[(avg_loss == 0) & (avg_gain > 0)] = 100
        rsi[(avg_gain == 0) & (avg_loss > 0)] = 0
        rsi[(avg_gain == 0) & (avg_loss == 0)] = 50
        return rsi.fillna(50)

    def calculate_adx(self, df, period=14):
        high = df['high']
        low = df['low']
        close = df['close']

        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0

        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        tr = pd.concat([tr1, tr2, tr3], axis=1, join='inner').max(axis=1)
        atr = tr.rolling(period).mean()

        plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1 / period).mean() / atr)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = ((dx.shift(1) * (period - 1)) + dx) / period
        return adx.ewm(alpha=1 / period).mean().fillna(0)

    def run(self, df_1m, df_4h, backtest_start_date=None):
        self.capital = self.initial_capital
        self.current_position = None
        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0, 0]
        self.last_order_time = -10**9
        self.recent_trade = [0.0, None]
        self.cooldown_time = self.base_cooldown
        self.trades = []
        self.equity_curve = []
        self.current_trend = None
        self.bankrupt = False

        out_1m = df_1m.copy()
        out_4h = df_4h.copy()

        if backtest_start_date is not None:
            out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()

        if len(out_1m) == 0:
            return

        out_1m['rsi'] = self.calculate_rsi(out_1m['close'], period=self.rsi_period)
        out_1m['adx'] = self.calculate_adx(out_1m, period=14)

        out_1m['ema16'] = out_1m['close'].ewm(span=16).mean()
        out_1m['ema50'] = out_1m['close'].ewm(span=50).mean()
        out_1m['ema99'] = out_1m['close'].ewm(span=99).mean()
        out_1m['ema200_1m'] = out_1m['close'].ewm(span=200).mean()
        bullish_stack = (out_1m['ema16'] > out_1m['ema50']) & (out_1m['ema50'] > out_1m['ema99']) & (out_1m['ema99'] > out_1m['ema200_1m'])
        bearish_stack = (out_1m['ema16'] < out_1m['ema50']) & (out_1m['ema50'] < out_1m['ema99']) & (out_1m['ema99'] < out_1m['ema200_1m'])
        out_1m['ema_status'] = np.select([bullish_stack, bearish_stack], ['bullish', 'bearish'], default='mixed')

        out_4h['ema200'] = out_4h['close'].ewm(span=200, adjust=False).mean().shift(1)
        out_4h['ema_touch'] = (out_4h['high'] >= out_4h['ema200']) & (out_4h['low'] <= out_4h['ema200'])

        out_1m['timestamp_4h'] = out_1m.index.floor('4h')
        is_new_4h_bucket = out_1m['timestamp_4h'] != out_1m['timestamp_4h'].shift(1)
        out_1m = out_1m.merge(out_4h[['ema200', 'ema_touch']], left_on='timestamp_4h', right_index=True, how='left')
        out_1m.drop('timestamp_4h', axis=1, inplace=True)
        out_1m['ema200'] = out_1m['ema200'].ffill()
        out_1m['ema_touch'] = out_1m['ema_touch'].ffill().fillna(False)
        out_1m['trend'] = np.where(out_1m['close'] > out_1m['ema200'], 'bullish', 'bearish')

        out_1m['ema_touch_event'] = (out_1m['ema_touch'] & is_new_4h_bucket).fillna(False)

        start_idx = max(200, 0)
        for i in range(start_idx, len(out_1m)):
            row = out_1m.iloc[i]
            timestamp = row.name
            price = row['close']
            rsi = row['rsi']
            adx = row['adx']
            trend = row['trend']
            ema_touch_event = row['ema_touch_event']
            ema_touch_now = bool(row['ema_touch']) if 'ema_touch' in row else False
            ema_val = row['ema200']
            ema_status = row['ema_status']

            if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                continue

            self._check_trend_change(trend, price, timestamp, ema_val)
            current_time = i
            time_since_last = current_time - self.last_order_time

            self._check_stop_loss(price, timestamp, current_time)
            did_stop_reentry = False

            # run same baseline behavior as standalone sweep variant: no halt filters, just skip when ema touch
            if (not did_stop_reentry) and (not self._is_trading_halted(current_time)):
                allow_long = self.allow_long_entries
                allow_short = self.allow_short_entries

                if self.require_ema_trend_for_entry:
                    if trend == 'bullish':
                        allow_short = False
                    elif trend == 'bearish':
                        allow_long = False

                if self.skip_entry_when_ema_touch and ema_touch_now:
                    allow_long = False
                    allow_short = False

                if self.enable_adx_regime_filter and adx > self.entry_adx_limit:
                    allow_long = False
                    allow_short = False

                if self.enable_ema_stack_filter:
                    if ema_status == 'bearish':
                        allow_long = False
                    elif ema_status == 'bullish':
                        allow_short = False

                if time_since_last >= self.cooldown_time and (not ema_touch_now):
                    if rsi <= self.rsi_oversold and allow_long:
                        self._process_long_entry(price, timestamp, adx, current_time, ema_status)
                    elif rsi >= self.rsi_overbought and allow_short:
                        self._process_short_entry(price, timestamp, adx, current_time, ema_status)

            self._check_take_profit(price, timestamp)
            self._record_equity(price, timestamp, ema_val)

        if self.current_position:
            last_price = out_1m['close'].iloc[-1]
            last_timestamp = out_1m.index[-1]
            self._close_position(last_price, last_timestamp, 'Final Close')

    def _check_trend_change(self, new_trend, price, timestamp, ema_value=0, current_time=None):
        if self.current_trend is None:
            self.current_trend = new_trend
            return
        if self.current_position and self.enable_trend_break_close:
            pos_side = self.current_position['side']
            long_break = pos_side == 'LONG' and price < ema_value * (1 - self.ema_buffer)
            short_break = pos_side == 'SHORT' and price > ema_value * (1 + self.ema_buffer)
            if long_break or short_break:
                self._close_position(price, timestamp, 'Trend Change')
        self.current_trend = new_trend

    def _check_stop_loss(self, price, timestamp, current_time):
        if not self.current_position:
            if self.stop_loss != [0, 0]:
                self.stop_loss = [0, 0]
            return

        pos = self.current_position
        entry_price = pos['avg_entry']
        side = pos['side']
        position_amt = pos['quantity']

        if self.stop_loss == [0, 0]:
            if side == 'LONG':
                stop_price = entry_price * (1 - self.stop_loss_pct)
                if price <= stop_price:
                    if self.stop_partial_close_ratio >= 0.999999 or not self.enable_stop_reentry:
                        self._close_position(price, timestamp, 'Stop Loss Full')
                    else:
                        close_qty = position_amt * self.stop_partial_close_ratio
                        self._partial_close(price, timestamp, close_qty, 'Stop Loss')
                        self.stop_loss = [price, close_qty]
            else:
                stop_price = entry_price * (1 + self.stop_loss_pct)
                if price >= stop_price:
                    if self.stop_partial_close_ratio >= 0.999999 or not self.enable_stop_reentry:
                        self._close_position(price, timestamp, 'Stop Loss Full')
                    else:
                        close_qty = position_amt * self.stop_partial_close_ratio
                        self._partial_close(price, timestamp, close_qty, 'Stop Loss')
                        self.stop_loss = [price, -close_qty]

    def _check_margin_stop_loss(self, price, timestamp, current_time):
        if not self.current_position:
            if self.stop_loss != [0, 0]:
                self.stop_loss = [0, 0]
            return

        pos = self.current_position
        side = pos['side']
        qty = pos['quantity']
        avg_entry = pos['avg_entry']
        if side == 'LONG':
            unrealized = (price - avg_entry) * qty
        else:
            unrealized = (avg_entry - price) * qty

        margin_base = max(self.capital, 0.0)
        if margin_base <= 0:
            return
        loss_limit = margin_base * self.margin_stop_loss_pct
        if unrealized <= -loss_limit:
            self._close_position(price, timestamp, f'Margin Stop {self.margin_stop_loss_pct * 100:.1f}%')
            self.stop_loss = [0, 0]

    def _try_stop_reentry_by_rsi(self, price, rsi, timestamp, current_time):
        if not self.enable_stop_reentry:
            return False
        if not self.current_position or self.stop_loss[1] == 0:
            return False

        side = self.current_position['side']
        stop_price, stop_qty = self.stop_loss
        add_qty = 0.0
        if side == 'LONG' and stop_qty > 0:
            valid_zone = price <= stop_price * (1 - self.stop_reentry_trigger_pct)
            rsi_signal = (rsi <= self.rsi_oversold) if self.reentry_requires_rsi_signal else True
            if valid_zone and rsi_signal:
                add_qty = min(stop_qty, self._remaining_add_qty())
        elif side == 'SHORT' and stop_qty < 0:
            valid_zone = price >= stop_price * (1 + self.stop_reentry_trigger_pct)
            rsi_signal = (rsi >= self.rsi_overbought) if self.reentry_requires_rsi_signal else True
            if valid_zone and rsi_signal:
                add_qty = min(abs(stop_qty), self._remaining_add_qty())

        if add_qty <= 1e-12:
            return False

        self._add_to_position(price, timestamp, add_qty, 0)
        self.stop_loss = [0, 0]
        self.last_order_time = current_time
        self.recent_trade = [price, side]
        self._update_cooldown(side)
        return True

    def _is_trading_halted(self, current_time):
        return False

    def _process_long_entry(self, price, timestamp, adx, current_time, ema_status):
        if self.bankrupt:
            return
        if not self.current_position:
            if self.capital <= 0:
                return
            qty = (self.capital * self.initial_entry_capital_ratio) / price * self.entry_scale
            self._open_position('LONG', price, timestamp, qty)
            self.last_order_time = current_time
            self.recent_trade = [price, 'LONG']
            self._update_cooldown('LONG')
        elif self.current_position['side'] == 'LONG':
            if self.stop_loss[1] > 0:
                return
            if price <= self.recent_trade[0] * 0.995:
                mult = self._get_adx_multiplier(adx)
                if mult > 0:
                    qty = min(self.position_quantity * mult, self._remaining_add_qty())
                    if qty <= 0:
                        return
                    self._add_to_position(price, timestamp, qty, adx)
                    self.last_order_time = current_time
                    self.recent_trade = [price, 'LONG']
                    self._update_cooldown('LONG')
        elif self.current_position['side'] == 'SHORT':
            base_qty = self.position_quantity if self.position_quantity else self.current_position['quantity']
            close_ratio = self.reverse_close_ratio_trend if ema_status == 'bearish' else self.reverse_close_ratio_mixed
            close_qty = base_qty * close_ratio
            self._partial_close(price, timestamp, close_qty, 'Reverse Signal')
            self.last_order_time = current_time
            self.recent_trade = [price, 'LONG']
            self._update_cooldown('LONG')

    def _process_short_entry(self, price, timestamp, adx, current_time, ema_status):
        if self.bankrupt:
            return
        if not self.current_position:
            if self.capital <= 0:
                return
            qty = (self.capital * self.initial_entry_capital_ratio) / price * self.entry_scale
            self._open_position('SHORT', price, timestamp, qty)
            self.last_order_time = current_time
            self.recent_trade = [price, 'SHORT']
            self._update_cooldown('SHORT')
        elif self.current_position['side'] == 'SHORT':
            if self.stop_loss[1] < 0:
                return
            if price >= self.recent_trade[0] * 1.005:
                mult = self._get_adx_multiplier(adx)
                if mult > 0:
                    qty = min(self.position_quantity * mult, self._remaining_add_qty())
                    if qty <= 0:
                        return
                    self._add_to_position(price, timestamp, qty, adx)
                    self.last_order_time = current_time
                    self.recent_trade = [price, 'SHORT']
                    self._update_cooldown('SHORT')
        elif self.current_position['side'] == 'LONG':
            base_qty = self.position_quantity if self.position_quantity else self.current_position['quantity']
            close_ratio = self.reverse_close_ratio_trend if ema_status == 'bullish' else self.reverse_close_ratio_mixed
            close_qty = base_qty * close_ratio
            self._partial_close(price, timestamp, close_qty, 'Reverse Signal')
            self.last_order_time = current_time
            self.recent_trade = [price, 'SHORT']
            self._update_cooldown('SHORT')

    def _get_adx_multiplier(self, adx):
        next_entry = self.entry_count + 1
        if next_entry > self.max_entry_count:
            return 0
        if not self.use_adx_multiplier:
            return 1
        if adx >= 50:
            return 3
        if adx >= 40:
            return 2
        return 1

    def _remaining_add_qty(self):
        if not self.current_position or not self.position_quantity:
            return 0.0
        max_qty = self.position_quantity * self.max_entry_count
        return max(0.0, max_qty - self.current_position['quantity'])

    def _update_cooldown(self, side):
        if self.current_position:
            count = max(1, self.entry_count)
            self.cooldown_time = self.base_cooldown + (count * 1)
        else:
            self.cooldown_time = self.base_cooldown

    def _check_take_profit(self, price, timestamp):
        if not self.current_position:
            return

        pos = self.current_position
        avg_entry = pos['avg_entry']
        if pos['side'] == 'LONG' and price >= avg_entry * (1 + self.take_profit_pct):
            self._close_position(price, timestamp, 'Take Profit')
        elif pos['side'] == 'SHORT' and price <= avg_entry * (1 - self.take_profit_pct):
            self._close_position(price, timestamp, 'Take Profit')

    def _open_position(self, side, price, timestamp, quantity):
        if self.bankrupt:
            return
        position_value = quantity * price
        commission = position_value * self.commission
        self.current_position = {
            'side': side,
            'avg_entry': price,
            'quantity': quantity,
            'entry_time': timestamp,
            'total_commission': commission,
        }
        self.position_quantity = quantity
        self.capital -= commission
        self.entry_count = 1
        self.stop_loss = [0, 0]

    def _add_to_position(self, price, timestamp, quantity, adx):
        if self.bankrupt or not self.current_position:
            return
        if not self.position_quantity or self.position_quantity == 0:
            return
        if quantity <= 0:
            return

        pos = self.current_position
        add_qty = min(quantity, self._remaining_add_qty())
        if add_qty <= 0:
            return

        position_value = add_qty * price
        commission = position_value * self.commission
        total_qty = pos['quantity'] + add_qty
        new_avg = (pos['avg_entry'] * pos['quantity'] + price * add_qty) / total_qty

        pos['avg_entry'] = new_avg
        pos['quantity'] = total_qty
        pos['total_commission'] += commission
        self.capital -= commission
        self.entry_count = round(total_qty / self.position_quantity)

    def _partial_close(self, price, timestamp, quantity, reason):
        if self.bankrupt or not self.current_position:
            return
        pos = self.current_position
        quantity = min(quantity, pos['quantity'])
        if quantity <= 0:
            return

        position_value = quantity * price
        commission = position_value * self.commission
        if pos['side'] == 'LONG':
            pnl = (price - pos['avg_entry']) * quantity
        else:
            pnl = (pos['avg_entry'] - price) * quantity
        pnl -= commission
        self.capital += pnl

        pos['quantity'] -= quantity
        if self.position_quantity and self.position_quantity > 0:
            self.entry_count = max(1, round(pos['quantity'] / self.position_quantity))
        else:
            self.entry_count = 1

        if pos['quantity'] < self.position_quantity * 0.1:
            self._close_position(price, timestamp, reason)
        else:
            self.trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': timestamp,
                'side': pos['side'],
                'avg_entry': pos['avg_entry'],
                'exit_price': price,
                'quantity': quantity,
                'num_entries': self.entry_count,
                'pnl': pnl,
                'return_pct': (pnl / self.initial_capital) * 100,
                'reason': reason,
            })

    def _close_position(self, price, timestamp, reason):
        if self.bankrupt or not self.current_position:
            return

        pos = self.current_position
        position_value = pos['quantity'] * price
        commission = position_value * self.commission
        if pos['side'] == 'LONG':
            pnl = (price - pos['avg_entry']) * pos['quantity']
        else:
            pnl = (pos['avg_entry'] - price) * pos['quantity']
        pnl -= (pos['total_commission'] + commission)
        self.capital += pnl

        self.trades.append({
            'entry_time': pos['entry_time'],
            'exit_time': timestamp,
            'side': pos['side'],
            'avg_entry': pos['avg_entry'],
            'exit_price': price,
            'quantity': pos['quantity'],
            'num_entries': self.entry_count,
            'pnl': pnl,
            'return_pct': (pnl / self.initial_capital) * 100,
            'reason': reason,
        })

        self.current_position = None
        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0, 0]
        self.cooldown_time = self.base_cooldown

    def _record_equity(self, price, timestamp, ema=0):
        equity = self.capital
        if self.current_position:
            pos = self.current_position
            if pos['side'] == 'LONG':
                equity += (price - pos['avg_entry']) * pos['quantity']
            else:
                equity += (pos['avg_entry'] - price) * pos['quantity']
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': equity,
            'price': price,
            'ema200': ema,
        })


def run_baseline_ema200():
    df_1m, df_4h = load_data()
    df_1m = df_1m[(df_1m.index >= BACKTEST_START) & (df_1m.index <= BACKTEST_END)].copy()

    bt = RSIAveragingBacktestStandalone(
        symbol=SYMBOL,
        initial_capital=INITIAL_CAPITAL,
        commission=COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    bt.rsi_oversold = 18
    bt.rsi_overbought = 85
    bt.take_profit_pct = 0.012
    bt.stop_loss_pct = 0.03
    bt.base_cooldown = 5
    bt.cooldown_time = 5

    bt.run(df_1m, df_4h, backtest_start_date=BACKTEST_START)
    return bt


def save_backtest_plot(bt: RSIAveragingBacktestStandalone, filename: str = "backtest_real_results.png") -> None:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)

    if eq.empty:
        return

    plt.figure(figsize=(12, 8))
    plt.plot(eq["timestamp"], eq["equity"], label="Equity")
    if not tr.empty:
        longs = tr[tr["side"] == "LONG"]
        shorts = tr[tr["side"] == "SHORT"]
        if not longs.empty:
            plt.scatter(longs["entry_time"], longs["avg_entry"], s=10, alpha=0.5, label="LONG entry")
        if not shorts.empty:
            plt.scatter(shorts["entry_time"], shorts["avg_entry"], s=10, alpha=0.5, label="SHORT entry")
    plt.title("Backtest RSI Averaging")
    plt.xlabel("Time")
    plt.ylabel("Equity (USDT)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()


def summarize(bt: RSIAveragingBacktestStandalone):
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)
    eq['timestamp'] = pd.to_datetime(eq['timestamp'])
    final_equity = float(eq['equity'].iloc[-1])
    total_return_pct = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0
    years = max((eq['timestamp'].iloc[-1] - eq['timestamp'].iloc[0]).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / INITIAL_CAPITAL, 1 / years) - 1.0) * 100.0
    max_dd_pct = abs((eq['equity'] - eq['equity'].cummax()) / eq['equity'].cummax().replace(0, np.nan) * 100.0).fillna(0.0).max()
    win_rate = float((tr['pnl'] > 0).mean() * 100.0) if len(tr) else 0.0
    return {
        'period_start': eq['timestamp'].iloc[0],
        'period_end': eq['timestamp'].iloc[-1],
        'final_equity': final_equity,
        'total_return_pct': total_return_pct,
        'cagr_pct': cagr_pct,
        'max_dd_pct': float(max_dd_pct),
        'trades': int(len(tr)),
        'win_rate_pct': win_rate,
    }


def main():
    bt = run_baseline_ema200()
    metrics = summarize(bt)
    save_backtest_plot(bt, filename="backtest_real_results.png")
    save_backtest_plot(bt, filename="backtest_Real_results.png")

    print(f"symbol={SYMBOL}")
    print(f"period={metrics['period_start']} ~ {metrics['period_end']}")
    print(f"final_equity={metrics['final_equity']:.4f}")
    print(f"total_return_pct={metrics['total_return_pct']:.4f}%")
    print(f"CAGR={metrics['cagr_pct']:.4f}%")
    print(f"max_dd_pct={metrics['max_dd_pct']:.4f}%")
    print(f"trades={metrics['trades']}, win_rate={metrics['win_rate_pct']:.2f}%")


if __name__ == "__main__":
    main()
