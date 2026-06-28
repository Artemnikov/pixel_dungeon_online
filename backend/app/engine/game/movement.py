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
"""Movement and combat for GameInstance.

Handles held-direction intent, stepping (with bump-attacks, pickups, door
unlocking, traps and stair traversal) and ranged/thrown/wand attacks.
"""

import random
import time
import uuid
from typing import Optional

from app.engine.dungeon.generator import TileType
from app.engine.entities.base import (
    Amulet,
    Bow,
    Dewdrop,
    Faction,
    Gold,
    Chest,
    Key,
    Mob as MobEntity,
    MissileWeapon,
    Player,
    Position,
    RevivingPotion,
    SpiritBow,
    Staff,
    Throwable,
    Wand,
    ZapContext,
    Waterskin,
    Weapon,
    is_immune,
)
from app.engine.entities.buffs import add_buff, get_buff, has_buff, remove_buff
from app.engine.entities.mobs import DM300, Goo, Wraith
from app.engine.entities.subclasses import Talent
from app.engine.systems.ballistica import ballistica_trace
from app.engine.systems.combat import resolve_melee_attack, resolve_ranged_attack
from app.engine.systems.loot import roll_drops
from app.engine.game.constants import KEY_TIME_TO_UNLOCK, MAX_FLOOR_ID
from app.engine.game.terrain_effects import press_cell


def _effective_wand_damage(w, lvl_bonus: int = 0) -> int:
    if hasattr(w, 'damage_roll_buffed'):
        return w.damage_roll_buffed(lvl_bonus=lvl_bonus)
    return w.damage


