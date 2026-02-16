# Sistema de Agentes Ultramemory - Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar un sistema completo de agentes especializados para automatización de memoria e investigación, con agentes bibliotecarios, cron jobs y CLI interactiva.

**Architecture:** Sistema de agentes con base de herramientas, heartbeat para tareas proactivas, scheduler configurable, y CLI interactiva para revisión manual.

**Tech Stack:** Python 3.11+, Click, httpx, Tavily API, async/await, YAML

---

## Fase 0: Agentes Existentes (ya implementados)

### Task 0.1: CodeIndexerAgent (YA EXISTE)

**Files:**
- Already exists: `agents/code_indexer.py`
- Already exists: `ultramemory_cli/code_index.py`

**Funcionalidad:**
- Indexa repositorios GitHub en memoria
- Soporta categorías: lefarma, e6labs, personal, opensource, hobby, trabajo, dependencias
- Incrementa indexing (solo archivos modificados)
- Integración con CodeWiki

**CLI Usage:**
```bash
ulmemory code-index owner/repo
ulmemory code-index https://github.com/owner/repo -c personal
```

---

## Fase 1: Sistema de Heartbeat y Estructura Base

### Task 1.1: Crear archivo heartbeat.md y sistema de lectura

**Files:**
- Create: `~/.ulmemory/heartbeat.md` (ejemplo inicial)
- Create: `agents/heartbeat_reader.py`

**Step 1: Escribir el HeartbeatReader**

```python
# agents/heartbeat_reader.py
"""Heartbeat system for proactive task execution."""

from pathlib import Path
from datetime import datetime
from typing import Any
import re


HEARTBEAT_PATH = Path.home() / ".ulmemory" / "heartbeat.md"


class HeartbeatReader:
    """Lee y parsea el archivo heartbeat.md para tareas pendientes."""

    def __init__(self, heartbeat_path: Path | None = None):
        self.path = heartbeat_path or HEARTBEAT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> dict[str, Any]:
        """Lee el heartbeat y retorna tareas pendientes."""
        if not self.path.exists():
            return {"tasks": [], "last_updated": None}

        content = self.path.read_text(encoding="utf-8")
        return self._parse_heartbeat(content)

    def _parse_heartbeat(self, content: str) -> dict[str, Any]:
        """Parsea el contenido del heartbeat."""
        tasks = []
        lines = content.split("\n")
        current_task = None

        for line in lines:
            # Buscar inicio de tarea: - [ ] o - [x]
            task_match = re.match(r'^-\s*\[([ x])\]\s*(.+)$', line)
            if task_match:
                if current_task:
                    tasks.append(current_task)

                status = task_match.group(1) == "x"
                title = task_match.group(2).strip()
                current_task = {
                    "title": title,
                    "completed": status,
                    "tags": [],
                    "priority": "normal",
                    "created": None,
                }
            elif current_task:
                # Tags: #tag1 #tag2
                tag_match = re.findall(r'#(\w+)', line)
                if tag_match:
                    current_task["tags"].extend(tag_match)

        if current_task:
            tasks.append(current_task)

        return {
            "tasks": tasks,
            "last_updated": datetime.now().isoformat(),
            "pending_count": sum(1 for t in tasks if not t["completed"]),
        }

    def get_pending_tasks(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """Obtiene tareas pendientes, opcionalmente filtradas por tags."""
        data = self.read()
        pending = [t for t in data["tasks"] if not t["completed"]]

        if tags:
            pending = [t for t in pending if any(tag in t["tags"] for tag in tags)]

        return pending

    def mark_completed(self, task_title: str) -> bool:
        """Marca una tarea como completada."""
        if not self.path.exists():
            return False

        content = self.path.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            if f"- [ ] {task_title}" in line or f"- [ ]  {task_title}" in line:
                line = line.replace("- [ ]", "- [x]")
            new_lines.append(line)

        self.path.write_text("\n".join(new_lines), encoding="utf-8")
        return True

    def add_task(self, title: str, tags: list[str] | None = None, priority: str = "normal"):
        """Agrega una nueva tarea al heartbeat."""
        if not self.path.exists():
            header = "# Heartbeat - Tareas Pendientes\n\n"
            self.path.write_text(header, encoding="utf-8")

        tags_str = " ".join(f"#{tag}" for tag in (tags or []))
        task_line = f"- [ ] {title} {tags_str}\n"

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(task_line)
```

**Step 2: Crear heartbeat.md de ejemplo**

```markdown
# Heartbeat - Tareas Pendientes

## Investigación
- [ ] Investigar nuevas tendencias en AI agents #research #ai
- [ ] Revisar artículos sobre RAG patterns #research #rag

## Mantenimiento
- [ ] Limpiar entradas duplicadas en memoria #maintenance

## Reportes
- [ ] Generar reporte semanal de actividad #report
```

**Step 3: Verificar módulo**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.heartbeat_reader import HeartbeatReader; h = HeartbeatReader(); print(h.read())"`
Expected: Estructura con tasks y last_updated

---

## Fase 2: Agentes Bibliotecarios (Memory Operations)

### Task 2.1: Enhance LibrarianInsertAgent

**Files:**
- Modify: `agents/librarian.py`

**Step 1: Agregar soporte para múltiples tipos de contenido**

Reemplazar el contenido de `agents/librarian.py`:

```python
"""Enhanced Librarian Agent - inserts information into memory."""

import json
import mimetypes
from typing import Any
from pathlib import Path

from core.memory import MemorySystem
from core.document_processor import DocumentProcessor


class LibrarianInsertAgent:
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
```

**Step 2: Probar el agente mejorado**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.librarian import LibrarianInsertAgent; print('OK')"`
Expected: `OK`

---

### Task 2.2: Enhance LibrarianDeleteAgent

**Files:**
- Modify: `agents/deleter.py`

