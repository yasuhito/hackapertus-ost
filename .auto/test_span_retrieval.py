"""Fictional fragments and actual pinned Pi/runAgent; no credentials or API."""
import copy
import itertools
import json
from pathlib import Path
import shutil
import socket
import sys

import pytest
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'track_2a/dev/format'))
import span_retrieval_contract as c
import span_retrieval_worker as w
import run_comparison as r
from test_comparison import item, response, tool


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError('network/credentials forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)


def source():
    return {'claim': 'final_verification 😀 É\n' + 'x' * 160 + '   ', 'final_verification': 'NLI select label',
            'task': 'A', 'vote': {'text': 'verbatim factual vote'}, 'languages': ['de', 'fr'],
            'source_spans': [{'span_id': 'original-1', 'page': 1, 'text': '源😀\n' + 'a' * 245},
                             {'span_id': 'original-2', 'page': 2, 'text': ' \n\t' * 90},
                             {'span_id': 'original-3', 'page': 3, 'text': ''}]}


def selection():
    return {'candidate_ids':item()['candidate_ids']}


def candidate_manifest():
    return {'variant':w.VARIANT,'strategy':'C','models':[r.MODELS[1]],
            'role_models':{'parent':r.MODELS[1],'child':r.MODELS[0]},
            'request_limit':300,'token_budget':78720000,'frozen':[item()]}


@pytest.fixture
def candidate(tmp_path,monkeypatch):
    fmt=tmp_path/'track_2a/dev/format';fmt.mkdir(parents=True)
    for path in r.HERE.iterdir():
        if path.suffix in ('.ts','.mjs','.json'): shutil.copyfile(path,fmt/path.name)
    w.install_templates(fmt);monkeypatch.setattr(r,'HERE',fmt)
    original = r.run_b
    with w.candidate_hooks(r,candidate_manifest()):
        implementation = r.run_b
        def full_stack(x, model, post, **kwargs):
            from span_retrieval_research import root_fake_request
            def guarded(role, number, payload):
                return root_fake_request(r, payload, lambda: post(role, number, payload))
            return implementation(x, model, guarded, **kwargs)
        r.run_b = full_stack
        yield r


def backend(x,calls,review=None,child_label=1):
    def post(role,number,payload):
        calls.append((role,number,copy.deepcopy(payload)))
        w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
        name=payload['tool_choice']['function']['name']
        args=({'mode':'source_only'} if name=='subagent' else
              review(number,payload) if role=='child' and review else {'candidate_ids':[]} if role=='child' else
              {'label':child_label if role=='child' else 0,'candidate_ids':x['candidate_ids']})
        return response(payload['model'],calls=[tool(name,args)])
    return post


def test_large_ascii_source_complete_sdk_packets_fit_without_factual_loss(candidate):
    x=item();data=json.loads(x['messages'][1]['content'])
    data['source_spans']=[{'span_id':f'original-span-{i:022d}','page':i//10+1,
                           'text':('alpha beta '*55)[:600]} for i in range(300)]
    x['candidate_ids']=[s['span_id'] for s in data['source_spans']]
    x['messages'][1]['content']=json.dumps(data,ensure_ascii=False)
    before=copy.deepcopy(x);calls=[]
    def post(role,number,payload):
        assert len(r.legacy.encode(payload))<=240000, 'NATIVE_PACKET_BYTE_LIMIT'
        calls.append(role);w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
        name=payload['tool_choice']['function']['name']
        args=({'mode':'source_only'} if name=='subagent' else {'candidate_ids':[data['source_spans'][0]['span_id']]} if role=='child'
              else {'label':1,'candidate_ids':[]})
        return response(payload['model'],calls=[tool(name,args)])
    args,diagnostics,sdk=r.run_b(x,r.MODELS[1],post,strategy='C',seconds=45)
    assert args=={'label':1,'candidate_ids':[]} and not diagnostics and x==before
    assert calls==['parent','child','parent']
    assert sdk['source_evidence']==c.validate({'candidate_ids':[data['source_spans'][0]['span_id']]},data)


@pytest.mark.parametrize('pair', [False, True])
def test_actual_sdk_role_projection_independence_and_delivered_counts(candidate,pair):
    x=item();data=json.loads(x['messages'][1]['content']);data['final_verification']='NLI recommendation only'
    x['messages'][1]['content']=json.dumps(data);before=copy.deepcopy(x);calls=[]
    args,diagnostics,sdk=r.run_b(x,r.MODELS[1],backend(x,calls,lambda n,p:selection() if pair else {'candidate_ids':[]}),strategy='C',seconds=45)
    assert args=={'label':0,'candidate_ids':x['candidate_ids']} and not diagnostics and x==before
    assert sdk['counts']=={'parent':2,'child':1,'reviewer':0}
    for role,_,payload in calls:
        user=next(m['content'] for m in payload['messages'] if m['role']=='user')
        assert user==(c.projection(data) if role=='child' else x['messages'][1]['content'])
        assert len(r.legacy.encode(payload))<=240000
        assert payload['model']==r.MODELS[1 if role=='parent' else 0]
    review=calls[1][2]
    assert [m['role'] for m in review['messages']]==['system','user']
    assert [t['function']['name'] for t in review['tools']]==['select_source_spans']
    assert 'NLI recommendation only' not in review['messages'][1]['content']
    delivered=sdk['review_audit']['parent_tool_reports']; assert len(delivered)==1
    assert delivered[0]['source_evidence']==sdk['source_evidence']
    assert set(delivered[0]) == {'source_evidence'}
    assert sdk['counts']['reviewer'] == 0
    assert sdk['source_evidence']['status']==('source_spans_selected' if pair else 'no_source_spans_selected')
    assert any(e['type']=='package_review_completed' and e['tools']==['select_source_spans'] for e in sdk['events'])
    assert not any(e['type'].startswith('auto_') for e in sdk['events'])


@pytest.mark.parametrize('repair',[True,False])
@pytest.mark.parametrize('bad',['unknown','malformed','duplicate','surrogate','coercible','extra'])
def test_actual_sdk_one_repair_or_explicit_unavailable(candidate,repair,bad):
    x=item();calls=[]
    def post(role,n,payload):
        value=backend(x,calls,lambda n,p:selection())(role,n,payload)
        if role=='child' and (n==0 or not repair):
            args=selection()
            if bad=='unknown': args['candidate_ids']=['unknown']
            if bad=='surrogate': args['candidate_ids']=['\ud800']
            if bad=='coercible': args['candidate_ids']=[1]
            if bad=='extra': args['label']=0
            raw='{' if bad=='malformed' else '{"candidate_ids":[],"candidate_ids":[]}' if bad=='duplicate' else json.dumps(args)
            value['choices'][0]['message']['tool_calls'][0]['function']['arguments']=raw
        return value
    args,diagnostics,sdk=r.run_b(x,r.MODELS[1],post,strategy='C',seconds=45)
    assert args and sdk['counts']['child']==2 and len(diagnostics)==(1 if repair else 2)
    assert sdk['source_evidence']['status']==('source_spans_selected' if repair else 'evidence_unavailable')
    assert sdk['review_audit']['parent_tool_reports'][0]['source_evidence']==sdk['source_evidence']


def test_actual_empty_path_still_explicit_no_pair(candidate):
    x=item();x['candidate_ids']=[];data=json.loads(x['messages'][1]['content']);data['source_spans']=[]
    x['messages'][1]['content']=json.dumps(data)
    def post(role,n,p):
        name=p['tool_choice']['function']['name']
        args={'mode':'source_only'} if name=='subagent' else {'candidate_ids':[]} if role=='child' else {'label':1,'candidate_ids':[]}
        return response(p['model'],calls=[tool(name,args)])
    args,diags,sdk=r.run_b(x,r.MODELS[1],post,strategy='C',seconds=45)
    assert args and not diags and sdk['counts']['child']==1
    assert sdk['source_evidence']['status']=='no_source_spans_selected'


def test_production_and_model_guards(candidate):
    with pytest.raises(ValueError,match='PRODUCTION'): w.install_templates(Path(__file__).resolve().parents[1]/'track_2a/dev/format')
    with pytest.raises(r.Stop):
        with w.candidate_hooks(r,{'variant':'baseline'}): pass
    x=item();r._span_view=c.inventory(json.loads(x['messages'][1]['content']))
    payload={'model':r.MODELS[0],'tools':[{'type':'function','function':{'name':'select_source_spans','description':'fictional','parameters':c.schema(r._span_view)}}],
             'tool_choice':{'type':'function','function':{'name':'select_source_spans'}}}
    r._span_user=c.projection(json.loads(x['messages'][1]['content']))
    payload['messages']=[{'role':'user','content':r._span_user}]
    w.enforce_bridge_tools(r,payload,x['candidate_ids'],'child')
    for role in ['parent','reviewer']:
        with pytest.raises(r.Stop): w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
    payload['model']=r.MODELS[1]
    with pytest.raises(r.Stop): w.enforce_bridge_tools(r,payload,x['candidate_ids'],'child')


def test_h1_feedback_unchanged_parent3_child2_and_reviewer_usage(candidate):
    x=item(); calls=[]
    def post(role, number, payload):
        calls.append((role, number, copy.deepcopy(payload)))
        name=payload['tool_choice']['function']['name']
        if name == 'subagent': args={'mode':'source_only'}
        elif name == 'select_source_spans': args={'candidate_ids':[]}
        else:
            rejected = role == 'parent' and number == 1
            args={'label':0,'candidate_ids':[] if rejected else x['candidate_ids']}
            if not rejected:
                assert r.SUPPORTING_SPAN_MESSAGE in json.dumps(payload['messages'])
        return response(payload['model'],calls=[tool(name,args)])
    accepted, diagnostics, sdk=r.run_b(x,r.MODELS[1],post,isolation_guard=True,strategy='C',seconds=45)
    assert accepted and diagnostics==['SUPPORTING_SPAN_REQUIRED']
    assert sdk['counts']=={'parent':3,'child':1,'reviewer':0}
    usage=next(e['usage'] for e in sdk['events'] if e['type']=='subagent_usage')
    assert usage['input']==80 and usage['output']==20 and usage['totalTokens']==100



def test_private_settings_written_once_exclusive_and_no_ordinary_adapter():
    text = (w.TEMPLATES / 'package-review.mjs').read_text()
    assert "writeFileSync(join(home, 'settings.json'), JSON.stringify(settings), { flag: 'wx', mode: 0o600 })" in text
    assert text.count('writeFileSync(join(home,') == 1
    assert "role: 'reviewer'" not in text
    sdk = (w.TEMPLATES / 'controlledsdk.ts').read_text()
    assert 'packageChild' not in sdk and "sessionRun('reviewer')" not in sdk
    assert sdk.count("await sessionRun('child')") == 1
    assert 'DUPLICATE_HELPER_INVOCATION' in sdk


def test_source_repair_same_private_package_session(candidate):
    x = item(); calls = []
    _, diagnostics, sdk = r.run_b(x, r.MODELS[1], backend(x, calls, lambda n,p: {'candidate_ids':[{}]} if n == 0 else selection()), strategy='C', seconds=45)
    assert diagnostics and sdk['counts'] == {'parent':2, 'child':2, 'reviewer':0}
    assert sum(e['type'] == 'package_review_started' for e in sdk['events']) == 1
    assert sum(e['type'] == 'package_review_completed' for e in sdk['events']) == 1
    assert all(e['role'] == 'child' for e in sdk['events'] if e['type'].startswith('package_'))


def test_three_hundred_distinct_fictional_inputs_six_hundred_actual_sdk_paths(candidate, monkeypatch):
    import span_retrieval_research as research
    # Do not wrap capture above Root: observe the unchanged real request path.
    monkeypatch.setattr(r, 'run_b', lambda *a, **kw: w.run_candidate(r, *a, **kw))
    original_request = r.Transport.request
    observed = []
    def request(self, method, path, payload):
        observed.append(copy.deepcopy(payload))
        return original_request(self, method, path, payload)
    monkeypatch.setattr(r.Transport, 'request', request)
    manifest = candidate_manifest()
    manifest['frozen'] = []
    users = set()
    for index in range(300):
        x = item(); x['case']['id'] = f'fictional-distinct-{index}'
        source = json.loads(x['messages'][1]['content'])
        source['claim'] += f' Fictional distinct claim {index}.'
        base=source['source_spans'][0]
        source['source_spans']=[{**base, 'text':'short'}, {**base,'span_id':f'fictional-long-{index}', 'text':'😀'*1200, 'metadata':{'order':index}}, {**base,'span_id':f'fictional-next-{index}', 'text':'源'*1200}]
        x['candidate_ids']=[span['span_id'] for span in source['source_spans']]
        x['messages'][1]['content'] = json.dumps(source, ensure_ascii=False)
        users.add(x['messages'][1]['content'])
        manifest['frozen'].append(x)
    packets = research.capture_sdk(r, manifest) + research.capture_sdk(r, manifest, populated=False)
    assert len(users) == 300
    assert len(packets) == len(observed) == 2400
    assert observed == [p['payload'] for p in packets]
    assert all(p['bytes'] <= 240000 for p in packets)
    assert [p['role'] for p in packets] == ['parent', 'child', 'child', 'parent', 'parent'] * 300 + ['parent', 'child', 'parent'] * 300
