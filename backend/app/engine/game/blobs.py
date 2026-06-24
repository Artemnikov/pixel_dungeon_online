from __future__ import annotations

import random
from typing import Any, Dict, List, Set, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Entity, is_immune
from app.engine.entities.buffs import add_buff, has_buff
from app.engine.game.floor_state import FloorState

_FIRE_IGNITE_STRENGTH = 4
_FIRE_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

# Per-tile burnout destination override. Mirrors SewerLevel.destroy()
# (SewerLevel.java:196-208): REGION_DECO -> WATER, REGION_DECO_ALT -> EMPTY_SP.
# The remake has no distinct "special floor" tile (EMPTY_SP already collapses
# to FLOOR elsewhere in spd_adapter._SPD_TO_TILE), so REGION_DECO_ALT's
# destination is FLOOR for consistency. Every other flamable tile keeps
# burning to EMBERS (the default).
_BURN_RESULT = {
    TileType.REGION_DECO: TileType.FLOOR_WATER,
    TileType.REGION_DECO_ALT: TileType.FLOOR,
}


_ELECTRIC_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def _evolve_electricity_blob(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
) -> None:
    cells: Set[Tuple[int, int]] = blob.get("cells", set())
    volume: Dict[Tuple[int, int], int] = blob.get("volume", {})
    if not cells:
        del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
        return

    is_wand_blob = blob_id and str(blob_id).startswith("wand_elec_")
    if is_wand_blob:
        tick_counter = blob.get("tick_counter", 0) + 1
        blob["tick_counter"] = tick_counter
        if tick_counter >= 150:
            del floor.blob_areas[blob_id]
            events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
            return

    new_cells: Set[Tuple[int, int]] = set()
    new_volume: Dict[Tuple[int, int], int] = {}
    spread_targets: Dict[Tuple[int, int], int] = {}
    damaged = False
    depth = getattr(floor, "floor_id", 1)

    for cx, cy in list(cells):
        vol = volume.get((cx, cy), 1)
        if vol <= 0:
            continue

        # Apply effect to chars on this cell
        for p in players.values():
            if p.floor_id != floor.floor_id or not p.is_alive:
                continue
            if p.pos.x == cx and p.pos.y == cy and not is_immune(p, "electricity"):
                from app.engine.entities.buffs import add_buff
                add_buff(p.buffs, "paralysis", duration=float(vol), level=1, stack_mode="replace")
                if vol % (20 if is_wand_blob else 2) == 1:
                    dmg = round(random.uniform(0, 1) if is_wand_blob else random.uniform(2, 2 + depth / 5.0))
                    if dmg > 0:
                        p.take_damage(dmg)
                        events.append({"type": "DAMAGE", "data": {"target": p.id, "amount": dmg, "shock": True}})
                        damaged = True
                # Charge wands in inventory
                from app.engine.entities.base import Wand
                for item in list(getattr(p, "belongings", None).all_items() if getattr(p, "belongings", None) else []):
                    if isinstance(item, Wand) and not item.cursed and item.charges < item.max_charges:
                        item.gain_charge(0.333)

        for m in list(floor.mobs.values()):
            if m.is_alive and m.pos.x == cx and m.pos.y == cy and not is_immune(m, "electricity"):
                from app.engine.entities.buffs import add_buff
                add_buff(m.buffs, "paralysis", duration=float(vol), level=1, stack_mode="replace")
                if vol % (20 if is_wand_blob else 2) == 1:
                    dmg = round(random.uniform(0, 1) if is_wand_blob else random.uniform(2, 2 + depth / 5.0))
                    if dmg > 0:
                        taken = m.take_damage(dmg)
                        events.append({"type": "DAMAGE", "data": {"target": m.id, "amount": taken, "shock": True}})
                        damaged = True
                        if not m.is_alive:
                            m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                                  players=list(players.values()))
                            events.append({"type": "DEATH", "data": {"target": m.id}})

        # Charge wands on ground
        for item_id, item in list(floor.items.items()):
            if item.pos and item.pos.x == cx and item.pos.y == cy:
                from app.engine.entities.base import Wand
                if isinstance(item, Wand) and not item.cursed and item.charges < item.max_charges:
                    item.gain_charge(0.333)

        # Spread first (SPD order: spread with current vol, then decrement)
        for dx, dy in _ELECTRIC_CARDINALS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                tile = floor.grid[ny][nx]
                if tile == TileType.FLOOR_WATER and (nx, ny) not in new_volume and (nx, ny) not in volume:
                    spread_targets[(nx, ny)] = vol
        # Decrement volume after spread
        new_vol = vol - 1
        if new_vol > 0:
            new_cells.add((cx, cy))
            new_volume[(cx, cy)] = new_vol

    for cell, vol in spread_targets.items():
        new_cells.add(cell)
        new_volume[cell] = vol

    if new_cells:
        blob["cells"] = new_cells
        blob["volume"] = new_volume
        cell_list = [(c[0], c[1], new_volume.get(c, 1)) for c in new_cells]
        events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": "electricity", "cells": cell_list}})
    else:
        del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})

    if damaged:
        events.append({"type": "PLAY_SOUND", "data": {"sound": "LIGHTNING"}})


