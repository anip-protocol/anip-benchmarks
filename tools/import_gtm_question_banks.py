#!/usr/bin/env python3
"""Import the GTM Agent 350+140 question banks from an ANIP checkout.

This script intentionally copies source question-bank fixtures, not historical run
outputs. Reports generated from benchmark runs should live under reports/.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


ACTOR_PREFIX_RE = re.compile(r"^\[(?P<actor>[a-z0-9_]+)\]\s*(?P<question>.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class NormalizedQuestion:
    id: str
    bank: str
    phase: int
    source_id: str
    category: str
    question: str
    actor_id: str
    expected_outcome: str
    expected_capability: str | None = None
    expected_service: str | None = None
    notes: str | None = None


def _git_commit(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    except Exception:
        return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _parse_actor(question: str, default_actor_id: str = "sales_leader") -> tuple[str, str]:
    match = ACTOR_PREFIX_RE.match(question.strip())
    if not match:
        return default_actor_id, question.strip()
    return match.group("actor").strip(), match.group("question").strip()


def _expected_from(value: Any) -> tuple[str, str | None, str | None]:
    if isinstance(value, dict):
        return (
            str(value.get("outcome") or "unspecified"),
            str(value.get("capability")) if value.get("capability") else None,
            str(value.get("service")) if value.get("service") else None,
        )
    return str(value or "unspecified"), None, None


def _normalize_core(phase: int, payload: dict[str, Any]) -> list[NormalizedQuestion]:
    items: list[NormalizedQuestion] = []
    for entry in payload.get("entries", []):
        actor_id, question = _parse_actor(str(entry.get("question") or ""))
        expected_outcome, expected_capability, expected_service = _expected_from(entry.get("expected_outcome"))
        source_id = str(entry.get("id") or "")
        items.append(
            NormalizedQuestion(
                id=f"core-p{phase}-{source_id}",
                bank="core-350",
                phase=phase,
                source_id=source_id,
                category=str(entry.get("category") or "unspecified"),
                question=question,
                actor_id=actor_id,
                expected_outcome=expected_outcome,
                expected_capability=expected_capability,
                expected_service=expected_service,
                notes=entry.get("notes"),
            )
        )
    return items


def _normalize_variation(phase: int, payload: dict[str, Any]) -> list[NormalizedQuestion]:
    items: list[NormalizedQuestion] = []
    for entry in payload.get("cases", []):
        actor_id = str(entry.get("actor_id") or "sales_leader")
        question = str(entry.get("question") or "").strip()
        expected_outcome, expected_capability, expected_service = _expected_from(entry.get("expected"))
        source_id = str(entry.get("id") or "")
        items.append(
            NormalizedQuestion(
                id=f"variation-p{phase}-{source_id}",
                bank="variation-140-v3",
                phase=phase,
                source_id=source_id,
                category=str(entry.get("category") or "unspecified"),
                question=question,
                actor_id=actor_id,
                expected_outcome=expected_outcome,
                expected_capability=expected_capability,
                expected_service=expected_service,
                notes=None,
            )
        )
    return items


def import_banks(anip_root: Path, repo_root: Path) -> dict[str, Any]:
    source_core = anip_root / "docs" / "examples" / "gtm-showcase" / "question-banks"
    source_variations = anip_root / "docs" / "examples" / "gtm-showcase" / "variation-question-banks-v3"
    if not source_core.exists():
        raise FileNotFoundError(f"Missing core question banks: {source_core}")
    if not source_variations.exists():
        raise FileNotFoundError(f"Missing variation question banks: {source_variations}")

    questions_dir = repo_root / "scenarios" / "gtm-agent" / "questions"
    core_dir = questions_dir / "core-350"
    variation_dir = questions_dir / "variation-140-v3"
    core_dir.mkdir(parents=True, exist_ok=True)
    variation_dir.mkdir(parents=True, exist_ok=True)

    normalized: list[NormalizedQuestion] = []
    copied: list[dict[str, Any]] = []

    for phase in range(1, 8):
        source_path = source_core / f"phase{phase}-question-bank.json"
        target_path = core_dir / source_path.name
        shutil.copyfile(source_path, target_path)
        payload = _read_json(source_path)
        normalized.extend(_normalize_core(phase, payload))
        copied.append({"bank": "core-350", "phase": phase, "source": str(source_path), "target": str(target_path.relative_to(repo_root)), "count": len(payload.get("entries", []))})

    for phase in range(1, 8):
        source_path = source_variations / f"phase{phase}-variation-bank-20.json"
        target_path = variation_dir / source_path.name
        shutil.copyfile(source_path, target_path)
        payload = _read_json(source_path)
        normalized.extend(_normalize_variation(phase, payload))
        copied.append({"bank": "variation-140-v3", "phase": phase, "source": str(source_path), "target": str(target_path.relative_to(repo_root)), "count": len(payload.get("cases", []))})

    core_count = sum(1 for item in normalized if item.bank == "core-350")
    variation_count = sum(1 for item in normalized if item.bank == "variation-140-v3")
    if core_count != 350:
        raise ValueError(f"Expected 350 core questions, got {core_count}")
    if variation_count != 140:
        raise ValueError(f"Expected 140 variation questions, got {variation_count}")

    manifest = {
        "benchmark": "gtm-agent-490",
        "schema_version": "anip-benchmarks/question-bank/v1",
        "source": {
            "anip_root": str(anip_root),
            "anip_commit": _git_commit(anip_root),
            "core_path": str(source_core),
            "variation_path": str(source_variations),
        },
        "counts": {
            "core_350": core_count,
            "variation_140_v3": variation_count,
            "total": len(normalized),
        },
        "files": copied,
    }
    _write_json(questions_dir / "question-bank-manifest.json", manifest)
    _write_json(
        questions_dir / "gtm-490-question-bank.json",
        {
            "benchmark": "gtm-agent-490",
            "schema_version": "anip-benchmarks/normalized-question-bank/v1",
            "manifest": "question-bank-manifest.json",
            "count": len(normalized),
            "questions": [asdict(item) for item in normalized],
        },
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anip-root", default="/Users/samirski/Development/ANIP")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()

    manifest = import_banks(Path(args.anip_root).resolve(), Path(args.repo_root).resolve())
    print(json.dumps(manifest["counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
