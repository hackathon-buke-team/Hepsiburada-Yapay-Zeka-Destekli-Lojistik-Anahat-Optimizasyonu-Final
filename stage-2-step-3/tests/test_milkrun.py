import copy
import itertools
import time
from collections import Counter
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction

import pandas as pd
import pytest

import src.milkrun as milkrun_module
from src.candidates import Part
from src.chain import analyze_leg_flows, physical_routes
from src.data import DATA_DIR, CompetitionData, Lane, VehicleType, load_all
from src.evaluation import (PlanEvaluation, PlanMetrics, forecast_fingerprint,
                            summarize_evaluation)
from src.export import require_plan_total
from src.forecast import forecast_horizon, to_forecast_frame
from src.ledger import HandlingLedger, TirLedger
from src.milkrun import (ROUTE_TYPES, _PairCandidate, _build_pair_candidates,
                         _decimal, _leg_key, _part_key)
from src.optimize import PlannedLeg, build_plan, prepare_frame
from src.repair import run_same_lane_stage
from src.simulator import SimResult
from src.timeutil import (SLA_TL_PER_DESI_HOUR, handling_minutes, late_hours,
                          travel_minutes)


VEHICLE_VALUES = {
    "Tır": (22400, 291.6666666666667, 13, 487.5, 25),
    "Kamyon": (12000, 208.33333333333334, 10, 318.25, 21),
    "Hafif Kamyon": (7200, 208.33333333333334, 10,
                     364.5833333333333, 20),
    "Kamyonet": (5600, 156.25, 6, 197.91666666666666, 18),
}


def _hours(minutes):
    return {
        name: minutes / 60
        for name in VEHICLE_VALUES
    }


@pytest.fixture
def pair_data():
    vehicles = {
        name: VehicleType(
            name,
            capacity,
            rental_hourly,
            rental_per_km,
            spot_hourly,
            spot_per_km,
        )
        for name, (
            capacity,
            rental_hourly,
            rental_per_km,
            spot_hourly,
            spot_per_km,
        ) in VEHICLE_VALUES.items()
    }
    lanes = {
        ("O", "B"): Lane("O", "B", 100, _hours(60), 1),
        ("O", "C"): Lane("O", "C", 120, _hours(70), 1),
        ("B", "C"): Lane("B", "C", 30, _hours(20), 1),
        ("C", "B"): Lane("C", "B", 40, _hours(25), 1),
    }
    demand = pd.DataFrame([
        {"cikis": "O", "varis": "B"},
        {"cikis": "O", "varis": "C"},
    ])
    return CompetitionData(
        vehicles=vehicles,
        lanes=lanes,
        rentals=[],
        handling_cap={"O": 100_000, "B": 100_000, "C": 100_000},
        tir_cap={"O": 100, "B": 100, "C": 100},
        demand=demand,
        tms=["O", "B", "C"],
    )


def _expected_spot_cost(vtype, start, end, km, data):
    vehicle = data.vehicles[vtype]
    seconds = int((end - start).total_seconds())
    return (
        Decimal(str(vehicle.spot_hourly))
        * Decimal(seconds)
        / Decimal(3600)
        + Decimal(str(vehicle.spot_per_km)) * Decimal(str(km))
    )


def _expected_sla(items, completion):
    return sum(
        (
            Decimal(str(desi))
            * Decimal(late_hours(part.deadline, completion))
            * Decimal(str(SLA_TL_PER_DESI_HOUR))
            for part, desi in items
        ),
        Decimal("0"),
    )


def _expected_direct_total(leg, data):
    return (
        _expected_spot_cost(
            leg.vtype,
            leg.load_start,
            leg.unload_end,
            data.lanes[(leg.origin, leg.dest)].km,
            data,
        )
        + _expected_sla(leg.items, leg.unload_end)
    )


def _direct_leg(item_id, dest, desi, load_start, data, vtype):
    lane = data.lanes[("O", dest)]
    handling = handling_minutes(desi)
    dep = load_start + timedelta(minutes=handling)
    arr = dep + timedelta(minutes=travel_minutes(lane.hours[vtype]))
    unload_end = arr + timedelta(minutes=handling)
    part = Part(
        part_id=item_id,
        base_id=item_id,
        desi=desi,
        ready=load_start,
        deadline=load_start + timedelta(days=lane.sla_days),
        dest=dest,
    )
    items = [(part, desi)]
    return PlannedLeg(
        kind="Spot",
        vtype=vtype,
        origin="O",
        dest=dest,
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=unload_end,
        items=items,
        cost=float(_expected_spot_cost(
            vtype, load_start, unload_end, lane.km, data)),
        penalty=float(_expected_sla(items, unload_end)),
    )


def _pair_sources(data, first_desi=1000, second_desi=1000,
                  first_type="Kamyonet", second_type="Kamyonet"):
    load_start = datetime(2026, 6, 29, 9)
    return (
        _direct_leg(
            "D00001", "B", first_desi, load_start, data, first_type),
        _direct_leg(
            "D00002", "C", second_desi, load_start, data, second_type),
    )


def _candidate(candidates, route, vtype="Kamyonet"):
    return next(
        candidate
        for candidate in candidates
        if candidate.route_destinations == route
        and candidate.vtype == vtype
    )


def test_pair_builds_both_orders_with_actual_interstop_lanes(pair_data):
    first, second = _pair_sources(pair_data)

    candidates = _build_pair_candidates(11, first, 7, second, pair_data)

    bc = _candidate(candidates, ("B", "C"))
    cb = _candidate(candidates, ("C", "B"))
    assert bc.source_tokens == cb.source_tokens == (7, 11)
    assert [(leg.origin, leg.dest) for leg in bc.legs] == [
        ("O", "B"), ("B", "C")]
    assert [(leg.origin, leg.dest) for leg in cb.legs] == [
        ("O", "C"), ("C", "B")]
    assert bc.legs[1].dep == datetime(2026, 6, 29, 10, 30)
    assert bc.legs[1].arr == datetime(2026, 6, 29, 10, 50)
    assert cb.legs[1].dep == datetime(2026, 6, 29, 10, 40)
    assert cb.legs[1].arr == datetime(2026, 6, 29, 11, 5)
    assert bc.legs[1].arr - bc.legs[1].dep == timedelta(minutes=20)
    assert cb.legs[1].arr - cb.legs[1].dep == timedelta(minutes=25)
    assert bc.legs[0].cost == float(_expected_spot_cost(
        "Kamyonet", bc.legs[0].load_start, bc.legs[1].unload_end,
        100 + 30, pair_data))
    assert cb.legs[0].cost == float(_expected_spot_cost(
        "Kamyonet", cb.legs[0].load_start, cb.legs[1].unload_end,
        120 + 40, pair_data))
    assert bc.legs[0].cost != cb.legs[0].cost


def test_pair_loads_everything_once_then_drops_by_destination(pair_data):
    first, second = _pair_sources(pair_data)
    pair = _candidate(
        _build_pair_candidates(1, first, 2, second, pair_data),
        ("B", "C"),
    )
    first_segment, second_segment = pair.legs

    assert first_segment.load_start == datetime(2026, 6, 29, 9)
    assert first_segment.dep == datetime(2026, 6, 29, 9, 20)
    assert len(first_segment.items) == 2
    assert any(item is first.items[0] for item in first_segment.items)
    assert any(item is second.items[0] for item in first_segment.items)
    assert second_segment.load_start == first_segment.unload_end
    assert second_segment.dep == first_segment.unload_end
    assert second_segment.items == [second.items[0]]
    assert second_segment.items[0] is second.items[0]
    assert all(part.dest == "C" for part, _desi in second_segment.items)
    assert (first_segment.chain_id, first_segment.chain_seq) == (0, 0)
    assert (second_segment.chain_id, second_segment.chain_seq) == (0, 1)


def test_pair_stores_continuous_vehicle_cost_only_on_first_segment(
        pair_data):
    first, second = _pair_sources(pair_data)
    pair = _candidate(
        _build_pair_candidates(1, first, 2, second, pair_data),
        ("B", "C"),
    )
    first_segment, second_segment = pair.legs
    seconds = int(
        (second_segment.unload_end - first_segment.load_start)
        .total_seconds()
    )
    vehicle = pair_data.vehicles["Kamyonet"]
    expected = (
        Decimal(str(vehicle.spot_hourly))
        * Decimal(seconds)
        / Decimal(3600)
        + Decimal(str(vehicle.spot_per_km)) * Decimal(100 + 30)
    )

    assert first_segment.cost == float(expected)
    assert second_segment.cost == 0


def test_pair_penalty_uses_each_original_final_drop(pair_data):
    first, second = _pair_sources(
        pair_data, first_desi=100, second_desi=200)
    first.items[0][0].deadline = datetime(2026, 6, 29, 9, 5)
    second.items[0][0].deadline = datetime(2026, 6, 29, 9, 55)

    pair = _candidate(
        _build_pair_candidates(1, first, 2, second, pair_data),
        ("B", "C"),
    )
    first_segment, second_segment = pair.legs

    assert first_segment.unload_end == datetime(2026, 6, 29, 10, 4)
    assert second_segment.unload_end == datetime(2026, 6, 29, 10, 26)
    assert late_hours(
        first.items[0][0].deadline, first_segment.unload_end) == 1
    assert late_hours(
        first.items[0][0].deadline, second_segment.unload_end) == 2
    assert late_hours(
        second.items[0][0].deadline, first_segment.unload_end) == 1
    assert first_segment.penalty == 40.0
    assert second_segment.penalty == 80.0
    assert pair.delta_tl == (
        _expected_spot_cost(
            pair.vtype,
            first_segment.load_start,
            second_segment.unload_end,
            130,
            pair_data,
        )
        + Decimal("40.0")
        + Decimal("80.0")
        - _expected_direct_total(first, pair_data)
        - _expected_direct_total(second, pair_data)
    )


def test_pair_recomputes_old_scheduled_cost_and_sla(pair_data):
    first, second = _pair_sources(
        pair_data, first_type="Kamyonet", second_type="Hafif Kamyon")
    first.items[0][0].deadline = datetime(2026, 6, 29, 9, 30)
    second.items[0][0].deadline = datetime(2026, 6, 29, 9, 20)
    first.cost = 99_999_999.25
    first.penalty = -88_888_888.5
    second.cost = -77_777_777.75
    second.penalty = 66_666_666.125

    pair = _candidate(
        _build_pair_candidates(41, first, 29, second, pair_data),
        ("B", "C"),
    )
    first_segment, second_segment = pair.legs
    expected = (
        _expected_spot_cost(
            pair.vtype,
            first_segment.load_start,
            second_segment.unload_end,
            130,
            pair_data,
        )
        + _expected_sla(
            [item for item in first_segment.items
             if item[0].dest == first_segment.dest],
            first_segment.unload_end,
        )
        + _expected_sla(second_segment.items, second_segment.unload_end)
        - _expected_direct_total(first, pair_data)
        - _expected_direct_total(second, pair_data)
    )

    assert _expected_sla(first.items, first.unload_end) > 0
    assert _expected_sla(second.items, second.unload_end) > 0
    assert pair.delta_tl == expected
    assert pair.delta_tl != Decimal(str(
        first.cost + first.penalty + second.cost + second.penalty))


