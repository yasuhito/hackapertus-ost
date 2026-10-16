import json
from pathlib import Path
import sys
import subprocess
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import predict as engine
from source_spans import candidates


def test_system_matches_submit_contract_without_duplicate_text_output():
    case = {"id": "synthetic", "claim": {"text": "Claim"},
            "reference": {"text": "Source."}}
    _, messages = engine.context(case, Path("."))
    system = messages[0]["content"]
    assert "Use the declared submit tool for the final answer." in system
    assert "candidate_ids (an array of provided span IDs)" in system
    assert "Return ONLY JSON:" not in system
    assert engine.NEUTRAL_GUARD in system
    assert engine.PARAPHRASE_GUARD in system
    assert engine.FINAL_VERIFICATION not in system
    assert json.loads(messages[1]["content"])["final_verification"] == engine.FINAL_VERIFICATION


def test_id_pipeline_restores_original_and_usage():
    case = {"id": "synthetic", "claim": {"text": "La proposition est refusée.", "language": "fr"},
            "reference": {"text": "La proposition est refusée.\n", "language": "fr"}}
    class Backend:
        def complete(self, messages, pages, claim):
            payload = json.loads(messages[1]["content"])
            assert "reference" not in payload
            assert "reference_string" not in payload and "gold" not in payload
            assert payload["source_spans"][0]["text"] == case["reference"]["text"]
            return json.dumps({"label": 0, "evidence": [{"span_id": payload["source_spans"][0]["span_id"]}]}), {"prompt_tokens": 12, "completion_tokens": 3}
    result = engine.predict(case, Backend())
    assert "error" not in result
    assert result["label"] == 0
    assert result["evidence"] == [{"page": None, "text": case["reference"]["text"]}]
    assert result["metrics"]["input_tokens"] == 12


def test_selection_preserves_page_and_rejects_unprovided_id(monkeypatch):
    pages = ("A first page.", "The selected original page.")
    monkeypatch.setattr(engine, "pdf_pages", lambda _: pages)
    monkeypatch.setattr(engine, "selected_context", lambda *args: ("unused display", {"selected_pages": [2]}))
    case = {"id": "synthetic", "claim": {"text": "Claim", "language": "de"},
            "booklet": {"path": "synthetic.pdf", "language": "de"}, "vote": "Synthetic vote"}
    masked, messages = engine.context(case, Path("."))
    supplied = json.loads(messages[1]["content"])["source_spans"]
    assert masked == ("", pages[1]) and {s["page"] for s in supplied} == {2}
    class Backend:
        def complete(self, *args):
            return json.dumps({"label": 0, "evidence": [{"span_id": candidates(pages)[0]["span_id"]}]}), {"prompt_tokens": 1, "completion_tokens": 1}
    result = engine.predict(case, Backend())
    assert "error" in result
    assert result["evidence"] == []


def test_missing_support_fails_the_pipeline():
    case = {"id": "synthetic", "claim": {"text": "Claim"}, "reference": {"text": "Source."}}
    class Backend:
        def complete(self, *args):
            return '{"label":0,"evidence":[]}', {"prompt_tokens": 1, "completion_tokens": 1}
    result = engine.predict(case, Backend())
    assert result.get("error") == "supporting span required"
    assert result["evidence"] == []


def test_real_mock_cli_non_neutral_end_to_end(tmp_path):
    source=tmp_path/'cases.jsonl';target=tmp_path/'result.jsonl'
    source.write_text(json.dumps({'id':'mock-positive','claim':{'text':'Ja'},'reference':{'text':'Ja'}})+'\n')
    subprocess.run([sys.executable,str(Path(engine.__file__)),'--backend','mock','--input',str(source),'--output',str(target)],check=True)
    result=json.loads(target.read_text())
    assert result['label']==0 and 'error' not in result and result['evidence']==[{'page':None,'text':'Ja'}]


def test_canonical_validator_is_separate_and_strict():
    row={'id':'x','label':0,'label_name':'entailment','evidence':[{'page':1,'text':'Original.'}],
         'metrics':{'input_tokens':1,'output_tokens':1,'inference_time_ms':1}}
    assert engine.validate_prediction(row,('Original.',))==(0,row['evidence'])
    with pytest.raises(ValueError):engine.decode(json.dumps(row),('Original.',))
    for change in [{'evidence':[{'page':2,'text':'Original.'}]}, {'evidence':[{'page':1,'text':'invented'}]},
                   {'label_name':'neutral'}, {'metrics':{'input_tokens':True,'output_tokens':1,'inference_time_ms':1}}, {'evidence':[]}]:
        with pytest.raises(ValueError):engine.validate_prediction({**row,**change},('Original.',))
