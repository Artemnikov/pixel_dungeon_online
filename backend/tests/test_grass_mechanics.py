"""SPD grass-mechanics fidelity: tall grass concealment, surprise attacks on
unaware mobs, dew drop pickup, and trample/furrow semantics.

References: HighGrass.java, Dewdrop.java, Mob.java (surprisedBy/enemySeen),
Hero.canSurpriseAttack, Char.hit.
"""
import time

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.items_consumable import Dewdrop, Waterskin
from app.engine.entities.items_equip import make_named_melee_weapon
from app.engine.entities.mobs import Rat
from app.engine.entities.player import Difficulty, Mob as MobEntity, Player
from app.engine.manager import GameInstance
from app.engine.systems.combat import resolve_melee_attack


def _open_game(w: int = 12, h: int = 12) -> GameInstance:
    game = GameInstance("test-game")
    game.players = {}
    game.mobs = {}
    game.grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    game._get_or_create_floor(game.depth).rebuild_flags()
    game.difficulty = Difficulty.NORMAL
    return game


def _grass_wall(game: GameInstance, x: int):
    floor = game._get_or_create_floor(game.depth)
    for y in range(floor.height):
        floor.grid[y][x] = TileType.HIGH_GRASS
    floor.rebuild_flags()
    return floor


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


# --- Tall grass conceals players from mob detection -------------------------
# SPD Mob.act(): enemyInFOV requires fieldOfView[enemy.pos]; HIGH_GRASS is
# LOS-blocking, so a player behind it can't be noticed regardless of range.

def test_high_grass_blocks_sleeping_mob_detection():
    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=2, y=5)
    mob = game._spawn_mob_at(Rat, 8, 5)
    game.mobs[mob.id] = mob
    mob.ai_state = "idle"
    _grass_wall(game, 5)

    for _ in range(100):
        game.update_tick()

    assert mob.ai_state == "idle"


def test_sleeping_mob_notices_player_with_clear_los():
    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=6, y=5)
    mob = game._spawn_mob_at(Rat, 8, 5)
    game.mobs[mob.id] = mob
    mob.ai_state = "idle"

    for _ in range(200):
        game.update_tick()
        if mob.ai_state == "hunting":
            break

    assert mob.ai_state == "hunting"


def test_high_grass_blocks_wandering_mob_detection():
    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=2, y=5)
    mob = game._spawn_mob_at(Rat, 8, 5)
    game.mobs[mob.id] = mob
    mob.ai_state = "wandering"
    _grass_wall(game, 5)

    for _ in range(100):
        # pin the mob in place so it can't wander around the grass wall
        game._mob_move_times = {mob.id: time.time() + 9999}
        game.update_tick()

    assert mob.ai_state == "wandering"


# --- Surprise attacks --------------------------------------------------------
# SPD Mob.surprisedBy: a mob that never noticed you (sleeping/wandering) is
# surprised even in plain sight; only hunting/fleeing mobs rely on FOV.

def test_attacking_unaware_mob_is_surprise():
    player = _combat_player()
    mob = _combat_mob(ai_state="sleeping", defense_skill=100)

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["hit"] is True
    assert result["surprise"] is True


def test_attacking_aware_visible_mob_is_not_surprise():
    player = _combat_player()
    mob = _combat_mob(ai_state="hunting")

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["hit"] is True
    assert result["surprise"] is False


def test_flail_cannot_surprise_attack():
    # SPD Hero.canSurpriseAttack: Flails never sneak-attack.
    player = _combat_player(strength=18)
    player.belongings.weapon = make_named_melee_weapon("Flail")
    mob = _combat_mob(ai_state="sleeping")

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["surprise"] is False


def test_understrength_weapon_cannot_surprise_attack():
    # SPD Hero.canSurpriseAttack: STR below the weapon requirement disables it.
    player = _combat_player(strength=10)
    player.belongings.weapon = make_named_melee_weapon("Greatsword")
    mob = _combat_mob(ai_state="sleeping")

    result = resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert result["surprise"] is False


