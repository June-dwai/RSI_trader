# 00_3 Study: 4h RSI(6) under BTC Price

## Setup
- Symbol: `BTCUSDT`
- Data period: `2022-01-01 00:00:00` ~ `2026-02-12 00:00:00`
- Data source: raw cached 1m/4h (no additional filtering)
- RSI definition: Wilder-style `RSI(6)` on 4h close
- Regime thresholds: low `<= 15`, high `>= 85`
- No-lookahead for display: `rsi6_confirmed = rsi6_raw.shift(1)`
- Shading: RSI>=85 intervals = light green, RSI<=15 intervals = light red (all panels)
- Added feature: `ema_rsi_mix_feature = ema_gap_pct * abs(rsi6_confirmed - 50)`
- where `ema_gap_pct = (close - ema200) / ema200 * 100`
- Added feature2: `ema_rsi_adx_mix_feature = ema_rsi_mix_feature * adx14_confirmed`
- where `adx14_confirmed = adx14_raw.shift(1)` on 4h

## 4h RSI Summary
- Bars: `10111`
- Mean / Std: `50.8078` / `18.5732`
- Time RSI<=15: `2.5418%`
- Time RSI>=85: `3.3726%`

## Conditional Next 4h Return (for quick intuition)
- Avg next 4h return when RSI<=15: `-0.0676%`
- Avg next 4h return when 15<RSI<85: `0.0118%`
- Avg next 4h return when RSI>=85: `0.1162%`

## Feature Summary
- Feature1 = `ema_gap_pct * abs(rsi6_confirmed - 50)`
  - Mean / Std: `10.3629` / `171.2035`
  - P10 / P50 / P90: `-129.9294` / `0.0495` / `171.4542`
- Feature2 = `Feature1 * adx14_confirmed`
  - Mean / Std: `508.7867` / `9496.8431`
  - P10 / P50 / P90: `-5035.5600` / `1.5397` / `6743.7970`

## Outputs
- Plot: `00_3_backtest_btcusdt_price_rsi6_4h.png`
- 4h data: `00_3_backtest_btcusdt_price_rsi6_4h_4h.csv`
- Report: `00_3_backtest_btcusdt_price_rsi6_4h.md`