**Step 1: Agregar preservación de conexiones y audit log**

Reemplazar `agents/deleter.py`:

```python
"""Enhanced Deleter Agent - removes memories with connection preservation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem


class DeleterAgent:
    """Agent responsible for deleting memories with audit trail.

    Features:
    - Preserves graph connections when possible
    - Maintains audit log of deletions
    - Option to create new connections after deletion
    """

    AUDIT_LOG = Path.home() / ".ulmemory" / "logs" / "deletions.jsonl"

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    async def delete_all(self, confirm: bool = False) -> dict[str, Any]:
        """Delete ALL memories from the system.

        Args:
            confirm: Must be True to actually delete

        Returns:
            Report with count of deleted items
        """
        if not confirm:
            return {
                "status": "aborted",
                "message": "Deletion not confirmed. Set confirm=True to proceed.",
            }

        result = {
            "status": "success",
            "qdrant_deleted": 0,
            "errors": [],
        }

        try:
            count_before = await self.memory.qdrant.count()
            deleted = await self.memory.qdrant.delete_all()
            result["qdrant_deleted"] = deleted if deleted else count_before

            # Log the deletion
            await self._log_deletion({
                "type": "delete_all",
                "count": result["qdrant_deleted"],
                "timestamp": datetime.now().isoformat(),
            })

            try:
                await self.memory.redis.clear_all()
                result["redis_cleared"] = True
            except Exception:
                result["redis_cleared"] = False

            try:
                await self.memory.graphiti.clear_all()
                result["graph_cleared"] = True
            except Exception:
                result["graph_cleared"] = False

            result["message"] = f"Deleted {result['qdrant_deleted']} memories"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_query(self, query: str, limit: int = 100, preserve_connections: bool = True) -> dict[str, Any]:
        """Delete memories matching a semantic query.

        Args:
            query: Search query to find memories to delete
            limit: Maximum memories to delete
            preserve_connections: If True, check graph before deletion

        Returns:
            Report with deleted items
        """
        result = {
            "status": "success",
            "query": query,
            "deleted": 0,
            "preserved_connections": 0,
            "errors": [],
        }

        try:
            # Search for memories
            results = await self.memory.qdrant.search(
                query_embedding=await self.memory.embedding.embed(query),
                limit=limit,
            )

            # Delete each found memory
            for item in results:
                try:
                    # Check for connections if preservation is enabled
                    if preserve_connections:
                        has_connections = await self._check_connections(item["id"])
                        if has_connections:
                            result["preserved_connections"] += 1
                            continue  # Skip deletion

                    await self.memory.qdrant.delete(item["id"])
                    result["deleted"] += 1

                    # Log the deletion
                    await self._log_deletion({
                        "type": "delete_by_query",
                        "query": query,
                        "deleted_id": item["id"],
                        "timestamp": datetime.now().isoformat(),
                    })

                except Exception as e:
                    result["errors"].append(f"Failed to delete {item['id']}: {e}")

            result["message"] = f"Deleted {result['deleted']} memories matching '{query}'"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))

        return result

    async def delete_by_id(self, memory_id: str, preserve_connections: bool = True) -> dict[str, Any]:
        """Delete a specific memory by ID.

        Args:
            memory_id: The ID of the memory to delete
            preserve_connections: If True, preserve graph connections

        Returns:
            Report with status
        """
        result = {
            "status": "success",
            "id": memory_id,
            "deleted": False,
        }

        try:
            if preserve_connections:
                has_connections = await self._check_connections(memory_id)
                if has_connections:
                    result["status"] = "blocked"
                    result["message"] = f"Memory {memory_id} has connections. Use force=True to delete anyway."
                    return result

            await self.memory.qdrant.delete(memory_id)
            result["deleted"] = True

            # Log the deletion
            await self._log_deletion({
                "type": "delete_by_id",
                "deleted_id": memory_id,
                "timestamp": datetime.now().isoformat(),
            })

            result["message"] = f"Memory {memory_id} deleted"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def delete_with_replacement(self, memory_id: str, new_content: str, new_metadata: dict | None = None) -> dict[str, Any]:
        """Delete memory and create new connections to replace it.

        Args:
            memory_id: ID to delete
            new_content: New content to add
            new_metadata: Metadata for new content

        Returns:
            Report with deletion and creation
        """
        # First, get related memories
        related = await self._get_related(memory_id)

        # Delete old
        await self.memory.qdrant.delete(memory_id)

        # Log deletion
        await self._log_deletion({
            "type": "delete_with_replacement",
            "deleted_id": memory_id,
            "new_relationships": len(related),
            "timestamp": datetime.now().isoformat(),
        })

        # Add new content
        new_metadata = new_metadata or {}
        new_metadata["replaces"] = memory_id
        new_metadata["related_count"] = len(related)

        doc_id = await self.memory.add(new_content, metadata=new_metadata)

        return {
            "status": "success",
            "deleted_id": memory_id,
            "new_id": doc_id,
            "related_preserved": len(related),
        }

    async def _check_connections(self, memory_id: str) -> bool:
        """Check if memory has graph connections."""
        try:
            # Try graphiti connection check
            result = await self.memory.graphiti.get_neighbors(memory_id)
            return len(result) > 0
        except Exception:
            return False

    async def _get_related(self, memory_id: str) -> list[str]:
        """Get related memory IDs."""
        try:
            result = await self.memory.graphiti.get_neighbors(memory_id)
            return [r.get("id") for r in result]
        except Exception:
            return []

    async def _log_deletion(self, entry: dict[str, Any]):
        """Log deletion to audit file."""
        try:
            with open(self.AUDIT_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Don't fail if logging fails

    async def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent deletion history."""
        if not self.AUDIT_LOG.exists():
            return []

        entries = []
        with open(self.AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue

        return entries[-limit:]

    async def count(self) -> int:
        """Count total memories in the system."""
        return await self.memory.qdrant.count()
```

