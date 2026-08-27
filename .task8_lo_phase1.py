import argparse
import json
import os
import subprocess
from pathlib import Path

SOFFICE = Path(r"C:\Users\darkb\AppData\Local\Temp\buke-lo-portable-a61d7017c22c45f994a213b2e23ba747\portable\program\soffice.exe")
DOCS_DIR = Path(r"C:\Users\darkb\Desktop\hb-final\.worktrees\buke-final-hardening\sunum\dokumanlar")
DOCS = sorted(DOCS_DIR.glob("*.docx"))


def convert(root: Path, index: int) -> None:
    document = DOCS[index]
    out_dir = root / "pdf"
    profile = root / "profiles" / f"profile-{index:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    profile.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    command = [str(SOFFICE), f"-env:UserInstallation=file:///{profile.as_posix()}", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(document)]
    result = subprocess.run(command, cwd=SOFFICE.parent, env=env, text=True, capture_output=True, timeout=300)
    pdf = out_dir / f"{document.stem}.pdf"
    record = {"docx": str(document), "docx_bytes": document.stat().st_size, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "pdf": str(pdf), "pdf_bytes": pdf.stat().st_size if pdf.exists() else 0}
    records_path = root / "conversion-records.json"
    records = json.loads(records_path.read_text(encoding="utf-8")) if records_path.exists() else []
    records = [item for item in records if item["docx"] != str(document)] + [record]
    records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    if result.returncode != 0 or not pdf.exists() or pdf.stat().st_size <= 0:
        raise SystemExit(1)


def render(root: Path) -> None:
    import fitz
    records = json.loads((root / "conversion-records.json").read_text(encoding="utf-8"))
    if len(records) != len(DOCS):
        raise SystemExit(f"expected {len(DOCS)} conversion records, found {len(records)}")
    rendered = []
    for record in sorted(records, key=lambda item: item["docx"]):
        pdf = Path(record["pdf"])
        png_dir = root / "png" / pdf.stem
        png_dir.mkdir(parents=True, exist_ok=True)
        document = fitz.open(pdf)
        paths = []
        for number, page in enumerate(document, start=1):
            png = png_dir / f"page-{number:02d}.png"
            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(png)
            paths.append(str(png))
        rendered.append({"docx": record["docx"], "pdf": str(pdf), "pages": len(document), "pngs": paths})
        document.close()
    (root / "render-records.json").write_text(json.dumps(rendered, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pymupdf": fitz.version, "rendered": rendered}, ensure_ascii=False))


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--index", type=int)
parser.add_argument("--render", action="store_true")
args = parser.parse_args()
if args.render == (args.index is not None):
    raise SystemExit("select exactly one of --index or --render")
if args.index is not None:
    if not 0 <= args.index < len(DOCS):
        raise SystemExit(f"index must be in [0, {len(DOCS)})")
    convert(args.root, args.index)
else:
    render(args.root)
