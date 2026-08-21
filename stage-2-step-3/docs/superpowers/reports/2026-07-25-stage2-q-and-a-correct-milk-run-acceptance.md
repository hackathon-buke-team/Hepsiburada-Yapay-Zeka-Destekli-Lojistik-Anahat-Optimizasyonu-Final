# Stage 2 Q&A-Correct Milk-Run Acceptance Report

> Plan: `docs/superpowers/plans/2026-07-25-stage2-q-and-a-correct-milk-run.md`
> Design: `docs/superpowers/specs/2026-07-24-safe-cost-optimization-design.md`
> Branch: `feature/transport-optimizer-milkrun` — all work unstaged and uncommitted.
> Accepted: **26 July 2026**

---

## 1. Scope Note — Pair-Only Extended To Four Stops

The plan scoped Stage 2 as **pair-only** and deferred 3–4 destination chains to an
independently gated "Stage 2b". Two measured, refereed experiments during acceptance
showed the deferral was leaving money on the table, and the project owner approved
each extension before it was implemented:

| Chain cap | Refereed total, TL | Gain |
|---|---:|---:|
| 2 stops (as planned) | 11,837,689.311111117 | — |
| 3 stops | 11,519,240.351388888 | −318,448.959722229 |
| **4 stops (accepted)** | **11,313,338.286111113** | **−205,902.065277775 more** |

### 1.1 The jury permits it, with no numeric cap

Exhaustively searched both official PDFs and `son-gelen-message.txt` (text extracted
with two independent engines, PyMuPDF and pdfplumber, and cross-checked). **No
competition document imposes any cap on how many transfer centres one vehicle may
visit in a single run.** The relevant rulings:

> **Q&A Soru 11.1 — Milk-run kuralı.** *"Bir aracın tek seferde **birden fazla**
> transfer merkezine uğrayıp sırayla yük bırakması mümkün mü? … ilk durakta bir kısım
> yükü indirirken geri kalan yük araçta kalıp **sonraki duraklarda** elleçleniyor…"*
> **Cevap: "Spot araçlar için evet mümkündür fakat kiralık araçlar için uğrama mümkün
> değildir."**

> **Q&A Soru 3 (NEURON-LOG)** — the only place an upper bound is ever asked about:
> *"…toplam sefer sayısı için herhangi bir **üst sınır** bulunmakta mıdır? Yoksa
> yalnızca fiziksel zaman uygunluğu, seyahat süresi ve elleçleme süreleri dikkate
> alınarak teorik olarak **sınırsız** sayıda sefer gerçekleştirebilir mi?"*
> **Cevap: "Evet kısıtlamalar dikkate alınarak sınırsız sefer yapabilirsiniz."**

> **Brief p.4:** *"Kullanacağınız araçlara **birçok farklı** transfer merkezine gidecek
> yükleri yükleyebilirsiniz."*
> **Q&A Soru 9:** *"Spot araçların çoklu bacak (uğrama) yapması **serbest
> bırakılmış**… Yalova'daki elleçleme süresi de aracın kullanım süresine dahildir."*

Supporting lexical evidence: `azami` and `en çok` occur **zero** times; `maksimum`
occurs three times and every one is about handling or Tır **capacity**, never route
length. The prohibition on `uğrama` appears five separate times and is **always**
scoped to `kiralık` vehicles — never to a vehicle *type* and never to a stop count.
One team's own worked three-stop example (`İstanbul-Eskişehir-Ankara`) was put to the
jury, which answered about the return leg and raised no objection to the stop count.

`MAX_CHAIN_STOPS` is therefore **entirely our own** engineering constant, not a rule.

### 1.2 What actually limits chain length

| Candidate limiter | Measurement | Binding? |
|---|---|---|
| Lane connectivity | 18 TMs → 18×17 = 306 ordered pairs; `datas/sehirler_arasi_lojistik.xlsx` holds **306** lanes, 0 missing | **No** — the matrix is complete, every stop order is routable |
| **Vehicle capacity** | Chains use non-Tır Spot types, so ≤ **12,000 desi**; an eligible source averages **4,128 desi** | **Yes — the real limit** |
| Group size | 117 groups; ≥3 sources: 86, ≥4: 81, ≥5: 76 | No |
| SLA | each extra stop delays every downstream drop | Partially — it is traded, not blocked |
| Enumeration cost | see below | **Yes at k = 5** |

Combinations surviving the 12,000-desi capacity filter:

