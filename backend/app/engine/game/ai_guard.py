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

from app.engine.entities.mobs import Guard
from app.engine.game.floor_state import FloorState


def _update_guard(game, guard: Guard, floor: FloorState, floor_id: int) -> bool:
    """On first hunt: pull chain → wake every mob on the floor."""
    if guard.ai_state != "hunting" or guard.chain_pulled:
        return False

    guard.chain_pulled = True

    target = game._find_nearest_player(guard.pos, floor_id)
    for mob in floor.mobs.values():
        if mob.id == guard.id or not mob.is_alive:
            continue
        if mob.ai_state in ("idle", "sleeping", "wandering"):
            mob.ai_state = "hunting"
            if target is not None:
                from app.engine.entities.base import Position
                mob.last_known_target_pos = Position(
                    x=target.pos.x, y=target.pos.y
                )

    game.add_event(
        "GUARD_CHAIN_PULL",
        {"mob": guard.id, "x": guard.pos.x, "y": guard.pos.y},
        floor_id=floor_id,
    )
    game.add_event("PLAY_SOUND", {"sound": "ALERT"}, floor_id=floor_id)
    return False  # let normal movement proceed this tick
