from __future__ import annotations

from typing import ClassVar, List, Literal, Optional, TYPE_CHECKING

from app.engine.entities.base import Action, ItemBase, ItemCategory
from app.engine.entities.items_equip import EquipableItem, KindofMisc

if TYPE_CHECKING:
    from app.engine.entities.player import Player


class Trinket(KindofMisc):
    kind: Literal["trinket"] = "trinket"
    type: str = "trinket"
    unique: bool = True
    level_known: bool = True
    category: ClassVar[str] = ItemCategory.TRINKET
    level: int = 0
    strength_requirement: int = 0
    DESC: ClassVar[str] = "A mystical trinket that grants a passive bonus while worn."

    def upgrade_energy_cost(self) -> int:
        return 6 + 2 * self.level

    @classmethod
    def energy_val(cls) -> int:
        return 5

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = list(super().actions(player))
        equipped = bool(player and player.belongings.is_equipped(self.id))
        return [Action.UNEQUIP if equipped else Action.EQUIP] + base

    def default_action(self) -> Optional[str]:
        return Action.EQUIP


class RatSkull(Trinket):
    kind: Literal["rat_skull"] = "rat_skull"
    name: str = "Rat Skull"

    @staticmethod
    def exotic_chance_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 2.0 + level


class ParchmentScrap(Trinket):
    kind: Literal["parchment_scrap"] = "parchment_scrap"
    name: str = "Parchment Scrap"

    def upgrade_energy_cost(self) -> int:
        return 10 + 5 * self.level

    @staticmethod
    def enchant_chance_multiplier(level: int = -1) -> float:
        mapping = {-1: 1.0, 0: 2.0, 1: 4.0, 2: 7.0, 3: 10.0}
        return mapping.get(level, 1.0)

    @staticmethod
    def curse_chance_multiplier(level: int = -1) -> float:
        mapping = {-1: 1.0, 0: 1.5, 1: 2.0, 2: 1.0, 3: 0.0}
        return mapping.get(level, 1.0)


class PetrifiedSeed(Trinket):
    kind: Literal["petrified_seed"] = "petrified_seed"
    name: str = "Petrified Seed"

    @staticmethod
    def stone_instead_of_seed_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.25 + 0.21 * level

    @staticmethod
    def grass_loot_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 1.0 + 0.25 * level / 3


class ExoticCrystals(Trinket):
    kind: Literal["exotic_crystals"] = "exotic_crystals"
    name: str = "Exotic Crystals"

    @staticmethod
    def consumable_exotic_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.125 + 0.125 * level


class MossyClump(Trinket):
    kind: Literal["mossy_clump"] = "mossy_clump"
    name: str = "Mossy Clump"

    def upgrade_energy_cost(self) -> int:
        return 10 + 5 * self.level

    @staticmethod
    def override_normal_level_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.25 + 0.25 * level


class DimensionalSundial(Trinket):
    kind: Literal["dimensional_sundial"] = "dimensional_sundial"
    name: str = "Dimensional Sundial"

    @staticmethod
    def daytime_spawn_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 0.95 - 0.05 * level

    @staticmethod
    def nighttime_spawn_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 1.25 + 0.25 * level


class ThirteenLeafClover(Trinket):
    kind: Literal["thirteen_leaf_clover"] = "thirteen_leaf_clover"
    name: str = "Thirteen-Leaf Clover"

    @staticmethod
    def alter_damage_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.25 + 0.25 * level


class TrapMechanism(Trinket):
    kind: Literal["trap_mechanism"] = "trap_mechanism"
    name: str = "Trap Mechanism"

    @staticmethod
    def override_normal_level_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.25 + 0.25 * level

    @staticmethod
    def reveal_hidden_trap_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.1 + 0.1 * level


class MimicTooth(Trinket):
    kind: Literal["mimic_tooth"] = "mimic_tooth"
    name: str = "Mimic Tooth"

    @staticmethod
    def mimic_chance_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 1.5 + 0.5 * level

    @staticmethod
    def ebony_mimic_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.125 + 0.125 * level


class WondrousResin(Trinket):
    kind: Literal["wondrous_resin"] = "wondrous_resin"
    name: str = "Wondrous Resin"

    def upgrade_energy_cost(self) -> int:
        return 10 + 5 * self.level

    @staticmethod
    def positive_curse_effect_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.25 + 0.25 * level

    @staticmethod
    def extra_curse_effect_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.125 + 0.125 * level


class EyeOfNewt(Trinket):
    kind: Literal["eye_of_newt"] = "eye_of_newt"
    name: str = "Eye of Newt"

    @staticmethod
    def vision_range_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 0.875 - 0.125 * level

    @staticmethod
    def mind_vision_radius(level: int = -1) -> int:
        if level == -1:
            return 0
        return 2 + level


