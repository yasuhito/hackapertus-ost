"""Aggregate-only candidate comparison, no model calls or test transcript display."""
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', required=True, choices=('v3','v4','v5','v6','v7','v8','v9','v10','v11','v12','v13'))
version=parser.parse_args().candidate
import importlib.util,json,math,statistics
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/cscs';DEST=OUT/f'hillclimb-{version}-analysis'
from results import completed_jobs, reference_name, reference_noise
completed_jobs(OUT, version)
if (DEST/'comparison.json').exists(): raise SystemExit('REFUSED: existing comparison is archived; no overwrite')
spec=importlib.util.spec_from_file_location('official','/tmp/ost-official-evaluator-3U4yO9/repo/evaluate.py');official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
base=json.loads((OUT/reference_name(version)/'aggregate.json').read_text());candidate=json.loads((DEST/'aggregate.json').read_text());split=json.loads((ROOT/'evals/c-system-prompt/split.json').read_text());gold={r['id']:r['label'] for r in map(json.loads,(OUT/'official-rescore-evidence/expected.jsonl').read_text().splitlines())}
basepred=[];candpred=[];baserec=[];candrec=[];operations=[]
new_segment=int(version[1:])>=11
basem=json.loads((OUT/('prompt-C-v5-r5' if new_segment else 'format-C-r5')/'manifest.json').read_text())
def normalized_sources(m):return {k[k.index('track_2a/'):]:v for k,v in m['sources'].items()}
for i in range(1,6):
 bj=OUT/(f'prompt-C-v5-r{i}' if new_segment else (f'format-C-r{i}' if i!=4 else 'format-C-r4.'));cj=OUT/f'prompt-C-{version}-r{i}'
 cm=json.loads((cj/'manifest.json').read_text());assert len(cm['frozen'])==54 and cm['role_models']==basem['role_models']
 assert all(c['messages'][1:]==b['messages'][1:] and c['pages']==b['pages'] and c['candidate_ids']==b['candidate_ids'] for c,b in zip(cm['frozen'],basem['frozen']))
 bs=normalized_sources(basem);cs=normalized_sources(cm);assert bs.keys()==cs.keys()
 assert [k for k in bs if bs[k]!=cs[k]]==['track_2a/src/predict.py']
 assert not any((cj/f).exists() for f in ['inflight.json','STOP.json','state.pending'])
 basepred.append({r['id']:r for r in map(json.loads,(bj/'70b-canonical.jsonl').read_text().splitlines())});candpred.append({r['id']:r for r in map(json.loads,(cj/'70b-canonical.jsonl').read_text().splitlines())})
 baserec.append({r['case_id']:r for r in [json.loads((bj/f'70b-{j:02}-case.json').read_text()) for j in range(54)]});candrec.append({r['case_id']:r for r in [json.loads((cj/f'70b-{j:02}-case.json').read_text()) for j in range(54)]})
 summary=json.loads((cj/'summary.json').read_text());operations.append({'repeat':i,'POST':summary['generation_requests'],'tokens':summary['actual_total_tokens'],'valid':summary['models']['swiss-ai/Apertus-v1.5-70B']['output_valid'],'seconds':float((OUT/f'prompt-C-{version}-r{i}-end.txt').read_text())-float((OUT/f'prompt-C-{version}-r{i}-start.txt').read_text()),'API_wait_seconds':summary['models']['swiss-ai/Apertus-v1.5-70B']['api_wait_ms']/1000})
results={'reference_version': 'v5' if new_segment else 'v0', 'operations':operations,'source_audit':'All code hashes match except predict.py; all supplied user messages/pages/IDs match baseline; production unchanged.', 'splits':{}}
for part in ['train','test']:
 ids=split[part];chosen=set(ids);bs=base[part];cs=candidate[part];gain=cs['Q_mean']-bs['Q_mean'];noise=reference_noise(OUT,version,part)
 def metrics(preds,recs):
  rows=[preds[id] for id in ids];rr=[recs[id] for id in ids];times=sorted(r['case_wall_ms'] for r in rr)
  return {'valid':sum(r['output_valid'] for r in rr),'fallback_neutral':sum(r['error']=='NO_ACCEPTED_SUBMIT' and r['prediction']['label']==1 for r in rr),'contradiction_entailment':sum(gold[id]==2 and official.label_of(preds[id])[0]==0 for id in ids),'tokens':sum(p['metrics']['input_tokens']+p['metrics']['output_tokens'] for p in rows),'case_mean_ms':sum(times)/len(times),'case_p95_ms':times[math.ceil(.95*len(times))-1],'API_wait_ms':sum(r['api_wait_ms'] for r in rr)}
 bops=[metrics(p,r) for p,r in zip(basepred,baserec)];cops=[metrics(p,r) for p,r in zip(candpred,candrec)]
 groups=[g for g in split['groups'].values() if set(g)<=chosen];conf=np.zeros((2,len(groups),2,3,3))
 for arm,predictions in enumerate([basepred,candpred]):
  for j,g in enumerate(groups):
   for id in g:
    for p in predictions:conf[arm,j,['A','B'].index(id[-1]),gold[id],official.label_of(p[id])[0]]+=.2
 def f1(c):
  tp=np.diagonal(c,axis1=-2,axis2=-1);den=c.sum(axis=-1)+c.sum(axis=-2);active=den>0
  return np.divide(2*tp,den,out=np.zeros_like(tp),where=active).sum(axis=-1)/active.sum(axis=-1)
 indices=np.random.default_rng(split['seed']).integers(0,len(groups),size=(20000,len(groups)));boot=f1(conf[:,indices].sum(axis=2));q=(.30*boot[:,:,0]+.28*boot[:,:,1])/.58;delta=q[1]-q[0]
 results['splits'][part]={'baseline_mean_Q':bs['Q_mean'],'candidate_mean_Q':cs['Q_mean'],'gain':gain,'baseline_noise':noise,'noise_evidence':{'reference_temporal':bs['Q_temporal_detectable_difference'],'legacy_v0_temporal':json.loads((OUT/'hillclimb-split5-date-balanced-analysis/aggregate.json').read_text())[part]['Q_temporal_detectable_difference']},'literal_pass':gain>=.02 and gain>noise,'strict_pass':gain>=noise+.02,'paired_group_delta95':np.quantile(delta,[.025,.975]).tolist(),'baseline_operations':bops,'candidate_operations':cops,'baseline_F1_A_mean':statistics.mean(r['F1_A'] for r in bs['repeats']),'candidate_F1_A_mean':statistics.mean(r['F1_A'] for r in cs['repeats']),'baseline_F1_B_mean':statistics.mean(r['F1_B'] for r in bs['repeats']),'candidate_F1_B_mean':statistics.mean(r['F1_B'] for r in cs['repeats']),'baseline_Hit_A_mean':statistics.mean(r['Hit_A'] for r in bs['repeats']),'candidate_Hit_A_mean':statistics.mean(r['Hit_A'] for r in cs['repeats']),'candidate_safe_all':all(all(r['safe_passes'].values()) for r in cs['repeats'])}
results['adopt_literal']=all(s['literal_pass'] and s['candidate_safe_all'] for s in results['splits'].values());results['adopt_strict']=all(s['strict_pass'] and s['candidate_safe_all'] for s in results['splits'].values())
(DEST/'comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'operations':operations,'splits':{p:{k:v for k,v in r.items() if not k.endswith('_operations')} for p,r in results['splits'].items()},'adopt_literal':results['adopt_literal'],'adopt_strict':results['adopt_strict']},ensure_ascii=False,indent=2))
