# Copyright (C) 2026 ArtemNikov
#
from __future__ import annotations

import uuid as _uuid
import random as _random
from typing import Annotated, ClassVar, Literal, Optional, List, Dict, Tuple, Union

from pydantic import BaseModel, Field, computed_field, model_validator, SerializeAsAny

from app.engine.entities.buffs import Buff, add_buff, remove_buff, has_buff, get_buff
from app.engine.entities.subclasses import SubclassInfo, TalentInfo, Talent
from app.engine.entities.weapons.weapon_defs import WEAPON_DEFS

from app.engine.entities.base import *  # noqa: F401,F403


class Gold(ItemBase):
    kind: Literal["gold"] = "gold"
    type: str = "gold"
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A pile of gold coins. Spend it at shops scattered through the dungeon."

    def do_pickup(self, game: Any, player: Any, floor: Any, item_id: str) -> bool:
        player.gold += self.quantity
        del floor.items[item_id]
        game.add_event("PICKUP_GOLD", {"player": player.id, "amount": self.quantity}, floor_id=player.floor_id)
        return True


class Food(ItemBase):
    kind: Literal["food"] = "food"
    type: str = "food"
    stackable: ClassVar[bool] = True
    energy: int = 300  # Hunger.HUNGRY
    DESC: ClassVar[str] = "Edible provisions. Eat it to stave off hunger."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.EAT, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.EAT

    def value(self, identified: bool = False) -> int:
        return 10 * self.quantity


class Key(ItemBase):
    kind: Literal["key"] = "key"
    type: str = "key"
    key_id: str = ""
    DESC: ClassVar[str] = "A key that unlocks a matching door or chest somewhere on this floor."

    def do_pickup(self, game: Any, player: Any, floor: Any, item_id: str) -> bool:
        player.add_key(self.key_id, player.floor_id, self.name)
        del floor.items[item_id]
        game.add_event("PICKUP_KEY", {"player": player.id, "key_id": self.key_id, "name": self.name}, floor_id=player.floor_id)
        return True


class KeyRecord(BaseModel):
    """A held key, tracked outside the bag (mirrors SPD's Notes.KeyRecord).

    Uniqueness is (key_id, depth): a key only unlocks doors on the floor it
    was found on, so two records with the same key_id but different depth
    are tracked separately.
    """
    key_id: str
    depth: int
    quantity: int = 1
    name: str = ""


class TenguMask(ItemBase):
    kind: Literal["tengu_mask"] = "tengu_mask"
    name: str = "Tengu's Mask"
    type: str = "misc"
    unique: bool = True
    DESC: ClassVar[str] = "The mask of the infamous Tengu assassin. Wearing it grants the power to choose a subclass path."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.WEAR, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.WEAR


class ArcaneStylus(ItemBase):
    kind: Literal["arcane_stylus"] = "arcane_stylus"
    name: str = "Arcane Stylus"
    type: str = "stylus"
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A stylus enchanted with magical energy. Use it to inscribe a random glyph onto a piece of armor."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        from typing import List as _List
        acts: _List[str] = [Action.THROW, Action.DROP]
        if player is not None:
            has_armor = any(isinstance(it, Armor) for it in player.belongings.all_items() if it.id != self.id)
            if has_armor:
                acts.insert(0, Action.INSCRIBE)
        return acts

    def default_action(self) -> Optional[str]:
        return Action.INSCRIBE


class MagicalInfusion(ItemBase):
    kind: Literal["magical_infusion"] = "magical_infusion"
    name: str = "Magical Infusion"
    type: str = "spell"
    unique: bool = True
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A magical infusion that upgrades a weapon or armor by one level. If the item already has an enchantment or glyph, it is preserved."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.USE, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.USE

    def value(self, identified: bool = False) -> int:
        return 60 * self.quantity


class KingsCrown(ItemBase):
    kind: Literal["kings_crown"] = "kings_crown"
    name: str = "King's Crown"
    type: str = "misc"
    unique: bool = True
    DESC: ClassVar[str] = "A crown taken from a fallen king. Wearing it while armor is equipped grants the power to imbue that armor with a special ability."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.WEAR, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.WEAR

