# Stage 1 Same-Lane Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deterministically move complete direct parts from underfilled non-Tir Spot donors into one existing same-lane receiver, then publish only a forecast-identical, zero-violation plan that saves at least 1.00 TL at raw precision.

**Architecture:** Keep `src/optimize.py` limited to initial daily rented/Spot construction. Add `src/evaluation.py` as the copy-owned scheduling, referee, metric, fingerprint, acceptance, and artifact boundary; add `src/repair.py` as the exact local proposal, complete-ledger transaction, and global Stage 1 decision boundary. `run.py` builds from the original in-memory forecast, referees a staged Excel reload, and calls rollback-safe publication only after every in-memory and artifact gate passes.

**Tech Stack:** Python 3.11+, pandas 2.0+, openpyxl 3.1+, pytest 8.0+, and standard-library `copy`, `dataclasses`, `datetime`, `decimal`, `fractions`, `pathlib`, `shutil`, and `tempfile`.

## Global Constraints

- Fixed accepted Stage 0 entry: 4,046 forecast rows, 4,977,975 desi, 1,269 legs, 126 rented, 1,143 Spot, 3,167 plan rows, 15,460,592.57 TL vehicle, 1,020,367.20 TL SLA, 16,480,959.77 TL total, zero violations, 186 current tests.
- Stage 1 accepts only when baseline and candidate both have zero violations and `Decimal(str(baseline_total)) - Decimal(str(candidate_total)) >= Decimal("1.00")`. Do not quantize before comparing.
- Preserve every forecast ID and row-level OD/date/slot/desi value. Canonicalize slot with `_canonical_forecast_time` and desi with `Decimal(str(value))`.
- Keep improvement logic out of `src/optimize.py`'s daily loop. Do not import, modify, call, or activate `src/milkrun.py`.
- Run one deterministic sweep; do not add random/convergence loops, new trips/routes/types, split creation, partial donor commits, or multi-receiver distribution.
- Donors are loaded Spot non-Tir legs ordered by exact `Fraction` fill and semantic keys. Rented legs are never removed.
- Receivers are loaded Spot/rented legs on the same directed OD, on any wave/day, with any current type including Tir, and sufficient current-type capacity.
- Move only direct parts: `chain_id is None`, every `part.dest == leg.dest`, and every Part object occurs in exactly one leg. Shared/transfer/milk-run parts remain unchanged, so predecessor/successor timing cannot be altered by Stage 1.
- Move complete existing `(Part, desi)` tuples. Never call `Part.piece()` or merge by textual ID.
- A changed receiver cannot later be a donor; it may receive multiple donors sequentially.
- Rank receiver proposals by most-negative exact Decimal delta, then semantic key. Never sort by Python object ID; identity is used only for shared-occurrence counts.
- Spot receiver: `load_start=max(old_load_start, latest_ready)`. Rented receiver: preserve old dep when `old_dep - new_handling >= latest_ready`, else use `load_start=latest_ready`, `dep=latest_ready+new_handling`.
- Recompute exact current-kind vehicle cost and SLA for old donor, old receiver, all existing receiver parts, and moved parts. Local acceptance is strictly `delta_tl < Decimal("0")`.
- Build fresh complete HandlingLedger and TirLedger instances before applying every proposal. Any readiness/capacity/ledger failure rejects without mutation.
- The independent simulator is the global feasibility/score authority. Rejection selects the pristine scheduled baseline.
- Keep official `out/*.xlsx` untouched while forecast, baseline, candidate, and selected-plan artifacts are staged under a temporary directory in `out/`.
- Publish plan first and immutable forecast second. On an ordinary `Exception`, restore both old files byte-for-byte, or remove destinations that were initially absent.
- Do not stage/commit/clean/revert. Preserve unrelated dirty changes. Use scoped snapshots and review checkpoints instead of commits.
- Update `PLAN.md` only after fresh acceptance. Do not update `ARCHITECTURE.md`, `ROADMAP.md`, or `docs/comparison/*`.

---

## Exact File And Interface Map

| Path | Action | Responsibility |
|---|---|---|
| `src/evaluation.py` | Create | Copy/schedule/referee boundary, fingerprint, metrics, Decimal gate, artifact verification. |
| `src/repair.py` | Create | Receiver math, deterministic complete-ledger sweep, repair metrics, Stage 1 decision. |
| `src/export.py` | Modify | Rollback-safe plan-first two-workbook publication. |
| `run.py` | Modify | Same-parent staging, fixed-baseline gate, artifact evaluation, final publication. |
| `tests/test_evaluation.py` | Create | Evaluation/fingerprint/metrics/acceptance/artifact tests. |
| `tests/test_same_lane_repair.py` | Create | Pricing/eligibility/ledger/conservation/determinism/rollback tests. |
| `tests/test_export.py` | Modify | Publication success/failure restoration tests. |
| `tests/test_optimize.py` | Modify | Global decision, run/publication, full-horizon seams only. |
| `PLAN.md` | Modify last | Fresh accepted Stage 1 evidence. |
| `docs/superpowers/reports/2026-07-24-stage1-same-lane-repair-acceptance.md` | Create last | Acceptance evidence and worktree review. |

