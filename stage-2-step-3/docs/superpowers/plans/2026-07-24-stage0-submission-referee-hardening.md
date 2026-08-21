# Stage 0 Submission and Referee Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make forecast Excel cells template-faithful, reject incorrect declared arrivals, and require declared plan cost to reconcile with the independent simulator before any cost optimization begins.

**Architecture:** Keep internal DataFrames in canonical string form while teaching schema validation to normalize Excel `time` cells. Apply workbook formatting only inside the atomic export path. Extend each parsed simulator leg with its declared arrival and compare it with the matrix-derived arrival. Add a pure cost-reconciliation helper called by `run.py` after simulation and before final plan export.

**Tech Stack:** Python 3.11+, pandas, openpyxl, pytest, existing `src.schemas`, `src.export`, `src.simulator` and `run.py` pipeline.

## Global Constraints

- Preserve exactly 4,046 forecast rows, 4,977,975 forecast desi and the existing `D#####` IDs.
- Preserve the current baseline total cost within 0.01 TL during Stage 0.
- Require zero simulator violations after all Stage 0 changes.
- Forecast slots written to Excel must be real `datetime.time` cells with number format `h:mm`.
- `Tahmin Edilen Desi` cells must use number format `0.000`.
- Plan departure and arrival strings remain `DD.MM.YYYY` and `HH:MM`.
- `Toplam maliyet` continues to mean allocated vehicle cost plus row SLA penalty.
- Do not modify forecast-model values, optimizer decisions or route topology in Stage 0.
- Do not commit unless the user explicitly requests a commit.

---

## File Structure

| File | Responsibility in Stage 0 |
|---|---|
| `src/schemas.py` | Canonicalize forecast slot values from strings or Excel time objects before validation and grid comparison. |
| `src/export.py` | Format forecast workbook cells and assert declared plan total against simulator total. |
| `src/simulator.py` | Parse declared arrival and reject a mismatch with matrix-derived arrival. |
| `run.py` | Invoke cost reconciliation after simulation and before writing the accepted plan. |
| `tests/test_schemas.py` | Unit tests for forecast slot normalization and logical duplicate detection. |
| `tests/test_export.py` | Excel cell-type/number-format and cost-reconciliation tests. |
| `tests/test_simulator_full.py` | Declared-arrival positive and negative regression tests. |

---

### Task 1: Canonical Forecast Slot Validation

**Files:**
- Modify: `src/schemas.py:10-12, 68-76, 86-126, 211-228`
- Test: `tests/test_schemas.py:1-41, 63-65, 240-244`

**Interfaces:**
- Produces: `_canonical_forecast_time(value) -> str | None`
- Consumed by: `validate_forecast()` and `validate_forecast_grid()`
- Accepted input examples: `"09:00"`, `"09:00:00"`, `datetime.time(9, 0)`
- Canonical output examples: `"09:00"`, `"17:00"`

- [ ] **Step 1: Write failing tests for Excel time objects and canonical duplicate cells**

Add `time` to the datetime import in `tests/test_schemas.py` and append:

```python
def test_forecast_accepts_excel_time_cells(data):
    df = _valid_forecast_df()
    df.loc[0, "Talep Tamamlama Saati"] = time(9, 0)
    df.loc[1, "Talep Tamamlama Saati"] = time(17, 0)

    assert validate_forecast(df, data) == []


def test_forecast_rejects_logical_duplicate_across_time_representations(data):
    rows = _valid_forecast_df().iloc[[0]].to_dict("records")
    duplicate = rows[0].copy()
    duplicate["Talep ID"] = "D00002"
    duplicate["Talep Tamamlama Saati"] = time(9, 0)
    df = pd.DataFrame([rows[0], duplicate], columns=FORECAST_COLS)

    errors = validate_forecast(df, data)

    assert any("forecast hücresi tekrarı" in error for error in errors)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python -m pytest tests/test_schemas.py::test_forecast_accepts_excel_time_cells tests/test_schemas.py::test_forecast_rejects_logical_duplicate_across_time_representations -v
```

Expected: both tests fail because `_valid_time` only accepts `HH:MM` strings and raw pandas duplicate comparison treats string/time representations as different.

