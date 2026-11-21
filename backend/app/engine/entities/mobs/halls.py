# Copyright (C) 2026 ArtemNikov
#
import random
from typing import ClassVar, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.engine.entities.mobs.city import Eye, Scorpio, RipperDemon
from app.engine.entities.base import is_immune
from app.engine.entities.player import Mob as MobEntity, DropEntry
from app.engine.game.constants import (
    OOZE_DURATION, YOG_DAMAGE_CD_DIVISOR, YOG_MINION_AGGRO_RADIUS, YOG_FINAL_HP, YOG_FIST_INVULN_RADIUS,
    YOG_FIST_LOCK_DIVISOR, YOG_FIST_LOCK_DIVISOR_STRONG, YOG_FIST_ROTTING_BLEED,
    YOG_LOCK_DIVISOR, YOG_LOCK_DIVISOR_STRONG, YOG_PHASE_HP_STEP, YOG_PHASE_UP_MIN_CD,
)

# ---------------------------------------------------------------------------
# Boss YogDzewa (floor 25): fists, summons, invincibility helpers
# ---------------------------------------------------------------------------

class YogDzewa(MobEntity):
    """Port of SPD `actors/mobs/YogDzewa.java`. IMMOVABLE, DEMONIC.

    Phase 0 waits to be noticed; phases 1-4 each add a fist and Yog is
    invulnerable while any fist lives; phase 5 is the final 100 HP. The act
    itself lives in game/ai_yog_dzewa.py; cooldowns are in SPD turns.
    """
    type: str = "boss"
    name: str = "Yog-Dzewa"
    hp: int = 1000
    max_hp: int = 1000
    attack_skill: int = 999
    defense_skill: int = 0
    damage_min: int = 20
    damage_max: int = 30
    dr_min: int = 0
    dr_max: int = 0
    exp: int = 50
    max_lvl: int = -2
    flying: bool = True
    view_distance: int = 12
    properties: List[str] = ["BOSS", "DEMONIC", "IMMOVABLE", "STATIC"]
    immunities: List[str] = Field(default_factory=lambda: [
        "dread", "terror", "amok", "charm", "sleep", "magical_sleep", "paralysis",
        "frost", "frozen", "chill", "slow", "vertigo"])
    loot_table: List[DropEntry] = []
    owns_attacks: ClassVar[bool] = True

    phase: int = 0
    fight_started: bool = False
    fist_ids: List[str] = Field(default_factory=list)
    fists_alive: int = 0
    fist_order: List[str] = Field(default_factory=list)
    challenge_summons: List[str] = Field(default_factory=list)
    regular_summons: List[str] = Field(default_factory=list)
    targeted_cells: List[Tuple[int, int]] = Field(default_factory=list)
    beam_target_id: str = ""
    ability_cooldown: float = 0.0
    summon_cooldown: float = 0.0
    pending_phase_ups: int = Field(default=0, exclude=True)
    locked_floor_credit: float = Field(default=0.0, exclude=True)
    status_popups: List[str] = Field(default_factory=list, exclude=True)
    stronger: bool = Field(default=False, exclude=True)

    def is_invulnerable(self) -> bool:
        return self.phase == 0 or self.fists_alive > 0

    def defense_proc(self, damage: int, attacker, floor_mobs: dict, tile_x: int, tile_y: int, **kwargs) -> int:
        """`YogDzewa.aggro`: Yog's minions within 4 tiles turn on its attacker."""
        if attacker is not None and getattr(attacker, "faction", self.faction) != self.faction:
            for m in (floor_mobs or {}).values():
                if (m.is_alive and isinstance(m, (Larva, YogRipper, YogEye, YogScorpio))
                        and max(abs(m.pos.x - self.pos.x), abs(m.pos.y - self.pos.y)) <= YOG_MINION_AGGRO_RADIUS):
                    m.aggro_target_id = attacker.id
                    m.ai_state = "hunting"
        return damage

    def take_damage(self, amount: int, is_split_damage: bool = False) -> int:
        """`YogDzewa.damage()`."""
        if amount < 0 or not self.is_alive:
            return 0
        if self.is_invulnerable():
            self.status_popups.append("invulnerable")
            return 0
        pre_hp = self.hp
        super().take_damage(amount, is_split_damage)
        if self.phase < 4:
            self.hp = max(self.hp, self.max_hp - YOG_PHASE_HP_STEP * self.phase)
        elif self.phase == 4:
            self.hp = max(self.hp, YOG_FINAL_HP)
        self.is_alive = self.hp > 0
        taken = pre_hp - self.hp
        if taken > 0:
            self.ability_cooldown -= taken / YOG_DAMAGE_CD_DIVISOR
            self.summon_cooldown -= taken / YOG_DAMAGE_CD_DIVISOR
        if self.phase < 4 and self.hp <= self.max_hp - YOG_PHASE_HP_STEP * self.phase:
            self.phase += 1
            self.pending_phase_ups += 1
            self.fists_alive += 2 if self.stronger else 1
            self.ability_cooldown = max(self.ability_cooldown, YOG_PHASE_UP_MIN_CD)
            self.summon_cooldown = max(self.summon_cooldown, YOG_PHASE_UP_MIN_CD)
        elif taken > 0:
            divisor = YOG_LOCK_DIVISOR_STRONG if self.stronger else YOG_LOCK_DIVISOR
            self.locked_floor_credit += taken / divisor
        return taken


