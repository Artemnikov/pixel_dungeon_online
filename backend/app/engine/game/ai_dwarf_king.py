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
  and immune to direct damage behind a 300 HP barrier. Spawns 3 scripted minion waves
  (Wave 1: Ghouls; Wave 2: Ghouls + Monk/Warlock; Wave 3: Ghouls + Monk + Warlock + Golems).
  Killing Phase 2 minions (KingDamager) breaks the King's barrier (25 dmg per minion).
- Phase 3 (Barrier <= 0): King enrages, leaves the throne, and enters Viscosity
  deferred damage mode. Continues rapid pedestal summoning. Damage dealt to King
  bleeds over time until defeat.
- Defeat: King drops King's Crown, unseals arena doors (7, 37) and (7, 25), clears
  remaining minions, upgrades Lloyd's Beacon, cleanses degrade, and opens Imp shop.
"""

from __future__ import annotations

import random
import time
from typing import List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position, Shield
from app.engine.entities.mobs import DKGhoul, DKGolem, DKMonk, DKWarlock, DwarfKing
from app.engine.entities.player import Mob as MobEntity, Player
from app.engine.game.constants import GAME_LOOP_HZ, TICKS_PER_TURN
from app.engine.game.floor_state import FloorState

THRONE_POS = (7, 31)
PEDESTAL_POSITIONS: List[Tuple[int, int]] = [(4, 28), (10, 28), (10, 34), (4, 34)]
BOTTOM_DOOR_POS = (7, 37)
TOP_DOOR_POS = (7, 25)

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
# Arena Sealing & Unsealing
# ---------------------------------------------------------------------------

def _dwarf_king_maybe_seal_arena(game, player: Player, floor: FloorState, floor_id: int) -> None:
    """Triggered when a player steps into depth 20: seals the arena when the player
    crosses the threshold past the entrance door into the throne room (y <= 36)."""
    if floor_id != 20:
        return
    if floor.generation_meta.get("dwarf_king_sealed", False):
        return

    # Arena is rows 25 to 36, cols 1 to 13 (strictly inside past the door at y=37)
    px, py = player.pos.x, player.pos.y
    if 25 <= py <= 36 and 1 <= px <= 13:
        _dwarf_king_seal_arena(game, floor, floor_id)


def _dwarf_king_seal_arena(game, floor: FloorState, floor_id: int) -> None:
    """Port of CityBossLevel.seal(): locks the entrance door, alerts the Dwarf King,
    applies LockedFloor to players, and starts the boss fight."""
    floor.generation_meta["dwarf_king_sealed"] = True

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
        game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=floor_id)


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


# ---------------------------------------------------------------------------
# Dwarf King Main Loop
# ---------------------------------------------------------------------------

def _update_dwarf_king(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Main tick update for Dwarf King boss on floor 20."""
    # 1. Process active pedestal summons
    _tick_pending_summons(game, dk, floor, floor_id)

    # 2. Process Phase 3 Viscosity deferred damage
    if dk.phase == 3:
        _tick_phase3_deferred_damage(game, dk, floor, floor_id)

    if not dk.is_alive:
        return

    # 3. If fight not started yet, do not act (boss waits for player to step into the arena)
    if not dk.fight_started:
        return

    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())

    # --- Phase 1: Active Melee, Summoning & Special Abilities ---
    if dk.phase == 1:
        hp_threshold = 100 if is_stronger else 50
        if dk.hp <= hp_threshold:
            _transition_to_phase2(game, dk, floor, floor_id)
            return

        # Summoning cooldown
        if dk.summon_cooldown <= 0:
            if _dwarf_king_summon(game, dk, floor, floor_id):
                dk.summons_made += 1
                min_cd = 8 if is_stronger else 10
                max_cd = 10 if is_stronger else 14
                dk.summon_cooldown = random.randint(min_cd, max_cd) * TICKS_PER_TURN
        else:
            dk.summon_cooldown -= 1

        # Ability cooldown (Life Link / Teleport Subject)
        if dk.ability_cooldown <= 0:
            if _dwarf_king_use_ability(game, dk, floor, floor_id):
                min_cd = 8 if is_stronger else 10
                max_cd = 10 if is_stronger else 14
                dk.ability_cooldown = random.randint(min_cd, max_cd) * TICKS_PER_TURN
        else:
            dk.ability_cooldown -= 1

    # --- Phase 2: King on Throne (Shield Phase & Scripted Waves) ---
    elif dk.phase == 2:
        # Scripted minion waves based on barrier HP
        _update_phase2_waves(game, dk, floor, floor_id, is_stronger)

        # Check if barrier is broken
        if dk.barrier_hp <= 0:
            _transition_to_phase3(game, dk, floor, floor_id)
            return

    # --- Phase 3: Enraged Melee & Rapid Pedestal Summons ---
    elif dk.phase == 3:
        if len(dk.pending_summons) < 4:
            if dk.summon_cooldown <= 0:
                if _dwarf_king_summon(game, dk, floor, floor_id):
                    dk.summons_made += 1
                    dk.summon_cooldown = random.randint(3, 5) * TICKS_PER_TURN
            else:
                dk.summon_cooldown -= 1


