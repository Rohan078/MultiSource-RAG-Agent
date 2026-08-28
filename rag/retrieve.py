from rag.embeddings import embed_texts
from rag.store import cosine_similarity, load_index


def search_docs(query, k=5, sources=None):
    index = load_index()
    if not index or not index.get("chunks"):
        return []

    allowed = set(sources) if sources else None
    query_vector = embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
    ranked = []
    for chunk in index["chunks"]:
        if allowed and chunk.get("source") not in allowed:
            continue
        score = cosine_similarity(query_vector, chunk["embedding"])
        ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)

    hits = []
    for score, chunk in ranked[:k]:
        hits.append(
            {
                "source": chunk.get("source", "doc"),
                "title": chunk["title"],
                "locator": chunk["locator"],
                "url": chunk["locator"],
                "text": chunk["text"],
                "table": chunk.get("table"),
                "score": round(score, 4),
            }
        )
    return hits


def search_tables(query, k=4):
    return search_docs(query, k=k, sources={"table"})
