"""Enhanced Librarian Agent - inserts information into memory."""

import json
import mimetypes
import hashlib
from datetime import datetime
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

    Enhanced with:
    - Automatic metadata extraction (title, description, tags)
    - File metadata extraction (size, dates, author)
    - Title extraction from content
    - Better URL metadata
    """

    # Common title patterns
    TITLE_PATTERNS = [
        r'^#\s+(.+)$',           # Markdown H1
        r'^##\s+(.+)$',          # Markdown H2
        r'^(.+)\n[=-]{3,}',      # Title with underline
        r'<title>(.+?)</title>', # HTML title
        r'<h1>(.+?)</h1>',       # HTML H1
    ]

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.processor = DocumentProcessor()

    async def add(self, content: str | Path, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Add content to memory.

        Enhanced with automatic metadata extraction from files and URLs.

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

        # 4. Extract automatic metadata
        base_metadata = self._extract_automatic_metadata(
            content,
            processed["text"],
            processed.get("metadata", {})
        )

        # 5. Merge with user-provided metadata
        final_metadata = {**base_metadata, **(metadata or {})}

        # 6. Add each chunk to memory
        results = []
        for i, chunk in enumerate(chunks):
            # Add chunk-specific metadata
            chunk_metadata = {
                **final_metadata,
                "source": str(content),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_type": content_type,
                "agent": "librarian_insert",
            }

            doc_id = await self.memory.add(chunk, metadata=chunk_metadata)
            results.append({"chunk": i + 1, "doc_id": doc_id})

        return {
            "status": "success",
            "chunks_created": len(chunks),
            "document_id": results[0]["doc_id"] if results else None,
            "content_type": content_type,
            "metadata_extracted": True,
        }

    def _extract_automatic_metadata(
        self,
        content: str | Path,
        text: str,
        processed_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract automatic metadata from content.

        Extracts:
        - title: From file name, URL, or content
        - description: First meaningful lines
        - tags: From content analysis
        - file_metadata: For files (size, dates)
        - url_metadata: For URLs

        Args:
            content: Original content (path or URL)
            text: Processed text content
            processed_metadata: Metadata from document processor

        Returns:
            Dictionary with automatic metadata
        """
        metadata = {}

        # Extract title
        title = self._extract_title(text, content)
        if title:
            metadata["title"] = title

        # Extract description (first non-empty lines)
        if text:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines:
                # Use first meaningful line as description
                desc = lines[0][:200]
                if len(lines) > 1:
                    desc += " " + lines[1][:100]
                metadata["description"] = desc

        # Extract tags from content
        tags = self._extract_tags(text)
        if tags:
            metadata["tags"] = tags

        # Add file metadata if available
        if isinstance(content, Path) and content.exists():
            file_meta = self._extract_file_metadata(content)
            metadata.update(file_meta)

        # Add URL metadata
        if isinstance(content, str) and content.startswith(("http://", "https://")):
            url_meta = self._extract_url_metadata(content)
            metadata.update(url_meta)

        # Merge with processed metadata
        if processed_metadata:
            metadata = {**metadata, **processed_metadata}

        return metadata

    def _extract_title(self, text: str, content: str | Path) -> str | None:
        """Extract title from content.

        Args:
            text: Text content
            content: Original content

        Returns:
            Extracted title or None
        """
        # Try content-based title extraction
        import re

        for pattern in self.TITLE_PATTERNS:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()

        # Fall back to filename
        if isinstance(content, Path):
            # Use stem (filename without extension)
            stem = content.stem
            # Clean up common patterns
            stem = re.sub(r'[-_]', ' ', stem)
            if len(stem) > 3 and len(stem) < 100:
                return stem

        # Try URL path
        if isinstance(content, str) and content.startswith(("http://", "https://")):
            from urllib.parse import urlparse
            parsed = urlparse(content)
            path = parsed.path.strip('/')
            if path:
                # Use last path segment as title
                parts = path.split('/')
                title = parts[-1].replace('-', ' ').replace('_', ' ')
                # Remove extension
                title = re.sub(r'\.[^.]+$', '', title)
                if len(title) > 3:
                    return title.title()

        return None

    def _extract_tags(self, text: str, max_tags: int = 8) -> list[str]:
        """Extract tags from content using frequency analysis.

        Args:
            text: Text content
            max_tags: Maximum number of tags to extract

        Returns:
            List of tags
        """
        import re
        from collections import Counter

        # Common stopwords for tag extraction
        stopwords = {
            'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'their',
            'which', 'would', 'could', 'should', 'there', 'where', 'when', 'what',
            'more', 'also', 'just', 'only', 'very', 'into', 'over', 'such', 'after',
            'before', 'about', 'above', 'below', 'between', 'under', 'again', 'then',
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'has', 'get', 'may', 'see', 'com',
            'www', 'http', 'https', 'org', 'net', 'edu', 'file', 'section', 'page'
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

        # Filter stopwords
        filtered = [w for w in words if w not in stopwords]

        # Get frequency
        freq = Counter(filtered)

        # Return top tags (words that appear multiple times)
        tags = [word for word, count in freq.most_common(max_tags) if count >= 2]

        return tags[:max_tags]

    def _extract_file_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file metadata
        """
        import os

        metadata = {}

        try:
            stat = file_path.stat()

            metadata["file_size"] = stat.st_size
            metadata["file_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            metadata["file_created"] = datetime.fromtimestamp(stat.st_ctime).isoformat()

            # Extract filename without extension as potential title
            metadata["file_name"] = file_path.name
            metadata["file_stem"] = file_path.stem
            metadata["file_extension"] = file_path.suffix.lower()

        except Exception:
            pass

        return metadata

    def _extract_url_metadata(self, url: str) -> dict[str, Any]:
        """Extract metadata from URL.

        Args:
            url: URL string

        Returns:
            Dictionary with URL metadata
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)

        metadata = {
            "url_scheme": parsed.scheme,
            "url_domain": parsed.netloc,
            "url_path": parsed.path,
        }

        # Extract domain name
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        metadata["url_domain_name"] = domain.split('.')[0] if domain else None

        return metadata

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
