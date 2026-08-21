"""Sabit cutoff ile sızıntısız talep tahmini değerlendirmesi."""
from __future__ import annotations

from datetime import date
from typing import Callable, TypedDict

import numpy as np
import pandas as pd

from .backtest import bias, build_grid, wmape


class FrozenResult(TypedDict):
    """Frozen backtest metrikleri ve hücre bazlı değerlendirme tablosu."""

    wmape: float
    bias: float
    n_cells: int
    evaluation: pd.DataFrame


def _as_day(value: date, label: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} geçerli bir tarih olmalı: {value!r}") from exc
    if not isinstance(timestamp, pd.Timestamp):
        raise ValueError(f"{label} geçerli bir tarih olmalı: {value!r}")
    return timestamp.normalize()


def _validate_ods(ods: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(ods, pd.DataFrame):
        raise ValueError("ods, cikis ve varis kolonlarını içeren bir DataFrame olmalı")
    missing = {"cikis", "varis"} - set(ods.columns)
    if missing:
        raise ValueError(f"ods kolonları eksik: {sorted(missing)}")
    universe = ods[["cikis", "varis"]].drop_duplicates().reset_index(drop=True)
    if universe.empty:
        raise ValueError("OD evreni boş olamaz")
    return universe


def _validate_forecast(forecast, target_index: pd.Index) -> pd.Series:
    if isinstance(forecast, pd.DataFrame):
        raise ValueError("Tahmin çıktısı tek boyutlu olmalı; DataFrame döndürülemez")

    if isinstance(forecast, pd.Series):
        values = forecast.copy()
    else:
        try:
            values = pd.Series(forecast)
        except (TypeError, ValueError) as exc:
            raise ValueError("Tahmin çıktısı tek boyutlu bir dizi olmalı") from exc

    expected_length = len(target_index)
    if len(values) != expected_length:
        raise ValueError(
            f"Tahmin uzunluğu hedef gridiyle eşleşmiyor: "
            f"beklenen {expected_length}, gelen {len(values)}")
    if isinstance(forecast, pd.Series) and not values.index.equals(target_index):
        raise ValueError("Tahmin indeksi hedef metadata indeksiyle aynı ve aynı sırada olmalı")
    if (pd.api.types.is_bool_dtype(values.dtype)
            or pd.api.types.is_complex_dtype(values.dtype)
            or not pd.api.types.is_numeric_dtype(values.dtype)):
        raise ValueError("Tahmin değerleri sayısal olmalı")

    numeric = values.astype(float)
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Tahmin değerleri sonlu olmalı; NaN veya sonsuz değer içeremez")
    if (numeric < 0).any():
        raise ValueError("Tahmin değerleri nonnegative olmalı; negatif değer içeremez")
    numeric.index = target_index
    return numeric


def run_frozen(
        demand: pd.DataFrame,
        model_fn: Callable[[pd.DataFrame, pd.DataFrame], object],
        cutoff: date,
        horizon_start: date,
        horizon_end: date,
        ods: pd.DataFrame | None = None) -> FrozenResult:
    """Modeli tek bir cutoff'ta eğitip sabit ufukta değerlendirir.

    Eğitim verisi yalnız ``tarih <= cutoff`` satırlarından oluşur. ``ods``
    verilmezse OD evreni de yalnız bu eğitim geçmişinden türetilir. Model,
    actual ``desi`` etiketi bulunmayan hedef metadata'sıyla çağrılır.
    """
    if not isinstance(demand, pd.DataFrame):
        raise ValueError("demand bir DataFrame olmalı")
    required = {"tarih", "cikis", "varis", "slot", "toplam_desi"}
    missing = required - set(demand.columns)
    if missing:
        raise ValueError(f"demand kolonları eksik: {sorted(missing)}")
    if not callable(model_fn):
        raise ValueError("model_fn çağrılabilir olmalı")

    cutoff_day = _as_day(cutoff, "cutoff")
    start_day = _as_day(horizon_start, "horizon_start")
    end_day = _as_day(horizon_end, "horizon_end")
    if cutoff_day >= start_day:
        raise ValueError("cutoff, horizon_start tarihinden önce olmalı")
    if start_day > end_day:
        raise ValueError("horizon_start, horizon_end tarihinden sonra olamaz")

    data = demand.copy()
    try:
        data["tarih"] = pd.to_datetime(data["tarih"], errors="raise").dt.normalize()
    except (TypeError, ValueError) as exc:
        raise ValueError("demand.tarih geçerli tarih değerleri içermeli") from exc
    if data["tarih"].isna().any():
        raise ValueError("demand.tarih geçerli tarih değerleri içermeli")

    train = data.loc[data["tarih"] <= cutoff_day].copy()
    if train.empty:
        raise ValueError("cutoff tarihinde veya öncesinde eğitim verisi bulunamadı")

    od_universe = _validate_ods(
        train[["cikis", "varis"]] if ods is None else ods)
    horizon = data.loc[data["tarih"].between(start_day, end_day)].copy()
    actual_grid = build_grid(
        horizon, start_day.date(), end_day.date(), ods=od_universe)
    target_metadata = actual_grid.drop(columns=["desi"]).copy()

    raw_forecast = model_fn(train.copy(), target_metadata.copy())
    forecast = _validate_forecast(raw_forecast, target_metadata.index)

    actual = actual_grid["desi"].astype(float)
    if actual.sum() <= 0:
        raise ValueError("WMAPE ve bias için değerlendirme actual toplamı pozitif olmalı")

    evaluation = target_metadata.copy()
    evaluation["actual"] = actual.to_numpy()
    evaluation["forecast"] = forecast.to_numpy()
    evaluation["error"] = evaluation["forecast"] - evaluation["actual"]
    evaluation["absolute_error"] = evaluation["error"].abs()

    return FrozenResult(
        wmape=wmape(actual, forecast),
        bias=bias(actual, forecast),
        n_cells=len(evaluation),
        evaluation=evaluation,
    )
