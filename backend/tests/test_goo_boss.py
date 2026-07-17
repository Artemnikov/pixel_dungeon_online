import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position, Faction
from app.engine.entities.items_consumable import Key
from app.engine.entities.player import Player
from app.engine.entities.mobs import Goo
from app.engine.dungeon.constants import TileType
from app.engine.dungeon.models import Room
from app.engine.game.constants import OOZE_DURATION
from app.engine.manager import GameInstance


def make_goo_floor(seed=1):
    # Builds the real SPD-faithful sewers boss floor (depth 5) via the live
    # spd_levelgen pipeline -- this already spawns its own Goo/RatKing and a
    # "goo_door"-keyed locked exit (spd_adapter.py), matching SewerBossLevel.
    game = GameInstance(f"goo-floor-seed-{seed}")
    floor = game.generate_floor(5)
    return floor, floor.rooms


# ---------------------------------------------------------------------------
# Stats / enrage
# ---------------------------------------------------------------------------

def test_goo_base_stats_match_original():
    goo = Goo(id="g1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    assert goo.hp == goo.max_hp == 100
    assert goo.attack_skill == 10
    assert goo.defense_skill == 8
    assert goo.get_damage_min() == 1
    assert goo.get_damage_max() == 8
    assert goo.exp == 10
    assert goo.is_enraged() is False


def test_goo_enrages_at_half_hp():
    goo = Goo(id="g1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    goo.hp = 51
    assert goo.is_enraged() is False
    assert goo.get_damage_max() == 8
    assert goo.get_effective_defense_skill() == 8

    goo.hp = 50
    assert goo.is_enraged() is True
    assert goo.get_damage_max() == 12
    assert goo.get_effective_defense_skill() == 12  # 8 * 1.5


# ---------------------------------------------------------------------------
# Ooze on hit
# ---------------------------------------------------------------------------

def test_goo_fight_started_fires_once_on_notice():
    # Mirrors SPD's Goo.notice() -> Level.seal() -> boss music start: the
    # backend should announce the fight exactly once, the moment Goo's AI
    # notices the hero (ai_state flips from idle to hunting).
    game = GameInstance("test-goo-notice")
    game.players = {}
    game.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = None  # stale from the real depth-1 floor; out of bounds for this 10x10 grid
    floor.rebuild_flags()
    game.mobs = {}

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    game.mobs[goo.id] = goo
    assert goo.ai_state == "idle"
    assert goo.fight_started is False

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)

    fired = []
    for _ in range(300):
        game.update_tick()
        fired += [e for e in game.flush_events() if e["type"] == "GOO_FIGHT_STARTED"]
        if goo.ai_state == "hunting":
            break

    assert goo.ai_state == "hunting", "Goo should eventually notice the adjacent hero"
    assert len(fired) == 1, "GOO_FIGHT_STARTED must fire exactly once"
    assert fired[0]["data"] == {"mob": goo.id}
    assert goo.fight_started is True


def test_goo_does_not_freeze_when_player_starts_diagonally_adjacent():
    # A player spawning diagonally adjacent (Manhattan dist 2) to a still-idle
    # Goo is within charge range. Before notice() (ai_state -> hunting), the
    # pumped-up charge must not engage and short-circuit the AI - otherwise
    # Goo gets stuck on its spawn tile forever, never starting the fight.
    game = GameInstance("test-goo-diagonal")
    game.players = {}
    game.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = None  # stale from the real depth-1 floor; out of bounds for this 10x10 grid
    floor.rebuild_flags()
    game.mobs = {}

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    game.mobs[goo.id] = goo
    assert goo.ai_state == "idle"

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=6, y=6)

    for _ in range(300):
        game.update_tick()
        game.flush_events()
        if goo.ai_state == "hunting":
            break

    assert goo.ai_state == "hunting", "Goo should notice the diagonally adjacent hero"
    assert goo.fight_started is True


