import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

sys.stdout.reconfigure(encoding="utf-8")
archive_path = Path(sys.argv[1])
required = {
    "main.py", "teknofest_manifest.json", "requirements.txt", "README.md", "DEGISIKLIKLER.md",
    "data/one_week_backtest.xlsx",
    "src/__init__.py", "src/candidates.py", "src/chain.py", "src/contract.py", "src/data.py", "src/evaluation.py", "src/export.py", "src/ledger.py", "src/milkrun.py", "src/optimize.py", "src/pickup.py", "src/repair.py", "src/schedule.py", "src/schemas.py", "src/simulator.py", "src/timeutil.py",
    "datas/Araç_Kapasite_Maliyet_Saat.xlsx", "datas/Ellecleme-kapasite.xlsx", "datas/Kiralık_Araclar.xlsx", "datas/sehirler_arasi_lojistik.xlsx", "datas/tir_kapasiteleri v2.xlsx",
}
forbidden_parts = {"final-teslim", "out", "tests", "tools", "sunum", "cache", "log", "logs", "tmp", "temp", "presentation", "presentations", "slides", "__pycache__", ".pytest_cache"}
forbidden_suffixes = {".zip", ".7z", ".rar", ".tar", ".tgz", ".gz", ".doc", ".docx", ".ppt", ".pptx", ".pdf"}
assert archive_path.stat().st_size < 10_000_000
with zipfile.ZipFile(archive_path) as archive:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    assert names == sorted(names), "entries not lexicographically sorted"
    assert len(names) == len(set(names)), "duplicate entry name"
    assert archive.testzip() is None, "CRC failure"
    for info in infos:
        name = info.orig_filename
        parts = name.split("/")
        assert name and "\\" not in name and "\x00" not in name
        assert not PurePosixPath(name).is_absolute() and not PureWindowsPath(name).drive
        assert all(part not in {"", ".", ".."} for part in parts)
        assert not info.is_dir() and not (info.flag_bits & 1), name
        mode = info.external_attr >> 16
        assert info.create_system == 3 and stat.S_IFMT(mode) == stat.S_IFREG, name
        lowered = {part.casefold() for part in parts}
        assert not (lowered & forbidden_parts), name
        assert PurePosixPath(name).suffix.casefold() not in forbidden_suffixes, name
        assert PurePosixPath(name).name != "run.py", name
    assert required <= set(names), sorted(required - set(names))
    manifest = json.loads(archive.read("teknofest_manifest.json").decode("utf-8"))
    assert manifest["takim_id"] == "997307"
    assert manifest["takim_adi"] == "buke"
    print(f"ZIP_BYTES={archive_path.stat().st_size}")
    print(f"SHA256={hashlib.sha256(archive_path.read_bytes()).hexdigest()}")
    print(f"ENTRY_COUNT={len(names)}")
    for name in names:
        print(f"ENTRY={name}")
    print("MANIFEST=997307/buke")
    print("AUDIT=PASS crc=clean sorted=1 unique=1 canonical=1 regular=1 encrypted=0 forbidden=0 required=1")
