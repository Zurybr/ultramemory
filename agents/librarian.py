"""Librarian Agent - inserts information into memory."""

from typing import Any
from pathlib import Path

from core.memory import MemorySystem
from core.document_processor import DocumentProcessor


class LibrarianAgent:
    """Agent responsible for organizing and inserting information into memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.processor = DocumentProcessor()

    async def add(self, content: str | Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Add content to memory.

        Args:
            content: Text, file path, or URL
            metadata: Optional metadata for the content

        Returns:
            Result with document_id and chunks created
        """
        # 1. Process content (detect type, extract text)
        processed = await self.processor.process(content)

        # 2. Chunk if needed
        chunks = self.processor.chunk(processed["text"])

        # 3. Add each chunk to memory
        results = []
        for i, chunk in enumerate(chunks):
            doc_id = await self.memory.add(
                chunk,
                metadata={
                    **(metadata or {}),
                    "source": str(content),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            results.append({"chunk": i + 1, "doc_id": doc_id})

        return {
            "status": "success",
            "chunks_created": len(chunks),
            "document_id": results[0]["doc_id"] if results else None,
        }

    async def add_from_directory(self, directory: Path, extensions: list[str] | None = None) -> dict[str, Any]:
        """Add all files from a directory."""
        if extensions is None:
            extensions = [".txt", ".pdf", ".md", ".html", ".xlsx", ".csv"]

        results = []
        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                try:
                    result = await self.add(file_path)
                    results.append({"file": str(file_path), "status": "success", **result})
                except Exception as e:
                    results.append({"file": str(file_path), "status": "error", "error": str(e)})

        return {
            "status": "success",
            "files_processed": len(results),
            "results": results,
        }
