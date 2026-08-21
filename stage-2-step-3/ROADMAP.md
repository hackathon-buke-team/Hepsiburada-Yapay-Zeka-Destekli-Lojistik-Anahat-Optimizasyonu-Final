# 🗺️ Project Roadmap — Hepsiburada Stage-2 (Advanced Solution)

> **Teknofest 2026 · AI-Assisted Logistics Line-Haul Optimization — Stage 2**
> This document tracks **what is done** and **what remains**. It is the single
> source of truth for team coordination. Update it as phases complete.

---

## 0. The Problem in One Paragraph

We must produce **two deliverables** for the horizon **29 Jun 09:00 → 05 Jul 17:00**:

1. **Demand forecast** (`TALEP TAHMİNİ.xlsx`) — predicted `desi` per
   origin–destination (OD) pair × time slot (09:00 / 17:00) × day.
2. **Transport plan** (`TAŞIMA PLANI.xlsx`) — an **hour-level** vehicle routing &
   load plan that moves the forecasted demand at **minimum total cost**.

`Total Cost = Vehicle Cost + SLA Penalty`, where
`Vehicle Cost = (hourly_rate × usage_time) + (distance × per_km_rate)` and
`SLA Penalty = late_desi × ceil(late_hours) × 0.40 TL`.

**Scoring:** the optimizer is scored on **our own forecast** (not hidden jury
data); the forecast is scored separately against real actuals (WMAPE). A
**format violation = disqualification**, so the format validators are a hard
gate, not a nicety.

---

## 1. Status at a Glance

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Foundations: time rules, data loaders, ledgers, schemas, **referee simulator**, backtest infra | ✅ **DONE** |
| **Phase 2** | **Forecast engine**: DOW-median base × calendar layer → `TALEP TAHMİNİ.xlsx` | ✅ **DONE** |
| **Phase 3** | **Optimizer**: rented fill → tır budget → spot mix + carry-over → minute scheduler → `TAŞIMA PLANI.xlsx` | 🔵 **v1 DONE** (direct + carry + flush-day rented; milk-run skeleton not wired; rider/1-hub + local search TODO) |
| **Phase 4** | Integration, end-to-end run, final tuning & submission | ⬜ **TODO** |

> **24 Jul 2026 — Q&A compliance pass:** full jury Q&A (`soru-cevap-full.docx`)
> verified against the pipeline: 16 items compliant, 2 fixed (rented fleet on
> 6–7 Jul spill days incl. simulator `rental_days` auto-extension; per-row
> desi-proportional declared handling durations). **155 tests green**,
> end-to-end **0 violations**, total cost **16,480,959.77 TL**. See `PLAN.md`.

---

## 2. ✅ DONE — Phase 1: Foundation Layer

All modules live in `src/`, are covered by **58 passing tests** (`python -m pytest`),
and encode the PDF worked examples verbatim. The referee simulator is the
independent quality gate for everything Phase 3 will produce.

| Module | Responsibility | Key guarantees |
|---|---|---|
| `src/timeutil.py` | Single source of truth for all rounding & time rules | `travel_minutes`, `handling_minutes` (0.01 min/desi), `late_hours`; durations **round UP** to whole minutes with a float-artifact guard |
| `src/data.py` | Validated Excel loaders → `CompetitionData` | NFC/NFD-agnostic filename resolution (Windows), typed frozen dataclasses, demand `tarih` cast to datetime |
| `src/ledger.py` | Daily capacity ledgers | Handling ledger with **midnight-proportional split**; tır-visit ledger (arrival+departure = 1 visit; stationary reload = 1) |
| `src/schemas.py` | Output templates + **format validators** | Exact column strings (incl. the "Araç Tipi" vs "Araç türü" trap); `validate_forecast` / `validate_plan`; numeric-safe cell parsing |
| `src/simulator.py` | **Referee simulator** — recomputes cost/SLA/violations from output DataFrames only | Double-implementation cross-check; caught two optimizer-class bugs (wrong-origin pickup C1, mixed-vehicle-type chain C2) before any optimizer exists |
| `src/backtest.py` | Forecast backtest infrastructure | `build_grid`, `wmape`, `bias`, `naive_lastweek`, `dow_median`; rolling-origin runner; holiday + month-end exclusion set |

