"""Pure deterministic mid-route pickup on existing Spot milk-run routes.

Stage 2 chains only ever *drop* cargo: the vehicle loads everything at the
origin and leaves a share at each stop. Jury Q&A 6 explicitly allows the
other half of the operation as well:

    "...Aynı şekilde bir araçtan x kadar yük indirilip y kadar yük
     yüklenirse kapasiteden x+y kadar yük düşülür."

That sentence describes one vehicle unloading *and* loading at one centre
and gives the handling arithmetic for it. The only prohibition is on rented
vehicles: "Kiralık araçlarla uğrama yapılmaz."

This module implements Tier A of that idea: the picked-up cargo's own
destination must be a stop the route **already visits**, so the route
topology never changes and no chain grows longer than Stage 2 made it.
A donor vehicle whose whole load is absorbed this way disappears from the
plan; its cargo keeps its physical Part identity, so the referee still sees
the demand starting from its own forecast origin (``src/simulator.py``
checks the route origin per part, not per vehicle) and the K1 contract on
split demands is untouched.

The economics, the declared-column contract and the trial-graph guard are
imported from ``src/milkrun.py`` on purpose: Stage 2 and Stage 3 must price
a physical route through exactly one code path, or a silent divergence
between the two stages would only surface as a referee mismatch.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from src.chain import physical_routes
from src.evaluation import (PlanEvaluation, accepts_candidate, evaluate_legs,
                            improvement_tl)
from src.milkrun import (_decimal, _final_sla_tl, _leg_key,
                         _scheduled_direct_total_tl, _trial_candidate_valid,
                         _vehicle_cost_tl, _whole_desi)
from src.optimize import PlannedLeg
from src.timeutil import handling_minutes, travel_minutes

# The stage keeps the same "is this actually an improvement" floor as Stage 1
# and Stage 2. The pinned, much stricter acceptance gate for the published
# run lives in run.py (STAGE3_MIN_SAVING_TL); this constant only decides
# whether the module hands back the candidate or the untouched baseline.
PICKUP_MIN_SAVING_TL = Decimal("1.00")


@dataclass(frozen=True)
class PickupMetrics:
    routes_considered: int
    rented_routes_skipped: int
    donors_available: int
    pairs_examined: int
    profitable_candidates: int
    pickups_accepted: int
    rejected_by_ledger: int
    donor_vehicles_removed: int
    parts_picked_up: int
    desi_picked_up: int
    local_saving_tl: Decimal
    pickup_type_mix: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class PickupDecision:
    baseline: PlanEvaluation
    candidate: PlanEvaluation
    selected: PlanEvaluation
    metrics: PickupMetrics
    accepted: bool
    saving_tl: Decimal


@dataclass(frozen=True)
class _PickupCandidate:
    """One priced Tier A pickup: route ``route_index`` absorbs a donor."""

    route_index: int
    pickup_at: int
    drop_at: int
    donor_token: int
    segments: tuple[PlannedLeg, ...]
    delta_tl: Decimal


@dataclass(frozen=True)
class _PickupSearch:
    """Priced candidates plus the search statistics that produced them."""

    candidates: tuple[_PickupCandidate, ...]
    routes_considered: int
    rented_routes_skipped: int
    pairs_examined: int


def _items_desi(items) -> Decimal:
    return sum(
        (_decimal(desi, "pickup part desi") for _part, desi in items),
        Decimal("0"),
    )


def _dropped_here(item_lists: list[list], index: int) -> list:
    """Cargo that is onboard at ``index`` and no longer onboard afterwards.

    Both the timetable and the SLA stamp read the drop set from the *new*
    onboard lists. Deriving it from the pre-pickup lists instead would make
    every stop between the pickup and its destination look like an unloading
    stop for cargo that is merely passing through.
    """
    following = (
        {id(part) for part, _desi in item_lists[index + 1]}
        if index + 1 < len(item_lists) else set()
    )
    return [item for item in item_lists[index] if id(item[0]) not in following]


def _loaded_here(item_lists: list[list], index: int) -> list:
    """Cargo that is onboard at ``index`` and was not onboard before it.

    This is the referee's own definition of "newly loaded" — it derives a
    leg's load start as ``dep - handling(newly loaded desi)`` — so deriving
    it the same way keeps the rebuilt timetable reproducible even for a
    route that already takes cargo on somewhere in its run.
    """
    previous = (
        {id(part) for part, _desi in item_lists[index - 1]}
        if index > 0 else set()
    )
    return [item for item in item_lists[index] if id(item[0]) not in previous]


def _route_km(segments, data) -> Decimal:
    return sum(
        (_decimal(data.lanes[(leg.origin, leg.dest)].km, "route distance")
         for leg in segments),
        Decimal("0"),
    )


def _require_spot_route(segments) -> None:
    """Rented routes are priced from rental tariffs and may not be touched.

    Q&A: "Kiralık araçlarla uğrama yapılmaz." Pricing one at Spot rates
    would understate its cost silently, so refusing here is both the rule
    check and the guard against a wrong tariff.
    """
    if not segments:
        raise ValueError("physical route cannot be empty")
    if any(leg.kind != "Spot" for leg in segments):
        raise ValueError("only a Spot route may be priced at Spot rates")


def _route_total_tl(segments, data) -> Decimal:
    """One physical route's vehicle usage plus its per-stop final SLA."""
    _require_spot_route(segments)
    item_lists = [list(leg.items) for leg in segments]
    total = _vehicle_cost_tl(
        segments[0].vtype,
        segments[0].load_start,
        segments[-1].unload_end,
        _route_km(segments, data),
        data,
    )
    for index, leg in enumerate(segments):
        total += _final_sla_tl(_dropped_here(item_lists, index),
                               leg.unload_end)
    return total


