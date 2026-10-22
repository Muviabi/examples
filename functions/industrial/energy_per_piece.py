def transform(inputs, params, ctx):
    """Watt-hours per piece of each period, and how far it is from the usual, so a drift shows early."""
    rows = inputs["energy"].copy()
    pieces = rows["pieces"].where(rows["pieces"] > 0)
    rows["wh_per_piece"] = (rows["kwh"] * 1000 / pieces).round(2)
    # The usual is the median of the periods that made pieces: a few odd periods do not move it.
    baseline = rows["wh_per_piece"].median()
    rows["vs_baseline_pct"] = ((rows["wh_per_piece"] / baseline - 1) * 100).round(1) if baseline else float("nan")
    rows["idle_energy"] = rows["pieces"].fillna(0).le(0) & rows["kwh"].gt(0)
    return {"energy": rows}
