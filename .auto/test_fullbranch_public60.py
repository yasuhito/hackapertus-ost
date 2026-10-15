"""Fictional branch proof and controller guards; no real labels/claims/responses."""
import ast
import copy
import itertools
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from unittest.mock import Mock
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import fullbranch_public60 as p
sys.path.insert(0, str(p.ROOT / 'track_2a/dev/format'))
import run_comparison as r
from test_comparison import item, response, tool


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('network/credentials forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)
    monkeypatch.setenv('PI_PACKAGE_ROOT', str(p.SDK))
    monkeypatch.setenv('PI_SUBAGENTS_ROOT', str(p.CHILD))


def projected_schema():
    tree = ast.parse(p.projected_sources()[p.RUNNER])
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'schemas')
    scope = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<fictional-schema>', 'exec'), scope)
    return scope['schemas']


def test_two_functions_exact_and_full_copies(tmp_path):
    for relative in (p.RUNNER, p.WIRE_SDK):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p.ROOT / relative, target)
    p.patch_workspace(tmp_path)
    p.patch_proof(tmp_path)
    schemas = projected_schema()
    ids = ['fictional-' + str(i).zfill(26) for i in range(5)]
    assert all(len(i) == 36 for i in ids)
    for child in (False, True):
        old, new = r.schemas(ids, child), schemas(ids, child)
        common = copy.deepcopy(new[0]['function']['parameters'])
        branches = common.pop('anyOf')
        assert common == old[0]['function']['parameters']
        assert new[1:] == old[1:]
        for branch, labels in zip(branches, ([1], [0,2])):
            expected = copy.deepcopy(common)
            expected['properties']['label']['enum'] = labels
            if labels == [0,2]:
                expected['properties']['candidate_ids']['minItems'] = 1
            assert branch == expected
    (tmp_path / p.WIRE_SDK).write_bytes((tmp_path / p.WIRE_SDK).read_bytes() + b'\n')
    with pytest.raises(ValueError, match='WORKSPACE_PATCH_CHANGED'):
        p.patch_proof(tmp_path)


def test_compiled_old_h2_equivalence_and_no_accepted_tuple_excluded():
    ids = ['fictional-' + str(i).zfill(26) for i in range(5)]
    new = projected_schema()(ids)[0]['function']['parameters']
    old = copy.deepcopy(r.schemas(ids)[0]['function']['parameters'])
    old['anyOf'] = [{'properties': {'label': {'enum':[1]}}},
                    {'properties': {'candidate_ids': {'minItems':1}}}]
    arrays = [list(a) for n in range(7) for a in itertools.product(ids[:2], repeat=n)]
    arrays += [ids, ids+[ids[0]], ['wrong'], [False], [None], 'wrong', None, {}]
    cases = [None, {}, [], {'label':1}, {'candidate_ids':[]}]
    expected = [False]*len(cases)
    for label in [0,1,2,1.0,True,False,-1,3,'1',None]:
        for values in arrays:
            value = {'label':label, 'candidate_ids':values}
            valid = (type(label) in (int,float) and label in (0,1,2)
                     and isinstance(values,list) and len(values)<=5
                     and all(type(v) is str and v in ids for v in values)
                     and (label == 1 or len(values)>0))
            cases += [value, {**value,'extra':True}]
            expected += [valid, False]
    script = """import { Compile } from '/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/typebox/build/compile/index.mjs';
let data=''; for await (const c of process.stdin) data+=c;
const {schemas,cases}=JSON.parse(data);
console.log(JSON.stringify(schemas.map(s=>{ const v=Compile(s); return cases.map(c=>v.Check(c)); })));"""
    run = subprocess.run(['node','--input-type=module','-e',script], input=p.encode({'schemas':[old,new],'cases':cases}), capture_output=True, check=True, timeout=60)
    assert json.loads(run.stdout) == [expected,expected]
    # Prove through original assembler for all finite unique-ID subsets, strict labels.
    fictional = {'id':'fictional', 'claim':{'text':'Unrelated.'},
                 'reference':{'text':'One. Two. Three. Four. Five.'}}
    pages, _ = r.legacy.engine().context(fictional, Path('.'))
    supplied = [s['span_id'] for s in r.candidates(pages, True)]
    assert supplied and all(len(x)==36 for x in supplied)
    for label in (0,1,2):
        for n in range(min(5,len(supplied))+1):
            for values in itertools.combinations(supplied,n):
                args = {'label':label,'candidate_ids':list(values)}
                if label != 1 and not values:
                    with pytest.raises(ValueError):
                        r.submission.assemble_tool(args, fictional, pages, {'input_tokens':1,'output_tokens':1,'inference_time_ms':0})
                else:
                    r.submission.assemble_tool(args, fictional, pages, {'input_tokens':1,'output_tokens':1,'inference_time_ms':0})
                    schema = projected_schema()(supplied)[0]['function']['parameters']
                    assert args['label'] in schema['properties']['label']['enum']
                    assert any(label in b['properties']['label']['enum'] and n >= b['properties']['candidate_ids'].get('minItems',0) for b in schema['anyOf'])


