from __future__ import annotations

import random
from typing import Any, Dict, List, Set, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Entity, is_immune
from app.engine.entities.buffs import add_buff
from app.engine.game.constants import BURNING_DURATION, GAS_TICK_INTERVAL, TICK_DURATION
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

# SPD KeyWall caps at 10 turns; the port runs 1 turn/sec (GAME_TURN_TICKS @ GAME_LOOP_HZ).
_KEY_WALL_SECONDS = 10.0


def _blob_ev(origin, kind: str, data: dict) -> dict:
    """Build a blob event anchored at the origin cell (x/y) so filter_events_for_player
    LOS-scopes it to players who can see the effect's location, not the trigger."""
    data = dict(data)
    if origin:
        data["x"], data["y"] = origin
    return {"type": kind, "data": data}


def _evolve_electricity_blob(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
) -> None:
    cells: Set[Tuple[int, int]] = blob.get("cells", set())
    volume: Dict[Tuple[int, int], int] = blob.get("volume", {})
    origin = blob.get("origin")
    if not cells:
        del floor.blob_areas[blob_id]
        events.append(_blob_ev(origin, "BLOB_DEPLETED", {"id": blob_id}))
        return

    is_wand_blob = blob_id and str(blob_id).startswith("wand_elec_")
    tick_counter = blob.get("tick_counter", 0) + 1
    blob["tick_counter"] = tick_counter
    max_ticks = 150 if is_wand_blob else 100  # 5 s for traps
    if tick_counter >= max_ticks:
        del floor.blob_areas[blob_id]
        events.append(_blob_ev(origin, "BLOB_DEPLETED", {"id": blob_id}))
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
                        events.append(_blob_ev(origin, "DAMAGE",
                                               {"target": p.id, "amount": dmg, "shock": True}))
                        damaged = True
                # Charge wands in inventory
                from app.engine.entities.wands import Wand
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
                        events.append(_blob_ev(origin, "DAMAGE",
                                               {"target": m.id, "amount": taken, "shock": True}))
                        damaged = True
                        if not m.is_alive:
                            m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                                  players=list(players.values()))
                            events.append(_blob_ev(origin, "DEATH", {"target": m.id}))

        # Charge wands on ground
        for item_id, item in list(floor.items.items()):
            if item.pos and item.pos.x == cx and item.pos.y == cy:
                from app.engine.entities.wands import Wand
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
        events.append(_blob_ev(origin, "BLOB_UPDATE",
                               {"id": blob_id, "type": "electricity", "cells": cell_list}))
    else:
        del floor.blob_areas[blob_id]
        events.append(_blob_ev(origin, "BLOB_DEPLETED", {"id": blob_id}))

    if damaged:
        events.append(_blob_ev(origin, "PLAY_SOUND", {"sound": "LIGHTNING"}))


