# 📋 Project Plan & Current Status — Hepsiburada Stage-2 (Advanced Solution)

> **Teknofest 2026 · AI-Assisted Logistics Line-Haul Optimization — Stage 2**
> Branch: `feature/stage2-milkrun-ve-gorsel-readme` · Last updated: **26 Jul 2026**
> This is the master hand-off document: problem, architecture, **verified
> results**, jury Q&A compliance, and the remaining work plan. Detailed
> technical reference: `ARCHITECTURE.md`; short status view: `ROADMAP.md`.

---

## 1. Problem in One Paragraph

Produce **two coupled deliverables** for the horizon **29 Jun 09:00 → 05 Jul 17:00**:

1. **Demand forecast** (`Talep-tahmini.xlsx`) — `desi` per origin→destination (OD)
   pair × slot (09:00 / 17:00) × day (full grid, ~4046 rows). Scored against
   real actuals via **WMAPE**.
2. **Transport plan** (`Tasima-plani.xlsx`) — minute-resolution vehicle routing
   that moves **our own forecast** at minimum **total cost**:
   `Total = Vehicle Cost + SLA Penalty`, where
   `Vehicle = hourly_rate × usage_hours + km × per_km_rate` and
   `SLA = late_desi × ⌈late_hours⌉ × 0.40 TL`.

**Any format deviation = disqualification** → the format validators
(`src/schemas.py`) and the referee simulator (`src/simulator.py`) are hard gates.

---

## 2. Architecture (as built)

```
datas/*.xlsx
   │
   ▼
src/data.py        Validated Excel loaders → CompetitionData            ✅
   ▼
src/forecast.py    DOW-median base (k=4, holidays/month-ends excluded)  ✅
   │               × leakage-free calendar multipliers
   ▼
src/optimize.py    Daily orchestration:                                 ✅
   │               rented fill → tır-visit budget allocation →
   │               spot vehicle-mix enumeration (with carry-over) →
   │               flush days (rented + spot, Q&A-compliant)
   │               (candidates.py: simulator-exact cost model per mix)
   ▼
src/schedule.py    Minute scheduler: V/D-ID assignment, midnight        ✅
   │               handling-overflow fixes, Q&A-exact declared columns
   ▼
src/simulator.py   REFEREE — independent recompute of cost + 17 rules   ✅
    ▼
src/evaluation.py  Copy-owned schedule/referee, exact metrics,          ✅
   │               fingerprints, acceptance + artifact re-simulation
   ▼
src/repair.py      Deterministic same-lane whole/direct repair with     ✅
   │               complete-ledger trials + global acceptance
   ▼
src/chain.py       Neutral physical routes + per-leg cargo flows,       ✅
   │               chain-length generic (1..k segments per vehicle)
   ▼
src/milkrun.py     Deterministic k-stop milk-run (MAX_CHAIN_STOPS = 4), ✅
   │               exact Decimal economics, complete-ledger trials,
   │               global Stage 2 decision + physical metrics
   ▼
src/pickup.py      Deterministic Tier A mid-route pickup (Stage 3):     ✅
   │               a chain takes cargo ON at a stop it already visits,
   │               milkrun-identical economics, accumulating ledger guard
   ▼
src/export.py      Template-exact writers, round-trip validation,       ✅
                   rollback-safe plan-first publication

run.py             Staged/refereed/published end-to-end (104.7 s)       ✅
src/backtest.py / frozen_backtest.py   Forecast backtest infra          ✅
tests/             **528 tests passing** (258.81 s / 0:04:18)           ✅
```

---

## 3. Verified Results (26 Jul 2026 — latest run)

> Full evidence: `docs/superpowers/reports/2026-07-25-stage2-q-and-a-correct-milk-run-acceptance.md`

### 3.0 Headline

| | Raw total, TL | vs Stage 0 |
|---|---:|---:|
| Stage 0 fixed baseline | 16,480,959.772222234 | — |
| Stage 1 same-lane repair | 14,680,184.845833339 | −1,800,774.93 |
| Stage 2 milk-run (≤4 stops) | 11,313,338.286111113 | −5,167,621.49 (−31.35%) |
| **Stage 3 mid-route pickup (Tier A)** | **11,232,476.731944447** | **−5,248,483.04 (−31.84%)** |