def test_mob_wakes_to_wandering_when_damaged():
    # SPD Mob.damage(): SLEEPING -> WANDERING (no auto-lock onto an unseen attacker).
    player = _combat_player()
    mob = _combat_mob(ai_state="sleeping", defense_skill=100)

    resolve_melee_attack(
        player, mob, {}, player.pos.x, player.pos.y,
        is_in_los=lambda a, b: True,
    )
    assert mob.ai_state == "wandering"


def test_mob_attacker_gets_no_los_surprise_on_player():
    # SPD: only mobs are surprised (surprisedBy requires enemy == hero); a mob
    # attacking a player who can't see it still rolls accuracy normally.
    mob = _combat_mob(ai_state="hunting", attack_skill=100)
    player = _combat_player(defense_skill=0)
    player.belongings.armor = None

    result = resolve_melee_attack(
        mob, player, {}, mob.pos.x, mob.pos.y,
        is_in_los=lambda a, b: False,
    )
    assert result["surprise"] is False
    assert result["hit"] is True  # 100 attack vs 0 defense still lands


def test_wand_zap_dispels_invisibility():
    # SPD Invisibility.dispel(): any wand zap breaks invisibility, even one
    # aimed at empty ground (only entity hits went through the ranged resolver).
    from app.engine.entities.items_wands import WandOfMagicMissile

    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=1, y=1)
    player.last_attack_time = 0.0
    wand = WandOfMagicMissile(id="w1", charges=3)
    player.add_to_inventory(wand)
    player.add_buff("invisibility", duration=20.0)
    assert player.invisible > 0

    game.perform_ranged_attack("p1", "w1", 4, 1)  # empty tile

    assert player.invisible == 0


# --- Dew drops ----------------------------------------------------------------
# SPD Dewdrop.doPickUp: waterskin first; otherwise drink on the spot (5% max HP
# per drop); refuse pickup entirely at full HP unless on an entrance/exit tile.

def _strip_waterskins(player: Player):
    for it in list(player.inventory):
        if isinstance(it, Waterskin):
            player.belongings.backpack.detach(it.id)


def _drop_dew(game: GameInstance, x: int, y: int) -> Dewdrop:
    floor = game._get_or_create_floor(game.depth)
    dew = Dewdrop(id="dew-1", name="Dewdrop", pos=Position(x=x, y=y))
    floor.items[dew.id] = dew
    return dew


def test_dew_pickup_heals_without_waterskin():
    game = _open_game()
    player = game.add_player("p1", "Player")
    _strip_waterskins(player)
    player.pos = Position(x=1, y=1)
    player.max_hp = 20
    player.hp = 10
    _drop_dew(game, 2, 1)
    floor = game._get_or_create_floor(game.depth)

    game.move_entity("p1", 1, 0)

    assert player.hp == 10 + round(player.get_total_max_hp() * 0.05)
    assert "dew-1" not in floor.items
    assert not any(isinstance(i, Dewdrop) for i in player.inventory)


def test_dew_pickup_refused_at_full_hp():
    game = _open_game()
    player = game.add_player("p1", "Player")
    _strip_waterskins(player)
    player.pos = Position(x=1, y=1)
    player.hp = player.get_total_max_hp()
    _drop_dew(game, 2, 1)
    floor = game._get_or_create_floor(game.depth)

    game.move_entity("p1", 1, 0)

    assert "dew-1" in floor.items  # left on the ground
    assert not any(isinstance(i, Dewdrop) for i in player.inventory)


def test_dew_fills_waterskin_first():
    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=1, y=1)
    player.hp = 5  # even injured, the waterskin takes priority
    waterskin = next(i for i in player.inventory if isinstance(i, Waterskin))
    waterskin.volume = 0
    _drop_dew(game, 2, 1)
    floor = game._get_or_create_floor(game.depth)

    game.move_entity("p1", 1, 0)

    assert waterskin.volume == 1
    assert player.hp == 5
    assert "dew-1" not in floor.items


