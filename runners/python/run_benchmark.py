#!/usr/bin/env python3
"""Run an ANIP benchmark lane and emit the common report envelope.

Current implementation supports dry-run reports. Concrete lane executors should
plug into `execute_question` without changing the report schema.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any


VALID_LANES = {"anip", "mcp", "raw-tools", "skills-recipes"}


def _git_commit(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    except Exception:
        return "unknown"


def _load_question_bank(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise ValueError(f"{path} does not contain a questions list")
    return payload


def _not_run_question(question: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(question["id"]),
        "question": str(question["question"]),
        "actor_id": str(question.get("actor_id") or "sales_leader"),
        "outcome": "not_run",
        "loops": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "latency_ms": 0,
        "failure_class": "dry_run",
        "trace_ref": "",
        "expected_outcome": question.get("expected_outcome"),
        "expected_capability": question.get("expected_capability"),
        "bank": question.get("bank"),
        "phase": question.get("phase"),
    }


def _summary(question_results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(question_results)
    return {
        "question_count": count,
        "success_rate": 0.0,
        "governance_correctness_rate": 0.0,
        "median_loops": 0,
        "p95_loops": 0,
        "total_estimated_cost_usd": 0.0,
        "median_latency_ms": 0,
        "p95_latency_ms": 0,
    }


def build_dry_run_report(repo_root: Path, lane: str, question_bank: Path, model: str, provider: str) -> dict[str, Any]:
    payload = _load_question_bank(question_bank)
    question_results = [_not_run_question(item) for item in payload["questions"]]
    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "benchmark": str(payload.get("benchmark") or "unknown"),
        "lane": lane,
        "run": {
            "id": f"dry-run-{uuid.uuid4().hex[:12]}",
            "started_at": now,
            "model": model,
            "provider": provider,
            "repo_commit": _git_commit(repo_root),
            "dataset_version": "not-run",
            "question_bank_version": str(payload.get("schema_version") or "unknown"),
        },
        "summary": _summary(question_results),
        "questions": question_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True, choices=sorted(VALID_LANES))
    parser.add_argument("--question-bank", default="scenarios/gtm-agent/questions/gtm-490-question-bank.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="not-run")
    parser.add_argument("--provider", default="not-run")
    parser.add_argument("--dry-run", action="store_true", help="Emit a schema-shaped report without invoking a model or services.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    question_bank = (repo_root / args.question_bank).resolve()
    output_path = (repo_root / args.output).resolve()

    if not args.dry_run:
        raise SystemExit("Only --dry-run is implemented so far; concrete lane execution is intentionally pending.")

    report = build_dry_run_report(repo_root, args.lane, question_bank, args.model, args.provider)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "questions": len(report["questions"]), "lane": args.lane}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