- [ ] **Step 3: Implement canonical forecast time conversion**

Change the datetime import in `src/schemas.py`:

```python
from datetime import date, datetime, time, timedelta
```

Add directly after `_valid_time`:

```python
def _canonical_forecast_time(value) -> str | None:
    if isinstance(value, time):
        if value.second or value.microsecond:
            return None
        return value.strftime("%H:%M")
    if isinstance(value, datetime):
        if value.second or value.microsecond:
            return None
        return value.strftime("%H:%M")

    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.second == 0:
            return parsed.strftime("%H:%M")
    return None
```

In `validate_forecast`, replace the raw slot conversion with:

```python
slot = _canonical_forecast_time(r["Talep Tamamlama Saati"])
if slot not in ("09:00", "17:00"):
    errs.append(
        f"satır {i}: Saat 09:00/17:00 değil: "
        f"{r['Talep Tamamlama Saati']}"
    )
```

Replace raw `df.duplicated(subset=FORECAST_CELL_COLS)` with logical cells:

```python
logical_cells = [
    (row["Tarih"],
     _canonical_forecast_time(row["Talep Tamamlama Saati"]),
     row["Çıkış Transfer Merkezi"],
     row["Varış Transfer Merkezi"])
    for _, row in df.iterrows()
]
if len(logical_cells) != len(set(logical_cells)):
    errs.append("Aynı tarih/saat/çıkış/varış forecast hücresi tekrarı var")
```

In `validate_forecast_grid`, canonicalize the slot when constructing `cell`:

```python
slot = _canonical_forecast_time(row["Talep Tamamlama Saati"])
if slot is None:
    continue
cell = (row["Çıkış Transfer Merkezi"],
        row["Varış Transfer Merkezi"], row_date, slot)
```

- [ ] **Step 4: Run schema tests**

Run:

```bash
python -m pytest tests/test_schemas.py -q
```

Expected: all schema tests pass, including the two new tests.

- [ ] **Step 5: Review checkpoint**

Inspect `git diff -- src/schemas.py tests/test_schemas.py`. Confirm plan-time validation remains strict `HH:MM`; only forecast slots accept Excel time objects and zero-second `HH:MM:SS` strings.

---

### Task 2: Template-Faithful Forecast Workbook Formatting

**Files:**
- Modify: `src/export.py:4-11, 19-43, 46-53`
- Test: `tests/test_export.py:1-10, 49-70`

**Interfaces:**
- Produces: `_format_forecast_workbook(path: Path) -> None`
- Extends: `_write_round_trip(..., formatter: Callable[[Path], None] | None = None) -> Path`
- Consumes: Task 1 schema normalization during post-write round-trip validation.

- [ ] **Step 1: Write the failing workbook fidelity test**

Add imports to `tests/test_export.py`:

```python
from datetime import date, time
from openpyxl import load_workbook
```

Extend `test_write_forecast_xlsx_round_trips_exact_template` after existing assertions:

```python
    workbook = load_workbook(path)
    sheet = workbook.active
    assert sheet["C2"].value == time(9, 0)
    assert sheet["C3"].value == time(17, 0)
    assert sheet["C2"].number_format == "h:mm"
    assert sheet["C3"].number_format == "h:mm"
    assert sheet["F2"].number_format == "0.000"
    assert sheet["F3"].number_format == "0.000"
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m pytest tests/test_export.py::test_write_forecast_xlsx_round_trips_exact_template -v
```

Expected: failure because `C2/C3` are strings with `General` format and `F2/F3` do not use `0.000`.

- [ ] **Step 3: Add workbook formatting to the atomic export path**

Add imports in `src/export.py`:

```python
from datetime import time
from typing import Callable

from openpyxl import load_workbook
```

Add this helper before `_write_round_trip`:

```python
def _format_forecast_workbook(path: Path) -> None:
    workbook = load_workbook(path)
    sheet = workbook.active
    slot_col = FORECAST_COLS.index("Talep Tamamlama Saati") + 1
    desi_col = FORECAST_COLS.index("Tahmin Edilen Desi") + 1

    for row in range(2, sheet.max_row + 1):
        slot_cell = sheet.cell(row=row, column=slot_col)
        hour, minute = (int(part) for part in str(slot_cell.value)[:5].split(":"))
        slot_cell.value = time(hour, minute)
        slot_cell.number_format = "h:mm"
        sheet.cell(row=row, column=desi_col).number_format = "0.000"

    workbook.save(path)
```

