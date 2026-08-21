# Stage 2 Q&A-Correct Pair-Only Milk-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace profitable pairs of eligible accepted-Stage-1 direct Spot vehicles with deterministic, Q&A-correct two-stop physical milk-run chains, then publish only a forecast-identical, zero-violation Stage 2 plan that saves at least 1.00 TL at raw precision.

**Architecture:** Add a neutral scheduler-side chain analyzer, then make scheduling and physical metrics consume that analyzer while keeping the simulator an independent output-only referee. Rewrite `src/milkrun.py` as a one-pass pair candidate generator/selector over a single copied Stage 1 graph, and put its global decision behind the existing copy/schedule/simulate acceptance boundary. Extend the staged pipeline so Stage 0 reproduces first, the exact accepted Stage 1 result is the Stage 2 baseline, and only verified Stage 1-baseline and Stage 2-selected artifacts can reach rollback-safe plan-first publication.

**Tech Stack:** Python 3.11+, pandas 2.0+, openpyxl 3.1+, pytest 8.0+, and standard-library `collections`, `copy`, `dataclasses`, `datetime`, `decimal`, `fractions`, `hashlib`, `itertools`, `pathlib`, `tempfile`, and `time`.

## Global Constraints

- The immutable optimization input is the accepted Stage 1 selected plan, not Stage 0: raw total `14,680,184.845833339 TL`, raw vehicle cost `12,510,401.245833337 TL`, raw SLA penalty `2,169,783.600000002 TL`, 1,092 route segments and 1,092 physical vehicles, 126 rented and 966 Spot vehicles, 3,167 plan rows, and zero violations.
- The forecast remains exactly 4,046 rows, 4,046 IDs `D00001..D04046`, and 4,977,975 desi. Preserve every row-level ID/date/slot/origin/destination/desi value and the canonical forecast fingerprint.
- The implementation entry suite is 291 tests. Final acceptance requires every existing test and every new Stage 2 test to pass; no existing gate may be weakened or skipped.
- Keep the existing Stage 0 reproduction gate first. Stage 0 remains 1,269 legs, 126 rented, 1,143 Spot, 3,167 rows, vehicle cost `15,460,592.57 TL`, SLA `1,020,367.20 TL`, total `16,480,959.77 TL`, and zero violations under its existing inclusive `0.01 TL` cost tolerance.
- Add an exact accepted Stage 1 entry gate after Stage 0 reproduction and before milk-run generation. It must require the exact raw Stage 1 costs/counts, accepted Stage 1 decision/repair metrics, direct-only topology, and zero violations specified in Task 8.
- Stage 2 accepts only when `Decimal(str(stage1_total)) - Decimal(str(stage2_total)) >= Decimal("1.00")`, without quantization, and both evaluations have zero violations. The same raw `1.00 TL` gate applies again to staged artifact referee totals.
- Stage 2 v1 is exactly pair-only: every new chain has exactly two destination stops and exactly two route segments. Three/four-stop Stage 2b growth is out of scope until pair-only Stage 2 is independently accepted.
- The approved “at most four stops” scope permits this two-stop subset. Do not add a route-detour ratio; Stage 3's `1.15` rule does not apply to Stage 2.
- Evaluate both destination orders and every fitting non-Tır type in `("Kamyonet", "Hafif Kamyon", "Kamyon")`; exact vehicle cost plus exact final-drop SLA determines acceptance.
- Eligible sources are loaded direct Spot non-Tır legs with `chain_id is None`; every `part.dest` equals the source destination; every physical `Part` object occurs exactly once in the input; both sources have one common origin and exactly equal `load_start`; destinations differ; and all complete existing parts together fit at least one allowed type.
- Do not impose a 5,600-desi source-leg cap. Reject a combined 12,001 desi, but allow an individual source above 5,600 when the complete pair fits Hafif Kamyon or Kamyon.
- Exclude rented legs, Tır legs, existing chains, same-destination pairs, unequal-load-start pairs, disconnected matrix arcs, and shared/transfer parts. Do not create a new `Part`, call `Part.piece`, split cargo, merge cargo by textual ID, or add an intermediate pickup.
- The pair's first segment is `O -> D1` and carries every source part; the second is `D1 -> D2` and carries only `D2` parts. The same `Part` objects and desi values must be shared across segment occurrences.
- Use actual matrix distance and travel time for `O -> D1` and `D1 -> D2`. The chain's full Spot vehicle cost is first-load-start through final-unload plus both arc distances, stored on segment 0; segment 1 stores zero vehicle cost.
- Charge each part's SLA only at its original final destination using its original deadline. No SLA is declared or charged while the part stays onboard or unloads at a non-final transfer point.
- `src/chain.py` is scheduler-side neutral infrastructure. `src/simulator.py` must not import `src.chain`, `LegFlow`, `physical_routes`, `analyze_leg_flows`, `src.schedule`, `src.milkrun`, or optimizer-internal chain state.
- One `Araç ID` identifies one physical route and one vehicle type. Every chain segment shares one vehicle ID; standalone legs remain separate physical routes.
- Demand suffixes count unique `Part` object identities, not rows. Assign a physical part once at its deterministic first occurrence, reuse its ID on later segments, and give distinct `Part` objects with the same base separate suffixes.
- Handling uses actual load/unload operations only and keeps `HandlingLedger`'s proportional midnight splitting. Cargo that stays onboard at an intermediate stop consumes and declares no handling there.
- Chain segments are individually unshiftable during scheduler handling repair. Unrelated eligible direct Spot non-Tır legs may still shift. An unresolved overload is not hidden; the independent simulator must reject it globally.
- Every output row declares full segment travel. It declares departure handling only on an actual load, arrival handling only on an actual unload, zero SLA until final unload, and physical vehicle cost only on the first/new occurrence of cargo.
- Allocate one physical route cost by desi across all unique newly loaded cargo on that route. Later carried occurrences receive zero vehicle allocation. A standalone empty rented row owns its complete physical vehicle cost.
- The independent simulator must compare every declared travel, handling, SLA, and vehicle-cost portion against its own row-operation and physical-trace reconstruction. Minute declarations are exact, SLA declarations use only a `0.000001 TL` numeric epsilon, and vehicle-cost row/trace comparisons use the required inclusive `0.01 TL` tolerance.
- Current direct-only Stage 0 and Stage 1 outputs must remain byte/semantic compatible, apart from regeneration of the same deterministically ordered IDs. Their accepted costs, rows, IDs, and zero-violation results must remain unchanged.
- `milk_run_improve` performs exactly one `deepcopy(legs)`. It may use object identity only for occurrence eligibility and transition tracking, never as a ranking or tie-break key.
- Candidate generation and selection use semantic keys only, run once, contain no random/convergence search, and do not reconsider newly formed chains.
- Candidate local deltas use `Decimal(str(value))` for every non-integral input. A local candidate is eligible only when `delta_tl < Decimal("0")`; zero is rejection.
- Before each candidate commit, build fresh complete handling and Tır ledgers over the whole trial graph using `analyze_leg_flows`. Any readiness, capacity, chain, handling, Tır, or accepted-Stage-1 distribution-end failure rejects without changing working state.
- New chain IDs are deterministic, collision-free integers beginning above the maximum existing chain ID. Rejected candidates do not consume an ID.
- A new chain's final cargo unload date may not exceed the accepted Stage 1 final cargo-unload date. Empty rented movements do not extend that boundary.
- Keep milk-run logic out of `src/optimize.py` and its daily loop. `src/candidates.py`, `src/optimize.py`, and `src/repair.py` remain the accepted Stage 0/1 construction path.
- Pipeline order is fixed: build; `run_same_lane_stage`; require Stage 0 on `stage1.baseline`; require exact accepted Stage 1 on `stage1.selected`; `run_milk_run_stage(stage1.selected)`; require Stage 2 acceptance; verify staged Stage 1 baseline; verify staged Stage 2 selected; require raw artifact saving; publish plan first and forecast second.
- If Stage 1 or Stage 2 rejects, raises, or fails any artifact gate, publish nothing and preserve both official accepted files. Continue using the existing ordinary-`Exception` rollback transaction in `publish_workbooks`.
- Print Stage 0, Stage 1, and Stage 2 costs, segment counts, physical rented/Spot counts, physical vehicle mix, physical Spot fill metrics, Stage 1 repair metrics, and all `MilkRunMetrics` fields.
- The deterministic four-stop research result is non-gating and deferred. Do not add four-stop production code, tests, parameters, or acceptance assertions in this plan.
- Preserve the read-only pair research evidence as directional only: 277 chains replacing 554 direct Spot vehicles, candidate `11,993,748.820833342 TL`, raw saving `2,686,436.024999997 TL`, and zero current-referee violations. Never make those counts or totals an exact general-pass assertion.
- Add exact synthetic witnesses for Kamyonet, Hafif Kamyon, and Kamyon, plus a forced valid two-stop chain. The real-horizon test asserts topology, declarations, inventory, gates, and positive raw saving, not the directional batch total.
- Keep all implementation work unstaged and uncommitted. Never run `git add`, `git commit`, `git restore`, `git checkout`, `git clean`, `git reset`, or any command that stages, commits, cleans, reverts, or discards worktree content.
- The worktree is intentionally dirty. Before each task, the SDD controller must preserve every existing task file as a task-scoped Git blob ref using `git hash-object --no-filters -w` plus `git update-ref refs/sdd/stage2/task-N/...-before`; this records content without staging, committing, or changing a worktree file. Review each changed file by diffing that ref against a fresh current-file blob, compare new files against `NUL`, retain the refs through any fix loop, and delete only those task refs after clean task approval. Do not use shell file-copy/write commands or overwrite unrelated user changes.
- Update `PLAN.md` and create the Stage 2 acceptance report only after every fresh acceptance command passes. Do not edit `ARCHITECTURE.md`, `ROADMAP.md`, `README.md`, `docs/comparison/*`, older specs, older plans, or older reports.

---

## Exact File And Interface Map

| Path | Action | Responsibility |
|---|---|---|
| `src/chain.py` | Create | Neutral physical-route grouping, structural chain validation, and input-aligned scheduler-side leg flows. |
| `src/schedule.py:25-183` | Modify | Physical vehicle/demand IDs, chain-safe handling repair, and operation-aware row declarations/cost allocation. |
| `src/simulator.py:17-409` | Modify | Preserve declared rows and independently referee travel, operation shares, SLA, and physical vehicle-cost allocation. |
| `src/milkrun.py:1-160` | Replace | Remove the unsafe four-stop skeleton; implement exact pair topology/pricing, deterministic one-pass selection, metrics, and global Stage 2 decision. |
| `src/evaluation.py:29-200` | Modify | Count physical routes and initial-onboard Spot fill while preserving the existing evaluation/acceptance APIs. |
| `run.py:30-261` | Modify | Exact Stage 1 entry, Stage 2 gate/order, physical metrics output, Stage 1/Stage 2 artifact verification, and publication. |
| `tests/test_chain.py` | Create | Route grouping, flow transitions, input alignment, and malformed-chain cases. |
| `tests/test_schedule_chain.py` | Create | Chain IDs, physical part suffixes, handling repair, row declarations, cost-once semantics, and direct regression. |
| `tests/test_milkrun.py` | Create | Pair eligibility/topology/timing/pricing, all vehicle witnesses, ledgers, deterministic selection, decision rollback, and real horizon. |
| `tests/test_simulator_cost.py:16-210` | Modify | Declared-row retention while preserving existing `items`/trace behavior. |
| `tests/test_simulator_full.py:24-322` | Modify | Independent declaration acceptance/rejection, duplicated cost, and empty-rental ownership. |
| `tests/test_evaluation.py:336-372` | Modify | Physical route counts/mix/fill and unchanged direct metrics. |
| `tests/test_optimize.py:48-682` | Modify | Exact Stage 1 gate, Stage 0/1/2 ordering, staged artifacts, rejection, success, and publication seams. |
| `PLAN.md` | Modify only after acceptance | Record accepted pair-only Stage 2 architecture, exact fresh metrics, gates, tests, runtime, and next work. |
| `docs/superpowers/reports/2026-07-25-stage2-q-and-a-correct-milk-run-acceptance.md` | Create only after acceptance | Record fresh full-horizon, artifact, declaration, inventory, publication, and worktree evidence. |
| `src/candidates.py` | Verify only | Existing `Part` identity and direct scheduled-cost source; do not edit. |
| `src/optimize.py` | Verify only | Existing `PlannedLeg` and Stage 0 construction; do not import or activate milk-run here. |
| `src/repair.py` | Verify only | Accepted Stage 1 repair/decision; do not change its algorithm or exact output. |
| `src/export.py` | Verify only | Existing schema writers, reconciliation, and rollback-safe plan-first publication. |
| `src/ledger.py`, `src/timeutil.py`, `src/schemas.py` | Verify only | Existing capacity, rounding, and schema contracts remain authoritative. |
| `tests/test_export.py`, `tests/test_same_lane_repair.py`, `tests/test_ledger.py`, `tests/test_schemas.py` | Verify only | Regression gates; no edits are planned. |

