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
import math
import random
import uuid
from typing import Optional

from app.engine.dungeon.constants import TileType
from app.engine.entities.base import Faction, Position
from app.engine.entities.player import Mob, Player
from app.engine.entities.buffs import add_buff
from app.engine.entities.subclasses import ArmorAbilityType, COST_ARMOR_ABILITY, COST_ENDURE, Subclass, Talent
from app.engine.systems.combat import resolve_melee_attack

# Rogue armor ability charge costs (SPD baseChargeUse).
COST_SMOKE_BOMB = 50
COST_DEATH_MARK = 25
COST_SHADOW_CLONE = 35


# Heroic Energy (warrior T4, universal): reduces any armor ability's charge
# cost. [0,1,2,3,4] points -> multiplier.
_HEROIC_ENERGY_MULT = [1.0, 0.88, 0.77, 0.68, 0.60]


def _heroic_energy_mult(player: Player) -> float:
    pts = player.subclass_info.talent_info.level(Talent.HEROIC_ENERGY)
    return _HEROIC_ENERGY_MULT[min(pts, 4)]


class ArmorAbilitiesMixin:
    def _finalize_endure(self, player: Player) -> None:
        banked = player.endure_banked
        player.endure_banked = 0.0
        if banked <= 0:
            return
        ti = player.subclass_info.talent_info
        sr = ti.level(Talent.SUSTAINED_RETRIBUTION)
        eto = ti.level(Talent.EVEN_THE_ODDS)
        if sr > 0:
            banked *= 1 + 0.15 * sr
        if eto > 0:
            floor = self._get_or_create_floor(player.floor_id)
            nearby = sum(
                1 for mob in floor.mobs.values()
                if mob.is_alive and mob.faction != Faction.PLAYER
                and max(abs(mob.pos.x - player.pos.x), abs(mob.pos.y - player.pos.y)) <= 2
            )
            banked *= 1 + nearby * 0.05 * eto
        player.endure_damage_bonus = banked
        player.endure_hits_left = 1 + sr

    def use_armor_ability(self, player_id: str, ability: str, target_x: Optional[int] = None, target_y: Optional[int] = None) -> None:
        player = self.players.get(player_id)
        if not player or player.is_downed or not player.is_alive:
            return

        floor_id = player.floor_id
        floor = self._get_or_create_floor(floor_id)

        if ability == ArmorAbilityType.HEROIC_LEAP:
            ti = player.subclass_info.talent_info
            body_slam = ti.level(Talent.BODY_SLAM)
            impact_wave = ti.level(Talent.IMPACT_WAVE)
            double_jump = ti.level(Talent.DOUBLE_JUMP)

            cost = int(COST_ARMOR_ABILITY * _heroic_energy_mult(player))
            if double_jump > 0:
                cost = int(cost * (0.84 ** double_jump))
            free_jump = double_jump > 0 and player.double_jump_ready

            if target_x is None or target_y is None:
                return
            if not (0 <= target_x < floor.width and 0 <= target_y < floor.height):
                return
            if floor.grid[target_y][target_x] == TileType.WALL:
                return
            dx = target_x - player.pos.x
            dy = target_y - player.pos.y
            dist = max(abs(dx), abs(dy))
            if dist < 1 or dist > 4:
                return
            if not free_jump and player.armor_charge < cost:
                return

            if free_jump:
                player.double_jump_ready = False
            else:
                player.armor_charge -= cost
                if double_jump > 0:
                    player.double_jump_ready = True

            player.pos.x = target_x
            player.pos.y = target_y
            self._invalidate_fov_cache()
            self.add_event("MOVE", {"entity": player.id, "x": target_x, "y": target_y}, floor_id=floor_id)
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)

            slammed = set()
            for dy_off in (-1, 0, 1):
                for dx_off in (-1, 0, 1):
                    if dx_off == 0 and dy_off == 0:
                        continue
                    cx, cy = target_x + dx_off, target_y + dy_off
                    if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                        continue
                    for mob in list(floor.mobs.values()):
                        if not (mob.is_alive and mob.pos.x == cx and mob.pos.y == cy):
                            continue
                        if body_slam > 0:
                            dmg = random.randint(body_slam, 4 * body_slam)
                            dmg += round(random.randint(player.get_dr_min(), player.get_dr_max()) * 0.25 * body_slam)
                            dmg -= random.randint(mob.get_dr_min(), mob.get_dr_max())
                            dmg = max(0, dmg)
                            mob.hp -= dmg
                            slammed.add(mob.id)
                            self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                            if not mob.is_alive:
                                self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)

            if impact_wave > 0:
                for dy_off in (-1, 0, 1):
                    for dx_off in (-1, 0, 1):
                        if dx_off == 0 and dy_off == 0:
                            continue
                        cx, cy = target_x + dx_off, target_y + dy_off
                        if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                            continue
                        for mob in list(floor.mobs.values()):
                            if not (mob.is_alive and mob.pos.x == cx and mob.pos.y == cy):
                                continue
                            if mob.id in slammed:
                                continue
                            knock = 1 + impact_wave
                            knock_x = cx + (cx - target_x) * knock
                            knock_y = cy + (cy - target_y) * knock
                            if 0 <= knock_x < floor.width and 0 <= knock_y < floor.height and floor.grid[knock_y][knock_x] != TileType.WALL:
                                mob.pos.x = knock_x
                                mob.pos.y = knock_y
                            if random.randint(0, 3) < impact_wave:
                                add_buff(mob.buffs, "vulnerable", duration=5.0, level=1)

        elif ability == ArmorAbilityType.SHOCKWAVE:
            ti = player.subclass_info.talent_info
            expanding = ti.level(Talent.EXPANDING_WAVE)
            striking = ti.level(Talent.STRIKING_WAVE)
            shock_force = ti.level(Talent.SHOCK_FORCE)

            cost = int(COST_ARMOR_ABILITY * _heroic_energy_mult(player))
            if player.armor_charge < cost:
                return
            player.armor_charge -= cost
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)

            scaling_str = player.get_effective_strength() - 10
            max_dist = 5 + expanding
            cone_deg = 60 + 15 * expanding
            half_cone = math.radians(cone_deg / 2)

            tx = target_x if target_x is not None else player.pos.x
            ty = target_y if target_y is not None else player.pos.y
            dir_x, dir_y = tx - player.pos.x, ty - player.pos.y
            if dir_x == 0 and dir_y == 0:
                dir_x, dir_y = 0, 1
            dir_angle = math.atan2(dir_y, dir_x)

            hit_any = False
            for mob in list(floor.mobs.values()):
                if not mob.is_alive or mob.faction == Faction.PLAYER:
                    continue
                mx, my = mob.pos.x - player.pos.x, mob.pos.y - player.pos.y
                dist = max(abs(mx), abs(my))
                if dist < 1 or dist > max_dist:
                    continue
                angle = math.atan2(my, mx)
                diff = abs(math.atan2(math.sin(angle - dir_angle), math.cos(angle - dir_angle)))
                if diff > half_cone:
                    continue

                dmg = random.randint(5 + scaling_str, 10 + 2 * scaling_str)
                dmg -= random.randint(mob.get_dr_min(), mob.get_dr_max())
                if shock_force > 0:
                    dmg = int(dmg * (1 + 0.2 * shock_force))
                dmg = max(0, dmg)
                mob.hp -= dmg
                hit_any = True
                self.add_event("DAMAGE", {"target": mob.id, "amount": dmg}, floor_id=floor_id)
                if not mob.is_alive:
                    self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
                    continue

                if shock_force > 0 and random.randint(0, 3) < shock_force:
                    add_buff(mob.buffs, "paralysis", duration=5.0, level=1)
                else:
                    knock_x = mob.pos.x + (mob.pos.x - player.pos.x)
                    knock_y = mob.pos.y + (mob.pos.y - player.pos.y)
                    if 0 <= knock_x < floor.width and 0 <= knock_y < floor.height and floor.grid[knock_y][knock_x] != TileType.WALL:
                        mob.pos.x = knock_x
                        mob.pos.y = knock_y
                    add_buff(mob.buffs, "cripple", duration=5.0, level=1)

                if striking > 0 and random.randint(0, 9) < 3 * striking:
                    self.add_event("PLAY_SOUND", {"sound": "HIT"}, floor_id=floor_id, source_player_id=player.id)
                    if player.subclass_info.subclass == "gladiator":
                        player.combo_count += 1
                        player.combo_timer = max(player.combo_timer, 5.0)
                    if striking >= 4:
                        add_buff(player.buffs, "striking_wave_tracker", duration=5.0, level=1)

            if hit_any:
                self._invalidate_fov_cache()

        elif ability == ArmorAbilityType.ENDURE:
            cost = int(COST_ENDURE * _heroic_energy_mult(player))
            if player.armor_charge < cost:
                return
            player.armor_charge -= cost
            player.endure_banked = 0.0
            add_buff(player.buffs, "endure_tracker", duration=12.0, level=1)
            # Endure + Combo (Gladiator): activating Endure while Combo is
            # active adds 3 turns to the combo timer.
            if player.subclass_info.subclass == Subclass.GLADIATOR and player.combo_count > 0:
                player.combo_timer += 3.0
            self.add_event("PLAY_SOUND", {"sound": "HIT_STRONG"}, floor_id=floor_id, source_player_id=player.id)

        elif ability == ArmorAbilityType.SMOKE_BOMB:
            self._ability_smoke_bomb(player, floor, floor_id, target_x, target_y)

        elif ability == ArmorAbilityType.DEATH_MARK:
            self._ability_death_mark(player, floor, floor_id, target_x, target_y)

        elif ability == ArmorAbilityType.SHADOW_CLONE:
            self._ability_shadow_clone(player, floor, floor_id, target_x, target_y)

    # --- Rogue abilities ---------------------------------------------------
    def _ability_smoke_bomb(self, player, floor, floor_id, target_x, target_y) -> None:
        # Blink up to 6 tiles in line-of-sight, blinding adjacent foes. Free-ish
        # for an invisible hero with Shadow Step. Mirrors SPD's SmokeBomb.
        if target_x is None or target_y is None:
            return
        if not (0 <= target_x < floor.width and 0 <= target_y < floor.height):
            return
        if floor.grid[target_y][target_x] == TileType.WALL:
            return
        dist = max(abs(target_x - player.pos.x), abs(target_y - player.pos.y))
        if dist < 1 or dist > 6:
            return
        if any(m.is_alive and m.pos.x == target_x and m.pos.y == target_y for m in floor.mobs.values()):
            return

        shadow_step = player.invisible > 0 and player.talent_info.has(Talent.SHADOW_STEP)
        cost = COST_SMOKE_BOMB
        if shadow_step:
            cost = int(cost * (0.84 ** player.talent_info.level(Talent.SHADOW_STEP)))
        if player.armor_charge < cost:
            return
        player.armor_charge -= cost

        body_replacement = player.talent_info.level(Talent.BODY_REPLACEMENT)
        if not shadow_step and body_replacement > 0:
            for mob in list(floor.mobs.values()):
                if mob.type == "ninja_log" and mob.owner_id == player.id:
                    mob.is_alive = False
                    self.add_event("DEATH", {"target": mob.id}, floor_id=floor_id)
            hp = 20 * body_replacement
            log = Mob(
                id=f"ninja_log_{uuid.uuid4().hex[:8]}",
                name="Ninja Log",
                type="ninja_log",
                pos=Position(x=player.pos.x, y=player.pos.y),
                hp=hp, max_hp=hp,
                attack=0, defense=0,
                defense_skill=0,
                dr_min=body_replacement, dr_max=3 * body_replacement,
                properties=["INORGANIC"],
                faction=Faction.PLAYER,
            )
            log.owner_id = player.id
            floor.mobs[log.id] = log
            self.add_event("SPAWN", {"entity": log.id, "x": log.pos.x, "y": log.pos.y, "kind": "ninja_log"}, floor_id=floor_id)

        player.pos.x, player.pos.y = target_x, target_y
        self._invalidate_fov_cache()
        self.add_event("MOVE", {"entity": player.id, "x": target_x, "y": target_y}, floor_id=floor_id)
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id, source_player_id=player.id)

        if not shadow_step:
            for mob in list(floor.mobs.values()):
                if not mob.is_alive or mob.faction == Faction.PLAYER:
                    continue
                if max(abs(mob.pos.x - target_x), abs(mob.pos.y - target_y)) <= 1:
                    add_buff(mob.buffs, "blinded", duration=5.0, level=1)
                    if getattr(mob, "ai_state", "") == "hunting":
                        mob.ai_state = "wandering"
            if player.talent_info.has(Talent.HASTY_RETREAT):
                dur = 1.0 + player.talent_info.level(Talent.HASTY_RETREAT)
                add_buff(player.buffs, "haste", duration=dur, level=1)
                player.add_buff("invisibility", duration=dur, level=1)

    def _ability_death_mark(self, player, floor, floor_id, target_x, target_y) -> None:
        # Mark a visible enemy: it takes +25% damage and, if slain while marked,
        # triggers Deathly Durability / Fear the Reaper talents.
        if target_x is None or target_y is None:
            return
        target = next((m for m in floor.mobs.values()
                       if m.is_alive and m.faction != Faction.PLAYER
                       and m.pos.x == target_x and m.pos.y == target_y), None)
        if target is None:
            return
        if not self._is_in_los(player.pos, target.pos, floor_id=floor_id):
            return

        # Double Mark: every other cast is free (and otherwise cheaper).
        double = player.talent_info.has(Talent.DOUBLE_MARK)
        cost = COST_DEATH_MARK
        if double and player.get_buff("double_mark_ready"):
            cost = 0
            player.remove_buff("double_mark_ready")
        elif double:
            cost = int(cost * (0.707 ** player.talent_info.level(Talent.DOUBLE_MARK)))
        if player.armor_charge < cost:
            return
        player.armor_charge -= cost
        if double and not player.get_buff("double_mark_ready"):
            player.add_buff("double_mark_ready", duration=999.0, level=1)

        add_buff(target.buffs, "death_mark", duration=5.0, level=1, source_id=player.id)
        self.add_event("DEATH_MARK", {"player": player.id, "target": target.id}, floor_id=floor_id, source_player_id=player.id)
        self.add_event("PLAY_SOUND", {"sound": "MELD"}, floor_id=floor_id, player_id=player.id)

    def _ability_shadow_clone(self, player, floor, floor_id, target_x, target_y) -> None:
        # Summon a shadow ally beside the hero. It fights nearby enemies; its HP
        # and combat scale with the Shadow Clone talents (see tick ally AI).
        if player.armor_charge < COST_SHADOW_CLONE:
            return
        spawn = None
        for ddx, ddy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            cx, cy = player.pos.x + ddx, player.pos.y + ddy
            if not (0 <= cx < floor.width and 0 <= cy < floor.height):
                continue
            if not floor.flags or not floor.flags.passable[cy][cx]:
                continue
            if any(m.is_alive and m.pos.x == cx and m.pos.y == cy for m in floor.mobs.values()):
                continue
            spawn = (cx, cy)
            break
        if spawn is None:
            return
        player.armor_charge -= COST_SHADOW_CLONE

        perfect_copy = player.talent_info.level(Talent.PERFECT_COPY)
        hp = 80 + round(0.1 * perfect_copy * (15 + 5 * player.level))

        damage_min, damage_max = 10, 20
        shadow_blade = player.talent_info.level(Talent.SHADOW_BLADE)
        if shadow_blade > 0:
            weapon = player.belongings.weapon
            attack_delay = weapon.attack_cooldown if weapon is not None else 1.0
            hero_avg_damage = (player.get_damage_min() + player.get_damage_max()) / 2
            bonus_dmg = round(0.08 * shadow_blade * (hero_avg_damage / attack_delay))
            if bonus_dmg > 0:
                damage_min += bonus_dmg
                damage_max += bonus_dmg

        dr_min, dr_max = 0, 2
        cloned_armor = player.talent_info.level(Talent.CLONED_ARMOR)
        if cloned_armor > 0:
            hero_avg_dr = (player.get_dr_min() + player.get_dr_max()) / 2
            bonus_dr = round(0.12 * cloned_armor * hero_avg_dr)
            if bonus_dr > 0:
                dr_min += bonus_dr
                dr_max += bonus_dr

        clone = Mob(
            id=f"shadow_clone_{uuid.uuid4().hex[:8]}",
            name="Shadow Clone",
            type="shadow_clone",
            pos=Position(x=spawn[0], y=spawn[1]),
            hp=hp, max_hp=hp,
            attack=10, defense=player.level + 4,
            defense_skill=player.level + 4,
            damage_min=damage_min, damage_max=damage_max,
            dr_min=dr_min, dr_max=dr_max,
            attack_cooldown=1.0,
            faction=Faction.PLAYER,
        )
        clone.owner_id = player.id
        floor.mobs[clone.id] = clone
        self.add_event("PLAY_SOUND", {"sound": "PUFF"}, floor_id=floor_id, source_player_id=player.id)
        self.add_event("SHADOW_CLONE", {"player": player.id, "clone": clone.id, "x": spawn[0], "y": spawn[1]}, floor_id=floor_id)
