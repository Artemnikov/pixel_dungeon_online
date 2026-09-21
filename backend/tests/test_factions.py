import pytest
import time
import uuid
from app.engine.manager import GameInstance
from app.engine.entities.base import Faction, Position

def test_faction_combat_restrictions():
    game = GameInstance("test_game")
    
    # Add two players (same faction)
    p1_id = "p1"
    p2_id = "p2"
    game.add_player(p1_id, "Player 1")
    game.add_player(p2_id, "Player 2")
    
    p1 = game.players[p1_id]
    p2 = game.players[p2_id]
    
    # Place them next to each other
    p1.pos = Position(x=1, y=1)
    p2.pos = Position(x=2, y=1)
    
    # Ensure they are on floor tiles for movement/combat
    game.grid[1][1] = 1 # Floor
    game.grid[1][2] = 1 # Floor
    
    initial_p2_hp = p2.hp
    
    # p1 tries to "move" onto p2 (should trigger combat check)
    game.move_entity(p1_id, 1, 0)
    
    # They are in the same faction, so p2 should NOT take damage
    assert p2.hp == initial_p2_hp, "Players should not damage each other"
    
    # Move p2 away so it doesn't interfere with mob targeting
    p2.pos = Position(x=5, y=5)
    # Manually move p1 so we know exact position
    p1.pos = Position(x=2, y=1)
    game.grid[1][3] = 1 # Floor at x=3, y=1
    
    # Add a mob (different faction) — orthogonally adjacent to p1 at (2,1)
    mob_id = "mob1"
    from app.engine.entities.player import Mob as MobEntity
    mob = MobEntity(
        id=mob_id,
        name="Rat",
        pos=Position(x=3, y=1),
        hp=50,
        max_hp=50,
        attack=2,
        defense=0,
        attack_skill=100,
        defense_skill=0,
        dr_min=0,
        dr_max=0,
        damage_min=20,
        damage_max=20,
        faction=Faction.DUNGEON
    )
    floor = game._get_or_create_floor(p1.floor_id)
    floor.mobs[mob_id] = mob
    p1.attack_skill = 100  # guarantee hits
    
    # p1 attacks mob (p1 at (2,1), mob at (3,1) — adjacent)
    game.move_entity(p1_id, 1, 0)
    
    # Different factions, mob SHOULD take damage
    assert mob.hp < 50, "Player should be able to attack mob"
    
    # Mob attacks player
    initial_p1_hp = p1.hp
    p1.defense = 0  # ensure damage goes through cloth armor DR
    p1.defense_skill = 0
    p1.belongings.armor = None  # remove default armor DR
    mob.damage_min = 20
    mob.damage_max = 20
    mob.attack_skill = 100
    mob.defense_skill = 0
    mob.last_attack_time = time.time() - 10.0  # reset attack cooldown
    from app.engine.systems.combat import resolve_melee_attack
    resolve_melee_attack(mob, p1, floor.mobs, mob.pos.x, mob.pos.y)
    assert p1.hp < initial_p1_hp, "Mob should be able to attack player"

