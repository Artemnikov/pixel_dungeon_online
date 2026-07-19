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
"""Port of SentryRoom.Sentry's act() -- an immovable, invulnerable guardian
that charges an unavoidable beam attack while a player lingers on the
room's "danger" floor tiles (SPD Terrain.EMPTY_SP) within line of sight, and
resets the charge the moment they leave either condition."""

import random

from app.engine.dungeon.constants import TileType
from app.engine.entities.mobs import Sentry
from app.engine.game.floor_state import FloorState


def _update_sentry(game, sentry: Sentry, floor: FloorState, floor_id: int) -> None:
    left, top, right, bottom = sentry.watch_room
    target = None
    for p in game._players_on_floor(floor_id):
        if not p.is_alive or p.is_downed:
            continue
        if not (left < p.pos.x < right and top < p.pos.y < bottom):
            continue
        if floor.grid[p.pos.y][p.pos.x] != TileType.FLOOR_WOOD:
            continue
        if not game._is_in_los(sentry.pos, p.pos, floor_id=floor_id):
            continue
        target = p
        break

    if target is None:
        if sentry.charging:
            sentry.charging = False
            sentry.charge_ticks_left = 0
            game.add_event("SENTRY_IDLE", {"mob": sentry.id}, floor_id=floor_id)
        return

    if not sentry.charging:
        sentry.charging = True
        sentry.charge_ticks_left = sentry.initial_charge_ticks
        game.add_event("SENTRY_CHARGE", {
            "mob": sentry.id, "target": target.id,
        }, floor_id=floor_id)
        game.add_event("PLAY_SOUND", {"sound": "CHARGEUP"}, floor_id=floor_id)
        return

    sentry.charge_ticks_left -= 1
    if sentry.charge_ticks_left > 0:
        return

    sentry.charging = False
    depth = sentry.sentry_depth
    dmg = random.randint(2 + depth // 2, 4 + depth)
    taken = target.take_damage(dmg)
    game.add_event("SENTRY_ZAP", {
        "mob": sentry.id, "target": target.id,
        "x": target.pos.x, "y": target.pos.y,
    }, floor_id=floor_id)
    game.add_event("PLAY_SOUND", {"sound": "ZAP"}, floor_id=floor_id)
    game.add_event("ATTACK", {
        "source": sentry.id, "target": target.id,
        "damage": taken, "surprise": False,
    }, floor_id=floor_id)
    if taken > 0:
        game.add_event("DAMAGE", {
            "target": target.id, "amount": taken,
            "source_x": sentry.pos.x, "source_y": sentry.pos.y,
            "projectile": "beam",
        }, floor_id=floor_id)
