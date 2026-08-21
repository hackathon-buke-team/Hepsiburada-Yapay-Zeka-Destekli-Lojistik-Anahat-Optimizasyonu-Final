"""Tahmin backtest altyapısı: tam grid, WMAPE/bias, baseline modeller.

Grid kuralı: talep verisinde görünmeyen (tarih, OD, slot) hücresi desi=0
demektir (EDA: her aktif hücre tam 1 satır).
"""
from __future__ import annotations

import calendar
from datetime import date

import pandas as pd

_HOLIDAYS = [
    date(2026, 1, 1),
    date(2026, 3, 19), date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),
    date(2026, 4, 23),
    date(2026, 5, 1),
    date(2026, 5, 19),
    date(2026, 5, 25), date(2026, 5, 26), date(2026, 5, 27), date(2026, 5, 28),
    date(2026, 5, 29), date(2026, 5, 30), date(2026, 5, 31),
]


def _month_ends() -> list:
    out = []
    for m in range(1, 6):
        last = calendar.monthrange(2026, m)[1]
        out += [date(2026, m, last), date(2026, m, last - 1)]
    return out


# Ay sonu dışlama listesi BİLEREK yalnız Ocak-Mayıs'ı kapsar: veri 28
# Haziran'da bitiyor ve Haziran'ın son iki günü (29-30) tahmin UFKUNUN
# içinde. Bu set yalnızca geçmiş-veri (eğitim) filtresidir; hedef günler
# asla bu listeyle dışlanmaz.
EXCLUDE_2026 = set(_HOLIDAYS) | set(_month_ends())


def build_grid(demand: pd.DataFrame, start: date, end: date,
               ods: pd.DataFrame = None) -> pd.DataFrame:
    """Tam grid: ods x 2 slot x [start..end]; görünmeyen hücre desi=0.

    ods verilmezse demand'dan türetilir — FİLTRELENMİŞ bir dilim
    geçiriyorsanız çift kaybını önlemek için tam OD listesini verin.
    """
    if ods is None:
        ods = demand[["cikis", "varis"]].drop_duplicates()
    dates = pd.DataFrame({"tarih": pd.date_range(start, end, freq="D")})
    slots = pd.DataFrame({"slot": ["09:00", "17:00"]})
    grid = ods.merge(dates, how="cross").merge(slots, how="cross")
    actual = demand.groupby(["cikis", "varis", "tarih", "slot"], as_index=False)[
        "toplam_desi"].sum()
    grid = grid.merge(actual, on=["cikis", "varis", "tarih", "slot"], how="left")
    grid["desi"] = grid["toplam_desi"].fillna(0).astype(float)
    return grid.drop(columns=["toplam_desi"])


def wmape(actual: pd.Series, forecast: pd.Series) -> float:
    return float((actual - forecast).abs().sum() / actual.sum())


def bias(actual: pd.Series, forecast: pd.Series) -> float:
    return float((forecast - actual).sum() / actual.sum())


def naive_lastweek(train: pd.DataFrame, targets: pd.DataFrame) -> pd.Series:
    hist = build_grid(train, train["tarih"].min().date(), train["tarih"].max().date())
    hist_idx = hist.set_index(["cikis", "varis", "slot", "tarih"])["desi"]
    keys = list(zip(targets["cikis"], targets["varis"], targets["slot"],
                    targets["tarih"] - pd.Timedelta(days=7)))
    return pd.Series([hist_idx.get(k, 0.0) for k in keys], index=targets.index)


def dow_median(train: pd.DataFrame, targets: pd.DataFrame, k: int = 4,
               exclude: set = EXCLUDE_2026) -> pd.Series:
    hist = build_grid(train, train["tarih"].min().date(), train["tarih"].max().date())
    hist = hist[~hist["tarih"].dt.date.isin(exclude)].copy()
    hist["dow"] = hist["tarih"].dt.dayofweek
    hist = hist.sort_values("tarih")
    grouped = {key: g[["tarih", "desi"]].to_numpy()
               for key, g in hist.groupby(["cikis", "varis", "slot", "dow"])}
    out = []
    for _, t in targets.iterrows():
        key = (t["cikis"], t["varis"], t["slot"], t["tarih"].dayofweek)
        arr = grouped.get(key)
        if arr is None:
            out.append(0.0)
            continue
        past = [d for dt_, d in arr if dt_ < t["tarih"]][-k:]
        out.append(float(pd.Series(past).median()) if past else 0.0)
    return pd.Series(out, index=targets.index)


def run_backtest(demand: pd.DataFrame, model_fn, test_start: date,
                 test_end: date) -> dict:
    """Rolling-origin backtest.

    DİKKAT: train, test_end dahil TÜM veriyi içerir (rolling-origin).
    model_fn her hedef satır için yalnızca o satırın tarihinden ÖNCEKİ
    verileri kullanmakla yükümlüdür (naive: t-7 lookup; dow_median:
    dt < hedef tarih filtresi). Aynı-gün/gelecek satır kullanan bir
    model_fn burada sessizce sızıntı yapar — yazma.
    """
    train = demand[demand["tarih"] <= pd.Timestamp(test_end)]
    ods = demand[["cikis", "varis"]].drop_duplicates()
    targets = build_grid(
        demand[(demand["tarih"] >= pd.Timestamp(test_start))
               & (demand["tarih"] <= pd.Timestamp(test_end))],
        test_start, test_end, ods=ods)
    forecast = model_fn(train, targets)
    return {"wmape": wmape(targets["desi"], forecast),
            "bias": bias(targets["desi"], forecast)}
