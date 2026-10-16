"""Fictional full-source identity, strict types and exact host restoration."""
import copy
import itertools
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import span_retrieval_contract as c


def source():
    return {'claim':'😀 complete predicate\ncondition and attribution',
            'final_verification':'discard directive only', 'metadata':{'final_verification':'retain factual field','empty':''},
            'source_spans':[{'span_id':sid,'page':i,'text':text,'metadata':{'unicode':'源','order':[2,1]}}
                            for i,(sid,text) in enumerate([('original-A','😀'*1200),('original-B','源'*1200),('original-C','')])]}


@pytest.mark.parametrize('claim',['',' \n\t','😀'*1600,'e\u0301'*800])
def test_only_top_directive_removed_full_claim_all_fields_order(claim):
    src=source();src['claim']=claim;before=copy.deepcopy(src)
    raw=c.projection(src);dto=json.loads(raw)
    expected={k:v for k,v in src.items() if k!='final_verification'}
    assert dto==expected and list(dto)==list(expected) and src==before
    assert raw==json.dumps(expected,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    assert dto['source_spans']==src['source_spans']


def test_every_zero_one_two_selection_restores_full_objects_without_aliases():
    src=source();ids=[s['span_id'] for s in src['source_spans']]
    for count in range(3):
        for chosen in itertools.permutations(ids,count):
            args={'candidate_ids':list(chosen)};report=c.validate(args,src)
            assert report['candidate_ids']==list(chosen)
            assert report['evidence_candidates']==[next(s for s in src['source_spans'] if s['span_id']==sid) for sid in chosen]
            assert set(report)=={'status','candidate_ids','evidence_candidates','provenance','note'}
            assert report['status']==('source_spans_selected' if count else 'no_source_spans_selected')
    report=c.validate({'candidate_ids':ids[:2]},src)
    assert [len(s['text']) for s in report['evidence_candidates']]==[1200,1200]
    report['evidence_candidates'][0]['metadata']['order'].append(3)
    assert src['source_spans'][0]['metadata']['order']==[2,1]


@pytest.mark.parametrize('args',[None,[],{}, {'candidate_ids':None},{'candidate_ids':{}},
    {'candidate_ids':[],'label':0},{'candidate_ids':['unknown']},{'candidate_ids':['original-A']*2},
    {'candidate_ids':['original-A','original-B','original-C']},
    *[{'candidate_ids':[value]} for value in (0,1.0,True,False,None,{},[],'\ud800')]])
def test_strict_arguments_before_any_sdk_coercion(args):
    with pytest.raises(ValueError):c.validate(args,source())


def test_empty_schema_native_basic_types_and_unavailable_distinct():
    src={'claim':'','source_spans':[]};schema=c.schema(c.inventory(src))
    assert schema['properties']['candidate_ids']['maxItems']==0
    assert 'enum' not in json.dumps(schema)
    c.validate({'candidate_ids':[]},src)
    for src in (src,source()):
        encoded=json.dumps(c.schema(c.inventory(src)))
        assert not any(k in encoded for k in ('anyOf','uniqueItems','if','then'))
    assert c.unavailable('RETRIEVAL_SCHEMA')['status']=='evidence_unavailable'
    assert c.unavailable('RETRIEVAL_SCHEMA')!=c.validate({'candidate_ids':[]},src)
