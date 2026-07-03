# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
from __future__ import annotations

import uuid as _uuid
import random as _random
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field, model_validator, SerializeAsAny

from app.engine.entities.buffs import Buff, add_buff, remove_buff, has_buff, get_buff
from app.engine.entities.subclasses import SubclassInfo, TalentInfo, Talent
from app.engine.entities.weapon_defs import WEAPON_DEFS

from app.engine.entities.base import *  # noqa: F401,F403
from app.engine.entities.items_equip import Artifact, KindofMisc, MeleeWeapon, Armor


class BrokenSeal(Artifact):
    kind: Literal["broken_seal"] = "broken_seal"
    name: str = "Broken Seal"
    charge: int = 0
    charge_cap: int = 100
    DESC: ClassVar[str] = "A broken seal from the warrior's armor. It can be affixed to armor to provide shielding as you fight."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        equipped = bool(player and player.belongings.is_equipped(self.id))
        if not equipped:
            return base
        has_armor = bool(player and player.belongings.armor is not None)
        if has_armor:
            return [Action.AFFIX, Action.UNEQUIP] + base
        return [Action.UNEQUIP] + base


class CloakOfShadows(Artifact):
    # The Rogue's signature artifact. Toggling STEALTH turns the hero invisible,
    # draining one charge every few seconds (see tick.py's cloak drain). It self-
    # levels with use (charge_cap grows 3 -> 10). Charge regenerates while not
    # stealthed. Mirrors SPD's CloakOfShadows; turn-based timers are recast as
    # real seconds for this engine.
    kind: Literal["cloak_of_shadows"] = "cloak_of_shadows"
    name: str = "Cloak of Shadows"
    type: str = "artifact"
    unique: bool = True
    charge: int = 3
    charge_cap: int = 3
    level_cap: ClassVar[int] = 10
    exp: int = 0
    DESC: ClassVar[str] = (
        "This cloak is an heirloom, passed down from generation to generation. "
        "Activate it to vanish into the shadows; striking from stealth lands a "
        "guaranteed, more powerful surprise attack."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None:
            return base
        light_cloak = player.talent_info.has("light_cloak")
        usable = (player.belongings.is_equipped(self.id) or light_cloak) and not self.cursed
        has_charge = self.charge > 0 or player.cloak_stealth_active
        if usable and has_charge:
            return [Action.STEALTH] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.STEALTH

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"The cloak holds {self.charge} of {self.charge_cap} charges.")
        return lines

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, self.level_cap)


class DriedRose(Artifact):
    kind: Literal["dried_rose"] = "dried_rose"
    name: str = "Dried Rose"
    type: str = "artifact"
    unique: bool = True
    charge: int = 100
    charge_cap: int = 100
    level_cap: ClassVar[int] = 10
    exp: int = 0
    ghost_id: Optional[str] = None
    weapon: Optional["MeleeWeapon"] = None
    armor: Optional["Armor"] = None
    dropped_petals: int = 0
    DESC: ClassVar[str] = "A dried rose that holds the spirit of a fallen warrior. Equip and charge it to summon the ghost as an ally."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None:
            return base
        equipped = player.belongings.is_equipped(self.id)
        can_summon = (
            equipped
            and self.charge >= self.charge_cap
            and not self.cursed
            and self.has_no_ghost()
        )
        if can_summon:
            return [Action.SUMMON] + base
        if self.has_ghost():
            return [Action.DIRECT, "GHOST_GEAR"] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.DIRECT if self.has_ghost() else Action.SUMMON

    def has_ghost(self) -> bool:
        return self.ghost_id is not None

    def has_no_ghost(self) -> bool:
        return self.ghost_id is None

    def ghost_strength(self) -> int:
        return 13 + self.level // 2

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, self.level_cap)


