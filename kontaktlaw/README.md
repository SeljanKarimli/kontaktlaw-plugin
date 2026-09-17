# KontaktLaw

An installable Codex plugin for contract review, Azerbaijani legal-source lookup, grammar correction, summaries, clause explanations and drafting.

## Included

- Eight processed MD knowledge snapshots with official-source links and source hashes. Local diff markup is removed while numbered legal footnotes are preserved.
- Twelve Codex-adapted legal workflows. Gemini prompts and inactive website stages are excluded.
- A task-focused skill and a read-only Python 3 knowledge search helper. No extra Python packages or API keys are needed.

After installing, start a new task, invoke KontaktLaw and supply a document. Specify the party whose interests should be protected, or request general review. The plugin uses the host assistant's configured model.

Knowledge and prompts are snapshots. The corpus headers report 9 June 2026. Verify current law against the linked official sources when needed. This package does not connect to external services.

## Legal limitation and data flow

**Bu pluginin cavabları hüquqi məsləhət deyil.** They are automated review assistance and may be incomplete or incorrect. Verify consequential decisions with current official sources and a qualified lawyer.

- The Python knowledge helper reads only the bundled law snapshots on the user's computer and returns matching source ranges.
- Documents, questions, and generated answers are processed by the host assistant under the host provider's settings and data policies.
- When the user requests current-law verification, available browsing tools may send a minimized legal search query to official websites. Private contract text, party identifiers, and unnecessary personal information must not be included in those queries.
- The plugin has no separate account, backend, telemetry, or document store. Users should remove unnecessary personal information before supplying documents.

## Install from GitHub

Repository: https://github.com/SeljanKarimli/kontaktlaw-plugin

Ask Codex:

> Use plugin-creator to install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin into my personal marketplace. The plugin is in the kontaktlaw folder. Download or clone the repository, inspect the plugin, validate it, register it in my default personal marketplace, and install it. Preserve other plugins and any existing local changes. Tell me how to invoke KontaktLaw in a new task.

Alternatively, download kontaktlaw-1.0.0.zip from the repository's Releases page and extract it into a folder named kontaktlaw. Ask Codex to install that local folder with plugin-creator.

The repository is public and discoverable. Anyone can download its knowledge and workflows. This GitHub release is a distribution package; it is not a ChatGPT marketplace listing. No credentials, customer documents, or chat history are included.

## License

Publisher-owned code and prompts are available under the [MIT License](LICENSE). Bundled legislation and other third-party material are excluded from that grant; see [Third-party legal sources](THIRD_PARTY_NOTICES.md).