Zero referee violations at every stage.

### 3.1 End-to-end pipeline (`python run.py`)

| Gate | Fresh output | Time |
|---|---|---|
| Forecast staging | 4,046 rows · 4,046 IDs · **4,977,975 desi** · unchanged fingerprint | included below |
| Fixed Stage 0 | **1,269 legs** (126 rented + 1,143 Spot) · 3,167 rows · 0 violations | included below |
| Same-lane repair | 177 moves · 177 Spot legs removed · candidate accepted | included below |
| Milk-run (≤4 stops) | 227 chains (127×2-stop, 28×3-stop, 72×4-stop) · 626 source vehicles replaced · 0 violations | included below |
| Mid-route pickup (Tier A) | 227 target routes × 340 donors = 135,660 pairs · 56 profitable · **28 accepted** · 0 violations | included below |
| Artifact/publication | Stage2-baseline then Tasima-plani, both verified · fingerprints equal · plan published first | included below |
| Complete pipeline | `out/Tasima-plani.xlsx`, then `out/Talep-tahmini.xlsx` published | **104.7 s** |

Fresh evidence: the complete suite passed **528 tests in 258.81 s (0:04:18)**. Both
staged artifacts passed schema, row-level fingerprint, declared-total, raw-saving,
and independent referee gates before publication.

### 3.2 Fixed Stage 0 cost (referee simulator — the only score that matters)

| Component | Amount (TL) |
|---|---|
| Vehicle cost | 15,460,592.57 |
| SLA penalty | 1,020,367.20 (6.2% — deliberate, jury-endorsed) |
| **TOTAL** | **16,480,959.77** |

The declared `Toplam maliyet` column reconciles with the simulator within the
strict `0.01 TL` Decimal tolerance.
The +84.4k TL vs the previous run is the Q&A compliance cost: 2 extra days
(6–7 Jul) × ~42.2k TL/day mandatory rented fleet (same for every competitor).

### 3.3 Accepted Stage 1 same-lane repair

| Metric | Stage 0 baseline | Stage 1 candidate |
|---|---:|---:|
| Legs | 1,269 | 1,092 |
| Plan rows | 3,167 | 3,167 |
| Rented / Spot | 126 / 1,143 | 126 / 966 |
| Vehicle cost, raw TL | 15,460,592.572222233 | 12,510,401.245833337 |
| SLA penalty, raw TL | 1,020,367.2000000012 | 2,169,783.600000002 |
| **Total, raw TL** | **16,480,959.772222234** | **14,680,184.845833339** |
| Sorted mix | HK 24 · K 196 · Kmt 950 · Tır 99 | HK 24 · K 196 · Kmt 773 · Tır 99 |
| Unweighted Spot fill | 92,207,719/192,024,000 (48.02%) | 30,735,517/54,096,000 (56.82%) |
| Spot strictly below 30% | 480 | 296 |
| Violations | 0 | 0 |

The accepted raw saving is **1,800,774.926388895 TL**. The repair considered
1,003 donors and accepted 177 whole/direct moves: 394 parts and 59,852 desi
moved, 177 Spot legs removed, and exact local savings of
`1,800,774.926388888876856333333 TL`. The candidate retains all 126 rented
legs and all demand inventory.

### 3.3b Accepted Stage 2 milk-run (≤4 stops)

| Metric | Stage 1 baseline | Stage 2 candidate |
|---|---:|---:|
| Segments (plan legs) | 1,092 | 1,092 |
| **Physical routes (vehicles)** | 1,092 | **693** |
| Plan rows | 3,167 | 5,510 |
| Rented / Spot routes | 126 / 966 | 126 / 567 |
| Vehicle cost, raw TL | 12,510,401.245833337 | 8,752,512.286111115 |
| SLA penalty, raw TL | 2,169,783.600000002 | 2,560,825.9999999986 |
| **Total, raw TL** | **14,680,184.845833339** | **11,313,338.286111113** |
| Sorted mix | HK 24 · K 196 · Kmt 773 · Tır 99 | HK 29 · K 306 · Kmt 259 · Tır 99 |
| Unweighted Spot fill | 30,735,517/54,096,000 (56.82%) | 3,490,999/4,536,000 (**76.96%**) |
| Spot strictly below 30% | 296 | **46** |
| Violations | 0 | 0 |

