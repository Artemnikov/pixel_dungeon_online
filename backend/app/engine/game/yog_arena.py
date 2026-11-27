# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `levels/HallsBossLevel.java` seal/unseal plus Yog-Dzewa's
death, with the multiplayer party prompt the other sealed arenas use.

SPD seals the arena as soon as the hero stands 2+ tiles from the entrance:
the entrance stops being stairs, LockedFloor starts and Yog-Dzewa appears at
exit + 3 rows. Nobody can go back up until Yog dies. In a party, the player
who would trigger the seal is held at the entrance and asks the others
first; whoever declines is sent back up to floor 24 before the seal, and
anyone arriving while it is sealed is locked in with the fight.
"""

import uuid
from typing import List

from app.engine.dungeon.constants import TileType
from app.engine.dungeon.spd_levelgen.halls_boss_layout import (
    get_center_piece_visuals, get_center_piece_walls,
)
from app.engine.entities.base import Faction, Position
from app.engine.entities.mobs import YogDzewa
from app.engine.game.ai_yog_dzewa import (
    MINION_TYPES, _get_spawners_alive, find_yog, init_yog_decks, update_visibility, yog_flush,
)
from app.engine.game.constants import YOG_SCORE_BASE, YOG_SCORE_PER_SPAWNER, YOG_VIEW_DISTANCE
from app.engine.game.floor_state import FloorState
from app.engine.game.locked_floor import clear_locked_floor, lock_duration

YOG_FLOOR = 25
NEIGHBOURS8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def is_yog_floor(floor: FloorState) -> bool:
    return floor is not None and floor.floor_id == YOG_FLOOR and floor.yog_pos is not None


def _entrance(floor: FloorState):
    return floor.entrance_pos or (16, 26)


def _exit(floor: FloorState):
    return floor.exit_pos or (16, 9)


def fight_pending(floor: FloorState) -> bool:
    """`map[entrance] == ENTRANCE && map[exit] != EXIT`."""
    if floor.generation_meta.get("yog_sealed") or floor.generation_meta.get("yog_defeated"):
        return False
    ex, ey = _entrance(floor)
    return floor.grid[ey][ex] == TileType.STAIRS_UP


def init_yog_floor(floor: FloorState) -> None:
    """HallsBossLevel initialiser: `viewDistance = min(4, viewDistance)`."""
    if is_yog_floor(floor):
        floor.view_distance = YOG_VIEW_DISTANCE


def _alive_players(game, floor_id: int) -> List:
    return [p for p in game._players_on_floor(floor_id) if p.is_alive and not p.is_downed]


# --- seal ---------------------------------------------------------------------

def maybe_seal(game, player, floor: FloorState, floor_id: int) -> None:
    """`HallsBossLevel.occupyCell`: seal once a hero is 2+ tiles from the entrance."""
    if not is_yog_floor(floor) or not fight_pending(floor):
        return
    ex, ey = _entrance(floor)
    if max(abs(player.pos.x - ex), abs(player.pos.y - ey)) < 2:
        return
    if floor.generation_meta.get("yog_prompt"):
        _hold_at_entrance(player, floor)
        return
    others = [p for p in _alive_players(game, floor_id) if p.id != player.id]
    if others:
        _hold_at_entrance(player, floor)
        _start_prompt(game, player, floor, others)
        return
    seal(game, floor, floor_id)


def _hold_at_entrance(player, floor: FloorState) -> None:
    ex, ey = _entrance(floor)
    player.pos = Position(x=ex, y=ey - 1)
    player.movement.stop()
    player.movement.path_queue.clear()


def seal(game, floor: FloorState, floor_id: int) -> None:
    """`HallsBossLevel.seal()`."""
    if not fight_pending(floor):
        return
    _close_prompts(game, floor)
    floor.generation_meta["yog_sealed"] = True
    game.qualified_for_boss_challenge = True

    ex, ey = _entrance(floor)
    floor.grid[ey][ex] = TileType.FLOOR_WOOD
    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": [{"x": ex, "y": ey, "tile": TileType.FLOOR_WOOD}]}, floor_id=floor_id)
    game.add_event("YOG_ARENA_SEALED", {"x": ex, "y": ey}, floor_id=floor_id)

    left = lock_duration(game)
    for p in game._players_on_floor(floor_id):
        p.locked_floor_left = left

    bx, by = floor.yog_pos
    occupant = next((c for c in list(game._players_on_floor(floor_id)) + list(floor.mobs.values())
                     if c.is_alive and (c.pos.x, c.pos.y) == (bx, by)), None)
    if occupant is not None:
        taken = {(c.pos.x, c.pos.y) for c in list(game._players_on_floor(floor_id)) + list(floor.mobs.values())
                 if c.is_alive}
        free = [(bx + dx, by + dy) for dx, dy in NEIGHBOURS8 if (bx + dx, by + dy) not in taken]
        import random
        dest = random.choice(free) if free else (bx, by + 2)
        occupant.pos = Position(x=dest[0], y=dest[1])
        game.add_event("PUSH", {"target": occupant.id, "x": dest[0], "y": dest[1],
                                "from_x": bx, "from_y": by}, floor_id=floor_id)

    yog = YogDzewa(id=str(uuid.uuid4()), pos=Position(x=bx, y=by), faction=Faction.DUNGEON)
    yog.floor_id = floor_id
    init_yog_decks(game, yog)
    floor.mobs[yog.id] = yog
    game._invalidate_fov_cache()


# --- party prompt -----------------------------------------------------------

def _start_prompt(game, initiator, floor: FloorState, others) -> None:
    floor.generation_meta["yog_prompt"] = {
        "initiator_id": initiator.id,
        "initiator_name": initiator.name,
        "approved": {initiator.id},
        "declined": set(),
        "pending": {p.id for p in others},
    }
    for p in others:
        game.add_event("YOG_JOIN_PROMPT", {"initiator_id": initiator.id, "initiator_name": initiator.name},
                       player_id=p.id)
    _emit_status(game, floor)


def _emit_status(game, floor: FloorState) -> None:
    prompt = floor.generation_meta.get("yog_prompt")
    if not prompt or prompt["initiator_id"] not in game.players:
        return

    def names(ids, skip_initiator=False):
        return [game.players[pid].name for pid in ids
                if pid in game.players and game.players[pid].is_alive
                and not (skip_initiator and pid == prompt["initiator_id"])]

    declined = names(prompt["declined"])
    game.add_event("YOG_PARTY_STATUS", {
        "initiator_id": prompt["initiator_id"],
        "pending_names": names(prompt["pending"]),
        "declined_names": declined,
        "approved_names": names(prompt["approved"], skip_initiator=True),
        "can_decide": len(declined) > 0,
    }, player_id=prompt["initiator_id"])


def _close_prompts(game, floor: FloorState) -> None:
    prompt = floor.generation_meta.pop("yog_prompt", None)
    if not prompt:
        return
    ids = set(prompt["approved"]) | set(prompt["declined"]) | set(prompt["pending"]) | {prompt["initiator_id"]}
    for pid in ids:
        if pid in game.players:
            game.add_event("YOG_PROMPT_CLOSE", {}, player_id=pid)


def respond_yog_join(game, player_id: str, approve: bool) -> None:
    player = game.players.get(player_id)
    floor = game.floors.get(YOG_FLOOR)
    if not player or player.floor_id != YOG_FLOOR or floor is None or not fight_pending(floor):
        return
    prompt = floor.generation_meta.get("yog_prompt")
    if not prompt or player_id == prompt["initiator_id"]:
        return
    prompt["pending"].discard(player_id)
    if approve:
        prompt["declined"].discard(player_id)
        prompt["approved"].add(player_id)
    else:
        prompt["approved"].discard(player_id)
        prompt["declined"].add(player_id)
    game.add_event("YOG_PROMPT_CLOSE", {}, player_id=player_id)

    alive = {p.id for p in _alive_players(game, YOG_FLOOR)}
    for key in ("pending", "declined", "approved"):
        prompt[key] &= alive
    if not prompt["pending"] and not prompt["declined"]:
        seal(game, floor, YOG_FLOOR)
    else:
        _emit_status(game, floor)


def decide_yog_start(game, player_id: str, action: str) -> None:
    floor = game.floors.get(YOG_FLOOR)
    if floor is None or not fight_pending(floor):
        return
    prompt = floor.generation_meta.get("yog_prompt")
    if not prompt or player_id != prompt["initiator_id"]:
        return
    if action == "wait":
        _close_prompts(game, floor)
        return
    if action == "start_without":
        approved = set(prompt["approved"])
        for p in _alive_players(game, YOG_FLOOR):
            if p.id not in approved:
                _send_up(game, p)
        seal(game, floor, YOG_FLOOR)


def _send_up(game, player) -> None:
    game._move_player_to_floor(player, YOG_FLOOR - 1, TileType.STAIRS_DOWN)
    game.add_event("STAIRS_UP", {"player": player.id}, player_id=player.id)


# --- death / unseal -------------------------------------------------------------

def on_yog_death(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> None:
    """`YogDzewa.die()` + `HallsBossLevel.unseal()`."""
    yog_flush(game, yog, floor, floor_id)
    for m in list(floor.mobs.values()):
        if m.is_alive and isinstance(m, MINION_TYPES):
            m.is_alive = False
            m.hp = 0
            game.add_event("DEATH", {"target": m.id}, floor_id=floor_id)
    update_visibility(game, None, floor, floor_id)
    game.add_event("BOSS_SLAIN", {"mob": yog.id, "depth": floor_id, "badge_image": 18}, floor_id=floor_id)
    spawners = _get_spawners_alive(game)
    if not ("stronger_bosses" in getattr(game, "challenges", set()) and spawners == 4):
        game.qualified_for_boss_challenge = False
    elif game.qualified_for_boss_challenge:
        game.add_event("YOG_DZEWA_BADGE_QUALIFIED", {}, floor_id=floor_id)
    game.boss_scores[4] += YOG_SCORE_BASE + YOG_SCORE_PER_SPAWNER * spawners
    unseal(game, floor, floor_id)
    game.add_event("BOSS_YELL", {"mob": yog.id, "key": "mobText.yog_defeated", "text": "...",
                                 "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)


def unseal(game, floor: FloorState, floor_id: int) -> None:
    floor.generation_meta["yog_sealed"] = False
    floor.generation_meta["yog_defeated"] = True
    clear_locked_floor(game, floor_id)
    ex, ey = _entrance(floor)
    xx, xy = _exit(floor)
    floor.grid[ey][ex] = TileType.STAIRS_UP
    floor.grid[xy][xx] = TileType.STAIRS_DOWN
    _set_centre_piece(floor, unsealed=True)
    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": [
        {"x": ex, "y": ey, "tile": TileType.STAIRS_UP},
        {"x": xx, "y": xy, "tile": TileType.STAIRS_DOWN},
    ]}, floor_id=floor_id)
    game.add_event("YOG_SHADOW_BURST", {"cells": [[xx - 1, xy, 25], [xx, xy, 100], [xx + 1, xy, 25]]},
                   floor_id=floor_id)
    game.add_event("YOG_ARENA_UNSEALED", {"custom_tiles": floor.custom_tiles,
                                          "custom_walls": floor.custom_walls}, floor_id=floor_id)


def _set_centre_piece(floor: FloorState, unsealed: bool) -> None:
    for layer in floor.custom_tiles:
        if layer.get("texture") == "halls_special":
            layer["tiles"] = get_center_piece_visuals(unsealed=unsealed)
    for layer in floor.custom_walls:
        if layer.get("texture") == "halls_special":
            layer["tiles"] = get_center_piece_walls(unsealed=unsealed)


def reset_arena(game, floor: FloorState, floor_id: int) -> None:
    """Public room only: put a won arena back to its unsealed, Yog-less start."""
    floor.generation_meta["yog_defeated"] = False
    floor.generation_meta["yog_sealed"] = False
    xx, xy = _exit(floor)
    floor.grid[xy][xx] = TileType.WALL_DECO
    ex, ey = _entrance(floor)
    floor.grid[ey][ex] = TileType.STAIRS_UP
    _set_centre_piece(floor, unsealed=False)
    floor.view_distance = YOG_VIEW_DISTANCE
    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": [
        {"x": xx, "y": xy, "tile": TileType.WALL_DECO},
        {"x": ex, "y": ey, "tile": TileType.STAIRS_UP},
    ]}, floor_id=floor_id)


def flush_floor(game, floor: FloorState, floor_id: int) -> None:
    """Applies queued damage side effects (phase changes, fist spawns,
    teleports, LockedFloor) before the turn-room dungeon phase acts, as SPD
    applies them inside `damage()` the moment the hit lands."""
    if not is_yog_floor(floor):
        return
    from app.engine.game.ai_yog_fists import fist_flush
    yog = find_yog(floor)
    if yog is not None:
        yog_flush(game, yog, floor, floor_id)
    for m in list(floor.mobs.values()):
        if m.is_alive and getattr(m, "fist_kind", ""):
            fist_flush(game, m, floor, floor_id)