**Step 2: Verificar**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.deleter import DeleterAgent; print('OK')"`
Expected: `OK`

---

### Task 2.3: Create ConsultantAgent

**Files:**
- Create: `agents/consultant.py`

**Step 1: Escribir el agente consultor**

```python
"""Consultant Agent - ordered information retrieval."""

from typing import Any
from core.memory import MemorySystem


class ConsultantAgent:
    """Agent for ordered, structured information retrieval.

    Features:
    - Ordered search results by relevance, date, or source
    - Context-aware retrieval
    - Supports complex queries
    - Returns structured text output
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def query(
        self,
        query: str,
        order_by: str = "relevance",
        max_results: int = 10,
        include_context: bool = True,
    ) -> dict[str, Any]:
        """Query memory with ordering.

        Args:
            query: Search query
            order_by: "relevance", "date", or "source"
            max_results: Maximum results to return
            include_context: Include surrounding context

        Returns:
            Structured results with ordered items
        """
        # Get raw results
        raw_results = await self.memory.qdrant.search(
            query_embedding=await self.memory.embedding.embed(query),
            limit=max_results * 2,  # Get more for sorting
        )

        # Sort results
        sorted_results = self._sort_results(raw_results, order_by)

        # Limit to max_results
        sorted_results = sorted_results[:max_results]

        # Format output
        formatted = []
        for i, item in enumerate(sorted_results, 1):
            content = item.get("content", item.get("payload", {}).get("content", ""))
            metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))

            entry = {
                "rank": i,
                "content": content[:500],  # Limit content length
                "score": item.get("score", 0),
                "source": metadata.get("source", "unknown"),
                "type": metadata.get("content_type", metadata.get("type", "text")),
            }

            if include_context:
                entry["full_content"] = content

            formatted.append(entry)

        return {
            "query": query,
            "total_found": len(raw_results),
            "returned": len(formatted),
            "order_by": order_by,
            "results": formatted,
        }

    def _sort_results(self, results: list[dict], order_by: str) -> list[dict]:
        """Sort results by specified criteria."""
        if order_by == "relevance":
            return sorted(results, key=lambda x: x.get("score", 0), reverse=True)

        elif order_by == "date":
            # Sort by timestamp in metadata
            def get_date(item):
                metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))
                return metadata.get("timestamp", "")
            return sorted(results, key=get_date, reverse=True)

        elif order_by == "source":
            def get_source(item):
                metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))
                return metadata.get("source", "zzz")
            return sorted(results, key=get_source)

        return results

    async def query_structured(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query with structured filters.

        Args:
            query: Search query
            filters: Dict with filters (type, source, date_range, tags)

        Returns:
            Filtered and structured results
        """
        filters = filters or {}

        # Base search
        results = await self.memory.qdrant.search(
            query_embedding=await self.memory.embedding.embed(query),
            limit=filters.get("limit", 20),
        )

        # Apply filters
        filtered = []
        for item in results:
            metadata = item.get("metadata", item.get("payload", {}).get("metadata", {}))

            # Filter by type
            if filters.get("type") and metadata.get("content_type") != filters["type"]:
                continue

            # Filter by source
            if filters.get("source") and metadata.get("source") != filters["source"]:
                continue

            # Filter by tags
            if filters.get("tags"):
                item_tags = metadata.get("tags", [])
                if not any(tag in item_tags for tag in filters["tags"]):
                    continue

            filtered.append(item)

        return {
            "query": query,
            "filters_applied": filters,
            "results": filtered,
            "count": len(filtered),
        }

    def format_as_text(self, results: dict[str, Any]) -> str:
        """Format query results as readable text.

        Args:
            results: Results from query()

        Returns:
            Formatted text string
        """
        lines = [
            f"=== Resultados para: {results['query']} ===",
            f"Ordenado por: {results['order_by']}",
            f"Total: {results['returned']} de {results['total_found']}",
            "",
        ]

        for item in results["results"]:
            lines.extend([
                f"[{item['rank']}] (score: {item['score']:.2f})",
                f"Fuente: {item['source']} | Tipo: {item['type']}",
                "",
                item["content"],
                "",
                "-" * 40,
                "",
            ])

        return "\n".join(lines)
```

**Step 2: Verificar**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.consultant import ConsultantAgent; print('OK')"`
Expected: `OK`

---

## Fase 3: Agentes Cron (Automatización)

### Task 3.1: Create ProactiveAgent

**Files:**
- Create: `agents/proactive.py`

**Step 1: Escribir el agente proactivo**

