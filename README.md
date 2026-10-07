# KontaktLaw plugin

An installable Codex plugin for contract review, Azerbaijani legal-source lookup, grammar correction, summaries, clause explanations, and drafting.

## Automatic review and clause viewer

KontaktLaw preserves the original Word design while applying verified grammar corrections to a separate DOCX copy. It asks which party to protect through Codex's question interface, then opens the complete Word pages beside the legal findings and highlights risky clauses. The uploaded document remains unchanged.

Submitting a legal document can activate the installed skill without mentioning KontaktLaw. Automatic selection is controlled by Codex; it is not a guaranteed background upload listener. Explicit summary, comparison, explanation, and other focused requests take precedence. Start a new task after updating. See the [automatic review workflow](kontaktlaw/skills/legal-review/references/automatic-review.md) and [plugin guide](kontaktlaw/README.md).

## Document comparison (v1.2.0)

The latest source adds Word, PDF, PNG and JPEG comparison with local Azerbaijani, English and Russian OCR, exact before/after passages, source locations and contextual legal-impact explanations. Existing workflows and review formatting are preserved. See the [comparison setup and workflow](kontaktlaw/skills/legal-review/references/document-comparison.md). OCR readings require visual verification.

## Install with Codex

Copy this prompt into Codex on the computer where you want to use the plugin:

> Use plugin-creator to install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin into my personal marketplace.
>
> The plugin is in the kontaktlaw folder. Download or clone the repo, validate the plugin, register it in my personal marketplace, and install it. Preserve my other plugins and existing local changes. Then explain how to use KontaktLaw in a new task.
>
> On Windows, also install `kontaktlaw/skills/legal-review/scripts/requirements-layout.txt` into the Python runtime used for the review and run `check_layout_runtime.py`. Confirm that Microsoft Word is installed and the preflight succeeds, because the complete Word-page viewer and risk highlights require them. Do not claim the UI is ready if the preflight fails.

Start a new task after installation and attach a legal Word document. KontaktLaw can activate from the attachment without an `@KontaktLaw` mention. It first checks grammar, then asks which party to protect before risk review. You can also specify a party or request general review up front.

The complete Word-page viewer currently requires Windows, Microsoft Word, and the packages in `requirements-layout.txt`. The legal analysis and extracted-text fallback remain available when native Word rendering is unavailable, but that fallback does not reproduce the original page design.

## Download the ZIP

The ZIP below is the older 1.0.0 release. Install from the latest repository source for automatic review, the clause viewer, and OCR-assisted comparison.

[Download KontaktLaw 1.0.0](https://github.com/SeljanKarimli/kontaktlaw-plugin/releases/download/v1.0.0/kontaktlaw-1.0.0.zip), or visit the [release page](https://github.com/SeljanKarimli/kontaktlaw-plugin/releases/tag/v1.0.0). Extract the ZIP into a folder named `kontaktlaw`, then ask Codex to use plugin-creator to install that folder in your personal marketplace.

Each recipient installs the plugin on their own computer. Use an up-to-date Codex installation with plugin support and the plugin-creator skill. The bundled knowledge search helper needs Python 3 and no additional packages. The plugin runs with the host assistant's configured model and tools; no separate KontaktLaw API key is required.

## Included

- The complete plugin in [`kontaktlaw/`](kontaktlaw/), including `.codex-plugin/plugin.json`.
- Eight Azerbaijani legal knowledge files and their source hashes.
- Twelve Codex-adapted legal workflows. Gemini prompts and inactive website stages are excluded.
- A legal-review skill and a read-only Python knowledge search helper.
- A ZIP containing the same plugin files, published as a release asset.

## Scope and sources

Knowledge and prompts are snapshots. The law corpus headers report 9 June 2026; verify current law against official sources when needed. The plugin does not connect to external services. Credentials and customer documents are not included.

This repository is public and discoverable. Anyone can download the bundled knowledge and prompts. This is GitHub distribution for local installation, not a listing in the ChatGPT marketplace.

## Legal limitation and data flow

**Bu pluginin cavabları hüquqi məsləhət deyil.** They are automated review assistance and may be incomplete or incorrect. Verify consequential decisions with current official sources and a qualified lawyer.

- The Python knowledge helper reads only the bundled law snapshots on the user's computer and returns matching source ranges.
- Documents, questions, and generated answers are processed by the host assistant under the host provider's settings and data policies.
- When the user requests current-law verification, available browsing tools may send a minimized legal search query to official websites. Private contract text, party identifiers, and unnecessary personal information must not be included in those queries.
- The plugin has no separate account, hosted backend, telemetry, or remote document store. Its optional read-only viewer serves local review artifacts on this computer; keep viewer URLs private. Users should remove unnecessary personal information before supplying documents.

## License

Publisher-owned code and prompts are available under the [MIT License](LICENSE). Bundled legislation and other third-party material are excluded from that grant; see [Third-party legal sources](THIRD_PARTY_NOTICES.md).

## Validation

Package validation checks the manifest, eight law-file hashes, twelve active prompt stages, 16,515 literal chunk line ranges, all 2,302 article headings, Azerbaijani/ASCII search equivalence, invalid read handling, and ZIP/source consistency. These checks do not establish that the law snapshot is current or that model responses have passed end-to-end testing.
