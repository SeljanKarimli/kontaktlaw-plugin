import hashlib
import json
from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
KNOWLEDGE = REPO / "kontaktlaw/skills/legal-review/references/knowledge"
LAW_DIR = KNOWLEDGE / "MDs"
SOURCES = KNOWLEDGE / "sources.json"
FOOTNOTE = re.compile(r"^\[\d+\]", re.MULTILINE)
EXPECTED_FOOTNOTES = {
    "602-IIQ - Elektron imza və elektron sənəd haqqında_rag_chunks.md": 9,
    "Azərbaycan Respublikasının Mülki Məcəlləsi_rag_chunks.md": 825,
    "Azərbaycan Respublikasının Vergi Məcəlləsi_rag_chunks.md": 1410,
    "Azərbaycan Respublikasının Əmək Məcəlləsi_rag_chunks.md": 343,
    "Cinayət yolu ilə əldə edilmiş əmlakın leqallaşdırılmasına və terrorçuluğun maliyyələşdirilməsinə qarşı mübarizə haqqında_rag_chunks.md": 15,
    "Elektron ticarət haqqında_rag_chunks.md": 5,
    "Fərdi məlumatlar haqqında_rag_chunks.md": 4,
    "İstehlakçıların hüquqlarının müdafiəsi haqqında Azərbaycan Respublikası Qanununun qüvvəyə minməsi barədə_rag_chunks.md": 37,
}


class CorpusPackagingTests(unittest.TestCase):
    def test_diff_markup_is_removed_and_footnotes_are_preserved(self):
        for name, expected_footnotes in EXPECTED_FOOTNOTES.items():
            text = (LAW_DIR / name).read_text(encoding="utf-8")
            self.assertNotIn('<span style="color:red">', text, name)
            self.assertNotIn("</span>", text, name)
            self.assertEqual(len(FOOTNOTE.findall(text)), expected_footnotes, name)
            self.assertIn(
                "hüquqi dəyişiklik qeydləri [N] istinadlı footnote-lardadır",
                text,
                name,
            )

    def test_manifest_matches_packaged_files(self):
        manifest = json.loads(SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["sources"]), 8)
        for source in manifest["sources"]:
            data = (LAW_DIR / source["file"]).read_bytes()
            self.assertEqual(len(data), source["bytes"], source["file"])
            self.assertEqual(
                hashlib.sha256(data).hexdigest(),
                source["sha256"],
                source["file"],
            )
            text = data.decode("utf-8")
            line_count = text.count("\n") + (not text.endswith("\n"))
            self.assertEqual(line_count, source["lines"], source["file"])


if __name__ == "__main__":
    unittest.main()
