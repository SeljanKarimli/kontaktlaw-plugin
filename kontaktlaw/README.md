# KontaktLaw

An installable Codex plugin for contract review, Azerbaijani legal-source lookup, grammar correction, summaries, clause explanations and drafting.

The current update adds automatic grammar → party selection → risk review and a local clause viewer. Version comparison with local OCR and the existing focused workflows remain available.

## Included

- Eight processed MD knowledge snapshots with official-source links and source hashes. Local diff markup is removed while numbered legal footnotes are preserved.
- Twelve Codex-adapted legal workflows. Gemini prompts and inactive website stages are excluded.
- A task-focused skill and a read-only Python 3 knowledge search helper. No extra Python packages or API keys are needed.
- An additional comparison workflow for DOCX, PDF, PNG and JPEG, including mixed-format pairs. PDF/image comparison requires optional packages; OCR requires local Tesseract with Azerbaijani, English and Russian language packs. Existing features retain their dependency-free setup.

After installing or updating, start a new task and submit a legal document. You do not need to name KontaktLaw: its skill permits implicit selection by Codex. Selection is host-controlled, not a guaranteed background upload listener. An explicit request for a summary, comparison, question or another focused task takes precedence. The plugin uses the host assistant's configured model; no separate model API key is required.

## Automatic review and clickable clauses

1. Read the complete available document and correct clear grammar errors in a separate Word working copy without changing its design or formatting, preserving legal meaning. Keep the original unchanged and record all corrections.
2. Call the Codex question tool with identified party names/roles as clickable choices, with **Ümumi baxış**. Reuse a party already selected by the user.
3. Analyze risks using the existing Azerbaijani six-paragraph format and legal-source requirements.
4. Open the local viewer in Codex's right-hand browser panel. Its **Problemli bənd** buttons scroll to the matching clause and highlight it. Show every page rendered by Microsoft Word, highlight risks immediately, switch between original and corrected versions, and download the corrected DOCX.

The Word viewer uses native Word page images, retaining the original page design. DOCX edits preserve formatting and non-text package parts; compare both rendered versions to verify that text edits have not caused reflow. Full-page rendering requires Windows Microsoft Word and `scripts/requirements-layout.txt`. Unverified OCR quotations and uncertain matches have disabled navigation. Text anchors use paragraph, exact quotation and occurrence. Ambiguous or unresolvable page-image highlights remain explicitly unlinked. An unchanged attachment resumes completed stages. Review artifacts are stored locally outside the plugin; they are not included in a plugin update or release.

The helper and host workflow are documented in [Automatic review and clause viewer](skills/legal-review/references/automatic-review.md). The read-only viewer uses Python's standard-library HTTP server on `127.0.0.1` with a private capability URL, no directory listing and no write endpoints. It shuts down after two hours without requests and can be reopened. Keep its URL private. Word downloads are DOCX; non-Word text fallback downloads are UTF-8 text; the uploaded file is never overwritten.

Knowledge and prompts are snapshots. The corpus headers report 9 June 2026. Verify current law against the linked official sources when needed. This package does not connect to external services.

## Compare documents

Supply the earlier and later documents and ask: “Bu iki sənədi müqayisə et, dəyişiklikləri və onların hüquqi təsirini izah et.” The plugin shows exact old/new passages and their locations in numbered Azerbaijani prose. OCR readings require visual verification; unreadable portions are disclosed.

See the [comparison workflow and setup](skills/legal-review/references/document-comparison.md). The helper never edits originals. It writes internal comparison JSON and OCR review images only to the specified output location; keep confidential outputs outside the plugin. There is no cloud OCR account or separate model API.

Developer checks: install `tests/requirements.txt`, then run `python -m unittest discover -s tests -v`. OCR integration checks require `KONTAKTLAW_RUN_OCR_TESTS=1`, Tesseract and the three language packs; set `KONTAKTLAW_TESSERACT` if needed. Test fixtures use Arial on Windows; elsewhere set `KONTAKTLAW_TEST_FONT` to a Unicode TrueType font. The source package does not replace an installed plugin automatically.

Rendered viewer checks additionally use `tests/requirements-browser.txt`. Set `KONTAKTLAW_RUN_BROWSER_TESTS=1` and `KONTAKTLAW_BROWSER` to an installed Chromium browser executable (or install Playwright Chromium), then run the same test command. `KONTAKTLAW_SCREENSHOTS` optionally retains synthetic screenshots outside the plugin. Tests cover quotation navigation, repeated occurrences, Unicode offsets, original/corrected selection, downloads, table cells, disabled uncertain links and desktop/narrow/mobile layouts. Actual automatic skill selection and clickable party prompts require a fresh Codex task; see the invocation scenarios in the workflow guide.

## Legal limitation and data flow

**Bu pluginin cavabları hüquqi məsləhət deyil.** They are automated review assistance and may be incomplete or incorrect. Verify consequential decisions with current official sources and a qualified lawyer.

- The Python knowledge helper reads only the bundled law snapshots on the user's computer and returns matching source ranges.
- Documents, questions, and generated answers are processed by the host assistant under the host provider's settings and data policies.
- When the user requests current-law verification, available browsing tools may send a minimized legal search query to official websites. Private contract text, party identifiers, and unnecessary personal information must not be included in those queries.
- The plugin has no separate account, hosted backend, telemetry, or remote document store. The optional viewer serves local review artifacts only on this computer. Users should remove unnecessary personal information before supplying documents.

## Install from GitHub

Repository: https://github.com/SeljanKarimli/kontaktlaw-plugin

Ask Codex:

> Use plugin-creator to install KontaktLaw from https://github.com/SeljanKarimli/kontaktlaw-plugin into my personal marketplace. The plugin is in the kontaktlaw folder. Download or clone the repository, inspect the plugin, validate it, register it in my default personal marketplace, and install it. Preserve other plugins and any existing local changes. Tell me how to invoke KontaktLaw in a new task.

Alternatively, download kontaktlaw-1.0.0.zip from the repository's Releases page and extract it into a folder named kontaktlaw. Ask Codex to install that local folder with plugin-creator.

The repository is public and discoverable. Anyone can download its knowledge and workflows. This GitHub release is a distribution package; it is not a ChatGPT marketplace listing. No credentials, customer documents, or chat history are included.

## License

Publisher-owned code and prompts are available under the [MIT License](LICENSE). Bundled legislation and other third-party material are excluded from that grant; see [Third-party legal sources](THIRD_PARTY_NOTICES.md).
