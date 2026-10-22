import numpy as np
import pandas as pd
import pytest

from conftest import function
from muvia_local import run

INDICATORS = function("markets/price_indicators")
VS_AVERAGE = function("markets/price_vs_average")


def test_indicators_on_a_rising_and_a_falling_series():
    ts = pd.date_range("2026-01-01", periods=60, freq="D")
    rising = pd.DataFrame({"ts": ts, "symbol": "UP", "price": 100 + np.arange(60.0)})
    falling = pd.DataFrame({"ts": ts, "symbol": "DOWN", "price": 200 - np.arange(60.0)})
    prices = run(INDICATORS, {"prices": pd.concat([falling, rising])},
                 params={"short_window": 5, "long_window": 20})["prices"]
    up = prices[prices["symbol"] == "UP"].reset_index(drop=True)
    down = prices[prices["symbol"] == "DOWN"].reset_index(drop=True)

    assert up["change_pct"].iloc[1] == pytest.approx(1.0)
    assert up["ma_short"].iloc[4] == pytest.approx(102.0) and pd.isna(up["ma_short"].iloc[3])
    assert up["trend"].iloc[-1] == "up" and down["trend"].iloc[-1] == "down"
    assert pd.isna(up["trend"].iloc[0])
    assert up["rsi"].iloc[-1] == 100.0 and down["rsi"].iloc[-1] == 0.0
    assert (up["volatility_pct"].dropna() >= 0).all()


def test_each_symbol_is_computed_on_its_own():
    ts = pd.date_range("2026-01-01", periods=3, freq="D")
    prices = pd.DataFrame({"ts": list(ts) * 2, "symbol": ["A"] * 3 + ["B"] * 3,
                           "price": [10.0, 11.0, 12.0, 50.0, 50.0, 50.0]})
    out = run(INDICATORS, {"prices": prices})["prices"]
    assert pd.isna(out[out["symbol"] == "B"]["change_pct"].iloc[0])  # B's first price follows nothing of A's


def test_price_against_the_days_average():
    prices = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2026-10-01 08:00", "2026-10-01 09:30", "2026-10-01 10:00", "2026-10-02 08:00"]),
            "seller": ["North", "South", "East", "North"],
            "product": ["diesel"] * 4,
            "price": [1.70, 1.80, 1.90, 1.75],
        }
    )
    out = run(VS_AVERAGE, {"prices": prices})["prices"]
    first_day = out.iloc[:3]
    assert first_day["average"].tolist() == [1.8, 1.8, 1.8]
    assert first_day["gap_pct"].tolist() == [-5.56, 0.0, 5.56]
    assert first_day["rank"].tolist() == [1, 2, 3] and first_day["sellers"].tolist() == [3, 3, 3]
    assert out.iloc[3][["average", "gap", "rank", "sellers"]].tolist() == [1.75, 0.0, 1, 1]