def _travel_delta(leg, data) -> timedelta:
    lane = data.lanes[(leg.origin, leg.dest)]
    hours = _decimal(lane.hours[leg.vtype],
                     f"{leg.origin}->{leg.dest} {leg.vtype} travel hours")
    if hours < 0:
        raise ValueError("travel hours cannot be negative")
    return timedelta(minutes=travel_minutes(float(hours)))


def _rebuild_route(segments, data, *, pickup_at: int, drop_at: int,
                   pickup_items) -> list[PlannedLeg]:
    """Rebuild a route's timetable with one mid-route pickup.

    The cargo goes onboard at ``segments[pickup_at].dest`` and comes off at
    ``segments[drop_at].dest``. Two timestamps are kept apart at the pickup
    stop, because they answer two different questions:

        unload_end   = arr + handling(drop desi)      <- the SLA stamp
        departure    = unload_end + handling(pickup)  <- the next segment

    The cargo dropped at that stop is delivered the moment its unloading
    ends; the loading that follows delays the vehicle, not the delivery.
    """
    segments = tuple(segments)
    _require_spot_route(segments)
    if len(segments) < 2:
        raise ValueError("a mid-route pickup needs at least two segments")
    if not 0 <= pickup_at < drop_at <= len(segments) - 1:
        raise ValueError(
            f"invalid pickup window {pickup_at} -> {drop_at} "
            f"for {len(segments)} segments")

    pickup_items = list(pickup_items)
    if not pickup_items:
        raise ValueError("a pickup must carry at least one Part")
    onboard_ids = {id(part) for leg in segments for part, _desi in leg.items}
    if any(id(part) in onboard_ids for part, _desi in pickup_items):
        raise ValueError("picked-up cargo is already onboard this route")
    pickup_desi = _whole_desi(_items_desi(pickup_items), "pickup desi")
    if pickup_desi <= 0:
        raise ValueError("pickup desi must be positive")

    item_lists = [
        list(leg.items) + (pickup_items if pickup_at < index <= drop_at
                           else [])
        for index, leg in enumerate(segments)
    ]

    def loading_at(index: int) -> timedelta:
        """Handling time for whatever goes onboard at segment ``index``."""
        if not 0 <= index < len(segments):
            return timedelta(0)
        return timedelta(minutes=handling_minutes(_whole_desi(
            _items_desi(_loaded_here(item_lists, index)), "segment load desi")))

    rebuilt = []
    clock = segments[0].load_start
    for index, leg in enumerate(segments):
        loading = loading_at(index)
        # Segment 0 is anchored on its load start; every later segment is
        # anchored on its departure, so its load start is the moment the
        # referee will derive: dep - handling(newly loaded desi).
        load_start, dep = ((clock, clock + loading) if index == 0
                           else (clock - loading, clock))
        arrival = dep + _travel_delta(leg, data)
        dropped = _dropped_here(item_lists, index)
        unload_end = arrival + timedelta(minutes=handling_minutes(
            _whole_desi(_items_desi(dropped), "stop drop desi")))
        rebuilt.append(PlannedLeg(
            kind=leg.kind,
            vtype=leg.vtype,
            origin=leg.origin,
            dest=leg.dest,
            load_start=load_start,
            dep=dep,
            arr=arrival,
            unload_end=unload_end,
            items=item_lists[index],
            cost=0.0,
            penalty=0.0,
            chain_id=leg.chain_id,
            chain_seq=leg.chain_seq,
        ))
        # Jury Q&A 6: unloading and loading at one centre are two successive
        # operations, so only the DEPARTURE waits for the loading to end.
        clock = unload_end + loading_at(index + 1)

    # Declared columns follow the milkrun.py contract exactly: the physical
    # route's vehicle cost sits on segment 0 alone, SLA sits on the stop
    # that actually completes the delivery.
    vehicle_cost = _vehicle_cost_tl(
        rebuilt[0].vtype,
        rebuilt[0].load_start,
        rebuilt[-1].unload_end,
        _route_km(rebuilt, data),
        data,
    )
    for index, leg in enumerate(rebuilt):
        leg.cost = float(vehicle_cost) if index == 0 else 0.0
        leg.penalty = float(_final_sla_tl(
            _dropped_here(item_lists, index), leg.unload_end))
    return rebuilt


