from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_002_PATH = Path("002_backtest_btcusdt.py")
BASE_04_PATH = Path("04_backtest_btcusdt_mode_compare.py")

OUT_BASE = "34_backtest_btcusdt_live_nla_longonly_hedge"
OUT_PNG = Path(f"{OUT_BASE}.png")
OUT_MD = Path(f"{OUT_BASE}.md")
OUT_CSV = Path(f"{OUT_BASE}.csv")
OUT_EVENTS_CSV = Path(f"{OUT_BASE}_events.csv")
OUT_TRADES_CSV = Path(f"{OUT_BASE}_trades.csv")

INITIAL_CAPITAL = 1000.0
ENTRY_SCALE = 0.50
EMA_PERIOD = 200
RSI_PERIOD = 6
ADX_PERIOD = 14


def load_module(alias: str, path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing script: {path}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _fmt(v: float, digits: int = 4) -> str:
    if pd.isna(v):
        return "N/A"
    return f"{float(v):.{digits}f}"


def load_data_no_filter(base_module) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods_1m = [("2022-01-01", "2024-12-31"), ("2025-01-01", base_module.BACKTEST_END)]
    periods_4h = [
        ("2021-07-01", "2021-12-31"),
        ("2022-01-01", "2024-12-31"),
        ("2025-01-01", base_module.BACKTEST_END),
    ]
    df_1m = base_module._load_cached_df(base_module.SYMBOL, "1m", periods_1m).sort_index()
    df_4h = base_module._load_cached_df(base_module.SYMBOL, "4h", periods_4h).sort_index()
    return df_1m, df_4h


class LiveParityNoLookahead:
    """
    Study-34 engine:
    - Study-33 long-only live-parity core
    - Add trend short hedge (5x base qty) using confirmed 4h trend
    - Absolute no-lookahead for 4h state:
      * trend anchor: previous closed 4h EMA200
      * touch gate: previous closed 4h touch OR current 4h touch-so-far
    """

    def __init__(
        self,
        base_module,
        symbol: str,
        initial_capital: float,
        commission: float,
        entry_scale: float,
    ):
        self.base = base_module
        self.symbol = symbol
        self.initial_capital = float(initial_capital)
        self.capital = float(initial_capital)
        self.commission = float(commission)
        self.entry_scale = float(entry_scale)

        self.rsi_period = RSI_PERIOD
        self.rsi_oversold = 18
        self.rsi_overbought = 85
        self.take_profit_pct = 0.012
        self.stop_loss_pct = 0.03
        self.base_cooldown = 5
        self.cooldown_time = self.base_cooldown

        self.current_position: dict | None = None
        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0.0, 0.0]
        self.pending_reentry: dict | None = None
        self.last_order_time = -10**9
        self.recent_trade = [0.0, None]
        self.current_trend = None
        self.hedge_position: dict | None = None
        self.hedge_base_qty = 0.0
        self.bankrupt = False

        self.trades: list[dict] = []
        self.equity_curve: list[dict] = []
        self.order_events: list[dict] = []
        self.signal_df = pd.DataFrame()

        self.stats = {
            "bars_processed": 0,
            "touch_bars": 0,
            "entry_window_bars": 0,
            "long_signal_bars": 0,
            "short_signal_bars": 0,
            "reverse_events": 0,
            "stop_loss_events": 0,
            "reentry_events": 0,
            "hedge_open_events": 0,
            "hedge_close_events": 0,
        }

    def _mark_order(self, timestamp, price: float, side: str, qty: float, tag: str):
        self.order_events.append(
            {
                "timestamp": pd.to_datetime(timestamp),
                "price": float(price),
                "side": side,
                "quantity": float(qty),
                "tag": tag,
            }
        )

    def calculate_rsi(self, closes: pd.Series, period: int = 6) -> pd.Series:
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
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
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1 / period).mean() / atr)
        minus_di = 100 * (minus_dm.abs().ewm(alpha=1 / period).mean() / atr)
        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).abs()) * 100
        adx = ((dx.shift(1) * (period - 1)) + dx) / period
        return adx.ewm(alpha=1 / period).mean().fillna(0)

    def _update_cooldown(self):
        if self.current_position:
            count = max(1, self.entry_count)
            self.cooldown_time = self.base_cooldown + count
        else:
            self.cooldown_time = self.base_cooldown

    def _get_adx_multiplier(self, adx: float) -> int:
        if adx >= 50:
            return 3
        if adx >= 40:
            return 2
        return 1

    def _mark_to_market_equity(self, price: float) -> float:
        equity = self.capital
        if self.current_position:
            pos = self.current_position
            if pos["side"] == "LONG":
                equity += (price - pos["avg_entry"]) * pos["quantity"]
            else:
                equity += (pos["avg_entry"] - price) * pos["quantity"]
        if self.hedge_position:
            hedge = self.hedge_position
            equity += (hedge["avg_entry"] - price) * hedge["quantity"]
        return float(equity)

    def _record_equity(self, price, timestamp, ema):
        if self.bankrupt:
            self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
            return
        equity = self._mark_to_market_equity(price)
        if equity <= 0:
            self.equity_curve.append({"timestamp": timestamp, "equity": 0.0, "price": price, "ema200": ema})
            self.capital = 0.0
            self.current_position = None
            self.position_quantity = 0.0
            self.entry_count = 0
            self.stop_loss = [0.0, 0.0]
            self.pending_reentry = None
            self.hedge_position = None
            self.bankrupt = True
            return
        self.equity_curve.append({"timestamp": timestamp, "equity": equity, "price": price, "ema200": ema})

    def _open_position(self, side: str, price: float, timestamp, quantity: float, tag: str):
        if quantity <= 0:
            return
        if self.current_position is not None:
            return

        position_value = quantity * price
        commission = position_value * self.commission
        self.capital -= commission

        self.current_position = {
            "side": side,
            "avg_entry": float(price),
            "quantity": float(quantity),
            "entry_time": pd.to_datetime(timestamp),
            "total_commission": float(commission),
        }
        self.position_quantity = float(quantity)
        self.entry_count = 1
        self.stop_loss = [0.0, 0.0]
        self.pending_reentry = None
        self.recent_trade = [float(price), side]
        self._update_cooldown()
        if side == "LONG" and self.position_quantity > 0:
            self.hedge_base_qty = float(self.position_quantity)

        exec_side = "BUY" if side == "LONG" else "SELL"
        self._mark_order(timestamp, price, exec_side, quantity, tag)

    def _add_to_position(self, price: float, timestamp, quantity: float, tag: str):
        if not self.current_position or quantity <= 0 or self.position_quantity <= 0:
            return

        pos = self.current_position
        max_position = self.position_quantity * 5.0
        add_qty = min(quantity, max_position - pos["quantity"])
        if add_qty <= 0:
            return

        value = add_qty * price
        commission = value * self.commission
        total_qty = pos["quantity"] + add_qty
        new_avg = (pos["avg_entry"] * pos["quantity"] + price * add_qty) / total_qty

        self.capital -= commission
        pos["avg_entry"] = float(new_avg)
        pos["quantity"] = float(total_qty)
        pos["total_commission"] += float(commission)
        self.entry_count = max(1, round(total_qty / self.position_quantity))
        self.recent_trade = [float(price), pos["side"]]
        self._update_cooldown()

        exec_side = "BUY" if pos["side"] == "LONG" else "SELL"
        self._mark_order(timestamp, price, exec_side, add_qty, tag)

    def _partial_close(self, price: float, timestamp, quantity: float, reason: str):
        if not self.current_position:
            return
        pos = self.current_position
        qty = min(quantity, pos["quantity"])
        if qty <= 0:
            return

        commission = qty * price * self.commission
        if pos["side"] == "LONG":
            pnl = (price - pos["avg_entry"]) * qty - commission
            exec_side = "SELL"
        else:
            pnl = (pos["avg_entry"] - price) * qty - commission
            exec_side = "BUY"
        self.capital += pnl
        pos["quantity"] -= qty

        self._mark_order(timestamp, price, exec_side, qty, f"PARTIAL_{reason}")

        if self.position_quantity > 0:
            self.entry_count = max(1, round(pos["quantity"] / self.position_quantity))
        else:
            self.entry_count = 1

        if pos["quantity"] <= max(self.position_quantity * 0.1, 1e-12):
            self._close_position(price, timestamp, reason)

    def _close_position(self, price: float, timestamp, reason: str):
        if not self.current_position:
            return
        pos = self.current_position
        qty = pos["quantity"]
        close_commission = qty * price * self.commission
        if pos["side"] == "LONG":
            pnl = (price - pos["avg_entry"]) * qty - close_commission
            exec_side = "SELL"
        else:
            pnl = (pos["avg_entry"] - price) * qty - close_commission
            exec_side = "BUY"
        self.capital += pnl

        self.trades.append(
            {
                "entry_time": pos["entry_time"],
                "exit_time": pd.to_datetime(timestamp),
                "side": pos["side"],
                "avg_entry": pos["avg_entry"],
                "exit_price": float(price),
                "quantity": float(qty),
                "num_entries": int(self.entry_count),
                "pnl": float(pnl),
                "return_pct": (float(pnl) / self.initial_capital) * 100.0,
                "reason": reason,
            }
        )
        self._mark_order(timestamp, price, exec_side, qty, f"CLOSE_{reason}")

        self.current_position = None
        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0.0, 0.0]
        self.pending_reentry = None
        self.recent_trade = [0.0, None]
        self._update_cooldown()

    def _check_take_profit(self, price: float, timestamp):
        if not self.current_position:
            return
        pos = self.current_position
        avg = pos["avg_entry"]
        if pos["side"] == "LONG" and price >= avg * (1 + self.take_profit_pct):
            self._close_position(price, timestamp, "Take Profit")
        elif pos["side"] == "SHORT" and price <= avg * (1 - self.take_profit_pct):
            self._close_position(price, timestamp, "Take Profit")

    def _check_stop_loss_and_reentry(self, price: float, timestamp):
        if not self.current_position:
            if self.stop_loss != [0.0, 0.0]:
                self.stop_loss = [0.0, 0.0]
            self.pending_reentry = None
            return

        pos = self.current_position
        side = pos["side"]
        entry_price = pos["avg_entry"]
        qty = pos["quantity"]

        if self.stop_loss == [0.0, 0.0]:
            if side == "LONG":
                stop_price = entry_price * (1 - self.stop_loss_pct)
                if price <= stop_price:
                    close_qty = qty * 0.8
                    self._partial_close(price, timestamp, close_qty, "Stop Loss")
                    self.stop_loss = [float(price), float(close_qty)]
                    self.pending_reentry = {
                        "side": "LONG",
                        "quantity": float(close_qty),
                        "trigger_price": float(price),
                        "reentry_price": float(price * (1 - self.stop_loss_pct)),
                    }
                    self.stats["stop_loss_events"] += 1
            else:
                stop_price = entry_price * (1 + self.stop_loss_pct)
                if price >= stop_price:
                    close_qty = qty * 0.8
                    self._partial_close(price, timestamp, close_qty, "Stop Loss")
                    self.stop_loss = [float(price), -float(close_qty)]
                    self.pending_reentry = {
                        "side": "SHORT",
                        "quantity": float(close_qty),
                        "trigger_price": float(price),
                        "reentry_price": float(price * (1 + self.stop_loss_pct)),
                    }
                    self.stats["stop_loss_events"] += 1
            return

        if self.stop_loss[1] == 0:
            return

        if self.pending_reentry is None:
            signed_qty = float(self.stop_loss[1])
            trigger = float(self.stop_loss[0])
            side_re = "LONG" if signed_qty > 0 else "SHORT"
            qty_re = abs(signed_qty)
            re_price = trigger * (1 - self.stop_loss_pct) if side_re == "LONG" else trigger * (1 + self.stop_loss_pct)
            self.pending_reentry = {
                "side": side_re,
                "quantity": qty_re,
                "trigger_price": trigger,
                "reentry_price": re_price,
            }

        re = self.pending_reentry
        if re["side"] == "LONG" and price <= re["reentry_price"]:
            self._add_to_position(re["reentry_price"], timestamp, re["quantity"], "REENTRY")
            self.stop_loss = [float(price), 0.0]
            self.pending_reentry = None
            self.stats["reentry_events"] += 1
        elif re["side"] == "SHORT" and price >= re["reentry_price"]:
            self._add_to_position(re["reentry_price"], timestamp, re["quantity"], "REENTRY")
            self.stop_loss = [float(price), 0.0]
            self.pending_reentry = None
            self.stats["reentry_events"] += 1

    def _execute_reverse_signal(self, target_side: str, price: float, timestamp, current_time_idx: int):
        if not self.current_position:
            return
        if self.current_position["side"] == target_side:
            return

        self._partial_close(price, timestamp, self.current_position["quantity"] * 0.8, "Reverse")
        if self.current_position and self.current_position["side"] != target_side:
            self._close_position(price, timestamp, "Reverse Residual")

        if self.capital <= 0:
            self.last_order_time = current_time_idx
            self.stats["reverse_events"] += 1
            return

        qty = (self.capital / price) * self.entry_scale
        if qty > 0:
            self._open_position(target_side, price, timestamp, qty, "REVERSE_OPEN")
        self.last_order_time = current_time_idx
        self.stats["reverse_events"] += 1

    def _process_long_entry(self, price: float, timestamp, adx: float, current_time: int):
        if not self.current_position:
            if self.capital <= 0:
                return
            qty = (self.capital / price) * self.entry_scale
            self._open_position("LONG", price, timestamp, qty, "OPEN")
            self.last_order_time = current_time
            return

        if self.current_position["side"] == "LONG":
            if price <= self.recent_trade[0] * 0.995:
                mult = self._get_adx_multiplier(adx)
                if mult > 0:
                    self._add_to_position(price, timestamp, self.position_quantity * mult, f"DCA_x{mult}")
                    self.last_order_time = current_time
            return

        self._execute_reverse_signal("LONG", price, timestamp, current_time)

    def _process_short_entry(self, price: float, timestamp, adx: float, current_time: int):
        if not self.current_position:
            if self.capital <= 0:
                return
            qty = (self.capital / price) * self.entry_scale
            self._open_position("SHORT", price, timestamp, qty, "OPEN")
            self.last_order_time = current_time
            return

        if self.current_position["side"] == "SHORT":
            if price >= self.recent_trade[0] * 1.005:
                mult = self._get_adx_multiplier(adx)
                if mult > 0:
                    self._add_to_position(price, timestamp, self.position_quantity * mult, f"DCA_x{mult}")
                    self.last_order_time = current_time
            return

        self._execute_reverse_signal("SHORT", price, timestamp, current_time)

    def _open_hedge_short(self, price: float, timestamp):
        if self.hedge_position is not None:
            return
        if self.position_quantity > 0:
            self.hedge_base_qty = float(self.position_quantity)
        base_qty = float(self.hedge_base_qty)
        if base_qty <= 0:
            return

        hedge_qty = base_qty * 5.0
        if hedge_qty <= 0:
            return

        open_commission = hedge_qty * price * self.commission
        self.capital -= open_commission
        self.hedge_position = {
            "side": "SHORT",
            "avg_entry": float(price),
            "quantity": float(hedge_qty),
            "entry_time": pd.to_datetime(timestamp),
            "total_commission": float(open_commission),
        }
        self._mark_order(timestamp, price, "SELL", hedge_qty, "HEDGE_OPEN")
        self.stats["hedge_open_events"] += 1

    def _close_hedge_short(self, price: float, timestamp, reason: str):
        if self.hedge_position is None:
            return

        pos = self.hedge_position
        close_commission = pos["quantity"] * price * self.commission
        pnl = (pos["avg_entry"] - price) * pos["quantity"]
        pnl -= (pos["total_commission"] + close_commission)
        self.capital += pnl

        self.trades.append(
            {
                "entry_time": pos["entry_time"],
                "exit_time": pd.to_datetime(timestamp),
                "side": "SHORT",
                "avg_entry": pos["avg_entry"],
                "exit_price": float(price),
                "quantity": float(pos["quantity"]),
                "num_entries": 1,
                "pnl": float(pnl),
                "return_pct": (float(pnl) / self.initial_capital) * 100.0,
                "reason": reason,
            }
        )
        self._mark_order(timestamp, price, "BUY", pos["quantity"], f"HEDGE_CLOSE_{reason}")
        self.hedge_position = None
        self.stats["hedge_close_events"] += 1

    def _manage_trend_hedge(self, confirmed_trend_4h, price: float, timestamp, is_new_4h_bucket: bool):
        if not is_new_4h_bucket:
            return
        if confirmed_trend_4h not in ("bullish", "bearish"):
            return

        if confirmed_trend_4h == "bearish" and self.hedge_position is None:
            self._open_hedge_short(price, timestamp)
        elif confirmed_trend_4h == "bullish" and self.hedge_position is not None:
            self._close_hedge_short(price, timestamp, "Trend Up")

    def run(self, df_1m: pd.DataFrame, df_4h: pd.DataFrame, backtest_start_date=None):
        self.capital = self.initial_capital
        self.current_position = None
        self.position_quantity = 0.0
        self.entry_count = 0
        self.skip_count = 0
        self.stop_loss = [0.0, 0.0]
        self.pending_reentry = None
        self.last_order_time = -10**9
        self.recent_trade = [0.0, None]
        self.cooldown_time = self.base_cooldown
        self.trades = []
        self.equity_curve = []
        self.order_events = []
        self.current_trend = None
        self.hedge_position = None
        self.hedge_base_qty = 0.0
        self.bankrupt = False
        for k in self.stats:
            self.stats[k] = 0

        out_1m = df_1m.copy()
        out_4h = df_4h.copy()

        if backtest_start_date is not None:
            out_1m = out_1m[out_1m.index >= pd.Timestamp(backtest_start_date)].copy()
        if len(out_1m) == 0:
            return

        out_1m["rsi"] = self.calculate_rsi(out_1m["close"], period=self.rsi_period)
        out_1m["adx"] = self.calculate_adx(out_1m, period=ADX_PERIOD)

        out_4h["ema200_closed"] = out_4h["close"].ewm(span=EMA_PERIOD, adjust=False).mean()
        out_4h["ema200_prev_closed"] = out_4h["ema200_closed"].shift(1)
        out_4h["touch_closed"] = (out_4h["high"] >= out_4h["ema200_closed"]) & (out_4h["low"] <= out_4h["ema200_closed"])
        out_4h["touch_prev_closed"] = out_4h["touch_closed"].shift(1).fillna(False)
        out_4h["trend_4h"] = np.where(out_4h["close"] > out_4h["ema200_prev_closed"], "bullish", "bearish")
        out_4h.loc[out_4h["ema200_prev_closed"].isna(), "trend_4h"] = np.nan
        out_4h["trend_4h_confirmed"] = out_4h["trend_4h"].shift(1)

        out_1m["bucket_4h"] = out_1m.index.floor("4h")
        out_1m["is_new_4h_bucket"] = out_1m["bucket_4h"] != out_1m["bucket_4h"].shift(1)
        out_1m["run_high_4h"] = out_1m.groupby("bucket_4h")["high"].cummax()
        out_1m["run_low_4h"] = out_1m.groupby("bucket_4h")["low"].cummin()

        out_1m = out_1m.merge(
            out_4h[["ema200_prev_closed", "touch_prev_closed", "trend_4h_confirmed"]],
            left_on="bucket_4h",
            right_index=True,
            how="left",
        )
        out_1m["ema200_prev_closed"] = out_1m["ema200_prev_closed"].ffill()
        out_1m["touch_prev_closed"] = out_1m["touch_prev_closed"].fillna(False)

        alpha = 2.0 / (EMA_PERIOD + 1.0)
        out_1m["ema200_live_current"] = alpha * out_1m["close"] + (1.0 - alpha) * out_1m["ema200_prev_closed"]
        out_1m["touch_curr_sofar"] = (
            (out_1m["run_high_4h"] >= out_1m["ema200_live_current"])
            & (out_1m["run_low_4h"] <= out_1m["ema200_live_current"])
        )
        out_1m["ema_touch_live_nla"] = out_1m["touch_prev_closed"] | out_1m["touch_curr_sofar"]
        out_1m["trend_prev_ema"] = np.where(out_1m["close"] > out_1m["ema200_prev_closed"], "bullish", "bearish")
        self.signal_df = out_1m[["close", "ema200_prev_closed", "ema_touch_live_nla", "trend_prev_ema"]].copy()

        for i in range(max(EMA_PERIOD, 200), len(out_1m)):
            row = out_1m.iloc[i]
            timestamp = row.name
            price = float(row["close"])
            rsi = float(row["rsi"])
            adx = float(row["adx"])
            ema_prev = float(row["ema200_prev_closed"]) if pd.notna(row["ema200_prev_closed"]) else np.nan
            if pd.isna(rsi) or pd.isna(adx) or pd.isna(ema_prev):
                continue

            trend = row["trend_prev_ema"]
            ema_touch = bool(row["ema_touch_live_nla"])
            confirmed_trend_4h = row["trend_4h_confirmed"]
            is_new_4h_bucket = bool(row["is_new_4h_bucket"])

            self.stats["bars_processed"] += 1
            if ema_touch:
                self.stats["touch_bars"] += 1
            else:
                self.stats["entry_window_bars"] += 1

            self.current_trend = trend
            self._check_stop_loss_and_reentry(price, timestamp)
            self._manage_trend_hedge(confirmed_trend_4h, price, timestamp, is_new_4h_bucket)

            time_since_last = i - self.last_order_time
            if (not ema_touch) and time_since_last >= self.cooldown_time:
                if rsi <= self.rsi_oversold and trend == "bullish":
                    self.stats["long_signal_bars"] += 1
                    self._process_long_entry(price, timestamp, adx, i)

            self._check_take_profit(price, timestamp)
            self._record_equity(price, timestamp, ema_prev)

        if self.current_position:
            last_price = float(out_1m["close"].iloc[-1])
            last_ts = out_1m.index[-1]
            self._close_position(last_price, last_ts, "Final Close")
            self._record_equity(last_price, last_ts, float(out_1m["ema200_prev_closed"].ffill().iloc[-1]))

        if self.hedge_position:
            last_price = float(out_1m["close"].iloc[-1])
            last_ts = out_1m.index[-1]
            self._close_hedge_short(last_price, last_ts, "Final Hedge Close")
            self._record_equity(last_price, last_ts, float(out_1m["ema200_prev_closed"].ffill().iloc[-1]))


