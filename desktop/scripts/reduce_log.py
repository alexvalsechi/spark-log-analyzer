#!/usr/bin/env python3
"""
Desktop reducer bridge.

Reads a ZIP file path and outputs a reduced report as text.
This script reuses backend LogReducer to keep parity with server behavior.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.services.log_reducer import LogReducer


def main() -> int:
    parser = argparse.ArgumentParser(description="Reduce Spark ZIP locally for desktop flow")
    parser.add_argument("--zip", required=True, help="Path to ZIP file")
    parser.add_argument("--out", required=True, help="Path to output reduced report")
    parser.add_argument("--compact", action="store_true", help="Use compact reducer output")
    args = parser.parse_args()

    zip_path = Path(args.zip)
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")

    reducer = LogReducer(output_format="md", compact=args.compact)
    summary, reduced_report = reducer.reduce(zip_path.read_bytes())

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(reduced_report, encoding="utf-8")

    # Keep this lightweight and machine-readable for Electron side.
    print(f"summary_app={summary.app_name}")
    print(f"summary_tasks={summary.num_tasks}")
    print(f"reduced_chars={len(reduced_report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
