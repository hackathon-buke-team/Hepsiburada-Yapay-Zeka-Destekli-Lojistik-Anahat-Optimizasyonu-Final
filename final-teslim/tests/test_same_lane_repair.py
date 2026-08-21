from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import permutations

import pandas as pd
import pytest

import src.repair as repair_module
from src.candidates import Part
from src.data import CompetitionData, Lane, VehicleType
from src.evaluation import PlanEvaluation
from src.optimize import PlannedLeg, build_plan, prepare_frame
from src.repair import (Stage1Decision, _ReceiverProposal, _receiver_proposal,
                        _recompute_receiver, _sla_penalty_tl,
                        _vehicle_cost_tl, run_same_lane_stage)
from src.schemas import FORECAST_COLS
from src.simulator import SimResult


VEHICLE_VALUES = {
    "Tır": (22400, 291.6666666666667, 13, 487.5, 25),
    "Kamyon": (12000, 208.33333333333334, 10, 318.25, 21),
    "Hafif Kamyon": (7200, 208.33333333333334, 10, 364.5833333333333, 20),
    "Kamyonet": (5600, 156.25, 6, 197.91666666666666, 18),
}


@pytest.fixture
def data():
    vehicles = {
        name: VehicleType(name, capacity, rental_hourly, rental_per_km,
                          spot_hourly, spot_per_km)
        for name, (capacity, rental_hourly, rental_per_km,
                   spot_hourly, spot_per_km) in VEHICLE_VALUES.items()
    }
    hours = {name: 1.0 for name in vehicles}
    lanes = {
        (origin, dest): Lane(origin, dest, 60, dict(hours), 1)
        for origin, dest in (("A", "B"), ("B", "A"))
    }
    return CompetitionData(
        vehicles=vehicles,
        lanes=lanes,
        rentals=[],
        handling_cap={"A": 100000, "B": 100000},
        tir_cap={"A": 100, "B": 100},
        demand=pd.DataFrame(),
        tms=["A", "B"],
    )


def _part(part_id, desi, ready, *, deadline=None, base_id=None,
          carried_before=False, dest="B"):
    return Part(
        part_id=part_id,
        base_id=part_id if base_id is None else base_id,
        desi=desi,
        ready=ready,
        deadline=deadline or ready + timedelta(days=1),
        carried_before=carried_before,
        dest=dest,
    )


def _leg(items, *, kind="Spot", vtype="Kamyonet", load_start,
         dep, arr, unload_end, vehicle_id=None, item_ids=None,
         origin="A", dest="B", chain_id=None, chain_seq=0):
    return PlannedLeg(
        kind=kind,
        vtype=vtype,
        origin=origin,
        dest=dest,
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=unload_end,
        items=list(items),
        cost=-1.0,
        penalty=-1.0,
        vehicle_id=vehicle_id,
        item_ids=[] if item_ids is None else list(item_ids),
        chain_id=chain_id,
        chain_seq=chain_seq,
    )


def _valid_leg(items, *, load_start, kind="Spot", vtype="Kamyonet",
               vehicle_id=None, origin="A", dest="B", chain_id=None,
               chain_seq=0):
    total = sum(desi for _part_value, desi in items)
    handling = (total + 99) // 100 if total > 0 else 0
    dep = load_start + timedelta(minutes=handling)
    arr = dep + timedelta(hours=1)
    unload_end = arr + timedelta(minutes=handling)
    return _leg(
        items,
        kind=kind,
        vtype=vtype,
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=unload_end,
        vehicle_id=vehicle_id,
        origin=origin,
        dest=dest,
        chain_id=chain_id,
        chain_seq=chain_seq,
    )


def _leg_signature(leg):
    part_keys = tuple(sorted(
        (
            part.base_id,
            part.part_id,
            part.ready,
            part.deadline,
            part.carried_before,
            part.dest or "",
            Decimal(str(desi)),
        )
        for part, desi in leg.items
    ))
    return (
        leg.kind != "Kiralık",
        leg.dep,
        leg.origin,
        leg.dest,
        leg.vtype,
        leg.load_start,
        leg.arr,
        leg.unload_end,
        leg.chain_id is None,
        -1 if leg.chain_id is None else leg.chain_id,
        leg.chain_seq,
        part_keys,
    )


def _semantic_signature(legs):
    return tuple(sorted(_leg_signature(leg) for leg in legs))


def _assert_zero_moves(metrics):
    assert (
        metrics.moves_accepted,
        metrics.parts_moved,
        metrics.desi_moved,
        metrics.spot_legs_removed,
        metrics.local_saving_tl,
    ) == (0, 0, 0, 0, Decimal("0"))


def _stage_evaluation(total_cost, *, legs=None, violations=()):
    return PlanEvaluation(
        legs=[] if legs is None else legs,
        plan_frame=pd.DataFrame(),
        result=SimResult(
            vehicle_cost=total_cost,
            sla_penalty=Decimal("0"),
            total_cost=total_cost,
            violations=list(violations),
            per_vehicle=pd.DataFrame(),
            per_demand=pd.DataFrame(),
        ),
        notes=(),
    )