| k | distinct-destination combinations | fit ≤ 12,000 desi | priced variants |
|---|---:|---:|---:|
| 2 | 5,426 | 3,669 (67.6%) | 22,014 |
| 3 | 22,719 | 10,423 (45.9%) | 187,614 |
| **4** | **73,650** | **23,602 (32.0%)** | **1,699,344** |
| 5 | 190,966 | 41,425 (21.7%) | 14,913,000 |

**k = 5 is not viable** with this brute-force enumerator: it was attempted and had
produced no result after ~13.5 minutes of CPU and 1.3 GB RSS. Reaching it would need
pruning (branch-and-bound, capacity-first ordering), which is out of scope here.
There is no runtime limit to respect — `son-gelen-message.txt`: *"Optimizasyon için
bir zaman sınırlaması yoktur."*

`MAX_CHAIN_STOPS = 4` is set in `src/milkrun.py` with this reasoning recorded inline.
The two-stop code path is unchanged and is exercised by the same tests as before.

---

## 2. Accepted Result

| Stage | Vehicle cost, raw TL | SLA penalty, raw TL | **Total, raw TL** | Violations |
|---|---:|---:|---:|---:|
| Stage 0 fixed baseline | 15,460,592.572222233 | 1,020,367.2000000012 | **16,480,959.772222234** | 0 |
| Stage 1 same-lane repair | 12,510,401.245833337 | 2,169,783.600000002 | **14,680,184.845833339** | 0 |
| Stage 2 milk-run (≤4 stops) | 8,752,512.286111115 | 2,560,825.9999999986 | **11,313,338.286111113** | 0 |

- Stage 1 raw saving vs Stage 0: **1,800,774.926388895 TL**
- Stage 2 raw saving vs Stage 1: **3,366,846.559722226 TL**
- **Cumulative Stage 0 → Stage 2: 5,167,621.486111121 TL (−31.35%)**

Stage 2 buys vehicle cost with lateness and nets strongly positive:
−3,757,888.96 TL of vehicle cost against +391,042.40 TL of SLA penalty. The jury sets
no hidden SLA cap, so this is pure total-cost minimisation.

### 2.1 Physical structure

| Metric | Stage 0 | Stage 1 | Stage 2 |
|---|---:|---:|---:|
| Segments (plan legs) | 1,269 | 1,092 | 1,092 |
| **Physical routes (vehicles)** | 1,269 | 1,092 | **693** |
| Rented routes | 126 | 126 | 126 |
| Spot routes | 1,143 | 966 | 567 |
| Plan rows | 3,167 | 3,167 | 5,510 |
| Vehicle mix | HK 24 · K 196 · Kmt 950 · Tır 99 | HK 24 · K 196 · Kmt 773 · Tır 99 | HK 29 · K 306 · Kmt 259 · Tır 99 |
| Unweighted Spot fill | 92,207,719/192,024,000 (48.02%) | 30,735,517/54,096,000 (56.82%) | 3,490,999/4,536,000 (**76.96%**) |
| Spot routes strictly below 30% | 480 | 296 | **46** |

Segments stay at 1,092 while physical vehicles fall to 693: every accepted chain
replaces its *k* source vehicles with **one** physical vehicle carrying *k* segments.
Identity check: `1092 − (626 − 227) = 693`, and `966 − (626 − 227) = 567` Spot routes.

### 2.2 `MilkRunMetrics` — every field, fresh

| Field | Value |
|---|---:|
| `groups_considered` | 93 |
| `pairs_evaluated` | 5,426 |
| `triples_evaluated` (all k ≥ 3 combinations) | 96,369 |
| `chains_accepted` | 227 |
| `chain_size_mix` | (2, **127**), (3, **28**), (4, **72**) |
| `source_vehicles_replaced` | 626 |
| `segments_created` | 626 |
| `parts_consolidated` | 2,110 |
| `desi_consolidated` | 1,675,453 |
| `chain_type_mix` | Hafif Kamyon 11 · Kamyon 120 · Kamyonet 96 |
| `local_saving_tl` | 3,366,846.559722222193718999999 |

Four-stop chains **cannibalise** three-stop ones rather than adding to them
(122 → 28 three-stop, +72 four-stop), which is why `chains_accepted` falls from 249 to
227 while `source_vehicles_replaced` rises from 620 to 626.

