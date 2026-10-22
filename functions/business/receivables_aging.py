import pandas as pd

# Days past due that close each bucket; the last bucket takes everything older.
BUCKETS = [(0, "not_due"), (30, "days_1_30"), (60, "days_31_60"), (90, "days_61_90")]
OLDEST = "over_90"


def transform(inputs, params, ctx):
    """Each customer's open receivables by how long they are past due, at the run's end."""
    invoices = inputs["invoices"].copy()
    as_of = pd.Timestamp(ctx.window.end)
    if as_of.tzinfo is not None:
        as_of = as_of.tz_convert(None)
    due = pd.to_datetime(invoices["due_date"])
    if due.dt.tz is not None:
        due = due.dt.tz_convert(None)
    invoices["days_overdue"] = (as_of - due).dt.days.clip(lower=0)

    invoices["bucket"] = OLDEST
    for limit, name in reversed(BUCKETS):
        invoices.loc[invoices["days_overdue"] <= limit, "bucket"] = name

    columns = [name for _, name in BUCKETS] + [OLDEST]
    aging = invoices.pivot_table(
        index="customer", columns="bucket", values="open_amount", aggfunc="sum", fill_value=0.0
    ).reindex(columns=columns, fill_value=0.0)
    aging["total"] = aging[columns].sum(axis=1)
    aging["oldest_days_overdue"] = invoices.groupby("customer")["days_overdue"].max()
    aging = aging.reset_index().sort_values("total", ascending=False)
    aging.columns.name = None
    return {"aging": aging[["customer", *columns, "total", "oldest_days_overdue"]]}