class AlchemistsToolkit(Artifact):
    kind: Literal["alchemists_toolkit"] = "alchemists_toolkit"
    name: str = "Alchemist's Toolkit"
    charge: int = 0
    charge_cap: int = 10
    level_cap: ClassVar[int] = 10
    exp: int = 0
    _charge_accum: float = 0.0
    DESC: ClassVar[str] = "A set of alchemical tools. It passively charges with alchemical energy, which can be used to brew items at any alchemy pot."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        acts = [Action.BREW]
        if self.level < self.level_cap:
            acts.append(Action.ENERGIZE)
        return acts + base

    def consume_energy(self, amount: int) -> int:
        """Drain kit charge first; return the remainder still owed from the
        player's energy (SPD AlchemistsToolkit.consumeEnergy)."""
        remainder = amount - self.charge
        self.charge = max(0, self.charge - amount)
        return max(0, remainder)

    def on_upgrade(self) -> None:
        # SPD AlchemistsToolkit.upgrade(): chargeCap++ unconditionally — the
        # kit's charge capacity is unrelated to level_cap (10 kit levels can
        # push charge_cap well past its starting value of 10).
        self.charge_cap += 1


class CapeOfThorns(Artifact):
    kind: Literal["cape_of_thorns"] = "cape_of_thorns"
    name: str = "Cape of Thorns"
    charge: int = 0
    charge_cap: int = 100
    level_cap: ClassVar[int] = 10
    exp: int = 0
    DESC: ClassVar[str] = "A tattered cape lined with hardened thorns. It absorbs damage, then releases it back at attackers when fully charged."

    def on_upgrade(self) -> None:
        pass  # cape levels grant increased retaliation, no charge_cap change


class ChaliceOfBlood(Artifact):
    kind: Literal["chalice_of_blood"] = "chalice_of_blood"
    name: str = "Chalice of Blood"
    charge: int = 0
    charge_cap: int = 1
    level_cap: ClassVar[int] = 10
    DESC: ClassVar[str] = "An ornate chalice. While equipped it enhances your natural regeneration. Pricking yourself with its needle upgrades it directly — at the cost of your health."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        if self.level < self.level_cap and not player.has_buff("time_stasis"):
            return [Action.PRICK] + base
        return base

    def on_upgrade(self) -> None:
        # SPD only swaps the sprite tier on upgrade; no stat field to change here.
        pass

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        from app.engine.game.artifacts import _chalice_heal_rate
        rate = _chalice_heal_rate(self.level)
        lines.append(f"Regenerates about {rate:.2f} HP per second while equipped.")
        return lines


class EtherealChains(Artifact):
    kind: Literal["ethereal_chains"] = "ethereal_chains"
    name: str = "Ethereal Chains"
    charge: int = 5               # SPD: 5 + level*2
    charge_cap: int = 5
    level_cap: ClassVar[int] = 5
    exp: int = 0
    _recharge_accum: float = 0.0
    DESC: ClassVar[str] = "A length of ethereal chain. Cast at a foe to yank them toward you; cast at a wall to pull yourself across the gap."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        if self.charge > 0:
            return [Action.CAST] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.CAST

    def on_upgrade(self) -> None:
        self.charge_cap = 5 + self.level * 2

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} charges.")
        return lines


class HolyTome(Artifact):
    kind: Literal["holy_tome"] = "holy_tome"
    name: str = "Holy Tome"
    charge: int = 0
    charge_cap: int = 3
    level_cap: ClassVar[int] = 10
    exp: int = 0
    DESC: ClassVar[str] = "A tome of holy scripture. Each scroll read while it is equipped charges it with divine power, which amplifies the next scroll read."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        if self.charge >= self.charge_cap:
            return [Action.BLESS] + base
        return base

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, 5)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} charges.")
        return lines


class HornOfPlenty(Artifact):
    kind: Literal["horn_of_plenty"] = "horn_of_plenty"
    name: str = "Horn of Plenty"
    charge: int = 0
    charge_cap: int = 5
    level_cap: ClassVar[int] = 10
    exp: int = 0
    _charge_accum: float = 0.0
    DESC: ClassVar[str] = "A magical horn that slowly fills with food. Snack from it for a quick heal, or eat deeply to become satiated."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        acts = []
        if self.charge >= 1:
            acts.append(Action.SNACK)
        if self.charge >= self.charge_cap:
            acts.append(Action.EAT)
        acts.append(Action.STORE)
        return acts + base

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, 10)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} food charges.")
        return lines