class SaltCube(Trinket):
    kind: Literal["salt_cube"] = "salt_cube"
    name: str = "Salt Cube"

    @staticmethod
    def hunger_gain_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 1.0 / (1.0 + 0.25 * (level + 1))

    @staticmethod
    def health_regen_multiplier(level: int = -1) -> float:
        mapping = {-1: 1.0, 0: 0.84, 1: 0.73, 2: 0.66, 3: 0.6}
        return mapping.get(level, 1.0)


class VialOfBlood(Trinket):
    kind: Literal["vial_of_blood"] = "vial_of_blood"
    name: str = "Vial of Blood"

    @staticmethod
    def delay_burst_healing(level: int = -1) -> bool:
        return level != -1

    @staticmethod
    def total_heal_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 1.0 + 0.125 * (level + 1)

    @staticmethod
    def max_heal_per_turn(level: int = -1, max_hp: int = 100) -> int:
        if level == -1:
            return max_hp
        mapping = {0: (4, 0.15), 1: (3, 0.10), 2: (2, 0.07), 3: (1, 0.05)}
        base, frac = mapping.get(level, (4, 0.15))
        return base + round(frac * max_hp)


class ShardOfOblivion(Trinket):
    kind: Literal["shard_of_oblivion"] = "shard_of_oblivion"
    name: str = "Shard of Oblivion"

    @staticmethod
    def loot_chance_multiplier(level: int = -1, worn_un_id: int = 0) -> float:
        if level == -1:
            return 1.0
        return 1.0 + 0.2 * min(worn_un_id, level + 1)


class ChaoticCenser(Trinket):
    kind: Literal["chaotic_censer"] = "chaotic_censer"
    name: str = "Chaotic Censer"

    @staticmethod
    def average_turns_until_gas(level: int = -1) -> int:
        if level == -1:
            return -1
        return 300 // (level + 1)


class FerretTuft(Trinket):
    kind: Literal["ferret_tuft"] = "ferret_tuft"
    name: str = "Ferret Tuft"

    @staticmethod
    def evasion_multiplier(level: int = -1) -> float:
        if level == -1:
            return 1.0
        return 1.0 + 0.125 * (level + 1)


class CrackedSpyglass(Trinket):
    kind: Literal["cracked_spyglass"] = "cracked_spyglass"
    name: str = "Cracked Spyglass"

    @staticmethod
    def extra_loot_chance(level: int = -1) -> float:
        if level == -1:
            return 0.0
        return 0.375 * (level + 1)


class TrinketCatalyst(ItemBase):
    kind: Literal["trinket_catalyst"] = "trinket_catalyst"
    type: str = "trinket_catalyst"
    name: str = "Trinket Catalyst"
    unique: bool = True
    level_known: bool = True
    category: ClassVar[str] = ItemCategory.MISC
    DESC: ClassVar[str] = "Can be used at an Alchemy Pot to create a random trinket."

    @classmethod
    def energy_val(cls) -> int:
        return 6

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = list(super().actions(player))
        return [Action.ALCHEMIZE] + base


_TRINKET_CLASSES = [
    RatSkull, ParchmentScrap, PetrifiedSeed, ExoticCrystals,
    MossyClump, DimensionalSundial, ThirteenLeafClover, TrapMechanism,
    MimicTooth, WondrousResin, EyeOfNewt, SaltCube, VialOfBlood,
    ShardOfOblivion, ChaoticCenser, FerretTuft, CrackedSpyglass,
]

_TRINKET_KINDS = [cls.model_fields["kind"].default for cls in _TRINKET_CLASSES]


def trinket_kind_for_index(idx: int) -> str:
    return _TRINKET_KINDS[idx] if 0 <= idx < len(_TRINKET_KINDS) else ""

def trinket_class_for_kind(kind: str):
    for cls in _TRINKET_CLASSES:
        if cls.model_fields["kind"].default == kind:
            return cls
    return None

def trinket_class_for_index(idx: int):
    if 0 <= idx < len(_TRINKET_CLASSES):
        return _TRINKET_CLASSES[idx]
    return RatSkull

def trinket_level(player, trinket_kind: str) -> int:
    """SPD trinketLevel(Class): returns buffed level of the trinket the player
    has equipped in their misc slot, or -1 if no matching trinket is worn."""
    misc = getattr(getattr(player, "belongings", None), "misc", None)
    if misc is None:
        return -1
    if getattr(misc, "kind", None) != trinket_kind:
        return -1
    return max(0, misc.level) if not misc.cursed else 0
