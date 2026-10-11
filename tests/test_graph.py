"""Tests for the compiled external-research graph.

Run from the repository root with:
    python -m pytest tests/test_graph.py -v
"""

from graph import graph as graph_module


def test_graph_passes_question_to_sources_and_builds_cited_report(monkeypatch):
    calls = {"news": [], "regulation": []}

    def fake_search_news(query):
        calls["news"].append(query)
        return {
            "status": "success",
            "items": [
                {
                    "title": "Supplier semiconductor update",
                    "date": "2026-10-01",
                    "source": "Example News",
                    "url": "https://example.test/news/1",
                    "snippet": "A sample supplier update.",
                    "mock": True,
                }
            ],
            "error": None,
        }

    def fake_search_regulation(query):
        calls["regulation"].append(query)
        return {
            "status": "success",
            "items": [
                {
                    "title": "Export control notice",
                    "date": "2026-10-02",
                    "source": "Example Regulator",
                    "url": "https://example.test/notices/2",
                    "snippet": "A sample regulatory notice.",
                    "mock": False,
                }
            ],
            "error": None,
        }

    monkeypatch.setattr(graph_module, "search_news", fake_search_news)
    monkeypatch.setattr(graph_module, "search_regulation", fake_search_regulation)

    result = graph_module.graph.invoke({"question": "Do restrictions affect suppliers?"})

    assert calls == {
        "news": ["Do restrictions affect suppliers?"],
        "regulation": ["Do restrictions affect suppliers?"],
    }
    assert len(result["news_articles"]) == 1
    assert len(result["government_evidence"]) == 1
    assert result["final_report"] == result["report"]
    assert "[MOCK] 2026-10-01 — Supplier semiconductor update" in result["final_report"]
    assert "Source: Example News" in result["final_report"]
    assert "https://example.test/news/1" in result["final_report"]
    assert "[LIVE] 2026-10-02 — Export control notice" in result["final_report"]
    assert "https://example.test/notices/2" in result["final_report"]