def _evolve_pylon_energy_blob(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
    ticks: int = 1,
) -> None:
    # Port of CavesBossLevel.PylonEnergy: persistent energy on wires and water
    # during pylon activation, dealing 6-12 electricity dmg per turn.
    if _turn_elapsed(blob, ticks, first_immediate=False) <= 0:
        return

    cells: Set[Tuple[int, int]] = blob.get("cells", set())
    volume: Dict[Tuple[int, int], int] = blob.get("volume", {})
    if not cells:
        return

    from app.engine.entities.mobs import DM300

    # Spreads instantly to all FLOOR_WATER cells in the arena region (y >= 13)
    cell_changed = False
    for y in range(13, floor.height):
        for x in range(floor.width):
            if floor.grid[y][x] == TileType.FLOOR_WATER and (x, y) not in cells:
                cells.add((x, y))
                volume[(x, y)] = 1
                cell_changed = True

    damaged = False
    any_dm300_supercharged = any(
        isinstance(m, DM300) and m.is_alive and getattr(m, "supercharged", False)
        for m in floor.mobs.values()
    )
    for cx, cy in list(cells):
        for p in players.values():
            if p.floor_id != floor.floor_id or not p.is_alive:
                continue
            if p.pos.x == cx and p.pos.y == cy and not getattr(p, "flying", False):
                dmg = random.randint(6, 12)
                p.take_damage(dmg)
                events.append({
                    "type": "DAMAGE",
                    "data": {
                        "target": p.id,
                        "amount": dmg,
                        "shock": True,
                        "_pylon_energy_hit": True,
                        "_dm300_supercharged": any_dm300_supercharged,
                    },
                })
                damaged = True

        for m in list(floor.mobs.values()):
            if m.is_alive and not getattr(m, "flying", False) and not isinstance(m, DM300) and m.pos.x == cx and m.pos.y == cy:
                dmg = random.randint(6, 12)
                taken = m.take_damage(dmg)
                events.append({"type": "DAMAGE", "data": {"target": m.id, "amount": taken, "shock": True}})
                damaged = True
                if not m.is_alive:
                    m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                          players=list(players.values()))
                    events.append({"type": "DEATH", "data": {"target": m.id}})

    if damaged:
        events.append({"type": "PLAY_SOUND", "data": {"sound": "LIGHTNING"}})

    if cell_changed:
        blob["cells"] = cells
        blob["volume"] = volume
        cell_list = [(c[0], c[1], 1) for c in cells]
        events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": "pylon_energy", "cells": cell_list}})


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
    from app.engine.entities.items.consumables import ChargrilledMeat, Dewdrop, MysteryMeat
    from app.engine.entities.items.scrolls import Scroll
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


def _turn_elapsed(blob: dict, ticks: int, first_immediate: bool) -> int:
    """How many whole SPD turns a per-turn blob owes after `ticks` more ticks.

    Real-time rooms pass 1 tick per call and turn rooms a whole turn's worth,
    so one counter serves both modes. A blob that `first_immediate` evolves on
    the call after it was seeded, as SPD's blob actor acts on the next turn.
    """
    default = GAS_TICK_INTERVAL - 1 if first_immediate else 0
    counter = blob.get("tick_counter", default) + ticks
    turns = counter // GAS_TICK_INTERVAL
    blob["tick_counter"] = counter - turns * GAS_TICK_INTERVAL
    return int(turns)


def seed_fire(floor: FloorState, cell: Tuple[int, int], amount: int, blob_id: str = "fire_seeded") -> None:
    """SPD `Blob.seed(cell, amount, Fire.class)`: adds `amount` to the cell's fire."""
    if amount <= 0:
        return
    blob = next((b for b in floor.blob_areas.values() if b.get("type") == "fire"), None)
    if blob is None:
        blob = {"type": "fire", "cells": set(), "volume": {}}
        floor.blob_areas[blob_id] = blob
    cells = blob.setdefault("cells", set())
    if not isinstance(cells, set):
        cells = set(tuple(c) for c in cells)
        blob["cells"] = cells
    volume = blob.setdefault("volume", {})
    cells.add(cell)
    volume[cell] = volume.get(cell, 0) + amount


def fire_volume_at(floor: FloorState, cell: Tuple[int, int]) -> int:
    """SPD `Fire.volumeAt(cell, Fire.class)`."""
    total = 0
    for b in floor.blob_areas.values():
        if b.get("type") != "fire":
            continue
        cells = b.get("cells", set())
        if cell in cells or list(cell) in cells:
            total += b.get("volume", {}).get(cell, _FIRE_IGNITE_STRENGTH)
    return total


def seed_gas(floor: FloorState, gas_type: str, cell: Tuple[int, int], amount: int, blob_id: str = "") -> None:
    """SPD `Blob.seed(cell, amount, <Gas>.class)` for one gas type."""
    blob = next((b for b in floor.blob_areas.values() if b.get("type") == gas_type), None)
    if blob is None:
        blob = {"type": gas_type, "cells": set(), "volume": {}}
        floor.blob_areas[blob_id or f"{gas_type}_seeded"] = blob
    cells = blob.setdefault("cells", set())
    if not isinstance(cells, set):
        cells = set(tuple(c) for c in cells)
        blob["cells"] = cells
    volume = blob.setdefault("volume", {})
    if amount > 0:
        cells.add(cell)
        volume[cell] = volume.get(cell, 0) + amount


