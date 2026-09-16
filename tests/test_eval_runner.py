import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('runner',Path(__file__).resolve().parents[1]/'evals/run.py')
runner=importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        (self.root/'stderr.txt').write_text('',encoding='utf-8')
        (self.root/'output.json').write_text(json.dumps({'answer':'Review','quotes':[],'legal_references':[]}),encoding='utf-8')
    def tearDown(self): self.temp.cleanup()
    def test_zero_exit_policy_rejection_is_failure(self):
        (self.root/'stderr.txt').write_text('rejected: blocked by policy',encoding='utf-8')
        self.assertEqual(runner.assess_run(self.root,0),'infrastructure_failure')
    def test_valid_output_needs_scoring(self):
        self.assertEqual(runner.assess_run(self.root,0),'requires_scoring')
    def test_missing_output_is_failure(self):
        (self.root/'output.json').unlink()
        self.assertEqual(runner.assess_run(self.root,0),'invalid_output')
    def test_timeout_is_failure(self):
        self.assertEqual(runner.assess_run(self.root,'timeout'),'infrastructure_failure')
