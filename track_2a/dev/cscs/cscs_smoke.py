#!/usr/bin/env python3
"""Explicit person-only single generation, with durable nonsecret attempt record."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

spec=importlib.util.spec_from_file_location('cscs_check',Path(__file__).with_name('cscs_check.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def run_one(client,model):
    if model not in c.MODELS:raise c.Stop('model_refused')
    sys.path.insert(0,str(c.APP_SRC))
    from predict import context,predict
    case=c.synthetic_case();pages,messages=context(case,Path('.'))
    payload={'model':model,'messages':messages,'temperature':0,'max_tokens':256,'stream':False}
    start=time.monotonic()
    response=client.request('POST','/v1/chat/completions',payload)
    record={'model':model,'generation_requests':1,'elapsed_ms':round((time.monotonic()-start)*1000),'usage':None,'output_valid':False,'cost':'credits may be consumed; check CSCS UI'}
    if not isinstance(response,dict):return record
    record['usage']=response.get('usage')
    usage=record['usage'];choices=response.get('choices')
    record['usage_valid']=isinstance(usage,dict) and all(type(usage.get(k))is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens'))
    if response.get('model')!=model or 'error' in response or not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict) or choices[0].get('finish_reason')!='stop':return record
    message=choices[0].get('message',{})
    raw=message.get('content') if isinstance(message,dict) else None
    record['raw_output']=raw if isinstance(raw,str) else None
    try:
        obj=json.loads(raw)
        spans={s['span_id'] for s in json.loads(messages[1]['content'])['source_spans']}
        if not isinstance(obj,dict) or set(obj)!={'label','evidence'} or type(obj['label'])is not int or obj['label'] not in (0,1,2) or not isinstance(obj['evidence'],list):return record
        if any(not isinstance(e,dict) or set(e)!={'span_id'} or e['span_id'] not in spans for e in obj['evidence']):return record
        class Saved:
            def complete(self,*args):return raw,usage if record['usage_valid'] else {}
        result=predict(case,Saved())
        record.update(output_valid='error' not in result,label=result['label'],expected_label=0,correct=result['label']==0 and 'error' not in result,evidence=result['evidence'])
    except (ValueError,TypeError,KeyError):pass
    return record

def write_record(stream,record):
    stream.seek(0);stream.truncate();json.dump(record,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def main():
    p=c.Parser();p.add_argument('--user-run',action='store_true');p.add_argument('--model',choices=sorted(c.MODELS),required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--key-file',type=Path,default=c.DEFAULT_KEY_FILE)
    args=p.parse_args();c.protect()
    if not args.user_run or not sys.stdin.isatty():raise c.Stop('interactive_person_operation_required')
    print('This makes ONE inference request and may consume CSCS credits. No retry or fallback. Model: '+args.model)
    if input('Type YES to authorize this single request: ')!='YES':raise c.Stop('not_confirmed')
    # Exclusive output creation happens before reading the key or contacting CSCS.
    fd=os.open(args.output,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w+',encoding='utf-8') as stream:
        write_record(stream,{'model':args.model,'status':'attempt_reserved_do_not_repeat','generation_requests':'unknown_until_completed'})
        directory=os.open(args.output.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
        client=c.Client(c.read_key(args.key_file),model=args.model)
        result=run_one(client,args.model)
        result['status']='completed';write_record(stream,result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except SystemExit:raise
    except BaseException:
        print('STOP: no retry; keep any attempt record. Secret/error body not logged.',file=sys.stderr);sys.exit(1)