The implementation must expose these exact interfaces and preserve all omitted existing fields/functions:

```python
# src/chain.py
@dataclass(frozen=True)
class LegFlow:
    loaded: tuple[tuple[Part, int | float], ...]
    carried: tuple[tuple[Part, int | float], ...]
    unloaded: tuple[tuple[Part, int | float], ...]
```

```text
physical_routes(legs: list[PlannedLeg]) -> list[tuple[PlannedLeg, ...]]
analyze_leg_flows(legs: list[PlannedLeg]) -> list[LegFlow]
```

`LegFlow` fields are operation sets and can overlap: `loaded` is a part's first contiguous route occurrence, `carried` means the same identity/desi continues into the next segment, and `unloaded` is its last contiguous route occurrence. A standalone item is in both `loaded` and `unloaded` and never in `carried`.

```python
# src/simulator.py
@dataclass(frozen=True)
class DeclaredRow:
    item_id: str | None
    desi: float
    travel_minutes: float
    arrival_handling_minutes: float
    departure_handling_minutes: float
    sla_penalty: float
    total_cost: float


@dataclass
class Leg:
    vehicle_id: str
    kind: str
    vtype: str
    origin: str
    dest: str
    dep: datetime
    declared_arr: datetime
    items: list
    violations: list[str] = field(default_factory=list)
    declared_rows: list[DeclaredRow] = field(default_factory=list)
```

`parse_legs`, `trace_vehicle`, `simulate`, `Leg.items`, `VehicleTrace`, and `SimResult` retain their existing callable/public behavior. Declaration checks are added by `simulate`; `trace_vehicle` remains the physical timing/cost primitive used by existing focused tests.

```python
# src/milkrun.py
ROUTE_TYPES = ("Kamyonet", "Hafif Kamyon", "Kamyon")


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


@dataclass(frozen=True)
class _PairCandidate:
    source_tokens: tuple[int, int]
    route_destinations: tuple[str, str]
    vtype: str
    legs: tuple[PlannedLeg, PlannedLeg]
    delta_tl: Decimal


@dataclass(frozen=True)
class MilkRunDecision:
    baseline: PlanEvaluation
    candidate: PlanEvaluation
    selected: PlanEvaluation
    metrics: MilkRunMetrics
    accepted: bool
    saving_tl: Decimal
```

```text
_build_pair_candidates(first_token: int, first: PlannedLeg,
                       second_token: int, second: PlannedLeg, data)
    -> tuple[_PairCandidate, ...]
milk_run_improve(legs: list[PlannedLeg], data)
    -> tuple[list[PlannedLeg], MilkRunMetrics]
run_milk_run_stage(baseline: PlanEvaluation, forecast_df, data)
    -> MilkRunDecision
```

`_PairCandidate.legs` is a tuple of newly constructed `PlannedLeg` templates with `chain_id=0` and `chain_seq` 0/1. The frozen candidate is never mutated; commit uses `dataclasses.replace` to assign the next real chain ID while preserving shared copied `Part` identities.

```python
# src/evaluation.py: field names stay source-compatible; meanings become physical
@dataclass(frozen=True)
class PlanMetrics:
    vehicle_cost: Decimal
    sla_penalty: Decimal
    total_cost: Decimal
    rented_legs: int       # physical rented routes
    spot_legs: int         # physical Spot routes
    vehicle_mix: tuple[tuple[str, int], ...]  # per physical route
    average_spot_fill: Fraction               # initial onboard load per Spot route
    spot_below_30_percent: int                # per physical Spot route
    violations: int
```

```text
# run.py exact callable signatures
_require_stage0_entry(forecast_frame: pd.DataFrame,
                      evaluation: PlanEvaluation, data) -> None
_require_stage1_entry(decision: Stage1Decision, data) -> None
_require_stage2_entry(stage1: Stage1Decision,
                      stage2: MilkRunDecision) -> None
_print_pipeline_metrics(stage1: Stage1Decision,
                        stage2: MilkRunDecision,
                        data,
                        stage1_seconds: float,
                        stage2_seconds: float) -> None
_stage_and_publish(stage1: Stage1Decision,
                   stage2: MilkRunDecision,
                   staged_forecast_path: Path,
                   expected_fingerprint: tuple,
                   data,
                   staging_dir: Path,
                   output_dir: Path) -> None
```

Dependency direction is fixed and acyclic:

```text
candidates.py <- optimize.py <- chain.py <- schedule.py <- evaluation.py
                               ^              ^
                               |              |
                            milkrun.py --------+

repair.py -> evaluation.py
run.py -> repair.py + milkrun.py + evaluation.py + export.py
simulator.py -> data/ledger/schemas/timeutil only (no chain/schedule/milkrun import)
```

---

### Task 1: Neutral Physical Routes And Leg Flow Analyzer

**Files:**
- Create: `src/chain.py`
- Create: `tests/test_chain.py`

**Interfaces:**
- Consumes: `src.candidates.Part`, `src.optimize.PlannedLeg`.
- Produces: frozen `LegFlow`, `physical_routes`, and input-aligned `analyze_leg_flows` exactly as mapped above.
- Does not import: scheduler, simulator, evaluation, repair, or milk-run modules.

- [ ] **Step 1: Record the task-scoped pre-task state**

```powershell
git status --short -- src/chain.py tests/test_chain.py
```

Expected: neither target exists; no workspace file is staged, removed, or reverted.

- [ ] **Step 2: Write the failing route and flow tests**

Create deterministic `Part`/`PlannedLeg` helpers over `A -> B -> C`. Add these exact cases:

| Test | Exact assertion |
|---|---|
| `test_physical_routes_keep_standalones_separate_and_group_chain` | Interleaved standalone, chain seq 1, chain seq 0, standalone returns three physical tuples in first-input-occurrence order; the chain tuple is internally `(seq0, seq1)`. |
| `test_pair_chain_flows_are_input_aligned` | For `p_b` and `p_c` on `A->B`, then only the same `p_c` on `B->C`: first flow loads both, carries only `p_c`, unloads only `p_b`; second flow loads none, carries none, unloads `p_c`; reversing input storage still aligns each flow with its original list position. |
| `test_standalone_loads_and_unloads_every_item` | `loaded == unloaded == tuple(leg.items)` and `carried == ()`. |
| `test_distinct_equal_parts_are_not_one_physical_part` | Two separate `Part` objects with equal fields are treated as distinct transitions. |
| `test_chain_requires_zero_based_contiguous_sequence` | Parametrize `[1]`, `[0, 2]`, and duplicate `[0, 0]`; each raises `ValueError` containing the chain ID and `chain_seq`. |
| `test_distinct_chain_ids_form_distinct_physical_routes` | Valid chain IDs 7 and 8 each produce one separate route tuple and never coalesce. |
| `test_chain_requires_connected_topology` | `A->B`, then `C->D` raises with `B` and `C`. |
| `test_chain_requires_one_kind_and_vehicle_type` | Mixed `Spot/Kiralık` and mixed `Kamyonet/Kamyon` each raise clearly. |
| `test_chain_rejects_duplicate_part_in_one_segment` | The same object twice in `items` raises with `duplicate Part`. |
| `test_chain_rejects_desi_change_for_same_part` | The same object at 100 then 99 raises with both desi values. |
| `test_chain_rejects_disappear_then_reappear` | Occurrences at seq 0 and seq 2 but not seq 1 raise with `non-contiguous Part`. |

The core valid witness must assert object identity, not textual equality:

```python
flows = analyze_leg_flows([first, second])
assert flows[0].loaded == ((p_b, 100), (p_c, 200))
assert flows[0].carried == ((p_c, 200),)
assert flows[0].unloaded == ((p_b, 100),)
assert flows[1] == LegFlow(loaded=(), carried=(), unloaded=((p_c, 200),))
assert flows[0].carried[0][0] is flows[1].unloaded[0][0]
```

- [ ] **Step 3: Run the strict red test**

Run: `python -m pytest tests/test_chain.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'src.chain'`.

- [ ] **Step 4: Implement structural route validation**

Implement `physical_routes` with this exact algorithm:

```text
scan enumerate(legs) once
  chain_id is None -> create one route record (first_index, (leg,))
  otherwise -> append (input_index, leg) to the one group for that chain_id
for each chain group:
  reject any leg whose chain_id differs from the group key
  sort by chain_seq
  require chain_seq == list(range(number_of_segments))
  require exactly one kind and exactly one vtype
  require previous.dest == next.origin for every adjacent pair
  emit (minimum input index, tuple(sorted chain legs))
return only the tuples
```

Use clear messages of the form `chain 7: chain_seq must be contiguous from 0`, `chain 7: disconnected B -> C`, and `chain 7: mixed vehicle type/kind`. Do not sort with `id()`.

- [ ] **Step 5: Implement input-aligned flow analysis**

For each validated route, preserve the existing `(Part, desi)` tuple objects and use `Decimal(str(desi))` only for exact transition comparison:

```text
for each segment:
  reject duplicate id(part) within that segment
for each physical Part identity across the route:
  require one exact desi value across all occurrences
  require occurrence segment indexes to be a contiguous integer range
for segment i and each current item in current item order:
  loaded   iff no equal identity/desi occurrence exists in segment i-1
  carried  iff an equal identity/desi occurrence exists in segment i+1
  unloaded iff no equal identity/desi occurrence exists in segment i+1
standalone special case: loaded=all, carried=(), unloaded=all
write each LegFlow into the result slot of that leg's original input index
```

Return `list[LegFlow]` with exactly `len(legs)` entries. Reject malformed state before returning any partial result.

- [ ] **Step 6: Run green and dependency regressions**

```powershell
python -m pytest tests/test_chain.py -q
python -m pytest tests/test_same_lane_repair.py tests/test_optimize.py -q
```

Expected: all selected tests pass; accepted Stage 1 behavior remains unchanged.

- [ ] **Step 7: Review only the Task 1 delta**

```powershell
git status --short -- src/chain.py tests/test_chain.py
git diff --no-index -- NUL src/chain.py
git diff --no-index -- NUL tests/test_chain.py
```

Expected: each no-index command displays the new file and exits 1. Review every malformed case, input alignment, object-identity use, exact desi comparison, import direction, and absence of scheduler/simulator imports. Do not stage or commit.

---

### Task 2: Chain-Aware Physical Vehicle And Demand IDs

**Files:**
- Modify: `src/schedule.py:80-103`
- Create: `tests/test_schedule_chain.py`

**Interfaces:**
- Consumes: `physical_routes(legs) -> list[tuple[PlannedLeg, ...]]`.
- Preserves: `_assign_ids(legs: list) -> None` and all direct-leg ordering behavior.
- Produces: one `vehicle_id` per physical route and one suffix per unique physical `Part` identity.

- [ ] **Step 1: Preserve the dirty scheduler before this task**

```powershell
git update-ref "refs/sdd/stage2/task-2/schedule-before" $(git hash-object --no-filters -w "src/schedule.py")
git status --short -- src/schedule.py tests/test_schedule_chain.py
```

Expected: the task ref is created without changing the index or worktree. Retain it through every Task 2 review/fix round.

- [ ] **Step 2: Write failing ID tests**

Use a two-stop chain plus earlier/later standalone routes. Add:

| Test | Exact assertion |
|---|---|
| `test_chain_segments_share_one_vehicle_id` | Seq 0 and seq 1 receive the same `V####`; two standalones receive two other IDs; all segments retain one kind/vtype. |
| `test_same_physical_part_reuses_item_id_and_desi` | A shared `Part` receives one output demand ID on both chain segments and unchanged desi. |
| `test_unique_split_parts_get_one_suffix_each` | Two distinct `Part` objects with base `D00001`, one repeated through a chain, yield exactly `D00001-1` and `D00001-2`; the repeated object reuses its suffix. |
| `test_distinct_equal_part_objects_still_get_distinct_suffixes` | Equal dataclass values but different identities are not collapsed. |
| `test_single_unique_part_keeps_base_id` | Multiple rows for one physical object still count as one part and keep `D00002` without `-1`. |
| `test_direct_vehicle_and_item_order_regression` | Three direct legs in deliberately unsorted input produce the current `(Kiralık first, then Spot by dep/origin/dest)` vehicle IDs and current suffix order exactly. |
| `test_malformed_chain_fails_before_any_id_assignment` | A sequence gap raises and leaves every prior `vehicle_id`/`item_ids` unchanged. |

