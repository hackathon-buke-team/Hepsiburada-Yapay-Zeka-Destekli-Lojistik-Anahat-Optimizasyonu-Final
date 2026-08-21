"""Uçtan uca çözüm hattı: veri → tahmin → optimize → çizelge → simüle → dışa aktar.

Çalıştırma:  python run.py
Çıktılar:    out/Talep-tahmini.xlsx , out/Tasima-plani.xlsx
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.chain import physical_routes
from src.data import load_all
from src.evaluation import (PlanEvaluation, forecast_fingerprint,
                            improvement_tl, plan_fingerprint,
                            summarize_evaluation, verify_plan_artifact)
from src.export import (publish_workbooks, write_forecast_xlsx,
                        write_plan_xlsx)
from src.forecast import forecast_horizon, to_forecast_frame
from src.milkrun import (MAX_CHAIN_STOPS, MilkRunDecision,
                         run_milk_run_stage)
from src.optimize import build_plan, prepare_frame
from src.pickup import PickupDecision, run_pickup_stage
from src.repair import Stage1Decision, run_same_lane_stage

HORIZON_START = date(2026, 6, 29)
HORIZON_END = date(2026, 7, 5)
OUT_DIR = Path("out")

STAGE0_FORECAST_ROWS = 4046
STAGE0_FORECAST_DESI = Decimal("4977975")
STAGE0_FORECAST_IDS = frozenset(f"D{number:05d}" for number in range(1, 4047))
STAGE0_LEGS = 1269
STAGE0_RENTED_LEGS = 126
STAGE0_SPOT_LEGS = 1143
STAGE0_PLAN_ROWS = 3167
STAGE0_VEHICLE_COST = Decimal("15460592.57")
STAGE0_SLA_PENALTY = Decimal("1020367.20")
STAGE0_TOTAL_COST = Decimal("16480959.77")
STAGE0_COST_TOLERANCE = Decimal("0.01")

STAGE1_SEGMENTS = 1092
STAGE1_PHYSICAL_ROUTES = 1092
STAGE1_RENTED_ROUTES = 126
STAGE1_SPOT_ROUTES = 966
STAGE1_PLAN_ROWS = 3167
STAGE1_VEHICLE_COST = Decimal("12510401.245833337")
STAGE1_SLA_PENALTY = Decimal("2169783.600000002")
STAGE1_TOTAL_COST = Decimal("14680184.845833339")
STAGE1_GLOBAL_SAVING = Decimal("1800774.926388895")
STAGE1_DONORS_CONSIDERED = 1003
STAGE1_MOVES_ACCEPTED = 177
STAGE1_PARTS_MOVED = 394
STAGE1_DESI_MOVED = 59852
STAGE1_SPOT_REMOVED = 177
STAGE1_LOCAL_SAVING = Decimal("1800774.926388888876856333333")

# Stage 2 is the stage that produces the submitted workbook, so it is pinned to
# its accepted result exactly like Stage 0 and Stage 1. A search change that
# silently loses the milk-run gain must fail loudly here, not publish quietly.
STAGE2_SEGMENTS = 1092
STAGE2_PHYSICAL_ROUTES = 693
STAGE2_RENTED_ROUTES = 126
STAGE2_SPOT_ROUTES = 567
STAGE2_PLAN_ROWS = 5510
STAGE2_VEHICLE_COST = Decimal("8752512.286111115")
STAGE2_SLA_PENALTY = Decimal("2560825.9999999986")
STAGE2_TOTAL_COST = Decimal("11313338.286111113")
STAGE2_GLOBAL_SAVING = Decimal("3366846.559722226")
STAGE2_GROUPS_CONSIDERED = 93
STAGE2_PAIRS_EVALUATED = 5426
STAGE2_TRIPLES_EVALUATED = 96369
STAGE2_CHAINS_ACCEPTED = 227
STAGE2_CHAIN_SIZE_MIX = ((2, 127), (3, 28), (4, 72))
STAGE2_SOURCE_VEHICLES_REPLACED = 626
STAGE2_SEGMENTS_CREATED = 626
STAGE2_PARTS_CONSOLIDATED = 2110
STAGE2_DESI_CONSOLIDATED = 1675453
STAGE2_CHAIN_TYPE_MIX = (
    ("Hafif Kamyon", 11), ("Kamyon", 120), ("Kamyonet", 96))
STAGE2_LOCAL_SAVING = Decimal("3366846.559722222193718999999")

# Stage 3 (mid-route pickup) now produces the submitted workbook, so it is
# pinned exactly like the stages before it. Stage 2 stays pinned to its own
# accepted result: Stage 3 is a separate module and a separate stage
# precisely so that the milk-run search result cannot drift underneath it.
STAGE3_SEGMENTS = 1064
STAGE3_PHYSICAL_ROUTES = 665
STAGE3_RENTED_ROUTES = 126
STAGE3_SPOT_ROUTES = 539
STAGE3_CHAIN_ROUTES = 227
STAGE3_PLAN_ROWS = 5523
STAGE3_VEHICLE_COST = Decimal("8616944.731944447")
STAGE3_SLA_PENALTY = Decimal("2615531.9999999995")
STAGE3_TOTAL_COST = Decimal("11232476.731944447")
STAGE3_GLOBAL_SAVING = Decimal("80861.554166666")
STAGE3_ROUTES_CONSIDERED = 227
STAGE3_RENTED_ROUTES_SKIPPED = 126
STAGE3_DONORS_AVAILABLE = 340
STAGE3_PAIRS_EXAMINED = 135660
STAGE3_PROFITABLE_CANDIDATES = 56
STAGE3_PICKUPS_ACCEPTED = 28
STAGE3_REJECTED_BY_LEDGER = 0
STAGE3_DONOR_VEHICLES_REMOVED = 28
STAGE3_PARTS_PICKED_UP = 82
STAGE3_DESI_PICKED_UP = 65754
STAGE3_LOCAL_SAVING = Decimal("80861.55416666666605766666666")
STAGE3_PICKUP_TYPE_MIX = (("Kamyon", 11), ("Kamyonet", 17))
# A meaningful floor, not a token one: 1,00 TL would still pass if the search
# collapsed to a single accidental pickup, and that must fail loudly here.
STAGE3_MIN_SAVING_TL = Decimal("50000.00")
# The search's own arithmetic and the referee's measured difference are two
# independent computations of the same number; they must agree to the cent's
# millionth. Every mid-route pickup defect found so far broke this first.
STAGE3_SAVING_TOLERANCE = Decimal("0.000001")


def _require_stage0_entry(forecast_frame: pd.DataFrame,
                          evaluation: PlanEvaluation, data) -> None:
    """Reject a run unless it reproduces the approved fixed Stage 0 entry."""
    mismatches = []

    def check_equal(label, getter, expected) -> None:
        try:
            actual = getter()
        except Exception as error:
            mismatches.append(f"{label} hesaplanamadı: {error}")
        else:
            if actual != expected:
                mismatches.append(f"{label} {actual} != {expected}")

    check_equal(
        "forecast satırı", lambda: len(forecast_frame),
        STAGE0_FORECAST_ROWS)

    try:
        forecast_desi = sum(
            (Decimal(str(value))
             for value in forecast_frame["Tahmin Edilen Desi"]),
            Decimal("0"),
        )
    except Exception as error:
        mismatches.append(f"forecast desi hesaplanamadı: {error}")
    else:
        if (not forecast_desi.is_finite()
                or forecast_desi != STAGE0_FORECAST_DESI):
            mismatches.append(
                f"forecast desi {forecast_desi} != {STAGE0_FORECAST_DESI}")

    try:
        forecast_ids = set(forecast_frame["Talep ID"].astype(str))
    except Exception as error:
        mismatches.append(f"forecast ID seti hesaplanamadı: {error}")
    else:
        if forecast_ids != STAGE0_FORECAST_IDS:
            missing = len(STAGE0_FORECAST_IDS - forecast_ids)
            extra = len(forecast_ids - STAGE0_FORECAST_IDS)
            mismatches.append(
                f"forecast ID seti eşleşmiyor (eksik {missing}, fazla {extra})")

    checks = (
        ("bacak", lambda: len(evaluation.legs), STAGE0_LEGS),
        ("kiralık bacak", lambda: sum(
            leg.kind == "Kiralık" for leg in evaluation.legs),
         STAGE0_RENTED_LEGS),
        ("Spot bacak", lambda: sum(
            leg.kind == "Spot" for leg in evaluation.legs),
         STAGE0_SPOT_LEGS),
        ("plan satırı", lambda: len(evaluation.plan_frame),
         STAGE0_PLAN_ROWS),
        ("ihlal", lambda: len(evaluation.result.violations), 0),
    )
    for label, getter, expected in checks:
        check_equal(label, getter, expected)

    cost_checks = (
        ("araç maliyeti", lambda: evaluation.result.vehicle_cost,
         STAGE0_VEHICLE_COST),
        ("SLA cezası", lambda: evaluation.result.sla_penalty,
         STAGE0_SLA_PENALTY),
        ("toplam maliyet", lambda: evaluation.result.total_cost,
         STAGE0_TOTAL_COST),
    )
    for label, getter, expected in cost_checks:
        try:
            actual = Decimal(str(getter()))
            if not actual.is_finite():
                raise ValueError("sonlu bir sayı olmalı")
            difference = abs(actual - expected)
        except Exception as error:
            mismatches.append(f"{label} hesaplanamadı: {error}")
        else:
            if difference <= STAGE0_COST_TOLERANCE:
                continue
            mismatches.append(f"{label} {actual} != {expected} ±0.01")

    if mismatches:
        details = "\n".join(f"- {mismatch}" for mismatch in mismatches)
        raise RuntimeError(f"Stage 0 giriş kapısı başarısız:\n{details}")


def _use_utf8_console() -> None:
    """Keep Turkish gate output printable when stdout is a cp1252 pipe."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def _exact_decimal(label: str, value, errors: list) -> Decimal | None:
    """Return an exact finite Decimal or record a mismatch and return None."""
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("sonlu bir sayı olmalı")
    except Exception as error:
        errors.append(f"{label} hesaplanamadı: {error}")
        return None
    return number


