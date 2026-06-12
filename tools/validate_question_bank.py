#!/usr/bin/env python3
"""Validate normalized benchmark question-bank fixtures."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {"id", "bank", "phase", "source_id", "category", "question", "actor_id", "expected_outcome"}


def validate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise ValueError(f"{path} does not contain a questions list")
    ids = [str(item.get("id")) for item in questions if isinstance(item, dict)]
    duplicate_ids = sorted([item for item, count in Counter(ids).items() if count > 1])
    if duplicate_ids:
        raise ValueError(f"duplicate question ids: {duplicate_ids[:10]}")
    missing: list[str] = []
    for index, item in enumerate(questions):
        if not isinstance(item, dict):
            raise ValueError(f"question at index {index} is not an object")
        absent = sorted(field for field in REQUIRED_FIELDS if not item.get(field))
        if absent:
            missing.append(f"{item.get('id', index)} missing {', '.join(absent)}")
    if missing:
        raise ValueError("invalid questions:\n" + "\n".join(missing[:25]))
    by_bank = Counter(str(item["bank"]) for item in questions)
    by_phase = Counter(int(item["phase"]) for item in questions)
    if by_bank.get("core-350") != 350:
        raise ValueError(f"expected 350 core questions, got {by_bank.get('core-350')}")
    if by_bank.get("variation-140-v3") != 140:
        raise ValueError(f"expected 140 variation questions, got {by_bank.get('variation-140-v3')}")
    for phase in range(1, 8):
        if by_phase.get(phase) != 70:
            raise ValueError(f"phase {phase} expected 70 questions, got {by_phase.get(phase)}")
    return {
        "path": str(path),
        "count": len(questions),
        "by_bank": dict(sorted(by_bank.items())),
        "by_phase": {str(key): by_phase[key] for key in sorted(by_phase)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="scenarios/gtm-agent/questions/gtm-490-question-bank.json")
    args = parser.parse_args()
    result = validate(Path(args.path))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
