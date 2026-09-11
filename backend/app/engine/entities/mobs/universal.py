# Copyright (C) 2026 ArtemNikov
#
import math
import random
from typing import Any, List, Optional, TYPE_CHECKING

from pydantic import Field

from app.engine.entities.base import Faction
from app.engine.entities.player import Mob as MobEntity, DropEntry

if TYPE_CHECKING:
    from app.engine.entities.base import Entity

# ---------------------------------------------------------------------------
# Universal / Environmental Enemies + Sentry (SentryRoom)
# ---------------------------------------------------------------------------

class Wraith(MobEntity):
    """HP=1, stats scale with floor_level. spawningWeight=0 (never regular spawn).
    adjustStats(level) must be called after creation."""
    name: str = "Wraith"
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 10     # 10 + level (scaled by GameInstance on spawn)
    defense_skill: int = 50    # base default, scaled by GameInstance on spawn
    damage_min: int = 1
    damage_max: int = 2        # 1 + level/2 .. 2 + level (set via floor_level)
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    flying: bool = True
    properties: List[str] = ["UNDEAD", "INORGANIC"]
    # Runtime: floor depth used to scale attack/damage
    floor_level: int = 1


class TormentedSpirit(Wraith):
    """Exotic wraith variant (1/100 chance). 50% more damage/accuracy scaling."""
    name: str = "Tormented Spirit"
    pacified: bool = False


class Piranha(MobEntity):
    """HP and defense scale with depth: HP=10+depth*5, defense=10+depth*2.
    Dies on land (out of water). EXP=0. Always drops mystery_meat."""
    name: str = "Piranha"
    hp: int = 30        # default depth=4: 10+4*5=30
    max_hp: int = 30
    attack_skill: int = 20
    defense_skill: int = 18    # 10 + depth*2 (depth=4)
    damage_min: int = 3
    damage_max: int = 8
    dr_min: int = 0
    dr_max: int = 0
    speed: float = 2.0
    exp: int = 0
    max_lvl: int = -2
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="mystery_meat", chance=1.0, max_global=0),
    ]
    # Runtime: set to current depth so stats can be recalculated
    floor_level: int = 4


class PhantomPiranha(Piranha):
    """Exotic piranha variant. Drops phantom_meat instead of mystery_meat."""
    name: str = "Phantom Piranha"
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="phantom_meat", chance=1.0, max_global=0),
    ]


class Mimic(MobEntity):
    """Disguised as a chest until attacked. HP=(1+level)*6, stats scale with level.
    EXP=0. DEMONIC property. setLevel() must be called after creation."""
    name: str = "Mimic"
    hp: int = 12       # level=1: (1+1)*6=12
    max_hp: int = 12
    attack_skill: int = 7      # 6 + level
    defense_skill: int = 2     # 2 + level/2
    damage_min: int = 2        # 1+level .. 2+2*level (attacking state)
    damage_max: int = 4
    dr_min: int = 0
    dr_max: int = 1            # 0 .. 1+level/2
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["DEMONIC"]
    # Runtime
    floor_level: int = 1
    disguised: bool = True
    stealthy: bool = False
    fake_chest_id: str = ""
    carried_items: List[Any] = Field(default_factory=list)

    def get_reveal_message(self) -> str:
        return "A chest was a mimic!"

    def get_sound_rate(self) -> float:
        return 1.0

    def _setup_reveal_state(self, player) -> None:
        self.ai_state = "hunting"
        self.target_id = player.id

    def _after_reveal(self, game, floor_id: int) -> None:
        pass

    def stop_hiding(self, game, player, floor, floor_id: int) -> None:
        """SPD Mimic.stopHiding: sets state=HUNTING, plays MIMIC sound, bursts
        star particles. The fake chest is removed and the mob becomes visible
        (disguised=False) so the frontend renders the mimic sprite."""
        if not self.disguised or not self.is_alive:
            return
        if self.fake_chest_id:
            floor.items.pop(self.fake_chest_id, None)
        self.disguised = False
        self._setup_reveal_state(player)
        game.add_event("SPAWN_MOB", {"mob": self.model_dump()}, floor_id=floor_id)
        game.add_event(
            "PLAY_SOUND",
            {"sound": "MIMIC", "rate": self.get_sound_rate(), "x": self.pos.x, "y": self.pos.y},
            floor_id=floor_id,
        )
        game.add_event(
            "MESSAGE",
            {"text": self.get_reveal_message(), "player": player.id},
            floor_id=floor_id,
        )
        self._after_reveal(game, floor_id)


class GoldenMimic(Mimic):
    """Golden variant — better loot, same base stats as Mimic at level."""
    name: str = "Golden Mimic"

    def get_reveal_message(self) -> str:
        return "A locked chest was a mimic!"

    def get_sound_rate(self) -> float:
        return 0.85


class EbonyMimic(Mimic):
    """Ebony variant — deals double damage on surprise attack."""
    name: str = "Ebony Mimic"

    def get_sound_rate(self) -> float:
        return 0.85