```text
@dataclass
PlanEvaluation(legs: list[PlannedLeg], plan_frame: pd.DataFrame,
               result: SimResult, notes: tuple[str, ...])

@dataclass(frozen=True)
PlanMetrics(vehicle_cost: Decimal, sla_penalty: Decimal, total_cost: Decimal,
            rented_legs: int, spot_legs: int,
            vehicle_mix: tuple[tuple[str, int], ...],
            average_spot_fill: Fraction, spot_below_30_percent: int,
            violations: int)

forecast_fingerprint(df: pd.DataFrame) -> tuple
plan_fingerprint(df: pd.DataFrame) -> tuple
evaluate_legs(legs: list[PlannedLeg], forecast_df: pd.DataFrame, data,
              *, fix: bool = True) -> PlanEvaluation
summarize_evaluation(evaluation: PlanEvaluation, data) -> PlanMetrics
improvement_tl(baseline: PlanEvaluation, candidate: PlanEvaluation) -> Decimal
accepts_candidate(baseline: PlanEvaluation, candidate: PlanEvaluation,
                  minimum_saving: Decimal = Decimal("1.00")) -> bool
verify_plan_artifact(plan_path: str | Path, forecast_path: str | Path, data,
                     *, expected_total: Decimal,
                     expected_forecast_fingerprint: tuple,
                     expected_plan_fingerprint: tuple,
                     tolerance: Decimal = Decimal("0.01")) -> SimResult

@dataclass(frozen=True)
RepairMetrics(donors_considered: int, moves_accepted: int, parts_moved: int,
              desi_moved: int, spot_legs_removed: int,
              local_saving_tl: Decimal)

repair_same_lane(legs: list[PlannedLeg], data)
    -> tuple[list[PlannedLeg], RepairMetrics]

@dataclass(frozen=True)
Stage1Decision(baseline: PlanEvaluation, candidate: PlanEvaluation,
               selected: PlanEvaluation, repair_metrics: RepairMetrics,
               accepted: bool, saving_tl: Decimal)

run_same_lane_stage(legs: list[PlannedLeg], forecast_df: pd.DataFrame, data)
    -> Stage1Decision

publish_workbooks(staged_plan: str | Path, staged_forecast: str | Path,
                  plan_destination: str | Path,
                  forecast_destination: str | Path) -> tuple[Path, Path]
```

Existing interfaces stay unchanged: `PlannedLeg`, `Part`, `to_plan_frame`, `validate_plan`, `simulate`, `require_plan_total`, `HandlingLedger`, `TirLedger`, `_canonical_forecast_time`, `handling_minutes`, `travel_minutes`, and `late_hours`.

---

### Task 1: Shared Evaluation, Fingerprint, Metrics, And Acceptance Boundary

**Files:**
- Create: `src/evaluation.py`
- Create: `tests/test_evaluation.py`

**Interfaces:**
- Produces all mapped evaluation interfaces except `verify_plan_artifact`, added in Task 5.
- `evaluate_legs` owns the only scheduling copy and never mutates caller legs.

- [ ] **Step 1: Capture scoped pre-task state**

```powershell
git status --short -- src/evaluation.py tests/test_evaluation.py
git diff --no-ext-diff -- src/evaluation.py tests/test_evaluation.py
```

- [ ] **Step 2: Write failing tests**

Create real-data helpers for one direct `İstanbul -> Yalova` Kamyonet and exact `FORECAST_COLS`. Add:

| Test | Exact assertion |
|---|---|
| `test_fingerprint_normalizes_slot_and_desi` | `"09:00"`/`time(9)` and `38`/`38.0` are equal. |
| `test_fingerprint_is_order_independent` | Reversing distinct rows is equal. |
| `test_fingerprint_detects_each_row_value` | Parametrize ID/date/slot/origin/dest/desi changes; every change differs. |
| `test_evaluate_deep_copies_once_without_source_mutation` | Monkeypatch module `deepcopy`; one call, nested Part copied, source equal, tuple notes, exact plan columns. |
| `test_evaluate_returns_violations` | Forecast 101 vs plan 100 retains delivery violation. |
| `test_evaluate_raises_schema_error` | Inject validator error; `ValueError` contains it. |
| `test_evaluate_raises_reconciliation_error` | Inject `require_plan_total` error; it propagates. |
| `test_metrics_use_unweighted_exact_fill` | 2800/5600 and 3600/7200 average to `Fraction(1, 2)`; sorted mix/counts/Decimal costs exact. |
| `test_strict_below_thirty_percent` | 1679/5600 counts, 1680/5600 does not. |
| `test_raw_inclusive_saving` | `0.999999`, `1.00`, `1.000001` map to false/true/true. |
| `test_both_sides_require_zero_violations` | Violation on either side rejects 10 TL saving. |

- [ ] **Step 3: Run red**

Run: `python -m pytest tests/test_evaluation.py -q`

Expected: `ModuleNotFoundError: No module named 'src.evaluation'`.

- [ ] **Step 4: Implement minimal evaluation code**

Implement these exact algorithms:

```text
_finite_decimal(value, label): Decimal(str(value)); reject conversion errors,
non-finite values, and preserve full precision.

forecast_fingerprint(df): require exact FORECAST_COLS; for every row build
(str(ID), str(date), canonical_slot, str(origin), str(dest), Decimal desi);
reject invalid slot/desi; return (tuple(FORECAST_COLS), tuple(sorted(rows))).

evaluate_legs: scheduled=deepcopy(legs) exactly once; call
to_plan_frame(scheduled,data,fix=fix); raise one ValueError containing every
validate_plan error; call simulate; call require_plan_total; return scheduled
legs/frame/result/tuple(notes). Do not raise merely because result has violations.

summarize_evaluation: convert result.vehicle_cost, result.sla_penalty, and
result.total_cost independently with Decimal(str(value)); count all rented/Spot legs;
Fraction(Decimal(str(leg.desi)))/capacity; arithmetic unweighted mean or 0/1;
strict fill < Fraction(3,10); violations=len(result.violations).

improvement_tl: Decimal baseline total minus Decimal candidate total.

accepts_candidate: reject negative/non-finite minimum; return true only when
both violation lists are empty and raw improvement >= minimum.
```

