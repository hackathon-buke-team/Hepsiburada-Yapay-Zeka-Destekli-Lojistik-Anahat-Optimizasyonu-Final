from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.backtest import dow_median
from src.data import DATA_DIR, load_all
from src.frozen_backtest import run_frozen


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _demand(rows):
    frame = pd.DataFrame(
        rows, columns=["tarih", "cikis", "varis", "slot", "toplam_desi"])
    frame["tarih"] = pd.to_datetime(frame["tarih"])
    return frame


def test_frozen_dow_median_on_real_data(data):
    result = run_frozen(
        data.demand,
        lambda train, targets: dow_median(train, targets, k=4),
        cutoff=date(2026, 6, 14),
        horizon_start=date(2026, 6, 15),
        horizon_end=date(2026, 6, 28),
    )

    assert result["n_cells"] == 289 * 2 * 14
    assert 0.20 < result["wmape"] < 0.25
    assert abs(result["bias"]) < 0.05
    assert list(result["evaluation"].columns) == [
        "cikis", "varis", "tarih", "slot", "actual", "forecast",
        "error", "absolute_error",
    ]


def test_default_od_universe_and_model_inputs_are_frozen():
    demand = _demand([
        ("2026-01-01", "A", "B", "09:00", 10),
        ("2026-01-02", "A", "B", "17:00", 20),
        ("2026-01-03", "A", "B", "09:00", 30),
        ("2026-01-03", "FUTURE", "ONLY", "09:00", 999),
    ])
    seen = {}

    def model(train, target_metadata):
        seen["train"] = train.copy()
        seen["targets"] = target_metadata.copy()
        return pd.Series(0.0, index=target_metadata.index)

    result = run_frozen(
        demand, model, cutoff=date(2026, 1, 2),
        horizon_start=date(2026, 1, 3), horizon_end=date(2026, 1, 3))

    assert seen["train"]["tarih"].max() == pd.Timestamp("2026-01-02")
    assert (seen["train"]["tarih"] <= pd.Timestamp("2026-01-02")).all()
    assert "desi" not in seen["targets"].columns
    assert "toplam_desi" not in seen["targets"].columns
    assert set(zip(seen["targets"]["cikis"], seen["targets"]["varis"])) == {("A", "B")}
    assert result["n_cells"] == 2
    assert result["evaluation"]["actual"].sum() == 30


def test_explicit_od_universe_is_used_for_actual_and_targets():
    demand = _demand([
        ("2026-01-01", "A", "B", "09:00", 10),
        ("2026-01-02", "X", "Y", "09:00", 40),
    ])
    ods = pd.DataFrame({"cikis": ["A", "X"], "varis": ["B", "Y"]})

    result = run_frozen(
        demand,
        lambda _train, targets: pd.Series(0.0, index=targets.index),
        cutoff=date(2026, 1, 1),
        horizon_start=date(2026, 1, 2),
        horizon_end=date(2026, 1, 2),
        ods=ods,
    )

    assert result["n_cells"] == 4
    assert set(zip(result["evaluation"]["cikis"],
                   result["evaluation"]["varis"])) == {("A", "B"), ("X", "Y")}
    assert result["evaluation"]["actual"].sum() == 40


@pytest.mark.parametrize("cutoff", [date(2026, 1, 2), date(2026, 1, 3)])
def test_cutoff_must_be_before_horizon(cutoff):
    demand = _demand([
        ("2026-01-01", "A", "B", "09:00", 10),
        ("2026-01-02", "A", "B", "09:00", 20),
    ])

    with pytest.raises(ValueError, match="cutoff.*horizon_start.*önce"):
        run_frozen(
            demand, lambda _train, targets: [0.0] * len(targets),
            cutoff=cutoff, horizon_start=date(2026, 1, 2),
            horizon_end=date(2026, 1, 2))


def test_horizon_start_must_not_be_after_end():
    demand = _demand([
        ("2026-01-01", "A", "B", "09:00", 10),
    ])

    with pytest.raises(ValueError, match="horizon_start.*horizon_end"):
        run_frozen(
            demand, lambda _train, targets: [0.0] * len(targets),
            cutoff=date(2026, 1, 1), horizon_start=date(2026, 1, 3),
            horizon_end=date(2026, 1, 2))


@pytest.fixture
def validation_case():
    demand = _demand([
        ("2026-01-01", "A", "B", "09:00", 10),
        ("2026-01-02", "A", "B", "09:00", 20),
    ])

    def run(model):
        return run_frozen(
            demand, model, cutoff=date(2026, 1, 1),
            horizon_start=date(2026, 1, 2), horizon_end=date(2026, 1, 2))

    return run


def test_rejects_wrong_forecast_length(validation_case):
    with pytest.raises(ValueError, match="Tahmin uzunluğu.*beklenen 2"):
        validation_case(lambda _train, _targets: [1.0])


def test_rejects_wrong_forecast_index(validation_case):
    with pytest.raises(ValueError, match="Tahmin indeksi"):
        validation_case(
            lambda _train, _targets: pd.Series([1.0, 2.0], index=[10, 11]))


@pytest.mark.parametrize("forecast", [
    ["1", "2"],
    [1.0, np.nan],
    [1.0, np.inf],
    [1.0, -0.1],
])
def test_rejects_invalid_forecast_values(validation_case, forecast):
    message = (
        "sayısal" if isinstance(forecast[0], str)
        else "sonlu" if not np.isfinite(np.asarray(forecast, dtype=float)).all()
        else "nonnegative"
    )
    with pytest.raises(ValueError, match=message):
        validation_case(lambda _train, _targets: forecast)


def test_metrics_and_evaluation_values(validation_case):
    result = validation_case(
        lambda _train, targets: pd.Series([10.0, 0.0], index=targets.index))

    assert result["wmape"] == pytest.approx(0.5)
    assert result["bias"] == pytest.approx(-0.5)
    assert result["evaluation"]["forecast"].tolist() == [10.0, 0.0]
    assert result["evaluation"]["error"].tolist() == [-10.0, 0.0]