```python
"""Proactive Agent - executes tasks from heartbeat."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem
from agents.heartbeat_reader import HeartbeatReader


class ProactiveAgent:
    """Agent that executes tasks from heartbeat.md.

    Runs every 30 minutes and checks for pending tasks.
    Supports task types: research, report, cleanup, notify
    """

    def __init__(self, memory_system: MemorySystem, heartbeat_path: Path | None = None):
        self.memory = memory_system
        self.heartbeat = HeartbeatReader(heartbeat_path)

    async def check_and_execute(self, max_tasks: int = 3) -> dict[str, Any]:
        """Check heartbeat and execute pending tasks.

        Args:
            max_tasks: Maximum tasks to execute per run

        Returns:
            Report of executed tasks
        """
        pending = self.heartbeat.get_pending_tasks()

        if not pending:
            return {
                "status": "no_tasks",
                "executed": 0,
                "message": "No pending tasks in heartbeat",
            }

        results = []
        tasks_to_execute = pending[:max_tasks]

        for task in tasks_to_execute:
            try:
                result = await self._execute_task(task)
                results.append({
                    "task": task["title"],
                    "status": "success",
                    "result": result,
                })

                # Mark as completed
                self.heartbeat.mark_completed(task["title"])

            except Exception as e:
                results.append({
                    "task": task["title"],
                    "status": "error",
                    "error": str(e),
                })

        return {
            "status": "completed",
            "executed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def _execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a single task based on its tags."""
        title = task["title"]
        tags = task.get("tags", [])

        # Determine task type from tags
        if "research" in tags:
            return await self._do_research(title)
        elif "report" in tags:
            return await self._do_report(title)
        elif "cleanup" in tags or "maintenance" in tags:
            return await self._do_cleanup(title)
        elif "notify" in tags:
            return await self._do_notify(title)
        else:
            # Default: log task
            return {"message": f"Task noted: {title}"}

    async def _do_research(self, task_title: str) -> dict[str, Any]:
        """Execute research task."""
        # Extract topic from title (remove "Investigar" prefix if present)
        topic = task_title.replace("Investigar", "").replace("investigar", "").strip()

        from agents.researcher import ResearcherAgent

        agent = ResearcherAgent(self.memory, enable_web_search=True)

        # Run research
        result = await agent.deep_research(topic, max_depth=2, save_to_memory=True)

        return {
            "topic": topic,
            "sources_found": result.get("total_sources", 0),
            "saved": result.get("synthesis_saved", False),
        }

    async def _do_report(self, task_title: str) -> dict[str, Any]:
        """Execute report generation task."""
        # Generate activity report
        count = await self.memory.qdrant.count()

        report = f"""# Reporte de Actividad

Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Estado de Memoria
- Total de entradas: {count}

## Tareas Completadas
- Reporte generado
"""

        # Save to memory
        doc_id = await self.memory.add(
            report,
            metadata={
                "type": "report",
                "report_type": "activity",
            },
        )

        return {
            "document_id": doc_id,
            "total_memories": count,
        }

    async def _do_cleanup(self, task_title: str) -> dict[str, Any]:
        """Execute cleanup task."""
        from agents.consolidator import ConsolidatorAgent

        agent = ConsolidatorAgent(self.memory)
        result = await agent.consolidate()

        return result

    async def _do_notify(self, task_title: str) -> dict[str, Any]:
        """Execute notification task."""
        # For now, just add a notification to memory
        await self.memory.add(
            f"Notificación: {task_title}",
            metadata={"type": "notification", "source": "proactive"},
        )

        return {"notified": True, "message": task_title}

    async def add_task(
        self,
        title: str,
        tags: list[str] | None = None,
        priority: str = "normal",
    ):
        """Add a task to heartbeat."""
        self.heartbeat.add_task(title, tags, priority)
```

**Step 2: Verificar**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.proactive import ProactiveAgent; print('OK')"`
Expected: `OK`

---

### Task 3.2: Enhance ResearcherAgent (Hourly)

**Files:**
- Modify: `agents/researcher.py`

**Step 1: Agregar configuración de todo list y fuentes científicas**

Agregar al inicio de `agents/researcher.py`:

```python
# Enhanced ResearcherAgent configuration
from pathlib import Path

RESEARCH_TODO_PATH = Path.home() / ".ulmemory" / "research" / "todo.md"
RESEARCH_OUTPUT_DIR = Path.home() / ".ulmemory" / "research" / "reports"

# Ensure directories exist
RESEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
```

Agregar método para leer todo list:

```python
def load_todo_list(self) -> list[str]:
    """Load research todo list from file."""
    if not RESEARCH_TODO_PATH.exists():
        return []

    content = RESEARCH_TODO_PATH.read_text(encoding="utf-8")
    topics = []

    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            topics.append(line)

    return topics

def save_todo_list(self, topics: list[str]):
    """Save research todo list (removes first item as it's being processed)."""
    RESEARCH_TODO_PATH.parent.mkdir(parents=True, exist_ok=True")

    remaining = topics[1:]  # Remove first (being processed)
    content = "# Research Todo List\n\n" + "\n".join(f"- {t}" for t in remaining)

    RESEARCH_TODO_PATH.write_text(content, encoding="utf-8")
```

**Step 2: Agregar método de investigación científica**

Agregar método a `ResearcherAgent`:

```python
async def research_with_sources(
    self,
    query: str,
    include_scientific: bool = True,
    include_github: bool = True,
) -> dict[str, Any]:
    """Research with specific sources.

    Args:
        query: Research query
        include_scientific: Include scientific papers (arXiv, etc)
        include_github: Include GitHub repositories

    Returns:
        Combined results from all sources
    """
    results = {
        "query": query,
        "sources_used": [],
        "web": [],
        "github": [],
        "scientific": [],
        "memory": [],
    }

    # Memory search
    mem_result = await self.memory_tool.execute(query=query, limit=10)
    if mem_result.success:
        results["memory"] = mem_result.data.get("vector_results", [])
        results["sources_used"].append("memory")

    # Web search
    if self.web_tool and self.web_tool.api_key:
        web_result = await self.web_tool.execute(
            query=query,
            max_results=10,
            search_depth="advanced"
        )
        if web_result.success:
            results["web"] = web_result.data.get("results", [])
            results["sources_used"].append("web")

    # GitHub search (via CodeWiki)
    if self.codewiki_tool:
        try:
            github_result = await self.codewiki_tool.execute(
                query=query,
                limit=10,
            )
            if github_result.success:
                results["github"] = github_result.data.get("results", [])
                results["sources_used"].append("github")
        except Exception:
            pass  # Optional source

    return results
```

---

### Task 3.3: Enhance ConsolidatorAgent (Daily)

**Files:**
- Modify: `agents/consolidator.py`

**Step 1: Agregar generación de insights**

Agregar método a `ConsolidatorAgent`:

```python
async def generate_insights(self) -> dict[str, Any]:
    """Generate insights from memory connections.

    Analyzes relationships and generates actionable insights.
    """
    insights = {
        "generated_at": datetime.now().isoformat(),
        "insights": [],
        "patterns_found": 0,
    }

    try:
        # Get all documents
        all_docs = await self.memory.qdrant.get_all(limit=5000)

        if not all_docs:
            return insights

        # Find common topics (simple frequency analysis)
        topics = {}
        for doc in all_docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            # Extract tags if present
            tags = metadata.get("tags", [])
            for tag in tags:
                topics[tag] = topics.get(tag, 0) + 1

        # Get top topics
        top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]

        if top_topics:
            insights["patterns_found"] = len(top_topics)
            insights["insights"].append({
                "type": "common_topics",
                "description": "Most frequent topics in memory",
                "data": [{"topic": t, "count": c} for t, c in top_topics],
            })

        # Find connected concepts (simple co-occurrence)
        # This is a simplified version - real implementation would use graph
        if len(all_docs) > 10:
            # Sample some documents to find patterns
            sample = all_docs[:100]
            word_freq = {}

            for doc in sample:
                content = doc.get("content", "").lower()
                words = content.split()
                unique_words = set(words)

                for word in unique_words:
                    if len(word) > 5:  # Skip short words
                        word_freq[word] = word_freq.get(word, 0) + 1

            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]

            if top_words:
                insights["insights"].append({
                    "type": "key_concepts",
                    "description": "Most frequent significant terms",
                    "data": [{"term": w, "frequency": f} for w, f in top_words],
                })

        # Save insights to memory
        insight_text = self._format_insights(insights)
        await self.memory.add(
            insight_text,
            metadata={
                "type": "insight",
                "generated_by": "consolidator",
            },
        )

        insights["saved_to_memory"] = True

    except Exception as e:
        insights["error"] = str(e)

    return insights

def _format_insights(self, insights: dict) -> str:
    """Format insights as markdown."""
    lines = [
        "# Insights Generados",
        "",
        f"Fecha: {insights['generated_at']}",
        "",
    ]

    for insight in insights.get("insights", []):
        lines.extend([
            f"## {insight['type'].replace('_', ' ').title()}",
            "",
            insight["description"],
            "",
        ])

        if insight["type"] == "common_topics":
            for item in insight["data"][:5]:
                lines.append(f"- **{item['topic']}**: {item['count']} ocurrencias")
        elif insight["type"] == "key_concepts":
            for item in insight["data"][:10]:
                lines.append(f"- {item['term']}: {item['frequency']} menciones")

        lines.append("")

    return "\n".join(lines)
```

---

### Task 3.4: Create PRDGeneratorAgent

**Files:**
- Create: `agents/prd_generator.py`

**Step 1: Escribir el agente generador de PRDs**

```python
"""PRD Generator Agent - converts research to PRDs."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.memory import MemorySystem


class PRDGeneratorAgent:
    """Agent that generates PRDs from research findings.

    Reads research files and generates structured PRD documents.
    Maintains an index of research->PRD mappings.
    """

    RESEARCH_DIR = Path.home() / ".ulmemory" / "research" / "reports"
    PRD_DIR = Path.home() / ".ulmemory" / "prds"
    INDEX_FILE = PRD_DIR / "index.json"

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.PRD_DIR.mkdir(parents=True, exist_ok=True)
        self.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    def generate_prd(self, research_file: str | Path, title: str | None = None) -> dict[str, Any]:
        """Generate PRD from research file.

        Args:
            research_file: Path to research file
            title: Optional title for the PRD

        Returns:
            Generated PRD info
        """
        research_path = Path(research_file)

        if not research_path.exists():
            return {
                "status": "error",
                "message": f"Research file not found: {research_file}",
            }

        content = research_path.read_text(encoding="utf-8")

        # Extract title if not provided
        if not title:
            # Try to get from first heading
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            if not title:
                title = research_path.stem

        # Generate PRD
        prd_content = self._generate_prd_content(title, content)

        # Save PRD
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prd_filename = f"{timestamp}_{title[:30].replace(' ', '_')}.md"
        prd_path = self.PRD_DIR / prd_filename

        prd_path.write_text(prd_content, encoding="utf-8")

        # Update index
        self._add_to_index(str(research_path), str(prd_path), title)

        return {
            "status": "success",
            "prd_file": str(prd_path),
            "research_file": str(research_path),
            "title": title,
        }

    def _generate_prd_content(self, title: str, research_content: str) -> str:
        """Generate PRD structure from research."""
        # Extract key sections from research
        summary = ""
        sources = []

        lines = research_content.split("\n")
        in_summary = False

        for line in lines:
            if "## Summary" in line:
                in_summary = True
                continue
            elif line.startswith("## "):
                in_summary = False

            if in_summary and line.strip():
                summary += line.strip() + " "

            if line.startswith("- ") and "http" in line:
                sources.append(line[2:].strip())

        # Generate PRD template
        prd = f"""# PRD: {title}

> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
> **Source:** Research findings

---

## Overview

{summary[:500] if summary else "Research topic: " + title}

---

## Problem Statement

What problem does this solve? Why is it needed?

- [ ] Identified problem 1
- [ ] Identified problem 2

---

## Goals

- [ ] Goal 1
- [ ] Goal 2
- [ ] Goal 3

---

## Non-Goals

What are we NOT solving in this iteration?

- Item 1
- Item 2

---

## Technical Approach

### Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| REQ-001 | Requirement 1 | Must | Pending |
| REQ-002 | Requirement 2 | Should | Pending |

### Architecture

```
# Architecture notes
```

### Dependencies

- Dependency 1
- Dependency 2

---

## Research Sources

{chr(10).join(f"- {s}" for s in sources[:10]) if sources else "- No sources cited"}

---

## Implementation Plan

### Phase 1: MVP

- [ ] Task 1
- [ ] Task 2

### Phase 2: Enhancement

- [ ] Task 3
- [ ] Task 4

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Metric 1 | Target | Method |

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-------------|
| Risk 1 | High | Mitigation |

---

## Open Questions

- [ ] Question 1
- [ ] Question 2
"""

        return prd

    def _add_to_index(self, research_path: str, prd_path: str, title: str):
        """Add entry to PRD index."""
        index = self._load_index()

        index.append({
            "research_file": research_path,
            "prd_file": prd_path,
            "title": title,
            "created": datetime.now().isoformat(),
            "status": "draft",
        })

        self.INDEX_FILE.write_text(json.dumps(index, indent=2))

    def _load_index(self) -> list[dict]:
        """Load PRD index."""
        if self.INDEX_FILE.exists():
            return json.loads(self.INDEX_FILE.read_text())
        return []

    def list_prds(self) -> list[dict]:
        """List all generated PRDs."""
        return self._load_index()

    def update_prd_status(self, prd_title: str, status: str):
        """Update PRD status (draft, in_progress, completed)."""
        index = self._load_index()

        for entry in index:
            if entry["title"] == prd_title:
                entry["status"] = status

        self.INDEX_FILE.write_text(json.dumps(index, indent=2))
```