def _require_stage1_entry(stage1_decision: Stage1Decision, data) -> None:
    """Reject unless Stage 1 reproduces exact accepted report constants."""
    errors = []
    evaluation = stage1_decision.selected

    def check(label, actual, expected):
        if actual != expected:
            errors.append(f"{label} {actual} != {expected}")

    segments = len(evaluation.legs)
    routes = physical_routes(evaluation.legs)
    check("segments", segments, STAGE1_SEGMENTS)
    check("physical_routes", len(routes), STAGE1_PHYSICAL_ROUTES)

    if len(routes) != segments or any(len(route) > 1 for route in routes):
        errors.append(
            f"zincirli fiziksel rota var: {segments} bacak, "
            f"{len(routes)} rota (Stage 1 yalnızca direkt olmalı)")
    if any(getattr(leg, "chain_id", None) is not None
           for leg in evaluation.legs):
        errors.append("zincir kimliği (chain_id) dolu bacak var")

    rented = sum(1 for r in routes if r[0].kind == "Kiralık")
    spot = sum(1 for r in routes if r[0].kind == "Spot")
    check("rented_routes", rented, STAGE1_RENTED_ROUTES)
    check("spot_routes", spot, STAGE1_SPOT_ROUTES)
    check("plan_rows", len(evaluation.plan_frame), STAGE1_PLAN_ROWS)

    if evaluation.result.violations:
        errors.append(
            f"Stage 1 ihlal {len(evaluation.result.violations)} != 0")
    if stage1_decision.baseline.result.violations:
        errors.append(
            "Stage 0 baseline ihlal "
            f"{len(stage1_decision.baseline.result.violations)} != 0")

    vc = _exact_decimal("vehicle_cost", evaluation.result.vehicle_cost, errors)
    sp = _exact_decimal("sla_penalty", evaluation.result.sla_penalty, errors)
    tc = _exact_decimal("total_cost", evaluation.result.total_cost, errors)
    baseline_tc = _exact_decimal(
        "stage0_total_cost", stage1_decision.baseline.result.total_cost,
        errors)
    reported = _exact_decimal(
        "global_saving_reported", stage1_decision.saving_tl, errors)
    if vc is not None:
        check("vehicle_cost", vc, STAGE1_VEHICLE_COST)
    if sp is not None:
        check("sla_penalty", sp, STAGE1_SLA_PENALTY)
    if tc is not None:
        check("total_cost", tc, STAGE1_TOTAL_COST)
    if tc is not None and baseline_tc is not None:
        check("global_saving", baseline_tc - tc, STAGE1_GLOBAL_SAVING)
    if reported is not None:
        check("global_saving_reported", reported, STAGE1_GLOBAL_SAVING)

    rm = stage1_decision.repair_metrics
    check("donors_considered", rm.donors_considered, STAGE1_DONORS_CONSIDERED)
    check("moves_accepted", rm.moves_accepted, STAGE1_MOVES_ACCEPTED)
    check("parts_moved", rm.parts_moved, STAGE1_PARTS_MOVED)
    check("desi_moved", rm.desi_moved, STAGE1_DESI_MOVED)
    check("spot_legs_removed", rm.spot_legs_removed, STAGE1_SPOT_REMOVED)
    check("local_saving_tl", rm.local_saving_tl, STAGE1_LOCAL_SAVING)

    if not stage1_decision.accepted:
        errors.append("kabul değil")
    if stage1_decision.selected is not stage1_decision.candidate:
        errors.append("seçilen aday değil")

    if errors:
        details = "\n".join(f"- {e}" for e in errors)
        raise RuntimeError(f"Stage 1 entry rejected:\n{details}")


