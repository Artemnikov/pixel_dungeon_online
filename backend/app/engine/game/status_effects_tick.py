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
"""Client-facing status effect bookkeeping: STATE_EFFECT event emission and
the player active_effects list synced to the frontend HUD each tick.
"""

from app.engine.dungeon.generator import TileType
from app.engine.entities.buffs import get_buff, has_buff
from app.engine.entities.player import Effect, Player


class StatusEffectsTickMixin:
    def _emit_state_effects(self):
        for player in self.players.values():
            if not player.is_alive:
                continue
            self._check_state_buff(player, player.pos.x, player.pos.y, player.floor_id)
        for floor_id in self.active_floor_ids:
            floor = self.floors[floor_id]
            for mob in floor.mobs.values():
                if not mob.is_alive:
                    continue
                self._check_state_buff(mob, mob.pos.x, mob.pos.y, floor_id)

    STATE_BUFF_MAP = {
        "burning": "burning",
        "frozen": "frozen",
        "chilled": "chilled",
        "illuminated": "illuminated",
        "marked": "marked",
        "shocked": "shocked",
        "bleeding": "bleeding",
        "poison": "poisoned",
        "poisoned": "poisoned",
        "bless": "hearts",
        "charm": "hearts",
        "chill": "chilled",
        "frost": "frozen",
        "lightning_charge": "shocked",
        "rock_armor": "hearts",
        "barrier": "hearts",
        "slow": "chilled",
        "daze": "daze",
        "levitation": "levitation",
    }

    def _frost_thaw(self, entity, floor):
        # Frost.detach: a character that thaws while standing in water is left
        # chilled (Chill for half of Frost's 10-turn duration).
        if floor is None:
            return
        x, y = entity.pos.x, entity.pos.y
        if 0 <= y < len(floor.grid) and 0 <= x < len(floor.grid[0]) \
                and floor.grid[y][x] == TileType.FLOOR_WATER:
            entity.add_buff("chill", duration=5.0, level=1, stack_mode="extend")

    def _check_state_buff(self, entity, x, y, floor_id):
        for buff_name, effect_type in self.STATE_BUFF_MAP.items():
            if has_buff(entity.buffs, buff_name):
                self.add_event("STATE_EFFECT", {
                    "entity_id": entity.id,
                    "effect": effect_type,
                    "x": x,
                    "y": y,
                }, floor_id=floor_id)

    def _sync_effects(self, player: Player):
        from app.engine.entities.buffs import has_buff, get_buff
        existing = {e.key: e for e in player.active_effects}
        effects = []
        if player.heal_left > 0:
            prev = existing.get("regen")
            duration = max(prev.duration if prev else 0.0, player.heal_left)
            effects.append(Effect(
                key="regen", name="Healing", icon=44,
                remaining=player.heal_left, duration=duration,
            ))
        if player.aqua_heal_left > 0:
            effects.append(Effect(
                key="aqua_rejuv", name="Aquatic Rejuvenation", icon=44,
                remaining=player.aqua_heal_left, duration=player.aqua_heal_left,
            ))
        if player.berserk_active:
            effects.append(Effect(
                key="berserk", name="Berserk", icon=13,
                remaining=player.berserk_power, duration=1.0,
            ))
        endure_buff = get_buff(player.buffs, "endure_tracker")
        if endure_buff is not None:
            effects.append(Effect(
                key="endure", name="Endure", icon=6,
                remaining=endure_buff.remaining, duration=12.0,
            ))
        if player.has_fury:
            effects.append(Effect(
                key="fury", name="Fury", icon=5,
                remaining=float(player.fury_turns_remaining), duration=10.0,
            ))
        if player.locked_floor_left is not None:
            effects.append(Effect(
                key="locked_floor", name="Locked Floor", icon=35,
                remaining=max(0.0, min(50.0, player.locked_floor_left)), duration=50.0,
            ))
        invis_buff = get_buff(player.buffs, "invisibility")
        if invis_buff is not None:
            effects.append(Effect(
                key="invisibility", name="Invisible", icon=12,
                remaining=invis_buff.remaining, duration=20.0,
            ))
        elif get_buff(player.buffs, "shadows") is not None:
            effects.append(Effect(
                key="invisibility", name="Invisible", icon=12,
            ))
        slow_buff = get_buff(player.buffs, "slow")
        if slow_buff is not None:
            effects.append(Effect(
                key="slow", name="Slowed", icon=23,
                remaining=slow_buff.remaining, duration=30.0,
            ))
        bleed_buff = get_buff(player.buffs, "bleeding")
        if bleed_buff is not None:
            effects.append(Effect(
                key="bleeding", name="Bleeding", icon=26,
                remaining=bleed_buff.remaining, duration=30.0,
            ))
        daze_buff = get_buff(player.buffs, "daze")
        if daze_buff is not None:
            effects.append(Effect(
                key="daze", name="Dazed", icon=70,
                remaining=daze_buff.remaining, duration=30.0,
            ))
        bless_buff = get_buff(player.buffs, "bless")
        if bless_buff is not None:
            effects.append(Effect(
                key="bless", name="Blessed", icon=37,
                remaining=bless_buff.remaining, duration=30.0,
            ))
        heal_buff = get_buff(player.buffs, "healing")
        if heal_buff is not None:
            effects.append(Effect(
                key="healing_buff", name="Healing", icon=44,
                remaining=heal_buff.remaining, duration=30.0,
            ))
        well_fed_buff = get_buff(player.buffs, "well_fed")
        if well_fed_buff is not None:
            effects.append(Effect(
                key="well_fed", name="Well Fed", icon=43,
                remaining=well_fed_buff.remaining, duration=30.0,
            ))
        levitation_buff = get_buff(player.buffs, "levitation")
        if levitation_buff is not None:
            effects.append(Effect(
                key="levitation", name="Levitation", icon=1,
                remaining=levitation_buff.remaining, duration=30.0,
            ))
        seal_shield = player.get_shield("broken_seal")
        if seal_shield is not None and seal_shield.amount > 0:
            effects.append(Effect(
                key="seal_shield", name="Shield", icon=84,
                remaining=seal_shield.amount,
                duration=player.get_broken_seal_max_shield() or seal_shield.amount,
            ))
        player.active_effects = effects
