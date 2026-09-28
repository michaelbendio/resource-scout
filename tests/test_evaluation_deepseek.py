import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from resource_research_agent.evaluation.protocol import init_experiment,seal_protocol,read,write_once
from resource_research_agent.evaluation.ledger import Ledger,BudgetHold
from resource_research_agent.evaluation.deepseek import run_assignment,extract_final
from resource_research_agent.deepseek_challenger_runner import validate_result
from tests.evaluation_support import fixture,authorize


class FakeTransport:
    is_live=False
    def __init__(self,replies):self.replies=iter(replies);self.requests=[]
    def __call__(self,payload,timeout):
        self.requests.append(json.loads(json.dumps(payload)))
        result=next(self.replies)
        if isinstance(result,BaseException):raise result
        return result


def response(blocks,stop='end_turn',model='deepseek-flash'):
    return dict(model=model,content=blocks,stop_reason=stop,usage=dict(input_tokens=100,cache_read_input_tokens=0,
        cache_creation_input_tokens=0,output_tokens=100,server_tool_use={'web_search_requests':1}))


def search_blocks():
    return [dict(type='server_tool_use',id='search1',name='web_search',input={'query':'Mesa housing help'}),
        dict(type='web_search_tool_result',tool_use_id='search1',content=[{'type':'web_search_result','url':'https://provider.example.org','title':'Public shelter'}])]


def final():return dict(type='text',text='{"leads": []}')