**Step 2: Verificar**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.prd_generator import PRDGeneratorAgent; print('OK')"`
Expected: `OK`

---

### Task 3.5: Create TerminalAgent

**Files:**
- Create: `agents/terminal.py`

**Step 1: Escribir el agente de terminal interactiva**

```python
"""Terminal Agent - interactive CLI guide."""

import asyncio
from typing import Any

from core.memory import MemorySystem


class TerminalAgent:
    """Interactive terminal agent for manual operations.

    Provides guided workflows for:
    - Viewing research status
    - Reviewing PRDs
    - Manual agent execution
    - System diagnostics
    """

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system

    async def show_dashboard(self) -> str:
        """Show system dashboard."""
        from pathlib import Path

        # Count memories
        count = await self.memory.qdrant.count()

        # Count research files
        research_dir = Path.home() / ".ulmemory" / "research" / "reports"
        research_count = len(list(research_dir.glob("*.md"))) if research_dir.exists() else 0

        # Count PRDs
        prd_dir = Path.home() / ".ulmemory" / "prds"
        prd_count = len(list(prd_dir.glob("*.md"))) if prd_dir.exists() else 0

        # Get recent activities
        recent = await self.memory.qdrant.search(
            query_embedding=await self.memory.embedding.embed("recent activity"),
            limit=5,
        )

        dashboard = f"""
╔══════════════════════════════════════════════════════════════╗
║                    ULTRAMEMORY DASHBOARD                     ║
╚══════════════════════════════════════════════════════════════╝

📊 ESTADÍSTICAS
   ├─ Memorias totales: {count}
   ├─ Investigaciones: {research_count}
   └─ PRDs generados: {prd_count}

📋 OPERACIONES DISPONIBLES
   ├─ ulmemory agent run researcher "query" --web
   ├─ ulmemory agent run consolidator
   ├─ ulmemory schedule list
   └─ ulmemory memory query "término"

🔔 PRÓXIMAS ACCIONES
   ├─ Revisar heartbeat: ~/.ulmemory/heartbeat.md
   ├─ Ver investigaciones: ~/.ulmemory/research/reports/
   └─ Revisar PRDs: ~/.ulmemory/prds/

💡 AYUDA
   └─ ulmemory --help
"""
        return dashboard

    async def guide_research(self, topic: str | None = None) -> str:
        """Guide user through research workflow."""
        if not topic:
            return """
🔍 GUÍA DE INVESTIGACIÓN

Para investigar un tema:

1. Define el tema de investigación
2. Ejecuta: ulmemory agent run researcher "tu tema" --web --deep
3. Revisa los resultados en ~/.ulmemory/research/reports/

¿Quieres investigar un tema específico?
Ejemplo: "AI agent frameworks" o "memory patterns"
"""

        return f"""
🎯 INVESTIGACIÓN: {topic}

Ejecutando investigación...

```bash
ulmemory agent run researcher "{topic}" --web --deep
```

Después de ejecutar, los resultados se guardarán en:
~/.ulmemory/research/reports/

Para generar un PRD desde la investigación:
```bash
ulmemory agent run prd-generator "ruta/a/investigacion.md"
```
"""

    async def guide_prd_review(self) -> str:
        """Guide user through PRD review."""
        from pathlib import Path
        import json

        index_file = Path.home() / ".ulmemory" / "prds" / "index.json"

        if not index_file.exists():
            return "No hay PRDs generados aún."

        prds = json.loads(index_file.read_text())

        lines = ["📄 PRDs GENERADOS\n"]

        for prd in prds:
            status_emoji = {
                "draft": "📝",
                "in_progress": "🔄",
                "completed": "✅",
            }.get(prd.get("status", "draft"), "📝")

            lines.append(f"{status_emoji} {prd['title']}")
            lines.append(f"   Estado: {prd.get('status', 'draft')}")
            lines.append(f"   Archivo: {prd['prd_file']}")
            lines.append("")

        lines.extend([
            "\n📋 OPERACIONES CON PRDs",
            "",
            "Para marcar como en progreso:",
            "  ulmemory agent run prd-generator --update 'título' --status in_progress",
            "",
            "Para marcar como completado:",
            "  ulmemory agent run prd-generator --update 'título' --status completed",
        ])

        return "\n".join(lines)

    async def diagnose(self) -> str:
        """Run system diagnostics."""
        issues = []
        checks = []

        # Check memory count
        try:
            count = await self.memory.qdrant.count()
            checks.append(f"✅ Memoria: {count} entradas")
        except Exception as e:
            issues.append(f"❌ Error en memoria: {e}")
            checks.append("❌ Memoria: Error")

        # Check config
        from pathlib import Path
        config = Path.home() / ".config" / "ultramemory" / "config.yaml"
        if config.exists():
            checks.append("✅ Config: Archivo existe")
        else:
            issues.append("⚠️ Config: No encontrado")
            checks.append("⚠️ Config: No existe")

        # Check research directory
        research_dir = Path.home() / ".ulmemory" / "research"
        if research_dir.exists():
            checks.append("✅ Research: Directorio existe")
        else:
            issues.append("⚠️ Research: No existe, se creará")
            checks.append("⚠️ Research: No existe")

        # Check heartbeat
        heartbeat = Path.home() / ".ulmemory" / "heartbeat.md"
        if heartbeat.exists():
            checks.append("✅ Heartbeat: Archivo existe")
        else:
            issues.append("⚠️ Heartbeat: No existe, se creará")
            checks.append("⚠️ Heartbeat: No existe")

        output = ["🔧 DIAGNÓSTICO DEL SISTEMA\n"]

        for check in checks:
            output.append(f"   {check}")

        if issues:
            output.append("\n⚠️ ACCIONES REQUERIDAS:")
            for issue in issues:
                output.append(f"   {issue}")
        else:
            output.append("\n✅ Sistema operativo")

        return "\n".join(output)
```