def _merge_same_type_blobs(floor: FloorState, btype: str) -> None:
    same = [(bid, b) for bid, b in floor.blob_areas.items() if b.get("type") == btype]
    if len(same) <= 1:
        return
    same.sort(key=lambda x: len(x[1].get("cells", set())), reverse=True)
    _, keep = same[0]
    for bid, b in same[1:]:
        b_cells: set = b.get("cells", set())
        b_vol: dict = b.get("volume", {})
        keep_cells: set = keep.setdefault("cells", set())
        keep_vol: dict = keep.setdefault("volume", {})
        for cell in b_cells:
            keep_cells.add(cell)
            if cell in b_vol and (cell not in keep_vol or b_vol[cell] > keep_vol[cell]):
                keep_vol[cell] = b_vol[cell]
        b["cells"] = set()
        b["volume"] = {}


def _blob_cell_intensity(blob: dict, cell: tuple) -> int:
    volume = blob.get("volume", {})
    if isinstance(volume, dict):
        return volume.get(cell, 1)
    return 1


def _burn_floor_items(floor: FloorState, cx: int, cy: int) -> None:
    """Selectively burn items at a cell, matching SPD Heap.burn()."""
    from app.engine.entities.base import ChargrilledMeat, Dewdrop, MysteryMeat, Scroll
    for item_id, item in list(floor.items.items()):
        if item.pos and item.pos.x == cx and item.pos.y == cy:
            if isinstance(item, Scroll) and not item.unique:
                del floor.items[item_id]
            elif isinstance(item, Dewdrop):
                del floor.items[item_id]
            elif isinstance(item, MysteryMeat):
                floor.items[item_id] = ChargrilledMeat(
                    id=item.id, quantity=item.quantity
                )


def _evolve_fire_blob(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
) -> None:
    cells: Set[Tuple[int, int]] = blob.get("cells", set())
    volume: Dict[Tuple[int, int], int] = blob.get("volume", {})
    new_cells: Set[Tuple[int, int]] = set()
    new_volume: Dict[Tuple[int, int], int] = {}
    spread_targets: Dict[Tuple[int, int], int] = {}
    observe = False
    burned = False
    destroyed_tiles: List[Tuple[int, int, int]] = []

    for cx, cy in list(cells):
        tile = floor.grid[cy][cx]
        if tile == TileType.FLOOR_WATER:
            continue
        cur_vol = volume.get((cx, cy), _FIRE_IGNITE_STRENGTH)
        vol = cur_vol - 0.05
        flamable = floor.flags.flamable[cy][cx] if floor.flags else False

        if vol <= 0:
            if flamable:
                new_tile = _BURN_RESULT.get(tile, TileType.EMBERS)
                floor.grid[cy][cx] = new_tile
                destroyed_tiles.append((cx, cy, new_tile))
                observe = True
            continue

        new_cells.add((cx, cy))
        new_volume[(cx, cy)] = vol

        for p in players.values():
            if p.floor_id != floor.floor_id or not p.is_alive:
                continue
            if p.pos.x == cx and p.pos.y == cy:
                add_buff(p.buffs, "burning", duration=8.0, level=1, stack_mode="extend")
                burned = True

        for m in list(floor.mobs.values()):
            if m.is_alive and m.pos.x == cx and m.pos.y == cy and not is_immune(m, "burning"):
                add_buff(m.buffs, "burning", duration=8.0, level=1, stack_mode="extend")
                burned = True

        if (cx, cy) in floor.plants:
            del floor.plants[(cx, cy)]

        _burn_floor_items(floor, cx, cy)

        for dx, dy in _FIRE_CARDINALS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if floor.flags.flamable[ny][nx] if floor.flags else False:
                    if (nx, ny) not in new_volume and (nx, ny) not in volume:
                        spread_targets[(nx, ny)] = _FIRE_IGNITE_STRENGTH

    for cell, vol in spread_targets.items():
        new_cells.add(cell)
        new_volume[cell] = vol

    if observe:
        floor.rebuild_flags()
        patches = [{"x": cx, "y": cy, "tile": tile}
                   for cx, cy, tile in destroyed_tiles]
        if patches:
            events.append({"type": "MAP_PATCH", "data": {"tiles": patches}})

    if new_cells:
        blob["cells"] = new_cells
        blob["volume"] = new_volume
        cell_list = [(c[0], c[1], new_volume.get(c, 1)) for c in new_cells]
        events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": "fire", "cells": cell_list}})
    else:
        del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
        return
    if burned:
        events.append({"type": "PLAY_SOUND", "data": {"sound": "BURNING"}})


def tick_blob_areas(floors: Dict[int, FloorState], players: Dict[str, Entity]) -> List[dict]:
    events: List[dict] = []

    for floor in floors.values():
        _merge_same_type_blobs(floor, "fire")
        _merge_same_type_blobs(floor, "tengu_fire")
        _merge_same_type_blobs(floor, "electricity")

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

            if btype == "fire":
                _evolve_fire_blob(floor, blob_id, blob, players, events)

            elif btype == "electricity":
                _evolve_electricity_blob(floor, blob_id, blob, players, events)

            elif btype in ("toxic_gas", "paralytic_gas", "corrosive_gas", "confusion_gas",
                           "tengu_fire", "tengu_shocker"):
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
