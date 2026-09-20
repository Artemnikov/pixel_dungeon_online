# Copyright (C) 2026 ArtemNikov
#
"""Duelist talent definitions, requirements, titles, and descriptions."""
from typing import Dict, Optional

from app.engine.entities.talent_enum import Subclass, Talent


# Maps talent name → (max_points, tier, subclass_required_or_None)
DUELIST_TALENT_DEFS: Dict[str, tuple[int, int, Optional[str]]] = {
    # Tier 1 (2 max points, tier 1)
    Talent.STRENGTHENING_MEAL: (2, 1, None),
    Talent.ADVENTURERS_INTUITION: (2, 1, None),
    Talent.PATIENT_STRIKE: (2, 1, None),
    Talent.AGGRESSIVE_BARRIER: (2, 1, None),

    # Tier 2 (2 max points, tier 2)
    Talent.FOCUSED_MEAL: (2, 2, None),
    Talent.LIQUID_AGILITY: (2, 2, None),
    Talent.WEAPON_RECHARGING: (2, 2, None),
    Talent.LETHAL_HASTE: (2, 2, None),
    Talent.SWIFT_EQUIP: (2, 2, None),

    # Tier 3 — Class Universal (3 max points, tier 3)
    Talent.PRECISE_ASSAULT: (3, 3, None),
    Talent.DEADLY_FOLLOWUP: (3, 3, None),

    # Tier 3 — Champion Subclass (3 max points, tier 3)
    Talent.VARIED_CHARGE: (3, 3, Subclass.CHAMPION),
    Talent.TWIN_UPGRADES: (3, 3, Subclass.CHAMPION),
    Talent.COMBINED_LETHALITY: (3, 3, Subclass.CHAMPION),

    # Tier 3 — Monk Subclass (3 max points, tier 3)
    Talent.UNENCUMBERED_SPIRIT: (3, 3, Subclass.MONK),
    Talent.MONASTIC_VIGOR: (3, 3, Subclass.MONK),
    Talent.COMBINED_ENERGY: (3, 3, Subclass.MONK),

    # Tier 3 — Armor Ability Unlocks
    Talent.CHALLENGE_ABILITY: (1, 3, None),
    Talent.ELEMENTAL_STRIKE_ABILITY: (1, 3, None),
    Talent.FEINT_ABILITY: (1, 3, None),

    # Tier 4 — Challenge Talents (4 max points, tier 4)
    Talent.CLOSE_THE_GAP: (4, 4, None),
    Talent.INVIGORATING_VICTORY: (4, 4, None),
    Talent.ELIMINATION_MATCH: (4, 4, None),

    # Tier 4 — Elemental Strike Talents (4 max points, tier 4)
    Talent.ELEMENTAL_REACH: (4, 4, None),
    Talent.STRIKING_FORCE: (4, 4, None),
    Talent.DIRECTED_POWER: (4, 4, None),

    # Tier 4 — Feint Talents (4 max points, tier 4)
    Talent.FEIGNED_RETREAT: (4, 4, None),
    Talent.EXPOSE_WEAKNESS: (4, 4, None),
    Talent.COUNTER_ABILITY: (4, 4, None),
}

DUELIST_TALENT_CLASS_REQ: Dict[str, str] = {
    # Tier 1
    Talent.STRENGTHENING_MEAL: "duelist",
    Talent.ADVENTURERS_INTUITION: "duelist",
    Talent.PATIENT_STRIKE: "duelist",
    Talent.AGGRESSIVE_BARRIER: "duelist",

    # Tier 2
    Talent.FOCUSED_MEAL: "duelist",
    Talent.LIQUID_AGILITY: "duelist",
    Talent.WEAPON_RECHARGING: "duelist",
    Talent.LETHAL_HASTE: "duelist",
    Talent.SWIFT_EQUIP: "duelist",

    # Tier 3
    Talent.PRECISE_ASSAULT: "duelist",
    Talent.DEADLY_FOLLOWUP: "duelist",
    Talent.VARIED_CHARGE: "duelist",
    Talent.TWIN_UPGRADES: "duelist",
    Talent.COMBINED_LETHALITY: "duelist",
    Talent.UNENCUMBERED_SPIRIT: "duelist",
    Talent.MONASTIC_VIGOR: "duelist",
    Talent.COMBINED_ENERGY: "duelist",
    Talent.CHALLENGE_ABILITY: "duelist",
    Talent.ELEMENTAL_STRIKE_ABILITY: "duelist",
    Talent.FEINT_ABILITY: "duelist",

    # Tier 4
    Talent.CLOSE_THE_GAP: "duelist",
    Talent.INVIGORATING_VICTORY: "duelist",
    Talent.ELIMINATION_MATCH: "duelist",
    Talent.ELEMENTAL_REACH: "duelist",
    Talent.STRIKING_FORCE: "duelist",
    Talent.DIRECTED_POWER: "duelist",
    Talent.FEIGNED_RETREAT: "duelist",
    Talent.EXPOSE_WEAKNESS: "duelist",
    Talent.COUNTER_ABILITY: "duelist",
}

