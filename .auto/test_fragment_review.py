"""Fictional fragments and actual pinned Pi/runAgent; no credentials or API."""
import copy
import itertools
import json
from pathlib import Path
import shutil
import socket
import sys

import pytest
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'track_2a/dev/format'))
import fragment_review_contract as c
import fragment_review_worker as w
import run_comparison as r
from test_comparison import item, response, tool


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError('network/credentials forbidden')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(r.legacy.c, 'read_key', forbidden)


def source():
    return {'claim': 'final_verification 😀 É\n' + 'x' * 160 + '   ', 'final_verification': 'NLI select label',
            'task': 'A', 'vote': {'text': 'verbatim factual vote'}, 'languages': ['de', 'fr'],
            'source_spans': [{'span_id': 'original-1', 'page': 1, 'text': '源😀\n' + 'a' * 245},
                             {'span_id': 'original-2', 'page': 2, 'text': ' \n\t' * 90},
                             {'span_id': 'original-3', 'page': 3, 'text': ''}]}


@pytest.mark.parametrize('value', ['', ' \n\t'*150, '😀'*321, 'e\u0301'*161, 'x'*500,
                                   'x'*45+' '+ 'y'*300, 'x'*300+' final_verification'])
@pytest.mark.parametrize('width', [80, 120])
def test_partition_complete_unicode_whitespace(value, width):
    parts = c.partition(value, width)
    assert ''.join(p[2] for p in parts) == value
    assert all(0 < end-start <= width and value[start:end] == quote for start,end,quote in parts)
    assert [p[0] for p in parts] == [0] + [p[1] for p in parts[:-1]] if parts else parts == []
    assert parts == c.partition(value, width)


def test_split_preference_and_full_projection():
    assert c.partition('a'*44+' '+ 'z'*100, 80)[0][1] == 45
    assert c.partition('a'*10+' '+ 'z'*100, 80)[0][1] == 80
    src = source(); before = copy.deepcopy(src); view = c.inventory(src)
    data = c.projection(src, view)
    assert src == before and 'NLI select label' not in data
    assert '\nFULL CLAIM\n'+src['claim']+'\nCLAIM FRAGMENTS\n' in data
    metadata={k:v for k,v in src.items() if k not in ('claim','source_spans','final_verification')}
    assert '\n'+json.dumps(metadata,ensure_ascii=False,separators=(',',':'))+'\n' in data
    assert ''.join(fragment['text'] for fragment in view['claim']) == src['claim']
    for index, span in enumerate(src['source_spans']):
        assert ''.join(f['text'] for f in view['source'] if f['span_index'] == index) == span['text']
        meta={k:v for k,v in span.items() if k not in ('text','span_id')}
        assert 'SOURCE SPAN METADATA\n'+json.dumps(meta,ensure_ascii=False,separators=(',',':')) in data
    for fragment in view['claim']+view['source']:
        assert f"[{fragment['id']}] {fragment['text']}\n" in data
    assert any(not f['text'].strip() for f in view['source'])
    assert all(f['text'].strip() for f in c.selectable(view,'source').values())
    assert c.base36(36) == '10'


def test_projection_metadata_names_cannot_overwrite_facts():
    src=source();src['claim_fragments']='original metadata';src['fragment_columns']={'facts':'unchanged'}
    data=c.projection(src)
    metadata={k:v for k,v in src.items() if k not in ('claim','source_spans','final_verification')}
    assert json.dumps(metadata,ensure_ascii=False,separators=(',',':')) in data


def test_every_finite_native_tuple_restores_exact_original():
    src=source(); view=c.inventory(src); schema=c.schema(view)
    assert 'anyOf' not in json.dumps(schema) and 'uniqueItems' not in json.dumps(schema)
    for axis, cid, sid in itertools.product(c.AXES, c.selectable(view,'claim'), c.selectable(view,'source')):
        args={'checks':[{'axis':axis,'claim_fragment_id':cid,'source_fragment_id':sid}]}
        report=c.validate(args,src); fact=report['facts'][0]
        assert report['status']=='fact_pair_selected' and report['host_rendered_id_selections']
        assert src['claim'][slice(*fact['claim_offsets'])] == fact['claim_quote']
        span=next(s for s in src['source_spans'] if s['span_id']==fact['candidate_id'])
        assert span['text'][slice(*fact['source_offsets'])] == fact['source_quote']
        assert len(fact['claim_quote'])<=80 and len(fact['source_quote'])<=120
        assert 'relevance is not proven' in report['note']
    assert c.validate({'checks':[]},src)['status']=='no_fact_pair_selected'
    assert 'not agreement, entailment or contradiction' in c.NOTE


@pytest.mark.parametrize('src', [{'claim':'','source_spans':[]}, {'claim':'  ','source_spans':[{'span_id':'a','text':'x'}]},
                                 {'claim':'a','source_spans':[{'span_id':'a','text':' \n'}]}])
def test_empty_inventory_only_empty_checks_without_empty_enum(src):
    schema=c.schema(c.inventory(src))
    assert schema['properties']['checks']['maxItems']==0
    assert '"enum": []' not in json.dumps(schema)
    c.validate({'checks':[]},src)
    with pytest.raises(ValueError): c.validate(selection(),src)