def _require_stage2_entry(stage1_decision: Stage1Decision,
                          stage2_decision: MilkRunDecision) -> None:
    """Reject unless Stage 2 entry requirements are met."""
    errors = []

    if stage2_decision.baseline is not stage1_decision.selected:
        errors.append("baseline identity mismatch: not stage1.selected")

    if not stage2_decision.accepted:
        errors.append("Stage 2 kabul değil")

    if stage2_decision.selected is not stage2_decision.candidate:
        errors.append("Stage 2 seçimi aday değil")

    if stage2_decision.selected.result.violations:
        errors.append("candidate has violations")
    if stage2_decision.baseline.result.violations:
        errors.append("baseline has violations")

    reported = _exact_decimal(
        "Stage 2 tasarruf", stage2_decision.saving_tl, errors)
    try:
        recomputed = improvement_tl(
            stage2_decision.baseline, stage2_decision.candidate)
    except Exception as error:
        errors.append(f"Stage 2 tasarruf yeniden hesaplanamadı: {error}")
    else:
        if reported is not None and reported != recomputed:
            errors.append(
                f"Stage 2 tasarruf {reported} != hakem farkı {recomputed}")

    if reported is not None and reported < Decimal("1.00"):
        errors.append(f"Stage 2 tasarruf {reported} < 1.00")

    if errors:
        details = "\n".join(f"- {e}" for e in errors)
        raise RuntimeError(f"Stage 2 entry rejected:\n{details}")


