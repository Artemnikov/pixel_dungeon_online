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
"""Player passive-regen ticking: delayed heal payout, aquatic rejuvenation,
entrance-room healing, passive HP regen, and passive wand recharge.
"""

import math
import random

from app.engine.dungeon.constants import TileType
from app.engine.entities.items_wands import Wand
from app.engine.entities.player import Player
from app.engine.entities.scroll_predicates import player_inventory_items
from app.engine.game.constants import (
    HEAL_TICK_INTERVAL,
    PASSIVE_REGEN_INTERVAL,
    RECHARGING_REGEN_MULTIPLIER,
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

    def _apply_passive_regen(self, player: Player):
        if not player.has_buff("well_fed"):
            return
        # SPD Regeneration.regenOn(): LockedFloor (sealed boss arena) pauses
        # passive regen once its timer runs out.
        if player.locked_floor_left is not None and player.locked_floor_left < 1:
            return
        if player.hp <= 0 or player.hp >= player.get_total_max_hp():
            player._regen_cooldown = 0
            return
        interval = PASSIVE_REGEN_INTERVAL
        # SaltCube trinket: slows natural regen
        from app.engine.entities.trinkets import SaltCube as _SaltCube
        from app.engine.entities.trinkets import trinket_level
        salt_lvl = trinket_level(player, "salt_cube")
        if salt_lvl >= 0:
            mult = _SaltCube.health_regen_multiplier(salt_lvl)
            interval = int(interval / mult) if mult > 0 else interval
        interval = max(1, interval // 3)  # 3x regen rate while well_fed
        cooldown = getattr(player, "_regen_cooldown", 0)
        cooldown -= 1
        if cooldown > 0:
            player._regen_cooldown = cooldown
            return
        player.hp = min(player.get_total_max_hp(), player.hp + 1)
        player._regen_cooldown = interval

    def _tick_passive_wand_recharge(self, player: Player, dt: float):
        """Passive wand recharge:
        - Normal wands: SPD formula (10 + 40 * 0.875^missing)
        - Staff-imbued wands: +1 charge every 2s (SPD MagesStaff style).
        - Recharging buff (Scroll of Recharging): multiplier on regen speed."""
        from app.engine.entities.items_equip import Staff as StaffCls
        weapon = getattr(player, "belongings", None)
        if weapon is not None:
            weapon = weapon.weapon
        imbued_wand = weapon.imbued_wand if isinstance(weapon, StaffCls) else None

        rate_mult = RECHARGING_REGEN_MULTIPLIER if player.has_buff("recharging") else 1.0
        from app.engine.entities.rings import energy_wand_multiplier
        rate_mult *= energy_wand_multiplier(player)

        for item in player_inventory_items(player):
            if item is imbued_wand:
                continue  # handled below by the dedicated staff-recharge block
            if isinstance(item, Wand) and item.charges < item.max_charges and not item.cursed:
                missing = item.max_charges - item.charges
                turns_to_charge = 10.0 + 40.0 * (0.875 ** missing)
                item.gain_charge(dt / turns_to_charge * rate_mult)
        # Staff-imbued wand recharge: +1 charge every 2s, scaled by the
        # wand's recharge_scale (set to 0.75 by MagesStaff imbuing).
        if imbued_wand is not None:
            w = imbued_wand
            if w.charges < w.max_charges and not w.cursed:
                w.gain_charge(dt / (2.0 * w.recharge_scale) * rate_mult)
