"""Shared scheduling, referee, fingerprint, metric, and acceptance boundary."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

import pandas as pd

from src.chain import physical_routes
from src.export import require_plan_total
from src.optimize import PlannedLeg
from src.schedule import to_plan_frame
from src.schemas import (FORECAST_COLS, PLAN_COLS, PLAN_NUMERIC_COLS,
                         _canonical_forecast_time, validate_plan)
from src.simulator import SimResult, simulate


@dataclass
class PlanEvaluation:
    legs: list[PlannedLeg]
    plan_frame: pd.DataFrame
    result: SimResult
    notes: tuple[str, ...]


@dataclass(frozen=True)
class PlanMetrics:
    vehicle_cost: Decimal
    sla_penalty: Decimal
    total_cost: Decimal
    rented_legs: int
    spot_legs: int
    vehicle_mix: tuple[tuple[str, int], ...]
    average_spot_fill: Fraction
    spot_below_30_percent: int
    violations: int


def _finite_decimal(value, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, OverflowError, TypeError, ValueError) as error:
        raise ValueError(f"{label} sonlu bir sayı olmalı") from error
    if not number.is_finite():
        raise ValueError(f"{label} sonlu bir sayı olmalı")
    return number


def _excel_numeric_decimal(value, label: str) -> Decimal:
    number = _finite_decimal(value, label)
    return _finite_decimal(format(float(number), ".16G"), label)


def forecast_fingerprint(df: pd.DataFrame) -> tuple:
    """Return an order-independent, value-exact forecast fingerprint."""
    if list(df.columns) != FORECAST_COLS:
        raise ValueError(
            f"Forecast kolonları birebir {FORECAST_COLS} olmalı")

    rows = []
    for index, row in df.iterrows():
        slot = _canonical_forecast_time(row["Talep Tamamlama Saati"])
        if slot is None:
            raise ValueError(
                f"satır {index}: geçersiz forecast saati: "
                f"{row['Talep Tamamlama Saati']!r}")
        desi = _finite_decimal(
            row["Tahmin Edilen Desi"], f"satır {index} forecast desi")
        rows.append((
            str(row["Talep ID"]),
            str(row["Tarih"]),
            slot,
            str(row["Çıkış Transfer Merkezi"]),
            str(row["Varış Transfer Merkezi"]),
            desi,
        ))
    return tuple(FORECAST_COLS), tuple(sorted(rows))


def plan_fingerprint(df: pd.DataFrame) -> tuple:
    """Return an order-independent, value-exact plan fingerprint."""
    if list(df.columns) != PLAN_COLS:
        raise ValueError(f"Plan kolonları birebir {PLAN_COLS} olmalı")

    numeric_columns = set(PLAN_NUMERIC_COLS)
    rows = []
    for index, row in df.iterrows():
        values = []
        for column in PLAN_COLS:
            value = row[column]
            if column in numeric_columns:
                value = _excel_numeric_decimal(
                    value, f"satır {index} {column}")
            elif (column == "Talep ID"
                  and (pd.isna(value) or not str(value).strip())):
                value = ""
            else:
                value = str(value)
            values.append(value)
        rows.append(tuple(values))
    return tuple(PLAN_COLS), tuple(sorted(rows))


def evaluate_legs(legs: list[PlannedLeg], forecast_df: pd.DataFrame, data,
                  *, fix: bool = True) -> PlanEvaluation:
    """Schedule and referee a privately owned copy of planned legs."""
    scheduled = deepcopy(legs)
    plan_frame, notes = to_plan_frame(scheduled, data, fix=fix)
    errors = validate_plan(plan_frame, data)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Plan doğrulaması başarısız:\n{details}")
    result = simulate(plan_frame, forecast_df, data)
    require_plan_total(plan_frame, result.total_cost)
    return PlanEvaluation(scheduled, plan_frame, result, tuple(notes))


def verify_plan_artifact(
        plan_path: str | Path,
        forecast_path: str | Path,
        data,
        *,
        expected_total: Decimal,
        expected_forecast_fingerprint: tuple,
        expected_plan_fingerprint: tuple,
        tolerance: Decimal = Decimal("0.01")) -> SimResult:
    """Reload and independently referee a staged plan/forecast pair."""
    allowed_difference = _finite_decimal(tolerance, "Artifact tolerance")
    if allowed_difference < 0:
        raise ValueError("Artifact tolerance negatif olamaz")
    expected = _finite_decimal(expected_total, "Beklenen artifact toplamı")

    reloaded_plan = pd.read_excel(Path(plan_path))
    reloaded_forecast = pd.read_excel(Path(forecast_path))
    if forecast_fingerprint(reloaded_forecast) != expected_forecast_fingerprint:
        raise ValueError("Forecast fingerprint eşleşmiyor")
    if plan_fingerprint(reloaded_plan) != expected_plan_fingerprint:
        raise ValueError("Plan fingerprint eşleşmiyor")

    errors = validate_plan(reloaded_plan, data)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Artifact plan doğrulaması başarısız:\n{details}")

    result = simulate(reloaded_plan, reloaded_forecast, data)
    if result.violations:
        details = "\n".join(f"- {violation}" for violation in result.violations)
        raise ValueError(f"Artifact hakem ihlalleri:\n{details}")

    artifact_total = _finite_decimal(
        result.total_cost, "Artifact hakem toplamı")
    if abs(artifact_total - expected) > allowed_difference:
        raise ValueError(
            "Artifact total eşleşmiyor: "
            f"beklenen {expected} TL, hakem {artifact_total} TL"
        )
    require_plan_total(
        reloaded_plan, result.total_cost, tolerance=allowed_difference)
    return result


def summarize_evaluation(evaluation: PlanEvaluation, data) -> PlanMetrics:
    """Summarize exact referee costs and unweighted physical-route fill."""
    vehicle_cost = _finite_decimal(
        evaluation.result.vehicle_cost, "Araç maliyeti")
    sla_penalty = _finite_decimal(
        evaluation.result.sla_penalty, "SLA cezası")
    total_cost = _finite_decimal(
        evaluation.result.total_cost, "Toplam maliyet")

    routes = physical_routes(evaluation.legs)
    rented_legs = sum(route[0].kind == "Kiralık" for route in routes)
    spot_legs = sum(route[0].kind == "Spot" for route in routes)
    vehicle_mix = tuple(sorted(Counter(
        route[0].vtype for route in routes).items()))
    spot_fills = [
        Fraction(Decimal(str(route[0].desi)))
        / data.vehicles[route[0].vtype].capacity_desi
        for route in routes
        if route[0].kind == "Spot"
    ]
    average_spot_fill = (
        sum(spot_fills, Fraction(0, 1)) / len(spot_fills)
        if spot_fills else Fraction(0, 1)
    )

    return PlanMetrics(
        vehicle_cost=vehicle_cost,
        sla_penalty=sla_penalty,
        total_cost=total_cost,
        rented_legs=rented_legs,
        spot_legs=spot_legs,
        vehicle_mix=vehicle_mix,
        average_spot_fill=average_spot_fill,
        spot_below_30_percent=sum(
            fill < Fraction(3, 10) for fill in spot_fills),
        violations=len(evaluation.result.violations),
    )


def improvement_tl(baseline: PlanEvaluation,
                   candidate: PlanEvaluation) -> Decimal:
    baseline_total = _finite_decimal(
        baseline.result.total_cost, "Baseline toplam maliyeti")
    candidate_total = _finite_decimal(
        candidate.result.total_cost, "Aday toplam maliyeti")
    return baseline_total - candidate_total


def accepts_candidate(
        baseline: PlanEvaluation,
        candidate: PlanEvaluation,
        minimum_saving: Decimal = Decimal("1.00")) -> bool:
    minimum = _finite_decimal(minimum_saving, "Minimum tasarruf")
    if minimum < 0:
        raise ValueError("Minimum tasarruf negatif olamaz")
    return (
        not baseline.result.violations
        and not candidate.result.violations
        and improvement_tl(baseline, candidate) >= minimum
    )
