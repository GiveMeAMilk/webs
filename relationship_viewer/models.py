from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


ENTITY_TYPES = ("Person", "Organization", "Social Account", "Data Source", "Location", "Other")


@dataclass(slots=True)
class Entity:
    id: str
    name: str
    type: str
    notes: str = ""
    attributes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, name: str, type: str, notes: str = "") -> "Entity":
        return cls(id=f"ent_{uuid4().hex[:10]}", name=name.strip(), type=type, notes=notes.strip())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "Untitled")),
            type=str(data.get("type", "Other")),
            notes=str(data.get("notes", "")),
            attributes={str(k): str(v) for k, v in data.get("attributes", {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "notes": self.notes,
            "attributes": self.attributes,
        }


@dataclass(slots=True)
class Relationship:
    id: str
    source: str
    target: str
    label: str
    notes: str = ""

    @classmethod
    def create(cls, source: str, target: str, label: str, notes: str = "") -> "Relationship":
        return cls(
            id=f"rel_{uuid4().hex[:10]}",
            source=source,
            target=target,
            label=label.strip() or "related to",
            notes=notes.strip(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relationship":
        return cls(
            id=str(data["id"]),
            source=str(data["source"]),
            target=str(data["target"]),
            label=str(data.get("label", "related to")),
            notes=str(data.get("notes", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            "notes": self.notes,
        }


@dataclass(slots=True)
class RelationshipGraph:
    entities: dict[str, Entity] = field(default_factory=dict)
    relationships: dict[str, Relationship] = field(default_factory=dict)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RelationshipGraph":
        graph = cls(notes=str(data.get("notes", "")))
        for raw_entity in data.get("entities", []):
            entity = Entity.from_dict(raw_entity)
            graph.entities[entity.id] = entity
        for raw_relationship in data.get("relationships", []):
            relationship = Relationship.from_dict(raw_relationship)
            if relationship.source in graph.entities and relationship.target in graph.entities:
                graph.relationships[relationship.id] = relationship
        return graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "notes": self.notes,
            "entities": [entity.to_dict() for entity in self.entities.values()],
            "relationships": [relationship.to_dict() for relationship in self.relationships.values()],
        }

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def add_relationship(self, relationship: Relationship) -> None:
        if relationship.source == relationship.target:
            raise ValueError("Relationship endpoints must be different.")
        if relationship.source not in self.entities or relationship.target not in self.entities:
            raise ValueError("Relationship endpoints must exist.")
        self.relationships[relationship.id] = relationship

    def remove_entity(self, entity_id: str) -> None:
        self.entities.pop(entity_id, None)
        for relationship_id in [
            relationship.id
            for relationship in self.relationships.values()
            if relationship.source == entity_id or relationship.target == entity_id
        ]:
            self.relationships.pop(relationship_id, None)

    def remove_relationship(self, relationship_id: str) -> None:
        self.relationships.pop(relationship_id, None)

    def neighbors(self, entity_id: str) -> list[tuple[Relationship, Entity]]:
        found: list[tuple[Relationship, Entity]] = []
        for relationship in self.relationships.values():
            if relationship.source == entity_id and relationship.target in self.entities:
                found.append((relationship, self.entities[relationship.target]))
            elif relationship.target == entity_id and relationship.source in self.entities:
                found.append((relationship, self.entities[relationship.source]))
        return sorted(found, key=lambda item: (item[1].type, item[1].name.lower()))

    def filtered_entities(self, query: str) -> list[Entity]:
        clean_query = query.strip().lower()
        entities = sorted(self.entities.values(), key=lambda item: (item.type, item.name.lower()))
        if not clean_query:
            return entities
        return [
            entity
            for entity in entities
            if clean_query in entity.name.lower()
            or clean_query in entity.type.lower()
            or clean_query in entity.notes.lower()
            or any(clean_query in value.lower() for value in entity.attributes.values())
        ]