def _target_eligible(route) -> bool:
    """A pickup target is a loaded, multi-stop, all-Spot physical route."""
    return (
        len(route) >= 2
        and all(leg.kind == "Spot" for leg in route)
        and all(leg.items for leg in route)
    )


def _donor_eligible(route, occurrences) -> bool:
    """A donor is one standalone Spot leg whose whole load ends at its dest.

    Anything that already transfers, is split across vehicles, or carries a
    fraction of a Part is refused: absorbing it would break the physical
    continuity the referee reconstructs from the output rows.
    """
    if len(route) != 1:
        return False
    leg = route[0]
    if not leg.items or leg.kind != "Spot" or leg.chain_id is not None:
        return False
    try:
        for part, desi in leg.items:
            exact_desi = _decimal(desi, "donor part desi")
            if (
                part.dest != leg.dest
                or occurrences.get(id(part), 0) != 1
                or exact_desi <= 0
                or exact_desi != exact_desi.to_integral_value()
                or exact_desi != _decimal(
                    part.desi, "donor complete Part desi")
            ):
                return False
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _price_pickup(route, route_index, route_total, pickup_at, drop_at,
                  donor_token, donor, hub_ready, data
                  ) -> _PickupCandidate | None:
    """Price one (route stop, donor) pair; return it only if it saves."""
    items = list(donor.items)
    # The vehicle loads the moment it finishes unloading; it never idles at
    # a hub waiting for cargo that is not ready yet.
    if any(part.ready > hub_ready for part, _desi in items):
        return None

    added_desi = _items_desi(items)
    # Every segment the cargo rides is checked, not just the first one: a
    # route that already takes cargo on later in its run can have its
    # binding segment anywhere inside the pickup window.
    for position in range(pickup_at + 1, drop_at + 1):
        segment = route[position]
        capacity = _decimal(data.vehicles[segment.vtype].capacity_desi,
                            f"{segment.vtype} capacity")
        if _items_desi(segment.items) + added_desi > capacity:
            return None

    segments = _rebuild_route(route, data, pickup_at=pickup_at,
                              drop_at=drop_at, pickup_items=items)
    delta = _route_total_tl(tuple(segments), data) - (
        route_total + _scheduled_direct_total_tl(donor, data))
    if delta >= Decimal("0"):
        return None
    return _PickupCandidate(
        route_index=route_index,
        pickup_at=pickup_at,
        drop_at=drop_at,
        donor_token=donor_token,
        segments=tuple(segments),
        delta_tl=delta,
    )


def _build_pickup_candidates(routes, donors, data) -> _PickupSearch:
    """Enumerate and price every Tier A pickup, in a deterministic order."""
    routes = [tuple(route) for route in routes]
    donors = list(donors)
    candidates = []
    routes_considered = 0
    rented_routes_skipped = 0
    pairs_examined = 0

    for route_index, route in enumerate(routes):
        if any(leg.kind != "Spot" for leg in route):
            rented_routes_skipped += 1
            continue
        if not _target_eligible(route):
            continue
        routes_considered += 1
        route_total = _route_total_tl(route, data)

        for pickup_at in range(len(route) - 1):
            hub = route[pickup_at].dest
            hub_ready = route[pickup_at].unload_end
            # Earliest matching stop wins: it delivers soonest and keeps the
            # extra load on the fewest segments.
            later = {}
            for position in range(pickup_at + 1, len(route)):
                later.setdefault(route[position].dest, position)

            for donor_token, donor in donors:
                pairs_examined += 1
                # A rented vehicle may not be absorbed into a chain, and its
                # cost is a rental tariff the Spot pricing helpers cannot
                # express. pickup_improve already filters these out; the
                # guard is repeated here so no caller can route around it.
                if donor.kind != "Spot" or donor.origin != hub:
                    continue
                drop_at = later.get(donor.dest)
                if drop_at is None:
                    continue
                try:
                    candidate = _price_pickup(
                        route, route_index, route_total, pickup_at, drop_at,
                        donor_token, donor, hub_ready, data)
                except (AttributeError, KeyError, OverflowError, TypeError,
                        ValueError):
                    continue
                if candidate is not None:
                    candidates.append(candidate)

    # Semantic ordering only: leg keys, stop index and donor key. The two
    # trailing indexes break ties between legs that are semantically equal,
    # and they are themselves derived from a semantic sort, so no object
    # identity or input order can leak into the accepted plan.
    route_keys = [tuple(_leg_key(leg) for leg in route) for route in routes]
    donor_keys = {token: _leg_key(donor) for token, donor in donors}
    candidates.sort(key=lambda candidate: (
        candidate.delta_tl,
        route_keys[candidate.route_index],
        candidate.pickup_at,
        donor_keys[candidate.donor_token],
        candidate.route_index,
        candidate.donor_token,
    ))
    return _PickupSearch(
        candidates=tuple(candidates),
        routes_considered=routes_considered,
        rented_routes_skipped=rented_routes_skipped,
        pairs_examined=pairs_examined,
    )


