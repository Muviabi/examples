import pandas as pd

COLUMNS = ["start", "end", "minutes"]
EMPTY = {"start": "datetime64[us]", "end": "datetime64[us]", "minutes": "float64"}


def transform(inputs, params, ctx):
    """The machine's stops, one row each, from its running signal: when each began and ended, how long it lasted."""
    minimum = float(params.get("min_minutes", 1.0))
    status = inputs["status"].sort_values("ts").reset_index(drop=True)
    if status.empty:
        return {"stops": pd.DataFrame({column: pd.Series(dtype=kind) for column, kind in EMPTY.items()})}

    running = status["running"].astype(bool)
    # A new stretch starts wherever the signal changes; each stretch ends where the next one starts.
    stretch = (running != running.shift()).cumsum()
    stretches = status.groupby(stretch).agg(start=("ts", "first"), running=("running", "first"))
    stretches["end"] = stretches["start"].shift(-1)
    # The last stretch is still open: a stop still going on ends, for now, at its last reading.
    stretches.loc[stretches.index[-1], "end"] = status["ts"].iloc[-1]

    stops = stretches[~stretches["running"].astype(bool)].copy()
    stops["minutes"] = ((stops["end"] - stops["start"]).dt.total_seconds() / 60).round(2)
    stops = stops[stops["minutes"] >= minimum]
    return {"stops": stops[COLUMNS].reset_index(drop=True)}
