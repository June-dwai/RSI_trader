from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


SYMBOL = "BTCUSDT"
BACKTEST_START = "2022-01-01"
BACKTEST_END = "2026-02-12"
INITIAL_CAPITAL = 1000.0
COMMISSION = 0.0004
ENTRY_SCALE = 0.50
DATA_DIR = Path("historical_data_mainnet")


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

    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="first")].sort_index()
    return merged


def _clean_cached_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    combined = df.copy()
    before = len(combined)
    q1 = combined["close"].quantile(0.25)
    q3 = combined["close"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    combined = combined[
        (combined["close"] >= lower_bound)
        & (combined["close"] <= upper_bound)
        & (combined["high"] >= lower_bound)
        & (combined["low"] >= lower_bound)
        & (combined["high"] <= upper_bound)
    ]

    removed_iqr = before - len(combined)
    removed_discrete = 0

    if timeframe == "1m" and len(combined) > 1:
        max_jump_pct = 10.0
        prev_close = combined["close"].shift(1)
        safe_prev_close = prev_close.replace(0, np.nan)
        safe_open = combined["open"].replace(0, np.nan)
        safe_low = combined["low"].replace(0, np.nan)

        open_gap_pct = ((combined["open"] - safe_prev_close) / safe_prev_close).abs() * 100
        close_change_pct = ((combined["close"] - safe_prev_close) / safe_prev_close).abs() * 100
        body_change_pct = ((combined["close"] - safe_open) / safe_open).abs() * 100
        range_pct = ((combined["high"] - combined["low"]) / safe_low).abs() * 100
        high_jump_pct = ((combined["high"] - safe_prev_close) / safe_prev_close).abs() * 100
        low_jump_pct = ((combined["low"] - safe_prev_close) / safe_prev_close).abs() * 100

        discrete_jump_mask = (
            (open_gap_pct > max_jump_pct)
            | (close_change_pct > max_jump_pct)
            | (body_change_pct > max_jump_pct)
            | (range_pct > max_jump_pct)
            | (high_jump_pct > max_jump_pct)
            | (low_jump_pct > max_jump_pct)
        )
        if len(discrete_jump_mask) > 0:
            discrete_jump_mask.iloc[0] = False
            removed_discrete = int(discrete_jump_mask.sum())
            combined = combined[~discrete_jump_mask]

    _ = removed_iqr, removed_discrete
    return combined.sort_index()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", BACKTEST_END)]
    periods_4h = [
        ("2021-07-01", "2021-12-31"),
        ("2022-01-01", "2024-12-31"),
        ("2025-01-01", BACKTEST_END),
    ]
    df_1m = _clean_cached_data(_load_cached_df(SYMBOL, "1m", periods_1m), "1m")
    df_4h = _clean_cached_data(_load_cached_df(SYMBOL, "4h", periods_4h), "4h")
    return df_1m, df_4h


class RSIAveragingBacktestStandalone:
    """Legacy RSI averaging strategy logic extracted from fce92a1 baseline."""

    def __init__(self, symbol: str, initial_capital: float = INITIAL_CAPITAL, commission: float = COMMISSION):
        self.symbol = symbol
        self.initial_capital = float(initial_capital)
        self.capital = float(initial_capital)
        self.commission = float(commission)

        self.current_position = None
        self.rsi_period = 6
        self.rsi_oversold = 15
        self.rsi_overbought = 85
        self.ema_period = 200
        self.stop_loss_pct = 0.03
        self.take_profit_pct = 0.010
        self.base_cooldown = 5
        self.cooldown_time = self.base_cooldown
        self.ema_buffer = 0.001

        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0, 0]
        self.last_order_time = -10**9
        self.recent_trade = [0.0, None]
        self.trades: list[dict] = []
        self.equity_curve: list[dict] = []
        self.current_trend = None

    def calculate_rsi(self, closes: pd.Series, period: int = 6) -> pd.Series:
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

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        atr = tr.rolling(window=period).mean()
        plus_di = 100 * pd.Series(pos_dm, index=df.index).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(neg_dm, index=df.index).rolling(window=period).mean() / atr

        dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).abs()
        adx = dx.rolling(window=period).mean()
        return adx

    def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
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

        out_1m = df_1m.copy()
        out_4h = df_4h.copy()

        if backtest_start_date is not None:
            out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
        if len(out_1m) == 0:
            return

        out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
        out_1m["adx"] = self.calculate_adx(out_1m, period=14)

        out_4h["ema200"] = out_4h["close"].ewm(span=200, adjust=False).mean().shift(1)
        out_4h["ema_touch_raw"] = (out_4h["high"] >= out_4h["ema200"]) & (out_4h["low"] <= out_4h["ema200"])
        # No look-ahead: current 4h bucket uses previous closed 4h touch state.
        out_4h["ema_touch_confirmed"] = out_4h["ema_touch_raw"].shift(1).fillna(False)

        out_1m["timestamp_4h"] = out_1m.index.floor("4h")
        out_1m = out_1m.merge(
            out_4h[["ema200", "ema_touch_confirmed"]],
            left_on="timestamp_4h",
            right_index=True,
            how="left",
        )
        out_1m.drop("timestamp_4h", axis=1, inplace=True)

        out_1m["ema200"] = out_1m["ema200"].ffill()
        out_1m["ema_touch"] = out_1m["ema_touch_confirmed"].ffill().fillna(False)
        out_1m.drop("ema_touch_confirmed", axis=1, inplace=True)
        out_1m["trend"] = np.where(out_1m["close"] > out_1m["ema200"], "bullish", "bearish")

        for i in range(200, len(out_1m)):
            row = out_1m.iloc[i]
            timestamp = row.name
            price = row["close"]
            rsi = row["rsi"]
            adx = row["adx"]
            trend = row["trend"]
            ema_touch = row["ema_touch"]
            ema_val = row["ema200"]

            if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_val):
                continue

            self._check_trend_change(trend, price, timestamp, ema_val)

            current_time = i
            time_since_last = current_time - self.last_order_time
            self._check_stop_loss(price, timestamp)

            if not ema_touch and time_since_last >= self.cooldown_time:
                if rsi <= self.rsi_oversold and trend == "bullish":
                    self._process_long_entry(price, timestamp, adx, current_time)
                elif rsi >= self.rsi_overbought and trend == "bearish":
                    self._process_short_entry(price, timestamp, adx, current_time)

            self._check_take_profit(price, timestamp)
            self._record_equity(price, timestamp, ema_val)

        if self.current_position:
            last_price = out_1m["close"].iloc[-1]
            last_timestamp = out_1m.index[-1]
            self._close_position(last_price, last_timestamp, "Final Close")

    def _check_trend_change(self, new_trend, price, timestamp, ema_value=0):
        if self.current_trend is None:
            self.current_trend = new_trend
            return

        if self.current_position:
            side = self.current_position["side"]
            long_break = side == "LONG" and price < ema_value * (1 - self.ema_buffer)
            short_break = side == "SHORT" and price > ema_value * (1 + self.ema_buffer)
            if long_break or short_break:
                self._close_position(price, timestamp, "Trend Change")

        self.current_trend = new_trend

    def _check_stop_loss(self, price, timestamp):
        if not self.current_position:
            if self.stop_loss != [0, 0]:
                self.stop_loss = [0, 0]
            return

        pos = self.current_position
        entry_price = pos["avg_entry"]
        side = pos["side"]
        position_amount = pos["quantity"]

        if self.stop_loss == [0, 0]:
            if side == "LONG":
                stop_price = entry_price * (1 - self.stop_loss_pct)
                if price <= stop_price:
                    close_qty = position_amount * 0.8
                    self._partial_close(price, timestamp, close_qty, "Stop Loss")
                    self.stop_loss = [price, close_qty]
            else:
                stop_price = entry_price * (1 + self.stop_loss_pct)
                if price >= stop_price:
                    close_qty = position_amount * 0.8
                    self._partial_close(price, timestamp, close_qty, "Stop Loss")
                    self.stop_loss = [price, -close_qty]

        elif self.stop_loss[1] != 0:
            stop_price, stop_qty = self.stop_loss
            if stop_qty > 0 and price <= stop_price * (1 - self.stop_loss_pct):
                self._add_to_position(price, timestamp, stop_qty, 20)
                self.stop_loss = [price, 0]
            elif stop_qty < 0 and price >= stop_price * (1 + self.stop_loss_pct):
                self._add_to_position(price, timestamp, abs(stop_qty), 20)
                self.stop_loss = [price, 0]

    def _process_long_entry(self, price, timestamp, adx, current_time):
        if not self.current_position:
            if self.capital <= 0:
                return
            qty = self.capital / price
            self._open_position("LONG", price, timestamp, qty)
            self.last_order_time = current_time
            self.recent_trade = [price, "LONG"]
            self._update_cooldown("LONG")

        elif self.current_position["side"] == "LONG":
            if price <= self.recent_trade[0] * 0.995:
                mult = self._get_adx_multiplier(adx)
                if mult > 0:
                    qty = self.position_quantity * mult
                    self._add_to_position(price, timestamp, qty, adx)
                    self.last_order_time = current_time
                    self.recent_trade = [price, "LONG"]
                    self._update_cooldown("LONG")

        elif self.current_position["side"] == "SHORT":
            close_qty = self.current_position["quantity"] * 0.8
            self._partial_close(price, timestamp, close_qty, "Reverse")
            if self.capital <= 0:
                return
            qty = self.capital / price
            self._open_position("LONG", price, timestamp, qty)
            self.last_order_time = current_time
            self.recent_trade = [price, "LONG"]
            self._update_cooldown("LONG")

    def _process_short_entry(self, price, timestamp, adx, current_time):
        if not self.current_position:
            if self.capital <= 0:
                return
            qty = self.capital / price
            self._open_position("SHORT", price, timestamp, qty)
            self.last_order_time = current_time
            self.recent_trade = [price, "SHORT"]
            self._update_cooldown("SHORT")

        elif self.current_position["side"] == "SHORT":
            if price >= self.recent_trade[0] * 1.005:
                mult = self._get_adx_multiplier(adx)
                if mult > 0:
                    qty = self.position_quantity * mult
                    self._add_to_position(price, timestamp, qty, adx)
                    self.last_order_time = current_time
                    self.recent_trade = [price, "SHORT"]
                    self._update_cooldown("SHORT")

        elif self.current_position["side"] == "LONG":
            close_qty = self.current_position["quantity"] * 0.8
            self._partial_close(price, timestamp, close_qty, "Reverse")
            if self.capital <= 0:
                return
            qty = self.capital / price
            self._open_position("SHORT", price, timestamp, qty)
            self.last_order_time = current_time
            self.recent_trade = [price, "SHORT"]
            self._update_cooldown("SHORT")

    def _get_adx_multiplier(self, adx):
        next_entry = self.entry_count + 1
        if adx >= 50:
            base_mult = 3
        elif adx >= 40:
            base_mult = 2
        else:
            base_mult = 1

        if next_entry <= 5:
            return base_mult

        if adx < 25:
            self.skip_count += 1
            return 0
        if adx < 40:
            mult = 1 + self.skip_count
            self.skip_count = 0
            return mult

        mult = base_mult + self.skip_count
        self.skip_count = 0
        return mult

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
        avg_entry = pos["avg_entry"]
        if pos["side"] == "LONG" and price >= avg_entry * (1 + self.take_profit_pct):
            self._close_position(price, timestamp, "Take Profit")
        elif pos["side"] == "SHORT" and price <= avg_entry * (1 - self.take_profit_pct):
            self._close_position(price, timestamp, "Take Profit")

    def _open_position(self, side, price, timestamp, quantity):
        position_value = quantity * price
        commission = position_value * self.commission

        self.current_position = {
            "side": side,
            "avg_entry": price,
            "quantity": quantity,
            "entry_time": timestamp,
            "total_commission": commission,
        }
        self.position_quantity = quantity
        self.capital -= commission
        self.entry_count = 1
        self.stop_loss = [0, 0]

    def _add_to_position(self, price, timestamp, quantity, adx):
        if not self.current_position:
            return
        if not self.position_quantity or self.position_quantity == 0:
            return
        if quantity <= 0:
            return

        max_position = self.position_quantity * 5
        pos = self.current_position
        add_qty = min(quantity, max_position - pos["quantity"])
        if add_qty <= 0:
            return

        position_value = add_qty * price
        commission = position_value * self.commission

        total_qty = pos["quantity"] + add_qty
        new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

        pos["avg_entry"] = new_avg
        pos["quantity"] = total_qty
        pos["total_commission"] += commission
        self.capital -= commission
        self.entry_count = round(total_qty / self.position_quantity)

    def _partial_close(self, price, timestamp, quantity, reason):
        if not self.current_position:
            return

        pos = self.current_position
        qty = min(quantity, pos["quantity"])
        if qty <= 0:
            return

        position_value = qty * price
        commission = position_value * self.commission
        if pos["side"] == "LONG":
            pnl = (price - pos["avg_entry"]) * qty - commission
        else:
            pnl = (pos["avg_entry"] - price) * qty - commission
        self.capital += pnl

        pos["quantity"] -= qty
        if self.position_quantity and self.position_quantity > 0:
            self.entry_count = max(1, round(pos["quantity"] / self.position_quantity))
        else:
            self.entry_count = 1

        if pos["quantity"] < self.position_quantity * 0.1:
            self._close_position(price, timestamp, reason)

    def _close_position(self, price, timestamp, reason):
        if not self.current_position:
            return

        pos = self.current_position
        position_value = pos["quantity"] * price
        commission = position_value * self.commission
        if pos["side"] == "LONG":
            pnl = (price - pos["avg_entry"]) * pos["quantity"]
        else:
            pnl = (pos["avg_entry"] - price) * pos["quantity"]
        pnl -= (pos["total_commission"] + commission)
        self.capital += pnl

        self.trades.append(
            {
                "entry_time": pos["entry_time"],
                "exit_time": timestamp,
                "side": pos["side"],
                "avg_entry": pos["avg_entry"],
                "exit_price": price,
                "quantity": pos["quantity"],
                "num_entries": self.entry_count,
                "pnl": pnl,
                "return_pct": (pnl / self.initial_capital) * 100,
                "reason": reason,
            }
        )

        self.current_position = None
        self.position_quantity = None
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0, 0]
        self.cooldown_time = self.base_cooldown

    def _record_equity(self, price, timestamp, ema=0):
        equity = self.capital
        if self.current_position:
            pos = self.current_position
            if pos["side"] == "LONG":
                equity += (price - pos["avg_entry"]) * pos["quantity"]
            else:
                equity += (pos["avg_entry"] - price) * pos["quantity"]

        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "equity": equity,
                "price": price,
                "ema200": ema,
            }
        )