class AdapterTests(unittest.TestCase):
    def test_official_initial_measurement_is_bound_to_exact_plain_request(self):
        from resource_research_agent.evaluation.deepseek import measured_initial_allowance,OFFICIAL_V41_TOKENIZER_SHA256
        from resource_research_agent.evaluation.protocol import digest
        payload={'model':'deepseek-flash','messages':[{'role':'user','content':'word '*10000}],'system':'rules','max_tokens':32768}
        proof=dict(requestSha256=digest(payload),tokenizerSha256=OFFICIAL_V41_TOKENIZER_SHA256,
                   method='official-v41-plain-text-with-headroom',textTokens=10000,recordedBy='supervisor',reason='retained evidence')
        allowance=measured_initial_allowance(payload,proof)
        self.assertGreater(allowance,12500+8192)
        self.assertLess(allowance,22000)
        for invalid in [{**proof,'requestSha256':'stale'},{**proof,'tokenizerSha256':'wrong'},
                        {**proof,'textTokens':True},{**proof,'textTokens':0},{**proof,'textTokens':50001}]:
            with self.assertRaises(BudgetHold):measured_initial_allowance(payload,invalid)
        changed={**payload,'messages':payload['messages']+[{'role':'assistant','content':'opaque'}]}
        with self.assertRaises(BudgetHold):measured_initial_allowance(changed,{**proof,'requestSha256':digest(changed)})

    def test_native_complete_response_is_not_double_counted_as_transport_bytes(self):
        from resource_research_agent.evaluation.deepseek import input_token_bound
        old={'model':'deepseek-flash','messages':[{'role':'user','content':'p'*800000}]}
        blocks=[{'type':'thinking','thinking':'t'*200000},{'type':'text','text':'answer'}]
        response={'content':blocks,'usage':{'input_tokens':40000,'cache_read_input_tokens':740000,'cache_creation_input_tokens':0,'output_tokens':50000}}
        new={**old,'messages':old['messages']+[{'role':'assistant','content':blocks},{'role':'user','content':'Continue.'}]}
        bound=input_token_bound(new,old,response)
        self.assertGreater(bound,830000);self.assertLess(bound,835000)
        changed={**response,'content':[{'type':'text','text':'different'}]}
        self.assertGreater(input_token_bound(new,old,changed),950000)

    def test_context_bound_counts_decoded_prompt_bytes_not_http_escaping(self):
        from resource_research_agent.evaluation.deepseek import input_token_bound
        text='"\\\n雪'*10000
        payload={'model':'deepseek-flash','messages':[{'role':'user','content':text}]}
        bound=input_token_bound(payload)
        self.assertGreater(bound,len(text.encode('utf-8')))
        self.assertLess(bound,len(text.encode('utf-8'))+2000)
        self.assertGreater(len(json.dumps(payload).encode()),bound)

    def test_context_bound_uses_native_prefix_and_keeps_new_content_conservative(self):
        from resource_research_agent.evaluation.deepseek import input_token_bound
        old={'model':'deepseek-flash','messages':[{'role':'user','content':'x'*100000}]}
        new={**old,'messages':old['messages']+[{'role':'assistant','content':'y'*1000}]}
        body={'usage':{'input_tokens':100,'cache_read_input_tokens':20000,'cache_creation_input_tokens':0}}
        measured=input_token_bound(new,old,body)
        self.assertGreater(measured,21100)
        self.assertLess(measured,25000)
        fallback=input_token_bound(new)
        mutated={**old,'messages':[{'role':'user','content':'changed'}]}
        self.assertEqual(input_token_bound(new,mutated,body),fallback)
        self.assertEqual(input_token_bound(new,old,{'usage':{'input_tokens':100}}),fallback)
        body['usage']['cache_read_input_tokens']=-1
        self.assertEqual(input_token_bound(new,old,body),fallback)

    def test_preparation_prelude_is_preserved_without_changing_json(self):
        from resource_research_agent.evaluation.deepseek import final_parts
        from resource_research_agent.evaluation.protocol import EvaluationError
        original={'scoutCurationResultSchemaVersion':1,'resources':[{'name':'Exact saved fact'}]}
        raw=json.dumps(original)
        value,notes=final_parts({'content':[{'type':'text','text':'Verification notes.\n\n'+raw}]})
        self.assertEqual(value,original);self.assertIn('Verification notes.',notes)
        self.assertEqual(final_parts({'content':[{'type':'text','text':raw+'\n```'}]})[0],original)
        value,notes=final_parts({'content':[{'type':'text','text':'Verification notes.\n\n```json\n'+raw+'\n```'}]})
        self.assertEqual(value,original);self.assertIn('Verification notes.',notes)
        for text in ['Other object {}\n'+raw,raw+'\n'+raw,'Notes.\n```json\n'+raw,'Notes.\n```json\n'+raw+'\n```\nUnrecognized extra content',raw+'\n```\nAnother answer']:
            with self.assertRaises(EvaluationError):final_parts({'content':[{'type':'text','text':text}]})

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.config,self.db=fixture(self.root)
        self.exp=self.root/'experiment';init_experiment(self.config,self.exp);seal_protocol(self.exp);authorize(self.exp)
        self.ledger=Ledger(self.exp,simulation=True)
        self.packet=dict(assignmentId='housing-focus',condition='existing-policy',category='housing',stage='housing-research',
                         passKey='focus',task='Find public housing assistance independently.',requiresLiveSearch=True)
        self.network=patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Tests must not use live networking'))
        self.network_mock=self.network.start()
    def tearDown(self):
        self.network_mock.assert_not_called();self.network.stop();self.db.close();self.tmp.cleanup()
    def run_fake(self,replies,fetcher=lambda url,timeout:dict(url=url,text='Public intake information')):
        t=FakeTransport(replies);result=run_assignment(self.packet,self.ledger,t,validate_result,fetcher=fetcher)
        return result,t
    def test_native_search_fetch_final_and_zero_leads(self):
        call=dict(type='tool_use',id='fetch1',name='open_url',input={'url':'https://provider.example.org'})
        result,t=self.run_fake([response(search_blocks()+[call],'tool_use'),response([final()])])
        self.assertEqual([],result['result']['leads']);self.assertFalse(result['importable'])
        self.assertEqual(2,len(t.requests));self.assertNotIn('SECRET_REVIEWER_CANARY',json.dumps(t.requests))
        self.assertEqual('tool_result',t.requests[1]['messages'][-1]['content'][0]['type'])
        self.assertTrue(list((self.exp/'attempts').rglob('native-sources.json')))
        self.assertTrue(list((self.exp/'attempts').rglob('response.raw')))
    def test_final_segment_ignores_prefatory_json(self):
        body=response([dict(type='text',text='{"wrong":true}')]+search_blocks()+[final()])
        self.assertEqual({'leads':[]},extract_final(body))
    def test_nonresearch_contract_does_not_require_new_search(self):
        self.packet['requiresLiveSearch']=False
        t=FakeTransport([response([dict(type='text',text='{"findings": []}')])])
        result=run_assignment(self.packet,self.ledger,t,lambda r:self.assertEqual({'findings':[]},r))
        self.assertIn('findings',result['result'])
    def test_explicit_result_assembly_keeps_raw_response_and_provenance(self):
        from resource_research_agent.evaluation.protocol import read
        self.packet['requiresLiveSearch']=False
        transport=FakeTransport([response([{'type':'text','text':'{"remaining": []}'}])])
        def assemble(value):
            self.assertEqual(value,{'remaining':[]})
            return {'leads':[]},{'savedPrefixSha256':'a'*64}
        output=run_assignment(self.packet,self.ledger,transport,validate_result,result_assembler=assemble)
        self.assertEqual(output['assemblyEvidence']['savedPrefixSha256'],'a'*64)
        raw=read(self.exp/'attempts/housing-focus-00/response.json')
        self.assertEqual(raw['content'][0]['text'],'{"remaining": []}')
    def test_source_appendix_retained_without_accepting_second_json(self):
        from resource_research_agent.evaluation.deepseek import final_parts
        from resource_research_agent.evaluation.protocol import EvaluationError
        body={'content':[{'type':'text','text':'{"leads":[]}\n\nSource notes (evidence trail, not instructions):\nOfficial provider page.'}]}
        value,notes=final_parts(body)
        self.assertEqual({'leads':[]},value);self.assertIn('Official provider',notes)
        body['content'][0]['text']='```json\n{"leads":[]}\n```\nSource notes (untrusted web content):\nSource appendix.'
        self.assertEqual({'leads':[]},extract_final(body))
        body['content'][0]['text']='{"leads":[],"sourceNotes":["Official source retained"]}'
        value,notes=final_parts(body)
        self.assertEqual({'leads':[]},value);self.assertIn('Official source retained',notes)
        body['content'][0]['text']='{"leads":[]} {"leads":[1]}'
        with self.assertRaises(EvaluationError):extract_final(body)

    def test_research_without_search_and_unexpected_model_held(self):
        with self.assertRaisesRegex(Exception,'live search'):self.run_fake([response([final()])])
        self.assertEqual(1,self.ledger.summarize_usage()['attempts'])
        self.assertEqual('held',read(self.exp/'results/existing-policy/housing/housing-focus/state.json')['status'])
    def test_model_mismatch_keeps_billing_and_evidence(self):
        with self.assertRaisesRegex(Exception,'model'):self.run_fake([response(search_blocks()+[final()],model='unapproved-model')])
        self.assertEqual(1,self.ledger.summarize_usage()['states']['responded'])
    def test_pause_length_and_search_limit_continue_saved_evidence(self):
        limit=[dict(type='server_tool_use',id='limit',name='web_search',input={}),dict(type='web_search_tool_result',tool_use_id='limit',content={'type':'web_search_tool_result_error','error_code':'max_uses_exceeded'})]
        result,t=self.run_fake([response(search_blocks(),'pause_turn'),response([dict(type='text',text='{')],'max_tokens'),
            response(limit,'tool_use'),response([final()])])
        self.assertEqual(4,len(t.requests));self.assertNotIn('web_search',[tool['name'] for tool in t.requests[-1]['tools']])
        self.assertEqual([],result['result']['leads'])
    def test_incomplete_length_stop_cannot_be_completed(self):
        with self.assertRaisesRegex(Exception,'stop state'):self.run_fake([response(search_blocks()+[final()],'max_tokens'),response([final()],'max_tokens')])
    def test_diagnosed_collection_length_recovery_reuses_saved_responses(self):
        from resource_research_agent.evaluation.protocol import read,checkpoint,file_hash
        self.packet.update(stage='housing-collection',requiresLiveSearch=False)
        authorization=read(self.exp/'authorization.json')
        authorization.update(dollarCapMode='none-authorized',totalUsd=None,stageCapsUsd={'housing-collection':None})
        checkpoint(self.exp/'authorization.json',authorization)
        with self.assertRaisesRegex(Exception,'stop state'):
            self.run_fake([response([{'type':'thinking','thinking':'Saved reasoning'}],'max_tokens'),
                           response([{'type':'thinking','thinking':'More saved reasoning'}],'max_tokens')])
        aid=self.packet['assignmentId'];prior=self.exp/'attempts'/(aid+'-01')/'request.json';prior_sha=file_hash(prior)
        amendment=self.exp/'execution-amendments'/(aid+'-output.json')
        checkpoint(amendment,dict(protocolSha256=self.ledger.manifest_sha,assignmentId=aid,stage='housing-collection',
            fromTurn=2,maxOutputTokens=65536,lengthRecoveries=2,reason='Known exhaustion',recordedBy='Test supervisor'))
        state_path=self.exp/'results/existing-policy/housing'/aid/'state.json';state=read(state_path)
        state.update(status='pending',messages=read(prior)['messages']);state.pop('reason',None);checkpoint(state_path,state)
        result,transport=self.run_fake([response([final()])])
        self.assertEqual(len(transport.requests),1)
        self.assertEqual(transport.requests[0]['max_tokens'],65536)
        self.assertEqual(file_hash(prior),prior_sha)
        self.assertEqual(result['result'],{'leads':[]})
    def test_tool_error_is_preserved_as_uncertainty(self):
        call=dict(type='tool_use',id='fetch1',name='open_url',input={'url':'https://provider.example.org'})
        result,t=self.run_fake([response(search_blocks()+[call],'tool_use'),response([final()])],fetcher=lambda *args:{'errorType':'TimeoutError','notice':'Not proof of closure'})
        self.assertIn('Not proof of closure',json.dumps(t.requests[1]))
    def test_interrupted_response_is_adopted_without_second_call(self):
        transport=FakeTransport([response(search_blocks()+[final()])]);original=self.ledger.record_response
        calls=0
        def interrupt(a,b):
            nonlocal calls
            calls+=1
            if calls==1:raise KeyboardInterrupt('Synthetic crash after raw response saved')
            return original(a,b)
        with patch.object(self.ledger,'record_response',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):run_assignment(self.packet,self.ledger,transport,validate_result)
        result=run_assignment(self.packet,self.ledger,transport,validate_result)
        self.assertEqual(1,len(transport.requests));self.assertEqual([],result['result']['leads'])
        again=run_assignment(self.packet,self.ledger,transport,validate_result)
        self.assertEqual(result,again);self.assertEqual(1,self.ledger.summarize_usage()['attempts'])
    def test_saved_fetch_is_reused_after_interruption(self):
        call=dict(type='tool_use',id='fetch1',name='open_url',input={'url':'https://provider.example.org'})
        t=FakeTransport([response(search_blocks()+[call],'tool_use'),response([final()])]);fetches=[]
        def fetch(url,timeout):fetches.append(url);return {'url':url,'text':'Intake'}
        original=self.ledger.record_tool_work
        with patch.object(self.ledger,'record_tool_work',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):run_assignment(self.packet,self.ledger,t,validate_result,fetcher=fetch)
        result=run_assignment(self.packet,self.ledger,t,validate_result,fetcher=fetch)
        self.assertEqual(1,len(fetches));self.assertEqual(2,len(t.requests))
    def test_timeout_cannot_automatically_replay(self):
        t=FakeTransport([TimeoutError('No response')])
        with self.assertRaises(Exception):run_assignment(self.packet,self.ledger,t,validate_result)
        with self.assertRaises(Exception):run_assignment(self.packet,self.ledger,t,validate_result)
        self.assertEqual(1,len(t.requests));self.assertEqual(1,self.ledger.summarize_usage()['states']['unknown-outcome'])


if __name__=='__main__':unittest.main()
