#!/usr/bin/env python3
"""OpenAI-compatible model usage capture proxy.

The proxy forwards requests to an upstream OpenAI-compatible API and records one
JSONL trace per model call. It is intentionally dependency-free so benchmark
lanes can use it without extra service framework setup.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SUPPORTED_PATH_SUFFIXES = ("/chat/completions", "/responses")
REDACTED_HEADERS = {"authorization", "proxy-authorization", "x-api-key", "api-key"}


@dataclass(frozen=True)
class ProxyConfig:
    upstream_base_url: str
    api_key: str | None
    trace_path: Path
    provider: str
    run_id: str
    lane: str
    benchmark: str


@dataclass(frozen=True)
class UsageRecord:
    benchmark: str
    lane: str
    run_id: str
    provider: str
    model: str | None
    path: str
    status: int
    started_at: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    total_tokens: int
    request_id: str | None
    question_id: str | None
    error_type: str | None


def _utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _join_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    if path.startswith("/v1/") and base.endswith("/v1"):
        path = path[3:]
    return f"{base}{path}"


def _safe_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def _header_dict(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in handler.headers.items():
        lower = key.lower()
        if lower in {"host", "content-length", "connection", "accept-encoding"}:
            continue
        if lower in REDACTED_HEADERS:
            continue
        headers[key] = value
    return headers


def _extract_usage(payload: Any) -> dict[str, int]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
        }

    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)

    cached_input_tokens = 0
    prompt_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details")
    if isinstance(prompt_details, dict):
        cached_input_tokens = int(prompt_details.get("cached_tokens") or 0)

    reasoning_tokens = 0
    completion_details = usage.get("completion_tokens_details") or usage.get("output_tokens_details")
    if isinstance(completion_details, dict):
        reasoning_tokens = int(completion_details.get("reasoning_tokens") or 0)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }


def _extract_model(request_payload: Any, response_payload: Any) -> str | None:
    if isinstance(response_payload, dict) and response_payload.get("model"):
        return str(response_payload["model"])
    if isinstance(request_payload, dict) and request_payload.get("model"):
        return str(request_payload["model"])
    return None


def _extract_request_id(response_headers: Any, payload: Any) -> str | None:
    for key in ("x-request-id", "openai-request-id", "request-id"):
        value = response_headers.get(key) if response_headers else None
        if value:
            return str(value)
    if isinstance(payload, dict):
        for key in ("id", "request_id"):
            if payload.get(key):
                return str(payload[key])
    return None


def _extract_question_id(headers: Any, request_payload: Any) -> str | None:
    value = headers.get("x-anip-benchmark-question-id") if headers else None
    if value:
        return str(value)
    if isinstance(request_payload, dict):
        metadata = request_payload.get("metadata")
        if isinstance(metadata, dict):
            for key in ("question_id", "benchmark_question_id"):
                if metadata.get(key):
                    return str(metadata[key])
    return None


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _is_supported_path(path: str) -> bool:
    clean_path = urlsplit(path).path
    return any(clean_path.endswith(suffix) for suffix in SUPPORTED_PATH_SUFFIXES)


class UsageProxyHandler(BaseHTTPRequestHandler):
    server_version = "AnipBenchmarkUsageProxy/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/healthz":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if not _is_supported_path(self.path):
            self._send_json(404, {"error": "unsupported_path", "path": self.path})
            return

        config: ProxyConfig = self.server.config  # type: ignore[attr-defined]
        started = time.perf_counter()
        started_at = _utc_now()
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""
        request_payload = _safe_json(body)
        upstream_url = _join_url(config.upstream_base_url, self.path)
        headers = _header_dict(self)
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        if body and "Content-Type" not in headers and "content-type" not in {key.lower() for key in headers}:
            headers["Content-Type"] = "application/json"

        status = 502
        response_body = b""
        response_headers: dict[str, str] = {}
        error_type: str | None = None

        try:
            request = urllib.request.Request(upstream_url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=120) as response:
                status = response.status
                response_body = response.read()
                response_headers = {key.lower(): value for key, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_body = exc.read()
            response_headers = {key.lower(): value for key, value in exc.headers.items()}
            error_type = "upstream_http_error"
        except urllib.error.URLError as exc:
            status = 502
            response_body = json.dumps({"error": {"type": "upstream_unreachable", "message": str(exc.reason)}}).encode("utf-8")
            error_type = "upstream_unreachable"
        except Exception as exc:  # defensive boundary for benchmark infra
            status = 502
            response_body = json.dumps({"error": {"type": "proxy_error", "message": exc.__class__.__name__}}).encode("utf-8")
            error_type = "proxy_error"

        response_payload = _safe_json(response_body)
        usage = _extract_usage(response_payload)
        latency_ms = int((time.perf_counter() - started) * 1000)
        record = UsageRecord(
            benchmark=config.benchmark,
            lane=config.lane,
            run_id=config.run_id,
            provider=config.provider,
            model=_extract_model(request_payload, response_payload),
            path=urlsplit(self.path).path,
            status=status,
            started_at=started_at,
            latency_ms=latency_ms,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_input_tokens=usage["cached_input_tokens"],
            reasoning_tokens=usage["reasoning_tokens"],
            total_tokens=usage["total_tokens"],
            request_id=_extract_request_id(response_headers, response_payload),
            question_id=_extract_question_id(self.headers, request_payload),
            error_type=error_type,
        )
        _append_jsonl(config.trace_path, asdict(record))
        self._send_bytes(status, response_body, response_headers.get("content-type", "application/json"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        if os.getenv("ANIP_BENCHMARK_PROXY_DEBUG"):
            super().log_message(format, *args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        self._send_bytes(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(host: str, port: int, config: ProxyConfig) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), UsageProxyHandler)
    server.config = config  # type: ignore[attr-defined]
    return server


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--upstream-base-url", default=os.getenv("ANIP_BENCHMARK_UPSTREAM_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--trace-path", default=os.getenv("ANIP_BENCHMARK_TRACE_PATH", "reports/local-runs/model-usage.jsonl"))
    parser.add_argument("--provider", default=os.getenv("ANIP_BENCHMARK_PROVIDER", "openai"))
    parser.add_argument("--run-id", default=os.getenv("ANIP_BENCHMARK_RUN_ID", "manual"))
    parser.add_argument("--lane", default=os.getenv("ANIP_BENCHMARK_LANE", "anip"))
    parser.add_argument("--benchmark", default=os.getenv("ANIP_BENCHMARK_NAME", "gtm-agent-490"))
    args = parser.parse_args()

    config = ProxyConfig(
        upstream_base_url=args.upstream_base_url,
        api_key=args.api_key,
        trace_path=Path(args.trace_path),
        provider=args.provider,
        run_id=args.run_id,
        lane=args.lane,
        benchmark=args.benchmark,
    )
    server = build_server(args.host, args.port, config)
    print(json.dumps({"listening": f"http://{args.host}:{args.port}", "trace_path": str(config.trace_path)}, sort_keys=True), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
