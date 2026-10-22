import pandas as pd


def transform(inputs, params, ctx):
    """The rows whose value is missing or outside the range you set, each with what is wrong with it."""
    column = params["column"]
    minimum = params.get("minimum")
    maximum = params.get("maximum")
    rows = inputs["rows"].copy()
    values = pd.to_numeric(rows[column], errors="coerce")

    rows["problem"] = None
    rows.loc[values.isna(), "problem"] = "missing"
    if minimum is not None:
        rows.loc[values < minimum, "problem"] = f"below {minimum}"
    if maximum is not None:
        rows.loc[values > maximum, "problem"] = f"above {maximum}"
    rows["problem"] = rows["problem"].astype("string")
    return {"violations": rows[rows["problem"].notna()].reset_index(drop=True)}