def test_mob_vs_mob_no_damage():
    game = GameInstance("test_game")
    
    mob1_id = "mob1"
    mob2_id = "mob2"
    from app.engine.entities.player import Mob as MobEntity
    
    game.mobs[mob1_id] = MobEntity(
        id=mob1_id,
        name="Rat 1",
        pos=Position(x=1, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        faction=Faction.DUNGEON
    )
    game.mobs[mob2_id] = MobEntity(
        id=mob2_id,
        name="Rat 2",
        pos=Position(x=2, y=1),
        hp=10,
        max_hp=10,
        attack=2,
        defense=0,
        faction=Faction.DUNGEON
    )
    game.grid[1][1] = 1
    game.grid[1][2] = 1
    
    mob2 = game.mobs[mob2_id]
    initial_mob2_hp = mob2.hp
    
    # Mob 1 tries to attack Mob 2
    game.move_entity(mob1_id, 1, 0)
    
    assert mob2.hp == initial_mob2_hp, "Mobs of the same faction should not damage each other"


def test_dungeon_player_pvp_combat():
    game = GameInstance("test_pvp")
    p_hero_id = "hero"
    p_dungeon_id = "dungeon_minion"
    
    hero = game.add_player(p_hero_id, "Hero", faction=Faction.PLAYER)
    dungeon_p = game.add_player(p_dungeon_id, "Dungeon Minion", faction=Faction.DUNGEON)
    
    hero.pos = Position(x=1, y=1)
    dungeon_p.pos = Position(x=2, y=1)
    
    floor = game._get_or_create_floor(1)
    floor.grid[1][1] = 1
    floor.grid[1][2] = 1
    
    hero.belongings.armor = None
    hero.defense = 0
    hero.defense_skill = 0
    dungeon_p.attack_skill = 100
    
    initial_hero_hp = hero.hp
    game.move_entity(p_dungeon_id, -1, 0)
    assert hero.hp < initial_hero_hp, "Dungeon player should damage hero player in PvP"


def test_dungeon_player_friendly_with_mobs():
    game = GameInstance("test_dungeon_ally")
    p_id = "dungeon_guy"
    player = game.add_player(p_id, "Dungeon Bro", faction=Faction.DUNGEON)
    player.pos = Position(x=1, y=1)
    
    from app.engine.entities.player import Mob as MobEntity
    mob_id = "rat_friend"
    mob = MobEntity(
        id=mob_id,
        name="Rat Friend",
        pos=Position(x=2, y=1),
        hp=20,
        max_hp=20,
        faction=Faction.DUNGEON,
    )
    floor = game._get_or_create_floor(1)
    floor.grid[1][1] = 1
    floor.grid[1][2] = 1
    floor.mobs[mob_id] = mob
    
    game.move_entity(p_id, 1, 0, seq=42)
    assert mob.hp == 20, "Dungeon mob should not take damage from dungeon player"
    assert player.pos.x == 2 and player.pos.y == 1, "Player should swap to mob position"
    assert mob.pos.x == 1 and mob.pos.y == 1, "Mob should swap to player position"

    move_results = [e for e in game.events if e["type"] == "MOVE_RESULT" and e.get("_player_id") == p_id]
    assert len(move_results) == 1
    assert move_results[0]["data"]["ok"] is True
    assert move_results[0]["data"]["seq"] == 42
    assert move_results[0]["data"]["x"] == 2
    assert move_results[0]["data"]["y"] == 1

    move_events = [e for e in game.events if e["type"] == "MOVE"]
    assert any(e["data"]["entity"] == p_id and e["data"]["x"] == 2 and e["data"]["y"] == 1 for e in move_events)
    assert any(e["data"]["entity"] == mob_id and e["data"]["x"] == 1 and e["data"]["y"] == 1 for e in move_events)


def test_dungeon_player_cannot_swap_with_immovable_mob():
    game = GameInstance("test_dungeon_immovable")
    p_id = "dungeon_guy"
    player = game.add_player(p_id, "Dungeon Bro", faction=Faction.DUNGEON)
    player.pos = Position(x=1, y=1)

    from app.engine.entities.player import Mob as MobEntity
    mob_id = "sentry_friend"
    mob = MobEntity(
        id=mob_id,
        name="Sentry",
        pos=Position(x=2, y=1),
        hp=50,
        max_hp=50,
        faction=Faction.DUNGEON,
        properties=["IMMOVABLE"],
    )
    floor = game._get_or_create_floor(1)
    floor.grid[1][1] = 1
    floor.grid[1][2] = 1
    floor.mobs[mob_id] = mob

    game.move_entity(p_id, 1, 0, seq=99)
    assert player.pos.x == 1 and player.pos.y == 1, "Player should stay in place"
    assert mob.pos.x == 2 and mob.pos.y == 1, "Mob should stay in place"

    move_results = [e for e in game.events if e["type"] == "MOVE_RESULT" and e.get("_player_id") == p_id]
    assert len(move_results) == 1
    assert move_results[0]["data"]["ok"] is False
    assert move_results[0]["data"]["seq"] == 99


def test_player_interacts_with_npc_instead_of_swapping():
    from app.engine.entities.mobs import Shopkeeper
    game = GameInstance("test_npc_interact")
    p_id = "hero"
    player = game.add_player(p_id, "Hero", faction=Faction.PLAYER)
    player.pos = Position(x=1, y=1)

    shopkeeper = Shopkeeper(
        id="shopkeeper_1",
        name="Shopkeeper",
        pos=Position(x=2, y=1),
        hp=100,
        max_hp=100,
        faction=Faction.PLAYER,
    )
    floor = game._get_or_create_floor(1)
    floor.grid[1][1] = 1
    floor.grid[1][2] = 1
    floor.mobs[shopkeeper.id] = shopkeeper

    game.move_entity(p_id, 1, 0, seq=101)
    assert player.pos.x == 1 and player.pos.y == 1, "Player should stay in place"
    assert shopkeeper.pos.x == 2 and shopkeeper.pos.y == 1, "Shopkeeper should stay in place"

    shop_events = [e for e in game.events if e["type"] == "SHOP_OPEN"]
    assert len(shop_events) == 1


def test_mob_ai_targets_hero_not_dungeon_player():
    game = GameInstance("test_mob_ai_faction")
    floor = game._get_or_create_floor(1)
    floor.grid = [[1] * 10 for _ in range(10)]
    
    p_dungeon = game.add_player("p_dung", "DungPlayer", faction=Faction.DUNGEON)
    p_dungeon.pos = Position(x=2, y=2)
    
    p_hero = game.add_player("p_hero", "HeroPlayer", faction=Faction.PLAYER)
    p_hero.pos = Position(x=8, y=8)
    
    target = game._find_nearest_player(Position(x=2, y=1), floor_id=1, faction=Faction.DUNGEON)
    assert target is not None
    assert target.id == "p_hero", "Mob should target hero player, not dungeon faction player"


def test_monster_class_creation():
    from app.engine.entities.player import CharacterClass
    from app.engine.entities.subclasses import Talent
    game = GameInstance("test_monster_classes")
    
    gnoll = game.add_player("g1", "GnollScout", class_type=CharacterClass.GNOLL, faction=Faction.DUNGEON)
    assert gnoll.class_type == "gnoll"
    assert gnoll.faction == "dungeon"
    assert gnoll.belongings.weapon is not None
    assert gnoll.belongings.weapon.name == "Spear"
    
    gnoll.level = 2
    game.on_talent_level_up(gnoll)
    assert gnoll.subclass_info.talent_points[1] > 0
    ok = game.upgrade_talent("g1", Talent.HEARTY_MEAL)
    assert ok is True
    assert gnoll.subclass_info.talent_info.level(Talent.HEARTY_MEAL) == 1
    
    skeleton = game.add_player("s1", "Skelly", class_type=CharacterClass.SKELETON, faction=Faction.DUNGEON)
    assert skeleton.class_type == "skeleton"
    assert "UNDEAD" in skeleton.properties


def test_duelist_weapon_skill_targets_opposing_player():
    from app.engine.entities.player import CharacterClass
    from app.engine.game.duelist_weapon_skills import CleaveSkill, SpikeSkill
    from app.engine.entities.items.equip import WornShortsword, make_named_melee_weapon

    game = GameInstance("test_duelist_pvp")
    duelist = game.add_player("d1", "Duelist", class_type=CharacterClass.DUELIST, faction=Faction.PLAYER)
    duelist.pos = Position(x=1, y=1)
    sword = WornShortsword()
    duelist.belongings.weapon = sword
    duelist.weapon_charge = 2.0
    duelist.attack_skill = 100

    dungeon_p = game.add_player("dung1", "DungeonGuy", class_type=CharacterClass.GNOLL, faction=Faction.DUNGEON)
    dungeon_p.pos = Position(x=2, y=1)
    dungeon_p.defense = 0
    dungeon_p.defense_skill = 0
    init_hp = dungeon_p.hp

    floor = game._get_or_create_floor(1)
    floor.grid[1][1] = 1
    floor.grid[1][2] = 1
    floor.grid[1][3] = 1

    cleave = CleaveSkill()
    can_use, err = cleave.can_execute(game, duelist, sword, 2, 1)
    assert can_use is True
    assert err is None
    ok = cleave.execute(game, duelist, sword, 2, 1)
    assert ok is True
    assert dungeon_p.hp < init_hp

    spear = make_named_melee_weapon("Spear")
    duelist.belongings.weapon = spear
    dungeon_p.pos = Position(x=3, y=1)
    spike = SpikeSkill()
    can_spike, err = spike.can_execute(game, duelist, spear, 3, 1)
    assert can_spike is True
    assert err is None

