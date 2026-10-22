import numpy as np
import pandas as pd

# The segment each pair of recency and frequency scores (1 worst, 5 best) falls in, first match wins.
SEGMENTS = [
    ("champions", lambda r, f: (r >= 4) & (f >= 4)),
    ("loyal", lambda r, f: f >= 4),
    ("new", lambda r, f: (r >= 4) & (f <= 1)),
    ("promising", lambda r, f: r >= 4),
    ("at_risk", lambda r, f: (r <= 2) & (f >= 3)),
    ("lost", lambda r, f: (r <= 1) & (f <= 2)),
]
OTHERS = "needs_attention"


def _score(values, ascending):
    """1 to 5 by quintile; ties share a score, and fewer than five customers still get 1..5."""
    ranks = values.rank(method="average", ascending=ascending, pct=True)
    return np.ceil(ranks * 5).clip(lower=1, upper=5).astype("int64")


def transform(inputs, params, ctx):
    """Recency, frequency and monetary value of each customer, scored 1-5, and the segment they fall in."""
    orders = inputs["orders"].copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    as_of = orders["order_date"].max()

    rfm = orders.groupby("customer").agg(
        last_order=("order_date", "max"),
        frequency=("order_date", "count"),
        monetary=("amount", "sum"),
    )
    rfm["recency_days"] = (as_of - rfm["last_order"]).dt.days
    rfm["r_score"] = _score(rfm["recency_days"], ascending=False)
    rfm["f_score"] = _score(rfm["frequency"], ascending=True)
    rfm["m_score"] = _score(rfm["monetary"], ascending=True)

    rfm["segment"] = OTHERS
    assigned = pd.Series(False, index=rfm.index)
    for name, rule in SEGMENTS:
        hit = rule(rfm["r_score"], rfm["f_score"]) & ~assigned
        rfm.loc[hit, "segment"] = name
        assigned |= hit

    rfm = rfm.reset_index().sort_values(["segment", "monetary"], ascending=[True, False])
    return {
        "customers": rfm[
            ["customer", "recency_days", "frequency", "monetary", "r_score", "f_score", "m_score", "segment"]
        ]
    }