class Throwable(ItemBase):
    kind: Literal["throwable"] = "throwable"
    type: str = "throwable"
    throw_behavior: str = "missile"
    stackable: ClassVar[bool] = True
    damage: int = 1
    range: int = 5
    projectile_type: str = "users_projectile"
    DESC: ClassVar[str] = "A thrown item. Hurl it at a target to deal damage."

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW


class Stone(Throwable):
    kind: Literal["stone"] = "stone"
    name: str = "Stone"
    damage: int = 1
    range: int = 5
    projectile_type: str = "stone"

    def value(self, identified: bool = False) -> int:
        return round(2.5 * self.quantity)


class Boomerang(Throwable):
    kind: Literal["boomerang"] = "boomerang"
    name: str = "Boomerang"
    damage: int = 3
    range: int = 6
    projectile_type: str = "boomerang"

    def value(self, identified: bool = False) -> int:
        return 20 * self.quantity


class ThrowableDagger(Throwable):
    kind: Literal["throwable_dagger"] = "throwable_dagger"
    name: str = "Throwable Dagger"
    damage: int = 4
    range: int = 4
    projectile_type: str = "dagger"

    def value(self, identified: bool = False) -> int:
        return 5 * self.quantity


_PLANT_TYPE_NAMES: Dict[str, str] = {
    "sungrass": "Sungrass Seed",
    "earthroot": "Earthroot Seed",
    "firebloom": "Firebloom Seed",
    "icecap": "Icecap Seed",
    "sorrowmoss": "Sorrowmoss Seed",
    "swiftthistle": "Swiftthistle Seed",
    "blindweed": "Blindweed Seed",
    "stormvine": "Stormvine Seed",
    "fadeleaf": "Fadeleaf Seed",
    "mageroyal": "Mageroyal Seed",
    "starflower": "Starflower Seed",
    "rotberry": "Rotberry Seed",
}

_PLANT_ALIASES: Dict[str, str] = {
    "dreamfoil": "mageroyal",
    "starwort": "starflower",
    "swifthistle": "swiftthistle",
}

STANDARD_SEEDS: Tuple[str, ...] = tuple(k for k in _PLANT_TYPE_NAMES if k != "rotberry")

SEED_DESC_TEMPLATE: str = "Throw this seed to the place where you want to grow a plant.\n\n{}"

PLANT_DESCS: Dict[str, str] = {
    "sungrass": "Sungrass is renowned for its sap's slow but effective healing properties.",
    "firebloom": "When something touches a firebloom, it bursts into flames.",
    "icecap": "Upon being touched, an icecap lets out a puff of freezing pollen. The freezing effect is much stronger if the environment is wet.",
    "sorrowmoss": "A sorrowmoss is a flower (not a moss) with razor-sharp petals, coated with a deadly venom.",
    "swiftthistle": "When trampled, swiftthistle will briefly accelerate the flow of time around it, allowing the trampler to perform several actions instantly.",
    "blindweed": "Upon being touched a blindweed perishes in a bright flash of light. The flash is strong enough to disorient for several seconds.",
    "earthroot": "When a creature touches an earthroot, its roots create a kind of immobile natural armor around it.",
    "stormvine": "Gravity affects the stormvine plant strangely, allowing its whispy blue tendrils to 'hang' on the air. Anything caught in the vine is affected by this, and becomes disoriented.",
    "fadeleaf": "Touching a fadeleaf will teleport any creature to a random place on the current level.",
    "mageroyal": "The mageroyal's prickly flowers contain a chemical which is known for its properties as a strong neutralizing agent. Anything that steps in this plant will be cleansed of many negative effects.",
    "starflower": "A rare plant, starflower is said to grant holy power to whomever touches it.",
    "rotberry": "The berries of a young rotberry shrub taste like sweet, sweet death. Over a few years, this rotberry shrub will grow into another rot heart. When trampled, a young rotberry will produce a small puff of toxic gas.",
}

