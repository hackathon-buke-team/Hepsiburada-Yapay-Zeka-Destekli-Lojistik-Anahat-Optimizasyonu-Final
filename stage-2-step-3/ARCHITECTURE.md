# 🏛️ System Architecture — Hepsiburada Stage-2 (Advanced Solution)

> **Teknofest 2026 · AI-Assisted Logistics Line-Haul Optimization — Stage 2**
> The complete technical reference: **what the problem is, what has been built,
> what remains, and how every piece fits together — start to finish.**
> Companion to `ROADMAP.md` (the short status view). This file is the deep dive.

---

## Table of Contents

1. [Problem Definition](#1-problem-definition)
2. [Input Data Model](#2-input-data-model)
3. [EDA Findings That Drive the Design](#3-eda-findings-that-drive-the-design)
4. [Target Architecture (end-to-end pipeline)](#4-target-architecture-end-to-end-pipeline)
5. [✅ DONE — Phase 1: Foundation Layer](#5--done--phase-1-foundation-layer)
6. [🔵 NEXT — Phase 2: Forecast Engine](#6--next--phase-2-forecast-engine)
7. [⬜ TODO — Phase 3: Transport Optimizer](#7--todo--phase-3-transport-optimizer)
8. [⬜ TODO — Phase 4: Integration & Submission](#8--todo--phase-4-integration--submission)
9. [The Referee Simulator (quality gate) in Detail](#9-the-referee-simulator-quality-gate-in-detail)
10. [Time & Rounding Rules (single source of truth)](#10-time--rounding-rules-single-source-of-truth)
11. [Contracts & Invariants (do not break)](#11-contracts--invariants-do-not-break)
12. [Open Jury / Q&A Questions](#12-open-jury--qa-questions)
13. [Test Strategy](#13-test-strategy)
14. [Status Ledger & Work Order](#14-status-ledger--work-order)
15. [How to Run](#15-how-to-run)

---

## 1. Problem Definition

We deliver **two coupled outputs** for the horizon **29 Jun 09:00 → 05 Jul 17:00**:

### 1.1 Demand Forecast (`TALEP TAHMİNİ.xlsx`)
Predict `desi` for **every historically-active OD (origin→destination) pair ×
2 time slots (09:00 / 17:00) × 7 days = ~4046 rows**. A row is required for each
combination (even low-value ones). Each row carries a synthetic `Talep ID`
(`D00001…`). Scored against **real actuals** via WMAPE.

### 1.2 Transport Plan (`TAŞIMA PLANI.xlsx`)
Move **our own forecasted demand** with an **hour-level (minute-resolution)**
vehicle plan at minimum total cost. Vehicle IDs `V0001…`; demand can be split
`D00001-1 / D00001-2` (recursively, `-1-1`). Scored on **our own forecast**, not
hidden data.

### 1.3 Cost Model
```
Total Cost = Vehicle Cost + SLA Penalty

Vehicle Cost = hourly_rate × usage_time  +  distance_km × per_km_rate
  usage_time = origin handling + waiting + travel + destination handling
               (from first load-start to last unload-end)

SLA Penalty  = late_desi × ceil(late_hours) × 0.40 TL
  SLA clock starts at demand-ready (09:00/17:00), stops when destination
  handling finishes. SLA window = 1 day (≤773 km lane) or 2 days (≥782 km).
```

### 1.4 Hard Rules (from spec + Q&A + `son-gelen-message.txt`)
- **Handling time** = `0.01 min/desi`, **separately** for load and unload. All
  cargo on one vehicle is handled simultaneously. Durations **round UP** to the
  next whole minute (55.2 min → 56).
- **Handling capacity** per TM per day (desi; inbound + outbound + consolidation
  pooled). Resets at **00:00**. A handling op crossing midnight is **split
  proportionally by time** (e.g. 10 000 desi started 23:30 over 100 min →
  3 000 desi on day 1, 7 000 on day 2).
- **Tır (semi-truck) capacity** per TM per day: counts **only Tır-type**
  vehicles (rented + spot), inbound and outbound pooled. A stationary
  unload-then-reload = **1 visit**. Resets at 00:00.
- **Rented vehicles (kiralık):** 14 vehicles on 12 routes, **must depart every
  day** even if empty; **no return trip**; **no intermediate stops**; only their
  own route. (Empty rented legs are written with `Talep ID` blank, desi 0.)
- **Spot vehicles:** unlimited trips, **milk-run allowed** (multiple stops),
  loaded return allowed; **empty returns are NOT written** to the plan.
- **Time resolution** = minute; a vehicle may depart at any minute of the day.
- Deliveries may spill past the horizon (e.g. 5 Jul demand delivered 7 Jul).
  There is **no optimizer runtime limit** (minutes-scale targeted).

### 1.5 Disqualification Risk
**Any deviation from the exact output template = not evaluated.** The format
validators in `src/schemas.py` are the hard gate.

---

## 2. Input Data Model

All files live in `datas/` and are loaded by `src/data.py` into typed, immutable
domain objects (`CompetitionData`). Column names/types are asserted on load.

| File | Loads into | Key contents / numbers |
|---|---|---|
| `teknofest26_gelismis.xlsx` | `demand` (DataFrame) | ~66 024 rows; `tarih, cikis, varis, talep_id, toplam_desi, slot`; slots normalized to `09:00`/`17:00`. **17:00 carries ~91% of desi.** |
| `Araç_Kapasite_Maliyet_Saat.xlsx` | `vehicles: dict[str,VehicleType]` | 4 types: **Tır**, **Kamyon**, **Hafif Kamyon**, **Kamyonet**. Each has `capacity_desi`, rented & spot `hourly` + `per_km`. (e.g. Tır 22 400 desi, 487.5 spot hourly, 25 spot/km; Kamyonet 5 600 desi.) |
| `Kiralık_Araclar.xlsx` | `rentals: list[RentalRoute]` | 12 routes / 14 vehicles (`origin, dest, count, vehicle`). ~42.2k TL/day sunk cost. |
| `sehirler_arasi_lojistik.xlsx` | `lanes: dict[(o,d),Lane]` | **exactly 306** directed lanes; `km`, per-type travel `hours`, `sla_days` (1 or 2). Derived speeds: Tır 65, Kamyon 70, Hafif 75, Kamyonet 80 km/h. |
| `Ellecleme-kapasite.xlsx` | `handling_cap: dict[TM,float]` | 18 TMs, all capacities `> 0` (asserted). |
| `tir_kapasiteleri v2.xlsx` | `tir_cap: dict[TM,int]` | 18 TMs. **Yalova 4, Balıkesir 1, seven TMs = 0.** ⚠️ **v2 is the jury-updated version — never use the old v1.** |
| `TALEP TAHMİNİ.xlsx` | (template only) | Output format example for the forecast. |
| `TAŞIMA PLANI.xlsx` | (template only) | Output format example for the plan. |

**Derived:** `tms` = 18 sorted transfer centers (union of lane endpoints).
**Kocaeli is never a destination** → demand appears on **289 OD pairs** of the
306 lanes.

**Data files are read-only and must never be modified.**

---

## 3. EDA Findings That Drive the Design

Every design choice below traces to one of these evidence-backed findings:

| Finding | Design consequence |
|---|---|
| **Month-end collapse** (deterministic in 5/5 months): last day ~1–3% of normal, day-before 0.6–0.7×, next business day 1.1–1.9×. **30 Jun is inside the horizon.** | **Calendar-multiplier layer** — the single highest-ROI forecast component. |
| **Day-of-week dominates:** Mon 1.93×, Sun 0.10×; 17:00 = 91% of desi. Backtest: recent same-DOW median (holidays excluded) ≈ 22.4% WMAPE vs naive 29.7%. | Base model = **robust DOW statistic**; ML challenger only if it proves out. |
| Yalova lanes opened 24 Jan–2 Feb; Kocaeli never a destination; Sundays only ~90 lanes active. | Exclude January for Yalova lanes; `*→Kocaeli` off-grid; intermittency rule. |
| Rented fleet ~42.2k TL/day sunk; fill cost 0.07–0.10 TL/desi; ~112k desi/day of empty trunk. | Optimizer: **fill rented first** + rider candidates. |
| **Tır-capacity bottleneck:** Yalova 4 (Mon need ~20), Balıkesir 1 (rented consumes it), 7 TMs = 0; Eskişehir/Kocaeli/Mersin spacious. | Hub set + tır-slot assignment as MILP constraints. |
| Mon 29 Jun: 8+ TMs at 130–140% of handling capacity. | Cross-day shifting + 00:00-reset exploitation + push consolidation to Wed–Sat. |
| **SLA is loose:** min direct slack 11.3 h; 09:00→17:00 wave-merge safe on all 289 lanes; small remainders cheaper to penalize than to dedicate a vehicle. | "Wait + penalty" is a **first-class candidate**; SLA is a soft constraint. |
| **Vehicle ladder:** ≤5600 Kamyonet; 5600–7200 Kamyon(<165 km)/Hafif(>165 km); 7200–12000 Kamyon; above → Tır. On İstanbul↔Yalova (60 km) 2 Kamyon beats 1 Tır. | Candidate-generator rules. |

---

## 4. Target Architecture (end-to-end pipeline)

```
datas/*.xlsx
   │
   ▼
src/data.py        Excel loaders → typed, validated domain objects        ✅ DONE
   │                (TM, Lane, VehicleType, RentalRoute, capacities, demand)
   ▼
src/forecast.py    Forecast engine → Forecast[~4046 rows]                  🔵 NEXT
   │                DOW-median base × calendar multipliers × intermittency
   ▼
src/candidates.py  Route-candidate set per demand                         ⬜ TODO
   │                (direct / rented trunk / rider / 1-hub / wait+penalty)
   ▼
src/optimize.py    Daily CP-SAT MILP → vehicle counts, assignments,       ⬜ TODO
   │                consolidation decisions (day-by-day, carry-over, feedback loop)
   ▼
src/schedule.py    Minute scheduler → departure/arrival minutes,          ⬜ TODO
   │                capacity ledgers, midnight split, V-ID / D-ID generation
   ▼
src/simulator.py   REFEREE SIMULATOR — independent recompute of cost +    ✅ DONE
   │                every rule check; reads only the output DataFrames
   ▼
src/export.py      Template-exact Excel writing + format validator        ⬜ TODO (writer)
                   (validate before writing; re-read & re-simulate after)  ✅ DONE (validators)

run.py             End-to-end pipeline (one command, runtime measured)     ⬜ TODO
tests/             Unit + property tests; the 5 PDF worked examples        ✅ 58 passing
```

**Support modules already built:** `src/timeutil.py` (rounding/time),
`src/ledger.py` (capacity ledgers), `src/backtest.py` (forecast backtest infra).

---

## 5. ✅ DONE — Phase 1: Foundation Layer

Six modules in `src/`, **58 passing tests**, PDF worked examples encoded
verbatim. This layer is the bedrock the optimizer will be built and judged on.

### 5.1 `src/timeutil.py` — Time & rounding (single source of truth)
- `HANDLING_MIN_PER_DESI = 0.01`, `SLA_TL_PER_DESI_HOUR = 0.4`.
- `_ceil_guarded(x) = math.ceil(round(x, 6))` — rounds up to whole minute while
  guarding against float artifacts (275.99999 must not overflow to 276).
- `travel_minutes(hours)`, `handling_minutes(desi)` (0 for desi ≤ 0),
  `late_hours(deadline, completion)` (ceil hours, 0 if not late),
  `parse_dt / fmt_date / fmt_time` (`DD.MM.YYYY`, `HH:MM`).

### 5.2 `src/data.py` — Data layer
- `load_all(data_dir) → CompetitionData` with frozen dataclasses
  `VehicleType / Lane / RentalRoute`.
- `_resolve_file()` — **Unicode-normalization-agnostic** filename resolution
  (tries literal, then NFC-normalized directory scan; ascii-safe error) — needed
  because Turkish filenames on Windows NTFS may be stored NFD.
- Asserts: exactly 306 lanes, 18 TMs, `handling_cap`/`tir_cap`/`tms` key sets
  identical, all handling caps `> 0`. Demand `tarih` cast to datetime, slot
  `9:00 → 09:00` normalized.

### 5.3 `src/ledger.py` — Daily capacity ledgers (00:00 reset)
- `HandlingLedger.add(tm, start, desi)` — computes handling duration, then a
  `while` loop **splits desi proportionally across midnight boundaries**
  (23:30 + 100 min → 3000/7000 across two days). `violations()` reports over-cap
  and unknown TMs.
- `TirLedger.add_event(tm, day, vehicle_id, visit_id)` — a **set** of
  `(vehicle_id, visit_id)` per `(tm, day)`, so a stationary reload counts once.
  `count()` and `violations()` (over-cap + unknown TM).

### 5.4 `src/schemas.py` — Output templates + format validators
- `FORECAST_COLS` (6) and `PLAN_COLS` (16) — **exact** template strings,
  including the traps: `"Araç Tipi"` (Spot/Kiralık) vs `"Araç türü"` (vehicle
  name); `"Varış elleçleme"` (lowercase e) vs `"Çıkış Elleçleme"` (capital E).
- Regexes: demand ID `^D\d{5}$`, split ID `^D\d{5}(-\d+)*$`, vehicle `^V\d{4,}$`,
  date `DD.MM.YYYY`, time `HH:MM`. `base_demand_id()` strips split suffixes.
- `validate_forecast(df, data)` — ID format, unique IDs, valid TMs, slot ∈
  {09:00,17:00}, non-negative numeric desi.
- `validate_plan(df, data)` — vehicle/type/lane checks; empty-rented leg
  (blank ID + desi 0) allowed, spot never empty, desi > 0 otherwise.
- `_num()` helper makes non-numeric cells a validation error, not a crash.

### 5.5 `src/simulator.py` — Referee simulator (see §9 for the full check list)
- `parse_legs → trace_vehicle → simulate`. Recomputes each vehicle's usage
  hours and cost, each demand's delivery + SLA penalty, and all ledger
  violations, reading **only the two output DataFrames** — a true independent
  second implementation. Reference: spot Tır 10 000 desi İst→Yalova = 3 580 TL.
- Adversarial review hardened two optimizer-class bugs: **C1** (pickup at wrong
  origin counted as delivered) and **C2** (mixed vehicle-type chain evading
  capacity + tır ledger).

### 5.6 `src/backtest.py` — Forecast backtest infrastructure
- `build_grid(demand, start, end, ods)` — full OD×slot×day grid; unseen cell =
  desi 0.
- `wmape`, `bias`; baselines `naive_lastweek` (t−7 lookup) and `dow_median`
  (k=4 recent same-DOW medians, holidays/month-ends excluded).
- `EXCLUDE_2026` = holidays + Jan–May month-end pairs (**intentionally excludes
  June** — 29/30 Jun are horizon targets, never training-excluded).
- `run_backtest(demand, model_fn, test_start, test_end)` — rolling-origin;
  `model_fn` is responsible for using only pre-target data (documented leakage
  contract). **Results: naive 0.2965, dow_median 0.2275 WMAPE.**

---

## 6. 🔵 NEXT — Phase 2: Forecast Engine

**Goal:** a complete, format-valid `TALEP TAHMİNİ.xlsx`, minimizing WMAPE with
bias ≈ 0. **Its `Talep ID`s become the demand universe feeding Phase 3** (see
contract K1).

### 6.1 Model — DECIDED
```
forecast(cell) = DOW_median_base(OD, slot, DOW; k=4, holidays/month-ends excluded)
                 × calendar_multiplier(date)
```
The horizon has **no public holiday** (Eid was late May). So the calendar layer
touches only three days:

| Day | Role | Multiplier (to calibrate) |
|---|---|---|
| 29 Jun | day before month-end | ~×0.7 |
| 30 Jun | **month-end collapse** | ~×0.02 |
| 01 Jul | first business day (rebound) | ~×1.4 |
| 02–05 Jul | normal | ×1.0 |

### 6.2 Output scope — DECIDED
**Full grid, rounded, zeros included:** one row per active OD × day × slot
(~4046), `round(desi) ≥ 0`, unique `Talep ID`. A `desi > 0` subset is kept
internally for the optimizer.

### 6.3 Modules to build
- **`src/forecast.py`** — `calendar_multipliers(train)`, `forecast_horizon(...)`,
  `assign_talep_ids(...)` (deterministic sequential `D#####`),
  `to_forecast_frame(...)`. Base **reuses `backtest.dow_median` by import** (no
  copy — single source of truth).
- **`src/frozen_backtest.py`** — `run_frozen(demand, model_fn, cutoff, h_start,
  h_end)`: train ≤ cutoff, **single-shot** (no refit inside the horizon — mirrors
  the real competition). Validated on a past week that **contains a month-end**,
  so the 30-Jun logic is genuinely exercised.
- **`src/schemas.py` extension** — `validate_forecast_grid(...)`: grid
  completeness (no missing / extra cells).
- **`src/export.py`** — `write_forecast_xlsx(...)`: writes the template exactly;
  round-trips through `validate_forecast`.

### 6.4 Calibration method
```
multiplier[offset] = median over historical month-ends of
                     ( actual_volume(offset_day) / DOW_baseline(offset_day) )
offset ∈ { last day, last-1 day, first business day }
```
Dividing by the DOW baseline **isolates the month-end effect from the DOW
effect** (30 Jun is a Tuesday; the base already captures Tuesday volume, the
multiplier only adds "it's month-end"). Global (all OD) with median for
robustness. The frozen backtest **A/B-tests each multiplier** (with vs without).

### 6.5 Acceptance criteria (gate)
- Frozen-backtest WMAPE **≤ DOW-median baseline**.
- `|bias|` small (target < ~2%).
- **Zero** errors from `validate_forecast` and `validate_forecast_grid`.

### 6.6 Open build decisions
- **(a)** Calendar multiplier global vs **per-slot** (17:00 is 91% of desi) —
  start global, let the frozen backtest decide.
- **(b)** Which past week is the frozen gate (recommend one with a month-end).
- **(c)** Module split as above.

---

## 7. ⬜ TODO — Phase 3: Transport Optimizer

Turns the Phase-2 forecast into `TAŞIMA PLANI.xlsx`. **Every candidate plan is
validated by the referee simulator before acceptance.**

### 7.1 `src/candidates.py` — Route candidates
Ordered candidate set per `(demand, day)`:
1. **Direct** — 1–2 vehicle-type combos by the ladder rule.
2. **Rented trunk** — if the OD is one of the 12 rented routes.
3. **Rider** — rented first leg + transfer + spot second leg (detour < 1.25).
4. **1-hub transfer** — hub ∈ {Eskişehir, Kocaeli, Mersin, Yalova, İstanbul},
   detour < 1.15, if tır-slot/handling allows; Kütahya/Bilecik only Kamyon
   cross-dock.
5. **Wait + penalty** — next wave/day + `ceil(hours) × 0.4 TL/desi`.
6. **Milk-run** (v2, if time) — 2–3-stop same-direction spot routes.

### 7.2 `src/optimize.py` — Daily MILP (OR-Tools CP-SAT)
- **Decomposition:** per-day (capacities are daily); previous-day carry-over is
  input; 7 (+2 spill) days solved in sequence; optional look-ahead shadow of
  day d+1 demand as a capacity reservation.
- **Variables:** integer vehicle count per lane×type×day; demand→candidate
  assignment (splittable); hub-flow variables; rented fill.
- **Constraints:** handling desi/day-TM; tır count/day-TM (incl. rented);
  vehicle capacity; mandatory rented departure; candidate-SLA feasibility.
- **Objective:** Σ vehicle cost + Σ penalty (integer, scaled to kuruş).
- **Feedback loop:** if the scheduler finds a minute-level infeasibility, add a
  cut for that day and re-solve (max 3 iters, then safe fallback: shift load to
  the next wave).
- **Local search (quality layer):** swap/merge/rebalance moves on the MILP
  solution, accepted by the simulator score (light hill-climb / SA).

### 7.3 `src/schedule.py` — Minute scheduler
- Expands daily decisions into concrete per-vehicle timelines.
- Handling ledger with **midnight proportional split** — deliberately exploits
  the 23:30 shift (peak-Monday 17:00 loads handled late-night, drawn from
  Tuesday's quota).
- Rounds transfer + handling up to whole minutes; emits `HH:MM`.
- Generates `V0001…` (a spot vehicle may run many trips/day) and `D…-1/-2`
  splits **only at the forecast origin TM** (contract K1).

### 7.4 `src/export.py` — Plan writer (validators already exist)
- `write_plan_xlsx(...)`: template-exact columns/order/types; validate before
  writing; re-read the written file and pass it through the simulator.

### 7.5 Supporting follow-ups (from the ledger)
- **I1** — recompute declared plan cost/SLA columns and cross-check vs the
  simulator; numeric checks on cost columns.
- **R2** — make `SimResult.violations` structured so local search can filter.
- **R3** — end-to-end handling + tır capacity-violation regression tests through
  `simulate()`.

---

## 8. ⬜ TODO — Phase 4: Integration & Submission

- `run.py`: single-command `data → forecast → optimize → schedule → simulate →
  export`, with runtime logging.
- Final referee-simulator pass on both files: **0 violations**, cost recomputed
  and equal to declared.
- Both files pass `validate_forecast` / `validate_plan` with **0 errors**.
- Sensitivity/tuning pass on calendar multipliers and SLA-vs-vehicle thresholds.
- Source code packaged for submission.

---

## 9. The Referee Simulator (quality gate) in Detail

`src/simulator.py` is an **independent second implementation** of the scoring
rules. It reads only the two output DataFrames + raw data — it never sees the
optimizer's internal state — so a disagreement between optimizer and simulator
is a real bug, caught before submission.

**Pipeline:** `parse_legs` (group plan rows into legs) → `trace_vehicle` (build
each vehicle's timeline & cost) → `simulate` (cross-vehicle demand integrity,
SLA, ledgers, rented rules).

**Every check it performs:**

| # | Check | Message intent |
|---|---|---|
| 1 | Leg chain continuity (`leg.origin == prev_dest`) | "bacak zinciri kopuk" |
| 2 | Duplicate Talep ID within a leg | "aynı bacakta tekrarlı talep ID" |
| 3 | Vehicle capacity overflow | "kapasite aşımı" |
| 4 | Lane exists in the matrix | "matriste olmayan hat" |
| 5 | Vehicle type/kind consistent across a chain (C2) | "bacak araç tipi/türü tutarsız" |
| 6 | Load doesn't start before previous unload ends | "yükleme … önceki işlem bitmeden" |
| 7 | Load doesn't start before demand ready at origin | "yükleme talep hazır olmadan" |
| 8 | Route starts at the forecast origin TM (C1) | "rota tahmin çıkışından başlamıyor" |
| 9 | Multi-vehicle transfer timing (load2 ≥ unload1) | "aktarma zamanlaması ihlali" |
| 10 | Delivery integrity (Σ delivered == forecast desi) | "teslim edilen desi != tahmin" |
| 11 | SLA penalty (per final part, `late_desi × ⌈h⌉ × 0.4`) | (accrues cost) |
| 12 | Rented leg on its own route only | "kiralık rota dışı" |
| 13 | Rented ≤ 1 leg/day; unique ID per day | "kiralık araç aynı gün N bacak" |
| 14 | Mandatory rented departures (count matches) | "Kiralık ihlali … beklenen/plandaki" |
| 15 | Handling capacity per TM/day (with midnight split) | "Elleçleme kapasitesi aşıldı" |
| 16 | Tır capacity per TM/day | "Tır kapasitesi aşıldı" |
| 17 | Every plan Talep ID exists in the forecast | "tahmin dosyasında olmayan talep" |

**Cost recompute:** `cost = hourly × usage_hours + per_km × total_km`, where
`usage_hours` runs from the first load-start to the last unload-end (waiting
included). `SimResult` returns `vehicle_cost`, `sla_penalty`, `total_cost`,
`violations`, and per-vehicle / per-demand tables.

---

## 10. Time & Rounding Rules (single source of truth)

Everything routes through `src/timeutil.py` — no duplicated arithmetic anywhere.

- **Round up to whole minutes:** `math.ceil(round(x, 6))`. Example (jury):
  İst→Yalova transfer 0.92 h = 55.2 min → **56 min**.
- **Handling:** `desi × 0.01 min`, rounded up, **separately** for load and
  unload. Example: 5000 desi → 50 min.
- **Midnight split (jury example):** 10 000 desi started 29 Jun 23:30 over
  100 min → 3000 desi charged to 29 Jun, 7000 to 30 Jun.
- **SLA:** `ceil(late_hours) × late_desi × 0.4 TL`. Example: 6000 desi 1 h late
  → 2400 TL. Clock starts at 09:00/17:00 ready-time, stops at destination
  unload-end.

---

## 11. Contracts & Invariants (do not break)

- **K1 — split-ID contract:** split suffixes (`D00001-1`, `-2`, recursively
  `-1-1`) are created **only at the forecast origin TM**; across hub transfers
  the **same ID continues**. The simulator's C1 origin check (row 8 above)
  depends on this — the Phase-3 scheduler must honor it.
- **Format = disqualification:** exact template columns only. `src/schemas.py`
  runs on every output before it's written.
- **Optimize on our own forecast:** no demand uncertainty in the plan phase.
  Keep forecast **bias ≈ 0** (WMAPE is symmetric; inflating desi inflates plan
  cost, deflating hurts WMAPE) — there is deliberately **no "reserve capacity
  for uncertainty"** concept.
- **Simulator is always the referee:** in CI, every plan passes through it; any
  cost mismatch or violation fails the build.
- **Data files are read-only.**

---

## 12. Open Jury / Q&A Questions

Resolve via the competition Q&A channel; each changes a concrete decision:

1. **Rented vehicle IDs** — is a *daily-unique* `V-ID` accepted, or must IDs be
   stable across days? (Simulator currently flags multi-day rented IDs.)
2. **Scoring source** — does the jury score the **declared** cost columns, or
   **recompute** independently? (Affects how defensively we fill cost columns.)
3. **Zero-forecast rows** — is `Desi = 0` accepted, or must every row be a tiny
   positive value? (We chose full-grid-with-zeros; a floor of 1 desi is the ready
   fallback.)
4. ~~**Tır-capacity semantics**~~ — **ANSWERED (jury Q&A, Jul 2026):** capacity
   is total daily visits (inbound+outbound pooled); stationary unload+reload =
   1 visit; leave-and-return = 2. Our conservative interpretation was correct;
   `TirLedger` semantics match exactly. ✅ Closed.

---

## 13. Test Strategy

- **Unit:** the 5 PDF worked examples verbatim — (a) 5000 desi → 50 min handling;
  (b) 6000 desi 1 h late → 2400 TL; (c) 10 000 desi 5 h lane → 500 min usage
  (560 with a 1 h wait); (d) 23:30 10 000 desi → 3000/7000 split; (e) 0.92 h →
  56 min — plus rounding/split edge cases and the format validators.
- **Property:** random small scenarios → simulator finds no false violation;
  split-demand desi sums are preserved.
- **Backtest:** forecast dual-window + frozen single-shot (Phase 2); optimizer
  "known past week" scenario as a cost regression metric (Phase 3).
- **End-to-end:** `run.py` one command; outputs clean through simulator +
  validators; runtime reported.

Current suite: **155 tests passing** (`python -m pytest`, ~2 min, includes
real-data validation).

---

## 14. Status Ledger & Work Order

| Step | Deliverable | Status |
|---|---|---|
| 1 | Foundation: `data`, `timeutil`, `ledger`, `schemas`, `simulator`, `backtest` + PDF tests | ✅ **DONE** |
| 2 | Forecast v1: base + calendar multipliers + frozen backtest → `TALEP TAHMİNİ.xlsx` | ✅ **DONE** |
| 3 | Plan v1: rented fill + tır budget + spot mix enumeration + carry-over + scheduler → first valid plan + cost baseline (**16,480,959.77 TL**, 0 violations) | ✅ **DONE** |
| 3b | Q&A compliance pass (24 Jul): rented fleet on 6–7 Jul spill days + simulator `rental_days` auto-extension; per-row desi-proportional declared durations | ✅ **DONE** |
| 4 | Consolidation: rider + 1-hub candidates + peak-Monday tactics → cost iterations (each measured by the simulator) | ⬜ TODO |
| 5 | Quality layers: **milk-run wiring** (skeleton exists; chain V-ID + stay-onboard durations first), local search, LightGBM challenger | 🔵 **NEXT** |
| 6 | Hardening: property tests, runtime optimization, final format check, source packaging | ⬜ TODO |

Current suite: **155 tests passing** (`python -m pytest`, ~2 min).

**Out of scope:** real-time/stochastic replanning; 2+-hub chains (marginal gain,
high SLA/handling risk); as-the-crow-flies distance (forbidden — use the matrix
verbatim).

Detailed progress ledger (git-ignored): `.superpowers/sdd/progress.md`.
Design spec: `docs/superpowers/specs/2026-07-13-hepsiburada-stage2-design.md`.

---

## 15. How to Run

```bash
pip install -r requirements.txt
python -m pytest          # 155 tests, ~2 min (includes real-data validation)
python run.py             # end-to-end: both output files + simulator cost report
```

`python run.py` produces both output files end-to-end (~2 min) and prints the
simulator's cost report + violation list (currently **0 violations**,
total **16,480,959.77 TL**). See `PLAN.md` for the current status dashboard.
