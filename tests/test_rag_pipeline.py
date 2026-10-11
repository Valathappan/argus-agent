"""Offline integration check for PDF loading and RAG chunk metadata.

Run from the repository root with:
    python -m pytest tests/test_rag_pipeline.py -v -s
"""

from collections import Counter

from config.settings import settings
from rag.chunking import chunk_pages
from rag.loader import load_pdfs


def test_pdf_corpus_loads_and_chunks_with_source_metadata():
    print(f"\n[RAG] Configured PDF folder: {settings.pdf_dir}")
    pdf_files = sorted(settings.pdf_dir.glob("*.pdf"))
    print(f"[RAG] PDF files found: {len(pdf_files)}")
    for path in pdf_files:
        print(f"  - {path.name} ({path.stat().st_size:,} bytes)")
    assert pdf_files, f"No PDF fixtures found in configured RAG folder: {settings.pdf_dir}"

    pages = load_pdfs(settings.pdf_dir)
    print(f"[RAG] Pages with extracted text: {len(pages)}")
    for source, count in sorted(Counter(page.source for page in pages).items()):
        print(f"  - {source}: {count} page(s)")
    assert pages, "The configured PDFs were found, but no page text could be extracted."

    chunks = chunk_pages(pages, chunk_size=80, overlap=10)
    print(f"[RAG] Chunks created: {len(chunks)} (80 words, 10-word overlap)")
    for source, count in sorted(Counter(chunk.source for chunk in chunks).items()):
        print(f"  - {source}: {count} chunk(s)")
    assert chunks, "Extracted PDF pages did not produce any RAG chunks."
    assert {chunk.source for chunk in chunks} == {path.name for path in pdf_files}

    print("[RAG] First chunk preview:")
    print(f"  ID: {chunks[0].id}")
    print(f"  Source: {chunks[0].source}, page {chunks[0].page}")
    print(f"  Text: {chunks[0].text[:250]}")

    for chunk in chunks:
        assert chunk.text.strip()
        assert chunk.source.endswith(".pdf")
        assert chunk.page >= 1
        assert chunk.id.startswith(f"{chunk.source}-p{chunk.page}-c")
    print("[RAG] Metadata checks passed: every chunk has text, source, page, and ID.")
