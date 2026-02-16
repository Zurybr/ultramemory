"""Tests for memory system."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.memory import MemorySystem


@pytest.fixture
def memory_system():
    return MemorySystem()


@pytest.mark.asyncio
async def test_memory_add(memory_system):
    """Test adding content to memory."""
    memory_system._generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    memory_system.qdrant.add = AsyncMock(return_value="test-id")
    memory_system.graphiti.add_episode = AsyncMock(return_value="episode-id")
    memory_system.redis.set = AsyncMock()

    result = await memory_system.add("Test content")

    assert result == "test-id"
    memory_system.qdrant.add.assert_called_once()
    memory_system.graphiti.add_episode.assert_called_once()


@pytest.mark.asyncio
async def test_memory_query(memory_system):
    """Test querying memory."""
    memory_system._generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    memory_system.qdrant.search = AsyncMock(return_value=[
        {"id": "1", "score": 0.9, "content": "Test"}
    ])
    memory_system.graphiti.search = AsyncMock(return_value=[])

    result = await memory_system.query("Test query")

    assert "vector_results" in result
    assert "graph_results" in result
