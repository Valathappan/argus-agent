"""Ingestion pipeline: PDFs -> pages -> chunks -> embeddings -> FAISS."""

from collections import Counter

from rich.console import Console
from rich.panel import Panel

from config.settings import settings
from rag.chunking import chunk_pages
from rag.ingestion import store_chunks
from rag.loader import load_documents

console = Console()


def main():
    console.rule("Step 1: Load PDFs")
    pages = load_documents(settings.pdf_dir)
    pages.extend(load_documents(settings.knowledge_base_dir))
    if not pages:
        console.print(f"[red]No PDF text found in {settings.pdf_dir}. Add your PDFs there and run again.[/red]")
        return
    for source, count in Counter(page.source for page in pages).items():
        console.print(f"  {source}: {count} pages")

    console.rule("Step 2: Split pages into chunks")
    chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
    console.print(
        f"  {len(pages)} pages -> {len(chunks)} chunks "
        f"(chunk size {settings.chunk_size} words, overlap {settings.chunk_overlap} words)"
    )
    for chunk in chunks[:2]:
        console.print(Panel(chunk.text, title=f"Sample chunk: {chunk.id}", border_style="cyan"))

    console.rule("Step 3: Embed chunks and store them in FAISS")
    stored = store_chunks(chunks)
    console.print(f"  [green]Stored {stored} chunks in FAISS index '{settings.faiss_index_name}'[/green]")
    console.print(f"  Index folder: {settings.faiss_dir}")


if __name__ == "__main__":
    main()