def test_goo_can_chase_through_rat_king_room():
    # On the boss floor, floor.rooms includes the Rat King secret room as
    # rooms[-1], which can overlap Goo's own arena. Regression test for the
    # since-removed safe-room movement restriction, which used to trap Goo
    # on its spawn tile whenever its only step toward the hero fell inside
    # that room's bounding box.
    game = GameInstance("test-goo-ratking-room")
    game.players = {}
    game.grid = [[TileType.FLOOR for _ in range(20)] for _ in range(20)]
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = None  # stale from the real depth-1 floor; out of bounds for this 20x20 grid
    floor.rebuild_flags()
    # Rat King room (rooms[-1]) covers the tile directly above Goo - Goo's
    # own spawn tile is outside it, so this only blocks the first step.
    floor.rooms = [
        Room(x=0, y=0, width=1, height=1),
        Room(x=9, y=9, width=2, height=1),
    ]
    game.mobs = {}

    goo = Goo(id="goo1", pos=Position(x=10, y=10), faction=Faction.DUNGEON)
    game.mobs[goo.id] = goo

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=10, y=5)

    for _ in range(300):
        game.update_tick()
        game.flush_events()
        if (goo.pos.x, goo.pos.y) != (10, 10):
            break

    assert (goo.pos.x, goo.pos.y) != (10, 10), "Goo must be able to step into its own arena even if it overlaps the Rat King room"


def test_goo_enrage_no_longer_plays_alert_sound():
    # SPD's Goo.damage() plays no sound at the bleed/enrage threshold (only a
    # status text + yell + bleed visuals) — the backend used to also fire a
    # PLAY_SOUND/ALERT here, which the original doesn't; it should be gone now.
    game = GameInstance("test-goo-enrage-sound")
    game.players = {}
    game.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    game._get_or_create_floor(game.depth).rebuild_flags()
    game.mobs = {}

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.hp = goo.max_hp // 2
    game.mobs[goo.id] = goo

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)

    floor = game._get_or_create_floor(game.depth)
    game._goo_sync_enrage(goo, floor.floor_id)
    events = game.flush_events()

    assert any(e["type"] == "GOO_ENRAGE" for e in events)
    assert not any(e["type"] == "PLAY_SOUND" and e["data"].get("sound") == "ALERT" for e in events)


