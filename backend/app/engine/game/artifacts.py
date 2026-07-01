# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
"""Artifact passive mechanics for GameInstance.

Mirrors the per-tick passive effects of each artifact (charge generation,
cape retaliation, chalice regen, etc.). Called from TickMixin.update_tick
via tick_artifacts(player, dt).
"""
import random

from app.engine.entities.items_artifacts import AlchemistsToolkit, CapeOfThorns, ChaliceOfBlood, EtherealChains, HolyTome, HornOfPlenty, LloydsBeacon, MasterThievesArmband, SandalsOfNature, SkeletonKey, TalismanOfForesight, TimekeepersHourglass, UnstableSpellbook
from app.engine.entities.player import Player
from app.engine.dungeon.generator import TileType

# Seconds per charge tick for passive-recharge artifacts.
_SLOW_RECHARGE = 50.0    # ~50s per charge (EtherealChains, LloydsBeacon, SkeletonKey, Armband, Hourglass)
_TOOLKIT_RECHARGE = 10.0  # 10s per energy charge (AlchemistsToolkit)
_HORN_RECHARGE = 20.0    # 20s per food charge (HornOfPlenty)
_TALISMAN_RECHARGE = 1.0  # 1s per talisman charge (TalismanOfForesight, 100-cap)
_SPELLBOOK_RECHARGE = 90.0  # ~90s per charge (UnstableSpellbook; SPD ~80-120 turns)


def _gain_exp(item, amount: int) -> None:
    if item.level >= item.level_cap:
        return
    item.exp += amount
    threshold = (item.level + 1) * 50
    if item.exp >= threshold:
        item.exp -= threshold
        item.level += 1
        item.level_known = True
        item.on_upgrade()


