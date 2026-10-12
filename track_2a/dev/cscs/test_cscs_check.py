import io
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import pytest
from cscs_check import Client, MockClient, MODEL, Stop, allowed_models, read_key, save_key, smoke

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args,**kwargs):raise AssertionError('Real network forbidden')
    monkeypatch.setattr(socket,'socket',fail);monkeypatch.setattr(socket,'create_connection',fail)

def test_mock_synthetic_integrated_ID_roundtrip():
    client=MockClient();result=smoke(client)
    assert result['entailment'] and result['source_ID_output_valid']
    assert result['evidence'][0]['page'] is None
    assert client.calls==[('GET','/v1/models'),('POST','/v1/chat/completions')]

def test_cscs_gateway_owned_by_not_swiss_ai():
    assert allowed_models({'data':[{'id':MODEL,'owned_by':'Envoy AI Gateway'}]})==[MODEL]

def test_models_whitelist_exact_capitalization_and_thinking_listing():
    data={'data':[{'id':MODEL+'-thinking'},{'id':'swiss-ai/Apertus-8B-Instruct-2509'},{'id':'google/gemma-4-31B-it'}]}
    assert allowed_models(data)==['swiss-ai/Apertus-8B-Instruct-2509',MODEL+'-thinking']

def test_synthetic_fake_key_storage_owner_only_no_overwrite(tmp_path):
    path=tmp_path/'private'/'api-key';save_key(path,'synthetic-placeholder')
    assert path.parent.stat().st_mode&0o777==0o700 and path.stat().st_mode&0o777==0o600
    assert read_key(path)=='synthetic-placeholder'
    with pytest.raises(FileExistsError):save_key(path,'replacement')

@pytest.mark.parametrize('bad',['','line\nline','contains space'])
def test_bad_key_shape_not_saved(tmp_path,bad):
    with pytest.raises(Stop):save_key(tmp_path/'private'/'api-key',bad)

def test_symlink_loose_permissions_and_hardlink_rejected(tmp_path):
    d=tmp_path/'private';d.mkdir(mode=0o700);original=d/'real';original.write_text('synthetic');original.chmod(0o600)
    target=d/'api-key';target.symlink_to(original)
    with pytest.raises(OSError):read_key(target)
    target.unlink();original.chmod(0o644)
    with pytest.raises(Stop):read_key(original)
    original.chmod(0o600);os.link(original,target)
    with pytest.raises(Stop):read_key(original)

class Reply(io.BytesIO):
    def __init__(self,status=200):super().__init__(b'{"data":[]}');self.status=status
class Fake:
    def __init__(self,status=200):self.reply=Reply(status);self.calls=[];self.closed=False
    def set_debuglevel(self,n):assert n==0
    def request(self,method,path,body,headers):self.calls.append((method,path,body))
    def getresponse(self):return self.reply
    def close(self):self.closed=True

def client(fake):
    def factory(host,timeout,context):
        assert host=='api.inference.cscs.ch' and timeout==45
        assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
        return fake
    return Client('synthetic-placeholder',factory)

def test_list_just_one_GET_no_generation_no_key_in_repr():
    fake=Fake();c=client(fake);c.request('GET','/v1/models')
    assert fake.calls==[('GET','/v1/models',None)] and fake.closed
    assert 'synthetic-placeholder' not in repr(c)

@pytest.mark.parametrize('status',[301,302,401,402,429,503])
def test_HTTP_failure_no_retry_or_error_body_read(status):
    fake=Fake(status)
    with pytest.raises(Stop):client(fake).request('GET','/v1/models')
    assert len(fake.calls)==1 and fake.reply.tell()==0 and fake.closed

def test_other_host_path_or_model_refused_before_call():
    fake=Fake();c=client(fake)
    with pytest.raises(Stop):c.request('GET','/v1/key')
    with pytest.raises(Stop):c.request('POST','/v1/chat/completions',{'model':'google/gemma','max_tokens':256,'stream':False})
    assert not fake.calls

def test_live_actions_require_person_flag_without_key_lookup(tmp_path):
    script=Path(__file__).with_name('cscs_check.py')
    result=subprocess.run([sys.executable,'-I','-B',str(script),'list-models','--key-file',str(tmp_path/'missing')],capture_output=True,text=True)
    assert result.returncode==1 and not list(tmp_path.iterdir())
    assert 'missing' not in result.stderr

def test_no_live_smoke_CLI_and_no_credential_argument_echo():
    script=Path(__file__).with_name('cscs_check.py')
    for arguments in [['smoke','--user-run'],['list-models','--key','synthetic-sensitive-sentinel']]:
        result=subprocess.run([sys.executable,'-I','-B',str(script),*arguments],capture_output=True,text=True)
        assert result.returncode!=0 and 'synthetic-sensitive-sentinel' not in result.stdout+result.stderr

def test_list_command_does_not_call_smoke_or_POST(monkeypatch,capsys):
    import cscs_check as module
    fake=Fake();monkeypatch.setattr(module,'protect',lambda:None);monkeypatch.setattr(module,'read_key',lambda _: 'mock-memory-only')
    monkeypatch.setattr(module,'Client',lambda _:client(fake));monkeypatch.setattr(sys,'argv',['cscs_check.py','list-models','--user-run'])
    module.main();assert fake.calls==[('GET','/v1/models',None)]
    assert json.loads(capsys.readouterr().out)['generation_requests']==0