def _controlled_stage(monkeypatch, baseline, candidate):
    evaluations = iter((baseline, candidate))
    metrics = repair_module.RepairMetrics(
        donors_considered=0,
        moves_accepted=0,
        parts_moved=0,
        desi_moved=0,
        spot_legs_removed=0,
        local_saving_tl=Decimal("0"),
    )
    monkeypatch.setattr(
        repair_module,
        "evaluate_legs",
        lambda legs, forecast, data, *, fix: next(evaluations),
    )
    monkeypatch.setattr(
        repair_module,
        "repair_same_lane",
        lambda legs, data: (candidate.legs, metrics),
    )
    decision = run_same_lane_stage([], pd.DataFrame(), object())
    return decision, metrics


def test_baseline_evaluated_before_repair(data, monkeypatch):
    source = [object()]
    forecast = pd.DataFrame()
    baseline = _stage_evaluation(Decimal("100"), legs=[object()])
    repaired = [object()]
    candidate = _stage_evaluation(Decimal("90"), legs=repaired)
    metrics = repair_module.RepairMetrics(
        donors_considered=1,
        moves_accepted=1,
        parts_moved=1,
        desi_moved=100,
        spot_legs_removed=1,
        local_saving_tl=Decimal("10"),
    )
    evaluations = iter((baseline, candidate))
    events = []

    def tracking_evaluate(stage_legs, forecast_frame, competition_data, *, fix):
        assert forecast_frame is forecast
        assert competition_data is data
        events.append(("evaluate", stage_legs, fix))
        return next(evaluations)

    def tracking_repair(stage_legs, competition_data):
        assert competition_data is data
        events.append(("repair", stage_legs))
        return repaired, metrics

    monkeypatch.setattr(repair_module, "evaluate_legs", tracking_evaluate)
    monkeypatch.setattr(repair_module, "repair_same_lane", tracking_repair)

    decision = run_same_lane_stage(source, forecast, data)

    assert isinstance(decision, Stage1Decision)
    assert [event[0] for event in events] == [
        "evaluate", "repair", "evaluate"]
    assert events[0][1] is source
    assert events[0][2] is True
    assert events[1][1] is baseline.legs
    assert events[2][1] is repaired
    assert events[2][2] is True


def test_global_violation_rolls_back(monkeypatch):
    baseline = _stage_evaluation(Decimal("100"))
    candidate = _stage_evaluation(
        Decimal("50"), violations=("candidate violation",))

    decision, metrics = _controlled_stage(monkeypatch, baseline, candidate)

    assert decision.baseline is baseline
    assert decision.candidate is candidate
    assert decision.repair_metrics is metrics
    assert decision.saving_tl == Decimal("50")
    assert decision.accepted is False
    assert decision.selected is baseline


def test_sub_one_tl_rolls_back(monkeypatch):
    baseline = _stage_evaluation(Decimal("100"))
    candidate = _stage_evaluation(Decimal("99.000001"))

    decision, _metrics = _controlled_stage(monkeypatch, baseline, candidate)

    assert decision.saving_tl == Decimal("0.999999")
    assert decision.accepted is False
    assert decision.selected is baseline


def test_stage_input_nonmutation(data):
    day = datetime(2026, 6, 29).date()
    forecast = pd.DataFrame([{
        "Talep ID": "D00001",
        "Tarih": "29.06.2026",
        "Talep Tamamlama Saati": "09:00",
        "Çıkış Transfer Merkezi": "A",
        "Varış Transfer Merkezi": "B",
        "Tahmin Edilen Desi": 100,
    }], columns=FORECAST_COLS)
    source = build_plan(data, prepare_frame(forecast), [day])
    source_before = deepcopy(source)
    forecast_before = forecast.copy(deep=True)

    run_same_lane_stage(source, forecast, data)

    assert source == source_before
    pd.testing.assert_frame_equal(forecast, forecast_before)


def test_spot_retimes_to_latest_ready(data):
    morning = datetime(2026, 6, 29, 9)
    evening = datetime(2026, 6, 29, 17)
    receiver_part = _part("receiver", 1000, morning)
    moved_part = _part("donor", 500, evening)
    receiver = _leg(
        [(receiver_part, 1000)],
        load_start=morning,
        dep=datetime(2026, 6, 29, 9, 10),
        arr=datetime(2026, 6, 29, 10, 10),
        unload_end=datetime(2026, 6, 29, 10, 20),
        vehicle_id="S0001",
        item_ids=["old-item-id"],
    )
    donor = _leg(
        [(moved_part, 500)],
        load_start=evening,
        dep=datetime(2026, 6, 29, 17, 5),
        arr=datetime(2026, 6, 29, 18, 5),
        unload_end=datetime(2026, 6, 29, 18, 10),
    )

    updated = _recompute_receiver(receiver, donor.items, data)

    assert updated is not None
    assert updated.load_start == datetime(2026, 6, 29, 17)
    assert updated.dep == datetime(2026, 6, 29, 17, 15)
    assert updated.arr == datetime(2026, 6, 29, 18, 15)
    assert updated.unload_end == datetime(2026, 6, 29, 18, 30)
    assert updated.items == [(receiver_part, 1000), (moved_part, 500)]
    assert updated.item_ids == []
    assert updated.vehicle_id == "S0001"
    assert updated.cost == 1376.875
    assert updated.penalty == 0.0

    proposal = _receiver_proposal(donor, receiver, data)
    assert proposal == _ReceiverProposal(
        receiver=updated,
        delta_tl=Decimal("-1277.91666666666666"),
        parts_moved=1,
        desi_moved=500,
    )