def _fire_burn(floor: FloorState, cx: int, cy: int, players: Dict[str, Entity]) -> bool:
    """SPD `Fire.burn(pos)`: reignite a char, burn the heap, wither the plant."""
    burned = False
    for p in players.values():
        if p.floor_id != floor.floor_id or not p.is_alive:
            continue
        if p.pos.x == cx and p.pos.y == cy and not is_immune(p, "burning"):
            add_buff(p.buffs, "burning", duration=BURNING_DURATION, level=1, stack_mode="extend")
            burned = True
    for m in list(floor.mobs.values()):
        if m.is_alive and m.pos.x == cx and m.pos.y == cy and not is_immune(m, "burning"):
            add_buff(m.buffs, "burning", duration=BURNING_DURATION, level=1, stack_mode="extend")
            burned = True
    if (cx, cy) in floor.plants:
        del floor.plants[(cx, cy)]
    _burn_floor_items(floor, cx, cy)
    return burned


def _evolve_fire_blob(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
    ticks: int = 1,
) -> None:
    """Port of `Fire.evolve()`, run once per SPD turn of elapsed time."""
    turns = _turn_elapsed(blob, ticks, first_immediate=True)
    for _ in range(turns):
        if blob_id not in floor.blob_areas:
            return
        _fire_turn(floor, blob_id, blob, players, events)


def _fire_turn(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
) -> None:
    cells: Set[Tuple[int, int]] = set(tuple(c) for c in blob.get("cells", set()))
    volume: Dict[Tuple[int, int], int] = blob.get("volume", {})
    cur = {c: volume.get(c, _FIRE_IGNITE_STRENGTH) for c in cells}
    new_volume: Dict[Tuple[int, int], int] = {}
    burned = False
    destroyed_tiles: List[Tuple[int, int, int]] = []
    flamable = floor.flags.flamable if floor.flags else None

    candidates: Set[Tuple[int, int]] = set(c for c, v in cur.items() if v > 0)
    for cx, cy in list(candidates):
        for dx, dy in _FIRE_CARDINALS:
            candidates.add((cx + dx, cy + dy))

    for cx, cy in candidates:
        if not (0 <= cx < floor.width and 0 <= cy < floor.height):
            continue
        here = cur.get((cx, cy), 0)
        is_flamable = bool(flamable[cy][cx]) if flamable else False
        if here > 0:
            if floor.grid[cy][cx] == TileType.FLOOR_WATER:
                continue
            burned = _fire_burn(floor, cx, cy, players) or burned
            fire = here - 1
            if fire <= 0 and is_flamable:
                tile = floor.grid[cy][cx]
                new_tile = _BURN_RESULT.get(tile, TileType.EMBERS)
                floor.grid[cy][cx] = new_tile
                destroyed_tiles.append((cx, cy, new_tile))
        elif is_flamable and any(cur.get((cx + dx, cy + dy), 0) > 0 for dx, dy in _FIRE_CARDINALS):
            fire = _FIRE_IGNITE_STRENGTH
            burned = _fire_burn(floor, cx, cy, players) or burned
        else:
            fire = 0
        if fire > 0:
            new_volume[(cx, cy)] = fire

    if destroyed_tiles:
        floor.rebuild_flags()
        patches = [{"x": cx, "y": cy, "tile": tile} for cx, cy, tile in destroyed_tiles]
        events.append({"type": "MAP_PATCH", "data": {"tiles": patches}})

    if new_volume:
        blob["cells"] = set(new_volume)
        blob["volume"] = new_volume
        cell_list = [(c[0], c[1], v) for c, v in new_volume.items()]
        events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": "fire", "cells": cell_list}})
    else:
        del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
        return
    if burned:
        events.append({"type": "PLAY_SOUND", "data": {"sound": "BURNING"}})


