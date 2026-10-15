"""Three-role actual Root Ledger + unchanged physical wrapper; fictional HTTP."""
import json
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0,str(Path(__file__).parent))
from test_role_review import candidate, offline, candidate_manifest, item, r, response
import fullbranch_transport as physical
import role_review_research as controller


def setup(tmp_path, monkeypatch, statuses, mutate=None):
    job=tmp_path/'job'; manifest=candidate_manifest()
    r.initialize(job,manifest)
    now=[100.0]; sleeps=[]; posts=[]
    monkeypatch.setattr(time,'monotonic',lambda:now[0])
    def sleep(seconds): sleeps.append(seconds); now[0]+=seconds
    monkeypatch.setattr(time,'sleep',sleep)
    monkeypatch.setenv('BASE_URL','http://fictional.invalid/v1')
    monkeypatch.setenv('API_KEY','fictional-never-record')
    class Connection:
        def __init__(self,*args,**kwargs): assert kwargs['timeout']==45
        def set_debuglevel(self,value): assert value==0
        def request(self,method,path,body,headers):
            assert (job/'inflight.json').exists() and (job/'physical/inflight.json').exists()
            posts.append(json.loads(body))
        def getresponse(self):
            status_value=statuses[min(len(posts)-1,len(statuses)-1)]
            if isinstance(status_value,BaseException): raise status_value
            class HTTPResponse:
                status=status_value
                def read(self,*args):
                    assert self.status==200
                    value=response(posts[-1]['model'],content='fictional')
                    if mutate: mutate(value)
                    return json.dumps(value).encode()
            return HTTPResponse()
        def close(self): pass
    def base(model): return r.Transport(model,submitted=True,factory=Connection)
    side=physical.PhysicalLedger(r,job,1000)
    ledger=r.Ledger(job,manifest,lambda model:side.client(model,base))
    return job,side,ledger,posts,sleeps


def post(ledger,role='reviewer',number=0):
    payload={'model':r.fixed_role_model('C',r.MODELS[1],role), 'messages':[],
             'temperature':0,'max_tokens':256,'stream':False}
    return ledger.post(r.MODELS[1],0,role,number,payload,deadline=400)


def test_three_role_known_usage_bijection_and_canonical_sum(candidate,tmp_path,monkeypatch):
    job,side,ledger,posts,sleeps=setup(tmp_path,monkeypatch,[200])
    for role in ('parent','child','reviewer'): post(ledger,role)
    metrics,_=r.metrics_for(ledger,r.MODELS[1],0,200)
    assert metrics=={'input_tokens':240,'output_tokens':60,'inference_time_ms':200}
    assert ledger.state['tokens']==300
    totals=controller.physical_role_totals(r,job,physical.verify)
    assert totals['physical_calls_by_role']=={'parent':1,'child':1,'reviewer':1}
    assert totals['full_total_tokens']==totals['charged_tokens']==300
    assert totals['full_usage_known'] and not sleeps
    assert [x['model'] for x in posts]==[r.MODELS[1],r.MODELS[0],r.MODELS[0]]


def test_reviewer_four500_fifth_success_no_sixth(candidate,tmp_path,monkeypatch):
    job,side,ledger,posts,sleeps=setup(tmp_path,monkeypatch,[500]*4+[200])
    post(ledger)
    assert len(posts)==5 and sleeps==[2,4,8,16] and ledger.state['requests']==1
    totals=controller.physical_role_totals(r,job,physical.verify)
    assert totals['physical_calls_by_role']['reviewer']==5
    assert totals['charged_tokens']==4*r.RESERVE+100 and totals['full_total_tokens'] is None


