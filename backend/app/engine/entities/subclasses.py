from typing import Any, Dict, Optional, Set

from pydantic import BaseModel, Field

from app.engine.entities.talent_enum import Subclass, ArmorAbilityType, Talent

# Which subclasses each hero class may choose (granted by Tengu's Mask).
CLASS_SUBCLASSES: Dict[str, tuple[str, ...]] = {
    "warrior": (Subclass.BERSERKER, Subclass.GLADIATOR),
    "rogue": (Subclass.ASSASSIN, Subclass.FREERUNNER),
    "mage": (Subclass.BATTLEMAGE, Subclass.WARLOCK),
    "huntress": (Subclass.SNIPER, Subclass.WARDEN),
    "duelist": (Subclass.CHAMPION, Subclass.MONK),
    "cleric": (Subclass.PRIEST, Subclass.PALADIN),
}

# Per-class talent data lives in talent_data/ (one module per hero class).
# The TALENT_* tables below merge them so external consumers keep importing
# everything from this module.
from app.engine.entities.talent_data.common import (  # noqa: E402
    COMMON_TALENT_DEFS,
    COMMON_TALENT_CLASS_REQ,
    COMMON_TALENT_TITLES,
    COMMON_TALENT_DESCRIPTIONS,
)
from app.engine.entities.talent_data.warrior import (  # noqa: E402
    WARRIOR_TALENT_DEFS,
    WARRIOR_TALENT_CLASS_REQ,
    WARRIOR_TALENT_TITLES,
    WARRIOR_TALENT_DESCRIPTIONS,
)
from app.engine.entities.talent_data.rogue import (  # noqa: E402
    ROGUE_TALENT_DEFS,
    ROGUE_TALENT_CLASS_REQ,
    ROGUE_TALENT_TITLES,
    ROGUE_TALENT_DESCRIPTIONS,
)
from app.engine.entities.talent_data.mage import (  # noqa: E402
    MAGE_TALENT_DEFS,
    MAGE_TALENT_CLASS_REQ,
    MAGE_TALENT_TITLES,
    MAGE_TALENT_DESCRIPTIONS,
)
from app.engine.entities.talent_data.huntress import (  # noqa: E402
    HUNTRESS_TALENT_DEFS,
    HUNTRESS_TALENT_CLASS_REQ,
    HUNTRESS_TALENT_TITLES,
    HUNTRESS_TALENT_DESCRIPTIONS,
)
from app.engine.entities.talent_data.duelist import (  # noqa: E402
    DUELIST_TALENT_DEFS,
    DUELIST_TALENT_CLASS_REQ,
    DUELIST_TALENT_TITLES,
    DUELIST_TALENT_DESCRIPTIONS,
)
from app.engine.entities.talent_data.cleric import (  # noqa: E402
    CLERIC_TALENT_DEFS,
    CLERIC_TALENT_CLASS_REQ,
    CLERIC_TALENT_TITLES,
    CLERIC_TALENT_DESCRIPTIONS,
)


# Maps talent name → (max_points, tier, subclass_required_or_None)
TALENT_DEFS: Dict[str, tuple[int, int, Optional[str]]] = {
    **COMMON_TALENT_DEFS,
    **WARRIOR_TALENT_DEFS,
    **ROGUE_TALENT_DEFS,
    **MAGE_TALENT_DEFS,
    **HUNTRESS_TALENT_DEFS,
    **DUELIST_TALENT_DEFS,
    **CLERIC_TALENT_DEFS,
}

# Talents restricted to a hero class (the engine otherwise gates only by
# subclass). Talents absent from this map are available to any class.
TALENT_CLASS_REQ: Dict[str, str] = {
    **COMMON_TALENT_CLASS_REQ,
    **WARRIOR_TALENT_CLASS_REQ,
    **ROGUE_TALENT_CLASS_REQ,
    **MAGE_TALENT_CLASS_REQ,
    **HUNTRESS_TALENT_CLASS_REQ,
    **DUELIST_TALENT_CLASS_REQ,
    **CLERIC_TALENT_CLASS_REQ,
}

# Every talent member must carry a definition (guards against an enum member
# added without a matching TALENT_DEFS entry).
_undefined = {m for m in Talent} - set(TALENT_DEFS)
assert not _undefined, f"talents missing TALENT_DEFS entries: {sorted(_undefined)}"


