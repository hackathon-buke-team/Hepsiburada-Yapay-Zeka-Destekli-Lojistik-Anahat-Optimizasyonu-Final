# Büke Final Delivery Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a technically compliant, independently verified `Buke_997307_Final_Teslim.zip` and an optimization-first jury presentation without changing the submitted optimization decisions or reference result.

**Architecture:** Keep the optimizer and cost model frozen, and harden only the integration boundary around input selection, workbook validation, demand-ID restoration, output publication, and deterministic release packaging. Build the ZIP from an explicit allowlist so presentation and development files cannot enter it; maintain the presentation and jury documents as a separate, repo-relative artifact pipeline.

**Tech Stack:** Python 3.11, pandas 2.3.2, openpyxl 3.1.5, pytest, standard-library `zipfile`, HTML/CSS/JavaScript/SVG, Selenium/Chrome for deck QA, python-docx plus the Codex document renderer for DOCX QA.

## Global Constraints

- Team ID is exactly `997307`; team name is exactly `Büke`.
- Final upload is exactly `C:\Users\darkb\Desktop\hb-final\Buke_997307_Final_Teslim.zip`.
- ZIP size must be less than `10,000,000` bytes.
- ZIP root must contain `main.py`, `teknofest_manifest.json`, and `requirements.txt`; it must not contain a `final-teslim/` wrapper directory.
- ZIP contents are limited to `main.py`, `teknofest_manifest.json`, `requirements.txt`, `README.md`, `DEGISIKLIKLER.md`, `src/**`, `datas/**`, and `data/one_week_backtest.xlsx`.
- ZIP must not contain the presentation, DOCX files, tests, tools, `run.py`, caches, logs, temporary files, or a pre-generated `out/Tasima-plani.xlsx`.
- Do not alter vehicle selection, route search, Stage 0, same-lane repair, milk-run, pickup, cost, SLA, scheduling, or capacity logic.
- Reference acceptance values are 5,523 plan rows, 16 columns, 0 violations, `11,232,476.731944447` TL, and 0 changed cells against root `Tasima-plani.xlsx`.
- `python main.py` must run without arguments or user interaction and must never perform network installation.
- Output success means one `out/Tasima-plani.xlsx` sheet with the exact 16-column schema and a zero exit code only after independent revalidation.
- Main jury story is 14 optimization-first slides; forecast/WMAPE, the 250% infeasible case, rejected ideas, and detailed rules are appendix material.

This is one coordinated release plan because Task 8 accepts the runtime ZIP, deck, and jury documents together. Tasks 1-5 form the independently reviewable runtime-package track; Tasks 6-7 form the independently reviewable jury-artifact track.

---

### Task 1: Freeze release identity, dependency versions, and documented claims

**Files:**
- Create: `final-teslim/tests/test_release_metadata.py`
- Modify: `final-teslim/teknofest_manifest.json:1-16`
- Modify: `final-teslim/requirements.txt:1-5`
- Modify: `final-teslim/README.md`
- Modify: `final-teslim/KONTROL_LISTESI.md`
- Modify: `final-teslim/DEGISIKLIKLER.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: PDF manifest field names and the approved team identity.
- Produces: exact metadata read by `tools/build_release.py` in Task 5; pinned runtime dependency declarations.

- [ ] **Step 1: Write failing metadata tests**

```python
# final-teslim/tests/test_release_metadata.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_final_identity_and_commands():
    manifest = json.loads((ROOT / "teknofest_manifest.json").read_text("utf-8"))
    assert manifest["takim_id"] == "997307"
    assert manifest["takim_adi"] == "Büke"
    assert manifest["python_surumu"] == "3.11"
    assert manifest["kurulum_komutlari"] == [
        "python -m pip install -r requirements.txt"
    ]
    assert manifest["calistirma_komutu"] == "python main.py"
    assert manifest["girdi_ortam_degiskeni"] == "TEKNOFEST_INPUT_FILE"
    assert manifest["girdi_yedek_yolu"] == "data/one_week_backtest.xlsx"
    assert manifest["cikti_klasoru"] == "out/"
    assert manifest["beklenen_ciktilar"] == ["Tasima-plani.xlsx"]


