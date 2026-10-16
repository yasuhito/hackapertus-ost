"""Fictional-only actual pinned SDK -> unchanged Root -> fake HTTP tests."""
import copy
import json
from pathlib import Path
import shutil
import socket
import sys
import pytest
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'track_2a/dev/format'))
import span_retrieval_contract as c
import dual_evidence_worker as w
import dual_evidence_research as research
import run_comparison as r
from test_comparison import item,response,tool

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a,**kw): raise AssertionError('network/credentials forbidden')
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(r.legacy.c,'read_key',forbidden)

def source():
    return {'claim':'Complete claim 😀 É\n'+'x'*160+'   ', 'final_verification':'NLI only',
            'task':'A','vote':{'text':'verbatim factual vote'},'languages':['de','fr'],
            'source_spans':[{'span_id':'original-1','page':1,'text':'源😀\n'+'a'*245},
                            {'span_id':'original-2','page':2,'text':' \n\t'*90},
                            {'span_id':'original-3','page':3,'text':''}]}

def selection(): return {'candidate_ids':item()['candidate_ids']}

def candidate_manifest():
    return {'variant':w.VARIANT,'strategy':'C','models':[r.MODELS[1]],
            'role_models':{'parent':r.MODELS[1],'child':r.MODELS[0],'reviewer':r.MODELS[0]},
            'request_limit':300,'token_budget':78720000,'frozen':[item()]}

@pytest.fixture
def candidate(tmp_path,monkeypatch):
    fmt=tmp_path/'track_2a/dev/format';fmt.mkdir(parents=True)
    for path in r.HERE.iterdir():
        if path.suffix in ('.ts','.mjs','.json'): shutil.copyfile(path,fmt/path.name)
    w.install_templates(fmt);monkeypatch.setattr(r,'HERE',fmt)
    with w.candidate_hooks(r,candidate_manifest()):
        implementation=r.run_b
        def full_stack(x,model,post,**kw):
            def guarded(role,n,payload):
                return research.root_fake_request(r,payload,lambda:post(role,n,payload))
            return implementation(x,model,guarded,**kw)
        r.run_b=full_stack
        yield r

def backend(x,calls,review=None,child_label=1):
    def post(role,n,payload):
        calls.append((role,n,copy.deepcopy(payload)))
        w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
        name=payload['tool_choice']['function']['name']
        args=({'mode':'source_only'} if name=='subagent' else
              (review(n,payload) if review else {'candidate_ids':[]}) if role=='reviewer' else
              {'label':child_label,'candidate_ids':[]} if role=='child' else
              {'label':0,'candidate_ids':x['candidate_ids']})
        return response(payload['model'],calls=[tool(name,args)])
    return post

@pytest.mark.parametrize('selected',[True,False])
def test_exact_advice_full_source_and_independence(candidate,selected):
    x=item();src=json.loads(x['messages'][1]['content']);src['final_verification']='original NLI retained'
    x['messages'][1]['content']=json.dumps(src);before=copy.deepcopy(x);calls=[]
    args,diags,sdk=r.run_b(x,r.MODELS[1],backend(x,calls,lambda n,p:selection() if selected else {'candidate_ids':[]}),strategy='C')
    assert args=={'label':0,'candidate_ids':x['candidate_ids']} and not diags and before==x
    assert sdk['counts']=={'parent':2,'child':1,'reviewer':1}
    normal={'label':1,'candidate_ids':[]}
    report={'recommendation':normal,'source_evidence':c.validate(selection() if selected else {'candidate_ids':[]},src)}
    assert sdk['review_audit']['parent_tool_reports']==[report]
    assert sdk['review_audit']['normal_child_recommendation']==normal
    for role,n,p in calls:
        assert p['model']==r.MODELS[1 if role=='parent' else 0]
        users=[m for m in p['messages'] if m['role']=='user']
        assert users==[{'role':'user','content':c.projection(src) if role=='reviewer' else x['messages'][1]['content']}]
        if role!='parent' and n==0: assert [m['role'] for m in p['messages']]==['system','user']
        if role=='reviewer': assert c.REVIEW_SYSTEM in p['messages'][0]['content']
    assert [e['type'] for e in sdk['events']].count('package_child_started')==1
    assert [e['type'] for e in sdk['events']].count('package_review_started')==1
    u=next(e['usage'] for e in sdk['events'] if e['type']=='subagent_usage')
    assert u['totalTokens']==200 and u['input']==160 and u['output']==40