Local (per-candidate) and global (referee) saving agree to `3,366,846.5597222…`; the
residual is float→Decimal representation in the referee's aggregate, well inside the
0.01 TL declared-total tolerance.

### 2.3 `RepairMetrics` (Stage 1, unchanged)

| Field | Value |
|---|---:|
| `donors_considered` | 1,003 |
| `moves_accepted` | 177 |
| `parts_moved` | 394 |
| `desi_moved` | 59,852 |
| `spot_legs_removed` | 177 |
| `local_saving_tl` | 1,800,774.926388888876856333333 |

---

## 3. Evidence

### 3.1 Tests

| Command | Result |
|---|---|
| `python -m pytest -q` (session entry, before Task 8) | 13 failed, 432 passed — Task 8 incomplete |
| `python -m pytest -q` (after Task 8) | 447 passed, 154.60 s |
| `python -m pytest -q` (after 3-stop Stage 2b) | 454 passed, 127.73 s |
| `python -m pytest -q` (after the Stage 2 frozen-result gate) | 471 passed, 121.86 s |
| `python -m pytest tests/test_optimize.py -q` (after k = 4) | 59 passed, 27.91 s |
| **`python -m pytest -q` (final, k = 4)** | **471 passed, 204.56 s (0:03:24)** |

The accepted suite count (471) exceeds the 291-test entry contract required by the
plan's Completion Definition. The runtime rise is the real-horizon milk-run test now
enumerating four-stop combinations.

### 3.2 Real staged pipeline — `python run.py`

Total runtime **110.0 s** (milk-run pass ≈ 72 s of it). Printed gates, in order:

```
forecast fingerprint unchanged · 4,046 IDs · 4,977,975 desi
Stage 0 exact reproduction (1,269 legs, 16,480,959.772222234 TL, 0 violations)
Stage 1 exact entry gate at 14,680,184.845833339 TL
Stage 2 accepted, raw saving 3,366,846.559722226 TL >= 1.00 TL
Stage 2 exact result gate: all 20 STAGE2_* constants reproduced
physical metrics + every MilkRunMetrics field for Stage 0/1/2
Stage1-baseline.xlsx written and verified
Tasima-plani.xlsx written and verified, raw artifact saving >= 1.00 TL
plan published first, then forecast
completion printed only after publication returned
```

The frozen-result gate proved itself on this change: with `MAX_CHAIN_STOPS` raised to
4 but the constants still pinned to the 3-stop run, `run.py` **refused to publish** and
printed a 17-line diff of every drifted value. The constants were then updated from
that diff and re-verified against a fresh run.

### 3.3 Official workbook schema and forecast fingerprint

`official schema/forecast: PASS 5510` — verified:

- `Talep-tahmini.xlsx`: 4,046 rows, 4,046 unique `Talep ID`, desi sum **4,977,975**,
  `forecast_fingerprint` equal to an independently rebuilt forecast,
  `validate_forecast_grid` empty, `C2` a real Excel `time` cell with `h:mm`,
  `F2` number format `0.000`.
- `Tasima-plani.xlsx`: **5,510 rows**, columns exactly `PLAN_COLS`, `validate_plan`
  empty, **693** unique `Araç ID`, 126 rented vehicles over 216 rows, 35 empty-rented
  rows with blank `Talep ID`, declared `Toplam maliyet` sum
  **11,313,338.286111113 TL**.

**Template fidelity fix.** The official template `datas/TAŞIMA PLANI.xlsx` formats
`Taşınan Desi` (column K) as `0.000`; our writer emitted `General`. `src/export.py`
now applies `_format_plan_workbook` on write, mirroring the forecast writer. Verified
on the published file: `K2 … K5511` all `0.000`. Covered by
`test_write_plan_xlsx_matches_template_desi_number_format`.

### 3.4 Independent reconstruction — `declaration/inventory/artifact: PASS`

Rebuilt Stage 0/1/2 from source in a separate process and re-refereed the published
workbooks. Verified:

- source legs and the in-memory forecast frame are **unmutated** by any stage;
- `forecast_fingerprint(memory) == forecast_fingerprint(artifact)`;
- `plan_fingerprint(artifact) == plan_fingerprint(stage2.selected.plan_frame)`;
- independent `simulate()` on the published workbook: **0 violations**,
  total 11,313,338.286111113 TL, `require_plan_total` reconciles;