class FloorScaledRSIAveragingBacktest(RSIAveragingBacktestStandalone):
    """Standalone floor scale=ENTRY_SCALE wrapper (no trend-change forced exits)."""

    def __init__(
        self,
        symbol: str,
        initial_capital: float = INITIAL_CAPITAL,
        commission: float = COMMISSION,
        entry_scale: float = ENTRY_SCALE,
    ):
        super().__init__(symbol=symbol, initial_capital=initial_capital, commission=commission)
        self.entry_scale = float(entry_scale)
        self.bankrupt = False

    def _open_position(self, side, price, timestamp, quantity):
        super()._open_position(side, price, timestamp, quantity * self.entry_scale)

    def _check_trend_change(self, new_trend, price, timestamp, ema_value=0):
        if self.current_trend is None:
            self.current_trend = new_trend
            return
        self.current_trend = new_trend

    def _record_equity(self, price, timestamp, ema=0):
        if self.bankrupt:
            self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
            return

        equity = self.capital
        if self.current_position:
            pos = self.current_position
            if pos["side"] == "LONG":
                equity += (price - pos["avg_entry"]) * pos["quantity"]
            else:
                equity += (pos["avg_entry"] - price) * pos["quantity"]

        if equity <= 0:
            self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
            self.capital = 0.0
            self.current_position = None
            self.position_quantity = None
            self.entry_count = 0
            self.skip_count = 0
            self.stop_loss = [0, 0]
            self.bankrupt = True
            return

        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "equity": equity,
                "price": price,
                "ema200": ema,
            }
        )