**Backtest baseline results (real data):** naive last-week **WMAPE 0.2965**,
DOW-median (k=4, holidays/month-ends excluded) **WMAPE 0.2275**. Consistent with
EDA. GBM was found marginal.

---

## 3. 🔵 NEXT — Phase 2: Forecast Engine

**Goal:** produce a complete, format-valid `TALEP TAHMİNİ.xlsx` for the horizon,
minimizing WMAPE while keeping bias near zero. The output `Talep ID`s are
**synthetic and become the demand universe that feeds Phase 3** (see contract K1).

### 2.1 Model (decided)
`forecast = DOW_median_base(k=4, holidays/month-ends excluded) × calendar_multiplier(date)`

The horizon contains **no public holiday** (Eid was in late May). So the calendar
layer only touches **three days**:

| Day | Role | Multiplier (to calibrate) |
|---|---|---|
| 29 Jun | day before month-end | ~×0.7 |
| 30 Jun | **month-end collapse** | ~×0.02 |
| 01 Jul | first business day (rebound) | ~×1.4 |
| 02–05 Jul | normal | ×1.0 |

### 2.2 Output scope (decided)
**Full grid**, rounded, zeros included: one row per *active OD × day × slot*
(~4046 rows), `round(desi) ≥ 0`, unique `Talep ID`. A `desi > 0` subset is kept
internally for the optimizer.

### 2.3 Modules to build
- `src/forecast.py` — `calendar_multipliers(train)`, `forecast_horizon(...)`,
  `assign_talep_ids(...)`, `to_forecast_frame(...)`. Base reuses
  `backtest.dow_median` (import, do **not** copy).
- `src/frozen_backtest.py` — `run_frozen(demand, model_fn, cutoff, h_start, h_end)`:
  train ≤ cutoff, **single-shot** (no refit inside horizon — mirrors real
  competition), validated on a past week that **contains a month-end**.
- `src/schemas.py` extension — `validate_forecast_grid(...)`: grid completeness
  (no missing/extra cells).
- `src/export.py` — `write_forecast_xlsx(...)`: writes the template exactly;
  round-trips through `validate_forecast`.

### 2.4 Calibration method
`multiplier[offset] = median over historical month-ends of
( actual_volume(offset_day) / DOW_baseline(offset_day) )`, for
`offset ∈ {last day, last-1 day, first business day}`. Dividing by the DOW
baseline **isolates the month-end effect from the day-of-week effect**. Global
(all OD) with median for robustness; the frozen backtest A/B-tests each
multiplier (with vs without).

### 2.5 Acceptance criteria (gate)
- Frozen backtest WMAPE **≤ DOW-median baseline**.
- `|bias|` small (target < ~2%).
- **Zero** errors from `validate_forecast` and `validate_forecast_grid`.

### 2.6 Open decisions (need a call before/while building)
- **(a)** Calendar multiplier: global vs **per-slot** (09:00 vs 17:00 — 17:00 is
  91% of desi). Recommendation: start global, let the frozen backtest decide.
- **(b)** Which past week is the frozen-backtest gate (recommend one containing a
  month-end, e.g. the last-week-of-May window).
- **(c)** Module split as above (`forecast` / `frozen_backtest` / `export`).

---

## 4. ⬜ TODO — Phase 3: Transport Optimizer

Turns the Phase-2 forecast into `TAŞIMA PLANI.xlsx`. Every candidate plan is
validated by the **referee simulator** (`src/simulator.py`) before acceptance.

### 3.1 Planned pipeline
1. **Candidate generation** — feasible legs per demand; consolidation candidates
   at hub TMs; **kiralık-fill first** (14 mandatory rented vehicles, ~42.2k TL/day
   sunk cost, ~112k desi/day of free trunk capacity to fill at 0.07–0.10 TL/desi).