_GAS_CARDINALS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def _evolve_gas_blob(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
    ticks: int = 1,
) -> None:
    turns = _turn_elapsed(blob, ticks, first_immediate=False)
    for _ in range(turns):
        if blob_id not in floor.blob_areas:
            return
        _gas_turn(floor, blob_id, blob, players, events)


def _gas_turn(
    floor: FloorState,
    blob_id: Any,
    blob: dict,
    players: Dict[str, Entity],
    events: List[dict],
) -> None:
    cells: Set[Tuple[int, int]] = blob.get("cells", set())
    volume: Dict[Tuple[int, int], int] = blob.get("volume", {})
    if not cells:
        return
    btype = blob.get("type", "toxic_gas")
    depth = getattr(floor, "floor_id", 1)

    # Collect all cells to process (current + 1-step neighbors)
    all_cells: Set[Tuple[int, int]] = set(cells)
    for cx, cy in cells:
        for dx, dy in _GAS_CARDINALS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                all_cells.add((nx, ny))

    solid = floor.flags.solid if floor.flags else None
    new_cells: Set[Tuple[int, int]] = set()
    new_volume: Dict[Tuple[int, int], int] = {}

    for cx, cy in all_cells:
        if not (0 <= cx < floor.width and 0 <= cy < floor.height):
            continue
        if solid and solid[cy][cx]:
            continue

        count = 1
        total = volume.get((cx, cy), 0)

        for dx, dy in _GAS_CARDINALS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                if not (solid and solid[ny][nx]):
                    total += volume.get((nx, ny), 0)
                    count += 1

        if total >= count:
            new_val = total // count - 1
        else:
            new_val = 0

        if new_val > 0:
            new_cells.add((cx, cy))
            new_volume[(cx, cy)] = new_val

    # Apply per-type effects
    for cx, cy in list(new_cells):
        for p in players.values():
            if p.floor_id != floor.floor_id or not p.is_alive:
                continue
            if p.pos.x == cx and p.pos.y == cy:
                if btype == "toxic_gas" and not is_immune(p, "toxic_gas"):
                    dmg = 1 + depth // 5
                    p.take_damage(dmg)
                    events.append({"type": "DAMAGE", "data": {"target": p.id, "amount": dmg}})
                elif btype == "paralytic_gas" and not is_immune(p, "paralytic_gas"):
                    add_buff(p.buffs, "paralysis", duration=3.0, level=1, stack_mode="extend")
                    events.append({"type": "MESSAGE", "data": {"text": "You are paralyzed!"}, "_player_id": p.id})
                elif btype == "corrosive_gas" and not is_immune(p, "corrosive_gas"):
                    add_buff(p.buffs, "corrosion", duration=5.0, level=1, stack_mode="extend")
                elif btype == "confusion_gas" and not is_immune(p, "confusion_gas"):
                    add_buff(p.buffs, "vertigo", duration=2.0, level=1, stack_mode="replace")
                elif btype == "shrouding_fog" and not is_immune(p, "shrouding_fog"):
                    # SPD SmokeScreen: chars inside thick smoke are blinded.
                    add_buff(p.buffs, "blindness", duration=2.0, level=1, stack_mode="extend")

        for m in list(floor.mobs.values()):
            if m.is_alive and m.pos.x == cx and m.pos.y == cy:
                if btype == "toxic_gas" and not is_immune(m, "toxic_gas"):
                    dmg = 1 + depth // 5
                    taken = m.take_damage(dmg)
                    events.append({"type": "DAMAGE", "data": {"target": m.id, "amount": taken}})
                    if not m.is_alive:
                        m.die(floor_mobs=floor.mobs, tile_x=m.pos.x, tile_y=m.pos.y,
                              players=list(players.values()))
                        events.append({"type": "DEATH", "data": {"target": m.id}})
                elif btype == "paralytic_gas" and not is_immune(m, "paralytic_gas"):
                    add_buff(m.buffs, "paralysis", duration=3.0, level=1, stack_mode="extend")
                elif btype == "corrosive_gas" and not is_immune(m, "corrosive_gas"):
                    add_buff(m.buffs, "corrosion", duration=5.0, level=1, stack_mode="extend")
                elif btype == "confusion_gas" and not is_immune(m, "confusion_gas"):
                    add_buff(m.buffs, "vertigo", duration=2.0, level=1, stack_mode="replace")
                elif btype == "shrouding_fog" and not is_immune(m, "shrouding_fog"):
                    # SPD SmokeScreen: chars inside thick smoke are blinded.
                    add_buff(m.buffs, "blindness", duration=2.0, level=1, stack_mode="extend")

    if new_cells:
        blob["cells"] = new_cells
        blob["volume"] = new_volume
        cell_list = [(c[0], c[1], new_volume.get(c, 1)) for c in new_cells]
        events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": btype, "cells": cell_list}})
    else:
        del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})