Use the exact dataclass fields/types from the interface map. `PlanMetrics` is frozen; `PlanEvaluation.notes` is always a tuple.

- [ ] **Step 5: Run green**

```bash
python -m pytest tests/test_evaluation.py -q
python -m pytest tests/test_export.py tests/test_simulator_full.py tests/test_optimize.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Scoped review checkpoint**

```powershell
git status --short -- src/evaluation.py tests/test_evaluation.py
git diff --no-index -- NUL src/evaluation.py
git diff --no-index -- NUL tests/test_evaluation.py
```

Review: one graph copy, immutable notes, all six row values, exact Decimal threshold, strict fill threshold, violations returned, malformed schema/cost raised.

---

### Task 2: Pure Receiver Recalculation And Local Proposal Rules

**Files:**
- Create: `src/repair.py`
- Create: `tests/test_same_lane_repair.py`

**Interfaces:**
- Produces `RepairMetrics`, private `_ReceiverProposal`, `_vehicle_cost_tl`, `_sla_penalty_tl`, `_leg_total_tl`, `_recompute_receiver`, `_receiver_proposal`.
- Defers donor sweep and full ledgers to Task 3.

```text
@dataclass(frozen=True)
_ReceiverProposal(receiver: PlannedLeg, delta_tl: Decimal,
                  parts_moved: int, desi_moved: int)
_vehicle_cost_tl(leg: PlannedLeg, data) -> Decimal
_sla_penalty_tl(leg: PlannedLeg) -> Decimal
_leg_total_tl(leg: PlannedLeg, data) -> Decimal
_recompute_receiver(receiver: PlannedLeg,
                    moved_items: list[tuple[Part, int | float]], data)
    -> PlannedLeg | None
_receiver_proposal(donor: PlannedLeg, receiver: PlannedLeg, data)
    -> _ReceiverProposal | None
```

- [ ] **Step 1: Capture scoped pre-task state**

```powershell
git status --short -- src/repair.py tests/test_same_lane_repair.py
git diff --no-ext-diff -- src/repair.py tests/test_same_lane_repair.py
```

- [ ] **Step 2: Write failing pure-helper tests**

Use symmetric 60 km, one-hour `A <-> B` lanes, SLA one day, handling 100,000, Tir cap 100, and current vehicle values:

```text
Tır          capacity 22400; rental 291.6666666666667/h + 13/km; Spot 487.5/h + 25/km
Kamyon       capacity 12000; rental 208.33333333333334/h + 10/km; Spot 318.25/h + 21/km
Hafif Kamyon capacity 7200;  rental 208.33333333333334/h + 10/km; Spot 364.5833333333333/h + 20/km
Kamyonet     capacity 5600;  rental 156.25/h + 6/km; Spot 197.91666666666666/h + 18/km
```

Add:

| Test | Exact assertion |
|---|---|
| `test_spot_retimes_to_latest_ready` | 1000 receiver at 09:00 + 500 ready 17:00 gives load 17:00, dep 17:15, arr 18:15, unload 18:30. |
| `test_rented_preserves_valid_departure` | Receiver dep 17:00 + moved ready 16:40 gives load 16:45 and unchanged dep. |
| `test_rented_delays_invalid_departure` | Moved ready 17:05 gives load 17:05 and dep 17:20. |
| `test_current_kind_rates` | Spot/rented parametrization, including Kamyonet `197.91666666666666`, equals `Decimal(str(rate))` seconds/hour plus km formula and differs from `Decimal(float)` expansion. |
| `test_existing_receiver_sla_is_in_delta` | Existing 5000 deadline 12:00, donor ready 11:00; receiver delay penalty makes proposal reject. |
| `test_capacity_rejects_whole_donor` | 5500 + 101 into Kamyonet returns `None`. |
| `test_delta_must_be_strictly_negative` | Semantic old totals 10/20 and new 30 return `None`. |

- [ ] **Step 3: Run red**

Run: `python -m pytest tests/test_same_lane_repair.py -q`

Expected: module import fails because `src.repair` is absent.

- [ ] **Step 4: Implement exact proposal math**

Use frozen dataclasses from the map and this exact behavior:

```text
_decimal: Decimal(str(value)); reject conversion/non-finite.
_desi_total: sum each tuple via _decimal from Decimal("0").
_whole_desi: require total == total.to_integral_value(), then int(total).

_vehicle_cost_tl:
  hourly/per_km = Spot rates iff kind == "Spot", else rental rates
  seconds = int((unload_end-load_start).total_seconds()); reject negative
  return _decimal(hourly)*Decimal(seconds)/Decimal(3600)
       + _decimal(per_km)*Decimal(lane.km)

_sla_penalty_tl:
  sum _decimal(desi) * Decimal(late_hours(part.deadline, leg.unload_end))
      * Decimal(str(SLA_TL_PER_DESI_HOUR)) for every tuple

_recompute_receiver:
  require loaded Spot/Kiralık receiver
  items = list(receiver.items) + list(moved_items), with no Part creation
  reject total above receiver current-type capacity
  handling = handling_minutes(_whole_desi(total)); latest=max(part.ready)
  apply exact Spot/rented branches from Global Constraints
  arr=dep+travel_minutes(current type); unload=arr+handling
  dataclasses.replace receiver, reset item_ids=[], preserve route/type/trip/ID
  store float(exact vehicle cost) and float(exact SLA) on returned leg

_receiver_proposal:
  require same directed OD
  updated=_recompute_receiver; reject None
  delta=_leg_total_tl(updated)-_leg_total_tl(receiver)-_leg_total_tl(donor)
  reject delta >= 0
  return updated, exact delta, len(donor.items), whole donor desi
