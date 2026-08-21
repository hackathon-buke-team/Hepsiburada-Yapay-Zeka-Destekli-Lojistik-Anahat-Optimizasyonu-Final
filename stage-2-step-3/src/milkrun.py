"""Pure deterministic multi-destination milk-run candidate construction."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from itertools import combinations, permutations

from src.chain import analyze_leg_flows, physical_routes
from src.evaluation import (PlanEvaluation, accepts_candidate, evaluate_legs,
                            improvement_tl)
from src.ledger import HandlingLedger, TirLedger
from src.optimize import PlannedLeg
from src.timeutil import (SLA_TL_PER_DESI_HOUR, handling_minutes, late_hours,
                           travel_minutes)


ROUTE_TYPES = ("Kamyonet", "Hafif Kamyon", "Kamyon")

# Jury Q&A 11.1: a Spot vehicle may call at more than one transfer centre in a
# single run and drop cargo in sequence; rented vehicles may not. Q&A 3 confirms
# there is no upper bound on a Spot vehicle's trips beyond the physical
# constraints. No competition document caps the stop count, so this constant is
# ours alone: it trades search cost for saving. Raising it widens the search
# without changing any cost or topology rule.
#
# Measured on this instance: k=3 -> 11,519,240.35 TL, k=4 -> 11,313,338.29 TL
# (-205,902.07). k=5 is not viable with this brute-force enumerator: the active
# groups hold C(n,5) = 254,992 subsets, each priced over 120 stop orders.
# The binding physical limit is capacity - chains use non-Tır Spot types, so a
# route may carry at most 12,000 desi while an eligible source averages 4,128.
MAX_CHAIN_STOPS = 4


@dataclass(frozen=True)
class MilkRunMetrics:
    groups_considered: int
    pairs_evaluated: int
    chains_accepted: int
    source_vehicles_replaced: int
    segments_created: int
    parts_consolidated: int
    desi_consolidated: int
    local_saving_tl: Decimal
    chain_type_mix: tuple[tuple[str, int], ...]
    triples_evaluated: int = 0
    chain_size_mix: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class MilkRunDecision:
    baseline: PlanEvaluation
    candidate: PlanEvaluation
    selected: PlanEvaluation
    metrics: MilkRunMetrics
    accepted: bool
    saving_tl: Decimal


@dataclass(frozen=True)
class _PairCandidate:
    """One priced milk-run variant over two or more source vehicles."""

    source_tokens: tuple[int, ...]
    route_destinations: tuple[str, ...]
    vtype: str
    legs: tuple[PlannedLeg, ...]
    delta_tl: Decimal


def _decimal(value, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, OverflowError, TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a finite number") from error
    if not number.is_finite():
        raise ValueError(f"{label} must be a finite number")
    return number


def _whole_desi(value, label: str = "desi total") -> int:
    total = _decimal(value, label)
    if total != total.to_integral_value():
        raise ValueError(f"{label} must be a whole number")
    return int(total)


def _part_key(item: tuple) -> tuple:
    part, desi = item
    return (
        part.base_id,
        part.part_id,
        part.ready,
        part.deadline,
        part.carried_before,
        part.dest or "",
        _decimal(desi, "part desi"),
    )


def _leg_key(leg: PlannedLeg) -> tuple:
    return (
        leg.kind != "Kiralık",
        leg.load_start,
        leg.dep,
        leg.origin,
        leg.dest,
        leg.vtype,
        leg.arr,
        leg.unload_end,
        leg.chain_id is None,
        -1 if leg.chain_id is None else leg.chain_id,
        leg.chain_seq,
        tuple(sorted(_part_key(item) for item in leg.items)),
    )


def _vehicle_cost_tl(vtype: str, load_start, unload_end, km, data) -> Decimal:
    seconds = int((unload_end - load_start).total_seconds())
    if seconds < 0:
        raise ValueError("vehicle usage duration cannot be negative")
    vehicle = data.vehicles[vtype]
    return (
        _decimal(vehicle.spot_hourly, f"{vtype} Spot hourly rate")
        * Decimal(seconds)
        / Decimal(3600)
        + _decimal(vehicle.spot_per_km, f"{vtype} Spot per-km rate")
        * _decimal(km, "route distance")
    )


def _final_sla_tl(items, unload_end) -> Decimal:
    rate = _decimal(SLA_TL_PER_DESI_HOUR, "SLA rate")
    return sum(
        (
            _decimal(desi, "part desi")
            * Decimal(late_hours(part.deadline, unload_end))
            * rate
            for part, desi in items
        ),
        Decimal("0"),
    )


def _scheduled_direct_total_tl(leg: PlannedLeg, data) -> Decimal:
    lane = data.lanes[(leg.origin, leg.dest)]
    return (
        _vehicle_cost_tl(
            leg.vtype,
            leg.load_start,
            leg.unload_end,
            lane.km,
            data,
        )
        + _final_sla_tl(leg.items, leg.unload_end)
    )


def _build_chain_candidates(
        tokens: tuple[int, ...],
        sources: tuple[PlannedLeg, ...],
        data) -> tuple[_PairCandidate, ...]:
    """Price every stop order and vehicle type for one set of source legs.

    The economics are identical for every chain length: one continuous vehicle
    usage window from the joint load start to the final unload end, the actual
    inter-stop lane distances, no intermediate handling for cargo that stays
    onboard, and final-only SLA charged per destination at its own drop time.
    """
    if len(sources) < 2:
        return ()

    base = sources[0]
    destinations = [source.dest for source in sources]
    if (
        len(set(destinations)) != len(destinations)
        or any(source.origin != base.origin for source in sources)
        or any(source.load_start != base.load_start for source in sources)
        or any(not source.items for source in sources)
        or any(part.dest != source.dest
               for source in sources
               for part, _desi in source.items)
    ):
        return ()

    if any((base.origin, source.dest) not in data.lanes
           for source in sources):
        return ()

    by_destination = {}
    total_desi = Decimal("0")
    for source in sources:
        source_total = sum(
            (_decimal(desi, "source part desi")
             for _part, desi in source.items),
            Decimal("0"),
        )
        try:
            source_desi = _whole_desi(source_total, "source desi")
        except ValueError:
            return ()
        if source_desi <= 0:
            return ()
        by_destination[source.dest] = (source, source_desi)
        total_desi += source_total

    try:
        combined_desi = _whole_desi(total_desi, "combined source desi")
    except ValueError:
        return ()
    if combined_desi > 12_000:
        return ()

    source_tokens = tuple(sorted(tokens))
    source_keys = tuple(sorted(_leg_key(source) for source in sources))
    old_total = sum(
        (_scheduled_direct_total_tl(source, data) for source in sources),
        Decimal("0"),
    )
    candidates = []

    for route_destinations in permutations(destinations):
        hops = [(base.origin, route_destinations[0])] + [
            (route_destinations[index], route_destinations[index + 1])
            for index in range(len(route_destinations) - 1)
        ]
        if any(hop not in data.lanes for hop in hops):
            continue
        lanes = [data.lanes[hop] for hop in hops]

        for vtype in ROUTE_TYPES:
            capacity = _whole_desi(
                data.vehicles[vtype].capacity_desi,
                f"{vtype} capacity",
            )
            if capacity < combined_desi:
                continue

            hop_hours = [
                _decimal(lane.hours[vtype], f"{hop} {vtype} travel hours")
                for hop, lane in zip(hops, lanes)
            ]
            if any(hours < 0 for hours in hop_hours):
                raise ValueError("travel hours cannot be negative")

            load_start = base.load_start
            clock = load_start + timedelta(
                minutes=handling_minutes(combined_desi))
            route_km = Decimal("0")
            segments = []
            slas = []
            for index, (hop, lane) in enumerate(zip(hops, lanes)):
                remaining = route_destinations[index:]
                onboard = [
                    item
                    for destination in remaining
                    for item in by_destination[destination][0].items
                ]
                drop_source, drop_desi = by_destination[
                    route_destinations[index]]
                departure = clock
                arrival = departure + timedelta(
                    minutes=travel_minutes(float(hop_hours[index])))
                unload_end = arrival + timedelta(
                    minutes=handling_minutes(drop_desi))
                route_km += _decimal(lane.km, "route distance")
                stop_sla = _final_sla_tl(list(drop_source.items), unload_end)
                slas.append(stop_sla)
                segments.append({
                    "origin": hop[0],
                    "dest": hop[1],
                    "load_start": load_start if index == 0 else departure,
                    "dep": departure,
                    "arr": arrival,
                    "unload_end": unload_end,
                    "items": onboard,
                    "penalty": float(stop_sla),
                })
                clock = unload_end

            vehicle_cost = _vehicle_cost_tl(
                vtype, load_start, segments[-1]["unload_end"], route_km, data)
            delta = vehicle_cost + sum(slas, Decimal("0")) - old_total
            if delta >= Decimal("0"):
                continue

            legs = tuple(
                PlannedLeg(
                    kind="Spot",
                    vtype=vtype,
                    origin=segment["origin"],
                    dest=segment["dest"],
                    load_start=segment["load_start"],
                    dep=segment["dep"],
                    arr=segment["arr"],
                    unload_end=segment["unload_end"],
                    items=segment["items"],
                    cost=float(vehicle_cost) if index == 0 else 0.0,
                    penalty=segment["penalty"],
                    chain_id=0,
                    chain_seq=index,
                )
                for index, segment in enumerate(segments)
            )
            candidates.append(_PairCandidate(
                source_tokens=source_tokens,
                route_destinations=tuple(route_destinations),
                vtype=vtype,
                legs=legs,
                delta_tl=delta,
            ))

    route_type_index = {
        vtype: index for index, vtype in enumerate(ROUTE_TYPES)
    }
    return tuple(sorted(
        candidates,
        key=lambda candidate: (
            candidate.delta_tl,
            candidate.route_destinations,
            route_type_index[candidate.vtype],
            source_keys,
        ),
    ))


def _build_pair_candidates(
        first_token: int,
        first: PlannedLeg,
        second_token: int,
        second: PlannedLeg,
        data) -> tuple[_PairCandidate, ...]:
    """Two-stop entry point; the general builder owns the economics."""
    return _build_chain_candidates(
        (first_token, second_token), (first, second), data)


def _source_eligible(leg: PlannedLeg, occurrences: Counter) -> bool:
    if (
        not leg.items
        or leg.kind != "Spot"
        or leg.vtype == "Tır"
        or leg.chain_id is not None
    ):
        return False

    try:
        for part, desi in leg.items:
            exact_desi = _decimal(desi, "source part desi")
            if (
                part.dest != leg.dest
                or occurrences[id(part)] != 1
                or exact_desi <= 0
                or exact_desi != exact_desi.to_integral_value()
                or exact_desi != _decimal(part.desi, "complete Part desi")
                or part.ready > leg.load_start
            ):
                return False
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _trial_candidate_valid(legs: list[PlannedLeg], data) -> bool:
    """Validate a complete trial graph against flow and daily ledgers."""
    try:
        flows = analyze_leg_flows(legs)
        handling = HandlingLedger(data.handling_cap)

        for leg, flow in zip(legs, flows):
            exact_items = []
            for part, desi in leg.items:
                exact_desi = _decimal(desi, "trial part desi")
                if (
                    exact_desi <= 0
                    or exact_desi != exact_desi.to_integral_value()
                    or exact_desi != _decimal(
                        part.desi, "trial complete Part desi")
                ):
                    return False
                exact_items.append(exact_desi)

            segment_desi = sum(exact_items, Decimal("0"))
            capacity = _decimal(
                data.vehicles[leg.vtype].capacity_desi,
                f"{leg.vtype} capacity",
            )
            if capacity < 0 or segment_desi > capacity:
                return False
            if any(part.ready > leg.load_start
                   for part, _desi in flow.loaded):
                return False

            loaded_desi = _whole_desi(sum(
                (_decimal(desi, "loaded part desi")
                 for _part, desi in flow.loaded),
                Decimal("0"),
            ), "loaded desi")
            unloaded_desi = _whole_desi(sum(
                (_decimal(desi, "unloaded part desi")
                 for _part, desi in flow.unloaded),
                Decimal("0"),
            ), "unloaded desi")
            handling.add(leg.origin, leg.load_start, loaded_desi)
            handling.add(leg.dest, leg.arr, unloaded_desi)

        if handling.violations():
            return False

        routes = sorted(
            physical_routes(legs),
            key=lambda route: tuple(_leg_key(leg) for leg in route),
        )
        tir = TirLedger(data.tir_cap)
        for route_position, route in enumerate(routes):
            if route[0].vtype != "Tır":
                continue
            vehicle_key = f"milk-run-trial-{route_position}"
            for visit_id, leg in enumerate(route):
                tir.add_event(
                    leg.origin, leg.dep.date(), vehicle_key, visit_id)
                tir.add_event(
                    leg.dest, leg.arr.date(), vehicle_key, visit_id + 1)
        return not tir.violations()
    except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
        return False


def milk_run_improve(
        legs: list[PlannedLeg], data
        ) -> tuple[list[PlannedLeg], MilkRunMetrics]:
    """Select profitable non-overlapping source pairs in one full pass."""
    copied = deepcopy(legs)
    ordered = sorted(copied, key=_leg_key)
    working = dict(enumerate(ordered))
    occurrences = Counter(
        id(part)
        for leg in ordered
        for part, _desi in leg.items
    )
    eligible = [
        (token, leg)
        for token, leg in working.items()
        if _source_eligible(leg, occurrences)
    ]

    groups = {}
    for token, leg in eligible:
        groups.setdefault((leg.origin, leg.load_start), []).append(
            (token, leg))

    groups_considered = 0
    pairs_evaluated = 0
    triples_evaluated = 0
    candidates = []
    for group_key in sorted(groups):
        group = groups[group_key]
        if len(group) < 2 or len({leg.dest for _token, leg in group}) < 2:
            continue
        groups_considered += 1
        for first_index, (first_token, first) in enumerate(group):
            for second_token, second in group[first_index + 1:]:
                if first.dest == second.dest:
                    continue
                pairs_evaluated += 1
                try:
                    built = _build_pair_candidates(
                        first_token, first, second_token, second, data)
                    candidates.extend(
                        candidate
                        for candidate in built
                        if candidate.delta_tl < Decimal("0")
                    )
                except (AttributeError, KeyError, OverflowError,
                        TypeError, ValueError):
                    continue

        for size in range(3, MAX_CHAIN_STOPS + 1):
            if len(group) < size:
                break
            for combination in combinations(group, size):
                members = tuple(leg for _token, leg in combination)
                if len({leg.dest for leg in members}) < size:
                    continue
                triples_evaluated += 1
                try:
                    built = _build_chain_candidates(
                        tuple(token for token, _leg in combination),
                        members,
                        data,
                    )
                    candidates.extend(
                        candidate
                        for candidate in built
                        if candidate.delta_tl < Decimal("0")
                    )
                except (AttributeError, KeyError, OverflowError,
                        TypeError, ValueError):
                    continue

    route_type_index = {
        vtype: index for index, vtype in enumerate(ROUTE_TYPES)
    }

    def candidate_key(candidate: _PairCandidate) -> tuple:
        source_legs = tuple(
            working[token] for token in candidate.source_tokens)
        source = source_legs[0]
        return (
            candidate.delta_tl,
            len(candidate.source_tokens),
            (source.origin, source.load_start)
            + tuple(candidate.route_destinations),
            route_type_index[candidate.vtype],
            tuple(sorted(_leg_key(leg) for leg in source_legs)),
        )

    candidates.sort(key=candidate_key)
    stage1_end_date = max(
        (leg.unload_end.date() for leg in ordered if leg.items),
        default=None,
    )
    next_chain_id = max(
        (leg.chain_id for leg in ordered if leg.chain_id is not None),
        default=0,
    ) + 1
    next_working_token = len(ordered)
    chains_accepted = 0
    parts_consolidated = 0
    desi_consolidated = 0
    local_saving_tl = Decimal("0")
    type_counts = Counter()
    size_counts = Counter()

    for candidate in candidates:
        tokens = tuple(candidate.source_tokens)
        if (
            len(tokens) < 2
            or len(set(tokens)) != len(tokens)
            or any(token not in working for token in tokens)
        ):
            continue

        try:
            committed = tuple(
                replace(template, chain_id=next_chain_id)
                for template in candidate.legs
            )
            if ([leg.chain_seq for leg in committed]
                    != list(range(len(tokens)))):
                continue
            if (
                stage1_end_date is None
                or committed[-1].unload_end.date() > stage1_end_date
            ):
                continue

            sources = tuple(working[token] for token in tokens)
            source_items = [
                item for source in sources for item in source.items
            ]
            committed_parts = len({id(part) for part, _desi in source_items})
            committed_desi = _whole_desi(sum(
                (_decimal(desi, "committed source desi")
                 for _part, desi in source_items),
                Decimal("0"),
            ), "committed source desi")
            committed_saving = -candidate.delta_tl
            consumed = set(tokens)
            trial = [
                leg for token, leg in working.items()
                if token not in consumed
            ] + list(committed)
        except (AttributeError, KeyError, OverflowError,
                TypeError, ValueError):
            continue

        if not _trial_candidate_valid(trial, data):
            continue

        for token in tokens:
            del working[token]
        for leg in committed:
            working[next_working_token] = leg
            next_working_token += 1
        chains_accepted += 1
        parts_consolidated += committed_parts
        desi_consolidated += committed_desi
        local_saving_tl += committed_saving
        type_counts[candidate.vtype] += 1
        size_counts[len(tokens)] += 1
        next_chain_id += 1

    metrics = MilkRunMetrics(
        groups_considered=groups_considered,
        pairs_evaluated=pairs_evaluated,
        chains_accepted=chains_accepted,
        source_vehicles_replaced=sum(
            size * count for size, count in size_counts.items()),
        segments_created=sum(
            size * count for size, count in size_counts.items()),
        parts_consolidated=parts_consolidated,
        desi_consolidated=desi_consolidated,
        local_saving_tl=local_saving_tl,
        chain_type_mix=tuple(sorted(type_counts.items())),
        triples_evaluated=triples_evaluated,
        chain_size_mix=tuple(sorted(size_counts.items())),
    )
    return sorted(working.values(), key=_leg_key), metrics


def run_milk_run_stage(baseline, forecast_df, data) -> MilkRunDecision:
    improved, metrics = milk_run_improve(baseline.legs, data)
    candidate = evaluate_legs(improved, forecast_df, data, fix=True)
    saving = improvement_tl(baseline, candidate)
    accepted = accepts_candidate(
        baseline, candidate, minimum_saving=Decimal("1.00"))
    selected = candidate if accepted else baseline
    return MilkRunDecision(
        baseline, candidate, selected, metrics, accepted, saving)
