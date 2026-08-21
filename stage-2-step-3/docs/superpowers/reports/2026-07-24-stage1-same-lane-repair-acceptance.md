# Stage 1 Same-Lane Repair Acceptance Report

## Decision

Stage 1 passed the pre-publication, in-memory, official-workbook, and artifact
acceptance gates on 25 July 2026. The accepted candidate is the Stage 1
same-lane repair result; milk-run remains inactive.

## Fresh Test And Runtime Evidence

| Command | Result |
|---|---|
| `python -m pytest tests/test_evaluation.py tests/test_same_lane_repair.py tests/test_export.py tests/test_optimize.py -q` | `114 passed in 82.61s (0:01:22)` |
| `python -m pytest -q` | `267 passed in 192.37s (0:03:12)` |
| `python run.py` | Stage 1 runtime `69.4 s`; publication completed; total runtime `85.7 s` |

The focused suite includes the full-horizon decision, whole/direct move,
strictly-negative local delta, complete handling/Tir ledger, artifact identity,
re-simulation, rejection, and rollback coverage.

## Baseline And Candidate

The values below are from a fresh reconstruction and referee command after the
real pipeline published the official files. Raw totals are the exact
`Decimal(str(simulator_value))` values used at the acceptance boundary.

| Metric | Stage 0 baseline | Stage 1 candidate |
|---|---:|---:|
| Legs | 1,269 | 1,092 |
| Plan rows | 3,167 | 3,167 |
| Rented legs | 126 | 126 |
| Spot legs | 1,143 | 966 |
| Sorted vehicle mix | Hafif Kamyon 24; Kamyon 196; Kamyonet 950; Tır 99 | Hafif Kamyon 24; Kamyon 196; Kamyonet 773; Tır 99 |
| Vehicle cost, raw TL | 15,460,592.572222233 | 12,510,401.245833337 |
| Vehicle cost, displayed TL | 15,460,592.57 | 12,510,401.25 |
| SLA penalty, raw TL | 1,020,367.2000000012 | 2,169,783.600000002 |
| SLA penalty, displayed TL | 1,020,367.20 | 2,169,783.60 |
| Total cost, raw TL | 16,480,959.772222234 | 14,680,184.845833339 |
| Total cost, displayed TL | 16,480,959.77 | 14,680,184.85 |
| Unweighted Spot fill, exact | 92,207,719 / 192,024,000 | 30,735,517 / 54,096,000 |
| Unweighted Spot fill, displayed | 48.02% | 56.82% |
| Spot legs strictly below 30% | 480 | 296 |
| Referee violations | 0 | 0 |

The exact official verifier output was:

```text
16480959.772222233936 12510401.25 2169783.60 14680184.845833338797 0 1800774.926388895
```

The raw global saving is `1,800,774.926388895 TL`, above the inclusive
`1.00 TL` gate. `decision.accepted == True` and the selected object is the
candidate. Both baseline and candidate have zero violations.

## Repair Metrics

| Metric | Exact value |
|---|---:|
| Donors considered | 1,003 |
| Moves accepted | 177 |
| Parts moved | 394 |
| Desi moved | 59,852 |
| Spot legs removed | 177 |
| Local Decimal saving, TL | 1,800,774.926388888876856333333 |
| Global Decimal saving, TL | 1,800,774.926388895 |

The local total is the sum of accepted whole, direct, strictly negative moves;
each trial passed fresh complete-ledger validation before mutation. The global
number is independently recomputed from the two complete simulator totals and
is the gating value.

## Forecast Evidence

The first exact official workbook command exited zero and printed:

```text
time h:mm 0.000 4046 4046 4977975
```

This proves a real Excel `time` in `C2`, `h:mm` in `C2`, `0.000` in `F2`,
4,046 rows, 4,046 unique IDs, and 4,977,975 total desi. The exact column-order
check passed, `validate_forecast_grid(...)` returned `[]`, and the official
row-level fingerprint equaled the independently rebuilt in-memory forecast
fingerprint. Supplemental command output recorded:

```text
forecast_columns_equal True
forecast_schema_errors []
forecast_fingerprint_equal True
forecast_fingerprint_rows 4046
forecast_fingerprint_sha256 5aa8c2044d8e5dc4fef06e4c3b5c5fb3367e6e2d9b6d37ca99e0dcbd9c31a187
```

The SHA-256 value is a compact evidence digest of `repr()` of the canonical
fingerprint tuple; the direct tuple equality, not the digest, is the gate.

## Plan And Artifact Evidence

The official plan retained exact `PLAN_COLS` order, `validate_plan(...)`
returned `[]`, and its canonical row-level fingerprint equaled the fingerprint
of the independently reconstructed selected candidate:

```text
plan_columns_equal True
plan_schema_errors []
plan_fingerprint_equal True
plan_fingerprint_rows 3167
plan_fingerprint_sha256 7c672536161693a8630ef05d950a193bc0772f769450f1992a1a144cccba38b6
```

The declared/referee reconciliation and independent artifact reload produced:

```text
official_simulation 12510401.245833337 2169783.600000002 14680184.845833339 0
declared_reconciliation 14680184.845833333319835 14680184.845833339 -5.680165E-9
artifact_resimulation 12510401.245833337 2169783.600000002 14680184.845833339 0
artifact_expected_delta 0E-9
```

`require_plan_total(...)` completed successfully. `verify_plan_artifact(...)`
reloaded both official workbooks, checked forecast and plan fingerprints,
validated schema, re-simulated to the candidate's exact raw total, found zero
violations, and repeated declared-total reconciliation.

