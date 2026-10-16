"""Controller integration on entirely fictional local inputs; no owner bundle."""
import copy
import json
from pathlib import Path
import sys
import time

import pytest
sys.path.insert(0, str(Path(__file__).parent))
import fragment_review_research as c
from test_fragment_review import candidate, offline, candidate_manifest, r, backend
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
    assert [p['role'] for p in packets]==['parent','child','reviewer','parent']
    assert all(p['bytes'] <= 240000 and p['sha256']==c.sha(r.legacy.encode(p['payload'])) for p in packets)
    # Includes the later parent packet containing actual helper reports.
    later=packets[-1]['payload']
    assert any(m['role']=='tool' and 'source_review' in m['content'] for m in later['messages'])


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
        for role,n in [('parent',0),('child',0),('reviewer',0),('parent',1)]:
            # Exact original SDK payloads captured in the first backend below.
            post(role,n,copy.deepcopy(payloads[(role,n)]))
        return copy.deepcopy(saved[0])
    payloads={}; counts={}
    class Fake:
        def __init__(self,model):self.model=model
        def request(self,method,path,payload):
            names={t['function']['name'] for t in payload['tools']}
            role='reviewer' if names=={'review_source'} else 'parent' if 'subagent' in names else 'child'
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
    assert result['canonical_count']==60 and result['canonical_successful_calls']==240
    assert result['review_available']==60 and result['parent_tool_report_cases']==60
    assert result['role_usage']['reviewer']['input_tokens']==4800
    assert result['physical_calls_by_role']=={'parent':120,'child':60,'reviewer':60}
    assert result['review_states']=={'fact_pair_selected':0,'no_fact_pair_selected':60,'review_unavailable':0}
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
    monkeypatch.setattr(c,'CONTROL',out/'fragment-review-v1-protocol.json')
    monkeypatch.setattr(c,'reference_binding',lambda:{'fictional_saved_control':True,'analysis':{}})
    c.prepare_only()
    control=c.verify_freeze()
    assert len(control['jobs'])==5
    for name,binding in control['jobs'].items():
        workspace=Path(binding['workspace'])
        audit=c.load(workspace/'offline-packets.json')
        assert audit['cases']==60 and len({p['case_index'] for p in audit['packets']})==60
        assert not (workspace/'expected.jsonl').exists()
        assert not (out/name).exists()  # preparation NEVER initializes a ledger
        assert all(p['bytes']<=240000 for p in audit['packets'])
    assert len(list(out.glob('*-workspace')))==5


def test_availability_requires_valid_report_delivered_in_parent_input():
    valid = {'status': 'no_fact_pair_selected', 'report': {'axis': 'none'}}
    unavailable = {'status': 'review_unavailable', 'reason': 'LIMIT'}
    assert not c.review_available_to_parent(valid, [])
    assert c.review_available_to_parent(valid, [{'source_review': valid}])
    assert not c.review_available_to_parent(unavailable, [{'source_review': unavailable}])
    with pytest.raises(ValueError, match='PARENT_REPORT_CHANGED'):
        c.review_available_to_parent(valid, [{'source_review': unavailable}])


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


