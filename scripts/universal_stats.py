"""Print universal-subgraph stats from the Neo4j instance defined by NEO4J_* env vars."""
from __future__ import annotations
import json
import os
import sys

from neo4j import GraphDatabase


def main() -> int:
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    pw = os.environ.get("NEO4J_PASSWORD")
    db = os.environ.get("NEO4J_DATABASE", "neo4j")
    if not (uri and user and pw):
        print("ERROR: NEO4J_URI/USER/PASSWORD env vars required", file=sys.stderr)
        return 2

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    try:
        with driver.session(database=db) as s:
            labels = {}
            for r in s.run(
                "MATCH (n:UniversalNode) UNWIND labels(n) AS l "
                "WITH l, count(*) AS c WHERE l <> 'UniversalNode' "
                "RETURN l, c ORDER BY c DESC"
            ):
                labels[r["l"]] = r["c"]
            rels = {}
            for r in s.run(
                "MATCH (a:UniversalNode)-[r]->(b:UniversalNode) "
                "RETURN type(r) AS t, count(r) AS c ORDER BY c DESC"
            ):
                rels[r["t"]] = r["c"]
            ev = s.run("MATCH (e:Evidence) RETURN count(e) AS c").single()["c"]
            totals = s.run(
                "MATCH (n:UniversalNode) RETURN count(n) AS c"
            ).single()["c"]
            print(json.dumps({
                "nodes_total": totals,
                "evidence_total": ev,
                "nodes_by_label": labels,
                "edges_by_type": rels,
            }, indent=2))
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