def test_actual_sdk_candidate_two_roles_same_schema_and_logical_caps(tmp_path):
    for source in p.source_files():
        target = tmp_path / source.relative_to(p.ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source,target)
    p.patch_workspace(tmp_path)
    candidate = p.module(tmp_path / p.RUNNER, 'fictional_candidate')
    x = item()
    seen = []
    def post(role, number, payload):
        seen.append((role,number))
        candidate.enforce_tools(payload,x['candidate_ids'],role)
        want = projected_schema()(x['candidate_ids'],role=='child')
        assert [t['function']['parameters'] for t in payload['tools']] == [t['function']['parameters'] for t in want]
        name = payload['tool_choice']['function']['name']
        args = {'mode':'source_only'} if name=='subagent' else {'label':0,'candidate_ids':[]}
        return response(payload['model'],calls=[tool(name,args)])
    args, diagnostics, sdk = candidate.run_b(x,r.MODELS[1],post,strategy='C',isolation_guard=True)
    assert args is None and sdk['counts']=={'parent':3,'child':2}
    assert seen == [('parent',0),('child',0),('child',1),('parent',1),('parent',2)]
    assert diagnostics == ['SUPPORTING_SPAN_REQUIRED']*4


def good_results(fallback=7):
    return [dict(valid=60-fallback, fallback=fallback, usage_known=True,
                 F1A=.60,F1B=.75,Q=.8029455012419827,HitA=.30) for _ in range(5)]


def test_quality_exact_floors_and_no_primary_gate():
    p.quality(good_results(60))  # even 300 fallbacks isn't a correctness gate
    for key in ('F1A','F1B','Q','HitA'):
        values=good_results()
        for value in values:
            value[key] -= 1e-12
        with pytest.raises(ValueError):
            p.quality(values)
    with pytest.raises(ValueError):
        p.quality(good_results()[:4])


def test_reference_is_readonly_original_h1_import(monkeypatch):
    original = {'jobs':['original-v5-not-h1-or-h2'],'results':[{'fallback':7}]}
    bind=Mock(return_value=original)
    monkeypatch.setattr(p.h1,'reference_binding',bind)
    assert p.reference_binding() is original
    bind.assert_called_once_with()


def test_all_five_complete_before_any_grader(monkeypatch,tmp_path):
    monkeypatch.setattr(p,'CONTROL',tmp_path/'protocol.json')
    monkeypatch.setattr(p,'OUT',tmp_path)
    jobs=[{'name':p.job_name('v5',i)} for i in range(1,6)]
    p.exclusive(p.CONTROL,{'jobs':jobs})
    seen=[]
    def incomplete(job):
        seen.append(job.name)
        if job.name==jobs[-1]['name']:
            raise ValueError('INCOMPLETE')
        return {}
    monkeypatch.setattr(p,'completed_result',incomplete)
    monkeypatch.setattr(p.subprocess,'run',lambda *a,**k:pytest.fail('partial grader'))
    with pytest.raises(ValueError,match='INCOMPLETE'):
        p.grade_job(tmp_path/jobs[0]['name'])
    assert seen==[j['name'] for j in jobs]
    assert not list(tmp_path.glob('*-official.json'))