- `verify_plan_artifact` passes with 0 violations;
- **chain topology:** 227 chains, every `chain_seq` contiguous from 0, every
  consecutive `dest == origin`, no repeated destination inside a route, one `kind` and
  one `vtype` per route, every chain Spot and never Tır, `2 ≤ len ≤ 4`, and at least
  one route longer than two;
- **rented fleet:** 126 rented physical routes preserved exactly;
- **inventory:** the baseline part/desi multiset equals the delivered multiset; every
  Part is loaded exactly once and finally unloaded exactly once at its own
  destination; loaded-set and delivered-set are identical;
- **final delivery date:** Stage 2 last cargo unload `2026-07-06` ≤ Stage 1 last cargo
  unload `2026-07-06` — longer chains never push delivery later;
- **referee is live:** adding one minute to a single `Yolculuk süresi` cell makes
  `simulate()` raise a travel-duration violation.

### 3.4b Determinism of the k-stop pass

`milk_run_improve` was run three times on the accepted Stage 1 legs: twice on an
identical deep copy, and once on the same legs **shuffled** with a fixed seed. All
three produced byte-identical plans and identical `MilkRunMetrics`:

```
run A == run B          : True
run A == shuffled run C : True
metrics A == B == C     : True
chains 227, size mix (2, 127) (3, 28) (4, 72),
local saving 3,366,846.559722222193718999999
```

Input order cannot change the submission — the ranking key
`(delta_tl, len(source_tokens), (origin, load_start) + destinations, vehicle-type
index, sorted source leg keys)` is a total order over candidates.

### 3.4c Direct check of the published workbook's chain topology

Read back from `out/Tasima-plani.xlsx` alone, grouping rows by `Araç ID`:

```
vehicles by leg count: {1: 466, 2: 127, 3: 28, 4: 72}   (total 693)
multi-stop vehicles  : 227
topology failures    : 0
```

Zero failures across: every multi-stop vehicle is `Spot` and never `Kiralık`, one
vehicle type per physical route, no `Tır` chain, each leg's destination equals the
next leg's origin, no repeated destination, and no return to the origin transfer
centre.

### 3.5 Official artifact hashes

| File | SHA-256 |
|---|---|
| Pre-acceptance `out/Tasima-plani.xlsx` | `2beecfc7540ce24d4fd92ec6b7ce37862e6e61d310420e2fd815295449ea5bef` |
| Pre-acceptance `out/Talep-tahmini.xlsx` | `99883abace15b3cf71953e2290a82d1fd4de101d421d4a7cca09996ec41cf244` |
| **Accepted `out/Tasima-plani.xlsx`** | `d452ab27074210611122577ea49a8292b7d1f496ba28941c5fb4c3a863393eeb` |
| **Accepted `out/Talep-tahmini.xlsx`** | `363a4e6a3b8597dede40302c1f2ff302c484a8718f96a3367928e3c9e8c783c3` |

XLSX packages embed write timestamps, so repeated runs of the same accepted plan
produce different SHA-256 values while the fingerprint tuples stay identical. That is
precisely why the gates are fingerprint equality and independent re-simulation, not
package hashes.

---

## 4. Task 8 — Pipeline Integration

`run.py` entered the session with the Stage 1/Stage 2 gates half-migrated and 13 red
tests. Completed work:

- `_require_stage1_entry` now checks **segment count** and **physical route count**
  independently, and rejects chained Stage 1 topology on two independent signals:
  `len(routes) != len(legs)` and any non-`None` `chain_id`. It also verifies
  `baseline.total − selected.total` against `STAGE1_GLOBAL_SAVING` *and* the
  decision's own reported `saving_tl`. Non-finite Decimals are collected as named
  mismatches rather than raising.
- `_require_stage2_entry` additionally requires
  `saving_tl == improvement_tl(baseline, candidate)` — a decision object that under-
  or over-states its own saving is rejected before anything is written.
- `_stage_and_publish` re-runs **both** entry gates, raises `Stage 2 reddedildi`
  before any artifact write when Stage 2 is not accepted, and verifies exactly two
  artifacts — `Stage1-baseline.xlsx` then `Tasima-plani.xlsx` — reusing the baseline
  referee result instead of re-verifying it.
- `_print_decision_metrics` → `_print_pipeline_metrics`, printing Stage 0/1/2 physical
  metrics plus both stage ledgers and the cumulative saving.
- `_use_utf8_console()` reconfigures stdout/stderr to UTF-8. Without it,
  `python run.py > log.txt` on a cp1252 console crashed **after** all gates passed but
  **before** publication.