def selection():
    return {'checks':[{'axis':'number','claim_fragment_id':'c0','source_fragment_id':'s0'}]}


@pytest.mark.parametrize('args', [None, [], {}, {'checks':None}, {'checks':{},'label':1},
    {'checks':[{},{}]}, {'checks':[{}]}, {'checks':[], 'label':0},
    {'checks':[{'axis':1,'claim_fragment_id':'c0','source_fragment_id':'s0'}]},
    {'checks':[{'axis':'number','claim_fragment_id':0,'source_fragment_id':'s0'}]},
    {'checks':[{'axis':'number','claim_fragment_id':'c0','source_fragment_id':True}]},
    {'checks':[{'axis':'number','claim_fragment_id':'c0','source_fragment_id':'unknown'}]},
    {'checks':[{'axis':'number','claim_fragment_id':'c0','source_fragment_id':'s0','label':0}]},
    {'checks':[{'axis':'none','claim_fragment_id':'c0','source_fragment_id':'s0'}]},
    {'checks':[{'axis':'number','claim_fragment_id':'\ud800','source_fragment_id':'s0'}]},
    {'checks':[selection()['checks'][0]]*2}])
def test_strict_no_coercion_unknown_extra_surrogate_duplicates(args):
    with pytest.raises(ValueError): c.validate(args,source())


def candidate_manifest():
    return {'variant':w.VARIANT,'strategy':'C','models':[r.MODELS[1]],
            'role_models':{'parent':r.MODELS[1],'child':r.MODELS[0],'reviewer':r.MODELS[0]},
            'request_limit':300,'token_budget':78720000,'frozen':[item()]}


@pytest.fixture
def candidate(tmp_path,monkeypatch):
    fmt=tmp_path/'track_2a/dev/format';fmt.mkdir(parents=True)
    for path in r.HERE.iterdir():
        if path.suffix in ('.ts','.mjs','.json'): shutil.copyfile(path,fmt/path.name)
    w.install_templates(fmt);monkeypatch.setattr(r,'HERE',fmt)
    with w.candidate_hooks(r,candidate_manifest()): yield r


def backend(x,calls,review=None,child_label=1):
    def post(role,number,payload):
        calls.append((role,number,copy.deepcopy(payload)))
        w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
        name=payload['tool_choice']['function']['name']
        args=({'mode':'source_only'} if name=='subagent' else
              review(number,payload) if role=='reviewer' and review else {'checks':[]} if role=='reviewer' else
              {'label':child_label if role=='child' else 0,'candidate_ids':x['candidate_ids']})
        return response(payload['model'],calls=[tool(name,args)])
    return post


def test_large_ascii_source_complete_sdk_packets_fit_without_factual_loss(candidate):
    x=item();data=json.loads(x['messages'][1]['content'])
    data['source_spans']=[{'span_id':f'original-span-{i:022d}','page':i//10+1,
                           'text':('alpha beta '*55)[:600]} for i in range(300)]
    x['candidate_ids']=[s['span_id'] for s in data['source_spans']]
    x['messages'][1]['content']=json.dumps(data,ensure_ascii=False)
    before=copy.deepcopy(x);calls=[]
    def post(role,number,payload):
        assert len(r.legacy.encode(payload))<=240000, 'NATIVE_PACKET_BYTE_LIMIT'
        calls.append(role);w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
        name=payload['tool_choice']['function']['name']
        args=({'mode':'source_only'} if name=='subagent' else selection() if role=='reviewer'
              else {'label':1,'candidate_ids':[]})
        return response(payload['model'],calls=[tool(name,args)])
    args,diagnostics,sdk=r.run_b(x,r.MODELS[1],post,strategy='C',seconds=45)
    assert args=={'label':1,'candidate_ids':[]} and not diagnostics and x==before
    assert calls==['parent','child','reviewer','parent']
    assert sdk['source_review']==c.validate(selection(),data)


@pytest.mark.parametrize('pair', [False, True])
def test_actual_sdk_role_projection_independence_and_delivered_counts(candidate,pair):
    x=item();data=json.loads(x['messages'][1]['content']);data['final_verification']='NLI recommendation only'
    x['messages'][1]['content']=json.dumps(data);before=copy.deepcopy(x);calls=[]
    args,diagnostics,sdk=r.run_b(x,r.MODELS[1],backend(x,calls,lambda n,p:selection() if pair else {'checks':[]}),strategy='C',seconds=45)
    assert args=={'label':0,'candidate_ids':x['candidate_ids']} and not diagnostics and x==before
    assert sdk['counts']=={'parent':2,'child':1,'reviewer':1}
    for role,_,payload in calls:
        user=next(m['content'] for m in payload['messages'] if m['role']=='user')
        assert user==(c.projection(data) if role=='reviewer' else x['messages'][1]['content'])
        assert len(r.legacy.encode(payload))<=240000
        assert payload['model']==r.MODELS[1 if role=='parent' else 0]
    review=calls[2][2]
    assert [m['role'] for m in review['messages']]==['system','user']
    assert [t['function']['name'] for t in review['tools']]==['review_source']
    assert 'NLI recommendation only' not in review['messages'][1]['content']
    delivered=sdk['review_audit']['parent_tool_reports']; assert len(delivered)==1
    assert delivered[0]['source_review']==sdk['source_review']
    assert delivered[0]['recommendation']=={'label':1,'candidate_ids':x['candidate_ids']}
    assert sdk['source_review']['status']==('fact_pair_selected' if pair else 'no_fact_pair_selected')
    assert any(e['type']=='package_review_completed' and e['tools']==['review_source'] for e in sdk['events'])
    assert not any(e['type'].startswith('auto_') for e in sdk['events'])


