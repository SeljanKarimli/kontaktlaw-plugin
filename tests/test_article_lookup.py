import argparse
import html
import importlib.util
from pathlib import Path
import re
import unittest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'kontaktlaw/skills/legal-review/scripts/search_knowledge.py'
SPEC = importlib.util.spec_from_file_location('kontaktlaw_lookup', SCRIPT)
lookup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lookup)


class ArticleLookupRegressionTests(unittest.TestCase):
    def lookup(self, law, article):
        return lookup.search(argparse.Namespace(query='', law=law, article=article, limit=20))

    def test_wrapped_tax_article_13_is_retrievable(self):
        result = self.lookup('Vergi', '13')
        self.assertGreater(result['matching_chunks'], 0)
        self.assertTrue(any(item['article'] == '13' for item in result['results']))

    def test_wrapped_labour_article_77_is_retrievable(self):
        result = self.lookup('Əmək', '77')
        self.assertGreater(result['matching_chunks'], 0)
        self.assertTrue(any(item['article'] == '77' for item in result['results']))

    def test_heading_only_civil_article_13_is_retrievable(self):
        result = self.lookup('Mülki', '13')
        self.assertGreater(result['matching_chunks'], 0)
        self.assertTrue(any(item['article'] == '13' for item in result['results']))

    def test_every_article_heading_is_indexed(self):
        expected_total = 0
        indexed_total = 0
        for source in lookup.metadata():
            path = lookup.LAW_DIR / source['file']
            headings = []
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if not re.match(r'^#{2,6}\s+', line):
                    continue
                text = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'^#+\s+', '', line))).strip()
                match = re.search(r'\bmadde\s+(\d+(?:[.-]\d+)*)\b', lookup.normalize(text))
                if match:
                    headings.append((number, match.group(1)))
            chunks = {(item['start'], item['article']) for item in lookup.chunks(source)}
            expected_total += len(headings)
            indexed_total += sum(item in chunks for item in headings)
        self.assertEqual(expected_total, 2302)
        self.assertEqual(indexed_total, expected_total)


if __name__ == '__main__':
    unittest.main()
