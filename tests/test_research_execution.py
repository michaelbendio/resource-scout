"""Synthetic execution trials: no real research, provider access or curation."""
import argparse
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package
from resource_research_agent.maintenance_cli import add_maintenance_commands, run_maintenance_command
from resource_research_agent.research_execution import ROLES, sample_categories
from resource_research_agent.scout_maintenance import MaintenanceWorkflow
from resource_research_agent.storage import ResearchStore
from tests.test_scout_improvement import fixture_package
from tests.test_scout_maintenance import result_for


def settings(rate=0, deliberate=None):
    return {'schemaVersion': 1, 'protocol': 'astra-sampled-v1', 'version': 'synthetic-v1',
            'serviceArea': 'Test County', 'sampling': {'seed': 'synthetic-fixed-seed', 'numerator': rate, 'denominator': 3},
            'deliberateCategoryIds': deliberate or [], 'modelIdentities': dict.fromkeys(ROLES)}


def response(a):
    if a['stage'].startswith('pass:'):
        r = deepcopy(a['outputContract'])
        r['assignmentSha256'] = a['assignmentSha256']
        r['researchNotes'] = 'Synthetic completed focus; no actual provider research.'
        r['observations'] = [{'summary': 'Synthetic gap', 'evidence': [], 'questions': ['Synthetic unresolved source access?']}]
    else:
        r = result_for(a)
        if a['stage'].startswith('audit:'):
            r['findings'] = [{'id': 'check', 'summary': 'Synthetic source contradiction', 'severity': 'material'}]
        if a['stage'] == 'reconcile':
            r['resolutions'] = [
                {'findingId': name + ':' + f['id'], 'status': 'resolved', 'reason': 'Synthetic independently checked disposition'}
                for name, audit in a['audits'].items() for f in audit['findings']]
            r['resolutions'] += [
                {'findingId': name + ':' + i['id'], 'status': 'resolved', 'reason': 'Synthetic comparison disposition'}
                for name, blind in a['blindResults'].items() for i in blind['items']]
    r['executionReceipt'] = {'complete': True, 'model': None,
        'contextId': a.get('dispatchContext', {}).get('contextId', 'synthetic-primary'),
        'freshContext': a['stage'].startswith('blind:'), 'isolatedInputs': True,
        'activeMinutes': 2, 'waitingMinutes': 1, 'coverageNotes': 'Synthetic scope checked; no actual research.',
        'remainingGaps': ['Synthetic gap remains'] if a['stage'].startswith('pass:') else []}
    return r


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ResearchStore(self.root / 'test.sqlite3')
        self.flow = MaintenanceWorkflow(self.store)
        self.data = fixture_package()
        self.payload = write_package(self.data, {'pdfs/guide.pdf': b'%PDF-1.4 Synthetic QA'})

    def prepare(self, config=None, resources=None, categories=None, name='Synthetic execution'):
        return self.flow.prepare(self.payload, 'Test TSO', ['r1'] if resources is None else resources,
            [] if categories is None else categories, run_name=name, historical=True,
            execution_config=config or settings())['id']

    def available(self, pid, name):
        return self.flow.record_provider(pid, self.flow.view(pid)['revision'], name, 'available',
                                        'Synthetic operator', 'Synthetic availability, no live service', 'synthetic-' + name)

    def until(self, pid, stage=None, task_id=None):
        while a := self.flow.next_assignment(pid, task_id=task_id):
            if a['stage'] == stage:
                return a
            self.flow.submit(pid, a['stage'], response(a))
            # Every completed stage must be durable in a new store/workflow.
            self.flow = MaintenanceWorkflow(ResearchStore(self.store.path))
        return None

    def mutate(self, pid, change):
        with self.store.connect() as c:
            s = json.loads(c.execute('SELECT state_json FROM scout_improvement_projects WHERE id=?', (pid,)).fetchone()[0])
            change(s)
            c.execute('UPDATE scout_improvement_projects SET state_json=? WHERE id=?', (json.dumps(s), pid))

    def test_primary_only_runs_to_research_ready_without_inventing_outside_work(self):
        pid = self.prepare()
        a = self.flow.next_assignment(pid)
        self.assertEqual(a, self.flow.next_assignment(pid))
        self.assertEqual(['primary', 'freeze', 'reconcile'], [s['stage'] for s in self.flow.view(pid)['tasks'][0]['research']])
        self.until(pid)
        v = self.flow.view(pid)
        self.assertEqual(1, v['coverage']['recheck']['completed'])
        self.assertFalse(v['items'][0]['review'])
        self.assertEqual({}, v['items'][0]['blindResults'])
        self.assertEqual({}, v['items'][0]['audits'])
        self.assertEqual('synthetic-primary', v['items'][0]['frozenResult']['executionReceipt']['contextId'])
        with self.assertRaises(ImprovementError):
            self.flow.prepare_export(pid, v['revision'])

    def test_playbook_passes_are_sealed_sequential_and_resumable(self):
        self.data['categories'].append({'id': 'employment', 'label': 'Employment', 'filters': []})
        self.payload = write_package(self.data, {'pdfs/guide.pdf': b'%PDF-1.4 Synthetic QA'})
        pid = self.prepare(resources=[], categories=['employment'])
        v = self.flow.view(pid)
        self.assertEqual(7, len(v['tasks'][0]['plan']['passes']))
        a = self.flow.next_assignment(pid)
        self.assertTrue(a['stage'].startswith('pass:'))
        self.assertEqual('employment-focused-v2', a['playbooks']['employment']['focused_research']['version'])
        with patch('resource_research_agent.research_execution.playbook_for', side_effect=AssertionError('Live guidance must not be loaded on resume')):
            self.assertEqual(a, self.flow.next_assignment(pid))
            self.until(pid)
        self.assertEqual(1, self.flow.view(pid)['coverage']['discovery']['completed'])

    def test_sampling_deterministic_ceil_separate_deliberate_and_no_reroll(self):
        ids = ['food', 'housing', 'employment', 'education', 'health', 'transport']
        self.data['categories'] = [{'id': i, 'label': i.title(), 'filters': []} for i in ids]
        self.payload = write_package(self.data, {'pdfs/guide.pdf': b'%PDF-1.4 Synthetic QA'})
        config = settings(1, ['employment'])
        pid = self.prepare(config, resources=[], categories=ids)
        v = self.flow.view(pid)
        sample = v['execution']['manifest']['sampling']
        self.assertEqual(2, len(sample['selectedCategoryIds']))
        self.assertNotIn('employment', sample['selectedCategoryIds'])
        self.assertEqual(['employment'], sample['deliberateCategoryIds'])
        self.assertEqual(pid, self.prepare(config, resources=[], categories=list(reversed(ids))))
        self.assertEqual(sample, MaintenanceWorkflow(self.store).view(pid)['execution']['manifest']['sampling'])
        self.assertEqual(sample_categories(ids, 'seed', 1, 3), sample_categories(ids[::-1], 'seed', 1, 3))
        self.assertEqual([], sample_categories(ids, 'seed', 0, 3))

    def test_unavailable_claude_does_not_complete_or_block_unrelated_category(self):
        self.data['categories'].append({'id': 'housing', 'label': 'Housing', 'filters': []})
        self.payload = write_package(self.data, {'pdfs/guide.pdf': b'%PDF-1.4 Synthetic QA'})
        pid = self.prepare(settings(deliberate=['food']), resources=[], categories=['food', 'housing'])
        self.until(pid)
        v = self.flow.view(pid)
        self.assertEqual(1, v['coverage']['discovery']['completed'])
        self.flow.record_provider(pid, v['revision'], 'Claude', 'unavailable', 'Synthetic operator', 'Synthetic limit')
        self.assertIsNone(self.flow.next_assignment(pid, researcher='Claude'))
        self.available(pid, 'Claude')
        blind = self.flow.next_assignment(pid, researcher='Claude')
        self.assertEqual('discovery:food', blind['taskId'])
        self.flow.submit(pid, blind['stage'], response(blind))
        self.until(pid)
        self.assertEqual(2, self.flow.view(pid)['coverage']['discovery']['completed'])

    def test_blind_inputs_exclude_primary_hints_questions_and_selection(self):
        self.data['resources'][0]['openQuestions'] = [{'id': 'q', 'question': 'ADMIN-SECRET', 'explanation': 'LEARNED-HINT', 'status': 'open', 'resolution': ''}]
        self.payload = write_package(self.data, {'pdfs/guide.pdf': b'%PDF-1.4 Synthetic QA'})
        pid = self.prepare(settings(deliberate=['food']))
        a = self.flow.next_assignment(pid)
        r = response(a); r['researchNotes'] = 'PRIMARY-SECRET'
        self.flow.submit(pid, 'primary', r)
        self.until(pid)
        self.available(pid, 'Claude')
        a = self.flow.next_assignment(pid, researcher='Claude')
        text = json.dumps(a)
        for forbidden in ['ADMIN-SECRET', 'LEARNED-HINT', 'PRIMARY-SECRET']:
            self.assertNotIn(forbidden, text)
        for forbidden in ['playbooks', 'passPlan', 'comparisonReasons', 'selectedCategoryIds', 'priorChecks', 'primaryResult']:
            self.assertNotIn(forbidden, a)
        self.assertEqual(self.data['resources'][0]['name'], a['target']['name'])
        bad = response(a); bad['executionReceipt']['freshContext'] = False
        with self.assertRaisesRegex(ImprovementError, 'fresh isolated'):
            self.flow.submit(pid, a['stage'], bad)
        self.flow.submit(pid, a['stage'], response(a))

    def test_whole_category_freezes_before_outside_work(self):
        pid = self.prepare(settings(deliberate=['food']), categories=['food'])
        self.available(pid, 'Claude')
        self.until(pid, task_id='recheck:r1')
        self.assertIsNone(self.flow.next_assignment(pid, researcher='Claude'))
        self.until(pid, stage='blind:Claude', task_id='discovery:food')
        self.assertIsNotNone(self.flow.next_assignment(pid, researcher='Claude', task_id='recheck:r1'))

    def test_all_three_challengers_are_targeted_after_primary_freeze(self):
        pid = self.prepare()
        for name in ('ChatGPT', 'Grok', 'Perplexity'):
            self.flow.request_challenge(pid, self.flow.view(pid)['revision'], 'recheck:r1', name, 'Synthetic operator', 'Synthetic targeted gap')
            self.available(pid, name)
        a = self.until(pid, 'audit:ChatGPT')
        frozen = deepcopy(self.flow.view(pid)['tasks'][0]['primaryFreeze'])
        self.assertEqual('Synthetic targeted gap', a['challengeReason'])
        self.flow.submit(pid, a['stage'], response(a))
        self.until(pid)
        v = self.flow.view(pid)
        self.assertEqual(frozen, v['tasks'][0]['primaryFreeze'])
        self.assertEqual({'ChatGPT', 'Grok', 'Perplexity'}, set(v['items'][0]['audits']))
        self.assertEqual(3, len(v['items'][0]['resolutions']))
        with self.assertRaisesRegex(ImprovementError, 'cannot silently'):
            self.flow.request_challenge(pid, v['revision'], 'recheck:r1', 'Grok', 'Synthetic operator', 'Different scope')

    def test_every_outside_finding_requires_disposition(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.available(pid, 'Claude')
        a = self.until(pid, 'reconcile')
        r = response(a); r['resolutions'] = []
        before = self.flow.view(pid)
        with self.assertRaisesRegex(ImprovementError, 'every audit finding'):
            self.flow.submit(pid, 'reconcile', r)
        self.assertEqual(before, self.flow.view(pid))
        self.flow.submit(pid, 'reconcile', response(a))

    def test_packet_model_context_and_scope_cannot_be_misattributed(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.available(pid, 'Claude')
        a = self.until(pid, 'blind:Claude')
        for changes in ({'complete': False}, {'contextId': 'wrong-session'}, {'activeMinutes': float('nan')}):
            r = response(a); r['executionReceipt'].update(changes)
            with self.assertRaises(ImprovementError):
                self.flow.submit(pid, a['stage'], r)
        with self.assertRaises(ImprovementError):
            self.flow.submit(pid, 'audit:Grok', response(a))
        self.flow.submit(pid, a['stage'], response(a))
        self.assertEqual(self.flow.view(pid), self.flow.submit(pid, a['stage'], response(a)))

    def test_tampered_guidance_assignment_and_frozen_result_fail_visibly(self):
        changes = [
            lambda s: s['execution']['manifest']['sampling'].update(seed='tampered'),
            lambda s: s['tasks']['recheck:r1']['assignments']['primary'].update(instructions=['tampered']),
            lambda s: s['tasks']['recheck:r1']['results']['primary'].update(researchNotes='tampered'),
            lambda s: s['tasks'].update({'discovery:food': deepcopy(s['tasks']['recheck:r1'])})]
        for i, change in enumerate(changes):
            pid = self.prepare(name=str(i)); self.until(pid)
            self.mutate(pid, change)
            with self.assertRaises(ImprovementError):
                self.flow.view(pid)

    def test_invalid_configuration_and_legacy_stop_cannot_bypass_sample(self):
        for mutate in (lambda c: c.update(protocol='unknown'), lambda c: c['sampling'].update(numerator=True),
                       lambda c: c.update(deliberateCategoryIds=['missing']), lambda c: c['modelIdentities'].update(Codex='')):
            c = settings(); mutate(c)
            with self.assertRaises(ImprovementError): self.prepare(c)
        pid = self.prepare(settings(deliberate=['food']))
        with self.assertRaises(ImprovementError):
            self.flow.stop_blind_research(pid, self.flow.view(pid)['revision'], 'Claude', 'Synthetic operator', 'Cannot bypass sampled requirement')

    def test_cli_opt_in_and_provider_and_challenge(self):
        package = self.root / 'source.zip'; package.write_bytes(self.payload)
        config = self.root / 'execution.json'; config.write_text(json.dumps(settings()))
        parser = argparse.ArgumentParser(); add_maintenance_commands(parser.add_subparsers())
        def run(argv): return run_maintenance_command(self.store, parser.parse_args(['maintain', *argv]))
        v = run(['prepare', str(package), '--office', 'Test TSO', '--run-name', 'Synthetic CLI', '--resource-id', 'r1', '--execution-config', str(config)])
        v = run(['challenge', str(v['id']), '--revision', str(v['revision']), '--task-id', 'recheck:r1', '--researcher', 'Grok', '--operator', 'Synthetic', '--reason', 'Synthetic challenge'])
        v = run(['provider', str(v['id']), '--revision', str(v['revision']), '--researcher', 'Grok', '--status', 'unavailable', '--operator', 'Synthetic', '--reason', 'Synthetic unavailable'])
        self.assertEqual('unavailable', v['providerAvailability']['Grok']['status'])

    def test_received_reply_survives_later_provider_outage(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.available(pid, 'Claude')
        a = self.until(pid, 'blind:Claude')
        self.flow.record_provider(pid, self.flow.view(pid)['revision'], 'Claude', 'unavailable', 'Synthetic operator', 'Synthetic later outage')
        self.assertIsNone(self.flow.next_assignment(pid, researcher='Claude'))
        self.flow.submit(pid, a['stage'], response(a))
        self.until(pid)
        self.assertEqual(1, self.flow.view(pid)['coverage']['recheck']['completed'])

    def test_blind_question_reaches_curator_package_without_service_approval(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.available(pid, 'Claude')
        a = self.until(pid, 'reconcile')
        r = response(a)
        r['resolutions'][0].update(status='needs-review', reason='Synthetic staff confirmation needed; no provider was contacted.')
        self.flow.submit(pid, 'reconcile', r)
        self.flow.connect_latest(pid, self.flow.view(pid)['revision'], self.payload, 'Test TSO')
        export = self.flow.prepare_question_export(pid, self.flow.view(pid)['revision'])
        package = read_package(self.flow.export_bytes(pid, export['exportId']))
        questions = package['resources']['r1']['openQuestions']
        self.assertEqual('Claude:r1', questions[0]['source']['findingId'])
        self.assertEqual('open', questions[0]['status'])
        self.assertEqual(self.data['resources'][0]['verifiedOn'], package['resources']['r1']['verifiedOn'])
        self.assertIsNone(self.flow.view(pid)['items'][0]['review'])

    def test_scope_amendment_preserves_old_sample_and_old_execution(self):
        ids = ['food', 'housing', 'employment', 'education', 'health', 'transport']
        self.data['categories'] = [{'id': i, 'label': i.title(), 'filters': []} for i in ids]
        self.payload = write_package(self.data, {'pdfs/guide.pdf': b'%PDF-1.4 Synthetic QA'})
        config = settings(1)
        pid = self.prepare(config, resources=[], categories=ids[:3])
        old = self.flow.view(pid)
        v = self.flow.prepare(self.payload, 'Test TSO', [], ids, run_name='Synthetic amendment', historical=True,
            execution_config=config, supersedes=pid, operator='Synthetic operator', change_reason='Add three categories')
        self.assertNotEqual(pid, v['id'])
        sampling = v['execution']['manifest']['sampling']
        self.assertEqual(2, len(sampling['cohorts']))
        self.assertEqual(old['execution']['manifest']['sampling']['cohorts'][0], sampling['cohorts'][0])
        self.assertEqual(old, self.flow.view(pid))
        self.assertEqual(0, v['coverage']['discovery']['completed'])
        config['sampling']['seed'] = 'reroll'
        with self.assertRaisesRegex(ImprovementError, 'original sampling'):
            self.flow.prepare(self.payload, 'Test TSO', [], ids, run_name='Bad amendment', historical=True,
                execution_config=config, supersedes=pid, operator='Synthetic operator', change_reason='Attempt reroll')

    def test_explicit_legacy_replacement_keeps_original_assignments(self):
        prior = self.flow.prepare(self.payload, 'Test TSO', ['r1'], [], run_name='Legacy', historical=True)
        assignment = self.flow.next_assignment(prior['id'])
        before = self.flow.view(prior['id'])
        new = self.flow.prepare(self.payload, 'Test TSO', ['r1'], [], run_name='Replacement', historical=True,
            execution_config=settings(), supersedes=prior['id'], operator='Synthetic operator', change_reason='New approved protocol')
        self.assertEqual(prior['id'], new['execution']['manifest']['protocolChange']['predecessorId'])
        self.assertEqual(before, self.flow.view(prior['id']))
        self.assertEqual(assignment, self.flow.next_assignment(prior['id']))

    def test_failed_result_transaction_leaves_no_half_freeze(self):
        pid = self.prepare()
        a = self.until(pid, 'freeze'); before = self.flow.view(pid)
        original = self.flow._save
        def fail_after_write(*args):
            original(*args)
            raise RuntimeError('Synthetic interruption before commit')
        with patch.object(self.flow, '_save', side_effect=fail_after_write):
            with self.assertRaisesRegex(RuntimeError, 'Synthetic interruption'):
                self.flow.submit(pid, 'freeze', response(a))
        self.assertEqual(before, self.flow.view(pid))
        self.flow.submit(pid, 'freeze', response(a))
        self.assertIsNotNone(self.flow.view(pid)['tasks'][0]['primaryFreeze'])

    def test_blind_context_cannot_reuse_primary_context(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.flow.record_provider(pid, self.flow.view(pid)['revision'], 'Claude', 'available', 'Synthetic operator',
                                  'Synthetic misleading context', 'synthetic-primary')
        a = self.until(pid, 'blind:Claude')
        with self.assertRaisesRegex(ImprovementError, 'already exposed'):
            self.flow.submit(pid, a['stage'], response(a))

    def test_protocol_guidance_is_snapshotted_before_any_assignment(self):
        from resource_research_agent.research_execution import PROTOCOL_GUIDANCE
        pid = self.prepare()
        guidance = json.loads(PROTOCOL_GUIDANCE.read_text())
        guidance['version'] = 'synthetic-changed'
        guidance['freeze'].append('SYNTHETIC-NEW-INSTRUCTION')
        path = self.root / 'guidance.json'; path.write_text(json.dumps(guidance))
        with patch('resource_research_agent.research_execution.PROTOCOL_GUIDANCE', path):
            old_freeze = self.until(pid, 'freeze')
            newer = self.prepare(name='new-guidance')
            new_freeze = self.until(newer, 'freeze')
        self.assertNotIn('SYNTHETIC-NEW-INSTRUCTION', old_freeze['instructions'])
        self.assertIn('SYNTHETIC-NEW-INSTRUCTION', new_freeze['instructions'])

    def test_operator_notes_do_not_contaminate_blind_packet(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.flow.record_provider(pid, self.flow.view(pid)['revision'], 'Claude', 'available',
            'Synthetic operator', 'PRIMARY-SECRET hinted in availability note', 'synthetic-claude')
        a = self.until(pid, 'blind:Claude')
        self.assertNotIn('PRIMARY-SECRET', json.dumps(a))

    def test_pending_status_and_timing_do_not_claim_elapsed_run_time(self):
        pid = self.prepare(settings(deliberate=['food']))
        self.until(pid)
        s = self.flow.view(pid)['executionSummary']
        self.assertEqual('not-checked', s['pendingOutsideChecks'][0]['availability'])
        self.assertEqual(4, s['researcherTiming']['Codex']['activeMinutes'])
        self.assertEqual(2, s['researcherTiming']['Codex']['waitingMinutes'])
        self.assertIn('not elapsed run time', s['timingMeaning'])


if __name__ == '__main__':
    unittest.main()
