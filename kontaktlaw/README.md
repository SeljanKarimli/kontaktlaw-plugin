# KontaktLaw

Review supplied contracts, correct grammar, summarize, explain and draft clauses, and inspect eight Azerbaijani legal-source snapshots. Twelve canonical stages support one plugin workflow. Python 3.11+ is required for the dependency-free helper.

After installation, invoke KontaktLaw in a new task, supply your document and identify the party to protect or request general review. Explanations default to Azerbaijani; quotations and proposed wording preserve the document language unless requested otherwise. Ask for JSON only when needed.

## Data handling and capabilities

The search helper is read-only, checks hashes and makes no network requests. Write capability supports document edits through host tools when requested. The host assistant's model and tools may process documents and retrieved text according to the provider's account settings. Remove unnecessary personal or confidential information before supplying documents. No separate KontaktLaw privacy guarantee is provided.

There is no connection to KontaktLaw website accounts, stored documents, OCR, database or model service. No additional KontaktLaw API key is needed.

## Limitations

Professional review remains necessary. Model findings can be incomplete or incorrect. Grammar-only edits preserve rights and duties; requested legal revisions can change them and should disclose the effect and unresolved terms.

The corpus is a 9 June 2026 snapshot. Current law requires independent official-source checks. Red spans identify differences from an earlier local copy, not official amendment status. Inspect amendment footnotes and surrounding provisions. Hashes detect changed bytes, not an attacker replacing both files and manifest.

## Distribution

This 1.1.0 candidate is not release-approved until its evaluation gates pass. Install a tested full commit or a release ZIP verified against its versioned SHA-256 manifest. Source and status: https://github.com/SeljanKarimli/kontaktlaw-plugin

Owned code and prompts are MIT licensed; see LICENSE. Legal material is excluded; see THIRD_PARTY_NOTICES.md and corpus sources.json. Historical prompts are retained only in the repository archive.