def test_rented_preserves_valid_departure(data):
    receiver_part = _part("receiver", 1000, datetime(2026, 6, 29, 9))
    moved_part = _part("donor", 500, datetime(2026, 6, 29, 16, 40))
    receiver = _leg(
        [(receiver_part, 1000)],
        kind="Kiralık",
        load_start=datetime(2026, 6, 29, 16, 50),
        dep=datetime(2026, 6, 29, 17),
        arr=datetime(2026, 6, 29, 18),
        unload_end=datetime(2026, 6, 29, 18, 10),
    )

    updated = _recompute_receiver(receiver, [(moved_part, 500)], data)

    assert updated is not None
    assert updated.load_start == datetime(2026, 6, 29, 16, 45)
    assert updated.dep == receiver.dep
    assert updated.arr == datetime(2026, 6, 29, 18)
    assert updated.unload_end == datetime(2026, 6, 29, 18, 15)


def test_rented_delays_invalid_departure(data):
    receiver_part = _part("receiver", 1000, datetime(2026, 6, 29, 9))
    moved_part = _part("donor", 500, datetime(2026, 6, 29, 17, 5))
    receiver = _leg(
        [(receiver_part, 1000)],
        kind="Kiralık",
        load_start=datetime(2026, 6, 29, 16, 50),
        dep=datetime(2026, 6, 29, 17),
        arr=datetime(2026, 6, 29, 18),
        unload_end=datetime(2026, 6, 29, 18, 10),
    )

    updated = _recompute_receiver(receiver, [(moved_part, 500)], data)

    assert updated is not None
    assert updated.load_start == datetime(2026, 6, 29, 17, 5)
    assert updated.dep == datetime(2026, 6, 29, 17, 20)
    assert updated.arr == datetime(2026, 6, 29, 18, 20)
    assert updated.unload_end == datetime(2026, 6, 29, 18, 35)


def test_rented_receiver_rejects_departure_day_change(data):
    receiver_ready = datetime(2026, 6, 29, 9)
    donor_ready = datetime(2026, 6, 30, 0, 1)
    receiver = _leg(
        [(_part("receiver", 1000, receiver_ready), 1000)],
        kind="Kiralık",
        load_start=datetime(2026, 6, 29, 23, 45),
        dep=datetime(2026, 6, 29, 23, 55),
        arr=datetime(2026, 6, 30, 0, 55),
        unload_end=datetime(2026, 6, 30, 1, 5),
    )
    donor = _valid_leg(
        [(_part("donor", 100, donor_ready), 100)],
        load_start=donor_ready,
    )

    updated = _recompute_receiver(receiver, donor.items, data)

    assert updated is not None
    assert updated.dep.date() != receiver.dep.date()
    assert _receiver_proposal(donor, receiver, data) is None


@pytest.mark.parametrize(
    ("kind", "vtype", "hourly", "per_km"),
    [
        ("Kiralık", "Tır", 291.6666666666667, 13),
        ("Kiralık", "Kamyon", 208.33333333333334, 10),
        ("Kiralık", "Hafif Kamyon", 208.33333333333334, 10),
        ("Kiralık", "Kamyonet", 156.25, 6),
        ("Spot", "Tır", 487.5, 25),
        ("Spot", "Kamyon", 318.25, 21),
        ("Spot", "Hafif Kamyon", 364.5833333333333, 20),
        ("Spot", "Kamyonet", 197.91666666666666, 18),
    ],
    ids=[
        "rented-tir",
        "rented-kamyon",
        "rented-hafif-kamyon",
        "rented-kamyonet",
        "spot-tir",
        "spot-kamyon",
        "spot-hafif-kamyon",
        "spot-kamyonet",
    ],
)
def test_current_kind_rates(data, kind, vtype, hourly, per_km):
    start = datetime(2026, 6, 29, 9)
    part = _part("cargo", 1500, start)
    leg = _leg(
        [(part, 1500)],
        kind=kind,
        vtype=vtype,
        load_start=start,
        dep=datetime(2026, 6, 29, 9, 15),
        arr=datetime(2026, 6, 29, 10, 15),
        unload_end=datetime(2026, 6, 29, 10, 30),
    )
    seconds = 5400
    expected = (
        Decimal(str(hourly)) * Decimal(seconds) / Decimal(3600)
        + Decimal(per_km) * Decimal(60)
    )

    actual = _vehicle_cost_tl(leg, data)

    assert actual == expected
    if kind == "Spot" and vtype == "Kamyonet":
        binary_float_expansion = (
            Decimal(hourly) * Decimal(seconds) / Decimal(3600)
            + Decimal(per_km) * Decimal(60)
        )
        assert actual != binary_float_expansion


