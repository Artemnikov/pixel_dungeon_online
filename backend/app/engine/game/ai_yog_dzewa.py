# Copyright (C) 2026 ArtemNikov
#
"""Port of SPD `actors/mobs/YogDzewa.java`: Yog-Dzewa's act, fist and minion
summons, and the phase changes driven by damage.

Yog acts once per SPD turn of its own time (game/spd_act_clock.py) in both
room modes. Damage is taken in `YogDzewa.take_damage` (entities/mobs/
halls.py); the side effects SPD runs inside `damage()` that need the game --
spawning the next fist, darkening the arena, extending LockedFloor -- are
queued there and drained by `yog_flush`, which runs every real-time tick and
at the start of every turn-room dungeon phase.

Multiplayer: Yog aims at its chosen target (the nearest player it can see);
"in the hero's FOV" checks use every player's FOV.
"""

import math
import random
from typing import List, Optional, Tuple

from app.engine.dungeon.dungeon_seed import seed_for_depth
from app.engine.dungeon.spd_random import SPDRandom
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import normal_float, normal_int_range
from app.engine.entities.buffs import is_rooted
from app.engine.entities.mobs import (
    BrightFist, BurningFist, DarkFist, DemonSpawner, Larva, RottingFist,
    RustedFist, SoiledFist, YogDzewa, YogEye, YogRipper, YogScorpio,
)
from app.engine.entities.mobs.universal import Bee
from app.engine.game import spd_act_clock
from app.engine.game.boss_targets import (
    arena_players, hero_cooldown_turns, interrupt, mob_fov, spend_gate, union_hero_fov,
)
from app.engine.game.constants import (
    YOG_BEAM_HP_PER_EXTRA, YOG_CHARGE_SPEND_MAX, YOG_CHARGE_SPEND_MIN,
    YOG_FINAL_SUMMON_BURST, YOG_FIST_SPAWN_DELAY, YOG_MAX_ABILITY_CD,
    YOG_MAX_SUMMON_CD, YOG_MIN_ABILITY_CD, YOG_MIN_SUMMON_CD,
    YOG_PHASE5_ABILITY_CAP, YOG_PHASE5_SUMMON_CAP,
    YOG_RAY_DMG, YOG_RAY_DMG_STRONG, YOG_RAY_SCORE_PENALTY,
    YOG_SUMMON_LOOP_GUARD, YOG_TARGETED_CELL_COLOR, YOG_TARGETED_CELL_FADE_MS,
    YOG_VIEW_DISTANCE,
)
from app.engine.game.floor_state import FloorState
from app.engine.game.locked_floor import add_locked_floor_time, is_stronger
from app.engine.systems.spd_ballistica import WONT_STOP, Ballistica, char_lookup

Cell = Tuple[int, int]

# SPD PathFinder.NEIGHBOURS8 / NEIGHBOURS9 order.
NEIGHBOURS8 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
NEIGHBOURS9 = ((-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1))

FIST_CLASSES = {
    "BurningFist": BurningFist, "SoiledFist": SoiledFist,
    "RottingFist": RottingFist, "RustedFist": RustedFist,
    "BrightFist": BrightFist, "DarkFist": DarkFist,
}
MINION_CLASSES = {"Larva": Larva, "YogRipper": YogRipper, "YogEye": YogEye, "YogScorpio": YogScorpio}
MINION_TYPES = (Larva, YogRipper, YogEye, YogScorpio)

_PAIRS = {
    "BurningFist": "SoiledFist", "SoiledFist": "BurningFist",
    "RottingFist": "RustedFist", "RustedFist": "RottingFist",
    "BrightFist": "DarkFist", "DarkFist": "BrightFist",
}


