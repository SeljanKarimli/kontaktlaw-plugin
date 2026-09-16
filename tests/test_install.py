import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'scripts/install.py')
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.parent=self.root/'plugins'; self.parent.mkdir()
        (self.parent/'unrelated.txt').write_text('preserve')
    def tearDown(self): self.temp.cleanup()
    def package(self,version='1.0.0',extra=None):
        data={'.codex-plugin/plugin.json':json.dumps({'name':'kontaktlaw','version':version}).encode(),'README.md':b'owned'}
        if extra: data.update(extra)
        archive=self.root/'test.zip'
        with zipfile.ZipFile(archive,'w') as zipped:
            for name,content in data.items(): zipped.writestr(name,content)
        manifest=self.root/'manifest.json'
        manifest.write_text(json.dumps({'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':{n:hashlib.sha256(c).hexdigest() for n,c in data.items()}}))
        return archive,manifest
    def test_fresh_and_upgrade_preserve_unrelated_and_rollback(self):
        installer.install(*self.package(),self.parent)
        installer.install(*self.package('1.1.0'),self.parent)
        self.assertEqual((self.parent/'unrelated.txt').read_text(),'preserve')
        self.assertTrue((self.parent/'kontaktlaw.previous/README.md').is_file())
    def test_modified_install_refused(self):
        target=installer.install(*self.package(),self.parent)
        (target/'README.md').write_text('user change')
        with self.assertRaisesRegex(ValueError,'modified'): installer.install(*self.package('1.1.0'),self.parent)
        self.assertEqual((target/'README.md').read_text(),'user change')
    def test_traversal_refused(self):
        with self.assertRaisesRegex(ValueError,'Unsafe'): installer.install(*self.package(extra={'../outside':b'x'}),self.parent)
        self.assertFalse((self.parent/'outside').exists())
    def test_tampered_zip_refused(self):
        archive,manifest=self.package(); archive.write_bytes(archive.read_bytes()+b'x')
        with self.assertRaisesRegex(ValueError,'checksum'): installer.install(archive,manifest,self.parent)