def test_existing_receiver_sla_is_in_delta(data):
    receiver_ready = datetime(2026, 6, 29, 9)
    donor_ready = datetime(2026, 6, 29, 11)
    receiver_part = _part(
        "receiver",
        5000,
        receiver_ready,
        deadline=datetime(2026, 6, 29, 12),
    )
    donor_part = _part("donor", 100, donor_ready)
    receiver = _leg(
        [(receiver_part, 5000)],
        load_start=receiver_ready,
        dep=datetime(2026, 6, 29, 9, 50),
        arr=datetime(2026, 6, 29, 10, 50),
        unload_end=datetime(2026, 6, 29, 11, 40),
    )
    donor = _leg(
        [(donor_part, 100)],
        load_start=donor_ready,
        dep=datetime(2026, 6, 29, 11, 1),
        arr=datetime(2026, 6, 29, 12, 1),
        unload_end=datetime(2026, 6, 29, 12, 2),
    )

    updated = _recompute_receiver(receiver, donor.items, data)

    assert updated is not None
    assert updated.unload_end == datetime(2026, 6, 29, 13, 42)
    assert _sla_penalty_tl(updated) == Decimal("4000.0")
    assert (
        _vehicle_cost_tl(updated, data)
        - _vehicle_cost_tl(receiver, data)
        - _vehicle_cost_tl(donor, data)
    ) < 0
    assert _receiver_proposal(donor, receiver, data) is None


def test_capacity_rejects_whole_donor(data):
    ready = datetime(2026, 6, 29, 9)
    receiver_part = _part("receiver", 5500, ready)
    donor_part = _part("donor", 101, ready)
    receiver = _leg(
        [(receiver_part, 5500)],
        load_start=ready,
        dep=datetime(2026, 6, 29, 9, 55),
        arr=datetime(2026, 6, 29, 10, 55),
        unload_end=datetime(2026, 6, 29, 11, 50),
    )
    donor = _leg(
        [(donor_part, 101)],
        load_start=ready,
        dep=datetime(2026, 6, 29, 9, 2),
        arr=datetime(2026, 6, 29, 10, 2),
        unload_end=datetime(2026, 6, 29, 10, 4),
    )

    assert _recompute_receiver(receiver, donor.items, data) is None
    assert _receiver_proposal(donor, receiver, data) is None
    assert receiver.items == [(receiver_part, 5500)]
    assert donor.items == [(donor_part, 101)]


def test_delta_must_be_strictly_negative(data, monkeypatch):
    ready = datetime(2026, 6, 29, 9)
    receiver_part = _part("receiver", 1000, ready)
    donor_part = _part("donor", 100, ready)
    receiver = _leg(
        [(receiver_part, 1000)],
        load_start=ready,
        dep=datetime(2026, 6, 29, 9, 10),
        arr=datetime(2026, 6, 29, 10, 10),
        unload_end=datetime(2026, 6, 29, 10, 20),
        vehicle_id="receiver-old",
    )
    donor = _leg(
        [(donor_part, 100)],
        load_start=ready,
        dep=datetime(2026, 6, 29, 9, 1),
        arr=datetime(2026, 6, 29, 10, 1),
        unload_end=datetime(2026, 6, 29, 10, 2),
        vehicle_id="donor-old",
    )
    updated = replace(receiver, vehicle_id="receiver-new")
    semantic_totals = {
        "receiver-old": Decimal(10),
        "donor-old": Decimal(20),
        "receiver-new": Decimal(30),
    }

    monkeypatch.setattr(
        repair_module,
        "_recompute_receiver",
        lambda old_receiver, moved_items, competition_data: updated,
    )
    monkeypatch.setattr(
        repair_module,
        "_leg_total_tl",
        lambda leg, competition_data: semantic_totals[leg.vehicle_id],
    )

    assert repair_module._receiver_proposal(donor, receiver, data) is None


def test_donor_deleted_when_complete_move_profitable(data):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 100, ready), 100)],
        load_start=ready,
        vehicle_id="donor",
    )
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)],
        load_start=ready,
        vehicle_id="receiver",
    )

    repaired, metrics = repair_module.repair_same_lane(
        [receiver, donor], data)

    assert len(repaired) == 1
    assert [(part.part_id, desi) for part, desi in repaired[0].items] == [
        ("receiver", 1000),
        ("donor", 100),
    ]
    assert metrics.donors_considered == 1
    assert (
        metrics.moves_accepted,
        metrics.parts_moved,
        metrics.desi_moved,
        metrics.spot_legs_removed,
    ) == (1, 1, 100, 1)
    assert metrics.local_saving_tl > Decimal("0")
    assert metrics.moves_accepted == metrics.spot_legs_removed


def test_capacity_rejection_unchanged(data):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 101, ready), 101)], load_start=ready)
    receiver = _valid_leg(
        [(_part("receiver", 5500, ready), 5500)], load_start=ready)
    original_signature = _semantic_signature([receiver, donor])

    repaired, metrics = repair_module.repair_same_lane(
        [receiver, donor], data)

    assert len(repaired) == 2
    assert _semantic_signature(repaired) == original_signature
    _assert_zero_moves(metrics)


