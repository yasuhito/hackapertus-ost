"""Actual native packet byte maxima and unchanged Root identity gates."""
import copy
import itertools
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from test_dual_evidence import candidate, offline, candidate_manifest, r
import dual_evidence_research as research
import span_retrieval_contract as contract


def native_report_bytes(source, ids):
    content=json.dumps({'recommendation':{'label':1,'candidate_ids':[]},'source_evidence':contract.validate({'candidate_ids':list(ids)},source)},ensure_ascii=False,separators=(',',':'))
    return len(r.legacy.encode({'messages':[{'role':'tool','content':content}]}))


@pytest.mark.parametrize('metadata',[False,True])
def test_double_escaped_report_contribution_beats_longer_plain_text(candidate,metadata):
    manifest=candidate_manifest();x=manifest['frozen'][0]
    src=json.loads(x['messages'][1]['content'])
    src['source_spans']=[{'span_id':sid,'text':text,'page':1} for sid,text in [('a','a'*210),('b','b'*200),('c','"'*95)]]
    if metadata:
        src['source_spans'][2].update(metadata={'unicode':'😀源','escaped':'\\\n"'*80})
        src['source_spans'].append({'span_id':'escaped-"\\\n😀','text':'short','page':1,'metadata':{'raw':'"'*200}})
    x['candidate_ids']=[s['span_id'] for s in src['source_spans']]
    x['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    chosen=research.fictional_selection(x)['candidate_ids']
    if not metadata:
        assert chosen==['c','a']
        assert native_report_bytes(src,['a','c'])>native_report_bytes(src,['a','b'])
    maximum=native_report_bytes(src,chosen)
    for count in range(3):
        for ids in itertools.permutations(x['candidate_ids'],count):
            assert native_report_bytes(src,ids)<=maximum
    packets=research.capture_sdk(r,manifest)
    parent=packets[-1]['payload']
    msg=next(m for m in parent['messages'] if m['role']=='tool')
    report=json.loads(msg['content'])['source_evidence']
    assert report==contract.validate({'candidate_ids':chosen},src)
    # Prove the compact serializer used for ranking matches actual SDK output.
    assert msg['content']==json.dumps({'recommendation':{'label':1,'candidate_ids':[]},'source_evidence':report},ensure_ascii=False,separators=(',',':'))
    bound=len(r.legacy.encode(parent))
    for ids in itertools.permutations(x['candidate_ids'],2):
        alternative=copy.deepcopy(parent)
        next(m for m in alternative['messages'] if m['role']=='tool')['content']=json.dumps(
            {'recommendation':{'label':1,'candidate_ids':[]},'source_evidence':contract.validate({'candidate_ids':list(ids)},src)},ensure_ascii=False,separators=(',',':'))
        assert len(r.legacy.encode(alternative))<=bound<=240000


@pytest.mark.parametrize('mutation',['plaintext','missing','subset','reordered','tampered','duplicate','text','metadata','claim','schema','model','tool_choice','system'])
def test_root_rejects_mutated_full_source_before_http(candidate,monkeypatch,mutation):
    manifest=candidate_manifest();x=manifest['frozen'][0]
    src=json.loads(x['messages'][1]['content'])
    src['source_spans'].append({**src['source_spans'][0],'span_id':'fictional-second','metadata':{'retained':True}})
    x['candidate_ids']=[span['span_id'] for span in src['source_spans']]
    x['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    packets=research.capture_sdk(r,manifest)
    packet=copy.deepcopy(next(p['payload'] for p in packets if p['role']=='reviewer'))
    dto=json.loads(packet['messages'][1]['content'])
    if mutation=='system':packet['messages'][0]['content']+=' changed'
    elif mutation=='plaintext':packet['messages'][1]['content']='unstructured source'
    elif mutation=='missing':del dto['source_spans']
    elif mutation=='subset':dto['source_spans'].pop()
    elif mutation=='reordered':dto['source_spans'].reverse()
    elif mutation=='tampered':dto['source_spans'][0]['span_id']='unknown'
    elif mutation=='duplicate':dto['source_spans'][1]=dto['source_spans'][0]
    elif mutation=='text':dto['source_spans'][0]['text']+=' changed'
    elif mutation=='metadata':dto['source_spans'][1]['metadata']['retained']=False
    elif mutation=='claim':dto['claim']+=' changed'
    elif mutation=='schema':packet['tools'][0]['function']['parameters']['additionalProperties']=True
    elif mutation=='model':packet['model']=r.MODELS[1]
    elif mutation=='tool_choice':packet['tool_choice']='auto'
    if mutation!='plaintext':packet['messages'][1]['content']=json.dumps(dto,separators=(',',':'),ensure_ascii=False)
    monkeypatch.setenv('BASE_URL','http://fictional.invalid/v1');monkeypatch.setenv('API_KEY','fictional-dummy')
    def factory(*a,**kw):pytest.fail('guard must precede HTTP construction')
    with pytest.raises(r.Stop):r.Transport(packet['model'],submitted=True,factory=factory).request('POST','/v1/chat/completions',packet)


def test_all_prior_dispatch_archive_layers_source_only():
    controls=[research.load(path) for path in (research.OLD_CONTROL,research.FRAGMENT_CONTROL,research.BOUND_CONTROL,research.EVIDENCE_CONTROL,research.SPAN_CONTROL)]
    for relative in research.EVIDENCE_DISPATCH_SHA256:
        research.verify_additive_dispatch(relative,*[control['controls'][relative] for control in controls[:3]])
        assert controls[3]['controls'][relative]==research.EVIDENCE_DISPATCH_SHA256[relative]
    for control in controls:
        for relative,digest in control['controls'].items():
            if relative not in research.EVIDENCE_DISPATCH_SHA256:
                assert research.sha((research.ROOT/relative).read_bytes())==digest
    assert research.sha(research.EVIDENCE_CONTROL.read_bytes())==research.EVIDENCE_PROTOCOL_SHA256


def test_advice_allowance_bounds_every_idlist_and_unavailable(candidate):
    x=item_for_bound=candidate_manifest()['frozen'][0]
    src=json.loads(x['messages'][1]['content'])
    src['source_spans']=[{'span_id':sid,'text':'x','page':1} for sid in ['a','b','c','d','e','f','escaped-"\\\n😀']]
    x['candidate_ids']=[s['span_id'] for s in src['source_spans']]
    x['messages'][1]['content']=json.dumps(src,ensure_ascii=False)
    bound=research.ordinary_recommendation_bound(r,x)
    def size(v):return len(r.legacy.encode(json.dumps(v,ensure_ascii=False,separators=(',',':'))))
    normal={'label':1,'candidate_ids':[]}
    for count in range(6):
        for ids in itertools.combinations(x['candidate_ids'],count):
            # Input-only syntactic superset, not an assertion of citation legality.
            for label in (0,1,2):
                assert size({'label':label,'candidate_ids':list(ids)})-size(normal)<=bound
    assert size({'status':'recommendation_unavailable','reason':'NO_CHILD_SUBMIT'})-size(normal)<=bound


@pytest.mark.parametrize('role,n',[('child',1),('reviewer',1),('parent',2)])
def test_late_only_oversize_fails_before_root_http(candidate,monkeypatch,role,n):
    manifest=candidate_manifest();original=r.legacy.encode;seen=[]
    def encode(v):
        raw=original(v)
        if isinstance(v,dict) and v.get('model') in r.MODELS and v.get('messages'):
            names={t['function']['name'] for t in v.get('tools',[])}
            who='parent' if 'subagent' in names else 'reviewer' if 'select_source_spans' in names else 'child'
            assistants=sum(m['role']=='assistant' for m in v['messages'])
            if who==role and assistants==n:
                seen.append((who,n));return raw+b'x'*240000
            assert len(raw)<=240000
        return raw
    monkeypatch.setattr(r.legacy,'encode',encode)
    with pytest.raises(ValueError,match='NATIVE_PACKET_BYTE_LIMIT'):research.capture_sdk(r,manifest)
    assert seen==[(role,n)]
