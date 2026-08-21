"""Stage 3 mid-route pickup: regression, pricing, ledger and determinism."""
import copy
import random
import time
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

import src.pickup as pickup_module
from src.candidates import Part
from src.chain import analyze_leg_flows, physical_routes
from src.data import DATA_DIR, CompetitionData, Lane, VehicleType, load_all
from src.evaluation import PlanEvaluation, evaluate_legs
from src.forecast import forecast_horizon, to_forecast_frame
from src.milkrun import _leg_key, run_milk_run_stage
from src.optimize import PlannedLeg, build_plan, prepare_frame
from src.pickup import (PICKUP_MIN_SAVING_TL, PickupDecision, PickupMetrics,
                        _build_pickup_candidates, _donor_eligible,
                        _PickupCandidate, _rebuild_route, _route_total_tl,
                        _target_eligible, pickup_improve, run_pickup_stage)
from src.repair import run_same_lane_stage
from src.timeutil import (SLA_TL_PER_DESI_HOUR, handling_minutes, late_hours,
                          travel_minutes)


VEHICLE_VALUES = {
    "Tır": (22400, 291.6666666666667, 13, 487.5, 25),
    "Kamyon": (12000, 208.33333333333334, 10, 318.25, 21),
    "Hafif Kamyon": (7200, 208.33333333333334, 10, 364.5833333333333, 20),
    "Kamyonet": (5600, 156.25, 6, 197.91666666666666, 18),
}

# Every fixture lane is priced per hop; the minute figures below are the
# single source of travel time for the hand-computed expectations.
LANE_MINUTES = {
    ("O", "B"): (60, 100),
    ("O", "C"): (70, 120),
    ("O", "D"): (65, 110),
    ("B", "C"): (20, 30),
    ("B", "D"): (25, 35),
    ("C", "B"): (25, 40),
    ("C", "D"): (30, 45),
    ("D", "C"): (30, 45),
    ("D", "E"): (15, 25),
    ("C", "E"): (35, 55),
}


def _hours(minutes):
    return {name: minutes / 60 for name in VEHICLE_VALUES}


def _make_data(*, handling_cap=None, tir_cap=None, rentals=()):
    vehicles = {
        name: VehicleType(name, capacity, rental_hourly, rental_per_km,
                          spot_hourly, spot_per_km)
        for name, (capacity, rental_hourly, rental_per_km, spot_hourly,
                   spot_per_km) in VEHICLE_VALUES.items()
    }
    lanes = {
        (origin, dest): Lane(origin, dest, km, _hours(minutes), 1)
        for (origin, dest), (minutes, km) in LANE_MINUTES.items()
    }
    tms = ["O", "B", "C", "D", "E"]
    return CompetitionData(
        vehicles=vehicles,
        lanes=lanes,
        rentals=list(rentals),
        handling_cap=dict(handling_cap or {tm: 1_000_000 for tm in tms}),
        tir_cap=dict(tir_cap or {tm: 100 for tm in tms}),
        demand=pd.DataFrame([{"cikis": "O", "varis": "B"}]),
        tms=tms,
    )


@pytest.fixture
def pickup_data():
    return _make_data()


# --- independent, hand-rolled expectations (no production helper reuse) ---


def _travel(origin, dest):
    return travel_minutes(LANE_MINUTES[(origin, dest)][0] / 60)


def _km(origin, dest):
    return LANE_MINUTES[(origin, dest)][1]


def _expected_vehicle_tl(vtype, load_start, unload_end, km):
    hourly, per_km = VEHICLE_VALUES[vtype][3], VEHICLE_VALUES[vtype][4]
    seconds = int((unload_end - load_start).total_seconds())
    return (Decimal(str(hourly)) * Decimal(seconds) / Decimal(3600)
            + Decimal(str(per_km)) * Decimal(str(km)))


def _expected_sla_tl(items, completion):
    return sum(
        (Decimal(str(desi))
         * Decimal(late_hours(part.deadline, completion))
         * Decimal(str(SLA_TL_PER_DESI_HOUR))
         for part, desi in items),
        Decimal("0"),
    )


def _desi(items):
    return sum(desi for _part, desi in items)


def _part(item_id, dest, desi, ready, *, deadline=None, sla_days=1):
    return Part(
        part_id=item_id,
        base_id=item_id,
        desi=desi,
        ready=ready,
        deadline=deadline if deadline is not None
        else ready + timedelta(days=sla_days),
        dest=dest,
    )


def _direct_leg(data, vtype, origin, dest, items, load_start, *,
                kind="Spot"):
    """One single-leg physical route, timed and priced from first principles."""
    desi = _desi(items)
    handling = timedelta(minutes=handling_minutes(desi))
    dep = load_start + handling
    arr = dep + timedelta(minutes=_travel(origin, dest))
    unload_end = arr + handling
    vehicle = _expected_vehicle_tl(vtype, load_start, unload_end,
                                   _km(origin, dest))
    return PlannedLeg(
        kind=kind, vtype=vtype, origin=origin, dest=dest,
        load_start=load_start, dep=dep, arr=arr, unload_end=unload_end,
        items=list(items), cost=float(vehicle),
        penalty=float(_expected_sla_tl(items, unload_end)),
    )