@pytest.mark.parametrize('exists', ['phase','job','STOP'])
def test_execute_replay_fatal_before_subprocess(tmp_path,monkeypatch,exists):
    monkeypatch.setattr(p,'OUT',tmp_path)
    monkeypatch.setattr(p,'CONTROL',tmp_path/'control.json')
    p.exclusive(p.CONTROL,{})
    jobs=[{'name':p.job_name('v5',i)} for i in range(1,6)]
    monkeypatch.setattr(p,'verify',lambda:{'jobs':jobs})
    monkeypatch.setattr(p,'check_reference',lambda c:None)
    monkeypatch.setattr(p.subprocess,'run',lambda *a,**k:pytest.fail('rerun'))
    target = p.phase_path('v5') if exists=='phase' else tmp_path/(jobs[0]['name'] if exists=='job' else 'public60-fullbranch-v1-STOP.json')
    target.write_text('{}')
    with pytest.raises(ValueError,match='REPLAY'):
        p.execute(time.time())


def test_dispatch_additions_leave_archived_branches_exact():
    before = (p.ROOT/'.auto/protocol-archive/fullbranch-before-measure.sh').read_text()
    after = (p.ROOT/'.auto/measure.sh').read_text()
    start = after.index('  --fullbranch-prepare|')
    end = after.index('  --provider-schema-edge-prepare)',start)
    assert after[:start]+after[end:] == before
    before=(p.ROOT/'.auto/protocol-archive/fullbranch-before-checks.sh').read_text()
    after=(p.ROOT/'.auto/checks.sh').read_text()
    start=after.index("if mode in ('fullbranch_reference'")
    end=after.index("elif mode == 'provider_schema_edge':",start)
    assert after[:start]+'if'+after[end+4:] == before


def test_approval_and_namespace():
    for value in (None,time.time()-181,time.time()+10):
        with pytest.raises(ValueError): p.fresh_approval(value)
    for name in ('h1','h2','v16'):
        with pytest.raises(ValueError): p.job_name(name,1)
    assert [p.job_name('v5',i) for i in range(1,6)] == [f'public60-fullbranch-v1-r{i}' for i in range(1,6)]

@pytest.mark.parametrize('fallback', [False,True])
def test_completed_all60_canonical_including_fallback_known_subtotal(tmp_path,monkeypatch,fallback):
    monkeypatch.setattr(p,'OUT',tmp_path)
    monkeypatch.setattr(p,'CONTROL',tmp_path/'no-control')
    job=tmp_path/p.job_name('v5',1)
    frozen=[]
    for index in range(60):
        value=item();value['case']['id']=f'fictional-{index}'
        frozen.append(value)
    m={'strategy':'C','models':[r.MODELS[1]],'role_models':{'parent':r.MODELS[1],'child':r.MODELS[0]},
       'request_limit':300,'token_budget':p.BUDGET,'frozen':frozen}
    r.initialize(job,m)
    side=p.physical.PhysicalLedger(r,job,time.monotonic()+300)
    class Base:
        def __init__(self,model):self.model=model
        def request(self,*a):return response(self.model,content='fictional')
    def sdk(x,model,post,**kwargs):
        post('parent',0,{'model':model})
        return (None if fallback else {'label':1,'candidate_ids':[]}), [], {}
    monkeypatch.setattr(r,'run_b',sdk)
    r.run(job,m,lambda model:side.client(model,Base))
    monkeypatch.setattr(p,'module',lambda *a:r)
    stats=p.completed_result(job,bind=False)
    assert stats['fallback']==(60 if fallback else 0)
    assert stats['valid']+stats['fallback']==60
    assert stats['tokens']==stats['known_successful_tokens']==6000
    assert stats['requests']==stats['physical_requests']==60
    canonical=p.rows(job/'70b-canonical.jsonl')
    assert len(canonical)==60 and all(v['label']==1 for v in canonical)
    assert sum(v['metrics']['input_tokens']+v['metrics']['output_tokens'] for v in canonical)==6000
    (job/'STOP.json').write_text('{}')
    with pytest.raises(ValueError,match='STOP_OR_ORPHAN'):
        p.completed_result(job,bind=False)