```

Do not use stored old penalties/costs in the comparison; recompute them from
scheduled times and rates. Every non-integral numeric value, including Python
float rates and tuple desi, must pass through `_decimal(value) ==
Decimal(str(value))`; direct `Decimal(...)` construction is only for integers.

- [ ] **Step 5: Run green**

```bash
python -m pytest tests/test_same_lane_repair.py -q
python -m pytest tests/test_simulator_cost.py tests/test_ledger.py -q
```

- [ ] **Step 6: Scoped review checkpoint**

```powershell
git status --short -- src/repair.py tests/test_same_lane_repair.py
git diff --no-index -- NUL src/repair.py
git diff --no-index -- NUL tests/test_same_lane_repair.py
```

Review: exact rates/rounding, both rented branches, all receiver SLA, whole-capacity rejection, no Part split/text merge, strict negative Decimal delta.

---

### Task 3: Deterministic Full Repair Sweep With Complete Ledgers

**Files:**
- Modify: `src/repair.py`
- Modify: `tests/test_same_lane_repair.py`

**Interfaces:**
- Produces `_canonical_part_key`, `_canonical_leg_key`, `_trial_ledgers_valid`, public `repair_same_lane`.

```text
_canonical_part_key(item: tuple[Part, int | float]) -> tuple
_canonical_leg_key(leg: PlannedLeg) -> tuple
_trial_ledgers_valid(legs: list[PlannedLeg], data) -> bool
```

- [ ] **Step 1: Capture scoped pre-task state**

```powershell
git status --short -- src/repair.py tests/test_same_lane_repair.py
git diff --no-ext-diff -- src/repair.py tests/test_same_lane_repair.py
```

- [ ] **Step 2: Write failing sweep tests**

Add every named case:

| Test | Exact result |
|---|---|
| `test_donor_deleted_when_complete_move_profitable` | 100 donor + 1000 receiver becomes one leg; move/part/desi/removed = 1/1/100/1; saving positive. |
| `test_capacity_rejection_unchanged` | 101 + 5500 Kamyonet remains two legs, zero move metrics. |
| `test_rented_never_donor` | Proposal donor-kind recorder sees only Spot. |
| `test_readiness_invalid_trial_rejected` | Unchanged malformed ready-after-load leg causes no proposal commit. |
| `test_direct_only_exclusions` | Parametrize chain, wrong `part.dest`, shared Part occurrence; unsafe cargo unchanged. |
| `test_handling_rejection` | Cap 1000; 600 donor day 1 + 600 receiver day 2 would make 1200 day 2; reject. |
| `test_tir_arrival_day_ledger_rejection` | Locally negative 5000 donor retimes 100-desi Spot Tir receiver from B arrival day 1 to day 2, conflicting with rented Tir; reject. |
| `test_tir_receiver_allowed_when_visits_fit` | Same without conflict; accept. |
| `test_later_day_receiver` | 29 Jun donor moves into 1 Jul receiver. |
| `test_whole_parts_conserved_without_piece` | 40/60 donor; patched `Part.piece` raises if called; exact tuples survive. |
| `test_input_nonmutation` | Caller graph equals deep copy after call; returned graph is copied. |
| `test_no_cost_increasing_move` | Nonnegative proposal leaves exact semantic signature. |
| `test_most_negative_then_semantic_receiver` | Controlled -20/-10 and equal-delta reversed-input cases pick required semantic receivers. |
| `test_changed_receiver_not_later_donor` | Track donor IDs; changed receiver absent from donor attempts. |
| `test_receiver_accepts_multiple_donors` | Two accepted sequential donor removals into one receiver. |
| `test_permutation_determinism` | Every permutation produces same semantic signature and metrics. |

The Tir rejection test must first assert `_receiver_proposal` exists, is negative, and changes arrival date; that isolates ledger rejection.

- [ ] **Step 3: Run red**

Run: `python -m pytest tests/test_same_lane_repair.py -q`

Expected: missing sweep/ledger helpers fail.

- [ ] **Step 4: Implement canonical keys and complete ledgers**

```text
part key = (base_id, part_id, ready, deadline, carried_before,
            dest-or-empty, Decimal desi)
leg key = (kind != "Kiralık", dep, origin, dest, vtype, load_start, arr,
           unload_end, chain_id is None, chain_id-or--1, chain_seq,
           tuple(sorted(part keys)))
```

`_trial_ledgers_valid` exact algorithm:

```text
create fresh HandlingLedger(data.handling_cap), TirLedger(data.tir_cap)
reject the proposal if any chain_id is not None; Stage 1 runs before Stage 2
and does not implement chain handling
reject any leg over current-type capacity
for each direct leg:
  reject any part.ready > leg.load_start
  add full desi at origin/load_start and destination/arr
reject handling.violations()
for each Tir leg in canonical order use one stable synthetic vehicle key based
on its canonical position; add origin visit 0 and destination visit 1
return not tir.violations()
```

Part identity is not used by the ledgers. Any chain in the full candidate makes
the Stage 1 local proposal ineligible rather than introducing Stage 2 semantics.

- [ ] **Step 5: Implement one-pass transaction**

```text
copied = deepcopy(legs) once; canonical-sort
occurrences = Counter(
    id(part) for leg in ordered for part, _desi in leg.items)
use occurrences[id(part)] only for shared-count eligibility
working = stable token -> leg; tokens never enter ranking
direct-only = loaded, chain_id None, every dest matches, every occurrence == 1
donors = direct-only Spot non-Tir sorted by
         (Fraction(Decimal total)/current capacity, semantic leg key)
