# Copyright (C) 2026 ArtemNikov
#
"""Evil Eye and Scorpio loot (Eye.createLoot / Scorpio.createLoot)."""

import random
from collections import Counter

from app.engine.entities.items.consumables import Dewdrop
from app.engine.entities.mobs import Eye, Scorpio
from app.engine.systems.loot import roll_drops


def test_eye_drops_two_dew_or_a_seed_or_a_stone():
    random.seed(7)
    kinds = Counter()
    for _ in range(800):
        drops = roll_drops(Eye(), {}, 3, 3)
        if all(isinstance(d, Dewdrop) for d in drops):
            assert len(drops) == 2
            kinds["dew"] += 1
        else:
            assert len(drops) == 1
            item = drops[0]
            assert item.kind == "seed" or item.kind.startswith("stone_of_")
            assert getattr(item, "plant_type", None) != "rotberry"
            assert item.kind not in ("stone_of_enchantment", "stone_of_augmentation")
            kinds["seed" if item.kind == "seed" else "stone"] += 1
    assert abs(kinds["dew"] / 800 - 0.5) < 0.06
    assert abs(kinds["seed"] / 800 - 0.25) < 0.06


def test_scorpio_never_drops_healing_or_strength():
    random.seed(8)
    dropped = Counter()
    for _ in range(1000):
        for d in roll_drops(Scorpio(), {}, 3, 3):
            dropped[type(d).__name__] += 1
    assert 400 < sum(dropped.values()) < 600
    assert "HealthPotion" not in dropped and "PotionOfStrength" not in dropped
    assert len(dropped) == 10
