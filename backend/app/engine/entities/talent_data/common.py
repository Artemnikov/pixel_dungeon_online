"""Shared (class-agnostic) talent data.

Only genuinely universal talents live here. Everything else is owned by the
per-class modules in this package. HEROIC_ENERGY is a Tier 4 charge-cost
reduction available to any class once T4 is unlocked; the Ratmogrify talents
belong to the Rat King's class-agnostic armor ability. All of them are
intentionally absent from TALENT_CLASS_REQ.
"""

from typing import Dict, Optional

from app.engine.entities.talent_enum import Talent


COMMON_TALENT_DEFS: Dict[str, tuple[int, int, Optional[str]]] = {
    Talent.HEROIC_ENERGY: (4, 4, None),
    Talent.RATSISTANCE: (4, 4, None),
    Talent.RATLOMACY: (4, 4, None),
    Talent.RATFORCEMENTS: (4, 4, None),
}

COMMON_TALENT_CLASS_REQ: Dict[str, str] = {}

COMMON_TALENT_TITLES: Dict[str, str] = {
    Talent.HEROIC_ENERGY: "Heroic Energy",
    Talent.RATSISTANCE: "Ratsistance",
    Talent.RATLOMACY: "Ratlomacy",
    Talent.RATFORCEMENTS: "Ratforcements",
}

# SPD Talent.title(): Heroic Energy is renamed while Ratmogrify is the hero's
# armor ability.
HEROIC_ENERGY_RAT_TITLE = "Ratroic Energy"

COMMON_TALENT_DESCRIPTIONS: Dict[str, str] = {
    Talent.HEROIC_ENERGY: "Reduces your armor ability's charge cost by 12%/23%/32%/40%.",
    Talent.RATSISTANCE: "Hostile ratmogrified enemies deal 10%/19%/27%/35% less damage.",
    Talent.RATLOMACY: "Using Ratmogrify on a ratmogrified enemy makes them friendly and makes the transformation permanent, giving them 0/2/4/6 turns of adrenaline.",
    Talent.RATFORCEMENTS: "Using Ratmogrify on yourself spawns 1/2/3/4 ally marsupial rats next to you.",
}
