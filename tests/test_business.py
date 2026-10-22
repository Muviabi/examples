from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from conftest import function
from muvia_local import ContractBroken, Window, run

AGING = function("business/receivables_aging")
RFM = function("business/rfm_segments")
PIPELINE = function("business/weighted_pipeline")
FORECAST = function("business/demand_forecast")


def test_aging_puts_each_invoice_in_its_bucket_at_the_runs_end():
    invoices = pd.DataFrame(
        {
            "customer": ["Rossi", "Rossi", "Rossi", "Bianchi", "Bianchi"],
            "due_date": pd.to_datetime(["2026-11-10", "2026-10-15", "2026-07-01", "2026-09-01", "2026-08-15"]),
            "open_amount": [100.0, 200.0, 300.0, 50.0, 25.0],
        }
    )
    aging = run(AGING, {"invoices": invoices}, window=Window(None, datetime(2026, 11, 1)))["aging"]
    rossi = aging.set_index("customer").loc["Rossi"]
    assert (rossi["not_due"], rossi["days_1_30"], rossi["over_90"], rossi["total"]) == (100, 200, 300, 600)
    assert rossi["oldest_days_overdue"] == 123
    bianchi = aging.set_index("customer").loc["Bianchi"]
    # 61 and 77 days past due: both in 61-90.
    assert (bianchi["days_31_60"], bianchi["days_61_90"]) == (0, 75)
    assert list(aging["customer"]) == ["Rossi", "Bianchi"]  # largest total first


def test_aging_refuses_a_table_without_its_due_date():
    with pytest.raises(ContractBroken, match="due_date"):
        run(AGING, {"invoices": pd.DataFrame({"customer": ["Rossi"], "open_amount": [1.0]})})


def test_rfm_scores_and_segments():
    rows = []
    for i, customer in enumerate("ABCDEFGHIJ"):
        # A orders most, most recently; J once, long ago.
        for n in range(10 - i):
            rows.append((customer, pd.Timestamp("2026-10-01") - pd.Timedelta(days=30 * i + n), 100.0 * (10 - i)))
    orders = pd.DataFrame(rows, columns=["customer", "order_date", "amount"])
    customers = run(RFM, {"orders": orders})["customers"].set_index("customer")
    assert customers.loc["A", ["r_score", "f_score", "m_score"]].tolist() == [5, 5, 5]
    assert customers.loc["J", ["r_score", "f_score", "m_score"]].tolist() == [1, 1, 1]
    assert customers.loc["A", "segment"] == "champions"
    assert customers.loc["J", "segment"] == "lost"
    assert customers["r_score"].between(1, 5).all()


def test_pipeline_weights_open_deals_and_leaves_closed_ones_out():
    deals = pd.DataFrame(
        {
            "stage": ["Proposal", "Proposal", "Negotiation", "Won", "lost"],
            "amount": [1000.0, 3000.0, 2000.0, 5000.0, 4000.0],
            "probability": [50.0, 20.0, np.nan, 100.0, 0.0],
            "expected_close": pd.to_datetime(["2026-11-03", "2026-11-28", "2026-12-10", "2026-11-01", "2026-11-01"]),
        }
    )
    pipeline = run(PIPELINE, {"deals": deals})["pipeline"]
    assert len(pipeline) == 2
    november = pipeline[pipeline["month"] == pd.Timestamp("2026-11-01")].iloc[0]
    assert (november["deals"], november["amount"], november["weighted_amount"]) == (2, 4000, 1100)
    december = pipeline[pipeline["month"] == pd.Timestamp("2026-12-01")].iloc[0]
    assert december["weighted_amount"] == 0  # no probability, no weight


def test_pipeline_reads_probabilities_as_fractions_when_told():
    deals = pd.DataFrame(
        {"stage": ["Proposal"], "amount": [1000.0], "probability": [0.4],
         "expected_close": pd.to_datetime(["2026-11-03"])}
    )
    pipeline = run(PIPELINE, {"deals": deals}, params={"probability_in_percent": False})["pipeline"]
    assert pipeline["weighted_amount"].iloc[0] == 400


def test_forecast_follows_a_steady_trend_and_skips_short_histories():
    days = pd.date_range("2026-01-05", periods=30 * 7, freq="D")
    steady = pd.DataFrame({"date": days, "product": "bolts", "quantity": 10.0 + np.arange(len(days)) * 0.1})
    short = pd.DataFrame({"date": days[:20], "product": "nuts", "quantity": 5.0})
    forecast = run(FORECAST, {"sales": pd.concat([steady, short])}, params={"horizon_weeks": 4})["forecast"]
    assert set(forecast["product"]) == {"bolts"}
    assert len(forecast) == 4
    last_week = steady.groupby(steady["date"].dt.to_period("W-SUN"))["quantity"].sum().iloc[-1]
    assert forecast["forecast"].iloc[0] == pytest.approx(last_week + 4.9, rel=0.05)
    assert (forecast["low"] <= forecast["forecast"]).all() and (forecast["forecast"] <= forecast["high"]).all()
    assert forecast["week"].iloc[0] == pd.Timestamp("2026-08-03")
