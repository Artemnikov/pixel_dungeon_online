# Copyright (C) 2026 ArtemNikov
#
"""Player passive-regen ticking: delayed heal payout, aquatic rejuvenation,
entrance-room healing, passive HP regen, and passive wand recharge.
"""

import math
import random
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction
from app.engine.entities.wands import Wand
from app.engine.entities.player import Player
from app.engine.entities.scroll_predicates import player_inventory_items
from app.engine.game.constants import (
    HEAL_TICK_INTERVAL,
    NOURISHED_COMBAT_HEAL_FRACTION,
    NOURISHED_HEAL_BOOST,
    RECHARGE_BUFF_BONUS,
    REST_ENEMY_RADIUS,
    REST_HEAL_INTERVAL,
    REST_STILL_TICKS,
)


class PlayerRegenMixin:
    def _apply_heal_tick(self, player: Player):
        if player.heal_left <= 0:
            return

        player.heal_cooldown -= 1
        if player.heal_cooldown > 0:
            return

        amt = int(round(player.heal_left * player.heal_pct_per_tick) + player.heal_flat_per_tick)
        amt = int(max(1, min(amt, player.heal_left)))

        # VialOfBlood trinket: cap per-turn healing during delayed heal
        from app.engine.entities.trinkets import VialOfBlood as _VialOfBlood
        from app.engine.entities.trinkets import trinket_level
        vob_lvl = trinket_level(player, "vial_of_blood")
        if vob_lvl >= 0:
            cap = _VialOfBlood.max_heal_per_turn(vob_lvl, player.get_total_max_hp())
            amt = min(amt, cap)

        if player.hp < player.get_total_max_hp():
            player.hp = int(min(player.get_total_max_hp(), player.hp + amt))

        player.heal_left -= amt
        player.heal_cooldown = HEAL_TICK_INTERVAL

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

        if player.heal_left <= 0:
            player.heal_left = 0.0
            player.heal_pct_per_tick = 0.0
            player.heal_flat_per_tick = 0.0

    def _apply_aqua_heal_tick(self, player: Player):
        # Elixir of Aquatic Rejuvenation (SPD AquaHealing): heals
        # max(1, maxHP/50) per turn while standing in water, until the pool
        # (round(maxHP*1.5)) is exhausted. Fractional heal amounts are rounded
        # probabilistically (SPD's Random.round / chance-of-rounding-up).
        if player.aqua_heal_left <= 0:
            return

        max_hp = player.get_total_max_hp()
        if player.hp >= max_hp:
            return

        floor = self._get_or_create_floor(player.floor_id)
        if floor.grid[player.pos.y][player.pos.x] != TileType.FLOOR_WATER:
            return

        raw = max(1.0, max_hp / 50.0)
        whole = math.floor(raw)
        frac = raw - whole
        amt = whole + 1 if random.random() < frac else whole
        amt = max(1, amt)
        amt = int(min(amt, player.aqua_heal_left, max_hp - player.hp))

        player.hp = int(min(max_hp, player.hp + amt))
        player.aqua_heal_left -= amt
        if player.aqua_heal_left <= 0:
            player.aqua_heal_left = 0.0

        self.add_event(
            "HEAL",
            {"target": player.id, "amount": int(amt), "x": player.pos.x, "y": player.pos.y},
            floor_id=player.floor_id,
        )

    _HUNGER_RATE = 1.0 / 20.0
    _HUNGER_HUNGRY = 300.0
    _HUNGER_STARVING = 450.0

    def _apply_hunger_tick(self, player: Player):
        if player.is_downed:
            return
        from app.engine.entities.trinkets import SaltCube as _SaltCube
        from app.engine.entities.trinkets import trinket_level
        rate = self._HUNGER_RATE
        lvl = trinket_level(player, "salt_cube")
        if lvl >= 0:
            rate *= _SaltCube.hunger_gain_multiplier(lvl)
        player.hunger = min(self._HUNGER_STARVING + 50, player.hunger + rate)
        if player.hunger >= self._HUNGER_STARVING:
            dmg = max(1, player.max_hp // 100)
            player.take_damage(dmg)

    # SPD WellFed.act(): +1 HP every 18 turns, independent of the normal
    # regen formula (this port maps 1 SPD turn to 1 real second, matching
    # how Hunger.STARVING=450 turns is already ported as a 450s clock).
    _WELL_FED_HEAL_INTERVAL = 18.0

    def _apply_sungrass_heal(self, entity, dt: float, floor_id: Optional[int] = None):
        """SPD Sungrass.Health: fractional heal accumulator advancing at
        (40 + HT) / 150 HP/sec (this port maps 1 SPD turn to 1 second).
        Walking off the plant tile breaks stationary buffs (source_id != None)."""
        from app.engine.entities.buffs import break_stationary_plant_buffs, get_buff, remove_buff

        break_stationary_plant_buffs(entity)
        buff = get_buff(getattr(entity, "buffs", []), "sungrass_health")
        if buff is None:
            entity._sungrass_heal_accum = 0.0
            return
        if getattr(entity, "hp", 0) <= 0:
            entity._sungrass_heal_accum = 0.0
            return

        max_hp = entity.get_total_max_hp() if hasattr(entity, "get_total_max_hp") else getattr(entity, "max_hp", 20)
        if entity.hp >= max_hp:
            entity._sungrass_heal_accum = 0.0
            return

        rate = (40.0 + max_hp) / 150.0
        accum = getattr(entity, "_sungrass_heal_accum", 0.0) + dt * rate
        if accum >= 1.0:
            heal_units = int(accum)
            actual_heal = min(heal_units, max_hp - entity.hp, buff.level)
            if actual_heal > 0:
                entity.hp += actual_heal
                buff.level -= actual_heal
                accum -= heal_units
                f_id = floor_id if floor_id is not None else getattr(entity, "floor_id", 1)
                pos = getattr(entity, "pos", None)
                px = pos.x if pos else 0
                py = pos.y if pos else 0
                self.add_event(
                    "HEAL",
                    {"target": entity.id, "amount": int(actual_heal), "x": px, "y": py},
                    floor_id=f_id,
                )
            if buff.level <= 0:
                if hasattr(entity, "remove_buff"):
                    entity.remove_buff("sungrass_health")
                else:
                    remove_buff(entity.buffs, "sungrass_health")
                entity._sungrass_heal_accum = 0.0
                return
        entity._sungrass_heal_accum = accum

    def _apply_passive_regen(self, player: Player, dt: float):
        if not player.has_buff("well_fed"):
            player._well_fed_heal_timer = 0.0
            return
        # SPD Regeneration.regenOn(): LockedFloor (sealed boss arena) pauses
        # passive regen once its timer runs out.
        if player.locked_floor_left is not None and player.locked_floor_left < 1:
            return
        if player.hp <= 0 or player.hp >= player.get_total_max_hp():
            return
        timer = getattr(player, "_well_fed_heal_timer", 0.0) + dt
        if timer >= self._WELL_FED_HEAL_INTERVAL:
            timer -= self._WELL_FED_HEAL_INTERVAL
            player.hp = min(player.get_total_max_hp(), player.hp + 1)
        player._well_fed_heal_timer = timer

    def _apply_rest_regen(self, player: Player, dt: float):
        """Online rest-healing: while standing still with no hostile mob
        nearby, regenerate 1 HP per REST_HEAL_INTERVAL seconds. The nourished
        buff (from eating food) doubles the rest rate and also lets healing
        tick during combat at a reduced rate. Fractional HP accumulates across
        20Hz ticks; whole HP is applied as a HEAL event.
        """
        if player.hp <= 0 or player.hp >= player.get_total_max_hp():
            player._rest_heal_accum = 0.0
            return
        # LockedFloor (sealed boss arena) pauses rest healing, matching the
        # well_fed passive-regen rule.
        if player.locked_floor_left is not None and player.locked_floor_left < 1:
            player._rest_heal_accum = 0.0
            return

        floor = self._get_or_create_floor(player.floor_id)
        fighting = any(
            m.is_alive and m.faction != Faction.PLAYER
            and abs(m.pos.x - player.pos.x) + abs(m.pos.y - player.pos.y) <= REST_ENEMY_RADIUS
            for m in floor.mobs.values()
        )
        stationary = player.stationary_ticks >= REST_STILL_TICKS
        nourished = player.has_buff("nourished")

        if stationary and not fighting:
            rate = 1.0 / REST_HEAL_INTERVAL
            if nourished:
                rate *= NOURISHED_HEAL_BOOST
        elif nourished and fighting:
            rate = 1.0 / REST_HEAL_INTERVAL * NOURISHED_COMBAT_HEAL_FRACTION
        else:
            player._rest_heal_accum = 0.0
            return

        accum = getattr(player, "_rest_heal_accum", 0.0) + rate * dt
        if accum >= 1.0:
            amt = int(accum)
            accum -= amt
            max_hp = player.get_total_max_hp()
            if player.hp < max_hp:
                player.hp = int(min(max_hp, player.hp + amt))
                self.add_event(
                    "HEAL",
                    {"target": player.id, "amount": amt, "x": player.pos.x, "y": player.pos.y},
                    floor_id=player.floor_id,
                )
        player._rest_heal_accum = accum

    def _tick_passive_wand_recharge(self, player: Player, dt: float):
        """Passive wand recharge:
        - All wands: SPD formula turnsToCharge = 10 + 40 * scale^missing,
          scale 0.875 normally, 0.75 for staff-imbued wands (MagesStaff).
        - Recharging buff (Scroll of Recharging): SPD Charger adds a flat
          0.25 * min(1, buff.remaining) charge per second."""
        from app.engine.entities.items.equip import Staff as StaffCls
        weapon = getattr(player, "belongings", None)
        if weapon is not None:
            weapon = weapon.weapon
        imbued_wand = weapon.imbued_wand if isinstance(weapon, StaffCls) else None

        from app.engine.entities.rings import energy_wand_multiplier
        rate_mult = energy_wand_multiplier(player)

        recharge_buff = player.get_buff("recharging")
        recharge_bonus = 0.0
        if recharge_buff is not None:
            recharge_bonus = RECHARGE_BUFF_BONUS * min(1.0, recharge_buff.remaining)

        for item in player_inventory_items(player):
            if item is imbued_wand:
                continue  # handled below by the dedicated staff-recharge block
            if isinstance(item, Wand) and item.charges < item.max_charges and not item.cursed:
                missing = item.max_charges - item.charges
                turns_to_charge = 10.0 + 40.0 * (0.875 ** missing)
                item.gain_charge(dt / turns_to_charge * rate_mult + recharge_bonus * dt)
        # Staff-imbued wand recharge: SPD MagesStaff uses the same exponential
        # formula with scale 0.75 (recharge_scale, set by Staff.update_wand).
        if imbued_wand is not None:
            w = imbued_wand
            if w.charges < w.max_charges and not w.cursed:
                missing = w.max_charges - w.charges
                turns_to_charge = 10.0 + 40.0 * (w.recharge_scale ** missing)
                w.gain_charge(dt / turns_to_charge * rate_mult + recharge_bonus * dt)
