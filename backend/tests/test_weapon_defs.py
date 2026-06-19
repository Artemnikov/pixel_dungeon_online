"""Stat-table verification for the generic tier 1-5 melee weapon roster
(docs/spd_items/01-weapons-bombs.md §2) and the generation wiring that
turns a WEP_T1..WEP_T5 RolledItem into a concrete weapon."""

from app.engine.entities.base import Dagger, MeleeWeapon, WornShortsword, make_named_melee_weapon
from app.engine.entities.weapon_defs import WEAPON_DEFS, WEP_TIER_ORDER
from app.engine.dungeon.spd_levelgen.generator import RolledItem
from app.engine.game.spd_adapter import _make_melee_weapon


# Expected (str_req, dmg_min(0), dmg_max(0)) per docs/spd_items/01-weapons-bombs.md §2.
EXPECTED_STATS = {
    "Gloves": (10, 1, 5),
    "Rapier": (10, 1, 8),
    "Cudgel": (10, 1, 8),
    "Shortsword": (12, 2, 12),
    "Hand Axe": (12, 2, 12),
    "Spear": (12, 2, 20),
    "Quarterstaff": (12, 2, 12),
    "Dirk": (12, 2, 12),
    "Sickle": (12, 2, 20),
    "Sword": (14, 3, 16),
    "Mace": (14, 3, 16),
    "Scimitar": (14, 3, 16),
    "Round Shield": (14, 3, 12),
    "Sai": (14, 3, 10),
    "Whip": (14, 3, 15),
    "Longsword": (16, 4, 20),
    "Battle Axe": (16, 4, 20),
    "Flail": (16, 4, 35),
    "Runic Blade": (16, 4, 20),
    "Assassin's Blade": (16, 4, 20),
    "Crossbow": (16, 4, 20),
    "Katana": (16, 4, 20),
    "Greatsword": (18, 5, 24),
    "War Hammer": (18, 5, 24),
    "Glaive": (18, 5, 40),
    "Greataxe": (20, 5, 45),
    "Greatshield": (18, 5, 18),
    "Gauntlet": (18, 5, 15),
    "War Scythe": (18, 5, 40),
}


def test_weapon_defs_cover_expected_roster():
    assert set(WEAPON_DEFS) == set(EXPECTED_STATS)


def test_weapon_defs_stats_match_doc():
    for name, (str_req, dmg_min, dmg_max) in EXPECTED_STATS.items():
        weapon = make_named_melee_weapon(name)
        assert weapon.strength_requirement == str_req, name
        assert weapon.dmg_min(0) == dmg_min, name
        assert weapon.dmg_max(0) == dmg_max, name


def test_make_named_melee_weapon_dagger_and_worn_shortsword():
    assert isinstance(make_named_melee_weapon("Dagger"), Dagger)
    assert isinstance(make_named_melee_weapon("Worn Shortsword"), WornShortsword)


def test_wep_tier_order_indices_resolve_for_every_tier():
    for cat, names in WEP_TIER_ORDER.items():
        for idx, name in enumerate(names):
            if name == "Pickaxe":
                continue  # never selected (weight 0)
            ri = RolledItem(category=cat, is_artifact=False, is_upgradable=True, level=0, item_index=idx)
            item = _make_melee_weapon(ri.category, ri.item_index, ri.level, "test-id", None)
            assert isinstance(item, MeleeWeapon)
            assert item.name == name
