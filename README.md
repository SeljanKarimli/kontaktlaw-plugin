# KontaktLaw plugin

An installable Codex plugin for contract review, Azerbaijani legal-source lookup, grammar correction, summaries, clause explanations, and drafting.

## Install with Codex

Copy this prompt into Codex on the computer where you want to use the plugin:

> Use plugin-creator to install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin into my personal marketplace. The plugin is in the kontaktlaw folder. Download or clone the repository, inspect the plugin, validate it, register it in my default personal marketplace, and install it. Preserve other plugins and any existing local changes. Tell me how to invoke KontaktLaw in a new task.

Start a new task after installation. Invoke KontaktLaw, supply your document, and specify the party whose interests should be protected or request a general review.

## Download the ZIP

[Download KontaktLaw 1.0.0](https://github.com/SeljanKarimli/kontaktlaw-plugin/releases/download/v1.0.0/kontaktlaw-1.0.0.zip), or visit the [release page](https://github.com/SeljanKarimli/kontaktlaw-plugin/releases/tag/v1.0.0). Extract the ZIP into a folder named `kontaktlaw`, then ask Codex to use plugin-creator to install that folder in your personal marketplace.

Each recipient installs the plugin on their own computer. Use an up-to-date Codex installation with plugin support and the plugin-creator skill. The bundled knowledge search helper needs Python 3 and no additional packages. The plugin runs with the host assistant's configured model and tools; no separate KontaktLaw API key is required.

## Included

- The complete plugin in [`kontaktlaw/`](kontaktlaw/), including `.codex-plugin/plugin.json`.
- Eight Azerbaijani legal knowledge files and their source hashes.
- 42 GPT and Gemini prompt snapshots captured on 15 September 2026.
- A legal-review skill and a read-only Python knowledge search helper.
- A ZIP containing the same plugin files, published as a release asset.

## Scope and sources

Knowledge and prompts are snapshots. The law corpus headers report 9 June 2026; verify current law against official sources when needed. The plugin does not connect to the KontaktLaw website's accounts, stored documents, OCR, Firebase, or model providers. Credentials and customer documents are not included.

This repository is public and discoverable. Anyone can download the bundled knowledge and prompts. This is GitHub distribution for local installation, not a listing in the ChatGPT marketplace.

## Validation

Package validation checks the manifest, eight law-file hashes, 42 prompt hashes, 14,078 literal chunk line ranges, article lookup, Azerbaijani/ASCII search equivalence, invalid read handling, and ZIP/source consistency. These checks do not establish that the law snapshot is current or that model responses have passed end-to-end testing.
