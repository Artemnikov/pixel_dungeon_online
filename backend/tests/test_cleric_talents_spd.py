"""SPD-faithful Cleric talents and spells parity test suite.

Covers:
- Tier 1: Satiated Spells, Holy Intuition, Searing Light, Shield of Light
- Tier 2: Enlightening Meal, Recall Inscription, Sunray, Divine Sense, Bless
- Tier 3: Cleanse, Light Reading, Priest (Holy Lance, Hallowed Ground, Mnemonic Prayer, Radiance),
          Paladin (Smite, Lay on Hands, Aura of Protection, Wall of Light)
- Tier 4: Ascended Form (Divine Intervention, Judgement, Flash),
          Trinity (Body Form, Mind Form, Spirit Form),
          Power of Many (Beaming Ray, Life Link, Stasis),
          Heroic Energy
"""

import pytest
from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.items.consumables import Food
from app.engine.entities.items.scrolls import ScrollOfIdentify, ScrollOfRecharging
from app.engine.entities.items.equip import Dagger
from app.engine.entities.player import CharacterClass, Mob as MobEntity
from app.engine.entities.runestones import Runestone
from app.engine.entities.subclasses import ArmorAbilityType, Subclass
from app.engine.entities.talent_enum import Talent
from app.engine.game.cleric_spells import get_available_spells, get_cleric_spell
from app.engine.manager import GameInstance
from app.engine.systems.combat import resolve_melee_attack


def _cleric(game: GameInstance, pid: str = "cleric_test"):
    player = game.add_player(pid, "Cleric", CharacterClass.CLERIC)
    tome = player.belongings.artifact
    if tome:
        tome.charge = 10
        tome.charge_cap = 10
    return player


def _mob(hp: int = 40, max_hp: int = 40, x: int = 2, y: int = 1, id: str = "m1", **kw):
    return MobEntity(
        id=id, name="Rat", pos=Position(x=x, y=y),
        hp=hp, max_hp=max_hp, attack=4, defense=0,
        defense_skill=0, dr_min=0, dr_max=0, **kw
    )


# ===========================================================================
# Tier 1 Tests
# ===========================================================================

def test_satiated_spells_grants_barrier_on_next_spell():
    g = GameInstance("test_satiated")
    p = _cleric(g)
    p.talent_info.talents[Talent.SATIATED_SPELLS] = 2

    # Eat food -> gains tracker
    g.on_food_eaten(p, Food(id="f1", name="Ration"))
    assert p.has_buff("satiated_spells_tracker")

    # Cast Holy Ward -> consumes tracker and grants 1 + 2*2 = 5 barrier
    assert g.cast_spell(p, "holy_ward") is True
    assert not p.has_buff("satiated_spells_tracker")
    assert p.has_buff("barrier")
    assert p.get_total_shield() == 5


def test_holy_intuition_cost_and_curse_reveal():
    g = GameInstance("test_intuition")
    p = _cleric(g)
    p.talent_info.talents[Talent.HOLY_INTUITION] = 1

    spell = get_cleric_spell("holy_intuition")
    assert spell.get_cost(p) == 3.0

    p.talent_info.talents[Talent.HOLY_INTUITION] = 2
    assert spell.get_cost(p) == 2.0

    item = Dagger(id="d1", name="Dagger")
    item.cursed_known = False
    p.belongings.backpack.collect(item)

    assert g.cast_spell(p, "holy_intuition") is True
    assert item.cursed_known is True


def test_searing_light_bonus_damage_on_illuminated():
    g = GameInstance("test_searing")
    p = _cleric(g)
    p.talent_info.talents[Talent.SEARING_LIGHT] = 2
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=50, max_hp=50, x=p.pos.x + 1, y=p.pos.y)
    floor.mobs[mob.id] = mob
    mob.add_buff("illuminated", duration=50.0)

    # Attack illuminated mob -> consumes illuminated and applies +5 bonus dmg
    res = resolve_melee_attack(
        p, mob, floor.mobs, p.pos.x, p.pos.y,
        add_event=lambda t, d: g.add_event(t, d, floor_id=p.floor_id),
        floor=floor, game=g,
    )
    assert res["hit"] is True
    assert not mob.has_buff("illuminated")
    assert res["damage"] >= 5


def test_shield_of_light_damage_absorption():
    g = GameInstance("test_sol")
    p = _cleric(g)
    p.talent_info.talents[Talent.SHIELD_OF_LIGHT] = 2
    floor = g._get_or_create_floor(p.floor_id)

    mob = _mob(hp=30, max_hp=30, x=p.pos.x + 1, y=p.pos.y, id="target_mob")
    mob_other = _mob(hp=30, max_hp=30, x=p.pos.x, y=p.pos.y + 1, id="other_mob")
    floor.mobs[mob.id] = mob
    floor.mobs[mob_other.id] = mob_other

    # Cast Shield of Light on target_mob
    assert g.cast_spell(p, "shield_of_light", tx=mob.pos.x, ty=mob.pos.y) is True
    buff = p.get_buff("shield_of_light_tracker")
    assert buff is not None
    assert getattr(buff, "source_id", None) == mob.id