class MovementCombatMixin:
    def _spend_unlock_action(self, player: Player) -> None:
        player.action_until = max(player.action_until, time.time() + KEY_TIME_TO_UNLOCK)

    def _items_at(self, floor, x: int, y: int):
        return [item for item in floor.items.values() if item.pos and item.pos.x == x and item.pos.y == y]

    def _find_room_containing(self, floor, x: int, y: int):
        for room in floor.rooms:
            if room.x <= x < room.x + room.width and room.y <= y < room.y + room.height:
                return room
        return None

    def _spawn_wraiths_around(self, floor, floor_id: int, player: Player) -> None:
        positions = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x, y = player.pos.x + dx, player.pos.y + dy
                if not (0 <= x < floor.width and 0 <= y < floor.height):
                    continue
                if not floor.flags or not floor.flags.passable[y][x]:
                    continue
                if any(m.is_alive and m.pos.x == x and m.pos.y == y for m in floor.mobs.values()):
                    continue
                if any(p.is_alive and p.pos.x == x and p.pos.y == y for p in self._players_on_floor(floor_id)):
                    continue
                positions.append((x, y))
        for x, y in positions[:4]:
            wid = str(uuid.uuid4())
            wraith = Wraith(id=wid, type="mob", pos=Position(x=x, y=y), faction=Faction.DUNGEON)
            attack = 10 + floor_id
            wraith.floor_level = floor_id
            wraith.attack_skill = attack
            wraith.defense_skill = attack * 5
            wraith.damage_min = 1 + floor_id // 2
            wraith.damage_max = 2 + floor_id
            floor.mobs[wid] = wraith
            self.add_event("SPAWN_MOB", {"mob": wraith.model_dump()}, floor_id=floor_id)

    def _drop_chest_contents(self, floor, chest: Chest, x: int, y: int) -> None:
        for contained in chest.contents:
            item = contained.model_copy(deep=True)
            item.id = str(uuid.uuid4())
            item.pos = Position(x=x, y=y)
            floor.items[item.id] = item

    def _shatter_other_crystal_chests(self, floor, floor_id: int, chest: Chest) -> None:
        if chest.pos is None:
            return
        room = self._find_room_containing(floor, chest.pos.x, chest.pos.y)
        if room is None:
            return
        for item_id, item in list(floor.items.items()):
            if item_id == chest.id or not isinstance(item, Chest) or item.chest_type != "CRYSTAL_CHEST" or item.pos is None:
                continue
            if room.x <= item.pos.x < room.x + room.width and room.y <= item.pos.y < room.y + room.height:
                del floor.items[item_id]
                self.add_event("CRYSTAL_CHEST_SHATTER", {"x": item.pos.x, "y": item.pos.y}, floor_id=floor_id)

    def _try_open_chest(self, player: Player, floor, floor_id: int, chest: Chest) -> bool:
        if chest.pos is None:
            return False
        if chest.chest_type == "LOCKED_CHEST" and not player.remove_key("golden", floor_id):
            self.add_event("LOCKED", {"player": player.id, "x": chest.pos.x, "y": chest.pos.y}, floor_id=floor_id)
            return False
        if chest.chest_type == "CRYSTAL_CHEST" and not player.remove_key("crystal", floor_id):
            self.add_event("LOCKED", {"player": player.id, "x": chest.pos.x, "y": chest.pos.y}, floor_id=floor_id)
            return False

        self._spend_unlock_action(player)
        x, y = chest.pos.x, chest.pos.y
        floor.items.pop(chest.id, None)
        if chest.chest_type == "CRYSTAL_CHEST":
            self._shatter_other_crystal_chests(floor, floor_id, chest)
        if chest.chest_type == "TOMB":
            self.add_event("PLAY_SOUND", {"sound": "TOMB"}, floor_id=floor_id)
            self._spawn_wraiths_around(floor, floor_id, player)
        elif chest.chest_type in ("SKELETON", "REMAINS"):
            self.add_event("PLAY_SOUND", {"sound": "BONES"}, floor_id=floor_id)
        else:
            self.add_event("PLAY_SOUND", {"sound": "UNLOCK"}, floor_id=floor_id)
        self._drop_chest_contents(floor, chest, x, y)
        self.add_event("OPEN_CHEST", {"player": player.id, "x": x, "y": y, "chest_type": chest.chest_type}, floor_id=floor_id)
        return True

    def set_move_intent(self, entity_id: str, dx: int, dy: int):
        """Set/clear a player's held keyboard direction. The update tick paces the
        actual stepping at AUTO_MOVE_INTERVAL."""
        player = self.players.get(entity_id)
        if player is None:
            return
        if dx == 0 and dy == 0:
            player.move_intent = None
            return
        was_moving = player.move_intent is not None
        player.move_intent = (dx, dy)
        player.path_queue = []
        # Grant an immediate first step only when starting from rest. Changing
        # direction mid-walk keeps the existing cadence, so rapidly switching keys
        # (e.g. the two keydowns that begin a diagonal) can't burst multiple steps
        # inside one AUTO_MOVE_INTERVAL.
        if not was_moving:
            player.last_auto_move_time = 0.0

    def move_entity(self, entity_id: str, dx: int, dy: int):
        floor_id, entity = self._get_floor_for_entity(entity_id)
        if entity is None or floor_id is None:
            return

        floor = self._get_or_create_floor(floor_id)

        if isinstance(entity, Player) and time.time() < entity.action_until:
            return

        if isinstance(entity, Player) and entity.is_downed:
            return

        new_x = entity.pos.x + dx
        new_y = entity.pos.y + dy

        if not (0 <= new_x < floor.width and 0 <= new_y < floor.height):
            return

        # Any movement attempt cancels a stale chasm-fall confirmation prompt
        # (the player did something else instead of confirming).
        if isinstance(entity, Player):
            entity.pending_chasm_fall = None

        # Diagonal moves past a wall corner are allowed, matching SPD's PathFinder
        # (it only checks the destination cell's passability, not the orthogonal cells).

        target_entity = None
        for p in self._players_on_floor(floor_id):
            if p.id != entity_id and p.is_alive and p.pos.x == new_x and p.pos.y == new_y:
                target_entity = p
                break

        if not target_entity:
            for m in floor.mobs.values():
                if m.id != entity_id and m.is_alive and m.pos.x == new_x and m.pos.y == new_y:
                    target_entity = m
                    break

        if target_entity:
            # Sheep interaction: player bump → baa message, 1s action cost, sound
            if isinstance(entity, Player) and getattr(target_entity, "name", "") == "Sheep":
                entity.action_until = time.time() + 1.0
                baa = random.choice(["Baa!", "Baa?", "Baa.", "Baa..."])
                self.add_event("MESSAGE", {"text": baa}, floor_id=floor_id, player_id=entity.id)
                self.add_event("PLAY_SOUND", {"sound": "SHEEP",
                                               "rate": random.uniform(0.91, 1.1)},
                               floor_id=floor_id)
                sheep_buff = get_buff(target_entity.buffs, "sheep_timer")
                if sheep_buff and sheep_buff.remaining >= 20:
                    sheep_buff.remaining = 0
                return

            # Mirrors SPD's enemyInFOV check (Mob.java:252): a mob cannot
            # perceive an invisible player, so it treats the tile as blocked
            # rather than attacking.
            if isinstance(entity, MobEntity) and isinstance(target_entity, Player) and target_entity.invisible > 0:
                return

            if (
                isinstance(entity, Player)
                and isinstance(target_entity, Player)
                and target_entity.is_downed
                and entity.faction == target_entity.faction
            ):
                revive_potion_idx = next(
                    (i for i, item in enumerate(entity.inventory) if isinstance(item, RevivingPotion)),
                    -1,
                )
                if revive_potion_idx != -1:
                    entity.inventory.pop(revive_potion_idx)
                    target_entity.is_downed = False
                    target_entity.hp = target_entity.get_total_max_hp() // 2
                    self.add_event("REVIVE", {"target": target_entity.id, "source": entity.id}, floor_id=floor_id)
                    return

            if entity.faction != target_entity.faction:
                if isinstance(entity, Player) and entity.is_downed:
                    return

                current_time = time.time()
                cooldown = entity.attack_cooldown
                if isinstance(entity, Player) and entity.equipped_weapon:
                    cooldown = entity.equipped_weapon.attack_cooldown
                if isinstance(entity, Player):
                    from app.engine.entities.rings import furor_multiplier
                    cooldown /= furor_multiplier(entity)

                if current_time - entity.last_attack_time < cooldown:
                    return

                entity.last_attack_time = current_time

                # Parry (warrior combo move): a riposte-primed defender
                # counter-strikes the attacker before damage resolves.
                if isinstance(target_entity, Player) and target_entity.has_buff("riposte_tracker"):
                    self._riposte_counter(target_entity, entity, floor, floor_id)

                if isinstance(entity, Player):
                    entity._last_action = ""
                result = resolve_melee_attack(
                    entity, target_entity,
                    floor.mobs, entity.pos.x, entity.pos.y,
                    is_in_los=lambda a, b: self._is_in_los(a, b, floor_id=floor_id),
                    floor=floor,
                    add_event=lambda type, data, **kw: self.add_event(type, data, **{
                        "floor_id": floor_id,
                        "source_player_id": entity.id if isinstance(entity, Player) else None,
                        **kw,
                    }),
                )
                if result["missed"]:
                    self.add_event("MISS", {"source": entity.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
                    self.add_event("ATTACK", {"source": entity.id, "target": target_entity.id, "damage": 0, "surprise": False}, floor_id=floor_id)
                    return
                dmg = result["damage"]
                self.add_event("ATTACK", {
                    "source": entity.id,
                    "target": target_entity.id,
                    "damage": dmg,
                    "surprise": result["surprise"],
                    "crit": result.get("crit", False),
                    "grim_proc": result.get("grim_proc", False),
                }, floor_id=floor_id)
                # SPD Char.java:509 plays hitSound(Random.Float(0.87f, 1.15f)),
                # then KindOfWeapon multiplies by hitSoundPitch. Mobs use the
                # default HIT/HIT_BODY at pitch 1.0 (no mob overrides hitSound).
                pitch_jitter = random.uniform(0.87, 1.15)
                if isinstance(entity, Player):
                    weapon = getattr(getattr(entity, "belongings", None), "weapon", None)
                    if result.get("crit"):
                        sound = "HIT_STRONG"
                        rate = pitch_jitter
                    elif weapon and getattr(weapon, "hit_sound", None):
                        sound = weapon.hit_sound
                        rate = pitch_jitter * getattr(weapon, "hit_sound_pitch", 1.0)
                    else:
                        sound = "HIT_SLASH"
                        rate = pitch_jitter
                    self.add_event("PLAY_SOUND", {"sound": sound, "rate": rate}, floor_id=floor_id, source_player_id=entity.id)
                else:
                    # Mob melee: broadcast HIT_BODY from the mob's position so
                    # every player who can see it hears the hit.
                    self.add_event("PLAY_SOUND", {"sound": "HIT_BODY", "rate": pitch_jitter, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
                if dmg > 0:
                    self.add_event("DAMAGE", {
                        "target": target_entity.id,
                        "amount": dmg,
                        "grim_proc": result.get("grim_proc", False),
                    }, floor_id=floor_id)
                    if result.get("grim_proc"):
                        self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=entity.id)
                    if isinstance(target_entity, Player) and isinstance(entity, Player):
                        # Friendly-fire only: mob-on-player hits are already
                        # covered by the broadcast HIT_BODY above.
                        self.add_event("PLAY_SOUND", {"sound": "HIT_BODY"}, floor_id=floor_id, source_player_id=target_entity.id)
                    if isinstance(target_entity, Player):
                        if target_entity.hp / target_entity.get_total_max_hp() <= 0.3:
                            self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=target_entity.id)
                    if isinstance(target_entity, Goo) and isinstance(entity, Player):
                        self._goo_add_locked_floor_time(floor_id, entity, dmg)

                self._maybe_trigger_dm300_supercharge(target_entity, floor, floor_id, entity.pos)

                # Warrior subclass: combo / berserk events after successful damage
                if isinstance(entity, Player) and dmg > 0:
                    if entity.subclass_info.subclass == "gladiator":
                        self.add_event("COMBO_UPDATE", {"player": entity.id, "count": entity.combo_count}, floor_id=floor_id, source_player_id=entity.id)
                        if entity.combo_count in (2, 4, 6, 8, 10):
                            moves = {2: "clobber", 4: "slam", 6: "parry", 8: "crush", 10: "fury"}
                            self.add_event("COMBO_MOVE_UNLOCKED", {"player": entity.id, "move": moves[entity.combo_count]}, floor_id=floor_id, source_player_id=entity.id)
                    if entity.subclass_info.subclass == "berserker":
                        self.add_event("RAGE_CHANGED", {"player": entity.id, "power": entity.berserk_power}, floor_id=floor_id, source_player_id=entity.id)

                if not target_entity.is_alive:
                    if isinstance(target_entity, MobEntity):
                        self.process_death_mark_kill(entity, target_entity, floor, floor_id)
                        self.handle_mob_death(target_entity, floor, floor_id)
                    if isinstance(entity, Player):
                        self.on_kill(entity, target_entity, floor.mobs, floor_id)
                        # Lethal Momentum (warrior T2): a killing blow that
                        # procced the free follow-up doesn't consume the
                        # attack's cooldown, allowing an immediate re-attack.
                        if remove_buff(entity.buffs, "lethal_momentum_tracker"):
                            entity.last_attack_time = 0.0
                    self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
                    if isinstance(target_entity, MobEntity):
                        target_entity.die(
                            attacker=entity,
                            floor_mobs=floor.mobs,
                            tile_x=target_entity.pos.x,
                            tile_y=target_entity.pos.y,
                            players=list(self._players_on_floor(floor_id)),
                        )
                    if isinstance(entity, Player) and isinstance(target_entity, MobEntity):
                        if entity.earn_exp(target_entity.exp):
                            self.on_talent_level_up(entity)
                        drops = roll_drops(target_entity, self.drop_counters, target_entity.pos.x, target_entity.pos.y, players=list(self._players_on_floor(floor_id)))
                        for item in drops:
                            floor.items[item.id] = item
                        if any(isinstance(d, Gold) for d in drops):
                            self.add_event("GOLD_DROP", {"x": target_entity.pos.x, "y": target_entity.pos.y}, floor_id=floor_id)
            return

        tile = floor.grid[new_y][new_x]
        if tile in (TileType.LOCKED_DOOR, TileType.CRYSTAL_DOOR, TileType.LOCKED_EXIT):
            if not isinstance(entity, Player):
                return
            self._try_unlock_locked_door(entity, floor, new_x, new_y)
            return

        if isinstance(entity, Player):
            chest = next((item for item in self._items_at(floor, new_x, new_y) if isinstance(item, Chest)), None)
            if chest is not None:
                self._try_open_chest(entity, floor, floor_id, chest)
                return

        if tile == TileType.CHASM:
            # Mobs never voluntarily step into a chasm (AI pathing already
            # avoids it via AVOID/PIT — see vision.py); this only guards
            # against an entity somehow ending up adjacent regardless.
            if isinstance(entity, Player) and floor_id < MAX_FLOOR_ID:
                entity.pending_chasm_fall = (new_x, new_y)
                self.add_event("CHASM_PROMPT", {"x": new_x, "y": new_y}, floor_id=floor_id, player_id=entity.id)
            return

        if not floor.flags or not floor.flags.passable[new_y][new_x]:
            return

        # Boss mobs (e.g. Goo) live and fight inside their arena, which can
        # overlap the level's entrance/secret rooms (e.g. the boss floor's
        # Rat King room) - the safe-room movement restriction is meant to
        # keep regular wandering mobs out of entrance/exit rooms, not to trap
        # a boss inside its own spawn room.
        if (not isinstance(entity, Player) and getattr(entity, "type", None) != "boss"
                and self._is_in_safe_room(floor, new_x, new_y)):
            return

        old_x, old_y = entity.pos.x, entity.pos.y
        entity.move(dx, dy)

        # Fire tiles ignite entities on contact (SPD: Blob checks on movement)
        for b in floor.blob_areas.values():
            if b.get("type") == "fire" and (new_x, new_y) in b.get("cells", set()):
                if not has_buff(entity.buffs, "burning") and not is_immune(entity, "burning"):
                    add_buff(entity.buffs, "burning", duration=8.0, level=1, stack_mode="extend")

        # Door enter/leave tile mutation: stepping onto a closed DOOR opens it;
        # leaving an open door closes it (if no other entity is on it).
        door_changed = False
        door_patches = []
        if floor.grid[entity.pos.y][entity.pos.x] == TileType.DOOR:
            floor.grid[entity.pos.y][entity.pos.x] = TileType.OPEN_DOOR
            door_changed = True
            door_patches.append({"x": entity.pos.x, "y": entity.pos.y, "tile": TileType.OPEN_DOOR})
        if floor.grid[old_y][old_x] == TileType.OPEN_DOOR:
            has_entity = any(
                p.pos.x == old_x and p.pos.y == old_y
                for p in self._players_on_floor(floor_id)
            )
            if not has_entity:
                has_entity = any(
                    m.is_alive and m.pos.x == old_x and m.pos.y == old_y
                    for m in floor.mobs.values()
                )
            if not has_entity:
                floor.grid[old_y][old_x] = TileType.DOOR
                door_changed = True
                door_patches.append({"x": old_x, "y": old_y, "tile": TileType.DOOR})

        if door_changed:
            floor.rebuild_flags()
            # StateUpdateMessage doesn't carry the grid (only INIT does, on
            # floor change) — clients only learn about this tile flip via a
            # MAP_PATCH event, same mechanism as unlocking/grass-trample.
            self.add_event("MAP_PATCH", {"tiles": door_patches}, floor_id=floor_id)

        # Position changed: door mutation may have changed flags and FOV.
        self._invalidate_fov_cache()

        # Terrain interaction (trample grass, trigger plants, etc.)
        result = press_cell(floor, (entity.pos.x, entity.pos.y), entity)
        if result["tile_changed"]:
            self.add_event("MAP_PATCH", {"tiles": [{"x": entity.pos.x, "y": entity.pos.y, "tile": floor.grid[entity.pos.y][entity.pos.x]}]}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "STEP_GRASS", "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id, source_player_id=entity.id if isinstance(entity, Player) else None)
            # HighGrass.trample()'s CellEmitter.get(pos).burst(LeafParticle.LEVEL_SPECIFIC, 4)
            self.add_event("LEAF_BURST", {"x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
        if result["triggered_plant"]:
            self.add_event("PLAY_SOUND", {"sound": "PLANT_TRIGGER", "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id, source_player_id=entity.id if isinstance(entity, Player) else None)

        if isinstance(entity, Player):
            self.add_event("MOVE", {"entity": entity_id, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)
            # Freerunner builds Momentum on each step.
            self.gain_momentum(entity)
            # Rejuvenating Steps (huntress T2): heal small amount per step
            rs = entity.talent_info.level("rejuvenating_steps")
            if rs > 0:
                heal = rs
                entity.hp = min(entity.get_total_max_hp(), entity.hp + heal)
                self.add_event("HEAL", {"target": entity.id, "amount": heal, "x": entity.pos.x, "y": entity.pos.y}, floor_id=floor_id)

        if isinstance(entity, Player):
            items_to_pickup = [
                i_id
                for i_id, i in floor.items.items()
                if i.pos and i.pos.x == entity.pos.x and i.pos.y == entity.pos.y
                and i.type != "grave"  # graves are scenery, not pickable
                and not i.for_sale  # shop stock is bought via SHOP_BUY, not auto-picked-up
            ]
            for i_id in items_to_pickup:
                item = floor.items[i_id]
                if isinstance(item, Gold):
                    entity.gold += item.quantity
                    del floor.items[i_id]
                    self.add_event("PICKUP_GOLD", {"player": entity.id, "amount": item.quantity}, floor_id=floor_id)
                    continue
                if isinstance(item, Dewdrop):
                    waterskin = next(
                        (i for i in entity.inventory if isinstance(i, Waterskin) and not i.is_full()),
                        None,
                    )
                    if waterskin is not None:
                        waterskin.volume = min(Waterskin.MAX_VOLUME, waterskin.volume + item.quantity)
                        del floor.items[i_id]
                        self.add_event("COLLECT_DEW", {"player": entity.id, "item": waterskin.id}, floor_id=floor_id)
                        continue
                if isinstance(item, Key):
                    entity.add_key(item.key_id, floor_id, item.name)
                    del floor.items[i_id]
                    self.add_event("PICKUP_KEY", {"player": entity.id, "key_id": item.key_id, "name": item.name}, floor_id=floor_id)
                    continue
                if entity.add_to_inventory(item):
                    del floor.items[i_id]
                    self.add_event("PICKUP", {"player": entity.id, "item": item.name}, floor_id=floor_id)
                    if entity.is_admin and item.type in ("potion", "scroll"):
                        self.identify_kind(item)

            self._trigger_trap_if_needed(floor, entity, floor_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_DOWN and entity.floor_id < MAX_FLOOR_ID:
            first_visit = entity.floor_id + 1 > entity.floors_explored
            self._move_player_to_floor(entity, entity.floor_id + 1, TileType.STAIRS_UP)
            self.add_event("STAIRS_DOWN", {"player": entity_id, "first_visit": first_visit}, player_id=entity_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_UP and entity.floor_id > 1:
            self._move_player_to_floor(entity, entity.floor_id - 1, TileType.STAIRS_DOWN)
            self.add_event("STAIRS_UP", {"player": entity_id}, player_id=entity_id)

        if isinstance(entity, Player) and tile == TileType.STAIRS_UP and entity.floor_id == 1:
            if any(isinstance(it, Amulet) for it in entity.belongings.all_items()):
                self._complete_victory(entity, floor, floor_id)
            else:
                self.add_event(
                    "MESSAGE",
                    {"text": "You can't leave yet, the rest of the dungeon awaits below!"},
                    player_id=entity_id,
                )

    def _maybe_trigger_dm300_supercharge(self, target: "MobEntity", floor, floor_id: int, near_pos: Position):
        """Trigger DM300 pylon activation if target is DM300 with pending activation."""
        if isinstance(target, DM300) and target.pending_pylon_activation:
            target.pending_pylon_activation = False
            self.add_event("DM300_SUPERCHARGE", {"mob": target.id}, floor_id=floor_id)
            self._activate_pylon(floor, floor_id, near_pos=near_pos)

    def perform_ranged_attack(self, player_id: str, item_id: str, target_x: int, target_y: int) -> Optional[int]:
        player = self.players.get(player_id)
        if not player or player.is_downed:
            return None

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        item = player.belongings.get_item(item_id)

        if not item:
            return None

        is_throwable = isinstance(item, Throwable)
        is_weapon = isinstance(item, (Weapon, Bow, SpiritBow))
        is_wand = isinstance(item, Wand)
        is_staff = isinstance(item, Staff)
        is_bow = isinstance(item, (Bow, SpiritBow))

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
        from app.engine.entities.rings import furor_multiplier
        cooldown /= furor_multiplier(player)

        if (current_time - player.last_attack_time) < cooldown:
            return None

        dist = abs(player.pos.x - target_x) + abs(player.pos.y - target_y)
        if not is_bow:
            if not is_wand and not is_staff:
                max_range = item.get_reach() if hasattr(item, "get_reach") else getattr(item, "range", 5)
                if dist > max_range:
                    return None
            if is_wand or is_staff:
                bfloor = self._get_or_create_floor(floor_id)
                target_x, target_y = ballistica_trace(
                    player.pos.x, player.pos.y, target_x, target_y,
                    bfloor.flags, bfloor.width, bfloor.height,
                    list(self._players_on_floor(floor_id)),
                    list(bfloor.mobs.values()),
                    player.id,
                )
            elif not self._is_in_los(player.pos, Position(x=target_x, y=target_y), floor_id=floor_id):
                return None

        player.last_attack_time = current_time
        player._last_action = "ranged"
        projectile_type = getattr(item, "projectile_type", "arrow")

        target_entity = None
        for p in self._players_on_floor(floor_id):
            if p.id != player_id and p.pos.x == target_x and p.pos.y == target_y:
                target_entity = p
                break

        if not target_entity:
            for m in floor.mobs.values():
                if m.is_alive and m.pos.x == target_x and m.pos.y == target_y:
                    target_entity = m
                    break

        beam_type = getattr(item, "beam_type", None)
        target_hp_ratio = None
        if beam_type == "health_ray" and target_entity and target_entity.get_total_max_hp() > 0:
            target_hp_ratio = target_entity.hp / target_entity.get_total_max_hp()
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
        if target_entity and player.faction != target_entity.faction:
            if isinstance(item, SpiritBow):
                atk_min = item.dmg_min(player.level)
                atk_max = item.dmg_max(player.level)
            elif effective_wand is not None:
                # Magic Charge: boost non-Magic-Missile wand by +1 level on next use
                magic_charge_lvl = 0
                if (
                    effective_wand.kind != "wand_magic_missile"
                    and player.has_buff("magic_charge")
                ):
                    magic_charge_lvl = 1
                    player.remove_buff("magic_charge")
                atk_min = atk_max = _effective_wand_damage(effective_wand, lvl_bonus=magic_charge_lvl)
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
            )
            player.damage_min, player.damage_max = old_min, old_max
            if result["missed"]:
                self.add_event("MISS", {"source": player.id, "target": target_entity.id, "defense_verb": result.get("defense_verb", "dodged")}, floor_id=floor_id)
            damage_dealt = result["damage"]
            ranged_event_data["crit"] = result.get("crit", False)
            ranged_event_data["grim_proc"] = result.get("grim_proc", False)

            if damage_dealt > 0:
                _magic_projectiles = {"magic_bolt", "magic_missile", "fire_bolt", "frost", "corrosion", "foliage", "force", "beacon", "shadow", "rainbow", "earth", "ward", "shaman_red", "shaman_blue", "shaman_purple", "elmo", "poison", "light_missile", "lightning", "beam"}
                if projectile_type in _magic_projectiles:
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
                    if target_entity.hp / target_entity.get_total_max_hp() <= 0.3:
                        self.add_event("PLAY_SOUND", {"sound": "HEALTH_WARN"}, player_id=target_entity.id)
                if isinstance(target_entity, Goo):
                    self._goo_add_locked_floor_time(floor_id, player, damage_dealt)

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
                if isinstance(target_entity, MobEntity):
                    self.process_death_mark_kill(player, target_entity, floor, floor_id)
                self.on_kill(player, target_entity, floor.mobs, floor_id)
                self.add_event("DEATH", {"target": target_entity.id}, floor_id=floor_id)
                if isinstance(target_entity, MobEntity):
                    if player.earn_exp(target_entity.exp):
                        self.on_talent_level_up(player)
                    drops = roll_drops(target_entity, self.drop_counters, target_entity.pos.x, target_entity.pos.y, players=list(self._players_on_floor(floor_id)))
                    for d in drops:
                        floor.items[d.id] = d
                    if any(isinstance(d, Gold) for d in drops):
                        self.add_event("GOLD_DROP", {"x": target_entity.pos.x, "y": target_entity.pos.y}, floor_id=floor_id)

        # Delegate wand-specific post-damage effects to the wand's handle_zap
        if effective_wand is not None and isinstance(effective_wand, Wand):
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
            )
            effective_wand.handle_zap(ctx)

        if is_wand or is_staff:
            wand_item = staff_wand if is_staff else item
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
        elif not is_bow:
            removed = player.belongings.backpack.detach(item.id)
            if removed is not None and player.belongings.get_item(item.id) is None:
                player.quickslot.convert_to_placeholder(removed)
                removed.pos = Position(x=target_x, y=target_y)
                floor.items[removed.id] = removed

        return damage_dealt
