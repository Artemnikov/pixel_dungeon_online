# Copyright (C) 2026 ArtemNikov
#
"""On-upgrade event handlers for talents."""
from __future__ import annotations

import uuid

from app.engine.entities.talent_enum import Talent
from .registry import EffectContext, registry


@registry.on("on_upgrade", Talent.ADVENTURERS_INTUITION)
def handle_adventurers_intuition_upgrade(ctx: EffectContext, level: int) -> None:
    """At rank 2, auto-identify currently equipped primary and secondary weapons."""
    if ctx.payload.get("talent") != Talent.ADVENTURERS_INTUITION or ctx.payload.get("level") != 2:
        return
    belongings = getattr(ctx.player, "belongings", None)
    if belongings is not None:
        weapon = getattr(belongings, "weapon", None)
        if weapon is not None and not getattr(weapon, "level_known", False):
            weapon.level_known = True
            weapon.cursed_known = True
        sec_weapon = getattr(belongings, "secondary_weapon", None)
        if sec_weapon is not None and not getattr(sec_weapon, "level_known", False):
            sec_weapon.level_known = True
            sec_weapon.cursed_known = True


@registry.on("on_upgrade", Talent.UNENCUMBERED_SPIRIT)
def handle_unencumbered_spirit_upgrade(ctx: EffectContext, level: int) -> None:
    """At rank 3, gift identified Cloth Armor and Gloves to player backpack/floor."""
    if ctx.payload.get("talent") != Talent.UNENCUMBERED_SPIRIT or ctx.payload.get("level") != 3:
        return
    from app.engine.entities.items.actions import _floor_drop
    from app.engine.entities.items.equip import ClothArmor, make_named_melee_weapon

    cloth = ClothArmor(id=str(uuid.uuid4()), level_known=True, cursed_known=True)
    gloves = make_named_melee_weapon("Gloves", id=str(uuid.uuid4()), level_known=True, cursed_known=True)

    player = ctx.player
    game = ctx.game
    for item in (cloth, gloves):
        collected = False
        if hasattr(player, "belongings") and hasattr(player.belongings, "backpack"):
            collected = player.belongings.backpack.collect(item)
        if not collected and hasattr(player, "pos"):
            _floor_drop(game, player, item, player.pos.x, player.pos.y)


@registry.on("on_upgrade", Talent.SWIFT_EQUIP)
def handle_swift_equip_upgrade(ctx: EffectContext, level: int) -> None:
    """Initialize or top up Swift Equip charges when upgraded out of cooldown."""
    if ctx.payload.get("talent") != Talent.SWIFT_EQUIP:
        return
    player = ctx.player
    if getattr(player, "swift_equip_cooldown", 0.0) <= 0.0:
        player.swift_equip_charges = level