def test_rented_never_donor(data, monkeypatch):
    ready = datetime(2026, 6, 29, 9)
    rented = _valid_leg(
        [(_part("rented", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=ready,
    )
    spot = _valid_leg(
        [(_part("spot", 100, ready), 100)], load_start=ready)
    donor_kinds = []
    original_proposal = repair_module._receiver_proposal

    def recording_proposal(donor, receiver, competition_data):
        donor_kinds.append(donor.kind)
        return original_proposal(donor, receiver, competition_data)

    monkeypatch.setattr(
        repair_module, "_receiver_proposal", recording_proposal)

    repaired, metrics = repair_module.repair_same_lane(
        [spot, rented], data)

    assert donor_kinds == ["Spot"]
    assert len(repaired) == 1
    assert repaired[0].kind == "Kiralık"
    assert metrics.moves_accepted == 1


def test_readiness_invalid_trial_rejected(data):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 100, ready), 100)], load_start=ready)
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=ready,
    )
    malformed_ready = datetime(2026, 6, 29, 12)
    malformed_load = datetime(2026, 6, 29, 11)
    malformed = _leg(
        [(_part("malformed", 200, malformed_ready, dest="A"), 200)],
        kind="Kiralık",
        origin="B",
        dest="A",
        load_start=malformed_load,
        dep=malformed_load + timedelta(minutes=2),
        arr=malformed_load + timedelta(hours=1, minutes=2),
        unload_end=malformed_load + timedelta(hours=1, minutes=4),
    )
    legs = [donor, malformed, receiver]
    original_signature = _semantic_signature(legs)

    assert _receiver_proposal(donor, receiver, data) is not None

    repaired, metrics = repair_module.repair_same_lane(legs, data)

    assert _semantic_signature(repaired) == original_signature
    _assert_zero_moves(metrics)


@pytest.mark.parametrize("exclusion", ["chain", "wrong-dest", "shared"])
def test_direct_only_exclusions(data, exclusion):
    ready = datetime(2026, 6, 29, 9)
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=ready,
    )

    if exclusion == "chain":
        unsafe = _valid_leg(
            [(_part("chain", 100, ready), 100)],
            load_start=ready,
            chain_id=7,
        )
        safe = _valid_leg(
            [(_part("safe", 100, ready), 100)],
            load_start=ready + timedelta(hours=1),
        )
        legs = [safe, receiver, unsafe]
    elif exclusion == "wrong-dest":
        unsafe = _valid_leg(
            [(_part("wrong", 100, ready, dest="A"), 100)],
            load_start=ready,
        )
        legs = [receiver, unsafe]
    else:
        shared = _part("shared", 100, ready)
        first = _valid_leg([(shared, 100)], load_start=ready)
        second = _valid_leg(
            [(shared, 100)], load_start=ready + timedelta(hours=1))
        legs = [second, receiver, first]

    original_signature = _semantic_signature(legs)

    repaired, metrics = repair_module.repair_same_lane(legs, data)

    assert _semantic_signature(repaired) == original_signature
    _assert_zero_moves(metrics)
    if exclusion == "shared":
        occurrences = [
            part
            for leg in repaired
            for part, _desi in leg.items
            if part.part_id == "shared"
        ]
        assert len(occurrences) == 2
        assert occurrences[0] is occurrences[1]


def test_handling_rejection(data):
    data.handling_cap = {"A": 1000, "B": 1000}
    donor_day = datetime(2026, 6, 29, 9)
    receiver_day = datetime(2026, 6, 30, 9)
    donor = _valid_leg(
        [(_part("donor", 600, donor_day), 600)],
        load_start=donor_day,
    )
    receiver = _valid_leg(
        [(_part("receiver", 600, receiver_day), 600)],
        kind="Kiralık",
        load_start=receiver_day,
    )
    original_signature = _semantic_signature([donor, receiver])

    assert _receiver_proposal(donor, receiver, data) is not None

    repaired, metrics = repair_module.repair_same_lane(
        [receiver, donor], data)

    assert _semantic_signature(repaired) == original_signature
    _assert_zero_moves(metrics)


def test_complete_ledger_rejects_unrelated_current_type_overcapacity(data):
    ready = datetime(2026, 6, 29, 9)
    valid = _valid_leg(
        [(_part("valid", 100, ready), 100)],
        kind="Kiralık",
        vtype="Tır",
        load_start=ready,
    )
    over_capacity = _valid_leg(
        [(_part("over-capacity", 5601, ready, dest="A"), 5601)],
        vtype="Kamyonet",
        origin="B",
        dest="A",
        load_start=ready + timedelta(hours=2),
    )

    assert data.vehicles["Kamyonet"].capacity_desi == 5600
    assert data.vehicles["Hafif Kamyon"].capacity_desi > 5601
    assert not repair_module._trial_ledgers_valid(
        [valid, over_capacity], data)


