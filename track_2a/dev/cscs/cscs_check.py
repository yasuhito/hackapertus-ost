#!/usr/bin/env python3
"""Person-operated CSCS check. Agent preparation/testing must use mock only."""
import argparse
import getpass
import http.client
import json
import os
from pathlib import Path
import resource
import ssl
import stat
import sys

BASE = 'https://api.inference.cscs.ch/v1'
MODEL = 'swiss-ai/Apertus-v1.5-8B'
MODELS = {MODEL, 'swiss-ai/Apertus-v1.5-70B'}
LIST_MODELS = MODELS | {m+'-thinking' for m in MODELS} | {'swiss-ai/Apertus-8B-Instruct-2509','swiss-ai/Apertus-70B-Instruct-2509'}
DEFAULT_KEY_FILE = Path.home()/'.config/hackapertus-ost-cscs/api-key'
APP_SRC = Path(__file__).resolve().parents[2]/'src'

class Stop(Exception):pass
class Parser(argparse.ArgumentParser):
    def error(self,*args):self.exit(2,'STOP: invalid arguments; never pass a key as an argument\n')

def protect():
    if sys.gettrace() or sys.getprofile():raise Stop('debugger_or_profiler_refused')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.umask(0o077)
    http.client.HTTPConnection.debuglevel=0;http.client.HTTPSConnection.debuglevel=0

def key_bytes(blob):
    if blob.endswith(b'\n'):blob=blob[:-1]
    if not blob or len(blob)>4096 or any(c<33 or c>126 for c in blob):raise Stop('key_must_be_single_ASCII_line')
    return blob.decode('ascii')

def private_directory(path):
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:raise Stop('private_directory_700_required')

def save_key(path,key):
    value=key_bytes(key.encode('ascii'))
    if not path.parent.exists():path.parent.mkdir(mode=0o700)
    private_directory(path.parent)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(value.encode()+b'\n');stream.flush();os.fsync(stream.fileno())

def read_key(path):
    private_directory(path.parent)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or stat.S_IMODE(info.st_mode) not in (0o400,0o600):raise Stop('private_regular_key_file_required')
        return key_bytes(os.read(fd,4098))
    finally:os.close(fd)

class Client:
    def __init__(self,key,factory=http.client.HTTPSConnection,model=MODEL):
        if model not in MODELS:raise Stop('model_refused')
        self.__key=key;self.factory=factory;self.model=model
    def __repr__(self):return '<CSCSClient credentials=redacted>'
    def request(self,method,path,payload=None):
        if (method,path) not in {('GET','/v1/models'),('POST','/v1/chat/completions')}:raise Stop('endpoint_refused')
        if method=='POST' and (payload.get('model')!=self.model or payload.get('max_tokens')!=256 or payload.get('stream')is not False or {'tools','models','plugins'}&payload.keys()):raise Stop('only_selected_nonthinking_check_allowed')
        connection=self.factory('api.inference.cscs.ch',timeout=45,context=ssl.create_default_context());connection.set_debuglevel(0)
        try:
            data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
            connection.request(method,path,body=data,headers={'Authorization':'Bearer '+self.__key,'Content-Type':'application/json','Accept-Encoding':'identity','User-Agent':'HackApertus-CSCS-SingleCheck/1.0'})
            response=connection.getresponse()
            if response.status!=200:raise Stop('HTTP_failure_no_redirect_or_retry')
            blob=response.read(2_000_001)
            if len(blob)>2_000_000:raise Stop('response_too_large')
            return json.loads(blob)
        except BaseException:
            raise Stop('request_failed_or_interrupted_no_retry') from None
        finally:connection.close()

def allowed_models(response):
    if not isinstance(response,dict) or not isinstance(response.get('data'),list):raise Stop('invalid_models_response')
    return sorted({r['id'] for r in response['data'] if isinstance(r,dict) and r.get('id') in LIST_MODELS})

def synthetic_case():
    return {'id':'synthetic-cscs','reference':{'text':'Der Bundesrat lehnt den Vorschlag ab.','language':'de'},'claim':{'text':'Der Bundesrat lehnt den Vorschlag ab.','language':'de'}}

def smoke(client):
    if MODEL not in allowed_models(client.request('GET','/v1/models')):raise Stop('8B_model_not_allowed_by_this_key')
    sys.path.insert(0,str(APP_SRC));from predict import context,predict
    case=synthetic_case();pages,messages=context(case,Path('.'))
    response=client.request('POST','/v1/chat/completions',{'model':MODEL,'messages':messages,'temperature':0,'max_tokens':256,'stream':False})
    if response.get('model')!=MODEL or 'error' in response:raise Stop('unexpected_model_or_error')
    usage=response.get('usage');choices=response.get('choices')
    if not isinstance(usage,dict) or any(type(usage.get(k))is not int or usage[k]<0 for k in ['prompt_tokens','completion_tokens']):raise Stop('raw_usage_unknown')
    if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise Stop('incomplete_generation')
    raw=choices[0]['message']['content']
    class SavedBackend:
        def complete(self,*args):return raw,usage
    result=predict(case,SavedBackend())
    return {'model':MODEL,'generation_requests':1,'entailment':result['label']==0,'source_ID_output_valid':'error' not in result,'evidence':result['evidence'],'input_tokens':usage['prompt_tokens'],'output_tokens':usage['completion_tokens'],'API_cost':'not reported; check CSCS project/key usage UI'}

class MockClient:
    def __init__(self):self.calls=[]
    def request(self,method,path,payload=None):
        self.calls.append((method,path))
        if method=='GET':return {'data':[{'id':MODEL,'owned_by':'Envoy AI Gateway'}]}
        span=json.loads(payload['messages'][1]['content'])['source_spans'][0]['span_id']
        return {'model':MODEL,'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'label':0,'evidence':[{'span_id':span}]})}}],'usage':{'prompt_tokens':20,'completion_tokens':8}}

def main():
    parser=Parser();parser.add_argument('action',choices=['mock','save-key','list-models']);parser.add_argument('--user-run',action='store_true');parser.add_argument('--key-file',type=Path,default=DEFAULT_KEY_FILE);args=parser.parse_args();protect()
    if args.action=='mock':
        result=smoke(MockClient());result.update(mode='mock',real_API_requests=0);print(json.dumps(result,ensure_ascii=False));return
    if not args.user_run:raise Stop('explicit_person_operation_required')
    if args.action=='save-key':
        if not sys.stdin.isatty():raise Stop('interactive_terminal_required')
        save_key(args.key_file,getpass.getpass('CSCS key (hidden input): '));print('Saved by your explicit operation; owner-only file, no overwrite.');return
    client=Client(read_key(args.key_file))
    if args.action=='list-models':print(json.dumps({'allowed_Apertus_models':allowed_models(client.request('GET','/v1/models')),'generation_requests':0}));return
    raise Stop('live_generation_not_enabled_in_this_stage')

if __name__=='__main__':
    try:main()
    except SystemExit:raise
    except BaseException:print('STOP: check failed; no retry; secret/error body not logged',file=sys.stderr);sys.exit(1)
