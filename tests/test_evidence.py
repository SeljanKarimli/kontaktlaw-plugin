import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('evidence',Path(__file__).resolve().parents[1]/'evals/check.py')
evidence=importlib.util.module_from_spec(spec); spec.loader.exec_module(evidence)

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.corpus=self.root/'MDs'; self.corpus.mkdir()
        self.fixture=self.root/'fixture.txt'; self.fixture.write_text('Buyer pays 700.\n',encoding='utf-8')
        self.law=self.corpus/'law.md'
        self.law.write_text('### <span>Maddə 13. Business</span>\nBusiness is permitted.\n### Maddə 14. Other\nAnother rule.\n',encoding='utf-8')
        (self.root/'sources.json').write_text(json.dumps({'sources':[{'file':'law.md','sha256':hashlib.sha256(self.law.read_bytes()).hexdigest()}]}),encoding='utf-8')
    def tearDown(self): self.temp.cleanup()
    def output(self,article='13'):
        return {'answer':'test','quotes':[],'legal_references':[{'file':'law.md','article':article,'start':2,'end':2,'text':'Business is permitted.','verification':'snapshot'}]}
    def test_correct_reference(self):
        self.assertEqual(evidence.check(self.output(),self.fixture,self.corpus)['deterministic_failures'],[])
    def test_real_quote_wrong_article_rejected(self):
        self.assertTrue(evidence.check(self.output('99999'),self.fixture,self.corpus)['deterministic_failures'])
    def test_tampered_source_rejected(self):
        self.law.write_text(self.law.read_text(encoding='utf-8')+'tampering',encoding='utf-8')
        self.assertTrue(evidence.check(self.output(),self.fixture,self.corpus)['deterministic_failures'])
    def test_imprecise_line_range_rejected(self):
        output=self.output(); output['legal_references'][0]['start']=1
        self.assertTrue(evidence.check(output,self.fixture,self.corpus)['deterministic_failures'])