Extend `_write_round_trip` without changing existing plan-writer behavior:

```python
def _write_round_trip(df: pd.DataFrame, path, columns: list,
                      validator, label: str,
                      formatter: Callable[[Path], None] | None = None) -> Path:
    # existing pre-validation and temporary-path setup
    try:
        df.loc[:, columns].to_excel(temporary_path, index=False)
        if formatter is not None:
            formatter(temporary_path)
        round_tripped = pd.read_excel(temporary_path)
        # existing round-trip validation and atomic replace
```

Pass the formatter only from `write_forecast_xlsx`:

```python
return _write_round_trip(
    df, path, FORECAST_COLS,
    lambda frame: validate_forecast_grid(
        frame, data, start, end, ods=ods),
    "Forecast",
    formatter=_format_forecast_workbook,
)
```

- [ ] **Step 4: Run export and schema tests**

Run:

```bash
python -m pytest tests/test_export.py tests/test_schemas.py -q
```

Expected: all tests pass and the forecast workbook fidelity assertions confirm real Excel time cells.

- [ ] **Step 5: Review checkpoint**

Inspect `git diff -- src/export.py tests/test_export.py`. Confirm `_write_round_trip` still validates before writing, validates after formatting/read-back, and atomically replaces the destination only after both validations pass.

---

### Task 3: Declared Arrival Referee Check

**Files:**
- Modify: `src/simulator.py:17-26, 58-81, 136-167`
- Modify: `tests/test_simulator_full.py:27-41, 92-146`

**Interfaces:**
- Extends: `Leg.declared_arr: datetime`
- `parse_legs(plan_df) -> list[Leg]` parses one declared arrival per grouped leg.
- `trace_vehicle(legs, data)` adds a violation when declared and recomputed arrival differ.

- [ ] **Step 1: Write a failing declared-arrival test**

Add after `test_on_time_no_penalty` in `tests/test_simulator_full.py`:

```python
def test_declared_arrival_must_match_matrix_travel(data):
    wrong = dict(P1, **{"Varış Saati": "12:00"})

    result = simulate(_plan([wrong]), _forecast([F1]), data, rental_days=[])

    assert any("beyan varış" in violation and "matris varışı" in violation
               for violation in result.violations)


def test_same_leg_rows_require_one_declared_arrival(data):
    first = dict(P1, **{"Taşınan Desi": 5000.0})
    second = dict(P1, **{"Talep ID": "D00002",
                         "Taşınan Desi": 5000.0,
                         "Varış Saati": "12:00"})

    result = simulate(
        _plan([first, second]),
        _forecast([
            dict(F1, **{"Tahmin Edilen Desi": 5000.0}),
            dict(F1, **{"Talep ID": "D00002",
                        "Tahmin Edilen Desi": 5000.0}),
        ]),
        data,
        rental_days=[],
    )

    assert any("aynı bacak grubunda beyan varış tutarsız" in violation
               for violation in result.violations)
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
python -m pytest tests/test_simulator_full.py::test_declared_arrival_must_match_matrix_travel tests/test_simulator_full.py::test_same_leg_rows_require_one_declared_arrival -v
```

Expected: both tests fail because the simulator ignores declared arrival columns.

- [ ] **Step 3: Parse and validate declared arrival**

Extend `Leg`:

```python
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
```

Inside each `parse_legs` group, parse every declared arrival and reject
inconsistent row declarations:

```python
declared_arrivals = [
    parse_dt(str(row["Varış Tarihi"]), str(row["Varış Saati"]))
    for _, row in g.iterrows()
]
if len(set(declared_arrivals)) > 1:
    leg_violations.append(
        f"{vid}: aynı bacak grubunda beyan varış tutarsız"
    )
```

Pass `declared_arr=declared_arrivals[0]` to `Leg`.

Immediately after matrix arrival is computed in `trace_vehicle`, add:

