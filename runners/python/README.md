# Python Runner

The Python runner lane will be the first concrete implementation because the GTM Agent showcase already has a Python runtime and question-bank harness.

Planned steps:

1. Load `scenarios/gtm-agent/questions/gtm-490-question-bank.json`.
2. Execute each question against a selected implementation lane.
3. Record raw traces separately from summarized metrics.
4. Emit `runners/report-schema.json` compatible reports.
5. Keep provider/model usage metadata explicit enough to recompute cost.

The first concrete lane should be `anip`, using the known-good GTM Agent ANIP service stack as the reference baseline.
