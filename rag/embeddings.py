from fastembed import TextEmbedding

EMBED_MODEL = "BAAI/bge-small-en-v1.5"

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=EMBED_MODEL)
    return _model


def embed_texts(texts, task_type=None):
    if not texts:
        return []
    prepared = [_prefix(text, task_type) for text in texts]
    return [vector.tolist() for vector in _get_model().embed(prepared)]


def _prefix(text, task_type):
    if task_type == "RETRIEVAL_QUERY":
        return f"query: {text}"
    if task_type == "RETRIEVAL_DOCUMENT":
        return f"passage: {text}"
    return text
