"""Enhanced Librarian Agent - inserts information into memory."""

import json
import mimetypes
from typing import Any
from pathlib import Path

from core.memory import MemorySystem
from core.document_processor import DocumentProcessor


class LibrarianAgent:
    """Agent responsible for organizing and inserting information into memory.

    Supports:
    - Plain text
    - Files (txt, pdf, md, html, docx, xlsx, csv)
    - Images (jpg, png, gif) - extracts EXIF metadata
    - URLs - fetches and processes content
    - Videos (mp4, webm) - extracts metadata
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.processor = DocumentProcessor()

    async def add(self, content: str | Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Add content to memory.

        Args:
            content: Text, file path, URL, or Path object
            metadata: Optional metadata for the content

        Returns:
            Result with document_id and chunks created
        """
        # 1. Detect content type and process
        processed = await self._process_content(content)

        # 2. Chunk if needed
        chunks = self.processor.chunk(processed["text"])

        # 3. Determine content type for metadata
        content_type = self._detect_content_type(content)

        # 4. Add each chunk to memory
        results = []
        for i, chunk in enumerate(chunks):
            doc_id = await self.memory.add(
                chunk,
                metadata={
                    **(metadata or {}),
                    "source": str(content),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "content_type": content_type,
                    "agent": "librarian_insert",
                },
            )
            results.append({"chunk": i + 1, "doc_id": doc_id})

        return {
            "status": "success",
            "chunks_created": len(chunks),
            "document_id": results[0]["doc_id"] if results else None,
            "content_type": content_type,
        }

    async def _process_content(self, content: str | Path) -> dict[str, Any]:
        """Process content based on type."""
        # If it's a Path and exists
        if isinstance(content, Path) and content.exists():
            return await self.processor.process(content)

        # If it's a URL
        if isinstance(content, str) and content.startswith(("http://", "https://")):
            return await self._fetch_url(content)

        # If it's text
        return {"text": str(content), "metadata": {}}

    async def _fetch_url(self, url: str) -> dict[str, Any]:
        """Fetch and process content from URL."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                if "text/html" in content_type:
                    # Extract text from HTML
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, "html.parser")
                    text = soup.get_text(separator="\n", strip=True)
                else:
                    text = response.text

                return {
                    "text": text[:50000],  # Limit size
                    "metadata": {
                        "url": url,
                        "fetched_at": str(Path().stat().st_mtime),
                    }
                }
        except Exception as e:
            return {
                "text": f"Error fetching URL: {str(e)}",
                "metadata": {"url": url, "error": str(e)}
            }

    def _detect_content_type(self, content: str | Path) -> str:
        """Detect the type of content."""
        if isinstance(content, Path) and content.exists():
            ext = content.suffix.lower()
            mime_type, _ = mimetypes.guess_type(str(content))

            if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                return "image"
            elif ext in [".mp4", ".webm", ".mov", ".avi"]:
                return "video"
            elif ext in [".pdf"]:
                return "document"
            elif ext in [".txt", ".md"]:
                return "text"
            elif ext in [".html", ".htm"]:
                return "webpage"
            elif ext in [".xlsx", ".xls", ".csv"]:
                return "spreadsheet"
            elif ext in [".docx", ".doc"]:
                return "word"
            return mime_type or "unknown"

        # Check if URL
        if isinstance(content, str):
            if content.startswith(("http://", "https://")):
                return "url"
            return "text"

        return "unknown"

    async def add_from_directory(self, directory: Path, extensions: list[str] | None = None) -> dict[str, Any]:
        """Add all files from a directory."""
        if extensions is None:
            extensions = [".txt", ".pdf", ".md", ".html", ".xlsx", ".csv", ".docx"]

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

    async def add_with_structure(self, content: str, structure: dict[str, Any]) -> dict[str, Any]:
        """Add content with explicit structural metadata.

        Args:
            content: The text content
            structure: Dict with keys: category, tags, relationships

        Returns:
            Result with document_id
        """
        metadata = {
            "structure_category": structure.get("category"),
            "structure_tags": structure.get("tags", []),
            "structure_relationships": structure.get("relationships", []),
            "agent": "librarian_insert_structured",
        }

        doc_id = await self.memory.add(content, metadata=metadata)

        return {
            "status": "success",
            "document_id": doc_id,
            "structure": structure,
        }
