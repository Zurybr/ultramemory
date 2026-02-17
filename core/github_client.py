"""GitHub client utilities for code indexing."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


# Supported file extensions - ALL programming languages and text files
# Index any file that is text/plain (not binary)
SUPPORTED_EXTENSIONS = {
    # Python
    ".py", ".pyw", ".pyi",
    # JavaScript/TypeScript
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts",
    # Java/Kotlin
    ".java", ".kt", ".kts", ".scala", ".groovy",
    # C/C++
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx",
    # C#
    ".cs", ".csx",
    # Go
    ".go",
    # Rust
    ".rs",
    # Ruby
    ".rb", ".erb", ".rake",
    # PHP
    ".php", ".phtml",
    # Swift
    ".swift",
    # Shell
    ".sh", ".bash", ".zsh", ".fish",
    # SQL
    ".sql",
    # Data/Config
    ".yaml", ".yml", ".json", ".toml", ".xml", ".ini", ".cfg", ".conf",
    # Web
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    # Markdown/Docs
    ".md", ".markdown", ".txt", ".rst",
    # Visual Basic / VB6
    ".vb", ".cls", ".frm", ".bas", ".mod",
    ".dsr", ".dca", ".dsx",  # VB6 Data Report
    ".vbp", ".vbg", ".vbw",  # VB6 Project
    ".ocx",  # VB6 ActiveX Controls
    ".OBJ",  # VB6 Form compiled binary (contains form data)
    ".frx",  # VB6 Form binary
    # Pascal/Delphi
    ".pas", ".dpk", ".dpr",
    # Other languages
    ".r", ".lua", ".pl", ".pm", ".ex", ".exs", ".erl", ".hs",
    ".ml", ".fs", ".fsx", ".clj", ".cljs", ".dart", ".elm",
    ".vue", ".svelte", ".jsx",
    # Scripts
    ".ps1", ".psm1", ".bat", ".cmd", ".awk",
    # Build files
    ".gradle", ".maven", ".cmake", ".make", ".dockerfile",
    # Data files
    ".csv", ".tsv", ".parquet",
    # Other
    ".env", ".gitignore", ".dockerignore",
    # Legacy/Enterprise
    ".adb", ".ads",  # Ada
    ".asm", ".s",  # Assembly
    ".m", ".mm", ".h",  # Objective-C
    ".f", ".f90", ".f95",  # Fortran
    ".cob", ".cbl",  # COBOL
    ".ada",  # Ada
    ".pro",  # Prolog
    ".mup",  # MuPAD
    ".sci", ".sce",  # Scilab
    ".jl",  # Julia
    ".nim",  # Nim
    ".zig",  # Zig
    ".v",  # Verilog
    ".sv",  # SystemVerilog
    ".vhdl",  # VHDL
}

# Language mapping
EXTENSION_TO_LANGUAGE = {
    ".py": "Python", ".pyw": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".mts": "TypeScript", ".cts": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".scala": "Scala", ".groovy": "Groovy",
    ".c": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".h": "C/C++ Header", ".hpp": "C++ Header",
    ".cs": "C#", ".csx": "C# Script",
    ".go": "Go", ".rs": "Rust",
    ".rb": "Ruby", ".erb": "Ruby", ".rake": "Rake",
    ".php": "PHP", ".phtml": "PHP",
    ".swift": "Swift",
    ".sh": "Shell", ".bash": "Bash", ".zsh": "Zsh", ".fish": "Fish",
    ".sql": "SQL",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".toml": "TOML", ".xml": "XML", ".ini": "INI",
    ".cfg": "Config", ".conf": "Config",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".md": "Markdown", ".markdown": "Markdown",
    ".txt": "Text", ".rst": "reStructuredText",
    ".vb": "Visual Basic", ".cls": "VB Class", ".frm": "VB Form", ".bas": "VB Module", ".mod": "VB Module",
    ".dsr": "VB Data Report", ".dca": "VB Data Report", ".dsx": "VB Data Report",
    ".vbp": "VB Project", ".vbg": "VB Project Group", ".vbw": "VB Workspace",
    ".ocx": "VB ActiveX Control",
    ".OBJ": "VB6 Form Binary", ".frx": "VB6 Form Binary",
    ".pas": "Pascal", ".dpk": "Delphi Package", ".dpr": "Delphi Project",
    # Legacy/Enterprise languages
    ".adb": "Ada", ".ads": "Ada", ".ada": "Ada",
    ".asm": "Assembly", ".s": "Assembly",
    ".m": "Objective-C", ".mm": "Objective-C",
    ".f": "Fortran", ".f90": "Fortran", ".f95": "Fortran",
    ".cob": "COBOL", ".cbl": "COBOL",
    ".pro": "Prolog",
    ".mup": "MuPAD",
    ".sci": "Scilab", ".sce": "Scilab",
    ".jl": "Julia",
    ".nim": "Nim",
    ".v": "Verilog", ".sv": "SystemVerilog",
    ".vhdl": "VHDL",
    ".r": "R", ".lua": "Lua", ".pl": "Perl", ".pm": "Perl Module",
    ".ex": "Elixir", ".exs": "Elixir",
    ".erl": "Erlang", ".hs": "Haskell",
    ".ml": "OCaml", ".fs": "F#", ".fsx": "F# Script",
    ".clj": "Clojure", ".cljs": "ClojureScript",
    ".dart": "Dart", ".elm": "Elm",
    ".vue": "Vue", ".svelte": "Svelte",
    ".ps1": "PowerShell", ".psm1": "PowerShell Module",
    ".bat": "Batch", ".cmd": "Batch", ".awk": "AWK",
    ".gradle": "Gradle", ".maven": "Maven", ".cmake": "CMake",
    ".make": "Make", ".dockerfile": "Dockerfile",
    ".csv": "CSV", ".tsv": "TSV", ".parquet": "Parquet",
    ".env": "Env", ".gitignore": "Git Ignore",
    ".dockerignore": "Docker Ignore"
}

# Default exclude patterns
DEFAULT_EXCLUDES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "target", ".pytest_cache",
    ".mypy_cache", ".tox", ".eggs", "*.egg-info", ".DS_Store",
    ".idea", ".vscode", "vendor", "bin", "obj",
    # Only exclude log files, NOT OBJ/frx which contain VB6 form data
    "log"
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

    def get_file_content(self, file_path: Path | str) -> str:
        """Read file content.

        Args:
            file_path: Path to file (can be Path or str)

        Returns:
            File content as string
        """
        # Convert to Path if string
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path

        with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Filter binary content for VB6 files
        if path_obj.suffix.lower() in {".frm", ".dsr", ".dca", ".dsx"}:
            content = self._filter_vb6_binary_content(content)

        return content

    def _filter_vb6_binary_content(self, content: str) -> str:
        """Filter binary content from VB6 files.

        VB6 files (.frm, .dsr, .dca, .dsx) contain embedded binary data
        that interferes with semantic search. This method extracts
        only the readable VB6 source code.

        Args:
            content: Raw file content

        Returns:
            Filtered content with only readable VB6 code
        """
        import re

        lines = content.split('\n')
        filtered_lines = []

        for line in lines:
            # Remove all non-ASCII characters completely
            ascii_only = ''.join(c for c in line if ord(c) < 128)

            # Skip empty lines
            if not ascii_only.strip():
                continue

            # Skip lines that are now empty after removing non-ASCII
            if len(ascii_only.strip()) == 0:
                continue

            # Keep only lines that are valid VB6 code patterns
            # VB6 forms: VERSION, Begin VB.Form, Begin {GUID}
            # VB properties: PropertyName = Value
            # VB code: Private Sub, Public Function, etc.
            if (ascii_only.startswith('VERSION') or
                ascii_only.startswith('Begin VB.') or
                ascii_only.startswith('Begin {') or
                ascii_only.startswith('End') or
                ascii_only.startswith('Attribute') or
                ascii_only.startswith('Option ') or
                ascii_only.startswith('Private ') or
                ascii_only.startswith('Public ') or
                ascii_only.startswith('EndProperty') or
                ascii_only.startswith('BeginProperty') or
                # Property assignments like "Caption = " or "Height = "
                re.match(r'^\s+\w+\s*=\s*.', ascii_only) or
                # GUID patterns like "{78E93846-85FD-11D0-8487-00A0C90DC8A9}"
                re.match(r'^\s*\{[\w-]+\}', ascii_only)):
                filtered_lines.append(ascii_only)

        # If we filtered too much (less than 3 lines), extract form metadata
        if len(filtered_lines) < 3:
            metadata_lines = []
            for line in lines:
                ascii_only = ''.join(c for c in line if ord(c) < 128)
                if ascii_only.strip() and (
                    'Caption' in ascii_only or
                    'Height' in ascii_only or
                    'Width' in ascii_only or
                    'Top' in ascii_only or
                    'Left' in ascii_only or
                    'TabIndex' in ascii_only
                ):
                    metadata_lines.append(ascii_only)
            filtered_lines = metadata_lines[:20]  # Limit to 20 metadata lines

        return '\n'.join(filtered_lines)

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
