# GTM Agent: ANIP Lane

This lane is the reference implementation for the GTM Agent benchmark.

It should use the known-good GTM Agent ANIP contract and generated service stack, then execute the same 490-question bank used by the other lanes.

## Intended execution path

1. Start the GTM Agent ANIP service stack.
2. Run `runners/python/run_benchmark.py --lane anip` with concrete ANIP execution enabled.
3. Capture model calls, ANIP discovery, token issuance, invocation payloads, outcomes, loop counts, usage, latency, and trace references.
4. Emit a report compatible with `runners/report-schema.json`.

## Current status

The common report envelope exists. Concrete ANIP service execution is the next implementation step.