class ArtifactsMixin:

    def tick_artifacts(self, player: Player, dt: float) -> None:
        artifact = player.belongings.artifact
        if artifact is None:
            return
        if not player.belongings.is_equipped(artifact.id):
            return
        if artifact.cursed:
            return

        kind = getattr(artifact, "kind", "")

        if kind == "alchemists_toolkit":
            self._tick_toolkit(player, artifact, dt)
        elif kind == "cape_of_thorns":
            self._tick_cape(player, artifact, dt)
        elif kind == "chalice_of_blood":
            self._tick_chalice(player, artifact, dt)
        elif kind == "ethereal_chains":
            self._tick_ethereal_chains(player, artifact, dt)
        elif kind == "holy_tome":
            self._tick_holy_tome(player, artifact, dt)
        elif kind == "horn_of_plenty":
            self._tick_horn(player, artifact, dt)
        elif kind == "lloyds_beacon":
            self._tick_beacon(player, artifact, dt)
        elif kind == "master_thieves_armband":
            self._tick_armband(player, artifact, dt)
        elif kind == "sandals_of_nature":
            self._tick_sandals(player, artifact, dt)
        elif kind == "skeleton_key":
            self._tick_skeleton_key(player, artifact, dt)
        elif kind == "talisman_of_foresight":
            self._tick_talisman(player, artifact, dt)
        elif kind == "timekeepers_hourglass":
            self._tick_hourglass(player, artifact, dt)
        elif kind == "unstable_spellbook":
            self._tick_spellbook(player, artifact, dt)

    # -----------------------------------------------------------------------
    # AlchemistsToolkit — passive energy generation
    # -----------------------------------------------------------------------
    def _tick_toolkit(self, player: Player, item: AlchemistsToolkit, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._charge_accum += dt
        while item._charge_accum >= _TOOLKIT_RECHARGE:
            item._charge_accum -= _TOOLKIT_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # CapeOfThorns — absorb damage into charge, retaliate at 100
    # Called from combat (on_player_hit) and also ticks down stale charge.
    # -----------------------------------------------------------------------
    def on_cape_absorb(self, player: Player, damage: int) -> int:
        """Call when player takes damage while wearing CapeOfThorns.
        Returns the damage after any absorption (cape absorbs nothing, just charges)."""
        artifact = player.belongings.artifact
        if artifact is None or getattr(artifact, "kind", "") != "cape_of_thorns":
            return damage
        if not player.belongings.is_equipped(artifact.id) or artifact.cursed:
            return damage

        artifact.charge = min(artifact.charge_cap, artifact.charge + damage)
        if artifact.charge >= artifact.charge_cap:
            self._cape_retaliate(player, artifact)
        return damage

    def _cape_retaliate(self, player: Player, item: CapeOfThorns) -> None:
        floor = self._get_or_create_floor(player.floor_id)
        bonus = 0.30 + item.level * 0.03
        retaliate_dmg = max(1, round(item.charge * bonus))
        item.charge = 0
        _gain_exp(item, 10)

        # Deal retaliate damage to all adjacent hostiles.
        for mob in floor.mobs.values():
            if not mob.is_alive or mob.faction == "player":
                continue
            if (abs(mob.pos.x - player.pos.x) <= 1 and
                    abs(mob.pos.y - player.pos.y) <= 1):
                mob.take_damage(retaliate_dmg)
                self.add_event("DAMAGE", {
                    "target": mob.id, "amount": retaliate_dmg, "thorns": True,
                }, floor_id=player.floor_id)

        self.add_event("CAPE_RETALIATE", {
            "player": player.id, "damage": retaliate_dmg,
        }, floor_id=player.floor_id, source_player_id=player.id)
        self.add_event("PLAY_SOUND", {"sound": "HIT"}, floor_id=player.floor_id)

    def _tick_cape(self, player: Player, item: CapeOfThorns, dt: float) -> None:
        # No passive generation; charge absorbs from hits (see on_cape_absorb).
        pass

    # -----------------------------------------------------------------------
    # ChaliceOfBlood — enhanced regen buff while equipped
    # -----------------------------------------------------------------------
    def _tick_chalice(self, player: Player, item: ChaliceOfBlood, dt: float) -> None:
        if not hasattr(item, "_regen_accum"):
            item._regen_accum = 0.0
        item._regen_accum += dt
        regen_interval = 10.0
        while item._regen_accum >= regen_interval:
            item._regen_accum -= regen_interval
            heal = 1 + item.level
            max_hp = player.get_total_max_hp()
            if player.hp < max_hp:
                player.hp = min(max_hp, player.hp + heal)
                self.add_event("HEAL", {
                    "target": player.id, "amount": heal,
                    "x": player.pos.x, "y": player.pos.y,
                }, floor_id=player.floor_id)

    # -----------------------------------------------------------------------
    # EtherealChains — passive recharge
    # -----------------------------------------------------------------------
    def _tick_ethereal_chains(self, player: Player, item: EtherealChains, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._recharge_accum += dt
        while item._recharge_accum >= _SLOW_RECHARGE:
            item._recharge_accum -= _SLOW_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # HolyTome — charges when player reads scrolls (see on_scroll_read hook)
    # -----------------------------------------------------------------------
    def _tick_holy_tome(self, player: Player, item: HolyTome, dt: float) -> None:
        pass  # charges via on_holy_tome_scroll_read, not by time

    def on_holy_tome_scroll_read(self, player: Player) -> None:
        """Call from scroll_actions after a scroll is read while tome is equipped."""
        artifact = player.belongings.artifact
        if artifact is None or getattr(artifact, "kind", "") != "holy_tome":
            return
        if not player.belongings.is_equipped(artifact.id):
            return
        artifact.charge = min(artifact.charge + 1, artifact.charge_cap)

    # -----------------------------------------------------------------------
    # HornOfPlenty — passive food charge generation
    # -----------------------------------------------------------------------
    def _tick_horn(self, player: Player, item: HornOfPlenty, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._charge_accum += dt
        while item._charge_accum >= _HORN_RECHARGE:
            item._charge_accum -= _HORN_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # LloydsBeacon — passive recharge
    # -----------------------------------------------------------------------
    def _tick_beacon(self, player: Player, item: LloydsBeacon, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._recharge_accum += dt
        while item._recharge_accum >= _SLOW_RECHARGE:
            item._recharge_accum -= _SLOW_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # MasterThievesArmband — passive steal-on-kill; also passive recharge
    # -----------------------------------------------------------------------
    def _tick_armband(self, player: Player, item: MasterThievesArmband, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._recharge_accum += dt
        while item._recharge_accum >= _SLOW_RECHARGE:
            item._recharge_accum -= _SLOW_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)

    def on_armband_kill(self, player: Player, mob) -> None:
        """Call when a player kills a mob while the armband is equipped."""
        artifact = player.belongings.artifact
        if artifact is None or getattr(artifact, "kind", "") != "master_thieves_armband":
            return
        if not player.belongings.is_equipped(artifact.id) or artifact.cursed:
            return
        # Passive thievery: small chance to steal gold.
        steal_chance = (artifact.level * 5 + 15) / 100.0
        if random.random() < steal_chance:
            gold = random.randint(1, max(1, player.floor_id * 2))
            player.gold += gold
            _gain_exp(artifact, 5)
            self.add_event("STEAL", {
                "player": player.id, "target": mob.id,
                "gold": gold, "success": True, "passive": True,
            }, floor_id=player.floor_id, source_player_id=player.id)

    # -----------------------------------------------------------------------
    # SandalsOfNature — charge on grass tiles stepped on
    # -----------------------------------------------------------------------
    def _tick_sandals(self, player: Player, item: SandalsOfNature, dt: float) -> None:
        pass  # charges via on_sandals_step, not by time

    def on_sandals_step(self, player: Player) -> None:
        """Call from movement when player steps onto a grass tile."""
        artifact = player.belongings.artifact
        if artifact is None or getattr(artifact, "kind", "") != "sandals_of_nature":
            return
        if not player.belongings.is_equipped(artifact.id) or artifact.cursed:
            return
        floor = self._get_or_create_floor(player.floor_id)
        tile = floor.grid[player.pos.y][player.pos.x]
        grass_tiles = (TileType.FLOOR_GRASS, TileType.HIGH_GRASS, TileType.FURROWED_GRASS)
        if tile not in grass_tiles:
            return
        if artifact.charge < artifact.charge_cap:
            artifact.charge = min(artifact.charge + 1, artifact.charge_cap)
        # At full charge, absorb a seed from the tile if one exists.
        if artifact.charge >= artifact.charge_cap:
            tile_seeds = floor.plants.get((player.pos.x, player.pos.y))
            if tile_seeds and len(artifact.stored_seeds) < 5:
                artifact.stored_seeds.append(tile_seeds + "_seed")
                floor.plants.pop((player.pos.x, player.pos.y), None)
                _gain_exp(artifact, 5)

    # -----------------------------------------------------------------------
    # SkeletonKey — passive recharge
    # -----------------------------------------------------------------------
    def _tick_skeleton_key(self, player: Player, item: SkeletonKey, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._recharge_accum += dt
        while item._recharge_accum >= 40.0:
            item._recharge_accum -= 40.0
            item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # TalismanOfForesight — passive charge generation (slow)
    # -----------------------------------------------------------------------
    def _tick_talisman(self, player: Player, item: TalismanOfForesight, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._charge_accum += dt
        while item._charge_accum >= _TALISMAN_RECHARGE:
            item._charge_accum -= _TALISMAN_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # TimekeepersHourglass — passive recharge + tick down freeze
    # -----------------------------------------------------------------------
    def _tick_hourglass(self, player: Player, item: TimekeepersHourglass, dt: float) -> None:
        # Tick down time-frozen state.
        if item.time_frozen and item.freeze_turns > 0:
            item.freeze_turns -= 1
            if item.freeze_turns <= 0:
                item.time_frozen = False
                item.freeze_turns = 0
                self.add_event("TIME_UNFREEZE", {
                    "player": player.id,
                }, floor_id=player.floor_id, source_player_id=player.id)

        # Passive recharge.
        if item.charge < item.charge_cap:
            item._recharge_accum += dt
            while item._recharge_accum >= _SLOW_RECHARGE:
                item._recharge_accum -= _SLOW_RECHARGE
                item.charge = min(item.charge + 1, item.charge_cap)

    # -----------------------------------------------------------------------
    # UnstableSpellbook — passive time-based recharge (mirrors bookRecharge)
    # -----------------------------------------------------------------------
    def _tick_spellbook(self, player: Player, item: UnstableSpellbook, dt: float) -> None:
        if item.charge >= item.charge_cap:
            return
        item._recharge_accum += dt
        while item._recharge_accum >= _SPELLBOOK_RECHARGE:
            item._recharge_accum -= _SPELLBOOK_RECHARGE
            item.charge = min(item.charge + 1, item.charge_cap)
