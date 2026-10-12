import importlib.util
import json
from pathlib import Path
import socket
import sys
import pytest
spec=importlib.util.spec_from_file_location('dev',Path(__file__).with_name('cscs_dev54.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*a,**k):raise AssertionError('network forbidden')
    monkeypatch.setattr(socket,'socket',fail);monkeypatch.setattr(socket,'create_connection',fail)
def manifest():
    e=r.engine();items=[]
    for n in range(54):
        case={'id':f'fake-{n}','claim':{'text':'Original.'}}
        pages=('Original.',) if n%2==0 else ('','Original.')
        if n%2==0:case['reference']={'text':pages[0]}
        else:case['booklet']={'path':'never-read.pdf'}
        messages=e.messages_for_pages(case,pages)
        items.append({'case':case,'pages':pages,'messages':messages,'messages_sha256':r.digest(r.encode(messages))})
    return {'frozen':items}
def job(tmp_path,m):
    d=tmp_path/'job';d.mkdir(mode=0o700)
    r.exclusive(d/'state.json',{'version':2,'reserved_tokens':0,'manifest_sha256':r.digest(r.encode(m)),'requests':0,'tokens':0,'completed':{},'blocked':False})
    return d
class Factory:
    def __init__(self,bad=None):self.calls=[];self.bad=bad
    def __call__(self,model):
        outer=self
        class Fake:
            def request(self,method,path,payload):
                outer.calls.append((model,payload))
                assert method=='POST' and path=='/v1/chat/completions'
                assert payload['max_tokens']==256 and payload['stream'] is False
                if outer.bad in ('http','interrupt'):
                    if outer.bad=='http':raise r.c.Stop('HTTP429')
                    raise KeyboardInterrupt()
                span=json.loads(payload['messages'][1]['content'])['source_spans'][0]['span_id']
                raw=json.dumps({'label':0,'evidence':[{'span_id':span}]})
                if outer.bad=='page':raw=json.dumps({'label':0,'evidence':[{'span_id':span.replace('p0001','p9999').replace('p0002','p9999')}]})
                if outer.bad=='extra':raw=json.dumps({'label':0,'evidence':[{'span_id':span}],'extra':1})
                if outer.bad=='duplicate':raw='{"label":0,"label":1,"evidence":[]}'
                u={'prompt_tokens':80,'completion_tokens':20,'total_tokens':100}
                if outer.bad=='usage':u=None
                if outer.bad=='inconsistent':u['total_tokens']=1
                if outer.bad=='output_limit':u={'prompt_tokens':80,'completion_tokens':257,'total_tokens':337}
                if outer.bad=='input_limit':u={'prompt_tokens':262145,'completion_tokens':20,'total_tokens':262165}
                return {'model':'fallback' if outer.bad=='model' else model,'choices':[{'finish_reason':'length' if outer.bad=='length' else 'stop','message':{'content':raw}}],'usage':u}
        return Fake()
def test_full_finite_mock_and_resume_no_double_send(tmp_path):
    m=manifest();d=job(tmp_path,m);f=Factory();s=r.run(d,m,f)
    assert len(f.calls)==108 and s['actual_total_tokens']==10800
    assert [a[0] for a in f.calls[:6]]==[r.MODELS[0]]*3+[r.MODELS[1]]*3
    assert r.load(d/'8b-01.json')['prediction']['evidence']==[{'page':2,'text':'Original.'}]
    assert r.load(d/'8b-00.json')['prediction']['evidence']==[{'page':None,'text':'Original.'}]
    assert not (d/'inflight.json').exists()
    r.run(d,m,f);assert len(f.calls)==108
    assert s['models'][r.MODELS[0]]['cases']==54
@pytest.mark.parametrize('bad',['http','interrupt','usage','inconsistent','output_limit','input_limit','model'])
def test_any_anomaly_first_sanity_stops_without_retry(tmp_path,bad):
    m=manifest();d=job(tmp_path,m);f=Factory(bad)
    with pytest.raises(BaseException):r.run(d,m,f)
    assert len(f.calls)==1 and (d/'inflight.json').exists()
    with pytest.raises(r.c.Stop):r.run(d,m,f)
    assert len(f.calls)==1

def test_token_budget_stops_before_second_request(tmp_path,monkeypatch):
    m=manifest();d=job(tmp_path,m);f=Factory()
    monkeypatch.setattr(r,'TOKEN_BUDGET',r.RESERVE+99)
    with pytest.raises(r.c.Stop):r.run(d,m,f)
    assert len(f.calls)==1 and r.load(d/'state.json')['tokens']==100

def test_request_budget_stops_before_second(tmp_path,monkeypatch):
    m=manifest();d=job(tmp_path,m);f=Factory();monkeypatch.setattr(r,'MAX_REQUESTS',1)
    with pytest.raises(r.c.Stop):r.run(d,m,f)
    assert len(f.calls)==1

def test_completed_prefix_resume_skips_saved_case(tmp_path):
    m=manifest();d=job(tmp_path,m);f=Factory();item=m['frozen'][0]
    response=f(r.MODELS[0]).request('POST','/v1/chat/completions',{'messages':item['messages'],'max_tokens':256,'stream':False})
    record=r.validate(response,item,r.MODELS[0],1);name=r.result_name(r.MODELS[0],0)
    r.exclusive(d/name,record)
    st=r.load(d/'state.json');st.update(requests=1,tokens=100,completed={name:r.digest(r.encode(record))});r.state_write(d/'state.json',st)
    f.calls.clear();r.run(d,m,f)
    assert len(f.calls)==107 and f.calls[0][1]['messages']==m['frozen'][1]['messages']

def test_save_failure_after_replace_retains_independent_fence(tmp_path,monkeypatch):
    m=manifest();d=job(tmp_path,m);f=Factory();original=r.state_write;calls=[]
    def late(path,state):
        original(path,state);calls.append(1)
        if len(calls)==2:raise OSError('late fsync failure')
    monkeypatch.setattr(r,'state_write',late)
    with pytest.raises(OSError):r.run(d,m,f)
    assert r.load(d/'state.json')['completed'] and (d/'inflight.json').exists()
    with pytest.raises(r.c.Stop):r.run(d,m,f)
    assert len(f.calls)==1

def test_reservation_storage_failure_no_network(tmp_path,monkeypatch):
    m=manifest();d=job(tmp_path,m);f=Factory()
    monkeypatch.setattr(r,'state_write',lambda *a: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):r.run(d,m,f)
    assert not f.calls and (d/'inflight.json').exists()

def test_no_user_run_never_reads_key_or_creates_job(tmp_path,monkeypatch):
    d=tmp_path/'never-created'
    monkeypatch.setattr(r.c,'protect',lambda:None)
    monkeypatch.setattr(sys.stdin,'isatty',lambda:pytest.fail('TTY check'))
    monkeypatch.setattr('builtins.input',lambda *a:pytest.fail('input prompt'))
    monkeypatch.setattr(r,'prepare',lambda:pytest.fail('prepare without approval'))
    monkeypatch.setattr(sys,'argv',['runner','--job',str(d)])
    monkeypatch.setattr(r.c,'read_key',lambda *a:pytest.fail('key read'))
    with pytest.raises(r.c.Stop):r.main()
    assert not d.exists()

@pytest.mark.parametrize('is_tty',[False,True])
def test_user_run_needs_no_tty_or_input(tmp_path,monkeypatch,is_tty):
    m=manifest();d=tmp_path/'noninteractive'
    monkeypatch.setattr(r,'prepare',lambda:m);monkeypatch.setattr(r.c,'protect',lambda:None)
    monkeypatch.setattr(sys.stdin,'isatty',lambda:is_tty)
    monkeypatch.setattr('builtins.input',lambda *a:pytest.fail('input prompt'))
    monkeypatch.setattr(sys,'argv',['runner','--user-run','--job',str(d)])
    monkeypatch.setattr(r.c,'read_key',lambda *a:pytest.fail('real key read'))
    calls=[]
    def offline_run(job_path,frozen,client_factory):
        assert job_path==d and frozen==m
        calls.append(1)
        return {'status':'offline-test'}
    monkeypatch.setattr(r,'run',offline_run)
    r.main()
    assert calls==[1] and (d/'manifest.json').exists()

def test_changed_completion_record_blocks_before_send(tmp_path):
    m=manifest();d=job(tmp_path,m);f=Factory();r.run(d,m,f)
    (d/'8b-00.json').write_text('{}');f.calls.clear()
    with pytest.raises(r.c.Stop):r.run(d,m,f)
    assert not f.calls

def test_wall_deadline_stops_uncertain_request_no_retry(tmp_path,monkeypatch):
    import time
    m=manifest();d=job(tmp_path,m);calls=[]
    class Slow:
        def request(self,*a):calls.append(1);time.sleep(.1)
    monkeypatch.setattr(r,'DEADLINE_SECONDS',.01)
    with pytest.raises(r.c.Stop):r.run(d,m,lambda _:Slow())
    assert calls==[1] and (d/'inflight.json').exists()
    with pytest.raises(r.c.Stop):r.run(d,m,lambda _:Slow())
    assert calls==[1]

@pytest.mark.parametrize('bad',['page','extra','duplicate','length'])
def test_known_invalid_quality_counts_and_70b_continues(tmp_path,bad):
    m=manifest();d=job(tmp_path,m)
    class Independent(Factory):
        def __call__(self,model):
            self.bad=bad if model==r.MODELS[0] else None
            return super().__call__(model)
    f=Independent();summary=r.run(d,m,f)
    assert len(f.calls)==108
    assert summary['models'][r.MODELS[0]]['evaluation_failures']==54
    assert summary['models'][r.MODELS[1]]['output_valid']==54
    assert r.load(d/'state.json')['tokens']==10800
    lines=(d/'8b-predictions.jsonl').read_text().splitlines()
    assert len(lines)==54 and all(json.loads(x).get('error') for x in lines)
    r.run(d,m,f);assert len(f.calls)==108

def test_known_oversized_usage_accounted_before_safety_stop(tmp_path):
    m=manifest();d=job(tmp_path,m);f=Factory('input_limit')
    with pytest.raises(r.c.Stop):r.run(d,m,f)
    assert r.load(d/'state.json')['tokens']==262165
    assert r.load(d/'state.json')['blocked']

def test_offline_schema_disallows_text_without_enabling_live_mode():
    schema=r.schema_candidate()['json_schema']['schema']
    assert not schema['additionalProperties']
    evidence=schema['properties']['evidence']['items']
    assert not evidence['additionalProperties'] and set(evidence['properties'])=={'span_id'}


def test_actual_failed_response_remains_invalid_and_usage_accountable():
    # Copied historical nonsecret record, never credentials or live endpoints.
    old=Path(__file__).resolve().parents[3]/'output/cscs/legacy-dev54-v1'
    if not old.exists():pytest.skip('historical copy not installed yet')
    record=r.load(old/'8b-01.json');m=r.load(old/'manifest.json')
    response={'model':record['model'],'usage':record['usage'],'choices':[{'finish_reason':'stop','message':{'content':record['raw_output']}}]}
    value=r.validate(response,m['frozen'][1],record['model'],record['elapsed_ms'])
    assert value['usage_known'] and value['usage_valid'] and not value['output_valid']
    assert value['usage']['total_tokens']==17992
    assert value['finish_reason']=='stop'