@pytest.mark.parametrize('statuses,count', [([500]*6,5),([400],1),([0],1),([TimeoutError()],1)])
def test_reviewer_permanent_failures_fence(candidate,tmp_path,monkeypatch,statuses,count):
    job,side,ledger,posts,sleeps=setup(tmp_path,monkeypatch,statuses)
    with pytest.raises(r.Stop): post(ledger)
    assert len(posts)==count and side.charged==count*r.RESERVE
    assert (job/'inflight.json').exists() and (job/'physical/inflight.json').exists()
    with pytest.raises(r.Stop,match='UNCERTAIN_FENCE'):
        r.Ledger(job,ledger.manifest,lambda _:pytest.fail('resume'))


@pytest.mark.parametrize('mutate', [lambda v:v.pop('usage'),lambda v:v.update(model='wrong'),
    lambda v:v['usage'].update(total_tokens=True)])
def test_reviewer_unknown200_usage_no_retry(candidate,tmp_path,monkeypatch,mutate):
    job,side,ledger,posts,sleeps=setup(tmp_path,monkeypatch,[200],mutate)
    with pytest.raises(r.Stop): post(ledger)
    assert len(posts)==1 and not sleeps and (job/'physical/inflight.json').exists()


@pytest.mark.parametrize('guard',['deadline','storage','model','cap','budget'])
def test_reviewer_guard_before_post(candidate,tmp_path,monkeypatch,guard):
    job,side,ledger,posts,sleeps=setup(tmp_path,monkeypatch,[200])
    if guard=='deadline': side.deadline=100
    elif guard=='storage':
        old=r.legacy.exclusive
        def exclusive(path,value):
            if path.name.endswith('-before.json'): raise OSError('fictional disk failure')
            old(path,value)
        monkeypatch.setattr(r.legacy,'exclusive',exclusive)
    elif guard=='model':
        with pytest.raises(r.Stop,match='ROLE_MODEL'):
            ledger.post(r.MODELS[1],0,'reviewer',0,{'model':r.MODELS[1]})
        assert not posts and not ledger.fence.exists()
        return
    elif guard=='cap': side.records=[None]*300
    else: side.charged=physical.BUDGET-physical.RESERVE+1
    with pytest.raises((r.Stop,OSError)): post(ledger)
    assert not posts and not sleeps


def test_actual_root_pipeline_sdk_physical_and_canonical_metrics(candidate,tmp_path):
    """One fictional canonical case, not just a bridge or ledger unit test."""
    from collections import Counter
    from test_role_review import backend
    manifest=candidate_manifest(); job=tmp_path/'whole-fictional-pipeline'
    r.initialize(job,manifest)
    side=physical.PhysicalLedger(r,job,time.monotonic()+60)
    calls=[]; counts=Counter(); fake=backend(manifest['frozen'][0],calls)
    class Fake:
        def __init__(self,model): self.model=model
        def request(self,method,path,payload):
            names={t['function']['name'] for t in payload['tools']}
            role='reviewer' if names=={'review_source'} else 'parent' if 'subagent' in names else 'child'
            n=counts[role]; counts[role]+=1
            assert self.model==payload['model']
            return fake(role,n,payload)
    summary=r.run(job,manifest,lambda model:side.client(model,Fake))
    assert summary['status']=='completed' and summary['generation_requests']==4
    assert summary['actual_total_tokens']==400
    stats=summary['models'][r.MODELS[1]]
    assert stats['calls_by_role']=={'parent':2,'child':1,'reviewer':1}
    assert stats['prompt_tokens']==320 and stats['completion_tokens']==80
    assert stats['output_valid']==1
    totals=controller.physical_role_totals(r,job,physical.verify)
    assert totals['physical_calls_by_role']=={'parent':2,'child':1,'reviewer':1}
    assert totals['full_total_tokens']==400
    record=r.legacy.load(job/next(iter(r.legacy.load(job/'state.json')['cases'])))
    assert record['prediction']['metrics']['input_tokens']==320
    assert record['sdk']['review_audit']['parent_tool_reports'][0]['recommendation']['label']==1
    assert record['prediction']['label']==0
