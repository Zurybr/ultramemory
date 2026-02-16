"""FastAPI service for Ultramemory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.memory import MemorySystem
from agents.librarian import LibrarianAgent
from agents.researcher import ResearcherAgent
from agents.consolidator import ConsolidatorAgent
from .models import (
    AddRequest,
    AddResponse,
    QueryRequest,
    QueryResponse,
    ConsolidateResponse,
    HealthResponse,
)


memory: MemorySystem | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager."""
    global memory
    memory = MemorySystem()
    yield
    await memory.close()


app = FastAPI(
    title="Ultramemory API",
    description="Hybrid memory system API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    services = {
        "qdrant": await memory.qdrant.health(),
        "redis": await memory.redis.health(),
        "graphiti": await memory.graphiti.health(),
    }

    return HealthResponse(
        status="healthy" if all(services.values()) else "degraded",
        services=services,
    )


@app.post("/memory/add", response_model=AddResponse)
async def add_content(request: AddRequest):
    """Add content to memory."""
    librarian = LibrarianAgent(memory)

    try:
        result = await librarian.add(request.content, request.metadata)
        return AddResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/query", response_model=QueryResponse)
async def query_memory(request: QueryRequest):
    """Query memory."""
    researcher = ResearcherAgent(memory)

    try:
        result = await researcher.query(request.query, request.limit)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/consolidate", response_model=ConsolidateResponse)
async def consolidate_memory():
    """Run consolidation."""
    consolidator = ConsolidatorAgent(memory)

    try:
        result = await consolidator.consolidate()
        return ConsolidateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/list")
async def list_agents():
    """List available agents."""
    return {
        "system": ["librarian", "researcher", "consolidator", "auto-researcher"],
        "custom": [],  # Load from settings
    }
