from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from runners.python.model_usage_proxy import ProxyConfig, build_server


class FakeOpenAIHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        payload = json.loads(body.decode("utf-8"))
        response = {
            "id": "chatcmpl-test",
            "model": payload.get("model", "test-model"),
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
                "prompt_tokens_details": {"cached_tokens": 3},
                "completion_tokens_details": {"reasoning_tokens": 2},
            },
        }
        raw = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("x-request-id", "req-test")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):  # noqa: A002
        return


class ModelUsageProxyTest(unittest.TestCase):
    def test_proxy_forwards_and_records_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            upstream = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAIHandler)
            upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
            upstream_thread.start()
            trace_path = Path(temp_dir) / "usage.jsonl"
            proxy = build_server(
                "127.0.0.1",
                0,
                ProxyConfig(
                    upstream_base_url=f"http://127.0.0.1:{upstream.server_port}/v1",
                    api_key="test-key",
                    trace_path=trace_path,
                    provider="fake-openai",
                    run_id="run-test",
                    lane="anip",
                    benchmark="gtm-agent-490",
                ),
            )
            proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
            proxy_thread.start()
            try:
                body = json.dumps({"model": "gpt-test", "messages": [], "metadata": {"question_id": "q1"}}).encode("utf-8")
                request = urllib.request.Request(
                    f"http://127.0.0.1:{proxy.server_port}/v1/chat/completions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["id"], "chatcmpl-test")
                rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
                self.assertEqual(len(rows), 1)
                row = rows[0]
                self.assertEqual(row["benchmark"], "gtm-agent-490")
                self.assertEqual(row["lane"], "anip")
                self.assertEqual(row["provider"], "fake-openai")
                self.assertEqual(row["model"], "gpt-test")
                self.assertEqual(row["status"], 200)
                self.assertEqual(row["input_tokens"], 12)
                self.assertEqual(row["output_tokens"], 5)
                self.assertEqual(row["cached_input_tokens"], 3)
                self.assertEqual(row["reasoning_tokens"], 2)
                self.assertEqual(row["total_tokens"], 17)
                self.assertEqual(row["request_id"], "req-test")
                self.assertEqual(row["question_id"], "q1")
            finally:
                proxy.shutdown()
                proxy.server_close()
                upstream.shutdown()
                upstream.server_close()


if __name__ == "__main__":
    unittest.main()