```python
if leg.declared_arr != arr:
    tr.violations.append(
        f"{leg.vehicle_id}: beyan varış {leg.declared_arr:%d.%m %H:%M} "
        f"!= matris varışı {arr:%d.%m %H:%M}"
    )
```

- [ ] **Step 4: Correct legacy tests that intentionally used fake arrivals**

Update transfer and adversarial fixtures in `tests/test_simulator_full.py` so
each test isolates its intended rule:

```python
# Yalova -> Eskişehir, Kamyon: ceil(2.63 * 60) = 158 minutes
# 12:40 + 158 minutes = 15:18
leg2["Varış Saati"] = "15:18"
leg2["Yolculuk süresi"] = 158

# Desi-change fixture: leg 1 departs 10:00 and arrives Yalova at 10:56.
leg1["Varış Saati"] = "10:56"
# Leg 2 departs 12:30 and arrives Eskisehir at 15:08.
leg2["Varış Saati"] = "15:08"
leg2["Yolculuk süresi"] = 158

# Bad-transfer-timing fixture: 11:00 + 158 minutes = 13:38.
leg2["Varış Saati"] = "13:38"
leg2["Yolculuk süresi"] = 158

# Invalid rented route still has a matrix-valid declared arrival:
# Istanbul -> Mardin Tir, 1,291 minutes from 29.06 11:00.
p["Varış Tarihi"] = "30.06.2026"
p["Varış Saati"] = "08:31"

# Wrong-origin fixture: Eskisehir -> Yalova Tir is 170 minutes.
p["Varış Saati"] = "14:50"
```

Update `tests/test_simulator_cost.py` as well:

```python
# These cost-suite rows inherit Tır from _row; active matrix travel is 170 min.
# Milk-run second leg: 13:00 + 170 minutes = 15:50.
row["Varış Saati"] = "15:50"
# Desi-change second leg: 13:30 + 170 minutes = 16:20.
row["Varış Saati"] = "16:20"
```

Preserve the original target violation in every adversarial test; do not allow
an unrelated arrival violation to satisfy it.

- [ ] **Step 5: Run the simulator tests**

Run:

```bash
python -m pytest tests/test_simulator_full.py tests/test_simulator_cost.py -q
```

Expected: all simulator tests pass, including the new negative test and updated transfer fixtures.

- [ ] **Step 6: Review checkpoint**

Search test fixtures for `Varış Saati": "23:59"` and inspect each remaining
case. Keep it only when the test intentionally expects an arrival mismatch or
the route is missing and no matrix arrival exists.

---

### Task 4: Declared Total Cost Reconciliation

**Files:**
- Modify: `src/export.py:14-17, 56-61`
- Modify: `run.py:12-17, 55-68`
- Test: `tests/test_export.py:83-101`

**Interfaces:**
- Produces: `require_plan_total(df: pd.DataFrame, expected_total: float, tolerance: float = 0.01) -> None`
- Raises: `ValueError` with both declared and referee totals when values differ beyond tolerance.
- Consumed by: `run.main()` after `simulate` and before `write_plan_xlsx`.

- [ ] **Step 1: Write failing reconciliation tests**

Import `require_plan_total` in `tests/test_export.py` and add:

```python
def test_require_plan_total_accepts_referee_total():
    frame = _plan_df()

    require_plan_total(frame, 1000.0)


def test_require_plan_total_rejects_mismatch():
    frame = _plan_df()

    with pytest.raises(ValueError, match="Toplam maliyet uzlaşmıyor"):
        require_plan_total(frame, 999.0)
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
python -m pytest tests/test_export.py::test_require_plan_total_accepts_referee_total tests/test_export.py::test_require_plan_total_rejects_mismatch -v
```

Expected: collection error because `require_plan_total` does not exist.

- [ ] **Step 3: Implement the pure reconciliation helper**

Add to `src/export.py` before `write_plan_xlsx`:

```python
def require_plan_total(df: pd.DataFrame, expected_total: float,
                       tolerance: float = 0.01) -> None:
    declared = float(pd.to_numeric(
        df["Toplam maliyet"], errors="raise").sum())
    if abs(declared - expected_total) > tolerance:
        raise ValueError(
            "Toplam maliyet uzlaşmıyor: "
            f"beyan {declared:.2f} TL, hakem {expected_total:.2f} TL"
        )
```

