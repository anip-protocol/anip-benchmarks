# Cost Model

## Required inputs

Each benchmark run must record raw usage data:

- model name
- input tokens
- output tokens
- cached input tokens, if available
- reasoning tokens, if exposed by provider
- tool call count
- service invocation count
- total wall-clock latency

## Estimated cost

Estimated cost should be calculated from a versioned pricing table stored with the report.

A report must not say "ANIP is cheaper" unless it includes enough data for another person to recompute the estimate.

## Price table format

Use this shape in report metadata:

```json
{
  "provider": "openai",
  "pricing_effective_date": "YYYY-MM-DD",
  "models": {
    "model-name": {
      "input_per_1m": 0.0,
      "output_per_1m": 0.0,
      "cached_input_per_1m": 0.0
    }
  }
}
```

## Comparison rules

- Compare equivalent success bands first.
- Do not compare a successful ANIP run against a baseline run that failed many tasks without reporting the failure rate.
- Separate design-time generation cost from runtime execution cost.
- Report median and p95, not only averages.
