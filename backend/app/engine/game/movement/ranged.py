# Copyright (C) 2026 ArtemNikov
#
"""Ranged/thrown/wand attacks for GameInstance (part of MovementCombatMixin).

Auto-aim, ballistica line-of-fire resolution, damage roll, per-wand post-zap
effects and thrown-item consumption.
"""

import random
import time
from typing import Optional

from app.engine.entities.base import Position, consume_backpack_item
from app.engine.entities.buffs import add_buff, get_buff, remove_buff
from app.engine.entities.wands.cursed_dispatcher import fire_cursed_wand
from app.engine.entities.items.equip import Bow, MissileWeapon, SpiritBow, Staff
from app.engine.entities.wands import Wand, ZapContext
from app.engine.entities.mobs import Goo
from app.engine.entities.player import Player, Weapon, hurt_warning_sound
from app.engine.entities.rings import furor_multiplier
from app.engine.entities.subclasses import Talent
from app.engine.entities.wands.wandmaker_quest_items import CeremonialCandle
from app.engine.game.ai_goo import _goo_add_locked_floor_time
from app.engine.systems.ballistica import ballistica_trace
from app.engine.systems.combat import _dispel_stealth, resolve_ranged_attack


def _effective_wand_damage(w, lvl_bonus: int = 0) -> int:
    if hasattr(w, 'damage_roll_buffed'):
        return w.damage_roll_buffed(lvl_bonus=lvl_bonus)
    return w.damage


def _apply_backup_barrier(player, wand_item) -> None:
    """Back Up Barrier (mage T1): shield when the staff/wand runs out of charge.

    SPD Wand.java:722-750 grants 1+2*points (3/5). The SPD Barrier buff has no
    decay — it only shrinks by absorbing damage (decay=0 in decay_shields).
    """
    lvl = player.talent_info.level("backup_barrier")
    if lvl <= 0:
        return
    player.add_shield("backup_barrier", 1 + 2 * lvl, priority=1, decay=0)


_MAGIC_PROJECTILE_TYPES = {
    "magic_bolt", "magic_missile", "fire_bolt", "frost", "corrosion", "foliage",
    "force", "beacon", "shadow", "rainbow", "earth", "ward", "shaman_red",
    "shaman_blue", "shaman_purple", "elmo", "poison", "light_missile", "lightning", "beam",
}