## D00082 Diagnostic

The optional witness was available. It remained a direct Denizli to Mardin
Kamyonet movement with 38 desi, but moved from its original Spot leg to a later
accepted receiver:

| State | Vehicle | Departure | Arrival | Lane | Type/desi |
|---|---|---|---|---|---|
| Before | V0128 | 29.06.2026 17:01 | 30.06.2026 09:28 | Denizli -> Mardin | Spot Kamyonet / 38 |
| After | V0781 | 04.07.2026 17:01 | 05.07.2026 09:28 | Denizli -> Mardin | Spot Kamyonet / 38 |

The historical `16,454,285.85 TL` total and `26,673.93 TL` saving are
non-gating prior witness evidence only. Neither value is used by this
full-horizon acceptance.

## Publication And Rollback

The real `python run.py` command completed all staged gates and printed
`Yayın tamamlandı; toplam 85.7 sn` only after publication returned. The
official files were replaced only by the accepted staged path. Both subsequent
official workbook commands loaded and verified those published files.

Publication order and rollback behavior were rerun verbosely:

```text
tests/test_export.py::test_publish_success_plan_then_forecast PASSED
tests/test_export.py::test_publish_second_failure_restores_both PASSED
tests/test_export.py::test_publish_failure_removes_absent_destinations PASSED
tests/test_optimize.py::test_rejected_stage_never_publishes PASSED
tests/test_optimize.py::test_all_artifacts_precede_publication PASSED
tests/test_optimize.py::test_sub_one_tl_artifact_saving_never_publishes PASSED
6 passed in 1.42s
```

`test_publish_success_plan_then_forecast` asserts the exact replacement order:
staged plan to official plan first, then staged forecast to official forecast.
The failure tests prove restoration of both existing destinations, removal of
both initially absent destinations, no publication on decision rejection, and
no publication when artifact saving is below raw `1.00 TL`.

## Worktree Review

The pre-acceptance status was captured before tests or publication. Stage 1
production/tests and `out/` were already dirty or untracked. Unrelated
pre-existing paths were preserved: `.claude/`, `ARCHITECTURE.md`, `ROADMAP.md`,
`docs/comparison/`, `src/optimize.py`, `src/schedule.py`, `src/schemas.py`,
`src/simulator.py`, `tests/test_schemas.py`, `tests/test_simulator_cost.py`, and
`tests/test_simulator_full.py`, together with the existing plan/spec documents.
No stage, commit, clean, revert, reset, or manual workbook publication command
was used.

After this report and `PLAN.md` were written, the required final commands
produced:

```text
focused: 114 passed in 106.97s (0:01:46)
full:    267 passed in 264.66s (0:04:24)
git diff --check: exit 0; no whitespace errors
```

`git diff --check` emitted only the existing LF-to-CRLF working-copy warnings.
Final status contained the intended uncommitted Stage 1 source/tests,
`PLAN.md`, `docs/superpowers/reports/`, and `out/`, plus the untouched dirty
paths listed above. The scoped diff and all five required no-index reviews were
run; the no-index commands displayed each new file and returned the expected
status 1. No incomplete implementation markers or changes to older
architecture, roadmap, README, or comparison documents were found.

## Post-Review Hardening (25 July 2026)

The single allowed final-review hardening wave addressed all four Minor
findings. Duplicate-semantic multiplicity, complete-ledger field selection,
and the publication rollback state matrix were pinned without changing their
production implementations. `_require_stage0_entry` now collects every raw
count and cost issue independently and always rejects malformed metrics with
one aggregate `RuntimeError`.

| Fresh command | Result |
|---|---|
| `python -m pytest tests/test_same_lane_repair.py tests/test_export.py tests/test_optimize.py -q` | `108 passed in 87.96s (0:01:27)` |
| `python -m pytest -q` | `291 passed in 214.99s (0:03:34)` |

The official plan SHA-256 remained
`36B017020597CE85E707430EB741066FF8AF50FAFA798F34204F17FDB243991E`; the
official forecast SHA-256 remained
`10802C3EB5BACC87D58DA8163709400B10FFBAC8D5B1260680CE64219FF409EC`.
`python run.py` was not run and neither official workbook was touched. All
accepted cost, move, pipeline, fingerprint, and publication metrics above are
unchanged.

## Controller Final Verification (25 July 2026)

After the hardening re-review returned `Ready: YES`, the complete suite and
real pipeline were run once more against the final production code:

```text
python -m pytest -q
291 passed in 198.61s (0:03:18)

python run.py
Stage 1 runtime: 76.8 s
Complete pipeline: 90.7 s
Candidate total: 14,680,184.845833339 TL
Violations: 0
```

The regenerated official forecast again printed
`time h:mm 0.000 4046 4046 4977975`. Independent official-plan simulation
returned vehicle cost `12,510,401.245833337 TL`, SLA penalty
`2,169,783.600000002 TL`, total `14,680,184.845833339 TL`, and zero violations;
declared reconciliation passed. The final regenerated SHA-256 values are:

| Official file | SHA-256 |
|---|---|
| `out/Tasima-plani.xlsx` | `2BEECFC7540CE24D4FD92EC6B7CE37862E6E61D310420E2FD815295449EA5BEF` |
| `out/Talep-tahmini.xlsx` | `99883ABACE15B3CF71953E2290A82D1FD4DE101D421D4A7CCA09996EC41CF244` |