def pickup_improve(legs: list[PlannedLeg],
                   data) -> tuple[list[PlannedLeg], PickupMetrics]:
    """Accept profitable, non-overlapping pickups in one deterministic pass."""
    ordered = sorted(deepcopy(legs), key=_leg_key)
    routes = physical_routes(ordered)
    occurrences = Counter(
        id(part) for leg in ordered for part, _desi in leg.items)
    donors = [
        (route_index, route[0])
        for route_index, route in enumerate(routes)
        if _donor_eligible(route, occurrences)
    ]
    search = _build_pickup_candidates(routes, donors, data)
    donor_by_token = dict(donors)

    # The working state carries every accepted move forward, so the guard
    # validates the *accumulated* plan. Validating each pickup against the
    # untouched baseline would let two individually-legal moves overflow a
    # shared daily ledger together.
    state = {index: list(route) for index, route in enumerate(routes)}
    used_targets: set[int] = set()
    removed_donors: set[int] = set()
    rejected_by_ledger = 0
    parts_picked_up = 0
    desi_picked_up = 0
    local_saving_tl = Decimal("0")
    type_counts: Counter = Counter()

    for candidate in search.candidates:
        if (candidate.route_index in used_targets
                or candidate.donor_token in removed_donors):
            continue
        trial = []
        for index in range(len(routes)):
            if index == candidate.donor_token or index in removed_donors:
                continue
            trial.extend(list(candidate.segments)
                         if index == candidate.route_index
                         else state[index])
        if not _trial_candidate_valid(trial, data):
            rejected_by_ledger += 1
            continue

        donor = donor_by_token[candidate.donor_token]
        state[candidate.route_index] = list(candidate.segments)
        used_targets.add(candidate.route_index)
        removed_donors.add(candidate.donor_token)
        parts_picked_up += len({id(part) for part, _desi in donor.items})
        desi_picked_up += _whole_desi(
            _items_desi(donor.items), "picked-up desi")
        local_saving_tl += -candidate.delta_tl
        type_counts[candidate.segments[0].vtype] += 1

    improved = [
        leg
        for index in range(len(routes))
        if index not in removed_donors
        for leg in state[index]
    ]
    metrics = PickupMetrics(
        routes_considered=search.routes_considered,
        rented_routes_skipped=search.rented_routes_skipped,
        donors_available=len(donors),
        pairs_examined=search.pairs_examined,
        profitable_candidates=len(search.candidates),
        pickups_accepted=len(used_targets),
        rejected_by_ledger=rejected_by_ledger,
        donor_vehicles_removed=len(removed_donors),
        parts_picked_up=parts_picked_up,
        desi_picked_up=desi_picked_up,
        local_saving_tl=local_saving_tl,
        pickup_type_mix=tuple(sorted(type_counts.items())),
    )
    return sorted(improved, key=_leg_key), metrics


def run_pickup_stage(baseline: PlanEvaluation, forecast_df,
                     data) -> PickupDecision:
    improved, metrics = pickup_improve(baseline.legs, data)
    candidate = evaluate_legs(improved, forecast_df, data, fix=True)
    saving = improvement_tl(baseline, candidate)
    accepted = accepts_candidate(
        baseline, candidate, minimum_saving=PICKUP_MIN_SAVING_TL)
    selected = candidate if accepted else baseline
    return PickupDecision(
        baseline, candidate, selected, metrics, accepted, saving)
