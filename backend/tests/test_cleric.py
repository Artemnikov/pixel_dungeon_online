"""Cleric class mechanics: starting gear, Holy Tome energy, spells progression,
armor abilities, and talent gating."""

import pytest
from app.engine.manager import GameInstance
from app.engine.entities.base import Position
from app.engine.entities.items.consumables import Food
from app.engine.entities.player import CharacterClass, Mob as MobEntity
from app.engine.entities.subclasses import ArmorAbilityType, Subclass
from app.engine.entities.talent_enum import Talent
from app.engine.game.cleric_spells import get_available_spells, get_cleric_spell


def _cleric(game, pid="cleric"):
    return game.add_player(pid, "Cleric", CharacterClass.CLERIC)


def _mob(hp=30, max_hp=30, x=2, y=1, id="m", **kw):
    return MobEntity(
        id=id, name="Rat", pos=Position(x=x, y=y),
        hp=hp, max_hp=max_hp, attack=2, defense=0,
        defense_skill=0, dr_min=0, dr_max=0, **kw
    )


def test_cleric_starting_gear():
    g = GameInstance("t")
    p = _cleric(g)
    assert p.class_type == CharacterClass.CLERIC
    assert p.belongings.weapon is not None
    assert p.belongings.weapon.name == "Cudgel"
    assert p.belongings.armor is not None
    assert p.belongings.armor.name == "Cloth Armor"
    assert p.belongings.artifact is not None
    assert p.belongings.artifact.kind == "holy_tome"
    assert p.belongings.artifact.charge == 3
    assert p.belongings.artifact.charge_cap == 3
    names = [i.name for i in p.belongings.backpack.items]
    assert "Ration" in names
    assert "Waterskin" in names
    assert "Velvet Pouch" in names
    assert "Scroll of Identify" in names
    assert p.quickslot.slots[0].item_id == p.belongings.artifact.id
    tome = p.belongings.artifact
    assert tome.default_action() == "CAST"
    assert "CAST" in tome.actions(p)


def test_cleric_inherent_spells_and_unlocks():
    g = GameInstance("t")
    p = _cleric(g)

    # At start (0 talents), only the 3 base spells are available
    available = [s.id for s in get_available_spells(p)]
    assert set(available) == {"guiding_light", "holy_weapon", "holy_ward"}

    # Bless is locked
    assert g.cast_spell(p, "bless") is False

    # Unlock Bless via talent
    p.talent_info.talents[Talent.BLESS] = 1
    available = [s.id for s in get_available_spells(p)]
    assert "bless" in available
    assert g.cast_spell(p, "bless") is True


def test_cleric_spell_casting_and_charges():
    g = GameInstance("t")
    p = _cleric(g)
    tome = p.belongings.artifact
    assert tome.charge == 3

    # Holy weapon costs 2 charges
    assert g.cast_spell(p, "holy_weapon") is True
    assert p.has_buff("holy_weapon")
    assert tome.charge == 1

    # Holy weapon again fails (cost 2, has 1)
    assert g.cast_spell(p, "holy_weapon") is False
    assert tome.charge == 1

    # Holy ward costs 1 charge
    assert g.cast_spell(p, "holy_ward") is True
    assert p.has_buff("holy_ward")
    assert tome.charge == 0

    # No charges left -> casting fails
    assert g.cast_spell(p, "holy_ward") is False


def test_cleric_holy_weapon_ward_cast_presentation():
    """Casting Holy Weapon / Holy Ward emits READ sound + operate animation + glow
    (SPD onCast READ sound, hero.sprite.operate, Enchanting.show)."""
    g = GameInstance("t")
    p = _cleric(g)
    tome = p.belongings.artifact
    tome.charge = 5
    tome.charge_cap = 10

    def _presentation_events():
        events = g.flush_events()
        sounds = [e["data"] for e in events if e["type"] == "PLAY_SOUND"]
        anims = [e["data"] for e in events if e["type"] == "PLAY_ANIMATION"]
        return sounds, anims

    # Holy Weapon: READ sound + operate animation + golden glow
    assert g.cast_spell(p, "holy_weapon") is True
    sounds, anims = _presentation_events()
    assert {"sound": "READ", "x": p.pos.x, "y": p.pos.y} in sounds
    assert {
        "player": p.id,
        "animation": "operate",
        "glow": "golden",
        "spell": "holy_weapon",
        "x": p.pos.x,
        "y": p.pos.y,
    } in anims

    # Holy Ward: same presentation
    assert g.cast_spell(p, "holy_ward") is True
    sounds, anims = _presentation_events()
    assert {"sound": "READ", "x": p.pos.x, "y": p.pos.y} in sounds
    assert {
        "player": p.id,
        "animation": "operate",
        "glow": "golden",
        "spell": "holy_ward",
        "x": p.pos.x,
        "y": p.pos.y,
    } in anims

    # Bless emits TELEPORT sound and no operate animation
    p.talent_info.talents[Talent.BLESS] = 1
    assert g.cast_spell(p, "bless") is True
    sounds, anims = _presentation_events()
    assert {"sound": "TELEPORT", "x": p.pos.x, "y": p.pos.y} in sounds
    assert anims == []


