from typing import TypedDict, List, Dict, Any, Optional

class IntelligenceState(TypedDict):
    user_query: str
    entities: List[str]
    news_articles: List[Dict[str, Any]]
    government_evidence: List[Dict[str, Any]]
    market_evidence: List[Dict[str, Any]]
    internal_documents: List[Dict[str, Any]]
    claims: List[Dict[str, Any]]
    conflicting_claims: List[Dict[str, Any]]
    impacted_suppliers: List[str]
    impacted_products: List[str]
    missing_information: List[str]
    investigation_iterations: int
    evidence_gate_result: str  # "pass", "needs_research", "stop_with_uncertainty"
    risk_score: Optional[float]
    confidence_score: Optional[float]
    evidence_quality_score: Optional[float]
    recommended_actions: List[Dict[str, Any]]
    evaluation_result: Dict[str, Any]
    final_report: str
    errors: List[str]