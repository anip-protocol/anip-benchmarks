# Runner Contract

Every benchmark lane must implement the same runner contract so reports are comparable.

## Inputs

- normalized question bank path
- lane name: `anip`, `mcp`, `raw-tools`, or `skills-recipes`
- implementation config path, optional
- model/provider config, optional
- output path

## Output

Every runner writes a JSON report compatible with `runners/report-schema.json`.

A report must include one entry per question, even if the runner fails before executing the full bank. Failed or skipped questions should use explicit outcomes such as `not_run`, `runtime_error`, or `loop_exhausted`.

## Trace discipline

Summaries are not enough. Real benchmark runs should also write raw traces containing:

- model requests and responses, with secrets redacted
- tool/service invocation requests and responses
- loop state transitions
- timing information
- token usage data when available
- failure classification inputs

Raw traces should live under a report-local `raw-traces/` directory, which is gitignored by default until we decide what can be published safely.

## Honesty rules

- Do not silently add ANIP-style contract enforcement to non-ANIP lanes.
- Do not compare costs without success and governance correctness rates.
- Do not remove difficult questions from one lane unless removed from all lanes.
- Do not tune prompts per failing question without documenting it as a benchmark revision.
