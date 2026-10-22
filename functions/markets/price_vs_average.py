def transform(inputs, params, ctx):
    """Each seller's price against the average of all sellers of the same product on the same day."""
    prices = inputs["prices"].copy()
    prices["day"] = prices["ts"].dt.floor("D")
    same_day = prices.groupby(["day", "product"])["price"]
    prices["average"] = same_day.transform("mean").round(4)
    prices["gap"] = (prices["price"] - prices["average"]).round(4)
    prices["gap_pct"] = (prices["gap"] / prices["average"] * 100).round(2)
    # Rank 1 is the cheapest of the day for that product.
    prices["rank"] = same_day.rank(method="min").astype("int64")
    prices["sellers"] = same_day.transform("size").astype("int64")
    return {"prices": prices.drop(columns="day")}
