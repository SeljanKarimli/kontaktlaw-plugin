# KontaktLaw plugin

Contract review, grammar correction, summaries, clause explanations and drafting for Codex, with eight Azerbaijani legal-source snapshots.

**1.1.0 is a release candidate, not an approved release.** See [release gates](docs/RELEASE-GATES.md). [Version 1.0.0 remains available](https://github.com/SeljanKarimli/kontaktlaw-plugin/releases/tag/v1.0.0) for rollback.

## Install the existing release

Ask Codex with plugin-creator:

> Install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin at full commit cb2608e8d495fa3b7c1a67fde72745676598d2ba. The plugin is in the kontaktlaw folder. Validate it, register it in my personal marketplace and install it. Preserve unrelated plugins and local changes. Tell me how to invoke it in a new task.

The [v1.0.0 ZIP](https://github.com/SeljanKarimli/kontaktlaw-plugin/releases/download/v1.0.0/kontaktlaw-1.0.0.zip) has SHA-256 `2b19af9b06f24870600f85efe7578231236dce80445cf5f531e8280640e43ff8`. Compare with `Get-FileHash -Algorithm SHA256` on Windows or `sha256sum` on Linux before extracting.

Version 1.1.0 instructions will identify its full tested commit and versioned checksum manifest after its gates pass. Do not treat an unpinned branch as an approved release.

## Candidate changes

- Twelve coherent active stages; historical GPT/Gemini and inactive stages live in the repository archive, outside the installable plugin.
- HTML-aware indexing, exact bounded excerpts, article and filename normalization, integrity checks and corpus coverage inventory.
- Separate grammar and substantive revision modes, with evidence checks against document instructions and forged citations.
- Portable tests, deterministic packaging, isolated installation checks and Windows/Linux CI.
- Twenty-four synthetic multilingual fixtures, with critical cases repeated three times. Model evaluation and legal sign-off are separate release requirements.

## Development

Python 3.11+; no runtime third-party Python packages:

```text
python -B -m unittest discover -s tests -v
python -B scripts/validate.py --output build/coverage.json
python -B scripts/package.py --candidate --output build/release
```

Package from a clean committed checkout. Archives and evaluations are excluded from the ZIP. The manifest records the full commit, corpus hashes and packaged files. See [evaluation protocol](evals/README.md) and [monthly source review](docs/CORPUS-MAINTENANCE.md).

`scripts/install.py` stages a checksum-verified ZIP, preserves unrelated files, refuses modified existing installations and retains the previous version. It does not register a marketplace or change the installed cache; use plugin-creator to register the folder. Staging checks do not replace an actual host installation test.

## Data and limitations

The search helper is read-only and offline. Document reading, official-source browsing and requested edits use the host assistant's tools and model. Documents and retrieved text may be processed by the host provider according to its account settings; this plugin provides no separate privacy guarantee. Remove unnecessary personal or confidential information first. No KontaktLaw website account, database, OCR or API connection is included.

Outputs require professional review and can miss risks or misinterpret clauses. Bundled law is a 9 June 2026 snapshot, not verified current law. Download success and integrity do not establish legal currency. Local red spans are not official amendment markers.

Owned code and prompts use [MIT](kontaktlaw/LICENSE). [Third-party material](kontaktlaw/THIRD_PARTY_NOTICES.md) is treated separately. This public repository is discoverable and is not a ChatGPT marketplace listing.
