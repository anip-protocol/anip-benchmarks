#!/usr/bin/env python3
"""Run the GTM ANIP lane through the release-gate regression harness.

This runner intentionally reuses the ANIP showcase regression harness for task
correctness. It then converts those harness reports plus optional model-usage
proxy JSONL traces into the shared benchmark report envelope.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


BENCHMARK = "gtm-agent-490"
LANE = "anip"


def _git_commit(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    except Exception:
        return "unknown"


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    stdout = completed.stdout.strip()
    parsed: dict[str, Any] = {}
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = {"stdout": stdout}
    parsed["returncode"] = completed.returncode
    parsed["stderr"] = completed.stderr.strip()
    return parsed


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _trace_totals(trace_path: Path | None) -> dict[str, int]:
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "model_call_count": 0,
    }
    if not trace_path or not trace_path.exists():
        return totals
    for line in trace_path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        totals["model_call_count"] += 1
        for key in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens", "total_tokens"):
            totals[key] += int(record.get(key) or 0)
    return totals


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((percentile / 100.0) * (len(ordered) - 1))))
    return ordered[index]


def _expected_from_turns(case: dict[str, Any]) -> Any:
    turns = case.get("turns") or []
    if turns:
        return turns[-1].get("expected", {}).get("outcome")
    return case.get("expected", {}).get("outcome")


def _actual_from_turns(case: dict[str, Any]) -> Any:
    turns = case.get("turns") or []
    if turns:
        return turns[-1].get("actual", {}).get("outcome")
    return case.get("actual", {}).get("outcome")


def _loops_from_turns(case: dict[str, Any]) -> int:
    loops = 0
    for turn in case.get("turns") or []:
        counts = turn.get("actual", {}).get("loop_counts") or {}
        loops += int(counts.get("total_loops") or 0)
    return loops


def _case_to_question(case: dict[str, Any], suite: str) -> dict[str, Any]:
    duration_ms = int(float(case.get("duration_seconds") or 0.0) * 1000)
    return {
        "id": str(case.get("id") or ""),
        "question": str(case.get("question") or ""),
        "actor_id": str(case.get("response", {}).get("actor_id") or ""),
        "outcome": "passed" if case.get("pass") else "failed",
        "actual_outcome": _actual_from_turns(case),
        "expected_outcome": _expected_from_turns(case),
        "loops": _loops_from_turns(case),
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "latency_ms": duration_ms,
        "failure_class": "" if case.get("pass") else "regression_harness_failure",
        "trace_ref": suite,
        "category": case.get("category"),
    }


def _collect_harness_reports(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for item in results:
        json_path = item.get("json")
        if json_path:
            reports.append(_load_json(Path(json_path)))
    return reports


def _summary(questions: list[dict[str, Any]], trace_totals: dict[str, int]) -> dict[str, Any]:
    count = len(questions)
    passed = sum(1 for item in questions if item.get("outcome") == "passed")
    loops = [float(item.get("loops") or 0) for item in questions]
    latencies = [float(item.get("latency_ms") or 0) for item in questions]
    success_rate = passed / count if count else 0.0
    return {
        "question_count": count,
        "success_rate": success_rate,
        "governance_correctness_rate": success_rate,
        "median_loops": statistics.median(loops) if loops else 0,
        "p95_loops": _percentile(loops, 95),
        "total_estimated_cost_usd": 0.0,
        "median_latency_ms": statistics.median(latencies) if latencies else 0,
        "p95_latency_ms": _percentile(latencies, 95),
        "model_call_count": trace_totals["model_call_count"],
        "input_tokens": trace_totals["input_tokens"],
        "output_tokens": trace_totals["output_tokens"],
        "cached_input_tokens": trace_totals["cached_input_tokens"],
        "reasoning_tokens": trace_totals["reasoning_tokens"],
        "total_tokens": trace_totals["total_tokens"],
    }


def _run_core(anip_root: Path, runtime_url: str, output_dir: Path, phases: list[int]) -> list[dict[str, Any]]:
    runner = anip_root / "examples" / "showcase" / "gtm" / "scripts" / "generated_stack" / "run_question_bank.py"
    command = [sys.executable, str(runner), "--runtime-url", runtime_url, "--output-dir", str(output_dir)]
    if phases == list(range(1, 8)):
        command.append("--all")
    else:
        for phase in phases:
            command.extend(["--phase", str(phase)])
    payload = _run(command, cwd=anip_root)
    if payload["returncode"] != 0:
        raise RuntimeError(f"Core question bank failed: {json.dumps(payload, indent=2)}")
    return list(payload.get("runs") or [])


def _run_variations(anip_root: Path, runtime_url: str, output_dir: Path, phases: list[int]) -> list[dict[str, Any]]:
    runner = anip_root / "examples" / "showcase" / "gtm" / "scripts" / "generated_stack" / "run_phase1_regression.py"
    bank_dir = anip_root / "docs" / "examples" / "gtm-showcase" / "variation-question-banks-v3"
    results: list[dict[str, Any]] = []
    for phase in phases:
        cases = bank_dir / f"phase{phase}-variation-bank-20.json"
        payload = _run(
            [sys.executable, str(runner), "--runtime-url", runtime_url, "--cases", str(cases), "--output-dir", str(output_dir)],
            cwd=anip_root,
        )
        payload["phase"] = phase
        payload["suite"] = f"gtm_phase{phase}_variation_bank_20_v3"
        if payload["returncode"] != 0:
            raise RuntimeError(f"Variation question bank phase {phase} failed: {json.dumps(payload, indent=2)}")
        results.append(payload)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anip-root", required=True, help="Path to a checked-out ANIP repo.")
    parser.add_argument("--runtime-url", required=True, help="Running GTM agent runtime URL, e.g. http://127.0.0.1:9304.")
    parser.add_argument("--output", required=True, help="Benchmark report JSON path relative to this repo or absolute.")
    parser.add_argument("--trace-path", help="Optional model-usage proxy JSONL trace path.")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--run-id", default=f"gtm-anip-{uuid.uuid4().hex[:12]}")
    parser.add_argument("--core", action="store_true", help="Run the 350 core bank.")
    parser.add_argument("--variations", action="store_true", help="Run the 140 variation bank.")
    parser.add_argument("--phase", type=int, action="append", dest="phases", help="Restrict to one or more phases.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    anip_root = Path(args.anip_root).resolve()
    phases = args.phases or list(range(1, 8))
    run_core = args.core or not args.variations
    run_variations = args.variations or not args.core
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    trace_path = Path(args.trace_path).resolve() if args.trace_path else None

    started_at = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with tempfile.TemporaryDirectory(prefix="anip-gtm-benchmark-") as temp_name:
        harness_dir = Path(temp_name) / "harness"
        harness_results: list[dict[str, Any]] = []
        if run_core:
            harness_results.extend(_run_core(anip_root, args.runtime_url, harness_dir / "core", phases))
        if run_variations:
            harness_results.extend(_run_variations(anip_root, args.runtime_url, harness_dir / "variations", phases))

        reports = _collect_harness_reports(harness_results)
        questions: list[dict[str, Any]] = []
        for report in reports:
            suite = str(report.get("suite") or "unknown")
            questions.extend(_case_to_question(case, suite) for case in report.get("cases") or [])

    trace_totals = _trace_totals(trace_path)
    report = {
        "benchmark": BENCHMARK,
        "lane": LANE,
        "run": {
            "id": args.run_id,
            "started_at": started_at,
            "model": args.model,
            "provider": args.provider,
            "repo_commit": _git_commit(repo_root),
            "anip_repo_commit": _git_commit(anip_root),
            "dataset_version": "gtm-showcase-question-banks",
            "question_bank_version": "core-350+variation-v3-140",
            "runtime_url": args.runtime_url,
            "trace_path": str(trace_path) if trace_path else "",
        },
        "summary": _summary(questions, trace_totals),
        "questions": questions,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "questions": len(questions), "passed": sum(1 for item in questions if item["outcome"] == "passed")}, indent=2, sort_keys=True))
    return 0 if all(item.get("outcome") == "passed" for item in questions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
