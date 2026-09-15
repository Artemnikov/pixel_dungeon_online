"""Duelist class mechanics: starting gear, weapon charge, finishers,
armor abilities, and talent gating."""

import pytest
from app.engine.manager import GameInstance
from app.engine.entities.base import Position
from app.engine.entities.player import CharacterClass, Mob as MobEntity
from app.engine.entities.subclasses import ArmorAbilityType


def _duelist(game, pid="duelist"):
    return game.add_player(pid, "Duelist", CharacterClass.DUELIST)


def _mob(hp=30, max_hp=30, x=2, y=1, **kw):
    return MobEntity(
        id="m", name="Rat", pos=Position(x=x, y=y),
        hp=hp, max_hp=max_hp, attack=2, defense=0,
        defense_skill=0, dr_min=0, dr_max=0, **kw
    )


def test_duelist_starting_gear():
    g = GameInstance("t")
    p = _duelist(g)
    assert p.class_type == CharacterClass.DUELIST
    assert p.belongings.weapon is not None
    assert p.belongings.weapon.name == "Rapier"
    assert p.belongings.weapon.level_known is True
    assert p.belongings.armor is not None
    assert p.belongings.armor.name == "Cloth Armor"
    assert p.belongings.armor.level_known is True
    names = [i.name for i in p.belongings.backpack.items]
    assert "Ration" in names
    assert "Waterskin" in names
    assert "Velvet Pouch" in names
    assert "Scroll of Identify" in names
    assert "Throwing Spikes" in names
    assert "Potion of Strength" in names
    assert "Scroll of Mirror Image" in names
    assert p.quickslot.slots[0].item_id == p.belongings.weapon.id


def test_duelist_weapon_charge_gain():
    g = GameInstance("t")
    p = _duelist(g)
    assert p.weapon_charge == 0
    assert p.finisher_ready is False

    p.gain_weapon_charge(1.0)
    assert p.weapon_charge == 1.0
    assert p.finisher_ready is True


def test_duelist_finisher_execution():
    g = GameInstance("t")
    p = _duelist(g)
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=30, x=p.pos.x + 2, y=p.pos.y)
    floor.mobs[mob.id] = mob

    p.weapon_charge = 2.0
    p.finisher_ready = True

    # Rapier Lunge at 2 tiles away
    g.action_duelist_finisher(p, mob.pos.x, mob.pos.y)

    assert p.weapon_charge == 1.0
    assert mob.hp < 30


def test_duelist_armor_abilities_dispatch():
    g = GameInstance("t")
    p = _duelist(g)
    p._kings_crown_worn = True
    floor = g._get_or_create_floor(p.floor_id)
    mob = _mob(hp=30, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.FEINT)
    assert p.armor_charge == 50

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.ELEMENTAL_STRIKE, mob.pos.x, mob.pos.y)
    assert p.armor_charge == 75

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.CHALLENGE, mob.pos.x, mob.pos.y)
    assert p.armor_charge == 65
    assert p.duel_mode_active is True
    assert p.duel_mode_target_id == mob.id


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_duelist_talents_route():
    from app.api.routes import get_talents
    res = await get_talents("duelist")
    assert isinstance(res, dict)
    assert res["class"] == "duelist"
    assert "champion" in res["subclasses"]
    assert "monk" in res["subclasses"]
    assert "1" in res["tiers"]
    assert len(res["tiers"]["1"]["talents"]) > 0

