# Dashboard prompt guide

Source: https://kontakt-law.web.app/dashboard

Captured 15 September 2026. GPT revision: `05687efc-add0-4aca-953f-ca02bb62dbe2`. Gemini prompts are intentionally excluded from this Codex plugin. Prompt wording was compared with the local registry by length and a 64-bit text fingerprint; the GPT grammar whitespace override was preserved.

These are static snapshots, not live synchronization. Legacy stages are inactive on the website. Use active prompts by task; do not load every file.

## Runtime adaptation

The website injects document context, selected-party data, retrieval evidence and JSON schemas at runtime. This skill supplies the equivalent evidence workflow and a readable response format. References to application JSON output apply when an actual schema is supplied; otherwise use the skill output guidance. These files do not provide Firebase, Qdrant, OCR, OnlyOffice, model routing or server validation. Never claim those services ran. Current user instructions and host requirements govern the requested scope.

## Stage index

| Stage | State | Prompt |
| --- | --- | --- |
| risk_review | Active: analysis | [GPT](prompts/gpt/risk_review.md) |
| risk_discovery | Inactive legacy | [GPT](prompts/gpt/risk_discovery.md) |
| risk_legacy | Inactive legacy | [GPT](prompts/gpt/risk_legacy.md) |
| grammar | Active: analysis | [GPT](prompts/gpt/grammar.md) |
| party_extraction | Active: analysis | [GPT](prompts/gpt/party_extraction.md) |
| party_validation | Inactive legacy | [GPT](prompts/gpt/party_validation.md) |
| ownership | Inactive legacy | [GPT](prompts/gpt/ownership.md) |
| general_ownership | Inactive legacy | [GPT](prompts/gpt/general_ownership.md) |
| evidence_repair | Inactive legacy | [GPT](prompts/gpt/evidence_repair.md) |
| enrichment | Inactive legacy | [GPT](prompts/gpt/enrichment.md) |
| document_facts | Inactive legacy | [GPT](prompts/gpt/document_facts.md) |
| reconciliation | Inactive legacy | [GPT](prompts/gpt/reconciliation.md) |
| chat | Active: on_demand | [GPT](prompts/gpt/chat.md) |
| query_condense | Active: on_demand | [GPT](prompts/gpt/query_condense.md) |
| summary | Active: on_demand | [GPT](prompts/gpt/summary.md) |
| explanation | Active: on_demand | [GPT](prompts/gpt/explanation.md) |
| rewrite | Active: on_demand | [GPT](prompts/gpt/rewrite.md) |
| edit_verification | Active: on_demand | [GPT](prompts/gpt/edit_verification.md) |
| web_research | Active: on_demand | [GPT](prompts/gpt/web_research.md) |
| clause_drafting | Active: on_demand | [GPT](prompts/gpt/clause_drafting.md) |
| clause_verification | Active: on_demand | [GPT](prompts/gpt/clause_verification.md) |