@pytest.mark.parametrize('repair',[True,False])
@pytest.mark.parametrize('bad',['unknown','malformed','duplicate','surrogate','coercible','extra'])
def test_raw_before_sdk_and_one_same_session_repair(candidate,repair,bad):
    x=item();calls=[]
    def post(role,n,p):
        value=backend(x,calls,lambda n,p:selection())(role,n,p)
        if role=='reviewer' and (n==0 or not repair):
            a=selection()
            if bad=='unknown':a['candidate_ids']=['unknown']
            if bad=='surrogate':a['candidate_ids']=['\ud800']
            if bad=='coercible':a['candidate_ids']=[1]
            if bad=='extra':a['label']=0
            raw='{' if bad=='malformed' else '{"candidate_ids":[],"candidate_ids":[]}' if bad=='duplicate' else json.dumps(a)
            value['choices'][0]['message']['tool_calls'][0]['function']['arguments']=raw
        return value
    args,diags,sdk=r.run_b(x,r.MODELS[1],post,strategy='C')
    assert args and len(diags)==(1 if repair else 2)
    assert sdk['counts']['reviewer']==2
    assert sdk['source_evidence']['status']==('source_spans_selected' if repair else 'evidence_unavailable')
    assert sum(e['type']=='package_review_started' for e in sdk['events'])==1
    assert sum(e['type']=='package_review_completed' for e in sdk['events'])==1
    if not repair: assert sdk['source_evidence']==c.unavailable(sdk['source_evidence']['reason'])


def test_honest_no_child_advice_never_synthesized(candidate):
    x=item();calls=[]
    def post(role,n,p):
        value=backend(x,calls)(role,n,p)
        if role=='child':value['choices'][0]['message']['tool_calls'][0]['function']['arguments']='{"label":"1","candidate_ids":[]}'
        return value
    args,diags,sdk=r.run_b(x,r.MODELS[1],post,strategy='C')
    assert args and sdk['review_audit']['normal_child_recommendation'] is None
    assert sdk['review_audit']['parent_tool_reports'][0]['recommendation']=={'status':'recommendation_unavailable','reason':'NO_CHILD_SUBMIT'}
    assert sdk['source_evidence']['status']=='no_source_spans_selected'


def test_private_bootstrap_once_readonly_reviewer_and_cleanup():
    ordinary=(r.HERE/'package-child.mjs').read_text()
    review=(w.TEMPLATES/'package-review.mjs').read_text()
    assert "{ mode: 0o600, flag: 'wx' }" in ordinary
    assert 'writeFileSync' not in review and "readFileSync(join(home, 'settings.json'), 'utf8') !== JSON.stringify(settings)" in review
    assert 'delete globalThis[symbol]; hook.deregister();' in review
    assert "types?.registerAgents(new Map())" in review
    sdk=(w.TEMPLATES/'controlledsdk.ts').read_text()
    assert sdk.count("await sessionRun('child')")==sdk.count("await sessionRun('reviewer')")==1
    assert sdk.index("await sessionRun('child')")<sdk.index("await sessionRun('reviewer')")
    assert 'DUPLICATE_HELPER_INVOCATION' in sdk
    # The normal child is the exact pinned ordinary adapter, not a new template.
    assert not (w.TEMPLATES/'package-child.mjs').exists()


