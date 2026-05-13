"""Data types for RAG system"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a document chunk"""
    chunk_id: str
    doc_id: str
    source_path: str
    title: str
    section: str
    text: str
    metadata: Dict[str, Any]
    char_start: int
    char_end: int
    chunk_index: int


class MarkdownEvidence(BaseModel):
    """Evidence from markdown document"""
    chunk_id: str
    text: str
    score: float
    section: Optional[str] = None
    metadata: Dict[str, Any] = {}


class GraphEvidence(BaseModel):
    """Evidence from knowledge graph"""
    entity_id: str
    entity_name: str
    fact_type: Literal["property", "relation", "path"]
    fact_text: str
    score: float
    cypher_query: Optional[str] = None
    metadata: Dict[str, Any] = {}


class RetrievalResult(BaseModel):
    """Result from retrieval process"""
    question: str
    mode: str
    markdown_evidence: List[MarkdownEvidence] = []
    graph_evidence: List[GraphEvidence] = []
    resolved_entities: List[str] = []
    intent: Optional[str] = None
    retrieval_time_ms: float = 0.0


class Answer(BaseModel):
    """Generated answer"""
    text: str
    citations: List[str] = []
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}


class RAGResponse(BaseModel):
    """Complete RAG response"""
    question: str
    answer: str
    mode: str
    evidence: Optional[RetrievalResult] = None
    citations: List[str] = []
    confidence: Optional[float] = None
    synthesis_time_ms: float = 0.0
    total_time_ms: float = 0.0
    token_usage: Optional[int] = None
    metadata: Dict[str, Any] = {}