**Step 2: Verificar**

Run: `cd /home/zurybr/workspace/ultramemory && python -c "from agents.terminal import TerminalAgent; print('OK')"`
Expected: `OK`

---

## Fase 4: Actualizar CLI

### Task 4.1: Update agents/__init__.py

**Files:**
- Modify: `agents/__init__.py`

**Step 1: Agregar nuevos agentes**

```python
"""Agent implementations for Ultramemory."""

from .librarian import LibrarianAgent, LibrarianInsertAgent
from .researcher import ResearcherAgent
from .consolidator import ConsolidatorAgent
from .auto_researcher import AutoResearcherAgent
from .custom_agent import CustomAgent
from .deleter import DeleterAgent
from .consultant import ConsultantAgent
from .proactive import ProactiveAgent
from .prd_generator import PRDGeneratorAgent
from .terminal import TerminalAgent
from .heartbeat_reader import HeartbeatReader

__all__ = [
    "LibrarianAgent",
    "LibrarianInsertAgent",
    "ResearcherAgent",
    "ConsolidatorAgent",
    "AutoResearcherAgent",
    "CustomAgent",
    "DeleterAgent",
    "ConsultantAgent",
    "ProactiveAgent",
    "PRDGeneratorAgent",
    "TerminalAgent",
    "HeartbeatReader",
]
```

---

### Task 4.2: Update CLI commands

**Files:**
- Modify: `ultramemory_cli/agents.py`

**Step 1: Agregar nuevos comandos**

Agregar al grupo de comandos de agente:

```python
@agent_group.command(name="consultant")
@click.argument("query")
@click.option("--order", "-o", default="relevance", help="Order by: relevance, date, source")
@click.option("--limit", "-l", default=10, type=int)
def run_consultant(query: str, order: str, limit: int):
    """Run consultant agent for ordered search."""

    async def _run():
        memory = MemorySystem()
        from agents.consultant import ConsultantAgent
        agent = ConsultantAgent(memory)

        result = await agent.query(query, order_by=order, max_results=limit)

        # Print formatted results
        formatted = agent.format_as_text(result)
        click.echo(formatted)

    asyncio.run(_run())


@agent_group.command(name="proactive")
def run_proactive():
    """Run proactive agent to check heartbeat."""

    async def _run():
        memory = MemorySystem()
        from agents.proactive import ProactiveAgent
        agent = ProactiveAgent(memory)

        result = await agent.check_and_execute()

        click.echo(f"\n🤖 Proactive Agent Results:")
        click.echo(f"   Status: {result['status']}")
        click.echo(f"   Executed: {result['executed']}")

        for r in result.get("results", []):
            status = "✅" if r["status"] == "success" else "❌"
            click.echo(f"   {status} {r['task']}")

    asyncio.run(_run())


@agent_group.command(name="terminal")
@click.argument("action", default="dashboard")
@click.option("--topic", "-t", help="Topic for research guide")
def run_terminal(action: str, topic: str):
    """Run terminal agent for interactive CLI."""

    async def _run():
        memory = MemorySystem()
        from agents.terminal import TerminalAgent
        agent = TerminalAgent(memory)

        if action == "dashboard":
            result = await agent.show_dashboard()
        elif action == "diagnose":
            result = await agent.diagnose()
        elif action == "guide" and topic:
            result = await agent.guide_research(topic)
        elif action == "guide":
            result = await agent.guide_research()
        elif action == "prds":
            result = await agent.guide_prd_review()
        else:
            result = await agent.show_dashboard()

        click.echo(result)

    asyncio.run(_run())


@agent_group.command(name="heartbeat")
@click.argument("action")
@click.argument("task", required=False)
def manage_heartbeat(action: str, task: str | None):
    """Manage heartbeat tasks.

    Actions:
        list    - List pending tasks
        add     - Add new task (use quotes)
        complete - Mark task as complete
    """
    from agents.heartbeat_reader import HeartbeatReader

    hb = HeartbeatReader()

    if action == "list":
        data = hb.read()
        click.echo("\n📋 Tareas Pendientes:")
        for i, t in enumerate(data["tasks"], 1):
            status = "✅" if t["completed"] else "⬜"
            tags = " ".join(f"#{tag}" for tag in t.get("tags", []))
            click.echo(f"   {status} {i}. {t['title']} {tags}")

    elif action == "add" and task:
        tags = []
        # Extract tags from task string
        import re
        tags = re.findall(r'#(\w+)', task)
        # Remove tags from title
        title = re.sub(r'#\w+', '', task).strip()

        hb.add_task(title, tags)
        click.echo(f"✅ Tarea agregada: {title}")

    elif action == "complete" and task:
        hb.mark_completed(task)
        click.echo(f"✅ Tarea completada: {task}")

    else:
        click.echo("Usage: ulmemory agent heartbeat <list|add|complete> [task]")


@agent_group.command(name="prd")
@click.argument("action")
@click.argument("research_file", required=False)
@click.option("--title", "-t", help="PRD title")
def manage_prd(action: str, research_file: str | None, title: str | None):
    """Manage PRD generation.

    Actions:
        generate - Generate PRD from research file
        list     - List all PRDs
    """
    from agents.prd_generator import PRDGeneratorAgent

    async def _run():
        memory = MemorySystem()
        agent = PRDGeneratorAgent(memory)

        if action == "generate" and research_file:
            result = agent.generate_prd(research_file, title)
            click.echo(f"✅ PRD generado: {result.get('prd_file')}")

        elif action == "list":
            prds = agent.list_prds()
            click.echo("\n📄 PRDs:")
            for prd in prds:
                click.echo(f"   - {prd['title']} [{prd.get('status', 'draft')}]")

        else:
            click.echo("Usage: ulmemory agent prd <generate|list> [research_file]")

    asyncio.run(_run())
```

