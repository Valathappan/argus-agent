from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class RetrievedChunk(BaseModel):
    text: str
    source_id: str
    metadata: Dict[str, Any]
    score: float

class ToolResult(BaseModel):
    status: Literal["ok", "empty", "error"]
    mock: bool = True
    items: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None

class Claim(BaseModel):
    claim_id: str
    text: str
    source_ids: List[str]
    source_authority: Literal["primary", "secondary", "unknown"]
    source_date: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["supported", "unverified", "contradicted"]

class RecommendedAction(BaseModel):
    action_id: str
    description: str
    priority: Literal["low", "medium", "high"]
    owner: Literal["procurement", "legal", "operations", "leadership"]
    rationale: str
    source_ids: List[str]
    requires_human_approval: bool = True