def _require_stage2_result(stage1_decision: Stage1Decision,
                           stage2_decision: MilkRunDecision, data) -> None:
    """Reject unless Stage 2 reproduces the exact accepted milk-run result."""
    errors = []
    evaluation = stage2_decision.selected
    metrics = stage2_decision.metrics

    def check(label, actual, expected):
        if actual != expected:
            errors.append(f"{label} {actual} != {expected}")

    segments = len(evaluation.legs)
    routes = physical_routes(evaluation.legs)
    chains = [route for route in routes if len(route) > 1]
    check("stage2_segments", segments, STAGE2_SEGMENTS)
    check("stage2_physical_routes", len(routes), STAGE2_PHYSICAL_ROUTES)
    check("stage2_plan_rows", len(evaluation.plan_frame), STAGE2_PLAN_ROWS)
    check("stage2_rented_routes",
          sum(1 for route in routes if route[0].kind == "Kiralık"),
          STAGE2_RENTED_ROUTES)
    check("stage2_spot_routes",
          sum(1 for route in routes if route[0].kind == "Spot"),
          STAGE2_SPOT_ROUTES)
    check("stage2_chain_routes", len(chains), STAGE2_CHAINS_ACCEPTED)

    # Every chain must stay a Spot, non-Tır, single-vehicle-type route whose
    # length the jury permits; MAX_CHAIN_STOPS bounds it, this pins the shape.
    for route in chains:
        if not 2 <= len(route) <= MAX_CHAIN_STOPS:
            errors.append(f"zincir uzunluğu {len(route)} sınır dışı")
        if route[0].kind != "Spot" or route[0].vtype == "Tır":
            errors.append(
                f"zincir {route[0].kind}/{route[0].vtype} olamaz "
                "(Q&A 11.1: uğrama yalnızca Spot)")
        if len({leg.vtype for leg in route}) != 1:
            errors.append("zincir içinde araç türü değişiyor")

    vehicle_cost = _exact_decimal(
        "stage2_vehicle_cost", evaluation.result.vehicle_cost, errors)
    sla_penalty = _exact_decimal(
        "stage2_sla_penalty", evaluation.result.sla_penalty, errors)
    total_cost = _exact_decimal(
        "stage2_total_cost", evaluation.result.total_cost, errors)
    stage1_total = _exact_decimal(
        "stage1_total_cost", stage1_decision.selected.result.total_cost,
        errors)
    if vehicle_cost is not None:
        check("stage2_vehicle_cost", vehicle_cost, STAGE2_VEHICLE_COST)
    if sla_penalty is not None:
        check("stage2_sla_penalty", sla_penalty, STAGE2_SLA_PENALTY)
    if total_cost is not None:
        check("stage2_total_cost", total_cost, STAGE2_TOTAL_COST)
    if total_cost is not None and stage1_total is not None:
        check("stage2_global_saving", stage1_total - total_cost,
              STAGE2_GLOBAL_SAVING)

    check("groups_considered", metrics.groups_considered,
          STAGE2_GROUPS_CONSIDERED)
    check("pairs_evaluated", metrics.pairs_evaluated, STAGE2_PAIRS_EVALUATED)
    check("triples_evaluated", metrics.triples_evaluated,
          STAGE2_TRIPLES_EVALUATED)
    check("chains_accepted", metrics.chains_accepted, STAGE2_CHAINS_ACCEPTED)
    check("chain_size_mix", tuple(metrics.chain_size_mix),
          STAGE2_CHAIN_SIZE_MIX)
    check("source_vehicles_replaced", metrics.source_vehicles_replaced,
          STAGE2_SOURCE_VEHICLES_REPLACED)
    check("segments_created", metrics.segments_created,
          STAGE2_SEGMENTS_CREATED)
    check("parts_consolidated", metrics.parts_consolidated,
          STAGE2_PARTS_CONSOLIDATED)
    check("desi_consolidated", metrics.desi_consolidated,
          STAGE2_DESI_CONSOLIDATED)
    check("chain_type_mix", tuple(metrics.chain_type_mix),
          STAGE2_CHAIN_TYPE_MIX)
    check("stage2_local_saving", metrics.local_saving_tl, STAGE2_LOCAL_SAVING)

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Stage 2 sonucu reddedildi:\n{details}")


