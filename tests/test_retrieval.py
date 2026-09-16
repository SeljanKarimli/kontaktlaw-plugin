import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import unicodedata
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lookup', REPO / 'kontaktlaw/skills/legal-review/scripts/search_knowledge.py')
lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lookup)

class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.laws = self.root / 'MDs'
        self.laws.mkdir()
        self.text = '# Law\n\n### <span style="color:red">Maddə 13. Business. Business is permitted.</span>\n---\n### Maddə 13-1. Exception\n13-1.1. A special exception applies.\n---\n### Maddə 13.2. Decimal\nA decimal article body.\n'
        self.filename = 'Mülki.md'
        self.source = {'file':self.filename, 'title':'Mülki', 'official_url':'https://example.org/law', 'snapshot_date':'2026-06-09', 'sha256':hashlib.sha256(self.text.encode()).hexdigest()}
        (self.laws / self.filename).write_bytes(self.text.encode())
        (self.root / 'sources.json').write_text(json.dumps({'sources':[self.source]}), encoding='utf-8')
        self.patcher = patch.multiple(lookup, ROOT=self.root, LAW_DIR=self.laws)
        self.patcher.start()
    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()
    def search(self, article=None, query=''):
        return lookup.search(argparse.Namespace(query=query, article=article, law='Mulki', limit=20))
    def test_wrapped_heading_body_is_retrievable(self):
        result = self.search('13')
        self.assertGreater(result['returned'], 0)
        self.assertIn('Business is permitted.', result['results'][0]['text'])
    def test_lexical_heading_body(self):
        self.assertGreater(self.search(query='permitted')['returned'], 0)
    def test_article_variants(self):
        for article in ['13.', ' 13 ', '13-1', '13.2']:
            self.assertGreater(self.search(article)['returned'], 0, article)
    def test_invalid_article(self):
        for article in ['../13', '13a', '13..2', '-13']:
            with self.assertRaises(ValueError): self.search(article)
    def test_tamper(self):
        (self.laws / self.filename).write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'ntegrity'): self.search('13')
    def test_nfd_filename(self):
        nfd = unicodedata.normalize('NFD', self.filename)
        (self.laws / self.filename).rename(self.laws / nfd)
        self.assertGreater(self.search('13')['returned'], 0)
        result = lookup.read(argparse.Namespace(file=nfd, start=1, end=3))
        self.assertEqual(result['lines'][2]['text'], self.text.splitlines()[2])
    def test_literal_ranges(self):
        for result in self.search(query='article permitted exception')['results']:
            raw = '\n'.join(self.text.splitlines()[result['start']-1:result['end']])
            self.assertTrue(raw.startswith(result['text']))
    def test_read_bounds_and_traversal(self):
        for file, start, end in [('../Mülki.md',1,2), (self.filename,0,2), (self.filename,1,251), (self.filename,999,1000)]:
            with self.assertRaises(ValueError): lookup.read(argparse.Namespace(file=file,start=start,end=end))
    def test_empty_results(self):
        self.assertEqual(self.search(query='zxqnevermatches')['returned'], 0)
    def replace_source(self, text):
        self.text=text
        (self.laws/self.filename).write_bytes(text.encode())
        self.source['sha256']=hashlib.sha256(text.encode()).hexdigest()
        (self.root/'sources.json').write_text(json.dumps({'sources':[self.source]}),encoding='utf-8')
    def test_long_single_line_is_literal_bounded_prefix(self):
        self.replace_source('### Maddə 1. Title '+ 'x'*4000)
        result=self.search('1')['results'][0]
        self.assertEqual(len(result['text']),3500)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['text_end_column'],3500)
        self.assertEqual(result['start'],result['end'])
        self.assertTrue(self.text.startswith(result['text']))
    def test_multiline_excerpt_has_exact_coordinates(self):
        self.replace_source('### Maddə 1. Title\n'+'ordinary text\n'*300+'distinctive target\n')
        result=self.search(query='distinctive')['results'][0]
        self.assertIn('distinctive',result['text'])
        self.assertEqual(result['text'],'\n'.join(self.text.splitlines()[result['start']-1:result['end']]))
        self.assertLessEqual(result['end']-result['start']+1,250)
    def test_search_limit_rejected(self):
        with self.assertRaises(ValueError): lookup.search(argparse.Namespace(query='text',article=None,law='',limit=21))
    def test_read_checks_integrity(self):
        (self.laws/self.filename).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'ntegrity'): lookup.read(argparse.Namespace(file=self.filename,start=1,end=1))
    def test_short_heading_only_article(self):
        self.replace_source('### Maddə 1. Qadağandır.\n')
        self.assertGreater(self.search('1')['returned'],0)
    def test_footnotes_preserved(self):
        self.replace_source('### Maddə 1. Title\nRule [1].\n## Footnotes\n[1] Historical amendment.\n')
        self.assertIn('Historical amendment',self.search(query='Historical')['results'][0]['text'])
    def test_subheading_preserves_article(self):
        self.replace_source('### Maddə 50. Control\n## <span>50. 8. 2. VÖEN;</span>\n')
        self.assertGreater(self.search('50', 'VÖEN')['returned'], 0)
    def test_match_survives_long_preceding_context(self):
        chunk={'text':'x'*3499+'\nneedle','start':1,'end':2}
        self.assertIn('needle',lookup.excerpt(chunk,{'needle'})['text'])

if __name__ == '__main__': unittest.main()
