# GTM Agent Benchmark Plan

## Purpose

Use the GTM Agent workload to compare runtime behavior and cost across ANIP and non-ANIP agent integration patterns.

This benchmark is intentionally separate from the ANIP monorepo so public cost claims can point to an independently reviewable methodology and fixtures.

## Workload

The benchmark uses 490 questions:

- 350 core questions across seven GTM phases.
- 140 language and behavior variation questions.

The workload includes success, clarification, restriction, masking, denial, approval-required, and composed workflow paths.

## First implementation order

1. Import and freeze the 490-question fixture.
2. Implement the ANIP lane runner and reproduce the known-good ANIP behavior.
3. Implement the MCP lane with realistic tool descriptions and annotations.
4. Implement the skills/recipes lane with consumer-side guidance.
5. Implement the raw-tools lane if it adds useful contrast.
6. Publish a report only after all lanes produce comparable traces.

## Public-claim rule

Do not publish cost or model-efficiency claims until the benchmark report includes:

- exact model names
- exact token usage
- loop counts
- success rates
- governance correctness rates
- pricing table date
- raw traces or trace references