- Staging directory prefix `.stage1-` → `.stage2-`.

Test changes: legacy Stage-0-baseline seam tests were replaced by their Stage-1/2
equivalents, including the parametrized
`test_stage1_or_stage2_rejection_preserves_both_official_files` and
`test_main_never_prints_completion_after_stage2_or_publication_exception`, plus a new
`test_stage2_entry_requires_reported_saving_to_match_referee`.

---

## 4b. Stage 2 Frozen-Result Gate (`_require_stage2_result`)

An adversarial audit of the published multi-stop submission raised eight claims. Seven
were refuted on independent reproduction — six of them variants of one misreading: the
idea that the per-row `Çıkış/Varış elleçleme süresi` columns should be **summed** to
obtain a leg's handling duration. The official brief forbids exactly that:

> *"bir araç içerisinde taşınan tüm gönderiler için elleçleme işleminin aynı anda
> başladığı ve aynı anda tamamlandığı varsayılır. Yarışmacılar aynı araç içerisindeki
> desiyi bölerek bir kısmını daha erken elleçlenmiş kabul edemezler."*

Handling is one **aggregate** operation per vehicle-stop, `⌈Σdesi × 0.01⌉`, which is
what both the scheduler and the referee use; the per-row column is the jury-mandated
desi-proportional *declaration* of that single operation, not an additive timeline.

**One claim survived refutation and was fixed.** Stage 0 and Stage 1 were pinned to
their accepted results by exact constants, but Stage 2 — the stage that produces the
submitted workbook — had no frozen value at all. Its gate checked only baseline
identity, acceptance, selection, zero violations, saving identity and `≥ 1.00 TL`. A
future change to the milk-run search that silently lost most of the gain would still
pass every gate, every test, and publish.

`run.py` now defines 20 `STAGE2_*` constants and enforces them in
`_require_stage2_result(stage1, stage2, data)`, called from `main()` immediately after
`_require_stage2_entry`. It collects, rather than short-circuits, mismatches across:
segments, physical routes, plan rows, rented/Spot routes, chain-route count, raw
vehicle/SLA/total cost, the recomputed global saving against Stage 1, and every
`MilkRunMetrics` field including `chain_size_mix` and `chain_type_mix`. It also pins
the **shape** of every chain: `2 ≤ len ≤ MAX_CHAIN_STOPS`, Spot-only, never Tır, one
vehicle type per route — the Q&A 11.1 constraint expressed as a runtime gate rather
than a comment.

Ten tests cover it, including `test_stage2_result_rejects_a_collapsed_milk_run`
(chains lost → four named mismatches), a rented/Tır chain, an over-length chain, a
mixed-vehicle-type chain, per-field cost drift at `1E-9`, and per-field metric drift.
The fixture derives from `run.STAGE2_*` on purpose: its job is to prove the **gate
logic** rejects drift, while the **constants themselves** are verified by the real
`python run.py` and the independent reconstruction script. That separation is what let
the k = 4 change be made safely.

Two audit observations were noted without change: `segments_created` and
`source_vehicles_replaced` are equal by construction in this chain model (each chain
of *k* sources creates *k* segments), and `triples_evaluated` counts all combinations
of size ≥ 3 — the console label reads `Çoklu deneme (k>=3)` to avoid implying "three".

---

## 5. k-Stop Generalisation

`src/milkrun.py`:

- `_build_chain_candidates(tokens, sources, data)` is the single pricing engine for any
  chain length. `_build_pair_candidates` is now a thin two-stop wrapper over it, which
  is why every pre-existing pair test — including the monkeypatched builder tests —
  passes unchanged.
- Economics are identical at every length: one continuous vehicle usage window from
  the joint load start to the final unload end, the **actual** inter-stop lane
  distances summed, no intermediate handling for cargo that stays onboard, and
  final-only SLA charged per destination at its own drop time. Vehicle cost is attached
  to segment 0 only, so a physical route is charged exactly once.
- Stop orders are enumerated over all permutations; an order whose inter-stop lane does
  not exist is skipped, never invented. (On this instance the lane matrix is complete,
  so no order is ever skipped for that reason.)
- `milk_run_improve` enumerates size-2 combinations and every size from 3 to
  `MAX_CHAIN_STOPS` per `(origin, load_start)` group, then runs the same deterministic
  greedy set-packing with the same complete-ledger trial validation
  (`_trial_candidate_valid`) and the same Stage 1 final-delivery-date guard.
