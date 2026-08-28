import json

from rag.paths import INDEX_PATH, STORE_DIR


def load_index():
    if not INDEX_PATH.exists():
        return None
    with INDEX_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_index(index):
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open("w", encoding="utf-8") as handle:
        json.dump(index, handle)


def cosine_similarity(left, right):
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