def _evolve_hallowed_ground_blob(floor: FloorState, blob_id: str, blob: dict, players: Dict[str, Entity], events: List[dict], dt: float = TICK_DURATION) -> None:
    cells_data = blob.get("cells", [])
    if not cells_data:
        if blob_id in floor.blob_areas:
            del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
        return

    # Check fire destroying hallowed ground
    fire_cells = set()
    for bid, b in floor.blob_areas.items():
        if b.get("type") in ("fire", "tengu_fire", "sacrificial_fire"):
            for fc in b.get("cells", []):
                fire_cells.add((fc[0], fc[1]))

    valid_cells = []
    rebuild = False
    cell_changed = False
    if len(fire_cells) > 0:
        for c in cells_data:
            if (c[0], c[1]) not in fire_cells:
                valid_cells.append(c)
            else:
                cell_changed = True
    else:
        valid_cells = list(cells_data)

    if not valid_cells:
        if blob_id in floor.blob_areas:
            del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
        return

    blob["cells"] = valid_cells
    remaining = blob.get("remaining", 20.0)
    remaining -= dt
    if remaining <= 0:
        if blob_id in floor.blob_areas:
            del floor.blob_areas[blob_id]
        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
        return
    blob["remaining"] = remaining

    # Accumulate time to tick effects once per second (1 turn)
    tick_accum = blob.get("tick_accum", 0.0) + dt
    if tick_accum >= 1.0 - 1e-9:
        tick_accum -= 1.0
        cell_set = set((c[0], c[1]) for c in valid_cells)

        for c in valid_cells:
            gx, gy = c[0], c[1]
            if 0 <= gy < len(floor.grid) and 0 <= gx < len(floor.grid[0]):
                if floor.grid[gy][gx] in (TileType.FLOOR, TileType.EMBERS, TileType.EMPTY_DECO):
                    floor.grid[gy][gx] = TileType.FLOOR_GRASS
                elif floor.grid[gy][gx] == TileType.FLOOR_GRASS:
                    if random.random() < 0.05:
                        floor.grid[gy][gx] = TileType.HIGH_GRASS
                        rebuild = True

        if rebuild:
            floor.rebuild_flags()

        for p in players.values():
            if getattr(p, "floor_id", None) == floor.floor_id and getattr(p, "is_alive", False) and (p.pos.x, p.pos.y) in cell_set:
                max_hp = getattr(p, "get_total_max_hp", lambda: getattr(p, "max_hp", 1))()
                if p.hp < max_hp:
                    p.hp = min(max_hp, p.hp + 1)
                else:
                    p.add_buff("barrier", duration=30.0, level=1, stack_mode="extend")

        for m in floor.mobs.values():
            if not getattr(m, "is_alive", False) or (m.pos.x, m.pos.y) not in cell_set:
                continue
            if getattr(m, "faction", "") == "player":
                if m.hp < m.max_hp:
                    m.hp = min(m.max_hp, m.hp + 1)
                else:
                    m.add_buff("barrier", duration=30.0, level=1, stack_mode="extend")
            else:
                if not getattr(m, "flying", False):
                    m.add_buff("crippled", duration=1.0)

    blob["tick_accum"] = tick_accum

    if cell_changed:
        cell_list = [(c[0], c[1], 1.0) for c in valid_cells]
        events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": "hallowed_ground", "cells": cell_list}})


