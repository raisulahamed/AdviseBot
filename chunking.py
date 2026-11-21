import re
from pypdf import PdfReader

SEC = re.compile(r"(?m)^(\d{1,2}\.\d{1,2})\s+(\S.*)$")
FOOT = re.compile(r"(?m)^CSE Department - Undergraduate Academic Regulations.*$|^Page \d+\s*$")


def load_chunks(pdf_path, doc_name="CSE Regulations"):
    chunks = []
    for page_no, page in enumerate(PdfReader(pdf_path).pages, start=1):
        text = FOOT.sub("", page.extract_text() or "")
        text = re.sub(r"[ \t]+", " ", text).strip()
        if not text or page_no == 1:
            continue
        ch = re.search(r"(?m)^Chapter (\d+)\.\s*(.*)$", text)
        chapter = f"Chapter {ch.group(1)}" if ch else ""
        parts = list(SEC.finditer(text))
        if not parts:
            chunks.append({"doc": doc_name, "section": chapter or f"page {page_no}", "title": ch.group(2) if ch else "", "page": page_no, "text": text})
            continue
        for i, m in enumerate(parts):
            end = parts[i + 1].start() if i + 1 < len(parts) else len(text)
            body = text[m.start():end].strip()
            chunks.append({"doc": doc_name, "section": m.group(1), "title": m.group(2).strip(), "page": page_no, "text": body})
    return chunks