class CrystalMimic(Mimic):
    """Crystal variant — steals on attack while disguised, teleports target when revealed, then flees."""
    name: str = "Crystal Mimic"
    pending_steal_name: str = ""
    pending_teleport: bool = False
    pending_stolen_item: Optional[Any] = None

    def get_reveal_message(self) -> str:
        return "The crystal chest was a mimic!"

    def get_sound_rate(self) -> float:
        return 1.25

    def _setup_reveal_state(self, player) -> None:
        self.ai_state = "fleeing"
        self.add_buff("haste", 2.0)

    def _after_reveal(self, game, floor_id: int) -> None:
        game.add_event(
            "CRYSTAL_CHEST_SHATTER",
            {"x": self.pos.x, "y": self.pos.y},
            floor_id=floor_id,
        )

    def attack_proc(self, target) -> None:
        if self.disguised:
            bp = target.belongings.backpack if getattr(target, 'belongings', None) else None
            if not bp:
                return
            tries = 10
            stolen = None
            for _ in range(tries):
                candidate = random.choice(bp.items) if bp.items else None
                if candidate is None:
                    break
                if not candidate.unique and candidate.level < 1 and candidate.type != 'key':
                    stolen = candidate
                    break
            if stolen is not None:
                bp.detach_all(stolen.id)
                self.pending_steal_name = stolen.name
                self.pending_stolen_item = stolen
        else:
            self.pending_teleport = True


class Statue(MobEntity):
    """Passive until attacked (activated=False). HP=15+depth*5.
    attackSkill scales with depth. Drops its weapon on death. EXP=0. INORGANIC."""
    name: str = "Statue"
    hp: int = 35       # depth=4: 15+4*5=35
    max_hp: int = 35
    attack_skill: int = 15     # scales with depth (approx 10+depth)
    defense_skill: int = 8     # 4+depth
    damage_min: int = 3
    damage_max: int = 10
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["INORGANIC"]
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="weapon", chance=1.0, max_global=0),
    ]
    # Runtime
    floor_level: int = 4
    activated: bool = False


class ArmoredStatue(Statue):
    """Armored variant — HP=30+depth*10, has armor glyph DR bonus."""
    name: str = "Armored Statue"
    hp: int = 70       # depth=4: 30+4*10=70
    max_hp: int = 70
    dr_min: int = 2
    dr_max: int = 10
    loot_table: List[DropEntry] = [
        DropEntry(item_kind="armor", chance=1.0, max_global=0),
    ]


class Guardian(Statue):
    """GuardianTrap.Guardian: a wandering (not levelgen-placed, not dormant)
    Statue summoned by GuardianTrap. EXP=0, always starts WANDERING (beckon()
    works on these unlike the base Statue, which stays dormant until hit)."""
    name: str = "Guardian"
    exp: int = 0
    ai_state: str = "wandering"


class Bee(MobEntity):
    """Flying. Neutral faction initially; turns ENEMY if honey pot is destroyed.
    HP=(2+level)*4, defense=9+level. EXP=0. spawn(level) sets stats."""
    name: str = "Bee"
    hp: int = 12       # level=1: (2+1)*4=12
    max_hp: int = 12
    attack_skill: int = 10     # = defenseSkill
    defense_skill: int = 10    # 9+level
    damage_min: int = 1        # HT/10
    damage_max: int = 3        # HT/4
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    flying: bool = True
    view_distance: int = 4
    # Runtime
    floor_level: int = 1
    honey_pot_id: str = ""

class Sentry(MobEntity):
    """SentryRoom's guardian statue (levels/rooms/special/SentryRoom.java's
    nested Sentry class). Immovable, invulnerable, never attacks in melee --
    fires an unavoidable death-ray beam if the hero lingers on the room's
    "danger" floor tiles within line of sight. Watch-zone rect and charge
    delay are threaded in from GenMob.extra at spawn (see ai_sentry.py)."""
    name: str = "Sentry"
    faction: str = Faction.DUNGEON
    hp: int = 1
    max_hp: int = 1
    attack_skill: int = 0
    defense_skill: int = 0
    damage_min: int = 0
    damage_max: int = 0
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 0
    max_lvl: int = -2
    properties: List[str] = ["IMMOVABLE"]
    loot_table: List[DropEntry] = []
    never_wakes: bool = True

    # Runtime (populated from GenMob.extra at spawn; see spd_adapter._spawn_mob)
    watch_room: List[int] = [0, 0, 0, 0]  # (left, top, right, bottom)
    initial_charge_ticks: int = 20
    charge_ticks_left: int = 0
    charging: bool = False
    sentry_depth: int = 1

    def take_damage(self, amount: int):
        # Sentry.damage(): do nothing -- invulnerable.
        return 0

    def get_effective_defense_skill(self) -> int:
        # Sentry.defenseSkill(): INFINITE_EVASION -- always dodges.
        return 10 ** 9
