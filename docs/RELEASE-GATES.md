# KontaktLaw 1.1.0 release evidence

Status: candidate under evaluation; do not create a v1.1.0 release yet.

| Audit item | Implementation / evidence | Release gate |
|---|---|---|
| Wrapped and heading-only provisions | retrieval regression suite | deterministic checks |
| Corpus completeness | independent inventory in scripts/validate.py | eight unchanged source hashes and classified ranges |
| Inconsistent website prompts | twelve canonical stages; archive/v1.0.0 outside package | prompt review |
| Injection / fabricated authority | evidence contract and adversarial fixtures | fresh Codex evaluation |
| No reproducible tests | tests/, scripts/, CI | Windows and Linux jobs |
| Duplicate / inactive instructions | repository archive, excluded from ZIP | packaging check |
| Legal-source currency | snapshot metadata and monthly process | never claimed from download alone |
| Ownership | publisher confirmed prompt redistribution permission on 2026-09-16 | legal-source status separate |
| Model accuracy | 24 synthetic cases, eight per language | baseline/candidate outputs and adjudicated scores required |
| Distribution | deterministic ZIP and versioned manifest | clean tested commit, verified download |

## Required before publishing

- Record complete v1.0.0 and candidate Codex runs, model/settings, outputs and critical-case repetitions.
- Qualified legal reviewer signs expectations and disputed findings. AI review is supplementary, not this sign-off.
- Measure exact quotations/locations and party attribution at 100%; zero invented references or successful instruction attacks; risk precision >=90%, recall >=85%; no unintended grammar meaning changes.
- Windows and Linux CI pass on the release commit. Test ZIP extraction and isolated fresh/upgrade installation without replacing unrelated files or user modifications.
- Resolve redistribution status of corpus material; permission for owned prompts does not itself settle third-party rights.
- Publish the full commit in release installation instructions, ZIP, SHA256SUMS and versioned manifest. Verify downloaded assets against the tested build. Preserve v1.0.0.

Do not substitute deterministic parser tests for legal quality or model evaluation. Counts of article headings include historical headings in amendment notes; they are not counts of currently operative legal articles.
