"""Isolated, source-pinned reconstruction of a historical inference contract."""
import importlib.util
import json
from pathlib import Path
import sys

request = json.load(sys.stdin)
root = Path(request['root'])
sys.path.insert(0, str(root))
path = root / ('engine_snapshot.py' if (root / 'engine_snapshot.py').exists() else 'predict.py')
spec = importlib.util.spec_from_file_location('frozen_replay_engine', path)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
case = request['case']
pages, messages = engine.context(case, Path(request['base']))
payload = json.loads(messages[1]['content'])
protocol = 'span_ids' if 'source_spans' in payload else 'legacy_quotes'
if protocol == 'legacy_quotes':
    payload['reference'] = request['reference']
    messages = [messages[0], {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}]

class SavedBackend:
    def complete(self, *args):
        return request['raw'], request['metrics_usage']

result = engine.predict(case, SavedBackend(), Path(request['base']))
print(json.dumps({'messages': messages, 'protocol': protocol, 'prediction': result}, ensure_ascii=False))
