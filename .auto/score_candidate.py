"""Machine-only official baseline split scoring; print aggregate scores only."""
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', required=True, choices=('v3','v4','v5','v6','v7','v8','v9','v10','v11','v12','v13','v12-retry1','v13-retry1'))
version=parser.parse_args().candidate
import importlib.util,json,math,statistics,os,tempfile
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/cscs';DEST=OUT/f'hillclimb-{version}-analysis';
from results import completed_jobs
completed_jobs(OUT, version)
DEST.mkdir(exist_ok=False)
(OUT/'tmp').mkdir(exist_ok=True);os.environ['TMPDIR']=str(OUT/'tmp');tempfile.tempdir=str(OUT/'tmp')
spec=importlib.util.spec_from_file_location('grader',ROOT/'evals/c-system-prompt/grader.py');grader=importlib.util.module_from_spec(spec);spec.loader.exec_module(grader)
spec=importlib.util.spec_from_file_location('official','/tmp/ost-official-evaluator-3U4yO9/repo/evaluate.py');official=importlib.util.module_from_spec(spec);spec.loader.exec_module(official)
pdf_mapping=json.loads((OUT/'preparation-provenance.json').read_text())['pdf_mapping']
rows=list(map(json.loads,(ROOT/'evals/c-system-prompt/cases.jsonl').read_text().splitlines()));byid={r['id']:r for r in rows};split=json.loads((ROOT/'evals/c-system-prompt/split.json').read_text());groups=split['groups'];summaries={};allpred=[]
for i in range(1,6):
 job=OUT/f'prompt-C-{version}-r{i}';allpred.append({p['id']:p for p in map(json.loads,(job/'70b-canonical.jsonl').read_text().splitlines())})
def local_case(case):
 if 'booklet' not in case:return case
 return {**case,'booklet':{**case['booklet'],'path':str(ROOT/pdf_mapping[case['booklet']['path']])}}
def jsonl(path,data):path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in data))
for part in ['train','test']:
 ids=split[part];chosen=set(ids);assert all(not(chosen&set(g)) or set(g)<=chosen for g in groups.values())
 jsonl(DEST/f'{part}-expected.jsonl',[{'id':id,**byid[id]['expect']} for id in ids]);jsonl(DEST/f'{part}-cases.jsonl',[local_case(byid[id]['input']) for id in ids]);scores=[]
 for repeat,preds in enumerate(allpred,1):
  jsonl(DEST/f'{part}-r{repeat}-predictions.jsonl',[preds[id] for id in ids]);r=grader.grade(Path('/tmp/ost-official-evaluator-3U4yO9/repo'),Path('/tmp/ost-official-evaluator-3U4yO9/env/bin/python'),DEST/f'{part}-r{repeat}-predictions.jsonl',DEST/f'{part}-expected.jsonl',DEST/f'{part}-cases.jsonl');scores.append(r)
  (DEST/f'{part}-r{repeat}.json').write_text(json.dumps(r,indent=2)+'\n')
 vals=[r['classification_objective']['value'] for r in scores];sd=statistics.stdev(vals);se=sd/math.sqrt(5)
 aggregate={'cases':len(ids),'source_groups':sum(set(g)<=chosen for g in groups.values()),'tasks':dict(Counter(id[-1] for id in ids)),'dates':dict(Counter(byid[id]['source_date'] for id in ids)),'gold_label_counts_per_task':{task:dict(Counter(byid[id]['expect']['label'] for id in ids if id[-1]==task)) for task in ['A','B']},'repeats':[{'repeat':i,'F1_A':r['official_report']['tasks']['A']['macro_f1'],'F1_B':r['official_report']['tasks']['B']['macro_f1'],'Q':r['classification_objective']['value'],'Hit_A':r['primary_evidence_objective']['value'],'safe_passes':r['safe_passes']} for i,r in enumerate(scores,1)],'Q_mean':statistics.mean(vals),'Q_run_sd':sd,'Q_run_spread':max(vals)-min(vals),'Q_temporal_detectable_difference':2*math.sqrt(2)*se,'Q_run_mean_t95':[statistics.mean(vals)-2.7764451052*se,statistics.mean(vals)+2.7764451052*se]}
 # Group bootstrap keeps A/B, identical source passages and all repeats together.
 relevant=[g for g in groups.values() if set(g)<=chosen];conf=np.zeros((len(relevant),2,3,3))
 for j,g in enumerate(relevant):
  for id in g:
   for preds in allpred:conf[j,['A','B'].index(id[-1]),byid[id]['expect']['label'],official.label_of(preds[id])[0]]+=.2
 def f1(c):
  tp=np.diagonal(c,axis1=-2,axis2=-1);den=c.sum(axis=-1)+c.sum(axis=-2);active=den>0
  return np.divide(2*tp,den,out=np.zeros_like(tp),where=active).sum(axis=-1)/active.sum(axis=-1)
 sample=np.random.default_rng(split['seed']).integers(0,len(relevant),size=(20000,len(relevant)));fs=f1(conf[sample].sum(axis=1));q=(.3*fs[:,0]+.28*fs[:,1])/.58
 aggregate.update(Q_case_bootstrap_95=np.quantile(q,[.025,.975]).tolist(),Q_case_bootstrap_se=float(q.std(ddof=1)),Q_unpaired_case_detectable_difference=2*math.sqrt(2)*float(q.std(ddof=1)))
 summaries[part]=aggregate
train_paths={byid[id]['input']['booklet']['path'] for id in split['train'] if 'booklet' in byid[id]['input']};test_paths={byid[id]['input']['booklet']['path'] for id in split['test'] if 'booklet' in byid[id]['input']}
summaries['split_audit']={'source_row_AB_overlap':0,'identical_reference_overlap':0,'booklet_overlap_count':len(train_paths&test_paths),'booklets_on_both_sides':sorted(train_paths&test_paths),'previously_exposed':True,'seed':split['seed'],'groups_total':len(groups),'new_inference_calls':0}
(DEST/'aggregate.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summaries,ensure_ascii=False,indent=2))
