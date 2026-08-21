# Safe Cost Optimization Design

**Project:** Hepsiburada Stage-2 Advanced Solution
**Date:** 24 July 2026
**Status:** Approved design, pending implementation plan
**Strategy:** Safety-first, staged optimization

## 1. Objective

Reduce the transport plan's simulator-recomputed total cost without changing
the submitted forecast universe, violating any jury rule, weakening output
format fidelity, or accepting a plan with simulator violations.

Every optimization stage is independently measurable and reversible. A stage is
accepted only when it produces a strictly lower total cost and zero referee
violations on the complete target horizon.

## 2. Fixed Baseline

The following result is the immutable comparison baseline for this initiative:

| Metric | Baseline |
|---|---:|
| Forecast rows | 4,046 |
| Forecast desi | 4,977,975 |
| Plan legs | 1,269 |
| Rented legs | 126 |
| Spot legs | 1,143 |
| Plan rows | 3,167 |
| Vehicle cost | 15,460,592.57 TL |
| SLA penalty | 1,020,367.20 TL |
| Total cost | **16,480,959.77 TL** |
| Simulator violations | **0** |
| Tests | **155 passing** |

The forecast values and their `D#####` identity universe remain unchanged during
transport-cost optimization. Forecast-model changes require a separate frozen
backtest design and are outside this initiative.

## 3. Competition Invariants

No optimization move may weaken these contracts:

1. The full rented fleet departs every required day through the final cargo
   delivery day, even when a rented leg is empty.
2. Rented vehicles use only their registered lane, have no stopovers and do not
   return.
3. Empty spot legs are not written and empty spot returns are not charged.
4. Vehicle and handling durations round up to whole minutes.
5. Handling capacity is pooled by center-day and crossing-midnight handling is
   split proportionally.
6. Tir capacity counts visits, including rented Tirs. A stationary unload/reload
   is one visit; leaving and returning is two visits.
7. A split piece is created only at the forecast origin. The same physical piece
   keeps the same ID and desi across transfer and milk-run legs.
8. Transfer loading begins only after the preceding unload finishes.
9. Cargo that remains onboard at an intermediate stop is not handled there.
10. SLA is computed from original forecast readiness to final-destination unload
    completion using the original OD SLA.
11. Every non-zero forecast desi is delivered exactly once at the final
    destination; transfer rows do not create or destroy desi.
12. One `Araç ID` represents one physical vehicle and one vehicle type.
13. Output columns and representations remain competition-template compatible.

## 4. Acceptance Gate

Every stage must preserve forecast identity and feasibility:

```text
candidate forecast rows/desi/IDs == current baseline forecast
and full test suite passes
and output schema and Excel round-trip validation pass
and referee violations == 0
```

Stage 0 is accepted when total cost remains equal to the baseline within 0.01 TL.
Stages 1-4 additionally require total cost to improve by at least 1.00 TL. If any
condition fails, the candidate stage is rejected without changing the accepted
baseline output.

For every accepted stage, record:

- Vehicle cost.
- SLA penalty.
- Total cost.
- Rented and spot leg counts.
- Vehicle-type mix.
- Average spot fill rate.
- Count of spot trips below 30% fill.
- Simulator violation count.
- Runtime.

## 5. Stage 0: Submission and Referee Hardening

Stage 0 does not target cost directly. It closes output and validation gaps
before local search can generate more complex plans.

### 5.1 Forecast Excel slot fidelity

The official forecast template stores `Talep Tamamlama Saati` as a real Excel
`time` value with `h:mm` number formatting. The current output stores a text
value such as `09:00`.

The forecast writer will preserve the DataFrame schema used internally, then
post-process the written workbook so slot cells are real Excel time values and
forecast desi cells use the template's numeric format. The round-trip validator
must normalize time objects back to canonical `HH:MM` before schema validation.

### 5.2 Declared arrival consistency

The referee currently recomputes arrival from departure and lane travel time but
does not compare it with declared `Varış Tarihi` and `Varış Saati`.

`parse_legs` will retain declared arrival. `trace_vehicle` will report a
violation when declared arrival differs from recomputed arrival. The check is
strict to whole minutes because all travel durations are already rounded to an
integer minute.

### 5.3 Declared cost consistency

The current convention remains unchanged during this initiative:

```text
Toplam maliyet row = allocated vehicle cost + row SLA penalty
```

The full `Toplam maliyet` column therefore sums to simulator total cost. Stage 0
will add an explicit reconciliation assertion after plan generation rather than
change this convention without a jury answer.