def _require_stage3_entry(stage2_decision: MilkRunDecision,
                          stage3_decision: PickupDecision) -> None:
    """Reject unless Stage 3 entry requirements are met."""
    errors = []

    if stage3_decision.baseline is not stage2_decision.selected:
        errors.append("baseline identity mismatch: not stage2.selected")

    if not stage3_decision.accepted:
        errors.append("Stage 3 kabul değil")

    if stage3_decision.selected is not stage3_decision.candidate:
        errors.append("Stage 3 seçimi aday değil")

    if stage3_decision.selected.result.violations:
        errors.append("candidate has violations")
    if stage3_decision.baseline.result.violations:
        errors.append("baseline has violations")

    reported = _exact_decimal(
        "Stage 3 tasarruf", stage3_decision.saving_tl, errors)
    try:
        recomputed = improvement_tl(
            stage3_decision.baseline, stage3_decision.candidate)
    except Exception as error:
        errors.append(f"Stage 3 tasarruf yeniden hesaplanamadı: {error}")
    else:
        if reported is not None and reported != recomputed:
            errors.append(
                f"Stage 3 tasarruf {reported} != hakem farkı {recomputed}")

    if reported is not None and reported < STAGE3_MIN_SAVING_TL:
        errors.append(
            f"Stage 3 tasarruf {reported} < {STAGE3_MIN_SAVING_TL}")

    # The reconciliation gate: what the search claims it saved and what the
    # referee measures must be the same number.
    local = _exact_decimal(
        "Stage 3 yerel tasarruf",
        stage3_decision.metrics.local_saving_tl, errors)
    if (reported is not None and local is not None
            and abs(local - reported) > STAGE3_SAVING_TOLERANCE):
        errors.append(
            f"Stage 3 yerel tasarruf {local}, hakem farkı {reported} ile "
            "uzlaşmıyor")

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Stage 3 entry rejected:\n{details}")


def _stage3_pickup_shape_errors(routes) -> list:
    """Read the pickup rules off the physical graph about to be published.

    Two properties are checked. Cargo may only be taken on mid-route by a
    Spot vehicle (Q&A: "Kiralık araçlarla uğrama yapılmaz"), and every piece
    of cargo must leave the vehicle at its own forecast destination — which
    is exactly what "the picked-up load rides only its own window" means once
    the plan is read back as a graph.

    This runs on the in-memory legs; that these are the rows that reach disk
    is proven separately by the plan fingerprint and the independent referee
    pass in ``verify_plan_artifact``.
    """
    errors = []
    mid_route_loadings = 0
    for route in routes:
        for index, leg in enumerate(route):
            previous = (
                {id(part) for part, _desi in route[index - 1].items}
                if index > 0 else set())
            following = (
                {id(part) for part, _desi in route[index + 1].items}
                if index + 1 < len(route) else set())
            if index > 0 and any(id(part) not in previous
                                 for part, _desi in leg.items):
                mid_route_loadings += 1
                if route[0].kind != "Spot":
                    errors.append(
                        f"kiralık rotada rota-ortası yükleme: "
                        f"{leg.origin}->{leg.dest}")
            for part, _desi in leg.items:
                if id(part) not in following and part.dest != leg.dest:
                    errors.append(
                        f"{part.base_id}: {leg.dest} indirme durağı ama "
                        f"nihai varışı {part.dest}")
    if mid_route_loadings != STAGE3_PICKUPS_ACCEPTED:
        errors.append(
            f"rota-ortası yükleme yapan segment {mid_route_loadings} != "
            f"{STAGE3_PICKUPS_ACCEPTED}")
    return errors