def run_baseline_ema200() -> FloorScaledRSIAveragingBacktest:
    df_1m, df_4h = load_data()
    df_1m = df_1m[(df_1m.index >= BACKTEST_START) & (df_1m.index <= BACKTEST_END)].copy()

    bt = FloorScaledRSIAveragingBacktest(
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


def summarize(bt: RSIAveragingBacktestStandalone) -> dict[str, float]:
    eq = pd.DataFrame(bt.equity_curve)
    tr = pd.DataFrame(bt.trades)

    if eq.empty:
        return {
            "period_start": pd.Timestamp("NaT"),
            "period_end": pd.Timestamp("NaT"),
            "final_equity": 0.0,
            "total_return_pct": -100.0,
            "cagr_pct": -100.0,
            "max_dd_pct": 100.0,
            "trades": 0,
            "win_rate_pct": 0.0,
        }

    eq["timestamp"] = pd.to_datetime(eq["timestamp"])
    final_equity = float(eq["equity"].iloc[-1])
    total_return_pct = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100.0
    years = max((eq["timestamp"].iloc[-1] - eq["timestamp"].iloc[0]).days / 365.25, 1e-9)
    cagr_pct = (pow(max(final_equity, 1e-12) / INITIAL_CAPITAL, 1 / years) - 1.0) * 100.0
    max_dd_pct = abs((eq["equity"] - eq["equity"].cummax()) / eq["equity"].cummax().replace(0, np.nan) * 100.0).fillna(0.0).max()
    win_rate = float((tr["pnl"] > 0).mean() * 100.0) if len(tr) else 0.0

    return {
        "period_start": eq["timestamp"].iloc[0],
        "period_end": eq["timestamp"].iloc[-1],
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "cagr_pct": cagr_pct,
        "max_dd_pct": float(max_dd_pct),
        "trades": int(len(tr)),
        "win_rate_pct": win_rate,
    }


def main():
    bt = run_baseline_ema200()
    metrics = summarize(bt)

    print(f"symbol={SYMBOL}")
    print(f"period={metrics['period_start']} ~ {metrics['period_end']}")
    print(f"entry_scale={ENTRY_SCALE:.2f}")
    print(f"final_equity={metrics['final_equity']:.4f}")
    print(f"total_return_pct={metrics['total_return_pct']:.4f}%")
    print(f"cagr_pct={metrics['cagr_pct']:.4f}%")
    print(f"max_dd_pct={metrics['max_dd_pct']:.4f}%")
    print(f"trades={metrics['trades']}, win_rate={metrics['win_rate_pct']:.2f}%")


if __name__ == "__main__":
    main()