def test_complete_ledger_origin_handling_uses_load_start_at_midnight(data):
    data.handling_cap = {"A": 500, "B": 100000}
    load_start = datetime(2026, 6, 29, 23, 55)
    leg = _leg(
        [(_part("origin-midnight", 1000, load_start), 1000)],
        load_start=load_start,
        dep=datetime(2026, 6, 30, 0, 5),
        arr=datetime(2026, 6, 30, 1, 5),
        unload_end=datetime(2026, 6, 30, 1, 15),
    )

    assert repair_module._trial_ledgers_valid([leg], data)


def test_complete_ledger_destination_handling_uses_arrival_at_midnight(data):
    data.handling_cap = {"A": 100000, "B": 500}
    load_start = datetime(2026, 6, 29, 22, 45)
    leg = _leg(
        [(_part("destination-midnight", 1000, load_start), 1000)],
        load_start=load_start,
        dep=datetime(2026, 6, 29, 22, 55),
        arr=datetime(2026, 6, 29, 23, 55),
        unload_end=datetime(2026, 6, 30, 0, 5),
    )

    assert repair_module._trial_ledgers_valid([leg], data)


def test_complete_ledger_tir_origin_conflict_uses_departure_date(data):
    data.tir_cap = {"A": 1, "B": 100}
    first_load = datetime(2026, 6, 29, 23, 59)
    second_load = datetime(2026, 6, 30, 0, 59)
    first = _leg(
        [(_part("first-tir", 100, first_load), 100)],
        vtype="Tır",
        load_start=first_load,
        dep=datetime(2026, 6, 30, 0),
        arr=datetime(2026, 6, 30, 1),
        unload_end=datetime(2026, 6, 30, 1, 1),
    )
    second = _leg(
        [(_part("second-tir", 100, second_load), 100)],
        vtype="Tır",
        load_start=second_load,
        dep=datetime(2026, 6, 30, 1),
        arr=datetime(2026, 6, 30, 2),
        unload_end=datetime(2026, 6, 30, 2, 1),
    )

    assert first.load_start.date() != second.load_start.date()
    assert first.dep.date() == second.dep.date()
    assert not repair_module._trial_ledgers_valid([first, second], data)


def _tir_retime_case(include_conflict):
    receiver_start = datetime(2026, 6, 29, 20)
    donor_start = datetime(2026, 6, 29, 23, 30)
    receiver = _valid_leg(
        [(_part("tir-receiver", 100, receiver_start), 100)],
        vtype="Tır",
        load_start=receiver_start,
    )
    donor = _valid_leg(
        [(_part("donor", 5000, donor_start), 5000)],
        load_start=donor_start,
    )
    legs = [receiver, donor]
    if include_conflict:
        conflict = _valid_leg(
            [],
            kind="Kiralık",
            vtype="Tır",
            load_start=datetime(2026, 6, 29, 23, 30),
        )
        legs.append(conflict)
    return donor, receiver, legs


def test_tir_arrival_day_ledger_rejection(data):
    data.tir_cap = {"A": 100, "B": 1}
    donor, receiver, legs = _tir_retime_case(include_conflict=True)
    proposal = _receiver_proposal(donor, receiver, data)

    assert proposal is not None
    assert proposal.delta_tl < Decimal("0")
    assert proposal.receiver.arr.date() != receiver.arr.date()

    conflict = next(leg for leg in legs if not leg.items)
    assert not repair_module._trial_ledgers_valid(
        [proposal.receiver, conflict], data)
    original_signature = _semantic_signature(legs)

    repaired, metrics = repair_module.repair_same_lane(legs, data)

    assert _semantic_signature(repaired) == original_signature
    _assert_zero_moves(metrics)


def test_tir_receiver_allowed_when_visits_fit(data):
    data.tir_cap = {"A": 100, "B": 1}
    donor, receiver, legs = _tir_retime_case(include_conflict=False)
    proposal = _receiver_proposal(donor, receiver, data)

    assert proposal is not None
    assert repair_module._trial_ledgers_valid([proposal.receiver], data)

    repaired, metrics = repair_module.repair_same_lane(legs, data)

    assert len(repaired) == 1
    assert repaired[0].vtype == "Tır"
    assert {part.part_id for part, _desi in repaired[0].items} == {
        "tir-receiver",
        "donor",
    }
    assert metrics.moves_accepted == 1
    assert metrics.spot_legs_removed == 1


def test_later_day_receiver(data):
    donor_day = datetime(2026, 6, 29, 9)
    receiver_day = datetime(2026, 7, 1, 9)
    donor = _valid_leg(
        [(_part("donor", 100, donor_day), 100)],
        load_start=donor_day,
    )
    receiver = _valid_leg(
        [(_part("receiver", 1000, receiver_day), 1000)],
        load_start=receiver_day,
    )

    repaired, metrics = repair_module.repair_same_lane(
        [receiver, donor], data)

    assert len(repaired) == 1
    assert repaired[0].load_start == receiver_day
    assert {part.part_id for part, _desi in repaired[0].items} == {
        "receiver",
        "donor",
    }
    assert metrics.moves_accepted == 1