def _chain_legs(data, vtype, origin, stops, load_start, *, chain_id=1,
                kind="Spot", extra_loads=None):
    """Build a milk-run chain whose stop ``i`` drops ``stops[i][1]``.

    ``extra_loads`` maps a stop index to cargo taken ON at that stop's
    transfer centre (i.e. loaded for segment ``index + 1``); it exists so a
    fixture can express a route that already carries a mid-route pickup.
    Times follow the same contract as ``src/milkrun.py``: one continuous
    usage window, no handling for cargo that stays onboard, and departure
    from a stop only after both its unloading and its loading finish.
    """
    extra_loads = dict(extra_loads or {})
    onboard = []
    for index in range(len(stops)):
        carried = [item for _dest, items in stops[index:] for item in items]
        for load_index, load_items in extra_loads.items():
            if load_index < index:
                drop_index = next(
                    position for position, (dest, _items) in enumerate(stops)
                    if dest == load_items[0][0].dest)
                if index <= drop_index:
                    carried = carried + list(load_items)
        onboard.append(carried)

    legs = []
    hops = [(origin, stops[0][0])] + [
        (stops[index][0], stops[index + 1][0])
        for index in range(len(stops) - 1)
    ]
    clock = load_start
    total_km = 0
    for index, (hop_origin, hop_dest) in enumerate(hops):
        loaded = (onboard[0] if index == 0
                  else list(extra_loads.get(index - 1, ())))
        if index == 0:
            leg_load_start = clock
            dep = clock + timedelta(minutes=handling_minutes(_desi(loaded)))
        else:
            dep = clock
            leg_load_start = dep - timedelta(
                minutes=handling_minutes(_desi(loaded)))
        arr = dep + timedelta(minutes=_travel(hop_origin, hop_dest))
        following = onboard[index + 1] if index + 1 < len(onboard) else []
        following_ids = {id(part) for part, _desi in following}
        dropped = [(part, desi) for part, desi in onboard[index]
                   if id(part) not in following_ids]
        unload_end = arr + timedelta(minutes=handling_minutes(_desi(dropped)))
        total_km += _km(hop_origin, hop_dest)
        legs.append(PlannedLeg(
            kind=kind, vtype=vtype, origin=hop_origin, dest=hop_dest,
            load_start=leg_load_start, dep=dep, arr=arr,
            unload_end=unload_end, items=list(onboard[index]),
            cost=0.0, penalty=float(_expected_sla_tl(dropped, unload_end)),
            chain_id=chain_id, chain_seq=index,
        ))
        clock = unload_end + timedelta(
            minutes=handling_minutes(_desi(extra_loads.get(index, ()))))

    legs[0].cost = float(_expected_vehicle_tl(
        vtype, legs[0].load_start, legs[-1].unload_end, total_km))
    return legs


def _signature(legs):
    return tuple(sorted(_leg_key(leg) for leg in legs))


# --- shared fixtures ---------------------------------------------------


def _simple_case(data, *, vtype="Kamyon", donor_vtype="Kamyonet",
                 donor_desi=5000, load_start=datetime(2026, 6, 29, 8, 0),
                 b_deadline=None, c_deadline=None, donor_deadline=None):
    """Route O->B->C plus one donor B->C sitting at the hub."""
    ready = datetime(2026, 6, 28, 0, 0)
    to_b = _part("D00001", "B", 600, ready, deadline=b_deadline
                 or datetime(2026, 7, 9, 0, 0))
    to_c = _part("D00002", "C", 400, ready, deadline=c_deadline
                 or datetime(2026, 7, 9, 0, 0))
    route = _chain_legs(data, vtype, "O",
                        [("B", [(to_b, 600)]), ("C", [(to_c, 400)])],
                        load_start)
    donor_part = _part("D00003", "C", donor_desi, ready,
                       deadline=donor_deadline or datetime(2026, 7, 9, 0, 0))
    donor = _direct_leg(data, donor_vtype, "B", "C",
                        [(donor_part, donor_desi)],
                        datetime(2026, 6, 29, 6, 0))
    return route, donor


# --- §3.1 rented routes may never be a pickup target -------------------


def test_rented_target_route_is_skipped_and_yields_no_candidates(
        pickup_data):
    """Q&A: 'Kiralık araçlarla uğrama yapılmaz.' — never a pickup target."""
    route, donor = _simple_case(pickup_data)
    rented = [
        PlannedLeg(**{**leg.__dict__, "kind": "Kiralık"}) for leg in route
    ]

    search = _build_pickup_candidates(
        [tuple(rented), (donor,)], [(1, donor)], pickup_data)

    assert search.candidates == ()
    assert search.rented_routes_skipped == 1
    assert search.routes_considered == 0
    assert search.pairs_examined == 0
    assert _target_eligible(tuple(rented)) is False
    assert _target_eligible(tuple(route)) is True


