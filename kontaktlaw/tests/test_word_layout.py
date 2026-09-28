from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from test_review import r, raw_docx, grammar_packet, correction
from word_layout import corrected_docx


class WordLayoutTests(unittest.TestCase):
    def test_preserve_format_and_other_zip_parts(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = raw_docx(folder/'source.docx', '<w:p><w:pPr><w:spacing w:after="80"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>Alıcı  </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>ödəyir.</w:t></w:r></w:p><w:sectPr><w:pgMar w:left="999"/></w:sectPr>', {'word/styles.xml':b'unchanged styles', 'word/media/image.png':b'image bytes'})
            original = source.read_bytes()
            state = r.prepare(source,folder/'review',mode='never')
            packet = grammar_packet(state,[correction('Alıcı  ödəyir.','Alıcı ödəyir.',span='s1')])
            state = r.apply_grammar(state,packet)
            corrected_docx(source,folder/'corrected.docx',state)
            self.assertEqual(source.read_bytes(),original)
            with ZipFile(folder/'corrected.docx') as result, ZipFile(source) as before:
                for name in before.namelist():
                    if name != 'word/document.xml': self.assertEqual(result.read(name),before.read(name))
                from lxml import etree as ET
                from word_layout import W
                tree = ET.fromstring(result.read('word/document.xml'))
                self.assertEqual(len(list(tree.iter(W+'b'))),2)
                self.assertEqual(next(tree.iter(W+'pgMar')).get(W+'left'),'999')
                self.assertEqual(next(tree.iter(W+'spacing')).get(W+'after'),'80')
                self.assertEqual(''.join(tree.itertext()),'Alıcı ödəyir.')

    def test_refuse_mixed_format_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            source=raw_docx(folder/'source.docx','<w:p><w:r><w:t>Alıcı  </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>ödəyir.</w:t></w:r></w:p>')
            state=r.prepare(source,folder/'review',mode='never')
            state=r.apply_grammar(state,grammar_packet(state,[correction('Alıcı  ödəyir.','Alıcı ödəyir.',span='s1')]))
            with self.assertRaisesRegex(ValueError,'identical run formatting'):
                corrected_docx(source,folder/'corrected.docx',state)
            self.assertFalse((folder/'corrected.docx').exists())


if __name__ == '__main__': unittest.main()
