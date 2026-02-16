"""Code Indexer Agent - indexes GitHub repositories into memory."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.github_client import GitHubClient, get_language
from core.memory import MemorySystem
from agents.tools.codewiki_tool import CodeWikiTool


CATEGORY_VALID = {"lefarma", "e6labs", "personal", "opensource", "hobby", "trabajo", "dependencias"}
CONTENT_TYPE_CODE = "code"


class CodeIndexerAgent:
    """Agent for indexing GitHub repositories into memory."""

    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.github = GitHubClient()
        self.codewiki = CodeWikiTool()

    async def index(
        self,
        repo_url: str,
        category: str | None = None,
        force: bool = False,
        exclude_patterns: list[str] | None = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """Index a GitHub repository.

        Args:
            repo_url: GitHub repository URL or owner/repo
            category: Repository category
            force: Force re-index of all files
            exclude_patterns: Additional exclude patterns
            limit: Max files to index per run

        Returns:
            Dictionary with indexing results
        """
        # Parse and validate category
        owner, repo_name = self.github.parse_repo_url(repo_url)
        repo_full_name = f"{owner}/{repo_name}"

        if category is None:
            category = "personal"
        category = category.lower()
        if category not in CATEGORY_VALID:
            raise ValueError(f"Invalid category: {category}. Must be one of: {CATEGORY_VALID}")

        # Clone repository
        repo_dir = self.github.clone_repo(repo_url)

        try:
            # Get repo info
            repo_info = self.github.get_repo_info(repo_url)
            current_commit, current_date = self.github.get_current_commit(repo_dir)

            # Get CodeWiki info for public repos
            codewiki_info = None
            if self.github.is_public_repo(repo_url):
                codewiki_info = await self._get_codewiki_info(repo_full_name)

            # Get file list
            files = self.github.get_file_list(repo_dir, exclude_patterns)

            # Limit files
            files = files[:limit]

            # Index files
            indexed = 0
            skipped = 0
            errors = []

            for file_path in files:
                try:
                    result = await self._index_single_file(
                        file_path=file_path,
                        repo_dir=repo_dir,
                        owner=owner,
                        repo_name=repo_name,
                        repo_url=repo_info.get("url", f"https://github.com/{repo_full_name}"),
                        category=category,
                        force=force,
                        current_commit=current_commit,
                        current_date=current_date
                    )
                    if result.get("indexed"):
                        indexed += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append({"file": str(file_path), "error": str(e)})

            return {
                "status": "success",
                "repo": repo_full_name,
                "category": category,
                "files_indexed": indexed,
                "files_skipped": skipped,
                "total_files": len(files),
                "errors": errors,
                "codewiki_available": codewiki_info is not None
            }

        finally:
            self.github.cleanup(repo_dir)

    async def _index_single_file(
        self,
        file_path: Path,
        repo_dir: Path,
        owner: str,
        repo_name: str,
        repo_url: str,
        category: str,
        force: bool,
        current_commit: str,
        current_date: str
    ) -> dict[str, Any]:
        """Index a single file.

        Args:
            file_path: Path to file
            repo_dir: Repository directory
            owner: Repository owner
            repo_name: Repository name
            repo_url: Repository URL
            category: Repository category
            force: Force re-index
            current_commit: Current HEAD commit
            current_date: Current HEAD date

        Returns:
            Dictionary with result
        """
        # Get file content
        content = self.github.get_file_content(file_path)
        file_rel_path = file_path.relative_to(repo_dir)

        # Get file-specific commit history
        file_history = self.github.get_file_history(repo_dir, file_rel_path)

        # Check if already indexed (incremental update)
        if not force:
            is_indexed, existing_doc_id = await self._check_if_indexed(
                owner, repo_name, str(file_rel_path)
            )
            if is_indexed and existing_doc_id:
                # Check if file has changed
                existing_commit = await self._get_indexed_commit(existing_doc_id)
                if existing_commit == file_history.get("sha"):
                    return {"indexed": False, "reason": "unchanged"}

                # Update existing
                await self._update_indexed_file(
                    existing_doc_id, content, file_history, current_commit, current_date
                )
                return {"indexed": True, "action": "updated"}

        # Create metadata
        metadata = {
            "content_type": CONTENT_TYPE_CODE,
            "repo_owner": owner,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "file_path": str(file_rel_path),
            "file_extension": file_path.suffix,
            "file_language": get_language(file_path),
            "commit_sha": current_commit,
            "commit_date": current_date,
            "last_modified_commit": file_history.get("sha"),
            "last_modified_date": file_history.get("date"),
            "last_modified_author": file_history.get("author"),
            "category": category,
            "indexed_at": datetime.now(timezone.utc).isoformat()
        }

        # Add to memory
        doc_id = await self.memory.add(content, metadata)

        return {"indexed": True, "action": "created", "doc_id": doc_id}

    async def _check_if_indexed(
        self,
        owner: str,
        repo_name: str,
        file_path: str
    ) -> tuple[bool, str | None]:
        """Check if file is already indexed.

        Args:
            owner: Repository owner
            repo_name: Repository name
            file_path: File path

        Returns:
            Tuple of (is_indexed, doc_id or None)
        """
        # Query for existing entries with same repo and file path
        results = await self.memory.query(
            f"repo_owner:{owner} repo_name:{repo_name} file_path:{file_path}",
            limit=10
        )

        for result in results.get("vector_results", []):
            meta = result.get("metadata", {})
            if (meta.get("repo_owner") == owner and
                meta.get("repo_name") == repo_name and
                meta.get("file_path") == file_path):
                return True, result.get("id")

        return False, None

    async def _get_indexed_commit(self, doc_id: str) -> str | None:
        """Get the commit SHA of an indexed file.

        Args:
            doc_id: Document ID

        Returns:
            Commit SHA or None
        """
        # This would need to fetch the document by ID
        # For now, we'll do a query to find it
        results = await self.memory.query(f"id:{doc_id}", limit=1)
        for result in results.get("vector_results", []):
            if result.get("id") == doc_id:
                return result.get("metadata", {}).get("last_modified_commit")
        return None

    async def _update_indexed_file(
        self,
        doc_id: str,
        content: str,
        file_history: dict,
        current_commit: str,
        current_date: str
    ) -> dict[str, Any]:
        """Update an indexed file.

        Args:
            doc_id: Document ID to update
            content: New content
            file_history: New file history
            current_commit: Current HEAD commit
            current_date: Current HEAD date

        Returns:
            Update result
        """
        # Delete old entry
        await self.memory.qdrant.delete(doc_id)

        # Create new metadata
        metadata = {
            "last_modified_commit": file_history.get("sha"),
            "last_modified_date": file_history.get("date"),
            "last_modified_author": file_history.get("author"),
            "commit_sha": current_commit,
            "commit_date": current_date,
            "indexed_at": datetime.now(timezone.utc).isoformat()
        }

        # Add new entry with updated metadata
        new_doc_id = await self.memory.add(content, metadata)

        return {"updated": True, "old_id": doc_id, "new_id": new_doc_id}

    async def _get_codewiki_info(self, repo: str) -> dict[str, Any] | None:
        """Get CodeWiki info for a public repository.

        Args:
            repo: Repository in format owner/repo

        Returns:
            CodeWiki info or None
        """
        try:
            result = await self.codewiki.execute(action="info", repo=repo)
            if result.success:
                return result.data
        except Exception:
            pass
        return None


class CategoryManager:
    """Manages repository category preferences."""

    SETTINGS_KEY = "github_categories"

    def __init__(self, settings_obj):
        self.settings = settings_obj

    def get_category(self, repo_full_name: str) -> str | None:
        """Get category for a repository.

        Args:
            repo_full_name: Repository in format owner/repo

        Returns:
            Category or None
        """
        categories = self.settings.get(self.SETTINGS_KEY, {})

        # Exact match
        if repo_full_name in categories:
            return categories[repo_full_name]

        # Owner default
        owner = repo_full_name.split("/")[0]
        if owner in categories:
            return categories[owner]

        # Default global
        if "*" in categories:
            return categories["*"]

        return None

    def set_category(self, repo_full_name: str, category: str) -> None:
        """Set category for a repository.

        Args:
            repo_full_name: Repository in format owner/repo
            category: Category name
        """
        categories = self.settings.get(self.SETTINGS_KEY, {})
        categories[repo_full_name] = category
        self.settings.set(self.SETTINGS_KEY, categories)
        self.settings.save()

    def set_owner_default(self, owner: str, category: str) -> None:
        """Set default category for all repos of an owner.

        Args:
            owner: Repository owner
            category: Category name
        """
        categories = self.settings.get(self.SETTINGS_KEY, {})
        categories[owner] = category
        self.settings.set(self.SETTINGS_KEY, categories)
        self.settings.save()

    def set_global_default(self, category: str) -> None:
        """Set global default category.

        Args:
            category: Category name
        """
        categories = self.settings.get(self.SETTINGS_KEY, {})
        categories["*"] = category
        self.settings.set(self.SETTINGS_KEY, categories)
        self.settings.save()