- [ ] **Step 3: Run red**

Run: `python -m pytest tests/test_schedule_chain.py -q`

Expected: chain segments receive different vehicle IDs and repeated rows receive separate suffixes, so the new assertions fail.

- [ ] **Step 4: Replace leg-count ID assignment with route-count assignment**

Import `physical_routes` and implement this exact route order:

```text
routes = physical_routes(legs)  # validates every chain before mutation
ordered_routes = stable sorted routes by
  (route[0].kind != "Kiralık", route[0].dep,
   route[0].origin, route[0].dest)
for i, route in enumerate(ordered_routes, 1):
  assign f"V{i:04d}" to every segment in route
```

Do not include `chain_id`, object identity, or input token in the ranking. Stable ties retain `physical_routes` first-occurrence order, matching current direct behavior.

- [ ] **Step 5: Assign demand IDs by first unique physical occurrence**

Reset every `leg.item_ids` only after route validation and vehicle IDs succeed. Build occurrences in the current direct-compatible order `(leg.dep, leg.vehicle_id, item_position)` and then:

```text
group by part.base_id
within a base, keep only the first occurrence of each id(part)
  (identity is a deduplication key, never a sort key)
if unique physical count == 1: map its identity to base_id
else: map ordered unique identities to base_id-1, base_id-2, and continuing integers
fill every segment row from the identity-to-final-ID map
```

Distinct objects with equal fields remain distinct. A shared object must have an exact consistent desi because `physical_routes`/later flow analysis validates the chain.

- [ ] **Step 6: Run green and direct regressions**

```powershell
python -m pytest tests/test_chain.py tests/test_schedule_chain.py -q
python -m pytest tests/test_optimize.py::test_plan_frame_per_row_handling_minutes tests/test_schemas.py tests/test_same_lane_repair.py -q
```

Expected: all pass; direct IDs and rows retain their existing deterministic order.

- [ ] **Step 7: Review against the Task 2 pre-task blob**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-2/schedule-before" $(git hash-object --no-filters -w "src/schedule.py")
git diff --no-index -- NUL tests/test_schedule_chain.py
git status --short -- src/schedule.py tests/test_schedule_chain.py
```

Expected: the blob diff and new-file diff show only Task 2 content and exit 1 when changes exist. Review validation-before-mutation, one V-ID per route, unique-identity suffix count, direct ordering, and absence of object-ID ranking. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-2/*` only after clean task approval.

---

### Task 3: Chain Handling Repair And Output Row/Cost Declarations

**Files:**
- Modify: `src/schedule.py:25-183`
- Modify: `tests/test_schedule_chain.py`

**Interfaces:**
- Consumes: `analyze_leg_flows`, `physical_routes`, `HandlingLedger`, and the Task 2 ID behavior.
- Preserves: `_fix_handling(legs, data, notes)`, `_shiftable`, and `to_plan_frame(legs, data, fix=True) -> tuple[pd.DataFrame, list]` signatures.
- Produces: operation-aware declarations and exactly-once physical route cost allocation.

- [ ] **Step 1: Preserve Task 2 outputs before changing declaration behavior**

```powershell
git update-ref "refs/sdd/stage2/task-3/schedule-before" $(git hash-object --no-filters -w "src/schedule.py")
git update-ref "refs/sdd/stage2/task-3/test-schedule-chain-before" $(git hash-object --no-filters -w "tests/test_schedule_chain.py")
git status --short -- src/schedule.py tests/test_schedule_chain.py
```

Expected: both task refs preserve the approved Task 2 content without changing the index or worktree. Retain them through every Task 3 review/fix round.

- [ ] **Step 2: Add the failing forced-chain declaration tests**

Create synthetic `A/B/C` data with exact one-hour arcs and a pair chain containing `D00001=100` for `B` and `D00002=200` for `C`. Segment 0 cost is `Decimal("246")` converted to float; segment 1 cost is zero. Add:

| Test | Exact assertion |
|---|---|
| `test_pair_chain_declares_one_physical_vehicle_and_part_ids` | Both segment groups use one V-ID/type; `D00002` and desi 200 repeat unchanged. |
| `test_chain_declares_only_actual_handling` | Segment 0 `D00001` is departure/arrival `1/1`; segment 0 `D00002` is `2/0`; segment 1 `D00002` is `0/2`. |
| `test_chain_declares_full_travel_on_every_row` | Every row on each segment contains that segment's full matrix travel, never a desi share. |
| `test_chain_declares_sla_only_on_final_unload` | Intermediate `D00002` SLA is zero; each part's final row equals its exact `late_hours * desi * 0.4`. |
| `test_chain_allocates_continuous_vehicle_cost_once` | Cost portions are `82`, `164`, `0`; total declared cost equals `246 + final SLA`; the carried later row has no vehicle allocation. |
| `test_chain_requires_later_segment_cost_zero` | A nonzero seq-1 `leg.cost` raises a clear `ValueError` before a frame is returned. |
| `test_empty_rented_standalone_owns_full_cost` | The one blank row has zero handling/SLA and `Toplam maliyet == leg.cost`. |
| `test_direct_frame_semantics_are_unchanged` | A frozen direct fixture exactly matches pre-chain ID/date/time/travel/handling/SLA/cost rows and `PLAN_COLS`. |

Add handling-repair cases:

| Test | Exact assertion |
|---|---|
| `test_handling_ledger_uses_drop_not_onboard_desi` | A first stop carrying 1,000 but dropping 100 consumes 1,000 at origin and 100 at that destination, not 1,000 twice. |
| `test_chain_segments_are_unshiftable` | An overloaded chain's timestamps remain byte-for-byte equal and notes report unresolved handling. |
| `test_unresolved_chain_handling_is_rejected_by_simulator` | Scheduling leaves the chain fixed and the complete generated frame receives the expected handling-capacity violation from `simulate`. |
| `test_unrelated_direct_leg_can_shift_around_chain_overload` | A smaller direct Spot non-Tır event on the same over-cap center/day moves to next midnight while every chain segment remains fixed. |
| `test_chain_handling_keeps_proportional_midnight_split` | A chain load/unload crossing midnight produces the exact split already specified by `HandlingLedger`. |

- [ ] **Step 3: Run red**

```powershell
python -m pytest tests/test_schedule_chain.py -q
```

Expected: current scheduler declares load/unload and cost on every occurrence and allows chain legs to shift, so the new tests fail.

- [ ] **Step 4: Make handling repair consume actual flows**

Change `_shiftable` to require `leg.chain_id is None`. On every repair iteration:

```text
flows = analyze_leg_flows(legs)
fresh HandlingLedger
for each (leg, flow):
  loaded_desi = sum flow.loaded desi
  unloaded_desi = sum flow.unloaded desi
  add loaded_desi at (leg.origin, leg.load_start) when positive
  add unloaded_desi at (leg.dest, leg.arr) when positive
for an over-cap (tm, day), direct shift candidates are only events whose
actual loaded/unloaded desi contributes to that exact tm/day
sort direct candidates by the existing exact key (leg.desi, leg.dep)
retime only the first eligible standalone direct leg
```

Keep `_retime` direct-only and preserve current usage duration/cost. Recompute flows on the next loop. If no direct candidate exists, append the existing unresolved note and return; do not alter a chain to conceal the violation.

- [ ] **Step 5: Make `to_plan_frame` declare physical operations and cost once**

After ID assignment and optional handling repair, call `analyze_leg_flows(legs)` again. Build route metadata from `physical_routes(legs)` before emitting rows:

```text
for each physical route:
  if len(route) > 1:
    require Decimal(str(cost)) == 0 for every segment after route[0]
  route_cost = route[0].cost
  newly_loaded = every flow.loaded tuple across the route
  require each physical Part identity appears in newly_loaded exactly once
  new_total = exact Decimal sum of newly-loaded desi
  for a multi-segment route, allocation for a loaded row =
      route_cost * (row_desi / float(new_total))
  allocation for every non-loaded occurrence = 0
```

For a singleton direct route, retain the existing byte-compatible expression `leg.cost * (desi / leg.desi)` rather than replacing it with Decimal arithmetic. Emit rows in the original `legs`/item order to preserve direct output order. For each cargo row:

```text
departure handling = handling_minutes(desi) iff identity is in flow.loaded else 0
arrival handling   = handling_minutes(desi) iff identity is in flow.unloaded else 0
travel             = full travel_minutes(matrix arc, leg.vtype)
SLA                 = exact existing formula iff identity is in flow.unloaded
                      and leg.dest == part.dest; otherwise 0
Toplam maliyet      = float(route vehicle allocation) + SLA
```

For a cargo-free standalone rented route, retain one blank row and place its complete `leg.cost` there. Reject a cargo-free multi-segment chain. Do not use stored `leg.penalty` for row declarations.

- [ ] **Step 6: Run green and direct compatibility tests**

```powershell
python -m pytest tests/test_chain.py tests/test_schedule_chain.py -q
python -m pytest tests/test_optimize.py::test_plan_frame_per_row_handling_minutes tests/test_simulator_cost.py tests/test_simulator_full.py -q
```

Expected: all selected tests pass; existing direct fixtures remain unchanged.

- [ ] **Step 7: Review Task 3 in isolation**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-3/schedule-before" $(git hash-object --no-filters -w "src/schedule.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-3/test-schedule-chain-before" $(git hash-object --no-filters -w "tests/test_schedule_chain.py")
git status --short -- src/schedule.py tests/test_schedule_chain.py
```

Review actual flow desi in ledgers, proportional midnight behavior, chain immobility, final-only SLA, full travel, one route cost, carried-row zero allocation, empty rental ownership, and direct regression. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-3/*` only after clean task approval.

---

### Task 4: Independent Simulator Declaration Referee

**Files:**
- Modify: `src/simulator.py:17-409`
- Modify: `tests/test_simulator_cost.py:16-210`
- Modify: `tests/test_simulator_full.py:24-322`

**Interfaces:**
- Produces: frozen `DeclaredRow` and `Leg.declared_rows` as mapped above.
- Preserves: `Leg.items` as the existing list of `(item_id, desi)`, plus `parse_legs`, `trace_vehicle`, `simulate`, `VehicleTrace`, and `SimResult` call signatures/results.
- Must remain independent of `src.chain`, scheduler, evaluation, repair, optimize, and milk-run modules.

- [ ] **Step 1: Preserve the current referee and its focused tests**

```powershell
git update-ref "refs/sdd/stage2/task-4/simulator-before" $(git hash-object --no-filters -w "src/simulator.py")
git update-ref "refs/sdd/stage2/task-4/test-simulator-cost-before" $(git hash-object --no-filters -w "tests/test_simulator_cost.py")
git update-ref "refs/sdd/stage2/task-4/test-simulator-full-before" $(git hash-object --no-filters -w "tests/test_simulator_full.py")
git status --short -- src/simulator.py tests/test_simulator_cost.py tests/test_simulator_full.py
```

Expected: all task refs are created without changing the index or worktree. Retain them through every Task 4 review/fix round.

- [ ] **Step 2: Pin declared-row retention without changing `items` behavior**

Add `test_parse_legs_preserves_declared_rows_and_existing_items` using two cargo rows and one empty rented row. Assert every numeric declaration is retained in `DeclaredRow`, blank ID becomes `None`, and existing `leg.items` remains exactly the same non-empty `(str(id), float(desi))` list as before.

```python
leg = parse_legs(frame)[0]
assert leg.items == [("D00001", 100.0), ("D00002", 200.0)]
assert leg.declared_rows[0] == DeclaredRow(
    item_id="D00001", desi=100.0, travel_minutes=60.0,
    arrival_handling_minutes=1.0, departure_handling_minutes=1.0,
    sla_penalty=0.0, total_cost=82.0)
```

- [ ] **Step 3: Add a hand-authored valid two-stop declaration fixture and mutation tests**

Use independent synthetic data: Kamyonet capacity 5,600, Spot `60 TL/hour + 1 TL/km`, no rentals, one-hour/60-km `A->B` and `B->C`, and a forecast matrix lane `A->C`. The valid chain is:

```text
09:00 load 100 for B + 200 for C; handling 3; depart A 09:03
arrive B 10:03; unload 100 for 1 minute; depart B 10:04
arrive C 11:04; unload 200 for 2 minutes; finish 11:06
physical cost = 60 * 126/60 + 1 * 120 = 246 TL
row vehicle allocation = 82, 164, 0
row handling = D1 first 1/1; D2 first 2/0; D2 second 0/2
row SLA = 0, 0, 0 for one-day deadlines
```

Add these exact tests by copying the valid frame and changing only the named declaration:

| Test | Mutation and required violation |
|---|---|
| `test_simulator_accepts_valid_pair_declarations` | No mutation; zero violations, vehicle cost 246, total 246. |
| `test_every_row_must_declare_full_matrix_travel` | Parametrize each of the three rows with travel `+1`; each reports that row's declared/matrix travel mismatch. |
| `test_new_and_unloaded_rows_require_exact_handling_share` | Set one actual new departure share or one actual unload arrival share to zero; each is rejected. |
| `test_stay_onboard_rows_require_zero_intermediate_handling` | Set first-segment `D00002` arrival handling to 2; reject. |
| `test_carried_final_row_has_zero_departure_and_real_arrival_handling` | Set second-segment `D00002` departure to 2 or arrival to 0; reject both. |
| `test_sla_must_be_zero_before_final_destination` | Put 1 TL SLA on first-segment carried `D00002`; reject. |
| `test_final_unload_sla_must_match_original_forecast_deadline` | Use a deliberately late final unload; zero or `expected + 0.0000011` SLA is rejected, exact expected is accepted. |
| `test_vehicle_cost_is_only_on_unique_new_rows` | Put any vehicle portion on second-segment carried `D00002`; reject. |
| `test_vehicle_cost_rows_are_proportional_within_one_cent` | Change 82/164 to 83/163: sum stays 246 but both row values are rejected. |
| `test_duplicated_chain_cost_is_rejected` | Add 246 to the later carried row; row and physical-trace allocation violations appear. |
| `test_sla_tolerance_boundary_is_inclusive` | On an otherwise valid late final row, declared SLA differences of exactly `+/-0.000001 TL` pass and `0.0000011 TL` fails. |
| `test_vehicle_cost_tolerance_boundary_is_inclusive` | On an otherwise valid row/trace, a vehicle-portion and trace-total difference of exactly `+/-0.01 TL` passes and `0.010001 TL` fails. |
| `test_physical_vehicle_cost_sum_must_match` | Add `0.010001` to one new row; reject the trace total. |
| `test_empty_rented_row_owns_full_vehicle_cost` | A standalone empty rented row with exact travel, zero handling/SLA, and full trace cost passes; zero declared cost fails. |

For `test_final_unload_sla_must_match_original_forecast_deadline`, first build a late but otherwise declaration-valid chain with recomputed arrival, physical cost, and proportional cost rows; then mutate only its final SLA cell. Every rejection test must isolate its named declaration rather than relying on an unrelated stale value.

- [ ] **Step 4: Run red**

```powershell
python -m pytest tests/test_simulator_cost.py::test_parse_legs_preserves_declared_rows_and_existing_items tests/test_simulator_full.py::test_simulator_accepts_valid_pair_declarations tests/test_simulator_full.py::test_duplicated_chain_cost_is_rejected -v
```

Expected: `DeclaredRow`/`declared_rows` is missing and declaration mutations are ignored.

- [ ] **Step 5: Parse declared rows alongside existing items**

Populate one `DeclaredRow` per grouped DataFrame row in original group order. Keep `items` construction unchanged and keep group-level arrival/type validation. Numeric conversion uses `float`; schema validation remains the normal public precondition, while direct simulator tests use valid finite numbers.

```text
item_id = None for blank/NaN, otherwise str(value)
desi = float(Taşınan Desi)
travel_minutes = float(Yolculuk süresi)
arrival_handling_minutes = float(Varış elleçleme süresi)
departure_handling_minutes = float(Çıkış Elleçleme süresi)
sla_penalty = float(SLA cezası)
total_cost = float(Toplam maliyet)
```

- [ ] **Step 6: Independently derive row operations inside the simulator**

Do not call scheduler/chain helpers. For each already vehicle-ID-grouped, departure-sorted trace:

```text
previous_stay = {}
for leg i:
  current = exact valid item_id -> desi rows; duplicate IDs already violate
  connected_previous = previous leg exists and previous.dest == leg.origin
  connected_next = next leg exists and leg.dest == next.origin
  new row iff connected_previous is false or previous_stay lacks same ID/desi
  stay row iff connected_next and next leg contains same ID/desi
  unloaded row iff not stay
  previous_stay = current rows marked stay
```

Use the existing `1e-6` desi equality convention. This operation derivation is output-only and shares no implementation with `analyze_leg_flows`.

- [ ] **Step 7: Validate declarations after each physical trace is recomputed**

In `simulate`, after `trace_vehicle` and forecast records are available, append declaration violations without changing recomputed cost/SLA totals:

```text
for every declared row:
  expected travel = travel_minutes(actual matrix lane for trace vtype), exact
  expected departure share = handling_minutes(row.desi) iff new else 0, exact
  expected arrival share = handling_minutes(row.desi) iff unloaded else 0, exact
  expected SLA = row.desi * late_hours(original deadline, leg unload_end) * 0.4
                 iff unloaded and leg.dest == original forecast dest; else 0

unique new cargo = first actual-new occurrence of each (item_id, equal desi)
new_total = sum unique-new desi
expected vehicle portion on each unique-new row = trace.cost * row.desi/new_total
expected vehicle portion on every other cargo row = 0
actual vehicle portion = row.total_cost - row.sla_penalty
require each SLA difference <= Decimal("0.000001")
require each vehicle-portion difference <= Decimal("0.01")
require sum(actual vehicle portions) differs from trace.cost by <= Decimal("0.01")
```

If a segment has no matrix lane or a row has no forecast record, retain the existing explicit violation and skip only the declaration comparison that lacks an independent expected value; never crash or treat it as valid. For a trace with no cargo, use test data containing the matching `RentalRoute`, require `kind == "Kiralık"`, one empty declared row, exact travel, zero handling/SLA, and `actual vehicle portion == trace.cost` within `0.01`. Report violations with vehicle ID, segment OD/departure, item ID, declared value, and expected value.

- [ ] **Step 8: Update existing valid simulator fixtures to remain declaration-valid**

Keep failure-specific malformed topology rows malformed, but make every fixture that asserts `violations == []` declare its recomputed values. Pin these existing exact examples:

```text
6,000-desi delayed Tır row: vehicle 2,930 TL; SLA 2,400 TL; total 5,330 TL
6,000/4,000 split Tır rows on separate vehicles: 2,930 TL and 2,605 TL vehicle portions
5,000-desi one-leg Tır row: 2,767.5 TL vehicle portion
transfer rows: each physical vehicle declares its own full recomputed vehicle cost;
intermediate SLA remains zero and only the forecast-destination row declares SLA
```

Use formula-based fixture helpers for any other varied time/desi row so a test changes only the rule it names.

- [ ] **Step 9: Run green, independence, and accepted-Stage-1 regression**

```powershell
python -m pytest tests/test_simulator_cost.py tests/test_simulator_full.py -q
python -m pytest tests/test_chain.py tests/test_schedule_chain.py tests/test_evaluation.py -q
python -m pytest tests/test_optimize.py::test_full_horizon_same_lane_stage_accepts_fixed_stage0_baseline -v
python -c "import ast; from pathlib import Path; tree=ast.parse(Path('src/simulator.py').read_text(encoding='utf-8')); imports={alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names}|{node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) and node.module}; forbidden=('src.chain','src.schedule','src.milkrun','src.optimize','src.evaluation','src.repair'); assert not any(module==blocked or module.startswith(blocked+'.') for module in imports for blocked in forbidden); print('simulator independence: PASS')"
```

Expected: all tests pass; the full accepted Stage 1 result still has exact accepted costs and zero declaration/referee violations; independence prints `PASS`.

- [ ] **Step 10: Review Task 4 against its pre-task blobs**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-4/simulator-before" $(git hash-object --no-filters -w "src/simulator.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-4/test-simulator-cost-before" $(git hash-object --no-filters -w "tests/test_simulator_cost.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-4/test-simulator-full-before" $(git hash-object --no-filters -w "tests/test_simulator_full.py")
git status --short -- src/simulator.py tests/test_simulator_cost.py tests/test_simulator_full.py
```

Review retained public items, independent transition logic, every-row travel, operation shares, original-SLA destination/deadline, unique-new proportional cost, inclusive boundary and out-of-bound sum/row tolerances, empty rental ownership, and unchanged recomputed score authority. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-4/*` only after clean task approval.

---

### Task 5: Pure Pair Topology, Timing, Pricing, And Vehicle Witnesses

**Files:**
- Replace: `src/milkrun.py:1-160`
- Create: `tests/test_milkrun.py`

**Interfaces:**
- Produces in this task: `ROUTE_TYPES`, frozen `_PairCandidate`, Decimal/semantic helpers, and `_build_pair_candidates`.
- Removes in this task: `MILK_MAX_LEG_DESI`, `MAX_STOPS`, `MIN_GAIN_TL`, `_chain_eval`, `_build_chain`, `_try_group`, and the unsafe old `milk_run_improve` implementation.
- Defers the complete public pass and metrics to Task 6; no inactive fallback or partial old algorithm remains.

- [ ] **Step 1: Preserve the unsafe skeleton**

```powershell
git update-ref "refs/sdd/stage2/task-5/milkrun-before" $(git hash-object --no-filters -w "src/milkrun.py")
git status --short -- src/milkrun.py tests/test_milkrun.py
```

Expected: the task ref is created without changing the index or worktree. Retain it through every Task 5 review/fix round.

- [ ] **Step 2: Build exact synthetic pair fixtures**

In `tests/test_milkrun.py`, create `CompetitionData` with `O`, `B`, `C`, complete required forecast/route arcs, high handling/Tır capacities, no rentals, and Stage 1 vehicle values. Provide an independent `_direct_leg(item_id, dest, desi, load_start, data, vtype)` helper that computes load/departure/arrival/unload from `handling_minutes` and matrix travel without calling milk-run code.

Use asymmetric lanes so tests can prove the real second arc is used:

```text
O->B: 100 km, 60 minutes for every type
O->C: 120 km, 70 minutes for every type
B->C: 30 km, 20 minutes for every type
C->B: 40 km, 25 minutes for every type
forecast O->B and O->C SLA: one day
```

- [ ] **Step 3: Write failing pure candidate tests**

| Test | Exact assertion |
|---|---|
| `test_pair_builds_both_orders_with_actual_interstop_lanes` | Profitable candidates include `(B,C)` using `B->C` and `(C,B)` using `C->B`; second-segment arrival/cost differs by those actual arc values. |
| `test_pair_loads_everything_once_then_drops_by_destination` | Segment 0 starts at the exact shared source `load_start`, departs after combined handling, contains all parts; segment 1 departs at first unload end with no load delay and contains only destination-2 parts. |
| `test_pair_stores_continuous_vehicle_cost_only_on_first_segment` | Segment 0 cost equals `Decimal(str(hourly))*seconds/3600 + Decimal(str(per_km))*(km1+km2)` converted to float; segment 1 cost is exactly zero. |
| `test_pair_penalty_uses_each_original_final_drop` | Destination-1 parts use first unload end, destination-2 parts use second unload end, and no carried-row/intermediate penalty is included. |
| `test_pair_recomputes_old_scheduled_cost_and_sla` | Source `cost`/`penalty` fields set to impossible sentinel values do not affect `delta_tl`; recomputed scheduled direct times/rates do. |
| `test_pair_delta_must_be_strictly_negative` | Monkeypatched exact old/new equality produces no `_PairCandidate`; `-0.000001` produces one. |
| `test_nonintegral_rates_use_decimal_str` | A Kamyonet float rate `197.91666666666666` yields the exact `Decimal(str(rate))` formula and differs from binary `Decimal(rate)`. |
| `test_pair_does_not_apply_stage3_detour_ratio` | A route whose distance ratio exceeds 1.15 is still generated when exact economics are negative. |
| `test_pair_preserves_whole_part_identity_without_piece` | Patched `Part.piece` raises if called; destination-2 objects are `is`-identical across both templates; no new Part appears. |
| `test_combined_12001_is_rejected` | Complete 6,001 + 6,000 desi returns no candidates for any type. |
| `test_source_above_5600_is_allowed` | Complete 5,601 + 5,601 sources generate a Kamyon candidate; no source cap blocks them. |