def _require_stage3_result(stage2_decision: MilkRunDecision,
                           stage3_decision: PickupDecision, data) -> None:
    """Reject unless Stage 3 reproduces the exact accepted pickup result."""
    errors = []
    evaluation = stage3_decision.selected
    metrics = stage3_decision.metrics

    def check(label, actual, expected):
        if actual != expected:
            errors.append(f"{label} {actual} != {expected}")

    routes = physical_routes(evaluation.legs)
    chains = [route for route in routes if len(route) > 1]
    check("stage3_segments", len(evaluation.legs), STAGE3_SEGMENTS)
    check("stage3_physical_routes", len(routes), STAGE3_PHYSICAL_ROUTES)
    check("stage3_plan_rows", len(evaluation.plan_frame), STAGE3_PLAN_ROWS)
    check("stage3_rented_routes",
          sum(1 for route in routes if route[0].kind == "Kiralık"),
          STAGE3_RENTED_ROUTES)
    check("stage3_spot_routes",
          sum(1 for route in routes if route[0].kind == "Spot"),
          STAGE3_SPOT_ROUTES)
    check("stage3_chain_routes", len(chains), STAGE3_CHAIN_ROUTES)

    # Tier A never changes topology. Pinned counts alone would allow one
    # route to gain a stop while another loses one, so the chain-length
    # multiset is compared against Stage 2 directly, and the drop in vehicle
    # count is required to be exactly the donors the search removed.
    stage2_routes = physical_routes(stage2_decision.selected.legs)
    stage2_shape = sorted(len(route) for route in stage2_routes if len(route) > 1)
    stage3_shape = sorted(len(route) for route in chains)
    if stage2_shape != stage3_shape:
        errors.append(
            "Tier A rota topolojisini değiştirdi: zincir uzunlukları "
            f"{Counter(stage3_shape)} != Stage 2 {Counter(stage2_shape)}")
    check("stage3_vehicles_removed", len(stage2_routes) - len(routes),
          STAGE3_DONOR_VEHICLES_REMOVED)

    for route in chains:
        if not 2 <= len(route) <= MAX_CHAIN_STOPS:
            errors.append(f"zincir uzunluğu {len(route)} sınır dışı")
        if route[0].kind != "Spot" or route[0].vtype == "Tır":
            errors.append(
                f"zincir {route[0].kind}/{route[0].vtype} olamaz "
                "(Q&A 11.1: uğrama yalnızca Spot)")
        if len({leg.vtype for leg in route}) != 1:
            errors.append("zincir içinde araç türü değişiyor")
    errors.extend(_stage3_pickup_shape_errors(routes))

    vehicle_cost = _exact_decimal(
        "stage3_vehicle_cost", evaluation.result.vehicle_cost, errors)
    sla_penalty = _exact_decimal(
        "stage3_sla_penalty", evaluation.result.sla_penalty, errors)
    total_cost = _exact_decimal(
        "stage3_total_cost", evaluation.result.total_cost, errors)
    stage2_total = _exact_decimal(
        "stage2_total_cost", stage2_decision.selected.result.total_cost,
        errors)
    if vehicle_cost is not None:
        check("stage3_vehicle_cost", vehicle_cost, STAGE3_VEHICLE_COST)
    if sla_penalty is not None:
        check("stage3_sla_penalty", sla_penalty, STAGE3_SLA_PENALTY)
    if total_cost is not None:
        check("stage3_total_cost", total_cost, STAGE3_TOTAL_COST)
    if total_cost is not None and stage2_total is not None:
        check("stage3_global_saving", stage2_total - total_cost,
              STAGE3_GLOBAL_SAVING)

    check("routes_considered", metrics.routes_considered,
          STAGE3_ROUTES_CONSIDERED)
    check("rented_routes_skipped", metrics.rented_routes_skipped,
          STAGE3_RENTED_ROUTES_SKIPPED)
    check("donors_available", metrics.donors_available,
          STAGE3_DONORS_AVAILABLE)
    check("pairs_examined", metrics.pairs_examined, STAGE3_PAIRS_EXAMINED)
    check("profitable_candidates", metrics.profitable_candidates,
          STAGE3_PROFITABLE_CANDIDATES)
    check("pickups_accepted", metrics.pickups_accepted,
          STAGE3_PICKUPS_ACCEPTED)
    check("rejected_by_ledger", metrics.rejected_by_ledger,
          STAGE3_REJECTED_BY_LEDGER)
    check("donor_vehicles_removed", metrics.donor_vehicles_removed,
          STAGE3_DONOR_VEHICLES_REMOVED)
    check("parts_picked_up", metrics.parts_picked_up, STAGE3_PARTS_PICKED_UP)
    check("desi_picked_up", metrics.desi_picked_up, STAGE3_DESI_PICKED_UP)
    check("stage3_local_saving", metrics.local_saving_tl, STAGE3_LOCAL_SAVING)
    check("pickup_type_mix", tuple(metrics.pickup_type_mix),
          STAGE3_PICKUP_TYPE_MIX)

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Stage 3 sonucu reddedildi:\n{details}")


