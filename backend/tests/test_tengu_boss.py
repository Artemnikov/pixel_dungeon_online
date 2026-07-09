import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.entities.base import Position, Faction
from app.engine.entities.mobs import Tengu
from app.engine.dungeon.generator import TileType
from app.engine.game.floor_state import FloorState
from app.engine.manager import GameInstance
from app.engine.systems.loot import roll_drops
from app.engine.entities.subclasses import Subclass
from app.engine.game.ai_tengu import TURN_TICKS


def make_floor(floor_id=10, w=10, h=10):
    grid = [[TileType.FLOOR for _ in range(w)] for _ in range(h)]
    floor = FloorState(floor_id=floor_id, grid=grid, rooms=[], mobs={}, items={}, region="prison")
    floor.rebuild_flags()
    return floor


def make_game(floor):
    game = GameInstance("test-tengu")
    game.players = {}
    game.depth = floor.floor_id
    game.floors[floor.floor_id] = floor
    return game


def advance_turns(game, tengu, floor, n=1, collect_events=False):
    """Advance N game turns by calling _update_tengu TURN_TICKS times each.
    If collect_events=True, returns all events produced (otherwise flushes silently).
    """
    events = []
    for _ in range(n * TURN_TICKS):
        game._update_tengu(tengu, floor, floor.floor_id)
        if collect_events:
            events.extend(game.flush_events())
        else:
            game.flush_events()
    return events


def test_tengu_base_stats_match_original():
    tengu = Tengu(id="t1", pos=Position(x=0, y=0), faction=Faction.DUNGEON)
    assert tengu.hp == tengu.max_hp == 200
    assert tengu.attack_skill == 20
    assert tengu.is_enraged() is False

    tengu.hp = 100
    assert tengu.is_enraged() is True


def test_tengu_attack_skill_is_adjacency_based():
    floor = make_floor()
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.floor_id = floor.floor_id

    player.pos = Position(x=6, y=6)          # Chebyshev-adjacent (diagonal)
    game._update_tengu(tengu, floor, floor.floor_id)
    game.flush_events()
    assert tengu.attack_skill == 10

    player.pos = Position(x=5, y=1)          # ranged
    game._update_tengu(tengu, floor, floor.floor_id)
    game.flush_events()
    assert tengu.attack_skill == 20


def test_tengu_jumps_when_dropping_an_hp_bracket():
    floor = make_floor()
    game = make_game(floor)

    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)
    player.floor_id = floor.floor_id

    assert tengu.hp_bracket == 7

    # Drop from 200 -> 170 HP: bracket goes from 7 to 6, should trigger a jump.
    tengu.hp = 170
    consumed = game._update_tengu(tengu, floor, floor.floor_id)

    assert consumed is True
    assert tengu.hp_bracket == 6
    assert (tengu.pos.x, tengu.pos.y) != (5, 5)

    events = [e for e in game.flush_events() if e["type"] == "TENGU_JUMP"]
    assert len(events) == 1
    assert events[0]["data"]["mob"] == tengu.id


def test_tengu_no_jump_without_bracket_drop():
    floor = make_floor()
    game = make_game(floor)

    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=8, y=8)
    player.floor_id = floor.floor_id

    # Not enraged, no LOS in range -> no ability, no jump.
    consumed = game._update_tengu(tengu, floor, floor.floor_id)
    assert consumed is False
    assert (tengu.pos.x, tengu.pos.y) == (5, 5)
    assert tengu.hp_bracket == 7


def test_tengu_throws_bomb_when_enraged_and_detonates():
    floor = make_floor()
    game = make_game(floor)

    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    tengu.hp = 100  # enraged (<= 50% HP)
    tengu.hp_bracket = (tengu.hp * 8 - 1) // tengu.max_hp  # already settled into this bracket
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)
    player.floor_id = floor.floor_id

    # SPD initial cooldown (ability_cooldown=2) needs 2 game turns.
    # Advance 2 turns = 40 ticks. Bomb fires on the last tick (cooldown reaches 0).
    events = advance_turns(game, tengu, floor, 2, collect_events=True)
    # If bomb was placed, timer is exactly 60 (no countdown ticks passed yet).
    # If not, the jump consumed the first tick; advance one more partial turn.
    if not any(e["type"] == "TENGU_BOMB" for e in events):
        events = advance_turns(game, tengu, floor, 1, collect_events=True)
    assert any(e["type"] == "TENGU_BOMB" for e in events), "No bomb placed"
    # SPD BombAbility: bomb placed on a free neighbor of the target closest to Tengu
    # Tengu at (5,5), player at (5,4). Neighbors: (4,3),(5,3),(6,3),(4,4),(6,4),(4,5),(5,5),(6,5)
    # (5,5) is occupied by Tengu, closest free is (4,4),(6,4),(4,5),(6,5) all at dist 1
    assert tengu.bomb_timer == 60, f"Expected 60, got {tengu.bomb_timer}"
    assert tengu.bomb_x != -1 and tengu.bomb_y != -1
    assert not (tengu.bomb_x == 5 and tengu.bomb_y == 5)  # not on Tengu
    assert abs(tengu.bomb_x - 5) <= 1 and abs(tengu.bomb_y - 4) <= 1  # adjacent to player
    assert any(e["type"] == "TENGU_BOMB" for e in events)

    # Tick until detonation (bomb timer ticks every call regardless of turn gate).
    hp_before = player.hp
    bomb_go = tengu.bomb_timer
    for _ in range(bomb_go + 5):
        consumed = game._update_tengu(tengu, floor, floor.floor_id)
        events = game.flush_events()
        if any(e["type"] == "TENGU_BLAST" for e in events):
            break

    assert tengu.bomb_timer == 0
    assert tengu.bomb_x == -1 and tengu.bomb_y == -1
    assert any(e["type"] == "TENGU_BLAST" for e in events)
    assert player.hp < hp_before


