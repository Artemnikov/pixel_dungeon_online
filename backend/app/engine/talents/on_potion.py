from app.engine.entities.buffs import add_buff
from app.engine.entities.talent_enum import Talent
from .constants import (
    LIQUID_WILLPOWER_BASE_RATIO,
    LIQUID_WILLPOWER_RATIO_PER_LEVEL,
    LIQUID_WILLPOWER_SHIELD_DECAY,
)
from .registry import EffectContext, registry


@registry.on("on_potion", Talent.LIQUID_WILLPOWER)
def handle_liquid_willpower(ctx: EffectContext, level: int) -> None:
    player = ctx.player
    shield_amt = round(
        player.get_total_max_hp() * (LIQUID_WILLPOWER_BASE_RATIO + LIQUID_WILLPOWER_RATIO_PER_LEVEL * level)
    )
    if shield_amt > 0:
        player.add_shield("liquid_willpower", shield_amt, priority=1, decay=LIQUID_WILLPOWER_SHIELD_DECAY)


@registry.on("on_potion", Talent.LIQUID_AGILITY)
def handle_liquid_agility(ctx: EffectContext, level: int) -> None:
    player = ctx.player
    # Rank 1: 3x evasion + 3x accuracy; Rank 2: infinite evasion + infinite accuracy
    add_buff(player.buffs, "liquid_agility_evasion", duration=5.0, level=level)
    add_buff(player.buffs, "liquid_agility_accuracy", duration=5.0, level=level)

