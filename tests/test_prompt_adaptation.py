from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
PROMPTS = REPO / "kontaktlaw/skills/legal-review/references/prompts/gpt"
ACTIVE = {
    "risk_review.md",
    "grammar.md",
    "party_extraction.md",
    "chat.md",
    "query_condense.md",
    "summary.md",
    "explanation.md",
    "rewrite.md",
    "edit_verification.md",
    "web_research.md",
    "clause_drafting.md",
    "clause_verification.md",
}
DEAD_RUNTIME_REFERENCES = {
    "[HÜQUQİ KONTEKST - VEKTOR DB RAG MƏNBƏLƏRİ]",
    "selected_party",
    "output_language",
    "supplied schema",
    "supplied source unit",
    "clause ID",
    "reference index",
    "duplicate_of",
    "affectedPartyId",
    "insertAfter",
    "ORIGINAL",
    "REVISED",
}


class PluginPromptAdaptationTests(unittest.TestCase):
    def test_only_twelve_active_prompts_are_installed(self):
        self.assertEqual({path.name for path in PROMPTS.glob("*.md")}, ACTIVE)

    def test_every_prompt_defines_plugin_input_and_output(self):
        for name in ACTIVE:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            self.assertIn("# Plugin adaptation:", text, name)
            self.assertIn("Input:", text, name)
            self.assertIn("Output:", text, name)

    def test_active_prompts_have_no_website_runtime_references(self):
        for name in ACTIVE:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            for dead_reference in DEAD_RUNTIME_REFERENCES:
                self.assertNotIn(dead_reference, text, f"{name}: {dead_reference}")


if __name__ == "__main__":
    unittest.main()