def test_cleric_holy_tome_turn_recharging():
    g = GameInstance("t")
    p = _cleric(g)
    tome = p.belongings.artifact
    tome.charge = 0
    tome.partial_charge = 0.0

    # Tick artifacts for 50 seconds (each charge takes ~42-45s)
    g.tick_artifacts(p, 50.0)
    assert tome.charge >= 1


def test_cleric_tome_exp_and_leveling():
    g = GameInstance("t")
    p = _cleric(g)
    tome = p.belongings.artifact
    tome.charge = 10
    tome.charge_cap = 10

    # Spending charges gains exp
    tome.spend_charge(10.0, hero_lvl=10)
    assert tome.exp > 0


def test_cleric_enlightening_meal():
    g = GameInstance("t")
    p = _cleric(g)
    p.talent_info.talents[Talent.ENLIGHTENING_MEAL] = 2
    tome = p.belongings.artifact
    tome.charge = 0
    tome.partial_charge = 0.0

    # Eat food -> gives 1.0 charge at level 2
    food = Food(id="food", name="Ration")
    g.on_food_eaten(p, food)
    assert tome.charge == 1


def test_cleric_quick_spell():
    g = GameInstance("t")
    p = _cleric(g)
    assert p.cleric_quick_spell is None

    # Unlocked spell can be set
    assert g.set_cleric_quick_spell(p, "guiding_light") is True
    assert p.cleric_quick_spell == "guiding_light"

    # Toggle off by sending same spell
    assert g.set_cleric_quick_spell(p, "guiding_light") is True
    assert p.cleric_quick_spell is None

    # Clear with None
    assert g.set_cleric_quick_spell(p, "holy_ward") is True
    assert g.set_cleric_quick_spell(p, None) is True
    assert p.cleric_quick_spell is None

    # Locked spell rejected
    assert g.set_cleric_quick_spell(p, "bless") is False


def test_cleric_light_reading():
    from app.engine.entities.items.artifacts import ChaliceOfBlood
    g = GameInstance("t")
    p = _cleric(g)
    tome = p.belongings.artifact

    # Unequip holy tome to backpack and equip chalice of blood instead
    p.belongings.artifact = ChaliceOfBlood(id="chalice")
    p.belongings.backpack.collect(tome)

    # Without Light Reading, cannot cast
    assert g.cast_spell(p, "holy_ward") is False

    # With Light Reading, can cast from backpack and spend charge
    p.talent_info.talents[Talent.LIGHT_READING] = 3
    assert tome.charge == 3
    assert g.cast_spell(p, "holy_ward") is True
    assert p.has_buff("holy_ward")
    assert tome.charge == 2

    # Tome in backpack recharges while Chalice is equipped
    tome.charge = 0
    tome.partial_charge = 0.0
    g.tick_artifacts(p, 100.0)
    assert tome.charge >= 1


def test_cleric_paladin_synergy():
    g = GameInstance("t")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PALADIN
    tome = p.belongings.artifact
    tome.charge = 5
    tome.charge_cap = 10

    # Cast holy weapon
    assert g.cast_spell(p, "holy_weapon") is True
    hw_buff = p.get_buff("holy_weapon")
    assert hw_buff is not None
    assert hw_buff.level == 6  # Paladin bonus +6
    init_dur = hw_buff.remaining

    # Cast holy ward -> extends holy weapon by 10 * 1 = 10 turns
    assert g.cast_spell(p, "holy_ward") is True
    assert hw_buff.remaining > init_dur


