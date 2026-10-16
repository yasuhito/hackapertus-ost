"""Controller integration on entirely fictional local inputs; no owner bundle."""
import copy
import json
from pathlib import Path
import sys
import time

import pytest
sys.path.insert(0, str(Path(__file__).parent))
import span_retrieval_research as c
from test_span_retrieval import candidate, offline, candidate_manifest, r, backend
import role_review_transport as t


def test_source_only_exclusive_workspace(tmp_path,monkeypatch):
    bundle=tmp_path/'bundle';bundle.mkdir()
    (bundle/'cases.jsonl').write_text(json.dumps({'id':'fictional','claim':{'text':'Original.'},'reference':{'text':'Original.'}})+'\n')
    monkeypatch.setattr(c,'BUNDLE',bundle)
    workspace=tmp_path/'candidate';c.copy_workspace(workspace,'candidate')
    assert (workspace/c.RUNNER).read_bytes()==(c.ROOT/c.RUNNER).read_bytes()
    assert (workspace/'track_2a/dev/format/sdk.ts').read_bytes()==(c.ROOT/'track_2a/dev/format/sdk.ts').read_bytes()
    assert (workspace/'track_2a/dev/format/controlledsdk.ts').exists()
    assert not any(p.name in ('expected.jsonl','selection-freeze.json') for p in workspace.rglob('*'))
    with pytest.raises(ValueError,match='EXCLUSIVE'):c.copy_workspace(workspace,'candidate')


def test_real_sdk_capture_ordinary_and_three_role_native_packets(candidate):
    manifest=candidate_manifest()
    packets=c.capture_sdk(r,manifest)
    assert [p['role'] for p in packets]==['parent','child','child','parent','parent']
    assert all(p['bytes'] <= 240000 and p['sha256']==c.sha(r.legacy.encode(p['payload'])) for p in packets)
    # Includes the later parent packet containing actual helper reports.
    later=packets[-1]['payload']
    assert any(m['role']=='tool' and 'source_evidence' in m['content'] for m in later['messages'])


def test_capture_byte_guard_checks_later_parent_packet(candidate,monkeypatch):
    manifest=candidate_manifest()
    original=r.legacy.encode
    def encode(value):
        raw=original(value)
        if isinstance(value,dict) and value.get('messages') and any(m.get('role')=='tool' for m in value['messages']):
            return raw+b'x'*240000
        return raw
    monkeypatch.setattr(r.legacy,'encode',encode)
    with pytest.raises(ValueError,match='NATIVE_PACKET'):c.capture_sdk(r,manifest)


def test_complete_result_actual_sdk_physical_and_review_audit(candidate,tmp_path,monkeypatch):
    manifest=candidate_manifest()
    # Operational verifier always demands 60: fictional repeat inputs preserve IDs/order.
    manifest['frozen']=[copy.deepcopy(manifest['frozen'][0]) for _ in range(60)]
    for index,item in enumerate(manifest['frozen']): item['case']['id']=f'fictional-{index}'
    name=c.JOBS[0];job=tmp_path/name
    r.initialize(job,manifest)
    side=t.PhysicalLedger(r,job,time.monotonic()+300)
    # Use actual SDK once; replay its valid bridge result on the remaining distinct
    # fictional cases while retaining real canonical+physical accounting for each.
    original=r.run_b; saved=[]
    def once(item,model,post,**kwargs):
        if not saved:
            value=original(item,model,post,**kwargs);saved.append(value);return value
        template=manifest['frozen'][0]
        fake=backend(template,[])
        for role,n in [('parent',0),('child',0),('parent',1)]:
            # Exact original SDK payloads captured in the first backend below.
            post(role,n,copy.deepcopy(payloads[(role,n)]))
        return copy.deepcopy(saved[0])
    payloads={}; counts={}
    class Fake:
        def __init__(self,model):self.model=model
        def request(self,method,path,payload):
            names={t['function']['name'] for t in payload['tools']}
            role='parent' if 'subagent' in names else 'child'
            n=counts.get(role,0);counts[role]=n+1
            number=n%2 if role=='parent' else 0
            payloads[(role,number)]=copy.deepcopy(payload)
            return backend(manifest['frozen'][0],[])(role,number,payload)
    monkeypatch.setattr(r,'run_b',once)
    r.run(job,manifest,lambda model:side.client(model,Fake))
    monkeypatch.setattr(c,'OUT',tmp_path)
    # Preserve the loaded real core under candidate hooks for reconstruction.
    monkeypatch.setattr(c,'module',lambda _:r)
    # Hooks cannot nest the same core; temporarily restore original globals by
    # using the existing validated core through a no-op local context.
    from contextlib import nullcontext
    monkeypatch.setattr(c,'candidate_hooks',lambda *a:nullcontext())
    result=c.completed_result(name,{'manifest_sha256':c.sha(c.encode(manifest))})
    assert result['canonical_count']==60 and result['canonical_successful_calls']==180
    assert result['review_available']==60 and result['parent_tool_report_cases']==60
    assert result['role_usage']['child']['input_tokens']==4800 and result['role_usage']['reviewer']['calls']==0
    assert result['physical_calls_by_role']=={'parent':120,'child':60,'reviewer':0}
    assert result['review_states']=={'source_spans_selected':0,'no_source_spans_selected':60,'evidence_unavailable':0}
    c.print_metrics({'mean_Q':c.quality(.8,.9),'elapsed_seconds':1,
                     'repeats':[{**result,'f1a':.8,'f1b':.9,'hita':.5}]*5})


