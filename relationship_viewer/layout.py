from __future__ import annotations

from collections import deque
from math import cos, pi, sin

from relationship_viewer.models import RelationshipGraph


def tree_positions(
    graph: RelationshipGraph,
    root_id: str | None,
    width: int,
    height: int,
) -> dict[str, tuple[float, float]]:
    if not graph.entities:
        return {}
    if root_id not in graph.entities:
        root_id = next(iter(graph.entities))

    levels: dict[int, list[str]] = {}
    visited = {root_id}
    queue: deque[tuple[str, int]] = deque([(root_id, 0)])
    while queue:
        entity_id, depth = queue.popleft()
        levels.setdefault(depth, []).append(entity_id)
        for _, neighbor in graph.neighbors(entity_id):
            if neighbor.id in visited:
                continue
            visited.add(neighbor.id)
            queue.append((neighbor.id, depth + 1))

    if len(visited) < len(graph.entities):
        levels.setdefault(max(levels) + 1, []).extend(
            entity_id for entity_id in graph.entities if entity_id not in visited
        )

    positions: dict[str, tuple[float, float]] = {}
    max_depth = max(levels)
    row_gap = (height - 120) / max(max_depth, 1)
    for depth, entity_ids in levels.items():
        y = 60 + depth * row_gap
        slot_width = width / (len(entity_ids) + 1)
        for index, entity_id in enumerate(entity_ids, start=1):
            positions[entity_id] = (slot_width * index, y)
    return positions


def radial_positions(
    graph: RelationshipGraph,
    root_id: str | None,
    width: int,
    height: int,
) -> dict[str, tuple[float, float]]:
    if not graph.entities:
        return {}
    if root_id not in graph.entities:
        root_id = next(iter(graph.entities))

    center = (width / 2, height / 2)
    positions = {root_id: center}
    others = [entity_id for entity_id in graph.entities if entity_id != root_id]
    radius = max(120, min(width, height) / 2 - 80)
    for index, entity_id in enumerate(others):
        angle = (2 * pi * index / max(len(others), 1)) - (pi / 2)
        positions[entity_id] = (center[0] + radius * cos(angle), center[1] + radius * sin(angle))
    return positions
