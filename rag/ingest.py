from rag.embeddings import EMBED_MODEL, embed_texts
from rag.loaders import (
    iter_source_files,
    iter_sqlite_files,
    iter_table_files,
    load_file,
)
from rag.paths import DATA_DIR
from rag.store import save_index
from rag.tables import import_csv, import_excel, import_sqlite, list_table_cards, reset_db


def ingest_folder(folder=None):
    folder = folder or DATA_DIR
    doc_files = iter_source_files(folder)
    table_files = iter_table_files(folder)
    sqlite_files = iter_sqlite_files(folder)
    if not doc_files and not table_files and not sqlite_files:
        raise FileNotFoundError(
            f"No documents or tables found in {folder}. "
            "Add .txt, .md, .pdf, .csv, .xlsx, or .db files."
        )

    chunks = []
    for path in doc_files:
        chunks.extend(load_file(path))

    conn = reset_db()
    imported_tables = []
    try:
        for path in table_files:
            suffix = path.suffix.lower()
            if suffix == ".csv":
                imported_tables.append(import_csv(conn, path))
            else:
                imported_tables.extend(import_excel(conn, path))
        for path in sqlite_files:
            imported_tables.extend(import_sqlite(conn, path))
        chunks.extend(list_table_cards(conn))
    finally:
        conn.close()

    if not chunks:
        raise ValueError(f"No readable text or tables found in {folder}.")

    vectors = embed_texts(
        [chunk["text"] for chunk in chunks],
        task_type="RETRIEVAL_DOCUMENT",
    )
    stored = []
    for chunk, vector in zip(chunks, vectors):
        stored.append({**chunk, "embedding": vector})

    files = [path.name for path in doc_files + table_files + sqlite_files]
    index = {
        "embed_model": EMBED_MODEL,
        "files": files,
        "tables": imported_tables,
        "chunks": stored,
    }
    save_index(index)
    return index


def main():
    index = ingest_folder()
    print(
        f"Indexed {len(index['chunks'])} chunks from "
        f"{len(index['files'])} file(s)."
    )
    if index.get("tables"):
        print("Tables:", ", ".join(index["tables"]))


if __name__ == "__main__":
    main()