- [ ] **Step 4: Call reconciliation from the end-to-end pipeline**

Update the import in `run.py`:

```python
from src.export import (require_plan_total, write_forecast_xlsx,
                        write_plan_xlsx)
```

After printing simulator violations and before `write_plan_xlsx`, add:

```python
if result.violations:
    raise RuntimeError(
        f"Plan hakem simülatöründe {len(result.violations)} ihlal üretti"
    )
require_plan_total(plan_frame, result.total_cost)
```

This makes `run.py` fail closed: a violated or cost-inconsistent candidate is
never exported as the accepted plan.

- [ ] **Step 5: Run export tests**

Run:

```bash
python -m pytest tests/test_export.py -q
```

Expected: all export tests pass.

- [ ] **Step 6: Review checkpoint**

Inspect `git diff -- src/export.py run.py tests/test_export.py`. Confirm the
helper is pure, tolerance is exactly 0.01 TL, and final plan writing happens only
after zero violations and cost reconciliation.

---

### Task 5: Stage 0 Full Acceptance Gate

**Files:**
- Verify: `src/schemas.py`
- Verify: `src/export.py`
- Verify: `src/simulator.py`
- Verify: `run.py`
- Verify: `out/Talep-tahmini.xlsx`
- Verify: `out/Tasima-plani.xlsx`

**Interfaces:**
- Consumes all Stage 0 deliverables.
- Produces a new accepted Stage 0 baseline with unchanged forecast and cost.

- [ ] **Step 1: Run focused Stage 0 tests**

Run:

```bash
python -m pytest tests/test_schemas.py tests/test_export.py tests/test_simulator_full.py tests/test_simulator_cost.py -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run the complete suite**

Run:

```bash
python -m pytest -q
```

Expected: zero failures; test count is at least 160 after the new Stage 0 tests.

- [ ] **Step 3: Run the complete pipeline**

Run:

```bash
python run.py
```

Expected:

```text
Forecast rows: 4,046
Forecast desi: 4,977,975
Simulator violations: 0
Vehicle cost: 15,460,592.57 TL
SLA penalty: 1,020,367.20 TL
Total cost: 16,480,959.77 TL
```

All costs must remain within 0.01 TL of the fixed baseline.

- [ ] **Step 4: Inspect Excel cell types and formats**

Run:

```powershell
python -c "from datetime import time; from openpyxl import load_workbook; w=load_workbook('out/Talep-tahmini.xlsx'); s=w.active; assert s['C2'].value in (time(9,0), time(17,0)); assert s['C2'].number_format == 'h:mm'; assert s['F2'].number_format == '0.000'; print(type(s['C2'].value).__name__, s['C2'].number_format, s['F2'].number_format)"
```

Expected output begins with `time h:mm 0.000`.

- [ ] **Step 5: Verify forecast identity did not change**

Run:

```powershell
python -c "import pandas as pd; f=pd.read_excel('out/Talep-tahmini.xlsx'); assert len(f)==4046; assert abs(f['Tahmin Edilen Desi'].sum()-4977975)<1e-9; assert f['Talep ID'].nunique()==4046; print(len(f), int(f['Tahmin Edilen Desi'].sum()), f['Talep ID'].nunique())"
```

Expected output: `4046 4977975 4046`.

- [ ] **Step 6: Run whitespace and worktree review**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors. Review all modified and untracked paths; do not
stage or commit unrelated user files.

- [ ] **Step 7: Record Stage 0 acceptance evidence**

Update the verified-results section in `PLAN.md` only if runtime or test count
changed. Preserve the baseline cost values and add one sentence confirming real
Excel time-cell output and declared-arrival referee coverage.

---

## Stage 0 Completion Definition

Stage 0 is complete only when:

- The official forecast output uses real Excel time cells and template number
  formats.
- A deliberately wrong declared arrival produces a referee violation.
- `run.py` refuses to export violated or cost-inconsistent plans.
- Forecast row count, IDs, desi and all baseline costs are unchanged.
- The full suite and end-to-end run pass with zero simulator violations.

After Stage 0 acceptance, write a separate Stage 1 implementation plan for the
same-lane repair pass. Do not mix Stage 1 changes into this plan.
