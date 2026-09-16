import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from package import release_gate

class ReleaseGateTests(unittest.TestCase):
    def test_missing_evidence_refuses_release(self):
        with self.assertRaisesRegex(ValueError,'evidence is required'):
            release_gate(None,'abc')
