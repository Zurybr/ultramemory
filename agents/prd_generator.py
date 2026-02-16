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