def test_cleric_holy_buffs_hud_effects():
    """Holy Weapon / Holy Ward surface as `active_effects` so the client HUD
    shows buff icons (SPD BuffIndicator. HOLY_WEAPON=73, HOLY_ARMOR=74)."""
    g = GameInstance("t")
    p = _cleric(g)
    tome = p.belongings.artifact
    tome.charge = 5
    tome.charge_cap = 10

    assert g.cast_spell(p, "holy_weapon") is True
    assert g.cast_spell(p, "holy_ward") is True
    g._sync_effects(p)

    effects = {e.key: e for e in p.active_effects}
    hw = effects.get("holy_weapon")
    assert hw is not None
    assert hw.icon == 73
    assert hw.remaining == pytest.approx(50.0)
    hw_ward = effects.get("holy_ward")
    assert hw_ward is not None
    assert hw_ward.icon == 74
    assert hw_ward.remaining == pytest.approx(50.0)


def test_cleric_paladin_does_not_self_extend_just_cast_buff():
    """SPD ClericSpell.onCast: a Paladin casting a holy spell does not extend the
    buff it just cast (only casts of *other* spells extend). A fresh Holy Weapon
    stays at exactly 50 turns instead of 50 + 10 * cost."""
    g = GameInstance("t")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PALADIN
    tome = p.belongings.artifact
    tome.charge = 5
    tome.charge_cap = 10

    assert g.cast_spell(p, "holy_weapon") is True
    hw_buff = p.get_buff("holy_weapon")
    assert hw_buff is not None
    assert hw_buff.level == 6
    assert hw_buff.remaining == pytest.approx(50.0)

    # Casting a *different* spell still extends the active holy weapon.
    assert g.cast_spell(p, "holy_ward") is True
    assert hw_buff.remaining == pytest.approx(60.0)

    # Recasting holy weapon refreshes to 50, not 50 + 20.
    assert g.cast_spell(p, "holy_weapon") is True
    assert hw_buff.remaining == pytest.approx(50.0)


def test_cleric_priest_synergy():
    g = GameInstance("t")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PRIEST
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # First guiding light costs 0 charges for Priest
    tome = p.belongings.artifact
    assert tome.charge == 3
    assert g.cast_spell(p, "guiding_light", tx=mob.pos.x, ty=mob.pos.y) is True
    assert tome.charge == 3
    assert getattr(p, "guiding_light_priest_cd", 0) > 0


