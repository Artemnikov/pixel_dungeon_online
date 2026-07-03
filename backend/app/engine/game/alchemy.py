# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 ArtemNikov
#
# Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
"""Alchemy station flows: preview, brew, energize, trinket choice.

Server-authoritative port of SPD's AlchemyScene interactions: the client only
sends selections and every gate re-validates here. One WS round-trip per
preview; brew is a single atomic message (no partial state on disconnect)."""
import random as _random
import uuid as _uuid
from collections import Counter
from typing import List, Optional

from app.engine.alchemy.energy import energy_val
from app.engine.alchemy.recipes import TrinketCatalystRecipe, usable_in_recipe
from app.engine.alchemy.registry import find_recipes
from app.engine.dungeon.generator import TileType
from app.engine.entities.base import Position
from app.engine.entities.items_artifacts import AlchemistsToolkit
from app.engine.entities.items_potions import ELIXIR_BREW_KINDS, Potion
from app.engine.entities.items_scrolls import Scroll
from app.engine.entities.trinkets import (
    _TRINKET_KINDS, TrinketCatalyst, trinket_class_for_kind,
)

MAX_SLOTS = 3
_STALE = "Your ingredients changed — try again."


class AlchemyMixin:
    # --- gates / helpers ----------------------------------------------------
    def _equipped_toolkit(self, player) -> Optional[AlchemistsToolkit]:
        art = player.belongings.artifact
        if isinstance(art, AlchemistsToolkit) and not art.cursed:
            return art
        return None

    def alchemy_gate_ok(self, player) -> bool:
        # Standing on/adjacent to an alchemy pot, or an equipped uncursed
        # toolkit (SPD: the toolkit is a portable pot).
        if self._equipped_toolkit(player) is not None:
            return True
        floor = self._get_or_create_floor(player.floor_id)
        px, py = player.pos.x, player.pos.y
        for dx, dy in ((0, 0), (0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = px + dx, py + dy
            if (nx, ny) in floor.alchemy_pots:
                return True
            if 0 <= ny < len(floor.grid) and 0 <= nx < len(floor.grid[0]):
                if floor.grid[ny][nx] == TileType.ALCHEMY:
                    return True
        return False

    def alchemy_available_energy(self, player) -> int:
        kit = self._equipped_toolkit(player)
        return player.energy + (kit.charge if kit else 0)

    def _alchemy_toast(self, player, text: str) -> None:
        self.add_event("TOAST", {"text": text},
                       floor_id=player.floor_id, player_id=player.id)

    def _spend_energy(self, player, cost: int) -> None:
        kit = self._equipped_toolkit(player)
        remainder = kit.consume_energy(cost) if kit else cost
        player.energy = max(0, player.energy - remainder)

    def _resolve_units(self, player, ingredient_ids: List[str]) -> Optional[List]:
        # One unit per id occurrence (SPD slots each hold a detached unit);
        # repeats allowed up to the stack's quantity.
        if not (1 <= len(ingredient_ids) <= MAX_SLOTS):
            return None
        counts = Counter(ingredient_ids)
        units = []
        for item_id in ingredient_ids:
            item = player.belongings.backpack.find(item_id)
            if item is None or not usable_in_recipe(item):
                return None
            if counts[item_id] > item.quantity:
                return None
            unit = item.model_copy(deep=True)
            unit.quantity = 1
            units.append(unit)
        return units

    def _grant_or_drop(self, player, item) -> None:
        if not item.id:
            item.id = str(_uuid.uuid4())
        if not player.add_to_inventory(item):
            item.pos = Position(x=player.pos.x, y=player.pos.y)
            floor = self._get_or_create_floor(player.floor_id)
            floor.items[item.id] = item

    # --- preview --------------------------------------------------------------
    def alchemy_preview(self, player_id: str, ingredient_ids: List[str]) -> None:
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        units = self._resolve_units(player, ingredient_ids)
        recipes = find_recipes(self, units) if units else []
        available = self.alchemy_available_energy(player)
        entries = []
        for idx, recipe in enumerate(recipes):
            out = recipe.sample_output(self, units)
            cost = recipe.cost(units)
            entry = {"recipe_index": idx, "cost": cost,
                     "affordable": cost <= available}
            if out is None:
                entry.update({"output_kind": None, "output_name": "???",
                              "output_quantity": 1, "known": False})
            else:
                # SPD Elixir.isKnown()/Brew.isKnown() always return true: these
                # are crafted potions, not randomized-appearance ones, so they
                # never hinge on identified_kinds.
                known = (not isinstance(out, (Potion, Scroll))
                         or out.kind in ELIXIR_BREW_KINDS
                         or out.kind in self.identified_kinds)
                typ = "potion" if isinstance(out, Potion) else "scroll"
                entry.update({
                    "output_kind": out.kind if known else None,
                    "output_name": out.name if known else self._label_for(out.kind, typ),
                    "output_quantity": out.quantity,
                    "known": known,
                })
            entries.append(entry)
        self.add_event("ALCHEMY_PREVIEW_RESULT", {
            "player": player.id, "ingredient_ids": list(ingredient_ids),
            "recipes": entries, "available_energy": available,
        }, floor_id=player.floor_id, player_id=player.id)

    # --- brew -------------------------------------------------------------------
    def alchemy_brew(self, player_id: str, ingredient_ids: List[str],
                     recipe_index: int) -> None:
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        if not self.alchemy_gate_ok(player):
            self._alchemy_toast(player, "You need an alchemy pot to brew.")
            return
        units = self._resolve_units(player, ingredient_ids)
        if units is None:
            self._alchemy_toast(player, _STALE)
            return
        recipes = find_recipes(self, units)
        if not (0 <= recipe_index < len(recipes)):
            self._alchemy_toast(player, _STALE)
            return
        recipe = recipes[recipe_index]
        cost = recipe.cost(units)
        if cost > self.alchemy_available_energy(player):
            self._alchemy_toast(player, "Not enough alchemical energy.")
            return

        # Catalyst rolls choices instead of producing output; it is consumed
        # only when the player picks a trinket (alchemy_trinket_choose).
        if isinstance(recipe, TrinketCatalystRecipe):
            catalyst = player.belongings.backpack.find(ingredient_ids[0])
            if not catalyst.rolled_kinds:
                self._spend_energy(player, cost)
                catalyst.rolled_kinds = _random.sample(_TRINKET_KINDS, 4)
            self.add_event("TRINKET_CHOICE", {
                "player": player.id, "catalyst_id": catalyst.id,
                "kinds": list(catalyst.rolled_kinds),
            }, floor_id=player.floor_id, player_id=player.id)
            return

        output = recipe.brew(self, units)
        if output is None:
            self._alchemy_toast(player, _STALE)
            return
        self._spend_energy(player, cost)

        # Consume one unit per slot occurrence; keep quickslot placeholders.
        for item_id in ingredient_ids:
            removed = player.belongings.backpack.detach(item_id)
            if removed is not None and player.belongings.get_item(item_id) is None:
                player.quickslot.convert_to_placeholder(removed)

        self._grant_or_drop(player, output)
        self.add_event("ALCHEMY_BREWED", {
            "player": player.id, "item_id": output.id, "item_kind": output.kind,
            "item_name": output.name, "quantity": output.quantity,
            "cost": cost, "energy": player.energy,
        }, floor_id=player.floor_id, player_id=player.id)

    # --- energize -----------------------------------------------------------------
    def alchemy_energize(self, player_id: str, item_id: str, all_items: bool) -> None:
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        if not self.alchemy_gate_ok(player):
            self._alchemy_toast(player, "You need an alchemy pot to convert items.")
            return
        item = player.belongings.backpack.find(item_id)
        if item is None:
            self._alchemy_toast(player, _STALE)
            return
        if energy_val(self, item) <= 0:
            self._alchemy_toast(player, "That can't be converted to energy.")
            return
        if all_items or item.quantity <= 1:
            removed = player.belongings.backpack.detach_all(item_id)
        else:
            removed = player.belongings.backpack.detach(item_id)
        if removed is None:
            return
        if player.belongings.get_item(item_id) is None:
            player.quickslot.convert_to_placeholder(removed)
        gained = energy_val(self, removed)
        player.energy += gained
        self.add_event("ALCHEMY_ENERGIZED", {
            "player": player.id, "amount": gained, "energy": player.energy,
        }, floor_id=player.floor_id, player_id=player.id)

    # --- trinket choice ----------------------------------------------------------
    def alchemy_trinket_choose(self, player_id: str, catalyst_id: str, kind: str) -> None:
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        catalyst = player.belongings.backpack.find(catalyst_id)
        if not isinstance(catalyst, TrinketCatalyst) or not catalyst.rolled_kinds:
            self._alchemy_toast(player, "There is no trinket to claim.")
            return
        if kind not in catalyst.rolled_kinds:
            return
        trinket_cls = trinket_class_for_kind(kind)
        if trinket_cls is None:
            return
        player.belongings.backpack.detach_all(catalyst_id)
        player.quickslot.clear_item(catalyst_id)
        trinket = trinket_cls()
        self._grant_or_drop(player, trinket)
        self.add_event("ALCHEMY_BREWED", {
            "player": player.id, "item_id": trinket.id, "item_kind": trinket.kind,
            "item_name": trinket.name, "quantity": 1, "cost": 0,
            "energy": player.energy,
        }, floor_id=player.floor_id, player_id=player.id)

    # --- toolkit energize (kit upgrade, 6 energy per level) ---------------------
    def toolkit_energize(self, player_id: str, toolkit_id: str, levels: int) -> None:
        player = self.players.get(player_id)
        if not player:
            return
        kit = self._equipped_toolkit(player)
        if kit is None or kit.id != toolkit_id:
            return
        max_levels = min(kit.level_cap - kit.level, player.energy // 6)
        levels = max(0, min(levels, max_levels))
        if levels <= 0:
            self._alchemy_toast(player, "Not enough alchemical energy.")
            return
        player.energy -= 6 * levels
        for _ in range(levels):
            kit.level += 1
            kit.level_known = True
            kit.on_upgrade()
        self.add_event("TOOLKIT_ENERGIZED", {
            "player": player.id, "toolkit_id": kit.id,
            "levels": levels, "level": kit.level,
        }, floor_id=player.floor_id, player_id=player.id)
