# Copyright (C) 2026 ArtemNikov
#
"""Death bookkeeping for a mob killed by damage that has no attacker
(bleeding, deferred damage): the same steps every DoT path runs."""

from app.engine.entities.items.consumables import Gold
from app.engine.systems.loot import roll_drops


def finish_dot_kill(game, mob, floor_id: int) -> None:
    floor = game._get_or_create_floor(floor_id)
    if mob.id not in floor.mobs:
        return
    mob.hp = 0
    mob.is_alive = False
    players = list(game._players_on_floor(floor_id))
    mob.die(floor_mobs=floor.mobs, tile_x=mob.pos.x, tile_y=mob.pos.y, players=players)
    game.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
    game.handle_mob_death(mob, floor, floor_id)
    drops = roll_drops(mob, game.drop_counters, mob.pos.x, mob.pos.y, players=players)
    for item in drops:
        floor.items[item.id] = item
    if any(isinstance(d, Gold) for d in drops):
        game.add_event("GOLD_DROP", {"x": mob.pos.x, "y": mob.pos.y}, floor_id=floor_id)