for donor token:
  skip deleted/changed receiver; increment donors_considered
  receivers = current distinct direct-only loaded Spot/Kiralık same-OD legs
  for each negative _receiver_proposal:
    build full trial by removing donor and replacing receiver only
    discard unless _trial_ledgers_valid(canonical trial)
  choose minimum (delta_tl, semantic updated-receiver key)
  if none, mutate nothing
  else atomically replace receiver/delete donor/mark changed;
       moves_accepted += 1, spot_legs_removed += 1,
       parts_moved += chosen.parts_moved, desi_moved += chosen.desi_moved,
       local_saving_tl += -chosen.delta_tl
return canonical working values and frozen metrics
```

`local_saving_tl` is positive savings, so a single `delta_tl == -20` records
`Decimal("20")`. `moves_accepted == spot_legs_removed` must always hold. No
second pass. One receiver may receive again; changed receiver cannot donate.

- [ ] **Step 6: Run green**

```bash
python -m pytest tests/test_same_lane_repair.py -q
python -m pytest tests/test_ledger.py tests/test_simulator_cost.py tests/test_simulator_full.py -q
```

- [ ] **Step 7: Scoped review checkpoint**

```powershell
git status --short -- src/repair.py tests/test_same_lane_repair.py
git diff --no-ext-diff -- src/repair.py tests/test_same_lane_repair.py
git diff --no-index -- NUL src/repair.py
git diff --no-index -- NUL tests/test_same_lane_repair.py
```

Review one accepted/rejected transaction, fresh ledgers before mutation, rollback, donor/receiver rules, exact metrics, identity restriction, canonical output.

---

### Task 4: Global Stage 1 Decision Boundary

**Files:**
- Modify: `src/repair.py`
- Modify: `tests/test_same_lane_repair.py`
- Modify: `tests/test_optimize.py`

**Interfaces:**
- Produces `Stage1Decision` and `run_same_lane_stage`.

- [ ] **Step 1: Capture scoped pre-task state**

```powershell
git status --short -- src/repair.py tests/test_same_lane_repair.py tests/test_optimize.py
git diff --no-ext-diff -- src/repair.py tests/test_same_lane_repair.py tests/test_optimize.py
git diff --no-index -- NUL src/repair.py
git diff --no-index -- NUL tests/test_same_lane_repair.py
git diff --no-index -- NUL tests/test_optimize.py
```

- [ ] **Step 2: Write failing decision tests**

Add:

| Test | Exact assertion |
|---|---|
| `test_baseline_evaluated_before_repair` | Call order evaluate fix true, repair receives `baseline.legs`, evaluate fix true. |
| `test_global_violation_rolls_back` | Candidate 50 vs baseline 100 but one violation; saving 50 retained, accepted false, selected baseline. |
| `test_sub_one_tl_rolls_back` | Raw saving 0.999999 selects baseline. |
| `test_stage_input_nonmutation` | Small real build and forecast equal pre-call copies. |

- [ ] **Step 3: Write the real full-horizon integration test**

In `tests/test_optimize.py`, build forecast for 29 Jun through 5 Jul, prepare/build source, then `run_same_lane_stage`. Assert:

```text
forecast: 4046 rows, 4977975 desi, 4046 unique IDs, unchanged fingerprint/frame
source legs unchanged
baseline: 1269 legs, 126 rented, 1143 Spot, 3167 rows
baseline costs quantized: 15460592.57 / 1020367.20 / 16480959.77
baseline violations: 0
decision accepted, selected is candidate, raw saving >= 1.00
candidate total lower, violations 0, require_plan_total passes
every baseline demand part still occurs once with identical desi and destination
candidate rented count remains 126 and Spot count is lower than 1143
```

The test may log D00082's before/after location for diagnosis, but must not fail
if another deterministic profitable packing consumes its prior witness receiver.
Treat 16,454,285.85 TL and 26,673.93 TL as prior targeted-witness evidence, not
general-pass exact assertions.

- [ ] **Step 4: Run red**

```bash
python -m pytest tests/test_same_lane_repair.py::test_baseline_evaluated_before_repair tests/test_same_lane_repair.py::test_global_violation_rolls_back tests/test_optimize.py::test_full_horizon_same_lane_stage_accepts_fixed_stage0_baseline -v
```

Expected: missing `Stage1Decision`/`run_same_lane_stage` fails collection.

- [ ] **Step 5: Implement exact decision**

```python
@dataclass(frozen=True)
class Stage1Decision:
    baseline: PlanEvaluation
    candidate: PlanEvaluation
    selected: PlanEvaluation
    repair_metrics: RepairMetrics
    accepted: bool
    saving_tl: Decimal


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
```

Never select locally repaired but globally unevaluated legs.

- [ ] **Step 6: Run green**

```bash
python -m pytest tests/test_evaluation.py tests/test_same_lane_repair.py -q
python -m pytest tests/test_optimize.py::test_full_horizon_same_lane_stage_accepts_fixed_stage0_baseline -v
python -m pytest tests/test_optimize.py tests/test_simulator_full.py tests/test_export.py -q
```

- [ ] **Step 7: Scoped review checkpoint**

```powershell
git status --short -- src/repair.py tests/test_same_lane_repair.py tests/test_optimize.py
git diff --no-ext-diff -- src/repair.py tests/test_same_lane_repair.py tests/test_optimize.py
git diff --no-index -- NUL src/repair.py
git diff --no-index -- NUL tests/test_same_lane_repair.py
git diff --no-index -- NUL tests/test_optimize.py
```

Review: pristine baseline first, repair scheduled copy, candidate globally evaluated, only acceptance helper selects, full-horizon fixed baseline and witness covered.

---

### Task 5: Artifact Referee, Rollback Publication, And `run.py` Integration

**Files:**
- Modify: `src/evaluation.py`
- Modify: `src/export.py`
- Modify: `run.py`
- Modify: `tests/test_evaluation.py`
- Modify: `tests/test_export.py`
- Modify: `tests/test_optimize.py`

**Interfaces:**
- Produces `verify_plan_artifact`, `publish_workbooks`, private `_require_stage0_entry`, `_print_decision_metrics`, `_stage_and_publish`.

```text
_require_stage0_entry(forecast_frame: pd.DataFrame,
                      evaluation: PlanEvaluation, data) -> None
