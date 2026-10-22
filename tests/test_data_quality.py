import numpy as np
import pandas as pd
import pytest

from conftest import function
from muvia_local import run

PROFILE = function("data_quality/column_profile")
DUPLICATES = function("data_quality/duplicate_rows")
RANGES = function("data_quality/range_checks")

ROWS = pd.DataFrame(
    {
        "order": ["A1", "A2", "A2", "A3", "A4"],
        "customer": ["Rossi", "Bianchi", "Bianchi", None, "Rossi"],
        "amount": [10.0, 20.0, 20.0, np.nan, -5.0],
        "placed": pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-02", "2026-10-03", None]),
    }
)


def test_profile_counts_missing_distinct_and_range_per_column():
    profile = run(PROFILE, {"rows": ROWS})["profile"].set_index("column")
    assert profile.loc["customer", ["kind", "rows", "missing", "missing_pct", "distinct"]].tolist() == [
        "text", 5, 1, 20.0, 2]
    assert profile.loc["amount", ["kind", "minimum", "maximum"]].tolist() == ["number", "-5.0", "20.0"]
    assert profile.loc["placed", "kind"] == "time" and profile.loc["placed", "missing"] == 1
    assert pd.isna(profile.loc["order", "minimum"])  # text has no range


def test_duplicates_on_the_key_you_name():
    duplicates = run(DUPLICATES, {"rows": ROWS}, params={"key_columns": "order"})["duplicates"]
    assert duplicates["order"].tolist() == ["A2", "A2"]
    assert duplicates["copies"].tolist() == [2, 2] and duplicates["duplicate_group"].tolist() == [1, 1]


def test_duplicates_on_every_column_by_default_and_unknown_keys_refused():
    assert len(run(DUPLICATES, {"rows": ROWS})["duplicates"]) == 2
    with pytest.raises(ValueError, match="no column sku"):
        run(DUPLICATES, {"rows": ROWS}, params={"key_columns": "order, sku"})


def test_range_checks_name_each_problem():
    violations = run(RANGES, {"rows": ROWS}, params={"column": "amount", "minimum": 0, "maximum": 15})["violations"]
    assert dict(zip(violations["order"], violations["problem"])) == {
        "A2": "above 15", "A3": "missing", "A4": "below 0"}


def test_range_checks_without_a_limit_report_only_missing_values():
    violations = run(RANGES, {"rows": ROWS}, params={"column": "amount"})["violations"]
    assert violations["problem"].tolist() == ["missing"]