DUELIST_TALENT_TITLES: Dict[str, str] = {
    # Tier 1
    Talent.STRENGTHENING_MEAL: "Strengthening Meal",
    Talent.ADVENTURERS_INTUITION: "Adventurer's Intuition",
    Talent.PATIENT_STRIKE: "Patient Strike",
    Talent.AGGRESSIVE_BARRIER: "Aggressive Barrier",

    # Tier 2
    Talent.FOCUSED_MEAL: "Focused Meal",
    Talent.LIQUID_AGILITY: "Liquid Agility",
    Talent.WEAPON_RECHARGING: "Weapon Recharging",
    Talent.LETHAL_HASTE: "Lethal Haste",
    Talent.SWIFT_EQUIP: "Swift Equip",

    # Tier 3
    Talent.PRECISE_ASSAULT: "Precise Assault",
    Talent.DEADLY_FOLLOWUP: "Deadly Followup",
    Talent.VARIED_CHARGE: "Varied Charge",
    Talent.TWIN_UPGRADES: "Twin Upgrades",
    Talent.COMBINED_LETHALITY: "Combined Lethality",
    Talent.UNENCUMBERED_SPIRIT: "Unencumbered Spirit",
    Talent.MONASTIC_VIGOR: "Monastic Vigor",
    Talent.COMBINED_ENERGY: "Combined Energy",
    Talent.CHALLENGE_ABILITY: "Challenge",
    Talent.ELEMENTAL_STRIKE_ABILITY: "Elemental Strike",
    Talent.FEINT_ABILITY: "Feint",

    # Tier 4
    Talent.CLOSE_THE_GAP: "Close the Gap",
    Talent.INVIGORATING_VICTORY: "Invigorating Victory",
    Talent.ELIMINATION_MATCH: "Elimination Match",
    Talent.ELEMENTAL_REACH: "Elemental Reach",
    Talent.STRIKING_FORCE: "Striking Force",
    Talent.DIRECTED_POWER: "Directed Power",
    Talent.FEIGNED_RETREAT: "Feigned Retreat",
    Talent.EXPOSE_WEAKNESS: "Expose Weakness",
    Talent.COUNTER_ABILITY: "Counter Ability",
}

