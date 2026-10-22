import numpy as np


def _rsi(prices, periods):
    """Relative strength index, Wilder's smoothing: 0-100, above 70 overbought, below 30 oversold."""
    change = prices.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / periods, min_periods=periods, adjust=False).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / periods, min_periods=periods, adjust=False).mean()
    # 100 - 100 / (1 + gain / loss), written so that a series that never fell reads 100, not nothing.
    return 100 * gain / (gain + loss).replace(0, np.nan)


def transform(inputs, params, ctx):
    """Moving averages, daily change, volatility and RSI of each instrument's price series."""
    short = int(params.get("short_window", 20))
    long = int(params.get("long_window", 50))
    rsi_periods = int(params.get("rsi_periods", 14))

    prices = inputs["prices"].sort_values(["symbol", "ts"]).reset_index(drop=True)
    by_symbol = prices.groupby("symbol")["price"]
    prices["change_pct"] = (by_symbol.pct_change() * 100).round(3)
    prices["ma_short"] = by_symbol.transform(lambda p: p.rolling(short, min_periods=short).mean()).round(4)
    prices["ma_long"] = by_symbol.transform(lambda p: p.rolling(long, min_periods=long).mean()).round(4)
    # Volatility: the spread of the last ``short`` daily changes, scaled to a year of 252 sessions.
    prices["volatility_pct"] = (
        prices.groupby("symbol")["change_pct"].transform(lambda c: c.rolling(short, min_periods=short).std())
        * np.sqrt(252)
    ).round(2)
    prices["rsi"] = by_symbol.transform(lambda p: _rsi(p, rsi_periods)).round(1)
    prices["trend"] = np.where(
        prices["ma_short"].isna() | prices["ma_long"].isna(),
        None,
        np.where(prices["ma_short"] > prices["ma_long"], "up", "down"),
    )
    prices["trend"] = prices["trend"].astype("string")
    return {"prices": prices}