_print_decision_metrics(decision: Stage1Decision, data,
                        runtime_seconds: float) -> None
_stage_and_publish(decision: Stage1Decision, staged_forecast_path: Path,
                   expected_fingerprint: tuple, data, staging_dir: Path,
                   output_dir: Path) -> None
```

- [ ] **Step 1: Capture scoped pre-task state**

```powershell
git status --short -- src/evaluation.py src/export.py run.py tests/test_evaluation.py tests/test_export.py tests/test_optimize.py
git diff --no-ext-diff -- src/evaluation.py src/export.py run.py tests/test_evaluation.py tests/test_export.py tests/test_optimize.py
git diff --no-index -- NUL src/evaluation.py
git diff --no-index -- NUL tests/test_evaluation.py
git diff --no-index -- NUL tests/test_optimize.py
```

- [ ] **Step 2: Write failing artifact tests**

Use no-rental A/B synthetic data, a valid one-row forecast/workbook, and a matching evaluated plan/workbook. Add:

| Test | Exact assertion |
|---|---|
| `test_artifact_reloads_and_resimulates` | Returned result has zero violations and exact expected total. |
| `test_artifact_detects_forecast_change` | Increment reloaded desi by one; fingerprint error. |
| `test_artifact_total_tolerance` | Expected difference 0.01 accepted; 0.010001 rejected. |
| `test_artifact_declared_reconciliation` | Add 1 TL to declared row; reconciliation error. |
| `test_artifact_rejects_violation` | Change declared arrival to 23:59; artifact violation error. |

- [ ] **Step 3: Write failing publication tests**

Add to `tests/test_export.py`:

```text
test_publish_success_plan_then_forecast:
  staged bytes new-plan/new-forecast; old destinations exist
  wrap os.replace; assert first calls are staged plan->official plan,
  staged forecast->official forecast; returned tuple and bytes exact

test_publish_second_failure_restores_both:
  monkeypatch second staged-source os.replace to raise OSError
  assert old-plan and old-forecast bytes restored

test_publish_failure_removes_absent_destinations:
  both official files initially absent; inject second failure
  assert both destinations absent afterward
```

- [ ] **Step 4: Write failing run/publication seam tests**

Add to `tests/test_optimize.py`:

| Test | Exact assertion |
|---|---|
| `test_rejected_stage_never_publishes` | Existing official bytes unchanged; baseline is staged/verified; candidate plan and `publish_workbooks` are not called; RuntimeError contains raw saving. |
| `test_all_artifacts_precede_publication` | Accepted event sequence is write/verify baseline, write/verify selected candidate plan, publish. |
| `test_main_uses_memory_forecast_and_reloaded_referee` | Monkeypatch distinct but fingerprint-equal frames; `prepare_frame` receives original object and `run_same_lane_stage` receives reloaded object. |
| `test_sub_one_tl_artifact_saving_never_publishes` | In-memory decision is accepted, staged baseline/candidate results differ by 0.999999 TL, official bytes stay unchanged, and `publish_workbooks` is not called. |

- [ ] **Step 5: Run red**

```bash
python -m pytest tests/test_evaluation.py::test_artifact_reloads_and_resimulates tests/test_export.py::test_publish_second_failure_restores_both tests/test_optimize.py::test_rejected_stage_never_publishes -v
```

Expected: missing artifact/publication/run helpers fail.

- [ ] **Step 6: Implement artifact verification**

```text
verify_plan_artifact:
  convert tolerance with _finite_decimal; reject negative
  pd.read_excel both paths
  require forecast_fingerprint(reloaded forecast) == expected fingerprint
  validate_plan reloaded plan; raise with all errors
  simulate reloaded plan against reloaded forecast
  require zero violations; raise with all violations
  require abs(Decimal(str(result.total_cost))-expected_total) <= tolerance
  require_plan_total(reloaded plan, result.total_cost, tolerance=tolerance)
  return result
```

- [ ] **Step 7: Implement rollback-safe publication**

Implement exact transaction:

```text
sources=(Path(staged_plan), Path(staged_forecast))
destinations=(Path(plan_destination), Path(forecast_destination))
require both source files, distinct four paths, same official parent
mkdir official parent
TemporaryDirectory(prefix=".publish-", dir=official_parent)
copy2 every existing destination to indexed backup before replacing anything
try:
  os.replace(staged_plan, plan_destination)
  os.replace(staged_forecast, forecast_destination)
except Exception as publication_error:
  for each destination:
    if it existed: os.replace(backup, destination)
    else: destination.unlink(missing_ok=True)
  if rollback raises, raise RuntimeError listing destination/errors from
  publication_error; otherwise re-raise publication_error
return (plan_destination, forecast_destination)
```

Catch `Exception`, not `BaseException`. Backup failure occurs before official replacement.

- [ ] **Step 8: Implement staged `run.py` flow**

Add fixed constants for every Stage 0 metric. `_require_stage0_entry` checks exact row/desi/ID set `D00001..D04046`, leg/count/row values, zero violations, and each cost within Decimal 0.01; collect all mismatches into one RuntimeError.

Implement `_stage_and_publish` exactly:

```text
write Stage0-baseline.xlsx; capture baseline_artifact_result from verification
if not decision.accepted: raise RuntimeError with raw saving; write no candidate
plan and publish nothing
write Tasima-plani.xlsx from selected candidate; capture candidate_artifact_result
from verification
artifact_saving = Decimal(str(baseline_artifact_result.total_cost))
                  - Decimal(str(candidate_artifact_result.total_cost))