def test_no_arm_start_under_5700_or_grade_prefix(tmp_path,monkeypatch):
    monkeypatch.setattr(time,'time',lambda:c.ABSOLUTE_STOP-5699)
    monkeypatch.setattr(c,'verify_freeze',lambda:pytest.fail('must guard before freeze/runtime work'))
    with pytest.raises(ValueError,match='INSUFFICIENT'):c.execute('candidate')
    monkeypatch.setattr(c,'complete_arm',lambda *a:(_ for _ in ()).throw(ValueError('INCOMPLETE_ARM')))
    monkeypatch.setattr(c.subprocess,'run',lambda *a,**kw:pytest.fail('no grading prefix'))
    with pytest.raises(ValueError,match='INCOMPLETE_ARM'):c.grade_arm({},'candidate')


def test_process_group_timeout_kills_descendants(tmp_path):
    # No model: a fictional sleeping worker with an equally sleeping child.
    with pytest.raises(ValueError,match='PROCESS_GROUP_DEADLINE'):
        c.subprocess_group([sys.executable,'-c','import subprocess,time; subprocess.Popen(["sleep","10"]);time.sleep(10)'],tmp_path,.1)


def test_scorer_commit_is_checked_before_model_or_workspace_work(tmp_path,monkeypatch):
    (tmp_path/'evaluate.py').write_text('fictional evaluator')
    monkeypatch.setattr(c,'OFFICIAL',tmp_path)
    monkeypatch.setattr(c,'SCORER_PYTHON',sys.executable)
    monkeypatch.setattr(c.subprocess,'check_output',lambda *a,**kw:'not-the-pinned-commit')
    with pytest.raises(ValueError,match='OFFICIAL_EVALUATOR_COMMIT_CHANGED'):
        c.runtime()


def test_precise_scoped_provenance_not_universal():
    bundle={'blinded_selection_frozen':True,'provenance_unused_verified':True,
            **{key:'a'*64 for key in ('selection_sha256','provenance_sha256','input_sha256','expected_sha256','case_order_sha256')}}
    with pytest.raises(ValueError,match='DATA_ADAPTER'):c.prospective_bindings(bundle,{})