@pytest.mark.parametrize('repair',[True,False])
@pytest.mark.parametrize('bad',['unknown','malformed','duplicate','surrogate','coercible','extra'])
def test_actual_sdk_one_repair_or_explicit_unavailable(candidate,repair,bad):
    x=item();calls=[]
    def post(role,n,payload):
        value=backend(x,calls,lambda n,p:selection())(role,n,payload)
        if role=='reviewer' and (n==0 or not repair):
            args=selection()
            if bad=='unknown': args['checks'][0]['source_fragment_id']='unknown'
            if bad=='surrogate': args['checks'][0]['claim_fragment_id']='\ud800'
            if bad=='coercible': args['checks'][0]['claim_fragment_id']=1
            if bad=='extra': args['label']=0
            raw='{' if bad=='malformed' else '{"checks":[],"checks":[]}' if bad=='duplicate' else json.dumps(args)
            value['choices'][0]['message']['tool_calls'][0]['function']['arguments']=raw
        return value
    args,diagnostics,sdk=r.run_b(x,r.MODELS[1],post,strategy='C',seconds=45)
    assert args and sdk['counts']['reviewer']==2 and len(diagnostics)==(1 if repair else 2)
    assert sdk['source_review']['status']==('fact_pair_selected' if repair else 'review_unavailable')
    assert sdk['review_audit']['parent_tool_reports'][0]['source_review']==sdk['source_review']


def test_actual_empty_path_still_explicit_no_pair(candidate):
    x=item();x['candidate_ids']=[];data=json.loads(x['messages'][1]['content']);data['source_spans']=[]
    x['messages'][1]['content']=json.dumps(data)
    def post(role,n,p):
        name=p['tool_choice']['function']['name']
        args={'mode':'source_only'} if name=='subagent' else {'checks':[]} if role=='reviewer' else {'label':1,'candidate_ids':[]}
        return response(p['model'],calls=[tool(name,args)])
    args,diags,sdk=r.run_b(x,r.MODELS[1],post,strategy='C',seconds=45)
    assert args and not diags and sdk['counts']['reviewer']==1
    assert sdk['source_review']['status']=='no_fact_pair_selected'


def test_production_and_model_guards(candidate):
    with pytest.raises(ValueError,match='PRODUCTION'): w.install_templates(Path(__file__).resolve().parents[1]/'track_2a/dev/format')
    with pytest.raises(r.Stop):
        with w.candidate_hooks(r,{'variant':'baseline'}): pass
    x=item();r._fragment_view=c.inventory(json.loads(x['messages'][1]['content']))
    payload={'model':r.MODELS[0],'tools':[{'type':'function','function':{'name':'review_source','description':'fictional','parameters':c.schema(r._fragment_view)}}],
             'tool_choice':{'type':'function','function':{'name':'review_source'}}}
    w.enforce_bridge_tools(r,payload,x['candidate_ids'],'reviewer')
    for role in ['parent','child']:
        with pytest.raises(r.Stop): w.enforce_bridge_tools(r,payload,x['candidate_ids'],role)
    payload['model']=r.MODELS[1]
    with pytest.raises(r.Stop): w.enforce_bridge_tools(r,payload,x['candidate_ids'],'reviewer')


def test_h1_feedback_unchanged_parent3_child2_and_reviewer_usage(candidate):
    x=item(); calls=[]
    def post(role, number, payload):
        calls.append((role, number, copy.deepcopy(payload)))
        name=payload['tool_choice']['function']['name']
        if name == 'subagent': args={'mode':'source_only'}
        elif name == 'review_source': args={'checks':[]}
        else:
            rejected = role == 'child' and number == 0 or role == 'parent' and number == 1
            args={'label':0,'candidate_ids':[] if rejected else x['candidate_ids']}
            if not rejected:
                assert r.SUPPORTING_SPAN_MESSAGE in json.dumps(payload['messages'])
        return response(payload['model'],calls=[tool(name,args)])
    accepted, diagnostics, sdk=r.run_b(x,r.MODELS[1],post,isolation_guard=True,strategy='C',seconds=45)
    assert accepted and diagnostics==['SUPPORTING_SPAN_REQUIRED']*2
    assert sdk['counts']=={'parent':3,'child':2,'reviewer':1}
    usage=next(e['usage'] for e in sdk['events'] if e['type']=='subagent_usage')
    assert usage['input']==240 and usage['output']==60 and usage['totalTokens']==300

