import pandas as pd

# Stages whose deals no longer count as pipeline, in the CRM's own words (compared in lower case).
CLOSED = {"won", "lost", "closed won", "closed lost"}


def transform(inputs, params, ctx):
    """The open pipeline by expected closing month and stage, each deal weighted by its probability."""
    deals = inputs["deals"].copy()
    deals = deals[~deals["stage"].str.strip().str.lower().isin(CLOSED)]
    probability = deals["probability"].fillna(0.0)
    if params.get("probability_in_percent", True):
        probability = probability / 100
    deals["weighted_amount"] = deals["amount"] * probability.clip(lower=0, upper=1)
    deals["month"] = pd.to_datetime(deals["expected_close"]).dt.to_period("M").dt.to_timestamp()

    pipeline = (
        deals.groupby(["month", "stage"], as_index=False)
        .agg(deals=("amount", "size"), amount=("amount", "sum"), weighted_amount=("weighted_amount", "sum"))
        .sort_values(["month", "weighted_amount"], ascending=[True, False])
    )
    return {"pipeline": pipeline}