def _print_pipeline_metrics(stage1_decision: Stage1Decision,
                            stage2_decision: MilkRunDecision,
                            stage3_decision: PickupDecision, data,
                            runtime_seconds: float) -> None:
    """Print exact Stage 0/1/2/3 physical metrics and every stage ledger."""
    for label, evaluation in (
            ("Stage 0 baseline", stage1_decision.baseline),
            ("Stage 1 selected", stage1_decision.selected),
            ("Stage 2 selected", stage2_decision.selected),
            ("Stage 3 candidate", stage3_decision.candidate)):
        metrics = summarize_evaluation(evaluation, data)
        mix = ", ".join(
            f"{vehicle}: {count}" for vehicle, count in metrics.vehicle_mix)
        fill = metrics.average_spot_fill
        routes = metrics.rented_legs + metrics.spot_legs
        print(f"[{label}]")
        print(f"    Araç maliyeti : {metrics.vehicle_cost:>14,.2f} TL")
        print(f"    SLA cezası    : {metrics.sla_penalty:>14,.2f} TL")
        print(f"    TOPLAM        : {metrics.total_cost:>14,.2f} TL")
        print(f"    Ham TOPLAM    : {metrics.total_cost} TL")
        print(f"    Segment       : {len(evaluation.legs)}")
        print(f"    Fiziksel rota : {routes} "
              f"({metrics.rented_legs} kiralık, {metrics.spot_legs} Spot)")
        print(f"    Araç karması  : {mix}")
        print(f"    Spot doluluk  : {float(fill):.2%} "
              f"({fill.numerator}/{fill.denominator})")
        print(f"    Spot <%30     : {metrics.spot_below_30_percent}")
        print(f"    İhlal         : {metrics.violations}")

    repair = stage1_decision.repair_metrics
    print("[Stage 1 same-lane repair]")
    print(f"    Donör         : {repair.donors_considered}")
    print(f"    Hamle         : {repair.moves_accepted}")
    print(f"    Parça/desi    : {repair.parts_moved}/{repair.desi_moved}")
    print(f"    Silinen Spot  : {repair.spot_legs_removed}")
    print(f"    Yerel tasarruf: {repair.local_saving_tl} TL")
    print(f"    Ham tasarruf  : {stage1_decision.saving_tl} TL")
    print(f"    Kabul         : {stage1_decision.accepted}")

    milk = stage2_decision.metrics
    chain_mix = ", ".join(
        f"{vehicle}: {count}" for vehicle, count in milk.chain_type_mix)
    size_mix = ", ".join(
        f"{size} durak: {count}" for size, count in milk.chain_size_mix)
    print(f"[Stage 2 milk-run (<= {MAX_CHAIN_STOPS} durak)]")
    print(f"    Grup          : {milk.groups_considered}")
    print(f"    Çift denemesi : {milk.pairs_evaluated}")
    print(f"    Çoklu deneme  : {milk.triples_evaluated} (k>=3)")
    print(f"    Kabul zincir  : {milk.chains_accepted}")
    print(f"    Zincir boyu   : {size_mix}")
    print(f"    Değişen araç  : {milk.source_vehicles_replaced}")
    print(f"    Yeni segment  : {milk.segments_created}")
    print(f"    Parça/desi    : {milk.parts_consolidated}/"
          f"{milk.desi_consolidated}")
    print(f"    Zincir karması: {chain_mix}")
    print(f"    Yerel tasarruf: {milk.local_saving_tl} TL")
    print(f"    Ham tasarruf  : {stage2_decision.saving_tl} TL")
    print(f"    Kabul         : {stage2_decision.accepted}")

    pickup = stage3_decision.metrics
    pickup_mix = ", ".join(
        f"{vehicle}: {count}" for vehicle, count in pickup.pickup_type_mix)
    print("[Stage 3 rota-ortası yük alma (Tier A)]")
    print(f"    Hedef rota    : {pickup.routes_considered} "
          f"({pickup.rented_routes_skipped} kiralık atlandı)")
    print(f"    Donör havuzu  : {pickup.donors_available}")
    print(f"    İncelenen çift: {pickup.pairs_examined}")
    print(f"    Kârlı aday    : {pickup.profitable_candidates}")
    print(f"    Kabul yük alma: {pickup.pickups_accepted}")
    print(f"    Defter reddi  : {pickup.rejected_by_ledger}")
    print(f"    Silinen araç  : {pickup.donor_vehicles_removed}")
    print(f"    Parça/desi    : {pickup.parts_picked_up}/"
          f"{pickup.desi_picked_up}")
    print(f"    Hedef karması : {pickup_mix}")
    print(f"    Yerel tasarruf: {pickup.local_saving_tl} TL")
    print(f"    Ham tasarruf  : {stage3_decision.saving_tl} TL")
    print(f"    Kabul         : {stage3_decision.accepted}")

    stage0_total = Decimal(str(stage1_decision.baseline.result.total_cost))
    stage3_total = Decimal(str(stage3_decision.selected.result.total_cost))
    print("[Kümülatif]")
    print(f"    Stage 0 -> 3  : {stage0_total - stage3_total} TL")
    print(f"    Süre          : {runtime_seconds:.1f} sn")


