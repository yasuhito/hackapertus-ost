#!/usr/bin/env python3
"""Fixed explicitly authorized finite job, no remote control or arbitrary input/model."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0,str(ROOT/'vendor'))
spec=importlib.util.spec_from_file_location('cscs_check',ROOT/'cscs_check.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
CASES=ROOT/'fixtures/cases-portable.jsonl'
CASE_SHA='4e152ed1118149c4ca0fecc5d7b20d7676f43a24b613b8cb465bb5eb0d80a44a'
MODELS=('swiss-ai/Apertus-v1.5-8B','swiss-ai/Apertus-v1.5-70B')
MAX_REQUESTS=108
TOKEN_BUDGET=2_000_000
# Conservative reservation using documented 262144 context plus output cap.
RESERVE=262144+256
DEADLINE_SECONDS=60
PROTOCOL_REMINDER='Output compact JSON only. Evidence objects have exactly one key: span_id. Never include text, page, explanation, or quotations. Copy the ID exactly. Example shape: {"label":1,"evidence":[]}.'

def schema_candidate():
    """Offline proposal only; live service support is not established."""
    return {'type':'json_schema','json_schema':{'name':'nli_source_ids','strict':True,'schema':{'type':'object','additionalProperties':False,'required':['label','evidence'],'properties':{'label':{'type':'integer','enum':[0,1,2]},'evidence':{'type':'array','maxItems':5,'items':{'type':'object','additionalProperties':False,'required':['span_id'],'properties':{'span_id':{'type':'string'}}}}}}}}


def deadline_stop(*args):raise c.Stop('request_wall_deadline_no_retry')
def post_once(client,payload):
    previous=signal.signal(signal.SIGALRM,deadline_stop)
    timer=signal.setitimer(signal.ITIMER_REAL,DEADLINE_SECONDS)
    try:return client.request('POST','/v1/chat/completions',payload)
    finally:
        signal.setitimer(signal.ITIMER_REAL,*timer);signal.signal(signal.SIGALRM,previous)

def digest(blob):return hashlib.sha256(blob).hexdigest()
def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()
def syncdir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def exclusive(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(encode(data));f.flush();os.fsync(f.fileno())
    syncdir(path.parent)
def exclusive_jsonl(path,rows):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        for row in rows:f.write(encode(row)+b'\n')
        f.flush();os.fsync(f.fileno())
    syncdir(path.parent)
def state_write(path,data):
    temp=path.with_suffix('.pending')
    exclusive(temp,data);os.replace(temp,path);syncdir(path.parent)
def load(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'r') as f:return json.load(f)
def engine():
    sys.path.insert(0,str(c.APP_SRC));import predict
    return predict

def prepare():
    blob=CASES.read_bytes()
    if digest(blob)!=CASE_SHA:raise c.Stop('fixed_case_hash_changed')
    rows=[json.loads(line) for line in blob.splitlines()]
    if len(rows)!=54 or len({x['id'] for x in rows})!=54 or sum('booklet' in x for x in rows)!=27:raise c.Stop('fixed_cases_changed')
    e=engine();frozen=[]
    for case in rows:
        if 'booklet' in case:
            original=Path(case['booklet']['path']);case={**case,'booklet':{**case['booklet'],'path':str(REPO/'booklets'/original.name)}}
        if set(case)-{'id','claim','booklet','reference','vote'}:raise c.Stop('unexpected_case_metadata')
        pages,messages=e.context(case,CASES.parent,selection_strategy='vote_pages')
        messages[0]['content']+='\n\n'+PROTOCOL_REMINDER
        if len(encode(messages))>66_000:raise c.Stop('unexpected_context_size')
        frozen.append({'case':case,'pages':pages,'messages':messages,'messages_sha256':digest(encode(messages))})
    hashes={str(p):digest(p.read_bytes()) for p in [c.APP_SRC/'predict.py',c.APP_SRC/'source_spans.py',c.APP_SRC/'document_selection.py',ROOT/'cscs_check.py',Path(__file__)]}
    return {'version':2,'protocol_reminder':PROTOCOL_REMINDER,'native_schema':'offline proposal only, not sent','case_sha256':CASE_SHA,'models':MODELS,'request_limit':MAX_REQUESTS,'token_budget':TOKEN_BUDGET,'request_token_reserve':RESERVE,'output_limit':256,'temperature':0,'selection_strategy':'vote_pages','sources':hashes,'frozen':frozen}

def usage_known(u):
    return isinstance(u,dict) and all(type(u.get(k))is int and u[k]>=0 for k in ('prompt_tokens','completion_tokens','total_tokens')) and u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
def usage_valid(u):
    return usage_known(u) and u['prompt_tokens']<=262144 and u['completion_tokens']<=256 and u['total_tokens']<=RESERVE

def validate(response,item,model,elapsed):
    record={'model':model,'case_id':item['case']['id'],'messages_sha256':item['messages_sha256'],'elapsed_ms':elapsed,'generation_requests':1,'usage_valid':False,'output_valid':False}
    if not isinstance(response,dict):return record
    usage=response.get('usage');record.update(usage=usage,usage_known=usage_known(usage),usage_valid=usage_valid(usage),server_model=response.get('model'),api_error='error' in response)
    choices=response.get('choices')
    if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):return record
    record['finish_reason']=choices[0].get('finish_reason')
    msg=choices[0].get('message');raw=msg.get('content') if isinstance(msg,dict) else None
    record['raw_output']=raw if isinstance(raw,str) else None
    if response.get('model')!=model or 'error' in response or record['finish_reason']!='stop':return record
    try:
        def pairs(pairs):
            obj={}
            for k,v in pairs:
                if k in obj:raise ValueError('duplicate key')
                obj[k]=v
            return obj
        obj=json.loads(raw,object_pairs_hook=pairs)
        if not isinstance(obj,dict) or set(obj)!={'label','evidence'}:return record
        e=engine();label,evidence=e.decode(json.dumps(obj),tuple(item['pages']),reference='reference' in item['case'])
        prediction={'id':item['case']['id'],'label':label,'label_name':e.LABELS[label],'evidence':evidence,'metrics':{'input_tokens':usage['prompt_tokens'] if record['usage_valid'] else 0,'output_tokens':usage['completion_tokens'] if record['usage_valid'] else 0,'inference_time_ms':elapsed}}
        e.validate_prediction(prediction,tuple(item['pages']),reference='reference' in item['case'])
        record.update(output_valid=True,prediction=prediction)
    except (ValueError,TypeError,KeyError):pass
    return record

def order():
    # Both models' first three fixed cases (B,A,B) before the remaining 51 each.
    return [(m,i) for m in MODELS for i in range(3)]+[(m,i) for m in MODELS for i in range(3,54)]
def result_name(model,index):return ('8b' if model==MODELS[0] else '70b')+f'-{index:02d}.json'

def run(job,manifest,client_factory):
    fence=job/'inflight.json';pending=job/'state.pending'
    if fence.exists() or pending.exists():raise c.Stop('uncertain_attempt_or_storage_stop_no_retry')
    state=load(job/'state.json')
    if state.get('version')!=2 or state['manifest_sha256']!=digest(encode(manifest)) or state.get('blocked') or state.get('reserved_tokens',0):raise c.Stop('job_changed_or_blocked')
    records={}
    tokens=0
    for name,sha in state['completed'].items():
        record=load(job/name)
        if digest(encode(record))!=sha or not record.get('usage_valid') or not usage_valid(record.get('usage')):raise c.Stop('completed_record_integrity_failure')
        records[name]=record;tokens+=record['usage']['total_tokens']
    if len(records)!=state['requests'] or tokens!=state['tokens']:raise c.Stop('ledger_mismatch')
    allowed={result_name(m,i) for m,i in order()}
    if set(records)-allowed:raise c.Stop('unexpected_completed_case')
    for model,index in order():
        name=result_name(model,index)
        if name in records:continue
        if state['requests']>=MAX_REQUESTS or state['tokens']+RESERVE>TOKEN_BUDGET:raise c.Stop('hard_budget_stop_before_request')
        # Fence is durable before key read/network; remains on every uncertain path.
        exclusive(fence,{'model':model,'index':index,'result':name,'reserved_tokens':RESERVE})
        state['requests']+=1;state['reserved_tokens']=RESERVE;state_write(job/'state.json',state)
        started=time.monotonic();item=manifest['frozen'][index]
        client=client_factory(model)
        response=post_once(client,{'model':model,'messages':item['messages'],'temperature':0,'max_tokens':256,'stream':False})
        record=validate(response,item,model,round((time.monotonic()-started)*1000))
        exclusive(job/name,record)
        # Account every known response before quality or safety decisions.
        if usage_known(record.get('usage')):state['tokens']+=record['usage']['total_tokens']
        state['completed'][name]=digest(encode(record))
        safe=record['usage_valid'] and record.get('server_model')==model and not record.get('api_error') and state['tokens']<=TOKEN_BUDGET
        if safe:state['reserved_tokens']=0
        else:state['blocked']=True
        state_write(job/'state.json',state)
        if not safe:raise c.Stop('unsafe_usage_model_or_accounting_no_retry')
        # No fallible durability operation after unlink; resurrection only blocks.
        fence.unlink();records[name]=record
        print(json.dumps({'completed':len(records),'max':MAX_REQUESTS,'model':model,'case_index':index,'tokens_used':state['tokens']},ensure_ascii=False),flush=True)
    # Refresh aggregate files atomically only after all finite calls complete.
    summary={'status':'completed','generation_requests':state['requests'],'actual_total_tokens':state['tokens'],'token_budget':TOKEN_BUDGET,'cost':'unknown; existing CSCS allocation only','sanity_each':3,'models':{}}
    for model in MODELS:
        subset=[records[result_name(model,i)] for i in range(54)]
        times=sorted(r['elapsed_ms'] for r in subset)
        summary['models'][model]={'cases':54,'output_valid':sum(r['output_valid'] for r in subset),'evaluation_failures':sum(not r['output_valid'] for r in subset),'usage_valid':54,'prompt_tokens':sum(r['usage']['prompt_tokens'] for r in subset),'completion_tokens':sum(r['usage']['completion_tokens'] for r in subset),'total_tokens':sum(r['usage']['total_tokens'] for r in subset),'mean_ms':sum(times)/54,'p95_ms':times[51]}
        path=job/('8b-predictions.jsonl' if model==MODELS[0] else '70b-predictions.jsonl')
        if not path.exists():exclusive_jsonl(path,[r.get('prediction',{'id':r['case_id'],'label':1,'label_name':'neutral','evidence':[],'error':'invalid_model_output','metrics':{'input_tokens':r['usage']['prompt_tokens'],'output_tokens':r['usage']['completion_tokens'],'inference_time_ms':r['elapsed_ms']}}) for r in subset])
    if not (job/'summary.json').exists():exclusive(job/'summary.json',summary)
    return summary

def main():
    p=c.Parser();p.add_argument('--prepare-only',action='store_true');p.add_argument('--user-run',action='store_true');p.add_argument('--job',type=Path,default=REPO/'output/cscs/dev54-v2');args=p.parse_args();c.protect()
    if args.prepare_only:
        m=prepare();print(json.dumps({'prepared_cases':len(m['frozen']),'manifest_sha256':digest(encode(m)),'requests_limit':MAX_REQUESTS,'token_budget':TOKEN_BUDGET,'credential_reads':0,'authenticated_requests':0}));return
    if not args.user_run:raise c.Stop('explicit_user_run_required')
    manifest=prepare()
    print('CANDIDATE v2. Known invalid output counts as evaluation failure, other model proceeds. Unknown usage/model/auth/storage errors stop ALL. Finite dev54 job: nonthinking v1.5 8B/70B each54; first3 each sanity. At most108 POSTs, no retry/fallback. Output256/request. Total token budget2000000; conservative262400 reservation/request. CSCS credits may be consumed; monetary cost UNKNOWN. No purchases. No holdout. Resume skips durable completed results.')
    # --user-run explicitly authorizes the fixed job; no TTY or input required.
    job=args.job
    if not job.exists():
        job.mkdir(mode=0o700);syncdir(job.parent)
    c.private_directory(job)
    fd=os.open(job/'lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not (job/'manifest.json').exists():
            exclusive(job/'manifest.json',manifest)
            exclusive(job/'state.json',{'version':2,'reserved_tokens':0,'manifest_sha256':digest(encode(manifest)),'requests':0,'tokens':0,'completed':{},'blocked':False})
        elif digest(encode(load(job/'manifest.json')))!=digest(encode(manifest)):raise c.Stop('source_or_context_changed_refuse_resume')
        # Only the explicitly authorized --user-run path may read credentials.
        cached=[]
        def person_client(model):
            if not cached:cached.append(c.read_key(c.DEFAULT_KEY_FILE))
            return c.Client(cached[0],model=model)
        result=run(job,manifest,person_client)
        print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except SystemExit:raise
    except BaseException:
        print('STOP: fixed job stopped; no retry. Keep records and do not delete inflight/state.pending. Secret and HTTP error body not logged.',file=sys.stderr);sys.exit(1)
