"""Optional cached local-only paragraph embeddings. Never fetch model weights."""
from functools import lru_cache
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_embedder():
    if os.getenv('OST_EMBEDDER') == 'none':
        return None
    configured = os.getenv('OST_EMBED_MODEL_DIR')
    paths = [Path(configured)] if configured else [
        Path('/app/models/potion-multilingual-128M-int8'),
        REPO_ROOT / 'models/potion-multilingual-128M-int8']
    path = next((p for p in paths if p.is_dir()), None)
    if path is None:
        return None
    try:
        from model2vec import StaticModel
    except ImportError:
        return None
    model = StaticModel.from_pretrained(str(path.resolve()))

    def encode(texts):
        return [[float(value) for value in vector] for vector in model.encode(texts)]
    return encode
