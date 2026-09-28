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
        resource={'openQuestions':deepcopy(q)};resource['openQuestions'][0]['futureField']='preserve';attach_questions(resource,q)
        self.assertEqual('preserve',resource['openQuestions'][0]['futureField'])
        with self.assertRaises(ImprovementError):attach_questions({'openQuestions':{}},q)

    def test_only_unresolved_findings_become_administrative_handoff(self):
        item={'results':{'audit:AI':{'findings':[{'id':'one','summary':'Check the local intake.'},{'id':'two','summary':'Already settled'}]},
                         'reconcile':{'resolutions':[{'findingId':'AI:one','status':'needs-review','reason':'The two office pages conflict.'}, {'findingId':'AI:two','status':'resolved','reason':'Corrected.'}]}}}
        q=improvement_questions(item,{'projectId':1})
        self.assertEqual(1,len(q));self.assertEqual('AI:one',q[0]['source']['findingId'])
        self.assertEqual('open',q[0]['status'])


    def test_invalid_questions_fail_package_intake_without_silently_dropping_data(self):
        q=make_questions([{'question':'Why?', 'explanation':'Conflict'}],{})[0]
        for bad in (None, {}, [None], [{'futureField':'hidden'}], [q,q], [{**q,'status':'unknown'}],
                    [{**q,'history':[None]}], [{**q,'status':'resolved','resolution':''}],
                    [{**q,'id':[]}], [{**q,'history':[{'status':'open','resolution':'','changedAt':'not a date'}]}]):
            package={'packageVersion':1,'resources':[{'id':'r','openQuestions':bad}], 'categories':[], 'forGroups':[]}
            with self.subTest(bad=bad), self.assertRaises(ImprovementError):
                read_package(write_package(package,{}))

    def test_repeated_pairs_deduplicate_and_category_union_keeps_all_questions(self):
        from resource_research_agent.scout_curation import _completed_resources
        pair={'question':'Why?', 'explanation':'Conflict'}
        one=make_questions([pair,pair],{})
        self.assertEqual(1,len(one))
        two=make_questions([{'question':'Where?', 'explanation':'Two offices'}],{})
        rows=[{'id':'r','categories':['a'],'openQuestions':one}, {'id':'r','categories':['b'],'openQuestions':two}]
        result=_completed_resources({'categories':[{'result':{'resources':[row]}} for row in rows]})
        self.assertEqual({'Why?','Where?'},{q['question'] for q in result[0]['openQuestions']})
        self.assertEqual(['a','b'],result[0]['categories'])

    def test_same_id_different_text_is_not_silently_accepted(self):
        one=make_questions([{'question':'Why?', 'explanation':'Conflict'}],{})
        resource={'openQuestions':deepcopy(one)}
        one[0]['question']='Different question'
        with self.assertRaises(ImprovementError):attach_questions(resource,one)
        self.assertEqual('Why?',resource['openQuestions'][0]['question'])
