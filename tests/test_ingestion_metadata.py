from rag.chunking import chunk_pages
from rag.loader import load_markdown
from rag.models import Chunk
from rag import faiss_store


def test_markdown_front_matter_metadata_survives_chunking(tmp_path):
    document = tmp_path / "supplier_contract.md"
    document.write_text(
        """---
document_id: SUP-CTR-001
document_type: supplier_contract
supplier: Northstar Semiconductor Ltd.
products: [Orion Edge Gateway, Atlas Vision Controller]
region: Taiwan; Singapore
effective_date: 2025-04-01
version: v2
---
# Supplier Agreement
Supplies the power-management modules.
""",
        encoding="utf-8",
    )

    pages = load_markdown(document)
    chunks = chunk_pages(pages, chunk_size=50, overlap=0)

    assert chunks[0].metadata == {
        "document_id": "SUP-CTR-001",
        "document_type": "supplier_contract",
        "supplier": "Northstar Semiconductor Ltd.",
        "products": ["Orion Edge Gateway", "Atlas Vision Controller"],
        "region": "Taiwan; Singapore",
        "effective_date": "2025-04-01",
        "version": "v2",
        "doc_type": "supplier_contract",
        "product": ["Orion Edge Gateway", "Atlas Vision Controller"],
        "doc_date": "2025-04-01",
    }


def test_faiss_index_persists_document_metadata(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import numpy as np

    class EmbeddingModel:
        def get_sentence_embedding_dimension(self):
            return 3

        def encode(self, texts, **kwargs):
            return np.array([[1.0, 0.0, 0.0] for _ in texts], dtype=np.float32)

    monkeypatch.setattr(
        faiss_store,
        "settings",
        SimpleNamespace(faiss_dir=tmp_path, faiss_index_name="test_docs"),
    )
    monkeypatch.setattr(faiss_store, "_get_embedding_model", lambda: EmbeddingModel())
    monkeypatch.setattr(faiss_store, "_index", None)
    monkeypatch.setattr(faiss_store, "_indexed_chunks", None)

    count = faiss_store.store_chunks(
        [
            Chunk(
                id="supplier-contract-p1-c0",
                text="Supplier contract evidence",
                source="supplier_contract.pdf",
                page=1,
                metadata={
                    "doc_type": "contract",
                    "supplier": "Supplier A",
                    "product": ["Widget"],
                    "region": "APAC",
                    "doc_date": "2026-01-15",
                    "version": "v2",
                },
            )
        ]
    )
    monkeypatch.setattr(faiss_store, "_index", None)
    monkeypatch.setattr(faiss_store, "_indexed_chunks", None)

    index, chunks = faiss_store.load_index()

    assert count == index.ntotal == 1
    assert chunks[0]["metadata"]["supplier"] == "Supplier A"
    assert chunks[0]["metadata"]["product"] == ["Widget"]