def _is_fist_near_yog(fist, floor_mobs: dict = None) -> bool:
    """`YogFist.isNearYog()`: Chebyshev distance <= 4 from Yog's cell
    (exit + 3 rows), whatever Yog's own state."""
    yog_pos = fist.yog_pos
    if yog_pos is None:
        return False
    return max(abs(fist.pos.x - yog_pos[0]), abs(fist.pos.y - yog_pos[1])) <= YOG_FIST_INVULN_RADIUS


class _YogFistMixin(BaseModel):
    """Shared state of SPD `YogFist` (game/ai_yog_fists.py holds the act)."""
    yog_id: str = ""
    yog_pos: Optional[Tuple[int, int]] = None
    view_distance: int = 6
    ai_state: str = "hunting"
    ranged_cooldown: float = 0.0
    invuln_warned: bool = False
    status_popups: List[str] = Field(default_factory=list, exclude=True)
    locked_floor_credit: float = Field(default=0.0, exclude=True)
    stronger: bool = Field(default=False, exclude=True)
    owns_attacks: ClassVar[bool] = True
    can_ranged_in_melee: ClassVar[bool] = True
    has_ranged_cooldown: ClassVar[bool] = True
    fist_kind: ClassVar[str] = ""

    def is_invulnerable(self) -> bool:
        if _is_fist_near_yog(self):
            if not self.invuln_warned:
                self.invuln_warned = True
                self.status_popups.append("invuln_warn")
            return True
        return False

    def _credit_lock(self, taken: int) -> None:
        if taken > 0:
            divisor = YOG_FIST_LOCK_DIVISOR_STRONG if self.stronger else YOG_FIST_LOCK_DIVISOR
            self.locked_floor_credit += taken / divisor

    def take_damage(self, amount: int, is_split_damage: bool = False):
        if amount < 0 or not self.is_alive:
            return 0
        if self.is_invulnerable():
            self.status_popups.append("invulnerable")
            return 0
        pre = self.hp
        super().take_damage(amount, is_split_damage)
        taken = pre - self.hp
        self._credit_lock(taken)
        return taken


class BurningFist(_YogFistMixin, MobEntity):
    """`YogFist.BurningFist`: FIERY; immune to Frost; tops up fire around itself."""
    type: str = "boss"
    name: str = "Burning Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    attack_range: int = 8
    properties: List[str] = ["BOSS", "DEMONIC", "FIERY"]
    immunities: List[str] = Field(default_factory=lambda: ["burning", "blazing", "frost", "frozen", "chill", "sleep"])
    loot_table: List[DropEntry] = []
    fist_kind: ClassVar[str] = "burning"


class SoiledFist(_YogFistMixin, MobEntity):
    """`YogFist.SoiledFist`: grows grass; damage shrinks with nearby tall grass."""
    type: str = "boss"
    name: str = "Soiled Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    attack_range: int = 8
    properties: List[str] = ["BOSS", "DEMONIC"]
    immunities: List[str] = Field(default_factory=lambda: ["sleep"])
    loot_table: List[DropEntry] = []
    fist_kind: ClassVar[str] = "soiled"
    grass_cells_nearby: int = Field(default=0, exclude=True)

    def take_damage(self, amount: int, is_split_damage: bool = False):
        n = self.grass_cells_nearby
        if n > 0:
            amount = round(amount * (6 - n) / 6)
        if amount < 0:
            return 0
        return super().take_damage(amount, is_split_damage)

    def take_burning_damage(self, amount: int) -> int:
        return 0


class RottingFist(_YogFistMixin, MobEntity):
    """`YogFist.RottingFist`: ACIDIC; turns damage into Bleeding; heals in water."""
    type: str = "boss"
    name: str = "Rotting Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    attack_range: int = 8
    properties: List[str] = ["BOSS", "DEMONIC", "ACIDIC"]
    immunities: List[str] = Field(default_factory=lambda: ["toxic_gas", "ooze", "sleep"])
    loot_table: List[DropEntry] = []
    fist_kind: ClassVar[str] = "rotting"

    def take_damage(self, amount: int, is_split_damage: bool = False):
        if amount < 0 or not self.is_alive:
            return 0
        if self.is_invulnerable():
            self.status_popups.append("invulnerable")
            return 0
        from app.engine.game.bleeding import apply_bleeding
        apply_bleeding(self, amount * YOG_FIST_ROTTING_BLEED)
        self.status_popups.append(f"bleeding:{int(self.bleeding_level)}")
        return 0

    def take_bleed_damage(self, amount: int) -> int:
        pre = self.hp
        MobEntity.take_damage(self, amount)
        taken = pre - self.hp
        self._credit_lock(taken)
        return taken

    def attack_proc(self, target):
        # RottingFist.attackProc: 50% Ooze for Ooze.DURATION.
        if random.random() < 0.5 and not is_immune(target, "ooze"):
            target.ooze_amount = OOZE_DURATION