def test_all_five_fictional_workspaces_export_300_actual_sdk_paths(tmp_path,monkeypatch):
    """Full prepare/freeze with no real bundle, labels, API, init or grading."""
    bundle=tmp_path/'bundle';bundle.mkdir();(bundle/'booklets').mkdir()
    out=tmp_path/'owned-output';out.mkdir()
    cases=[{'id':f'fictional-{i:04d}', 'claim':{'text':'Original fictional statement.'},
            'reference':{'text':'Original fictional statement.'}} for i in range(60)]
    def jsonl(path,values):
        path.write_bytes(b''.join(c.encode(v)+b'\n' for v in values))
    jsonl(bundle/'cases.jsonl',cases)
    jsonl(bundle/'expected.jsonl',[{'id':v['id'],'fictional_owner_only_gold':True} for v in cases])
    prepared=[];audits=[]
    for case in cases:
        pages,messages=r.legacy.engine().context(case,Path('.'),selection_strategy='vote_pages')
        prepared.append({'id':case['id'],'messages':messages})
        ids=[span['span_id'] for span in r.candidates(pages,True)]
        compact=(json.dumps(pages,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
        audits.append({'id':case['id'],'candidate_ids':ids,'selected_page_text_sha256':c.sha(compact)})
    jsonl(bundle/'prepared-contexts.jsonl',prepared)
    jsonl(bundle/'context-audit.jsonl',audits)
    jsonl(bundle/'source-metadata.jsonl',[{'source_index':i} for i in range(30)])
    (bundle/'booklets/manifest.json').write_text('{}')
    compact=lambda value:(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    evidence='.auto/role-review-implementation.md'
    selected={'selection':list(range(60)), 'selection_freeze_sha256':'a'*64,
              'provenance_scope':c.SCOPE,'universal_unseen_claim':False,
              'exclusion_evidence_sha256':{evidence:c.sha((c.ROOT/evidence).read_bytes())}}
    selected['freeze_sha256']=c.sha(compact(selected))
    (bundle/'selection-freeze.json').write_bytes(c.encode(selected))
    artifacts=c.fingerprint([p for p in bundle.rglob('*') if p.is_file() and p.name!='selection-freeze.json'],bundle)
    evidence='.auto/role-review-implementation.md'
    manifest={'source_sha256':'87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd',
              'revision':'fc2b27600310778da6bbf445651ddbca22d86269','selection':list(range(30)),
              'case_order':[v['id'] for v in cases], 'artifact_sha256':artifacts,
              'selection_file_sha256':c.sha((bundle/'selection-freeze.json').read_bytes()),
              'selection_freeze_sha256':selected['selection_freeze_sha256'],
              'provenance_scope':c.SCOPE,'universal_unseen_claim':False,
              'selection_before_expected':True,'reserved_confirmation_prepared':False,
              'system_sha256':c.sha(r.legacy.engine().SYSTEM.encode()),'code_sha256':{}}
    compact=lambda value:(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    manifest['freeze_sha256']=c.sha(compact(manifest))
    (bundle/'selection-manifest.json').write_bytes(c.encode(manifest))
    monkeypatch.setattr(c,'BUNDLE',bundle);monkeypatch.setattr(c,'OUT',out)
    monkeypatch.setattr(c,'CONTROL',out/'span-retrieval-v1-protocol.json')
    monkeypatch.setattr(c,'reference_binding',lambda:{'fictional_saved_control':True,'analysis':{}})
    monkeypatch.setattr(c,'runtime',lambda:{})
    c.prepare_only()
    control=c.verify_freeze()
    assert len(control['jobs'])==5
    for name,binding in control['jobs'].items():
        workspace=Path(binding['workspace'])
        audit=c.load(workspace/'offline-packets.json')
        assert audit['cases']==60 and len({p['case_index'] for p in audit['packets']})==60
        assert audit['root_transport_packets']==len(audit['packets'])==480
        assert audit['populated_and_no_pair'] is True
        assert audit['selected_with_both_repairs'] is True and audit['no_selection_normal_path'] is True
        assert not (workspace/'expected.jsonl').exists()
        assert not (out/name).exists()  # preparation NEVER initializes a ledger
        assert all(p['bytes']<=240000 for p in audit['packets'])
    assert len(list(out.glob('*-workspace')))==5


def test_availability_requires_valid_report_delivered_in_parent_input():
    valid = {'status': 'no_source_spans_selected', 'report': {'axis': 'none'}}
    unavailable = {'status': 'evidence_unavailable', 'reason': 'LIMIT'}
    assert not c.review_available_to_parent(valid, [])
    assert c.review_available_to_parent(valid, [{'source_evidence': valid}])
    assert not c.review_available_to_parent(unavailable, [{'source_evidence': unavailable}])
    with pytest.raises(ValueError, match='PARENT_REPORT_CHANGED'):
        c.review_available_to_parent(valid, [{'source_evidence': unavailable}])


def test_five_complete_fictional_jobs_use_real_unchanged_official_grader(tmp_path,monkeypatch,offline):
    bundle=tmp_path/'bundle';bundle.mkdir();out=tmp_path/'out';out.mkdir()
    cases=[]; gold=[]; predictions=[]
    for index in range(60):
        task='A' if index%2==0 else 'B';cid=f'fictional-official-{index:04d}-{task}'
        case={'id':cid,'claim':{'text':'Original.','language':'de'}}
        case['booklet' if task=='A' else 'reference']={'language':'de', **({'path':'fictional-unused.pdf'} if task=='A' else {'text':'Original.'})}
        cases.append(case);gold.append({'id':cid,'label':0,'reference':'Original.'})
        predictions.append({'id':cid,'label':0,'label_name':'entailment','evidence':[{'page':1,'text':'Original.'}],
                            'metrics':{'input_tokens':80,'output_tokens':20,'inference_time_ms':1}})
    for path,records in ((bundle/'cases.jsonl',cases),(bundle/'expected.jsonl',gold)):
        path.write_bytes(b''.join(c.encode(v)+b'\n' for v in records))
    complete={}
    for name in c.JOBS[:5]:
        job=out/name;job.mkdir();(job/'70b-canonical.jsonl').write_bytes(b''.join(c.encode(v)+b'\n' for v in predictions))
        complete[name]={'canonical_count':60,'complete':True,'source_valid':True,'model_valid':True,
                        'usage_known':True,'ledger_valid':True,'fallbacks':0,'review_available':0}
    monkeypatch.setattr(c,'BUNDLE',bundle);monkeypatch.setattr(c,'OUT',out)
    monkeypatch.setattr(c,'complete_arm',lambda control,arm:complete)
    result=c.grade_arm({},'candidate')
    assert len(result)==5
    assert all(v['f1a']==v['f1b']==v['hita']==1 and v['official']['official_commit']==c.EVALUATOR_COMMIT for v in result)
    with pytest.raises(ValueError,match='GRADING_REPLAY_REFUSED'):
        c.grade_arm({},'candidate')


@pytest.mark.parametrize('args,expected', [
    (('UNDECLARED_TOOLS_REFUSED',), 'UNDECLARED_TOOLS_REFUSED'),
    (('HARD_BUDGET_STOP_BEFORE_SEND',), 'HARD_BUDGET_STOP_BEFORE_SEND'),
    (('CASE_DEADLINE_ALL_STOP',), 'CASE_DEADLINE_ALL_STOP'),
    (('request_wall_deadline_no_retry',), 'request_wall_deadline_no_retry'),
    (('Bearer fictional-secret header=do-not-log',), 'unavailable'),
    (('UNDECLARED_TOOLS_REFUSED', 'do-not-log'), 'unavailable'),
    (({'secret': 'do-not-log'},), 'unavailable')])
def test_new_worker_safe_allowlisted_guard_diagnostic_preserves_fences(tmp_path, monkeypatch, args, expected):
    import types
    job = tmp_path / 'new-fictional-job'; job.mkdir()
    protected = {'STOP.json': b'original root fence', 'inflight.json': b'original logical reservation',
                 'physical/inflight.json': b'original unknown-cost reservation'}
    for relative, raw in protected.items():
        path = job / relative; path.parent.mkdir(exist_ok=True); path.write_bytes(raw)
    error = r.Stop(*args)
    def fail(*a):
        raise error
    core = types.SimpleNamespace(Stop=r.Stop, initialize=lambda *a:None, run=fail)
    monkeypatch.setattr(c.transport, 'PhysicalLedger', lambda *a:types.SimpleNamespace(client=None))
    with pytest.raises(r.Stop) as caught:
        c.run_guarded_job(core, job, {}, time.time()+300)
    assert caught.value is error
    assert c.load(job/'guard-stop.json') == {'code': expected, 'type': 'Stop'}
    assert 'do-not-log' not in (job/'guard-stop.json').read_text()
    assert all((job/relative).read_bytes() == raw for relative,raw in protected.items())
    # Even the new diagnostic cannot be overwritten on a repeated failure.
    with pytest.raises(r.Stop):
        c.run_guarded_job(core, job, {}, time.time()+300)
    assert c.load(job/'guard-stop.json')['code'] == expected


def test_new_guard_diagnostic_alone_fences_completed_result(tmp_path, monkeypatch):
    name = c.JOBS[0]
    job = tmp_path / name; job.mkdir()
    (job/'guard-stop.json').write_text('{"code":"unavailable","type":"Stop"}')
    monkeypatch.setattr(c, 'OUT', tmp_path)
    with pytest.raises(ValueError, match='STOP_OR_ORPHAN_FATAL'):
        c.completed_result(name, {})


@pytest.mark.parametrize('span_count',[0,1,2])
def test_selected_capture_proves_both_repairs_and_exact_report_every_later_parent(candidate,monkeypatch,span_count):
    manifest=candidate_manifest();item=manifest['frozen'][0]
    src=json.loads(item['messages'][1]['content']);base=src['source_spans'][0]
    src['source_spans']=[{**base,'span_id':f'original-{i}','text':'😀'*1200,'metadata':{'i':i}} for i in range(span_count)]
    item['candidate_ids']=[span['span_id'] for span in src['source_spans']]
    item['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    original=r.run_b;results=[]
    def observe(*args,**kwargs):
        result=original(*args,**kwargs);results.append(result);return result
    monkeypatch.setattr(r,'run_b',observe)
    packets=c.capture_sdk(r,manifest)
    accepted,diagnostics,sdk=results[0]
    assert diagnostics==[('RETRIEVAL_DUPLICATE_ID' if span_count else 'RETRIEVAL_UNKNOWN_ID'),'SUPPORTING_SPAN_REQUIRED']
    assert sdk['counts']=={'parent':3,'child':2,'reviewer':0}
    raw=sdk['review_audit']['raw_helper_args']
    assert len(raw)==2
    assert json.loads(raw[0])=={'candidate_ids':[item['candidate_ids'][0]]*2 if span_count else ['offline-invalid-original-id']}
    assert json.loads(raw[1])==c.fictional_selection(item)
    for packet in packets[-2:]:
        reports=[json.loads(m['content']) for m in packet['payload']['messages'] if m['role']=='tool' and 'source_evidence' in m['content']]
        assert reports==[{'source_evidence':sdk['source_evidence']}]
        assert len(reports[0]['source_evidence']['evidence_candidates'])==span_count
        assert 'raw_helper_args' not in json.dumps(reports)
    assert r.SUPPORTING_SPAN_MESSAGE in json.dumps(packets[-1]['payload']['messages'])
    assert accepted=={'label':1,'candidate_ids':[]}


@pytest.mark.parametrize('target',['second_child','third_parent'])
def test_full_repair_native_byte_guard_rejects_late_only_oversize(candidate,monkeypatch,target):
    manifest=candidate_manifest();item=manifest['frozen'][0]
    src=json.loads(item['messages'][1]['content']);base=src['source_spans'][0]
    src['source_spans']=[{**base,'span_id':f'full-{i}','text':'源'*1200} for i in range(2)]
    item['candidate_ids']=[span['span_id'] for span in src['source_spans']]
    item['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    original=r.legacy.encode;observed=[]
    def encode(value):
        raw=original(value)
        if isinstance(value,dict) and value.get('model') in r.MODELS and value.get('messages'):
            messages=value['messages'];child=value['model']==r.MODELS[0]
            second_child=child and any(m['role']=='assistant' for m in messages)
            third_parent=not child and any(m['role']=='tool' and r.SUPPORTING_SPAN_MESSAGE in m['content'] for m in messages)
            hit=second_child if target=='second_child' else third_parent
            observed.append((hit,len(raw)))
            assert len(raw)<=240000
            if hit:
                if target=='third_parent':
                    report=next(json.loads(m['content'])['source_evidence'] for m in messages if m['role']=='tool' and 'source_evidence' in m['content'])
                    assert len(report['evidence_candidates'])==2
                return raw+b'x'*240000
        return raw
    monkeypatch.setattr(r.legacy,'encode',encode)
    with pytest.raises(ValueError,match='NATIVE_PACKET_BYTE_LIMIT'):c.capture_sdk(r,manifest)
    assert observed and observed[-1][0] and not any(hit for hit,_ in observed[:-1])