- The ranking key gained `len(source_tokens)` after `delta_tl`; for pair-only inputs
  every candidate has length 2, so existing ranking tests are unaffected.
- `MilkRunMetrics` gained `triples_evaluated` and `chain_size_mix` (both defaulted, so
  existing constructions stay valid). `source_vehicles_replaced` and `segments_created`
  are Σ*k* over accepted chains.

`src/chain.py` and `src/schedule.py` required **no change** — they were already
chain-length-generic, which the 4-segment plan validating and exporting confirms.

Tests in `tests/test_milkrun.py`: multi-stop builder topology, an independent Decimal
recomputation of a three-stop chain's timing/cost/SLA, capacity and
duplicate-destination rejection, end-to-end acceptance through `milk_run_improve`,
`MAX_CHAIN_STOPS` bounding the enumeration, and multi-stop load/carry/unload flows. The
real-horizon test was generalised from pair-only arithmetic and renamed
`test_full_horizon_chain_stage_accepts_stage1_baseline`.

---

## 6. Directional Pre-Implementation Pair Evidence

The following values were recorded **before** implementation as directional exploration
only:

- `277` candidate pairs
- `554` source vehicles
- `11,993,748.820833342 TL`
- `2,686,436.024999997 TL`

**None of these is an exact acceptance assertion.** They are not gates, are not
reproduced by the accepted pipeline, and must not be cited as expected values.

Also non-gating, and superseded: the intermediate pair-only result
**11,837,689.311111117 TL** (308 two-stop chains) and the three-stop result
**11,519,240.351388888 TL** (127 two-stop + 122 three-stop chains). The accepted Stage 2
figures are those in §2.

---

## 7. Deferred, Non-Gating Work

- **Five-stop chains.** Not viable with the current brute-force enumerator (no result
  after ~13.5 min CPU / 1.3 GB RSS). Would need pruning; **not implemented, not
  measured as a saving, and not gated**.
- **Tır in chains.** The audit established there is no documentary basis for excluding
  Tır — the `uğrama` prohibition is scoped to `kiralık` vehicles only, never to a
  vehicle type. Including Tır would double the chain capacity ceiling to 22,400 desi.
  It is excluded here as a deliberate, documented conservatism: Tır capacity is a
  scarce hard constraint (0 at seven transfer centres, 1 at Balıkesir, 2 at Tekirdağ)
  and each chain stop consumes a visit. **Unmeasured; would need its own gate.**
- **Mid-route pickup.** Q&A Soru 4.4 explicitly contemplates a vehicle that drops
  cargo and then picks cargo up at an intermediate stop. Our chains only drop.
  Unexploited degree of freedom, unmeasured.
- **Exact max-weight matching** instead of greedy set-packing — measured at
  47,795.99 TL on the pair-only candidate set; an *alternative* to the multi-stop pass,
  not additive, and already exceeded by it.
- **Low-fill Spot consolidation.** Measured dead end: the remaining sub-30% Spot routes
  are the only vehicle on their lane that day, so same-lane merging recovers 0 TL.
- **Forecast month-end bias** (+28.3% on the 30 Mar–5 Apr backtest window) remains the
  top forecast-side improvement target and is untouched by this change.

---

## 8. Git State

- All Stage 1 and Stage 2 work remains **dirty, unstaged and uncommitted**.
- No `stage`, `commit`, `clean`, `revert`, `reset`, `checkout`, `restore` or `discard`
  command was run at any point.
- `git diff --cached --name-only` is empty; nothing from this plan is staged.
- `git diff --check` exits 0 (LF/CRLF notices are informational only).
- Intended modified files: `run.py`, `src/milkrun.py`, `src/export.py`,
  `tests/test_optimize.py`, `tests/test_milkrun.py`, `tests/test_export.py`, `PLAN.md`,
  plus the regenerated `out/` workbooks and this report.
- Pre-existing unrelated dirty paths preserved untouched: `src/optimize.py`,
  `src/schedule.py`, `src/schemas.py`, `src/simulator.py`, `tests/test_schemas.py`,
  `tests/test_simulator_cost.py`, `tests/test_simulator_full.py`, `.claude/`,
  `ARCHITECTURE.md`, `ROADMAP.md`, `docs/comparison/`, and the untracked plan/spec
  documents.
- Older architecture, roadmap, comparison, spec and prior report documents were **not
  modified**.