def tick_blob_areas(
    floors: Dict[int, FloorState],
    players: Dict[str, Entity],
    dt: float = TICK_DURATION,
    ticks: int = 1,
) -> List[dict]:
    """Advance every blob by one call's worth of time: `dt` SPD turns (as
    seconds) and `ticks` real-time ticks -- 1/40 and 1 in real time, 1.0 and
    a whole turn's ticks in a turn room."""
    events: List[dict] = []

    for floor in floors.values():
        floor_id = getattr(floor, "floor_id", None)
        _merge_same_type_blobs(floor, "fire")
        _merge_same_type_blobs(floor, "tengu_fire")
        _merge_same_type_blobs(floor, "electricity")

        start = len(events)

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
                    remaining -= dt
                    blob["remaining"] = remaining
                    if remaining <= 0:
                        del floor.blob_areas[blob_id]
                        events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                        continue

            if btype == "key_wall":
                # SPD KeyWall: temporary SOLID|LOS_BLOCKING walls capped at 10
                # turns. Rebuild flags on expiry so the override is cleared.
                remaining = blob.get("remaining", _KEY_WALL_SECONDS)
                remaining -= dt
                if remaining <= 0:
                    del floor.blob_areas[blob_id]
                    events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                    floor.rebuild_flags()
                    continue
                blob["remaining"] = remaining

            elif btype in ("light_wall", "wall_of_light"):
                remaining = blob.get("remaining", 20.0)
                remaining -= dt
                if remaining <= 0:
                    owner_id = blob.get("owner")
                    if owner_id and owner_id in players:
                        setattr(players[owner_id], "_has_active_wall", False)
                    del floor.blob_areas[blob_id]
                    events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                    floor.rebuild_flags()
                    continue
                blob["remaining"] = remaining

            elif btype == "hallowed_ground":
                _evolve_hallowed_ground_blob(floor, blob_id, blob, players, events, dt)

            elif btype == "fire":
                _evolve_fire_blob(floor, blob_id, blob, players, events, ticks)

            elif btype == "electricity":
                _evolve_electricity_blob(floor, blob_id, blob, players, events)

            elif btype == "pylon_energy":
                _evolve_pylon_energy_blob(floor, blob_id, blob, players, events, ticks)

            elif btype in ("toxic_gas", "paralytic_gas", "corrosive_gas",
                           "confusion_gas", "shrouding_fog"):
                _evolve_gas_blob(floor, blob_id, blob, players, events, ticks)

            elif btype in ("tengu_fire", "tengu_shocker"):
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

            elif btype == "sacrificial_fire":
                fire_idx = blob.get("fire_index", 0)
                fires = floor.generation_meta.get("sacrifice_fires", [])
                if fire_idx >= len(fires):
                    del floor.blob_areas[blob_id]
                    events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                    continue
                fire = fires[fire_idx]
                vol = fire.get("volume", 0)
                if vol <= 0:
                    del floor.blob_areas[blob_id]
                    events.append({"type": "BLOB_DEPLETED", "data": {"id": blob_id}})
                    continue
                max_vol = fire.get("max_volume", 1)
                intensity = max(vol / max_vol, 0.1)
                cell_list = [(c[0], c[1], intensity) for c in cells_data]
                events.append({"type": "BLOB_UPDATE", "data": {"id": blob_id, "type": btype, "cells": cell_list}})

        if floor_id is not None:
            for ev in events[start:]:
                ev["_floor_id"] = floor_id

    return events