def test_pair_delta_must_be_strictly_negative(pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    monkeypatch.setattr(
        milkrun_module,
        "_vehicle_cost_tl",
        lambda *_args: Decimal("100"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_final_sla_tl",
        lambda *_args: Decimal("0"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_scheduled_direct_total_tl",
        lambda *_args: Decimal("50"),
    )

    assert _build_pair_candidates(1, first, 2, second, pair_data) == ()

    monkeypatch.setattr(
        milkrun_module,
        "_scheduled_direct_total_tl",
        lambda *_args: Decimal("50.0000005"),
    )
    candidates = _build_pair_candidates(1, first, 2, second, pair_data)

    assert len(candidates) == 6
    assert all(isinstance(candidate, _PairCandidate)
               for candidate in candidates)
    assert {candidate.delta_tl for candidate in candidates} == {
        Decimal("-0.000001")}


def test_nonintegral_rates_use_decimal_str(pair_data):
    first, second = _pair_sources(pair_data)
    pair = _candidate(
        _build_pair_candidates(1, first, 2, second, pair_data),
        ("B", "C"),
    )
    first_segment, second_segment = pair.legs
    vehicle = pair_data.vehicles["Kamyonet"]
    new_seconds = int(
        (second_segment.unload_end - first_segment.load_start)
        .total_seconds()
    )
    first_seconds = int(
        (first.unload_end - first.load_start).total_seconds())
    second_seconds = int(
        (second.unload_end - second.load_start).total_seconds())
    second_coefficient = Decimal(new_seconds - first_seconds - second_seconds)
    distance_delta = Decimal(130 - 100 - 120)
    expected = (
        Decimal(str(vehicle.spot_hourly))
        * second_coefficient
        / Decimal(3600)
        + Decimal(str(vehicle.spot_per_km)) * distance_delta
    )
    binary_float_expansion = (
        Decimal(vehicle.spot_hourly)
        * second_coefficient
        / Decimal(3600)
        + Decimal(vehicle.spot_per_km) * distance_delta
    )

    assert vehicle.spot_hourly == 197.91666666666666
    assert pair.delta_tl == expected
    assert pair.delta_tl != binary_float_expansion


def test_pair_does_not_apply_stage3_detour_ratio(pair_data):
    pair_data.lanes[("B", "C")] = replace(
        pair_data.lanes[("B", "C")], km=160)
    pair_data.vehicles["Kamyonet"] = replace(
        pair_data.vehicles["Kamyonet"], spot_hourly=10_000.0)
    first, second = _pair_sources(pair_data)
    detour_ratio = Decimal(100 + 160) / Decimal(100 + 120)

    candidates = _build_pair_candidates(1, first, 2, second, pair_data)
    pair = _candidate(candidates, ("B", "C"))

    assert detour_ratio > Decimal("1.15")
    assert pair.delta_tl < Decimal("0")


def test_pair_preserves_whole_part_identity_without_piece(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)

    def forbidden_piece(_part, _take):
        raise AssertionError("Part.piece must not be called")

    monkeypatch.setattr(Part, "piece", forbidden_piece)

    pair = _candidate(
        _build_pair_candidates(1, first, 2, second, pair_data),
        ("B", "C"),
    )
    first_segment, second_segment = pair.legs

    assert any(item is first.items[0] for item in first_segment.items)
    assert any(item is second.items[0] for item in first_segment.items)
    assert second_segment.items[0] is second.items[0]
    assert second_segment.items[0][0] is second.items[0][0]
    assert [part for part, _desi in first_segment.items] == [
        first.items[0][0], second.items[0][0]]
    assert [part for part, _desi in second_segment.items] == [
        second.items[0][0]]


def test_combined_12001_is_rejected(pair_data):
    first, second = _pair_sources(
        pair_data,
        first_desi=6001,
        second_desi=6000,
        first_type="Hafif Kamyon",
        second_type="Hafif Kamyon",
    )

    assert _build_pair_candidates(1, first, 2, second, pair_data) == ()


def test_source_above_5600_is_allowed(pair_data):
    first, second = _pair_sources(
        pair_data,
        first_desi=5601,
        second_desi=5601,
        first_type="Hafif Kamyon",
        second_type="Hafif Kamyon",
    )

    candidates = _build_pair_candidates(1, first, 2, second, pair_data)

    witness = _candidate(candidates, ("B", "C"), "Kamyon")
    assert witness.delta_tl < Decimal("0")
    assert witness.legs[0].desi == 11202


def _replace_with_witness_parts(leg, late_deadline):
    original = leg.items[0][0]
    total = int(leg.desi)
    late = Part(
        part_id=f"{original.part_id}-late",
        base_id=original.base_id,
        desi=1,
        ready=original.ready,
        deadline=late_deadline,
        dest=original.dest,
    )
    remainder = Part(
        part_id=f"{original.part_id}-remainder",
        base_id=original.base_id,
        desi=total - 1,
        ready=original.ready,
        deadline=original.deadline,
        dest=original.dest,
    )
    leg.items = [(late, 1), (remainder, total - 1)]


@pytest.mark.parametrize(
    ("total", "required_type"),
    [(5600, "Kamyonet"), (7200, "Hafif Kamyon"), (12000, "Kamyon")],
)
def test_exact_pair_witness_for_each_vehicle_type(
        total, required_type, pair_data):
    load_start = datetime(2026, 6, 29, 9)
    first_desi = total // 2
    second_desi = total - first_desi
    source_type = (
        "Kamyonet" if max(first_desi, second_desi) <= 5600
        else "Hafif Kamyon"
    )
    first = _direct_leg(
        "D00001", "B", first_desi, load_start, pair_data, source_type)
    second = _direct_leg(
        "D00002", "C", second_desi, load_start, pair_data, source_type)

    dep1 = load_start + timedelta(minutes=handling_minutes(total))
    arr1 = dep1 + timedelta(minutes=travel_minutes(
        pair_data.lanes[("O", "B")].hours[required_type]))
    unload_end1 = arr1 + timedelta(minutes=handling_minutes(first_desi))
    arr2 = unload_end1 + timedelta(minutes=travel_minutes(
        pair_data.lanes[("B", "C")].hours[required_type]))
    unload_end2 = arr2 + timedelta(minutes=handling_minutes(second_desi))
    _replace_with_witness_parts(
        first, unload_end1 - timedelta(minutes=30))
    _replace_with_witness_parts(
        second, unload_end2 - timedelta(minutes=30))

    candidates = _build_pair_candidates(1, first, 2, second, pair_data)
    witness = next(
        candidate for candidate in candidates
        if candidate.vtype == required_type
    )
    first_segment, second_segment = witness.legs
    expected_cost = _expected_spot_cost(
        required_type,
        first_segment.load_start,
        second_segment.unload_end,
        pair_data.lanes[("O", "B")].km
        + pair_data.lanes[("B", "C")].km,
        pair_data,
    )
    expected_first_sla = _expected_sla(
        first.items, first_segment.unload_end)
    expected_second_sla = _expected_sla(
        second.items, second_segment.unload_end)

    assert witness.route_destinations == ("B", "C")
    assert witness.delta_tl < Decimal("0")
    assert first_segment.desi == total
    assert first_segment.load_start == load_start
    assert first_segment.cost == float(expected_cost)
    assert second_segment.cost == 0
    assert second_segment.items[0][0] is second.items[0][0]
    assert pair_data.vehicles[required_type].capacity_desi >= total
    assert expected_first_sla == Decimal("0.4")
    assert expected_second_sla == Decimal("0.4")
    assert first_segment.penalty == float(expected_first_sla)
    assert second_segment.penalty == float(expected_second_sla)
    assert witness.delta_tl == (
        expected_cost
        + expected_first_sla
        + expected_second_sla
        - _expected_direct_total(first, pair_data)
        - _expected_direct_total(second, pair_data)
    )


def test_pair_evaluates_every_fitting_non_tir_type_in_exact_order(
        pair_data, monkeypatch):
    first, second = _pair_sources(
        pair_data, first_desi=3000, second_desi=3000)
    calls = []

    def recording_cost(vtype, *_args):
        calls.append(vtype)
        return Decimal("1")

    monkeypatch.setattr(milkrun_module, "_vehicle_cost_tl", recording_cost)
    monkeypatch.setattr(
        milkrun_module,
        "_final_sla_tl",
        lambda *_args: Decimal("0"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_scheduled_direct_total_tl",
        lambda *_args: Decimal("100"),
    )

    candidates = _build_pair_candidates(1, first, 2, second, pair_data)

    assert ROUTE_TYPES == ("Kamyonet", "Hafif Kamyon", "Kamyon")
    assert calls == [
        "Hafif Kamyon", "Kamyon", "Hafif Kamyon", "Kamyon"]
    assert len(candidates) == 4


def test_semantic_keys_match_literal_fields_and_ignore_identity_metadata(
        pair_data):
    start = datetime(2026, 6, 29, 9)
    deadline = datetime(2026, 6, 30, 9)
    first_part = Part(
        "same-part", "same-base", 100.25, start,
        deadline, True, "B")
    second_part = Part(
        "same-part", "same-base", 100.25, start,
        deadline, True, "B")
    assert first_part is not second_part
    first = _direct_leg("unused", "B", 100, start, pair_data, "Kamyonet")
    first.items = [(first_part, 100.25)]
    second = replace(
        first,
        items=[(second_part, 100.25)],
        cost=999_999.0,
        penalty=888_888.0,
        vehicle_id="ignored-vehicle",
        item_ids=["ignored-item"],
    )
    expected_part_key = (
        "same-base",
        "same-part",
        start,
        deadline,
        True,
        "B",
        Decimal("100.25"),
    )
    expected_leg_key = (
        True,
        start,
        datetime(2026, 6, 29, 9, 1),
        "O",
        "B",
        "Kamyonet",
        datetime(2026, 6, 29, 10, 1),
        datetime(2026, 6, 29, 10, 2),
        True,
        -1,
        0,
        (expected_part_key,),
    )

    assert _part_key(first.items[0]) == expected_part_key
    assert _part_key(second.items[0]) == expected_part_key
    assert _part_key((replace(second_part, dest=None), 100.25)) == (
        "same-base",
        "same-part",
        start,
        deadline,
        True,
        "",
        Decimal("100.25"),
    )
    assert _leg_key(first) == expected_leg_key
    assert _leg_key(second) == expected_leg_key


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf"), Decimal("NaN")],
)
def test_decimal_rejects_nonfinite_inputs(value):
    with pytest.raises(ValueError):
        _decimal(value, "controlled value")


def test_pair_defensively_rejects_invalid_topology_and_fractional_total(
        pair_data):
    first, second = _pair_sources(pair_data)
    same_destination = _direct_leg(
        "D00003", "B", 1000, first.load_start, pair_data, "Kamyonet")
    wrong_destination = _direct_leg(
        "D00004", "C", 1000, first.load_start, pair_data, "Kamyonet")
    wrong_destination.items[0][0].dest = "B"
    fractional = _direct_leg(
        "D00005", "C", 1000, first.load_start, pair_data, "Kamyonet")
    fractional.items = [(fractional.items[0][0], 1000.5)]

    invalid_seconds = [
        replace(second, origin="B"),
        replace(second, load_start=second.load_start + timedelta(minutes=1)),
        same_destination,
        wrong_destination,
        fractional,
    ]
    for invalid_second in invalid_seconds:
        assert _build_pair_candidates(
            1, first, 2, invalid_second, pair_data) == ()


def test_pair_candidates_are_frozen_and_literal_route_type_sorted(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    monkeypatch.setattr(
        milkrun_module,
        "_vehicle_cost_tl",
        lambda *_args: Decimal("100"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_final_sla_tl",
        lambda *_args: Decimal("0"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_scheduled_direct_total_tl",
        lambda *_args: Decimal("50.0000005"),
    )

    candidates = _build_pair_candidates(90, first, 10, second, pair_data)
    deadline = datetime(2026, 6, 30, 9)
    expected_source_keys = (
        (
            True,
            datetime(2026, 6, 29, 9),
            datetime(2026, 6, 29, 9, 10),
            "O",
            "B",
            "Kamyonet",
            datetime(2026, 6, 29, 10, 10),
            datetime(2026, 6, 29, 10, 20),
            True,
            -1,
            0,
            ((
                "D00001", "D00001", datetime(2026, 6, 29, 9),
                deadline, False, "B", Decimal("1000"),
            ),),
        ),
        (
            True,
            datetime(2026, 6, 29, 9),
            datetime(2026, 6, 29, 9, 10),
            "O",
            "C",
            "Kamyonet",
            datetime(2026, 6, 29, 10, 20),
            datetime(2026, 6, 29, 10, 30),
            True,
            -1,
            0,
            ((
                "D00002", "D00002", datetime(2026, 6, 29, 9),
                deadline, False, "C", Decimal("1000"),
            ),),
        ),
    )
    expected_order = [
        (Decimal("-0.000001"), ("B", "C"), "Kamyonet", (10, 90)),
        (Decimal("-0.000001"), ("B", "C"), "Hafif Kamyon", (10, 90)),
        (Decimal("-0.000001"), ("B", "C"), "Kamyon", (10, 90)),
        (Decimal("-0.000001"), ("C", "B"), "Kamyonet", (10, 90)),
        (Decimal("-0.000001"), ("C", "B"), "Hafif Kamyon", (10, 90)),
        (Decimal("-0.000001"), ("C", "B"), "Kamyon", (10, 90)),
    ]

    assert tuple(sorted((_leg_key(first), _leg_key(second)))) == \
        expected_source_keys
    assert [
        (
            candidate.delta_tl,
            candidate.route_destinations,
            candidate.vtype,
            candidate.source_tokens,
        )
        for candidate in candidates
    ] == expected_order
    with pytest.raises(FrozenInstanceError):
        candidates[0].delta_tl = Decimal("0")


def test_pair_tie_order_ignores_identity_tokens_and_source_permutation(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    other_first, other_second = _pair_sources(pair_data)
    assert first.items[0][0] is not other_first.items[0][0]
    assert second.items[0][0] is not other_second.items[0][0]
    monkeypatch.setattr(
        milkrun_module,
        "_vehicle_cost_tl",
        lambda *_args: Decimal("100"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_final_sla_tl",
        lambda *_args: Decimal("0"),
    )
    monkeypatch.setattr(
        milkrun_module,
        "_scheduled_direct_total_tl",
        lambda *_args: Decimal("50.0000005"),
    )
    expected_order = [
        (Decimal("-0.000001"), ("B", "C"), "Kamyonet"),
        (Decimal("-0.000001"), ("B", "C"), "Hafif Kamyon"),
        (Decimal("-0.000001"), ("B", "C"), "Kamyon"),
        (Decimal("-0.000001"), ("C", "B"), "Kamyonet"),
        (Decimal("-0.000001"), ("C", "B"), "Hafif Kamyon"),
        (Decimal("-0.000001"), ("C", "B"), "Kamyon"),
    ]

    forward = _build_pair_candidates(
        900, first, -20, second, pair_data)
    reversed_distinct = _build_pair_candidates(
        314, other_second, 271, other_first, pair_data)

    assert {
        candidate.source_tokens for candidate in forward
    } == {(-20, 900)}
    assert {
        candidate.source_tokens for candidate in reversed_distinct
    } == {(271, 314)}
    assert [
        (candidate.delta_tl, candidate.route_destinations, candidate.vtype)
        for candidate in forward
    ] == expected_order
    assert [
        (candidate.delta_tl, candidate.route_destinations, candidate.vtype)
        for candidate in reversed_distinct
    ] == expected_order


METRIC_FIELDS = (
    "groups_considered",
    "pairs_evaluated",
    "chains_accepted",
    "source_vehicles_replaced",
    "segments_created",
    "parts_consolidated",
    "desi_consolidated",
    "local_saving_tl",
    "chain_type_mix",
    "triples_evaluated",
    "chain_size_mix",
)


def _metric_values(metrics):
    return tuple(getattr(metrics, name) for name in METRIC_FIELDS)


def _zero_metric_values():
    return (0, 0, 0, 0, 0, 0, 0, Decimal("0"), (), 0, ())


def _stage2_evaluation(total_cost, *, legs=None, violations=(), marker="stage"):
    return PlanEvaluation(
        legs=[] if legs is None else legs,
        plan_frame=pd.DataFrame({"marker": [marker]}),
        result=SimResult(
            vehicle_cost=total_cost,
            sla_penalty=Decimal("0"),
            total_cost=total_cost,
            violations=list(violations),
            per_vehicle=pd.DataFrame({"vehicle": [marker]}),
            per_demand=pd.DataFrame({"demand": [marker]}),
        ),
        notes=(marker,),
    )


def _zero_milk_run_metrics():
    return milkrun_module.MilkRunMetrics(
        groups_considered=0,
        pairs_evaluated=0,
        chains_accepted=0,
        source_vehicles_replaced=0,
        segments_created=0,
        parts_consolidated=0,
        desi_consolidated=0,
        local_saving_tl=Decimal("0"),
        chain_type_mix=(),
    )


def _run_controlled_stage2(monkeypatch, baseline, candidate):
    improved = [object()]
    metrics = _zero_milk_run_metrics()
    monkeypatch.setattr(
        milkrun_module,
        "milk_run_improve",
        lambda stage_legs, data: (improved, metrics),
    )
    monkeypatch.setattr(
        milkrun_module,
        "evaluate_legs",
        lambda stage_legs, forecast, data, *, fix: candidate,
        raising=False,
    )
    decision = milkrun_module.run_milk_run_stage(
        baseline, pd.DataFrame(), object())
    return decision, metrics


def _literal_leg_signature(leg):
    return (
        leg.kind,
        leg.vtype,
        leg.origin,
        leg.dest,
        leg.load_start,
        leg.dep,
        leg.arr,
        leg.unload_end,
        leg.chain_id,
        leg.chain_seq,
        tuple(
            (
                part.base_id,
                part.part_id,
                part.ready,
                part.deadline,
                part.carried_before,
                part.dest,
                Decimal(str(desi)),
            )
            for part, desi in leg.items
        ),
    )


def _literal_graph_signature(legs):
    return tuple(_literal_leg_signature(leg) for leg in legs)


def _lane_leg(item_id, origin, dest, desi, load_start, data, *,
              vtype="Kamyonet", kind="Spot", chain_id=None, chain_seq=0):
    lane = data.lanes[(origin, dest)]
    duration = handling_minutes(desi)
    dep = load_start + timedelta(minutes=duration)
    arr = dep + timedelta(minutes=travel_minutes(lane.hours[vtype]))
    unload_end = arr + timedelta(minutes=duration)
    part = Part(
        part_id=item_id,
        base_id=item_id,
        desi=desi,
        ready=load_start,
        deadline=load_start + timedelta(days=lane.sla_days),
        dest=dest,
    )
    return PlannedLeg(
        kind=kind,
        vtype=vtype,
        origin=origin,
        dest=dest,
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=unload_end,
        items=[(part, desi)],
        chain_id=chain_id,
        chain_seq=chain_seq,
    )


def _controlled_candidate(first_token, first, second_token, second, *,
                          delta, route=("B", "C"), vtype="Kamyonet",
                          first_arr=None):
    by_destination = {first.dest: first, second.dest: second}
    first_drop = by_destination[route[0]]
    second_drop = by_destination[route[1]]
    all_items = list(first.items) + list(second.items)
    combined = int(sum(Decimal(str(desi)) for _part, desi in all_items))
    first_desi = int(sum(
        Decimal(str(desi)) for _part, desi in first_drop.items))
    second_desi = int(sum(
        Decimal(str(desi)) for _part, desi in second_drop.items))
    load_start = first.load_start
    dep1 = load_start + timedelta(minutes=handling_minutes(combined))
    if first_arr is None:
        first_arr = dep1 + timedelta(hours=1)
    unload_end1 = first_arr + timedelta(
        minutes=handling_minutes(first_desi))
    dep2 = unload_end1
    arr2 = dep2 + timedelta(hours=1)
    unload_end2 = arr2 + timedelta(
        minutes=handling_minutes(second_desi))
    first_segment = PlannedLeg(
        kind="Spot",
        vtype=vtype,
        origin=first.origin,
        dest=route[0],
        load_start=load_start,
        dep=dep1,
        arr=first_arr,
        unload_end=unload_end1,
        items=all_items,
        chain_id=0,
        chain_seq=0,
    )
    second_segment = PlannedLeg(
        kind="Spot",
        vtype=vtype,
        origin=route[0],
        dest=route[1],
        load_start=dep2,
        dep=dep2,
        arr=arr2,
        unload_end=unload_end2,
        items=list(second_drop.items),
        chain_id=0,
        chain_seq=1,
    )
    return _PairCandidate(
        source_tokens=tuple(sorted((first_token, second_token))),
        route_destinations=route,
        vtype=vtype,
        legs=(first_segment, second_segment),
        delta_tl=Decimal(str(delta)),
    )


def _new_chain_groups(legs, existing_ids=()):
    groups = {}
    for leg in legs:
        if leg.chain_id is not None and leg.chain_id not in existing_ids:
            groups.setdefault(leg.chain_id, []).append(leg)
    return {
        chain_id: sorted(group, key=lambda leg: leg.chain_seq)
        for chain_id, group in groups.items()
    }


def test_metrics_are_frozen_and_have_exact_mapped_fields():
    metric_type = milkrun_module.MilkRunMetrics
    metrics = metric_type(
        groups_considered=1,
        pairs_evaluated=2,
        chains_accepted=3,
        source_vehicles_replaced=6,
        segments_created=6,
        parts_consolidated=7,
        desi_consolidated=8,
        local_saving_tl=Decimal("9.25"),
        chain_type_mix=(("Kamyon", 3),),
        triples_evaluated=4,
        chain_size_mix=((2, 2), (3, 1)),
    )

    assert tuple(field.name for field in fields(metric_type)) == METRIC_FIELDS
    assert _metric_values(metrics) == (
        1, 2, 3, 6, 6, 7, 8, Decimal("9.25"), (("Kamyon", 3),),
        4, ((2, 2), (3, 1)))
    with pytest.raises(FrozenInstanceError):
        metrics.groups_considered = 0


def test_stage2_uses_accepted_stage1_evaluation_as_baseline(
        pair_data, monkeypatch):
    baseline_leg = object()
    baseline = _stage2_evaluation(
        Decimal("100"), legs=[baseline_leg], marker="baseline")
    improved = [object()]
    candidate = _stage2_evaluation(
        Decimal("90"), legs=improved, marker="candidate")
    metrics = _zero_milk_run_metrics()
    events = []

    def tracking_improve(stage_legs, data):
        events.append(("improve", stage_legs, data))
        return improved, metrics

    def tracking_evaluate(stage_legs, forecast, data, *, fix):
        events.append(("evaluate", stage_legs, forecast, data, fix))
        return candidate

    forecast = pd.DataFrame({"forecast": [1]})
    monkeypatch.setattr(milkrun_module, "milk_run_improve", tracking_improve)
    monkeypatch.setattr(
        milkrun_module, "evaluate_legs", tracking_evaluate, raising=False)

    decision = milkrun_module.run_milk_run_stage(
        baseline, forecast, pair_data)

    assert events == [
        ("improve", baseline.legs, pair_data),
        ("evaluate", improved, forecast, pair_data, True),
    ]
    assert decision.baseline is baseline
    assert decision.candidate is candidate
    assert decision.selected is candidate
    assert decision.metrics is metrics


def test_milk_run_decision_is_frozen_and_has_exact_mapped_fields(monkeypatch):
    baseline = _stage2_evaluation(Decimal("100"), marker="baseline")
    candidate = _stage2_evaluation(Decimal("90"), marker="candidate")

    decision, _metrics = _run_controlled_stage2(
        monkeypatch, baseline, candidate)

    assert tuple(
        field.name for field in fields(milkrun_module.MilkRunDecision)
    ) == (
        "baseline",
        "candidate",
        "selected",
        "metrics",
        "accepted",
        "saving_tl",
    )
    with pytest.raises(FrozenInstanceError):
        decision.accepted = False


def test_stage2_candidate_evaluates_with_fix_true(pair_data, monkeypatch):
    baseline = _stage2_evaluation(Decimal("100"), marker="baseline")
    improved = [object()]
    candidate = _stage2_evaluation(Decimal("90"), marker="candidate")
    forecast = pd.DataFrame({"forecast": [1]})
    calls = []
    monkeypatch.setattr(
        milkrun_module,
        "milk_run_improve",
        lambda stage_legs, data: (improved, _zero_milk_run_metrics()),
    )

    def tracking_evaluate(stage_legs, forecast_frame, data, *, fix):
        calls.append((stage_legs, forecast_frame, data, fix))
        return candidate

    monkeypatch.setattr(
        milkrun_module, "evaluate_legs", tracking_evaluate, raising=False)

    milkrun_module.run_milk_run_stage(baseline, forecast, pair_data)

    assert calls == [(improved, forecast, pair_data, True)]
    assert calls[0][1] is forecast
    assert calls[0][2] is pair_data


def test_stage2_global_violation_rolls_back(monkeypatch):
    baseline = _stage2_evaluation(Decimal("100"), marker="baseline")
    candidate = _stage2_evaluation(
        Decimal("50"),
        violations=("candidate violation",),
        marker="candidate",
    )

    decision, metrics = _run_controlled_stage2(
        monkeypatch, baseline, candidate)

    assert decision.baseline is baseline
    assert decision.candidate is candidate
    assert decision.metrics is metrics
    assert decision.saving_tl == Decimal("50")
    assert decision.accepted is False
    assert decision.selected is baseline


@pytest.mark.parametrize(
    ("saving", "accepted"),
    [
        (Decimal("0.999999"), False),
        (Decimal("1.00"), True),
        (Decimal("1.000001"), True),
    ],
)
def test_stage2_raw_one_tl_boundary(saving, accepted, monkeypatch):
    baseline = _stage2_evaluation(Decimal("100"), marker="baseline")
    candidate = _stage2_evaluation(
        Decimal("100") - saving, marker="candidate")

    decision, _metrics = _run_controlled_stage2(
        monkeypatch, baseline, candidate)

    assert decision.saving_tl == saving
    assert decision.accepted is accepted
    assert decision.selected is (candidate if accepted else baseline)


def test_stage2_inputs_remain_unchanged(pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    baseline = _stage2_evaluation(
        Decimal("100"), legs=[second, first], marker="baseline")
    forecast = pd.DataFrame({
        "forecast": ["owned"],
        "desi": [Decimal("2000")],
    })
    candidate = _stage2_evaluation(Decimal("90"), marker="candidate")
    baseline_before = copy.deepcopy(baseline)
    forecast_before = forecast.copy(deep=True)
    original_legs = baseline.legs
    original_frame = baseline.plan_frame
    original_result = baseline.result

    monkeypatch.setattr(
        milkrun_module,
        "evaluate_legs",
        lambda stage_legs, forecast_frame, data, *, fix: candidate,
        raising=False,
    )

    decision = milkrun_module.run_milk_run_stage(
        baseline, forecast, pair_data)

    assert decision.baseline is baseline
    assert baseline.legs is original_legs
    assert baseline.plan_frame is original_frame
    assert baseline.result is original_result
    assert baseline.legs == baseline_before.legs
    pd.testing.assert_frame_equal(
        baseline.plan_frame, baseline_before.plan_frame)
    assert baseline.result.vehicle_cost == baseline_before.result.vehicle_cost
    assert baseline.result.sla_penalty == baseline_before.result.sla_penalty
    assert baseline.result.total_cost == baseline_before.result.total_cost
    assert baseline.result.violations == baseline_before.result.violations
    pd.testing.assert_frame_equal(
        baseline.result.per_vehicle, baseline_before.result.per_vehicle)
    pd.testing.assert_frame_equal(
        baseline.result.per_demand, baseline_before.result.per_demand)
    assert baseline.notes == baseline_before.notes
    pd.testing.assert_frame_equal(forecast, forecast_before)


@pytest.mark.parametrize(
    "case",
    ["empty", "rented", "tir", "chain", "wrong-dest", "repeated"],
)
def test_only_direct_loaded_spot_non_tir_sources_are_eligible(
        case, pair_data):
    first, second = _pair_sources(pair_data)
    legs = [first, second]
    if case == "empty":
        second.items = []
    elif case == "rented":
        second.kind = "Kiralık"
    elif case == "tir":
        second.vtype = "Tır"
    elif case == "chain":
        second.chain_id = 4
    elif case == "wrong-dest":
        second.items[0][0].dest = "B"
    else:
        repeated = replace(
            first,
            load_start=first.load_start + timedelta(days=1),
            dep=first.dep + timedelta(days=1),
            arr=first.arr + timedelta(days=1),
            unload_end=first.unload_end + timedelta(days=1),
            items=[first.items[0]],
        )
        legs.append(repeated)
    before = copy.deepcopy(legs)

    improved, metrics = milkrun_module.milk_run_improve(legs, pair_data)

    assert legs == before
    assert _literal_graph_signature(improved) == tuple(sorted(
        (_literal_leg_signature(leg) for leg in before),
        key=lambda signature: (
            signature[0] != "Kiralık",
            signature[4],
            signature[5],
            signature[2],
            signature[3],
            signature[1],
            signature[6],
            signature[7],
            signature[8] is None,
            -1 if signature[8] is None else signature[8],
            signature[9],
            signature[10],
        ),
    ))
    assert _metric_values(metrics) == _zero_metric_values()


@pytest.mark.parametrize(
    "case",
    ["zero", "fractional", "mismatch", "not-ready"],
)
def test_source_requires_complete_positive_integral_ready_parts(
        case, pair_data):
    first, second = _pair_sources(pair_data)
    part, _desi = second.items[0]
    if case == "zero":
        part.desi = 0
        second.items = [(part, 0)]
    elif case == "fractional":
        part.desi = 1000.5
        second.items = [(part, 1000.5)]
    elif case == "mismatch":
        second.items = [(part, 999)]
    else:
        part.ready = second.load_start + timedelta(seconds=1)

    improved, metrics = milkrun_module.milk_run_improve(
        [first, second], pair_data)

    assert len(improved) == 2
    assert all(leg.chain_id is None for leg in improved)
    assert _metric_values(metrics) == _zero_metric_values()


def test_pair_requires_exact_equal_load_start(pair_data):
    first, second = _pair_sources(pair_data)
    second.load_start += timedelta(minutes=1)

    improved, metrics = milkrun_module.milk_run_improve(
        [second, first], pair_data)

    assert len(improved) == 2
    assert all(leg.chain_id is None for leg in improved)
    assert _metric_values(metrics) == _zero_metric_values()


@pytest.mark.parametrize("case", ["origin", "destination"])
def test_pair_requires_common_origin_and_distinct_destinations(
        case, pair_data):
    first, second = _pair_sources(pair_data)
    if case == "origin":
        second.origin = "B"
    else:
        second.dest = "B"
        second.items[0][0].dest = "B"

    improved, metrics = milkrun_module.milk_run_improve(
        [first, second], pair_data)

    assert len(improved) == 2
    assert all(leg.chain_id is None for leg in improved)
    assert _metric_values(metrics) == _zero_metric_values()


def test_no_source_leg_5600_cap_in_full_pass(pair_data):
    first, second = _pair_sources(
        pair_data,
        first_desi=5601,
        second_desi=5601,
        first_type="Hafif Kamyon",
        second_type="Hafif Kamyon",
    )

    improved, metrics = milkrun_module.milk_run_improve(
        [second, first], pair_data)

    chains = _new_chain_groups(improved)
    assert list(chains) == [1]
    assert [leg.chain_seq for leg in chains[1]] == [0, 1]
    assert [leg.vtype for leg in chains[1]] == ["Kamyon", "Kamyon"]
    assert _metric_values(metrics)[:7] == (1, 1, 1, 2, 2, 2, 11202)
    assert metrics.local_saving_tl > Decimal("0")
    assert metrics.chain_type_mix == (("Kamyon", 1),)


def test_full_pass_rejects_combined_12001(pair_data):
    first, second = _pair_sources(
        pair_data,
        first_desi=6001,
        second_desi=6000,
        first_type="Hafif Kamyon",
        second_type="Hafif Kamyon",
    )

    improved, metrics = milkrun_module.milk_run_improve(
        [first, second], pair_data)

    assert len(improved) == 2
    assert all(leg.chain_id is None for leg in improved)
    assert _metric_values(metrics) == (
        1, 1, 0, 0, 0, 0, 0, Decimal("0"), (), 0, ())


def test_full_pass_considers_both_orders_and_all_fitting_types(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    original_builder = milkrun_module._build_pair_candidates
    observed = []

    def recording_builder(*args):
        candidates = original_builder(*args)
        observed.append([
            (candidate.route_destinations, candidate.vtype)
            for candidate in candidates
        ])
        return candidates

    monkeypatch.setattr(
        milkrun_module, "_build_pair_candidates", recording_builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [second, first], pair_data)

    assert len(observed) == 1
    assert len(observed[0]) == 6
    assert set(observed[0]) == {
        (("B", "C"), "Kamyonet"),
        (("B", "C"), "Hafif Kamyon"),
        (("B", "C"), "Kamyon"),
        (("C", "B"), "Kamyonet"),
        (("C", "B"), "Hafif Kamyon"),
        (("C", "B"), "Kamyon"),
    }
    assert len(_new_chain_groups(improved)) == 1
    assert metrics.groups_considered == 1
    assert metrics.pairs_evaluated == 1
    assert metrics.chains_accepted == 1


def test_full_pass_is_exactly_two_segments_and_one_pass(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    third = _direct_leg(
        "D00003", "C", 900, first.load_start, pair_data, "Kamyonet")
    original_builder = milkrun_module._build_pair_candidates
    source_chain_ids = []

    def recording_builder(first_token, first_leg, second_token, second_leg,
                          data):
        source_chain_ids.append((first_leg.chain_id, second_leg.chain_id))
        return original_builder(
            first_token, first_leg, second_token, second_leg, data)

    monkeypatch.setattr(
        milkrun_module, "_build_pair_candidates", recording_builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [third, second, first], pair_data)

    chains = _new_chain_groups(improved)
    assert source_chain_ids == [(None, None), (None, None)]
    assert metrics.pairs_evaluated == 2
    assert metrics.chains_accepted == 1
    assert len(chains) == 1
    assert [leg.chain_seq for group in chains.values() for leg in group] == [0, 1]
    assert len(improved) == 3


def test_whole_part_identity_survives_commit(pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)

    def forbidden_piece(_part, _take):
        raise AssertionError("Part.piece must not be called")

    monkeypatch.setattr(Part, "piece", forbidden_piece)

    improved, metrics = milkrun_module.milk_run_improve(
        [first, second], pair_data)

    chain = next(iter(_new_chain_groups(improved).values()))
    first_segment, second_segment = chain
    first_parts = [part for part, _desi in first_segment.items]
    second_parts = [part for part, _desi in second_segment.items]
    all_occurrences = first_parts + second_parts
    assert metrics.parts_consolidated == 2
    assert len({id(part) for part in all_occurrences}) == 2
    assert len(first_parts) == 2
    assert len(second_parts) == 1
    assert any(part is second_parts[0] for part in first_parts)
    assert sum(part is second_parts[0] for part in all_occurrences) == 2
    other = next(part for part in first_parts if part is not second_parts[0])
    assert sum(part is other for part in all_occurrences) == 1


@pytest.mark.parametrize("legs", [[], pytest.param(None, id="ineligible")])
def test_no_eligible_group_returns_owned_copy_and_zero_metrics(
        legs, pair_data):
    if legs is None:
        first, _second = _pair_sources(pair_data)
        first.kind = "Kiralık"
        legs = [first]

    improved, metrics = milkrun_module.milk_run_improve(legs, pair_data)

    assert improved is not legs
    assert _literal_graph_signature(improved) == _literal_graph_signature(legs)
    if legs:
        assert improved[0] is not legs[0]
        assert improved[0].items[0][0] is not legs[0].items[0][0]
    assert _metric_values(metrics) == _zero_metric_values()


def test_profitable_pair_rejected_by_complete_handling_ledger(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    next_day = first.load_start + timedelta(days=1)
    unrelated = _lane_leg(
        "unrelated", "B", "C", 600, next_day, pair_data,
        kind="Kiralık")
    pair_data.handling_cap = {"O": 100_000, "B": 1_000, "C": 100_000}

    def builder(first_token, first_leg, second_token, second_leg, _data):
        return (_controlled_candidate(
            first_token,
            first_leg,
            second_token,
            second_leg,
            delta="-25",
            first_arr=datetime(2026, 6, 30, 9),
        ),)

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)
    legs = [second, unrelated, first]
    before = copy.deepcopy(legs)

    improved, metrics = milkrun_module.milk_run_improve(legs, pair_data)

    assert legs == before
    assert all(leg.chain_id is None for leg in improved)
    assert _metric_values(metrics) == (
        1, 1, 0, 0, 0, 0, 0, Decimal("0"), (), 0, ())


@pytest.mark.parametrize("malformation", ["chain", "readiness", "capacity"])
def test_complete_trial_rejects_malformed_readiness_and_capacity_states(
        malformation, pair_data):
    first, second = _pair_sources(
        pair_data, first_desi=100, second_desi=100)
    unrelated = _lane_leg(
        "malformed", "B", "C", 100,
        first.load_start + timedelta(days=1), pair_data,
        kind="Kiralık")
    if malformation == "chain":
        unrelated.kind = "Spot"
        unrelated.chain_id = 91
        unrelated.chain_seq = 1
    elif malformation == "readiness":
        unrelated.items[0][0].ready = unrelated.load_start + timedelta(
            seconds=1)
    else:
        unrelated.items[0][0].desi = 5601
        unrelated.items = [(unrelated.items[0][0], 5601)]

    improved, metrics = milkrun_module.milk_run_improve(
        [unrelated, first, second], pair_data)

    assert len(improved) == 3
    assert not _new_chain_groups(improved, existing_ids=(91,))
    assert metrics.pairs_evaluated == 1
    assert metrics.chains_accepted == 0


def test_complete_handling_trial_keeps_exact_midnight_split(
        pair_data, monkeypatch):
    start = datetime(2026, 6, 29, 23, 30)
    leg = _direct_leg("midnight", "B", 10_000, start, pair_data, "Tır")
    ledgers = []

    class RecordingHandlingLedger(HandlingLedger):
        def __init__(self, capacity):
            super().__init__(capacity)
            ledgers.append(self)

    monkeypatch.setattr(
        milkrun_module, "HandlingLedger", RecordingHandlingLedger)

    assert milkrun_module._trial_candidate_valid([leg], pair_data)
    assert len(ledgers) == 1
    assert ledgers[0].used[("O", date(2026, 6, 29))] == 3000
    assert ledgers[0].used[("O", date(2026, 6, 30))] == 7000
    assert sum(
        used for (tm, _day), used in ledgers[0].used.items() if tm == "O"
    ) == 10_000


def test_profitable_pair_rejected_by_unchanged_tir_visits(pair_data):
    first, second = _pair_sources(
        pair_data, first_desi=100, second_desi=100)
    start = first.load_start + timedelta(hours=3)
    tir_one = _lane_leg(
        "tir-one", "B", "C", 100, start, pair_data, vtype="Tır")
    tir_two = _lane_leg(
        "tir-two", "B", "C", 100, start, pair_data, vtype="Tır")
    pair_data.tir_cap = {"O": 100, "B": 1, "C": 100}
    legs = [tir_one, first, tir_two, second]
    before = copy.deepcopy(legs)

    improved, metrics = milkrun_module.milk_run_improve(legs, pair_data)

    assert legs == before
    assert all(leg.chain_id is None for leg in improved)
    assert _metric_values(metrics) == (
        1, 1, 0, 0, 0, 0, 0, Decimal("0"), (), 0, ())


def test_tir_stationary_arrival_departure_is_one_visit(
        pair_data, monkeypatch):
    start = datetime(2026, 6, 29, 9)
    to_b = Part(
        "to-b", "to-b", 100, start, start + timedelta(days=1),
        dest="B")
    to_c = Part(
        "to-c", "to-c", 200, start, start + timedelta(days=1),
        dest="C")
    first = PlannedLeg(
        kind="Spot", vtype="Tır", origin="O", dest="B",
        load_start=start, dep=start + timedelta(minutes=3),
        arr=start + timedelta(hours=1, minutes=3),
        unload_end=start + timedelta(hours=1, minutes=4),
        items=[(to_b, 100), (to_c, 200)], chain_id=5, chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot", vtype="Tır", origin="B", dest="C",
        load_start=first.unload_end, dep=first.unload_end,
        arr=first.unload_end + timedelta(hours=1),
        unload_end=first.unload_end + timedelta(hours=1, minutes=2),
        items=[(to_c, 200)], chain_id=5, chain_seq=1,
    )
    pair_data.tir_cap = {"O": 1, "B": 1, "C": 1}
    ledgers = []

    class RecordingTirLedger(TirLedger):
        def __init__(self, capacity):
            super().__init__(capacity)
            ledgers.append(self)

    monkeypatch.setattr(milkrun_module, "TirLedger", RecordingTirLedger)

    assert milkrun_module._trial_candidate_valid([second, first], pair_data)
    assert len(ledgers) == 1
    assert ledgers[0].count("O", date(2026, 6, 29)) == 1
    assert ledgers[0].count("B", date(2026, 6, 29)) == 1
    assert ledgers[0].count("C", date(2026, 6, 29)) == 1


def test_chain_cannot_extend_stage1_final_cargo_date(
        pair_data, monkeypatch):
    first, second = _pair_sources(
        pair_data, first_desi=100, second_desi=100)
    empty_rented = PlannedLeg(
        kind="Kiralık",
        vtype="Kamyonet",
        origin="O",
        dest="B",
        load_start=datetime(2026, 7, 2, 8),
        dep=datetime(2026, 7, 2, 8),
        arr=datetime(2026, 7, 2, 9),
        unload_end=datetime(2026, 7, 2, 9),
        items=[],
    )

    def builder(first_token, first_leg, second_token, second_leg, _data):
        return (_controlled_candidate(
            first_token,
            first_leg,
            second_token,
            second_leg,
            delta="-40",
            first_arr=datetime(2026, 6, 30, 9),
        ),)

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [empty_rented, second, first], pair_data)

    assert len(improved) == 3
    assert all(leg.chain_id is None for leg in improved)
    assert any(not leg.items and leg.unload_end.date() == date(2026, 7, 2)
               for leg in improved)
    assert metrics.pairs_evaluated == 1
    assert metrics.chains_accepted == 0


def test_rejected_trial_does_not_block_later_candidate(
        pair_data, monkeypatch):
    first, second = _pair_sources(
        pair_data, first_desi=100, second_desi=100)
    unrelated = _lane_leg(
        "unrelated", "B", "C", 600,
        first.load_start + timedelta(days=1), pair_data,
        kind="Kiralık")
    pair_data.handling_cap = {"O": 100_000, "B": 650, "C": 100_000}

    def builder(first_token, first_leg, second_token, second_leg, _data):
        return (
            _controlled_candidate(
                first_token,
                first_leg,
                second_token,
                second_leg,
                delta="-30",
                route=("B", "C"),
                first_arr=datetime(2026, 6, 30, 9),
            ),
            _controlled_candidate(
                first_token,
                first_leg,
                second_token,
                second_leg,
                delta="-20",
                route=("C", "B"),
            ),
        )

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [unrelated, first, second], pair_data)

    chain = next(iter(_new_chain_groups(improved).values()))
    assert [(leg.origin, leg.dest) for leg in chain] == [
        ("O", "C"), ("C", "B")]
    assert _metric_values(metrics) == (
        1, 1, 1, 2, 2, 2, 200, Decimal("20"), (("Kamyonet", 1),),
        0, ((2, 1),))


def test_chain_ids_start_above_existing_and_rejections_do_not_consume(
        pair_data, monkeypatch):
    day = datetime(2026, 6, 29, 9)
    sources = []
    for hour in (9, 10, 11):
        load_start = day.replace(hour=hour)
        sources.extend([
            _direct_leg(
                f"B-{hour}", "B", 100, load_start,
                pair_data, "Kamyonet"),
            _direct_leg(
                f"C-{hour}", "C", 100, load_start,
                pair_data, "Kamyonet"),
        ])
    existing_three = _lane_leg(
        "existing-three", "C", "B", 10,
        datetime(2026, 7, 1, 8), pair_data,
        chain_id=3)
    existing_seven = _lane_leg(
        "existing-seven", "B", "C", 600,
        datetime(2026, 6, 30, 8), pair_data,
        chain_id=7)
    pair_data.handling_cap = {"O": 100_000, "B": 650, "C": 100_000}

    def builder(first_token, first_leg, second_token, second_leg, _data):
        hour = first_leg.load_start.hour
        if hour == 9:
            return (_controlled_candidate(
                first_token,
                first_leg,
                second_token,
                second_leg,
                delta="-100",
                first_arr=datetime(2026, 6, 30, 9),
            ),)
        return (_controlled_candidate(
            first_token,
            first_leg,
            second_token,
            second_leg,
            delta="-50" if hour == 10 else "-40",
        ),)

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [existing_seven, *reversed(sources), existing_three], pair_data)

    groups = _new_chain_groups(improved, existing_ids=(3, 7))
    assert sorted(groups) == [8, 9]
    assert [
        [part.part_id for part, _desi in groups[chain_id][0].items]
        for chain_id in (8, 9)
    ] == [["B-10", "C-10"], ["B-11", "C-11"]]
    assert metrics.pairs_evaluated == 3
    assert metrics.chains_accepted == 2
    assert metrics.local_saving_tl == Decimal("90")


def test_input_graph_and_forecast_objects_are_not_mutated(pair_data):
    first, second = _pair_sources(pair_data)
    legs = [second, first]
    pair_data.demand = pd.DataFrame([
        {"token": ["forecast-owned"], "value": 17},
    ])
    before_legs = copy.deepcopy(legs)
    before_data = copy.deepcopy(pair_data)
    original_parts = [part for leg in legs for part, _desi in leg.items]
    original_part_state = [copy.deepcopy(vars(part)) for part in original_parts]

    improved, metrics = milkrun_module.milk_run_improve(legs, pair_data)

    assert legs == before_legs
    assert improved is not legs
    assert all(returned is not original
               for returned, original in zip(improved, legs))
    assert [vars(part) for part in original_parts] == original_part_state
    assert pair_data.vehicles == before_data.vehicles
    assert pair_data.lanes == before_data.lanes
    assert pair_data.rentals == before_data.rentals
    assert pair_data.handling_cap == before_data.handling_cap
    assert pair_data.tir_cap == before_data.tir_cap
    assert pair_data.tms == before_data.tms
    pd.testing.assert_frame_equal(pair_data.demand, before_data.demand)
    assert metrics.chains_accepted == 1


def test_milk_run_improve_deepcopies_graph_exactly_once(
        pair_data, monkeypatch):
    first, second = _pair_sources(pair_data)
    legs = [first, second]
    calls = []
    real_deepcopy = copy.deepcopy

    def recording_deepcopy(value):
        calls.append(value)
        return real_deepcopy(value)

    monkeypatch.setattr(milkrun_module, "deepcopy", recording_deepcopy)

    improved, metrics = milkrun_module.milk_run_improve(legs, pair_data)

    assert len(calls) == 1
    assert calls[0] is legs
    assert improved is not legs
    assert metrics.chains_accepted == 1


def test_most_negative_candidate_wins_overlap(pair_data, monkeypatch):
    start = datetime(2026, 6, 29, 9)
    sources = [
        _direct_leg("B-1", "B", 100, start, pair_data, "Kamyonet"),
        _direct_leg("B-2", "B", 100, start, pair_data, "Kamyonet"),
        _direct_leg("C-1", "C", 100, start, pair_data, "Kamyonet"),
        _direct_leg("C-2", "C", 100, start, pair_data, "Kamyonet"),
    ]
    deltas = {
        frozenset(("B-1", "C-1")): "-30",
        frozenset(("B-1", "C-2")): "-20",
        frozenset(("B-2", "C-1")): "-10",
    }

    def builder(first_token, first, second_token, second, _data):
        pair_ids = frozenset((
            first.items[0][0].part_id,
            second.items[0][0].part_id,
        ))
        if pair_ids not in deltas:
            return ()
        return (_controlled_candidate(
            first_token,
            first,
            second_token,
            second,
            delta=deltas[pair_ids],
        ),)

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [sources[3], sources[1], sources[2], sources[0]], pair_data)

    chain = next(iter(_new_chain_groups(improved).values()))
    assert [part.part_id for part, _desi in chain[0].items] == ["B-1", "C-1"]
    assert sorted(
        part.part_id
        for leg in improved
        if leg.chain_id is None
        for part, _desi in leg.items
    ) == ["B-2", "C-2"]
    assert _metric_values(metrics) == (
        1, 4, 1, 2, 2, 2, 200, Decimal("30"), (("Kamyonet", 1),),
        0, ((2, 1),))


def test_equal_delta_uses_route_type_source_semantic_key(
        pair_data, monkeypatch):
    start = datetime(2026, 6, 29, 9)
    sources = [
        _direct_leg("B-a", "B", 100, start, pair_data, "Kamyonet"),
        _direct_leg("B-z", "B", 100, start, pair_data, "Kamyonet"),
        _direct_leg("C-a", "C", 100, start, pair_data, "Kamyonet"),
        _direct_leg("C-z", "C", 100, start, pair_data, "Kamyonet"),
    ]

    saved = {}

    def variants(first_token, first, second_token, second):
        return (
            _controlled_candidate(
                first_token, first, second_token, second,
                delta="-10", route=("C", "B"), vtype="Kamyonet"),
            _controlled_candidate(
                first_token, first, second_token, second,
                delta="-10", route=("B", "C"), vtype="Kamyon"),
            _controlled_candidate(
                first_token, first, second_token, second,
                delta="-10", route=("B", "C"), vtype="Kamyonet"),
        )

    def builder(first_token, first, second_token, second, _data):
        pair_ids = frozenset((
            first.items[0][0].part_id,
            second.items[0][0].part_id,
        ))
        candidates = variants(first_token, first, second_token, second)
        if pair_ids == frozenset(("B-a", "C-a")):
            saved["semantic-first"] = candidates
            return ()
        if pair_ids == frozenset(("B-z", "C-z")):
            return candidates + saved["semantic-first"]
        return ()

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)

    improved, metrics = milkrun_module.milk_run_improve(
        [sources[3], sources[1], sources[2], sources[0]], pair_data)

    groups = _new_chain_groups(improved)
    assert sorted(groups) == [1, 2]
    assert [
        (
            chain_id,
            groups[chain_id][0].origin,
            groups[chain_id][0].dest,
            groups[chain_id][1].origin,
            groups[chain_id][1].dest,
            groups[chain_id][0].vtype,
            [part.part_id for part, _desi in groups[chain_id][0].items],
        )
        for chain_id in (1, 2)
    ] == [
        (1, "O", "B", "B", "C", "Kamyonet", ["B-a", "C-a"]),
        (2, "O", "B", "B", "C", "Kamyonet", ["B-z", "C-z"]),
    ]
    assert _metric_values(metrics) == (
        1, 4, 2, 4, 4, 4, 400, Decimal("20"), (("Kamyonet", 2),),
        0, ((2, 2),))


def test_every_input_permutation_has_same_semantic_output_and_metrics(
        pair_data, monkeypatch):
    start = datetime(2026, 6, 29, 9)
    sources = [
        _direct_leg("B-a", "B", 100, start, pair_data, "Kamyonet"),
        _direct_leg("B-z", "B", 100, start, pair_data, "Kamyonet"),
        _direct_leg("C-a", "C", 100, start, pair_data, "Kamyonet"),
        _direct_leg("C-z", "C", 100, start, pair_data, "Kamyonet"),
    ]

    def builder(first_token, first, second_token, second, _data):
        return (_controlled_candidate(
            first_token,
            first,
            second_token,
            second,
            delta="-10",
            route=("B", "C"),
            vtype="Kamyonet",
        ),)

    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)
    outcomes = []

    for permutation in itertools.permutations(sources):
        improved, metrics = milkrun_module.milk_run_improve(
            list(permutation), pair_data)
        outcomes.append((_literal_graph_signature(improved), metrics))

    assert all(outcome == outcomes[0] for outcome in outcomes)
    signature, metrics = outcomes[0]
    assert [(leg[8], leg[9], leg[2], leg[3], leg[1]) for leg in signature] == [
        (1, 0, "O", "B", "Kamyonet"),
        (2, 0, "O", "B", "Kamyonet"),
        (1, 1, "B", "C", "Kamyonet"),
        (2, 1, "B", "C", "Kamyonet"),
    ]
    assert _metric_values(metrics) == (
        1, 4, 2, 4, 4, 4, 400, Decimal("20"), (("Kamyonet", 2),),
        0, ((2, 2),))


def test_duplicate_semantic_sources_preserve_multiplicity(
        pair_data, monkeypatch):
    start = datetime(2026, 6, 29, 9)
    first_b = _direct_leg(
        "same-b", "B", 100, start, pair_data, "Kamyonet")
    second_b = copy.deepcopy(first_b)
    first_c = _direct_leg(
        "same-c", "C", 100, start, pair_data, "Kamyonet")
    second_c = copy.deepcopy(first_c)
    sources = [first_b, second_b, first_c, second_c]
    assert first_b == second_b and first_b is not second_b
    assert first_b.items[0][0] is not second_b.items[0][0]
    assert first_c == second_c and first_c is not second_c

    def owned_shallow_graph(value):
        return [
            replace(leg, items=list(leg.items), item_ids=list(leg.item_ids))
            for leg in value
        ]

    def builder(first_token, first, second_token, second, _data):
        return (_controlled_candidate(
            first_token,
            first,
            second_token,
            second,
            delta="-10",
        ),)

    monkeypatch.setattr(milkrun_module, "deepcopy", owned_shallow_graph)
    monkeypatch.setattr(milkrun_module, "_build_pair_candidates", builder)
    semantic_outcomes = []

    for permutation in itertools.permutations(sources):
        first_input_b = next(leg for leg in permutation if leg.dest == "B")
        first_input_c = next(leg for leg in permutation if leg.dest == "C")
        improved, metrics = milkrun_module.milk_run_improve(
            list(permutation), pair_data)
        chain_one = _new_chain_groups(improved)[1]
        chain_one_parts = [part for part, _desi in chain_one[0].items]
        assert any(part is first_input_b.items[0][0]
                   for part in chain_one_parts)
        assert any(part is first_input_c.items[0][0]
                   for part in chain_one_parts)
        assert len(improved) == 4
        assert sorted(leg.chain_id for leg in improved) == [1, 1, 2, 2]
        assert metrics.parts_consolidated == 4
        assert metrics.desi_consolidated == 400
        semantic_outcomes.append(
            (_literal_graph_signature(improved), metrics))

    assert all(outcome == semantic_outcomes[0]
               for outcome in semantic_outcomes)


def test_full_horizon_chain_stage_accepts_stage1_baseline(
        record_property):
    data = load_all(DATA_DIR)
    horizon_start = date(2026, 6, 29)
    horizon_end = date(2026, 7, 5)
    forecast = to_forecast_frame(forecast_horizon(
        data.demand, horizon_start, horizon_end))
    forecast_before = forecast.copy(deep=True)
    forecast_fingerprint_before = forecast_fingerprint(forecast)
    days = [
        horizon_start + timedelta(days=offset)
        for offset in range(7)
    ]
    source = build_plan(data, prepare_frame(forecast), days)
    stage1 = run_same_lane_stage(source, forecast, data)
    baseline = stage1.selected
    baseline_before = copy.deepcopy(baseline)
    baseline_legs = baseline.legs
    baseline_frame = baseline.plan_frame
    baseline_result = baseline.result

    stage2_started = time.perf_counter()
    decision = milkrun_module.run_milk_run_stage(
        baseline, forecast, data)
    stage2_runtime = time.perf_counter() - stage2_started

    candidate = decision.candidate
    candidate_total = Decimal(str(candidate.result.total_cost))
    record_property("stage2_total_tl", str(candidate_total))
    record_property("stage2_saving_tl", str(decision.saving_tl))
    record_property("stage2_runtime_seconds", f"{stage2_runtime:.6f}")
    for metric_field in fields(milkrun_module.MilkRunMetrics):
        record_property(
            metric_field.name,
            str(getattr(decision.metrics, metric_field.name)),
        )

    expected_forecast_ids = {
        f"D{number:05d}" for number in range(1, 4047)
    }
    assert (
        len(forecast),
        forecast["Talep ID"].nunique(),
        int(forecast["Tahmin Edilen Desi"].sum()),
    ) == (4046, 4046, 4977975)
    assert set(forecast["Talep ID"].astype(str)) == expected_forecast_ids
    assert forecast_fingerprint(forecast) == forecast_fingerprint_before
    pd.testing.assert_frame_equal(forecast, forecast_before)

    assert stage1.accepted is True
    assert Decimal(str(baseline.result.total_cost)) == Decimal(
        "14680184.845833339")
    baseline_routes = physical_routes(baseline.legs)
    baseline_metrics = summarize_evaluation(baseline, data)
    assert len(baseline.legs) == len(baseline_routes) == 1092
    assert all(leg.chain_id is None for leg in baseline.legs)
    assert len(baseline.plan_frame) == 3167
    assert baseline.result.violations == []
    assert baseline_metrics == PlanMetrics(
        vehicle_cost=Decimal("12510401.245833337"),
        sla_penalty=Decimal("2169783.600000002"),
        total_cost=Decimal("14680184.845833339"),
        rented_legs=126,
        spot_legs=966,
        vehicle_mix=(
            ("Hafif Kamyon", 24),
            ("Kamyon", 196),
            ("Kamyonet", 773),
            ("Tır", 99),
        ),
        average_spot_fill=Fraction(30735517, 54096000),
        spot_below_30_percent=296,
        violations=0,
    )

    assert decision.baseline is baseline
    assert decision.accepted is True
    assert decision.selected is candidate
    assert decision.saving_tl >= Decimal("1.00")
    assert candidate_total < Decimal(str(baseline.result.total_cost))
    assert candidate.result.violations == []
    require_plan_total(candidate.plan_frame, candidate.result.total_cost)

    assert baseline.legs is baseline_legs
    assert baseline.plan_frame is baseline_frame
    assert baseline.result is baseline_result
    assert baseline.legs == baseline_before.legs
    pd.testing.assert_frame_equal(
        baseline.plan_frame, baseline_before.plan_frame)
    assert baseline.result.vehicle_cost == baseline_before.result.vehicle_cost
    assert baseline.result.sla_penalty == baseline_before.result.sla_penalty
    assert baseline.result.total_cost == baseline_before.result.total_cost
    assert baseline.result.violations == baseline_before.result.violations
    pd.testing.assert_frame_equal(
        baseline.result.per_vehicle, baseline_before.result.per_vehicle)
    pd.testing.assert_frame_equal(
        baseline.result.per_demand, baseline_before.result.per_demand)
    assert baseline.notes == baseline_before.notes
    assert forecast_fingerprint(forecast) == forecast_fingerprint_before
    pd.testing.assert_frame_equal(forecast, forecast_before)

    routes = physical_routes(candidate.legs)
    chains = [route for route in routes if route[0].chain_id is not None]
    standalone_routes = [
        route for route in routes if route[0].chain_id is None
    ]
    chain_segments = sum(len(route) for route in chains)
    assert chains
    assert len(candidate.legs) == 1092
    assert sum(len(route) for route in routes) == 1092
    assert len(standalone_routes) == 1092 - chain_segments
    assert len(routes) == len(standalone_routes) + len(chains)
    assert all(
        2 <= len(route) <= milkrun_module.MAX_CHAIN_STOPS
        for route in chains
    )
    assert any(len(route) > 2 for route in chains)
    assert all(
        [leg.chain_seq for leg in route] == list(range(len(route)))
        for route in chains
    )
    assert all(
        len({leg.kind for leg in route}) == 1
        and route[0].kind == "Spot"
        and len({leg.vtype for leg in route}) == 1
        and route[0].vtype != "Tır"
        for route in chains
    )
    assert all(
        route[index].dest == route[index + 1].origin
        for route in chains
        for index in range(len(route) - 1)
    )
    assert all(
        len({leg.dest for leg in route}) == len(route)
        for route in chains
    )
    stage1_final_cargo_date = max(
        leg.unload_end.date() for leg in baseline.legs if leg.items)
    assert all(
        route[-1].unload_end.date() <= stage1_final_cargo_date
        for route in chains
    )
    assert not any(
        route[0].kind == "Kiralık" or route[0].vtype == "Tır"
        for route in chains
    )

    physical_metrics = summarize_evaluation(candidate, data)
    physical_mix = tuple(sorted(Counter(
        route[0].vtype for route in routes).items()))
    physical_rented = sum(
        route[0].kind == "Kiralık" for route in routes)
    physical_spot = sum(route[0].kind == "Spot" for route in routes)
    assert physical_metrics.rented_legs == physical_rented == 126
    # Every chain replaces its k source vehicles with one physical vehicle.
    assert physical_metrics.spot_legs == physical_spot == (
        966 - (chain_segments - len(chains)))
    assert physical_metrics.vehicle_mix == physical_mix
    assert physical_metrics.violations == 0
    record_property("stage2_physical_routes", str(len(routes)))
    record_property("stage2_rented_routes", str(physical_rented))
    record_property("stage2_spot_routes", str(physical_spot))
    record_property("stage2_vehicle_mix", str(physical_mix))
    record_property(
        "stage2_average_spot_fill",
        (f"{physical_metrics.average_spot_fill.numerator}/"
         f"{physical_metrics.average_spot_fill.denominator}"),
    )
    record_property(
        "stage2_spot_below_30_percent",
        str(physical_metrics.spot_below_30_percent),
    )

    def item_key(part, desi):
        return (
            part.base_id,
            part.part_id,
            part.ready,
            part.deadline,
            part.carried_before,
            part.dest,
            Decimal(str(part.desi)),
            Decimal(str(desi)),
        )

    baseline_inventory = Counter(
        item_key(part, desi)
        for leg in baseline.legs
        for part, desi in leg.items
    )
    baseline_part_occurrences = Counter(
        id(part)
        for leg in baseline.legs
        for part, _desi in leg.items
    )
    assert baseline_part_occurrences
    assert set(baseline_part_occurrences.values()) == {1}

    flows = analyze_leg_flows(candidate.legs)
    loaded_items = [
        item for flow in flows for item in flow.loaded
    ]
    unloaded_items = [
        (leg, item)
        for leg, flow in zip(candidate.legs, flows)
        for item in flow.unloaded
    ]
    loaded_counts = Counter(id(part) for part, _desi in loaded_items)
    unloaded_counts = Counter(
        id(part) for _leg, (part, _desi) in unloaded_items)
    assert loaded_counts
    assert set(loaded_counts.values()) == {1}
    assert set(unloaded_counts.values()) == {1}
    assert loaded_counts == unloaded_counts
    assert all(
        leg.dest == part.dest
        for leg, (part, _desi) in unloaded_items
    )
    loaded_inventory = Counter(
        item_key(part, desi) for part, desi in loaded_items)
    unloaded_inventory = Counter(
        item_key(part, desi)
        for _leg, (part, desi) in unloaded_items
    )
    assert loaded_inventory == baseline_inventory
    assert unloaded_inventory == baseline_inventory

    # A Part keeps its exact identity and desi on every segment it rides.
    for route in chains:
        for previous, following in zip(route, route[1:]):
            for later_part, later_desi in following.items:
                identity_matches = [
                    earlier_desi
                    for earlier_part, earlier_desi in previous.items
                    if earlier_part is later_part
                ]
                assert len(identity_matches) == 1
                assert Decimal(str(identity_matches[0])) == Decimal(
                    str(later_desi))

    baseline_occurrences = Counter(
        id(part)
        for leg in baseline.legs
        for part, _desi in leg.items
    )

    def source_eligible(leg):
        if (
            not leg.items
            or leg.kind != "Spot"
            or leg.vtype == "Tır"
            or leg.chain_id is not None
        ):
            return False
        for part, desi in leg.items:
            exact_desi = Decimal(str(desi))
            if (
                part.dest != leg.dest
                or baseline_occurrences[id(part)] != 1
                or not exact_desi.is_finite()
                or exact_desi <= 0
                or exact_desi != exact_desi.to_integral_value()
                or exact_desi != Decimal(str(part.desi))
                or part.ready > leg.load_start
            ):
                return False
        return True

    eligible_sources = [
        leg for leg in baseline.legs if source_eligible(leg)
    ]
    source_groups = {}
    for leg in eligible_sources:
        source_groups.setdefault((leg.origin, leg.load_start), []).append(leg)
    considered_groups = [
        group
        for group in source_groups.values()
        if len(group) >= 2 and len({leg.dest for leg in group}) >= 2
    ]
    actual_pairs = sum(
        first.dest != second.dest
        for group in considered_groups
        for first, second in itertools.combinations(group, 2)
    )
    assert decision.metrics.groups_considered == len(considered_groups)
    assert decision.metrics.pairs_evaluated == actual_pairs
    assert decision.metrics.chains_accepted == len(chains)
    assert decision.metrics.source_vehicles_replaced == chain_segments
    assert decision.metrics.segments_created == chain_segments
    assert decision.metrics.chain_type_mix == tuple(sorted(Counter(
        route[0].vtype for route in chains).items()))
    assert decision.metrics.chain_size_mix == tuple(sorted(Counter(
        len(route) for route in chains).items()))

    chain_initial_items = []
    for route in chains:
        first_segment = route[0]
        items_by_destination = {}
        for item in first_segment.items:
            items_by_destination.setdefault(item[0].dest, []).append(item)
        assert set(items_by_destination) == {leg.dest for leg in route}
        # Each later segment carries exactly the parts still undelivered, so
        # nothing is handled twice and nothing is reloaded at a hub.
        for position, segment in enumerate(route):
            expected_items = [
                item
                for later in route[position:]
                for item in items_by_destination[later.dest]
            ]
            assert Counter(
                item_key(part, desi) for part, desi in segment.items
            ) == Counter(
                item_key(part, desi) for part, desi in expected_items
            )
        chain_initial_items.extend(first_segment.items)

    assert len({id(part) for part, _desi in chain_initial_items}) == len(
        chain_initial_items)
    chain_inventory = Counter(
        item_key(part, desi) for part, desi in chain_initial_items)
    assert chain_inventory <= baseline_inventory
    consolidated_desi = sum(
        (Decimal(str(desi)) for _part, desi in chain_initial_items),
        Decimal("0"),
    )
    assert consolidated_desi == consolidated_desi.to_integral_value()
    assert decision.metrics.parts_consolidated == len(chain_initial_items)
    assert decision.metrics.desi_consolidated == int(consolidated_desi)
    assert decision.metrics.local_saving_tl > Decimal("0")


# ---------------------------------------------------------------------------
# Stage 2b: deterministic k-stop (three-destination) milk-run chains.
# Jury Q&A 11.1 permits a Spot vehicle to call at more than one transfer
# centre in one run; rented vehicles may not.
# ---------------------------------------------------------------------------

@pytest.fixture
def triple_data():
    """Four transfer centres where exactly one stop order O->B->C->D exists."""
    vehicles = {
        name: VehicleType(name, capacity, rental_hourly, rental_per_km,
                          spot_hourly, spot_per_km)
        for name, (capacity, rental_hourly, rental_per_km,
                   spot_hourly, spot_per_km) in VEHICLE_VALUES.items()
    }
    lanes = {
        ("O", "B"): Lane("O", "B", 100, _hours(60), 0),
        ("O", "C"): Lane("O", "C", 120, _hours(70), 0),
        ("O", "D"): Lane("O", "D", 150, _hours(90), 0),
        ("B", "C"): Lane("B", "C", 30, _hours(20), 0),
        ("C", "D"): Lane("C", "D", 50, _hours(30), 0),
    }
    demand = pd.DataFrame([
        {"cikis": "O", "varis": "B"},
        {"cikis": "O", "varis": "C"},
        {"cikis": "O", "varis": "D"},
    ])
    return CompetitionData(
        vehicles=vehicles,
        lanes=lanes,
        rentals=[],
        handling_cap={name: 100_000 for name in ("O", "B", "C", "D")},
        tir_cap={name: 100 for name in ("O", "B", "C", "D")},
        demand=demand,
        tms=["O", "B", "C", "D"],
    )


def _triple_sources(triple_data):
    load_start = datetime(2026, 6, 29, 9, 0)
    return (
        _lane_leg("D01", "O", "B", 1000, load_start, triple_data),
        _lane_leg("D02", "O", "C", 1200, load_start, triple_data),
        _lane_leg("D03", "O", "D", 800, load_start, triple_data),
    )


def test_three_stop_builder_prices_the_only_connected_order(triple_data):
    """Orders whose inter-stop lanes are missing are skipped, not invented."""
    to_b, to_c, to_d = _triple_sources(triple_data)
    candidates = milkrun_module._build_chain_candidates(
        (7, 3, 5), (to_b, to_c, to_d), triple_data)

    assert candidates
    assert {candidate.route_destinations for candidate in candidates} == {
        ("B", "C", "D")}
    assert all(candidate.source_tokens == (3, 5, 7)
               for candidate in candidates)
    assert all(len(candidate.legs) == 3 for candidate in candidates)
    assert all([leg.chain_seq for leg in candidate.legs] == [0, 1, 2]
               for candidate in candidates)
    assert all(leg.kind == "Spot"
               for candidate in candidates for leg in candidate.legs)


def test_three_stop_builder_matches_an_independent_recomputation(triple_data):
    to_b, to_c, to_d = _triple_sources(triple_data)
    candidates = milkrun_module._build_chain_candidates(
        (1, 2, 3), (to_b, to_c, to_d), triple_data)
    by_type = {candidate.vtype: candidate for candidate in candidates}
    candidate = by_type["Kamyonet"]
    first, second, third = candidate.legs

    load_start = to_b.load_start
    dep1 = load_start + timedelta(minutes=handling_minutes(3000))
    arr1 = dep1 + timedelta(minutes=travel_minutes(1.0))
    unload_end1 = arr1 + timedelta(minutes=handling_minutes(1000))
    arr2 = unload_end1 + timedelta(minutes=travel_minutes(20 / 60))
    unload_end2 = arr2 + timedelta(minutes=handling_minutes(1200))
    arr3 = unload_end2 + timedelta(minutes=travel_minutes(30 / 60))
    unload_end3 = arr3 + timedelta(minutes=handling_minutes(800))

    assert (first.origin, first.dest) == ("O", "B")
    assert (second.origin, second.dest) == ("B", "C")
    assert (third.origin, third.dest) == ("C", "D")
    assert (first.load_start, first.dep, first.arr, first.unload_end) == (
        load_start, dep1, arr1, unload_end1)
    assert (second.load_start, second.dep, second.arr, second.unload_end) == (
        unload_end1, unload_end1, arr2, unload_end2)
    assert (third.load_start, third.dep, third.arr, third.unload_end) == (
        unload_end2, unload_end2, arr3, unload_end3)

    # Cargo that stays onboard is never handled at an intermediate stop, so
    # each segment carries exactly the parts still to be delivered.
    assert first.items == list(to_b.items) + list(to_c.items) + list(
        to_d.items)
    assert second.items == list(to_c.items) + list(to_d.items)
    assert third.items == list(to_d.items)

    expected_vehicle = _expected_spot_cost(
        "Kamyonet", load_start, unload_end3, 100 + 30 + 50, triple_data)
    expected_sla = (
        _expected_sla(to_b.items, unload_end1)
        + _expected_sla(to_c.items, unload_end2)
        + _expected_sla(to_d.items, unload_end3)
    )
    expected_old = sum(
        (_expected_direct_total(leg, triple_data)
         for leg in (to_b, to_c, to_d)),
        Decimal("0"),
    )

    # The whole physical route is charged exactly once, on segment 0.
    assert Decimal(str(first.cost)) == Decimal(str(float(expected_vehicle)))
    assert second.cost == 0.0 and third.cost == 0.0
    assert candidate.delta_tl == (
        expected_vehicle + expected_sla - expected_old)
    assert candidate.delta_tl < Decimal("0")


def test_three_stop_builder_rejects_capacity_and_duplicate_destinations(
        triple_data):
    to_b, to_c, to_d = _triple_sources(triple_data)
    oversized = _lane_leg(
        "D04", "O", "D", 11_000, to_d.load_start, triple_data)
    assert milkrun_module._build_chain_candidates(
        (1, 2, 3), (to_b, to_c, oversized), triple_data) == ()

    duplicate = _lane_leg("D05", "O", "B", 500, to_b.load_start, triple_data)
    assert milkrun_module._build_chain_candidates(
        (1, 2, 3), (to_b, to_c, duplicate), triple_data) == ()

    later = _lane_leg(
        "D06", "O", "D", 800,
        to_d.load_start + timedelta(hours=1), triple_data)
    assert milkrun_module._build_chain_candidates(
        (1, 2, 3), (to_b, to_c, later), triple_data) == ()


def test_milk_run_improve_accepts_a_three_stop_chain(triple_data):
    sources = list(_triple_sources(triple_data))
    improved, metrics = milkrun_module.milk_run_improve(sources, triple_data)

    chains = _new_chain_groups(improved)
    assert len(chains) == 1
    route = next(iter(chains.values()))
    assert [leg.chain_seq for leg in route] == [0, 1, 2]
    assert [(leg.origin, leg.dest) for leg in route] == [
        ("O", "B"), ("B", "C"), ("C", "D")]
    assert len({leg.vtype for leg in route}) == 1
    assert all(leg.kind == "Spot" for leg in route)

    assert metrics.chains_accepted == 1
    assert metrics.source_vehicles_replaced == 3
    assert metrics.segments_created == 3
    assert metrics.chain_size_mix == ((3, 1),)
    assert metrics.triples_evaluated == 1
    assert metrics.pairs_evaluated == 3
    assert metrics.parts_consolidated == 3
    assert metrics.desi_consolidated == 3000
    assert metrics.local_saving_tl > Decimal("0")


def test_max_chain_stops_bounds_the_enumeration(triple_data, monkeypatch):
    """Lowering the cap to two forbids any three-stop chain deterministically."""
    monkeypatch.setattr(milkrun_module, "MAX_CHAIN_STOPS", 2)
    sources = list(_triple_sources(triple_data))
    improved, metrics = milkrun_module.milk_run_improve(sources, triple_data)

    chains = _new_chain_groups(improved)
    assert all(len(route) == 2 for route in chains.values())
    assert metrics.triples_evaluated == 0
    assert metrics.chain_size_mix in ((), ((2, 1),))


def test_chain_flows_and_topology_hold_for_three_stops(triple_data):
    sources = list(_triple_sources(triple_data))
    improved, _metrics = milkrun_module.milk_run_improve(
        sources, triple_data)

    routes = physical_routes(improved)
    chain_routes = [r for r in routes if r[0].chain_id is not None]
    assert len(chain_routes) == 1
    route = chain_routes[0]
    assert all(route[i].dest == route[i + 1].origin
               for i in range(len(route) - 1))

    flows = analyze_leg_flows(improved)
    by_leg = {id(leg): flow for leg, flow in zip(improved, flows)}
    first, second, third = route
    # Everything is loaded once at the origin and nothing is reloaded later.
    assert len(by_leg[id(first)].loaded) == 3
    assert by_leg[id(second)].loaded == ()
    assert by_leg[id(third)].loaded == ()
    # Exactly one destination is served per stop.
    assert len(by_leg[id(first)].unloaded) == 1
    assert len(by_leg[id(second)].unloaded) == 1
    assert len(by_leg[id(third)].unloaded) == 1
    assert len(by_leg[id(first)].carried) == 2
    assert len(by_leg[id(second)].carried) == 1
    assert by_leg[id(third)].carried == ()