def test_route_total_refuses_to_price_a_rented_route_at_spot_rates(
        pickup_data):
    """Defence in depth: rented routes cost rental rates, never spot ones."""
    route, _donor = _simple_case(pickup_data)
    rented = [
        PlannedLeg(**{**leg.__dict__, "kind": "Kiralık"}) for leg in route
    ]

    assert _route_total_tl(tuple(route), pickup_data) > Decimal("0")
    with pytest.raises(ValueError, match="Spot"):
        _route_total_tl(tuple(rented), pickup_data)


def test_rented_donor_is_not_eligible(pickup_data):
    _route, donor = _simple_case(pickup_data)
    rented_donor = PlannedLeg(**{**donor.__dict__, "kind": "Kiralık"})

    assert _donor_eligible((donor,), {id(donor.items[0][0]): 1}) is True
    assert _donor_eligible(
        (rented_donor,), {id(rented_donor.items[0][0]): 1}) is False


# --- §3.2 the pickup stop's SLA stamp is the END OF UNLOADING ----------


def test_pickup_stop_sla_stamp_excludes_the_loading_that_follows(
        pickup_data):
    """Loading after unloading delays departure, never the SLA stamp."""
    route, donor = _simple_case(
        pickup_data, b_deadline=datetime(2026, 6, 29, 9, 16))
    pickup_items = list(donor.items)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=0,
                             drop_at=1, pickup_items=pickup_items)

    # Segment 0 is untouched up to and including the unloading at B.
    assert rebuilt[0].arr == datetime(2026, 6, 29, 9, 10)
    assert rebuilt[0].unload_end == datetime(2026, 6, 29, 9, 16)
    assert rebuilt[0].unload_end == rebuilt[0].arr + timedelta(
        minutes=handling_minutes(600))
    # The 5.000 desi loading (50 min) delays only the DEPARTURE.
    assert rebuilt[1].dep == datetime(2026, 6, 29, 10, 6)
    assert rebuilt[1].dep == rebuilt[0].unload_end + timedelta(
        minutes=handling_minutes(5000))
    # ...and the simulator's implied load start is exactly the unload end.
    assert rebuilt[1].load_start == rebuilt[0].unload_end

    dropped_at_b = [(part, desi) for part, desi in rebuilt[0].items
                    if part.dest == "B"]
    assert Decimal(str(rebuilt[0].penalty)) == Decimal("0")
    assert _expected_sla_tl(dropped_at_b, rebuilt[0].unload_end) == Decimal(
        "0")
    # A stamp taken after the loading would have charged a whole late hour.
    assert _expected_sla_tl(dropped_at_b, rebuilt[1].dep) == Decimal("240.0")


def test_pickup_stop_departure_waits_for_the_loading_to_finish(pickup_data):
    """The referee starts loading at dep - handling(new desi); no overlap."""
    route, donor = _simple_case(pickup_data)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=0,
                             drop_at=1, pickup_items=list(donor.items))

    referee_load_start = rebuilt[1].dep - timedelta(
        minutes=handling_minutes(5000))
    assert referee_load_start == rebuilt[0].unload_end
    assert referee_load_start >= rebuilt[0].unload_end


# --- §3.3 picked-up cargo rides only its own pickup..drop window -------


def test_picked_up_cargo_never_rides_past_its_own_stop(pickup_data):
    """4-durak rota: 2. durakta alınan, 3. durakta inen yük 4. segmentte yok."""
    ready = datetime(2026, 6, 28, 0, 0)
    far = datetime(2026, 7, 9, 0, 0)
    stops = [
        ("B", [(_part("D00001", "B", 300, ready, deadline=far), 300)]),
        ("C", [(_part("D00002", "C", 300, ready, deadline=far), 300)]),
        ("D", [(_part("D00003", "D", 300, ready, deadline=far), 300)]),
        ("E", [(_part("D00004", "E", 300, ready, deadline=far), 300)]),
    ]
    route = _chain_legs(pickup_data, "Kamyon", "O", stops,
                        datetime(2026, 6, 29, 8, 0))
    picked = _part("D00009", "D", 900, ready, deadline=far)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=1,
                             drop_at=2, pickup_items=[(picked, 900)])

    carried = [
        [part is picked for part, _desi in leg.items] for leg in rebuilt
    ]
    assert [any(flags) for flags in carried] == [False, False, True, False]


def test_carried_pickup_is_not_unloaded_at_an_intermediate_stop(pickup_data):
    """Cargo bound for a later stop must not be handled at stops it passes."""
    ready = datetime(2026, 6, 28, 0, 0)
    far = datetime(2026, 7, 9, 0, 0)
    stops = [
        ("B", [(_part("D00001", "B", 300, ready, deadline=far), 300)]),
        ("C", [(_part("D00002", "C", 300, ready, deadline=far), 300)]),
        ("D", [(_part("D00003", "D", 300, ready, deadline=far), 300)]),
    ]
    route = _chain_legs(pickup_data, "Kamyon", "O", stops,
                        datetime(2026, 6, 29, 8, 0))
    picked = _part("D00009", "D", 6000, ready, deadline=far)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=0,
                             drop_at=2, pickup_items=[(picked, 6000)])

    assert [any(part is picked for part, _desi in leg.items)
            for leg in rebuilt] == [False, True, True]
    # C is a pass-through for the pickup: only the 300 desi bound for C is
    # unloaded there, so unloading takes 3 minutes, not 63.
    assert rebuilt[1].unload_end == rebuilt[1].arr + timedelta(
        minutes=handling_minutes(300))
    assert rebuilt[1].dep == rebuilt[0].unload_end + timedelta(
        minutes=handling_minutes(6000))
    # Only the drop stop handles the picked-up desi.
    assert rebuilt[2].unload_end == rebuilt[2].arr + timedelta(
        minutes=handling_minutes(6300))


