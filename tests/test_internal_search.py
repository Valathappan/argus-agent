from rag import retrieval
from rag.reranker import rerank


def _chunk(
    source: str,
    supplier: str,
    product: str,
    score: float,
    *,
    doc_date: str = "2026-01-01",
    version: str = "v1",
) -> tuple[dict, float]:
    return (
        {
            "text": f"Evidence for {supplier}",
            "metadata": {
                "source": source,
                "page": 1,
                "doc_type": "contract",
                "supplier": supplier,
                "product": product,
                "region": "APAC",
                "doc_date": doc_date,
                "version": version,
                "status": "active",
            },
        },
        score,
    )


def test_search_internal_applies_metadata_and_date_filters(monkeypatch):
    monkeypatch.setattr(
        retrieval,
        "query_index",
        lambda query, top_k: [
            _chunk("new.pdf", "Supplier A", "Widget", 0.85, doc_date="2026-05-01", version="v2"),
            _chunk("old.pdf", "Supplier A", "Widget", 0.90, doc_date="2024-05-01", version="v1"),
            _chunk("other.pdf", "Supplier B", "Gadget", 0.95, doc_date="2026-05-01", version="v2"),
        ],
    )

    response = retrieval.search_internal(
        "supplier widget",
        2,
        {
            "supplier": "Supplier A",
            "product": "Widget",
            "region": "APAC",
            "document_type": "contract",
            "date": {"from": "2025-01-01", "to": "2026-12-31"},
        },
    )

    assert response["reason"] is None
    assert [item["source_id"] for item in response["results"]] == ["new.pdf#p1"]
    assert response["results"][0]["score"] == 0.85
    assert response["results"][0]["metadata"]["doc_type"] == "contract"


def test_search_internal_explains_weak_and_empty_searches(monkeypatch):
    monkeypatch.setattr(retrieval, "query_index", lambda query, top_k: [_chunk("weak.pdf", "A", "B", 0.1)])

    weak = retrieval.search_internal("weak match", 3)
    empty = retrieval.search_internal("   ", 3)

    assert weak["results"] == []
    assert "minimum similarity score" in weak["reason"]
    assert empty == {"results": [], "reason": "The search query is empty."}


def test_search_internal_does_not_fail_if_reranking_fails(monkeypatch, caplog):
    monkeypatch.setattr(retrieval, "query_index", lambda query, top_k: [_chunk("doc.pdf", "A", "B", 0.8)])

    def fail_reranking(chunks):
        raise RuntimeError("reranker unavailable")

    monkeypatch.setattr(retrieval, "rerank", fail_reranking)

    response = retrieval.search_internal("contract", 1)

    assert response["results"][0]["source_id"] == "doc.pdf#p1"
    assert response["reason"] is None
    assert "Reranking failed" in caplog.text


def test_search_internal_rejects_invalid_filters_before_search(monkeypatch):
    monkeypatch.setattr(
        retrieval,
        "query_index",
        lambda query, top_k: (_ for _ in ()).throw(AssertionError("must not query")),
    )

    try:
        retrieval.search_internal("contract", 1, {"unknown": "value"})
    except ValueError as error:
        assert "Unsupported retrieval filter" in str(error)
    else:
        raise AssertionError("Expected unsupported filter to raise ValueError")


def test_reranker_prefers_newer_higher_version_documents():
    older = {
        "text": "Older",
        "source_id": "old.pdf#p1",
        "metadata": {"doc_date": "2024-01-01", "version": "v1", "status": "active"},
        "score": 0.80,
    }
    newer = {
        "text": "Newer",
        "source_id": "new.pdf#p1",
        "metadata": {"doc_date": "2026-01-01", "version": "v2", "status": "active"},
        "score": 0.79,
    }

    assert rerank([older, newer]) == [newer, older]


def test_reranker_prefers_active_over_expired_when_relevance_is_close():
    expired = _chunk("old.pdf", "Supplier A", "Widget", 0.82)[0]
    active = _chunk("new.pdf", "Supplier A", "Widget", 0.80)[0]
    expired["metadata"]["status"] = "expired"
    active["metadata"]["status"] = "active"
    expired_result = {
        "text": expired["text"],
        "source_id": "old.pdf#p1",
        "metadata": {"doc_date": "2026-01-01", "version": "v2"},
        "score": 0.82,
    }
    active_result = {
        "text": active["text"],
        "source_id": "new.pdf#p1",
        "metadata": {"doc_date": "2026-01-01", "version": "v2"},
        "score": 0.80,
    }

    assert rerank(
        [expired_result, active_result],
        [expired["metadata"], active["metadata"]],
    ) == [active_result, expired_result]


def test_internal_analyst_records_impacts_and_sources(monkeypatch):
    from agents import internal_analyst

    document = {
        "text": "Supplier evidence",
        "source_id": "contract.pdf#p2",
        "metadata": {
            "doc_type": "contract",
            "supplier": "Supplier A",
            "product": ["Widget", "Gadget"],
            "region": "APAC",
            "doc_date": "2026-01-01",
            "version": "v2",
            "status": "active",
        },
        "score": 0.8,
    }
    monkeypatch.setattr(
        internal_analyst,
        "search_internal",
        lambda query, top_k: {"results": [document], "reason": None},
    )

    updates = internal_analyst.analyze_internal({"user_query": "Supplier A event"})

    assert updates["internal_documents"] == [document]
    assert updates["impacted_suppliers"] == [{"name": "Supplier A", "source_ids": ["contract.pdf#p2"]}]
    assert updates["impacted_products"] == [
        {"name": "Widget", "source_ids": ["contract.pdf#p2"]},
        {"name": "Gadget", "source_ids": ["contract.pdf#p2"]},
    ]
