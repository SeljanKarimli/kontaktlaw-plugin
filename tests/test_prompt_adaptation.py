from pathlib import Path
import re
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

    def test_distributed_guidance_has_no_internal_stack_or_identifiers(self):
        paths = [
            REPO / "README.md",
            REPO / "kontaktlaw/README.md",
            REPO / "kontaktlaw/provenance.json",
            REPO / "kontaktlaw/skills/legal-review/SKILL.md",
            REPO / "kontaktlaw/skills/legal-review/references/prompt-guide.md",
        ]
        forbidden = {
            "firebase",
            "qdrant",
            "onlyoffice",
            "model routing",
            "kontakt-law.web.app/dashboard",
            "kontakt home",
            "paşa bank",
            "bank respublika",
        }
        for path in paths:
            text = path.read_text(encoding="utf-8").lower()
            for value in forbidden:
                self.assertNotIn(value, text, f"{path.name}: {value}")
            self.assertIsNone(
                re.search(r"\b[0-9a-f]{40}\b", text),
                f"{path.name}: internal Git revision",
            )
            self.assertIsNone(
                re.search(
                    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
                    text,
                ),
                f"{path.name}: internal profile UUID",
            )

    def test_party_examples_use_no_real_company_names(self):
        text = (PROMPTS / "party_extraction.md").read_text(encoding="utf-8").lower()
        for company in ("kontakt home", "paşa bank", "bank respublika"):
            self.assertNotIn(company, text)

    def test_prompt_instructions_use_one_language_and_one_output_rule(self):
        for name in ACTIVE:
            text = (PROMPTS / name).read_text(encoding="utf-8")
            self.assertTrue(text.isascii(), f"{name}: prompt instructions must be English")
            self.assertIn("canonical language rule in SKILL.md", text, name)

        skill = (REPO / "kontaktlaw/skills/legal-review/SKILL.md").read_text(
            encoding="utf-8"
        )
        guide = (
            REPO / "kontaktlaw/skills/legal-review/references/prompt-guide.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Output language", skill)
        self.assertIn("Azerbaijani by default", skill)
        self.assertNotIn("Azerbaijani by default", guide)


if __name__ == "__main__":
    unittest.main()