# Armor-ability talents → the ability they unlock (first point locks the choice).
ABILITY_TALENTS: Dict[str, str] = {
    # Mage
    Talent.ELEMENTAL_BLAST_ABILITY: ArmorAbilityType.ELEMENTAL_BLAST,
    Talent.WILD_MAGIC_ABILITY: ArmorAbilityType.WILD_MAGIC,
    Talent.WARP_BEACON_ABILITY: ArmorAbilityType.WARP_BEACON,
    # Huntress
    Talent.SPECTRAL_BLADES_ABILITY: ArmorAbilityType.SPECTRAL_BLADES,
    Talent.NATURES_POWER_ABILITY: ArmorAbilityType.NATURES_POWER,
    Talent.SPIRIT_HAWK_ABILITY: ArmorAbilityType.SPIRIT_HAWK,
    # Duelist
    Talent.CHALLENGE_ABILITY: ArmorAbilityType.CHALLENGE,
    Talent.ELEMENTAL_STRIKE_ABILITY: ArmorAbilityType.ELEMENTAL_STRIKE,
    Talent.FEINT_ABILITY: ArmorAbilityType.FEINT,
    # Cleric
    Talent.ASCENDED_FORM_ABILITY: ArmorAbilityType.ASCENDED_FORM,
    Talent.TRINITY_ABILITY: ArmorAbilityType.TRINITY,
    Talent.POWER_OF_MANY_ABILITY: ArmorAbilityType.POWER_OF_MANY,
}


# Tier 4 talent → the armor ability it belongs to. Talents absent from this
# map (e.g. HEROIC_ENERGY-equivalents) are available regardless of which
# ability was chosen.
T4_ABILITY_TALENTS: Dict[str, str] = {
    Talent.BODY_SLAM: ArmorAbilityType.HEROIC_LEAP,
    Talent.IMPACT_WAVE: ArmorAbilityType.HEROIC_LEAP,
    Talent.DOUBLE_JUMP: ArmorAbilityType.HEROIC_LEAP,
    Talent.EXPANDING_WAVE: ArmorAbilityType.SHOCKWAVE,
    Talent.STRIKING_WAVE: ArmorAbilityType.SHOCKWAVE,
    Talent.SHOCK_FORCE: ArmorAbilityType.SHOCKWAVE,
    Talent.SUSTAINED_RETRIBUTION: ArmorAbilityType.ENDURE,
    Talent.SHRUG_IT_OFF: ArmorAbilityType.ENDURE,
    Talent.EVEN_THE_ODDS: ArmorAbilityType.ENDURE,
    # Rogue
    Talent.HASTY_RETREAT: ArmorAbilityType.SMOKE_BOMB,
    Talent.BODY_REPLACEMENT: ArmorAbilityType.SMOKE_BOMB,
    Talent.SHADOW_STEP: ArmorAbilityType.SMOKE_BOMB,
    Talent.FEAR_THE_REAPER: ArmorAbilityType.DEATH_MARK,
    Talent.DEATHLY_DURABILITY: ArmorAbilityType.DEATH_MARK,
    Talent.DOUBLE_MARK: ArmorAbilityType.DEATH_MARK,
    Talent.SHADOW_BLADE: ArmorAbilityType.SHADOW_CLONE,
    Talent.CLONED_ARMOR: ArmorAbilityType.SHADOW_CLONE,
    Talent.PERFECT_COPY: ArmorAbilityType.SHADOW_CLONE,
    # Duelist
    Talent.CLOSE_THE_GAP: ArmorAbilityType.CHALLENGE,
    Talent.INVIGORATING_VICTORY: ArmorAbilityType.CHALLENGE,
    Talent.ELIMINATION_MATCH: ArmorAbilityType.CHALLENGE,
    Talent.ELEMENTAL_REACH: ArmorAbilityType.ELEMENTAL_STRIKE,
    Talent.STRIKING_FORCE: ArmorAbilityType.ELEMENTAL_STRIKE,
    Talent.DIRECTED_POWER: ArmorAbilityType.ELEMENTAL_STRIKE,
    Talent.FEIGNED_RETREAT: ArmorAbilityType.FEINT,
    Talent.EXPOSE_WEAKNESS: ArmorAbilityType.FEINT,
    Talent.COUNTER_ABILITY: ArmorAbilityType.FEINT,
    # Cleric
    Talent.DIVINE_INTERVENTION: ArmorAbilityType.ASCENDED_FORM,
    Talent.JUDGEMENT: ArmorAbilityType.ASCENDED_FORM,
    Talent.FLASH: ArmorAbilityType.ASCENDED_FORM,
    Talent.BODY_FORM: ArmorAbilityType.TRINITY,
    Talent.MIND_FORM: ArmorAbilityType.TRINITY,
    Talent.SPIRIT_FORM: ArmorAbilityType.TRINITY,
    Talent.BEAMING_RAY: ArmorAbilityType.POWER_OF_MANY,
    Talent.LIFE_LINK: ArmorAbilityType.POWER_OF_MANY,
    Talent.STASIS: ArmorAbilityType.POWER_OF_MANY,
}