## 6. Stage 1: Same-Lane Repair

This is the first cost-reduction stage because it has the best demonstrated
risk-to-value ratio and does not introduce new route topology.

### 6.1 Candidate donors

Consider loaded non-Tir spot legs in ascending fill ratio. Rented legs are never
deleted. Tir legs are initially excluded because moving Tir cargo can change
visit-day feasibility and physical reuse semantics.

### 6.2 Candidate receivers

A receiver must:

- Have the same origin and destination as the donor.
- Be a loaded spot or rented leg.
- Start no earlier than every moved part's ready time.
- Have sufficient vehicle capacity after insertion.
- Preserve all transfer-predecessor and transfer-successor timing.

Receiver search includes later waves and later days. Waiting is allowed because
SLA is a priced soft constraint, but its exact penalty is included.

### 6.3 Move granularity

Stage 1 moves whole physical parts only. It does not create new split pieces.
This captures the main benefit of deleting underfilled trips while keeping the
split-origin contract out of the first repair implementation. Origin-only split
moves may be designed later as a separately measured extension.

### 6.4 Exact move delta

For each receiver insertion, recompute:

- Receiver handling duration.
- Receiver departure, arrival and unload completion when its schedule changes.
- Receiver vehicle cost.
- SLA penalty for every part already on the receiver.
- Handling-ledger deltas at both centers and all affected days.
- Transfer timing for moved and existing parts.

If all donor parts are placed, remove the donor and subtract its full vehicle
cost and penalties. Accept only a strictly negative total-cost delta.

### 6.5 Validation boundary

Local calculations are a fast pre-filter, not the final referee. Accepted moves
are applied to a copied leg set. After each deterministic pass, the complete
plan is scheduled and simulated. The pass is committed only if the global
acceptance gate passes.

## 7. Stage 2: Q&A-Correct Milk-Run

Stage 2 connects and hardens the existing `src/milkrun.py` implementation.

### 7.1 Scope

Initial scope is direct, loaded, non-Tir spot legs with:

- A common origin.
- Compatible departure day and readiness.
- Different final destinations.
- Total load fitting one Kamyonet, Hafif Kamyon or Kamyon.
- At most four destination stops.

Rented and Tir vehicles remain excluded in v1.

### 7.2 Chain identity

All legs in one milk-run receive the same physical `Araç ID` and vehicle type.
A part carried through multiple stops keeps the same item ID and desi on every
leg until its destination.

The scheduler will assign IDs by physical `chain_id`, not by leg. Item suffixes
will be assigned by unique physical part identity, not by row occurrence.

### 7.3 Handling semantics

At the origin, all onboard cargo is loaded once. At each destination, only cargo
delivered at that destination is unloaded. Cargo remaining onboard has zero
intermediate unload and reload handling.

Declared row handling follows the jury's desi-share answer:

- Origin load share is declared on the first leg.
- Final unload share is declared on the leg where the part is delivered.
- Stay-onboard intermediate handling is zero.

### 7.4 Chain cost declaration

The referee charges one continuous physical usage interval from first load
start to final unload completion plus all traversed distance.

The scheduler will compute this vehicle-chain cost once and distribute it once
across the chain's physical delivered parts. It must not duplicate cost on each
onboard row or leg. Row allocations plus SLA must reconcile to simulator total.

### 7.5 Acceptance

A milk-run replaces separate direct legs only when:

- Exact chain vehicle cost plus exact SLA is lower.
- Handling and Tir ledgers remain valid.
- Every part route remains continuous.
- The full scheduled output passes the global acceptance gate.

## 8. Stage 3: Strict One-Hub Repair

Stage 3 adds the higher-complexity move demonstrated by the friend solution,
but uses our stricter split and route contracts.

### 8.1 Topology

For a donor part on `O -> D`, search existing compatible legs:

```text
O -> H
H -> D
```

The initial implementation inserts cargo only into already-existing legs. It
does not create two new spot trips, which keeps the move focused on deleting an
underfilled donor.

### 8.2 Hub restrictions

The initial candidate set is `{Istanbul, Yalova, Eskisehir, Kocaeli, Mersin}`.
Both directed matrix legs must exist, and total path distance must be at most
1.15 times direct distance. A later expansion of the hub set is a separately
measured tuning change, not part of Stage 3 v1.

### 8.3 Piece contract