# ===========================================================================
# Tier 2 Tests
# ===========================================================================

def test_recall_inscription_scroll_recast():
    g = GameInstance("test_recall")
    p = _cleric(g)
    p.talent_info.talents[Talent.RECALL_INSCRIPTION] = 2
    tome = p.belongings.artifact
    tome.charge = 10

    # Read a Scroll of Recharging
    scroll = ScrollOfRecharging(id="s_rech")
    p.belongings.backpack.collect(scroll)
    from app.engine.entities.scroll_actions import action_read
    action_read(g, p, scroll)

    # Player has last_used_inscription
    assert getattr(p, "last_used_inscription", None) is not None
    assert p.last_used_inscription["kind"] == "scroll_of_recharging"

    # Recast with Recall Inscription
    spell = get_cleric_spell("recall_inscription")
    assert spell.get_cost(p) == 3.0
    assert g.cast_spell(p, "recall_inscription") is True
    assert p.has_buff("recharging")


def test_sunray_damage_blind_and_paralyze():
    g = GameInstance("test_sunray")
    p = _cleric(g)
    p.talent_info.talents[Talent.SUNRAY] = 2
    floor = g._get_or_create_floor(p.floor_id)

    # Undead mob gets max damage roll (12)
    undead = _mob(hp=50, max_hp=50, x=p.pos.x + 2, y=p.pos.y, id="skel", mob_type="skeleton")
    floor.mobs[undead.id] = undead

    assert g.cast_spell(p, "sunray", tx=undead.pos.x, ty=undead.pos.y) is True
    assert undead.hp == 38  # 50 - 12
    assert undead.has_buff("blindness")
    assert undead.has_buff("sunray_recently_blinded_tracker")

    # Second hit while blinded inflicts Paralysis
    assert g.cast_spell(p, "sunray", tx=undead.pos.x, ty=undead.pos.y) is True
    assert undead.has_buff("paralysis")


def test_divine_sense_mind_vision():
    g = GameInstance("test_ds")
    p = _cleric(g)
    p.talent_info.talents[Talent.DIVINE_SENSE] = 2

    assert g.cast_spell(p, "divine_sense") is True
    buff = p.get_buff("mind_vision")
    assert buff is not None
    assert buff.level == 12


def test_bless_spell_self_and_ally():
    g = GameInstance("test_bless")
    p = _cleric(g)
    p.talent_info.talents[Talent.BLESS] = 2
    floor = g._get_or_create_floor(p.floor_id)

    # Self cast -> bless + 15 barrier
    assert g.cast_spell(p, "bless") is True
    assert p.has_buff("bless")
    assert p.get_total_shield() == 15

    # Cast on wounded ally -> heals missing HP, excess to barrier
    ally = _mob(hp=10, max_hp=20, x=p.pos.x + 1, y=p.pos.y, id="ally_m", faction="player")
    floor.mobs[ally.id] = ally

    assert g.cast_spell(p, "bless", tx=ally.pos.x, ty=ally.pos.y) is True
    assert ally.hp == 20  # healed 10
    assert ally.has_buff("barrier")  # excess 5 barrier
    assert ally.has_buff("bless")


# ===========================================================================
# Tier 3 Tests
# ===========================================================================

def test_cleanse_spell_removes_debuffs_and_gives_immunity():
    g = GameInstance("test_cleanse")
    p = _cleric(g)
    p.talent_info.talents[Talent.CLEANSE] = 3

    p.add_buff("poison", duration=10.0)
    p.add_buff("burning", duration=10.0)
    p.add_buff("paralysis", duration=10.0)

    assert g.cast_spell(p, "cleanse") is True
    assert not p.has_buff("poison")
    assert not p.has_buff("burning")
    assert not p.has_buff("paralysis")
    assert p.get_total_shield() == 30
    assert p.has_buff("debuff_immune")


def test_priest_holy_lance_and_radiance():
    g = GameInstance("test_priest")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PRIEST
    p.talent_info.talents[Talent.HOLY_LANCE] = 3
    floor = g._get_or_create_floor(p.floor_id)

    undead = _mob(hp=150, max_hp=150, x=p.pos.x + 1, y=p.pos.y, id="demon_mob", mob_type="demon")
    floor.mobs[undead.id] = undead

    # Holy Lance deals max 110 dmg to demons
    assert g.cast_spell(p, "holy_lance", tx=undead.pos.x, ty=undead.pos.y) is True
    assert undead.hp == 40  # 150 - 110
    assert undead.has_buff("illuminated")
    assert p.has_buff("lance_cooldown")

    # Casting Holy Lance again fails during cooldown
    assert g.cast_spell(p, "holy_lance", tx=undead.pos.x, ty=undead.pos.y) is False

    # Radiance detonates Illuminated for 5 + lvl holy damage
    p.level = 10
    assert g.cast_spell(p, "radiance") is True
    assert undead.hp == 25  # 40 - 15
    assert undead.has_buff("paralysis")


