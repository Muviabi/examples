import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# The fewest weeks a product needs before it is forecast at all.
MIN_WEEKS = 8


def _forecast(weekly, horizon, season):
    """The next ``horizon`` weeks and a band of about 95 % around them, from exponential smoothing:
    damped trend always, a yearly-like season only with two full seasons of history."""
    seasonal = "add" if season and len(weekly) >= 2 * season else None
    model = ExponentialSmoothing(
        weekly.to_numpy(dtype=float),
        trend="add",
        damped_trend=True,
        seasonal=seasonal,
        seasonal_periods=season if seasonal else None,
        initialization_method="estimated",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # convergence notes on short series are not errors
        fitted = model.fit()
    predicted = np.clip(fitted.forecast(horizon), 0, None)
    spread = 1.96 * np.std(fitted.resid) * np.sqrt(np.arange(1, horizon + 1))
    return predicted, np.clip(predicted - spread, 0, None), predicted + spread


def transform(inputs, params, ctx):
    """Next weeks' quantity of each product, from its weekly sales."""
    horizon = int(params.get("horizon_weeks", 8))
    season = int(params.get("season_weeks", 52))
    sales = inputs["sales"].copy()
    sales["week"] = pd.to_datetime(sales["date"]).dt.to_period("W-SUN").dt.start_time

    rows = []
    for product, part in sales.groupby("product"):
        weekly = part.groupby("week")["quantity"].sum().asfreq("W-MON", fill_value=0)
        if len(weekly) < MIN_WEEKS:
            ctx.logger.info("%s: %d weeks of sales, fewer than %d: not forecast", product, len(weekly), MIN_WEEKS)
            continue
        predicted, low, high = _forecast(weekly, horizon, season)
        weeks = pd.date_range(weekly.index[-1] + pd.Timedelta(weeks=1), periods=horizon, freq="W-MON")
        rows.append(
            pd.DataFrame({"product": product, "week": weeks, "forecast": predicted, "low": low, "high": high})
        )

    columns = ["product", "week", "forecast", "low", "high"]
    forecast = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=columns)
    for column in ("forecast", "low", "high"):
        forecast[column] = forecast[column].astype(float).round(2)
    forecast["week"] = pd.to_datetime(forecast["week"])
    return {"forecast": forecast[columns]}
