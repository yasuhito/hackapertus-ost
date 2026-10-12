import importlib.util
import json
from pathlib import Path
import socket
import sys
import pytest
spec=importlib.util.spec_from_file_location('smoke',Path(__file__).with_name('cscs_smoke.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args,**kwargs):raise AssertionError('real network forbidden')
    monkeypatch.setattr(socket,'socket',fail);monkeypatch.setattr(socket,'create_connection',fail)
class Fake:
    def __init__(self,bad=None):self.calls=[];self.bad=bad
    def request(self,method,path,payload):
        self.calls.append((method,path,payload))
        assert method=='POST' and path=='/v1/chat/completions'
        assert payload['max_tokens']==256 and payload['stream'] is False
        span=json.loads(payload['messages'][1]['content'])['source_spans'][0]['span_id']
        obj={'label':0,'evidence':[{'span_id':span}]}
        if self.bad=='span':obj['evidence'][0]['span_id']='invented'
        if self.bad=='extra':obj['extra']=1
        if self.bad=='bool':obj['label']=True
        r={'model':payload['model'],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(obj)}}],'usage':{'prompt_tokens':20,'completion_tokens':8}}
        if self.bad=='model':r['model']='fallback'
        if self.bad=='length':r['choices'][0]['finish_reason']='length'
        if self.bad=='usage':r['usage']=None
        return r
@pytest.mark.parametrize('model',sorted(s.c.MODELS))
def test_single_exact_model_same_synthetic(model):
    f=Fake();r=s.run_one(f,model)
    assert len(f.calls)==1 and r['correct'] and r['usage_valid'] and r['output_valid']
    assert r['evidence'][0]['page'] is None
@pytest.mark.parametrize('bad',['span','extra','bool','model','length'])
def test_invalid_response_retains_usage_no_retry(bad):
    f=Fake(bad);r=s.run_one(f,s.c.MODEL)
    assert not r['output_valid'] and r['usage']=={'prompt_tokens':20,'completion_tokens':8} and len(f.calls)==1

def test_usage_unknown_separate_from_output():
    r=s.run_one(Fake('usage'),s.c.MODEL);assert not r['usage_valid']

def invoke(monkeypatch,tmp_path,answer='YES'):
    output=tmp_path/'result.json'
    monkeypatch.setattr(sys,'argv',['smoke','--user-run','--model',s.c.MODEL,'--output',str(output)])
    monkeypatch.setattr(s.c,'protect',lambda:None)
    monkeypatch.setattr(sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr('builtins.input',lambda _:answer)
    return output

def test_decline_does_not_read_key_or_create_output(monkeypatch,tmp_path):
    o=invoke(monkeypatch,tmp_path,'NO')
    monkeypatch.setattr(s.c,'read_key',lambda _:pytest.fail('key read'))
    with pytest.raises(s.c.Stop):s.main()
    assert not o.exists()

def test_existing_output_refuses_key_read(monkeypatch,tmp_path):
    o=invoke(monkeypatch,tmp_path);o.write_text('preserved')
    monkeypatch.setattr(s.c,'read_key',lambda _:pytest.fail('key read'))
    with pytest.raises(FileExistsError):s.main()
    assert o.read_text()=='preserved'

def test_interrupted_attempt_retained_and_blocks_rerun(monkeypatch,tmp_path):
    o=invoke(monkeypatch,tmp_path)
    monkeypatch.setattr(s.c,'read_key',lambda _:'synthetic')
    class Interrupted:
        def __init__(self,*a,**k):pass
        def request(self,*a,**k):raise KeyboardInterrupt()
    monkeypatch.setattr(s.c,'Client',Interrupted)
    with pytest.raises(KeyboardInterrupt):s.main()
    assert json.loads(o.read_text())['status']=='attempt_reserved_do_not_repeat'
    with pytest.raises(FileExistsError):s.main()
    assert o.stat().st_mode&0o777==0o600

def test_confirmed_success_mock_only(monkeypatch,tmp_path):
    o=invoke(monkeypatch,tmp_path)
    monkeypatch.setattr(s.c,'read_key',lambda _:'synthetic')
    fake=Fake();monkeypatch.setattr(s.c,'Client',lambda *a,**k:fake)
    s.main();assert len(fake.calls)==1 and json.loads(o.read_text())['correct']