# Armor abilities a class may choose from, by class_type.
CLASS_ARMOR_ABILITIES: Dict[str, tuple[str, ...]] = {
    "warrior": (ArmorAbilityType.HEROIC_LEAP, ArmorAbilityType.SHOCKWAVE, ArmorAbilityType.ENDURE),
    "rogue": (ArmorAbilityType.SMOKE_BOMB, ArmorAbilityType.DEATH_MARK, ArmorAbilityType.SHADOW_CLONE),
    "duelist": (ArmorAbilityType.CHALLENGE, ArmorAbilityType.ELEMENTAL_STRIKE, ArmorAbilityType.FEINT),
    "cleric": (ArmorAbilityType.ASCENDED_FORM, ArmorAbilityType.TRINITY, ArmorAbilityType.POWER_OF_MANY),
}


# Level thresholds where talent tiers unlock
TIER_UNLOCK_LEVELS: Dict[int, int] = {
    1: 2,
    2: 7,
    3: 13,
    4: 21,
}

# Tier → max points per talent
TIER_MAX_POINTS: Dict[int, int] = {
    1: 2,
    2: 2,
    3: 3,
    4: 4,
}

# Combo moves (Gladiator) unlocked by combo count threshold, with UI tint.
COMBO_MOVES: Dict[str, dict] = {
    "clobber": {"count": 2, "tint": 0x00FF00},
    "slam": {"count": 4, "tint": 0xCCFF00},
    "parry": {"count": 6, "tint": 0xFFFF00},
    "crush": {"count": 8, "tint": 0xFFCC00},
    "fury": {"count": 10, "tint": 0xFF0000},
}

COST_ARMOR_ABILITY = 35  # Leap/Shockwave charge cost
COST_ENDURE = 50  # Endure charge cost (slightly higher)

# Heroic Energy (universal T4): reduces any armor ability's charge cost.
# [0,1,2,3,4] points -> multiplier.
HEROIC_ENERGY_MULT = (1.0, 0.88, 0.77, 0.68, 0.60)


def heroic_energy_mult(player: Any) -> float:
    """Universal armor-ability charge discount from the Heroic Energy talent."""
    pts = player.talent_info.level(Talent.HEROIC_ENERGY)
    return HEROIC_ENERGY_MULT[min(pts, 4)]

# Human-readable titles and descriptions served via /api/talents/{class}
TALENT_TITLES: Dict[str, str] = {
    **COMMON_TALENT_TITLES,
    **WARRIOR_TALENT_TITLES,
    **ROGUE_TALENT_TITLES,
    **MAGE_TALENT_TITLES,
    **HUNTRESS_TALENT_TITLES,
    **DUELIST_TALENT_TITLES,
    **CLERIC_TALENT_TITLES,
}

TALENT_DESCRIPTIONS: Dict[str, str] = {
    **COMMON_TALENT_DESCRIPTIONS,
    **WARRIOR_TALENT_DESCRIPTIONS,
    **ROGUE_TALENT_DESCRIPTIONS,
    **MAGE_TALENT_DESCRIPTIONS,
    **HUNTRESS_TALENT_DESCRIPTIONS,
    **DUELIST_TALENT_DESCRIPTIONS,
    **CLERIC_TALENT_DESCRIPTIONS,
}


class TalentInfo(BaseModel):
    talents: Dict[str, int] = Field(default_factory=dict)

    def get(self, name: str) -> int:
        return self.talents.get(name, 0)

    def has(self, name: str) -> bool:
        return self.talents.get(name, 0) > 0

    def level(self, name: str) -> int:
        return self.talents.get(name, 0)

    def max_level(self, name: str) -> int:
        return TALENT_DEFS.get(name, (0, 0, None))[0]


class SubclassInfo(BaseModel):
    subclass: Optional[str] = None
    talent_info: TalentInfo = Field(default_factory=TalentInfo)
    # Available talent points per tier (tier → count). Player earns these when a
    # new tier unlocks (level 2, 7, 13, 21) and consumes them on upgrade_talent().
    talent_points: Dict[int, int] = Field(default_factory=dict)
    # Bonus talent points per tier, granted by Potion of Divine Inspiration.
    bonus_talent_points: Dict[int, int] = Field(default_factory=dict)
    # Tracks which milestone levels (2, 6, 13) have had their events emitted.
    # Prevents re-emission on subsequent level-ups and ensures events fire even
    # when a multi-level jump skips the exact milestone level.
    emitted_milestones: Set[int] = Field(default_factory=set, exclude=True)
    # Talents replaced via Scroll of Metamorphosis: {original_talent: replacement_talent}
    metamorphed_talents: Dict[str, str] = Field(default_factory=dict)
