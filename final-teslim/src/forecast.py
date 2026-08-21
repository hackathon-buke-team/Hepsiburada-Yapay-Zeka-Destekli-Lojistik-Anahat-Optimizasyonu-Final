"""Talep tahmini: DOW medyan tabanı, takvim etkileri ve şablon çıktısı."""
from __future__ import annotations

import calendar
import math
from datetime import date
from typing import Mapping

import pandas as pd

from src.backtest import EXCLUDE_2026, build_grid, dow_median
from src.schemas import FORECAST_COLS

CALENDAR_ROLES = (
    "day_before_month_end",
    "month_end",
    "first_day_after_month_end",
    "normal",
)
MIN_CALENDAR_SAMPLES = 2
MAX_TALEP_ID = 99_999
_SORT_COLS = ["tarih", "cikis", "varis", "slot"]


def _as_timestamp(value, label: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} geçerli bir tarih olmalı: {value!r}") from exc
    if pd.isna(timestamp):
        raise ValueError(f"{label} geçerli bir tarih olmalı: {value!r}")
    if timestamp.tz is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _calendar_role(value) -> str:
    timestamp = pd.Timestamp(value)
    last_day = calendar.monthrange(timestamp.year, timestamp.month)[1]
    if timestamp.day == last_day:
        return "month_end"
    if timestamp.day == last_day - 1:
        return "day_before_month_end"
    if timestamp.day == 1:
        return "first_day_after_month_end"
    return "normal"


def _require_demand_columns(demand: pd.DataFrame) -> None:
    required = {"tarih", "cikis", "varis", "slot", "toplam_desi"}
    missing = sorted(required - set(demand.columns))
    if missing:
        raise ValueError(f"demand kolonları eksik: {missing}")


def _normalise_demand(demand: pd.DataFrame) -> pd.DataFrame:
    _require_demand_columns(demand)
    out = demand.copy()
    out["tarih"] = pd.to_datetime(out["tarih"], errors="raise").dt.normalize()
    return out


def _normalise_ods(demand: pd.DataFrame, ods: pd.DataFrame | None) -> pd.DataFrame:
    source = demand[["cikis", "varis"]] if ods is None else ods
    missing = {"cikis", "varis"} - set(source.columns)
    if missing:
        raise ValueError(f"ods kolonları eksik: {sorted(missing)}")
    return (source[["cikis", "varis"]]
            .drop_duplicates()
            .sort_values(["cikis", "varis"], kind="mergesort")
            .reset_index(drop=True))