def test_dew_consumed_on_stairs_even_at_full_hp():
    game = _open_game()
    player = game.add_player("p1", "Player")
    _strip_waterskins(player)
    player.pos = Position(x=1, y=1)
    player.hp = player.get_total_max_hp()
    floor = game._get_or_create_floor(game.depth)
    floor.grid[1][2] = TileType.STAIRS_UP  # floor 1: no amulet, so no transition
    floor.rebuild_flags()
    _drop_dew(game, 2, 1)

    game.move_entity("p1", 1, 0)

    assert "dew-1" not in floor.items  # force-consumed, SPD entrance/exit rule
    assert not any(isinstance(i, Dewdrop) for i in player.inventory)


# --- Trample / furrowed grass ---------------------------------------------
# SPD HighGrass.trample keys off the huntress *class*: she furrows high grass
# and never tramples furrowed grass down, regardless of subclass.

def test_huntress_keeps_furrowed_grass():
    game = _open_game()
    player = game.add_player("p1", "Player", class_type="huntress")
    player.pos = Position(x=1, y=1)
    floor = game._get_or_create_floor(game.depth)
    floor.grid[1][2] = TileType.FURROWED_GRASS
    floor.rebuild_flags()

    game.move_entity("p1", 1, 0)

    assert floor.grid[1][2] == TileType.FURROWED_GRASS


def test_non_huntress_tramples_furrowed_to_short_grass():
    game = _open_game()
    player = game.add_player("p1", "Player", class_type="warrior")
    player.pos = Position(x=1, y=1)
    floor = game._get_or_create_floor(game.depth)
    floor.grid[1][2] = TileType.FURROWED_GRASS
    floor.rebuild_flags()

    game.move_entity("p1", 1, 0)

    assert floor.grid[1][2] == TileType.FLOOR_GRASS


def test_huntress_furrows_high_grass():
    game = _open_game()
    player = game.add_player("p1", "Player", class_type="huntress")
    player.pos = Position(x=1, y=1)
    floor = game._get_or_create_floor(game.depth)
    floor.grid[1][2] = TileType.HIGH_GRASS
    floor.rebuild_flags()

    game.move_entity("p1", 1, 0)

    assert floor.grid[1][2] == TileType.FURROWED_GRASS


def test_cursed_sandals_suppress_grass_loot(monkeypatch):
    from app.engine.entities.items_artifacts import SandalsOfNature
    from app.engine.game import terrain_effects

    game = _open_game()
    player = game.add_player("p1", "Player")
    player.pos = Position(x=3, y=3)
    floor = game._get_or_create_floor(game.depth)
    monkeypatch.setattr(terrain_effects.random, "random", lambda: 0.0)

    # Cursed equipped sandals: no grass loot at all (SPD naturalismLevel = -1).
    player.belongings.artifact = SandalsOfNature(id="sandals", cursed=True)
    before = set(floor.items)
    terrain_effects.roll_grass_loot(floor, player)
    assert set(floor.items) == before

    # Uncursed: loot rolls proceed (random forced to 0 -> seed + dew drop).
    player.belongings.artifact = SandalsOfNature(id="sandals2", cursed=False)
    terrain_effects.roll_grass_loot(floor, player)
    assert len(floor.items) > len(before)


def test_naturalism_level_mapping():
    from app.engine.entities.items_artifacts import SandalsOfNature
    from app.engine.game.terrain_effects import _naturalism_level

    player = _combat_player()
    assert _naturalism_level(player) == 0

    sandals = SandalsOfNature(id="s", level=2)
    player.belongings.artifact = sandals
    assert _naturalism_level(player) == 3  # SPD: itemLevel() + 1

    sandals.level = 9  # remake levels past SPD's +3 cap; loot range stays SPD's
    assert _naturalism_level(player) == 4

    sandals.cursed = True
    assert _naturalism_level(player) == -1