def test_whole_parts_conserved_without_piece(data, monkeypatch):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [
            (_part("donor-40", 40, ready), 40),
            (_part("donor-60", 60, ready), 60),
        ],
        load_start=ready,
    )
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)], load_start=ready)

    def forbidden_piece(_part_value, _take):
        raise AssertionError("Part.piece must not be called")

    monkeypatch.setattr(Part, "piece", forbidden_piece)

    repaired, metrics = repair_module.repair_same_lane(
        [donor, receiver], data)

    assert len(repaired) == 1
    assert [(part.part_id, part.desi, desi)
            for part, desi in repaired[0].items] == [
        ("receiver", 1000, 1000),
        ("donor-40", 40, 40),
        ("donor-60", 60, 60),
    ]
    assert metrics.parts_moved == 2
    assert metrics.desi_moved == 100


def test_input_nonmutation(data):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 100, ready), 100)], load_start=ready)
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)], load_start=ready)
    legs = [receiver, donor]
    before = deepcopy(legs)
    input_parts = [part for leg in legs for part, _desi in leg.items]

    repaired, metrics = repair_module.repair_same_lane(legs, data)

    assert legs == before
    assert repaired is not legs
    assert all(output_leg is not input_leg
               for output_leg in repaired for input_leg in legs)
    assert all(output_part is not input_part
               for leg in repaired for output_part, _desi in leg.items
               for input_part in input_parts)
    assert metrics.moves_accepted == 1


def test_no_cost_increasing_move(data, monkeypatch):
    receiver_ready = datetime(2026, 6, 29, 9)
    donor_ready = datetime(2026, 6, 29, 11)
    receiver = _valid_leg(
        [(_part(
            "receiver",
            5000,
            receiver_ready,
            deadline=datetime(2026, 6, 29, 12),
        ), 5000)],
        load_start=receiver_ready,
    )
    donor = _valid_leg(
        [(_part("donor", 100, donor_ready), 100)],
        load_start=donor_ready,
    )
    updated = _recompute_receiver(receiver, donor.items, data)
    assert updated is not None
    delta = (
        repair_module._leg_total_tl(updated, data)
        - repair_module._leg_total_tl(receiver, data)
        - repair_module._leg_total_tl(donor, data)
    )
    assert delta >= Decimal("0")
    assert _receiver_proposal(donor, receiver, data) is None
    original_signature = _semantic_signature([receiver, donor])
    monkeypatch.setattr(
        repair_module,
        "_receiver_proposal",
        lambda donor_leg, receiver_leg, competition_data: _ReceiverProposal(
            receiver=updated,
            delta_tl=Decimal("0"),
            parts_moved=1,
            desi_moved=100,
        ),
    )

    repaired, metrics = repair_module.repair_same_lane(
        [donor, receiver], data)

    assert _semantic_signature(repaired) == original_signature
    _assert_zero_moves(metrics)