class RangedAttackMixin:
    def _autoaim_cell(self, player, target) -> tuple:
        """Mirror of SPD QuickSlotButton.autoAim: aim straight at the target if a
        shot lands on it, else 'angle' the shot from a nearby cell whose ballistica
        still hits the target (shooting around a corner). Falls back to the
        target's own cell when no line of fire exists."""
        floor = self._get_or_create_floor(player.floor_id)
        others = list(self._players_on_floor(player.floor_id))
        mobs = list(floor.mobs.values())

        def hits(tx: int, ty: int) -> bool:
            rx, ry = ballistica_trace(
                player.pos.x, player.pos.y, tx, ty,
                floor.flags, floor.width, floor.height,
                others, mobs, player.id,
            )
            return rx == target.pos.x and ry == target.pos.y

        if hits(target.pos.x, target.pos.y):
            return target.pos.x, target.pos.y

        best = None
        best_d = 99
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                cx, cy = target.pos.x + dx, target.pos.y + dy
                if (cx, cy) == (target.pos.x, target.pos.y):
                    continue
                if hits(cx, cy):
                    d = abs(player.pos.x - cx) + abs(player.pos.y - cy)
                    if d < best_d:
                        best_d, best = d, (cx, cy)
        return best if best is not None else (target.pos.x, target.pos.y)

    def perform_ranged_attack(self, player_id: str, item_id: str, target_x: int, target_y: int,
                              target_entity_id: Optional[str] = None) -> Optional[int]:
        player = self.players.get(player_id)
        if not player or player.is_downed:
            return None

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        item = player.belongings.get_item(item_id)

        if not item:
            return None

        is_throwable = getattr(item, "throw_behavior", "") == "missile"
        is_weapon = isinstance(item, (Weapon, Bow, SpiritBow))
        is_wand = isinstance(item, Wand)
        is_staff = isinstance(item, Staff)
        is_bow = isinstance(item, (Bow, SpiritBow))

        if not is_weapon and not is_wand and not is_staff and not is_bow and not is_throwable:
            from app.engine.entities.items.actions import action_throw
            action_throw(self, player, item, target_x, target_y)
            return 0

        # Staff zap: delegate to imbued wand for charge/damage checks
        staff_wand = item.imbued_wand if is_staff else None
        effective_wand = staff_wand if is_staff else (item if is_wand else None)

        if is_wand and item.charges <= 0:
            return None

        if is_staff and staff_wand is None:
            return None

        if is_staff and staff_wand.charges <= 0:
            return None

        current_time = time.time()
        cooldown = 1.0
        if is_weapon:
            cooldown = item.attack_cooldown
        cooldown /= furor_multiplier(player)

        if (current_time - player.last_attack_time) < cooldown:
            return None

        # ScrollEmpower (Inscribed Power): +2 effective wand level while active
        # (SPD Wand.java:400-402). Set transiently so buffed_lvl() reports the
        # boosted level for damage rolls AND utility-wand effects, cleared after
        # the zap resolves.
        scroll_empower_buff = None
        if (is_wand or is_staff) and effective_wand is not None:
            scroll_empower_buff = get_buff(player.buffs, "scroll_empower")
            if scroll_empower_buff is not None:
                effective_wand._empower_bonus = 2

        wand_item = staff_wand if is_staff else item

        # Locked-target auto-aim (SPD QuickSlotButton.autoAim): when the client
        # sends the mob/player it is aiming at, resolve the firing cell here so
        # line-of-fire stays server-authoritative.
        if target_entity_id is not None:
            ent = floor.mobs.get(target_entity_id)
            if ent is None:
                for pp in self._players_on_floor(floor_id):
                    if pp.id == target_entity_id:
                        ent = pp
                        break
            if ent is not None and getattr(ent, "is_alive", True):
                target_x, target_y = self._autoaim_cell(player, ent)

        dist = abs(player.pos.x - target_x) + abs(player.pos.y - target_y)
        is_piercing = False
        if is_wand or is_staff:
            bfloor = self._get_or_create_floor(floor_id)
            is_piercing = getattr(effective_wand, "beam_type", None) == "death_ray"
            if is_piercing and effective_wand is not None:
                max_dist = 6 + 2 * effective_wand.buffed_lvl()
                target_x, target_y = ballistica_trace(
                    player.pos.x, player.pos.y, target_x, target_y,
                    bfloor.flags, bfloor.width, bfloor.height,
                    [], [], player.id,
                    stop_chars=False, stop_solid=False, max_dist=max_dist,
                )
            else:
                target_x, target_y = ballistica_trace(
                    player.pos.x, player.pos.y, target_x, target_y,
                    bfloor.flags, bfloor.width, bfloor.height,
                    list(self._players_on_floor(floor_id)),
                    list(bfloor.mobs.values()),
                    player.id,
                )
        else:
            max_range = item.get_reach() if hasattr(item, "get_reach") else getattr(item, "range", 5)
            if dist > max_range:
                return None
            if not self._is_in_los(player.pos, Position(x=target_x, y=target_y), floor_id=floor_id):
                return None

        player.last_attack_time = current_time
        player._last_action = "ranged"
        projectile_type = getattr(item, "projectile_type", "arrow")

        target_entity = self._entity_at(floor, floor_id, target_x, target_y, player_id)

        # SPD Wand.tryToZap: zapping a CURSED wand never fires its normal
        # effect — it triggers a random CursedWand effect instead, and the
        # curse becomes known. Rainbow bolt visual + ZAP sound (SPD fx()).
        if effective_wand is not None and effective_wand.cursed:
            effective_wand.cursed_known = True
            next_attack_in_ms = round(max(0.0, player.last_attack_time + cooldown - time.time()) * 1000)
            self.add_event("RANGED_ATTACK", {
                "source": player_id,
                "x": player.pos.x, "y": player.pos.y,
                "target_x": target_x, "target_y": target_y,
                "projectile": "rainbow",
                "crit": False, "grim_proc": False,
                "beam_type": None, "target_hp_ratio": None,
                "sound": "ATTACK_MAGIC",
                "is_wand": True, "is_bow": False,
                "next_attack_in_ms": next_attack_in_ms,
            }, floor_id=floor_id)
            fire_cursed_wand(self, player, effective_wand, target_x, target_y,
                             consume_charge=False)
            _dispel_stealth(player)
            # SPD Wand.java:722-750: Back Up Barrier triggers before the curse
            # branch, so a cursed zap that empties the wand still shields.
            charges_per_cast = getattr(effective_wand, "charges_per_cast", lambda: 1)()
            if effective_wand.charges == charges_per_cast:
                _apply_backup_barrier(player, effective_wand)
            # SPD wandUsed(): cursed zaps always consume exactly 1 charge
            effective_wand.charges = max(0, effective_wand.charges - 1)
            if scroll_empower_buff is not None:
                effective_wand._empower_bonus = 0
            return 0

        # Back Up Barrier (mage T1): shield when this zap will empty the wand
        # (SPD Wand.java:722-750 — triggers before the zap fully resolves).
        charges_per_cast = getattr(effective_wand, "charges_per_cast", lambda: 1)()
        if (is_wand or is_staff) and wand_item.charges == charges_per_cast:
            _apply_backup_barrier(player, wand_item)

        # GreatCrab: negates wand/spell damage while awake & not paralyzed
        crab_blocked = (
            target_entity is not None
            and hasattr(target_entity, "blocks_ranged_source")
            and target_entity.blocks_ranged_source(player)
        )

        beam_type = getattr(item, "beam_type", None)
        target_hp_ratio = None
        if beam_type == "health_ray" and target_entity and target_entity.get_total_max_hp() > 0:
            target_hp_ratio = target_entity.hp / target_entity.get_total_max_hp()
        next_attack_in_ms = round(max(0.0, player.last_attack_time + cooldown - time.time()) * 1000)
        ranged_event_data = {
            "source": player_id,
            "x": player.pos.x,
            "y": player.pos.y,
            "target_x": target_x,
            "target_y": target_y,
            "projectile": projectile_type,
            "crit": False,
            "grim_proc": False,
            "beam_type": beam_type,
            "target_hp_ratio": target_hp_ratio,
            "sound": getattr(effective_wand or item, "wand_sound", None),
            "is_wand": is_wand or is_staff,
            "is_bow": is_bow,
            "next_attack_in_ms": next_attack_in_ms,
        }
        # Thrown inventory items fly as their own sprite (not a generic dart).
        # Wands keep the magic_bolt projectile. Bows are not thrown — they fire
        # arrows, so the bow item itself is not serialized as the projectile.
        if not is_wand and not is_bow:
            ranged_event_data["item"] = self._serialize_floor_item(item)
        self.add_event(
            "RANGED_ATTACK",
            ranged_event_data,
            floor_id=floor_id,
        )

        damage_dealt = 0
        result = {}
        magic_charge_consumed = False
        if not crab_blocked and not is_piercing and target_entity and player.faction != target_entity.faction:
            if isinstance(item, SpiritBow):
                atk_min = item.dmg_min(player.level)
                atk_max = item.dmg_max(player.level)
            elif effective_wand is not None:
                # SPD MagicCharge buff: while active, non-MM wands cast at
                # the Magic Missile's level instead of their own.
                magic_charge_lvl = 0
                mc = get_buff(player.buffs, "magic_charge")
                if effective_wand.kind != "wand_magic_missile" and mc:
                    magic_charge_lvl = mc.level - effective_wand.buffed_lvl()
                    remove_buff(player.buffs, "magic_charge")
                    magic_charge_consumed = True
                atk_min = atk_max = _effective_wand_damage(effective_wand, lvl_bonus=magic_charge_lvl)
                # SPD WandEmpower (Empowering Meal): flat +1/+2 damage on damage
                # wands, next 3 zaps (DamageWand.damageRoll:51-63).
                if hasattr(effective_wand, "damage_roll_buffed"):
                    wand_empower = get_buff(player.buffs, "wand_empower")
                    if wand_empower is not None:
                        atk_min += 1 + player.talent_info.level("empowering_meal")
                        atk_max = atk_min
                        wand_empower.level -= 1
                        if wand_empower.level <= 0:
                            remove_buff(player.buffs, "wand_empower")
                # SPD WandOfPrismaticLight: +33% vs demonic/undead
                if effective_wand.kind == "wand_prismatic_light" and target_entity:
                    tprops = getattr(target_entity, "properties", None) or []
                    if "DEMONIC" in tprops or "UNDEAD" in tprops:
                        atk_min = atk_max = int(atk_min * 1.333)
            elif is_weapon:
                if player.belongings.weapon and item.id == player.belongings.weapon.id:
                    atk_min = player.get_damage_min()
                    atk_max = player.get_damage_max()
                else:
                    dmg = item.damage + (player.strength // 2)
                    atk_min = atk_max = dmg
            else:
                dmg = item.damage + (player.strength // 2)
                atk_min = atk_max = dmg
            old_min, old_max = player.damage_min, player.damage_max
            player.damage_min, player.damage_max = atk_min, atk_max
            result = resolve_ranged_attack(
                player, target_entity, item,
                floor.mobs, target_x, target_y,
                is_in_los=lambda a, b: self._is_in_los(a, b, floor_id=floor_id),
                floor=floor,
                game=self,
            )
            player.damage_min, player.damage_max = old_min, old_max
            if result["missed"]:
                self.add_event("MISS", {"source": player.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
            damage_dealt = result["damage"]
            ranged_event_data["crit"] = result.get("crit", False)
            ranged_event_data["grim_proc"] = result.get("grim_proc", False)

            if damage_dealt > 0:
                if projectile_type in _MAGIC_PROJECTILE_TYPES:
                    splash_lvl = effective_wand.buffed_lvl() if effective_wand is not None else 0
                    dmg_beam_type = getattr(effective_wand or item, "beam_type", None) if (is_wand or is_staff) else None
                    self.add_event("DAMAGE", {
                        "target": target_entity.id,
                        "amount": damage_dealt,
                        "crit": result.get("crit", False),
                        "grim_proc": result.get("grim_proc", False),
                        "projectile": projectile_type,
                        "splash_count": splash_lvl // 2 + 2,
                        "source_x": player.pos.x,
                        "source_y": player.pos.y,
                        "beam_type": dmg_beam_type,
                    }, floor_id=floor_id)
                else:
                    self.add_event("DAMAGE", {
                        "target": target_entity.id,
                        "amount": damage_dealt,
                        "crit": result.get("crit", False),
                        "grim_proc": result.get("grim_proc", False),
                        "source_x": player.pos.x,
                        "source_y": player.pos.y,
                    }, floor_id=floor_id)
                    self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG" if result.get("crit") else "HIT_ARROW"}, floor_id=floor_id, source_player_id=player.id)
                if result.get("grim_proc"):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)

                if isinstance(target_entity, Player):
                    self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=target_entity.id)
                    warn_sound = hurt_warning_sound(damage_dealt, target_entity.hp, target_entity.get_total_max_hp())
                    if warn_sound:
                        self.add_event("PLAY_SOUND", {"sound": warn_sound}, player_id=target_entity.id)
                if isinstance(target_entity, Goo):
                    _goo_add_locked_floor_time(self, floor_id, player, damage_dealt)

                # Improvised Projectiles (warrior T2): non-launcher thrown
                # items blind the target on hit (50-turn cooldown).
                ip = player.subclass_info.talent_info.level(Talent.IMPROVISED_PROJECTILES)
                if (
                    ip > 0 and is_throwable and not isinstance(item, MissileWeapon)
                    and target_entity.is_alive
                    and not player.has_buff("improvised_projectile_cooldown")
                ):
                    add_buff(target_entity.buffs, "blindness", duration=1.0 + ip, level=1)
                    add_buff(player.buffs, "improvised_projectile_cooldown", duration=50.0, level=1)

            self._maybe_trigger_dm300_supercharge(target_entity, floor, floor_id, player.pos)

            if not target_entity.is_alive:
                self._finish_kill(player, target_entity, floor, floor_id)

        if crab_blocked:
            self.add_event("MISS", {"source": player_id, "target": target_entity.id, "defense_verb": "blocks"}, floor_id=floor_id)

        # Delegate wand-specific post-damage effects to the wand's handle_zap
        if effective_wand is not None and isinstance(effective_wand, Wand) and not crab_blocked:
            ctx = ZapContext(
                attacker=player,
                target_x=target_x, target_y=target_y,
                target_entity=target_entity,
                damage_dealt=damage_dealt,
                hit=result.get("hit", False),
                crit=result.get("crit", False),
                missed=result.get("missed", False),
                floor=floor, floor_id=floor_id,
                floor_mobs=floor.mobs,
                floor_players=list(self._players_on_floor(floor_id)),
                add_event=lambda type, data, **kw: self.add_event(type, data, **kw),
                game=self,
            )
            effective_wand.handle_zap(ctx)

        if is_wand or is_staff:
            # SPD Invisibility.dispel(): every zap breaks invisibility, even
            # one aimed at empty ground (entity hits already dispel in the
            # ranged resolver).
            _dispel_stealth(player)
            # Wand Preservation (mage T2): chance to not consume charge
            wp = player.talent_info.level("wand_preservation")
            charges_used = getattr(effective_wand, "charges_per_cast", lambda: 1)()
            if wp <= 0 or random.random() >= wp * 0.17:
                wand_item.charges = max(0, wand_item.charges - charges_used)
            # Magic Charge: buff that boosts next non-Magic-Missile wand by +1 level
            if wand_item.kind == "wand_magic_missile" and damage_dealt > 0:
                player.add_buff("magic_charge", duration=4.0, level=wand_item.buffed_lvl(), stack_mode="extend")
            # Shield Battery (mage T2): gain shield on wand zap
            sb = player.talent_info.level("shield_battery")
            if sb > 0:
                shield_amt = 1 + sb
                player.add_shield("shield_battery", shield_amt, priority=1, decay=600)
            # Apply Empowered Strike tracker after zap if applicable
            if is_staff and damage_dealt > 0:
                es_talent = player.talent_info.level("empowered_strike")
                if es_talent > 0:
                    player.add_buff("empowered_strike_tracker", duration=10.0, level=es_talent)
            # Lingering Magic (mage T1): this zap lingers — the next melee
            # attack deals bonus magic damage (SPD Wand.java:513-517).
            lingering = player.talent_info.level("lingering_magic")
            if lingering > 0:
                player.add_buff("lingering_magic_tracker", duration=5.0, level=lingering)
            # ScrollEmpower (Inscribed Power): consume one empowered zap. SPD
            # skips consumption when MagicCharge was used this zap
            # (Wand.java:490-503).
            if scroll_empower_buff is not None and not magic_charge_consumed:
                scroll_empower_buff.level -= 1
                if scroll_empower_buff.level <= 0:
                    remove_buff(player.buffs, "scroll_empower")
            if scroll_empower_buff is not None:
                effective_wand._empower_bonus = 0
        elif not is_bow:
            removed = consume_backpack_item(player, item)
            if removed is not None:
                removed.pos = Position(x=target_x, y=target_y)
                floor.items[removed.id] = removed
                if isinstance(removed, CeremonialCandle):
                    self._check_ritual_candles(floor_id)

        return damage_dealt