def test_goo_attack_proc_can_apply_ooze():
    goo = Goo(id="g1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    target = Player(id="p1", name="Hero", pos=Position(x=1, y=0), hp=50, max_hp=50, faction=Faction.PLAYER)

    import random
    random.seed(0)
    applied = False
    for _ in range(200):
        target.ooze_amount = 0
        goo.attack_proc(target)
        if target.ooze_amount == OOZE_DURATION:
            applied = True
            break
    assert applied, "attack_proc should eventually apply ooze (~1/3 chance per the original)"


# ---------------------------------------------------------------------------
# Boss floor generation: water arena + locked exit
# ---------------------------------------------------------------------------

def test_boss_floor_has_water_arena_and_locked_door():
    floor, rooms = make_goo_floor()

    water_tiles = sum(
        1 for row in floor.grid for cell in row if cell == TileType.FLOOR_WATER
    )
    assert water_tiles > 0, "Boss arena should contain a water pool (Goo heals there)"

    assert len(floor.locked_doors) == 1
    (dx, dy), key_id = next(iter(floor.locked_doors.items()))
    # Java Level.exit() resolves via the registered LevelTransition, so it
    # finds the exit cell regardless of terrain (EXIT or LOCKED_EXIT). Our
    # port instead scans the map for a terrain id -- it must recognize
    # LOCKED_EXIT too, or floor.exit_pos (used by the frontend's
    # compass-to-exit indicator) silently comes back None on boss floors.
    assert floor.exit_pos == (dx, dy)
    assert key_id == "goo_door"
    assert floor.grid[dy][dx] == TileType.LOCKED_EXIT
    assert floor.flags.passable[dy][dx] is False, "Locked door must block movement until unlocked"


# ---------------------------------------------------------------------------
# Boss death: key + loot drops, idempotent
# ---------------------------------------------------------------------------

def test_goo_death_drops_key_matching_locked_door():
    floor, rooms = make_goo_floor()
    goo = Goo(id=str(uuid.uuid4()), pos=Position(x=rooms[1].center[0], y=rooms[1].center[1]),
              faction=Faction.DUNGEON)
    floor.mobs[goo.id] = goo

    game = GameInstance("test-goo-death")
    game.handle_mob_death(goo, floor, 5)

    keys = [i for i in floor.items.values() if isinstance(i, Key)]
    assert len(keys) == 1
    assert keys[0].key_id == "goo_door"
    assert keys[0].name == "Worn Key"

    door_key_id = next(iter(floor.locked_doors.values()))
    assert keys[0].key_id == door_key_id


def test_goo_death_is_idempotent_single_key():
    floor, rooms = make_goo_floor()
    goo = Goo(id=str(uuid.uuid4()), pos=Position(x=rooms[1].center[0], y=rooms[1].center[1]),
              faction=Faction.DUNGEON)
    floor.mobs[goo.id] = goo

    game = GameInstance("test-goo-death-2")
    game.handle_mob_death(goo, floor, 5)
    game.handle_mob_death(goo, floor, 5)

    keys = [i for i in floor.items.values() if isinstance(i, Key)]
    assert len(keys) == 1, "Calling the death handler twice must not drop a second key"


def test_key_unlocks_the_boss_door():
    floor, rooms = make_goo_floor()
    (dx, dy), key_id = next(iter(floor.locked_doors.items()))

    game = GameInstance("test-goo-unlock")
    player = Player(id="p1", name="Hero", pos=Position(x=dx - 1, y=dy), hp=50, max_hp=50, faction=Faction.PLAYER)
    player.add_key(key_id, floor.floor_id, "Worn Key")

    assert game._try_unlock_locked_door(player, floor, dx, dy) is True
    # Boss-arena exit (goo_door) unlocks into stairs down, not a regular door.
    assert floor.grid[dy][dx] == TileType.STAIRS_DOWN
    assert floor.locked_doors == {}
    assert floor.flags.passable[dy][dx] is True
    assert player.key_count(key_id, floor.floor_id) == 0


def test_locked_door_blocks_without_matching_key():
    floor, rooms = make_goo_floor()
    (dx, dy), key_id = next(iter(floor.locked_doors.items()))

    game = GameInstance("test-goo-no-key")
    player = Player(id="p1", name="Hero", pos=Position(x=dx - 1, y=dy), hp=50, max_hp=50, faction=Faction.PLAYER)

    assert game._try_unlock_locked_door(player, floor, dx, dy) is False
    assert floor.grid[dy][dx] == TileType.LOCKED_EXIT
    assert (dx, dy) in floor.locked_doors


def test_unlock_non_goo_door_stays_a_door():
    floor, rooms = make_goo_floor()
    (dx, dy), _key_id = next(iter(floor.locked_doors.items()))
    # The boss arena's own door is always a LOCKED_EXIT (unlocks to stairs);
    # to exercise a regular locked door with a non-goo key, swap the tile too.
    floor.grid[dy][dx] = TileType.LOCKED_DOOR
    floor.locked_doors[(dx, dy)] = "iron"

    game = GameInstance("test-iron-unlock")
    player = Player(id="p1", name="Hero", pos=Position(x=dx - 1, y=dy), hp=50, max_hp=50, faction=Faction.PLAYER)
    player.add_key("iron", floor.floor_id, "Iron Key")

    assert game._try_unlock_locked_door(player, floor, dx, dy) is True
    assert floor.grid[dy][dx] == TileType.DOOR


# ---------------------------------------------------------------------------
# Entrance seal (SPD Level.seal()/unseal()) + boss-challenge badge/score
# ---------------------------------------------------------------------------

def test_goo_fight_started_seals_entrance_with_water():
    # Mirrors SPD's Goo.notice() -> Level.seal(): the floor's entrance tile
    # turns to water (blocking the stairs-up interaction) so the hero can't
    # flee mid-fight, and the run becomes eligible for the challenge badge.
    game = GameInstance("test-goo-seal")
    game.players = {}
    game.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = (2, 2)
    floor.grid[2][2] = TileType.STAIRS_UP
    floor.rebuild_flags()
    game.mobs = {}
    game.qualified_for_boss_challenge = False

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    game.mobs[goo.id] = goo

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)

    patches = []
    for _ in range(300):
        game.update_tick()
        patches += [e for e in game.flush_events() if e["type"] == "MAP_PATCH"]
        if goo.ai_state == "hunting":
            break

    assert goo.ai_state == "hunting"
    assert floor.grid[2][2] == TileType.FLOOR_WATER, "Entrance must turn to water once Goo notices the hero"
    assert any(p["data"]["tiles"] == [{"x": 2, "y": 2, "tile": TileType.FLOOR_WATER}] for p in patches)
    assert game.qualified_for_boss_challenge is True


