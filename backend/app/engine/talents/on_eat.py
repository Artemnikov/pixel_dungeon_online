from app.engine.entities.buffs import add_buff
from app.engine.entities.talent_enum import Talent
from .constants import (
    HEARTY_MEAL_THRESHOLD,
    HEARTY_MEAL_BASE_HEAL,
    HEARTY_MEAL_HEAL_PER_LEVEL,
    IRON_STOMACH_IMMUNITY_DURATION_PER_LEVEL,
    CACHED_RATIONS_BASE_HEAL,
    CACHED_RATIONS_HEAL_PER_LEVEL,
    EMPOWERING_MEAL_CHARGES,
    ENERGIZING_MEAL_BASE_DURATION,
    ENERGIZING_MEAL_DURATION_PER_LEVEL,
    INVIGORATING_MEAL_BASE_DURATION,
    INVIGORATING_MEAL_DURATION_PER_LEVEL,
)
from .registry import EffectContext, registry


@registry.on("on_eat", Talent.HEARTY_MEAL)
def handle_hearty_meal(ctx: EffectContext, level: int) -> None:
    player = ctx.player
    if player.hp / max(player.get_total_max_hp(), 1) < HEARTY_MEAL_THRESHOLD:
        healing = HEARTY_MEAL_BASE_HEAL + HEARTY_MEAL_HEAL_PER_LEVEL * level
        player.hp = min(player.get_total_max_hp(), player.hp + healing)


@registry.on("on_eat", Talent.IRON_STOMACH)
def handle_iron_stomach(ctx: EffectContext, level: int) -> None:
    add_buff(
        ctx.player.buffs,
        "iron_stomach_immunity",
        duration=IRON_STOMACH_IMMUNITY_DURATION_PER_LEVEL * level,
        level=1,
    )


@registry.on("on_eat", Talent.CACHED_RATIONS)
def handle_cached_rations(ctx: EffectContext, level: int) -> None:
    heal_amt = float(CACHED_RATIONS_BASE_HEAL + CACHED_RATIONS_HEAL_PER_LEVEL * level)
    ctx.player.set_heal(heal_amt, 0.25, 0)


@registry.on("on_eat", Talent.EMPOWERING_MEAL)
def handle_empowering_meal(ctx: EffectContext, level: int) -> None:
    player = ctx.player
    add_buff(player.buffs, "wand_empower", duration=999999.0, level=EMPOWERING_MEAL_CHARGES, stack_mode="extend")
    if hasattr(ctx.game, "add_event"):
        ctx.game.add_event("ENERGY_BURST", {"player": player.id}, floor_id=player.floor_id)


@registry.on("on_eat", Talent.MYSTICAL_MEAL)
def handle_mystical_meal(ctx: EffectContext, level: int) -> None:
    player = ctx.player
    cloak = player.belongings.artifact if hasattr(player, "belongings") else None
    if cloak is not None and getattr(cloak, "kind", "") == "cloak_of_shadows":
        cloak.charge = min(cloak.charge_cap, cloak.charge + level)


@registry.on("on_eat", Talent.ENERGIZING_MEAL)
def handle_energizing_meal(ctx: EffectContext, level: int) -> None:
    duration = ENERGIZING_MEAL_BASE_DURATION + ENERGIZING_MEAL_DURATION_PER_LEVEL * level
    add_buff(ctx.player.buffs, "recharging", duration=duration)


@registry.on("on_eat", Talent.INVIGORATING_MEAL)
def handle_invigorating_meal(ctx: EffectContext, level: int) -> None:
    duration = INVIGORATING_MEAL_BASE_DURATION + INVIGORATING_MEAL_DURATION_PER_LEVEL * level
    add_buff(ctx.player.buffs, "haste", duration=duration, level=1)
@registry.on("on_eat", Talent.SATIATED_SPELLS)
def handle_satiated_spells(ctx: EffectContext, level: int) -> None:
    add_buff(ctx.player.buffs, "satiated_spells_tracker", duration=999999.0, level=level)


@registry.on("on_eat", Talent.ENLIGHTENING_MEAL)
def handle_enlightening_meal(ctx: EffectContext, level: int) -> None:
    tome = ctx.player.get_holy_tome()
    if tome is not None:
        tome.direct_charge((1.0 + level) / 3.0)


