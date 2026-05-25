"""Stable id and slug builders for graph nodes.

Every node id is deterministic so re-runs of the pipeline merge cleanly
instead of duplicating. Slugs are URL-safe and are used as filenames in the
markdown wiki vault.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Optional


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_LEADING_TRAIL_DASH = re.compile(r"^-+|-+$")


def canonical_slug(text: str, *, max_len: int = 80) -> str:
    """Produce a stable, lowercase, dash-separated slug.

    >>> canonical_slug("FastAPI for ML")
    'fastapi-for-ml'
    """
    if not text:
        return "untitled"
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = _SLUG_RE.sub("-", norm)
    norm = _LEADING_TRAIL_DASH.sub("", norm)
    if len(norm) > max_len:
        norm = norm[:max_len].rstrip("-")
    return norm or "untitled"


def canonical_concept(name: str) -> str:
    """Canonicalize a concept / skill / technology name.

    Lowercased, alphanumerics + dashes only. Used as the primary key for
    skill/technology/concept entity resolution. Aliases (e.g. fast-api ->
    fastapi) should be resolved by ``concept_resolver`` before this is called.
    """
    return canonical_slug(name)


def _short_hash(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"|")
    return h.hexdigest()[:10]


# ── id builders ───────────────────────────────────────────────────────────

def repo_id(owner: str, name: str) -> str:
    return f"repo:{owner}/{name}"


def file_id(repo: str, path: str, rev: Optional[str] = None) -> str:
    base = f"file:{repo}/{path.lstrip('/')}"
    if rev:
        return f"{base}@{rev[:10]}"
    return base


def function_id(repo: str, path: str, qualname: str) -> str:
    return f"fn:{repo}/{path.lstrip('/')}::{qualname}"


def class_id(repo: str, path: str, qualname: str) -> str:
    return f"cls:{repo}/{path.lstrip('/')}::{qualname}"


def skill_id(name: str) -> str:
    return f"skill:{canonical_concept(name)}"


def technology_id(name: str) -> str:
    return f"tech:{canonical_concept(name)}"


def concept_id(name: str) -> str:
    return f"concept:{canonical_concept(name)}"


def domain_id(name: str) -> str:
    return f"domain:{canonical_concept(name)}"


def deployment_id(provider: str, project: str, ident: Optional[str] = None) -> str:
    parts = [provider, canonical_concept(project)]
    if ident:
        parts.append(ident)
    return "dep:" + "/".join(parts)


def commit_id(repo: str, sha: str) -> str:
    return f"commit:{repo}@{sha[:10]}"


def document_id(repo: str, path: str) -> str:
    return f"doc:{repo}/{path.lstrip('/')}"


def section_id(doc: str, heading: str) -> str:
    return f"sec:{doc}#{canonical_slug(heading)}"


def conversation_id(provider: str, ident: str) -> str:
    return f"conv:{provider}/{ident}"


def person_id(login_or_email: str) -> str:
    if "@" in login_or_email:
        # privacy: hash emails
        return f"person:eh-{_short_hash(login_or_email.lower())}"
    return f"person:{login_or_email.lower()}"