The same physical part, ID and desi appear on both legs. No new split ID begins
at H. If a donor part must be divided, division occurs at O before either child
enters the first leg.

### 8.4 Timing and capacity

The second-leg load starts no earlier than first-leg unload completion. Both
receiver vehicles are recomputed after insertion. Hub handling consumes one
unload and one load for transferred cargo, with proportional midnight splitting
where applicable.

The exact cost delta includes both receiver vehicle changes, all affected SLA
changes and removal of the donor trip.

## 9. Stage 4: Deterministic Parameter Tuning

After structural improvements stabilize, perform this deterministic sweep over
the existing heuristic thresholds:

- `TIR_MIN_DESI`: 10,000, 12,000 and 14,000.
- `MAX_CARRY_DESI`: 2,800, 4,200 and 5,600.
- `CARRY_VAR_TL`: 0.06, 0.12 and 0.18.
- `MAX_TIR_PER_LANE`: 2 and 3.

Each configuration runs against the identical forecast and full referee. Search
space remains intentionally small; structural optimization has higher expected
value than broad parameter fitting.

The selected configuration is the minimum-cost zero-violation result, with
deterministic tie-breaking toward fewer vehicles and then shorter runtime.

## 10. Architecture Boundaries

### 10.1 Baseline construction

`src/optimize.py` remains responsible for initial rented and spot leg creation.

### 10.2 Improvement passes

Improvement logic must not be added directly into the initial daily loop. It
will live behind explicit functions operating on `list[PlannedLeg]`, for example:

```text
repair_same_lane(legs, data) -> candidate legs + metrics
milk_run_improve(legs, data) -> candidate legs + metrics
repair_one_hub(legs, data) -> candidate legs + metrics
```

Each pass is deterministic and independently testable.

### 10.3 Scheduling and scoring

`src/schedule.py` owns physical chain IDs, row declarations and timestamps.
`src/simulator.py` remains the final source of truth for feasibility and score.

A shared evaluation helper may deep-copy legs before scheduling because the
scheduler currently mutates leg timestamps and IDs during handling repair.

## 11. Failure Handling and Reversibility

- Improvement passes operate on copied state.
- A failed local move is discarded without partial ledger mutation.
- A pass producing any simulator violation is rejected in full.
- A pass with equal or higher total cost is rejected in full.
- The last accepted baseline remains reproducible and writable at every stage.
- Runtime exceptions must not overwrite the last accepted output files; output
  writing occurs only after acceptance.

## 12. Test Strategy

Development follows test-driven implementation for every stage.

### Stage 0 tests

- Forecast slot round-trip preserves real Excel time cells and grid validation.
- A wrong declared arrival is rejected by the simulator.
- Existing correct outputs retain zero violations.

### Stage 1 tests

- A donor trip is deleted when all cargo fits a cheaper same-lane receiver.
- A move is rejected when capacity, readiness, transfer timing or handling
  capacity fails.
- SLA changes for existing receiver cargo are included in the delta.
- No move may increase total cost.

### Stage 2 tests

- All chain legs share one vehicle ID and type.
- Stay-onboard cargo has no intermediate handling.
- Part ID and desi remain constant through the chain.
- Chain cost is counted and declared once.
- Milk-run is rejected when SLA or handling cost removes the saving.

### Stage 3 tests

- Same part ID and desi appear on both transfer legs.
- Second-leg loading cannot precede first-leg unload completion.
- Hub handling is charged twice and midnight splitting remains exact.
- New split IDs cannot first appear at the hub.

### Full acceptance tests

- `python -m pytest` passes.
- `python run.py` completes.
- Both Excel outputs pass schema and round-trip validation.
- Simulator violations are zero.
- Forecast rows, IDs and total desi match the fixed baseline.
- Candidate total cost is strictly below the previous accepted baseline.

## 13. Rollout Order

The implementation order is fixed:

1. Stage 0: submission and referee hardening.
2. Stage 1: same-lane repair.
3. Stage 2: milk-run chain plumbing and activation.
4. Stage 3: strict one-hub repair.
5. Stage 4: deterministic parameter tuning.

No later stage begins until the previous stage has a measured accepted baseline.

## 14. Success Criteria

Minimum success is any reproducible cost reduction below 16,480,959.77 TL with
the forecast unchanged and zero violations.

The engineering target after repair, milk-run and hub insertion is a total cost
in the 14-15 million TL range. This target is directional, not an acceptance
requirement; correctness and measured improvement take precedence over a target
number.