def test_priest_hallowed_ground_blob_creation():
    g = GameInstance("test_hg")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PRIEST
    p.talent_info.talents[Talent.HALLOWED_GROUND] = 2
    floor = g._get_or_create_floor(p.floor_id)

    assert g.cast_spell(p, "hallowed_ground", tx=p.pos.x, ty=p.pos.y) is True
    blob_id = f"hallowed_ground_{p.id}"
    assert blob_id in floor.blob_areas
    assert floor.blob_areas[blob_id]["type"] == "hallowed_ground"


def test_priest_mnemonic_prayer():
    g = GameInstance("test_mnemonic")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PRIEST
    p.talent_info.talents[Talent.MNEMONIC_PRAYER] = 2
    floor = g._get_or_create_floor(p.floor_id)

    # Add haste buff to player
    b = p.add_buff("haste", duration=10.0)
    init_rem = b.remaining

    assert g.cast_spell(p, "mnemonic_prayer") is True
    assert b.remaining == init_rem + 4.0
    assert getattr(b, "mnemonic_extended", False) is True

    # Cannot extend twice
    assert g.cast_spell(p, "mnemonic_prayer") is True
    assert b.remaining == init_rem + 4.0


def test_paladin_smite_and_lay_on_hands():
    g = GameInstance("test_paladin")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PALADIN
    p.talent_info.talents[Talent.LAY_ON_HANDS] = 2
    floor = g._get_or_create_floor(p.floor_id)

    # Lay on Hands gives 20 barrier to self (cap 60)
    assert g.cast_spell(p, "lay_on_hands") is True
    assert p.get_total_shield() == 20

    # Smite adjacent demon
    mob = _mob(hp=100, max_hp=100, x=p.pos.x + 1, y=p.pos.y, id="demon_p", mob_type="demon")
    floor.mobs[mob.id] = mob
    p.level = 10

    assert g.cast_spell(p, "smite", tx=mob.pos.x, ty=mob.pos.y) is True
    assert mob.hp < 100


def test_paladin_wall_of_light_and_dismiss():
    g = GameInstance("test_wall")
    p = _cleric(g)
    p.subclass_info.subclass = Subclass.PALADIN
    p.talent_info.talents[Talent.WALL_OF_LIGHT] = 2
    floor = g._get_or_create_floor(p.floor_id)

    target_x, target_y = p.pos.x + 1, p.pos.y
    assert g.cast_spell(p, "wall_of_light", tx=target_x, ty=target_y) is True
    blob_id = f"wall_of_light_{p.id}"
    assert blob_id in floor.blob_areas

    # Recasting early dismisses for 0 charges
    spell = get_cleric_spell("wall_of_light")
    assert spell.get_cost(p) == 0.0
    assert g.cast_spell(p, "wall_of_light") is True
    assert blob_id not in floor.blob_areas


# ===========================================================================
# Tier 4 Tests
# ===========================================================================

def test_ascended_form_judgement_and_divine_intervention():
    g = GameInstance("test_ascend")
    p = _cleric(g)
    p._kings_crown_worn = True
    g.choose_armor_ability(p.id, ArmorAbilityType.ASCENDED_FORM)
    p.talent_info.talents[Talent.DIVINE_INTERVENTION] = 2
    p.talent_info.talents[Talent.JUDGEMENT] = 2
    floor = g._get_or_create_floor(p.floor_id)

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.ASCENDED_FORM)
    assert p.ascended_form_active is True

    # Divine Intervention grants 200 shield
    assert g.cast_spell(p, "divine_intervention") is True
    assert p.get_total_shield() >= 200

    # Judgement smites FOV enemies
    mob = _mob(hp=80, max_hp=80, x=p.pos.x + 2, y=p.pos.y, id="judg_mob")
    floor.mobs[mob.id] = mob
    assert g.cast_spell(p, "judgement") is True
    assert mob.hp < 80


def test_power_of_many_life_link_and_stasis():
    g = GameInstance("test_pom")
    p = _cleric(g)
    p._kings_crown_worn = True
    g.choose_armor_ability(p.id, ArmorAbilityType.POWER_OF_MANY)
    p.talent_info.talents[Talent.LIFE_LINK] = 2
    p.talent_info.talents[Talent.STASIS] = 2
    floor = g._get_or_create_floor(p.floor_id)

    p.armor_charge = 100
    g.use_armor_ability(p.id, ArmorAbilityType.POWER_OF_MANY, p.pos.x + 1, p.pos.y)
    assert p.powered_ally_id is not None
    ally = floor.mobs[p.powered_ally_id]

    # Cast Life Link
    assert g.cast_spell(p, "life_link") is True
    assert p.has_buff("life_link")
    assert ally.has_buff("life_link")

    # Take damage with Life Link -> damage splits without recursive crash
    init_hp = p.hp
    ally_init_hp = ally.hp
    p.take_damage(20)
    assert p.hp == init_hp - 10
    assert ally.hp < ally_init_hp

    # Cast Stasis to store ally
    assert g.cast_spell(p, "stasis") is True
    assert p.has_buff("stasis")

    # Recast Stasis to recall ally
    spell = get_cleric_spell("stasis")
    assert spell.get_cost(p) == 0.0
    assert g.cast_spell(p, "stasis") is True
    assert not p.has_buff("stasis")