# ---------------------------------------------------------------------------
# Summoning & Pedestals
# ---------------------------------------------------------------------------

def _get_available_pedestal(dk: DwarfKing) -> Optional[Tuple[int, int]]:
    """Returns a pedestal pos that does not currently have an active pending summon."""
    occupied = {s["pos"] for s in dk.pending_summons}
    available = [p for p in PEDESTAL_POSITIONS if p not in occupied]
    return random.choice(available) if available else None


def _dwarf_king_summon(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> bool:
    """Queues a minion summon on an open pedestal."""
    pedestal = _get_available_pedestal(dk)
    if not pedestal:
        return False

    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    delay_turns = 2 if is_stronger else 3

    # Pick minion class based on SPD rules
    if is_stronger:
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

    particle = "bones"
    if cls == DKGolem:
        particle = "spark"
    elif cls == DKWarlock:
        particle = "shadow"
    elif cls == DKMonk:
        particle = "fire"

    dk.pending_summons.append({
        "pos": pedestal,
        "cls": cls,
        "ticks_left": int(delay_turns * TICKS_PER_TURN),
        "particle": particle,
    })

    game.add_event("DWARF_KING_SUMMON_START", {
        "x": pedestal[0],
        "y": pedestal[1],
        "particle": particle,
    }, floor_id=floor_id)

    return True


def _tick_pending_summons(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Decrements pending summon timers and resolves spawns when delay expires."""
    active: List[dict] = []
    for summon in dk.pending_summons:
        summon["ticks_left"] -= 1
        if summon["ticks_left"] > 0:
            active.append(summon)
            continue

        # Timer expired -> spawn minion
        px, py = summon["pos"]
        cls = summon["cls"]

        # Sound effect on appearance
        sound = "BONES"
        if cls == DKGolem:
            sound = "CHARGEUP"
        elif cls == DKWarlock:
            sound = "CURSED"
        elif cls == DKMonk:
            sound = "BURNING"

        game.add_event("PLAY_SOUND", {"sound": sound, "x": px, "y": py}, floor_id=floor_id)
        game.add_event("DWARF_KING_SUMMON_BURST", {"x": px, "y": py, "mob_cls": cls.__name__}, floor_id=floor_id)

        # Check occupant of the pedestal tile
        occupant_player = next((p for p in game._players_on_floor(floor_id) if p.is_alive and p.pos.x == px and p.pos.y == py), None)
        occupant_mob = next((m for m in floor.mobs.values() if m.is_alive and m.pos.x == px and m.pos.y == py), None)

        # If a character stands directly on the pedestal, deal 20-40 damage
        is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
        crushed_pedestal = False
        if occupant_player:
            dmg = random.randint(20, 40)
            taken = occupant_player.take_damage(dmg)
            game.add_event("DAMAGE", {"target": occupant_player.id, "amount": taken}, floor_id=floor_id)
            crushed_pedestal = True
            if not occupant_player.is_alive:
                game.add_event("DEATH", {"target": occupant_player.id}, floor_id=floor_id)

        if occupant_mob and getattr(occupant_mob, "name", "") == "Sheep":
            occupant_mob.is_alive = False
            game.add_event("DEATH", {"target": occupant_mob.id}, floor_id=floor_id)
            crushed_pedestal = True

        # In Phase 2, absorbing the pedestal blast damages the King's barrier (matching SPD)
        if crushed_pedestal and dk.phase == 2:
            shield_dmg = dk.max_hp // (18 if is_stronger else 12)
            dk.barrier_hp = max(0, dk.barrier_hp - shield_dmg)
            dk.shields = [Shield(name="dwarf_king_barrier", amount=dk.barrier_hp, priority=10, decay=0)] if dk.barrier_hp > 0 else []
            game.add_event("DWARF_KING_SHIELD_DAMAGE", {
                "mob": dk.id,
                "amount": shield_dmg,
                "barrier_hp": dk.barrier_hp,
            }, floor_id=floor_id)
            if dk.barrier_hp <= 0:
                _transition_to_phase3(game, dk, floor, floor_id)

        # Find empty spawn pos (pedestal or neighboring passable tile)
        spawn_pos = (px, py)
        if occupant_player or (occupant_mob and occupant_mob.is_alive):
            candidates = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = px + dx, py + dy
                    if (0 <= nx < floor.width and 0 <= ny < floor.height
                            and (floor.flags and floor.flags.passable[ny][nx])
                            and not any(m.is_alive and m.pos.x == nx and m.pos.y == ny for m in floor.mobs.values())
                            and not any(p.is_alive and p.pos.x == nx and p.pos.y == ny for p in game._players_on_floor(floor_id))):
                        candidates.append((nx, ny))
            if candidates:
                spawn_pos = random.choice(candidates)

        new_mob = game._spawn_mob_at(cls, spawn_pos[0], spawn_pos[1])
        new_mob.ai_state = "hunting"
        if dk.phase == 2:
            new_mob.king_damager = True
            new_mob.linked_king_id = dk.id

        floor.mobs[new_mob.id] = new_mob
        game.add_event("ZAP_SUMMON", {"x": spawn_pos[0], "y": spawn_pos[1]}, floor_id=floor_id)

    dk.pending_summons = active


# ---------------------------------------------------------------------------
# Phase 1 Special Abilities: Life Link & Teleport Subject
# ---------------------------------------------------------------------------

def _get_active_subjects(floor: FloorState) -> List[MobEntity]:
    """Returns all active allied minions of the Dwarf King."""
    return [
        m for m in floor.mobs.values()
        if m.is_alive and isinstance(m, (DKGhoul, DKMonk, DKWarlock, DKGolem))
    ]


def _dwarf_king_use_ability(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> bool:
    """Selects and casts either Life Link or Teleport Subject."""
    subjects = _get_active_subjects(floor)
    if not subjects:
        return False

    # Selection weighting (SPD: 50/50 initial, then alternates with 7/8 bias)
    if dk.last_ability == 0:
        use_link = random.random() < 0.5
    elif dk.last_ability == 1:  # LINK
        use_link = random.random() < (1.0 / 8.0)
    else:  # TELE
        use_link = random.random() < (7.0 / 8.0)

    if use_link:
        if _cast_life_link(game, dk, subjects, floor_id):
            dk.last_ability = 1
            return True
        elif _cast_teleport_subject(game, dk, subjects, floor, floor_id):
            dk.last_ability = 2
            return True
    else:
        if _cast_teleport_subject(game, dk, subjects, floor, floor_id):
            dk.last_ability = 2
            return True
        elif _cast_life_link(game, dk, subjects, floor_id):
            dk.last_ability = 1
            return True

    return False


def _cast_life_link(game, dk: DwarfKing, subjects: List[MobEntity], floor_id: int) -> bool:
    """Links King to the furthest allied subject via LifeLink beam."""
    # Find furthest unlinked minion
    furthest = None
    max_dist = -1.0
    for m in subjects:
        if m.id == dk.linked_mob_id or m.has_buff("life_link"):
            continue
        dist = game._get_distance(dk.pos, m.pos)
        if dist > max_dist:
            max_dist = dist
            furthest = m

    if furthest is None:
        return False

    dk.linked_mob_id = furthest.id
    dk._owner_ref = furthest
    dk.add_buff("life_link", duration=100.0)
    furthest.linked_mob_id = dk.id
    furthest.add_buff("life_link", duration=100.0)
    furthest._owner_ref = dk

    quote = YELL_LIFELINK_1 if random.randint(0, 1) == 0 else YELL_LIFELINK_2
    game.add_event("BOSS_YELL", {"mob": dk.id, "text": quote, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)
    game.add_event("HEALTH_RAY", {
        "fx": dk.pos.x, "fy": dk.pos.y,
        "tx": furthest.pos.x, "ty": furthest.pos.y,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "RAY", "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)

    return True


def _cast_teleport_subject(game, dk: DwarfKing, subjects: List[MobEntity], floor: FloorState, floor_id: int) -> bool:
    """Repositions the King away from the hero, and teleports the furthest subject next to the hero."""
    player = game._find_nearest_player(dk.pos, floor_id)
    if player is None:
        return False

    # Find furthest subject
    furthest = max(subjects, key=lambda m: game._get_distance(dk.pos, m.pos), default=None)
    if furthest is None:
        return False

    # Reposition King: move one step away from player if open
    dx = 1 if dk.pos.x > player.pos.x else (-1 if dk.pos.x < player.pos.x else 0)
    dy = 1 if dk.pos.y > player.pos.y else (-1 if dk.pos.y < player.pos.y else 0)
    new_kx, new_ky = dk.pos.x + dx, dk.pos.y + dy
    if (0 <= new_kx < floor.width and 0 <= new_ky < floor.height
            and (floor.flags and floor.flags.passable[new_ky][new_kx])
            and not any(m.is_alive and m.pos.x == new_kx and m.pos.y == new_ky for m in floor.mobs.values())):
        dk.pos = Position(x=new_kx, y=new_ky)

    # Teleport furthest minion directly adjacent to player
    adj_cells = []
    for adx in (-1, 0, 1):
        for ady in (-1, 0, 1):
            if adx == 0 and ady == 0:
                continue
            ax, ay = player.pos.x + adx, player.pos.y + ady
            if (0 <= ax < floor.width and 0 <= ay < floor.height
                    and (floor.flags and floor.flags.passable[ay][ax])
                    and not any(m.is_alive and m.pos.x == ax and m.pos.y == ay for m in floor.mobs.values())):
                adj_cells.append((ax, ay))

    if adj_cells:
        dest = random.choice(adj_cells)
        furthest.pos = Position(x=dest[0], y=dest[1])
        game.add_event("PLAY_SOUND", {"sound": "TELEPORT", "x": dest[0], "y": dest[1]}, floor_id=floor_id)

    quote = YELL_TELEPORT_1 if random.randint(0, 1) == 0 else YELL_TELEPORT_2
    game.add_event("BOSS_YELL", {"mob": dk.id, "text": quote, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)

    return True


# ---------------------------------------------------------------------------
# Phase 2: Throne & Scripted Waves
# ---------------------------------------------------------------------------

def _transition_to_phase2(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Transitions Dwarf King into Phase 2 on the Throne."""
    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    dk.phase = 2
    dk.hp = 100 if is_stronger else 50
    dk.barrier_hp = 450 if is_stronger else 300
    dk.barrier_max = dk.barrier_hp
    dk.shields = [Shield(name="dwarf_king_barrier", amount=dk.barrier_hp, priority=10, decay=0)]
    dk.summons_made = 0
    dk.pending_summons.clear()

    # Teleport King to throne at (7, 31)
    tx, ty = THRONE_POS
    dk.pos = Position(x=tx, y=ty)
    if "IMMOVABLE" not in dk.properties:
        dk.properties.append("IMMOVABLE")

    # Clear all active minions and life links
    for m in list(floor.mobs.values()):
        if m.is_alive and isinstance(m, (DKGhoul, DKMonk, DKWarlock, DKGolem)):
            m.is_alive = False
            game.add_event("DEATH", {"target": m.id}, floor_id=floor_id)

    dk.linked_mob_id = ""
    dk._owner_ref = None
    dk.remove_buff("life_link")

    game.add_event("DWARF_KING_PHASE2", {"mob": dk.id}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=floor_id)
    game.add_event("BOSS_YELL", {"mob": dk.id, "text": YELL_WAVE_1, "x": tx, "y": ty}, floor_id=floor_id)


def _update_phase2_waves(game, dk: DwarfKing, floor: FloorState, floor_id: int, is_stronger: bool) -> None:
    """Spawns scripted Phase 2 waves based on barrier HP."""
    # Wave 1: 4 Ghouls (6 on challenge)
    if dk.summons_made == 0:
        count = 6 if is_stronger else 4
        for _ in range(count):
            pedestal = _get_available_pedestal(dk) or random.choice(PEDESTAL_POSITIONS)
            dk.pending_summons.append({
                "pos": pedestal,
                "cls": DKGhoul,
                "ticks_left": random.randint(int(1 * TICKS_PER_TURN), int(4 * TICKS_PER_TURN)),
                "particle": "bones",
            })
            game.add_event("DWARF_KING_SUMMON_START", {"x": pedestal[0], "y": pedestal[1], "particle": "bones"}, floor_id=floor_id)
        dk.summons_made = count

    # Wave 2: Ghouls + Monk/Warlock
    threshold_2 = 300 if is_stronger else 200
    if dk.barrier_hp <= threshold_2 and dk.summons_made < (12 if is_stronger else 8):
        game.add_event("BOSS_YELL", {"mob": dk.id, "text": YELL_WAVE_2, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=floor_id)
        minions = [DKGhoul, DKGhoul, DKGhoul, random.choice([DKMonk, DKWarlock])]
        if is_stronger:
            minions.extend([DKGhoul, DKMonk, DKWarlock])
        for cls in minions:
            pedestal = _get_available_pedestal(dk) or random.choice(PEDESTAL_POSITIONS)
            particle = "bones" if cls == DKGhoul else ("fire" if cls == DKMonk else "shadow")
            dk.pending_summons.append({
                "pos": pedestal,
                "cls": cls,
                "ticks_left": random.randint(int(1 * TICKS_PER_TURN), int(4 * TICKS_PER_TURN)),
                "particle": particle,
            })
            game.add_event("DWARF_KING_SUMMON_START", {"x": pedestal[0], "y": pedestal[1], "particle": particle}, floor_id=floor_id)
        dk.summons_made += len(minions)

    # Wave 3: Ghouls + Monk + Warlock + Golems
    threshold_3 = 150 if is_stronger else 100
    if dk.barrier_hp <= threshold_3 and dk.summons_made < (18 if is_stronger else 12):
        game.add_event("BOSS_YELL", {"mob": dk.id, "text": YELL_WAVE_3, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=floor_id)
        minions = [DKWarlock, DKMonk, DKGhoul, DKGhoul]
        if is_stronger:
            minions.extend([DKGolem, DKGolem])
        for cls in minions:
            pedestal = _get_available_pedestal(dk) or random.choice(PEDESTAL_POSITIONS)
            particle = "bones" if cls == DKGhoul else ("fire" if cls == DKMonk else ("shadow" if cls == DKWarlock else "spark"))
            dk.pending_summons.append({
                "pos": pedestal,
                "cls": cls,
                "ticks_left": random.randint(int(1 * TICKS_PER_TURN), int(4 * TICKS_PER_TURN)),
                "particle": particle,
            })
            game.add_event("DWARF_KING_SUMMON_START", {"x": pedestal[0], "y": pedestal[1], "particle": particle}, floor_id=floor_id)
        dk.summons_made = 18 if is_stronger else 12


def handle_dwarf_king_minion_death(game, mob: MobEntity, floor: FloorState, floor_id: int) -> None:
    """Called when a Phase 2 minion (KingDamager) dies: breaks King's barrier.
    Also cleans up LifeLink if the dying minion was linked to the King."""
    dk = next((m for m in floor.mobs.values() if isinstance(m, DwarfKing) and m.is_alive), None)
    if dk:
        if dk.linked_mob_id == mob.id:
            dk.linked_mob_id = ""
            dk._owner_ref = None
            dk.remove_buff("life_link")

    if not getattr(mob, "king_damager", False):
        return

    if not dk or dk.phase != 2:
        return

    is_stronger = "stronger_bosses" in getattr(game, "challenges", set())
    shield_dmg = dk.max_hp // (18 if is_stronger else 12)  # 25 dmg

    dk.barrier_hp = max(0, dk.barrier_hp - shield_dmg)
    dk.shields = [Shield(name="dwarf_king_barrier", amount=dk.barrier_hp, priority=10, decay=0)] if dk.barrier_hp > 0 else []
    game.add_event("DWARF_KING_SHIELD_DAMAGE", {
        "mob": dk.id,
        "amount": shield_dmg,
        "barrier_hp": dk.barrier_hp,
    }, floor_id=floor_id)

    if dk.barrier_hp <= 0:
        _transition_to_phase3(game, dk, floor, floor_id)


# ---------------------------------------------------------------------------
# Phase 3: Enraged & Viscosity Deferred Damage
# ---------------------------------------------------------------------------

def _transition_to_phase3(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Transitions Dwarf King into Phase 3 (Enraged, Bleeding)."""
    dk.phase = 3
    dk.shields = []
    dk.phase3_ticks = 0
    dk.linked_mob_id = ""
    dk._owner_ref = None
    if "IMMOVABLE" in dk.properties:
        dk.properties.remove("IMMOVABLE")

    target = game._find_nearest_player(dk.pos, floor_id)
    hero_name = target.name if target else "hero"
    quote = YELL_ENRAGED_TEMPLATE.format(name=hero_name)

    game.add_event("DWARF_KING_PHASE3", {"mob": dk.id}, floor_id=floor_id)
    game.add_event("BOSS_YELL", {"mob": dk.id, "text": quote, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "CHALLENGE"}, floor_id=floor_id)


def _tick_phase3_deferred_damage(game, dk: DwarfKing, floor: FloorState, floor_id: int) -> None:
    """Ticks away Viscosity deferred damage on King in Phase 3 once per turn (bleeding health bar)."""
    if dk.deferred_damage <= 0 or not dk.is_alive:
        return

    # SPD Viscosity DeferedDamage ticks once per turn (TICKS_PER_TURN = 5 ticks = 125ms / ~1s real-time turn rate)
    dk.phase3_ticks += 1
    if dk.phase3_ticks < TICKS_PER_TURN:
        return
    dk.phase3_ticks = 0

    # Deal 10% of deferred damage (minimum 1)
    bleed = max(1, int(dk.deferred_damage * 0.1))
    dk.deferred_damage -= bleed
    dk.hp -= bleed

    game.add_event("DAMAGE", {"target": dk.id, "amount": bleed}, floor_id=floor_id)

    # Losing yell when HP falls below 20 while alive
    if 0 < dk.hp < 20 and not dk.losing_announced:
        dk.losing_announced = True
        game.add_event("BOSS_YELL", {"mob": dk.id, "text": YELL_LOSING, "x": dk.pos.x, "y": dk.pos.y}, floor_id=floor_id)

    if dk.hp <= 0:
        dk.hp = 0
        dk.is_alive = False
        dk.die(floor_mobs=floor.mobs, tile_x=dk.pos.x, tile_y=dk.pos.y,
               players=list(game._players_on_floor(floor_id)))
        game.add_event("DEATH", {"target": dk.id}, floor_id=floor_id)
        game.handle_mob_death(dk, floor, floor_id)
