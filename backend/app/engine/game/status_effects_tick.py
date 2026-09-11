# Copyright (C) 2026 ArtemNikov
#
"""Client-facing status effect bookkeeping: STATE_EFFECT event emission and
the player active_effects list synced to the frontend HUD each tick.
"""

from typing import Callable, Dict, List, Optional, Protocol

from app.engine.dungeon.constants import TileType
from app.engine.entities.buffs import get_buff, has_buff
from app.engine.entities.player import Effect, Player


class StatusEffectProvider(Protocol):
    def provide(self, player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
        ...


class BuffStatusEffectProvider:
    """Strategy for standard buff-based active HUD status effects."""

    def __init__(
        self,
        buff_type: str,
        key: str,
        name: str,
        icon: int,
        duration: float = 30.0,
        level_as_remaining: bool = False,
        duration_calculator: Optional[Callable[[Player, object], float]] = None,
        fallback_buff_type: Optional[str] = None,
    ):
        self.buff_type = buff_type
        self.key = key
        self.name = name
        self.icon = icon
        self.default_duration = duration
        self.level_as_remaining = level_as_remaining
        self.duration_calculator = duration_calculator
        self.fallback_buff_type = fallback_buff_type

    def provide(self, player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
        buff = get_buff(player.buffs, self.buff_type)
        if buff is None and self.fallback_buff_type:
            buff = get_buff(player.buffs, self.fallback_buff_type)
        if buff is None:
            return None

        remaining = float(buff.level) if self.level_as_remaining else buff.remaining
        if self.duration_calculator is not None:
            dur = self.duration_calculator(player, buff)
        else:
            dur = self.default_duration

        return Effect(
            key=self.key,
            name=self.name,
            icon=self.icon,
            remaining=remaining,
            duration=dur,
        )


class PropertyStatusEffectProvider:
    """Strategy for player property-backed active HUD status effects."""

    def __init__(self, extractor: Callable[[Player, Dict[str, Effect]], Optional[Effect]]):
        self.extractor = extractor

    def provide(self, player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
        return self.extractor(player, existing)


def _provide_regen(player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
    if player.heal_left <= 0:
        return None
    prev = existing.get("regen")
    duration = max(prev.duration if prev else 0.0, player.heal_left)
    return Effect(
        key="regen", name="Healing", icon=44,
        remaining=player.heal_left, duration=duration,
    )


def _provide_aqua_rejuv(player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
    if player.aqua_heal_left <= 0:
        return None
    return Effect(
        key="aqua_rejuv", name="Aquatic Rejuvenation", icon=44,
        remaining=player.aqua_heal_left, duration=player.aqua_heal_left,
    )


def _provide_berserk(player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
    if not player.berserk_active:
        return None
    return Effect(
        key="berserk", name="Berserk", icon=13,
        remaining=player.berserk_power, duration=1.0,
    )


def _provide_fury(player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
    if not player.has_fury:
        return None
    return Effect(
        key="fury", name="Fury", icon=5,
        remaining=float(player.fury_turns_remaining), duration=10.0,
    )


def _provide_locked_floor(player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
    if player.locked_floor_left is None:
        return None
    return Effect(
        key="locked_floor", name="Locked Floor", icon=35,
        remaining=max(0.0, min(50.0, player.locked_floor_left)), duration=50.0,
    )


def _provide_seal_shield(player: Player, existing: Dict[str, Effect]) -> Optional[Effect]:
    seal_shield = player.get_shield("broken_seal")
    if seal_shield is None or seal_shield.amount <= 0:
        return None
    return Effect(
        key="seal_shield", name="Shield", icon=84,
        remaining=seal_shield.amount,
        duration=player.get_broken_seal_max_shield() or seal_shield.amount,
    )


class StatusEffectRegistry:
    def __init__(self, providers: List[StatusEffectProvider]):
        self._providers = providers

    def collect(self, player: Player) -> List[Effect]:
        existing = {e.key: e for e in player.active_effects}
        effects: List[Effect] = []
        for provider in self._providers:
            effect = provider.provide(player, existing)
            if effect is not None:
                effects.append(effect)
        return effects


DEFAULT_STATUS_EFFECT_REGISTRY = StatusEffectRegistry([
    PropertyStatusEffectProvider(_provide_regen),
    BuffStatusEffectProvider(
        "sungrass_health", "sungrass_health", "Herbal Healing", 19,
        level_as_remaining=True,
        duration_calculator=lambda p, b: float(p.get_total_max_hp()),
    ),
    BuffStatusEffectProvider(
        "earthroot_armor", "earthroot_armor", "Earthroot", 20,
        level_as_remaining=True,
        duration_calculator=lambda p, b: float(p.get_total_max_hp()),
    ),
    PropertyStatusEffectProvider(_provide_aqua_rejuv),
    PropertyStatusEffectProvider(_provide_berserk),
    BuffStatusEffectProvider("endure_tracker", "endure", "Endure", 6, duration=12.0),
    PropertyStatusEffectProvider(_provide_fury),
    PropertyStatusEffectProvider(_provide_locked_floor),
    BuffStatusEffectProvider("invisibility", "invisibility", "Invisible", 12, duration=20.0, fallback_buff_type="shadows"),
    BuffStatusEffectProvider("slow", "slow", "Slowed", 23, duration=30.0),
    BuffStatusEffectProvider("bleeding", "bleeding", "Bleeding", 26, duration=30.0),
    BuffStatusEffectProvider("barkskin", "barkskin", "Barkskin", 24, duration=50.0),
    BuffStatusEffectProvider("roots", "roots", "Rooted", 11, duration=10.0),
    BuffStatusEffectProvider("daze", "daze", "Dazed", 70, duration=30.0),
    BuffStatusEffectProvider("stagger", "stagger", "Staggered", 70, duration=5.0),
    BuffStatusEffectProvider("bless", "bless", "Blessed", 37, duration=30.0),
    BuffStatusEffectProvider("healing", "healing_buff", "Healing", 44, duration=30.0),
    BuffStatusEffectProvider("well_fed", "well_fed", "Well Fed", 43, duration=450.0),
    BuffStatusEffectProvider(
        "nourished", "nourished", "Nourished", 44,
        duration_calculator=lambda p, b: getattr(p, "_nourished_duration", 0.0) or getattr(b, "remaining", 0.0),
    ),
    BuffStatusEffectProvider("levitation", "levitation", "Levitation", 1, duration=30.0),
    PropertyStatusEffectProvider(_provide_seal_shield),
    BuffStatusEffectProvider("provoked_anger_tracker", "provoked_anger", "Provoked Anger", 45, duration=5.0),
    BuffStatusEffectProvider("frost_imbue", "frost_imbue", "Frost Imbue", 55, duration=30.0),
    BuffStatusEffectProvider("fire_imbue", "fire_imbue", "Fire Imbue", 55, duration=30.0),
    BuffStatusEffectProvider("toxic_imbue", "toxic_imbue", "Toxic Imbue", 55, duration=30.0),
])


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
        "stagger": "stagger",
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
        player.active_effects = DEFAULT_STATUS_EFFECT_REGISTRY.collect(player)