DUELIST_TALENT_DESCRIPTIONS: Dict[str, str] = {
    # Tier 1
    Talent.STRENGTHENING_MEAL: "Eating food grants bonus damage on your next few melee attacks.",
    Talent.ADVENTURERS_INTUITION: "Identifies weapons and armor faster in combat. At max rank, instantly identifies weapons upon equipping.",
    Talent.PATIENT_STRIKE: "Waiting in place grants bonus damage on your next melee attack.",
    Talent.AGGRESSIVE_BARRIER: "Using a weapon ability when below 50% HP grants a protective barrier.",

    # Tier 2
    Talent.FOCUSED_MEAL: "Eating food takes only 1 turn and instantly restores weapon charge.",
    Talent.LIQUID_AGILITY: "Using potions grants massive evasion and accuracy on your next action.",
    Talent.WEAPON_RECHARGING: "Gains weapon charge over time while under Wand or Artifact Recharging buffs.",
    Talent.LETHAL_HASTE: "Killing an enemy with a weapon ability grants greater haste for several turns.",
    Talent.SWIFT_EQUIP: "Switching or equipping weapons takes 0 turns periodically.",

    # Tier 3
    Talent.PRECISE_ASSAULT: "After using a weapon ability, your next melee attack within 5 turns gains significantly higher accuracy.",
    Talent.DEADLY_FOLLOWUP: "Hitting an enemy with a thrown weapon increases melee damage dealt to them for 5 turns.",
    Talent.VARIED_CHARGE: "Using two different weapon abilities sequentially restores weapon charge.",
    Talent.TWIN_UPGRADES: "Lower-level equipped weapon shares the upgrade level of your higher-level weapon based on tier difference.",
    Talent.COMBINED_LETHALITY: "Attacking with a weapon after using another weapon's ability executes low-health enemies.",
    Talent.UNENCUMBERED_SPIRIT: "Lighter tier equipment grants higher Monk energy multipliers. Max rank grants free identified starter gear.",
    Talent.MONASTIC_VIGOR: "Lowers the energy threshold required for empowered Monk abilities.",
    Talent.COMBINED_ENERGY: "Using a weapon ability and a high-cost Monk ability sequentially restores 1 energy.",
    Talent.CHALLENGE_ABILITY: "Unlocks the Challenge armor ability to isolate and duel a target foe.",
    Talent.ELEMENTAL_STRIKE_ABILITY: "Unlocks the Elemental Strike armor ability to unleash weapon enchantment in a cone.",
    Talent.FEINT_ABILITY: "Unlocks the Feint armor ability to confuse foes and leave an afterimage.",

    # Tier 4
    Talent.CLOSE_THE_GAP: "Hero leaps towards the target upon initiating Challenge.",
    Talent.INVIGORATING_VICTORY: "Defeating the challenged foe heals the hero and restores health based on damage taken during the duel.",
    Talent.ELIMINATION_MATCH: "Challenging another foe shortly after a duel ends reduces armor charge cost.",
    Talent.ELEMENTAL_REACH: "Increases the cone range and angle of Elemental Strike.",
    Talent.STRIKING_FORCE: "Increases the power and duration of Elemental Strike effects.",
    Talent.DIRECTED_POWER: "Primary melee strike gains bonus enchantment power for each enemy caught in the cone.",
    Talent.FEIGNED_RETREAT: "Hero gains Haste when an enemy attacks the afterimage.",
    Talent.EXPOSE_WEAKNESS: "Enemies that strike the afterimage become Vulnerable and Weakened.",
    Talent.COUNTER_ABILITY: "Using a weapon ability shortly after the afterimage is struck restores weapon charge.",
}

# Legacy alias mapping dict for backward-compatibility migrations
DUELIST_LEGACY_TALENT_MAP: Dict[str, str] = {
    "aggressive_approach": Talent.STRENGTHENING_MEAL,
    "lightweight_combat": Talent.ADVENTURERS_INTUITION,
    "duelist_lethal_momentum": Talent.PATIENT_STRIKE,
    "stick_and_move": Talent.AGGRESSIVE_BARRIER,
    "dual_strike": Talent.FOCUSED_MEAL,
    "circle_of_slaughter": Talent.LIQUID_AGILITY,
    "finisher": Talent.WEAPON_RECHARGING,
    "ferocity": Talent.LETHAL_HASTE,
    "charged_attack": Talent.PRECISE_ASSAULT,
    "champion_power": Talent.VARIED_CHARGE,
    "champion_endurance": Talent.TWIN_UPGRADES,
    "champion_reach": Talent.COMBINED_LETHALITY,
    "monks_spirit": Talent.COMBINED_ENERGY,
    "lasting_challenge": Talent.CLOSE_THE_GAP,
    "heightened_challenge": Talent.INVIGORATING_VICTORY,
    "dual_challenge": Talent.ELIMINATION_MATCH,
    "searing_strike": Talent.ELEMENTAL_REACH,
    "chilling_strike": Talent.STRIKING_FORCE,
    "charged_strike": Talent.DIRECTED_POWER,
    "shadow_feint": Talent.FEIGNED_RETREAT,
    "reactive_feint": Talent.EXPOSE_WEAKNESS,
    "phantasmal_feint": Talent.COUNTER_ABILITY,
}