class LloydsBeacon(Artifact):
    kind: Literal["lloyds_beacon"] = "lloyds_beacon"
    name: str = "Lloyd's Beacon"
    charge: int = 3
    charge_cap: int = 3
    level_cap: ClassVar[int] = 10
    exp: int = 0
    beacon_floor: Optional[int] = None
    beacon_x: Optional[int] = None
    beacon_y: Optional[int] = None
    _recharge_accum: float = 0.0
    DESC: ClassVar[str] = "A magical beacon. Set it at a location, then return to that exact spot from anywhere — even a different floor."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        acts = [Action.BEACON_SET]
        if self.beacon_floor is not None and self.charge > 0:
            acts.append(Action.BEACON_RETURN)
        return acts + base

    def default_action(self) -> Optional[str]:
        return Action.BEACON_RETURN if self.beacon_floor is not None else Action.BEACON_SET

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, 6)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} charges.")
        if self.beacon_floor is not None:
            lines.append(f"Beacon set at floor {self.beacon_floor} ({self.beacon_x},{self.beacon_y}).")
        return lines


class MasterThievesArmband(Artifact):
    kind: Literal["master_thieves_armband"] = "master_thieves_armband"
    name: str = "Master Thieves' Armband"
    charge: int = 5
    charge_cap: int = 5
    level_cap: ClassVar[int] = 10
    exp: int = 0
    _recharge_accum: float = 0.0
    DESC: ClassVar[str] = "A faded armband once worn by a legendary thief. Each kill has a chance to steal gold from the victim; you can also attempt a targeted steal at the cost of a charge."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        if self.charge > 0:
            return [Action.STEAL] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.STEAL

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, 10)


class SandalsOfNature(Artifact):
    kind: Literal["sandals_of_nature"] = "sandals_of_nature"
    name: str = "Sandals of Nature"
    charge: int = 0
    charge_cap: int = 5
    level_cap: ClassVar[int] = 10
    exp: int = 0
    stored_seeds: List[str] = Field(default_factory=list)
    DESC: ClassVar[str] = "Sandals woven from living grass. Walking on vegetation charges them; use the stored energy to identify seeds or plant them directly from your pack."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        acts = []
        if self.charge >= 1 and player:
            has_unid_seed = any(
                getattr(it, "kind", "").endswith("_seed") and not it.level_known
                for it in player.belongings.backpack.items.values()
            )
            if has_unid_seed:
                acts.append(Action.IDENTIFY_SEED)
        if self.stored_seeds:
            acts.append(Action.PLANT_SEED)
        return acts + base

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, 10)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} nature charges.")
        if self.stored_seeds:
            lines.append(f"Stored seeds: {len(self.stored_seeds)}")
        return lines


class SkeletonKey(Artifact):
    kind: Literal["skeleton_key"] = "skeleton_key"
    name: str = "Skeleton Key"
    charge: int = 5
    charge_cap: int = 5
    level_cap: ClassVar[int] = 10
    exp: int = 0
    _recharge_accum: float = 0.0
    DESC: ClassVar[str] = "A skeleton key that can open any lock. It also lets you reveal nearby hidden doors and traps."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        acts = []
        if self.charge >= 1:
            acts.append(Action.UNLOCK)
        if self.charge >= 2:
            acts.append(Action.KEY_REVEAL)
        return acts + base

    def on_upgrade(self) -> None:
        self.charge_cap = min(self.charge_cap + 1, 10)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} charges.")
        return lines


class TalismanOfForesight(Artifact):
    kind: Literal["talisman_of_foresight"] = "talisman_of_foresight"
    name: str = "Talisman of Foresight"
    charge: int = 0
    charge_cap: int = 100
    level_cap: ClassVar[int] = 10
    exp: int = 0
    _charge_accum: float = 0.0
    DESC: ClassVar[str] = "A mystical talisman. It slowly charges with foresight; spend 20 charges to scry the floor and reveal hidden traps and doors nearby."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        if self.charge >= 20:
            return [Action.SCRY] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.SCRY

    def on_upgrade(self) -> None:
        pass  # leveling increases scry radius, no field change needed

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Charged {self.charge}/{self.charge_cap}.")
        return lines


class TimekeepersHourglass(Artifact):
    kind: Literal["timekeepers_hourglass"] = "timekeepers_hourglass"
    name: str = "Timekeeper's Hourglass"
    charge: int = 5               # SPD: 5 + level()
    charge_cap: int = 5
    level_cap: ClassVar[int] = 5
    exp: int = 0
    _recharge_accum: float = 0.0
    DESC: ClassVar[str] = "An hourglass of impossible complexity. Freeze halts all enemies around you; Stasis suspends you outside of time — untouchable, but unable to act."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        if self.charge > 0:
            return [Action.FREEZE, Action.STASIS] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.FREEZE

    def on_upgrade(self) -> None:
        self.charge_cap = 5 + self.level

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} charges.")
        return lines