Add exact vehicle witnesses using totals that force each minimum fitting type:

```python
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

    candidates = _build_pair_candidates(1, first, 2, second, pair_data)
    witness = next(candidate for candidate in candidates
                   if candidate.vtype == required_type)

    assert witness.delta_tl < Decimal("0")
    assert witness.legs[0].desi == total
    assert witness.legs[0].load_start == load_start
    assert witness.legs[1].cost == 0
    assert witness.legs[1].items[0][0] is second.items[0][0]
    assert pair_data.vehicles[required_type].capacity_desi >= total
```

Provide `pair_data` through the module's exact synthetic fixture. For each witness, also assert the Decimal cost formula and destination-specific SLA values already pinned by the preceding pure tests.

- [ ] **Step 4: Run red**

Run: `python -m pytest tests/test_milkrun.py -q`

Expected: `_PairCandidate` and `_build_pair_candidates` imports fail, or old skeleton semantics fail the exact tests.

- [ ] **Step 5: Replace the skeleton with exact Decimal and semantic primitives**

Define `_decimal(value, label)`, `_whole_desi`, `_part_key`, `_leg_key`, `_vehicle_cost_tl`, `_final_sla_tl`, and `_scheduled_direct_total_tl` locally in `src/milkrun.py`. Exact rules:

```text
all non-integral numeric inputs -> Decimal(str(value)); reject non-finite
whole handling/capacity total -> require total == total.to_integral_value()
part key -> (base_id, part_id, ready, deadline, carried_before,
             dest-or-empty, Decimal tuple desi)
leg key -> (kind != "Kiralık", load_start, dep, origin, dest, vtype,
            arr, unload_end, chain_id is None, chain_id-or--1, chain_seq,
            tuple(sorted part keys))
source vehicle cost -> source actual vtype Spot rate,
  integer seconds from source load_start through source unload_end,
  and source direct matrix km
source SLA -> every source item at source.unload_end
semantic keys -> fields/Decimal values only; never id(part), token, or hash order
```

Keep object identity only when copying existing tuples into segment item lists.

- [ ] **Step 6: Implement `_build_pair_candidates` for exactly two destinations**

The function assumes Task 6 will enforce source eligibility, but defensively returns `()` unless origins/load starts match, destinations differ, all parts match source destinations, and total is whole/positive. Then:

```text
source_tokens = tuple(sorted((first_token, second_token)))
old_total = recomputed scheduled total(first) + recomputed scheduled total(second)
for route_destinations in ((first.dest, second.dest),
                           (second.dest, first.dest)):
  require O->D1 and D1->D2 matrix arcs
  for vtype in ROUTE_TYPES whose capacity >= combined total:
    load_start = exact common source load_start
    dep1 = load_start + handling_minutes(combined total)
    arr1 = dep1 + actual O->D1 travel
    unload_end1 = arr1 + handling_minutes(D1 drop total)
    dep2 = unload_end1
    arr2 = dep2 + actual D1->D2 travel
    unload_end2 = arr2 + handling_minutes(D2 drop total)
    continuous cost = Spot hourly * (unload_end2-load_start) +
                      Spot per-km * (arc1 km + arc2 km)
    final SLA = D1 items at unload_end1 + D2 items at unload_end2
    delta = continuous cost + final SLA - old_total
    keep only delta < 0
```

Construct segment 0 as Spot/chosen-type `O -> D1` with `load_start`, `dep1`, `arr1`, `unload_end1`, all existing item tuples, full cost, D1-only penalty, `chain_id=0`, and `chain_seq=0`. Construct segment 1 as the same Spot/chosen-type `D1 -> D2` with `load_start=dep2`, `dep=dep2`, `arr=arr2`, `unload_end=unload_end2`, the exact same D2 item objects, zero cost, D2-only penalty, `chain_id=0`, and `chain_seq=1`. Return a tuple sorted by `(delta_tl, route_destinations, ROUTE_TYPES index, source semantic keys)`.

- [ ] **Step 7: Run green and scheduler/referee compatibility**

```powershell
python -m pytest tests/test_milkrun.py -q
python -m pytest tests/test_chain.py tests/test_schedule_chain.py tests/test_simulator_cost.py tests/test_simulator_full.py -q
```

Expected: all pass; no old four-stop symbol or behavior remains.

- [ ] **Step 8: Review the complete skeleton replacement**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-5/milkrun-before" $(git hash-object --no-filters -w "src/milkrun.py")
git diff --no-index -- NUL tests/test_milkrun.py
git status --short -- src/milkrun.py tests/test_milkrun.py
```

Review exact old/new economics, both orders/types, actual second arcs, no detour rule, no source cap, 12,001 rejection, final SLA, first-segment cost, zero second cost, identity preservation, and complete removal of unsafe growth code. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-5/*` only after clean task approval.

---

### Task 6: Deterministic Full Pair Pass, Complete Ledgers, Chain IDs, And Metrics

**Files:**
- Modify: `src/milkrun.py`
- Modify: `tests/test_milkrun.py`

**Interfaces:**
- Produces: frozen `MilkRunMetrics` and public `milk_run_improve` exactly as mapped.
- Consumes: Task 5 candidate templates, `analyze_leg_flows`, `physical_routes`, `HandlingLedger`, and `TirLedger`.
- Guarantees: one input graph copy, immutable candidate records, atomic commits, pair-only output, and deterministic metrics.

- [ ] **Step 1: Preserve the pure pair implementation**

```powershell
git update-ref "refs/sdd/stage2/task-6/milkrun-before" $(git hash-object --no-filters -w "src/milkrun.py")
git update-ref "refs/sdd/stage2/task-6/test-milkrun-before" $(git hash-object --no-filters -w "tests/test_milkrun.py")
git status --short -- src/milkrun.py tests/test_milkrun.py
```

Expected: both task refs preserve the approved Task 5 content without changing the index or worktree. Retain them through every Task 6 review/fix round.

- [ ] **Step 2: Add failing source eligibility and pair-only tests**

| Test | Exact assertion |
|---|---|
| `test_only_direct_loaded_spot_non_tir_sources_are_eligible` | Parametrize empty, rented, Tır, existing chain, wrong `part.dest`, and globally repeated `Part`; each remains unchanged and yields zero accepted chains. |
| `test_pair_requires_exact_equal_load_start` | Equal departure dates/times with load starts one minute apart do not pair. |
| `test_pair_requires_common_origin_and_distinct_destinations` | Different origins or equal destinations do not increment accepted metrics. |
| `test_no_source_leg_5600_cap_in_full_pass` | Two eligible sources above 5,600 but combined within 12,000 form one Kamyon chain. |
| `test_full_pass_rejects_combined_12001` | Pair is counted as evaluated but produces no chain. |
| `test_full_pass_considers_both_orders_and_all_fitting_types` | A spy around `_build_pair_candidates` observes one unordered pair and its returned order/type alternatives; metrics count one pair, not six variants. |
| `test_full_pass_is_exactly_two_segments_and_one_pass` | Every new `chain_id` has seq `[0,1]`; generated chain segments are never used as new sources. |
| `test_whole_part_identity_survives_commit` | No `Part.piece`; all accepted source identities load once and destination-2 identities repeat by `is` across exactly two segments. |
| `test_no_eligible_group_returns_owned_copy_and_zero_metrics` | Empty/ineligible input returns the one copied graph, unchanged semantic content, and every metric zero without a date-boundary error. |

Define metric counting exactly in tests:

```text
groups_considered = eligible (origin, exact load_start) buckets containing
                    at least two source legs and at least two destinations
pairs_evaluated = unordered distinct-destination source pairs handed to the
                  capacity/order/type evaluator, including over-12,000 pairs
chains_accepted = committed non-overlapping pairs
source_vehicles_replaced = 2 * chains_accepted
segments_created = 2 * chains_accepted
parts_consolidated = unique physical Part identities in committed sources
desi_consolidated = exact whole desi in committed sources
local_saving_tl = sum(-candidate.delta_tl) for committed candidates
chain_type_mix = sorted tuple of (selected vtype, chain count)
```

- [ ] **Step 3: Add failing transaction and ledger tests**

| Test | Exact assertion |
|---|---|
| `test_profitable_pair_rejected_by_complete_handling_ledger` | Local delta is negative, but its retimed unload conflicts with an unrelated event/day cap; no source is removed and metrics show zero commits. |
| `test_profitable_pair_rejected_by_unchanged_tir_visits` | An unrelated complete Tır ledger conflict makes the trial infeasible; no mutation occurs. |
| `test_chain_cannot_extend_stage1_final_cargo_date` | A locally profitable chain ending one date after max loaded input `unload_end.date()` is rejected; empty rented legs on a later date do not extend the boundary. |
| `test_rejected_trial_does_not_block_later_candidate` | First ranked overlapping candidate fails a ledger; a later feasible candidate using its sources can still commit. |
| `test_chain_ids_start_above_existing_and_rejections_do_not_consume` | Existing chain IDs 3 and 7 plus one rejected candidate produce first accepted ID 8, then 9. |
| `test_input_graph_and_forecast_objects_are_not_mutated` | Caller graph equals a pre-call deep copy; returned graph is distinct; original Part objects are untouched. |
| `test_milk_run_improve_deepcopies_graph_exactly_once` | Monkeypatched module `deepcopy` records one call with the input list and no other call. |

The complete handling trial must include a crossing-midnight case and assert the exact proportional split, not merely `violations == []`.

- [ ] **Step 4: Add failing deterministic non-overlap tests**

Use controlled candidates over four semantic sources. Add:

| Test | Exact assertion |
|---|---|
| `test_most_negative_candidate_wins_overlap` | Deltas `-30`, `-20`, `-10` select `-30` first and skip every candidate sharing either source. |
| `test_equal_delta_uses_route_type_source_semantic_key` | Equal deltas choose lexicographically defined route, then `ROUTE_TYPES` order, then source semantic keys; tokens and object IDs do not affect choice. |
| `test_every_input_permutation_has_same_semantic_output_and_metrics` | All permutations of a small source set return equal canonical leg signatures, selected routes/types, chain IDs, and `MilkRunMetrics`. |
| `test_duplicate_semantic_sources_preserve_multiplicity` | Equal semantic but physically distinct source legs are neither collapsed nor ranked by object ID; output multiplicity is constant across permutations. |

- [ ] **Step 5: Run red**

```powershell
python -m pytest tests/test_milkrun.py -q
```

Expected: public `milk_run_improve`/`MilkRunMetrics` is absent and full-pass assertions fail.

- [ ] **Step 6: Implement canonical eligibility and candidate generation over one copy**

```text
copied = deepcopy(legs) exactly once
ordered = stable sorted copied legs by the local semantic leg key
tokens = enumerate(ordered); token is state identity only
occurrences = Counter(id(part) for every copied item)
eligible source iff:
  items; kind Spot; vtype != "Tır"; chain_id is None
  every part.dest == leg.dest
  every occurrences[id(part)] == 1
  tuple desi is positive, integral, equals the existing part's complete desi
  every part.ready <= exact leg.load_start
group eligible tokens by (origin, load_start)
for each semantic group and unordered source pair with distinct destinations:
  increment pairs_evaluated once
  append every strict-negative candidate from _build_pair_candidates
```

Do not filter a source by its own desi. Candidate capacity filtering uses only allowed type capacities. Keep every original ineligible/unselected leg in working state.

- [ ] **Step 7: Implement complete trial feasibility without repair-module coupling**

Add a private `_trial_candidate_valid(legs: list[PlannedLeg], data) -> bool`:

```text
try flows = analyze_leg_flows(legs); reject ValueError
fresh HandlingLedger(data.handling_cap)
for each leg/flow:
  reject segment desi > current vtype capacity
  reject any flow.loaded part.ready > leg.load_start
  add exact aggregate loaded desi at origin/load_start
  add exact aggregate unloaded desi at dest/arr
reject handling.violations()

fresh TirLedger(data.tir_cap)
for each physical route in deterministic semantic order where vtype == "Tır":
  use a unique semantic-position vehicle key
  leg i origin event visit_id=i on dep.date()
  leg i dest event visit_id=i+1 on arr.date()
reject tir.violations()
return true
```