def _safe_nonnegative(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype(float)
    numeric = numeric.replace([float("inf"), -float("inf")], 0.0).fillna(0.0)
    return numeric.clip(lower=0.0)


def calendar_multipliers(train: pd.DataFrame) -> dict[str, float]:
    """Geçmiş ay sonlarından leakage-free global robust rol çarpanları çıkar.

    Her olay gününün toplam actual hacmi, aynı hücreler için hesaplanan DOW
    medyan tabanının toplamına bölünür. Taban çağrısına olay günü ve daha yeni
    actual'lar verilmez. Rol başına en az iki sonlu, nonnegative oran yoksa
    güvenli ``1.0`` fallback'i kullanılır. ``normal`` rolü tanım gereği 1.0'dır.
    """
    if train.empty:
        return {role: 1.0 for role in CALENDAR_ROLES}

    history = _normalise_demand(train)
    start = history["tarih"].min()
    end = history["tarih"].max()
    if pd.isna(start) or pd.isna(end):
        return {role: 1.0 for role in CALENDAR_ROLES}

    ods = _normalise_ods(history, None)
    if ods.empty:
        return {role: 1.0 for role in CALENDAR_ROLES}

    dates = pd.date_range(start, end, freq="D")
    event_dates = [timestamp for timestamp in dates
                   if _calendar_role(timestamp) != "normal"]
    dynamic_exclude = {
        timestamp.date() for timestamp in dates
        if _calendar_role(timestamp) in {"day_before_month_end", "month_end"}
    }
    baseline_exclude = set(EXCLUDE_2026) | dynamic_exclude
    ratios = {role: [] for role in CALENDAR_ROLES if role != "normal"}

    for target_date in event_dates:
        past = history[history["tarih"] < target_date]
        if past.empty:
            continue

        targets = build_grid(
            history, target_date.date(), target_date.date(), ods=ods)
        baseline = dow_median(
            past, targets, k=4, exclude=baseline_exclude)
        actual_total = float(pd.to_numeric(
            targets["desi"], errors="coerce").sum())
        baseline_total = float(pd.to_numeric(
            baseline, errors="coerce").sum())
        if (not math.isfinite(actual_total) or actual_total < 0
                or not math.isfinite(baseline_total) or baseline_total <= 0):
            continue

        ratio = actual_total / baseline_total
        if math.isfinite(ratio) and ratio >= 0:
            ratios[_calendar_role(target_date)].append(ratio)

    result = {"normal": 1.0}
    for role in CALENDAR_ROLES[:-1]:
        samples = ratios[role]
        result[role] = (float(pd.Series(samples, dtype=float).median())
                        if len(samples) >= MIN_CALENDAR_SAMPLES else 1.0)
    return {role: result[role] for role in CALENDAR_ROLES}


def forecast_horizon(
        demand: pd.DataFrame, start: date, end: date,
        ods: pd.DataFrame | None = None, k: int = 4,
        multipliers: Mapping[str, float] | None = None) -> pd.DataFrame:
    """Aktif OD × gün × 09/17 tam grid için tahmin üretir.

    ``demand`` yalnız tahmin cutoff'undan, yani ``start`` tarihinden, önceki
    gözlemleri içermelidir. Bu frozen-history sözleşmesi ufuk actual'larının
    modele sızmasını önler. Tahmin DOW medyan tabanı ile günün takvim rolü
    çarpanının çarpımıdır.
    """
    start_ts = _as_timestamp(start, "start")
    end_ts = _as_timestamp(end, "end")
    if end_ts < start_ts:
        raise ValueError("end, start tarihinden önce olamaz")
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k pozitif bir tam sayı olmalı")
    if demand.empty:
        raise ValueError("demand boş olamaz")

    history = _normalise_demand(demand)
    if (history["tarih"] >= start_ts).any():
        raise ValueError("demand yalnız start/cutoff öncesi gözlemleri içermeli")

    active_ods = _normalise_ods(history, ods)
    if active_ods.empty:
        raise ValueError("En az bir aktif OD çifti gerekli")

    targets = build_grid(
        history, start_ts.date(), end_ts.date(), ods=active_ods)
    targets = targets.sort_values(_SORT_COLS, kind="mergesort").reset_index(drop=True)
    base = _safe_nonnegative(dow_median(history, targets, k=k))
    role_by_row = targets["tarih"].map(_calendar_role)
    role_multipliers = (calendar_multipliers(history)
                        if multipliers is None else dict(multipliers))
    factors = pd.to_numeric(
        role_by_row.map(lambda role: role_multipliers.get(role, 1.0)),
        errors="coerce")

    out = targets[_SORT_COLS].copy()
    out["calendar_role"] = role_by_row
    out["forecast"] = _safe_nonnegative(base * factors)
    return out


def assign_talep_ids(forecast: pd.DataFrame) -> pd.DataFrame:
    """Satırları kararlı biçimde sıralayıp ``D00001...`` kimliklerini atar."""
    if len(forecast) > MAX_TALEP_ID:
        raise ValueError(
            f"Talep ID kapasitesi aşıldı: en fazla {MAX_TALEP_ID} satır desteklenir, "
            f"{len(forecast)} satır verildi")
    missing = set(_SORT_COLS) - set(forecast.columns)
    if missing:
        raise ValueError(f"forecast sıralama kolonları eksik: {sorted(missing)}")

    out = forecast.copy()
    out["tarih"] = pd.to_datetime(out["tarih"], errors="raise").dt.normalize()
    out = out.sort_values(_SORT_COLS, kind="mergesort").reset_index(drop=True)
    out["talep_id"] = [f"D{i:05d}" for i in range(1, len(out) + 1)]
    return out


def to_forecast_frame(forecast: pd.DataFrame) -> pd.DataFrame:
    """İç tahmin gridini yarışmanın ``FORECAST_COLS`` şablonuna dönüştürür."""
    value_col = "forecast" if "forecast" in forecast.columns else "desi"
    if value_col not in forecast.columns:
        raise ValueError("forecast veya desi değer kolonu gerekli")

    internal = assign_talep_ids(forecast)
    rounded = _safe_nonnegative(internal[value_col]).round().astype("int64")
    out = pd.DataFrame({
        "Talep ID": internal["talep_id"],
        "Tarih": internal["tarih"].dt.strftime("%d.%m.%Y"),
        "Talep Tamamlama Saati": internal["slot"].astype(str),
        "Çıkış Transfer Merkezi": internal["cikis"],
        "Varış Transfer Merkezi": internal["varis"],
        "Tahmin Edilen Desi": rounded,
    })
    return out[FORECAST_COLS]
