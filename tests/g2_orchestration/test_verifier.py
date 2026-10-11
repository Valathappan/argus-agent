from agents.verifier import verify_claims


def test_verifier_flags_seeded_effective_date_conflict_without_resolving_it():
    result = verify_claims({
        "news_articles": [
            {
                "source": "major_news",
                "source_id": "news-1",
                "claim_type": "effective_date",
                "value": "2025-09-01",
                "text": "The restriction takes effect on 2025-09-01.",
                "primary_source": False,
            },
            {
                "source": "industry_pub",
                "source_id": "industry-2",
                "claim_type": "effective_date",
                "value": "immediate",
                "text": "The restriction takes effect immediately.",
                "primary_source": False,
            },
        ],
    })

    assert len(result["conflicting_claims"]) == 1
    conflict = result["conflicting_claims"][0]
    assert conflict["conflict_type"] == "effective_date"
    assert set(conflict["source_ids"]) == {"news-1", "industry-2"}
    assert conflict["resolution"] is None
    assert {claim["status"] for claim in result["claims"]} == {"contradicted"}
    assert all(claim["source_ids"] for claim in result["claims"])


def test_duplicate_articles_do_not_inflate_confidence_or_claim_count():
    article = {
        "claim_type": "scope",
        "value": "categories X, Y, Z only",
        "text": "The rule covers categories X, Y, and Z only.",
        "source_type": "news",
    }
    result = verify_claims({
        "news_articles": [
            {**article, "source_id": "article-1"},
            {**article, "source_id": "article-copy"},
        ],
    })

    assert len(result["claims"]) == 1
    assert set(result["claims"][0]["source_ids"]) == {"article-1", "article-copy"}
    assert result["claims"][0]["confidence"] == 0.55
    assert result["claims"][0]["status"] == "unverified"


def test_government_evidence_is_marked_primary():
    result = verify_claims({
        "government_evidence": {
            "status": "ok",
            "items": [{
                "source_id": "gov-notice-1",
                "claim_type": "scope",
                "value": "categories X and Y",
                "text": "The notice applies to categories X and Y.",
            }],
        },
    })

    assert result["claims"][0]["source_authority"] == "primary"
    assert result["claims"][0]["status"] == "supported"