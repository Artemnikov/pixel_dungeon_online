# Copyright (C) 2026 ArtemNikov
#
# Re-export hub for all mob classes, split by region:
#   sewers.py  - depths 1-5 (incl. Goo)
#   prison.py  - depths 6-10 (incl. Tengu)
#   caves.py   - depths 11-15 (incl. DM-300)
#   city.py    - depths 16-20 (incl. Dwarf King)
#   halls.py   - depth 25 (Yog-Dzewa + fists)
#   universal.py, spawners.py, npcs.py

from app.engine.entities.player import Mob as MobEntity

from app.engine.entities.mobs.sewers import (
    Rat, Snake, Gnoll, Swarm, Crab, Slime,
    AlbinoRat, GnollExile, HermitCrab, CausticSlime,
    Goo,
)
from app.engine.entities.mobs.prison import (
    Tengu, Skeleton, Thief, Bandit, DM100, Guard, NecroSkeleton,
    Necromancer, SpectralNecromancer, Bat, Brute, ArmoredBrute,
    Shaman, RedShaman, BlueShaman, PurpleShaman,
)
from app.engine.entities.mobs.caves import (
    DM300, Spinner, DM200, DM201, Ghoul, FireElemental, FrostElemental,
    ShockElemental, ChaosElemental, Warlock, Monk, Senior, Golem,
)
from app.engine.entities.mobs.city import (
    DwarfKing, DKGhoul, DKMonk, DKWarlock, DKGolem,
    Succubus, Eye, Scorpio, AcidicScorpio, RipperDemon,
)
from app.engine.entities.mobs.halls import (
    YogDzewa, BurningFist, SoiledFist, RottingFist, RustedFist,
    BrightFist, DarkFist, YogEye, YogScorpio, YogRipper, Larva,
)
from app.engine.entities.mobs.universal import (
    Wraith, TormentedSpirit, Piranha, PhantomPiranha, Mimic,
    GoldenMimic, EbonyMimic, CrystalMimic, Statue, ArmoredStatue,
    Guardian, Bee, Sentry,
)
from app.engine.entities.mobs.spawners import DemonSpawner, Pylon
from app.engine.entities.mobs.npcs import (
    RatKing, Shopkeeper, Imp, GhostHeroMob, MirrorImage,
)

__all__ = [
    "MobEntity",
    # sewers
    "Rat", "Snake", "Gnoll", "Swarm", "Crab", "Slime",
    "AlbinoRat", "GnollExile", "HermitCrab", "CausticSlime", "Goo",
    # prison
    "Tengu", "Skeleton", "Thief", "Bandit", "DM100", "Guard", "NecroSkeleton",
    "Necromancer", "SpectralNecromancer", "Bat", "Brute", "ArmoredBrute",
    "Shaman", "RedShaman", "BlueShaman", "PurpleShaman",
    # caves
    "DM300", "Spinner", "DM200", "DM201", "Ghoul", "FireElemental",
    "FrostElemental", "ShockElemental", "ChaosElemental", "Warlock", "Monk",
    "Senior", "Golem",
    # city
    "DwarfKing", "DKGhoul", "DKMonk", "DKWarlock", "DKGolem", "Succubus",
    "Eye", "Scorpio", "AcidicScorpio", "RipperDemon",
    # halls
    "YogDzewa", "BurningFist", "SoiledFist", "RottingFist", "RustedFist",
    "BrightFist", "DarkFist", "YogEye", "YogScorpio", "YogRipper", "Larva",
    # universal / spawners / npcs
    "Wraith", "TormentedSpirit", "Piranha", "PhantomPiranha", "Mimic",
    "GoldenMimic", "EbonyMimic", "CrystalMimic", "Statue", "ArmoredStatue",
    "Guardian", "Bee", "Sentry",
    "DemonSpawner", "Pylon",
    "RatKing", "Shopkeeper", "Imp", "GhostHeroMob", "MirrorImage",
]