Accepted raw saving **3,366,846.559722226 TL**. The pass considered 93 groups,
evaluated 5,426 pairs and 96,369 k≥3 combinations, and accepted **227 chains — 127
two-stop, 28 three-stop and 72 four-stop** — replacing 626 source vehicles with 626
chained segments, consolidating 2,110 parts and 1,675,453 desi, with exact local
savings of `3,366,846.559722222193718999999 TL`. All 126 rented legs and the full
demand inventory are retained, and the final cargo delivery date does not move
(`2026-07-06` in both plans).

**Jury basis for multi-stop (Q&A Soru 11.1):** *"Bir aracın tek seferde **birden
fazla** transfer merkezine uğrayıp sırayla yük bırakması mümkün mü? … **Cevap: Spot
araçlar için evet mümkündür fakat kiralık araçlar için uğrama mümkün değildir.**"*
**Soru 3** answers the only upper-bound question ever asked: *"…toplam sefer sayısı
için herhangi bir üst sınır bulunmakta mıdır?"* → *"Evet kısıtlamalar dikkate alınarak
**sınırsız** sefer yapabilirsiniz."* Soru 9 and Soru 12 confirm intermediate handling
and waiting time count toward vehicle usage — which is how a chain is priced (one
continuous usage window).

**No document caps the stop count**, so `MAX_CHAIN_STOPS = 4` is our own engineering
constant, not a rule. The real limit is capacity: chains use non-Tır Spot types
(≤ 12,000 desi) while an eligible source averages 4,128 desi, so only 32% of 4-source
combinations fit. The lane matrix is complete (306 = 18×17), so connectivity never
binds. Chains are Spot-only and never Tır — a documented conservatism, not a rule,
because Tır capacity is 0 at seven transfer centres.

Official acceptance gates passed with exact column order and empty schema error
lists. The official forecast fingerprint equals the independently rebuilt
4,046-row forecast fingerprint; the official plan fingerprint equals the
independently reconstructed selected-candidate fingerprint. Artifact
reload/re-simulation reproduces raw total `11,313,338.286111113 TL` with zero
violations, and the declared `Toplam maliyet` sum matches it. Publication is
rollback-safe and replaces the plan before the forecast.

**Stage 2 is now pinned like Stage 0/1.** `run.py::_require_stage2_result` enforces
20 exact `STAGE2_*` constants — costs, counts, every `MilkRunMetrics` field, and the
chain *shape* (`2 ≤ len ≤ MAX_CHAIN_STOPS`, Spot-only, never Tır, one vehicle type per
route). A search change that silently lost the milk-run gain used to pass every gate
and publish; it now fails loudly.

**Determinism.** `milk_run_improve` was run twice on identical input and once on the
same legs shuffled with a fixed seed: byte-identical plans and identical metrics all
three times. The submission cannot change with input order.

### 3.3c Accepted Stage 3 mid-route pickup (Tier A)

| Metric | Stage 2 baseline | Stage 3 candidate |
|---|---:|---:|
| Segments (plan legs) | 1,092 | **1,064** |
| **Physical routes (vehicles)** | 693 | **665** |
| Plan rows | 5,510 | 5,523 |
| Rented / Spot routes | 126 / 567 | 126 / 539 |
| Chain routes (multi-stop) | 227 | **227 — unchanged** |
| Vehicle cost, raw TL | 8,752,512.286111115 | 8,616,944.731944447 |
| SLA penalty, raw TL | 2,560,825.9999999986 | 2,615,531.9999999995 |
| **Total, raw TL** | **11,313,338.286111113** | **11,232,476.731944447** |
| Sorted mix | HK 29 · K 306 · Kmt 259 · Tır 99 | HK 29 · K 304 · Kmt 233 · Tır 99 |
| Unweighted Spot fill | 3,490,999/4,536,000 (76.96%) | (**79.03%**) |
| Spot strictly below 30% | 46 | **30** |
| Violations | 0 | 0 |

