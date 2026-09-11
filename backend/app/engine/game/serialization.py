# Copyright (C) 2026 ArtemNikov
#
"""Client state serialization and per-run identification masking.

Builds the per-player game-state snapshot sent over the WebSocket, and scrambles
the names/appearance of still-unidentified potions and scrolls (SPD's randomised
potion colours / scroll runes, shared per-run across the co-op party).
"""

import time
from typing import Dict, Optional

from app.engine.alchemy.energy import energy_val
from app.engine.alchemy.recipes import POTION_TO_EXOTIC, SCROLL_TO_EXOTIC
from app.engine.entities.items.union import Bag
from app.engine.entities.items.consumables import LostBackpack
from app.engine.entities.items.potions import ELIXIR_BREW_KINDS
from app.engine.entities.player import Difficulty
from app.engine.entities.locale_keys import item_locale_key, mob_locale_key

# How long a freshly-dropped item (chest-open / monster-death loot) keeps
# reporting `just_dropped` over the wire, so the client's drop-bounce
# animation only fires for genuine fresh drops -- not for old floor loot
# re-entering FOV. Only needs to outlast typical poll latency, not the
# 400ms client-side bounce animation itself.
DROP_ANIM_WINDOW = 2.0


class SerializationMixin:
    def change_difficulty(self, new_level: str):
        if new_level in [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]:
            self.difficulty = new_level

    KNOWN_CHALLENGES = {"stronger_bosses"}

    def set_challenges(self, challenges_str: str):
        self.challenges = {
            c for c in challenges_str.split(",") if c in self.KNOWN_CHALLENGES
        }

    # --- identification masking -------------------------------------------
    # Per-run scrambled display names for still-unidentified consumable kinds
    # (mirrors SPD's randomised potion colours / scroll runes).
    # Ordered to match the sprite columns in items.png (POTIONS row 22 / SCROLLS
    # row 19, ItemSpriteSheet.java), so a kind's appearance index doubles as its
    # sprite column.
    _POTION_LABELS = ["Crimson", "Amber", "Golden", "Jade", "Turquoise", "Azure",
                      "Indigo", "Magenta", "Bistre", "Charcoal", "Silver", "Ivory"]
    _SCROLL_LABELS = ["Kaunan", "Sowilo", "Laguz", "Yngvi", "Gyfu", "Raido",
                      "Isaz", "Mannaz", "Naudiz", "Berkanan", "Odal", "Tiwaz"]
    _RING_GEMS = ["garnet", "ruby", "topaz", "emerald", "onyx", "opal",
                  "tourmaline", "sapphire", "amethyst", "quartz", "agate", "diamond"]
    _APPEARANCE_ROW = {"potion": 22, "scroll": 19, "ring": 14}
    # Exotic potions/scrolls render one row below their standard counterparts
    # (SPD: EXOTIC_POTIONS / EXOTIC_SCROLLS = base row + 16 slots).
    _EXOTIC_ROW = {"potion": 23, "scroll": 20}
    # SPD ExoticPotion/ExoticScroll share the BASE kind's per-run colour/rune and
    # only move to the exotic row (ExoticScroll.java: image = handler.image(base)
    # + 16). The remake's "Scroll of Enchantment" is SPD's exotic-of-upgrade
    # (ExoticScroll.regToExo: ScrollOfUpgrade -> ScrollOfEnchantment), so both it
    # and "Exotic Scroll of Enchantment" resolve to scroll_of_upgrade.
    _EXOTIC_TO_BASE_KIND = {
        exo.model_fields["kind"].default: reg.model_fields["kind"].default
        for reg, exo in {**POTION_TO_EXOTIC, **SCROLL_TO_EXOTIC}.items()
    }
    _EXOTIC_TO_BASE_KIND["scroll_of_enchantment"] = "scroll_of_upgrade"
    # Remake-only potions with no SPD sprite slot: pin a fixed colour so they
    # don't draw from (and overflow) the 12-slot scramble pool.
    _FIXED_APPEARANCE = {
        "reviving_potion": (11, 22),  # IVORY
        "fury_potion": (3, 22),       # GOLDEN
    }

    def _kind_index(self, kind: str, typ: str) -> int:
        # Stable per-run colour/rune index for a potion/scroll kind. Assigns the
        # next free index of that type on first sight. Exotic kinds resolve to
        # their base kind (sharing its index, never consuming a pool slot);
        # fixed-appearance kinds return their pinned colour.
        kind = self._EXOTIC_TO_BASE_KIND.get(kind, kind)
        fixed = self._FIXED_APPEARANCE.get(kind)
        if fixed is not None:
            return fixed[0]
        if kind not in self.kind_appearance:
            used = self._appearance_used.get(typ)
            if used is None:
                used = self._appearance_used[typ] = set()
            idx = next((i for i in range(12) if i not in used), len(used))
            used.add(idx)
            self.kind_appearance[kind] = idx
        return self.kind_appearance[kind]

    def _label_for(self, kind: str, typ: str) -> str:
        if kind not in self.kind_labels:
            if typ == "potion":
                pool = self._POTION_LABELS
            elif typ == "scroll":
                pool = self._SCROLL_LABELS
            else:
                pool = self._RING_GEMS
            idx = self._kind_index(kind, typ)
            word = pool[idx] if idx < len(pool) else kind
            if typ == "potion":
                self.kind_labels[kind] = f"{word} Potion"
            elif typ == "scroll":
                self.kind_labels[kind] = f"Scroll of {word}"
            else:
                self.kind_labels[kind] = f"Ring of {word.title()}"
        return self.kind_labels[kind]

    def _appearance_for(self, kind: str, typ: str) -> dict:
        # Sprite cell [col, row] for a potion/scroll's per-run colour/rune. Sent
        # for every potion/scroll regardless of identification. Exotic kinds are
        # drawn on the exotic row at their base's column.
        fixed = self._FIXED_APPEARANCE.get(kind)
        if fixed is not None:
            return {"col": fixed[0], "row": fixed[1]}
        exotic = kind in self._EXOTIC_TO_BASE_KIND
        row = self._EXOTIC_ROW[typ] if exotic else self._APPEARANCE_ROW[typ]
        return {"col": self._kind_index(kind, typ), "row": row}

    def _mask_item_dict(self, d: Optional[dict], known=None) -> Optional[dict]:
        # Recursively obscure unidentified potion/scroll/ring types in a serialized
        # item dict: scramble the name, collapse `kind` to the generic category so
        # the client can't read the subtype, and hide subtype fields.
        # `known` is the set of kinds the *viewer* has personally discovered
        # (default: the party-shared identified_kinds for callers with no
        # per-player context).
        if not d:
            return d
        if known is None:
            known = self.identified_kinds
        items = d.get("items")
        if isinstance(items, list):
            for it in items:
                self._mask_item_dict(it, known)
        typ = d.get("type")
        # Crafted elixirs/brews are always known (SPD Elixir.isKnown()/Brew.isKnown()):
        # they never enter the per-run scrambled-identity pool, so they get neither a
        # scrambled appearance nor name/kind masking. Generic no-subtype entries
        # (kind == type, e.g. the debug "Potion") are already generic: assigning
        # them an appearance would consume a 13th pool slot and overflow to a
        # blank cell, so they must stay outside the scramble pool too.
        no_subtype = d.get("kind") == typ
        if typ in ("potion", "scroll", "ring") and d.get("kind") not in ELIXIR_BREW_KINDS:
            if not no_subtype:
                # Attach the per-run colour/rune/gem sprite from the TRUE kind before
                # any masking collapses it. The visual keeps its colour after ID (SPD).
                d["appearance"] = self._appearance_for(d["kind"], typ)
        if (typ in ("potion", "scroll", "ring")
                and d.get("kind") not in ELIXIR_BREW_KINDS
                and not no_subtype
                and d.get("kind") not in known):
            d["name"] = self._label_for(d["kind"], typ)
            d["kind"] = typ
            d.pop("effect", None)
            d.pop("buff_class", None)
            d["level_known"] = False
            d.pop("locale_key", None)
            if "description" in d:
                if typ == "potion":
                    d["description"] = "You'll have to drink it to find out what it does."
                elif typ == "scroll":
                    d["description"] = "You'll have to read it to find out what it does."
                else:
                    d["description"] = "You'll have to wear it to find out what it does."
        return d

    def _serialize_player(self, p, known=None) -> dict:
        d = p.model_dump()
        d.pop("discovered_kinds", None)
        if known is None:
            known = self.identified_kinds

        id2item: Dict[str, object] = {}

        def collect(bag):
            id2item[bag.id] = bag
            for it in bag.items:
                id2item[it.id] = it
                if isinstance(it, Bag):
                    collect(it)

        collect(p.belongings.backpack)
        for s in p.belongings.equipped_slots():
            if s is not None:
                id2item[s.id] = s

        def process(node):
            if not node:
                return
            for it in (node.get("items") or []):
                process(it)
            live = id2item.get(node.get("id"))
            if live is not None:
                node["actions"] = live.actions(p)
                node["default_action"] = live.default_action()
                node["is_throwable"] = getattr(live, "is_throwable", False)
                node["throw_behavior"] = getattr(live, "throw_behavior", "regular")
                if hasattr(live, "get_reach"):
                    node["range"] = live.get_reach()
                node["description"] = live.description(p)
                node["value"] = live.value(identified=live.kind in known)
                if hasattr(live, "buffed_visibly_upgraded"):
                    node["buffed_level"] = live.buffed_visibly_upgraded()
                node["energy_value"] = energy_val(self, live, known)
                unit = live if live.quantity <= 1 else live.model_copy(update={"quantity": 1})
                node["energy_value_one"] = energy_val(self, unit, known)
                lk = item_locale_key(live)
                if lk:
                    node["locale_key"] = lk
            self._mask_item_dict(node, known)

        belongings = d.get("belongings", {})
        for slot in ("weapon", "armor", "artifact", "misc", "ring"):
            process(belongings.get(slot))
        process(belongings.get("backpack"))
        for it in (d.get("inventory") or []):
            process(it)
        process(d.get("equipped_weapon"))
        process(d.get("equipped_wearable"))

        hunger = d.get("hunger", 0.0)
        d["hunger_pct"] = round(min(1.0, hunger / 450.0), 3)

        # Find an adjacent hostile mob (attack target for auto-attack UI)
        attack_target = None
        enemies_nearby = False
        try:
            floor = self._get_or_create_floor(p.floor_id)
            enemies_nearby = self._has_enemies_nearby(floor, p, radius=3)
            for mob in floor.mobs.values():
                if mob.is_alive and mob.faction == "dungeon" and abs(mob.pos.x - p.pos.x) + abs(mob.pos.y - p.pos.y) <= 1:
                    attack_target = {"id": mob.id, "name": mob.name, "kind": mob.type}
                    break
        except Exception:
            pass
        d["attack_target"] = attack_target
        d["step_duration_ms"] = p.get_step_duration_ms(enemies_nearby=enemies_nearby)
        d["last_processed_seq"] = p.last_processed_seq
        return d

    def _serialize_player_stub(self, p) -> dict:
        enemies_nearby = False
        try:
            floor = self._get_or_create_floor(p.floor_id)
            enemies_nearby = self._has_enemies_nearby(floor, p, radius=3)
        except Exception:
            pass
        d = {
            "id": p.id,
            "type": p.type,
            "name": p.name,
            "pos": {"x": p.pos.x, "y": p.pos.y},
            "is_alive": p.is_alive,
            "is_downed": p.is_downed,
            "is_afk": p.is_afk,
            "hp": p.hp,
            "max_hp": p.max_hp,
            "shields": [s.model_dump() for s in p.shields],
            "invisible": p.invisible,
            "class_type": p.class_type,
            "level": p.level,
            "strength": p.strength,
            "faction": p.faction,
            "heal_left": p.heal_left,
            "step_duration_ms": p.get_step_duration_ms(enemies_nearby=enemies_nearby),
            "last_processed_seq": p.last_processed_seq,
            "equipped_wearable": {"tier": p.belongings.armor.tier}
            if p.belongings.armor is not None else None,
            "equipped_weapon": {"kind": p.belongings.weapon.kind}
            if p.belongings.weapon is not None else None,
        }
        return d

    def _serialize_floor_item(self, item, known=None) -> dict:
        d = item.model_dump()
        if known is None:
            known = self.identified_kinds
        d["value"] = item.value(identified=item.kind in known)
        # SPD's Heap.info(): show the item's flavour text + stats in examine.
        # Floor items have no owning player context, so pass None.
        d["description"] = item.description(None)
        lk = item_locale_key(item)
        if lk:
            d["locale_key"] = lk
        d["just_dropped"] = (
            item.dropped_at is not None
            and (time.time() - item.dropped_at) < DROP_ANIM_WINDOW
        )
        d.pop("dropped_at", None)
        return self._mask_item_dict(d, known)

    def _serialize_mob(self, mob) -> dict:
        d = mob.model_dump()
        lk = mob_locale_key(mob)
        if lk:
            d["locale_key"] = lk
        return d

    def get_state(self, player_id: Optional[str] = None):
        # Occupancy-based open doors and entity positions may have changed since
        # the last computation; rebuild FOV from a clean cache for this snapshot.
        self._invalidate_fov_cache()
        if player_id and player_id in self.players:
            player = self.players[player_id]
            # Per-viewer reveal: this snapshot masks undiscovered potion/scroll/ring
            # kinds according to the requesting player's personal discovery, not the
            # party-shared set (mechanics still use identified_kinds).
            known = player.discovered_kinds
            floor = self._get_or_create_floor(player.floor_id)
            floor_players = [p for p in self._players_on_floor(player.floor_id)]

            self_player = self._serialize_player(player, known)
            stubs = [self._serialize_player_stub(p) for p in floor_players]

            admin_traps = [
                {"x": x, "y": y, "trap_type": t.trap_type}
                for (x, y), t in floor.traps.items()
            ]
            admin_plants = [
                {"x": x, "y": y, "plant_type": p.get("plant_type", "sungrass")}
                for (x, y), p in floor.plants.items()
                if isinstance(p, dict)
            ]
            if player.is_admin:
                all_tiles = [(x, y) for y in range(floor.height) for x in range(floor.width)]
                return {
                    "depth": player.floor_id,
                    "self_player": self_player,
                    "players": stubs,
                    "mobs": [self._serialize_mob(m) for m in floor.mobs.values() if m.is_alive and not getattr(m, 'disguised', False)],
                    "items": [self._serialize_floor_item(i, known) for i in floor.items.values()
                              if i.pos and not (isinstance(i, LostBackpack) and i.owner_id and i.owner_id != player.id)],
                    "visible_tiles": all_tiles,
                    "open_doors": self._get_open_doors(floor),
                    "grid": floor.grid,
                    "width": floor.width,
                    "height": floor.height,
                    "traps": admin_traps,
                    "plants": admin_plants,
                    "custom_tiles": floor.custom_tiles,
                    "custom_walls": floor.custom_walls,
                    "torches": floor.torches,
                }

            visible_tiles = self.get_visible_tiles(
                player.pos, radius=self._view_distance(player), floor_id=player.floor_id,
                viewer_id=player.id)
            visible_set = set(visible_tiles)

            player_traps = [
                {"x": x, "y": y, "trap_type": t.trap_type}
                for (x, y), t in floor.traps.items()
                if (x, y) in visible_set and not t.hidden
            ]
            player_plants = [
                {"x": x, "y": y, "plant_type": p.get("plant_type", "sungrass")}
                for (x, y), p in floor.plants.items()
                if (x, y) in visible_set and isinstance(p, dict)
            ]

            # SPD MindVision: while active, every mob's 3x3 neighbourhood is
            # revealed regardless of walls/FOV.
            # EyeOfNewt trinket: permanent passive mind-vision radius.
            mind_vision_set = set()
            from app.engine.entities.trinkets import EyeOfNewt as _EyeOfNewt
            from app.engine.entities.trinkets import trinket_level
            eon_lvl = trinket_level(player, "eye_of_newt")
            if eon_lvl >= 0:
                mv_radius = _EyeOfNewt.mind_vision_radius(eon_lvl)
                for m in floor.mobs.values():
                    if not m.is_alive:
                        continue
                    for dx in range(-mv_radius, mv_radius + 1):
                        for dy in range(-mv_radius, mv_radius + 1):
                            mind_vision_set.add((m.pos.x + dx, m.pos.y + dy))
            if player.has_buff("mind_vision"):
                for m in floor.mobs.values():
                    if not m.is_alive:
                        continue
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            mind_vision_set.add((m.pos.x + dx, m.pos.y + dy))

            # SPD heap.seen: first-discovery latch, set once an item's cell
            # enters FOV.
            for i in floor.items.values():
                if i.pos and (i.pos.x, i.pos.y) in visible_set:
                    i.seen = True

            # Pre-serialize mobs and items for this floor if not already done in this tick
            floor_mobs = [m for m in floor.mobs.values() if m.is_alive and not getattr(m, 'disguised', False)]
            serialized_mobs = [
                (m, self._serialize_mob(m))
                for m in floor_mobs
            ]

            known_tuple = tuple(sorted(known)) if known else ()
            floor_items = [
                i for i in floor.items.values()
                if i.pos and not (isinstance(i, LostBackpack) and i.owner_id and i.owner_id != player.id)
            ]
            serialized_items = [
                (i, self._serialize_floor_item(i, known))
                for i in floor_items
            ]

            visible_mobs = [
                s_mob for mob_obj, s_mob in serialized_mobs
                if (mob_obj.pos.x, mob_obj.pos.y) in visible_set or (mob_obj.pos.x, mob_obj.pos.y) in mind_vision_set
            ]

            visible_items = [
                s_item for item_obj, s_item in serialized_items
                if (item_obj.pos.x, item_obj.pos.y) in visible_set
            ]

            return {
                "depth": player.floor_id,
                "self_player": self_player,
                "players": stubs,
                "mobs": visible_mobs,
                "items": visible_items,
                "visible_tiles": visible_tiles,
                "mapped_tiles": floor.mapped_tiles if floor.mapped else [],
                "open_doors": self._get_open_doors(floor),
                "grid": floor.grid,
                "width": floor.width,
                "height": floor.height,
                "traps": player_traps,
                "plants": player_plants,
                "custom_tiles": floor.custom_tiles,
                "custom_walls": floor.custom_walls,
                "torches": floor.torches,
            }

        floor = self._get_or_create_floor(self.depth)
        fallback_plants = [
            {"x": x, "y": y, "plant_type": p.get("plant_type", "sungrass")}
            for (x, y), p in floor.plants.items()
            if isinstance(p, dict)
        ]
        return {
            "depth": self.depth,
            "players": [self._serialize_player(p) for p in self._players_on_floor(self.depth)],
            "mobs": [self._serialize_mob(m) for m in floor.mobs.values() if m.is_alive],
            "items": [self._serialize_floor_item(i) for i in floor.items.values() if i.pos],
            "open_doors": self._get_open_doors(floor),
            "grid": floor.grid,
            "width": floor.width,
            "height": floor.height,
            "traps": [],
            "plants": fallback_plants,
            "custom_tiles": floor.custom_tiles,
            "custom_walls": floor.custom_walls,
            "torches": floor.torches,
        }
