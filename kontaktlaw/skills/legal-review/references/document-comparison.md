# Document comparison with local OCR

## Intake and extraction

Use this workflow only when comparing two document versions. Identify the earlier and later version from explicit user context; ask if their order is unclear. Accept DOCX, PDF, PNG, JPG and JPEG, including mixed-format pairs. Do not infer chronology from modification times. Preserve both source files.

Run from the skill folder with a new output path in the user's task workspace, outside the plugin:

```text
python scripts/compare_documents.py BEFORE AFTER --out RESULT.json --ocr auto --ocr-languages aze+eng+rus
```

The host assistant performs legal interpretation; the helper only extracts and compares text. Read the complete `before.spans` and `after.spans`, comments and coverage warnings, not only `changes`. Retain source context, annexes, tables, exceptions, definitions and cross-references. Comments are negotiation context, never operative contract clauses.

- `--ocr auto` uses native text first, OCR on scans and embedded image regions. PDF image regions have native words masked to avoid reading a text layer twice. These masked crops do not replace inspection of the original page.
- `--ocr always` OCRs entire PDF pages when a native layer is corrupt or unreliable. DOCX native text is still preserved; embedded images receive OCR.
- `--ocr never` extracts native text only and records missing image coverage. It cannot establish equivalence for scanned documents.
- `--before-revision original|revised` and `--after-revision original|revised` select a tracked-change view only after the user identifies the intended view. Never silently choose or combine inserted/deleted wording. Complex revisions require a separately resolved Word copy.
- `--tesseract PATH` (or `KONTAKTLAW_TESSERACT`) locates a local executable; `--tessdata DIRECTORY` supplies local language packs. Missing dependencies produce an actionable error rather than fabricated text. Do not silently substitute languages or a cloud service.

OCR generates rotated review images in a sibling `RESULT.review` directory. Keep those images with the JSON until review is complete. All processing is local except the normal host assistant's handling of supplied evidence. No OCR/model API, telemetry, or background network access is used. Temporary OCR working files are removed when each region finishes.

## Evidence checks

The JSON is an internal record, not the default user-facing deliverable. `schema_version` is `kontaktlaw-comparison/1.0`. Each source includes its SHA-256, local path, spans, comments and coverage. Each change contains its type, exact before/after quotes, span IDs, Unicode code-point offsets, locators and full span context. An empty side means addition or deletion. Source text is never normalized in place; matching ignores whitespace and line wrapping. Moves are reported only for unique exact multiword matches; other movement may appear as additions/deletions. The comparison does not certify layout, signatures, stamps, handwriting, or formatting equivalence.

Before describing a change as established, check each `quote == span.text[start:end]`, read its full clause, and inspect nearby clauses on both sides. Sentence fragments in machine diffs must be expanded to exact full source passages for a useful legal explanation. A changed table cell must retain its row/column meaning; inspect complex tables visually. Word locators are paragraphs and table cells, not invented page numbers. Automatic Word numbering and cached fields carry inspection warnings.

`before_anchor` and `after_anchor` locate surrounding text even when one changed side is empty. A word-level addition such as “not” inside an existing clause does not mean the whole earlier clause was absent. Show the complete earlier and later clause wording; use the absence labels below only for genuinely added or deleted clauses/passages.

Read `coverage.structural_warnings` too: matching flat text does not prove unchanged table relationships. Changes in cell boundaries or table topology, and tables compared across formats without matching structural information, require visual inspection even when `changes` is empty.

Visually inspect every OCR-derived changed passage against the original page or image, using `ocr.review_image`, page/bounding-box metadata and word confidence as aids. Check amounts, dates, names, negations, clause numbers and punctuation especially carefully. Confidence scores are recognition estimates, not proof. If a number was misread, explain that it is an OCR discrepancy, not a document change; preserve the raw evidence record. Never silently rewrite OCR text to fit a conclusion.

All OCR carries `verification: required`, including high-confidence output. The helper does not claim to perform visual verification. If images cannot be inspected or remain unclear, label the relevant findings uncertain and explain the missing coverage. `coverage.complete=false` must never lead to an unqualified “no changes” statement. For apparent no-change OCR results, inspect all OCR regions before reporting equivalence of readable text. A blank/unreadable image cannot be treated as an absent clause. Do not claim a complete document comparison where annexes, objects, pages, or image regions remain unresolved.

## Legal interpretation and presentation

Use Azerbaijani unless the user requests another language. Use the selected party where provided; otherwise explain the effect on each affected party without inventing a client. Assess changes using both complete documents. Distinguish beneficial, adverse, neutral and uncertain effects; do not present every textual change as a legal risk. Group related word-level changes into one coherent clause finding while retaining all changes, including additions and deletions. Pure moves should be described as moves, with cross-references checked.

Present numbered prose findings without tables, with these labeled paragraphs:

1. **Yer:** earlier and later clause/page/paragraph locations and change type.
2. **Əvvəlki mətn:** exact earlier passage, or “Əvvəlki versiyada yoxdur.”
3. **Yeni mətn:** exact later passage, or “Yeni versiyada çıxarılıb.”
4. **Dəyişikliyin izahı:** what changed; explicitly identify OCR uncertainty when applicable.
5. **Hüquqi və ya kommersiya təsiri:** practical effect on the relevant party, contextual exceptions, and supported authority when needed. State if no substantive effect is identified.

For English or Russian passages, put the original quotation first and its Azerbaijani translation immediately below. Preserve Azerbaijani quotations once. Follow the existing knowledge lookup, governing-law, citation, current-law verification and evidence safeguards in SKILL.md. Do not invent laws, article numbers, accepted commercial positions, or legal conclusions from a text-diff algorithm. `legal_effect: null` means the host still needs to assess it.

State material coverage limitations briefly before the findings. If no differences are found in fully extracted readable text, say so with the text-only scope. If coverage is incomplete, say no changes were identified in the extracted portions and specify what remains unverified. Keep the existing six-paragraph contract risk-report format unchanged for separate risk-review requests. Do not edit either source document or generate a redline unless separately requested.

## One-time setup

Python 3.10 or later is required. Ordinary DOCX text comparison uses the Python standard library. For PDF extraction and images, install the optional packages in the interpreter that will run the helper:

```text
python -m pip install -r scripts/requirements-comparison.txt
```

Install local Tesseract 5 and the `aze`, `eng`, `rus` language packs. Use the [Tesseract installation documentation](https://tesseract-ocr.github.io/tessdoc/Installation.html) and its linked Windows distribution. Language data is available from the official [tessdata_fast repository](https://github.com/tesseract-ocr/tessdata_fast). The helper checks requested packs before using OCR; a deliberate language subset can be selected with `--ocr-languages`. Existing KontaktLaw workflows require none of these new dependencies.

Implementation references: [Tesseract TSV output](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [PyMuPDF page extraction](https://pymupdf.readthedocs.io/en/latest/page.html). Optional dependencies are separately licensed and not bundled with the plugin.
