from datetime import date

import pandas as pd
import pytest
from src.backtest import (EXCLUDE_2026, build_grid, wmape, bias,
                          naive_lastweek, dow_median, run_backtest)
from src.data import load_all, DATA_DIR


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def test_exclude_calendar():
    assert date(2026, 5, 27) in EXCLUDE_2026      # Kurban
    assert date(2026, 6, 29) not in EXCLUDE_2026
    assert date(2026, 3, 31) in EXCLUDE_2026      # ay sonu
    assert date(2026, 3, 30) in EXCLUDE_2026      # sondan bir önceki
    assert date(2026, 2, 28) in EXCLUDE_2026      # Şubat sonu (28 gün!)


def test_build_grid_shape_and_zero_fill(data):
    g = build_grid(data.demand, date(2026, 6, 15), date(2026, 6, 28))
    assert len(g) == 289 * 2 * 14
    assert (g["desi"] >= 0).all()
    total_in_window = data.demand[
        (data.demand["tarih"] >= "2026-06-15")
        & (data.demand["tarih"] <= "2026-06-28")]["toplam_desi"].sum()
    assert g["desi"].sum() == total_in_window


def test_metrics():
    a = pd.Series([100.0, 0.0, 50.0])
    f = pd.Series([80.0, 10.0, 50.0])
    assert abs(wmape(a, f) - 30 / 150) < 1e-9
    assert abs(bias(a, f) - (-10) / 150) < 1e-9


def test_backtest_naive_reproduces_eda(data):
    # EDA bulgusu: son 2 haftada naive-geçen-hafta ~%29,7 WMAPE
    r = run_backtest(data.demand, naive_lastweek, date(2026, 6, 15), date(2026, 6, 28))
    assert 0.25 < r["wmape"] < 0.34


def test_backtest_dow_median_beats_naive(data):
    rn = run_backtest(data.demand, naive_lastweek, date(2026, 6, 15), date(2026, 6, 28))
    rm = run_backtest(data.demand,
                      lambda tr, tg: dow_median(tr, tg, k=4),
                      date(2026, 6, 15), date(2026, 6, 28))
    assert rm["wmape"] < rn["wmape"]
    assert abs(rm["bias"]) < 0.10   # bayram-dışlamalı medyan düşük bias'lı


def test_build_grid_with_explicit_ods(data):
    full_ods = data.demand[["cikis", "varis"]].drop_duplicates()
    tek_hat = data.demand[(data.demand["cikis"] == "İstanbul")
                          & (data.demand["varis"] == "Yalova")]
    g = build_grid(tek_hat, date(2026, 6, 22), date(2026, 6, 28), ods=full_ods)
    assert len(g) == 289 * 2 * 7
    assert g["desi"].sum() == tek_hat[
        (tek_hat["tarih"] >= "2026-06-22")
        & (tek_hat["tarih"] <= "2026-06-28")]["toplam_desi"].sum()
