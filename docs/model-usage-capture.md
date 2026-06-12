# Model Usage Capture

Cost claims require measured model usage, not estimates from prompt size.

## Required data per model call

- provider
- model
- request timestamp
- response timestamp
- latency_ms
- input_tokens
- output_tokens
- cached_input_tokens, if available
- reasoning_tokens, if available
- request_id, if available
- benchmark question id
- lane
- run id

## Capture options

### Preferred: OpenAI-compatible proxy

Run each lane against a local proxy that forwards chat/completions or responses requests to the provider and records usage metadata.

Advantages:

- comparable across lanes
- minimal changes to showcase/runtime code
- centralized redaction
- centralized cost calculation

### Acceptable: SDK wrapper

Wrap provider SDK calls inside each runner.

Disadvantage: implementation may diverge across lanes and languages.

### Not acceptable for published cost claims

- estimating token usage only from prompt character counts
- using prompt length without output usage
- reporting cost without model and pricing metadata

## Redaction

Raw traces must redact:

- API keys
- bearer tokens
- private service URLs if needed
- personally sensitive payload values if introduced later

The GTM benchmark currently uses synthetic showcase data, which makes trace publication easier, but the redaction path should still be explicit.
