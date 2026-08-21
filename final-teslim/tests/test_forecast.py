from datetime import date

import pandas as pd
import pytest

import src.forecast as forecast_module
from src.data import DATA_DIR, load_all
from src.forecast import (assign_talep_ids, calendar_multipliers,
                          forecast_horizon, to_forecast_frame)
from src.schemas import FORECAST_COLS, validate_forecast


def _daily_demand(start, end, role_values=None):
    role_values = role_values or {}
    rows = []
    next_id = 1
    for timestamp in pd.date_range(start, end, freq="D"):
        value = role_values.get(timestamp.strftime("%Y-%m-%d"), 100.0)
        for slot in ("09:00", "17:00"):
            rows.append({
                "tarih": timestamp,
                "cikis": "A",
                "varis": "B",
                "talep_id": f"X{next_id}",
                "toplam_desi": value,
                "slot": slot,
            })
            next_id += 1
    return pd.DataFrame(rows)


def test_calendar_multipliers_are_robust_role_medians():
    train = _daily_demand("2026-01-01", "2026-03-01", {
        "2026-01-30": 50,
        "2026-02-27": 50,
        "2026-01-31": 20,
        "2026-02-28": 20,
        "2026-02-01": 140,
        "2026-03-01": 140,
    })

    result = calendar_multipliers(train)

    assert result == pytest.approx({
        "day_before_month_end": 0.5,
        "month_end": 0.2,
        "first_day_after_month_end": 1.4,
        "normal": 1.0,
    })


def test_calendar_multipliers_fall_back_with_one_sample():
    train = _daily_demand("2026-01-01", "2026-02-01")

    assert calendar_multipliers(train) == {
        "day_before_month_end": 1.0,
        "month_end": 1.0,
        "first_day_after_month_end": 1.0,
        "normal": 1.0,
    }


def test_calendar_calibration_never_trains_on_target_actual(monkeypatch):
    train = _daily_demand("2026-01-01", "2026-03-01")
    checked_targets = []

    def leakage_guard(past, targets, k=4, exclude=None):
        target_date = targets["tarih"].iloc[0]
        assert (past["tarih"] < target_date).all()
        checked_targets.append(target_date)
        return pd.Series(100.0, index=targets.index)

    monkeypatch.setattr(forecast_module, "dow_median", leakage_guard)

    calendar_multipliers(train)

    assert checked_targets


def test_forecast_horizon_builds_full_grid_and_sanitizes(monkeypatch):
    demand = pd.concat([
        _daily_demand("2026-01-01", "2026-01-28"),
        _daily_demand("2026-01-01", "2026-01-28").assign(
            cikis="C", varis="D"),
    ], ignore_index=True)
    calls = []

    def fake_dow_median(train, targets, k=4, exclude=None):
        calls.append((len(train), len(targets), k))
        values = [100.0] * len(targets)
        values[0] = float("inf")
        return pd.Series(values, index=targets.index)

    monkeypatch.setattr(forecast_module, "dow_median", fake_dow_median)
    result = forecast_horizon(
        demand, date(2026, 1, 29), date(2026, 2, 1), k=3,
        multipliers={
            "day_before_month_end": 0.5,
            "month_end": -1.0,
            "first_day_after_month_end": float("nan"),
        })

    assert len(result) == 2 * 4 * 2
    assert set(result["slot"]) == {"09:00", "17:00"}
    assert calls == [(len(demand), len(result), 3)]
    assert result["forecast"].map(lambda value: value >= 0).all()
    assert result["forecast"].map(lambda value: pd.notna(value)).all()
    assert (result.loc[result["calendar_role"] == "month_end", "forecast"] == 0).all()
    assert (result.loc[
        result["calendar_role"] == "first_day_after_month_end", "forecast"] == 0).all()


def test_forecast_horizon_rejects_demand_at_or_after_cutoff():
    demand = _daily_demand("2026-01-01", "2026-01-29")

    with pytest.raises(ValueError, match="cutoff öncesi"):
        forecast_horizon(demand, date(2026, 1, 29), date(2026, 1, 30))


def test_assign_talep_ids_is_deterministic_and_checks_capacity():
    rows = pd.DataFrame([
        {"tarih": "2026-07-01", "cikis": "B", "varis": "C",
         "slot": "17:00", "forecast": 1},
        {"tarih": "2026-06-30", "cikis": "A", "varis": "C",
         "slot": "09:00", "forecast": 2},
    ])

    assigned = assign_talep_ids(rows)
    reversed_assigned = assign_talep_ids(rows.iloc[::-1])

    pd.testing.assert_frame_equal(assigned, reversed_assigned)
    assert assigned["talep_id"].tolist() == ["D00001", "D00002"]
    with pytest.raises(ValueError, match="99999"):
        assign_talep_ids(pd.DataFrame(index=range(100_000)))


def test_to_forecast_frame_uses_exact_schema_and_keeps_zeros():
    internal = pd.DataFrame([
        {"tarih": "2026-07-01", "cikis": "B", "varis": "C",
         "slot": "17:00", "forecast": -3.0},
        {"tarih": "2026-06-30", "cikis": "A", "varis": "C",
         "slot": "09:00", "forecast": 12.6},
        {"tarih": "2026-06-30", "cikis": "A", "varis": "B",
         "slot": "17:00", "forecast": float("inf")},
    ])

    result = to_forecast_frame(internal)

    assert list(result.columns) == FORECAST_COLS
    assert result["Talep ID"].tolist() == ["D00001", "D00002", "D00003"]
    assert result["Tarih"].tolist() == ["30.06.2026", "30.06.2026", "01.07.2026"]
    assert result["Tahmin Edilen Desi"].tolist() == [0, 13, 0]
    assert pd.api.types.is_integer_dtype(result["Tahmin Edilen Desi"])


@pytest.fixture(scope="module")
def real_data():
    return load_all(DATA_DIR)


def test_real_forecast_has_4046_rows_and_valid_schema(real_data):
    internal = forecast_horizon(
        real_data.demand, date(2026, 6, 29), date(2026, 7, 5))
    result = to_forecast_frame(internal)

    assert len(result) == 4046
    assert list(result.columns) == FORECAST_COLS
    assert (result["Tahmin Edilen Desi"] >= 0).all()
    assert validate_forecast(result, real_data) == []
