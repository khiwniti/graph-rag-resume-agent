"""Shared filesystem walker that skips vendored / build / VCS noise.

`rglob("*")` over a 1 GB repo with a checked-in `node_modules` or
sibling project takes minutes and OOMs. This walker uses ``os.scandir`` and
prunes whole directories before descending.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Iterator, Optional


# Directories we never want to descend into.
SKIP_DIRS: frozenset[str] = frozenset({
    # VCS
    ".git", ".hg", ".svn",
    # Python
    "__pycache__", ".venv", "venv", "env", ".env", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "site-packages", "egg-info",
    # JS/TS
    "node_modules", ".next", ".nuxt", ".turbo", ".output", ".svelte-kit",
    ".parcel-cache", ".vite", "out",
    # Build artifacts
    "dist", "build", "bin", "obj", "target", ".gradle", ".cache",
    "coverage", ".coverage", "htmlcov",
    # Editors / OS
    ".idea", ".vscode", ".DS_Store",
    # Common large bundled assets
    "vendor", "third_party", "third-party",
    # Lock-step duplicates / submodules of own work
    "checkpoints", "wandb", "mlruns",
    # Vendored copies of other projects (Suna, etc.) and backups
    "suna", "suna-init", "suna-backup", "suna-init-backup",
    # Nested clones of common upstream projects checked into the repo
    "supabase", "frontend-build", "android-build", "ios-build",
    "pods", "Pods", "Carthage", "DerivedData",
    # ML / data dumps
    "datasets", "data_cache", "models_cache", ".huggingface",
})


# Files larger than this are skipped entirely by AST/regex extractors —
# protects against single 5MB Python files that take minutes to parse.
MAX_FILE_BYTES = 200_000


def looks_like_backup_dir(name: str) -> bool:
    """Match patterns like ``suna-init-backup-20260327-082403`` or ``-old``."""
    lower = name.lower()
    return (
        "-backup-" in lower
        or lower.endswith(("-backup", "-old", "-bak", ".bak", "-copy"))
    )

# Skip individual files (not dirs).
SKIP_FILE_NAMES: frozenset[str] = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "Cargo.lock", "go.sum",
})

# Hard cap on how many files of any kind we'll even consider.
DEFAULT_MAX_VISIT = 5000


def iter_files(
    root: str | Path,
    *,
    extensions: Optional[Iterable[str]] = None,
    max_visit: int = DEFAULT_MAX_VISIT,
    follow_symlinks: bool = False,
) -> Iterator[Path]:
    """Yield files under ``root`` in BFS order, skipping noise directories.

    Parameters
    ----------
    extensions : iterable of suffixes (lowercase, with leading dot, e.g. ``.py``)
                 If provided, only files with these suffixes are yielded.
    max_visit  : hard cap on files visited (NOT yielded). Stops the walk to
                 protect against runaway repos.
    """
    root = Path(root)
    if not root.is_dir():
        return

    ext_set: Optional[frozenset[str]] = (
        frozenset(e.lower() for e in extensions) if extensions else None
    )

    visited = 0
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    visited += 1
                    if visited > max_visit:
                        return
                    name = entry.name
                    if name.startswith(".") and name not in (".github",):
                        # allow .github (CI/docs) but skip dotfiles by default
                        if name in SKIP_DIRS:
                            continue
                        if name not in (".github",):
                            continue
                    if entry.is_dir(follow_symlinks=follow_symlinks):
                        if name in SKIP_DIRS:
                            continue
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=follow_symlinks):
                        if name in SKIP_FILE_NAMES:
                            continue
                        if ext_set is not None:
                            sfx = os.path.splitext(name)[1].lower()
                            if sfx not in ext_set:
                                continue
                        yield Path(entry.path)
        except (PermissionError, OSError):
            continue
