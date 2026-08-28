def chunk_text(text, max_chars=900, overlap=150):
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    packed = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            packed.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            packed.extend(_split_long(paragraph, max_chars, overlap))
            current = ""
    if current:
        packed.append(current)
    return packed


def _split_long(text, max_chars, overlap):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]
