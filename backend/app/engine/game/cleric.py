# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
"""Cleric class mechanics for GameInstance.

Spell casting system, spell cooldowns, Trinity item borrowing, and armor abilities.
Called from TickMixin and ArmorAbilitiesMixin.
"""
import random

from app.engine.entities.player import Player, CharacterClass

_SPELL_COOLDOWNS: dict[str, float] = {
    "holy_light": 20.0,
    "holy_weapon": 30.0,
    "divine_sense": 15.0,
    "mend": 25.0,
    "bless": 20.0,
    "guiding_light": 15.0,
    "holy_ward": 25.0,
    "recall_inscription": 30.0,
    "trinity_spell": 40.0,
    "power_of_many": 50.0,
    "ascended_form": 60.0,
}


class ClericMixin:

    def tick_cleric(self, player: Player, dt: float) -> None:
        if player.class_type != CharacterClass.CLERIC:
            return
        # Tick down all spell cooldowns
        for spell in list(player.spell_cooldowns.keys()):
            player.spell_cooldowns[spell] = max(0.0, player.spell_cooldowns[spell] - dt)
        # Clear spells_cast_this_turn (reset each tick)
        player.spells_cast_this_turn = []
        # Tick down ascended form
        if player.ascended_form_active and player.ascended_form_timer > 0:
            player.ascended_form_timer -= dt
            if player.ascended_form_timer <= 0:
                player.ascended_form_active = False
                self.add_event("ASCENDED_END", {"player": player.id},
                               floor_id=player.floor_id, source_player_id=player.id)
        # Paladin: tick down blessed weapon
        if player.blessed_weapon_turns > 0:
            player.blessed_weapon_turns -= 1

    def cast_spell(self, player: Player, spell_name: str, tx: int = None, ty: int = None) -> bool:
        """Attempt to cast a cleric spell. Returns True on success."""
        if player.class_type != CharacterClass.CLERIC:
            return False
        if player.has_buff("magic_immune"):
            return False
        cooldown = player.spell_cooldowns.get(spell_name, 0.0)
        if cooldown > 0:
            self.add_event("SPELL_ON_COOLDOWN", {
                "player": player.id, "spell": spell_name, "remaining": cooldown,
            }, floor_id=player.floor_id, player_id=player.id)
            return False

        dispatched = self._dispatch_spell(player, spell_name, tx, ty)
        if dispatched:
            player.spell_cooldowns[spell_name] = _SPELL_COOLDOWNS.get(spell_name, 20.0)
            player.spells_cast_this_turn.append(spell_name)
        return dispatched

    def _dispatch_spell(self, player: Player, spell_name: str, tx, ty) -> bool:
        floor = self._get_or_create_floor(player.floor_id)
        if spell_name == "holy_light":
            visible_mobs = list(self._mobs_in_fov(player, floor, player.floor_id))
            for mob in visible_mobs:
                if mob.faction == "player":
                    continue
                dmg = max(1, random.randint(4, 8) + player.level)
                dealt = mob.take_damage(dmg)
                mob.add_buff("blindness", duration=5.0)
                self.add_event("DAMAGE", {"target": mob.id, "amount": dealt, "holy": True},
                               floor_id=player.floor_id)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "holy_weapon":
            player.blessed_weapon_turns = 30
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "divine_sense":
            player.add_buff("mind_vision", duration=30.0)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "mend":
            heal = max(1, round(player.get_total_max_hp() * 0.3))
            player.set_heal(heal, 0.25, 0)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "bless":
            player.add_buff("bless", duration=20.0)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "guiding_light":
            player.add_buff("foresight", duration=100.0)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "holy_ward":
            shield = round(player.get_total_max_hp() * 0.25)
            player.add_buff("shielded", duration=30.0, level=shield)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

        elif spell_name == "recall_inscription":
            # Re-reads a random scroll effect from inventory (stub)
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            self.add_event("RECALL_INSCRIPTION_STUB", {"player": player.id},
                           floor_id=player.floor_id, player_id=player.id)
            return True

        else:
            # Stub for unimplemented spells
            self.add_event("SPELL_CAST", {"player": player.id, "spell": spell_name},
                           floor_id=player.floor_id, source_player_id=player.id)
            return True

    # ── Armor Abilities ──────────────────────────────────────────────────────

    def action_ascended_form(self, player: Player) -> None:
        """Ascended Form: buff all spells + shield for 30s."""
        if player.class_type != CharacterClass.CLERIC:
            return
        shield = round(player.get_total_max_hp() * 0.4)
        player.add_buff("shielded", duration=30.0, level=shield)
        player.add_buff("spell_power", duration=30.0, level=2)
        player.ascended_form_active = True
        player.ascended_form_timer = 30.0
        player.armor_charge = 0
        self.add_event("ASCENDED_FORM", {"player": player.id},
                       floor_id=player.floor_id, source_player_id=player.id)

    def action_trinity(self, player: Player, item_kind: str) -> None:
        """Trinity: borrow one item form (up to 3). Stub: emits event for client."""
        if player.class_type != CharacterClass.CLERIC:
            return
        if len(player.current_trinity_forms) >= 3:
            player.current_trinity_forms.pop(0)
        player.current_trinity_forms.append(item_kind)
        player.armor_charge = max(0, player.armor_charge - 33)
        self.add_event("TRINITY_FORM", {"player": player.id, "forms": player.current_trinity_forms},
                       floor_id=player.floor_id, source_player_id=player.id)

    def action_power_of_many(self, player: Player, tx: int, ty: int) -> None:
        """Power of Many: summon a Light Ally at target cell."""
        if player.class_type != CharacterClass.CLERIC:
            return
        import uuid as _uuid
        from app.engine.entities.base import Position
        from app.engine.entities.player import Mob
        floor = self._get_or_create_floor(player.floor_id)

        # Remove existing ally if any
        if player.powered_ally_id and player.powered_ally_id in floor.mobs:
            existing = floor.mobs[player.powered_ally_id]
            existing.is_alive = False
            self.add_event("DEATH", {"target": existing.id}, floor_id=player.floor_id)
            del floor.mobs[player.powered_ally_id]

        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return
        if not (floor.flags and floor.flags.passable[ty][tx]):
            return

        ally_id = f"light_ally_{_uuid.uuid4().hex[:8]}"
        ally_hp = round(player.get_total_max_hp() * 0.6)
        ally = Mob(
            id=ally_id, type="mob", mob_type="light_ally",
            name="Light Ally",
            pos=Position(x=tx, y=ty),
            hp=ally_hp, max_hp=ally_hp,
            attack=player.attack, defense=player.defense // 2,
            damage_min=player.damage_min, damage_max=player.damage_max,
            faction="player", owner_id=player.id,
        )
        floor.mobs[ally.id] = ally
        player.powered_ally_id = ally_id
        player.armor_charge = 0
        self.add_event("POWER_OF_MANY", {"player": player.id, "ally_id": ally_id, "x": tx, "y": ty},
                       floor_id=player.floor_id, source_player_id=player.id)
