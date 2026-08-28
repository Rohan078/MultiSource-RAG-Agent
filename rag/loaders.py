from pathlib import Path

from rag.chunk import chunk_text

TEXT_SUFFIXES = {".txt", ".md"}
PDF_SUFFIXES = {".pdf"}
DOC_SUFFIXES = TEXT_SUFFIXES | PDF_SUFFIXES
TABLE_SUFFIXES = {".csv", ".xlsx", ".xls"}
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SUPPORTED = DOC_SUFFIXES | TABLE_SUFFIXES | SQLITE_SUFFIXES


def load_file(path: Path):
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
        return _chunks_from_text(path.name, text)
    if suffix in PDF_SUFFIXES:
        return _chunks_from_pdf(path)
    return []


def iter_files(folder: Path, suffixes):
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )


def iter_source_files(folder: Path):
    return iter_files(folder, DOC_SUFFIXES)


def iter_table_files(folder: Path):
    return iter_files(folder, TABLE_SUFFIXES)


def iter_sqlite_files(folder: Path):
    return iter_files(folder, SQLITE_SUFFIXES)


def _chunks_from_text(name, text):
    return [
        {
            "source": "doc",
            "title": name,
            "locator": name,
            "text": chunk,
        }
        for chunk in chunk_text(text)
    ]


def _chunks_from_pdf(path: Path):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    chunks = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        locator = f"{path.name} p.{index}"
        for chunk in chunk_text(page_text):
            chunks.append(
                {
                    "source": "doc",
                    "title": path.name,
                    "locator": locator,
                    "text": chunk,
                }
            )
    return chunks