def test_cleric_guiding_light_projectile_events():
    """Guiding Light emits an SPD-faithful RANGED_ATTACK (light_missile bolt,
    zap.mp3 sound via ATTACK_MAGIC, hero cast animation via is_wand) followed by
    a DAMAGE carrying the projectile + burst size (client syncs burst/sound to
    the bolt's arrival)."""
    g = GameInstance("t")
    p = _cleric(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    assert g.cast_spell(p, "guiding_light", tx=mob.pos.x, ty=mob.pos.y) is True

    events = g.flush_events()
    ranged = [e["data"] for e in events if e["type"] == "RANGED_ATTACK"]
    damages = [e["data"] for e in events if e["type"] == "DAMAGE"]
    assert len(ranged) == 1
    assert len(damages) == 1

    ra = ranged[0]
    assert ra["source"] == p.id
    assert ra["x"] == p.pos.x and ra["y"] == p.pos.y
    assert ra["target_x"] == mob.pos.x and ra["target_y"] == mob.pos.y
    assert ra["projectile"] == "light_missile"
    assert ra["sound"] == "ATTACK_MAGIC"  # zap.mp3 on the client
    assert ra["is_wand"] is True          # hero cast zap animation + facing
    assert ra["is_bow"] is False

    dmg = damages[0]
    assert dmg["target"] == mob.id
    assert dmg["holy"] is True
    assert dmg["projectile"] == "light_missile"
    assert dmg["splash_count"] == 3       # SPD burst(0xFFFFFF44, 3)
    assert 2 <= dmg["amount"] <= 8


def test_cleric_guiding_light_ballistics_trace_past_mob():
    """Targeting a cell behind an enemy traces ballistics and impacts the enemy."""
    g = GameInstance("t")
    p = _cleric(g)
    floor = g._get_or_create_floor(p.floor_id)
    for dx in range(1, 6):
        floor.flags.solid[p.pos.y][p.pos.x + dx] = False
        floor.flags.passable[p.pos.y][p.pos.x + dx] = True
    mob = _mob(x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Player at (x, y), mob at (x+2, y), click at (x+5, y)
    assert g.cast_spell(p, "guiding_light", tx=p.pos.x + 5, ty=p.pos.y) is True

    events = g.flush_events()
    ranged = [e["data"] for e in events if e["type"] == "RANGED_ATTACK"]
    damages = [e["data"] for e in events if e["type"] == "DAMAGE"]
    assert len(ranged) == 1
    assert len(damages) == 1
    assert ranged[0]["target_x"] == mob.pos.x
    assert ranged[0]["target_y"] == mob.pos.y
    assert damages[0]["target"] == mob.id


def test_cleric_guiding_light_empty_tile_or_wall_click():
    """Targeting an empty floor tile or wall fires the bolt to the collision point."""
    g = GameInstance("t")
    p = _cleric(g)
    floor = g._get_or_create_floor(p.floor_id)
    for dx in range(1, 6):
        floor.flags.solid[p.pos.y][p.pos.x + dx] = False
        floor.flags.passable[p.pos.y][p.pos.x + dx] = True

    # Click empty cell 3 tiles away
    assert g.cast_spell(p, "guiding_light", tx=p.pos.x + 3, ty=p.pos.y) is True

    events = g.flush_events()
    ranged = [e["data"] for e in events if e["type"] == "RANGED_ATTACK"]
    damages = [e["data"] for e in events if e["type"] == "DAMAGE"]
    assert len(ranged) == 1
    assert len(damages) == 0  # No mob hit
    assert ranged[0]["projectile"] == "light_missile"
    assert ranged[0]["target_x"] == p.pos.x + 3
    assert ranged[0]["target_y"] == p.pos.y


def test_cleric_guiding_light_auto_aim_nearest_mob():
    """Casting without target coordinates auto-aims at the closest visible mob."""
    g = GameInstance("t")
    p = _cleric(g)
    floor = g._get_or_create_floor(p.floor_id)
    for dx in range(1, 6):
        floor.flags.solid[p.pos.y][p.pos.x + dx] = False
        floor.flags.passable[p.pos.y][p.pos.x + dx] = True
    mob_far = _mob(x=p.pos.x + 4, y=p.pos.y, id="far_mob")
    mob_near = _mob(x=p.pos.x + 1, y=p.pos.y, id="near_mob")
    floor.mobs[mob_far.id] = mob_far
    floor.mobs[mob_near.id] = mob_near

    assert g.cast_spell(p, "guiding_light") is True

    events = g.flush_events()
    damages = [e["data"] for e in events if e["type"] == "DAMAGE"]
    assert len(damages) == 1
    assert damages[0]["target"] == "near_mob"


def test_cleric_holy_tome_equipped_in_misc_slot():
    """Holy Tome equipped in belongings.misc is recognized by get_holy_tome()."""
    g = GameInstance("t")
    p = _cleric(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    # Move tome to misc slot
    p.belongings.misc = p.belongings.artifact
    p.belongings.artifact = None

    assert p.get_holy_tome() is not None
    assert g.cast_spell(p, "guiding_light", tx=mob.pos.x, ty=mob.pos.y) is True


def test_cleric_armor_abilities_dispatch():
    g = GameInstance("t")
    p = _cleric(g)
    p._kings_crown_worn = True
    floor = g._get_or_create_floor(p.floor_id)

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.ASCENDED_FORM)
    assert p.ascended_form_active is True
    assert p.armor_charge == 60

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.TRINITY)
    assert p.armor_charge == 67
    assert len(p.current_trinity_forms) > 0

    p.armor_charge = 100
    target_x, target_y = p.pos.x + 1, p.pos.y
    g.use_armor_ability(p.id, ArmorAbilityType.POWER_OF_MANY, target_x, target_y)
    assert p.armor_charge == 50
    assert p.powered_ally_id is not None
    assert p.powered_ally_id in floor.mobs


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_cleric_talents_route():
    from app.api.routes import get_talents
    res = await get_talents("cleric")
    assert isinstance(res, dict)
    assert res["class"] == "cleric"
    assert "priest" in res["subclasses"]
    assert "paladin" in res["subclasses"]
    assert "1" in res["tiers"]
    assert len(res["tiers"]["1"]["talents"]) > 0
    talent_names = [t["id"] for t in res["tiers"]["1"]["talents"]]
    assert "holy_intuition" in talent_names
    assert "satiated_spells" in talent_names
