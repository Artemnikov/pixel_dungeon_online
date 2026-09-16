# Copyright (C) 2026 ArtemNikov
#
"""SpellTarget hierarchy for single-target Cleric spells.

Bless, Lay on Hands, and Mnemonic Prayer each classify their target into one
of three polymorphic kinds — self, ally, or enemy — and apply their per-spell
effect through the target's `apply_*` method. This replaces the inline
self/ally/enemy if/else ladders those spells used to carry.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from app.engine.entities.player import Player

from app.engine.game.cleric_subclass import get_cleric_subclass_strategy

HARMFUL_DEBUFFS = frozenset({
    "poison", "bleeding", "crippled", "burning", "slowed", "paralysis",
    "blindness", "corrosion", "ooze", "weakness", "vulnerable", "hex",
    "daze", "charm", "terror", "amok", "frost", "frozen", "chill", "chilled",
})

# Form-shift buffs Mnemonic Prayer must never extend on friendly characters.
_MNEMONIC_FRIENDLY_EXCLUSIONS = frozenset({
    "ascend_form", "body_form", "spirit_form", "power_of_many", "stasis",
    "empowered_strike",
})


def duplicate_to_life_linked_ally(game: Any, player: Player, callback: Callable[[Any], Any]) -> None:
    """Duplicate a single-target beneficial spell's effect to the life-linked
    Light Ally (Power of Many), when one is active."""
    if player.has_buff("life_link") and getattr(player, "powered_ally_id", None):
        floor = game._get_or_create_floor(player.floor_id)
        ally = floor.mobs.get(player.powered_ally_id)
        if ally is not None and getattr(ally, "is_alive", False):
            callback(ally)


def _resolve_char_at(game: Any, player: Player, floor: Any, tx: Optional[int], ty: Optional[int]) -> Optional[Any]:
    """Return the living character occupying (tx, ty), if any."""
    if tx is None or ty is None:
        return None
    if hasattr(game, "_players_on_floor"):
        for other_p in game._players_on_floor(player.floor_id):
            if other_p.pos.x == tx and other_p.pos.y == ty and getattr(other_p, "is_alive", False):
                return other_p
    for m in floor.mobs.values():
        if m.is_alive and m.pos.x == tx and m.pos.y == ty:
            return m
    return None


def _extend_friendly_buffs(entity: Any, ext: float) -> None:
    """Mnemonic Prayer on self/ally: extend every beneficial buff once."""
    for buff in entity.buffs:
        btype = getattr(buff, "type", "")
        if not getattr(buff, "mnemonic_extended", False):
            if btype not in HARMFUL_DEBUFFS and btype not in _MNEMONIC_FRIENDLY_EXCLUSIONS:
                buff.remaining += ext
                setattr(buff, "mnemonic_extended", True)


def _extend_hostile_buffs(entity: Any, ext: float) -> None:
    """Mnemonic Prayer on enemy: extend every harmful debuff once."""
    for buff in entity.buffs:
        if getattr(buff, "type", "") in HARMFUL_DEBUFFS and not getattr(buff, "mnemonic_extended", False):
            buff.remaining += ext
            setattr(buff, "mnemonic_extended", True)


class SpellTarget(ABC):
    """A single-target Cleric spell's resolved target, polymorphically
    dispatching the three spells that distinguish self/ally/enemy targets."""

    kind: str = "base"

    @property
    @abstractmethod
    def entity(self) -> Any:
        """The character this target resolves to (caster, ally, or enemy)."""

    @abstractmethod
    def apply_bless(self, game: Any, player: Player, pts: int) -> None:
        ...

    @abstractmethod
    def apply_lay_on_hands(self, game: Any, player: Player, base: int, max_cap: int) -> None:
        ...

    @abstractmethod
    def apply_mnemonic_prayer(self, game: Any, player: Player, ext: float) -> None:
        ...


class SelfTarget(SpellTarget):
    kind = "self"

    def __init__(self, player: Player) -> None:
        self._player = player

    @property
    def entity(self) -> Player:
        return self._player

    def apply_bless(self, game: Any, player: Player, pts: int) -> None:
        dur = 2.0 + 4.0 * pts
        shield = 5 + 5 * pts
        player.add_buff("bless", duration=dur)
        player.add_shield("barrier", shield, priority=1, decay=0)
        player.add_buff("barrier", duration=30.0, level=shield)
        duplicate_to_life_linked_ally(
            game, player, lambda ally: (
                ally.add_buff("bless", duration=dur),
                ally.add_shield("barrier", shield, priority=1, decay=0),
                ally.add_buff("barrier", duration=30.0, level=shield),
            )
        )

    def apply_lay_on_hands(self, game: Any, player: Player, base: int, max_cap: int) -> None:
        cur_shield = player.get_total_shield()
        to_add = max(0, min(base, max_cap - cur_shield))
        if to_add > 0:
            player.add_shield("barrier", to_add, priority=1, decay=0)
            player.add_buff("barrier", duration=30.0, level=to_add, stack_mode="extend")
        duplicate_to_life_linked_ally(
            game, player, lambda ally: (
                ally.add_shield("barrier", to_add, priority=1, decay=0),
                ally.add_buff("barrier", duration=30.0, level=to_add, stack_mode="extend"),
            )
        )

    def apply_mnemonic_prayer(self, game: Any, player: Player, ext: float) -> None:
        _extend_friendly_buffs(self.entity, ext)
        game.add_event(
            "PLAY_SOUND",
            {"sound": "CHARGEUP", "x": self.entity.pos.x, "y": self.entity.pos.y},
            floor_id=player.floor_id,
        )


class AllyTarget(SpellTarget):
    kind = "ally"

    def __init__(self, ally: Any) -> None:
        self._ally = ally

    @property
    def entity(self) -> Any:
        return self._ally

    def apply_bless(self, game: Any, player: Player, pts: int) -> None:
        target_char = self.entity
        dur = 5.0 + 5.0 * pts
        heal_pool = 5 + 5 * pts
        target_char.add_buff("bless", duration=dur)
        max_hp = getattr(target_char, "get_total_max_hp", lambda: getattr(target_char, "max_hp", 1))()
        missing = max(0, max_hp - target_char.hp)
        if missing < heal_pool:
            target_char.hp = max_hp
            excess = heal_pool - missing
            target_char.add_shield("barrier", excess, priority=1, decay=0)
            target_char.add_buff("barrier", duration=30.0, level=excess)
        else:
            target_char.hp += heal_pool
        # Life link: a Bless landing on the powered ally duplicates back to the caster.
        if player.has_buff("life_link") and getattr(player, "powered_ally_id", None) == target_char.id:
            player.add_buff("bless", duration=dur)
            player.add_shield("barrier", heal_pool, priority=1, decay=0)
            player.add_buff("barrier", duration=30.0, level=heal_pool)

    def apply_lay_on_hands(self, game: Any, player: Player, base: int, max_cap: int) -> None:
        target_char = self.entity
        max_hp = getattr(target_char, "get_total_max_hp", lambda: getattr(target_char, "max_hp", 1))()
        missing = max(0, max_hp - target_char.hp)
        if missing < base:
            target_char.hp = max_hp
            cur_shield = getattr(target_char, "get_total_shield", lambda: getattr(target_char, "shield", 0))()
            excess = base - missing
            to_add = max(0, min(excess, max_cap - cur_shield))
            if to_add > 0:
                target_char.add_shield("barrier", to_add, priority=1, decay=0)
                target_char.add_buff("barrier", duration=30.0, level=to_add, stack_mode="extend")
        else:
            target_char.hp += base

    def apply_mnemonic_prayer(self, game: Any, player: Player, ext: float) -> None:
        _extend_friendly_buffs(self.entity, ext)
        game.add_event(
            "PLAY_SOUND",
            {"sound": "CHARGEUP", "x": self.entity.pos.x, "y": self.entity.pos.y},
            floor_id=player.floor_id,
        )


class EnemyTarget(SpellTarget):
    kind = "enemy"

    def __init__(self, enemy: Any) -> None:
        self._enemy = enemy

    @property
    def entity(self) -> Any:
        return self._enemy

    def apply_bless(self, game: Any, player: Player, pts: int) -> None:
        # Blessing a hostile target has no effect beyond the subclass hook
        # (Priest marks it Illuminated).
        get_cleric_subclass_strategy(player).illuminate(game, player, self.entity)

    def apply_lay_on_hands(self, game: Any, player: Player, base: int, max_cap: int) -> None:
        # Lay on Hands has no hostile-target effect.
        pass

    def apply_mnemonic_prayer(self, game: Any, player: Player, ext: float) -> None:
        _extend_hostile_buffs(self.entity, ext)
        get_cleric_subclass_strategy(player).illuminate(game, player, self.entity)
        game.add_event(
            "PLAY_SOUND",
            {"sound": "DEBUFF", "x": self.entity.pos.x, "y": self.entity.pos.y},
            floor_id=player.floor_id,
        )


def resolve_spell_target(game: Any, player: Player, floor: Any, tx: Optional[int], ty: Optional[int]) -> SpellTarget:
    """Classify a single-target Cleric spell's target into Self/Ally/Enemy.

    Mirrors the inline logic the three single-target spells used to share:
    - no target, the caster's own cell, an unoccupied cell, or a cell
      occupied by the caster resolve to *self*;
    - a same-faction character resolves to *ally*;
    - a hostile character resolves to *enemy*.
    """
    if (tx is None and ty is None) or (tx == player.pos.x and ty == player.pos.y):
        return SelfTarget(player)
    target_char = _resolve_char_at(game, player, floor, tx, ty)
    if target_char is None or target_char.id == player.id:
        return SelfTarget(player)
    if target_char.faction == player.faction or target_char.faction == "player":
        return AllyTarget(target_char)
    return EnemyTarget(target_char)