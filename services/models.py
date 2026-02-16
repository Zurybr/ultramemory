"""Pydantic models for API."""

from typing import Any
from pydantic import BaseModel


class AddRequest(BaseModel):
    """Request to add content to memory."""

    content: str
    metadata: dict[str, Any] | None = None


class AddResponse(BaseModel):
    """Response from adding content."""

    status: str
    chunks_created: int
    document_id: str | None


class QueryRequest(BaseModel):
    """Request to query memory."""

    query: str
    limit: int = 5


class QueryResponse(BaseModel):
    """Response from querying memory."""

    query: str
    results: list[dict[str, Any]]
    total_found: int


class ConsolidateResponse(BaseModel):
    """Response from consolidation."""

    status: str
    duplicates_removed: int
    entities_merged: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    services: dict[str, bool]
