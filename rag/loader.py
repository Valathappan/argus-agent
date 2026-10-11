from datetime import date, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader
import yaml

from rag.models import Page


def _normalize_metadata(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_metadata(item) for item in value]
    return value


def _read_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}

    front_matter, separator, _ = text[3:].partition("\n---")
    if not separator:
        return {}

    raw_metadata = yaml.safe_load(front_matter)
    if not isinstance(raw_metadata, dict):
        raise ValueError(f"Expected YAML metadata mapping at the start of {path}.")

    metadata = _normalize_metadata(raw_metadata)
    if "document_type" in metadata:
        metadata.setdefault("doc_type", metadata["document_type"])
    if "products" in metadata:
        metadata.setdefault("product", metadata["products"])
    if "effective_date" in metadata:
        metadata.setdefault("doc_date", metadata["effective_date"])
    metadata.setdefault("document_id", path.stem)
    return metadata


def load_pdf(path: Path) -> list[Page]:
    reader = PdfReader(path)
    pages = []
    for number, pdf_page in enumerate(reader.pages, start=1):
        text = " ".join((pdf_page.extract_text() or "").split())
        if text:
            pages.append(Page(text=text, source=path.name, page=number))
    return pages


def load_markdown(path: Path) -> list[Page]:
    text = path.read_text(encoding="utf-8")
    metadata = _read_front_matter(path)
    body = text
    if text.startswith("---"):
        _, separator, remainder = text[3:].partition("\n---")
        if separator:
            body = remainder.split("\n", 1)[1] if "\n" in remainder else ""
    normalized_text = " ".join(body.split())
    if not normalized_text:
        return []
    return [Page(text=normalized_text, source=path.name, page=1, metadata=metadata)]


def load_pdfs(folder: Path) -> list[Page]:
    pages = []
    for path in sorted(folder.glob("*.pdf")):
        pages.extend(load_pdf(path))
    return pages


def load_documents(folder: Path) -> list[Page]:
    """Load PDFs and Markdown files, retaining Markdown front-matter metadata."""
    pages = []
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() == ".pdf":
            pages.extend(load_pdf(path))
        elif path.suffix.lower() in {".md", ".markdown"}:
            pages.extend(load_markdown(path))
    return pages