def test_tengu_yells_gotcha_on_first_notice_at_full_hp():
    floor = make_floor()
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)
    player.floor_id = floor.floor_id

    game._update_tengu(tengu, floor, floor.floor_id)
    yells = [e for e in game.flush_events() if e["type"] == "BOSS_YELL"]
    assert any(y["data"]["text"] == "Gotcha, Hero!" for y in yells)
    assert tengu.noticed is True

    # No second notice yell on the next turn.
    game._update_tengu(tengu, floor, floor.floor_id)
    assert not any(e["type"] == "BOSS_YELL" and "otcha" in e["data"]["text"]
                   for e in game.flush_events())


def test_tengu_yells_defeated_on_death():
    floor = make_floor()
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    game.add_player("p1", "Hero")

    game.handle_mob_death(tengu, floor, floor.floor_id)
    assert any(e["type"] == "BOSS_YELL" and e["data"]["text"] == "Free at last..."
               for e in game.flush_events())


def test_tengu_shocker_emits_alternating_lightning_events():
    floor = make_floor()
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    tengu.shocker_active = True
    tengu.shocker_x, tengu.shocker_y = 5, 3
    tengu.shocking_ordinals = None
    floor.mobs[tengu.id] = tengu
    game.add_player("p1", "Hero")

    seen = []
    for _ in range(3):
        game._tick_tengu_shocker_turn(tengu, floor, floor.floor_id)
        for e in game.flush_events():
            if e["type"] == "TENGU_SHOCKER":
                seen.append(e["data"]["ordinals"])
    assert len(seen) >= 2
    assert seen[-1] != seen[-2]


def test_tengu_fire_direction_is_cardinal_for_shallow_oblique():
    floor = make_floor(w=12, h=12)
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=1, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=4, y=6)          # dx=3, dy=1 -> first step cardinal (1,0)
    player.floor_id = floor.floor_id

    assert game._tengu_throw_fire(tengu, player, floor, floor.floor_id) is True
    blob = next(b for b in floor.blob_areas.values() if b.get("type") == "tengu_fire")
    from app.engine.dungeon.spd_levelgen.level import _CIRCLE8_OFFSETS
    assert _CIRCLE8_OFFSETS[blob["direction"]] == (1, 0)


def test_tengu_bomb_emits_three_countdown_on_placement():
    floor = make_floor()
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    player = game.add_player("p1", "Hero")
    player.pos = Position(x=5, y=4)
    player.floor_id = floor.floor_id

    assert game._tengu_throw_bomb(tengu, player, floor, floor.floor_id) is True
    events = game.flush_events()
    cds = [e for e in events if e["type"] == "TENGU_BOMB_COUNTDOWN"]
    assert any(e["data"]["count"] == 3 for e in cds)


def test_tengu_bomb_blast_respects_walls():
    floor = make_floor(w=7, h=7)
    # Solid wall column at x=3 for y=2..4 (isolates left half from right half)
    for yy in (2, 3, 4):
        floor.grid[yy][3] = TileType.WALL
    floor.rebuild_flags()
    game = make_game(floor)
    tengu = Tengu(id="t1", pos=Position(x=1, y=3), faction=Faction.DUNGEON)
    floor.mobs[tengu.id] = tengu
    game.add_player("p1", "Hero")

    cells = game._bomb_blast_cells(floor, 2, 3)   # bomb just left of the wall
    assert (2, 3) in cells
    assert (5, 3) not in cells                     # right of the wall, unreachable
    assert (4, 3) not in cells                     # behind the wall column


def test_tengu_mask_drops_for_player_without_subclass():
    game = make_game(make_floor())
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    player = game.add_player("p1", "Hero")
    assert player.subclass_info.subclass is None

    drops = roll_drops(tengu, {}, 5, 5, players=[player])
    assert any(item.kind == "tengu_mask" for item in drops)


def test_tengu_mask_does_not_drop_once_all_players_have_subclass():
    game = make_game(make_floor())
    tengu = Tengu(id="t1", pos=Position(x=5, y=5), faction=Faction.DUNGEON)
    player = game.add_player("p1", "Hero")
    player.subclass_info.subclass = Subclass.BERSERKER

    drops = roll_drops(tengu, {}, 5, 5, players=[player])
    assert not any(item.kind == "tengu_mask" for item in drops)
