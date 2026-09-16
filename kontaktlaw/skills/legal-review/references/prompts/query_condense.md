---
stage: query_condense
status: active
inputs: Ambiguous follow-up and relevant conversation context
outputs: Self-contained question or clarification
---

# Query Condense

Use the shared language, evidence and output rules in SKILL.md.

Resolve references using explicit conversation context. Preserve party, task, jurisdiction and uncertainty. Ask a narrow clarification when two materially different interpretations remain. Do not introduce facts or turn a document question into legal research unnecessarily.

## Example

“Does that also apply to replacements?” after a warranty discussion means the warranty on replacement goods; if two warranties were discussed, ask which one.
