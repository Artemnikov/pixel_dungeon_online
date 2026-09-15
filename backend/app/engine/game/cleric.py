# Copyright (C) 2026 ArtemNikov
#
"""Cleric class mechanics for GameInstance.

Polymorphic spell casting system, Holy Tome energy management,
Trinity item borrowing, and armor abilities.
Called from TickMixin and ArmorAbilitiesMixin.
"""
from typing import Optional

from app.engine.entities.base import Position
from app.engine.entities.player import CharacterClass, Player
from app.engine.entities.items.artifacts import HolyTome
from app.engine.game.cleric_spells import (
    SPELL_REGISTRY,
    get_available_spells,
    get_cleric_spell,
)


class ClericMixin:

    def tick_cleric(self, player: Player, dt: float) -> None:
        if player.class_type != CharacterClass.CLERIC:
            return

        if hasattr(player, "guiding_light_priest_cd") and player.guiding_light_priest_cd > 0:
            player.guiding_light_priest_cd = max(0.0, player.guiding_light_priest_cd - dt)

        for spell in list(player.spell_cooldowns.keys()):
            player.spell_cooldowns[spell] = max(0.0, player.spell_cooldowns[spell] - dt)

        if player.ascended_form_active and player.ascended_form_timer > 0:
            player.ascended_form_timer -= dt
            if player.ascended_form_timer <= 0:
                player.ascended_form_active = False
                player.ascended_form_casts = 0
                player.flash_casts = 0
                player.divine_intervention_used = False
                self.add_event(
                    "ASCENDED_END",
                    {"player": player.id},
                    floor_id=player.floor_id,
                    source_player_id=player.id,
                )

        if not player.has_buff("stasis") and getattr(player, "_stasis_stored_ally", None) is not None:
            floor = self._get_or_create_floor(player.floor_id)
            stored = player._stasis_stored_ally
            floor.mobs[stored.id] = stored
            stored.pos = Position(x=player.pos.x, y=player.pos.y)
            stored.is_alive = True
            player._stasis_stored_ally = None

    def set_cleric_quick_spell(self, player: Player, spell_name: Optional[str]) -> bool:
        """Set or toggle-clear the cleric's tome quick-cast spell (ActionIndicator tag)."""
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return False

        if not spell_name or spell_name == player.cleric_quick_spell:
            player.cleric_quick_spell = None
        else:
            spell = get_cleric_spell(spell_name)
            if spell is None or not spell.is_unlocked(player):
                return False
            player.cleric_quick_spell = spell_name

        self.add_event(
            "CLERIC_QUICK_SPELL",
            {
                "player": player.id,
                "spell": player.cleric_quick_spell,
            },
            floor_id=player.floor_id,
            player_id=player.id,
        )
        return True

    def cast_spell(self, player: Player, spell_name: str, tx: Optional[int] = None, ty: Optional[int] = None) -> bool:
        """Attempt to cast a cleric spell. Returns True on success."""
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return False
        if player.has_buff("magic_immune"):
            return False

        spell = get_cleric_spell(spell_name)
        if spell is None or not spell.is_unlocked(player):
            return False

        tome = player.get_holy_tome()
        if tome is None:
            self.add_event(
                "SPELL_FAILED",
                {"player": player.id, "spell": spell_name, "reason": "no_holy_tome"},
                floor_id=player.floor_id,
                player_id=player.id,
            )
            return False

        cost = spell.get_cost(player)
        if tome.charge < cost:
            self.add_event(
                "SPELL_NO_CHARGES",
                {"player": player.id, "spell": spell_name, "required": cost, "current": tome.charge},
                floor_id=player.floor_id,
                player_id=player.id,
            )
            return False

        dispatched = spell.execute(self, player, tx, ty)
        if dispatched:
            spell.on_spell_cast(self, player, tome, cost)
        return dispatched

    def action_ascended_form(self, player: Player) -> None:
        """Ascended Form: buff all spells + shield for 10s."""
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return
        shield = 30
        player.add_shield("ascended_form", shield, priority=2, decay=0)
        player.add_buff("shielded", duration=10.0, level=shield)
        player.ascended_form_active = True
        player.ascended_form_timer = 10.0
        player.ascended_form_casts = 0
        player.flash_casts = 0
        self.add_event(
            "ASCENDED_FORM",
            {"player": player.id},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

    def action_trinity(self, player: Player, item_kind: str) -> None:
        """Trinity: borrow one item form (up to 3). Stub: emits event for client."""
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return
        if len(player.current_trinity_forms) >= 3:
            player.current_trinity_forms.pop(0)
        player.current_trinity_forms.append(item_kind)
        self.add_event(
            "TRINITY_FORM",
            {"player": player.id, "forms": player.current_trinity_forms},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )

    def action_power_of_many(self, player: Player, tx: int, ty: int) -> None:
        """Power of Many: summon a Light Ally at target cell."""
        if player.class_type != CharacterClass.CLERIC or player.is_downed or not player.is_alive:
            return
        import uuid as _uuid
        from app.engine.entities.base import Position
        from app.engine.entities.player import Mob

        floor = self._get_or_create_floor(player.floor_id)

        if not (0 <= tx < floor.width and 0 <= ty < floor.height):
            return
        if not (floor.flags and floor.flags.passable[ty][tx]):
            return

        if player.powered_ally_id and player.powered_ally_id in floor.mobs:
            existing = floor.mobs[player.powered_ally_id]
            existing.is_alive = False
            self.add_event("DEATH", {"target": existing.id}, floor_id=player.floor_id)
            del floor.mobs[player.powered_ally_id]

        ally_id = f"light_ally_{_uuid.uuid4().hex[:8]}"
        ally_hp = 80 + player.level * 4
        ally = Mob(
            id=ally_id,
            type="mob",
            mob_type="light_ally",
            name="Light Ally",
            pos=Position(x=tx, y=ty),
            hp=ally_hp,
            max_hp=ally_hp,
            attack=player.attack,
            defense=player.defense // 2,
            damage_min=player.damage_min,
            damage_max=player.damage_max,
            faction="player",
            owner_id=player.id,
        )
        floor.mobs[ally.id] = ally
        ally._owner_ref = player
        player.powered_ally_id = ally_id
        player._active_powered_ally = ally
        self.add_event(
            "POWER_OF_MANY",
            {"player": player.id, "ally_id": ally_id, "x": tx, "y": ty},
            floor_id=player.floor_id,
            source_player_id=player.id,
        )
