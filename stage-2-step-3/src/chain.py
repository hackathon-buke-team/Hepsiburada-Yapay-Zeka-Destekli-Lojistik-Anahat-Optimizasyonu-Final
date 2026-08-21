"""Neutral physical-route validation and per-leg cargo flow analysis."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.candidates import Part
from src.optimize import PlannedLeg


@dataclass(frozen=True)
class LegFlow:
    loaded: tuple[tuple[Part, int | float], ...]
    carried: tuple[tuple[Part, int | float], ...]
    unloaded: tuple[tuple[Part, int | float], ...]


def _validated_route_records(legs: list[PlannedLeg]):
    routes = []
    chain_groups = {}

    for input_index, leg in enumerate(legs):
        if leg.chain_id is None:
            routes.append((input_index, ((input_index, leg),)))
        else:
            chain_groups.setdefault(leg.chain_id, []).append(
                (input_index, leg))

    for chain_id, group in chain_groups.items():
        if any(leg.chain_id != chain_id for _index, leg in group):
            raise ValueError(f"chain {chain_id}: inconsistent chain_id")

        ordered = sorted(group, key=lambda indexed: indexed[1].chain_seq)
        sequences = [leg.chain_seq for _index, leg in ordered]
        if sequences != list(range(len(ordered))):
            raise ValueError(
                f"chain {chain_id}: chain_seq must be contiguous from 0")

        if len({leg.kind for _index, leg in ordered}) != 1:
            raise ValueError(f"chain {chain_id}: mixed kind")
        if len({leg.vtype for _index, leg in ordered}) != 1:
            raise ValueError(f"chain {chain_id}: mixed vehicle type")

        for (_previous_index, previous), (_next_index, next_leg) in zip(
                ordered, ordered[1:]):
            if previous.dest != next_leg.origin:
                raise ValueError(
                    f"chain {chain_id}: disconnected "
                    f"{previous.dest} -> {next_leg.origin}")

        routes.append((min(index for index, _leg in group), tuple(ordered)))

    routes.sort(key=lambda route: route[0])
    return routes


def physical_routes(
        legs: list[PlannedLeg]) -> list[tuple[PlannedLeg, ...]]:
    """Return validated physical routes in first-input-occurrence order."""
    return [
        tuple(leg for _input_index, leg in route)
        for _first_index, route in _validated_route_records(legs)
    ]


def analyze_leg_flows(legs: list[PlannedLeg]) -> list[LegFlow]:
    """Validate physical cargo continuity and return input-aligned flows."""
    routes = _validated_route_records(legs)
    validated_routes = []

    for _first_index, route in routes:
        first_leg = route[0][1]
        route_label = (f"chain {first_leg.chain_id}"
                       if first_leg.chain_id is not None
                       else f"leg {route[0][0]}")
        segment_values = []
        occurrences = {}

        for segment_index, (_input_index, leg) in enumerate(route):
            values = {}
            for part, desi in leg.items:
                identity = id(part)
                if identity in values:
                    raise ValueError(
                        f"{route_label}: duplicate Part in segment "
                        f"{segment_index}")

                exact_desi = Decimal(str(desi))
                values[identity] = exact_desi
                existing = occurrences.get(identity)
                if existing is None:
                    occurrences[identity] = (
                        part, exact_desi, desi, [segment_index])
                else:
                    _same_part, first_exact, first_desi, indexes = existing
                    if exact_desi != first_exact:
                        raise ValueError(
                            f"{route_label}: Part desi changed "
                            f"{first_desi} -> {desi}")
                    indexes.append(segment_index)
            segment_values.append(values)

        for _part, _exact_desi, _first_desi, indexes in occurrences.values():
            expected = list(range(indexes[0], indexes[-1] + 1))
            if indexes != expected:
                raise ValueError(f"{route_label}: non-contiguous Part")

        validated_routes.append((route, segment_values))

    flows_by_index = {}
    for route, segment_values in validated_routes:
        if len(route) == 1:
            input_index, leg = route[0]
            items = tuple(leg.items)
            flows_by_index[input_index] = LegFlow(
                loaded=items, carried=(), unloaded=items)
            continue

        for segment_index, (input_index, leg) in enumerate(route):
            previous = (segment_values[segment_index - 1]
                        if segment_index > 0 else {})
            following = (segment_values[segment_index + 1]
                         if segment_index + 1 < len(route) else {})

            loaded = tuple(
                item for item in leg.items
                if previous.get(id(item[0])) != Decimal(str(item[1])))
            carried = tuple(
                item for item in leg.items
                if following.get(id(item[0])) == Decimal(str(item[1])))
            unloaded = tuple(
                item for item in leg.items
                if following.get(id(item[0])) != Decimal(str(item[1])))
            flows_by_index[input_index] = LegFlow(
                loaded=loaded, carried=carried, unloaded=unloaded)

    return [flows_by_index[index] for index in range(len(legs))]