# SPD Generator.Category.SCROLL.classes order (index -> kind). Weights come from
# run_state.SCROLL_DEFAULT_PROBS_TOTAL (same index). Upgrade (index 0) has weight
# 0, so it is never drawn; transmutation (index 11) is drawn then explicitly
# removed. Mirrors UnstableSpellbook.setupScrolls().
_SPELLBOOK_SCROLL_KINDS: Tuple[str, ...] = (
    "scroll_of_upgrade", "scroll_of_identify", "scroll_of_remove_curse",
    "scroll_of_mirror_image", "scroll_of_recharging", "scroll_of_teleportation",
    "scroll_of_lullaby", "scroll_of_magic_mapping", "scroll_of_rage",
    "scroll_of_retribution", "scroll_of_terror", "scroll_of_transmutation",
)


def _build_spellbook_index() -> List[str]:
    """Weighted draw-without-replacement over the SPD scroll deck, minus
    transmutation (upgrade is weight-0 so never picked). Order matters: the book
    shrinks this list from the front as it levels up."""
    from app.engine.dungeon.spd_levelgen.run_state import SCROLL_DEFAULT_PROBS_TOTAL
    pool = [(k, SCROLL_DEFAULT_PROBS_TOTAL[i])
            for i, k in enumerate(_SPELLBOOK_SCROLL_KINDS)
            if SCROLL_DEFAULT_PROBS_TOTAL[i] > 0]
    order: List[str] = []
    while pool:
        kinds = [k for k, _ in pool]
        weights = [w for _, w in pool]
        pick = _random.choices(kinds, weights=weights, k=1)[0]
        order.append(pick)
        pool = [(k, w) for k, w in pool if k != pick]
    order = [k for k in order if k != "scroll_of_transmutation"]
    return order


class UnstableSpellbook(Artifact):
    kind: Literal["unstable_spellbook"] = "unstable_spellbook"
    name: str = "Unstable Spellbook"
    charge: int = 2               # floor(level*0.6)+2, starts full
    charge_cap: int = 2
    level_cap: ClassVar[int] = 10
    exp: int = 0
    scroll_index: List[str] = Field(default_factory=list)
    initialized: bool = False     # guards one-time index build across reloads
    _recharge_accum: float = 0.0
    DESC: ClassVar[str] = "A spellbook crackling with unstable magic. It slowly recharges; read it to unleash a random scroll, empowering the ones it has learned into their exotic forms."

    def model_post_init(self, __context) -> None:
        if not self.initialized:
            self.scroll_index = _build_spellbook_index()
            self.initialized = True

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if player is None or not player.belongings.is_equipped(self.id) or self.cursed:
            return base
        acts: List[str] = []
        if getattr(player, "_pending_book_item_id", None) == self.id:
            acts.append(Action.BOOK_READ_RESOLVE)
        if self.charge >= 1:
            acts.append(Action.BOOK_READ)
        if self.level < self.level_cap and self._has_infusable_scroll(player):
            acts.append(Action.BOOK_INFUSE)
        return acts + base

    def _has_infusable_scroll(self, player: "Player") -> bool:
        # SPD only accepts a scroll matching the front two of the index.
        front = self.scroll_index[:2]
        for it in player.belongings.all_items():
            if getattr(it, "kind", "") in front and it.level_known:
                return True
        return False

    def default_action(self) -> Optional[str]:
        return Action.BOOK_READ

    def on_upgrade(self) -> None:
        self.charge_cap = int(self.level * 0.6) + 2
        while self.scroll_index and len(self.scroll_index) > (self.level_cap - 1 - self.level):
            self.scroll_index.pop(0)

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        lines = super()._info_lines(player)
        lines.append(f"Holds {self.charge}/{self.charge_cap} charges.")
        return lines


class Petal(ItemBase):
    kind: Literal["petal"] = "petal"
    name: str = "Petal"
    type: str = "misc"
    category: ClassVar[str] = ItemCategory.MISC
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A dried rose petal. It can upgrade a Dried Rose artifact."
