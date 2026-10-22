import pandas as pd


def _kind(series):
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "time"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    return "text"


def transform(inputs, params, ctx):
    """One row per column of the table: its kind, how many values are missing, how many distinct, its range."""
    rows = inputs["rows"]
    total = len(rows)
    profile = []
    for name in rows.columns:
        series = rows[name]
        kind = _kind(series)
        present = series.dropna()
        ranged = kind in ("number", "time") and not present.empty
        profile.append(
            {
                "column": str(name),
                "kind": kind,
                "rows": total,
                "missing": int(total - len(present)),
                "missing_pct": round((total - len(present)) / total * 100, 2) if total else 0.0,
                "distinct": int(present.nunique()),
                "minimum": str(present.min()) if ranged else None,
                "maximum": str(present.max()) if ranged else None,
            }
        )
    return {"profile": pd.DataFrame(profile, columns=["column", "kind", "rows", "missing", "missing_pct",
                                                      "distinct", "minimum", "maximum"])}
