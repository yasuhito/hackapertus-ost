"""Pure prospective controller gates; no outputs, gold, or inference."""
import copy
from pathlib import Path
import sys

import pytest
sys.path.insert(0,str(Path(__file__).parent))
import fragment_review_research as r


def repeats(f1a=.65,f1b=.80):
    return [dict(complete=True,canonical_count=60,source_valid=True,model_valid=True,
                 usage_known=True,ledger_valid=True,f1a=f1a,f1b=f1b,hita=.8,fallbacks=1,
                 review_available=60) for _ in range(5)]


def test_backpressure_rejects_small_positive_gain(tmp_path,monkeypatch):
    baseline = {'repeats': repeats()}
    candidate = {'repeats': repeats(.66,.80)}
    candidate['comparison'] = r.candidate_gates(baseline['repeats'],candidate['repeats'])
    assert candidate['comparison']['gain'] > 0 and not candidate['comparison']['research_keep']
    control_path = tmp_path/'control.json';control_path.write_bytes(b'{}')
    monkeypatch.setattr(r,'CONTROL',control_path)
    context = {'mode':'fragment_review','arm':'candidate','candidate':r.VARIANT,
               'protocol_sha256':r.sha(control_path.read_bytes())}
    monkeypatch.setattr(r,'load',lambda _:context)
    monkeypatch.setattr(r,'verify_freeze',lambda:{})
    monkeypatch.setattr(r,'checked_analysis',lambda control,arm:candidate if arm=='candidate' else baseline)
    monkeypatch.setattr(r,'checked_reference',lambda control:baseline)
    monkeypatch.setattr(r,'print_metrics',lambda _:None)
    with pytest.raises(ValueError,match='CANDIDATE_QUALITY_GATES_FAILED'):
        r.check_context()


def test_fresh_baseline_integrity_has_no_candidate_f1_or_gain_gates():
    assert r.baseline_integrity(repeats(.1,.2))
    with pytest.raises(ValueError,match='INCOMPLETE_ARM'):
        r.baseline_integrity(repeats()[:4])
    bad=repeats();bad[-1]['complete']=False
    with pytest.raises(ValueError,match='INCOMPLETE_ARM'):
        r.baseline_integrity(bad)


def test_q_noise_and_all_guards_unrounded():
    baseline=repeats();candidate=repeats(.68,.83)
    result=r.candidate_gates(baseline,candidate)
    assert result['research_keep'] and not result['deployment_approved']
    assert result['gain']==pytest.approx(.03) and result['baseline_noise']==0
    assert r.quality(1,0)==pytest.approx(.30/.58)
    candidate[0]['review_available']=45
    assert r.candidate_gates(baseline,candidate)['research_keep']
    candidate[0]['review_available']=44
    assert not r.candidate_gates(baseline,candidate)['research_keep']
    candidate=repeats(.68,.83);candidate[-1]['fallbacks']=2
    assert not r.candidate_gates(baseline,candidate)['gates']['fallbacks_not_more']
    candidate=repeats(.68,.83);candidate[-1]['hita']=.79
    assert not r.candidate_gates(baseline,candidate)['gates']['mean_hita_not_lower']
    baseline=repeats(); baseline[0]['f1a']=.2
    assert not r.candidate_gates(baseline,repeats(.68,.83))['gates']['gain_above_baseline_noise']


@pytest.mark.parametrize('field,value', [('f1a',.59),('f1b',.74)])
def test_each_candidate_repeat_floor(field,value):
    candidate=repeats(.9,.9);candidate[0][field]=value
    result=r.candidate_gates(repeats(.2,.2),candidate)
    assert not result['research_keep']


def test_prospective_bindings_refuse_missing_data_and_any_missing_job():
    with pytest.raises(ValueError,match='DATA_ADAPTER_NOT_READY'):
        r.prospective_bindings({}, {})
    bundle={'blinded_selection_frozen':True,'provenance_scope':r.SCOPE,'universal_unseen_claim':False,'provenance_evidence_sha256':{'fictional':'c'*64},
            **{k:'a'*64 for k in ('selection_sha256','provenance_sha256','input_sha256','expected_sha256','case_order_sha256')}}
    with pytest.raises(ValueError,match='ALL_FIVE_JOBS'):
        r.prospective_bindings(bundle,{})
    jobs={name:{'variant':r.VARIANT if '-candidate-' in name else r.BASELINE,
                'canonical_cases':60,'gold_free':True,'all_packets_within_bounds':True,
                'caps':copy.deepcopy(r.CAPS),'input_sha256':bundle['input_sha256'],
                **{k+'_sha256':'b'*64 for k in ('source','runtime','helpers','tests','wire','prompt','schema','native_packets','protocol')}}
          for name in r.JOBS}
    frozen=r.prospective_bindings(bundle,jobs)
    assert len(frozen['jobs'])==5 and len(frozen['freeze_sha256'])==64
    assert r.CAPS['physical_posts']==300 and r.CAPS['case_seconds']==300
    jobs[r.JOBS[-1]]['caps']['physical_posts']=301
    with pytest.raises(ValueError,match='FROZEN_BOUNDS'):
        r.prospective_bindings(bundle,jobs)


def test_canonical_metric_output_separates_measured_and_unknown(capsys):
    repeat={**repeats()[0], 'parent_tool_report_cases':60,'canonical_successful_calls':240,
            'review_states':{'fact_pair_selected':40,'no_fact_pair_selected':20,'review_unavailable':0},
            'fragment_selection_rejections':0,
            'full_usage_known':False,'physical_requests':241,'unknown_failed_count':1,
            'reserved_unknown_charge':262400,'charged_tokens':286400,
            'known_successful_tokens':24000,'known_successful_input_tokens':19200,
            'known_successful_output_tokens':4800,'physical_network_seconds':10,'physical_backoff_seconds':2,
            'full_total_tokens':None,'physical_calls_by_role':{'parent':120,'child':60,'reviewer':61},
            'role_usage':{role:{'calls':60,'input_tokens':4800,'output_tokens':1200,'api_wait_ms':1000}
                          for role in ('parent','child','reviewer')}}
    r.print_metrics({'repeats':[repeat]*5,'mean_Q':r.quality(.65,.8),'elapsed_seconds':20})
    output=capsys.readouterr().out
    assert f'METRIC mean_Q={r.quality(.65,.8)}\n' in output
    assert 'METRIC canonical_successful_calls=1200\n' in output
    assert 'METRIC total_physical_requests=1205\n' in output
    assert 'METRIC full_total_tokens=unavailable\n' in output
    assert 'METRIC review_fact_pair_selected=200\n' in output
    assert 'METRIC review_no_fact_pair_selected=100\n' in output
    assert 'METRIC review_unavailable=0\n' in output
    assert 'METRIC fragment_selection_rejections=0\n' in output


@pytest.mark.parametrize('evidence',[True,{}, {'file':'not-a-hash'}])
def test_scoped_evidence_must_be_hashed_not_boolean(evidence):
    bundle={'blinded_selection_frozen':True,'provenance_scope':r.SCOPE,
            'universal_unseen_claim':False,'provenance_evidence_sha256':evidence}
    with pytest.raises(ValueError,match='DATA_ADAPTER_NOT_READY'):r.prospective_bindings(bundle,{})