def test_goo_unseal_entrance_restores_stairs_and_is_idempotent():
    game = GameInstance("test-goo-unseal")
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = (2, 2)
    floor.grid[2][2] = TileType.FLOOR_WATER
    floor.rebuild_flags()

    game._goo_unseal_entrance(floor, floor.floor_id)
    assert floor.grid[2][2] == TileType.STAIRS_UP
    patches = [e for e in game.flush_events() if e["type"] == "MAP_PATCH"]
    assert len(patches) == 1
    assert patches[0]["data"]["tiles"] == [{"x": 2, "y": 2, "tile": TileType.STAIRS_UP}]

    # Calling again once already unsealed must not re-emit a patch.
    game._goo_unseal_entrance(floor, floor.floor_id)
    assert game.flush_events() == []


def test_goo_water_heal_disqualifies_boss_challenge_badge():
    # SPD Goo.act(): healing in water sets qualifiedForBossChallengeBadge = false.
    game = GameInstance("test-goo-water-heal-badge")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR_WATER for _ in range(10)] for _ in range(10)]
    floor.rebuild_flags()
    game.qualified_for_boss_challenge = True

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.hp = goo.max_hp - 10
    goo.heal_cooldown = 0

    game._goo_water_heal(goo, floor, floor.floor_id)

    assert goo.hp == goo.max_hp - 10 + goo.heal_inc
    assert game.qualified_for_boss_challenge is False


