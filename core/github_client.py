"""GitHub client utilities for code indexing."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb",
    ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".kt", ".scala", ".sql",
    ".sh", ".yaml", ".yml", ".json", ".xml", ".md"
}

# Language mapping
EXTENSION_TO_LANGUAGE = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".jsx": "JavaScript", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".cpp": "C++", ".c": "C", ".h": "C/C++ Header",
    ".swift": "Swift", ".kt": "Kotlin", ".scala": "Scala",
    ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON", ".xml": "XML", ".md": "Markdown"
}

# Default exclude patterns
DEFAULT_EXCLUDES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "target", ".pytest_cache",
    ".mypy_cache", ".tox", ".eggs", "*.egg-info", ".DS_Store",
    ".idea", ".vscode", "vendor", "bin", "obj"
}


class GitHubClient:
    """Client for interacting with GitHub repositories via gh CLI."""

    def __init__(self):
        """Initialize GitHub client."""
        self._verify_gh_installed()
        self._verify_gh_auth()

    def _verify_gh_installed(self):
        """Verify gh CLI is installed."""
        if not shutil.which("gh"):
            raise RuntimeError(
                "Error: gh CLI not found. Please install GitHub CLI first:\n"
                "  macOS: brew install gh\n"
                "  Linux: sudo apt install gh\n"
                "  Windows: winget install GitHub.cli"
            )

    def _verify_gh_auth(self):
        """Verify gh is authenticated."""
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Error: gh not authenticated. Please run:\n"
                "  gh auth login"
            )

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str]:
        """Parse GitHub URL to extract owner and repo.

        Args:
            url: GitHub URL or owner/repo format

        Returns:
            Tuple of (owner, repo_name)

        Examples:
            https://github.com/owner/repo -> ("owner", "repo")
            owner/repo -> ("owner", "repo")
        """
        # Remove .git suffix
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        # Handle owner/repo format
        if "/" in url and not url.startswith("http"):
            parts = url.split("/")
            if len(parts) == 2:
                return parts[0], parts[1]

        # Handle full URL
        patterns = [
            r"github\.com[/:]([^/]+)/([^/]+)",
            r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$"
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(f"Invalid GitHub URL: {url}")

    def clone_repo(self, repo_url: str, target_dir: Path | None = None) -> Path:
        """Clone repository to a temporary directory.

        Args:
            repo_url: GitHub repository URL or owner/repo
            target_dir: Optional target directory (creates temp if not provided)

        Returns:
            Path to cloned repository
        """
        owner, repo = self.parse_repo_url(repo_url)
        repo_target = f"{owner}/{repo}"

        if target_dir is None:
            target_dir = Path(tempfile.mkdtemp(prefix=f"ulmemory-{repo}-"))

        # Clone shallow to save time
        result = subprocess.run(
            ["gh", "repo", "clone", repo_target, str(target_dir)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to clone repo: {result.stderr}")

        return target_dir

    def get_repo_info(self, repo_url: str) -> dict[str, Any]:
        """Get repository metadata via gh API.

        Args:
            repo_url: GitHub repository URL or owner/repo

        Returns:
            Dictionary with repo metadata
        """
        owner, repo = self.parse_repo_url(repo_url)
        repo_target = f"{owner}/{repo}"

        result = subprocess.run(
            ["gh", "api", f"repos/{repo_target}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to get repo info: {result.stderr}")

        data = json.loads(result.stdout)
        return {
            "name": data.get("name"),
            "owner": data.get("owner", {}).get("login"),
            "url": data.get("html_url"),
            "description": data.get("description"),
            "visibility": data.get("visibility"),
            "defaultBranch": data.get("default_branch"),
            "createdAt": data.get("created_at"),
            "updatedAt": data.get("updated_at"),
        }

    def get_current_commit(self, repo_dir: Path) -> tuple[str, str]:
        """Get current HEAD commit SHA and date.

        Args:
            repo_dir: Path to cloned repository

        Returns:
            Tuple of (commit_sha, commit_date ISO format)
        """
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )
        commit_sha = result.stdout.strip()

        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )
        commit_date = result.stdout.strip()

        return commit_sha, commit_date

    def get_file_list(
        self,
        repo_dir: Path,
        exclude_patterns: list[str] | None = None
    ) -> list[Path]:
        """List files in repository matching criteria.

        Args:
            repo_dir: Path to repository
            exclude_patterns: Additional patterns to exclude

        Returns:
            List of file paths
        """
        exclude_set = DEFAULT_EXCLUDES.copy()
        if exclude_patterns:
            exclude_set.update(exclude_patterns)

        files = []
        for file_path in repo_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Check relative path
            rel_path = file_path.relative_to(repo_dir)

            # Skip excluded directories
            if any(part in exclude_set for part in rel_path.parts):
                continue

            # Check extension
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # Skip files > 1MB
            if file_path.stat().st_size > 1024 * 1024:
                continue

            files.append(file_path)

        return files

    def get_file_content(self, file_path: Path) -> str:
        """Read file content.

        Args:
            file_path: Path to file

        Returns:
            File content as string
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def get_file_history(
        self,
        repo_dir: Path,
        file_rel_path: Path
    ) -> dict[str, Any]:
        """Get commit info for specific file.

        Args:
            repo_dir: Path to repository
            file_rel_path: Relative path to file

        Returns:
            Dictionary with last commit info (sha, date, author)
        """
        result = subprocess.run(
            [
                "git", "log", "-1",
                "--format=%H|%cI|%an|%ae",
                "--", str(file_rel_path)
            ],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            return {"sha": None, "date": None, "author": None, "email": None}

        parts = result.stdout.strip().split("|")
        return {
            "sha": parts[0] if len(parts) > 0 else None,
            "date": parts[1] if len(parts) > 1 else None,
            "author": parts[2] if len(parts) > 2 else None,
            "email": parts[3] if len(parts) > 3 else None
        }

    def cleanup(self, repo_dir: Path) -> None:
        """Clean up cloned repository.

        Args:
            repo_dir: Path to repository to remove
        """
        if repo_dir.exists() and repo_dir.parent == tempfile.gettempdir():
            shutil.rmtree(repo_dir, ignore_errors=True)

    def is_public_repo(self, repo_url: str) -> bool:
        """Check if repository is public.

        Args:
            repo_url: GitHub repository URL or owner/repo

        Returns:
            True if public, False if private
        """
        try:
            info = self.get_repo_info(repo_url)
            return info.get("visibility") == "public"
        except Exception:
            return False


def get_language(file_path: Path) -> str:
    """Get programming language from file extension.

    Args:
        file_path: Path to file

    Returns:
        Language name
    """
    return EXTENSION_TO_LANGUAGE.get(file_path.suffix.lower(), "Unknown")
