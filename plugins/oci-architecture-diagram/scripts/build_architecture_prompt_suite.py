#!/usr/bin/env python3
"""Write the deterministic 100-case OCI architecture prompt suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from architecture_prompt_cases import architecture_prompt_cases


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build examples/architecture-prompt-suite.json")
    parser.add_argument("--out", default=str(PLUGIN_ROOT / "examples" / "architecture-prompt-suite.json"))
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    cases = architecture_prompt_cases()
    output.write_text(json.dumps({"caseCount": len(cases), "cases": cases}, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} architecture prompt cases to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
