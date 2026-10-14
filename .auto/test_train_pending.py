"""Failed TRAIN measurements must not reuse an earlier passing check selector."""
import json
from pathlib import Path
import shutil
import subprocess


def test_pending_train_selector_is_rejected(tmp_path):
    auto = tmp_path / '.auto'
    auto.mkdir()
    source = Path(__file__).resolve().parent / 'checks.sh'
    shutil.copyfile(source, auto / 'checks.sh')
    (auto / 'check-context.json').write_text(json.dumps({
        'mode': 'train_pending', 'candidate': 'v14'
    }))
    result = subprocess.run(['bash', str(auto / 'checks.sh')], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'CHECK_SELECTOR_MISSING' in result.stderr
