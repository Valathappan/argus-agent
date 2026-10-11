from agents.supervisor import analyze_query


def test_analyze_query_returns_objective_entities_and_evidence_needs():
    result = analyze_query({
        "user_query": "Will Acme Semiconductor be affected by the new export restriction?",
        "entities": [],
    })

    assert result["investigation_objective"] == "Will Acme Semiconductor be affected by the new export restriction?"
    assert "Acme Semiconductor" in result["entities"]
    assert any("official" in need for need in result["evidence_needed"])
    assert any("internal" in need for need in result["evidence_needed"])
    assert any("provenance" in need for need in result["evidence_needed"])


def test_analyze_query_preserves_entities_already_in_state():
    result = analyze_query({"user_query": "Investigate new restrictions.", "entities": ["Known Supplier"]})

    assert "Known Supplier" in result["entities"]