This reconstructs every unchanged Tır visit; new pair chains are non-Tır. It must not call `src.repair._trial_ledgers_valid` because that accepted Stage 1 helper intentionally rejects chains.

- [ ] **Step 8: Implement deterministic non-overlap selection and atomic commit**

Sort all immutable candidates by this exact key:

```text
(candidate.delta_tl,
 (origin, exact load_start, D1, D2),
 ROUTE_TYPES.index(candidate.vtype),
 tuple(sorted(source semantic leg keys)))
```

Then:

```text
stage1_end_date = max((unload_end.date() for copied loaded legs), default=None)
next_chain_id = max(existing non-None chain IDs, default=0) + 1
for candidate in sorted candidates:
  skip if either source token is absent from current working state
  committed legs = dataclasses.replace each template with next_chain_id
  reject if stage1_end_date is None or committed segment-1 unload_end.date() > stage1_end_date
  trial = complete current working graph minus two sources plus committed legs
  reject unless _trial_candidate_valid(trial, data)
  only now atomically delete both source tokens and insert both chain legs
  update every metric from exact candidate/source data
  increment next_chain_id only after commit
return canonical semantic-sorted working legs and frozen metrics
```

No candidate, ledger, or metric mutation occurs before the commit point. Do not run another generation pass.

- [ ] **Step 9: Run green and all local chain/referee tests**

```powershell
python -m pytest tests/test_milkrun.py -q
python -m pytest tests/test_chain.py tests/test_schedule_chain.py tests/test_simulator_cost.py tests/test_simulator_full.py tests/test_ledger.py -q
```

Expected: all pass, including deterministic permutations, single-copy ownership, and atomic ledger rejection.

- [ ] **Step 10: Review Task 6 in isolation**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-6/milkrun-before" $(git hash-object --no-filters -w "src/milkrun.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-6/test-milkrun-before" $(git hash-object --no-filters -w "tests/test_milkrun.py")
git status --short -- src/milkrun.py tests/test_milkrun.py
```

Review exact eligibility, one copy, all pairs/orders/types, immutable candidates, semantic ranking, non-overlap, fresh complete ledgers, no mutation on rejection, date boundary, sequential IDs, one pass, and exact metrics. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-6/*` only after clean task approval.

---

### Task 7: Global Stage 2 Decision And Chain-Aware Physical Metrics

**Files:**
- Modify: `src/milkrun.py`
- Modify: `src/evaluation.py:165-200`
- Modify: `tests/test_milkrun.py`
- Modify: `tests/test_evaluation.py:336-372`

**Interfaces:**
- Produces: frozen `MilkRunDecision` and `run_milk_run_stage` exactly as mapped.
- Changes semantics only: existing `PlanMetrics.rented_legs`, `spot_legs`, `vehicle_mix`, and Spot fill fields count physical routes.
- Consumes: accepted Stage 1 `PlanEvaluation`, `milk_run_improve`, `evaluate_legs(improved, forecast_df, data, fix=True)`, `improvement_tl`, and `accepts_candidate`.

- [ ] **Step 1: Preserve the pass and evaluation boundary**

```powershell
git update-ref "refs/sdd/stage2/task-7/milkrun-before" $(git hash-object --no-filters -w "src/milkrun.py")
git update-ref "refs/sdd/stage2/task-7/evaluation-before" $(git hash-object --no-filters -w "src/evaluation.py")
git update-ref "refs/sdd/stage2/task-7/test-milkrun-before" $(git hash-object --no-filters -w "tests/test_milkrun.py")
git update-ref "refs/sdd/stage2/task-7/test-evaluation-before" $(git hash-object --no-filters -w "tests/test_evaluation.py")
git status --short -- src/milkrun.py src/evaluation.py tests/test_milkrun.py tests/test_evaluation.py
```

Expected: all task refs preserve the approved Task 6 boundary without changing the index or worktree. Retain them through every Task 7 review/fix round.

- [ ] **Step 2: Write failing physical metric tests**

Add to `tests/test_evaluation.py`:

| Test | Exact assertion |
|---|---|
| `test_chain_metrics_count_one_physical_spot_route` | One two-segment Spot chain counts as one `spot_legs`, one vehicle in mix, and not two. |
| `test_chain_fill_uses_initial_onboard_load` | Fill uses seq-0 total onboard desi divided by route vehicle capacity, not the smaller seq-1 remainder and not a segment average. |
| `test_physical_below_thirty_threshold_is_strict` | A chain initial fill 1,679/5,600 counts and 1,680/5,600 does not. |
| `test_direct_stage0_stage1_metric_semantics_are_unchanged` | Existing standalone fixture still equals the current exact `PlanMetrics` object. |
| `test_malformed_metric_chain_raises` | Invalid sequence/topology is not silently counted. |

- [ ] **Step 3: Write failing global decision tests**

Add to `tests/test_milkrun.py`:

| Test | Exact assertion |
|---|---|
| `test_stage2_uses_accepted_stage1_evaluation_as_baseline` | `milk_run_improve` receives `baseline.legs`; only improved legs are evaluated; baseline is not re-evaluated. |
| `test_stage2_candidate_evaluates_with_fix_true` | `evaluate_legs` receives `fix=True`, the same forecast object, and the same data object. |
| `test_stage2_global_violation_rolls_back` | A cheaper violating candidate retains raw saving but `accepted=False` and `selected is baseline`. |
| `test_stage2_raw_one_tl_boundary` | `0.999999` rejects; exactly `1.00` and `1.000001` accept. |
| `test_stage2_inputs_remain_unchanged` | Baseline legs/frame/result and forecast frame equal pre-call deep copies. |

- [ ] **Step 4: Run red**

```powershell
python -m pytest tests/test_evaluation.py::test_chain_metrics_count_one_physical_spot_route tests/test_milkrun.py::test_stage2_uses_accepted_stage1_evaluation_as_baseline -v
```

Expected: segment-count metrics are wrong and `MilkRunDecision`/`run_milk_run_stage` is absent.

- [ ] **Step 5: Change metrics to physical routes**

In `summarize_evaluation`:

```text
routes = physical_routes(evaluation.legs)
rented_legs = count route[0].kind == "Kiralık"
spot_legs = count route[0].kind == "Spot"
vehicle_mix = Counter(route[0].vtype for route in routes)
for each Spot route:
  initial_onboard = Decimal(str(route[0].desi))
  fill = Fraction(initial_onboard) / route vehicle capacity
average and strict < 3/10 retain current exact Fraction behavior
costs and violations remain unchanged
```

All direct routes are singleton tuples, so accepted Stage 0/1 values remain identical.

- [ ] **Step 6: Implement the exact global Stage 2 boundary**

```python
@dataclass(frozen=True)
class MilkRunDecision:
    baseline: PlanEvaluation
    candidate: PlanEvaluation
    selected: PlanEvaluation
    metrics: MilkRunMetrics
    accepted: bool
    saving_tl: Decimal


def run_milk_run_stage(baseline, forecast_df, data) -> MilkRunDecision:
    improved, metrics = milk_run_improve(baseline.legs, data)
    candidate = evaluate_legs(improved, forecast_df, data, fix=True)
    saving = improvement_tl(baseline, candidate)
    accepted = accepts_candidate(
        baseline, candidate, minimum_saving=Decimal("1.00"))
    selected = candidate if accepted else baseline
    return MilkRunDecision(
        baseline, candidate, selected, metrics, accepted, saving)
```

Do not evaluate or mutate the baseline again. A locally improved but globally rejected graph is never selected.

- [ ] **Step 7: Add the full real-horizon pair-only acceptance test**

Build the unchanged 29 June through 5 July forecast, source plan, and accepted Stage 1 decision; then run Stage 2. Name the test `test_full_horizon_pair_only_stage_accepts_stage1_baseline` and assert:

```text
forecast remains 4046 rows / 4046 IDs / 4977975 desi and frame-equal
Stage 1 selected raw total == Decimal("14680184.845833339")
Stage 1 selected == 1092 segments/physical routes, 126 rented, 966 Spot,
                    3167 rows, zero violations, all chain_id None
Stage 2 baseline is Stage 1 selected
Stage 2 accepted and selected is candidate
raw Stage 2 saving >= Decimal("1.00") and candidate total < baseline total
candidate violations == [] and require_plan_total passes
candidate retains 1092 route segments; physical route count is
    1092 - chains_accepted and physical Spot count is 966 - chains_accepted
every new chain has exactly seq 0/1, one Spot non-Tır type, connected topology,
and final unload date <= Stage 1 final cargo-unload date
every physical Part loads exactly once, unloads at part.dest exactly once,
and repeated segment occurrences retain object identity/desi
physical rented count remains 126; no rented or Tır chain exists
MilkRunMetrics equations match actual chain/source/segment/type/inventory counts
```

Give the test pytest's `record_property` fixture and record `stage2_total_tl=str(candidate total)`, `stage2_saving_tl=str(decision.saving_tl)`, and every `MilkRunMetrics` field for diagnostics. Do not assert 277, 554, `11,993,748.820833342`, or `2,686,436.024999997`.

- [ ] **Step 8: Run green and the full real-horizon test**

```powershell
python -m pytest tests/test_evaluation.py tests/test_milkrun.py -q
python -m pytest tests/test_milkrun.py::test_full_horizon_pair_only_stage_accepts_stage1_baseline -v
python -m pytest tests/test_same_lane_repair.py tests/test_optimize.py tests/test_simulator_full.py -q
```

Expected: all pass; Stage 0/1 remain exact and the pair-only candidate clears the global raw-saving/referee gate without an exact batch-total assertion.

- [ ] **Step 9: Review Task 7 against its pre-task blobs**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-7/milkrun-before" $(git hash-object --no-filters -w "src/milkrun.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-7/evaluation-before" $(git hash-object --no-filters -w "src/evaluation.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-7/test-milkrun-before" $(git hash-object --no-filters -w "tests/test_milkrun.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-7/test-evaluation-before" $(git hash-object --no-filters -w "tests/test_evaluation.py")
git status --short -- src/milkrun.py src/evaluation.py tests/test_milkrun.py tests/test_evaluation.py
```

Review physical-route semantics, initial onboard fill, unchanged direct values, accepted Stage 1 baseline identity, one candidate evaluation with `fix=True`, raw boundary, rollback, nonmutation, and semantic full-horizon assertions. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-7/*` only after clean task approval.

---

### Task 8: Exact Stage 1 Gate And Staged Stage 2 Pipeline Integration

**Files:**
- Modify: `run.py:30-261`
- Modify: `tests/test_optimize.py:48-682`
- Verify only: `src/export.py`, `tests/test_export.py`, `src/optimize.py`, `src/repair.py`

**Interfaces:**
- Produces: `_require_stage1_entry`, `_require_stage2_entry`, `_print_pipeline_metrics`, and revised `_stage_and_publish` exactly as mapped.
- Preserves: `_require_stage0_entry`, `publish_workbooks`, workbook names, forecast construction, and original-memory/build versus reloaded-referee forecast separation.
- Consumes: `Stage1Decision`, `MilkRunDecision`, `run_same_lane_stage`, `run_milk_run_stage`, physical metrics, fingerprints, and artifact verification.

- [ ] **Step 1: Preserve the current Stage 1 pipeline and seams**

```powershell
git update-ref "refs/sdd/stage2/task-8/run-before" $(git hash-object --no-filters -w "run.py")
git update-ref "refs/sdd/stage2/task-8/test-optimize-before" $(git hash-object --no-filters -w "tests/test_optimize.py")
git status --short -- run.py tests/test_optimize.py src/export.py tests/test_export.py src/optimize.py src/repair.py
```

Expected: both task refs preserve the accepted Stage 1 pipeline without changing the index or worktree. Retain them through every Task 8 review/fix round.

- [ ] **Step 2: Add exact accepted Stage 1 constants and failing gate tests**

Define these exact constants in `run.py`:

```python
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
```

Add tests:

| Test | Exact assertion |
|---|---|
| `test_stage1_entry_accepts_only_complete_report_values` | A complete exact decision passes. |
| `test_stage1_entry_requires_accepted_selected_candidate` | False accepted flag, selected baseline, or candidate violations each fail. |
| `test_stage1_entry_rejects_each_raw_cost_difference` | `1E-12` change to vehicle, SLA, total, global saving, or local saving fails; there is no cent tolerance. |
| `test_stage1_entry_rejects_each_count_and_repair_metric_difference` | Parametrize every segment/route/kind/row/repair field `+1`; each named mismatch appears. |
| `test_stage1_entry_requires_direct_only_physical_routes` | A chain with unchanged segment count fails exact entry. |
| `test_stage1_entry_aggregates_independent_mismatches` | One RuntimeError contains every independently measurable mismatch. |