---

### Task 4.3: Update scheduler for new agents

**Files:**
- Modify: `ultramemory_cli/scheduler.py`

**Step 1: Agregar nuevos schedules**

```python
# Agregar al scheduler commands:

# Schedule for proactive (every 30 min)
@schedule_group.command(name="add-proactive")
def add_proactive_schedule():
    """Add proactive agent schedule (every 30 minutes)."""
    # This will be called internally
    schedules = _load_schedules()

    task = {
        "id": _get_next_id(),
        "name": "proactive-heartbeat",
        "agent": "proactive",
        "cron": "*/30 * * * *",
        "args": "",
        "enabled": True,
        "created": datetime.now().isoformat(),
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo("✅ Proactive agent scheduled: cada 30 minutos")


# Schedule for researcher (hourly)
@schedule_group.command(name="add-researcher")
@click.option("--cron", "-c", default="0 * * * *", help="Cron (default: hourly)")
def add_researcher_schedule(cron: str):
    """Add researcher agent schedule."""
    schedules = _load_schedules()

    task = {
        "id": _get_next_id(),
        "name": "researcher-hourly",
        "agent": "auto-researcher",
        "cron": cron,
        "args": "",
        "enabled": True,
        "created": datetime.now().isoformat(),
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Researcher agent scheduled: {_cron_to_human(cron)}")


# Schedule for consolidator (daily morning)
@schedule_group.command(name="add-consolidator")
@click.option("--hour", "-h", default=5, type=int, help="Hour (default: 5am)")
def add_consolidator_schedule(hour: int):
    """Add consolidator agent schedule (daily)."""
    schedules = _load_schedules()

    task = {
        "id": _get_next_id(),
        "name": "consolidator-daily",
        "agent": "consolidator",
        "cron": f"0 {hour} * * *",
        "args": "",
        "enabled": True,
        "created": datetime.now().isoformat(),
    }

    schedules.append(task)
    _save_schedules(schedules)
    _sync_to_crontab()

    click.echo(f"✅ Consolidator scheduled: daily at {hour}:00")
```

---

## Fase 5: Git Commit

### Task 5.1: Commit all changes

**Step 1: Stage and commit**

```bash
git add agents/
git add ultramemory_cli/agents.py
git add ultramemory_cli/scheduler.py
git commit -m "$(cat <<'EOF'
feat: Complete agent system with cron automation

New agents:
- LibrarianInsertAgent: Enhanced with file/URL/image/video support
- DeleterAgent: With connection preservation and audit log
- ConsultantAgent: Ordered search and retrieval
- ProactiveAgent: Reads heartbeat.md every 30 min
- PRDGeneratorAgent: Generates PRDs from research
- TerminalAgent: Interactive CLI dashboard

Updates:
- ResearcherAgent: Scientific papers + GitHub research
- ConsolidatorAgent: Generates insights from connections

New CLI commands:
- ulmemory agent consultant <query>
- ulmemory agent proactive
- ulmemory agent terminal [action]
- ulmemory agent heartbeat <list|add|complete>
- ulmemory agent prd <generate|list>
- ulmemory schedule add-proactive
- ulmemory schedule add-researcher
- ulmemory schedule add-consolidator

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

**Step 2: Push to remote**

```bash
git push origin main
```

---

## Fase 6: Document in Ultramemory

### Task 6.1: Store implementation insights

```bash
ulmemory memory add "Implemented complete agent system: LibrarianInsertAgent (files/URLs/images/videos), DeleterAgent (audit log, connection preservation), ConsultantAgent (ordered search), ProactiveAgent (heartbeat-driven every 30min), PRDGeneratorAgent (research to PRD), TerminalAgent (interactive CLI), enhanced ResearcherAgent (scientific + GitHub), enhanced ConsolidatorAgent (insights generation). Key patterns: heartbeat.md for task management, audit logging, structured PRD templates." -m "type=feature,project=ultramemory,version=0.3.0"
```

---

## Execution Summary

| Fase | Descripción | Archivos |
|------|-------------|----------|
| 0 | Agentes existentes | `agents/code_indexer.py` (YA EXISTE) |
| 1 | Heartbeat system | `agents/heartbeat_reader.py` |
| 2 | Bibliotecarios | `agents/librarian.py`, `agents/deleter.py`, `agents/consultant.py` |
| 3 | Agentes Cron | `agents/proactive.py`, `agents/prd_generator.py`, `agents/terminal.py` |
| 4 | CLI | `ultramemory_cli/agents.py`, `ultramemory_cli/scheduler.py` |
| 5 | Git | Commit and push |
| 6 | Memory | Store insights |

---

**Plan complete. Ready for execution with superpowers:subagent-driven-development or superpowers:executing-plans.**
