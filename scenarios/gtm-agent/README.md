# GTM Agent Scenario

The GTM Agent benchmark is the first public benchmark target.

It should compare the same GTM task bank across ANIP, MCP-style tools, raw tools, and skills/recipes/workflows.

## Workload

- 490 natural-language questions
- bounded analytics
- actor-aware masking and restriction
- clarification behavior
- denial behavior
- approval-required behavior
- composed service workflows

## Source of truth

The ANIP lane should use the published GTM Agent package/contract that was validated across the 490-question bank.

The non-ANIP lanes should use equivalent backend capabilities and data, but without silently importing ANIP's service-owned governance contract.