def test_goo_pumped_release_penalizes_score_and_badge():
    # SPD Goo.damageRoll()/attack(): completing a pumped charge against the
    # hero (hit or miss) always costs 100 score and disqualifies the badge.
    game = GameInstance("test-goo-pumped-penalty")
    game.boss_scores[0] = 0
    game.qualified_for_boss_challenge = True

    goo = Goo(id="goo1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    target = Player(id="p1", name="Hero", pos=Position(x=1, y=0), hp=50, max_hp=50, faction=Faction.PLAYER)

    game._goo_release_charge(goo, target, 5)

    assert game.boss_scores[0] == -100
    assert game.qualified_for_boss_challenge is False


def test_goo_death_unseals_entrance_and_awards_boss_score():
    floor, rooms = make_goo_floor()
    floor.entrance_pos = (1, 1)
    floor.grid[1][1] = TileType.STAIRS_UP
    floor.rebuild_flags()

    game = GameInstance("test-goo-death-unseal")
    game.boss_scores[0] = 0
    game.qualified_for_boss_challenge = True
    game._goo_seal_entrance(floor, floor.floor_id)
    game.flush_events()
    assert floor.grid[1][1] == TileType.FLOOR_WATER

    goo = Goo(id=str(uuid.uuid4()), pos=Position(x=rooms[1].center[0], y=rooms[1].center[1]),
              faction=Faction.DUNGEON)
    floor.mobs[goo.id] = goo

    game.handle_mob_death(goo, floor, 5)
    events = game.flush_events()

    assert floor.grid[1][1] == TileType.STAIRS_UP, "Goo's death must unseal the entrance"
    assert game.boss_scores[0] == 1000
    assert any(e["type"] == "GOO_BADGE_QUALIFIED" for e in events)


# ---------------------------------------------------------------------------
# Exit torches (SPD SewerBossLevel.addVisuals)
# ---------------------------------------------------------------------------

def test_boss_exit_flanked_by_torch_positions():
    # SPD SewerBossLevel.addVisuals(): a lit torch (flame + light halo, not a
    # terrain tile) flanks each side of the exit. WALL_DECO means something
    # else entirely in the sewers region (a dripping Sink decoration), so the
    # exit's terrain must stay plain WALL; the torch positions are tracked
    # separately for the frontend to render its own flame VFX.
    floor, rooms = make_goo_floor()
    (ex, ey), key_id = next(iter(floor.locked_doors.items()))
    assert key_id == "goo_door"
    assert floor.grid[ey][ex - 1] == TileType.WALL
    assert floor.grid[ey][ex + 1] == TileType.WALL
    assert set(floor.torches) == {(ex - 1, ey), (ex + 1, ey)}


# ---------------------------------------------------------------------------
# LockedFloor buff (SPD Level.seal()/unseal() + Regeneration.regenOn())
# ---------------------------------------------------------------------------

def test_goo_seal_sets_locked_floor_left_for_players_on_floor():
    game = GameInstance("test-goo-lockedfloor-seal")
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = (2, 2)
    floor.grid[2][2] = TileType.STAIRS_UP
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")
    assert player.locked_floor_left is None

    game._goo_seal_entrance(floor, floor.floor_id)
    assert player.locked_floor_left == 50.0


def test_goo_seal_uses_shorter_timer_with_stronger_bosses_challenge():
    game = GameInstance("test-goo-lockedfloor-seal-challenge")
    game.challenges = ["stronger_bosses"]
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = (2, 2)
    floor.grid[2][2] = TileType.STAIRS_UP
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")

    game._goo_seal_entrance(floor, floor.floor_id)
    assert player.locked_floor_left == 20.0


def test_goo_unseal_clears_locked_floor_left():
    game = GameInstance("test-goo-lockedfloor-unseal")
    floor = game._get_or_create_floor(game.depth)
    floor.entrance_pos = (2, 2)
    floor.grid[2][2] = TileType.FLOOR_WATER
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")
    player.locked_floor_left = 30.0

    game._goo_unseal_entrance(floor, floor.floor_id)
    assert player.locked_floor_left is None


def test_goo_water_heal_drains_locked_floor_time():
    game = GameInstance("test-goo-lockedfloor-drain")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR_WATER for _ in range(10)] for _ in range(10)]
    floor.rebuild_flags()
    player = game.add_player("p1", "Hero")
    player.locked_floor_left = 50.0

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.hp = goo.max_hp - 10
    goo.heal_cooldown = 0

    game._goo_water_heal(goo, floor, floor.floor_id)

    assert player.locked_floor_left == 50.0 - goo.heal_inc * 1.5


def test_goo_damage_taken_in_melee_adds_locked_floor_time():
    game = GameInstance("test-goo-lockedfloor-add")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor.rebuild_flags()
    floor.mobs = {}

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=4, y=5)
    player.attack_skill = 100
    player.locked_floor_left = 10.0

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.defense_skill = 0
    goo.dr_min = 0
    goo.dr_max = 0
    floor.mobs[goo.id] = goo

    game.move_entity(player.id, 1, 0)

    assert player.locked_floor_left is not None and player.locked_floor_left > 10.0


def test_goo_damage_taken_caps_locked_floor_time_at_50():
    game = GameInstance("test-goo-lockedfloor-cap")
    floor = game._get_or_create_floor(game.depth)
    floor.grid = [[TileType.FLOOR for _ in range(10)] for _ in range(10)]
    floor.rebuild_flags()
    floor.mobs = {}

    player = game.add_player("p1", "Hero")
    player.pos = Position(x=4, y=5)
    player.attack_skill = 100
    player.locked_floor_left = 49.0

    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.defense_skill = 0
    goo.dr_min = 0
    goo.dr_max = 0
    floor.mobs[goo.id] = goo

    game.move_entity(player.id, 1, 0)

    assert player.locked_floor_left == 50.0


