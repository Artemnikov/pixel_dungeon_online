# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
"""Duelist class mechanics for GameInstance.

Weapon charge system, finisher detection, duel mode, and armor abilities.
Called from TickMixin and ArmorAbilitiesMixin.
"""
import random

from app.engine.entities.base import Player, CharacterClass

_CHARGE_PER_HIT = 10
_CHARGE_MAX = 100
_CHARGE_DECAY_PER_S = 2.0


class DuelistMixin:

    def tick_duelist(self, player: Player, dt: float) -> None:
        if player.class_type != CharacterClass.DUELIST:
            return
        # Weapon charge decay (SPD: charge decays when not attacking)
        if player.weapon_charge > 0:
            player._weapon_charge_accum = getattr(player, "_weapon_charge_accum", 0.0) + dt
            decay = int(player._weapon_charge_accum * _CHARGE_DECAY_PER_S)
            if decay > 0:
                player.weapon_charge = max(0, player.weapon_charge - decay)
                player._weapon_charge_accum -= decay / _CHARGE_DECAY_PER_S
        # Tick down duel mode
        if player.duel_mode_active:
            if player.duel_mode_target_id:
                floor = self._get_or_create_floor(player.floor_id)
                target = floor.mobs.get(player.duel_mode_target_id)
                if target is None or not target.is_alive:
                    player.duel_mode_active = False
                    player.duel_mode_target_id = None
                    self.add_event("DUEL_END", {"player": player.id, "reason": "target_dead"},
                                   floor_id=player.floor_id, source_player_id=player.id)
        # Tick down ascended cleric state (shared field used by both classes)
        if player.ascended_form_active and player.ascended_form_timer > 0:
            player.ascended_form_timer -= dt
            if player.ascended_form_timer <= 0:
                player.ascended_form_active = False
                self.add_event("ASCENDED_END", {"player": player.id},
                               floor_id=player.floor_id, source_player_id=player.id)

    def on_duelist_hit(self, player: Player) -> None:
        """Call from combat when Duelist lands a melee hit."""
        if player.class_type != CharacterClass.DUELIST:
            return
        player.weapon_charge = min(_CHARGE_MAX, player.weapon_charge + _CHARGE_PER_HIT)
        player._weapon_charge_accum = 0.0
        subclass = player.subclass_info.subclass
        if subclass == "champion":
            threshold = 50
        elif subclass == "monk":
            threshold = 40
        else:
            threshold = 60
        player.finisher_ready = player.weapon_charge >= threshold
        self.add_event("WEAPON_CHARGE", {
            "player": player.id, "charge": player.weapon_charge,
            "finisher_ready": player.finisher_ready,
        }, floor_id=player.floor_id, source_player_id=player.id)

    def action_duelist_finisher(self, player: Player, tx: int, ty: int) -> None:
        """Use finisher ability (consumes weapon charge)."""
        if player.class_type != CharacterClass.DUELIST:
            return
        if not player.finisher_ready:
            return
        floor = self._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values()
                       if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None:
            return
        subclass = player.subclass_info.subclass
        charge = player.weapon_charge
        player.weapon_charge = 0
        player.finisher_ready = False

        if subclass == "champion":
            # Champion: heavy strike + brief stun
            dmg = max(1, round(charge * 0.3 + player.damage_min))
            dealt = target.take_damage(dmg)
            target.add_buff("paralysis", duration=2.0, level=1, stack_mode="extend")
            self.add_event("DAMAGE", {"target": target.id, "amount": dealt, "finisher": "champion"},
                           floor_id=player.floor_id)
        elif subclass == "monk":
            # Monk: fast multi-hit (3 hits at reduced damage)
            total = 0
            for _ in range(3):
                dmg = max(1, round(charge * 0.1 + player.damage_min))
                dealt = target.take_damage(dmg)
                total += dealt
            self.add_event("DAMAGE", {"target": target.id, "amount": total, "finisher": "monk"},
                           floor_id=player.floor_id)
        else:
            dmg = max(1, round(charge * 0.2 + player.damage_min))
            dealt = target.take_damage(dmg)
            self.add_event("DAMAGE", {"target": target.id, "amount": dealt, "finisher": "basic"},
                           floor_id=player.floor_id)

        self.add_event("FINISHER_USED", {"player": player.id, "subclass": subclass},
                       floor_id=player.floor_id, source_player_id=player.id)
        if not target.is_alive:
            self._handle_kill_event(player, target, floor)

    def action_challenge(self, player: Player, tx: int, ty: int) -> None:
        """Challenge armor ability: force 1v1, teleport other mobs away."""
        if player.class_type != CharacterClass.DUELIST:
            return
        floor = self._get_or_create_floor(player.floor_id)
        target = next((m for m in floor.mobs.values()
                       if m.is_alive and m.pos.x == tx and m.pos.y == ty), None)
        if target is None:
            return
        from app.engine.entities.base import Position
        pool = [(x, y) for y in range(floor.height) for x in range(floor.width)
                if floor.flags and floor.flags.passable[y][x]
                and (abs(x-player.pos.x) > 6 or abs(y-player.pos.y) > 6)]
        for mob in floor.mobs.values():
            if not mob.is_alive or mob.faction == "player" or mob.id == target.id:
                continue
            if pool:
                nx, ny = random.choice(pool)
                mob.pos = Position(x=nx, y=ny)
        player.duel_mode_active = True
        player.duel_mode_target_id = target.id
        player.armor_charge = 0
        self.add_event("CHALLENGE", {"player": player.id, "target": target.id},
                       floor_id=player.floor_id, source_player_id=player.id)

    def action_elemental_strike(self, player: Player, tx: int, ty: int) -> None:
        """Elemental Strike armor ability: AOE cone of weapon enchant."""
        if player.class_type != CharacterClass.DUELIST:
            return
        floor = self._get_or_create_floor(player.floor_id)
        enchant = player.last_weapon_enchant or "blazing"
        affected = []
        for mob in floor.mobs.values():
            if not mob.is_alive or mob.faction == "player":
                continue
            if abs(mob.pos.x - tx) <= 2 and abs(mob.pos.y - ty) <= 2:
                dmg = max(1, random.randint(player.damage_min, player.damage_max))
                mob.take_damage(dmg)
                if "blaz" in enchant or "fire" in enchant:
                    mob.add_buff("burning", duration=8.0, level=1, stack_mode="extend")
                elif "chill" in enchant or "frost" in enchant:
                    mob.add_buff("frost", duration=8.0, level=1)
                elif "shock" in enchant or "light" in enchant:
                    mob.add_buff("paralysis", duration=1.0, level=1, stack_mode="extend")
                affected.append(mob.id)
        player.armor_charge = 0
        self.add_event("ELEMENTAL_STRIKE", {"player": player.id, "enchant": enchant, "hit": affected},
                       floor_id=player.floor_id, source_player_id=player.id)

    def action_feint(self, player: Player) -> None:
        """Feint armor ability: create after-image decoy, briefly dodge."""
        if player.class_type != CharacterClass.DUELIST:
            return
        player.add_buff("invisibility", duration=2.0)
        player.add_buff("evasion_boost", duration=3.0, level=50)
        player.armor_charge = 0
        self.add_event("FEINT", {"player": player.id}, floor_id=player.floor_id,
                       source_player_id=player.id)

    def _handle_kill_event(self, player: Player, mob, floor) -> None:
        """Shared kill post-processing for duelist finishers."""
        from app.engine.systems.loot import roll_drops
        mob.die(floor_mobs=floor.mobs, tile_x=mob.pos.x, tile_y=mob.pos.y,
                players=list(self._players_on_floor(player.floor_id)))
        self.add_event("DEATH", {"target": mob.id}, floor_id=player.floor_id)
        self.handle_mob_death(mob, floor, player.floor_id)
        for drop in roll_drops(mob, self.drop_counters, mob.pos.x, mob.pos.y,
                               players=list(self._players_on_floor(player.floor_id))):
            floor.items[drop.id] = drop