def test_runtime_dependencies_are_exactly_pinned():
    active = [
        line.strip() for line in (ROOT / "requirements.txt").read_text("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert active == ["pandas==2.3.2", "openpyxl==3.1.5"]
```

- [ ] **Step 2: Run the metadata tests and confirm they fail**

Run from `final-teslim`:

```powershell
python -m pytest tests/test_release_metadata.py -q
```

Expected: failures for placeholder `takim_id`, the old `pip install` command, and ranged dependencies.

- [ ] **Step 3: Apply the exact identity and dependency values**

Set the manifest identity and command fields exactly as asserted above. Replace the two active requirement lines with:

```text
pandas==2.3.2
openpyxl==3.1.5
```

Update all five Markdown files so that:

- the manifest is described as completed with ID `997307`;
- no checklist row is green while mentioning an unresolved placeholder;
- the deliverable is named `Buke_997307_Final_Teslim.zip`;
- the archive root and no-pre-generated-output rules are explicit;
- `592/592` is described as the audit baseline, while the final report will use the post-change count;
- the ~150 second runtime remains labelled as a prior reference measurement until the fresh full run is complete;
- the final scoring scope is optimization only.

- [ ] **Step 4: Run targeted tests and textual consistency scans**

```powershell
python -m pytest tests/test_release_metadata.py -q
rg -n 'BASVURU_NUMARANIZI_YAZIN|"pip install -r requirements\.txt"|Manifest.*var|takim_id.*yer tutucu' . ..\README.md
```

Expected: tests pass; `rg` returns no unresolved placeholder or stale install command.

- [ ] **Step 5: Commit metadata hardening**

```powershell
git add final-teslim/teknofest_manifest.json final-teslim/requirements.txt final-teslim/README.md final-teslim/KONTROL_LISTESI.md final-teslim/DEGISIKLIKLER.md final-teslim/tests/test_release_metadata.py README.md
git commit -m "fix: finalize Buke delivery metadata"
```

---

### Task 2: Make the input contract exact and fail-fast

**Files:**
- Modify: `final-teslim/tests/test_contract.py:26-190,385-415`
- Modify: `final-teslim/src/contract.py:196-390`

**Interfaces:**
- Consumes: `FORECAST_COLS`, `INPUT_ENV_VAR`, `INPUT_FALLBACK_PATH`, and static `CompetitionData`.
- Produces: `resolve_input_path(root: Path | str = ".") -> Path`; `read_demand_table(path, data) -> tuple[pd.DataFrame, dict[str, str], list[str]]` with no silent row loss or coercion.

- [ ] **Step 1: Replace tolerant tests with exact-contract failures**

Add or replace tests with these concrete cases:

```python
def test_env_tanimli_fakat_dosya_yoksa_yedege_dusmez(tmp_path, monkeypatch):
    fallback = tmp_path / "data" / "one_week_backtest.xlsx"
    fallback.parent.mkdir(parents=True)
    fallback.write_bytes(b"x")
    missing = tmp_path / "missing.xlsx"
    monkeypatch.setenv(INPUT_ENV_VAR, str(missing.resolve()))
    with pytest.raises(InputContractError, match="TEKNOFEST_INPUT_FILE"):
        resolve_input_path(tmp_path)


def test_env_yolu_mutlak_olmalidir(tmp_path, monkeypatch):
    monkeypatch.setenv(INPUT_ENV_VAR, "relative.xlsx")
    with pytest.raises(InputContractError, match="mutlak"):
        resolve_input_path(tmp_path)


def test_ikinci_sayfa_reddedilir(tmp_path, data):
    path = tmp_path / "girdi.xlsx"
    frame = _demand_frame([
        ["D00001", "01.01.2030", "09:00", "İstanbul", "Yalova", 100]
    ])
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Sheet1")
        frame.to_excel(writer, index=False, sheet_name="Extra")
    with pytest.raises(InputContractError, match="tek sayfa.*Sheet1"):
        read_demand_table(path, data)


def test_kolon_adi_ve_sirasi_birebir_olmalidir(tmp_path, data):
    frame = _demand_frame([
        ["D00001", "01.01.2030", "09:00", "İstanbul", "Yalova", 100]
    ])
    frame = frame.rename(columns={"Talep ID": "talep id"})
    with pytest.raises(InputContractError, match="kolon"):
        read_demand_table(_write(frame, tmp_path / "girdi.xlsx"), data)


@pytest.mark.parametrize("bad_desi", [-1, 5.5, float("inf"), "abc", None])
def test_gecersiz_veya_kesirli_desi_dosyayi_reddeder(
        tmp_path, data, bad_desi):
    frame = _demand_frame([
        ["D00001", "01.01.2030", "09:00", "İstanbul", "Yalova", bad_desi]
    ])
    with pytest.raises(InputContractError, match="satır 2.*desi"):
        read_demand_table(_write(frame, tmp_path / "girdi.xlsx"), data)


@pytest.mark.parametrize("bad_id", [None, "", "   "])
def test_bos_talep_id_reddedilir(tmp_path, data, bad_id):
    frame = _demand_frame([
        [bad_id, "01.01.2030", "09:00", "İstanbul", "Yalova", 100]
    ])
    with pytest.raises(InputContractError, match="Talep ID"):
        read_demand_table(_write(frame, tmp_path / "girdi.xlsx"), data)


def test_tekrarli_talep_id_reddedilir(tmp_path, data):
    frame = _demand_frame([
        ["REQ-7", "01.01.2030", "09:00", "İstanbul", "Yalova", 100],
        ["REQ-7", "01.01.2030", "17:00", "İstanbul", "Yalova", 200],
    ])
    with pytest.raises(InputContractError, match="tekrarlı Talep ID"):
        read_demand_table(_write(frame, tmp_path / "girdi.xlsx"), data)


def test_gecersiz_satir_atlanmak_yerine_dosyayi_reddeder(tmp_path, data):
    frame = _demand_frame([
        ["D00001", "01.01.2030", "09:00", "İstanbul", "Yalova", 100],
        ["D00002", None, "09:00", "İstanbul", "Yalova", 200],
    ])
    with pytest.raises(InputContractError, match="satır 3.*tarih"):
        read_demand_table(_write(frame, tmp_path / "girdi.xlsx"), data)
```

Delete the old tests that require case/spacing-tolerant headers, silent row drops, negative-to-zero conversion, fractional rounding, and missing-env fallback.

- [ ] **Step 2: Run the exact-contract tests and confirm failure**

```powershell
python -m pytest tests/test_contract.py -q
```

Expected: the newly strict cases fail against current tolerant behavior.

- [ ] **Step 3: Implement strict path and workbook validation**

Use this control flow in `resolve_input_path`:

```python
env_value = os.environ.get(INPUT_ENV_VAR, "").strip().strip('"').strip("'")
if env_value:
    env_path = Path(env_value)
    if not env_path.is_absolute():
        raise InputContractError(
            f"{INPUT_ENV_VAR} mutlak bir .xlsx yolu olmalıdır: {env_value}")
    if env_path.suffix.lower() != ".xlsx" or not env_path.is_file():
        raise InputContractError(
            f"{INPUT_ENV_VAR} dosyası bulunamadı veya .xlsx değil: {env_path}")
    return env_path

fallback = root / INPUT_FALLBACK_PATH
if fallback.is_file():
    return fallback
raise InputContractError(f"Yedek girdi dosyası bulunamadı: {fallback}")
```

Open the workbook before parsing and require exact sheet and columns:

```python
book = pd.ExcelFile(path, engine="openpyxl")
if book.sheet_names != ["Sheet1"]:
    raise InputContractError(
        f"Girdi tam bir sayfa içermeli ve adı Sheet1 olmalı: {book.sheet_names}")
raw = pd.read_excel(book, sheet_name="Sheet1")
if list(raw.columns) != FORECAST_COLS:
    raise InputContractError(
        f"Girdi kolonları ad ve sıra olarak birebir değil. "
        f"Beklenen: {FORECAST_COLS}; bulunan: {list(raw.columns)}")
```

Replace `_to_desi` with a non-coercing integral parser:

```python
def _to_desi(value) -> int | None:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return None
    number = float(number)
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        return None
    return int(number)
```

During row iteration, raise `InputContractError` immediately with Excel row number `position + 2` and field name. Track original IDs in a set and reject empty or duplicate values. Keep the existing canonical sort and `id_map` generation after all rows pass.

- [ ] **Step 4: Run contract and reference-input regressions**

```powershell
python -m pytest tests/test_contract.py tests/test_data.py tests/test_schemas.py -q
```

Expected: all selected tests pass; the 4,046-row reference input retains its exact total desi and canonical ID order.

- [ ] **Step 5: Commit strict input behavior**

```powershell
git add final-teslim/src/contract.py final-teslim/tests/test_contract.py
git commit -m "fix: enforce exact final input contract"
```

---

### Task 3: Make hyphenated demand IDs unambiguous in referee validation

**Files:**
- Modify: `final-teslim/src/schemas.py:42-43`
- Modify: `final-teslim/src/simulator.py:226,437,526,549`
- Modify: `final-teslim/tests/test_schemas.py`
- Modify: `final-teslim/tests/test_simulator_full.py`

**Interfaces:**
- Consumes: plan item ID and the exact set of input demand IDs.
- Produces: `base_demand_id(talep_id: str, known_ids: Collection[str] | None = None) -> str`.

- [ ] **Step 1: Write failing ID-resolution tests**

```python
from src.schemas import base_demand_id


def test_tireli_ozgun_kimlik_once_tam_eslesir():
    known = {"TALEP-1", "TALEP-2"}
    assert base_demand_id("TALEP-1", known) == "TALEP-1"


def test_yalniz_sagdaki_sayisal_parca_soneki_ayrilir():
    known = {"TALEP-1"}
    assert base_demand_id("TALEP-1-2", known) == "TALEP-1"
    assert base_demand_id("TALEP-1-X", known) == "TALEP-1-X"


def test_kanonik_parca_kurali_korunur():
    assert base_demand_id("D00007-3") == "D00007"
```

Add a simulator regression that constructs a forecast row named `TALEP-1`, restores a split plan row as `TALEP-1-2`, and asserts no "tahmin dosyasında olmayan talep" violation is produced.

- [ ] **Step 2: Run tests and confirm the current first-hyphen split fails**

```powershell
python -m pytest tests/test_schemas.py tests/test_simulator_full.py -q
```

Expected: `TALEP-1` resolves incorrectly to `TALEP` before the fix.

- [ ] **Step 3: Implement exact-first, rightmost-numeric-suffix resolution**

```python
from collections.abc import Collection


def base_demand_id(
        talep_id: str,
        known_ids: Collection[str] | None = None) -> str:
    text = str(talep_id).strip()
    if known_ids is not None and text in known_ids:
        return text
    prefix, separator, suffix = text.rpartition("-")
    if separator and suffix.isdigit():
        if known_ids is None or prefix in known_ids:
            return prefix
    return text
```

At every simulator lookup, pass the demand mapping itself as the known-ID collection:

```python
rec = demands.get(base_demand_id(row.item_id, demands))
```

Apply the same argument to all four lookups at the current simulator lines 437, 526, and 549 plus any duplicate found by `rg -n "base_demand_id" final-teslim/src`.

- [ ] **Step 4: Run ID and full simulator tests**

```powershell
python -m pytest tests/test_schemas.py tests/test_simulator_full.py tests/test_contract.py -q
```

Expected: all tests pass, including canonical IDs and hyphenated originals.

- [ ] **Step 5: Commit identity mapping fix**

```powershell
git add final-teslim/src/schemas.py final-teslim/src/simulator.py final-teslim/tests/test_schemas.py final-teslim/tests/test_simulator_full.py
git commit -m "fix: preserve hyphenated demand identities"
```

---

### Task 4: Prevent stale or unverified output from receiving exit code zero

**Files:**
- Create: `final-teslim/tests/test_main_contract.py`
- Modify: `final-teslim/main.py:83-197,200-298`
- Modify: `final-teslim/src/contract.py:447-564`
- Modify: `final-teslim/tests/test_contract.py:246-354`

**Interfaces:**
- Consumes: `PlanEvaluation.result.violations`, canonical demand frame, `id_map`, and output destination.
- Produces: `_clear_stale_output(destination: Path) -> None`; `validate_written_plan(path, demand_frame, data, id_map) -> None`; `Publisher.publish(label: str, evaluation) -> bool` that accepts only independently valid plans.

- [ ] **Step 1: Write failing stale-output and exception-boundary tests**

```python
# final-teslim/tests/test_main_contract.py
from pathlib import Path
from types import SimpleNamespace

import pytest

import main as app


def test_clear_stale_output_removes_only_target_file(tmp_path):
    destination = tmp_path / "out" / "Tasima-plani.xlsx"
    destination.parent.mkdir()
    destination.write_bytes(b"old")
    sibling = destination.parent / "keep.txt"
    sibling.write_text("keep", encoding="utf-8")
    app._clear_stale_output(destination)
    assert not destination.exists()
    assert sibling.read_text("utf-8") == "keep"


def test_publisher_rejects_evaluation_with_violations(tmp_path, monkeypatch):
    publisher = app.Publisher(
        tmp_path / "out" / "Tasima-plani.xlsx",
        data=object(),
        id_map={},
        demand_frame=object(),
    )
    evaluation = SimpleNamespace(
        result=SimpleNamespace(violations=["capacity"]),
        plan_frame=object(),
    )
    assert publisher.publish("broken", evaluation) is False
    assert publisher.published is None


def test_call_with_deadline_keyboard_interrupti_yutmaz(monkeypatch):
    monkeypatch.setattr(app, "TIME_BUDGET_MINUTES", 0)

    def stop():
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        app._call_with_deadline(stop, (), float("inf"))
```

In `test_contract.py`, add a test that monkeypatches `src.simulator.simulate` to return one violation during temporary-file validation and asserts that the destination is not replaced.

- [ ] **Step 2: Run the new tests and verify failure**

```powershell
python -m pytest tests/test_main_contract.py tests/test_contract.py -q
```

Expected: missing `_clear_stale_output`, old `Publisher` signature, and `BaseException` swallowing fail.

- [ ] **Step 3: Implement output cleanup and narrow exception handling**

Add:

```python
def _clear_stale_output(destination: Path) -> None:
    destination.unlink(missing_ok=True)
```

Call it at the start of `main()` before input resolution:

```python
destination = ROOT / OUTPUT_DIR / OUTPUT_FILENAME
_clear_stale_output(destination)
```

Replace both `except BaseException as error` clauses inside `_call_with_deadline` with `except Exception as error`. Keep timeout fallback behavior unchanged.

- [ ] **Step 4: Validate the temporary workbook before atomic replace**

Add to `src.contract`:

```python
def validate_written_plan(path: Path | str, demand_frame: pd.DataFrame,
                          data, id_map: dict) -> None:
    from src.simulator import simulate

    book = pd.ExcelFile(path, engine="openpyxl")
    if book.sheet_names != ["Sheet1"]:
        raise ValueError(f"Yazılan plan tek Sheet1 içermiyor: {book.sheet_names}")
    plan = pd.read_excel(book, sheet_name="Sheet1")
    if list(plan.columns) != PLAN_COLS:
        raise ValueError("Yazılan planın 16 kolonu ad/sıra olarak hatalı")

    referee_demand = demand_frame.copy()
    referee_demand["Talep ID"] = [
        id_map.get(value, value) for value in referee_demand["Talep ID"]
    ]
    result = simulate(plan, referee_demand, data)
    if result.violations:
        raise ValueError(
            "Yazılan plan hakem ihlali içeriyor: " + "; ".join(result.violations[:5]))
    declared = float(pd.to_numeric(plan["Toplam maliyet"]).sum())
    if abs(declared - result.total_cost) > 0.01:
        raise ValueError(
            f"Beyan-hakem maliyet farkı: {declared} != {result.total_cost}")
```

Extend `write_final_plan` with optional `demand_frame`; after reloading and checking round-trip values, call `validate_written_plan(temporary_path, demand_frame, data, id_map)` before `os.replace`. Round-trip differences beyond the existing Excel tolerance must raise instead of printing a warning.

Extend `Publisher.__init__` with `demand_frame`; reject `evaluation.result.violations` before writing and pass the canonical demand frame to `write_final_plan`. Set `published` only after the validated atomic write succeeds.

Construct it from `main()` with the already cleared destination:

```python
publisher = Publisher(destination, data, id_map, frame)
```

- [ ] **Step 5: Require one validated publication before return zero**

At the end of `main`, replace the unconditional success path with:

```python
if publisher.published is None or not publisher.destination.is_file():
    raise RuntimeError("Doğrulanmış taşıma planı yayınlanamadı")
return 0
```

Keep the abandoned-worker `os._exit(code)` behavior only after `code` is obtained from a successful `main()` call.

- [ ] **Step 6: Run publication and evaluation regressions**

```powershell
python -m pytest tests/test_main_contract.py tests/test_contract.py tests/test_evaluation.py tests/test_simulator_full.py -q
```

Expected: all selected tests pass; invalid temporary workbooks never replace a valid destination.

- [ ] **Step 7: Commit runtime output hardening**

```powershell
git add final-teslim/main.py final-teslim/src/contract.py final-teslim/tests/test_main_contract.py final-teslim/tests/test_contract.py
git commit -m "fix: publish only independently valid final output"
```

---

### Task 5: Build the final ZIP from a deterministic runtime allowlist

**Files:**
- Create: `final-teslim/tools/build_release.py`
- Create: `final-teslim/tests/test_release_package.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: finalized `final-teslim` runtime tree and manifest.
- Produces: `collect_release_files(root: Path) -> list[Path]`; `validate_release_source(root: Path) -> None`; `build_release(root: Path, destination: Path) -> str` returning SHA-256.

- [ ] **Step 1: Write failing release-package tests**

```python
# final-teslim/tests/test_release_package.py
import json
import zipfile
from pathlib import Path

from tools.build_release import (
    MAX_BYTES, build_release, collect_release_files, validate_release_source,
)

ROOT = Path(__file__).resolve().parents[1]


def test_actual_release_allowlist_excludes_non_runtime_content():
    names = {path.relative_to(ROOT).as_posix() for path in collect_release_files(ROOT)}
    assert {"main.py", "teknofest_manifest.json", "requirements.txt"} <= names
    assert "data/one_week_backtest.xlsx" in names
    assert not any(name.startswith("out/") for name in names)
    assert not any(name.startswith("tests/") for name in names)
    assert not any(name.startswith("tools/") for name in names)
    assert not any(name.startswith("sunum/") for name in names)
    assert "run.py" not in names


def test_built_zip_has_runtime_files_at_archive_root(tmp_path):
    destination = tmp_path / "Buke_997307_Final_Teslim.zip"
    digest = build_release(ROOT, destination)
    assert len(digest) == 64
    assert destination.stat().st_size < MAX_BYTES
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert "main.py" in names
        assert "teknofest_manifest.json" in names
        assert "requirements.txt" in names
        assert not any(name.startswith("final-teslim/") for name in names)
        assert not any(name.startswith("out/") for name in names)


def test_build_is_byte_reproducible(tmp_path):
    first = tmp_path / "a.zip"
    second = tmp_path / "b.zip"
    assert build_release(ROOT, first) == build_release(ROOT, second)
    assert first.read_bytes() == second.read_bytes()


def test_manifest_placeholder_blocks_release(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    (root / "teknofest_manifest.json").write_text(
        json.dumps({"takim_id": "BASVURU_NUMARANIZI_YAZIN"}), encoding="utf-8")
    try:
        validate_release_source(root)
    except ValueError as error:
        assert "takim_id" in str(error)
    else:
        raise AssertionError("placeholder manifest accepted")
```

- [ ] **Step 2: Run release tests and confirm the module is missing**

```powershell
python -m pytest tests/test_release_package.py -q
```

Expected: import failure for `tools.build_release`.

- [ ] **Step 3: Implement an explicit allowlist and validation gates**

Use these constants:

```python
ROOT_FILES = {
    "main.py", "teknofest_manifest.json", "requirements.txt",
    "README.md", "DEGISIKLIKLER.md",
}
ROOT_DIRS = {"src", "datas"}
EXACT_FILES = {"data/one_week_backtest.xlsx"}
MAX_BYTES = 10_000_000
FORBIDDEN_TEXT = {
    "BASVURU_NUMARANIZI_YAZIN",
    "C:/Users/darkb",
    "C:\\Users\\darkb",
    "AppData/Local/Temp/claude",
}
```

`collect_release_files` must return sorted files from only those roots, excluding every cache component. `validate_release_source` must parse all ten manifest keys, assert identity `997307`/`Büke`, assert the three mandatory root files, scan UTF-8 text files for forbidden strings, and reject a source `out/Tasima-plani.xlsx` only as an archive candidate rather than deleting the user's file.

Create the archive deterministically:

```python
with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                     compresslevel=9) as archive:
    for source in collect_release_files(root):
        relative = source.relative_to(root).as_posix()
        info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o644 & 0xFFFF) << 16
        archive.writestr(info, source.read_bytes(), compresslevel=9)
```

Reopen the temporary ZIP with `testzip()`, verify root entries and exclusions, enforce `MAX_BYTES`, then atomically replace the destination. Return `hashlib.sha256(destination.read_bytes()).hexdigest()`.

Provide CLI defaults:

```python
source = Path(__file__).resolve().parents[1]
destination = source.parent / "Buke_997307_Final_Teslim.zip"
```

- [ ] **Step 4: Ignore only the generated final artifact**

Append this exact root `.gitignore` entry:

```text
/Buke_997307_Final_Teslim.zip
```

- [ ] **Step 5: Run package tests and inspect one generated archive**

```powershell
python -m pytest tests/test_release_package.py -q
python tools/build_release.py
tar -tf ..\Buke_997307_Final_Teslim.zip
```

Expected: tests pass; first archive entries are root-level files, with no `final-teslim/`, `out/`, `tests/`, `tools/`, `run.py`, or presentation paths.

- [ ] **Step 6: Commit deterministic packaging**

```powershell
git add .gitignore final-teslim/tools/build_release.py final-teslim/tests/test_release_package.py
git commit -m "feat: build deterministic final runtime archive"
```

---

### Task 6: Rebuild the jury deck as 14 optimization-first slides plus appendices

**Files:**
- Modify: `sunum/kaynak/v2_template.html:483-875`
- Modify: `sunum/kaynak/deck_data.json`
- Modify: `sunum/kaynak/build_deck.py`
- Create: `sunum/kaynak/test_build_deck.py`
- Create: `sunum/kaynak/qa_deck.py`
- Regenerate: `sunum/v2.html`
- Modify: `sunum/README.md`

**Interfaces:**
- Consumes: verified metrics from root `Tasima-plani.xlsx`, `final-teslim/data/one_week_backtest.xlsx`, and `deck_data.json`.
- Produces: self-contained `sunum/v2.html`; `sunum/kaynak/generated_notes.json`; automated screenshot/DOM QA results.

- [ ] **Step 1: Write failing build portability and slide-structure tests**

```python
# sunum/kaynak/test_build_deck.py
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUNUM = HERE.parent


def test_build_scripts_have_no_machine_specific_paths():
    text = "\n".join(
        (HERE / name).read_text("utf-8")
        for name in ("build_deck.py", "notes2md.py", "build_docs.py")
    )
    assert "C:/Users/darkb" not in text
    assert "AppData/Local/Temp/claude" not in text


def test_deck_builds_from_repo_sources():
    run = subprocess.run(
        [sys.executable, str(HERE / "build_deck.py")],
        cwd=SUNUM.parent, capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    html = (SUNUM / "v2.html").read_text("utf-8")
    assert "Takım ID 997307" in html
    notes = json.loads((HERE / "generated_notes.json").read_text("utf-8"))
    assert [slide["title"] for slide in notes[:4]] == [
        "Kapak", "Problem", "Final girdisi", "Maliyet modeli"
    ]
    assert len([slide for slide in notes if not slide["appendix"]]) == 14
```

- [ ] **Step 2: Run the build tests and confirm hardcoded paths/current flow fail**

```powershell
python -m pytest sunum/kaynak/test_build_deck.py -q
```

Expected: hardcoded Claude paths and the current 17-slide order fail.

- [ ] **Step 3: Make `build_deck.py` repo-relative and emit notes JSON**

Replace path constants with:

```python
HERE = pathlib.Path(__file__).resolve().parent
SUNUM = HERE.parent
TEMPLATE = HERE / "v2_template.html"
DATA = HERE / "deck_data.json"
DEST = SUNUM / "v2.html"
BUILD = HERE / ".build"
NOTES = HERE / "generated_notes.json"
BUILD.mkdir(exist_ok=True)
```

Read template/data from `TEMPLATE`/`DATA`; write JS and harness under `BUILD`. Extend the Node harness to print one machine-readable line:

```javascript
console.log('NOTES_JSON=' + JSON.stringify(
  SL.map((s, i) => ({
    n: i + 1,
    title: s.title,
    notes: s.notes,
    use: s.use,
    appendix: Boolean(s.appendix)
  }))
));
```

Parse that line in Python and write pretty UTF-8 JSON to `generated_notes.json`. Ignore `sunum/kaynak/.build/` in the root `.gitignore`.

Extend the slide helper and rendered element metadata:

```javascript
function add(title, html, notes, use, appendix=false) {
  SL.push({title, html, notes, use, appendix});
}
```

When rendering each slide, set `data-appendix="true"` for appendix entries and `data-appendix="false"` for the 14 main entries. Pass `true` as the fifth argument on every appendix `add` call.

- [ ] **Step 4: Implement the approved 14-slide main flow**

Reorder/rewrite the slide `add` calls so non-appendix slides are exactly:

1. `Kapak`: 4.98M desi, 0 violations, 11.23M TL; phrase the method as `açıklanabilir karar zekâsı`.
2. `Problem`: network, binding constraints, objective.
3. `Final girdisi`: external one-week input, exact six-column contract, forecast not called.
4. `Maliyet modeli`: vehicle plus SLA timeline; fix the overflowing lower-right card.
5. `Stage 0`: valid baseline and conditional local enumeration wording.
6. `Stage 1`: same-lane repair.
7. `Stage 2`: milk-run.
8. `Stage 3`: route-middle pickup.
9. `Rota vakası`: vehicle `V0154`, Spot; Istanbul to Balıkesir on 29.06.2026 18:26-21:41, then Balıkesir to Manisa 22:11-30.06.2026 00:24; `D00516-1` 2,974 desi and `D00532-1` 5,600 desi; visually show the carried 5,600 desi across both legs.
10. `Maliyet merdiveni`: 16.48M -> 14.68M -> 11.31M -> 11.23M; rebuild the SVG with left padding so no label is clipped.
11. `Bağımsız hakem`: 0 violations and declared/referee difference 0; label the post-change test count from the actual final pytest run only after Task 8.
12. `Genelleştirilebilirlik`: show only 35%, 100%, and 125% scenarios in the main table.
13. `Teknik uyum`: ID `997307`, team `Büke`, flat ZIP root, `main.py`, no forecast call, exact output schema; do not say merely "Manifest var".
14. `Kapanış`: final thesis and three verified proof points; no future-work list.

Mark forecast/data-cleaning/WMAPE, 250% infeasible stress, rejected ideas, detailed 17-rule table, and extended technical tables with `appendix: true`. Add an appendix divider after main slide 14. Keep all appendix content accessible through the table of contents but label it `Soru-Cevap Ekleri`.

Set minimum body copy to 20px, table copy to at least 18px, and chart labels to at least 16px. Limit each main slide to one primary chart and three headline numbers.

- [ ] **Step 5: Add automated browser QA**

Implement `qa_deck.py` with Selenium Chrome to:

- open `sunum/v2.html` at 1600x900;
- assert 14 non-appendix slides and the expected title sequence;
- visit every slide with ArrowRight;
- record browser console errors and require an empty error list; add an embedded data-URI favicon to the HTML template so there is no favicon 404;
- compare every visible child bounding box with its slide's `getBoundingClientRect()` in the same viewport coordinate system, using a 1px tolerance;
- require cards/tables to satisfy `scrollWidth <= clientWidth + 1` and `scrollHeight <= clientHeight + 1`, and require SVG text bounding boxes to stay within their SVG bounding box;
- assert generated SVG text contains no `NaN`, `undefined`, or `Infinity`;
- save full-slide screenshots to a caller-provided directory;
- test ArrowRight, Home, End, `N`, and `O` interactions.

Expose:

```powershell
python sunum/kaynak/qa_deck.py --output-dir "$env:TEMP\buke-deck-qa"
```

- [ ] **Step 6: Build, run automated QA, and visually inspect all main screenshots**

```powershell
python sunum/kaynak/build_deck.py
python -m pytest sunum/kaynak/test_build_deck.py -q
python sunum/kaynak/qa_deck.py --output-dir "$env:TEMP\buke-deck-qa"
```

Expected: build and tests pass; zero console/overflow/chart errors. Open all 14 main screenshots and confirm the Stage 4 card, cost ladder, route case, and compliance slide have no clipping or misleading status.

- [ ] **Step 7: Commit the rebuilt deck**

```powershell
git add .gitignore sunum/kaynak/v2_template.html sunum/kaynak/deck_data.json sunum/kaynak/build_deck.py sunum/kaynak/test_build_deck.py sunum/kaynak/qa_deck.py sunum/kaynak/generated_notes.json sunum/v2.html sunum/README.md
git commit -m "feat: refocus jury deck on final optimization"
```

---

### Task 7: Make jury documents reproducible and synchronize claims

**Files:**
- Modify: `sunum/kaynak/notes2md.py`
- Modify: `sunum/kaynak/build_docs.py`
- Modify: `sunum/dokumanlar/md/00-sunum-konusma-notlari.md`
- Modify: `sunum/dokumanlar/md/01-algoritma-teknik-rapor.md`
- Modify: `sunum/dokumanlar/md/02-juri-soru-cevap-kitabi.md`
- Modify: `sunum/dokumanlar/md/03-teknik-gereksinim-uyum-matrisi.md`
- Modify: `sunum/dokumanlar/md/04-sunum-konusma-metni.md`
- Regenerate: all five `sunum/dokumanlar/*.docx`
- Create: `sunum/kaynak/test_document_sources.py`

**Interfaces:**
- Consumes: `generated_notes.json`, approved deck order, manifest, release rules, and verified metrics.
- Produces: synchronized Markdown and five render-verified DOCX files.

- [ ] **Step 1: Write failing portability and claim-consistency tests**

```python
# sunum/kaynak/test_document_sources.py
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUNUM = HERE.parent
MD = SUNUM / "dokumanlar" / "md"


def test_document_builders_are_repo_relative():
    text = (HERE / "notes2md.py").read_text("utf-8") + \
        (HERE / "build_docs.py").read_text("utf-8")
    assert "C:/Users/darkb" not in text
    assert "AppData/Local/Temp/claude" not in text
    assert "notes.json" not in text
    assert "generated_notes.json" in text


def test_documents_use_final_identity_and_scope():
    combined = "\n".join(path.read_text("utf-8") for path in sorted(MD.glob("*.md")))
    assert "997307" in combined
    assert "BASVURU_NUMARANIZI_YAZIN" not in combined
    assert "ZIP kökünde `main.py`" in combined
    assert "final puanlaması yalnız optimizasyon" in combined
```

- [ ] **Step 2: Run source tests and confirm the current hardcoded paths/stale claims fail**

```powershell
python -m pytest sunum/kaynak/test_document_sources.py -q
```

- [ ] **Step 3: Make notes and DOCX builders repo-relative**

In both scripts define:

```python
HERE = pathlib.Path(__file__).resolve().parent
SUNUM = HERE.parent
DOCS = SUNUM / "dokumanlar"
MD = DOCS / "md"
```

Make `notes2md.py` read `HERE / "generated_notes.json"`; generate the slide map from the 14 main slides, then add a separately headed appendix section. Compute timing from notes at 135 words/minute and require main-flow estimated speech plus 18% transition allowance to be at most 15 minutes.

- [ ] **Step 4: Synchronize all Markdown sources**

Apply these exact content decisions across the five sources:

- Team identity is `997307 / Büke`.
- Final upload is one runtime ZIP; presentation/DOCX files are not inside it.
- Final scoring calls only optimization; forecast/WMAPE is background or appendix.
- Archive root contains `main.py`; no wrapper and no pre-generated output.
- Input errors fail explicitly; an invalid env path never falls back to another week.
- Fractional desi is explicitly rejected rather than rounded because the frozen solver is integer-based.
- Reference metrics remain 5,523 rows, 0 violations, and 11,232,476.73 TL.
- The final test count and runtime are inserted only from Task 8 evidence.
- "AI destekli" is replaced in the primary framing by "açıklanabilir karar zekâsı".
- "Enumeration optimum" is narrowed to "sabit hat-gün yükü için koşullu yerel optimum".
- The 250% infeasible scenario is Q&A material, not a main success claim.
- Delete every sentence claiming the package is fully ready before the final ZIP verification completes.

- [ ] **Step 5: Regenerate Markdown notes and all DOCX files**

```powershell
python sunum/kaynak/build_deck.py
python sunum/kaynak/notes2md.py
python sunum/kaynak/build_docs.py
python -m pytest sunum/kaynak/test_document_sources.py -q
```

Expected: all five DOCX files are recreated from current Markdown and all tests pass.

- [ ] **Step 6: Render every DOCX page for visual QA**

Install the missing Python renderer dependency in the current environment:

```powershell
python -m pip install pdf2image
```

Run the renderer for all five files with separate output directories:

```powershell
$renderer = 'C:\Users\darkb\.codex\plugins\cache\openai-primary-runtime\documents\26.819.11345\skills\documents\render_docx.py'
$renderRoot = Join-Path $env:TEMP 'buke-docx-qa'
Get-ChildItem -LiteralPath 'sunum\dokumanlar' -Filter '*.docx' | Sort-Object Name | ForEach-Object {
    $prefix = $_.BaseName.Substring(0, 2)
    $output = Join-Path $renderRoot $prefix
    python $renderer $_.FullName --output_dir $output --emit_pdf --verbose
    if ($LASTEXITCODE -ne 0) { throw "DOCX renderer failed: $($_.FullName)" }
}
```

Inspect every rendered PNG for clipped paragraphs, split table rows, unreadable 9pt text, blank pages, and broken Turkish glyphs. If LibreOffice/Poppler remains unavailable, use this concrete installed-Microsoft-Word fallback to export all five PDFs:

```powershell
$renderRoot = Join-Path $env:TEMP 'buke-docx-qa-word'
New-Item -ItemType Directory -Path $renderRoot -Force | Out-Null
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    Get-ChildItem -LiteralPath 'sunum\dokumanlar' -Filter '*.docx' | Sort-Object Name | ForEach-Object {
        $pdf = Join-Path $renderRoot ($_.BaseName + '.pdf')
        $doc = $word.Documents.Open($_.FullName, $false, $true)
        try { $doc.ExportAsFixedFormat($pdf, 17) } finally { $doc.Close($false) }
    }
} finally {
    $word.Quit()
}
$env:BUKE_DOCX_RENDER_ROOT = $renderRoot
```

Render every exported PDF without Poppler by using PyMuPDF:

```powershell
@'
import os
from pathlib import Path
import fitz

root = Path(os.environ["BUKE_DOCX_RENDER_ROOT"])
for pdf in sorted(root.glob("*.pdf")):
    out = root / pdf.stem
    out.mkdir(exist_ok=True)
    doc = fitz.open(pdf)
    for index, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(
            out / f"page-{index + 1:03d}.png")
    print(f"{pdf.name}: pages={len(doc)}")
'@ | python -
Remove-Item Env:BUKE_DOCX_RENDER_ROOT -ErrorAction SilentlyContinue
```

Inspect every emitted page image and record all five page counts in the verification report.

- [ ] **Step 7: Commit synchronized documents**

```powershell
git add sunum/kaynak/notes2md.py sunum/kaynak/build_docs.py sunum/kaynak/test_document_sources.py sunum/dokumanlar/md sunum/dokumanlar/*.docx
git commit -m "docs: synchronize jury evidence and generated documents"
```

---

### Task 8: Execute the complete release gate and create the upload ZIP

**Files:**
- Create: `docs/release/2026-08-21-buke-997307-verification.md`
- Generate, do not commit: `Buke_997307_Final_Teslim.zip`
- Verify: all files changed in Tasks 1-7

**Interfaces:**
- Consumes: finalized runtime package, deck, documents, test suite, release builder, and root reference workbook.
- Produces: the user-uploadable ZIP, its SHA-256, and an evidence-backed verification report.

- [ ] **Step 1: Record versions and baseline hashes**

```powershell
python --version
python -c "import pandas,openpyxl; print('pandas='+pandas.__version__); print('openpyxl='+openpyxl.__version__)"
Get-FileHash -Algorithm SHA256 'Tasima-plani.xlsx'
Get-FileHash -Algorithm SHA256 'final-teslim\data\one_week_backtest.xlsx'
git status --short
```

Expected: Python 3.11, pandas 2.3.2, openpyxl 3.1.5, and no unrelated changes.

- [ ] **Step 2: Verify the pinned requirements in a clean virtual environment**

```powershell
$venvRoot = Join-Path $env:TEMP ('buke-venv-' + [guid]::NewGuid().ToString('N'))
python -m venv $venvRoot
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'
& $venvPython -m pip install --disable-pip-version-check -r 'final-teslim\requirements.txt'
& $venvPython -c "import pandas,openpyxl; assert pandas.__version__=='2.3.2'; assert openpyxl.__version__=='3.1.5'; print('clean dependency install OK')"
```

Expected: clean installation succeeds with the exact two pinned versions. This validates installation; subsequent program runs make no network calls.

- [ ] **Step 3: Run the complete test suite from the package root**

```powershell
Push-Location final-teslim
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONHASHSEED='0'
python -m pytest -q -p no:cacheprovider
Pop-Location
```

Expected: every collected test passes. Record the actual total and elapsed time; do not reuse `592` if the new total differs.

- [ ] **Step 4: Run one full reference optimization from the development package**

```powershell
Push-Location final-teslim
Remove-Item Env:TEKNOFEST_INPUT_FILE -ErrorAction SilentlyContinue
python main.py
python tools/verify_output.py --plan out/Tasima-plani.xlsx --input data/one_week_backtest.xlsx
Pop-Location
```

Expected: exit code 0, 5,523 rows, exact 16-column schema, 0 violations, declared/referee difference 0, and total cost 11,232,476.731944447 TL.

- [ ] **Step 5: Compare the fresh plan cell-by-cell with the frozen reference**

Run from repository root:

```powershell
@'
import math
import pandas as pd

left = pd.read_excel('Tasima-plani.xlsx')
right = pd.read_excel('final-teslim/out/Tasima-plani.xlsx')
assert list(left.columns) == list(right.columns)
assert left.shape == right.shape == (5523, 16)
differences = []
for row in range(len(left)):
    for column in left.columns:
        a, b = left.at[row, column], right.at[row, column]
        if pd.isna(a) and pd.isna(b):
            continue
        if pd.api.types.is_number(a) and pd.api.types.is_number(b):
            equal = math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-9)
        else:
            equal = str(a).strip() == str(b).strip()
        if not equal:
            differences.append((row + 2, column, a, b))
            if len(differences) == 5:
                break
    if len(differences) == 5:
        break
assert not differences, differences
print('0 cell differences')
'@ | python -
```

Expected: `0 cell differences`.

- [ ] **Step 6: Rebuild and QA presentation/documents one final time**

```powershell
python sunum/kaynak/build_deck.py
python -m pytest sunum/kaynak/test_build_deck.py sunum/kaynak/test_document_sources.py -q
python sunum/kaynak/qa_deck.py --output-dir "$env:TEMP\buke-deck-final-qa"
python sunum/kaynak/build_docs.py
```

Expected: 14 main slides, zero automated QA errors, and visually approved DOCX renders from Task 7.

- [ ] **Step 7: Build the final archive after removing the development output from release consideration**

The builder excludes `out/` by allowlist and does not delete the evidence workbook:

```powershell
Set-Location final-teslim
python tools/build_release.py
Set-Location ..
```

Expected: `Buke_997307_Final_Teslim.zip` exists at repository root and is below 10,000,000 bytes.

- [ ] **Step 8: Extract two clean copies and run fallback and env modes from ZIP root**

```powershell
$fallbackRoot = Join-Path $env:TEMP ('buke-fallback-' + [guid]::NewGuid().ToString('N'))
$envRoot = Join-Path $env:TEMP ('buke-env-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fallbackRoot,$envRoot | Out-Null
Expand-Archive -LiteralPath 'Buke_997307_Final_Teslim.zip' -DestinationPath $fallbackRoot
Expand-Archive -LiteralPath 'Buke_997307_Final_Teslim.zip' -DestinationPath $envRoot

Push-Location $fallbackRoot
Remove-Item Env:TEKNOFEST_INPUT_FILE -ErrorAction SilentlyContinue
& $venvPython main.py
Pop-Location

$env:TEKNOFEST_INPUT_FILE = (Resolve-Path -LiteralPath (Join-Path $envRoot 'data\one_week_backtest.xlsx')).Path
Push-Location $envRoot
& $venvPython main.py
Pop-Location
Remove-Item Env:TEKNOFEST_INPUT_FILE -ErrorAction SilentlyContinue

$fallbackPlan = Join-Path $fallbackRoot 'out\Tasima-plani.xlsx'
$fallbackInput = Join-Path $fallbackRoot 'data\one_week_backtest.xlsx'
$envPlan = Join-Path $envRoot 'out\Tasima-plani.xlsx'
$envInput = Join-Path $envRoot 'data\one_week_backtest.xlsx'
& $venvPython final-teslim/tools/verify_output.py --plan $fallbackPlan --input $fallbackInput
& $venvPython final-teslim/tools/verify_output.py --plan $envPlan --input $envInput
```

Expected: both clean archive-root runs return 0 and both referee checks report 0 violations and 0 cost difference.

- [ ] **Step 9: Audit archive contents, size, placeholders, and hash**

```powershell
$zip = Get-Item -LiteralPath 'Buke_997307_Final_Teslim.zip'
if ($zip.Length -ge 10000000) { throw "ZIP too large: $($zip.Length) bytes" }
$names = tar -tf $zip.FullName
if ($names -notcontains 'main.py') { throw 'main.py missing at ZIP root' }
if ($names -notcontains 'teknofest_manifest.json') { throw 'manifest missing at ZIP root' }
if ($names | Where-Object { $_ -match '^(final-teslim/|out/|tests/|tools/|sunum/)|(^|/)run\.py$|__pycache__|\.pytest_cache' }) {
    throw 'Forbidden release entry found'
}
Get-FileHash -Algorithm SHA256 $zip.FullName
```

Extracted text scan:

```powershell
$auditRoot = Join-Path $env:TEMP ('buke-audit-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $auditRoot | Out-Null
Expand-Archive -LiteralPath 'Buke_997307_Final_Teslim.zip' -DestinationPath $auditRoot
rg -n "BASVURU_NUMARANIZI_YAZIN|C:/Users/darkb|C:\\Users\\darkb|AppData/Local/Temp/claude" $auditRoot
```

Expected: `rg` finds nothing; record exact byte size and SHA-256.

- [ ] **Step 10: Write and commit the verification report**

Create `docs/release/2026-08-21-buke-997307-verification.md` with the actual:

- commit SHA;
- Python/pandas/openpyxl versions;
- final pytest count and elapsed time;
- development and both extracted-ZIP run times;
- input/output row and column counts;
- total cost, violation count, and declared/referee difference;
- reference workbook and final ZIP SHA-256 values;
- exact ZIP byte size and root entry list;
- presentation main-slide count and QA result;
- DOCX page counts and visual QA result;
- explicit instruction: upload only `Buke_997307_Final_Teslim.zip` to the final code-package field.

```powershell
git add docs/release/2026-08-21-buke-997307-verification.md
git commit -m "docs: record final Buke release verification"
```

- [ ] **Step 11: Run final repository and artifact checks**

```powershell
git status --short
git log -8 --oneline
Get-Item 'Buke_997307_Final_Teslim.zip' | Select-Object FullName,Length,LastWriteTime
Get-FileHash -Algorithm SHA256 'Buke_997307_Final_Teslim.zip'
```

Expected: only the intentionally ignored ZIP remains outside Git status; all implementation and verification documents are committed.
