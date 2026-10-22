import pandas as pd


def transform(inputs, params, ctx):
    """Each reading's distance from its recent normal, in standard deviations, and whether it is an anomaly."""
    window = int(params.get("window", 60))
    threshold = float(params.get("threshold", 3.0))
    column = params.get("column") or "value"

    # Sorted, then a fresh index: the rolling figures line up with the rows they were computed on.
    rows = inputs["readings"].sort_values("ts").reset_index(drop=True)
    values = rows[column].astype(float)
    # The normal is the window before each reading, the reading itself left out.
    history = values.shift(1).rolling(window, min_periods=max(5, window // 4))
    mean, std = history.mean(), history.std()
    rows["zscore"] = ((values - mean) / std.where(std > 0)).round(3)
    rows["anomaly"] = rows["zscore"].abs() >= threshold
    return {"readings": rows}