def test_rebuild_reproduces_the_referee_load_start_on_every_segment(
        pickup_data):
    """Every segment's load start must be dep - handling(newly loaded desi).

    That is how the referee derives it from the exported rows, and it holds
    for a route that already takes cargo on mid-run, not only for the
    drop-only chains Stage 2 produces today.
    """
    ready = datetime(2026, 6, 28, 0, 0)
    far = datetime(2026, 7, 9, 0, 0)
    existing = _part("D00010", "D", 4000, ready, deadline=far)
    stops = [
        ("B", [(_part("D00001", "B", 1000, ready, deadline=far), 1000)]),
        ("C", [(_part("D00002", "C", 500, ready, deadline=far), 500)]),
        ("D", [(_part("D00003", "D", 500, ready, deadline=far), 500)]),
    ]
    # The route already loads 4.000 desi at C for the run to D.
    route = _chain_legs(pickup_data, "Kamyon", "O", stops,
                        datetime(2026, 6, 29, 8, 0),
                        extra_loads={1: [(existing, 4000)]})
    picked = _part("D00020", "D", 900, ready, deadline=far)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=0,
                             drop_at=2, pickup_items=[(picked, 900)])

    for index, leg in enumerate(rebuilt):
        previous = ({id(part) for part, _desi in rebuilt[index - 1].items}
                    if index else set())
        newly_loaded = _desi([item for item in leg.items
                              if id(item[0]) not in previous])
        referee_load_start = leg.dep - timedelta(
            minutes=handling_minutes(newly_loaded))
        assert leg.load_start == referee_load_start, f"segment {index}"
        if index:
            # ...and loading may never start before the previous unloading
            # has finished, which is the referee's overlap violation.
            assert leg.load_start >= rebuilt[index - 1].unload_end

    # Concretely: C loads 4.000 desi (40 min) on top of its own unloading.
    assert _desi(rebuilt[2].items) == 500 + 4000 + 900
    assert rebuilt[2].dep == rebuilt[1].unload_end + timedelta(minutes=40)
    assert rebuilt[2].load_start == rebuilt[1].unload_end


def test_rented_donor_is_never_priced_even_if_handed_in_directly(pickup_data):
    """pickup_improve filters donors; the builder must not trust its caller."""
    route, donor = _simple_case(pickup_data)
    rented_donor = PlannedLeg(**{**donor.__dict__, "kind": "Kiralık"})

    assert len(_build_pickup_candidates(
        [tuple(route), (donor,)], [(1, donor)], pickup_data).candidates) == 1
    search = _build_pickup_candidates(
        [tuple(route), (rented_donor,)], [(1, rented_donor)], pickup_data)
    assert search.candidates == ()
    assert search.pairs_examined == 1


def test_pickup_window_bounds_are_validated(pickup_data):
    route, donor = _simple_case(pickup_data)
    items = list(donor.items)

    for pickup_at, drop_at in ((1, 1), (0, 0), (-1, 1), (0, 2), (1, 0)):
        with pytest.raises(ValueError):
            _rebuild_route(tuple(route), pickup_data, pickup_at=pickup_at,
                           drop_at=drop_at, pickup_items=items)
    with pytest.raises(ValueError):
        _rebuild_route(tuple(route), pickup_data, pickup_at=0, drop_at=1,
                       pickup_items=[])


def test_rebuild_rejects_cargo_already_onboard(pickup_data):
    route, _donor = _simple_case(pickup_data)
    already = route[0].items[0]

    with pytest.raises(ValueError):
        _rebuild_route(tuple(route), pickup_data, pickup_at=0, drop_at=1,
                       pickup_items=[already])


# --- declared-column contract, identical to milkrun.py -----------------


def test_rebuild_declares_route_cost_once_and_sla_per_stop(pickup_data):
    route, donor = _simple_case(pickup_data)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=0,
                             drop_at=1, pickup_items=list(donor.items))

    total_km = _km("O", "B") + _km("B", "C")
    expected_vehicle = _expected_vehicle_tl(
        "Kamyon", rebuilt[0].load_start, rebuilt[-1].unload_end, total_km)
    assert Decimal(str(rebuilt[0].cost)) == Decimal(str(float(
        expected_vehicle)))
    assert [leg.cost for leg in rebuilt[1:]] == [0.0]
    assert [(leg.chain_id, leg.chain_seq) for leg in rebuilt] == [
        (1, 0), (1, 1)]
    assert [(leg.kind, leg.vtype) for leg in rebuilt] == [
        ("Spot", "Kamyon"), ("Spot", "Kamyon")]
    assert all(leg.vehicle_id is None and leg.item_ids == []
               for leg in rebuilt)

    dropped_b = [item for item in rebuilt[0].items if item[0].dest == "B"]
    dropped_c = [item for item in rebuilt[1].items]
    assert Decimal(str(rebuilt[0].penalty)) == Decimal(str(float(
        _expected_sla_tl(dropped_b, rebuilt[0].unload_end))))
    assert Decimal(str(rebuilt[1].penalty)) == Decimal(str(float(
        _expected_sla_tl(dropped_c, rebuilt[1].unload_end))))


