# KontaktLaw

An installable Codex plugin for contract review, Azerbaijani legal-source lookup, grammar correction, summaries, clause explanations and drafting.

## Included

- Eight original MD knowledge files (5.17 MB), with official-source links and source hashes.
- All 42 prompt texts from the GPT and Gemini dashboard profiles, captured on 15 September 2026; inactive legacy stages are labelled.
- A task-focused skill and a read-only Python 3 knowledge search helper. No extra Python packages or API keys are needed.

After installing, start a new task, invoke KontaktLaw and supply a document. Specify the party whose interests should be protected, or request general review. The plugin uses the host assistant's configured model.

Knowledge and prompts are snapshots. The corpus headers report 9 June 2026. Verify current law against the linked official sources when needed. This package does not connect to the website's accounts, stored documents, OCR, Firebase or model providers.

## Install from GitHub

Repository: https://github.com/SeljanKarimli/kontaktlaw-plugin

Ask Codex:

> Use plugin-creator to install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin into my personal marketplace. The plugin is in the kontaktlaw folder. Download or clone the repository, inspect the plugin, validate it, register it in my default personal marketplace, and install it. Preserve other plugins and any existing local changes. Tell me how to invoke KontaktLaw in a new task.

Alternatively, download kontaktlaw-1.0.0.zip from the repository's Releases page and extract it into a folder named kontaktlaw. Ask Codex to install that local folder with plugin-creator.

The repository is public and discoverable. Anyone can download its knowledge and prompt snapshots. This GitHub release is a distribution package; it is not a ChatGPT marketplace listing. No credentials, customer documents, dashboard records or chat history are included.