Accepted raw saving **80,861.554166666 TL**. The pass skipped 126 rented routes,
considered 227 multi-stop Spot targets against 340 single-leg Spot donors, examined
**135,660 (route-stop, donor) pairs**, priced **56 profitable candidates** and
accepted **28 non-overlapping pickups** — removing 28 whole vehicles and moving 82
parts / 65,754 desi, with exact local savings of
`80,861.55416666666605766666666 TL`. Zero candidates were rejected by the ledger
guard. All 126 rented legs and the full demand inventory are retained, and the final
cargo delivery date does not move (`2026-07-06` in both plans).

**Jury basis (Q&A Soru 6):** *"…Aynı şekilde bir araçtan **x kadar yük indirilip y
kadar yük yüklenirse** kapasiteden x+y kadar yük düşülür."* That sentence describes
one vehicle unloading *and* loading at one centre and supplies the handling
arithmetic. The only prohibition is on rented vehicles (*"Kiralık araçlarla uğrama
yapılmaz"*), which is why a rented route can never be a pickup target — and why
`_route_total_tl` refuses to price one at all, since rented cost uses rental tariffs.

**Tier A only.** The picked-up cargo's destination must be a stop the route *already*
visits, so the route topology never changes: 227 chains before, 227 chains after, none
longer than `MAX_CHAIN_STOPS`. Tier B (extending a route by one stop, producing
5-stop routes) is explicitly **out of scope** — it would change `MAX_CHAIN_STOPS` and
the K1 documentation, so it is a separate decision.

**Two timestamps at a pickup stop.** Conflating them is a silent error:

```python
unload_end   = arr + handling(drop desi)      # the SLA stamp
depart_after = unload_end + handling(pickup)  # the next segment's departure
```

Cargo dropped there is delivered the moment its unloading ends; the loading that
follows delays the *vehicle*, not the *delivery*. Symmetrically, picked-up cargo rides
only `pickup_at < i ≤ drop_at`; letting it ride past its own stop would corrupt both
SLA and capacity. Both are pinned by dedicated regression tests.

A side effect worth recording: an unload-then-load stop consumes **one** `TirLedger`
visit, not two — the referee writes leg *i*'s arrival and leg *i+1*'s departure under
the same `visit_id`.

**Stage 3 is pinned like Stage 0/1/2.** `run.py::_require_stage3_result` enforces 23
exact `STAGE3_*` constants — costs, counts, every `PickupMetrics` field, and the
*shape of the pickup itself*: mid-route loading only on Spot routes, and every piece
of cargo dropped at its own forecast destination. `_require_stage3_entry` additionally
requires identity, zero violations, a saving of **≥ 50,000 TL** (1.00 TL would still
pass if the search collapsed to one accidental pickup), and — most importantly — that
the search's own analytic saving reconciles with the referee's measured difference to
within `0.000001 TL`.

**That reconciliation gate is what found every defect.** The prototype had three, and
nothing else noticed any of them: targeting rented routes (a rule violation priced at
the wrong tariff), taking the SLA stamp after the loading (over-declared by
5,108.80 TL), and letting picked-up cargo ride past its destination (274.00 TL). A
fourth was found while writing the production code: the prototype derived the "what is
dropped here" set from the *pre-pickup* item lists, so cargo merely passing through an
intermediate stop was counted as unloaded there. That one was self-consistent — the
referee still reported zero violations — but it inflated handling time and pushed every
later segment later. Fixing it is why the production result beats the prototype's
measured 79,975.04 TL by **886.52 TL**.

**Determinism.** `pickup_improve` was run on identical input and on the same legs
shuffled with fixed seeds: identical plans and identical metrics every time. The
ranking key is semantic — `(delta_tl, route leg keys, pickup_at, donor leg key)` — with
index tiebreakers that are themselves derived from a semantic sort, so no object
identity or input order can reach the submission.

### 3.4 Forecast profile (calendar layer working as designed)

| Day | Desi | Note |
|---|---|---|
| 29 Jun (Mon) | 1,161,736 | peak Monday |
| 30 Jun (Tue) | **24,040** | month-end collapse ×0.02 |
| 01 Jul (Wed) | 1,305,721 | rebound ×1.21 |
| 02 Jul | 978,038 | |
| 03 Jul | 859,444 | |
| 04 Jul (Sat) | 591,542 | |
| 05 Jul (Sun) | 57,454 | |

Calibrated multipliers (leakage-free, from history): day-before-month-end
**0.675**, month-end **0.020**, first-day-after **1.207**, normal 1.0.

### 3.5 Forecast quality (frozen single-shot backtests, real data)

| Window | Model (DOW × calendar) | DOW-only base |
|---|---|---|
| Normal week (15–21 Jun) | WMAPE **0.2174**, bias −7.0% | identical (no calendar days inside) |
| Month-end week (30 Mar–5 Apr) | WMAPE **0.4464**, bias +28.3% | WMAPE 0.5328, bias +36.9% |

Rolling-origin baselines (documented): naive 0.2965, DOW-median 0.2275.
The calendar layer clearly helps on month-end windows; **bias on month-end
weeks is the top forecast-improvement target**.

### 3.6 Stage 0 plan structure

- **Rented fleet:** 14 vehicles/day × **9 days** (29 Jun – 7 Jul) = 126 legs;
  empty legs written with blank `Talep ID`, desi 0 (28 such rows on 6–7 Jul).
- **Spot mix:** Kamyonet 950, Kamyon 160, Hafif Kamyon 24, Tır 9 vehicles.
- 83 plan rows arrive **6 Jul** (spill — allowed and expected).
- 11 handling-capacity overflows (Denizli, 2 Jul) fixed by post-midnight shifts.

---

## 4. Jury Q&A Compliance — full checklist (verified 24 Jul 2026)

Source: `soru-cevap-full.docx` (complete jury Q&A) + template files.

### 4.1 ✅ Compliant (16 items)

| # | Jury rule | Where enforced |
|---|---|---|
| 1 | Empty spot returns are never written | optimizer never emits return legs |
| 2 | No rented returns | simulator rule 12 (own-route only) |
| 3 | Forecast horizon 29 Jun 09:00 → 5 Jul 17:00; optimize own forecast; spill allowed | `run.py` horizon; flush days |
| 4 | Durations round **UP** to whole minutes (0.92 h = 55.2 → **56 min**) | `timeutil._ceil_guarded` + PDF tests |
| 5 | Midnight **proportional** handling split (23:30 10,000 desi/100 min → 3,000/7,000) | `HandlingLedger` + PDF tests |
| 6 | Milk-run: cargo handled **only** where loaded/unloaded (stay-onboard not handled) | simulator `stay`/`new_desi` logic; milkrun cost model |
| 7 | No 10 % min-fill rule for spot (removed this stage) | not enforced anywhere |
| 8 | Transfers: same `Talep ID` on consecutive legs, **no** `-1` suffix; desi not double-counted | simulator `base_demand_id` + desi-conservation checks |
| 9 | `Yolculuk süresi` needs **no** proportional split | full leg travel written on every row |
| 10 | Kocaeli never a destination (intended) | data layer + grid |
| 11 | Empty rented legs written (blank `Talep ID`, desi 0) | 28 rows in output; validators allow |
| 12 | Tır capacity = total daily visits; stationary reload = 1, leave+return = 2 | `TirLedger` (vehicle, visit) set semantics |
| 13 | No hidden SLA cap — pure total-cost minimization | deliberate penalty buying (6.2% of cost) |
| 14 | One `Araç ID` = one physical vehicle, consistent type | 0 mixed-type IDs; simulator rule 5 |
| 15 | Dynamic fill limits allowed | informational, unused |
| 16 | **Tır-capacity semantics confirmed by jury Q&A** (was open question #4) — our conservative reading (inbound+outbound pooled, rented Tırs count) is correct | closes `ARCHITECTURE.md` §12 Q4 |

### 4.2 🔧 Fixed on 24 Jul 2026 (2 items — were non-compliant)

**Fix A — Rented fleet on spill days (6–7 Jul).** Jury (3 consistent answers):
rented vehicles must be planned **until distribution ends**, even empty, cost
included; spilled cargo should ride rented first, spot as needed.
*Was:* flush days were spot-only; the simulator's default `rental_days` covered
forecast days only (blind spot). *Now:*
- `optimize.py` — flush days run `_fill_rented` + `_flush_day`: full rented
  fleet departs every day through 7 Jul (empty if no cargo); carried cargo
  rides rented trunks first.
- Flush-day departure policy: **non-Tır rentals leave early** (00:00 + full-load
  handling → less SLA); **Tır rentals keep the 17:00 policy** — an early Tır
  departure would land its arrival on the same day as the previous evening's
  post-midnight arrival and double-book the scarce tır budget (Balıkesir 1,
  Tekirdağ 2). Seed reservations use the exact same policy per route.
- `simulator.py` — default `rental_days` now extends through the **last cargo
  delivery day** (unload-end), so the referee itself catches a missing
  spill-day rental. Explicit `rental_days=[]` still disables the check.
- Tests: flush-day fleet size, per-type departure policy, end-to-end 0-violation
  scenario with forced spill, simulator spill-day coverage.

**Fix B — Per-row declared handling durations.** Jury: "cost and duration are
distributed by desi share" (D001 40 % / D002 60 %), each row rounded up;
travel duration needs **no** distribution.
*Was:* full leg handling minutes written on every item row (e.g. 224 min on
both D00541/1,476 and D00542-1/20,924). *Now:* each row declares
`⌈row_desi × 0.01⌉` (→ 15 and 210 min); cost split was already proportional;
`Toplam maliyet` still sums exactly to the simulator total. Test covers the
two-item example + travel column staying full-leg.

**Fix C — Plan `Taşınan Desi` number format (26 Jul 2026).** The official template
`datas/TAŞIMA PLANI.xlsx` formats column K as `0.000`; our writer emitted `General`.
`src/export.py::_format_plan_workbook` now applies it on write, mirroring the
forecast writer. Values were already numeric so no parser was affected; this closes
the last cell-level difference from the template.

> **Milk-run stay-onboard rule — now live.** Rows for cargo that stays onboard at an
> intermediate stop declare **0** handling for that leg (jury: cargo is handled only
> where it is loaded/unloaded). All 249 chains in the published plan satisfy this,
> carry one `Araç ID` and one vehicle type per physical route, keep the same
> `Talep ID` across legs with constant desi, declare full-leg travel on every row,
> and charge the physical route's vehicle cost exactly once.

### 4.3 Still-open jury questions (unchanged)

1. Rented `V-ID` stability across days (we use daily-unique IDs — conservative).
2. Does the jury score the **declared** cost columns or recompute? (We make
   declared columns exactly consistent with the recompute either way.)
3. Are `desi = 0` forecast rows accepted? (We write the full grid with zeros;
   fallback = floor of 1.)

---

## 5. Remaining Work (priority order)

**Stage 0, Stage 1 (same-lane repair), Stage 2 (≤4-stop milk-run) and Stage 3
(Tier A mid-route pickup) are complete, refereed, and published.** The transport-plan
side is in a shippable state; the remaining items are improvements, not gaps.

1. **Forecast bias on month-end weeks** (+28.3 % on the 30 Mar–5 Apr backtest
   window) — but see §5.1: the target itself turned out to be an artefact, and every
   correction candidate failed out of sample. Treat with suspicion before reopening.
2. **Mid-route pickup, Tier B.** Tier A is shipped (−80,861.55 TL). Tier B extends a
   route by one stop so the picked-up cargo can go somewhere the route does not
   already visit; an independent measurement saw ~145,764 TL for A+B, i.e. ~66k TL
   incremental. It produces **5-stop routes**, so `MAX_CHAIN_STOPS` and the K1
   documentation both move — a separate decision with its own gate.
3. **Five-stop chains.** Not viable with the current brute-force enumerator: no
   result after ~13.5 min CPU / 1.3 GB RSS (C(n,5) = 254,992 subsets × 120 stop
   orders × 3 vehicle types). Needs pruning (branch-and-bound, capacity-first
   ordering) before it is worth attempting.
4. **Tır in chains.** No rule forbids it — the `uğrama` prohibition is scoped to
   *kiralık* vehicles only, never to a vehicle type — and it would double the chain
   capacity ceiling to 22,400 desi. **Measured and rejected**; see §5.1.
5. **Rider + 1-hub consolidation candidates** (Eskişehir/Kocaeli/Mersin/Yalova/
   İstanbul hubs; detour < 1.15; K1 contract supported by the simulator).
6. **Tuning sweep**: `TIR_MIN_DESI`, `MAX_CARRY_DESI`, `CARRY_VAR_TL`,
   `MAX_TIR_PER_LANE`; measure each change with the simulator total.
7. **Phase 4**: final packaging and submission.

### 5.1 Measured dead ends (do not re-attempt)

- **Same-lane merging of low-fill Spot routes** — re-measured on the shipped ≤4-stop
  plan: **46 of 46** sub-30% Spot routes (418,581.51 TL, mean fill 14.33%, 36,912
  desi) are the *only* vehicle on their lane that day, so there is no peer to merge
  into. Recoverable saving: **0 TL**.
- **Exact max-weight matching instead of greedy set-packing** — worth 47,795.99 TL on
  the pair-only candidate set, but it is an *alternative* to the multi-stop pass, not
  additive, and the shipped ≤4-stop pass already beats it by ~476k TL.
- **SLA reduction by targeting the worst demands** — the penalty is a long tail; the
  worst 20 demands hold only ~15% of it.
- **Five-stop chains by brute force** — no result after ~13.5 min CPU / 1.3 GB RSS.
- **Tır in chains** — measured after all: the full patch is **+18,100 TL worse** and
  the minimal patch is bit-identical. Kamyon dominates Tır at the same 12,000 desi in
  every condition (318.25 vs 487.50 TL/h), and 93.6% of the profitable Tır candidates
  die on the seven zero-capacity centres.
- **Forecast bias correction** (per-slot multipliers, +day-2, rebound, base
  recalibration) — the target is spurious: the +28.3% figure is an artefact of the
  29 Mar cutoff fitting the `first_day` multiplier from n=2. Under leave-one-out the
  shipped model's bias is **−0.0573** (under-forecast). All four candidates failed out
  of sample.

---

## 6. How to Run / Verify

```bash
pip install -r requirements.txt
python -m pytest        # 528 tests, 258.81 s in final verification
python run.py           # 104.7 s; staged gates then plan-first publication
```

Data files in `datas/` are **read-only** (`tir_kapasiteleri v2.xlsx` is the
jury-updated version — never use v1).

---

## 7. Git State

- `feature/stage2-milkrun-ve-gorsel-readme` (pushed):
  - Phase 2–3 implementation (forecast + optimizer + scheduler + export +
    milk-run skeleton).
  - Stage 1 + Stage 2: evaluation boundary, deterministic same-lane repair, neutral
    chain layer, chain-aware scheduler/referee, deterministic k-stop milk-run, exact
    Stage 1/Stage 2 entry gates, staged artifact provenance and re-simulation,
    rollback-safe plan-first publication, the official accepted workbooks and the
    Stage 2 acceptance report.
  - The Stage 3 hand-off plan and its measured prototype under
    `docs/superpowers/{plans,prototypes}/`.
- **Stage 3 (this change):** `src/pickup.py`, `tests/test_pickup.py`, the `STAGE3_*`
  gates and publication rewiring in `run.py`, Stage 3 gate tests in
  `tests/test_optimize.py`, refreshed figures, and the Stage 3 acceptance report.