2. **Daily MILP** (CP-SAT / OR-Tools) — assign demand to vehicles/legs subject to
   handling-capacity and **tır-capacity** hard limits, minimizing total cost;
   trade dedicated-vehicle cost vs deliberate SLA penalty (buy lateness when
   cheaper than a vehicle).
3. **Minute-level scheduler** — expand daily decisions into concrete departure/
   arrival/handling timestamps; exploit the **midnight (00:00) capacity reset**.
4. **Export** — `src/export.py::write_plan_xlsx(...)`, honoring the **K1 split
   contract** (split suffixes originate only at the forecast origin TM; the same
   ID continues across hub transfers — the simulator's C1 origin check depends on
   this).

### 3.2 Supporting work (from the Phase-2/3 follow-up list)
- **I1** — plan column reconciliation: recompute declared cost/SLA columns and
  cross-check against the simulator; numeric checks on cost columns.
- **R2** — make `SimResult.violations` structured (so Phase-3 local search can
  filter on them).
- **R3** — end-to-end handling + tır capacity-violation regression tests through
  `simulate()`.

### 3.3 Hard constraints to respect (from EDA — these bite)
- **Tır capacity** is a hard bottleneck: Yalova 4 (Monday need ~20), Balıkesir 1
  (rented vehicles consume it), **7 TMs have 0**. Eskişehir / Kocaeli / Mersin are
  spacious hub candidates.
- **Handling capacity** is binding on **Mondays at 8+ TMs** → shift consolidation
  to Wed–Sat and use the midnight reset.
- **SLA is loose** (min slack 11.3h; all lanes fit direct) → buying small SLA
  penalties (0.4 TL/desi/h) is cheaper than a dedicated vehicle above ~850–1700
  desi at 400 km.
- **Vehicle ladder:** ≤5600 Kamyonet; 5600–7200 Kamyon(<165km)/Hafif(>165km);
  7200–12000 Kamyon; above → Tır. On İstanbul↔Yalova (60 km) **2 Kamyon beats 1
  Tır** (handling load).

---

## 5. ⬜ TODO — Phase 4: Integration & Submission

- End-to-end run: `data → forecast → optimize → schedule → simulate → export`.
- Final referee-simulator pass on both output files (0 violations, cost recomputed).
- Both files pass `validate_forecast` / `validate_plan` with **0 errors**.
- Sensitivity/tuning pass on calendar multipliers and SLA-vs-vehicle thresholds.

---

## 6. ❓ Open Jury / Q&A Questions (K2)

Resolve via the competition Q&A channel; each changes a concrete decision:

1. **Rented vehicle IDs** — is a *daily-unique* `V-ID` accepted (a rented vehicle
   re-used on another day getting a fresh ID), or must IDs be stable?
2. **Scoring source** — does the jury score the **declared** cost columns in our
   plan, or does it **recompute** cost independently? (Affects how defensively we
   fill the cost columns.)
3. **Zero-forecast rows** — is `Desi = 0` accepted in the forecast, or must every
   row be a **tiny positive** value? (We chose full-grid-with-zeros; this Q&A
   could flip us to a small floor.)

---

## 7. 📌 Key Contracts (do not break)

- **K1 — split-ID contract:** split suffixes (`D00001-1`, `D00001-2`) are created
  **only at the forecast origin TM**. Across hub transfers the **same ID
  continues**. The referee simulator's C1 wrong-origin check relies on this.
- **Format = disqualification:** any deviation from the exact template columns
  fails. `src/schemas.py` is the last line of defense — run it on every output.
- **Optimize on our own forecast:** no demand uncertainty in the plan phase; keep
  forecast **bias ≈ 0** so the optimizer isn't systematically over/under-served.

---

## 8. How to Run

```bash
pip install -r requirements.txt
python -m pytest          # 155 tests, ~2 min (includes real-data validation)
python run.py             # end-to-end: out/Talep-tahmini.xlsx + out/Tasima-plani.xlsx
```

Design specs and implementation plans live in `docs/superpowers/`.
Progress ledger (git-ignored) in `.superpowers/sdd/progress.md`.