def test_rebuilt_route_passes_physical_flow_validation(pickup_data):
    route, donor = _simple_case(pickup_data)

    rebuilt = _rebuild_route(tuple(route), pickup_data, pickup_at=0,
                             drop_at=1, pickup_items=list(donor.items))

    flows = analyze_leg_flows(list(rebuilt))
    assert [len(flow.loaded) for flow in flows] == [2, 1]
    assert [len(flow.unloaded) for flow in flows] == [1, 2]
    assert physical_routes(list(rebuilt)) == [tuple(rebuilt)]


# --- exact pricing -----------------------------------------------------


def test_candidate_delta_matches_independent_decimal_recomputation(
        pickup_data):
    # The route's own C cargo is late in both worlds, at different stamps,
    # so the delta carries a real SLA term and not only vehicle hours.
    route, donor = _simple_case(
        pickup_data, c_deadline=datetime(2026, 6, 29, 9, 0))

    search = _build_pickup_candidates(
        [tuple(route), (donor,)], [(1, donor)], pickup_data)

    assert len(search.candidates) == 1
    candidate = search.candidates[0]
    assert (candidate.route_index, candidate.pickup_at, candidate.drop_at,
            candidate.donor_token) == (0, 0, 1, 1)

    # Old world: the chain priced on its own plus the standalone donor.
    old_chain = (
        _expected_vehicle_tl("Kamyon", route[0].load_start,
                             route[-1].unload_end,
                             _km("O", "B") + _km("B", "C"))
        + _expected_sla_tl(
            [item for item in route[0].items if item[0].dest == "B"],
            route[0].unload_end)
        + _expected_sla_tl(route[1].items, route[1].unload_end)
    )
    old_donor = (
        _expected_vehicle_tl("Kamyonet", donor.load_start, donor.unload_end,
                             _km("B", "C"))
        + _expected_sla_tl(donor.items, donor.unload_end)
    )

    # New world: one chain, one continuous usage window.
    load_start = datetime(2026, 6, 29, 8, 0)
    dep0 = load_start + timedelta(minutes=handling_minutes(1000))
    arr0 = dep0 + timedelta(minutes=_travel("O", "B"))
    unload0 = arr0 + timedelta(minutes=handling_minutes(600))
    dep1 = unload0 + timedelta(minutes=handling_minutes(5000))
    arr1 = dep1 + timedelta(minutes=_travel("B", "C"))
    unload1 = arr1 + timedelta(minutes=handling_minutes(5400))
    new_chain = (
        _expected_vehicle_tl("Kamyon", load_start, unload1,
                             _km("O", "B") + _km("B", "C"))
        + _expected_sla_tl(
            [item for item in route[0].items if item[0].dest == "B"], unload0)
        + _expected_sla_tl(list(route[1].items) + list(donor.items), unload1)
    )

    assert candidate.delta_tl == new_chain - (old_chain + old_donor)
    assert candidate.delta_tl < Decimal("0")
    assert [leg.arr for leg in candidate.segments] == [arr0, arr1]
    assert candidate.segments[-1].unload_end == unload1


def test_unprofitable_candidate_is_not_offered(pickup_data):
    """A donor that is cheaper on its own must not become a pickup."""
    route, donor = _simple_case(
        pickup_data, donor_desi=5600,
        donor_deadline=datetime(2026, 6, 29, 9, 0))

    search = _build_pickup_candidates(
        [tuple(route), (donor,)], [(1, donor)], pickup_data)

    for candidate in search.candidates:
        assert candidate.delta_tl < Decimal("0")
    assert search.pairs_examined == 1


# --- feasibility guards ------------------------------------------------


def test_capacity_is_checked_on_every_segment_the_pickup_rides(pickup_data):
    """The binding segment is not always the one right after the pickup."""
    ready = datetime(2026, 6, 28, 0, 0)
    far = datetime(2026, 7, 9, 0, 0)
    to_d_later = _part("D00010", "D", 4000, ready, deadline=far)
    stops = [
        ("B", [(_part("D00001", "B", 1000, ready, deadline=far), 1000)]),
        ("C", [(_part("D00002", "C", 500, ready, deadline=far), 500)]),
        ("D", [(_part("D00003", "D", 500, ready, deadline=far), 500)]),
    ]
    # The route already takes 4.000 desi on at C, so segment 2 carries more
    # than segment 1 - the naive "check the first segment" guard breaks here.
    route = _chain_legs(pickup_data, "Kamyonet", "O", stops,
                        datetime(2026, 6, 29, 8, 0),
                        extra_loads={1: [(to_d_later, 4000)]})
    assert [_desi(leg.items) for leg in route] == [2000, 1000, 4500]

    def search_with(donor_desi):
        donor_part = _part("D00020", "D", donor_desi, ready, deadline=far)
        donor = _direct_leg(pickup_data, "Kamyonet", "B", "D",
                            [(donor_part, donor_desi)],
                            datetime(2026, 6, 29, 6, 0))
        return _build_pickup_candidates(
            [tuple(route), (donor,)], [(1, donor)], pickup_data)

    # 1.000 desi fits everywhere (2.000 / 5.500 <= 5.600).
    assert len(search_with(1000).candidates) == 1
    # 1.200 desi still fits at B (2.200) but overflows at C->D (5.700).
    assert search_with(1200).candidates == ()