- [ ] **Step 3: Add failing Stage 0/1/2 order and decision-gate tests**

| Test | Exact assertion |
|---|---|
| `test_main_order_is_stage1_then_stage0_gate_then_stage1_gate_then_stage2` | Event order is build, Stage 1, Stage 0 gate on `stage1.baseline`, Stage 1 gate, Stage 2 with `stage1.selected`, Stage 2 gate, artifact flow. |
| `test_stage1_rejection_never_calls_stage2_or_publication` | Existing official bytes stay unchanged; Stage 2 and publication spies are untouched. |
| `test_stage2_entry_requires_stage1_selected_baseline` | A value-equal but different baseline object fails. |
| `test_stage2_entry_requires_acceptance_candidate_selection_and_raw_saving` | Rejection, wrong selected object, violation, or `0.999999` fails. |
| `test_stage2_rejection_never_writes_or_publishes` | No plan artifact write and no official change. |

- [ ] **Step 4: Add failing staged artifact/publication seam tests**

Update existing helpers to build separate Stage 1 and Stage 2 decisions. Add/update:

| Test | Exact assertion |
|---|---|
| `test_stage2_artifacts_verify_stage1_baseline_before_selected` | Events are write/verify `Stage1-baseline.xlsx`, write/verify Stage 2 `Tasima-plani.xlsx`, then publish. |
| `test_staged_baseline_is_stage1_selected_not_stage0` | Baseline frame/fingerprint/expected total are `stage1.selected`. |
| `test_stage2_sub_one_tl_artifact_saving_never_publishes` | In-memory accepted, artifact raw saving `0.999999`; official bytes remain unchanged. |
| `test_stage1_or_stage2_rejection_preserves_both_official_files` | Parametrize each rejected stage; old plan/forecast bytes remain exact. |
| `test_success_uses_existing_plan_first_publication` | `_stage_and_publish` calls `publish_workbooks(selected plan, staged forecast, official plan, official forecast)` only after both verifies. |
| `test_main_never_prints_completion_after_stage2_or_publication_exception` | Completion text is absent for either exception. |
| `test_main_keeps_memory_forecast_for_build_and_reloaded_forecast_for_both_stages` | `prepare_frame` receives original; both stage decisions receive the reloaded referee frame. |

- [ ] **Step 5: Run red**

```powershell
python -m pytest tests/test_optimize.py::test_stage1_entry_accepts_only_complete_report_values tests/test_optimize.py::test_main_order_is_stage1_then_stage0_gate_then_stage1_gate_then_stage2 tests/test_optimize.py::test_stage2_artifacts_verify_stage1_baseline_before_selected -v
```

Expected: new helpers/signature are missing and current pipeline stages Stage 0 as the artifact baseline.

- [ ] **Step 6: Implement exact Stage 1 and Stage 2 entry gates**

`_require_stage1_entry` collects, rather than short-circuits, all checks:

```text
decision.accepted is True
decision.selected is decision.candidate
selected has no violations
len(selected.legs) == 1092
len(physical_routes(selected.legs)) == 1092
all selected chain_id is None
physical rented/Spot == 126/966
len(selected.plan_frame) == 3167
Decimal(str(vehicle/SLA/total)) exactly equals the three raw constants
decision.saving_tl exactly equals STAGE1_GLOBAL_SAVING
every RepairMetrics field exactly equals its constant
```

Reject non-finite Decimal values and include all mismatch labels in one `RuntimeError`.

`_require_stage2_entry` requires:

```text
stage2.baseline is stage1.selected
stage2.accepted is True
stage2.selected is stage2.candidate
stage2.baseline and candidate both have zero violations
stage2.saving_tl == improvement_tl(stage2.baseline, stage2.candidate)
stage2.saving_tl >= Decimal("1.00")
```

- [ ] **Step 7: Revise artifact staging around Stage 1 baseline and Stage 2 selected**

At `_stage_and_publish` entry, rerun `_require_stage1_entry` and `_require_stage2_entry` before writing a plan artifact. Then:

```text
write stage1.selected.plan_frame -> staging/Stage1-baseline.xlsx
verify it against stage1.selected raw total and plan fingerprint
write stage2.selected.plan_frame -> staging/Tasima-plani.xlsx
verify it against stage2.selected raw total and plan fingerprint
artifact_saving = Decimal(str(stage1 artifact total))
                  - Decimal(str(stage2 artifact total))
require artifact_saving >= Decimal("1.00")
call existing publish_workbooks with staged plan first and immutable staged forecast second
```

Any exception occurs before publication or enters the existing rollback-safe publication transaction. Do not write an official path directly.

- [ ] **Step 8: Integrate Stage 2 into `main` without touching the daily optimizer**

Use this exact order:

```text
load data; build in-memory forecast; capture forecast fingerprint
create out/.stage2-* temporary directory
write/reload staged forecast; require fingerprint equality
prepare/build source legs from original in-memory forecast
stage1 = run_same_lane_stage(source, reloaded forecast, data)
_require_stage0_entry(in-memory forecast, stage1.baseline, data)  # first gate
_require_stage1_entry(stage1, data)                               # exact gate
stage2 = run_milk_run_stage(stage1.selected, reloaded forecast, data)
_require_stage2_entry(stage1, stage2)
print Stage 0 baseline, Stage 1 selected, Stage 2 candidate physical metrics;
print RepairMetrics and MilkRunMetrics; print raw savings/acceptance/runtimes
_stage_and_publish(stage1, stage2, staged_forecast_path,
                   expected_fingerprint, data, staging_dir, OUT_DIR)
print completion only after publication returns
```

Do not import `src.milkrun` from `src.optimize.py`; only `run.py` owns stage orchestration.

- [ ] **Step 9: Run green pipeline seams and exact baseline regressions**

```powershell
python -m pytest tests/test_optimize.py -q
python -m pytest tests/test_export.py tests/test_evaluation.py tests/test_same_lane_repair.py tests/test_milkrun.py -q
python -m pytest tests/test_optimize.py::test_full_horizon_same_lane_stage_accepts_fixed_stage0_baseline tests/test_milkrun.py::test_full_horizon_pair_only_stage_accepts_stage1_baseline -v
```

Expected: all pass; Stage 0/1 exact gates precede Stage 2; rejection preserves official paths; success verifies both artifacts before plan-first publication.

- [ ] **Step 10: Review Task 8 and verify excluded modules did not change**

```powershell
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-8/run-before" $(git hash-object --no-filters -w "run.py")
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-8/test-optimize-before" $(git hash-object --no-filters -w "tests/test_optimize.py")
git diff --no-ext-diff -- src/export.py src/optimize.py src/repair.py
git status --short -- run.py tests/test_optimize.py src/export.py src/optimize.py src/repair.py
```

Review exact Stage 1 values, Stage 0-first order, baseline object identity, raw thresholds, both staged fingerprints/referees, no publication on either rejection, output metrics, immutable forecast, and milk-run exclusion from `optimize.py`. Do not stage or commit. The controller deletes `refs/sdd/stage2/task-8/*` only after clean task approval.

---

### Task 9: Full-Horizon Acceptance, Official Artifacts, Documentation, And Final Scoped Review

**Files:**
- Verify: `src/chain.py`
- Verify: `src/schedule.py`
- Verify: `src/simulator.py`
- Verify: `src/milkrun.py`
- Verify: `src/evaluation.py`
- Verify: `run.py`
- Verify: all focused and existing tests
- Replace only through accepted `python run.py`: `out/Tasima-plani.xlsx`, `out/Talep-tahmini.xlsx`
- Modify only after every acceptance check passes: `PLAN.md`
- Create only after every acceptance check passes: `docs/superpowers/reports/2026-07-25-stage2-q-and-a-correct-milk-run-acceptance.md`

**Interfaces:**
- Consumes Tasks 1-8.
- Produces no optimization behavior; it produces accepted official workbooks and complete fresh evidence only.
- Prohibits edits to older architecture, roadmap, comparison, spec, plan, and report documents.

- [ ] **Step 1: Capture pre-acceptance status and official fingerprints**

```powershell
git update-ref "refs/sdd/stage2/task-9/plan-before" $(git hash-object --no-filters -w "PLAN.md")
if (Test-Path -LiteralPath "out/Tasima-plani.xlsx") { Get-FileHash -Algorithm SHA256 -LiteralPath "out/Tasima-plani.xlsx" }
if (Test-Path -LiteralPath "out/Talep-tahmini.xlsx") { Get-FileHash -Algorithm SHA256 -LiteralPath "out/Talep-tahmini.xlsx" }
git status --short
git diff --no-ext-diff -- src/chain.py src/schedule.py src/simulator.py src/milkrun.py src/evaluation.py run.py tests/test_chain.py tests/test_schedule_chain.py tests/test_milkrun.py tests/test_simulator_cost.py tests/test_simulator_full.py tests/test_evaluation.py tests/test_optimize.py PLAN.md
```

Record the printed pre-acceptance hashes and pre-existing unrelated dirty paths in the SDD ledger. The task ref preserves `PLAN.md` without changing the index or worktree; retain it through every Task 9 review/fix round. Do not modify or remove unrelated paths.

- [ ] **Step 2: Run focused Stage 2 acceptance tests**

```powershell
python -m pytest tests/test_chain.py tests/test_schedule_chain.py tests/test_simulator_cost.py tests/test_simulator_full.py tests/test_milkrun.py tests/test_evaluation.py tests/test_optimize.py tests/test_export.py -q
```

Expected: exit 0 with zero failures, including exact Stage 0/1 gates, three vehicle witnesses, forced chain, independent declarations, full horizon, artifacts, rejection, and rollback.

- [ ] **Step 3: Run the complete suite from the dirty worktree**

Run: `python -m pytest -q`

Expected: exit 0; record exact count/runtime. The accepted count must be greater than the 291-test entry suite.

- [ ] **Step 4: Run the real staged pipeline**

Run: `python run.py`

Require all printed gates before completion:

```text
unchanged forecast fingerprint / 4046 IDs / 4977975 desi
exact Stage 0 reproduction
exact accepted Stage 1 entry at raw 14680184.845833339 TL
Stage 2 accepted with raw saving >= 1.00 TL
zero Stage 0/1/2 violations
physical metrics and every MilkRunMetrics field
Stage 1 baseline artifact verification
Stage 2 selected artifact verification and raw artifact saving >= 1.00 TL
plan-first publication followed by forecast publication
completion printed only after publication
```

- [ ] **Step 5: Verify official Excel type/schema and unchanged forecast fingerprint**

```powershell
@'
from datetime import date, time
import pandas as pd
from openpyxl import load_workbook
from src.data import load_all
from src.evaluation import forecast_fingerprint
from src.forecast import forecast_horizon, to_forecast_frame
from src.schemas import FORECAST_COLS, PLAN_COLS, validate_forecast_grid, validate_plan

data = load_all()
forecast = pd.read_excel("out/Talep-tahmini.xlsx")
plan = pd.read_excel("out/Tasima-plani.xlsx")
expected = to_forecast_frame(forecast_horizon(
    data.demand, date(2026, 6, 29), date(2026, 7, 5)))
workbook = load_workbook("out/Talep-tahmini.xlsx")
sheet = workbook.active
assert isinstance(sheet["C2"].value, time)
assert sheet["C2"].number_format == "h:mm"
assert sheet["F2"].number_format == "0.000"
assert list(forecast.columns) == FORECAST_COLS
assert list(plan.columns) == PLAN_COLS
assert validate_forecast_grid(
    forecast, data, date(2026, 6, 29), date(2026, 7, 5)) == []
assert validate_plan(plan, data) == []
assert len(forecast) == 4046
assert forecast["Talep ID"].nunique() == 4046
assert int(forecast["Tahmin Edilen Desi"].sum()) == 4977975
assert forecast_fingerprint(forecast) == forecast_fingerprint(expected)
print("official schema/forecast: PASS", len(plan))
'@ | python -
```

Expected: `official schema/forecast: PASS` and the fresh Stage 2 plan-row count.

- [ ] **Step 6: Independently reconstruct Stage 0, exact Stage 1, selected Stage 2, inventory, and artifact score**

