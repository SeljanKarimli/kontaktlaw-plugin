"""The versioned plugin cache must not make long law filenames unreadable."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/legal-review/scripts'))
import search_knowledge as knowledge


class KnowledgePathTests(unittest.TestCase):
    def test_all_bundled_laws_are_readable(self):
        sources=knowledge.metadata()
        self.assertEqual(len(sources),8)
        for source in sources:
            with self.subTest(law=source['file']):
                result=knowledge.read(SimpleNamespace(file=source['file'],start=1,end=3))
                self.assertTrue(result['lines'])

    @unittest.skipUnless(os.name == 'nt','Windows long-path regression')
    def test_long_cache_path_reads_and_searches(self):
        with tempfile.TemporaryDirectory() as temp:
            regular=Path(temp)/('a'*90)/('b'*90)/('c'*90)
            extended=knowledge.local_path(regular)
            extended.mkdir(parents=True)
            law={'file':'Azərbaycan qanunu.md','title':'Azərbaycan qanunu',
                 'official_url':'https://example.invalid','snapshot_date':'test'}
            (extended/law['file']).write_text('## Maddə 1\nMüqavilə öhdəlikləri.\n',encoding='utf-8')
            with patch.object(knowledge,'LAW_DIR',extended),patch.object(knowledge,'metadata',return_value=[law]):
                result=knowledge.read(SimpleNamespace(file=law['file'],start=1,end=2))
                self.assertIn('Müqavilə',result['lines'][1]['text'])
                result=knowledge.search(SimpleNamespace(query='müqavilə',law='',article=None,limit=1))
                self.assertEqual(result['returned'],1)
            # Use the extended form for teardown too, without recursive deletion.
            (extended/law['file']).unlink()
            extended.rmdir()
            extended.parent.rmdir()
            extended.parent.parent.rmdir()


if __name__ == '__main__':
    unittest.main()
