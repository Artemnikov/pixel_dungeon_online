"""Surprise-attack window on LOS reacquisition.

SPD Mob.surprisedBy returns true while the mob's enemySeen flag is stale: a mob
that saw a player, lost sight of them, then sees them again doesn't re-process
the sighting until its next act. In this real-time remake that stale-tick state
is an explicit SURPRISE_WINDOW_SECONDS window during which that player's strikes
(melee and ranged) land as surprise attacks: auto-hit + crit.
"""
import time

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.items.wands import WandOfMagicMissile
from app.engine.entities.mobs import Rat
from app.engine.entities.player import Difficulty, Mob as MobEntity, Player
from app.engine.game.constants import SURPRISE_WINDOW_SECONDS
from app.engine.manager import GameInstance
from app.engine.systems.combat import resolve_melee_attack, resolve_ranged_attack


def _open_game(w: int = 12, h: int = 12) -> GameInstance:
    import uuid
    game = GameInstance(f"test-surprise-{uuid.uuid4()}")
    game.players = {}
    game.mobs = {}
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor.mobs.clear()
    floor.items.clear()
    floor.traps.clear()
    floor.plants.clear()
    floor.rebuild_flags()
    game.difficulty = Difficulty.NORMAL
    return game


def _combat_mob(**kwargs) -> MobEntity:
    defaults = dict(
        id="m", name="Rat", pos=Position(x=2, y=1),
        hp=50, max_hp=50, attack=2, defense=0,
        defense_skill=0, dr_min=0, dr_max=0,
    )
    defaults.update(kwargs)
    return MobEntity(**defaults)


def _combat_player(**kwargs) -> Player:
    defaults = dict(
        id="p", name="Tester", pos=Position(x=1, y=1),
        hp=20, max_hp=20, attack=3, defense=1,
        attack_skill=100, defense_skill=0,
    )
    defaults.update(kwargs)
    return Player(**defaults)


def test_active_window_grants_surprise_crit():
    # Player IS in the mob's FOV at strike time, but the mob just reacquired
    # them after a LOS break -> surprise auto-hit + crit.
    player = _combat_player()
    mob = _combat_mob(
        ai_state="hunting",
        surprise_windows={player.id: time.time() + SURPRISE_WINDOW_SECONDS},
    )

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["hit"] is True
    assert result["surprise"] is True
    assert result["crit"] is True


def test_expired_window_no_surprise():
    player = _combat_player()
    mob = _combat_mob(
        ai_state="hunting",
        surprise_windows={player.id: time.time() - 1.0},
    )

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["surprise"] is False
    assert result["crit"] is False
    assert result["hit"] is True  # normal accuracy roll (0 defense still lands)


def test_window_is_per_player():
    # Only the player who actually broke and reacquired LOS gets the window.
    player = _combat_player()
    mob = _combat_mob(
        ai_state="hunting",
        surprise_windows={"someone-else": time.time() + SURPRISE_WINDOW_SECONDS},
    )

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["surprise"] is False


def test_window_applies_to_ranged_attacks():
    player = _combat_player()
    mob = _combat_mob(
        ai_state="hunting",
        surprise_windows={player.id: time.time() + SURPRISE_WINDOW_SECONDS},
    )
    item = WandOfMagicMissile(id="w1", charges=3)

    result = resolve_ranged_attack(
        player, mob, item, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["hit"] is True
    assert result["surprise"] is True
    assert result["crit"] is True


def test_los_reacquisition_arms_window_then_zap_crits():
    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=2, y=5)
    floor = game._get_or_create_floor(game.depth)

    mob = game._spawn_mob_at(Rat, 6, 5)
    game.mobs[mob.id] = mob
    floor.mobs[mob.id] = mob
    mob.ai_state = "hunting"
    mob.max_hp = 50
    mob.hp = 50
    mob.speed = 0.0
    mob.defense_skill = 0
    mob.dr_min = 0
    mob.dr_max = 0

    # Phase 1: mob has LOS on the player (first sight arms no window).
    for _ in range(50):
        game.update_tick()
        if mob.los_prev_seen.get("p1") is True:
            break
    assert mob.los_prev_seen.get("p1") is True
    assert mob.surprise_windows == {}

    # Phase 2: a wall blocks LOS -> mob loses sight of the player.
    floor.grid[5][4] = TileType.WALL
    floor.rebuild_flags()
    for _ in range(50):
        game.update_tick()
        if mob.los_prev_seen.get("p1") is False:
            break
    assert mob.los_prev_seen.get("p1") is False

    # Phase 3: wall removed, player reappears in the mob's FOV -> window armed.
    floor.grid[5][4] = TileType.FLOOR
    floor.rebuild_flags()
    game.update_tick()
    assert mob.surprise_windows.get("p1", 0.0) > time.time()

    # Phase 4: a wand zap during the window is a crit surprise hit.
    mob.surprise_windows["p1"] = time.time() + 10.0
    player.last_attack_time = 0.0
    player.attack_skill = 999
    mob.defense_skill = 0
    wand = WandOfMagicMissile(id="w1", charges=3)
    player.belongings.backpack.items.append(wand)
    game.events.clear()
    game.perform_ranged_attack("p1", "w1", mob.pos.x, mob.pos.y)
    damage_events = [
        ev for ev in game.events
        if ev["type"] == "DAMAGE" and ev["data"].get("target") == mob.id
    ]
    assert damage_events, "wand zap should damage the rat"
    assert damage_events[-1]["data"]["crit"] is True
    assert 0 < mob.hp < 50

    # Phase 5: after the window expires, the same zap is no longer a crit.
    mob.surprise_windows["p1"] = time.time() - 1.0
    player.last_attack_time = 0.0
    game.events.clear()
    game.perform_ranged_attack("p1", "w1", mob.pos.x, mob.pos.y)
    damage_events = [
        ev for ev in game.events
        if ev["type"] == "DAMAGE" and ev["data"].get("target") == mob.id
    ]
    assert damage_events, "wand zap should still damage the rat"
    assert damage_events[-1]["data"]["crit"] is False