def test_ordinary_child_native_system_user_repair_exact_baseline(candidate,monkeypatch):
    x=item();dual=[];base=[]
    def capture(target):
        def post(role,n,p):
            target.append((role,n,copy.deepcopy(p)))
            name=p['tool_choice']['function']['name']
            a={'mode':'source_only'} if name=='subagent' else {'candidate_ids':[]} if role=='reviewer' else {'label':1,'candidate_ids':[]}
            v=response(p['model'],calls=[tool(name,a)])
            if role=='child' and n==0:v['choices'][0]['message']['tool_calls'][0]['function']['arguments']='{"label":1,"label":1,"candidate_ids":[]}'
            return v
        return post
    r.run_b(x,r.MODELS[1],capture(dual),strategy='C')
    # Baseline run_b function source is loaded in its own original module and SDK.
    core=research.module(research.ROOT/research.RUNNER)
    baseline_post=capture(base)
    def baseline_root(role,n,payload):
        return research.root_fake_request(core,payload,lambda:baseline_post(role,n,payload))
    core.run_b(x,core.MODELS[1],baseline_root,strategy='C')
    assert [p for role,n,p in dual if role=='child']==[p for role,n,p in base if role=='child']


def test_300_distinct_fictional_inputs_five_workspaces_600_sdk_paths(tmp_path,monkeypatch):
    observed=[];original=r.Transport.request
    def request(self,method,path,payload):
        observed.append(copy.deepcopy(payload));return original(self,method,path,payload)
    monkeypatch.setattr(r.Transport,'request',request)
    users=set();all_packets=[];production_format=r.HERE
    for workspace in range(5):
        fmt=tmp_path/f'w{workspace}'/'track_2a/dev/format';fmt.mkdir(parents=True)
        for path in production_format.iterdir():
            if path.suffix in ('.ts','.mjs','.json'):shutil.copyfile(path,fmt/path.name)
        w.install_templates(fmt)
        manifest=candidate_manifest();manifest['frozen']=[]
        for i in range(60):
            index=workspace*60+i;x=item();x['case']['id']=f'fictional-{index}'
            src=json.loads(x['messages'][1]['content']);src['claim']+=f' Fictional distinct {index}.'
            src['final_verification']='ordinary NLI only'
            base=src['source_spans'][0]
            src['source_spans']=[{**base,'text':'short'},
                {**base,'span_id':f'escaped-"\\\n😀-{index}','text':'"'*1200,'metadata':{'escaped':'\\\n"'*200}},
                {**base,'span_id':f'fictional-源-{index}','text':'源'*1200,'metadata':{'order':index}}]
            x['candidate_ids']=[s['span_id'] for s in src['source_spans']]
            x['messages'][1]['content']=json.dumps(src,ensure_ascii=False);users.add(x['messages'][1]['content'])
            manifest['frozen'].append(x)
        monkeypatch.setattr(r,'HERE',fmt)
        with w.candidate_hooks(r,manifest):
            packets=research.capture_sdk(r,manifest)+research.capture_sdk(r,manifest,False)
        assert len(packets)==660
        assert [p['role'] for p in packets]==['parent','child','child','reviewer','reviewer','parent','parent']*60+['parent','child','reviewer','parent']*60
        all_packets+=packets
    assert len(users)==300 and len(all_packets)==len(observed)==3300
    assert observed==[p['payload'] for p in all_packets]
    assert all(p['bytes']<=p['advice_bound_bytes']<=240000 for p in all_packets)


def test_empty_unicode_source_actual_sdk_honest_none(candidate):
    x=item();src=json.loads(x['messages'][1]['content'])
    src.update(claim=' \n😀源e\u0301', source_spans=[], metadata={'empty':'','order':[2,1]})
    x['candidate_ids']=[];x['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    calls=[]
    def post(role,n,p):
        name=p['tool_choice']['function']['name']
        a={'mode':'source_only'} if name=='subagent' else {'candidate_ids':[]} if role=='reviewer' else {'label':1,'candidate_ids':[]}
        calls.append((role,n,p));return response(p['model'],calls=[tool(name,a)])
    args,diags,sdk=r.run_b(x,r.MODELS[1],post,strategy='C')
    assert args=={'label':1,'candidate_ids':[]} and not diags
    assert [role for role,n,p in calls]==['parent','child','reviewer','parent']
    assert sdk['source_evidence']==c.validate({'candidate_ids':[]},src)
    assert sdk['review_audit']['parent_tool_reports']==[{'recommendation':args,'source_evidence':sdk['source_evidence']}]
