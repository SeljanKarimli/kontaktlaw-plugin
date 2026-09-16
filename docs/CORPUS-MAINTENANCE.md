# Corpus maintenance

The immutable corpus version is 2026-06-09. Sources, original filenames, URLs, hashes and recorded dates are in the installed sources.json. `current_law_verified_at: null` means no current-law verification is asserted.

Monthly, an assigned legal maintainer should:

1. Inspect each official source and publication/amendment history, including effective dates, repeals and transitional provisions. Record who reviewed it and when.
2. Compare substantive text and footnotes against the existing snapshot. A successful HTTP response or downloaded file is not a finding of legal currency.
3. Have changes reviewed for legal effect and completeness. Preserve the prior corpus and its hashes.
4. Introduce approved updates as a separate version with a dated review record, new hashes, coverage inventory and regression evidence. Do not silently overwrite this improvement release's corpus.
5. If official text cannot be checked, record the failure and keep currency unverified.

Red HTML spans indicate differences between local copies, not legally effective amendments. Amendment notes are preserved as evidence and must be interpreted separately from operative provisions. Hash verification detects changed bytes; an attacker replacing both corpus and manifest can bypass it. Verify the release origin, commit and checksum independently.