def test_maximal_rendered_pair_in_full_native_parent_packet(candidate):
    x=candidate_manifest()['frozen'][0]
    src=json.loads(x['messages'][1]['content'])
    src['claim']='😀'*80+'\\'*80
    original=src['source_spans'][0]
    original['text']='😀'*120+'\\'*120
    x['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    manifest=candidate_manifest();manifest['frozen']=[x]
    packets=c.capture_sdk(r,manifest)
    parent=packets[-1]['payload']
    report=json.loads(next(m['content'] for m in parent['messages'] if m['role']=='tool'))['source_review']
    fact=report['facts'][0]
    assert len(fact['claim_quote'])==80 and len(fact['source_quote'])==120
    assert report['host_rendered_id_selections'] and all(p['bytes']<=240000 for p in packets)
    # Each selectable pair has a no-longer serialized report than the chosen one.
    import fragment_review_contract as fc
    view=fc.inventory(src)
    maximum=len(c.encode(report))
    for cid in fc.selectable(view,'claim'):
        for sid in fc.selectable(view,'source'):
            args={'checks':[{'axis':'condition','claim_fragment_id':cid,'source_fragment_id':sid}]}
            assert len(c.encode(fc.validate(args,src)))<=maximum


def test_saved_reference_300_paths_archived_dispatch_and_mutation_fences(tmp_path,monkeypatch):
    """Fictional saved control artifacts. Official/ledger check delegated read-only."""
    import types
    import fragment_review_contract as fc
    root=tmp_path;out=root/'output/cscs';out.mkdir(parents=True)
    auto=root/'.auto';(auto/'protocol-archive').mkdir(parents=True)
    controls={}
    for name in ('measure.sh','checks.sh'):
        original=b'fictional original dispatcher\n'
        (auto/'protocol-archive'/('role-review-v1-'+name)).write_bytes(original)
        (auto/name).write_bytes(b'# BEGIN fragment-review-v1 additive\nnew dispatch\n# END fragment-review-v1 additive\n'+original)
        controls['.auto/'+name]=c.sha(original)
    (auto/'old-helper.py').write_text('# immutable fictional helper\n')
    controls['.auto/old-helper.py']=c.sha((auto/'old-helper.py').read_bytes())
    analysis={'mean_Q':0.7293563908542025,'repeats':[{'fallbacks':0}]*5}
    analysis_file=out/'role-review-v1-baseline-analysis.json';analysis_file.write_bytes(c.encode(analysis))
    jobs={}
    for repeat in range(1,6):
        name=f'role-review-v1-baseline-r{repeat}';ws=out/(name+'-workspace');ws.mkdir()
        packets=[]
        for index in range(60):
            payload={'model':r.MODELS[1],'messages':[{'role':'user','content':f'fictional saved path {index}'}]}
            packets.append({'case_index':index,'payload':payload,'sha256':c.sha(c.encode(payload))})
        (ws/'offline-packets.json').write_bytes(c.encode({'cases':60,'remote_calls':0,'packets':packets}))
        jobs[name]={'workspace':str(ws),'files':c.fingerprint(list(ws.iterdir()),ws)}
        (out/name).mkdir();(out/name/'canonical.jsonl').write_text('fictional saved outputs\n')
        (out/(name+'-official.json')).write_text('{"fictional_saved_official":true}')
    old={'controls':controls,'runtime':{},'jobs':jobs,'policy':{'jobs':{}}}
    control=out/'role-review-v1-protocol.json';control.write_bytes(c.encode(old))
    monkeypatch.setattr(c,'ROOT',root);monkeypatch.setattr(c,'OUT',out);monkeypatch.setattr(c,'OLD_CONTROL',control)
    monkeypatch.setattr(c,'OLD_PROTOCOL_SHA256',c.sha(control.read_bytes()))
    checks=[]
    saved=types.SimpleNamespace(bundle_manifest=lambda:({},{}),prospective_bindings=lambda *a:old['policy'],
        checked_analysis=lambda control,arm:checks.append(arm) or analysis,analysis_path=lambda arm:analysis_file)
    monkeypatch.setitem(sys.modules,'role_review_research',saved)
    binding=c.reference_binding()
    assert binding['saved_sdk_case_paths']==300 and checks==['baseline']
    c.checked_reference({'reference':binding})
    # Hash drift, dispatcher mutation and saved-packet drift must all fence.
    (auto/'old-helper.py').write_text('# changed\n')
    with pytest.raises(ValueError,match='OLD_CONTROL_CHANGED'):c.reference_binding()
    (auto/'old-helper.py').write_text('# immutable fictional helper\n')
    (auto/'measure.sh').write_bytes((auto/'measure.sh').read_bytes()+b'changed old bytes\n')
    with pytest.raises(ValueError,match='OLD_DISPATCH_CHANGED'):c.reference_binding()
    (auto/'measure.sh').write_bytes(b'# BEGIN fragment-review-v1 additive\nnew dispatch\n# END fragment-review-v1 additive\nfictional original dispatcher\n')
    packet=Path(jobs['role-review-v1-baseline-r1']['workspace'])/'offline-packets.json'
    packet.write_bytes(b'{}')
    with pytest.raises(ValueError,match='OLD_WORKSPACE_CHANGED'):c.reference_binding()
