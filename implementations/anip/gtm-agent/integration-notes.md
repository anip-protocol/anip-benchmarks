# ANIP GTM Agent Integration Notes

## Existing reusable harness

The ANIP monorepo already contains a GTM question-bank harness:

- `examples/showcase/gtm/scripts/run_question_bank.py`
- `examples/showcase/gtm/scripts/generated_stack/run_question_bank.py`
- `examples/showcase/gtm/scripts/run_phase1_regression.py`

Those scripts execute question-bank cases against the GTM Agent runtime endpoint and validate expected outcomes. The benchmark repo should reuse this behavior rather than invent a separate scoring path.

## Gap for cost benchmark credibility

The existing runtime/harness records loop counts and outcomes, but cost comparison needs more:

- model name
- provider
- input tokens
- output tokens
- cached input tokens, if available
- latency per model call
- number of model calls per question
- total estimated cost per question

For ANIP-vs-MCP-vs-skills comparisons, token/cost capture must be implemented at the benchmark runner or model proxy layer, not inferred from prompt lengths.

## Recommended first concrete ANIP lane

1. Start from the known-good GTM Agent ANIP stack.
2. Route model calls through a benchmark-controlled OpenAI-compatible proxy or wrapper.
3. Capture request/response usage and latency.
4. Run all 490 questions from `scenarios/gtm-agent/questions/gtm-490-question-bank.json`.
5. Convert the existing harness results into `runners/report-schema.json`.
6. Persist raw traces under a report-local `raw-traces/` directory.

## Why a proxy/wrapper is preferable

A benchmark proxy avoids modifying the showcase runtime differently for each lane. It also makes token/cost measurement comparable across ANIP, MCP, raw-tools, and skills/recipes lanes.
