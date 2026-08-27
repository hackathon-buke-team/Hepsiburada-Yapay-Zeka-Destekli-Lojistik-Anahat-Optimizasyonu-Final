import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--cwd", type=Path, required=True)
parser.add_argument("--log-dir", type=Path, required=True)
args = parser.parse_args()
args.log_dir.mkdir(parents=True, exist_ok=True)
started = time.perf_counter()
with (args.log_dir / "stdout.log").open("w", encoding="utf-8") as stdout, (args.log_dir / "stderr.log").open("w", encoding="utf-8") as stderr:
    result = subprocess.run([sys.executable, "main.py"], cwd=args.cwd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, text=True)
elapsed = time.perf_counter() - started
(args.log_dir / "result.json").write_text(json.dumps({"returncode": result.returncode, "elapsed_seconds": elapsed}, indent=2), encoding="utf-8")
raise SystemExit(result.returncode)
