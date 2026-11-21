# Copyright (C) 2026 ArtemNikov
#
"""Port of the complete King of Dwarves boss fight from Shattered Pixel Dungeon
(actors/mobs/DwarfKing.java, levels/CityBossLevel.java).

Mechanics & Phases:
- Entrance & Sealing: When a player enters the arena past (7, 37), the door locks,
  the fight starts, boss yells notice, and players gain LockedFloor (no rest regen).
- Phase 1 (HP > 50 / > 100 with challenge): Active melee combat. Cooldowns
  accelerate when the King takes damage. Uses Pedestal Summoning (Ghouls, Monks,
  Warlocks, Golems) and Special Abilities (Life Link damage sharing, Teleport
  Subject repositioning).
- Phase 2 (HP <= 50 / <= 100): King retreats to throne at (7, 31), becomes IMMOVABLE
  and immune to direct damage behind a barrier equal to his max HP. Spawns 3 scripted
  minion waves gated on the barrier (Wave 1: Ghouls; Wave 2: Ghouls + Monk/Warlock;
  Wave 3: Warlock + Monk + Ghouls; Golems only with stronger bosses). Each Phase 2
  minion (KingDamager) that dies or stops being hostile deals HT/12 to the barrier.
- Phase 3 (Barrier <= 0): King enrages, leaves the throne, and enters Viscosity
  deferred damage mode. Continues rapid pedestal summoning. Damage dealt to King
  bleeds over time until defeat.
- Defeat: King drops King's Crown, unseals arena doors (7, 37) and (7, 25), clears
  remaining minions, upgrades Lloyd's Beacon, cleanses degrade, and opens Imp shop.
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position, Shield, normal_int_range
from app.engine.entities.mobs import DKGhoul, DKGolem, DKMonk, DKWarlock, DwarfKing, Ghoul, Golem, Monk, Warlock
from app.engine.entities.player import Mob as MobEntity, Player
from app.engine.game.constants import DK_IDLE_CLOCK_MULTIPLIER, TICKS_PER_TURN
from app.engine.game.floor_state import FloorState

THRONE_POS = (7, 31)
PEDESTAL_POSITIONS: List[Tuple[int, int]] = [(4, 28), (10, 28), (10, 34), (4, 34)]
BOTTOM_DOOR_POS = (7, 37)
TOP_DOOR_POS = (7, 25)

DK_MINION_CLASSES = {
    "DKGhoul": DKGhoul,
    "DKMonk": DKMonk,
    "DKWarlock": DKWarlock,
    "DKGolem": DKGolem,
}

# Dialogue quotes (1-1 faithful to SPD actors.properties)
YELL_NOTICE = "How dare you! You have no idea what you're interfering with!"
YELL_LIFELINK_1 = "I have need of your essence, slave!"
YELL_LIFELINK_2 = "Bleed for me, slave!"
YELL_TELEPORT_1 = "Deal with them, slave!"
YELL_TELEPORT_2 = "Keep them busy, slave!"
YELL_WAVE_1 = "Enough! Arise my slaves!"
YELL_WAVE_2 = "More! Bleed for your king!"
YELL_WAVE_3 = "Useless! KILL THEM NOW!"
YELL_ENRAGED_TEMPLATE = "You cannot kill me {name}. I. AM. IMMORTAL!"
YELL_LOSING = "No! You can't do this... you have no idea what lies below..."
YELL_DEFEATED = "You've... Doomed us all..."


# ---------------------------------------------------------------------------
# Arena Sealing & Unsealing + Multiplayer Party Prompt
# ---------------------------------------------------------------------------

def _alive_players_on_city_boss_floor(game, floor_id: int) -> List[Player]:
    return [p for p in game._players_on_floor(floor_id) if p.is_alive]


def _dwarf_king_entry_positions() -> List[Tuple[int, int]]:
    """Candidate entry positions inside the arena past door (7, 37).
    Row y=36, columns 7, 6, 8, 5, 9, 4, 10, then row y=35."""
    row_xs = [7]
    for offset in range(1, 6):
        row_xs.extend([7 - offset, 7 + offset])
    positions: List[Tuple[int, int]] = []
    for y in (36, 35):
        for x in row_xs:
            if 1 <= x <= 13:
                positions.append((x, y))
    return positions


def _teleport_players_to_arena(game, floor: FloorState, floor_id: int, players: list) -> None:
    if not players:
        return
    candidates = _dwarf_king_entry_positions()
    taken = {
        (m.pos.x, m.pos.y) for m in floor.mobs.values() if m.is_alive
    }
    participant_ids = {p.id for p in players}
    for p in game._players_on_floor(floor_id):
        if p.is_alive and p.id not in participant_ids:
            taken.add((p.pos.x, p.pos.y))

    for player in players:
        if not player.is_alive:
            continue
        for nx, ny in candidates:
            if (nx, ny) in taken:
                continue
            from_x, from_y = player.pos.x, player.pos.y
            player.pos.x, player.pos.y = nx, ny
            player.movement.stop()
            player.movement.path_queue.clear()
            taken.add((nx, ny))
            if (from_x, from_y) != (nx, ny):
                game.add_event(
                    "TELEPORT",
                    {"player": player.id, "from_x": from_x, "from_y": from_y, "x": nx, "y": ny},
                    floor_id=floor_id,
                )
            break


def _gather_allies_to_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of CityBossLevel.seal() ally gathering: brings player allies/pets into arena."""
    door_pos = BOTTOM_DOOR_POS  # (7, 37)
    inside_players = [p for p in game._players_on_floor(floor_id) if p.is_alive and 25 <= p.pos.y <= 36]
    lead_pos = inside_players[0].pos if inside_players else Position(x=7, y=36)

    # Find candidate tiles around lead_pos inside arena
    candidates: List[Tuple[int, int]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            cx, cy = lead_pos.x + dx, lead_pos.y + dy
            if (1 <= cx <= 13 and 25 <= cy <= 36
                    and floor.flags and floor.flags.passable[cy][cx]
                    and not any(m.is_alive and m.pos.x == cx and m.pos.y == cy for m in floor.mobs.values())
                    and not any(p.is_alive and p.pos.x == cx and p.pos.y == cy for p in game._players_on_floor(floor_id))):
                candidates.append((cx, cy))

    # Sort candidates by distance to door_pos
    candidates.sort(key=lambda c: (c[0] - door_pos[0]) ** 2 + (c[1] - door_pos[1]) ** 2)

    for m in list(floor.mobs.values()):
        if not m.is_alive or m.faction != "player":
            continue
        # If ally is outside the arena, teleport them into arena
        if m.pos.y > 36 or m.pos.y < 25:
            if candidates:
                dest = candidates.pop(0)
                from_x, from_y = m.pos.x, m.pos.y
                m.pos = Position(x=dest[0], y=dest[1])
                game.add_event(
                    "TELEPORT",
                    {"player": m.id, "from_x": from_x, "from_y": from_y, "x": dest[0], "y": dest[1]},
                    floor_id=floor_id,
                )


def _fight_pending(floor: FloorState) -> bool:
    """CityBossLevel.occupyCell() seal precondition: bottom door open, top door still locked."""
    tx, ty = TOP_DOOR_POS
    return (not floor.generation_meta.get("dwarf_king_sealed", False)
            and floor.grid[ty][tx] == TileType.LOCKED_DOOR)


def _maybe_initiate_dwarf_king_door_prompt(game, player: Player, floor: FloorState, x: int, y: int) -> None:
    if floor.floor_id != 20 or not _fight_pending(floor):
        return
    if (x, y) != BOTTOM_DOOR_POS:
        return
    _start_dwarf_king_party_prompt(game, player, floor)


def _start_dwarf_king_party_prompt(game, initiator: Player, floor: FloorState) -> None:
    floor_id = floor.floor_id
    alive_players = _alive_players_on_city_boss_floor(game, floor_id)
    others = [p for p in alive_players if p.id != initiator.id]
    if not others:
        return

    floor.dwarf_king_prompt = {
        "initiator_id": initiator.id,
        "initiator_name": initiator.name,
        "approved": {initiator.id},
        "declined": set(),
        "pending": {p.id for p in others},
    }
    for p in others:
        game.add_event(
            "DWARF_KING_JOIN_PROMPT",
            {"initiator_id": initiator.id, "initiator_name": initiator.name},
            player_id=p.id,
        )
    _emit_dwarf_king_party_status(game, floor)


def _emit_dwarf_king_party_status(game, floor: FloorState) -> None:
    prompt = floor.dwarf_king_prompt
    if not prompt:
        return
    initiator_id = prompt["initiator_id"]
    if initiator_id not in game.players:
        return
    pending_names = [
        game.players[pid].name for pid in prompt["pending"]
        if pid in game.players and game.players[pid].is_alive
    ]
    declined_names = [
        game.players[pid].name for pid in prompt["declined"]
        if pid in game.players and game.players[pid].is_alive
    ]
    approved_names = [
        game.players[pid].name for pid in prompt["approved"]
        if pid != initiator_id and pid in game.players and game.players[pid].is_alive
    ]
    game.add_event(
        "DWARF_KING_PARTY_STATUS",
        {
            "initiator_id": initiator_id,
            "pending_names": pending_names,
            "declined_names": declined_names,
            "approved_names": approved_names,
            "can_decide": len(declined_names) > 0,
        },
        player_id=initiator_id,
    )


def _close_dwarf_king_prompts(game, floor: FloorState) -> None:
    prompt = floor.dwarf_king_prompt
    if not prompt:
        return
    all_ids = set(prompt["approved"]) | set(prompt["declined"]) | set(prompt["pending"]) | {prompt["initiator_id"]}
    floor.dwarf_king_prompt = None
    for pid in all_ids:
        if pid in game.players:
            game.add_event("DWARF_KING_PROMPT_CLOSE", {}, player_id=pid)


def respond_dwarf_king_join(game, player_id: str, approve: bool) -> None:
    player = game.players.get(player_id)
    if not player or player.floor_id != 20:
        return
    floor = game.floors.get(20)
    if not floor or floor.generation_meta.get("dwarf_king_sealed", False) or not floor.dwarf_king_prompt:
        return
    prompt = floor.dwarf_king_prompt
    if player_id == prompt["initiator_id"]:
        return

    prompt["pending"].discard(player_id)
    if approve:
        prompt["declined"].discard(player_id)
        prompt["approved"].add(player_id)
    else:
        prompt["approved"].discard(player_id)
        prompt["declined"].add(player_id)

    game.add_event("DWARF_KING_PROMPT_CLOSE", {}, player_id=player_id)

    alive_ids = {p.id for p in _alive_players_on_city_boss_floor(game, 20)}
    prompt["pending"] &= alive_ids
    prompt["declined"] &= alive_ids
    prompt["approved"] &= alive_ids

    if not prompt["pending"] and not prompt["declined"]:
        participants = [
            p for p in _alive_players_on_city_boss_floor(game, 20)
            if p.id in prompt["approved"]
        ]
        _close_dwarf_king_prompts(game, floor)
        _teleport_and_start_dwarf_king_fight(game, floor, 20, participants)
    else:
        _emit_dwarf_king_party_status(game, floor)


def decide_dwarf_king_start(game, player_id: str, action: str) -> None:
    floor = game.floors.get(20)
    if not floor or floor.generation_meta.get("dwarf_king_sealed", False) or not floor.dwarf_king_prompt:
        return
    prompt = floor.dwarf_king_prompt
    if player_id != prompt["initiator_id"]:
        return

    if action == "wait":
        _close_dwarf_king_prompts(game, floor)
        return

    if action == "start_without":
        approved_ids = set(prompt["approved"])
        participants = [
            p for p in _alive_players_on_city_boss_floor(game, 20)
            if p.id in approved_ids
        ]
        if not participants:
            initiator = game.players.get(player_id)
            if initiator and initiator.is_alive:
                participants = [initiator]
        _close_dwarf_king_prompts(game, floor)
        _teleport_and_start_dwarf_king_fight(game, floor, 20, participants)


def _teleport_and_start_dwarf_king_fight(game, floor: FloorState, floor_id: int, participants: list) -> None:
    if not _fight_pending(floor):
        return
    _teleport_players_to_arena(game, floor, floor_id, participants)
    _dwarf_king_seal_arena(game, floor, floor_id)


def _dwarf_king_maybe_seal_arena(game, player: Player, floor: FloorState, floor_id: int) -> None:
    """Triggered when a player steps into depth 20: seals the arena when the player
    crosses the threshold past the entrance door into the throne room (y <= 36).
    If multiple players are on floor 20 and arena is not sealed, initiates party prompt."""
    if floor_id != 20 or not _fight_pending(floor):
        return

    # Arena is rows 25 to 36, cols 1 to 13 (strictly inside past the door at y=37)
    px, py = player.pos.x, player.pos.y
    if 25 <= py <= 36 and 1 <= px <= 13:
        alive_players = _alive_players_on_city_boss_floor(game, floor_id)
        if len(alive_players) > 1 and not floor.dwarf_king_prompt:
            # Player stepped into arena: if other players on floor, initiate party prompt
            # and pull this player just back to door threshold
            player.pos = Position(x=BOTTOM_DOOR_POS[0], y=BOTTOM_DOOR_POS[1] + 1)
            player.movement.stop()
            player.movement.path_queue.clear()
            _start_dwarf_king_party_prompt(game, player, floor)
            return

        _dwarf_king_seal_arena(game, floor, floor_id)


def _dwarf_king_seal_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of CityBossLevel.seal(): locks the entrance door, alerts the Dwarf King,
    applies LockedFloor to players, teleports allies, and starts the boss fight."""
    floor.generation_meta["dwarf_king_sealed"] = True

    # Close any active prompt
    _close_dwarf_king_prompts(game, floor)

    # Lock the bottom entrance door at (7, 37)
    dx, dy = BOTTOM_DOOR_POS

    # Displace any character standing on the door cell forward into the arena
    for ch in list(game._players_on_floor(floor_id)) + list(floor.mobs.values()):
        if ch.pos.x == dx and ch.pos.y == dy:
            ch.pos = Position(x=dx, y=dy - 1)

    floor.grid[dy][dx] = TileType.LOCKED_DOOR
    floor.locked_doors[(dx, dy)] = "dwarf_king_arena"
    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": [{"x": dx, "y": dy, "tile": TileType.LOCKED_DOOR}]}, floor_id=floor_id)

    # Gather player allies into the arena
    _gather_allies_to_arena(game, floor, floor_id)

    game.qualified_for_boss_challenge = True

    # LockedFloor pauses natural resting HP regeneration (50 turns normal, 20 challenge)
    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    lock_duration = 20.0 if is_stronger else 50.0
    for player in game._players_on_floor(floor_id):
        player.locked_floor_left = lock_duration

    # Notify the Dwarf King mob
    dk = next((m for m in floor.mobs.values() if isinstance(m, DwarfKing) and m.is_alive), None)
    if dk:
        dk.fight_started = True
        dk.ai_state = "hunting"
        game.add_event("DWARF_KING_FIGHT_STARTED", {"mob": dk.id}, floor_id=floor_id)
        game.add_event("BOSS_YELL", {"mob": dk.id, "text": YELL_NOTICE, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)


def _dwarf_king_unseal_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of CityBossLevel.unseal(): unlocks both doors, allows passage to depth 21,
    and spawns the Imp shop if quest completed."""
    floor.generation_meta["dwarf_king_sealed"] = False

    # Unlock bottom door (7, 37)
    bx, by = BOTTOM_DOOR_POS
    floor.grid[by][bx] = TileType.DOOR
    floor.locked_doors.pop((bx, by), None)

    # Unlock top exit door (7, 25)
    tx, ty = TOP_DOOR_POS
    floor.grid[ty][tx] = TileType.DOOR
    floor.locked_doors.pop((tx, ty), None)

    floor.rebuild_flags()
    game.add_event("MAP_PATCH", {"tiles": [
        {"x": bx, "y": by, "tile": TileType.DOOR},
        {"x": tx, "y": ty, "tile": TileType.DOOR},
    ]}, floor_id=floor_id)

    # If Imp quest completed, spawn shopkeeper and items on floor 20
    if game.run_state.imp_quest.completed:
        game._spawn_imp_shop(floor)

    for player in game._players_on_floor(floor_id):
        player.locked_floor_left = None


def _dwarf_king_add_locked_floor_time(game, floor_id: int, dmg: float) -> None:
    """Port of DwarfKing.damage() LockedFloor extension: dmg/3f normal, dmg/5f challenge."""
    if dmg <= 0:
        return
    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    added = dmg / 5.0 if is_stronger else dmg / 3.0
    for player in game._players_on_floor(floor_id):
        if player.locked_floor_left is not None:
            player.locked_floor_left = min(50.0, player.locked_floor_left + added)



def _flush_locked_floor_credit(game, dk: DwarfKing, floor_id: int) -> None:
    credit = dk._locked_floor_credit
    if credit > 0:
        dk._locked_floor_credit = 0.0
        _dwarf_king_add_locked_floor_time(game, floor_id, credit)


def _throw_throne_items(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Port of Char.throwItems(), run from DwarfKing.act() while on the throne:
    one item per turn is knocked off to a random passable neighbour."""
    if (dk.pos.x, dk.pos.y) != THRONE_POS:
        return
    tx, ty = THRONE_POS
    item = next(
        (it for it in floor.items.values()
         if it.pos is not None and (it.pos.x, it.pos.y) == (tx, ty)),
        None,
    )
    if item is None:
        return
    candidates = [
        (tx + ndx, ty + ndy) for ndx, ndy in NEIGHBOURS8
        if _passable(floor, tx + ndx, ty + ndy)
    ]
    if not candidates:
        return
    dest = random.choice(candidates)
    item.pos = Position(x=dest[0], y=dest[1])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

NONE, LINK, TELE = 0, 1, 2
LIFE_LINK_TURNS = 100

NEIGHBOURS8: List[Tuple[int, int]] = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0), (1, 0),
    (-1, 1), (0, 1), (1, 1),
]


def _is_stronger(game) -> bool:
    return "stronger_bosses" in getattr(game, "challenges", set())


def _cooldown_roll(game) -> int:
    return normal_int_range(8, 10) if _is_stronger(game) else normal_int_range(10, 14)


def _phase2_hp(game) -> int:
    return 100 if _is_stronger(game) else 50


def _in_map(floor: FloorState, x: int, y: int) -> bool:
    return 0 <= x < floor.width and 0 <= y < floor.height


def _solid(floor: FloorState, x: int, y: int) -> bool:
    if not _in_map(floor, x, y):
        return True
    return bool(floor.flags and floor.flags.solid[y][x])


def _passable(floor: FloorState, x: int, y: int) -> bool:
    return _in_map(floor, x, y) and bool(floor.flags and floor.flags.passable[y][x])


def _char_at(game, floor: FloorState, floor_id: int, x: int, y: int):
    for p in game._players_on_floor(floor_id):
        if p.is_alive and p.pos.x == x and p.pos.y == y:
            return p
    for m in floor.mobs.values():
        if m.is_alive and m.pos.x == x and m.pos.y == y:
            return m
    return None


def _true_distance(ax: int, ay: int, bx: int, by: int) -> float:
    return math.hypot(ax - bx, ay - by)


def _is_paralysed(dk: DwarfKing) -> bool:
    return dk.has_buff("paralysis") or dk.has_buff("frost") or dk.has_buff("frozen")


def _get_subjects(dk: DwarfKing, floor: FloorState) -> List[MobEntity]:
    """Port of DwarfKing.getSubjects(): every same-alignment Ghoul/Monk/Warlock/Golem."""
    return [
        m for m in floor.mobs.values()
        if m.is_alive and m.faction == dk.faction and isinstance(m, (Ghoul, Monk, Warlock, Golem))
    ]


def _cell_past_target(floor: FloorState, src: Position, dst: Position) -> Optional[Tuple[int, int]]:
    """`new Ballistica(src, dst, STOP_TARGET).path.get(dist + 1)`: the cell one step
    beyond `dst` on SPD's DDA line from `src`, or None if the line leaves the map."""
    x0, y0, x1, y1 = src.x, src.y, dst.x, dst.y
    dx, dy = x1 - x0, y1 - y0
    sx = 1 if dx > 0 else -1
    sy = 1 if dy > 0 else -1
    dx, dy = abs(dx), abs(dy)
    if dx > dy:
        step_a, step_b, d_a, d_b = (sx, 0), (0, sy), dx, dy
    else:
        step_a, step_b, d_a, d_b = (0, sy), (sx, 0), dy, dx
    x, y = x0, y0
    err = d_a // 2
    reached = False
    while 1 <= x < floor.width - 1 and 1 <= y < floor.height - 1:
        if reached:
            return (x, y)
        if (x, y) == (x1, y1):
            reached = True
        x, y = x + step_a[0], y + step_a[1]
        err += d_b
        if err >= d_a:
            err -= d_a
            x, y = x + step_b[0], y + step_b[1]
    return None


def _set_barrier(dk: DwarfKing, amount: int) -> None:
    dk.barrier_hp = max(0, amount)
    dk.shields = (
        [Shield(name="dwarf_king_barrier", amount=dk.barrier_hp, priority=10, decay=0)]
        if dk.barrier_hp > 0 else []
    )


def _yell(game, dk: DwarfKing, text: str, floor_id: int) -> None:
    game.add_event("BOSS_YELL", {"mob": dk.id, "text": text, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)


def _scream(game, dk: DwarfKing, text: str, floor_id: int) -> None:
    game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=floor_id)
    _yell(game, dk, text, floor_id)


def _teleport_char(game, ch, x: int, y: int, floor_id: int) -> None:
    """ScrollOfTeleportation.appear(): instant relocation with TELEPORT sound/light."""
    from_x, from_y = ch.pos.x, ch.pos.y
    ch.pos = Position(x=x, y=y)
    game.add_event("TELEPORT", {"player": ch.id, "from_x": from_x, "from_y": from_y, "x": x, "y": y},
                   floor_id=floor_id)


# ---------------------------------------------------------------------------
# Dwarf King Main Loop
# ---------------------------------------------------------------------------

def _update_dwarf_king(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> bool:
    """Per-tick driver. DwarfKing.act() runs once per game turn on `act_ticks`;
    Viscosity bleed runs on its own clock. Returns True when the generic mob AI
    must not move/attack for the King this tick."""
    if not dk.is_alive:
        return True
    if not dk.fight_started:
        return True

    if dk.phase == 1 and dk.hp <= _phase2_hp(game):
        _transition_to_phase2(game, dk, floor, floor_id)

    _sweep_king_damagers(game, dk, floor, floor_id)
    _flush_deferred_popups(game, dk, floor_id)
    if dk.phase == 3:
        _tick_phase3_deferred_damage(game, dk, floor, floor_id)
        if not dk.is_alive:
            return True

    idle = dk.phase == 2 and not _get_subjects(dk, floor)
    dk.act_ticks += DK_IDLE_CLOCK_MULTIPLIER if idle else 1
    if dk.act_ticks >= TICKS_PER_TURN:
        dk.act_ticks = 0
        dk.turn_spent = False
        _dwarf_king_act(game, dk, floor, floor_id)

    _flush_locked_floor_credit(game, dk, floor_id)

    if not dk.is_alive:
        return True
    return dk.phase == 2 or dk.turn_spent


def _dwarf_king_act(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    _throw_throne_items(game, dk, floor, floor_id)
    _tick_life_links(dk)

    if dk.phase == 1:
        _phase1_act(game, dk, floor, floor_id)
    elif dk.phase == 2:
        _tick_barrier(dk)
        _phase2_act(game, dk, floor, floor_id)
    elif dk.phase == 3 and len(dk.pending_summons) < 4:
        if _summon_subject(game, dk, 2 if _is_stronger(game) else 3):
            dk.summons_made += 1

    _tick_pending_summons(game, dk, floor, floor_id)


def _phase1_act(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    if dk.summon_cooldown <= 0 and _summon_subject(game, dk, 2 if _is_stronger(game) else 3):
        dk.summons_made += 1
        dk.summon_cooldown += _cooldown_roll(game)
    elif dk.summon_cooldown > 0:
        dk.summon_cooldown -= 1

    if _is_paralysed(dk):
        dk.turn_spent = True
        return

    if dk.ability_cooldown <= 0:
        if _dwarf_king_use_ability(game, dk, floor, floor_id):
            dk.ability_cooldown += _cooldown_roll(game)
            dk.turn_spent = True
    else:
        dk.ability_cooldown -= 1


# ---------------------------------------------------------------------------
# Summoning & Pedestals
# ---------------------------------------------------------------------------

def _summon_particle(cls) -> str:
    if cls is DKGolem:
        return "spark"
    if cls is DKWarlock:
        return "shadow"
    if cls is DKMonk:
        return "fire"
    return "bones"


def _get_summoning_pos(dk: DwarfKing) -> Optional[Tuple[int, int]]:
    """CityBossLevel.getSummoningPos(): a random pedestal without an inbound summon."""
    occupied = {tuple(s["pos"]) for s in dk.pending_summons}
    available = [p for p in PEDESTAL_POSITIONS if p not in occupied]
    return random.choice(available) if available else None


def _summon_subject_of(dk: DwarfKing, delay: int, cls) -> bool:
    pos = _get_summoning_pos(dk)
    if pos is None:
        return False
    dk.pending_summons.append({
        "pos": pos,
        "cls": cls.__name__,
        "delay": delay,
        "particle": _summon_particle(cls),
    })
    return True


def _summon_subject(game, dk: DwarfKing, delay: int) -> bool:
    if _is_stronger(game):
        if dk.summons_made % 3 == 2:
            if dk.summons_made % 9 == 8:
                cls = DKGolem
            else:
                cls = DKMonk if random.randint(0, 1) == 0 else DKWarlock
        else:
            cls = DKGhoul
    else:
        if dk.summons_made % 4 == 3:
            cls = DKMonk if random.randint(0, 1) == 0 else DKWarlock
        else:
            cls = DKGhoul
    return _summon_subject_of(dk, delay, cls)


_SUMMON_SOUNDS = {"DKGolem": "CHARGEUP", "DKWarlock": "CURSED", "DKMonk": "BURNING"}


def _tick_pending_summons(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Port of DwarfKing.Summoning.act(), once per turn per inbound summon."""
    active: List[dict] = []
    for summon in list(dk.pending_summons):
        summon["delay"] -= 1
        if summon["delay"] > 0:
            active.append(summon)
            continue
        _resolve_summon(game, dk, floor, floor_id, summon)
        if not dk.is_alive:
            return
    dk.pending_summons = active


def _resolve_summon(game, dk: DwarfKing, floor: FloorState, floor_id: int, summon: dict) -> None:
    px, py = summon["pos"]
    cls_name = summon["cls"]
    cls = DK_MINION_CLASSES[cls_name]

    game.add_event("PLAY_SOUND", {"sound": _SUMMON_SOUNDS.get(cls_name, "BONES"), "x": px, "y": py},
                   floor_id=floor_id)
    game.add_event("DWARF_KING_SUMMON_BURST", {"x": px, "y": py, "mob_cls": cls_name}, floor_id=floor_id)

    sx, sy = px, py
    if _char_at(game, floor, floor_id, sx, sy) is not None:
        candidates = [
            (px + ndx, py + ndy) for ndx, ndy in NEIGHBOURS8
            if _passable(floor, px + ndx, py + ndy) and _char_at(game, floor, floor_id, px + ndx, py + ndy) is None
        ]
        if candidates:
            sx, sy = random.choice(candidates)

    occupant = _char_at(game, floor, floor_id, sx, sy)
    if occupant is not None and getattr(occupant, "name", "") == "Sheep":
        occupant.is_alive = False
        game.add_event("DEATH", {"target": occupant.id}, floor_id=floor_id)
        occupant = None

    if occupant is None:
        new_mob = game._spawn_mob_at(cls, sx, sy, floor_id)
        new_mob.ai_state = "hunting"
        if dk.phase == 2:
            new_mob.king_damager = True
            new_mob.linked_king_id = dk.id
            dk.king_damager_ids.append(new_mob.id)
        floor.mobs[new_mob.id] = new_mob
        return

    taken = occupant.take_damage(normal_int_range(20, 40))
    game.add_event("DAMAGE", {"target": occupant.id, "amount": taken}, floor_id=floor_id)
    if occupant is not dk and not occupant.is_alive:
        game.add_event("DEATH", {"target": occupant.id}, floor_id=floor_id)
        if isinstance(occupant, MobEntity):
            game.handle_mob_death(occupant, floor, floor_id)
    if dk.phase == 2:
        _king_damager_hit(game, dk, floor, floor_id)


# ---------------------------------------------------------------------------
# Phase 1 Special Abilities: Life Link & Teleport Subject
# ---------------------------------------------------------------------------

def _tick_life_links(dk: DwarfKing) -> None:
    kept = []
    for link in dk._life_links:
        link[1] -= 1
        if link[1] > 0 and link[0].is_alive:
            kept.append(link)
    dk._life_links = kept
    if not kept:
        dk.remove_buff("life_link")


def _dwarf_king_use_ability(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> bool:
    if dk.last_ability == NONE:
        dk.last_ability = LINK if random.randint(0, 1) == 0 else TELE
    elif dk.last_ability == LINK:
        dk.last_ability = LINK if random.randint(0, 7) == 0 else TELE
    else:
        dk.last_ability = LINK if random.randint(0, 7) != 0 else TELE

    if dk.last_ability == LINK and _cast_life_link(game, dk, floor, floor_id):
        return True
    if _cast_teleport_subject(game, dk, floor, floor_id):
        dk.last_ability = TELE
        return True
    return False


def _cast_life_link(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> bool:
    """Port of DwarfKing.lifeLinkSubject(): links the furthest not-yet-linked subject."""
    linked = {id(link[0]) for link in dk._life_links}
    furthest = None
    for m in _get_subjects(dk, floor):
        if id(m) in linked:
            continue
        if furthest is None or game._get_distance(dk.pos, furthest.pos) < game._get_distance(dk.pos, m.pos):
            furthest = m
    if furthest is None:
        return False

    dk._life_links.append([furthest, LIFE_LINK_TURNS])
    dk.add_buff("life_link", duration=float(LIFE_LINK_TURNS))
    furthest.add_buff("life_link", duration=float(LIFE_LINK_TURNS))
    furthest._owner_ref = dk

    _yell(game, dk, YELL_LIFELINK_1 if random.randint(1, 2) == 1 else YELL_LIFELINK_2, floor_id)
    game.add_event("HEALTH_RAY", {
        "fx": dk.pos.x, "fy": dk.pos.y,
        "tx": furthest.pos.x, "ty": furthest.pos.y,
    }, floor_id=floor_id)
    return True


def _cast_teleport_subject(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> bool:
    """Port of DwarfKing.teleportSubject(): the King steps away from his enemy and
    the furthest subject appears next to the enemy, on the side facing the King."""
    enemy = game._find_nearest_player(dk.pos, floor_id)
    if enemy is None:
        return False

    furthest = None
    for m in _get_subjects(dk, floor):
        if furthest is None or game._get_distance(dk.pos, furthest.pos) < game._get_distance(dk.pos, m.pos):
            furthest = m
    if furthest is None:
        return False

    best = (dk.pos.x, dk.pos.y)
    target_cell = _cell_past_target(floor, enemy.pos, dk.pos)
    if (target_cell is not None
            and _char_at(game, floor, floor_id, *target_cell) is None
            and not _solid(floor, *target_cell)):
        best = target_cell
    else:
        best_dist = _true_distance(dk.pos.x, dk.pos.y, enemy.pos.x, enemy.pos.y)
        for ndx, ndy in NEIGHBOURS8:
            nx, ny = dk.pos.x + ndx, dk.pos.y + ndy
            if (_char_at(game, floor, floor_id, nx, ny) is None
                    and not _solid(floor, nx, ny)
                    and _true_distance(nx, ny, enemy.pos.x, enemy.pos.y) > best_dist):
                best = (nx, ny)
                best_dist = _true_distance(nx, ny, enemy.pos.x, enemy.pos.y)
    dk.pos = Position(x=best[0], y=best[1])

    best_dist = _true_distance(enemy.pos.x, enemy.pos.y, dk.pos.x, dk.pos.y)
    best = (enemy.pos.x, enemy.pos.y)
    for ndx, ndy in NEIGHBOURS8:
        nx, ny = enemy.pos.x + ndx, enemy.pos.y + ndy
        if (_char_at(game, floor, floor_id, nx, ny) is None
                and not _solid(floor, nx, ny)
                and _true_distance(nx, ny, dk.pos.x, dk.pos.y) < best_dist):
            best = (nx, ny)
            best_dist = _true_distance(nx, ny, dk.pos.x, dk.pos.y)

    if best != (enemy.pos.x, enemy.pos.y):
        _teleport_char(game, furthest, best[0], best[1], floor_id)
    _yell(game, dk, YELL_TELEPORT_1 if random.randint(1, 2) == 1 else YELL_TELEPORT_2, floor_id)
    return True


# ---------------------------------------------------------------------------
# Phase 2: Throne, Barrier & Scripted Waves
# ---------------------------------------------------------------------------

def _transition_to_phase2(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Phase-1 branch of DwarfKing.damage() once HP reaches the threshold."""
    dk.hp = _phase2_hp(game)
    tx, ty = THRONE_POS
    _teleport_char(game, dk, tx, ty, floor_id)
    if "IMMOVABLE" not in dk.properties:
        dk.properties.append("IMMOVABLE")
    dk.phase = 2
    dk.summons_made = 0
    dk.wave_wait = 0
    dk.barrier_max = dk.max_hp
    _set_barrier(dk, dk.max_hp)
    dk.pending_summons = []

    for m in _get_subjects(dk, floor):
        m.is_alive = False
        game.add_event("DEATH", {"target": m.id}, floor_id=floor_id)

    dk._life_links = []
    dk.remove_buff("life_link")

    game.add_event("DWARF_KING_PHASE2", {"mob": dk.id, "x": tx, "y": ty}, floor_id=floor_id)


def _tick_barrier(dk: DwarfKing) -> None:
    """DKBarrior.act(): incShield() then Barrier decay, which only bites from 20 up."""
    if dk.barrier_hp <= 0:
        return
    if dk.barrier_hp + 1 < 20:
        _set_barrier(dk, dk.barrier_hp + 1)


def _phase2_act(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    if dk.wave_wait > 0:
        dk.wave_wait -= 1
        return
    spent = _phase2_wave_step_stronger(game, dk, floor_id) if _is_stronger(game) else _phase2_wave_step(game, dk, floor_id)
    dk.wave_wait = spent - 1


def _phase2_wave_step(game, dk: DwarfKing, floor_id: int) -> int:
    """Non-challenge branch of DwarfKing.act() phase 2. Returns turns spent."""
    if dk.summons_made < 4:
        if dk.summons_made == 0:
            _scream(game, dk, YELL_WAVE_1, floor_id)
        _summon_subject_of(dk, 3, DKGhoul)
        dk.summons_made += 1
        return 3
    if dk.barrier_hp <= 200 and dk.summons_made < 8:
        if dk.summons_made == 4:
            _scream(game, dk, YELL_WAVE_2, floor_id)
        if dk.summons_made == 7:
            _summon_subject_of(dk, 3, DKMonk if random.randint(0, 1) == 0 else DKWarlock)
        else:
            _summon_subject_of(dk, 3, DKGhoul)
        dk.summons_made += 1
        return 1
    if dk.barrier_hp <= 100 and dk.summons_made < 12:
        _scream(game, dk, YELL_WAVE_3, floor_id)
        for cls in (DKWarlock, DKMonk, DKGhoul, DKGhoul):
            _summon_subject_of(dk, 4, cls)
        dk.summons_made = 12
        return 1
    return 1


def _phase2_wave_step_stronger(game, dk: DwarfKing, floor_id: int) -> int:
    """Stronger-bosses branch of DwarfKing.act() phase 2. Returns turns spent."""
    if dk.summons_made < 6:
        if dk.summons_made == 0:
            _scream(game, dk, YELL_WAVE_1, floor_id)
        _summon_subject_of(dk, 3, DKGhoul)
        _summon_subject_of(dk, 3, DKGhoul)
        dk.summons_made += 2
        return 3
    if dk.barrier_hp <= 300 and dk.summons_made < 12:
        if dk.summons_made == 6:
            _scream(game, dk, YELL_WAVE_2, floor_id)
        _summon_subject_of(dk, 3, DKGhoul)
        _summon_subject_of(dk, 3, DKGhoul)
        _summon_subject_of(dk, 3, DKMonk if dk.summons_made == 6 else DKWarlock)
        dk.summons_made += 3
        return 3
    if dk.barrier_hp <= 150 and dk.summons_made < 18:
        if dk.summons_made == 12:
            _scream(game, dk, YELL_WAVE_3, floor_id)
            for cls in (DKWarlock, DKMonk, DKGhoul, DKGhoul):
                _summon_subject_of(dk, 3, cls)
            dk.summons_made += 4
            return 3
        _summon_subject_of(dk, 3, DKGolem)
        _summon_subject_of(dk, 3, DKGolem)
        dk.summons_made += 2
        return 1
    return 1


def _king_damager_hit(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """`DwarfKing.damage(HT/12, new KingDamager())` (HT/18 with stronger bosses):
    soaks into the barrier with overflow to HP in phase 2, deferred in phase 3."""
    if not dk.is_alive:
        return
    dmg = dk.max_hp // (18 if _is_stronger(game) else 12)
    if dk.phase == 3:
        dk.take_damage(dmg)
        return
    if dk.phase != 2:
        return
    absorbed = min(dk.barrier_hp, dmg)
    _set_barrier(dk, dk.barrier_hp - absorbed)
    if dmg > absorbed:
        dk.hp = max(0, dk.hp - (dmg - absorbed))
    dk._locked_floor_credit += dmg
    game.add_event("DWARF_KING_SHIELD_DAMAGE", {
        "mob": dk.id,
        "amount": dmg,
        "barrier_hp": dk.barrier_hp,
    }, floor_id=floor_id)
    if dk.barrier_hp <= 0:
        _transition_to_phase3(game, dk, floor, floor_id)


def _sweep_king_damagers(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """KingDamager.detach(): fires once per tracked phase-2 summon as soon as it dies
    (by any cause), leaves the floor, or stops being an enemy."""
    for mob_id in list(dk.king_damager_ids):
        m = floor.mobs.get(mob_id)
        if m is not None and m.is_alive and m.faction == dk.faction:
            continue
        dk.king_damager_ids.remove(mob_id)
        if m is not None:
            m.king_damager = False
        _king_damager_hit(game, dk, floor, floor_id)


def _find_alive_king(floor: FloorState) -> Optional[DwarfKing]:
    return next((m for m in floor.mobs.values() if isinstance(m, DwarfKing) and m.is_alive), None)


def handle_dwarf_king_minion_death(game, mob: MobEntity, floor: FloorState, floor_id: int) -> None:
    """Called for every mob death: drops the King's LifeLink to the dying mob and
    fires KingDamager.detach() for phase-2 summons."""
    dk = _find_alive_king(floor)
    if dk is None or mob is dk:
        return
    if any(link[0] is mob for link in dk._life_links):
        dk._life_links = [link for link in dk._life_links if link[0] is not mob]
        if not dk._life_links:
            dk.remove_buff("life_link")
    _sweep_king_damagers(game, dk, floor, floor_id)


# ---------------------------------------------------------------------------
# Phase 3: Enraged & Viscosity Deferred Damage
# ---------------------------------------------------------------------------

def _transition_to_phase3(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    if dk.phase == 3:
        return
    if "IMMOVABLE" in dk.properties:
        dk.properties.remove("IMMOVABLE")
    dk.phase = 3
    dk.summons_made = 1
    _set_barrier(dk, 0)
    dk.phase3_ticks = 0

    target = game._find_nearest_player(dk.pos, floor_id)
    hero_name = target.name if target else "hero"
    game.add_event("DWARF_KING_PHASE3", {"mob": dk.id}, floor_id=floor_id)
    _scream(game, dk, YELL_ENRAGED_TEMPLATE.format(name=hero_name), floor_id)


def _flush_deferred_popups(game, dk: DwarfKing, floor_id: int) -> None:
    if not dk._deferred_popups:
        return
    for amount in dk._deferred_popups:
        game.add_event("DWARF_KING_DEFERRED", {
            "mob": dk.id, "amount": amount, "x": dk.pos.x, "y": dk.pos.y,
        }, floor_id=floor_id)
    dk._deferred_popups = []


def _tick_phase3_deferred_damage(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Viscosity.DeferedDamage.act(): once per turn, 10% of the pool (min 1)."""
    if dk.deferred_damage <= 0:
        return
    dk.phase3_ticks += 1
    if dk.phase3_ticks < TICKS_PER_TURN:
        return
    dk.phase3_ticks = 0

    bleed = max(1, int(dk.deferred_damage * 0.1))
    dk.deferred_damage = max(0, dk.deferred_damage - bleed)
    pre_hp = dk.hp
    dk.hp = max(0, dk.hp - bleed)
    dk._locked_floor_credit += bleed
    game.add_event("DAMAGE", {"target": dk.id, "amount": bleed}, floor_id=floor_id)

    if dk.hp > 0:
        if pre_hp > 20 and dk.hp < 20:
            _yell(game, dk, YELL_LOSING, floor_id)
        return

    dk.is_alive = False
    players = list(game._players_on_floor(floor_id))
    dk.die(floor_mobs=floor.mobs, tile_x=dk.pos.x, tile_y=dk.pos.y, players=players)
    game.add_event("DEATH", {"target": dk.id}, floor_id=floor_id)
    killer = game._find_nearest_player(dk.pos, floor_id)
    if killer is not None:
        game._award_kill_xp(killer, dk, floor_id)
    _flush_locked_floor_credit(game, dk, floor_id)
    game.handle_mob_death(dk, floor, floor_id)
