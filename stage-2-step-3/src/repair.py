"""Same-lane proposal math and deterministic complete-ledger repair."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from src.candidates import Part
from src.evaluation import (PlanEvaluation, accepts_candidate, evaluate_legs,
                            improvement_tl)
from src.ledger import HandlingLedger, TirLedger
from src.optimize import PlannedLeg
from src.timeutil import (SLA_TL_PER_DESI_HOUR, handling_minutes, late_hours,
                          travel_minutes)


@dataclass(frozen=True)
class RepairMetrics:
    donors_considered: int
    moves_accepted: int
    parts_moved: int
    desi_moved: int
    spot_legs_removed: int
    local_saving_tl: Decimal


@dataclass(frozen=True)
class Stage1Decision:
    baseline: PlanEvaluation
    candidate: PlanEvaluation
    selected: PlanEvaluation
    repair_metrics: RepairMetrics
    accepted: bool
    saving_tl: Decimal


@dataclass(frozen=True)
class _ReceiverProposal:
    receiver: PlannedLeg
    delta_tl: Decimal
    parts_moved: int
    desi_moved: int


def _decimal(value) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, OverflowError, TypeError, ValueError) as error:
        raise ValueError("value must be a finite number") from error
    if not number.is_finite():
        raise ValueError("value must be a finite number")
    return number


def _desi_total(items: list[tuple[Part, int | float]]) -> Decimal:
    return sum((_decimal(desi) for _part, desi in items), Decimal("0"))


def _whole_desi(total: Decimal) -> int:
    if total != total.to_integral_value():
        raise ValueError("desi total must be a whole number")
    return int(total)


def _vehicle_cost_tl(leg: PlannedLeg, data) -> Decimal:
    vehicle = data.vehicles[leg.vtype]
    lane = data.lanes[(leg.origin, leg.dest)]
    if leg.kind == "Spot":
        hourly = vehicle.spot_hourly
        per_km = vehicle.spot_per_km
    else:
        hourly = vehicle.rental_hourly
        per_km = vehicle.rental_per_km

    seconds = int((leg.unload_end - leg.load_start).total_seconds())
    if seconds < 0:
        raise ValueError("vehicle usage duration cannot be negative")
    return (
        _decimal(hourly) * Decimal(seconds) / Decimal(3600)
        + _decimal(per_km) * Decimal(lane.km)
    )


def _sla_penalty_tl(leg: PlannedLeg) -> Decimal:
    rate = _decimal(SLA_TL_PER_DESI_HOUR)
    return sum(
        (
            _decimal(desi)
            * Decimal(late_hours(part.deadline, leg.unload_end))
            * rate
            for part, desi in leg.items
        ),
        Decimal("0"),
    )


def _leg_total_tl(leg: PlannedLeg, data) -> Decimal:
    return _vehicle_cost_tl(leg, data) + _sla_penalty_tl(leg)


def _recompute_receiver(
        receiver: PlannedLeg,
        moved_items: list[tuple[Part, int | float]],
        data) -> PlannedLeg | None:
    if receiver.kind not in {"Spot", "Kiralık"} or not receiver.items:
        return None

    items = list(receiver.items) + list(moved_items)
    total = _desi_total(items)
    capacity = Decimal(data.vehicles[receiver.vtype].capacity_desi)
    if total > capacity:
        return None

    handling = handling_minutes(_whole_desi(total))
    handling_delta = timedelta(minutes=handling)
    latest_ready = max(part.ready for part, _desi in items)
    if receiver.kind == "Spot":
        load_start = max(receiver.load_start, latest_ready)
        dep = load_start + handling_delta
    elif receiver.dep - handling_delta >= latest_ready:
        load_start = receiver.dep - handling_delta
        dep = receiver.dep
    else:
        load_start = latest_ready
        dep = latest_ready + handling_delta

    lane = data.lanes[(receiver.origin, receiver.dest)]
    arr = dep + timedelta(minutes=travel_minutes(
        lane.hours[receiver.vtype]))
    unload_end = arr + handling_delta
    updated = replace(
        receiver,
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=unload_end,
        items=items,
        item_ids=[],
    )
    return replace(
        updated,
        cost=float(_vehicle_cost_tl(updated, data)),
        penalty=float(_sla_penalty_tl(updated)),
    )


def _receiver_proposal(
        donor: PlannedLeg, receiver: PlannedLeg, data
        ) -> _ReceiverProposal | None:
    if (donor.origin, donor.dest) != (receiver.origin, receiver.dest):
        return None

    updated = _recompute_receiver(receiver, donor.items, data)
    if updated is None:
        return None
    if (receiver.kind == "Kiralık"
            and updated.dep.date() != receiver.dep.date()):
        return None
    delta = (
        _leg_total_tl(updated, data)
        - _leg_total_tl(receiver, data)
        - _leg_total_tl(donor, data)
    )
    if delta >= Decimal(0):
        return None
    return _ReceiverProposal(
        receiver=updated,
        delta_tl=delta,
        parts_moved=len(donor.items),
        desi_moved=_whole_desi(_desi_total(donor.items)),
    )


def _canonical_part_key(item: tuple[Part, int | float]) -> tuple:
    part, desi = item
    return (
        part.base_id,
        part.part_id,
        part.ready,
        part.deadline,
        part.carried_before,
        part.dest or "",
        _decimal(desi),
    )


def _canonical_leg_key(leg: PlannedLeg) -> tuple:
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
        tuple(sorted(_canonical_part_key(item) for item in leg.items)),
    )


def _trial_ledgers_valid(legs: list[PlannedLeg], data) -> bool:
    handling = HandlingLedger(data.handling_cap)
    tir = TirLedger(data.tir_cap)
    ordered = sorted(legs, key=_canonical_leg_key)

    if any(leg.chain_id is not None for leg in ordered):
        return False

    for leg in ordered:
        total = _desi_total(leg.items)
        if total > Decimal(data.vehicles[leg.vtype].capacity_desi):
            return False
        if any(part.ready > leg.load_start for part, _desi in leg.items):
            return False
        whole_total = _whole_desi(total)
        handling.add(leg.origin, leg.load_start, whole_total)
        handling.add(leg.dest, leg.arr, whole_total)

    if handling.violations():
        return False

    for position, leg in enumerate(ordered):
        if leg.vtype != "Tır":
            continue
        vehicle_key = f"same-lane-{position}"
        tir.add_event(leg.origin, leg.dep.date(), vehicle_key, 0)
        tir.add_event(leg.dest, leg.arr.date(), vehicle_key, 1)
    return not tir.violations()


def repair_same_lane(
        legs: list[PlannedLeg], data
        ) -> tuple[list[PlannedLeg], RepairMetrics]:
    ordered = sorted(deepcopy(legs), key=_canonical_leg_key)
    occurrences = Counter(
        id(part)
        for leg in ordered
        for part, _desi in leg.items
    )
    working = dict(enumerate(ordered))

    def direct_only(leg: PlannedLeg) -> bool:
        return (
            bool(leg.items)
            and leg.chain_id is None
            and all(part.dest == leg.dest for part, _desi in leg.items)
            and all(occurrences[id(part)] == 1
                    for part, _desi in leg.items)
        )

    donors = [
        (token, leg)
        for token, leg in working.items()
        if direct_only(leg) and leg.kind == "Spot" and leg.vtype != "Tır"
    ]
    donors.sort(key=lambda item: (
        Fraction(_desi_total(item[1].items))
        / data.vehicles[item[1].vtype].capacity_desi,
        _canonical_leg_key(item[1]),
    ))

    changed_receivers = set()
    donors_considered = 0
    moves_accepted = 0
    parts_moved = 0
    desi_moved = 0
    spot_legs_removed = 0
    local_saving_tl = Decimal("0")

    for donor_token, _initial_donor in donors:
        if (donor_token not in working
                or donor_token in changed_receivers):
            continue
        donors_considered += 1
        donor = working[donor_token]
        candidates = []

        for receiver_token, receiver in working.items():
            if (
                    receiver_token == donor_token
                    or not direct_only(receiver)
                    or receiver.kind not in {"Spot", "Kiralık"}
                    or (receiver.origin, receiver.dest)
                    != (donor.origin, donor.dest)):
                continue
            proposal = _receiver_proposal(donor, receiver, data)
            if (proposal is None
                    or proposal.delta_tl >= Decimal("0")):
                continue
            trial = sorted(
                (
                    proposal.receiver
                    if token == receiver_token else current
                    for token, current in working.items()
                    if token != donor_token
                ),
                key=_canonical_leg_key,
            )
            if not _trial_ledgers_valid(trial, data):
                continue
            candidates.append((
                (proposal.delta_tl,
                 _canonical_leg_key(proposal.receiver)),
                receiver_token,
                proposal,
            ))

        if not candidates:
            continue
        _rank, receiver_token, chosen = min(
            candidates, key=lambda candidate: candidate[0])
        working[receiver_token] = chosen.receiver
        del working[donor_token]
        changed_receivers.add(receiver_token)
        moves_accepted += 1
        spot_legs_removed += 1
        parts_moved += chosen.parts_moved
        desi_moved += chosen.desi_moved
        local_saving_tl += -chosen.delta_tl

    repaired = sorted(working.values(), key=_canonical_leg_key)
    metrics = RepairMetrics(
        donors_considered=donors_considered,
        moves_accepted=moves_accepted,
        parts_moved=parts_moved,
        desi_moved=desi_moved,
        spot_legs_removed=spot_legs_removed,
        local_saving_tl=local_saving_tl,
    )
    return repaired, metrics


def run_same_lane_stage(legs, forecast_df, data) -> Stage1Decision:
    baseline = evaluate_legs(legs, forecast_df, data, fix=True)
    repaired, metrics = repair_same_lane(baseline.legs, data)
    candidate = evaluate_legs(repaired, forecast_df, data, fix=True)
    saving = improvement_tl(baseline, candidate)
    accepted = accepts_candidate(
        baseline, candidate, minimum_saving=Decimal("1.00"))
    selected = candidate if accepted else baseline
    return Stage1Decision(
        baseline, candidate, selected, metrics, accepted, saving)
