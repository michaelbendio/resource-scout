import unittest
from copy import deepcopy
from resource_research_agent.open_questions import make_questions, attach_questions, improvement_questions
from resource_research_agent.improvement_packages import ImprovementError, read_package, write_package


class OpenQuestionTests(unittest.TestCase):
    def test_dedup_and_curator_resolution_survive_research_and_package_roundtrip(self):
        questions=make_questions([{'question':'Which program requires residency?', 'explanation':'Provider pages disagree.'}], {'kind':'writing'})
        record={'id':'r1','name':'Example','openQuestions':deepcopy(questions),'verifiedOn':'08/26'}
        record['openQuestions'][0].update(status='resolved',resolution='Staff confirmed the voucher rule.',history=[{'status':'resolved','resolution':'Staff confirmed the voucher rule.','changedAt':'2026-09-06'}])
        attach_questions(record,questions)
        self.assertEqual(1,len(record['openQuestions']))
        self.assertEqual('resolved',record['openQuestions'][0]['status'])
        package={'resourcePackageSchemaVersion':3,'packageVersion':1,'resources':[record],'categories':[],'forGroups':[]}
        saved=read_package(write_package(package,{}))['resources']['r1']
        self.assertEqual(record,saved)

    def test_scout_cannot_resolve_questions_or_erase_unknown_data(self):
        for bad in ({'question':'Why?', 'explanation':'Conflict', 'status':'resolved'}, {'question':'Why?'}, {'question':'','explanation':'Conflict'}):
            with self.assertRaises(ImprovementError):make_questions([bad],{})
        q=make_questions([{'question':'Why?', 'explanation':'Conflict'}],{})
        resource={'openQuestions':[{'futureField':'preserve'}]};attach_questions(resource,q)
        self.assertEqual({'futureField':'preserve'},resource['openQuestions'][0])
        with self.assertRaises(ImprovementError):attach_questions({'openQuestions':{}},q)

    def test_only_unresolved_findings_become_administrative_handoff(self):
        item={'results':{'audit:AI':{'findings':[{'id':'one','summary':'Check the local intake.'},{'id':'two','summary':'Already settled'}]},
                         'reconcile':{'resolutions':[{'findingId':'AI:one','status':'needs-review','reason':'The two office pages conflict.'}, {'findingId':'AI:two','status':'resolved','reason':'Corrected.'}]}}}
        q=improvement_questions(item,{'projectId':1})
        self.assertEqual(1,len(q));self.assertEqual('AI:one',q[0]['source']['findingId'])
        self.assertEqual('open',q[0]['status'])

