"""Controller integration on entirely fictional local inputs; no owner bundle."""
import copy
import json
from pathlib import Path
import sys
import time

import pytest
sys.path.insert(0, str(Path(__file__).parent))
import dual_evidence_research as c
from test_dual_evidence import candidate, offline, candidate_manifest, r, backend
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
    assert [p['role'] for p in packets]==['parent','child','child','reviewer','reviewer','parent','parent']
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


def test_availability_requires_valid_report_delivered_in_parent_input():
    valid = {'status': 'no_source_spans_selected', 'report': {'axis': 'none'}}
    unavailable = {'status': 'evidence_unavailable', 'reason': 'LIMIT'}
    assert not c.review_available_to_parent(valid, [])
    assert c.review_available_to_parent(valid, [{'recommendation':{'label':1,'candidate_ids':[]},'source_evidence': valid}])
    assert not c.review_available_to_parent(unavailable, [{'recommendation':{'label':1,'candidate_ids':[]},'source_evidence': unavailable}])
    with pytest.raises(ValueError, match='PARENT_REPORT_CHANGED'):
        c.review_available_to_parent(valid, [{'recommendation':{'label':1,'candidate_ids':[]},'source_evidence': unavailable}])


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




def test_completed_result_real_sdk_physical_ledger_all_roles(candidate,tmp_path,monkeypatch):
    """One SDK path, sixty real canonical/physical ledger cases, no Root bypass."""
    manifest=candidate_manifest()
    manifest['frozen']=[copy.deepcopy(manifest['frozen'][0]) for _ in range(60)]
    for index,x in enumerate(manifest['frozen']):x['case']['id']=f'fictional-ledger-{index}'
    name=c.JOBS[0];job=tmp_path/name;r.initialize(job,manifest)
    side=t.PhysicalLedger(r,job,time.monotonic()+300)
    original=r.run_b;saved=[];payloads={};counts={}
    class Fake:
        def __init__(self,model):self.model=model
        def request(self,method,path,payload):
            names={x['function']['name'] for x in payload['tools']}
            role='parent' if 'subagent' in names else 'reviewer' if 'select_source_spans' in names else 'child'
            n=counts.get(role,0);counts[role]=n+1
            number=n%2 if role=='parent' else 0
            payloads[(role,number)]=copy.deepcopy(payload)
            return c.root_fake_request(r,payload,lambda:backend(manifest['frozen'][0],[])(role,number,payload))
    def once(x,model,post,**kw):
        if not saved:
            value=original(x,model,post,**kw);saved.append(value);return value
        for role,n in [('parent',0),('child',0),('reviewer',0),('parent',1)]:
            post(role,n,copy.deepcopy(payloads[(role,n)]))
        return copy.deepcopy(saved[0])
    monkeypatch.setattr(r,'run_b',once)
    r.run(job,manifest,lambda model:side.client(model,Fake))
    monkeypatch.setattr(c,'OUT',tmp_path)
    # Reconstruct with a fresh real core, never bypass a frozen verifier.
    import importlib.util
    spec=importlib.util.spec_from_file_location('dual_completed_core',c.ROOT/c.RUNNER)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    monkeypatch.setattr(c,'module',lambda _:core)
    result=c.completed_result(name,{'manifest_sha256':c.sha(c.encode(manifest))})
    assert result['canonical_count']==60 and result['canonical_successful_calls']==240
    assert result['physical_calls_by_role']=={'parent':120,'child':60,'reviewer':60}
    assert result['role_usage']['reviewer']['input_tokens']==4800
    assert result['review_available']==result['parent_tool_report_cases']==60
    assert result['review_states']=={'source_spans_selected':0,'no_source_spans_selected':60,'evidence_unavailable':0}
    assert all(v['normal_child_recommendation']=={'label':1,'candidate_ids':[]} for v in result['review_records'])
