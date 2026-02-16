"""Tests for document processor."""

import pytest
from pathlib import Path
import tempfile

from core.document_processor import DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor(chunk_size=100, chunk_overlap=20)


def test_chunk_small_text(processor):
    """Test that small text is not chunked."""
    text = "This is a short text."
    chunks = processor.chunk(text)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_long_text(processor):
    """Test that long text is chunked."""
    text = "A" * 200 + ". " + "B" * 200 + "."
    chunks = processor.chunk(text)

    assert len(chunks) > 1


def test_chunk_with_overlap(processor):
    """Test that chunks overlap."""
    text = "This is sentence one. This is sentence two. " * 50
    chunks = processor.chunk(text)

    if len(chunks) > 1:
        # Check overlap exists
        assert any(chunks[i].endswith(chunks[i+1][:10]) for i in range(len(chunks) - 1))


@pytest.fixture
def temp_text_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content for the file.")
        return Path(f.name)


@pytest.mark.asyncio
async def test_process_text(processor):
    """Test processing plain text."""
    result = await processor.process("Hello world")

    assert result["type"] == "text"
    assert result["text"] == "Hello world"


@pytest.mark.asyncio
async def test_process_file(processor, temp_text_file):
    """Test processing a file."""
    result = await processor.process(temp_text_file)

    assert result["type"] == "text"
    assert "Test content" in result["text"]