WARDEN_PLANT_DESCS: Dict[str, str] = {
    "sungrass": "_The Warden_ can receive healing from trampled sungrass even if she moves away from it.",
    "firebloom": "When she tramples a firebloom, _the Warden_ will be briefly imbued with flame instead of being harmed.",
    "icecap": "When she tramples an icecap, _the Warden_ will be briefly imbued with frost instead of being harmed.",
    "sorrowmoss": "When she tramples a sorrowmoss, _the Warden_ will be briefly imbued with toxin instead of being harmed.",
    "swiftthistle": "In addition to gaining instantaneous actions, _the Warden_ will also get a brief haste boost when trampling swiftthistle.",
    "blindweed": "_The Warden_ will channel a blindweed's energy into a temporary shroud of invisibility, instead of being disoriented.",
    "earthroot": "The roots of an earthroot plant will move with _the Warden_, providing her mobile barkskin armor.",
    "stormvine": "_The Warden_ is able to control the gravitational effect of stormvine, and will briefly levitate when she tramples one.",
    "fadeleaf": "The teleportation effect of fadeleaf is more potent for _the Warden_, teleporting her back to the end of the previous dungeon level.",
    "mageroyal": "In addition to the neutralizing effect, _the Warden_ will become temporarily immune to all area-bound effects when stepping on mageroyal.",
    "starflower": "In addition to being blessed, _the Warden_ will gain a significant amount of wand recharging when she tramples a starflower.",
    "rotberry": "Normally a rotberry bush only produces a little gas when trampled, but _the Warden_ is able to harness energy from it to temporarily boost her strength!",
}


