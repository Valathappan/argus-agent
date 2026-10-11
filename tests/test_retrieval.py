from rag import retrieval


def test_retrieve_returns_standard_chunk_shape(monkeypatch):
    def fake_query_index(query, top_k):
        assert query == "supplier contract"
        assert top_k == 1
        return [
            (
                {
                    "text": "Example contract text",
                    "metadata": {
                        "source": "contract_supplier_abc_v2.pdf",
                        "page": 3,
                        "doc_type": "contract",
                        "supplier": "Supplier ABC",
                        "product": "Example product",
                        "region": "APAC",
                        "doc_date": "2026-01-15",
                        "version": "v2",
                    },
                },
                0.83,
            )
        ]

    monkeypatch.setattr(retrieval, "query_index", fake_query_index)

    assert retrieval.retrieve("supplier contract", 1) == [
        {
            "text": "Example contract text",
            "source_id": "contract_supplier_abc_v2.pdf#p3",
            "metadata": {
                "doc_type": "contract",
                "supplier": "Supplier ABC",
                "product": "Example product",
                "region": "APAC",
                "doc_date": "2026-01-15",
                "version": "v2",
            },
            "score": 0.83,
        }
    ]
