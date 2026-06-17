from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from app.engine.entities.base import Entity
from app.engine.game.floor_state import FloorState


def _blob_cell_intensity(blob: dict, cell: tuple) -> int:
    volume = blob.get("volume", {})
    if isinstance(volume, dict):
        return volume.get(cell, 1)
    return 1


def tick_blob_areas(floors: Dict[int, FloorState], players: Dict[str, Entity]) -> List[dict]:
    events: List[dict] = []

    for floor in floors.values():
        for blob_id, blob in list(floor.blob_areas.items()):
            btype = blob.get("type", "unknown")
            cells_data = blob.get("cells", [])
            if not cells_data:
                del floor.blob_areas[blob_id]
                events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                continue

            if btype == "foliage":
                cells: Set[Tuple[int, int]] = set(tuple(c) for c in cells_data)
                for player in players.values():
                    if player.floor_id != floor.floor_id:
                        continue
                    if not player.is_alive:
                        continue
                    pos = (player.pos.x, player.pos.y)
                    if pos in cells:
                        player.add_buff("shadows", duration=2.0, stack_mode="extend")

                remaining = blob.get("remaining", 0.0)
                if remaining > 0:
                    remaining -= 0.05
                    blob["remaining"] = remaining
                    if remaining <= 0:
                        del floor.blob_areas[blob_id]
                        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                        continue

            if btype in ("fire", "toxic_gas", "paralytic_gas", "corrosive_gas", "confusion_gas",
                         "electricity", "tengu_fire", "tengu_shocker"):
                volume = blob.get("volume", {})
                has_any = False
                cell_list = []
                for c in cells_data:
                    ck = tuple(c) if isinstance(c, list) else c
                    intensity = volume.get(ck, 1) if isinstance(volume, dict) else 1
                    if intensity > 0:
                        has_any = True
                        cell_list.append((c[0], c[1], intensity))
                if has_any:
                    events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": btype, "cells": cell_list}})
                else:
                    del floor.blob_areas[blob_id]
                    events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})

    return events
