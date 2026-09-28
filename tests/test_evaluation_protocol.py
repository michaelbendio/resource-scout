import json
import tempfile
import unittest
from pathlib import Path
from resource_research_agent.evaluation.protocol import (init_experiment,seal_protocol,verify_protocol,
    provider_inputs,inside,EvaluationError)
from tests.evaluation_support import fixture


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config,self.db=fixture(self.root);self.exp=self.root/'experiment'
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def start(self):
        init_experiment(self.config,self.exp);return seal_protocol(self.exp)
    def test_seal_blinds_answers_and_detects_tampering(self):
        self.start();self.assertNotIn('SECRET_REVIEWER_CANARY',json.dumps(provider_inputs(self.exp)))
        self.assertIn('SECRET_REVIEWER_CANARY',(self.exp/'reference/baseline.json').read_text())
        with self.assertRaises(EvaluationError):init_experiment(self.config,self.exp)
        (self.exp/'inputs/system.json').write_text('{}')
        with self.assertRaisesRegex(EvaluationError,'changed'):verify_protocol(self.exp)
    def test_no_traversal_or_symlink_escape(self):
        self.start();(self.exp/'escape').symlink_to(self.root,target_is_directory=True)
        for value in ['../source.sqlite3','escape/source.sqlite3']:
            with self.assertRaises(EvaluationError):inside(self.exp,value)
    def test_reference_cannot_be_added_to_provider_allowlist(self):
        self.start();p=self.exp/'manifest.json';m=json.loads(p.read_text())
        m['providerInputAllowlist'].append('reference/baseline.json');p.write_text(json.dumps(m))
        with self.assertRaisesRegex(EvaluationError,'allowlist'):provider_inputs(self.exp)
    def test_credentials_not_accepted_in_provider_configuration(self):
        self.config['provider']['apiKey']='not-a-real-key'
        with self.assertRaisesRegex(EvaluationError,'credentials'):init_experiment(self.config,self.exp)


if __name__=='__main__':unittest.main()
