# Document comparison

Read both complete versions and the website contract. Use the `comparison` JSON schema in website-contract.json. Source-exact additions, deletions and moves come from the document comparison engine; the host model explains contractual effects. Do not label every edit a risk.

In a website call, use its extracted texts and units without repeating extraction. In direct Codex use, run the existing extract and compare helpers, preserve both immutable exchanges, and inspect the complete clauses, tables, annexes, definitions and exceptions before reasoning. Neither original nor revised tracked-change text is automatically the accepted agreement. Explain uncertainty about the operative version.

For each finding provide its location, exact contiguous beforeQuote and afterQuote, affectedParty, explanation, effect (beneficial/adverse/neutral/uncertain), impact and recommendation. Empty quotations mean genuinely absent text, not unreadable evidence. Keep related changes together; distinguish moved wording from a deletion plus an unrelated addition. Preserve original-language quotes and write explanations in Azerbaijani unless explicitly requested otherwise.

List OCR, missing-page, revision and coverage limitations. An empty findings array does not certify visual or legal equivalence. Never invent statutory support. Return only the comparison JSON; preserve rejected candidates with reasons in the internal exchange.