def test_most_negative_then_semantic_receiver(data, monkeypatch):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 100, ready), 100)], load_start=ready)
    early = _leg(
        [(_part("early", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=datetime(2026, 6, 29, 9, 50),
        dep=datetime(2026, 6, 29, 10),
        arr=datetime(2026, 6, 29, 11),
        unload_end=datetime(2026, 6, 29, 11, 10),
    )
    late = _leg(
        [(_part("late", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=datetime(2026, 6, 29, 10, 50),
        dep=datetime(2026, 6, 29, 11),
        arr=datetime(2026, 6, 29, 12),
        unload_end=datetime(2026, 6, 29, 12, 10),
    )
    controlled_deltas = {
        "early": Decimal("-10"),
        "late": Decimal("-20"),
    }
    original_proposal = repair_module._receiver_proposal

    def controlled_proposal(donor_leg, receiver_leg, competition_data):
        proposal = original_proposal(
            donor_leg, receiver_leg, competition_data)
        if proposal is None:
            return None
        receiver_id = receiver_leg.items[0][0].part_id
        return replace(proposal, delta_tl=controlled_deltas[receiver_id])

    monkeypatch.setattr(
        repair_module, "_receiver_proposal", controlled_proposal)

    repaired, metrics = repair_module.repair_same_lane(
        [early, donor, late], data)

    chosen = next(
        leg for leg in repaired
        if any(part.part_id == "donor" for part, _desi in leg.items)
    )
    assert chosen.items[0][0].part_id == "late"
    assert metrics.local_saving_tl == Decimal("20")

    controlled_deltas["early"] = Decimal("-20")
    forward, forward_metrics = repair_module.repair_same_lane(
        [late, donor, early], data)
    reverse, reverse_metrics = repair_module.repair_same_lane(
        [early, donor, late], data)
    forward_chosen = next(
        leg for leg in forward
        if any(part.part_id == "donor" for part, _desi in leg.items)
    )

    assert forward_chosen.items[0][0].part_id == "early"
    assert _semantic_signature(forward) == _semantic_signature(reverse)
    assert forward_metrics == reverse_metrics
    assert forward_metrics.local_saving_tl == Decimal("20")


def test_changed_receiver_not_later_donor(data, monkeypatch):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 100, ready), 100)], load_start=ready)
    target = _valid_leg(
        [(_part("target", 1000, ready), 1000)], load_start=ready)
    parking = _valid_leg(
        [(_part("parking", 2000, ready), 2000)],
        kind="Kiralık",
        load_start=ready,
    )
    donor_ids = []
    original_proposal = repair_module._receiver_proposal

    def recording_proposal(donor_leg, receiver_leg, competition_data):
        donor_id = donor_leg.items[0][0].part_id
        donor_ids.append(donor_id)
        proposal = original_proposal(
            donor_leg, receiver_leg, competition_data)
        if proposal is None or donor_id != "donor":
            return proposal
        receiver_id = receiver_leg.items[0][0].part_id
        controlled = Decimal("-20" if receiver_id == "target" else "-10")
        return replace(proposal, delta_tl=controlled)

    monkeypatch.setattr(
        repair_module, "_receiver_proposal", recording_proposal)

    repaired, metrics = repair_module.repair_same_lane(
        [parking, target, donor], data)

    assert donor_ids
    assert set(donor_ids) == {"donor"}
    changed = next(
        leg for leg in repaired
        if any(part.part_id == "donor" for part, _desi in leg.items)
    )
    assert changed.items[0][0].part_id == "target"
    assert metrics.moves_accepted == 1


def test_receiver_accepts_multiple_donors(data):
    ready = datetime(2026, 6, 29, 9)
    first = _valid_leg(
        [(_part("first", 100, ready), 100)], load_start=ready)
    second = _valid_leg(
        [(_part("second", 200, ready), 200)], load_start=ready)
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=ready,
    )

    repaired, metrics = repair_module.repair_same_lane(
        [second, receiver, first], data)

    assert len(repaired) == 1
    assert repaired[0].kind == "Kiralık"
    assert [part.part_id for part, _desi in repaired[0].items] == [
        "receiver",
        "first",
        "second",
    ]
    assert (
        metrics.moves_accepted,
        metrics.parts_moved,
        metrics.desi_moved,
        metrics.spot_legs_removed,
    ) == (2, 2, 300, 2)
    assert metrics.local_saving_tl > Decimal("0")


def test_permutation_determinism(data):
    ready = datetime(2026, 6, 29, 9)
    first = _valid_leg(
        [(_part("first", 100, ready), 100)], load_start=ready)
    second = _valid_leg(
        [(_part("second", 200, ready), 200)], load_start=ready)
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=ready,
    )
    reverse = _valid_leg(
        [(_part("reverse", 300, ready, dest="A"), 300)],
        kind="Kiralık",
        origin="B",
        dest="A",
        load_start=ready + timedelta(hours=2),
    )
    legs = [reverse, second, receiver, first]
    results = []

    for ordering in permutations(legs):
        repaired, metrics = repair_module.repair_same_lane(
            list(ordering), data)
        ordered_signature = tuple(_leg_signature(leg) for leg in repaired)
        assert ordered_signature == tuple(sorted(ordered_signature))
        results.append((ordered_signature, metrics))

    assert all(result == results[0] for result in results)


def test_duplicate_semantic_occurrences_survive_every_permutation(data):
    ready = datetime(2026, 6, 29, 9)
    donor = _valid_leg(
        [(_part("donor", 100, ready), 100)], load_start=ready)
    receiver = _valid_leg(
        [(_part("receiver", 1000, ready), 1000)],
        kind="Kiralık",
        load_start=ready,
    )
    first_part = _part("duplicate", 300, ready, dest="A")
    second_part = _part("duplicate", 300, ready, dest="A")
    assert first_part is not second_part
    first_duplicate = replace(
        _valid_leg(
            [(first_part, 300)],
            kind="Kiralık",
            origin="B",
            dest="A",
            load_start=ready + timedelta(hours=2),
        ),
        cost=101.0,
        penalty=11.0,
        vehicle_id="ignored-first",
        item_ids=["ignored-item-first"],
    )
    second_duplicate = replace(
        _valid_leg(
            [(second_part, 300)],
            kind="Kiralık",
            origin="B",
            dest="A",
            load_start=ready + timedelta(hours=2),
        ),
        cost=202.0,
        penalty=22.0,
        vehicle_id="ignored-second",
        item_ids=["ignored-item-second"],
    )
    assert _leg_signature(first_duplicate) == _leg_signature(second_duplicate)

    expected_occurrences = Counter({
        ("ignored-first", ("ignored-item-first",), 101.0, 11.0): 1,
        ("ignored-second", ("ignored-item-second",), 202.0, 22.0): 1,
    })
    results = []
    for ordering in permutations(
            [donor, receiver, first_duplicate, second_duplicate]):
        repaired, metrics = repair_module.repair_same_lane(
            list(ordering), data)
        duplicate_occurrences = Counter(
            (leg.vehicle_id, tuple(leg.item_ids), leg.cost, leg.penalty)
            for leg in repaired
            if _leg_signature(leg) == _leg_signature(first_duplicate)
        )

        assert duplicate_occurrences == expected_occurrences
        results.append((_semantic_signature(repaired), metrics))

    assert all(result == results[0] for result in results)
    assert results[0][1].moves_accepted == 1
