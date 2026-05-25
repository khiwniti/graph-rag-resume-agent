"""Import evidence-backed profile data (LinkedIn-derived) into Neo4j.

This complements the UniversalGraph importer:
- UniversalGraph -> (Person)-[:HAS_SKILL]->(Skill), (Project)-[:REQUIRES_SKILL]->(Skill)
- This script -> (Person)-[:HAS_ABOUT]->(About), (Person)-[:HAS_CONTACT]->(Contact),
                 (Person)-[:HAS_ROLE]->(Role), (Person)-[:HAS_OSS_PROJECT]->(OssProject)

Safe for Neo4j Aura free tier: small node/edge counts.

Usage:
  python scripts/import_profile_to_neo4j.py --person-id me --person-name "Khiw Nitithadachot"

Requires env:
  NEO4J_URI, NEO4J_USER (or NEO4J_USERNAME), NEO4J_PASSWORD
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from neo4j import GraphDatabase  # type: ignore


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise SystemExit(f"Missing required env var: {name}")
    return v


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_person(tx, person_id: str, person_name: str):
    tx.run(
        """
        MERGE (p:Person {id: $person_id})
        ON CREATE SET p.name = $person_name
        ON MATCH SET p.name = coalesce(p.name, $person_name)
        """,
        person_id=person_id,
        person_name=person_name,
    )


def import_about(tx, person_id: str, about: Dict[str, Any]):
    about_id = f"about:{person_id}"
    tx.run(
        """
        MATCH (p:Person {id: $person_id})
        MERGE (a:About {id: $about_id})
        SET a.headline = $headline,
            a.narrative = $narrative,
            a.source = $source,
            a.evidenceRef = $evidence_ref,
            a.evidenceUrl = $evidence_url
        MERGE (p)-[:HAS_ABOUT]->(a)
        """,
        person_id=person_id,
        about_id=about_id,
        headline=about.get("headline") or "",
        narrative=about.get("narrative") or [],
        source=(about.get("evidence", {}) or {}).get("source") or "",
        evidence_ref=(about.get("evidence", {}) or {}).get("ref") or "",
        evidence_url=(about.get("evidence", {}) or {}).get("url") or "",
    )


def import_contact(tx, person_id: str, contact: Dict[str, Any]):
    contact_id = f"contact:{person_id}"
    tx.run(
        """
        MATCH (p:Person {id: $person_id})
        MERGE (c:Contact {id: $contact_id})
        SET c.email = $email,
            c.phone = $phone,
            c.address = $address,
            c.github = $github,
            c.linkedin = $linkedin,
            c.source = $source,
            c.evidenceRef = $evidence_ref,
            c.evidenceUrl = $evidence_url
        MERGE (p)-[:HAS_CONTACT]->(c)
        """,
        person_id=person_id,
        contact_id=contact_id,
        email=contact.get("email") or "",
        phone=contact.get("phone") or "",
        address=contact.get("address") or "",
        github=contact.get("github") or "",
        linkedin=contact.get("linkedin") or "",
        source=(contact.get("evidence", {}) or {}).get("source") or "",
        evidence_ref=(contact.get("evidence", {}) or {}).get("ref") or "",
        evidence_url=(contact.get("evidence", {}) or {}).get("url") or "",
    )


def import_experience(tx, person_id: str, roles: List[Dict[str, Any]]):
    # Upsert Role nodes and connect via HAS_ROLE.
    # Use deterministic IDs by order to keep stable across re-imports.
    for i, r in enumerate(roles, start=1):
        role_id = f"role:{person_id}:{i:02d}"
        tx.run(
            """
            MATCH (p:Person {id: $person_id})
            MERGE (r:Role {id: $role_id})
            SET r.yearRange = $year_range,
                r.title = $title,
                r.company = $company,
                r.description = $desc,
                r.skills = $skills,
                r.highlight = $hi,
                r.source = $source,
                r.evidenceRef = $evidence_ref,
                r.evidenceUrl = $evidence_url
            MERGE (p)-[:HAS_ROLE {order: $order}]->(r)
            """,
            person_id=person_id,
            role_id=role_id,
            year_range=r.get("y") or "",
            title=r.get("t") or "",
            company=r.get("c") or "",
            desc=r.get("d") or "",
            skills=r.get("s") or [],
            hi=bool(r.get("hi")) if r.get("hi") is not None else False,
            source=(r.get("evidence", {}) or {}).get("source") or "",
            evidence_ref=(r.get("evidence", {}) or {}).get("ref") or "",
            evidence_url=(r.get("evidence", {}) or {}).get("url") or "",
            order=i,
        )


def import_oss(tx, person_id: str, oss_items: List[Dict[str, Any]]):
    """Import OSS/passion projects."""
    for i, item in enumerate(oss_items, start=1):
        oss_id = f"oss:{person_id}:{i:02d}"
        tx.run(
            """
            MATCH (p:Person {id: $person_id})
            MERGE (o:OssProject {id: $oss_id})
            SET o.name = $name,
                o.alias = $alias,
                o.subtitle = $subtitle,
                o.description = $desc,
                o.url = $url,
                o.tech = $tech,
                o.evidence = $evidence
            MERGE (p)-[:HAS_OSS_PROJECT {order: $order}]->(o)
            """,
            person_id=person_id,
            oss_id=oss_id,
            name=item.get("n") or "",
            alias=item.get("alias") or "",
            subtitle=item.get("s") or "",
            desc=item.get("d") or "",
            url=item.get("u"),
            tech=item.get("t") or [],
            evidence=item.get("evidence") or [],
            order=i,
        )


def import_credentials(tx, person_id: str, cred: Dict[str, Any]):
    # Store one aggregate node + individual certifications.
    cred_id = f"credentials:{person_id}"
    tx.run(
        """
        MATCH (p:Person {id: $person_id})
        MERGE (c:Credentials {id: $cred_id})
        SET c.topSkills = $top_skills,
            c.languages = $languages,
            c.notes = $notes,
            c.source = $source,
            c.evidenceRef = $evidence_ref,
            c.evidenceUrl = $evidence_url
        MERGE (p)-[:HAS_CREDENTIALS]->(c)
        """,
        person_id=person_id,
        cred_id=cred_id,
        top_skills=cred.get("topSkills") or [],
        # Neo4j property values must be primitives or arrays of primitives.
        # Store languages as a list of strings like "English — Professional working proficiency".
        languages=[
            (f"{x.get('language','').strip()} — {x.get('proficiency','').strip()}".strip(" —"))
            if isinstance(x, dict)
            else str(x)
            for x in (cred.get("languages") or [])
        ],
        notes=cred.get("notes") or [],
        source=(cred.get("evidence", {}) or {}).get("source") or "",
        evidence_ref=(cred.get("evidence", {}) or {}).get("ref") or "",
        evidence_url=(cred.get("evidence", {}) or {}).get("url") or "",
    )

    certs = cred.get("certifications") or []
    for i, cert in enumerate(certs, start=1):
        cert_id = f"cert:{person_id}:{i:02d}"
        tx.run(
            """
            MATCH (p:Person {id: $person_id})
            MERGE (x:Certification {id: $cert_id})
            SET x.name = $name,
                x.issuer = $issuer,
                x.issued = $issued,
                x.credentialId = $credential_id,
                x.skills = $skills,
                x.source = $source,
                x.evidenceRef = $evidence_ref,
                x.evidenceUrl = $evidence_url
            MERGE (p)-[:HAS_CERTIFICATION {order: $order}]->(x)
            """,
            person_id=person_id,
            cert_id=cert_id,
            name=cert.get("name") or "",
            issuer=cert.get("issuer") or "",
            issued=cert.get("issued") or "",
            credential_id=cert.get("credential_id") or "",
            skills=cert.get("skills") or [],
            source=(cred.get("evidence", {}) or {}).get("source") or "",
            evidence_ref=(cred.get("evidence", {}) or {}).get("ref") or "",
            evidence_url=(cred.get("evidence", {}) or {}).get("url") or "",
            order=i,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--person-id", required=True)
    ap.add_argument("--person-name", required=True)
    ap.add_argument(
        "--profile-dir",
        default=str(REPO_ROOT / "data" / "profile"),
        help="Directory containing about.json, contact.json, experience.json",
    )
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    about = _read_json(profile_dir / "about.json")
    contact = _read_json(profile_dir / "contact.json")
    experience = _read_json(profile_dir / "experience.json")

    oss_path = profile_dir / "oss.json"
    oss_items: List[Dict[str, Any]] = _read_json(oss_path) if oss_path.exists() else []

    cred_path = profile_dir / "credentials.json"
    credentials: Dict[str, Any] = _read_json(cred_path) if cred_path.exists() else {}

    uri = _env("NEO4J_URI")
    # Support both conventions: NEO4J_USERNAME (preferred) and NEO4J_USER (existing .env)
    user = os.getenv("NEO4J_USERNAME") or _env("NEO4J_USER")
    pwd = _env("NEO4J_PASSWORD")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    try:
        with driver.session() as session:
            session.execute_write(upsert_person, args.person_id, args.person_name)
            session.execute_write(import_about, args.person_id, about)
            session.execute_write(import_contact, args.person_id, contact)

            session.execute_write(import_experience, args.person_id, experience)

            if oss_items:
                session.execute_write(import_oss, args.person_id, oss_items)

            if credentials:
                session.execute_write(import_credentials, args.person_id, credentials)

        print(
            json.dumps(
                {
                    "status": "ok",
                    "personId": args.person_id,
                    "about": True,
                    "contact": True,
                    "rolesImported": len(experience),
                    "ossImported": len(oss_items),
                    "certificationsImported": len((credentials or {}).get("certifications") or []),
                },
                indent=2,
            )
        )
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
