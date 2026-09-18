from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
PLUGINS = (
    (
        REPO / "kontaktlaw-text/skills/legal-review-text/SKILL.md",
        REPO / "kontaktlaw-text/skills/legal-review-text/references/prompts/gpt/risk_review.md",
    ),
    (
        REPO / "kontaktlaw/skills/legal-review/SKILL.md",
        REPO / "kontaktlaw/skills/legal-review/references/prompts/gpt/risk_review.md",
    ),
)


class KontaktLawTextLanguageTests(unittest.TestCase):
    def test_azerbaijani_is_primary_output_language(self):
        for skill_path, _ in PLUGINS:
            text = skill_path.read_text(encoding="utf-8")
            self.assertIn("Azerbaijani is the primary output language", text)
            self.assertIn("fully in Azerbaijani", text)

    def test_foreign_documents_include_original_and_azerbaijani(self):
        for _, prompt_path in PLUGINS:
            text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("Original mətn:", text)
            self.assertIn("Original dildə təklif:", text)
            self.assertGreaterEqual(text.count("Azərbaycan dilinə tərcümə:"), 2)

    def test_azerbaijani_documents_are_not_duplicated(self):
        for _, prompt_path in PLUGINS:
            text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("For an Azerbaijani document, show the quotation once", text)
            self.assertIn("give the proposal once in Azerbaijani", text)

    def test_risk_analysis_remains_prose_only(self):
        for _, prompt_path in PLUGINS:
            text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("Never use a Markdown table", text)
            self.assertIn("Do not compress findings into a table", text)


if __name__ == "__main__":
    unittest.main()
