# KontaktLaw

An installable Codex plugin for contract review, Azerbaijani legal-source lookup, grammar correction, summaries, clause explanations and drafting.

## Preview status

Version 2.0.0-preview.2 adds shared evidence validation, structured extraction, comparisons, approved templates, source-update staging and a separate Office companion. This preview has not passed lawyer-labelled model evaluations or live Microsoft Office acceptance testing. No accuracy or platform-parity claim is made. Read the skill evidence workflow for commands.

## Included

- Eight processed MD knowledge snapshots with official-source links and source hashes. Local diff markup is removed while numbered legal footnotes are preserved.
- Twelve Codex-adapted legal workflows. Gemini prompts and inactive website stages are excluded.
- A task-focused skill and a read-only Python 3 knowledge search helper. Core tools need no extra packages or API keys. PDF extraction and DOCX report creation require the optional scripts/requirements-document.txt dependencies.

After installing, start a new task, invoke KontaktLaw and supply a document. Specify the party whose interests should be protected, or request general review. The plugin uses the host assistant's configured model.

Knowledge and prompts are snapshots. The corpus headers report 9 June 2026. Verify current law against the linked official sources when needed. This package does not connect to external services.

## Legal limitation and data flow

**Bu pluginin cavabları hüquqi məsləhət deyil.** They are automated review assistance and may be incomplete or incorrect. Verify consequential decisions with current official sources and a qualified lawyer.

- The Python knowledge helper reads only the bundled law snapshots on the user's computer and returns matching source ranges.
- Documents, questions, and generated answers are processed by the host assistant under the host provider's settings and data policies.
- When the user requests current-law verification, available browsing tools may send a minimized legal search query to official websites. Private contract text, party identifiers, and unnecessary personal information must not be included in those queries.
- The plugin has no separate account, hosted backend, or telemetry. The explicit local workspace stores only user-authorized templates and outputs. Users should remove unnecessary personal information before supplying documents.

## Install from GitHub

Repository: https://github.com/SeljanKarimli/kontaktlaw-plugin

Ask Codex:

> Use plugin-creator to install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin into my personal marketplace. The plugin is in the kontaktlaw folder. Download or clone the repository, inspect the plugin, validate it, register it in my default personal marketplace, and install it. Preserve other plugins and any existing local changes. Tell me how to invoke KontaktLaw in a new task.

Alternatively, download kontaktlaw-1.0.0.zip from the repository's Releases page and extract it into a folder named kontaktlaw. Ask Codex to install that local folder with plugin-creator.

The repository is public and discoverable. Anyone can download its knowledge and workflows. This GitHub release is a distribution package; it is not a ChatGPT marketplace listing. No credentials, customer documents, or chat history are included.

## License

Publisher-owned code and prompts are available under the [MIT License](LICENSE). Bundled legislation and other third-party material are excluded from that grant; see [Third-party legal sources](THIRD_PARTY_NOTICES.md).

## Website JSON profile (2.0 preview)

KontaktLaw now returns website-compatible JSON by default. Shared schemas and examples are in `skills/legal-review/references/website-contract.json` and `website-examples.json`. The immutable evidence exchange stays internal; `website-result` converts source offsets to UTF-16 and retains rejected findings with reasons. KontaktLaw Text keeps its existing prose presentation. This preview does not certify model accuracy or activate an installed worker.

## Optional Word viewer and local comparison

The existing complete-page Word viewer and OCR comparison helpers remain available when explicitly requested. JSON remains the default KontaktLaw output. Read [viewer prerequisites](skills/legal-review/references/automatic-review.md) before opening it. On Windows install `skills/legal-review/scripts/requirements-layout.txt` into the Python runtime used for review and run `skills/legal-review/scripts/check_layout_runtime.py`; Microsoft Word must be installed. Do not claim layout support when that check fails. The original document is never overwritten. Viewer artifacts stay outside the plugin and are served only through a private loopback URL.

The local comparison helper uses native extraction and optional Tesseract; see [comparison setup](skills/legal-review/references/document-comparison.md). Run `python -m unittest discover -s kontaktlaw/tests -v` from the repository for its regression tests. OCR and rendered viewer tests remain opt-in as described in the test files.