def test_pickup_rejected_when_cargo_is_not_ready_at_the_hub(pickup_data):
    route, donor = _simple_case(pickup_data)
    late_part = _part("D00003", "C", 5000,
                      datetime(2026, 6, 29, 9, 17),
                      deadline=datetime(2026, 7, 9, 0, 0))
    late_donor = _direct_leg(pickup_data, "Kamyonet", "B", "C",
                             [(late_part, 5000)],
                             datetime(2026, 6, 29, 9, 17))

    # The vehicle finishes unloading at B at 09:16; cargo ready at 09:17
    # cannot be loaded without idling, which the model forbids.
    assert route[0].unload_end == datetime(2026, 6, 29, 9, 16)
    search = _build_pickup_candidates(
        [tuple(route), (late_donor,)], [(1, late_donor)], pickup_data)
    assert search.candidates == ()
    assert search.pairs_examined == 1


def test_donor_destination_must_be_a_stop_the_route_already_visits(
        pickup_data):
    """Tier A only: the route topology may not change."""
    route, _donor = _simple_case(pickup_data)
    ready = datetime(2026, 6, 28, 0, 0)
    stranger = _part("D00003", "D", 1000, ready,
                     deadline=datetime(2026, 7, 9, 0, 0))
    donor = _direct_leg(pickup_data, "Kamyonet", "B", "D",
                        [(stranger, 1000)], datetime(2026, 6, 29, 6, 0))

    search = _build_pickup_candidates(
        [tuple(route), (donor,)], [(1, donor)], pickup_data)

    assert search.candidates == ()
    assert search.pairs_examined == 1


def test_donor_eligibility_rules(pickup_data):
    route, donor = _simple_case(pickup_data)
    single = {id(donor.items[0][0]): 1}

    assert _donor_eligible((donor,), single) is True
    # A chained (multi-segment) route is not a donor.
    assert _donor_eligible(tuple(route), {}) is False
    # An empty leg carries nothing to pick up.
    empty = PlannedLeg(**{**donor.__dict__, "items": []})
    assert _donor_eligible((empty,), {}) is False
    # A part that also travels somewhere else may not be moved.
    assert _donor_eligible((donor,), {id(donor.items[0][0]): 2}) is False
    # Cargo whose destination is not the leg destination is a transfer.
    transfer_part = _part("D00003", "E", 5000, datetime(2026, 6, 28, 0, 0))
    transfer = PlannedLeg(**{**donor.__dict__,
                            "items": [(transfer_part, 5000)]})
    assert _donor_eligible((transfer,), {id(transfer_part): 1}) is False


# --- ledger guard and accumulation -------------------------------------


def _midnight_case(data, hub, chain_id, base_id):
    """Route O->hub->C whose pickup pushes the C unloading past midnight."""
    ready = datetime(2026, 6, 28, 0, 0)
    far = datetime(2026, 7, 9, 0, 0)
    to_hub = _part(f"{base_id}1", hub, 600, ready, deadline=far)
    to_c = _part(f"{base_id}2", "C", 400, ready, deadline=far)
    route = _chain_legs(data, "Kamyon", "O",
                        [(hub, [(to_hub, 600)]), ("C", [(to_c, 400)])],
                        datetime(2026, 6, 29, 22, 0), chain_id=chain_id)
    donor_part = _part(f"{base_id}3", "C", 4000, ready, deadline=far)
    donor = _direct_leg(data, "Kamyonet", hub, "C",
                        [(donor_part, 4000)], datetime(2026, 6, 29, 21, 0))
    return route, donor


def test_ledger_guard_rejects_a_pickup_that_overflows_the_drop_centre():
    data = _make_data(handling_cap={"O": 1_000_000, "B": 1_000_000,
                                    "C": 8_000, "D": 1_000_000,
                                    "E": 1_000_000})
    route, donor = _midnight_case(data, "B", 1, "D001")
    filler_part = _part("D0091", "C", 4000, datetime(2026, 6, 30, 0, 0),
                        deadline=datetime(2026, 7, 9, 0, 0))
    filler = _direct_leg(data, "Kamyonet", "O", "C", [(filler_part, 4000)],
                         datetime(2026, 6, 30, 8, 0))

    legs = list(route) + [donor, filler]
    baseline_signature = _signature(legs)
    improved, metrics = pickup_improve(legs, data)

    # The pickup itself is profitable and would otherwise be taken...
    search = _build_pickup_candidates(
        [tuple(route), (donor,), (filler,)], [(1, donor), (2, filler)], data)
    assert len(search.candidates) == 1
    assert search.candidates[0].delta_tl < Decimal("0")
    # ...but it moves 4.400 desi of unloading from 29 to 30 June at C.
    assert metrics.pickups_accepted == 0
    assert metrics.rejected_by_ledger == 1
    assert metrics.local_saving_tl == Decimal("0")
    assert _signature(improved) == baseline_signature


