# Dashboard prompt guide

Source: https://kontakt-law.web.app/dashboard

Captured 15 September 2026. GPT revision: 05687efc-add0-4aca-953f-ca02bb62dbe2. Gemini revision: bundled. The site selected Gemini at capture time. Both complete profiles are preserved. Prompt wording was compared with the local registry by length and a 64-bit text fingerprint; the one GPT grammar whitespace override was preserved.

These are static snapshots, not live synchronization. Legacy stages are inactive on the website. Use active prompts by task; do not load every file.

## Runtime adaptation

The website injects document context, selected-party data, retrieval evidence and JSON schemas at runtime. This skill supplies the equivalent evidence workflow and a readable response format. References to application JSON output apply when an actual schema is supplied; otherwise use the skill output guidance. These files do not provide Firebase, Qdrant, OCR, OnlyOffice, model routing or server validation. Never claim those services ran. Current user instructions and host requirements govern the requested scope.

## Stage index

| Stage | State | GPT | Gemini |
| --- | --- | --- | --- |
| risk_review | Active: analysis | [GPT](prompts/gpt/risk_review.md) | [Gemini](prompts/gemini/risk_review.md) |
| risk_discovery | Inactive legacy | [GPT](prompts/gpt/risk_discovery.md) | [Gemini](prompts/gemini/risk_discovery.md) |
| risk_legacy | Inactive legacy | [GPT](prompts/gpt/risk_legacy.md) | [Gemini](prompts/gemini/risk_legacy.md) |
| grammar | Active: analysis | [GPT](prompts/gpt/grammar.md) | [Gemini](prompts/gemini/grammar.md) |
| party_extraction | Active: analysis | [GPT](prompts/gpt/party_extraction.md) | [Gemini](prompts/gemini/party_extraction.md) |
| party_validation | Inactive legacy | [GPT](prompts/gpt/party_validation.md) | [Gemini](prompts/gemini/party_validation.md) |
| ownership | Inactive legacy | [GPT](prompts/gpt/ownership.md) | [Gemini](prompts/gemini/ownership.md) |
| general_ownership | Inactive legacy | [GPT](prompts/gpt/general_ownership.md) | [Gemini](prompts/gemini/general_ownership.md) |
| evidence_repair | Inactive legacy | [GPT](prompts/gpt/evidence_repair.md) | [Gemini](prompts/gemini/evidence_repair.md) |
| enrichment | Inactive legacy | [GPT](prompts/gpt/enrichment.md) | [Gemini](prompts/gemini/enrichment.md) |
| document_facts | Inactive legacy | [GPT](prompts/gpt/document_facts.md) | [Gemini](prompts/gemini/document_facts.md) |
| reconciliation | Inactive legacy | [GPT](prompts/gpt/reconciliation.md) | [Gemini](prompts/gemini/reconciliation.md) |
| chat | Active: on_demand | [GPT](prompts/gpt/chat.md) | [Gemini](prompts/gemini/chat.md) |
| query_condense | Active: on_demand | [GPT](prompts/gpt/query_condense.md) | [Gemini](prompts/gemini/query_condense.md) |
| summary | Active: on_demand | [GPT](prompts/gpt/summary.md) | [Gemini](prompts/gemini/summary.md) |
| explanation | Active: on_demand | [GPT](prompts/gpt/explanation.md) | [Gemini](prompts/gemini/explanation.md) |
| rewrite | Active: on_demand | [GPT](prompts/gpt/rewrite.md) | [Gemini](prompts/gemini/rewrite.md) |
| edit_verification | Active: on_demand | [GPT](prompts/gpt/edit_verification.md) | [Gemini](prompts/gemini/edit_verification.md) |
| web_research | Active: on_demand | [GPT](prompts/gpt/web_research.md) | [Gemini](prompts/gemini/web_research.md) |
| clause_drafting | Active: on_demand | [GPT](prompts/gpt/clause_drafting.md) | [Gemini](prompts/gemini/clause_drafting.md) |
| clause_verification | Active: on_demand | [GPT](prompts/gpt/clause_verification.md) | [Gemini](prompts/gemini/clause_verification.md) |
