import numpy as np
import pandas as pd
import pytest

from conftest import function
from muvia_local import run

OEE = function("industrial/oee")
ANOMALIES = function("industrial/signal_anomalies")
STOPS = function("industrial/stop_events")
ENERGY = function("industrial/energy_per_piece")


def test_oee_of_a_textbook_shift():
    # 480 planned, 420 running: 87.5 %; 19 271 pieces at 1.2 s ideal = 385.42 min of 420: 91.77 %;
    # 18 848 good of 19 271: 97.81 %; OEE 78.5 %.
    production = pd.DataFrame(
        {"line": ["L1", "L2"], "planned_minutes": [480.0, 0.0], "run_minutes": [420.0, 0.0],
         "ideal_cycle_seconds": [1.2, 1.2], "total_pieces": [19271.0, 0.0], "good_pieces": [18848.0, 0.0]}
    )
    rows = run(OEE, {"production": production})["production"]
    first = rows.iloc[0]
    assert (first["availability"], first["performance"], first["quality"], first["oee"]) == (87.5, 91.8, 97.8, 78.5)
    assert rows.iloc[1]["oee"] == 0  # a line that was not planned scores nothing, not a division by zero
    assert list(rows["line"]) == ["L1", "L2"]  # the rows' own columns stay


def test_a_spike_is_an_anomaly_and_the_steady_signal_is_not():
    rng = np.random.default_rng(7)
    values = 50 + rng.normal(0, 1, 200)
    values[150] = 70
    readings = pd.DataFrame({"ts": pd.date_range("2026-10-01", periods=200, freq="min"), "value": values})
    shuffled = readings.sample(frac=1, random_state=1)  # rows out of order still line up
    rows = run(ANOMALIES, {"readings": shuffled}, params={"window": 60, "threshold": 4})["readings"]
    assert rows["anomaly"].sum() == 1
    assert rows.loc[rows["anomaly"], "ts"].iloc[0] == readings["ts"].iloc[150]
    assert rows["zscore"].iloc[:14].isna().all()  # too few readings before them to judge


def test_anomalies_read_the_column_the_parameter_names():
    readings = pd.DataFrame({"ts": pd.date_range("2026-10-01", periods=30, freq="h"),
                             "pressure": [1.0, 1.1] * 14 + [1.05, 9.0]})
    rows = run(ANOMALIES, {"readings": readings}, params={"column": "pressure", "window": 20})["readings"]
    assert bool(rows["anomaly"].iloc[-1]) and rows["anomaly"].sum() == 1


def test_stops_are_found_and_short_ones_dropped():
    ts = pd.to_datetime(["2026-10-01 08:00:00", "2026-10-01 08:10:00", "2026-10-01 08:40:00",
                         "2026-10-01 08:40:30", "2026-10-01 09:00:00", "2026-10-01 09:15:00"])
    status = pd.DataFrame({"ts": ts, "running": [True, False, True, False, True, False]})
    stops = run(STOPS, {"status": status}, params={"min_minutes": 1})["stops"]
    # 08:10-08:40 (30 min); 08:40:30-09:00 (19.5); 09:15 still stopped, 0 min so far: dropped.
    assert stops["minutes"].tolist() == [30.0, 19.5]
    assert stops["start"].iloc[0] == pd.Timestamp("2026-10-01 08:10")


def test_no_readings_no_stops():
    status = pd.DataFrame({"ts": pd.to_datetime([]), "running": pd.Series([], dtype=bool)})
    assert run(STOPS, {"status": status})["stops"].empty


def test_energy_per_piece_against_the_median():
    energy = pd.DataFrame({"hour": pd.date_range("2026-10-01", periods=4, freq="h"),
                           "kwh": [10.0, 10.0, 12.0, 3.0], "pieces": [1000.0, 1000.0, 1000.0, 0.0]})
    rows = run(ENERGY, {"energy": energy})["energy"]
    assert rows["wh_per_piece"].tolist()[:3] == [10.0, 10.0, 12.0]
    assert rows["vs_baseline_pct"].iloc[2] == pytest.approx(20.0)
    assert rows["idle_energy"].tolist() == [False, False, False, True]