def _stage_and_publish(stage1_decision: Stage1Decision,
                       stage2_decision: MilkRunDecision,
                       stage3_decision: PickupDecision,
                       staged_forecast_path: Path,
                       expected_fingerprint: tuple,
                       data,
                       staging_dir: Path,
                       output_dir: Path) -> None:
    staging_dir = Path(staging_dir)
    output_dir = Path(output_dir)

    _require_stage1_entry(stage1_decision, data)
    if not stage2_decision.accepted:
        raise RuntimeError(
            f"Stage 2 reddedildi; tasarruf {stage2_decision.saving_tl} TL")
    _require_stage2_entry(stage1_decision, stage2_decision)
    if not stage3_decision.accepted:
        raise RuntimeError(
            f"Stage 3 reddedildi; tasarruf {stage3_decision.saving_tl} TL")
    _require_stage3_entry(stage2_decision, stage3_decision)

    # The staged baseline is whatever the published plan has to beat, so it
    # moves forward with the pipeline: Stage 3 publishes, Stage 2 is its
    # independently refereed reference point.
    baseline_path = write_plan_xlsx(
        stage2_decision.selected.plan_frame,
        staging_dir / "Stage2-baseline.xlsx",
        data,
    )
    baseline_artifact_result = verify_plan_artifact(
        baseline_path,
        staged_forecast_path,
        data,
        expected_total=Decimal(str(stage2_decision.selected.result.total_cost)),
        expected_forecast_fingerprint=expected_fingerprint,
        expected_plan_fingerprint=plan_fingerprint(
            stage2_decision.selected.plan_frame),
    )

    selected_path = write_plan_xlsx(
        stage3_decision.selected.plan_frame,
        staging_dir / "Tasima-plani.xlsx",
        data,
    )
    candidate_artifact_result = verify_plan_artifact(
        selected_path,
        staged_forecast_path,
        data,
        expected_total=Decimal(str(stage3_decision.selected.result.total_cost)),
        expected_forecast_fingerprint=expected_fingerprint,
        expected_plan_fingerprint=plan_fingerprint(
            stage3_decision.selected.plan_frame),
    )

    artifact_saving = (
        Decimal(str(baseline_artifact_result.total_cost))
        - Decimal(str(candidate_artifact_result.total_cost))
    )
    if artifact_saving < STAGE3_MIN_SAVING_TL:
        raise RuntimeError(
            f"Staged artifact tasarrufu {STAGE3_MIN_SAVING_TL} TL altında: "
            f"{artifact_saving} TL")

    publish_workbooks(
        selected_path,
        staged_forecast_path,
        output_dir / "Tasima-plani.xlsx",
        output_dir / "Talep-tahmini.xlsx",
    )


def main() -> None:
    _use_utf8_console()
    t0 = time.perf_counter()
    data = load_all()
    fc = forecast_horizon(data.demand, HORIZON_START, HORIZON_END)
    forecast_frame = to_forecast_frame(fc)
    expected_fingerprint = forecast_fingerprint(forecast_frame)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".stage2-", dir=OUT_DIR) as staging_name:
        staging_dir = Path(staging_name)
        staged_forecast_path = write_forecast_xlsx(
            forecast_frame,
            staging_dir / "Talep-tahmini.xlsx",
            data,
            HORIZON_START,
            HORIZON_END,
        )
        referee_forecast_frame = pd.read_excel(staged_forecast_path)
        if (forecast_fingerprint(referee_forecast_frame)
                != expected_fingerprint):
            raise RuntimeError("Staged forecast fingerprint eşleşmiyor")

        frame = prepare_frame(forecast_frame)
        days = [
            HORIZON_START + timedelta(days=offset)
            for offset in range((HORIZON_END - HORIZON_START).days + 1)
        ]
        legs = build_plan(data, frame, days)
        stage1 = run_same_lane_stage(
            legs, referee_forecast_frame, data)
        _require_stage0_entry(forecast_frame, stage1.baseline, data)
        _require_stage1_entry(stage1, data)
        stage2 = run_milk_run_stage(
            stage1.selected, referee_forecast_frame, data)
        _require_stage2_entry(stage1, stage2)
        _require_stage2_result(stage1, stage2, data)
        stage3 = run_pickup_stage(
            stage2.selected, referee_forecast_frame, data)
        _require_stage3_entry(stage2, stage3)
        _require_stage3_result(stage2, stage3, data)
        runtime_seconds = time.perf_counter() - t0
        _print_pipeline_metrics(stage1, stage2, stage3, data, runtime_seconds)
        _stage_and_publish(
            stage1,
            stage2,
            stage3,
            staged_forecast_path,
            expected_fingerprint,
            data,
            staging_dir,
            OUT_DIR,
        )

    total_seconds = time.perf_counter() - t0
    print(f"Yayın tamamlandı; toplam {total_seconds:.1f} sn")


if __name__ == "__main__":
    main()