def test_passive_regen_paused_once_locked_floor_time_runs_out():
    game = GameInstance("test-goo-lockedfloor-regen-block")
    floor = game._get_or_create_floor(game.depth)
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=floor.rooms[0].center[0], y=floor.rooms[0].center[1])
    player.hp = player.get_total_max_hp() - 10
    player.locked_floor_left = 0.5
    player._regen_cooldown = 0

    game._apply_passive_regen(player)

    assert player.hp == player.get_total_max_hp() - 10, "Regen must be paused while locked-floor time is exhausted"


def test_passive_regen_works_normally_without_locked_floor_buff():
    game = GameInstance("test-goo-lockedfloor-regen-ok")
    floor = game._get_or_create_floor(game.depth)
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=floor.rooms[0].center[0], y=floor.rooms[0].center[1])
    player.hp = player.get_total_max_hp() - 10
    player._regen_cooldown = 0

    game._apply_passive_regen(player)

    assert player.hp == player.get_total_max_hp() - 9


def test_locked_floor_buff_surfaces_as_active_effect_icon():
    game = GameInstance("test-goo-lockedfloor-icon")
    player = game.add_player("p1", "Hero")
    player.locked_floor_left = 30.0

    game._sync_effects(player)

    effect = next((e for e in player.active_effects if e.key == "locked_floor"), None)
    assert effect is not None
    assert effect.icon == 35


# ---------------------------------------------------------------------------
# Boss music silencing while a boss is alive but hasn't been engaged yet
# (SPD SewerBossLevel.playLevelMusic: ambient track silenced while Goo lives)
# ---------------------------------------------------------------------------

def test_boss_lurking_true_while_goo_alive_and_unfought():
    game = GameInstance("test-boss-lurking")
    floor = game._get_or_create_floor(game.depth)
    floor.mobs = {}
    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[goo.id] = goo

    assert game._boss_lurking_on_floor(floor.floor_id) is True


def test_boss_lurking_false_once_fight_started():
    game = GameInstance("test-boss-lurking-started")
    floor = game._get_or_create_floor(game.depth)
    floor.mobs = {}
    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.fight_started = True
    floor.mobs[goo.id] = goo

    assert game._boss_lurking_on_floor(floor.floor_id) is False


def test_boss_lurking_false_once_goo_is_dead():
    game = GameInstance("test-boss-lurking-dead")
    floor = game._get_or_create_floor(game.depth)
    floor.mobs = {}
    goo = Goo(id="goo1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    goo.hp = 0
    goo.is_alive = False
    floor.mobs[goo.id] = goo

    assert game._boss_lurking_on_floor(floor.floor_id) is False


def test_boss_lurking_false_with_no_boss_mobs():
    game = GameInstance("test-boss-lurking-none")
    floor = game._get_or_create_floor(game.depth)
    floor.mobs = {}

    assert game._boss_lurking_on_floor(floor.floor_id) is False


# ---------------------------------------------------------------------------
# Rat King (sewer boss secret room NPC)
# ---------------------------------------------------------------------------

def test_floor5_spawns_rat_king_npc():
    from app.engine.entities.mobs import RatKing

    game = GameInstance("test-ratking")
    floor = game.generate_floor(5)

    rat_kings = [m for m in floor.mobs.values() if isinstance(m, RatKing)]
    assert len(rat_kings) == 1
    rat_king = rat_kings[0]
    assert rat_king.name == "Rat King"

    # Immune to all damage.
    assert rat_king.take_damage(9999) == 0
    assert rat_king.hp == rat_king.max_hp
    assert rat_king.is_alive is True

    # Always sleeping, never wakes/hunts.
    assert rat_king.ai_state == "sleeping"
    assert getattr(rat_king, "never_wakes", False) is True
    hunting_mobs = [m for m in floor.mobs.values() if m.ai_state == "hunting"]
    assert rat_king not in hunting_mobs
