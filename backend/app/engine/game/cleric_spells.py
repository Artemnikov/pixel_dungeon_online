# Copyright (C) 2026 ArtemNikov
#
"""Cleric spell casting system, Holy Tome spells, mechanics, and presentation."""

from abc import ABC, abstractmethod
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Position
from app.engine.entities.buffs import add_buff
from app.engine.entities.items.artifacts import HolyTome
from app.engine.entities.player import CharacterClass, Mob, Player
from app.engine.game.cleric_subclass import get_cleric_subclass_strategy
from app.engine.game.cleric_targets import (
    HARMFUL_DEBUFFS,
    duplicate_to_life_linked_ally,
    resolve_spell_target,
)
from app.engine.game.terrain_effects import press_cell
from app.engine.systems.ballistica import ballistica_trace


# ===========================================================================
# Recall Inscription cost table / dispatch (data-driven, no if/elif ladder)
# ===========================================================================

_RUNESTONE_PREMIUM_COST: Dict[str, float] = {
    "stone_of_augmentation": 4.0,
    "stone_of_enchantment": 4.0,
}
_SCROLL_COST_OVERRIDES: Dict[str, float] = {
    "scroll_of_metamorphosis": 8.0,
    "scroll_of_enchantment": 8.0,
    "scroll_of_transmutation": 6.0,
}
_SCROLL_EXOTIC_PREFIXES: Tuple[str, ...] = ("scroll_of_psionic", "scroll_of_siren")


def _inscription_recall_cost(inscr: Optional[Dict[str, Any]]) -> float:
    if not inscr:
        return 3.0
    itype = inscr.get("type", "scroll")
    ikind = inscr.get("kind", "")
    if itype == "runestone":
        return _RUNESTONE_PREMIUM_COST.get(ikind, 2.0)
    if itype == "scroll":
        if ikind in _SCROLL_COST_OVERRIDES:
            return _SCROLL_COST_OVERRIDES[ikind]
        if "exotic" in ikind or ikind.startswith(_SCROLL_EXOTIC_PREFIXES):
            return 4.0
    return 3.0


def _recall_scroll(game: Any, player: Player, inscr: Dict[str, Any], ikind: str, tx: Optional[int], ty: Optional[int]) -> None:
    from app.engine.entities.items.scrolls import (
        ScrollOfIdentify, ScrollOfMagicMapping, ScrollOfRecharging,
        ScrollOfRemoveCurse, ScrollOfTeleportation, ScrollOfTerror,
        ScrollOfLullaby, ScrollOfRage, ScrollOfRetribution,
        ScrollOfTransmutation, ScrollOfMirrorImage,
    )
    from app.engine.entities.scroll_actions import action_read
    scroll_map = {
        "scroll_of_identify": ScrollOfIdentify,
        "scroll_of_magic_mapping": ScrollOfMagicMapping,
        "scroll_of_recharging": ScrollOfRecharging,
        "scroll_of_remove_curse": ScrollOfRemoveCurse,
        "scroll_of_teleportation": ScrollOfTeleportation,
        "scroll_of_terror": ScrollOfTerror,
        "scroll_of_lullaby": ScrollOfLullaby,
        "scroll_of_rage": ScrollOfRage,
        "scroll_of_retribution": ScrollOfRetribution,
        "scroll_of_transmutation": ScrollOfTransmutation,
        "scroll_of_mirror_image": ScrollOfMirrorImage,
    }
    cls = scroll_map.get(ikind, ScrollOfRecharging)
    dummy_scroll = cls(id=f"recalled_{ikind}")
    action_read(game, player, dummy_scroll)


def _recall_runestone(game: Any, player: Player, inscr: Dict[str, Any], ikind: str, tx: Optional[int], ty: Optional[int]) -> None:
    from app.engine.entities.runestone_actions import action_throw_runestone
    from app.engine.entities.runestones import (
        Runestone, StoneOfAggression, StoneOfBlast, StoneOfBlink,
        StoneOfClairvoyance, StoneOfDeepSleep, StoneOfFear, StoneOfFlock,
        StoneOfShock,
    )
    recall_classes = {
        "stone_of_blast": StoneOfBlast,
        "stone_of_blink": StoneOfBlink,
        "stone_of_deep_sleep": StoneOfDeepSleep,
        "stone_of_clairvoyance": StoneOfClairvoyance,
        "stone_of_aggression": StoneOfAggression,
        "stone_of_flock": StoneOfFlock,
        "stone_of_shock": StoneOfShock,
        "stone_of_fear": StoneOfFear,
    }
    cls = recall_classes.get(ikind, Runestone)
    dummy_stone = cls(id=f"recalled_{ikind}")
    target_x = tx if tx is not None else player.pos.x
    target_y = ty if ty is not None else player.pos.y
    action_throw_runestone(game, player, dummy_stone, target_x, target_y)


_RECALL_HANDLERS: Dict[str, Any] = {
    "scroll": _recall_scroll,
    "runestone": _recall_runestone,
}


def _resolve_target_mob(game: Any, player: Player, floor: Any, tx: Optional[int] = None, ty: Optional[int] = None) -> Optional[Mob]:
    if tx is not None and ty is not None:
        for mob in floor.mobs.values():
            if mob.is_alive and mob.faction != player.faction and mob.pos.x == tx and mob.pos.y == ty:
                return mob
        return None
    visible_mobs = [m for m in game._mobs_in_fov(player, floor, player.floor_id) if m.faction != player.faction and m.is_alive]
    if visible_mobs:
        visible_mobs.sort(key=lambda m: (m.pos.x - player.pos.x) ** 2 + (m.pos.y - player.pos.y) ** 2)
        return visible_mobs[0]
    return None