```powershell
@'
from collections import Counter
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import pandas as pd

from run import (_require_stage0_entry, _require_stage1_entry,
                 _require_stage2_entry)
from src.chain import analyze_leg_flows, physical_routes
from src.data import load_all
from src.evaluation import (forecast_fingerprint, plan_fingerprint,
                            summarize_evaluation, verify_plan_artifact)
from src.export import require_plan_total
from src.forecast import forecast_horizon, to_forecast_frame
from src.milkrun import run_milk_run_stage
from src.optimize import build_plan, prepare_frame
from src.repair import run_same_lane_stage
from src.schemas import validate_plan
from src.simulator import simulate

data = load_all()
memory_forecast = to_forecast_frame(forecast_horizon(
    data.demand, date(2026, 6, 29), date(2026, 7, 5)))
memory_before = memory_forecast.copy(deep=True)
artifact_forecast = pd.read_excel("out/Talep-tahmini.xlsx")
artifact_plan = pd.read_excel("out/Tasima-plani.xlsx")
days = [date(2026, 6, 29) + timedelta(days=i) for i in range(7)]
source = build_plan(data, prepare_frame(memory_forecast), days)
source_before = deepcopy(source)
stage1 = run_same_lane_stage(source, artifact_forecast, data)
_require_stage0_entry(memory_forecast, stage1.baseline, data)
_require_stage1_entry(stage1, data)
stage2 = run_milk_run_stage(stage1.selected, artifact_forecast, data)
_require_stage2_entry(stage1, stage2)

assert source == source_before
pd.testing.assert_frame_equal(memory_forecast, memory_before)
assert forecast_fingerprint(memory_forecast) == forecast_fingerprint(artifact_forecast)
assert validate_plan(artifact_plan, data) == []
assert plan_fingerprint(artifact_plan) == plan_fingerprint(stage2.selected.plan_frame)
official = simulate(artifact_plan, artifact_forecast, data)
assert official.violations == []
require_plan_total(artifact_plan, official.total_cost)
artifact = verify_plan_artifact(
    "out/Tasima-plani.xlsx",
    "out/Talep-tahmini.xlsx",
    data,
    expected_total=Decimal(str(stage2.selected.result.total_cost)),
    expected_forecast_fingerprint=forecast_fingerprint(artifact_forecast),
    expected_plan_fingerprint=plan_fingerprint(stage2.selected.plan_frame),
)
assert artifact.violations == []
raw_saving = (Decimal(str(stage1.selected.result.total_cost))
              - Decimal(str(official.total_cost)))
assert raw_saving >= Decimal("1.00")

routes = physical_routes(stage2.selected.legs)
chains = [route for route in routes if route[0].chain_id is not None]
assert chains
assert len(stage2.selected.legs) == 1092
assert len(routes) == 1092 - len(chains)
assert all(len(route) == 2 for route in chains)
assert all([leg.chain_seq for leg in route] == [0, 1] for route in chains)
assert all(route[0].kind == "Spot" and route[0].vtype != "Tır"
           for route in chains)
metrics = summarize_evaluation(stage2.selected, data)
assert metrics.rented_legs == 126
assert metrics.spot_legs == 966 - len(chains)

def item_key(part, desi):
    return (part.base_id, part.part_id, part.ready, part.deadline,
            part.carried_before, part.dest, Decimal(str(part.desi)),
            Decimal(str(desi)))

baseline_inventory = Counter(
    item_key(part, desi)
    for leg in stage1.selected.legs
    for part, desi in leg.items)
flows = analyze_leg_flows(stage2.selected.legs)
final_inventory = Counter(
    item_key(part, desi)
    for leg, flow in zip(stage2.selected.legs, flows)
    for part, desi in flow.unloaded
    if leg.dest == part.dest)
loaded_counts = Counter(
    id(part) for flow in flows for part, _desi in flow.loaded)
final_counts = Counter(
    id(part)
    for leg, flow in zip(stage2.selected.legs, flows)
    for part, _desi in flow.unloaded
    if leg.dest == part.dest)
assert baseline_inventory == final_inventory
assert loaded_counts and set(loaded_counts.values()) == {1}
assert final_counts and set(final_counts.values()) == {1}
assert set(loaded_counts) == set(final_counts)
stage1_end = max(
    leg.unload_end.date() for leg in stage1.selected.legs if leg.items)
stage2_end = max(
    leg.unload_end.date()
    for leg, flow in zip(stage2.selected.legs, flows)
    if any(leg.dest == part.dest for part, _desi in flow.unloaded))
assert stage2_end <= stage1_end

bad = artifact_plan.copy(deep=True)
bad.loc[bad.index[0], "Yolculuk süresi"] += 1
bad_result = simulate(bad, artifact_forecast, data)
assert any("yolculuk" in violation.lower()
           for violation in bad_result.violations)

print("stage0", Decimal(str(stage1.baseline.result.total_cost)))
print("stage1", Decimal(str(stage1.selected.result.total_cost)))
print("stage2", Decimal(str(official.total_cost)))
print("raw_saving", raw_saving)
print("physical_routes", len(routes), "chains", len(chains),
      "segments", len(stage2.selected.legs), "rentals", metrics.rented_legs)
print("declaration/inventory/artifact: PASS")
'@ | python -
```

Expected: exact Stage 0 and Stage 1 raw totals, a lower Stage 2 raw total, raw saving at least 1.00, 126 rentals, nonzero pair chains, and `declaration/inventory/artifact: PASS`.

- [ ] **Step 7: Record fresh official hashes without using them as semantic gates**

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath "out/Tasima-plani.xlsx"
Get-FileHash -Algorithm SHA256 -LiteralPath "out/Talep-tahmini.xlsx"
```

Record both values in the report. Fingerprint tuple equality and independent simulation, not XLSX package hashes, are the acceptance gates.

- [ ] **Step 8: Create the complete Stage 2 acceptance report only now**

Verify the parent and create only the new report:

```powershell
if (-not (Test-Path -LiteralPath "docs/superpowers/reports")) { throw "Expected reports directory is missing" }
```

Create `docs/superpowers/reports/2026-07-25-stage2-q-and-a-correct-milk-run-acceptance.md` with header `# Stage 2 Q&A-Correct Pair-Only Milk-Run Acceptance Report`. Record exact fresh values for:

- focused/full test commands, counts, runtimes, and real pipeline runtime;
- exact Stage 0 and accepted Stage 1 reproduction values and gate order;
- Stage 2 vehicle/SLA/raw total, raw saving, violations, segments, physical rented/Spot, physical mix/fill/<30%, and final delivery date;
- every `MilkRunMetrics` field and exact local/global/artifact Decimal saving;
- forecast row/ID/desi fingerprint, Excel cell type/format, schema, and unchanged-frame evidence;
- one V-ID/type per chain, pair-only seq 0/1, all three synthetic vehicle witnesses, actual inter-stop lanes, final-only SLA, no intermediate handling, full row travel, cost once, and physical Part inventory;
- independent simulator declaration acceptance plus wrong-travel/handling/SLA/duplicated-cost rejection tests;
- staged Stage 1/Stage 2 artifact fingerprints, declared reconciliation, independent re-simulation, and official hashes;
- Stage 1/Stage 2 rejection preservation, plan-first publication, rollback tests, and completion-print ordering;
- the prior read-only values `277`, `554`, `11,993,748.820833342 TL`, and `2,686,436.024999997 TL` under a section explicitly titled `Directional Pre-Implementation Pair Evidence`; state that none is an exact acceptance assertion;
- deterministic four-stop research as deferred, non-gating Stage 2b work with no implementation in this change;
- pre/final dirty status, intended files, unrelated pre-existing dirty paths, and confirmation that no stage, commit, clean, revert, reset, or discard command ran.

If any fresh value is unavailable, rerun its exact command before writing the report; do not record a partial or estimated value.

- [ ] **Step 9: Update `PLAN.md` only after report evidence is complete**

Update only current status content:

```text
architecture: insert chain.py, chain-aware schedule, independent declaration
referee, physical metrics, pair-only milkrun pass, and Stage 2 pipeline
verified results: retain exact Stage 0/1 tables and add exact fresh Stage 2 table
tests/runtime: replace 291/old runtime with fresh accepted values
gates: exact Stage 1 entry, raw Stage 2/artifact >=1.00, fingerprints,
       declarations, inventory, final date, rollback, plan-first publication
remaining work: mark pair-only Stage 2 complete; list 3/4-stop Stage 2b and
                deterministic four-stop research as independently gated/deferred
git state: all Stage 1/2 work remains dirty, unstaged, and uncommitted
```

Do not modify older docs named in Global Constraints.

- [ ] **Step 10: Run final tests and whitespace/status checks after docs**

```powershell
python -m pytest tests/test_chain.py tests/test_schedule_chain.py tests/test_simulator_cost.py tests/test_simulator_full.py tests/test_milkrun.py tests/test_evaluation.py tests/test_optimize.py tests/test_export.py -q
python -m pytest -q
git diff --check
git diff --cached --name-only
git status --short
```

Expected: both pytest commands exit 0; `git diff --check` exits 0 (existing LF/CRLF warnings may be informational); `git diff --cached --name-only` contains no Stage 2 task path; status contains intended uncommitted Stage 2 files plus untouched pre-existing dirty files; nothing from this plan is staged.

- [ ] **Step 11: Perform the final task-scoped reviewer gate**

```powershell
git diff --no-ext-diff -- src/schedule.py src/simulator.py src/milkrun.py src/evaluation.py run.py tests/test_simulator_cost.py tests/test_simulator_full.py tests/test_evaluation.py tests/test_optimize.py PLAN.md
git diff --no-index -- NUL src/chain.py
git diff --no-index -- NUL tests/test_chain.py
git diff --no-index -- NUL tests/test_schedule_chain.py
git diff --no-index -- NUL tests/test_milkrun.py
git diff --no-index -- NUL docs/superpowers/reports/2026-07-25-stage2-q-and-a-correct-milk-run-acceptance.md
git diff --exit-code --no-ext-diff "refs/sdd/stage2/task-9/plan-before" $(git hash-object --no-filters -w "PLAN.md")
git status --short
```

Expected: new-file no-index commands and the `PLAN.md` blob diff display content and exit 1 when changes exist. Reviewer confirms every resolved requirement, exact signature/type, strict TDD witness, circular-import boundary, Windows command, full fixture, artifact gate, excluded document/module, and dirty-worktree prohibition. No stage or commit follows this review. The controller deletes `refs/sdd/stage2/task-9/*` only after clean task approval.

---

## Plan Author Self-Review

- [x] Spec coverage: every resolved architecture/scope decision and required test/acceptance gate maps to Tasks 1-9.
- [x] Placeholder scan: no incomplete in-scope test body, unspecified error handling, or unnamed fixture remains; typing ellipses denote variadic tuples only, and out-of-scope Stage 2b is explicitly excluded rather than left incomplete.
- [x] Type/signature consistency: `LegFlow`, `DeclaredRow`, `_PairCandidate`, `MilkRunMetrics`, `MilkRunDecision`, physical `PlanMetrics`, and pipeline helper signatures agree across producers, consumers, tests, and acceptance scripts.
- [x] Circular imports: scheduler/evaluation/milk-run depend on neutral `chain.py`; `optimize.py` does not depend back on them; simulator remains independently outside that graph.
- [x] Windows commands: every execution/blob-ref/review command is PowerShell 5.1-compatible, uses quoted paths where needed, and preserves pre-task dirty content without shell file-copy/write commands.
- [x] Executable fixtures: route-flow, manual declaration, three vehicle types, forced pair, ledger/date rejection, full horizon, artifact, inventory, and publication fixtures have exact values and named assertions.
- [x] Worktree safety: the plan contains no stage/commit step and explicitly prohibits stage, commit, clean, revert, reset, checkout, restore, and discard operations.

---

## Completion Definition

Pair-only Stage 2 is complete only when Stage 0 reproduces first, the exact accepted Stage 1 result passes its raw/count/repair/direct-topology gate, every new route is an eligible deterministic two-stop Spot non-Tır chain, chain flows/IDs/handling/SLA/travel/cost declarations are correct, the independent simulator rejects every declaration corruption and accepts the full current artifacts, physical inventory and final-delivery date are preserved, Stage 2 saves at least 1.00 TL raw in memory and after Excel reload, both staged artifacts pass schema/fingerprint/reconciliation/referee checks, 126 rentals remain, plan-first rollback-safe publication succeeds, the complete suite passes above its 291-test entry count, fresh evidence is recorded only after acceptance, older docs remain untouched, and all work remains unstaged and uncommitted.
