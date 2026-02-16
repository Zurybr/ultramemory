"""Document processor for various file types."""

import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pandas as pd
from bs4 import BeautifulSoup
import requests


class DocumentProcessor:
    """Process various document types into plain text."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def process(self, content: str | Path) -> dict[str, Any]:
        """Process content and extract text.

        Args:
            content: Text string, file path, or URL

        Returns:
            Dict with 'text', 'type', and 'metadata'
        """
        content_str = str(content)

        # URL
        if content_str.startswith(("http://", "https://")):
            return await self._process_url(content_str)

        # File path
        path = Path(content)
        if path.exists() and path.is_file():
            return await self._process_file(path)

        # Plain text
        return {"text": content_str, "type": "text", "metadata": {}}

    async def _process_url(self, url: str) -> dict[str, Any]:
        """Process URL and extract text."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return {"text": text, "type": "url", "metadata": {"url": url}}

    async def _process_file(self, path: Path) -> dict[str, Any]:
        """Process file based on extension."""
        ext = path.suffix.lower()

        if ext == ".pdf":
            return await self._process_pdf(path)
        elif ext in [".txt", ".md"]:
            return {"text": path.read_text(encoding="utf-8"), "type": "text", "metadata": {"filename": path.name}}
        elif ext in [".xlsx", ".xls"]:
            return await self._process_excel(path)
        elif ext == ".csv":
            return await self._process_csv(path)
        elif ext == ".html":
            return await self._process_html(path)
        else:
            return {"text": str(path), "type": "unknown", "metadata": {"filename": path.name}}

    async def _process_pdf(self, path: Path) -> dict[str, Any]:
        """Process PDF file."""
        text_parts = []
        with fitz.open(path) as doc:
            for page in doc:
                text_parts.append(page.get_text())

        return {"text": "\n".join(text_parts), "type": "pdf", "metadata": {"filename": path.name}}

    async def _process_excel(self, path: Path) -> dict[str, Any]:
        """Process Excel file."""
        dfs = pd.read_excel(path, sheet_name=None)
        text_parts = []

        for sheet_name, df in dfs.items():
            text_parts.append(f"## Sheet: {sheet_name}\n")
            text_parts.append(df.to_csv(index=False))

        return {"text": "\n".join(text_parts), "type": "excel", "metadata": {"filename": path.name}}

    async def _process_csv(self, path: Path) -> dict[str, Any]:
        """Process CSV file."""
        df = pd.read_csv(path)
        return {"text": df.to_csv(index=False), "type": "csv", "metadata": {"filename": path.name}}

    async def _process_html(self, path: Path) -> dict[str, Any]:
        """Process HTML file."""
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")

        for tag in soup(["script", "style"]):
            tag.decompose()

        return {"text": soup.get_text(separator="\n", strip=True), "type": "html", "metadata": {"filename": path.name}}

    def chunk(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind(".", start, end)
                last_newline = text.rfind("\n", start, end)
                break_point = max(last_period, last_newline)

                if break_point > start:
                    end = break_point + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap

        return chunks
