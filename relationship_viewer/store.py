from __future__ import annotations

import json
from pathlib import Path

from relationship_viewer.models import Entity, Relationship, RelationshipGraph


SAMPLE_GRAPH = {
    "notes": "Workspace notes for leads, questions, source quality, or next steps.",
    "entities": [
        {
            "id": "ent_alex",
            "name": "Alex Rivera",
            "type": "Person",
            "notes": "Primary person of interest.",
            "attributes": {"role": "Founder"},
        },
        {
            "id": "ent_northstar",
            "name": "Northstar Labs",
            "type": "Organization",
            "notes": "AI research company.",
            "attributes": {"domain": "northstar.example"},
        },
        {
            "id": "ent_alex_x",
            "name": "@alexrivera",
            "type": "Social Account",
            "notes": "Public social profile.",
            "attributes": {"platform": "X"},
        },
        {
            "id": "ent_registry",
            "name": "Business Registry Export",
            "type": "Data Source",
            "notes": "Imported corporate filings dataset.",
            "attributes": {"format": "CSV"},
        },
        {
            "id": "ent_brisbane",
            "name": "Brisbane",
            "type": "Location",
            "notes": "Known operating location.",
            "attributes": {"country": "Australia"},
        },
    ],
    "relationships": [
        {"id": "rel_1", "source": "ent_alex", "target": "ent_northstar", "label": "founded", "notes": ""},
        {"id": "rel_2", "source": "ent_alex", "target": "ent_alex_x", "label": "uses", "notes": ""},
        {
            "id": "rel_3",
            "source": "ent_northstar",
            "target": "ent_registry",
            "label": "appears in",
            "notes": "",
        },
        {
            "id": "rel_4",
            "source": "ent_northstar",
            "target": "ent_brisbane",
            "label": "operates in",
            "notes": "",
        },
    ],
}


def load_graph(path: Path | None) -> RelationshipGraph:
    if path is None or not path.exists():
        return RelationshipGraph.from_dict(SAMPLE_GRAPH)
    with path.open("r", encoding="utf-8") as handle:
        return RelationshipGraph.from_dict(json.load(handle))


def save_graph(graph: RelationshipGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(graph.to_dict(), handle, indent=2)
        handle.write("\n")


def export_tree_text(graph: RelationshipGraph, root_id: str) -> str:
    root = graph.entities[root_id]
    lines: list[str] = []
    seen: set[str] = set()

    def visit(entity: Entity, depth: int) -> None:
        prefix = "  " * depth
        marker = " (seen)" if entity.id in seen else ""
        lines.append(f"{prefix}- {entity.name} [{entity.type}]{marker}")
        if entity.id in seen:
            return
        seen.add(entity.id)
        for relationship, neighbor in graph.neighbors(entity.id):
            lines.append(f"{prefix}  -> {relationship.label}")
            visit(neighbor, depth + 2)

    visit(root, 0)
    return "\n".join(lines) + "\n"


def parse_attributes(raw: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    for line in raw.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if ":" in clean:
            key, value = clean.split(":", 1)
        elif "=" in clean:
            key, value = clean.split("=", 1)
        else:
            key, value = clean, ""
        attributes[key.strip()] = value.strip()
    return attributes