def _true_distance(a: Cell, b: Cell) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _yell(game, yog, key: str, text: str, floor_id: int) -> None:
    game.add_event("BOSS_YELL", {"mob": yog.id, "key": key, "text": text,
                                 "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)


# --- summon decks ---------------------------------------------------------

def build_fist_schedule(challenged: bool, rng: Optional[SPDRandom] = None) -> Tuple[List[str], List[str]]:
    """The `fistSummons` / `challengeSummons` initialiser, on the depth-seeded RNG."""
    if rng is None:
        rng = SPDRandom()
    fists = [
        "BurningFist" if rng.IntMax(2) == 0 else "SoiledFist",
        "RottingFist" if rng.IntMax(2) == 0 else "RustedFist",
        "BrightFist" if rng.IntMax(2) == 0 else "DarkFist",
    ]
    rng.shuffle(fists)
    if rng.IntMax(2) == 0:
        challenge = [_PAIRS[fists[1]], _PAIRS[fists[2]], _PAIRS[fists[0]]]
    else:
        challenge = [_PAIRS[fists[2]], _PAIRS[fists[0]], _PAIRS[fists[1]]]
    return fists, (challenge if challenged else [])


def build_regular_summons(spawners_alive: int, challenged: bool) -> List[type]:
    """The `regularSummons` initialiser, driven by Statistics.spawnersAlive."""
    summons = []
    if challenged:
        for i in range(6):
            if i >= 4:
                summons.append(YogRipper)
            elif i >= spawners_alive:
                summons.append(Larva)
            else:
                summons.append(YogEye if i % 2 == 0 else YogScorpio)
    else:
        for i in range(4):
            summons.append(Larva if i >= spawners_alive else YogRipper)
    random.shuffle(summons)
    return summons


def _get_spawners_alive(game) -> int:
    """Statistics.spawnersAlive: Demon Spawners still alive on floors 21-24."""
    count = 0
    for fid in (21, 22, 23, 24):
        f = game.floors.get(fid)
        if f:
            count += sum(1 for m in f.mobs.values() if isinstance(m, DemonSpawner) and m.is_alive)
    return count


def init_yog_decks(game, yog: YogDzewa) -> None:
    challenged = is_stronger(game)
    rng = SPDRandom()
    master = getattr(game, "master_seed", None)
    if master is not None:
        rng.push_generator(seed_for_depth(master, 25) + 1)
    fists, challenge = build_fist_schedule(challenged, rng)
    yog.fist_order = fists
    yog.challenge_summons = challenge
    yog.regular_summons = [c.__name__ for c in build_regular_summons(_get_spawners_alive(game), challenged)]
    yog.stronger = challenged


# --- visibility -----------------------------------------------------------

def update_visibility(game, yog: Optional[YogDzewa], floor: FloorState, floor_id: int) -> None:
    """`YogDzewa.updateVisibility`: 4, then 3/2/1/1 as phases advance."""
    vd = YOG_VIEW_DISTANCE
    if yog is not None and yog.phase > 1 and yog.is_alive:
        vd = max(YOG_VIEW_DISTANCE - (yog.phase - 1), 1)
    if floor.view_distance != vd:
        floor.view_distance = vd
        game._invalidate_fov_cache()
    game.add_event("YOG_VIEW_DISTANCE", {"view_distance": vd}, floor_id=floor_id)


# --- driver ---------------------------------------------------------------

def _update_yog_dzewa(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> bool:
    yog_flush(game, yog, floor, floor_id)
    spd_act_clock.run(game, yog, lambda: yog_act(game, yog, floor, floor_id))
    yog_flush(game, yog, floor, floor_id)
    return True


def yog_flush(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> None:
    """Applies what `YogDzewa.damage()` does beyond HP and cooldowns."""
    yog.stronger = is_stronger(game)
    if floor.generation_meta.get("yog_sealed"):
        from app.engine.game.locked_floor import lock_duration
        for p in game._players_on_floor(floor_id):
            if p.is_alive and p.locked_floor_left is None:
                p.locked_floor_left = lock_duration(game)
    while yog.pending_phase_ups > 0:
        yog.pending_phase_ups -= 1
        _phase_up(game, yog, floor, floor_id)
    if yog.locked_floor_credit > 0:
        add_locked_floor_time(game, floor_id, yog.locked_floor_credit)
        yog.locked_floor_credit = 0.0
    while yog.status_popups:
        kind = yog.status_popups.pop(0)
        game.add_event("STATUS_TEXT", {"target": yog.id, "key": f"status.{kind}",
                                       "kind": "positive", "x": yog.pos.x, "y": yog.pos.y},
                       floor_id=floor_id)


def _phase_up(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> None:
    update_visibility(game, yog, floor, floor_id)
    game.add_event("MESSAGE", {"key": "mob.yog_dzewa.darkness",
                               "text": "The darkness pulls in closer..."}, floor_id=floor_id)
    game.add_event("STATUS_TEXT", {"target": yog.id, "key": "status.invulnerable",
                                   "kind": "positive", "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)
    game.add_event("YOG_PHASE_CHANGE", {"mob": yog.id, "phase": yog.phase,
                                        "view_distance": floor.view_distance}, floor_id=floor_id)
    if yog.fist_order:
        add_fist(game, yog, floor, floor_id, yog.fist_order.pop(0))
    if yog.stronger and yog.challenge_summons:
        add_fist(game, yog, floor, floor_id, yog.challenge_summons.pop(0))
    _shadow_burst(game, floor, floor_id)
    yog.ability_cooldown = max(yog.ability_cooldown, 5.0)
    yog.summon_cooldown = max(yog.summon_cooldown, 5.0)


def _shadow_burst(game, floor: FloorState, floor_id: int) -> None:
    ex, ey = floor.exit_pos or (16, 9)
    game.add_event("YOG_SHADOW_BURST", {"cells": [[ex - 1, ey, 25], [ex, ey, 100], [ex + 1, ey, 25]]},
                   floor_id=floor_id)


def _is_sheep(ch) -> bool:
    return ch is not None and hasattr(ch, "buffs") and ch.has_buff("sheep_timer")


def add_fist(game, yog: YogDzewa, floor: FloorState, floor_id: int, cls_name: str) -> None:
    """`YogDzewa.addFist`."""
    cls = FIST_CLASSES[cls_name]
    ex, ey = floor.exit_pos or (16, 9)
    lookup = char_lookup(game, floor, floor_id)
    target = (ex, ey + 1)

    def free(c):
        ch = lookup(*c)
        return ch is None or _is_sheep(ch)

    pos = (ex, ey)
    if not yog.stronger and free(target):
        pos = target
    elif free((target[0] - 1, target[1])):
        pos = (target[0] - 1, target[1])
    elif free((target[0] + 1, target[1])):
        pos = (target[0] + 1, target[1])
    elif free(target):
        pos = target
    occupant = lookup(*pos)
    if _is_sheep(occupant):
        occupant.is_alive = False
        game.add_event("DEATH", {"target": occupant.id}, floor_id=floor_id)
        game.handle_mob_death(occupant, floor, floor_id)

    _shadow_burst(game, floor, floor_id)
    yog.ability_cooldown = max(yog.ability_cooldown, 5.0)
    yog.summon_cooldown = max(yog.summon_cooldown, 5.0)

    fist = game._spawn_mob_at(cls, pos[0], pos[1], floor_id)
    fist.yog_id = yog.id
    fist.yog_pos = (yog.pos.x, yog.pos.y)
    fist.ai_state = "hunting"
    fist.stronger = yog.stronger
    spd_act_clock.add_with_delay(fist, YOG_FIST_SPAWN_DELAY)
    floor.mobs[fist.id] = fist
    yog.fist_ids.append(fist.id)
    game.add_event("YOG_FIST_SPAWN", {"mob": yog.id, "fist": fist.id, "cls": cls_name,
                                      "x": pos[0], "y": pos[1], "from_x": ex, "from_y": ey},
                   floor_id=floor_id)


def process_fist_death(game, fist, floor: FloorState, floor_id: int) -> None:
    """`YogFist.die` -> `YogDzewa.processFistDeath`."""
    yog = floor.mobs.get(getattr(fist, "yog_id", "")) or find_yog(floor)
    if yog is None:
        return
    yog.fists_alive = sum(1 for m in floor.mobs.values()
                          if m.id in yog.fist_ids and m.is_alive and m.id != fist.id)
    if yog.phase == 4 and yog.fists_alive == 0:
        _yell(game, yog, "mob.yog_dzewa.hope", "YOUR. HOPE. IS. AN. ILLUSION!", floor_id)
        yog.summon_cooldown = YOG_FINAL_SUMMON_BURST
        yog.phase = 5
        game.add_event("YOG_FINAL_PHASE", {"mob": yog.id}, floor_id=floor_id)


def find_yog(floor: FloorState) -> Optional[YogDzewa]:
    return next((m for m in floor.mobs.values() if isinstance(m, YogDzewa) and m.is_alive), None)


# --- the act --------------------------------------------------------------

def _notice(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> None:
    """`YogDzewa.notice()` the first time a hero sees Yog."""
    _yell(game, yog, "mob.yog_dzewa.notice", "I. SEE. YOU.", floor_id)
    game.add_event("YOG_FIGHT_STARTED", {"mob": yog.id}, floor_id=floor_id)
    if yog.phase == 0:
        yog.phase = 1
        yog.fight_started = True
        yog.summon_cooldown = normal_float(YOG_MIN_SUMMON_CD, YOG_MAX_SUMMON_CD)
        yog.ability_cooldown = normal_float(YOG_MIN_ABILITY_CD, YOG_MAX_ABILITY_CD)


def _choose_target(game, yog: YogDzewa, floor: FloorState, floor_id: int):
    fov = mob_fov(game, yog, floor_id)
    best, best_d = None, None
    for p in arena_players(game, floor_id):
        if p.invisible > 0 or (p.pos.x, p.pos.y) not in fov:
            continue
        d = _true_distance((p.pos.x, p.pos.y), (yog.pos.x, yog.pos.y))
        if best is None or d < best_d:
            best, best_d = p, d
    if best is None:
        best = game._find_nearest_player(yog.pos, floor_id)
    return best


def yog_act(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> float:
    if yog.phase == 0:
        if (yog.pos.x, yog.pos.y) in union_hero_fov(game, floor_id):
            _notice(game, yog, floor, floor_id)
    if yog.phase == 0:
        return 1.0

    target = _choose_target(game, yog, floor, floor_id)
    spent = 1.0

    beam_target = (game.players.get(yog.beam_target_id) or target) if yog.targeted_cells else None
    if yog.targeted_cells and not (beam_target is not None and is_rooted(beam_target)):
        _fire_beams(game, yog, floor, floor_id)

    if yog.ability_cooldown <= 0 and target is not None:
        spent = _charge_beams(game, yog, target, floor, floor_id)

    guard = 0
    while yog.summon_cooldown <= 0 and guard < YOG_SUMMON_LOOP_GUARD:
        guard += 1
        if not _summon(game, yog, target, floor, floor_id):
            break

    if yog.summon_cooldown > 0:
        yog.summon_cooldown -= 1
    if yog.ability_cooldown > 0:
        yog.ability_cooldown -= 1
    if yog.phase == 5 and yog.ability_cooldown > YOG_PHASE5_ABILITY_CAP:
        yog.ability_cooldown = YOG_PHASE5_ABILITY_CAP
    if yog.phase == 5 and yog.summon_cooldown > YOG_PHASE5_SUMMON_CAP:
        yog.summon_cooldown = YOG_PHASE5_SUMMON_CAP
    return spent


def _fire_beams(game, yog: YogDzewa, floor: FloorState, floor_id: int) -> None:
    lookup = char_lookup(game, floor, floor_id)
    affected = []
    seen = set()
    ends = []
    patches = []
    src = (yog.pos.x, yog.pos.y)
    for cell in yog.targeted_cells:
        b = Ballistica(src, tuple(cell), WONT_STOP, floor, lookup)
        ends.append(list(b.collision_pos))
        for x, y in b.path:
            ch = lookup(x, y)
            if ch is not None and ch.id not in seen and ch.id != yog.id and (
                    ch.faction != yog.faction or isinstance(ch, Bee)):
                seen.add(ch.id)
                affected.append(ch)
            if floor.flags and floor.flags.flamable[y][x]:
                floor.grid[y][x] = TileType.EMBERS
                patches.append({"x": x, "y": y, "tile": TileType.EMBERS})
                floor.rebuild_flags()

    game.add_event("YOG_DEATH_RAY", {"mob": yog.id, "sx": yog.pos.x, "sy": yog.pos.y,
                                     "ends": ends, "hits": [c.id for c in affected]}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "RAY", "x": yog.pos.x, "y": yog.pos.y}, floor_id=floor_id)
    if patches:
        game.add_event("MAP_PATCH", {"tiles": patches}, floor_id=floor_id)
    for ch in affected:
        if ch.type == "player":
            game.boss_scores[4] -= YOG_RAY_SCORE_PENALTY
        if hasattr(ch, "has_buff") and ch.has_buff("focus"):
            game.add_event("MISS", {"source": yog.id, "target": ch.id,
                                    "defense_verb": getattr(ch, "defense_verb", "dodged")}, floor_id=floor_id)
            continue
        dmg = normal_int_range(*(YOG_RAY_DMG_STRONG if yog.stronger else YOG_RAY_DMG))
        taken = ch.take_damage(dmg)
        game.add_event("ATTACK", {"source": yog.id, "target": ch.id, "damage": taken,
                                  "surprise": False, "crit": False, "grim_proc": False}, floor_id=floor_id)
        if taken:
            game.add_event("DAMAGE", {"target": ch.id, "amount": taken, "x": ch.pos.x, "y": ch.pos.y,
                                      "source_x": yog.pos.x, "source_y": yog.pos.y}, floor_id=floor_id)
        if ch.type != "player" and not ch.is_alive:
            from app.engine.game.dot_death import finish_dot_kill
            finish_dot_kill(game, ch, floor_id)
    yog.targeted_cells = []
    yog.beam_target_id = ""


def _charge_beams(game, yog: YogDzewa, target, floor: FloorState, floor_id: int) -> float:
    lookup = char_lookup(game, floor, floor_id)
    src = (yog.pos.x, yog.pos.y)
    hero = (target.pos.x, target.pos.y)
    beams = 1 + (yog.max_hp - yog.hp) // YOG_BEAM_HP_PER_EXTRA
    affected = set()
    targets: List[Cell] = list(tuple(c) for c in yog.targeted_cells)
    for i in range(beams):
        cell = hero
        if i != 0:
            while True:
                dx, dy = NEIGHBOURS8[random.randint(0, 7)]
                cell = (hero[0] + dx, hero[1] + dy)
                if not (_true_distance(src, hero) > _true_distance(src, cell)):
                    break
        targets.append(cell)
        affected.update(Ballistica(src, cell, WONT_STOP, floor, lookup).path)

    flags = floor.flags
    all_adj = True
    for dx, dy in NEIGHBOURS9:
        c = (hero[0] + dx, hero[1] + dy)
        in_map = 0 <= c[0] < floor.width and 0 <= c[1] < floor.height
        if in_map and c not in affected and flags.passable[c[1]][c[0]]:
            all_adj = False
            break
    if all_adj and targets:
        targets.pop()

    cells = set()
    for cell in targets:
        cells.update(Ballistica(src, cell, WONT_STOP, floor, lookup).path)
    yog.targeted_cells = targets
    yog.beam_target_id = target.id
    game.add_event("YOG_TARGETED_CELLS", {"mob": yog.id, "cells": [list(c) for c in cells],
                                          "color": YOG_TARGETED_CELL_COLOR,
                                          "duration_ms": YOG_TARGETED_CELL_FADE_MS}, floor_id=floor_id)
    spent = spend_gate(hero_cooldown_turns(game, target), YOG_CHARGE_SPEND_MIN, YOG_CHARGE_SPEND_MAX)
    interrupt(game, target)
    yog.ability_cooldown += normal_float(YOG_MIN_ABILITY_CD, YOG_MAX_ABILITY_CD)
    yog.ability_cooldown -= (yog.phase - 1)
    return spent


def _beckon(game, mob, cell: Cell) -> None:
    """`Mob.beckon(cell)`: wander toward the cell unless already hunting."""
    if mob.ai_state != "hunting":
        mob.ai_state = "wandering"
    targets = getattr(game, "_mob_wander_targets", None)
    if targets is None:
        targets = game._mob_wander_targets = {}
    targets[mob.id] = tuple(cell)


def _summon(game, yog: YogDzewa, target, floor: FloorState, floor_id: int) -> bool:
    if not yog.regular_summons:
        yog.regular_summons = [c.__name__ for c in build_regular_summons(_get_spawners_alive(game), yog.stronger)]
    name = yog.regular_summons.pop(0)
    yog.regular_summons.append(name)
    cls = MINION_CLASSES.get(name, Larva)

    lookup = char_lookup(game, floor, floor_id)
    hero = (target.pos.x, target.pos.y) if target is not None else (yog.pos.x, yog.pos.y)
    spawn = None
    for dx, dy in NEIGHBOURS8:
        c = (yog.pos.x + dx, yog.pos.y + dy)
        if lookup(*c) is None and (spawn is None or _true_distance(hero, spawn) > _true_distance(hero, c)):
            spawn = c
    if spawn is None:
        for dx, dy in NEIGHBOURS8:
            c = (yog.pos.x + dx, yog.pos.y + dy)
            if _is_sheep(lookup(*c)) and (spawn is None or _true_distance(hero, spawn) > _true_distance(hero, c)):
                spawn = c
        if spawn is not None:
            sheep = lookup(*spawn)
            sheep.is_alive = False
            game.add_event("DEATH", {"target": sheep.id}, floor_id=floor_id)
            game.handle_mob_death(sheep, floor, floor_id)
    if spawn is None:
        return False

    minion = game._spawn_mob_at(cls, spawn[0], spawn[1], floor_id)
    _beckon(game, minion, hero)
    floor.mobs[minion.id] = minion
    game.add_event("MOB_SPAWN", {"mob": minion.id, "cls": name, "x": spawn[0], "y": spawn[1],
                                 "from_x": yog.pos.x, "from_y": yog.pos.y}, floor_id=floor_id)

    yog.summon_cooldown += normal_float(YOG_MIN_SUMMON_CD, YOG_MAX_SUMMON_CD)
    yog.summon_cooldown -= (yog.phase - 1)
    if yog.fists_alive > 0:
        yog.summon_cooldown += YOG_MIN_SUMMON_CD - (yog.phase - 1)
    return True
