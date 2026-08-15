from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    title: str
    doc_type: str
    standard_code: Optional[str] = None
    page_count: int
    status: str
    error: Optional[str] = None
    insights: Optional[dict[str, Any]] = None


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    section: Optional[str] = None
    bbox: BBox
    snippet: str
    element_type: str = "text"


class ChatRequest(BaseModel):
    question: str
    document_ids: list[str] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[Citation]
    confidence: float
    grounded: bool
    query_type: str
    unsupported_claims: list[str] = Field(default_factory=list)
    retrieved_count: int = 0
    expanded_query: Optional[str] = None
    conversions: list[str] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    follow_up: bool = False


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    citations: Optional[list[Any]] = None
    confidence: Optional[float] = None
    grounded: Optional[bool] = None
    query_type: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    messages: list[MessageOut]


QueryType = Literal["spec_lookup", "comparison", "explanation", "unit_conversion", "follow_up"]


class CompareRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class CompareResponse(BaseModel):
    specs: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    documents: list[DocumentOut]


class EvalCaseResult(BaseModel):
    question: str
    expected: str
    answer: str
    grounded: bool
    faithfulness: float
    answer_relevance: float
    context_precision: float
    passed: bool


class EvalRunOut(BaseModel):
    id: str
    scores: dict[str, Any]
    cases: list[dict[str, Any]]
    created_at: str
