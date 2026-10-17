"""Collect a compact, LLM-friendly snapshot of a repository (or a single file)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    ".idea", ".vscode", ".mypy_cache", ".pytest_cache", ".tox", "target", ".next",
}
IGNORED_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf", ".zip",
    ".gz", ".tar", ".7z", ".mp3", ".mp4", ".mov", ".woff", ".woff2", ".ttf",
    ".eot", ".pyc", ".so", ".dll", ".exe", ".bin", ".lock", ".min.js", ".map",
    # secrets: never leave the machine
    ".pem", ".key", ".p12", ".pfx",
)
IGNORED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".DS_Store", "id_rsa", "id_ed25519",
}
PRIORITY_NAMES = {
    "readme.md", "readme", "pyproject.toml", "package.json", "cargo.toml", "go.mod",
    "requirements.txt", "setup.py", "makefile", "dockerfile", "docker-compose.yml",
    "main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs", "lib.rs",
}
MAX_TREE_LINES = 300


@dataclass
class Snapshot:
    name: str
    paths: list[str]
    files: list[tuple[str, str]]  # (relative path, content)
    skipped: int

    @property
    def chars(self) -> int:
        return sum(len(content) for _, content in self.files)

    def render(self) -> str:
        parts = [f"Repository: {self.name}", "", "File list:"]
        parts += self.paths[:MAX_TREE_LINES]
        if len(self.paths) > MAX_TREE_LINES:
            parts.append(f"... (+{len(self.paths) - MAX_TREE_LINES} more files)")
        parts.append("")
        for rel, content in self.files:
            parts.append(f'<file path="{rel}">\n{content}\n</file>')
        return "\n".join(parts)


def _is_secret_or_ignored(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1]
    if any(p in IGNORED_DIRS or p.endswith(".egg-info") for p in parts[:-1]):
        return True
    if name in IGNORED_NAMES or name.startswith(".env"):
        return True
    return name.lower().endswith(IGNORED_SUFFIXES)


def _is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"\0" in fh.read(2048)
    except OSError:
        return True


def _git_files(root: Path) -> list[str] | None:
    """Use git so .gitignore is respected. Returns None if root isn't a git repo."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return [line for line in out.stdout.splitlines() if line]


def _walk_files(root: Path) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            rel = os.path.relpath(os.path.join(dirpath, filename), root)
            found.append(Path(rel).as_posix())
    return found


def _read(path: Path, limit: int) -> str:
    with open(path, "rb") as fh:
        return fh.read(limit).decode("utf-8", errors="replace")


def collect(root: Path, max_chars: int = 60_000) -> Snapshot:
    root = Path(root)
    candidates = _git_files(root)
    if candidates is None:
        candidates = _walk_files(root)

    kept = []
    for rel in candidates:
        full = root / rel
        if _is_secret_or_ignored(rel) or not full.is_file() or _is_binary(full):
            continue
        kept.append((rel, full.stat().st_size))

    def priority(item):
        rel, size = item
        name = rel.rsplit("/", 1)[-1].lower()
        return (0 if name in PRIORITY_NAMES else 1, rel.count("/"), size)

    kept.sort(key=priority)

    files, skipped, remaining = [], 0, max_chars
    for rel, _ in kept:
        if remaining < 500:
            skipped += 1
            continue
        content = _read(root / rel, remaining)
        files.append((rel, content))
        remaining -= len(content)

    paths = sorted(rel for rel, _ in kept)
    return Snapshot(name=root.resolve().name, paths=paths, files=files, skipped=skipped)


def collect_file(path: Path, max_chars: int = 60_000) -> Snapshot:
    path = Path(path)
    if _is_binary(path):
        raise OSError(f"{path} looks like a binary file")
    content = _read(path, max_chars)
    return Snapshot(name=path.name, paths=[path.name], files=[(path.name, content)], skipped=0)