class ClericSpell(ABC):
    id: str = ""
    name: str = ""
    tier: int = 1
    base_cost: float = 1.0
    targeting: str = "none"
    icon: str = "✨"
    desc: str = ""
    cast_sound: Optional[str] = None
    cast_animation: Optional[str] = None
    cast_glow: Optional[str] = None

    def get_cost(self, player: Player) -> float:
        return self.base_cost

    def present_cast(self, game: Any, player: Player) -> None:
        """Emit the client presentation events for this spell's cast."""
        if self.cast_sound:
            game.add_event(
                "PLAY_SOUND",
                {"sound": self.cast_sound, "x": player.pos.x, "y": player.pos.y},
                floor_id=player.floor_id,
            )
        if self.cast_animation:
            game.add_event(
                "PLAY_ANIMATION",
                {
                    "player": player.id,
                    "animation": self.cast_animation,
                    "glow": self.cast_glow,
                    "spell": self.id,
                    "x": player.pos.x,
                    "y": player.pos.y,
                },
                floor_id=player.floor_id,
            )

    def is_unlocked(self, player: Player) -> bool:
        return True

    def can_cast(self, player: Player, tome: Optional[HolyTome] = None) -> bool:
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return False
        if player.has_buff("magic_immune"):
            return False
        if not self.is_unlocked(player):
            return False
        if tome is not None and tome.charge < self.get_cost(player):
            return False
        return True

    def on_spell_cast(self, game: Any, player: Player, tome: HolyTome, cost: float) -> None:
        player.remove_buff("invisibility")
        player.remove_buff("shadow_meld")

        # Satiated Spells T1: consuming tracker grants barrier (and duplicates to life-linked ally)
        if player.talent_info.has("satiated_spells") and player.has_buff("satiated_spells_tracker"):
            pts = player.talent_info.level("satiated_spells")
            shield_amount = 1 + 2 * pts
            player.add_shield("barrier", shield_amount, priority=1, decay=0)
            player.add_buff("barrier", duration=30.0, level=shield_amount)
            player.remove_buff("satiated_spells_tracker")
            duplicate_to_life_linked_ally(
                game, player, lambda ally: (
                    ally.add_shield("barrier", shield_amount, priority=1, decay=0),
                    ally.add_buff("barrier", duration=30.0, level=shield_amount),
                )
            )

        tome.spend_charge(cost, hero_lvl=player.level)

        # Paladin engine: casting other spells extends active Holy Weapon and Holy Ward
        if get_cleric_subclass_strategy(player).extends_auras_on_cast(player) and cost > 0:
            ext_turns = 10.0 * cost
            if self.id != "holy_weapon" and player.has_buff("holy_weapon"):
                b = player.get_buff("holy_weapon")
                if b:
                    b.remaining = min(100.0, b.remaining + ext_turns)
            if self.id != "holy_ward" and player.has_buff("holy_ward"):
                b = player.get_buff("holy_ward")
                if b:
                    b.remaining = min(100.0, b.remaining + ext_turns)

        # Ascended Form: spell cast counter + shield bonus
        if getattr(player, "ascended_form_active", False):
            player.ascended_form_casts = getattr(player, "ascended_form_casts", 0) + 1
            if cost > 0:
                shield_bonus = round(10.0 * cost)
                player.add_buff("shielded", duration=30.0, level=shield_bonus)

        game.add_event(
            "SPELL_CAST",
            {"player": player.id, "spell": self.id, "cost": cost},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

        self.present_cast(game, player)

    @abstractmethod
    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pass


# ===========================================================================
# Inherent & Tier 1 Spells
# ===========================================================================

class GuidingLightSpell(ClericSpell):
    id = "guiding_light"
    name = "Guiding Light"
    tier = 1
    base_cost = 1.0
    targeting = "mob"
    icon = "🕯️"
    desc = "Fires a holy bolt dealing 2-8 magic damage and illuminating the target."

    def get_cost(self, player: Player) -> float:
        if get_cleric_subclass_strategy(player).guiding_light_is_free(player):
            return 0.0
        return self.base_cost

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        if tx is None or ty is None:
            auto_mob = _resolve_target_mob(game, player, floor)
            if auto_mob is None:
                return False
            tx, ty = auto_mob.pos.x, auto_mob.pos.y

        collision_x, collision_y = ballistica_trace(
            player.pos.x, player.pos.y, tx, ty,
            floor.flags, floor.width, floor.height,
            list(game._players_on_floor(player.floor_id)),
            list(floor.mobs.values()),
            player.id,
        )

        if collision_x == player.pos.x and collision_y == player.pos.y:
            return False

        cost = self.get_cost(player)
        if cost == 0.0:
            get_cleric_subclass_strategy(player).mark_guiding_light_used(player)

        game.add_event(
            "RANGED_ATTACK",
            {
                "source": player.id,
                "x": player.pos.x,
                "y": player.pos.y,
                "target_x": collision_x,
                "target_y": collision_y,
                "projectile": "light_missile",
                "crit": False,
                "grim_proc": False,
                "beam_type": None,
                "sound": "ATTACK_MAGIC",
                "is_wand": True,
                "is_bow": False,
                "next_attack_in_ms": None,
            },
            floor_id=player.floor_id,
        )

        target_mob = None
        for mob in floor.mobs.values():
            if mob.is_alive and mob.faction != player.faction and mob.pos.x == collision_x and mob.pos.y == collision_y:
                target_mob = mob
                break

        if target_mob is not None:
            dmg = random.randint(2, 8)
            dealt = target_mob.take_damage(dmg)
            game.add_event(
                "DAMAGE",
                {
                    "target": target_mob.id,
                    "amount": dealt,
                    "holy": True,
                    "projectile": "light_missile",
                    "splash_count": 3,
                },
                floor_id=player.floor_id,
            )

            if target_mob.is_alive:
                target_mob.add_buff("illuminated", duration=50.0)
                target_mob.add_buff("was_illuminated_tracker", duration=50.0)
            else:
                game._handle_kill_event(player, target_mob, floor)
        else:
            press_cell(floor, (collision_x, collision_y), trampler=player)

        return True


class HolyWeaponSpell(ClericSpell):
    id = "holy_weapon"
    name = "Holy Weapon"
    tier = 1
    base_cost = 2.0
    targeting = "none"
    icon = "⚔️"
    desc = "Imbues weapon attacks with holy power for 50 turns (+2 magic damage, +6 for Paladin)."
    cast_sound = "READ"
    cast_animation = "operate"
    cast_glow = "golden"

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        bonus = get_cleric_subclass_strategy(player).holy_weapon_bonus()
        player.add_buff("holy_weapon", duration=50.0, level=bonus)
        return True


class HolyWardSpell(ClericSpell):
    id = "holy_ward"
    name = "Holy Ward"
    tier = 1
    base_cost = 1.0
    targeting = "none"
    icon = "🛡️"
    desc = "Imbues armor with holy defense for 50 turns (+1 damage blocked, +3 for Paladin)."
    cast_sound = "READ"
    cast_animation = "operate"
    cast_glow = "golden"

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        bonus = get_cleric_subclass_strategy(player).holy_ward_bonus()
        player.add_buff("holy_ward", duration=50.0, level=bonus)
        return True


class HolyIntuitionSpell(ClericSpell):
    id = "holy_intuition"
    name = "Holy Intuition"
    tier = 1
    base_cost = 3.0
    targeting = "none"
    icon = "🔍"
    desc = "Reveals whether items in your backpack are cursed without equipping them."
    cast_sound = "READ"
    cast_animation = "read"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("holy_intuition")

    def get_cost(self, player: Player) -> float:
        pts = player.talent_info.level("holy_intuition")
        return max(1.0, float(4 - pts))

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        revealed_any = False
        for item in player.belongings.all_items():
            if hasattr(item, "cursed_known") and not getattr(item, "cursed_known", False):
                item.cursed_known = True
                revealed_any = True

        game.add_event("HOLY_INTUITION", {"player": player.id, "revealed": revealed_any}, floor_id=player.floor_id)
        return True


class ShieldOfLightSpell(ClericSpell):
    id = "shield_of_light"
    name = "Shield of Light"
    tier = 1
    base_cost = 1.0
    targeting = "mob"
    icon = "✨"
    desc = "Creates a ward absorbing incoming damage from a targeted enemy."
    cast_sound = "READ"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("shield_of_light")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        target_mob = _resolve_target_mob(game, player, floor, tx, ty)
        if target_mob is None or not target_mob.is_alive:
            return False

        pts = player.talent_info.level("shield_of_light")
        shield_power = 1 + pts
        buff = player.add_buff("shield_of_light_tracker", duration=5.0, level=shield_power)
        if buff:
            buff.source_id = target_mob.id
        return True


# ===========================================================================
# Tier 2 Spells
# ===========================================================================

class RecallInscriptionSpell(ClericSpell):
    id = "recall_inscription"
    name = "Recall Inscription"
    tier = 2
    base_cost = 3.0
    targeting = "none"
    icon = "📜"
    desc = "Repeats the effect of the last runestone or scroll used."
    cast_sound = "READ"
    cast_animation = "operate"
    cast_glow = "golden"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("recall_inscription")

    def get_cost(self, player: Player) -> float:
        return _inscription_recall_cost(getattr(player, "last_used_inscription", None))

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        inscr = getattr(player, "last_used_inscription", None)
        if not inscr:
            return False
        total_time = getattr(game, "total_time", 0.0)
        if total_time - inscr.get("time", 0.0) > inscr.get("duration", 300.0):
            player.last_used_inscription = None
            return False

        handler = _RECALL_HANDLERS.get(inscr.get("type", "scroll"))
        if handler is not None:
            handler(game, player, inscr, inscr.get("kind", ""), tx, ty)

        player.last_used_inscription = None
        game.add_event("RECALL_INSCRIPTION", {"player": player.id}, floor_id=player.floor_id)
        return True


class SunraySpell(ClericSpell):
    id = "sunray"
    name = "Sunray"
    tier = 2
    base_cost = 1.0
    targeting = "mob"
    icon = "☀️"
    desc = "Blasts an enemy for magic damage and blinds them (paralyzing if already blind)."
    cast_sound = "RAY"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("sunray")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        target_mob = _resolve_target_mob(game, player, floor, tx, ty)
        if target_mob is None or not target_mob.is_alive:
            return False

        pts = player.talent_info.level("sunray")
        min_dmg, max_dmg = (6, 12) if pts >= 2 else (4, 8)
        dur = 6.0 if pts >= 2 else 4.0

        is_unholy = target_mob.is_unholy
        dmg = max_dmg if is_unholy else random.randint(min_dmg, max_dmg)
        dealt = target_mob.take_damage(dmg)

        game.add_event(
            "RANGED_ATTACK",
            {
                "source": player.id,
                "x": player.pos.x,
                "y": player.pos.y,
                "target_x": target_mob.pos.x,
                "target_y": target_mob.pos.y,
                "projectile": None,
                "crit": False,
                "grim_proc": False,
                "beam_type": "sun_ray",
                "sound": "RAY",
                "is_wand": True,
                "is_bow": False,
                "next_attack_in_ms": None,
            },
            floor_id=player.floor_id,
        )

        game.add_event(
            "DAMAGE",
            {"target": target_mob.id, "amount": dealt, "holy": True, "splash_count": 5},
            floor_id=player.floor_id,
        )

        if target_mob.is_alive:
            if target_mob.has_buff("blindness") and target_mob.has_buff("sunray_recently_blinded_tracker"):
                target_mob.remove_buff("sunray_recently_blinded_tracker")
                target_mob.add_buff("paralysis", duration=dur)
            elif not target_mob.has_buff("sunray_used_tracker"):
                target_mob.add_buff("blindness", duration=dur)
                target_mob.add_buff("sunray_recently_blinded_tracker", duration=dur)
                target_mob.add_buff("sunray_used_tracker", duration=999999.0)

            get_cleric_subclass_strategy(player).illuminate(game, player, target_mob)
        else:
            game._handle_kill_event(player, target_mob, floor)

        return True


class DivineSenseSpell(ClericSpell):
    id = "divine_sense"
    name = "Divine Sense"
    tier = 2
    base_cost = 2.0
    targeting = "none"
    icon = "👁️"
    desc = "Grants Mind Vision in an 8-12 tile radius for 50 turns."
    cast_sound = "READ"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("divine_sense")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("divine_sense")
        rad = 12 if pts >= 2 else 8
        player.add_buff("mind_vision", duration=50.0, level=rad)
        return True


class BlessSpell(ClericSpell):
    id = "bless"
    name = "Bless"
    tier = 2
    base_cost = 1.0
    targeting = "ally_or_self"
    icon = "🙏"
    desc = "Blesses yourself with accuracy and shield, or an ally with Bless and healing."
    cast_sound = "TELEPORT"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("bless")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("bless")
        floor = game._get_or_create_floor(player.floor_id)
        target = resolve_spell_target(game, player, floor, tx, ty)
        target.apply_bless(game, player, pts)
        game.add_event("FLARE", {"x": player.pos.x, "y": player.pos.y, "color": "#FFFF00", "radius": 32, "rays": 6}, floor_id=player.floor_id)
        return True


# ===========================================================================
# Tier 3 Shared Spells
# ===========================================================================

class CleanseSpell(ClericSpell):
    id = "cleanse"
    name = "Cleanse"
    tier = 3
    base_cost = 2.0
    targeting = "none"
    icon = "🕊️"
    desc = "Cleanses all negative debuffs and grants barrier & debuff immunity."
    cast_sound = "READ"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("cleanse")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("cleanse")
        shield = 10 * pts
        dur_immune = 2.0 * (pts - 1) if pts >= 2 else 0.0

        player.cleanse(HARMFUL_DEBUFFS)
        player.add_shield("barrier", shield, priority=1, decay=0)
        player.add_buff("barrier", duration=30.0, level=shield)
        if dur_immune > 0:
            player.add_buff("debuff_immune", duration=dur_immune)

        floor = game._get_or_create_floor(player.floor_id)
        if hasattr(game, "_players_on_floor"):
            for other_p in game._players_on_floor(player.floor_id):
                if other_p.id != player.id and getattr(other_p, "is_alive", False):
                    other_p.cleanse(HARMFUL_DEBUFFS)
                    other_p.add_shield("barrier", shield, priority=1, decay=0)
                    other_p.add_buff("barrier", duration=30.0, level=shield)
                    if dur_immune > 0:
                        other_p.add_buff("debuff_immune", duration=dur_immune)

        for mob in list(game._mobs_in_fov(player, floor, player.floor_id)):
            if mob.is_alive and mob.faction == player.faction:
                for d in HARMFUL_DEBUFFS:
                    mob.remove_buff(d)
                mob.add_shield("barrier", shield, priority=1, decay=0)
                mob.add_buff("barrier", duration=30.0, level=shield)
                if dur_immune > 0:
                    mob.add_buff("debuff_immune", duration=dur_immune)

        duplicate_to_life_linked_ally(
            game, player, lambda ally: (
                [ally.remove_buff(d) for d in HARMFUL_DEBUFFS],
                ally.add_shield("barrier", shield, priority=1, decay=0),
                ally.add_buff("barrier", duration=30.0, level=shield),
                ally.add_buff("debuff_immune", duration=dur_immune) if dur_immune > 0 else None,
            )
        )

        game.add_event("FLARE", {"x": player.pos.x, "y": player.pos.y, "color": "#FF4CD2", "radius": 32, "rays": 6}, floor_id=player.floor_id)
        return True


# ===========================================================================
# Tier 3 Priest Spells
# ===========================================================================

class RadianceSpell(ClericSpell):
    id = "radiance"
    name = "Radiance"
    tier = 3
    base_cost = 2.0
    targeting = "none"
    icon = "🌟"
    desc = "Paralyzes visible enemies and detonates Illuminated targets."
    cast_sound = "BLAST"

    def is_unlocked(self, player: Player) -> bool:
        return get_cleric_subclass_strategy(player).unlocks(self.id)

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        player.add_buff("light", duration=100.0)

        visible_mobs = list(game._mobs_in_fov(player, floor, player.floor_id))
        for mob in visible_mobs:
            if mob.faction == player.faction or not mob.is_alive:
                continue
            mob.add_buff("paralysis", duration=3.0)
            if mob.has_buff("illuminated"):
                mob.remove_buff("illuminated")
                dmg = player.level + 5
                dealt = mob.take_damage(dmg)
                game.add_event("DAMAGE", {"target": mob.id, "amount": dealt, "holy": True}, floor_id=player.floor_id)
                if not mob.is_alive:
                    game._handle_kill_event(player, mob, floor)
                else:
                    mob.add_buff("illuminated", duration=50.0)
            else:
                mob.add_buff("illuminated", duration=50.0)

        game.add_event("FLASH_SCREEN", {"color": "0x80FFFFFF", "duration": 350}, floor_id=player.floor_id)
        return True


class HolyLanceSpell(ClericSpell):
    id = "holy_lance"
    name = "Holy Lance"
    tier = 3
    base_cost = 4.0
    targeting = "mob"
    icon = "🔱"
    desc = "Pierces enemies in a line for high holy damage."
    cast_sound = "ZAP"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("holy_lance") and not player.has_buff("lance_cooldown")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        target_mob = _resolve_target_mob(game, player, floor, tx, ty)
        if target_mob is None or not target_mob.is_alive:
            return False

        pts = player.talent_info.level("holy_lance")
        dmg_table = {1: (30, 55), 2: (45, 83), 3: (60, 110)}
        min_d, max_d = dmg_table.get(pts, (30, 55))
        is_unholy = target_mob.is_unholy
        dmg = max_d if is_unholy else random.randint(min_d, max_d)
        dealt = target_mob.take_damage(dmg)

        game.add_event(
            "RANGED_ATTACK",
            {
                "source": player.id,
                "x": player.pos.x,
                "y": player.pos.y,
                "target_x": target_mob.pos.x,
                "target_y": target_mob.pos.y,
                "projectile": "throwing_spike",
                "crit": False,
                "grim_proc": False,
                "beam_type": None,
                "sound": "HIT_MAGIC",
                "is_wand": True,
                "is_bow": False,
                "next_attack_in_ms": None,
            },
            floor_id=player.floor_id,
        )

        game.add_event(
            "DAMAGE",
            {"target": target_mob.id, "amount": dealt, "holy": True, "splash_count": 10},
            floor_id=player.floor_id,
        )

        player.add_buff("lance_cooldown", duration=30.0)

        if target_mob.is_alive:
            target_mob.add_buff("illuminated", duration=50.0)
        else:
            game._handle_kill_event(player, target_mob, floor)

        return True


class HallowedGroundSpell(ClericSpell):
    id = "hallowed_ground"
    name = "Hallowed Ground"
    tier = 3
    base_cost = 2.0
    targeting = "cell"
    icon = "🌱"
    desc = "Sanctifies the ground, healing allies and crippling enemies."
    cast_sound = "MELD"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("hallowed_ground")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        cx = tx if tx is not None else player.pos.x
        cy = ty if ty is not None else player.pos.y
        pts = player.talent_info.level("hallowed_ground")
        radius = pts  # 1 -> 3x3, 2 -> 5x5, 3 -> 7x7

        cells: List[Tuple[int, int]] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= ny < floor.height and 0 <= nx < floor.width:
                    if floor.flags and not floor.flags.solid[ny][nx]:
                        cells.append((nx, ny))
                        if floor.grid[ny][nx] in (TileType.FLOOR, TileType.EMBERS, TileType.EMPTY_DECO):
                            floor.grid[ny][nx] = TileType.FLOOR_GRASS

        blob_id = f"hallowed_ground_{player.id}"
        floor.blob_areas[blob_id] = {
            "type": "hallowed_ground",
            "cells": cells,
            "remaining": 20.0,
            "owner": player.id,
        }

        cell_set = set(cells)
        # On-cast effects
        for p in game.players.values():
            if p.floor_id == player.floor_id and p.is_alive and (p.pos.x, p.pos.y) in cell_set:
                p.hp = min(p.get_total_max_hp(), p.hp + 15)
                p.add_shield("barrier", 15, priority=1, decay=0)
                p.add_buff("barrier", duration=30.0, level=15)

        for m in floor.mobs.values():
            if not m.is_alive or (m.pos.x, m.pos.y) not in cell_set:
                continue
            if m.faction == player.faction or m.faction == "player":
                m.hp = min(m.max_hp, m.hp + 15)
                m.add_shield("barrier", 15, priority=1, decay=0)
                m.add_buff("barrier", duration=30.0, level=15)
            else:
                if not getattr(m, "flying", False):
                    m.add_buff("roots", duration=2.0)
                m.add_buff("illuminated", duration=50.0)

        return True


class MnemonicPrayerSpell(ClericSpell):
    id = "mnemonic_prayer"
    name = "Mnemonic Prayer"
    tier = 3
    base_cost = 1.0
    targeting = "ally_or_self"
    icon = "📖"
    desc = "Extends positive buffs on allies or negative debuffs on enemies."

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("mnemonic_prayer")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        pts = player.talent_info.level("mnemonic_prayer")
        ext = 2.0 + float(pts)

        target = resolve_spell_target(game, player, floor, tx, ty)
        target.apply_mnemonic_prayer(game, player, ext)

        return True


# ===========================================================================
# Tier 3 Paladin Spells
# ===========================================================================

class SmiteSpell(ClericSpell):
    id = "smite"
    name = "Smite"
    tier = 3
    base_cost = 2.0
    targeting = "mob"
    icon = "⚡"
    desc = "Strikes an adjacent foe with infinite accuracy and bonus holy damage."
    cast_sound = "HIT_STRONG"
    cast_animation = "attack"

    def is_unlocked(self, player: Player) -> bool:
        return get_cleric_subclass_strategy(player).unlocks(self.id)

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        target_mob = _resolve_target_mob(game, player, floor, tx, ty)
        if target_mob is None or not target_mob.is_alive:
            return False

        if abs(target_mob.pos.x - player.pos.x) > 1 or abs(target_mob.pos.y - player.pos.y) > 1:
            return False

        min_bonus = 5 + player.level // 2
        max_bonus = 10 + player.level
        is_unholy = target_mob.is_unholy
        bonus = max_bonus if is_unholy else random.randint(min_bonus, max_bonus)
        dmg = player.damage_max + bonus
        dealt = target_mob.take_damage(dmg)

        game.add_event("DAMAGE", {"target": target_mob.id, "amount": dealt, "holy": True, "splash_count": 10}, floor_id=player.floor_id)

        if not target_mob.is_alive:
            game._handle_kill_event(player, target_mob, floor)

        return True


class LayOnHandsSpell(ClericSpell):
    id = "lay_on_hands"
    name = "Lay on Hands"
    tier = 3
    base_cost = 1.0
    targeting = "ally_or_self"
    icon = "🤲"
    desc = "Grants barrier to yourself or restores health to an ally."
    cast_sound = "TELEPORT"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("lay_on_hands")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("lay_on_hands")
        base = 10 + 5 * pts
        max_cap = 3 * base

        floor = game._get_or_create_floor(player.floor_id)
        target = resolve_spell_target(game, player, floor, tx, ty)
        target.apply_lay_on_hands(game, player, base, max_cap)

        return True


class AuraOfProtectionSpell(ClericSpell):
    id = "aura_of_protection"
    name = "Aura of Protection"
    tier = 3
    base_cost = 2.0
    targeting = "none"
    icon = "🛡️"
    desc = "Emits a protective aura reducing damage taken by allies within 2 tiles."
    cast_sound = "READ"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("aura_of_protection")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("aura_of_protection")
        player.add_buff("aura_of_protection", duration=20.0, level=pts)
        return True


class WallOfLightSpell(ClericSpell):
    id = "wall_of_light"
    name = "Wall of Light"
    tier = 3
    base_cost = 3.0
    targeting = "cell"
    icon = "🧱"
    desc = "Raises a solid barrier of light for 20 turns, knocking back and stunning enemies."
    cast_sound = "CHARGEUP"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("wall_of_light")

    def get_cost(self, player: Player) -> float:
        # 0 cost to dismiss if wall is currently active on the current floor
        return 0.0 if getattr(player, "_has_active_wall", None) == player.floor_id else 3.0

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        blob_id = f"wall_of_light_{player.id}"

        # If already exists, dismiss early for 0 charges
        if blob_id in floor.blob_areas:
            del floor.blob_areas[blob_id]
            player._has_active_wall = None
            floor.rebuild_flags()
            game.add_event("BLOB_DEPLETED", {"id": blob_id}, floor_id=player.floor_id)
            return True

        if tx is None or ty is None:
            return False

        pts = player.talent_info.level("wall_of_light")
        width = 1 + 2 * pts  # 3, 5, 7 tiles
        half = width // 2

        dx = tx - player.pos.x
        dy = ty - player.pos.y
        # Perpendicular vector
        if abs(dx) >= abs(dy):
            px, py = 0, 1
        else:
            px, py = 1, 0

        wall_cells = []
        for step in range(-half, half + 1):
            wx = tx + px * step
            wy = ty + py * step
            if 0 <= wy < floor.height and 0 <= wx < floor.width:
                wall_cells.append((wx, wy))

        floor.blob_areas[blob_id] = {
            "type": "wall_of_light",
            "cells": wall_cells,
            "remaining": 20.0,
            "owner": player.id,
        }
        player._has_active_wall = player.floor_id
        floor.rebuild_flags()

        # Knockback and stun enemies on spawn
        for m in floor.mobs.values():
            if m.is_alive and m.faction != player.faction and (m.pos.x, m.pos.y) in wall_cells:
                m.add_buff("paralysis", duration=3.0)

        return True


# ===========================================================================
# Tier 4 Ascended Form Spells
# ===========================================================================

class DivineInterventionSpell(ClericSpell):
    id = "divine_intervention"
    name = "Divine Intervention"
    tier = 4
    base_cost = 5.0
    targeting = "none"
    icon = "👑"
    desc = "Grants a massive shield (150-300) and extends Ascended Form."
    cast_sound = "CHARGEUP"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return (
            player.talent_info.has("divine_intervention")
            and getattr(player, "ascended_form_active", False)
            and not getattr(player, "divine_intervention_used", False)
        )

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("divine_intervention")
        shield = 100 + 50 * pts
        player.add_shield("divine_shield", shield, priority=2, decay=0)
        player.add_buff("shielded", duration=30.0, level=shield)
        player.ascended_form_timer = getattr(player, "ascended_form_timer", 0.0) + (2.0 + float(pts))
        player.divine_intervention_used = True

        floor = game._get_or_create_floor(player.floor_id)
        if hasattr(game, "_players_on_floor"):
            for other_p in game._players_on_floor(player.floor_id):
                if other_p.id != player.id and getattr(other_p, "is_alive", False):
                    other_p.add_shield("divine_shield", shield, priority=2, decay=0)
                    other_p.add_buff("shielded", duration=30.0, level=shield)

        for mob in list(game._mobs_in_fov(player, floor, player.floor_id)):
            if mob.is_alive and mob.faction == player.faction:
                mob.add_shield("divine_shield", shield, priority=2, decay=0)
                mob.add_buff("shielded", duration=30.0, level=shield)

        duplicate_to_life_linked_ally(
            game, player, lambda ally: (
                ally.add_shield("divine_shield", shield, priority=2, decay=0),
                ally.add_buff("shielded", duration=30.0, level=shield),
            )
        )

        game.add_event("FLARE", {"x": player.pos.x, "y": player.pos.y, "color": "#FFFF00", "radius": 40, "rays": 8}, floor_id=player.floor_id)
        return True


class JudgementSpell(ClericSpell):
    id = "judgement"
    name = "Judgement"
    tier = 4
    base_cost = 3.0
    targeting = "none"
    icon = "⚡"
    desc = "Smites all visible enemies, dealing damage amplified by spells cast during Ascension."
    cast_sound = "BLAST"
    cast_animation = "attack"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("judgement") and getattr(player, "ascended_form_active", False)

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        pts = player.talent_info.level("judgement")
        dmg_table = {1: (10, 20), 2: (15, 30), 3: (20, 40), 4: (25, 50)}
        min_d, max_d = dmg_table.get(pts, (10, 20))
        casts = getattr(player, "ascended_form_casts", 0)
        mult = 1.0 + 0.333 * casts

        for mob in list(game._mobs_in_fov(player, floor, player.floor_id)):
            if mob.faction == player.faction or not mob.is_alive:
                continue
            dmg = round(random.randint(min_d, max_d) * mult)
            dealt = mob.take_damage(dmg)
            game.add_event("DAMAGE", {"target": mob.id, "amount": dealt, "holy": True}, floor_id=player.floor_id)
            if not mob.is_alive:
                game._handle_kill_event(player, mob, floor)
            else:
                get_cleric_subclass_strategy(player).illuminate(game, player, mob)

        player.ascended_form_casts = 0
        game.add_event("FLASH_SCREEN", {"color": "0x80FFFFFF", "duration": 350}, floor_id=player.floor_id)
        return True


class FlashSpell(ClericSpell):
    id = "flash"
    name = "Flash"
    tier = 4
    base_cost = 2.0
    targeting = "cell"
    icon = "⚡"
    desc = "Teleports up to 3-6 tiles away instantly."
    cast_sound = "TELEPORT"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("flash") and getattr(player, "ascended_form_active", False)

    def get_cost(self, player: Player) -> float:
        return self.base_cost + float(getattr(player, "flash_casts", 0))

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        if tx is None or ty is None:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        pts = player.talent_info.level("flash")
        max_dist = 2 + pts
        dist = math.hypot(tx - player.pos.x, ty - player.pos.y)
        if dist > max_dist:
            return False
        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return False
        if not (floor.flags and floor.flags.passable[ty][tx]):
            return False
        if any(m.is_alive and m.pos.x == tx and m.pos.y == ty for m in floor.mobs.values()):
            return False

        player.pos = Position(x=tx, y=ty)
        player.flash_casts = getattr(player, "flash_casts", 0) + 1
        game.add_event("MOVE", {"player": player.id, "x": tx, "y": ty}, floor_id=player.floor_id)
        return True


# ===========================================================================
# Tier 4 Trinity Spells
# ===========================================================================

class BodyFormSpell(ClericSpell):
    id = "body_form"
    name = "Body Form"
    tier = 4
    base_cost = 2.0
    targeting = "none"
    icon = "⚔️"
    desc = "Imbues weapon enchantment or armor glyph for 20-40 turns."
    cast_sound = "TELEPORT"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("body_form")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("body_form")
        dur = round(13.33 + 6.67 * pts)
        player.add_buff("empowered_strike", duration=float(dur), level=2)
        return True


class MindFormSpell(ClericSpell):
    id = "mind_form"
    name = "Mind Form"
    tier = 4
    base_cost = 3.0
    targeting = "mob"
    icon = "🔮"
    desc = "Casts a high level wand blast or thrown missile."
    cast_sound = "TELEPORT"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("mind_form")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        target_mob = _resolve_target_mob(game, player, floor, tx, ty)
        if target_mob is None or not target_mob.is_alive:
            return False

        pts = player.talent_info.level("mind_form")
        dmg = random.randint(15, 30) + pts * 5
        dealt = target_mob.take_damage(dmg)
        game.add_event("DAMAGE", {"target": target_mob.id, "amount": dealt, "magic": True}, floor_id=player.floor_id)
        if not target_mob.is_alive:
            game._handle_kill_event(player, target_mob, floor)

        return True


class SpiritFormSpell(ClericSpell):
    id = "spirit_form"
    name = "Spirit Form"
    tier = 4
    base_cost = 4.0
    targeting = "none"
    icon = "💍"
    desc = "Borrows the power of an identified ring or artifact for 20 turns."
    cast_sound = "TELEPORT"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("spirit_form")

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("spirit_form")
        player.add_buff("recharging", duration=20.0, level=pts)
        player.add_buff("haste", duration=20.0, level=pts)
        return True


# ===========================================================================
# Tier 4 Power of Many Spells
# ===========================================================================

class BeamingRaySpell(ClericSpell):
    id = "beaming_ray"
    name = "Beaming Ray"
    tier = 4
    base_cost = 1.0
    targeting = "cell"
    icon = "🌠"
    desc = "Teleports your Light Ally up to 4-16 tiles and boosts their damage."
    cast_sound = "RAY"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("beaming_ray") and player.powered_ally_id is not None

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        if tx is None or ty is None or not player.powered_ally_id:
            return False
        floor = game._get_or_create_floor(player.floor_id)
        if player.powered_ally_id not in floor.mobs:
            return False

        ally = floor.mobs[player.powered_ally_id]
        pts = player.talent_info.level("beaming_ray")
        max_dist = 4 * pts
        dist = math.hypot(tx - ally.pos.x, ty - ally.pos.y)
        if dist > max_dist:
            return False
        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return False
        if not (floor.flags and floor.flags.passable[ty][tx]):
            return False
        if any(m.is_alive and m.pos.x == tx and m.pos.y == ty for m in floor.mobs.values()):
            return False

        ally.pos = Position(x=tx, y=ty)
        ally.add_buff("damage_boost", duration=10.0, level=pts)
        game.add_event(
            "RANGED_ATTACK",
            {
                "source": player.id,
                "x": player.pos.x,
                "y": player.pos.y,
                "target_x": tx,
                "target_y": ty,
                "projectile": None,
                "beam_type": "sun_ray",
                "sound": "RAY",
            },
            floor_id=player.floor_id,
        )
        game.add_event("MOVE", {"target": ally.id, "x": tx, "y": ty}, floor_id=player.floor_id)
        return True


class LifeLinkSpell(ClericSpell):
    id = "life_link"
    name = "Life Link"
    tier = 4
    base_cost = 2.0
    targeting = "none"
    icon = "🔗"
    desc = "Links HP with your Light Ally for 10-20 turns and duplicates spells."
    cast_sound = "RAY"
    cast_animation = "zap"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("life_link") and player.powered_ally_id is not None

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        pts = player.talent_info.level("life_link")
        dur = round(6.67 + 3.33 * pts)
        player.add_buff("life_link", duration=float(dur))

        floor = game._get_or_create_floor(player.floor_id)
        if player.powered_ally_id in floor.mobs:
            ally = floor.mobs[player.powered_ally_id]
            ally.add_buff("life_link", duration=float(dur))
            ally._owner_ref = player
            player._active_powered_ally = ally
            game.add_event(
                "RANGED_ATTACK",
                {
                    "source": player.id,
                    "x": player.pos.x,
                    "y": player.pos.y,
                    "target_x": ally.pos.x,
                    "target_y": ally.pos.y,
                    "projectile": None,
                    "beam_type": "health_ray",
                    "sound": "RAY",
                },
                floor_id=player.floor_id,
            )

        return True


class StasisSpell(ClericSpell):
    id = "stasis"
    name = "Stasis"
    tier = 4
    base_cost = 2.0
    targeting = "none"
    icon = "⏳"
    desc = "Stores your Light Ally inside you in stasis for up to 60-150 turns."
    cast_sound = "TELEPORT"
    cast_animation = "operate"

    def is_unlocked(self, player: Player) -> bool:
        return player.talent_info.has("stasis") and player.powered_ally_id is not None

    def get_cost(self, player: Player) -> float:
        return 0.0 if (player.has_buff("stasis") or getattr(player, "_stasis_stored_ally", None) is not None) else 2.0

    def execute(self, game: Any, player: Player, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        floor = game._get_or_create_floor(player.floor_id)
        pts = player.talent_info.level("stasis")
        dur = float(30 + 30 * pts)

        if player.has_buff("stasis") or getattr(player, "_stasis_stored_ally", None) is not None:
            # Recall ally from stasis
            player.remove_buff("stasis")
            stored = getattr(player, "_stasis_stored_ally", None)
            if stored is not None:
                floor.mobs[stored.id] = stored
                stored.pos = Position(x=player.pos.x, y=player.pos.y)
                stored.is_alive = True
                player._stasis_stored_ally = None
            elif player.powered_ally_id in floor.mobs:
                ally = floor.mobs[player.powered_ally_id]
                ally.pos = Position(x=player.pos.x, y=player.pos.y)
                ally.is_alive = True
            game.add_event("PLAY_SOUND", {"sound": "TELEPORT", "x": player.pos.x, "y": player.pos.y}, floor_id=player.floor_id)
            return True

        if player.powered_ally_id in floor.mobs:
            ally = floor.mobs[player.powered_ally_id]
            player._stasis_stored_ally = ally
            del floor.mobs[ally.id]
            player.add_buff("stasis", duration=dur)
            game.add_event("PLAY_SOUND", {"sound": "TELEPORT", "x": ally.pos.x, "y": ally.pos.y}, floor_id=player.floor_id)
            return True

        return False


ALL_CLERIC_SPELLS: List[ClericSpell] = [
    GuidingLightSpell(),
    HolyWeaponSpell(),
    HolyWardSpell(),
    HolyIntuitionSpell(),
    ShieldOfLightSpell(),
    RecallInscriptionSpell(),
    SunraySpell(),
    DivineSenseSpell(),
    BlessSpell(),
    CleanseSpell(),
    RadianceSpell(),
    HolyLanceSpell(),
    HallowedGroundSpell(),
    MnemonicPrayerSpell(),
    SmiteSpell(),
    LayOnHandsSpell(),
    AuraOfProtectionSpell(),
    WallOfLightSpell(),
    DivineInterventionSpell(),
    JudgementSpell(),
    FlashSpell(),
    BodyFormSpell(),
    MindFormSpell(),
    SpiritFormSpell(),
    BeamingRaySpell(),
    LifeLinkSpell(),
    StasisSpell(),
]

SPELL_REGISTRY: Dict[str, ClericSpell] = {spell.id: spell for spell in ALL_CLERIC_SPELLS}


def get_cleric_spell(spell_id: str) -> Optional[ClericSpell]:
    return SPELL_REGISTRY.get(spell_id)


def get_available_spells(player: Player) -> List[ClericSpell]:
    return [spell for spell in ALL_CLERIC_SPELLS if spell.is_unlocked(player)]