def test_guard_accumulates_across_accepted_pickups():
    """Two pickups that are each fine alone must not both be accepted."""
    data = _make_data(handling_cap={"O": 1_000_000, "B": 1_000_000,
                                    "C": 12_000, "D": 1_000_000,
                                    "E": 1_000_000})
    route_one, donor_one = _midnight_case(data, "B", 1, "D001")
    route_two, donor_two = _midnight_case(data, "D", 2, "D002")
    filler_part = _part("D0091", "C", 4000, datetime(2026, 6, 30, 0, 0),
                        deadline=datetime(2026, 7, 9, 0, 0))
    filler = _direct_leg(data, "Kamyonet", "O", "C", [(filler_part, 4000)],
                         datetime(2026, 6, 30, 8, 0))

    legs = list(route_one) + list(route_two) + [donor_one, donor_two, filler]
    improved, metrics = pickup_improve(legs, data)

    assert metrics.profitable_candidates == 2
    assert metrics.pickups_accepted == 1
    assert metrics.rejected_by_ledger == 1
    assert metrics.donor_vehicles_removed == 1
    assert len(improved) == len(legs) - 1


def test_accepted_pickup_removes_the_donor_and_keeps_the_cargo(pickup_data):
    route, donor = _simple_case(pickup_data)
    legs = list(route) + [donor]
    donor_part = donor.items[0][0]

    improved, metrics = pickup_improve(legs, pickup_data)

    assert metrics.pickups_accepted == 1
    assert metrics.donor_vehicles_removed == 1
    assert metrics.parts_picked_up == 1
    assert metrics.desi_picked_up == 5000
    assert metrics.local_saving_tl > Decimal("0")
    assert metrics.pickup_type_mix == (("Kamyon", 1),)
    assert len(improved) == 2
    assert all(leg.chain_id == 1 for leg in improved)
    # pickup_improve works on its own deep copy, so the cargo is matched by
    # demand identity rather than by object identity.
    carrying = [leg for leg in improved
                if any(part.base_id == donor_part.base_id
                       for part, _desi in leg.items)]
    assert [(leg.origin, leg.dest) for leg in carrying] == [("B", "C")]


def test_no_profitable_candidate_leaves_the_plan_untouched(pickup_data):
    ready = datetime(2026, 6, 28, 0, 0)
    far = datetime(2026, 7, 9, 0, 0)
    lonely = _direct_leg(pickup_data, "Kamyonet", "O", "B",
                         [(_part("D00001", "B", 500, ready, deadline=far),
                           500)], datetime(2026, 6, 29, 8, 0))

    improved, metrics = pickup_improve([lonely], pickup_data)

    assert _signature(improved) == _signature([lonely])
    assert metrics.pickups_accepted == 0
    assert metrics.routes_considered == 0
    assert metrics.local_saving_tl == Decimal("0")


def test_pickup_improve_does_not_mutate_its_input(pickup_data):
    route, donor = _simple_case(pickup_data)
    legs = list(route) + [donor]
    before = copy.deepcopy(legs)

    improved, _metrics = pickup_improve(legs, pickup_data)

    assert _signature(legs) == _signature(before)
    assert not any(leg is other for leg in improved for other in legs)


# --- determinism -------------------------------------------------------


def test_identical_plan_for_shuffled_input():
    data = _make_data(handling_cap={"O": 1_000_000, "B": 1_000_000,
                                    "C": 12_000, "D": 1_000_000,
                                    "E": 1_000_000})
    route_one, donor_one = _midnight_case(data, "B", 1, "D001")
    route_two, donor_two = _midnight_case(data, "D", 2, "D002")
    filler_part = _part("D0091", "C", 4000, datetime(2026, 6, 30, 0, 0),
                        deadline=datetime(2026, 7, 9, 0, 0))
    filler = _direct_leg(data, "Kamyonet", "O", "C", [(filler_part, 4000)],
                         datetime(2026, 6, 30, 8, 0))
    legs = list(route_one) + list(route_two) + [donor_one, donor_two, filler]

    outcomes = []
    for seed in range(6):
        shuffled = copy.deepcopy(legs)
        random.Random(seed).shuffle(shuffled)
        improved, metrics = pickup_improve(shuffled, data)
        outcomes.append((_signature(improved), metrics))

    assert all(outcome == outcomes[0] for outcome in outcomes)


# --- dataclass contracts -----------------------------------------------


def test_metrics_and_candidate_are_frozen(pickup_data):
    route, donor = _simple_case(pickup_data)
    _improved, metrics = pickup_improve(list(route) + [donor], pickup_data)
    candidate = _build_pickup_candidates(
        [tuple(route), (donor,)], [(1, donor)], pickup_data).candidates[0]

    with pytest.raises(FrozenInstanceError):
        metrics.pickups_accepted = 99
    with pytest.raises(FrozenInstanceError):
        candidate.delta_tl = Decimal("0")
    assert [field.name for field in fields(_PickupCandidate)] == [
        "route_index", "pickup_at", "drop_at", "donor_token", "segments",
        "delta_tl"]
    assert isinstance(metrics.local_saving_tl, Decimal)
    assert PICKUP_MIN_SAVING_TL == Decimal("1.00")


