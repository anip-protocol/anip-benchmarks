# Benchmark Methodology

## Goal

Measure the practical differences between ANIP governed service contracts and common agent integration styles on the same task set.

The benchmark must be credible enough to support public claims about runtime behavior, including cost. That means every baseline must be implemented honestly and run against the same workload.

## Non-goals

- Do not benchmark only happy-path questions.
- Do not compare ANIP against intentionally weak baselines.
- Do not count prompt-only safety instructions as equivalent to provider-enforced execution policy.
- Do not publish cost claims without model, token, loop, and pricing metadata.

## Required lanes

### ANIP

The agent consumes governed ANIP capabilities. The service contract carries capability identity, input contracts, authority boundaries, side-effect posture, denial/recovery semantics, approval behavior, audit evidence, and verification metadata.

### MCP

The agent consumes MCP-style tools with tool descriptions and annotations where applicable. Provider-side tool execution should be realistic, but the baseline should not silently add ANIP-style contract enforcement unless it is represented explicitly in the MCP implementation.

### Raw tools

The agent receives direct API/tool access with ordinary schemas and documentation.

### Skills/recipes/workflows

The agent receives consumer-side instructions that explain tool order, safety rules, approval behavior, and recovery policy. This lane measures how much behavior can be moved into prompts or local workflow logic rather than provider-owned contracts.

## Run protocol

For each lane:

1. Use the same question bank.
2. Use the same dataset and initial backend state.
3. Use the same model family where possible.
4. Record every model call and every tool/service invocation.
5. Record structured outcome classification for every question.
6. Persist raw traces separately from summarized reports.
7. Re-run failed cases with trace capture before changing implementation code.

## Reproducibility metadata

Each run report must include:

- git commit of this benchmark repo
- ANIP package version, if applicable
- generated service version or package ID
- model name
- model provider
- pricing table version/date
- environment variables required, with secrets redacted
- dataset version
- question bank version
- runner version