class RustedFist(_YogFistMixin, MobEntity):
    """`YogFist.RustedFist`: LARGE, INORGANIC; defers all damage (Viscosity)."""
    type: str = "boss"
    name: str = "Rusted Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 22
    damage_max: int = 44
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    attack_range: int = 8
    properties: List[str] = ["BOSS", "DEMONIC", "LARGE", "INORGANIC"]
    immunities: List[str] = Field(default_factory=lambda: ["bleeding", "toxic_gas", "poison", "sleep"])
    loot_table: List[DropEntry] = []
    fist_kind: ClassVar[str] = "rusted"
    large_pathing: ClassVar[bool] = True

    def take_damage(self, amount: int, is_split_damage: bool = False):
        if amount < 0 or not self.is_alive:
            return 0
        if self.is_invulnerable():
            self.status_popups.append("invulnerable")
            return 0
        from app.engine.game.deferred_damage import extend_deferred
        extend_deferred(self, amount)
        self.status_popups.append(f"deferred:{amount}")
        return 0

    def take_deferred_damage(self, amount: int) -> int:
        pre = self.hp
        MobEntity.take_damage(self, amount)
        taken = pre - self.hp
        self._credit_lock(taken)
        return taken


class _HalfHpTeleportFist(_YogFistMixin):
    can_ranged_in_melee: ClassVar[bool] = False
    has_ranged_cooldown: ClassVar[bool] = False
    pending_teleport: bool = Field(default=False, exclude=True)
    pending_death_flash: bool = Field(default=False, exclude=True)

    def take_damage(self, amount: int, is_split_damage: bool = False):
        before = self.hp
        taken = _YogFistMixin.take_damage(self, amount, is_split_damage)
        half = self.max_hp // 2
        if self.is_alive and before > half and self.hp <= half:
            self.hp = half
            self.pending_teleport = True
        elif not self.is_alive:
            self.pending_death_flash = True
        return taken


class BrightFist(_HalfHpTeleportFist, MobEntity):
    """`YogFist.BrightFist`: ELECTRIC; light beam blinds; teleports at half HP."""
    type: str = "boss"
    name: str = "Bright Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    attack_range: int = 8
    properties: List[str] = ["BOSS", "DEMONIC", "ELECTRIC"]
    immunities: List[str] = Field(default_factory=lambda: ["sleep"])
    loot_table: List[DropEntry] = []
    fist_kind: ClassVar[str] = "bright"


class DarkFist(_HalfHpTeleportFist, MobEntity):
    """`YogFist.DarkFist`: dark bolt weakens Light; teleports at half HP."""
    type: str = "boss"
    name: str = "Dark Fist"
    hp: int = 300
    max_hp: int = 300
    attack_skill: int = 36
    defense_skill: int = 20
    damage_min: int = 18
    damage_max: int = 36
    dr_min: int = 0
    dr_max: int = 15
    exp: int = 25
    max_lvl: int = -2
    attack_range: int = 8
    properties: List[str] = ["BOSS", "DEMONIC"]
    immunities: List[str] = Field(default_factory=lambda: ["sleep"])
    loot_table: List[DropEntry] = []
    fist_kind: ClassVar[str] = "dark"


class YogEye(Eye):
    """YogDzewa summon — Eye minion variant. BOSS_MINION."""
    name: str = "Yog Eye"
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    max_lvl: int = -2


class YogScorpio(Scorpio):
    """YogDzewa summon — Scorpio minion variant. BOSS_MINION."""
    name: str = "Yog Scorpio"
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    max_lvl: int = -2


class YogRipper(RipperDemon):
    """YogDzewa summon — RipperDemon minion variant. BOSS_MINION."""
    name: str = "Yog Ripper"
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    max_lvl: int = -2


class Larva(MobEntity):
    """Yog-Dzewa minion: Larva. HP=20, defense=12, attack=30, dmg=15-25, dr=0-4."""
    name: str = "Larva"
    hp: int = 20
    max_hp: int = 20
    attack_skill: int = 30
    defense_skill: int = 12
    damage_min: int = 15
    damage_max: int = 25
    dr_min: int = 0
    dr_max: int = 4
    exp: int = 5
    max_lvl: int = -2
    view_distance: int = 6
    properties: List[str] = ["DEMONIC", "BOSS_MINION"]
    loot_table: List[DropEntry] = []

