from pathlib import Path

from pypdf import PdfReader

from rag.models import Page


def load_pdf(path: Path) -> list[Page]:
    reader = PdfReader(path)
    pages = []
    for number, pdf_page in enumerate(reader.pages, start=1):
        text = " ".join((pdf_page.extract_text() or "").split())
        if text:
            pages.append(Page(text=text, source=path.name, page=number))
    return pages


def load_pdfs(folder: Path) -> list[Page]:
    pages = []
    for path in sorted(folder.glob("*.pdf")):
        pages.extend(load_pdf(path))
    return pages