# --- stage boundary ----------------------------------------------------


def test_run_pickup_stage_keeps_the_baseline_when_nothing_improves(
        pickup_data, monkeypatch):
    route, donor = _simple_case(pickup_data)
    legs = list(route) + [donor]
    forecast = pd.DataFrame(columns=["Talep ID"])

    baseline = PlanEvaluation(legs, pd.DataFrame(), _StubResult(1000.0), ())
    monkeypatch.setattr(
        pickup_module, "evaluate_legs",
        lambda *args, **kwargs: PlanEvaluation(
            legs, pd.DataFrame(), _StubResult(1000.0), ()))

    decision = run_pickup_stage(baseline, forecast, pickup_data)

    assert isinstance(decision, PickupDecision)
    assert decision.accepted is False
    assert decision.selected is decision.baseline
    assert decision.baseline is baseline
    assert decision.saving_tl == Decimal("0")


class _StubResult:
    def __init__(self, total_cost):
        self.total_cost = total_cost
        self.vehicle_cost = total_cost
        self.sla_penalty = 0.0
        self.violations = []


# --- real horizon ------------------------------------------------------


def test_full_horizon_pickup_stage_accepts_stage2_baseline(record_property):
    data = load_all(DATA_DIR)
    horizon_start = date(2026, 6, 29)
    horizon_end = date(2026, 7, 5)
    forecast = to_forecast_frame(forecast_horizon(
        data.demand, horizon_start, horizon_end))
    days = [horizon_start + timedelta(days=offset) for offset in range(7)]
    stage1 = run_same_lane_stage(
        build_plan(data, prepare_frame(forecast), days), forecast, data)
    stage2 = run_milk_run_stage(stage1.selected, forecast, data)
    baseline = stage2.selected
    baseline_before = copy.deepcopy(baseline.legs)

    started = time.perf_counter()
    decision = run_pickup_stage(baseline, forecast, data)
    runtime = time.perf_counter() - started

    total = Decimal(str(decision.candidate.result.total_cost))
    record_property("stage3_total_tl", str(total))
    record_property("stage3_saving_tl", str(decision.saving_tl))
    record_property("stage3_runtime_seconds", f"{runtime:.6f}")
    for metric_field in fields(PickupMetrics):
        record_property(metric_field.name,
                        str(getattr(decision.metrics, metric_field.name)))

    assert Decimal(str(baseline.result.total_cost)) == Decimal(
        "11313338.286111113")
    assert baseline.result.violations == []
    assert _signature(baseline.legs) == _signature(baseline_before)

    assert decision.baseline is baseline
    assert decision.accepted is True
    assert decision.selected is decision.candidate
    assert decision.candidate.result.violations == []
    assert decision.saving_tl >= Decimal("50000.00")

    # The reconciliation gate: the saving the search claims analytically and
    # the saving the referee actually measures must be the same number. Every
    # one of the three prototype defects showed up here first.
    assert abs(decision.metrics.local_saving_tl
               - decision.saving_tl) < Decimal("0.000001")

    assert Decimal(str(decision.candidate.result.total_cost)) == Decimal(
        "11232476.731944447")
    assert Decimal(str(decision.candidate.result.vehicle_cost)) == Decimal(
        "8616944.731944447")
    assert Decimal(str(decision.candidate.result.sla_penalty)) == Decimal(
        "2615531.9999999995")
    assert decision.saving_tl == Decimal("80861.554166666")
    assert decision.metrics == PickupMetrics(
        routes_considered=227,
        rented_routes_skipped=126,
        donors_available=340,
        pairs_examined=135_660,
        profitable_candidates=56,
        pickups_accepted=28,
        rejected_by_ledger=0,
        donor_vehicles_removed=28,
        parts_picked_up=82,
        desi_picked_up=65_754,
        local_saving_tl=Decimal("80861.55416666666605766666666"),
        pickup_type_mix=(("Kamyon", 11), ("Kamyonet", 17)),
    )

    routes = physical_routes(decision.candidate.legs)
    assert len(decision.candidate.legs) == 1064
    assert len(routes) == 665
    assert len(decision.candidate.plan_frame) == 5523
    # Tier A never changes a route's topology: Stage 2's 227 chains stay 227
    # chains, and no chain grows past the stop limit Stage 2 set.
    assert sum(1 for route in routes if len(route) > 1) == 227
    assert max(len(route) for route in routes) <= 4
    assert all(route[0].kind == "Spot" for route in routes
               if len(route) > 1)
    # Every picked-up part rides one contiguous window inside its route and
    # is delivered at its own forecast destination.
    for route in routes:
        for index, leg in enumerate(route):
            following = ({id(part) for part, _desi in route[index + 1].items}
                         if index + 1 < len(route) else set())
            for part, _desi in leg.items:
                if id(part) not in following:
                    assert part.dest == leg.dest