class Seed(ItemBase):
    kind: Literal["seed"] = "seed"
    name: str = "Seed"
    type: str = "seed"
    throw_behavior: str = "seed"
    stackable: ClassVar[bool] = True
    plant_type: str = "sungrass"
    DESC: ClassVar[str] = "Throw this seed to the place where you want to grow a plant."

    def description(self, player: Optional["Player"] = None) -> str:
        pt = _PLANT_ALIASES.get(self.plant_type, self.plant_type)
        plant_desc = PLANT_DESCS.get(pt)
        if not plant_desc:
            return self.DESC
        if player is not None:
            subclass_info = getattr(player, "subclass_info", None)
            if subclass_info and getattr(subclass_info, "subclass", None) == "warden":
                warden_desc = WARDEN_PLANT_DESCS.get(pt)
                if warden_desc:
                    plant_desc = f"{plant_desc}\n\n{warden_desc}"
        return SEED_DESC_TEMPLATE.format(plant_desc)

    @model_validator(mode="before")
    @classmethod
    def _normalize_seed(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_pt = data.get("plant_type")
            if not raw_pt and (raw_name := data.get("name")):
                candidate = raw_name.lower().removesuffix(" seed").strip()
                if candidate in _PLANT_TYPE_NAMES or candidate in _PLANT_ALIASES:
                    raw_pt = candidate
            if raw_pt:
                normalized = raw_pt.lower()
                data["plant_type"] = _PLANT_ALIASES.get(normalized, normalized)

            effective_pt = data.get("plant_type") or getattr(cls, "plant_type", "sungrass")
            if not data.get("name"):
                default_name = getattr(cls, "name", "Seed")
                if default_name in ("Seed", "seed", effective_pt):
                    data["name"] = _PLANT_TYPE_NAMES.get(effective_pt, f"{effective_pt.capitalize()} Seed")
            elif data.get("name") in ("Seed", "seed", effective_pt):
                data["name"] = _PLANT_TYPE_NAMES.get(effective_pt, f"{effective_pt.capitalize()} Seed")
        return data

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return [Action.PLANT, Action.THROW, Action.DROP]

    def default_action(self) -> Optional[str]:
        return Action.THROW

    def is_similar(self, other: "ItemBase") -> bool:
        return (
            type(self) is type(other)
            and not self.is_bag
            and self.level == other.level
            and getattr(self, "plant_type", "") == getattr(other, "plant_type", "")
        )

    def value(self, identified: bool = False) -> int:
        if self.plant_type in ("starflower", "rotberry"):
            return 30 * self.quantity
        return 10 * self.quantity


class Blandfruit(Food):
    kind: Literal["blandfruit"] = "blandfruit"
    name: str = "Blandfruit"
    energy: int = 450  # Full food value when cooked
    potion_type: Optional[str] = None  # None = raw, or potion kind string
    DESC: ClassVar[str] = (
        "A strange, tasteless fruit. It is unusable raw, but can be cooked at an alchemy pot with a seed to imbue it with magical effects."
    )

    def value(self, identified: bool = False) -> int:
        return 20 * self.quantity

    def dynamic_name(self) -> str:
        names = {
            "health": "Sunfruit",
            "strength": "Rotfruit",
            "paralytic_gas": "Earthfruit",
            "invisibility": "Blindfruit",
            "liquid_flame": "Firefruit",
            "frost": "Icefruit",
            "mind_vision": "Fadefruit",
            "toxic_gas": "Sorrowfruit",
            "levitation": "Stormfruit",
            "purity": "Dreamfruit",
            "experience": "Starfruit",
            "haste": "Swiftfruit",
        }
        if self.potion_type in names:
            return names[self.potion_type]
        return self.name


class MysteryMeat(Food):
    kind: Literal["mystery_meat"] = "mystery_meat"
    name: str = "Mystery Meat"
    energy: int = 150  # Hunger.HUNGRY / 2
    DESC: ClassVar[str] = "Raw meat from a defeated creature. Eat it to restore some health — if you dare."


class Dewdrop(ItemBase):
    kind: Literal["dewdrop"] = "dewdrop"
    name: str = "Dewdrop"
    type: str = "dewdrop"
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A drop of magical dew. It radiates healing energy."

    def do_pickup(self, game: Any, player: Any, floor: Any, item_id: str) -> bool:
        return game._pickup_dewdrop(player, floor, player.floor_id, item_id, self)


class EnergyCrystal(ItemBase):
    # SPD EnergyCrystal: quantity == energy amount. Never sits in a bag — on
    # pickup it converts straight into the player's alchemical energy
    # (Gold/Dewdrop pickup pattern).
    kind: Literal["energy_crystal"] = "energy_crystal"
    name: str = "Energy Crystal"
    type: str = "energy_crystal"
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A small crystal of pure alchemical energy. It is absorbed the moment it is picked up."

    def do_pickup(self, game: Any, player: Any, floor: Any, item_id: str) -> bool:
        player.energy += self.quantity
        del floor.items[item_id]
        game.add_event("PICKUP_ENERGY", {"player": player.id, "amount": self.quantity}, floor_id=player.floor_id)
        return True


class Waterskin(ItemBase):
    kind: Literal["waterskin"] = "waterskin"
    name: str = "Waterskin"
    type: str = "waterskin"
    stackable: ClassVar[bool] = False
    unique: bool = True
    MAX_VOLUME: ClassVar[int] = 20
    volume: int = 0
    DESC: ClassVar[str] = (
        "A leather pouch that can hold magical dew. Drinking from it restores health."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if self.volume > 0:
            return [Action.DRINK] + base
        return base

    def default_action(self) -> Optional[str]:
        return Action.DRINK if self.volume > 0 else None

    def value(self, identified: bool = False) -> int:
        return 0

    def is_full(self) -> bool:
        return self.volume >= self.MAX_VOLUME

    def _info_lines(self, player: Optional["Player"] = None) -> List[str]:
        if self.volume == 0:
            return ["It is currently empty."]
        return [f"It contains {self.volume}/{self.MAX_VOLUME} drops of dew."]


class Amulet(ItemBase):
    kind: Literal["amulet"] = "amulet"
    name: str = "Amulet of Yendor"
    type: str = "amulet"
    stackable: ClassVar[bool] = False
    unique: bool = True
    DESC: ClassVar[str] = "The legendary Amulet of Yendor. Carry it to the surface to win."


class Berry(Food):
    kind: Literal["berry"] = "berry"
    name: str = "Berry"
    energy: int = 100
    DESC: ClassVar[str] = "A sweet berry. Restores a small amount of food."


class SmallRation(Food):
    kind: Literal["small_ration"] = "small_ration"
    name: str = "Small Ration"
    energy: int = 150
    DESC: ClassVar[str] = "A small bundle of provisions. Better than nothing."


class Ration(Food):
    kind: Literal["ration"] = "ration"
    name: str = "Ration"
    energy: int = 300
    DESC: ClassVar[str] = "A satisfying portion of food. Keeps hunger at bay for a good while."


class Pasty(Food):
    kind: Literal["pasty"] = "pasty"
    name: str = "Pasty"
    energy: int = 450
    DESC: ClassVar[str] = "A hearty pastry stuffed with vegetables and meat. Very filling."


class ChargrilledMeat(Food):
    kind: Literal["chargrilled_meat"] = "chargrilled_meat"
    name: str = "Chargrilled Meat"
    energy: int = 150  # Hunger.HUNGRY / 2
    DESC: ClassVar[str] = "Properly cooked mystery meat. Smells delicious."


class FrozenCarpaccio(Food):
    kind: Literal["frozen_carpaccio"] = "frozen_carpaccio"
    name: str = "Frozen Carpaccio"
    energy: int = 150  # Hunger.HUNGRY / 2
    DESC: ClassVar[str] = "Raw meat that has been frozen solid. Can be defrosted by cooking it."


class PhantomMeat(Food):
    kind: Literal["phantom_meat"] = "phantom_meat"
    name: str = "Phantom Meat"
    energy: int = 450  # Hunger.STARVING
    DESC: ClassVar[str] = "Spectral meat from a phantom creature. It fills you with an otherworldly nourishment."


class SupplyRation(Food):
    kind: Literal["supply_ration"] = "supply_ration"
    name: str = "Supply Ration"
    energy: int = 200  # 2 * Hunger.HUNGRY / 3
    DESC: ClassVar[str] = "A military-issue ration. Compact but nutritious, and comes with a bit of healing."


class StewedMeat(Food):
    kind: Literal["stewed_meat"] = "stewed_meat"
    name: str = "Stewed Meat"
    energy: int = 150
    DESC: ClassVar[str] = "Mystery meat, gently stewed at an alchemy pot. Safe to eat, if not very filling."

    def value(self, identified: bool = False) -> int:
        return 8 * self.quantity


class MeatPie(Food):
    kind: Literal["meat_pie"] = "meat_pie"
    name: str = "Meat Pie"
    energy: int = 900
    DESC: ClassVar[str] = "A delicious pie cooked from meat, a pasty and a ration. Extremely filling."

    def value(self, identified: bool = False) -> int:
        return 40 * self.quantity


class GooBlob(ItemBase):
    # Goo's death drop (SPD GooBlob): stackable alchemy reagent (see
    # app.engine.alchemy).
    kind: Literal["goo_blob"] = "goo_blob"
    name: str = "Goo Blob"
    type: str = "misc"
    stackable: ClassVar[bool] = True
    DESC: ClassVar[str] = "A blob of black ooze left behind by Goo. Can be combined with a Health Potion at an Alchemy Pot."

    def value(self, identified: bool = False) -> int:
        return 30 * self.quantity


class CorpseDust(ItemBase):
    # Wandmaker quest item, Corpse Dust variant (SPD items.quest.CorpseDust):
    # unique, always identified/cursed-known, and -- unlike normal items --
    # can't be dropped or thrown (actions() below mirrors Java's actions()
    # returning an empty list). While held it attaches a `dust_ghost_spawner`
    # buff that periodically summons DustWraiths near the holder (see
    # movement.py's pickup handler, tick.py's per-player buff loop, and
    # wandmaker_quest.py for the DustWraith mob itself). Only removed via
    # world.py's wandmaker_claim_reward (no generic on-detach hook exists in
    # this engine for non-equippable items, so the dispel lives there).
    kind: Literal["corpse_dust"] = "corpse_dust"
    name: str = "dust of the corpse"
    type: str = "misc"
    unique: bool = True
    cursed: bool = True
    cursed_known: bool = True
    level_known: bool = True
    DESC: ClassVar[str] = (
        "A handful of grim, gritty dust that seems to writhe in your grasp. "
        "You feel it stirring things that would rather stay buried."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return []

    def do_pickup(self, game: Any, player: Any, floor: Any, item_id: str) -> bool:
        if super().do_pickup(game, player, floor, item_id):
            player.add_buff("dust_ghost_spawner", duration=999999.0)
            return True
        return False


class DwarfToken(ItemBase):
    # Imp quest reward token (SPD items.quest.DwarfToken): stackable, always
    # identified, dropped by Golems/Monks once the quest is given. Not sellable.
    kind: Literal["dwarf_token"] = "dwarf_token"
    name: str = "Dwarf Token"
    type: str = "misc"
    stackable: ClassVar[bool] = True
    level_known: bool = True
    cursed_known: bool = True
    DESC: ClassVar[str] = "A small clay token, traded by dwarves of the Imp's homeland."


class Ankh(ItemBase):
    # Resurrection item (SPD items.Ankh): auto-triggers on death. Blessed
    # variant requires full Waterskin and grants instant revive at 25% HP
    # (Easy: 75%) with all items preserved. Unblessed lets the player pick
    # 2 items to keep; rest goes into a LostBackpack on the ground.
    kind: Literal["ankh"] = "ankh"
    name: str = "Ankh"
    type: str = "ankh"
    stackable: ClassVar[bool] = False
    unique: bool = True
    cursed_known: bool = True
    level_known: bool = True
    blessed: bool = False
    # bones=True: can appear as cross-run remains (SPD Ankh.bones=true)
    bones: bool = True
    DESC: ClassVar[str] = (
        "An ancient artifact of resurrection. When you die, this will "
        "bring you back to life. It can be blessed using a full waterskin, "
        "which will preserve all of your items on resurrection."
    )
    DESC_BLESSED: ClassVar[str] = (
        "An ancient artifact of resurrection, blessed with sacred waters. "
        "When you die, it will restore you to life with all of your items intact."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        base = super().actions(player)
        if not self.blessed and player is not None:
            for item in player.belongings.all_items():
                if isinstance(item, Waterskin) and item.is_full():
                    return [Action.BLESS] + base
        return base

    def default_action(self) -> Optional[str]:
        return None

    def description(self, player: Optional["Player"] = None) -> str:
        if self.blessed:
            return self.DESC_BLESSED
        return self.DESC

    def value(self, identified: bool = False) -> int:
        return 50 * self.quantity


class LostBackpack(ItemBase):
    # Drop container placed at death position when player resurrects via
    # unblessed ankh. Contains all items not chosen by the player. Only
    # the owning player can pick it up.
    kind: Literal["lost_backpack"] = "lost_backpack"
    name: str = "Lost Backpack"
    type: str = "lost_backpack"
    unique: bool = True
    cursed_known: bool = True
    level_known: bool = True
    # Items stored inside the backpack (serialized on the wire).
    stored_items: List["AnyItem"] = Field(default_factory=list)
    # item_id -> quickslot index, for items that were quickslotted at death.
    quickslot_map: Dict[str, int] = Field(default_factory=dict)
    # Only this player can pick up the backpack.
    owner_id: str = ""
    DESC: ClassVar[str] = (
        "Your lost belongings. Step on them to recover everything."
    )

    def actions(self, player: Optional["Player"] = None) -> List[str]:
        return []

    def default_action(self) -> Optional[str]:
        return None

    def do_pickup(self, game: Any, player: Any, floor: Any, item_id: str) -> bool:
        if self.owner_id == player.id:
            game._recover_lost_backpack(player, self)
            del floor.items[item_id]
            game.add_event("PICKUP", {
                "player": player.id, "item": "Lost Backpack",
                "x": player.pos.x, "y": player.pos.y,
                "item_type": "lost_backpack",
            }, floor_id=player.floor_id)
            return True
        return False

    def value(self, identified: bool = False) -> int:
        return 0