def build_drawdown_series(eq_df: pd.DataFrame) -> pd.Series:
    equity = eq_df["equity"].astype(float)
    dd = (equity - equity.cummax()) / equity.cummax().replace(0, np.nan) * 100.0
    return dd.fillna(0.0)


def save_plot(eq_df: pd.DataFrame, signal_df: pd.DataFrame, events_df: pd.DataFrame):
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={"height_ratios": [1.1, 1.3]})
    ax0, ax1 = axes

    ax0.plot(eq_df["timestamp"], eq_df["equity"], color="#111111", linewidth=1.1, label="Equity")
    ax0.axhline(INITIAL_CAPITAL, color="#777777", linestyle="--", linewidth=0.9, label=f"Start {INITIAL_CAPITAL:.0f}")
    ax0.set_title("34 Study: Live-parity No-lookahead (Long-only + Trend Short Hedge)")
    ax0.set_ylabel("Equity (USDT)")
    ax0.grid(True, alpha=0.2)
    ax0.legend(loc="upper left")

    px = signal_df.reset_index().rename(columns={"index": "timestamp"})
    ax1.plot(px["timestamp"], px["ema200_prev_closed"], color="#ff7f0e", linewidth=1.0, label="4h EMA200 (prev closed)")

    if not events_df.empty:
        buys = events_df[events_df["side"] == "BUY"]
        sells = events_df[events_df["side"] == "SELL"]
        if not buys.empty:
            ax1.scatter(buys["timestamp"], buys["price"], marker="^", s=18, color="#2ca02c", alpha=0.75, label="BUY event")
        if not sells.empty:
            ax1.scatter(sells["timestamp"], sells["price"], marker="v", s=18, color="#d62728", alpha=0.75, label="SELL event")

    ax1.set_title("Price + 4h EMA200 + Buy/Sell Events")
    ax1.set_ylabel("Price (USDT)")
    ax1.set_xlabel("Time")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left", ncol=2)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def save_report(
    bt: LiveParityNoLookahead,
    metrics: dict,
    eq_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    events_df: pd.DataFrame,
):
    dd = build_drawdown_series(eq_df)
    reason_df = pd.DataFrame(columns=["reason", "trades", "win_rate_pct", "net_pnl", "avg_pnl"])
    if not trades_df.empty:
        reason_df = (
            trades_df.groupby("reason", dropna=False)
            .agg(
                trades=("pnl", "size"),
                win_rate_pct=("pnl", lambda x: float((x > 0).mean() * 100.0)),
                net_pnl=("pnl", "sum"),
                avg_pnl=("pnl", "mean"),
            )
            .reset_index()
            .sort_values("net_pnl", ascending=False)
        )

    lines: list[str] = []
    lines.append("# 34 Backtest: Live Parity (No-lookahead, Long-only + Trend Short Hedge)")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Base target: study-33 long-only no-lookahead + existing trend short hedge logic (5x base qty).")
    lines.append("- Symbol: `BTCUSDT`")
    lines.append(f"- Initial capital: `{INITIAL_CAPITAL:.0f}`")
    lines.append(f"- Entry scale: `{ENTRY_SCALE:.2f}`")
    lines.append("- Parameters: RSI(6), oversold 18, overbought 85, TP 1.2%, SL 3.0%, max position 5x.")
    lines.append("- Data: raw cached 1m + 4h (no jump/IQR filtering).")
    lines.append("")
    lines.append("## No-lookahead Guard")
    lines.append("- Trend anchor uses previous closed 4h EMA200 only: `ema200_prev_closed`.")
    lines.append("- `ema_touch` gate uses only known info at each 1m close:")
    lines.append("  1) previous closed 4h touch, plus")
    lines.append("  2) current 4h touch-so-far from 1m cumulative high/low up to current bar.")
    lines.append("- No future 4h high/low or future 1m bars are referenced.")
    lines.append("")
    lines.append("## Metrics")
    lines.append("| Final Equity | Return % | CAGR % | MDD % | Calmar | Trades | Long/Short | Win Rate % | Profit Factor |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {_fmt(metrics.get('final_equity'))} | {_fmt(metrics.get('total_return_pct'))} | {_fmt(metrics.get('cagr_pct'))} | "
        f"{_fmt(metrics.get('max_drawdown_pct'))} | {_fmt(metrics.get('calmar_ratio'))} | {int(metrics.get('trades', 0))} | "
        f"{int(metrics.get('long_trades', 0))}/{int(metrics.get('short_trades', 0))} | {_fmt(metrics.get('win_rate_pct'))} | {_fmt(metrics.get('profit_factor'))} |"
    )
    lines.append("")
    lines.append("## Signal Stats")
    touch_ratio = (bt.stats["touch_bars"] / bt.stats["bars_processed"] * 100.0) if bt.stats["bars_processed"] > 0 else np.nan
    lines.append(f"- Processed bars: `{bt.stats['bars_processed']}`")
    lines.append(f"- EMA-touch bars: `{bt.stats['touch_bars']}` (`{_fmt(touch_ratio)}%`)")
    lines.append(f"- Entry-window bars (not touch): `{bt.stats['entry_window_bars']}`")
    lines.append(f"- Long signal bars: `{bt.stats['long_signal_bars']}`")
    lines.append(f"- Short signal bars: `{bt.stats['short_signal_bars']}`")
    lines.append(f"- Reverse events: `{bt.stats['reverse_events']}`")
    lines.append(f"- Stop-loss events: `{bt.stats['stop_loss_events']}`")
    lines.append(f"- Re-entry events: `{bt.stats['reentry_events']}`")
    lines.append(f"- Hedge open events: `{bt.stats['hedge_open_events']}`")
    lines.append(f"- Hedge close events: `{bt.stats['hedge_close_events']}`")
    if not events_df.empty:
        buy_cnt = int((events_df["side"] == "BUY").sum())
        sell_cnt = int((events_df["side"] == "SELL").sum())
        lines.append(f"- Order events (BUY/SELL): `{buy_cnt}/{sell_cnt}`")
    lines.append("")
    lines.append("## Drawdown")
    lines.append(f"- Worst drawdown: `{_fmt(abs(dd.min()))}%`")
    lines.append(f"- Average drawdown: `{_fmt(abs(dd.mean()))}%`")
    lines.append("")
    lines.append("## Reason Breakdown")
    lines.append("| Reason | Trades | Win Rate % | Net PnL | Avg PnL |")
    lines.append("|---|---:|---:|---:|---:|")
    if reason_df.empty:
        lines.append("| `N/A` | 0 | N/A | N/A | N/A |")
    else:
        for _, r in reason_df.iterrows():
            lines.append(
                f"| `{r['reason']}` | {int(r['trades'])} | {_fmt(r['win_rate_pct'])} | {_fmt(r['net_pnl'])} | {_fmt(r['avg_pnl'])} |"
            )
    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Plot: `{OUT_PNG}`")
    lines.append(f"- Report: `{OUT_MD}`")
    lines.append(f"- Metrics CSV: `{OUT_CSV}`")
    lines.append(f"- Events CSV: `{OUT_EVENTS_CSV}`")
    lines.append(f"- Trades CSV: `{OUT_TRADES_CSV}`")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def run():
    base = load_module("m002_32", BASE_002_PATH)
    helper = load_module("m04_32", BASE_04_PATH)

    df_1m, df_4h = load_data_no_filter(base)
    df_1m = df_1m[(df_1m.index >= base.BACKTEST_START) & (df_1m.index <= base.BACKTEST_END)].copy()

    bt = LiveParityNoLookahead(
        base_module=base,
        symbol=base.SYMBOL,
        initial_capital=INITIAL_CAPITAL,
        commission=base.COMMISSION,
        entry_scale=ENTRY_SCALE,
    )
    helper.configure_baseline_params(bt)
    bt.run(df_1m, df_4h, backtest_start_date=base.BACKTEST_START)

    eq_df = pd.DataFrame(bt.equity_curve)
    if eq_df.empty:
        raise RuntimeError("Empty equity curve.")
    eq_df["timestamp"] = pd.to_datetime(eq_df["timestamp"])
    eq_df = eq_df.sort_values("timestamp").reset_index(drop=True)

    trades_df = pd.DataFrame(bt.trades)
    if not trades_df.empty:
        trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
        trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])

    events_df = pd.DataFrame(bt.order_events)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"])
        events_df = events_df.sort_values("timestamp").reset_index(drop=True)

    metrics = helper.calculate_metrics(bt, INITIAL_CAPITAL)
    metrics_row = {
        "study": OUT_BASE,
        "symbol": base.SYMBOL,
        "initial_capital": INITIAL_CAPITAL,
        "entry_scale": ENTRY_SCALE,
        "final_equity": metrics.get("final_equity", np.nan),
        "total_return_pct": metrics.get("total_return_pct", np.nan),
        "cagr_pct": metrics.get("cagr_pct", np.nan),
        "max_drawdown_pct": metrics.get("max_drawdown_pct", np.nan),
        "calmar_ratio": metrics.get("calmar_ratio", np.nan),
        "trades": metrics.get("trades", 0),
        "long_trades": metrics.get("long_trades", 0),
        "short_trades": metrics.get("short_trades", 0),
        "win_rate_pct": metrics.get("win_rate_pct", np.nan),
        "profit_factor": metrics.get("profit_factor", np.nan),
        "touch_bars": bt.stats["touch_bars"],
        "entry_window_bars": bt.stats["entry_window_bars"],
        "reverse_events": bt.stats["reverse_events"],
        "stop_loss_events": bt.stats["stop_loss_events"],
        "reentry_events": bt.stats["reentry_events"],
        "hedge_open_events": bt.stats["hedge_open_events"],
        "hedge_close_events": bt.stats["hedge_close_events"],
    }
    pd.DataFrame([metrics_row]).to_csv(OUT_CSV, index=False)
    if not events_df.empty:
        events_df.to_csv(OUT_EVENTS_CSV, index=False)
    else:
        pd.DataFrame(columns=["timestamp", "price", "side", "quantity", "tag"]).to_csv(OUT_EVENTS_CSV, index=False)
    if not trades_df.empty:
        trades_df.to_csv(OUT_TRADES_CSV, index=False)
    else:
        pd.DataFrame(
            columns=["entry_time", "exit_time", "side", "avg_entry", "exit_price", "quantity", "num_entries", "pnl", "return_pct", "reason"]
        ).to_csv(OUT_TRADES_CSV, index=False)

    save_plot(eq_df, bt.signal_df, events_df)
    save_report(bt, metrics, eq_df, trades_df, events_df)

    print(f"saved_plot={OUT_PNG}")
    print(f"saved_report={OUT_MD}")
    print(f"saved_metrics={OUT_CSV}")
    print(f"saved_events={OUT_EVENTS_CSV}")
    print(f"saved_trades={OUT_TRADES_CSV}")
    print(
        f"symbol={base.SYMBOL}, final_equity={_fmt(metrics.get('final_equity'))}, "
        f"cagr={_fmt(metrics.get('cagr_pct'))}%, mdd={_fmt(metrics.get('max_drawdown_pct'))}%"
    )


if __name__ == "__main__":
    run()
