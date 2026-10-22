def transform(inputs, params, ctx):
    """Availability, performance, quality and OEE of each row: a shift, a day, an order."""
    rows = inputs["production"].copy()
    planned = rows["planned_minutes"].where(rows["planned_minutes"] > 0)
    running = rows["run_minutes"].where(rows["run_minutes"] > 0)
    total = rows["total_pieces"].where(rows["total_pieces"] > 0)

    rows["availability"] = (rows["run_minutes"] / planned).clip(upper=1)
    # Performance: the time the pieces made should have taken, over the time the line ran.
    rows["performance"] = (rows["total_pieces"] * rows["ideal_cycle_seconds"] / 60 / running).clip(upper=1)
    rows["quality"] = rows["good_pieces"] / total
    rows["oee"] = rows["availability"] * rows["performance"] * rows["quality"]

    for column in ("availability", "performance", "quality", "oee"):
        rows[column] = (rows[column].fillna(0.0) * 100).round(1)
    return {"production": rows}