if artifact_saving < Decimal("1.00"): raise RuntimeError and publish nothing
publish_workbooks(staged selected plan, staged forecast,
                  official plan, official forecast)
```

Rewrite `main()` in this order:

```text
load data; build forecast_frame in memory; fingerprint it
OUT_DIR.mkdir; TemporaryDirectory(prefix=".stage1-", dir=OUT_DIR)
write forecast only into temp; pd.read_excel staged forecast; require fingerprint
prepare/build legs from original forecast_frame
run_same_lane_stage(legs, staged_reloaded_forecast, data)
require fixed Stage 0 entry
summarize/print baseline and candidate vehicle/SLA/total, rented/Spot counts,
sorted mix, unweighted fill, <30% count, violations; print repair metrics,
raw saving, accepted flag, Stage 1 runtime
call _stage_and_publish
print completion only after publication returns
```

Remove the old early official forecast write, direct scheduling/simulation, and direct official plan write. All evaluation must precede publication.

- [ ] **Step 9: Run green**

```bash
python -m pytest tests/test_evaluation.py tests/test_export.py -q
python -m pytest tests/test_optimize.py::test_rejected_stage_never_publishes tests/test_optimize.py::test_all_artifacts_precede_publication tests/test_optimize.py::test_main_uses_memory_forecast_and_reloaded_referee tests/test_optimize.py::test_sub_one_tl_artifact_saving_never_publishes -v
python -m pytest tests/test_same_lane_repair.py tests/test_optimize.py -q
```

- [ ] **Step 10: Scoped review checkpoint**

```powershell
git status --short -- src/evaluation.py src/export.py run.py tests/test_evaluation.py tests/test_export.py tests/test_optimize.py
git diff --no-ext-diff -- src/evaluation.py src/export.py run.py tests/test_evaluation.py tests/test_export.py tests/test_optimize.py
git diff --no-index -- NUL src/evaluation.py
git diff --no-index -- NUL tests/test_evaluation.py
git diff --no-index -- NUL tests/test_optimize.py
```

Review: original optimizer forecast vs reloaded referee forecast, fixed baseline,
candidate artifact match, raw staged-artifact saving at least 1.00 TL, all
evaluation before publication, plan-first order, restoration for existing/absent
files, official paths untouched on rejection.

---

### Task 6: Full-Horizon Acceptance, Outputs, `PLAN.md`, And Final Review

**Files:**
- Verify: `src/evaluation.py`
- Verify: `src/repair.py`
- Verify: `src/export.py`
- Verify: `run.py`
- Verify: `tests/test_evaluation.py`
- Verify: `tests/test_same_lane_repair.py`
- Verify: `tests/test_export.py`
- Verify: `tests/test_optimize.py`
- Replace only after acceptance: `out/Tasima-plani.xlsx`, `out/Talep-tahmini.xlsx`
- Modify only after acceptance: `PLAN.md`
- Create only after acceptance: `docs/superpowers/reports/2026-07-24-stage1-same-lane-repair-acceptance.md`

**Interfaces:**
- Consumes Tasks 1-5; produces accepted workbooks and exact evidence only.

- [ ] **Step 1: Capture pre-acceptance worktree**

```powershell
git status --short
git diff --no-ext-diff -- src/evaluation.py src/repair.py src/export.py run.py tests/test_evaluation.py tests/test_same_lane_repair.py tests/test_export.py tests/test_optimize.py PLAN.md
```

- [ ] **Step 2: Run focused acceptance tests**

```bash
python -m pytest tests/test_evaluation.py tests/test_same_lane_repair.py tests/test_export.py tests/test_optimize.py -q
```

Expected: zero failures, including full-horizon, artifact, and rollback tests.

- [ ] **Step 3: Run full suite**

Run: `python -m pytest -q`

Expected: exit 0; record exact count/runtime. Accepted count is greater than entry count 186.

- [ ] **Step 4: Run complete pipeline**

Run: `python run.py`

Require: fixed Stage 0 metrics; fingerprint equality; candidate raw saving at least 1.00; both violation counts zero; declared reconciliation; Stage 1 accepted; publication succeeds plan first.

- [ ] **Step 5: Verify official workbook identity/type/schema**

Run:

```powershell
python -c "from datetime import date,time; import pandas as pd; from openpyxl import load_workbook; from src.data import load_all; from src.evaluation import forecast_fingerprint; from src.forecast import forecast_horizon,to_forecast_frame; from src.schemas import FORECAST_COLS,validate_forecast_grid; d=load_all(); w=load_workbook('out/Talep-tahmini.xlsx'); s=w.active; assert isinstance(s['C2'].value,time); assert s['C2'].number_format=='h:mm'; assert s['F2'].number_format=='0.000'; f=pd.read_excel('out/Talep-tahmini.xlsx'); expected=to_forecast_frame(forecast_horizon(d.demand,date(2026,6,29),date(2026,7,5))); assert list(f.columns)==FORECAST_COLS; assert validate_forecast_grid(f,d,date(2026,6,29),date(2026,7,5))==[]; assert len(f)==4046; assert f['Talep ID'].nunique()==4046; assert int(f['Tahmin Edilen Desi'].sum())==4977975; assert forecast_fingerprint(f)==forecast_fingerprint(expected); print(type(s['C2'].value).__name__,s['C2'].number_format,s['F2'].number_format,len(f),f['Talep ID'].nunique(),int(f['Tahmin Edilen Desi'].sum()))"
python -c "from datetime import date,timedelta; from decimal import Decimal; import pandas as pd; from src.data import load_all; from src.evaluation import forecast_fingerprint,plan_fingerprint,verify_plan_artifact; from src.export import require_plan_total; from src.forecast import forecast_horizon,to_forecast_frame; from src.optimize import build_plan,prepare_frame; from src.repair import run_same_lane_stage; from src.schemas import PLAN_COLS,validate_plan; from src.simulator import simulate; d=load_all(); f=pd.read_excel('out/Talep-tahmini.xlsx'); p=pd.read_excel('out/Tasima-plani.xlsx'); memory=to_forecast_frame(forecast_horizon(d.demand,date(2026,6,29),date(2026,7,5))); days=[date(2026,6,29)+timedelta(days=i) for i in range(7)]; source=build_plan(d,prepare_frame(memory),days); decision=run_same_lane_stage(source,f,d); baseline=decision.baseline.result; candidate=simulate(p,f,d); saving=Decimal(str(baseline.total_cost))-Decimal(str(candidate.total_cost)); expected_plan_fingerprint=plan_fingerprint(decision.selected.plan_frame); assert list(p.columns)==PLAN_COLS; assert validate_plan(p,d)==[]; assert decision.accepted; assert decision.selected is decision.candidate; assert baseline.violations==[]; assert Decimal(str(baseline.total_cost)).quantize(Decimal('0.01'))==Decimal('16480959.77'); assert candidate.violations==[]; assert saving>=Decimal('1.00'); assert plan_fingerprint(p)==expected_plan_fingerprint; require_plan_total(p,candidate.total_cost); artifact=verify_plan_artifact('out/Tasima-plani.xlsx','out/Talep-tahmini.xlsx',d,expected_total=Decimal(str(decision.selected.result.total_cost)),expected_forecast_fingerprint=forecast_fingerprint(f),expected_plan_fingerprint=expected_plan_fingerprint); assert artifact.violations==[]; print(f'{baseline.total_cost:.12f}',f'{candidate.vehicle_cost:.2f}',f'{candidate.sla_penalty:.2f}',f'{candidate.total_cost:.12f}',len(candidate.violations),saving)"
```

Expected first output: `time h:mm 0.000 4046 4046 4977975`; the second prints raw baseline, candidate vehicle/SLA/raw total, zero violations, and raw saving at least 1.00.

- [ ] **Step 6: Write exact acceptance report**

Verify and create the report directory before adding the file:

```powershell
$parentExists = Test-Path -LiteralPath "docs/superpowers"
if (-not $parentExists) { throw "Expected docs/superpowers parent is missing" }
New-Item -ItemType Directory -Path "docs/superpowers/reports" -Force
```

Create `docs/superpowers/reports/2026-07-24-stage1-same-lane-repair-acceptance.md` with header `# Stage 1 Same-Lane Repair Acceptance Report`. Record exact fresh values for:

- fixed baseline and candidate vehicle/SLA/total, rented/Spot counts, sorted mix, unweighted Spot fill, strict-below-30% count, violations;
- donors considered, moves, parts/desi moved, Spot legs removed, exact local/global Decimal savings;
- focused/full test commands, exact count/runtimes, pipeline runtime;
- forecast fingerprint/ID/desi/type/schema proof, declared reconciliation, artifact re-simulation;
- D00082 before/after location when available; label 16,454,285.85 and 26,673.93 as non-gating prior witness evidence only;
- publication success/order and rollback test names;
- final diff/status review and unrelated pre-existing dirty paths.

If any value is unavailable, rerun its command; do not write partial evidence.

- [ ] **Step 7: Update `PLAN.md` only now**

Add evaluation/repair to architecture while keeping milk-run inactive. Preserve Stage 0 table; add exact Stage 1 metrics/raw saving/runtime. Replace 186/current runtime with fresh values. Record fingerprint/artifact/publication gates. Mark same-lane repair complete and milk-run next. Do not edit older architecture/roadmap/comparison documents.

- [ ] **Step 8: Final verification**

```bash
python -m pytest tests/test_evaluation.py tests/test_same_lane_repair.py tests/test_export.py tests/test_optimize.py -q
python -m pytest -q
git diff --check
git status --short
```

Expected: both pytest commands pass; `git diff --check` exits zero with no whitespace errors (existing LF-to-CRLF warnings may appear); status contains intended uncommitted Stage 1 files plus untouched existing changes.

- [ ] **Step 9: Final scoped reviewer gate**

```powershell
git diff --no-ext-diff -- src/evaluation.py src/repair.py src/export.py run.py tests/test_evaluation.py tests/test_same_lane_repair.py tests/test_export.py tests/test_optimize.py PLAN.md docs/superpowers/reports/2026-07-24-stage1-same-lane-repair-acceptance.md
git status --short
git diff --no-index -- NUL src/evaluation.py
git diff --no-index -- NUL src/repair.py
git diff --no-index -- NUL tests/test_evaluation.py
git diff --no-index -- NUL tests/test_same_lane_repair.py
git diff --no-index -- NUL docs/superpowers/reports/2026-07-24-stage1-same-lane-repair-acceptance.md
```

Expected: new-file diff commands exit 1 because they display content. Reviewer confirms all resolved design requirements, exact signatures, no incomplete steps, only intended files, fresh metrics, untouched older docs, and no stage/commit/clean/revert action.

---

## Completion Definition

Stage 1 is complete only when the fixed Stage 0 baseline reproduces, the row-level forecast fingerprint is unchanged, every local move is whole/direct/strictly negative and ledger-valid, the global candidate saves at least 1.00 TL raw with zero violations, every staged/official artifact reconciles and re-simulates, rollback publication tests pass, official publication succeeds plan first, all tests/checks pass, fresh evidence is recorded, older docs stay untouched, and all changes remain unstaged/uncommitted.
