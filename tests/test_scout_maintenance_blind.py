"""Synthetic protocol checks; no provider calls or real research outcomes."""
import argparse
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from resource_research_agent.codex_first_research import (
    load_researcher_roster, prepare_codex_first_plan, validate_researcher_roster,
)
from resource_research_agent.improvement_packages import ImprovementError, digest, write_package
from resource_research_agent.maintenance_cli import add_maintenance_commands, run_maintenance_command
from resource_research_agent.scout_maintenance import BLIND_ROSTER, MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for


class MaintenanceBlindTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = ResearchStore(self.root / 'test.sqlite3')
        self.flow = MaintenanceWorkflow(self.store)
        self.payload = write_package(fixture_package(), {'pdfs/guide.pdf': b'%PDF-1.4 synthetic QA only'})
        self.pid = self.flow.prepare(self.payload, 'Test TSO', ['r1'], ['food'],
            run_name='Synthetic blind QA', historical=True, blind_comparison=True)['id']

    def response(self, a, status='moved'):
        result = result_for(a, status)
        if a['stage'] == 'primary':
            result['researchNotes'] = 'Synthetic PRIMARY-SECRET must not enter blind assignment.'
        if a['stage'] == 'audit:ChatGPT':
            result['findings'] = [{'id': 'check', 'summary': 'Synthetic AUDIT-SECRET.', 'severity': 'material'}]
        if 'resolutions' in result:
            ids = [name + ':' + f['id'] for name, r in a['audits'].items() for f in r['findings']]
            ids += [name + ':' + i['id'] for name, r in a.get('blindResults', {}).items() for i in r['items']]
            result['resolutions'] = [{'findingId': fid, 'status': 'resolved', 'reason': 'Synthetic evidence comparison; retain the supported item.'} for fid in ids]
        return result

    def complete_preblind(self, task_id=None):
        while a := self.flow.next_assignment(self.pid, task_id=task_id):
            if a['stage'].startswith('blind:'):
                return a
            self.assertNotEqual('reconcile', a['stage'])
            self.flow.submit(self.pid, a['stage'], self.response(a))
        return None

    def test_whole_batch_freeze_precedes_blind_assignment_and_final_output(self):
        self.assertIsNone(self.flow.next_assignment(self.pid, researcher='Claude'))
        self.complete_preblind('recheck:r1')
        self.assertIsNone(self.flow.next_assignment(self.pid, researcher='Claude'))
        self.assertIsNone(self.flow.view(self.pid)['blindFreeze'])
        self.assertEqual([], self.flow.view(self.pid)['items'])
        blind = self.complete_preblind()
        view = self.flow.view(self.pid)
        frozen = deepcopy(view['blindFreeze'])
        self.assertEqual(digest(frozen['manifest']), frozen['manifestSha256'])
        self.assertEqual({'recheck:r1', 'discovery:food'}, set(frozen['manifest']['tasks']))
        self.assertEqual(0, view['coverage']['recheck']['completed'])
        self.assertIsNone(self.flow.next_assignment(self.pid, researcher='Codex'))
        self.assertEqual(blind, MaintenanceWorkflow(ResearchStore(self.store.path)).next_assignment(self.pid, researcher='Claude'))
        encoded = json.dumps(blind)
        for forbidden in ('PRIMARY-SECRET', 'AUDIT-SECRET', 'primaryResult', 'frozenResult', 'priorChecks', 'blindResults'):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual('blind:Claude', blind['stage'])
        self.assertEqual('r1', blind['target']['id'])
        self.assertEqual(2, len(blind['knownIdentities']))
        self.flow.submit(self.pid, blind['stage'], self.response(blind))
        final = self.flow.next_assignment(self.pid, researcher='Codex', task_id=blind['taskId'])
        self.assertEqual('reconcile', final['stage'])
        self.assertEqual(frozen, final['blindFreeze'])
        self.assertIn('PRIMARY-SECRET', final['primaryResult']['researchNotes'])
        self.assertIn('Claude', final['blindResults'])
        result = self.response(final)
        incomplete = deepcopy(result)
        incomplete['resolutions'] = [r for r in result['resolutions'] if not r['findingId'].startswith('Claude:')]
        with self.assertRaisesRegex(ImprovementError, 'every audit finding'):
            self.flow.submit(self.pid, 'reconcile', incomplete)
        self.flow.submit(self.pid, 'reconcile', result)
        self.assertEqual(frozen, self.flow.view(self.pid)['blindFreeze'])
        row = self.flow.view(self.pid)['items'][0]
        self.assertEqual(frozen['manifestSha256'], row['blindFreezeSha256'])
        self.assertIn('Claude:r1', row['findings'])
        self.assertEqual(1, self.flow.view(self.pid)['coverage']['recheck']['completed'])
        self.assertEqual(0, self.flow.view(self.pid)['coverage']['discovery']['completed'])
        blind2 = self.flow.next_assignment(self.pid, researcher='Claude')
        self.flow.submit(self.pid, blind2['stage'], self.response(blind2))
        final2 = self.flow.next_assignment(self.pid, researcher='Codex')
        self.flow.submit(self.pid, final2['stage'], self.response(final2))
        self.assertEqual(1, self.flow.view(self.pid)['coverage']['discovery']['completed'])

    def test_frozen_results_are_immutable_and_manifest_drift_blocks_reveal(self):
        self.complete_preblind()
        with self.store.connect() as c:
            state = json.loads(c.execute('SELECT state_json FROM scout_improvement_projects WHERE id=?', (self.pid,)).fetchone()[0])
        original = state['tasks']['recheck:r1']['results']['freeze']
        changed = deepcopy(original)
        changed['researchNotes'] += ' Changed.'
        with self.assertRaisesRegex(ImprovementError, 'cannot be overwritten'):
            self.flow.submit(self.pid, 'freeze', changed)
        before = self.flow.view(self.pid)
        self.assertEqual(before, self.flow.submit(self.pid, 'freeze', original))
        # Simulate damaged persisted state; the API must refuse to expose blind work.
        state['tasks']['recheck:r1']['results']['freeze'] = changed
        with self.store.connect() as c:
            c.execute('UPDATE scout_improvement_projects SET state_json=? WHERE id=?', (json.dumps(state), self.pid))
        with self.assertRaisesRegex(ImprovementError, 'frozen pre-blind research has changed'):
            self.flow.next_assignment(self.pid, researcher='Claude')

    def test_legacy_runs_and_rosters_keep_their_original_stages(self):
        old = self.flow.prepare(self.payload, 'Test TSO', ['r1'], ['food'], run_name='Synthetic blind QA', historical=True)
        self.assertNotEqual(self.pid, old['id'])
        self.assertNotIn('blindFreeze', old)
        self.assertEqual(['primary', 'audit:ChatGPT', 'audit:Grok', 'audit:Perplexity', 'reconcile'],
                         [r['stage'] for r in old['tasks'][0]['research']])
        roster = load_researcher_roster(BLIND_ROSTER)
        self.assertEqual('blind', roster['researchers'][-1]['role'])
        with self.assertRaises(RuntimeError):
            validate_researcher_roster({**roster, 'schemaVersion': 1})
        with self.assertRaisesRegex(ValueError, 'v2 maintenance workflow'):
            prepare_codex_first_plan(self.store, 1, roster=roster)

    def test_modified_manifest_blocks_blind_assignment(self):
        self.complete_preblind()
        with self.store.connect() as c:
            state = json.loads(c.execute('SELECT state_json FROM scout_improvement_projects WHERE id=?', (self.pid,)).fetchone()[0])
            state['blindFreeze']['manifest']['baseSha256'] = 'damaged'
            c.execute('UPDATE scout_improvement_projects SET state_json=? WHERE id=?', (json.dumps(state), self.pid))
        with self.assertRaisesRegex(ImprovementError, 'frozen pre-blind research has changed'):
            self.flow.next_assignment(self.pid, researcher='Claude')

    def test_blind_closure_check_is_required_before_final_retirement_proposal(self):
        self.pid = self.flow.prepare(self.payload, 'Test TSO', ['r1'], [],
            run_name='Synthetic closure QA', historical=True, blind_comparison=True)['id']
        while a := self.flow.next_assignment(self.pid):
            if a['stage'].startswith('blind:'):
                break
            self.flow.submit(self.pid, a['stage'], self.response(a, 'possibly-closed'))
        self.flow.submit(self.pid, a['stage'], self.response(a, 'inconclusive'))
        final = self.flow.next_assignment(self.pid)
        with self.assertRaisesRegex(ImprovementError, 'blind researcher to check'):
            self.flow.submit(self.pid, 'reconcile', self.response(final, 'possibly-closed'))
        self.flow.submit(self.pid, 'reconcile', self.response(final, 'inconclusive'))
        self.assertEqual('inconclusive', self.flow.view(self.pid)['items'][0]['status'])

    def test_cli_opt_in_is_durable(self):
        package = self.root / 'source.zip'
        package.write_bytes(self.payload)
        parser = argparse.ArgumentParser()
        add_maintenance_commands(parser.add_subparsers())
        args = parser.parse_args(['maintain', 'prepare', str(package), '--office', 'Test TSO',
            '--run-name', 'CLI blind QA', '--resource-id', 'r1', '--blind-comparison'])
        view = run_maintenance_command(self.store, args)
        self.assertIn('blindComparisonPolicy', view)
        self.assertIn('blind:Claude', [r['stage'] for r in view['tasks'][0]['research']])
