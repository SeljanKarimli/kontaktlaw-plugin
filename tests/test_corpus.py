import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('validation',Path(__file__).resolve().parents[1]/'scripts/validate.py')
validation=importlib.util.module_from_spec(spec); spec.loader.exec_module(validation)

class CorpusTests(unittest.TestCase):
    def test_complete_coverage(self):
        result=validation.validate()
        self.assertEqual(len(result['sources']),8)
        self.assertTrue(all(s['article_count']>0 for s in result['sources']))
    def test_known_broken_articles(self):
        import argparse
        for law,article in [('Vergi','13'),('Əmək','77'),('Mülki','13')]:
            result=validation.lookup.search(argparse.Namespace(law=law,article=article,query='',limit=6))
            self.assertGreater(result['returned'],0,(law,article))

if __name__=='__main__': unittest.main()
