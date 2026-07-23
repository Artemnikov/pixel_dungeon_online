"""Item-action dispatch for GameInstance.

Routes item actions (equip/drop/drink/read/throw/zap...) through the
``item_actions`` handler table, plus quickslot wiring and party-shared
identification of potion/scroll kinds.
"""

from typing import Optional

from app.engine.entities import item_actions, scroll_actions
from app.engine.entities.base import Position
from app.engine.entities.runestones import Runestone
from app.engine.entities.items_wands import Wand
from app.engine.entities.player import QuickSlotEntry
from app.engine.entities.runestone_actions import (
    apply_stone_augment, apply_stone_intuition_guess, apply_stone_intuition_pick,
    apply_stone_target,
)
from app.engine.entities.scroll_predicates import PREDICATE


class ItemsMixin:
    # --- generic item-action dispatch -------------------------------------
    def execute_item_action(self, player_id: str, item_id: str, action: str,
                            target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        item = player.belongings.get_item(item_id)
        if item is None:
            return
        if action not in item.actions(player):
            return
        handler = item_actions.ITEM_ACTION_DISPATCH.get(action)
        if handler is not None:
            handler(self, player, item, target_x, target_y)

    def set_quickslot(self, player_id: str, index: int, item_id: Optional[str]):
        player = self.players.get(player_id)
        if not player:
            return
        if item_id is None:
            if 0 <= index < len(player.quickslot.slots):
                player.quickslot.slots[index] = QuickSlotEntry()
            return
        item = player.belongings.get_item(item_id)
        if item is not None:
            player.quickslot.set_slot(index, item)

    def use_quickslot(self, player_id: str, index: int,
                      target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        if not player or not (0 <= index < len(player.quickslot.slots)):
            return
        entry = player.quickslot.slots[index]
        if not entry.item_id:
            return
        item = player.belongings.get_item(entry.item_id)
        if item is None:
            return
        action = item.default_action()
        if action:
            self.execute_item_action(player_id, item.id, action, target_x, target_y)

    def use_item(self, player_id: str, item_id: str,
                 target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        if not player:
            return
        item = player.belongings.get_item(item_id)
        if item is None:
            return
        action = item.default_action()
        if action:
            self.execute_item_action(player_id, item_id, action, target_x, target_y)

    def select_scroll_target(self, player_id: str, scroll_id: str, item_id: str):
        player = self.players.get(player_id)
        if not player:
            return
        scroll = player.belongings.get_item(scroll_id)
        if scroll is None:
            # Scroll may have been pre-consumed (unidentified path). Use pending state.
            kind = getattr(player, "_pending_scroll_kind", None)
            scroll_id_ = getattr(player, "_pending_scroll_id", None)
            if kind is None or scroll_id_ != scroll_id:
                return
            scroll = type("_PendingScroll", (), {"id": scroll_id, "kind": kind})()
        predicate = PREDICATE.get(scroll.kind)
        if predicate is None:
            return
        target = player.belongings.get_item(item_id)
        if target is None or not predicate(target, self):
            return
        scroll_actions.apply_scroll_target(self, player, scroll, target)
        player._pending_scroll_kind = None
        player._pending_scroll_id = None

    def select_stone_target(self, player_id: str, stone_id: str, item_id: str):
        player = self.players.get(player_id)
        if not player:
            return
        stone = player.belongings.get_item(stone_id)
        if stone is None:
            return
        if stone.kind == "magical_infusion":
            self.use_magical_infusion(player_id, item_id, infusion_id=stone_id)
            return
        if stone.kind == "arcane_stylus":
            target = player.belongings.get_item(item_id)
            if target is None:
                return
            item_actions.apply_stylus_target(self, player, stone, target)
            return
        if not isinstance(stone, Runestone):
            return
        target = player.belongings.get_item(item_id)
        if target is None:
            return
        apply_stone_target(self, player, stone, target)

    def stone_intuition_pick(self, player_id: str, stone_id: str, item_id: str):
        player = self.players.get(player_id)
        if not player:
            return
        apply_stone_intuition_pick(self, player, stone_id, item_id)

    def stone_intuition_guess(self, player_id: str, stone_id: str, item_id: str,
                               guessed_kind: str):
        player = self.players.get(player_id)
        if not player:
            return
        apply_stone_intuition_guess(self, player, stone_id, item_id, guessed_kind)

    def stone_augment_choose(self, player_id: str, stone_id: str, item_id: str,
                              augment_type: str):
        player = self.players.get(player_id)
        if not player:
            return
        apply_stone_augment(self, player, stone_id, item_id, augment_type)

    def imbue_wand(self, player_id: str, staff_id: str, wand_id: str):
        """Handle imbue wand choice from IMBUE_WAND_CHOICE_AVAILABLE dialog."""
        player = self.players.get(player_id)
        if not player:
            return
        staff = player.belongings.get_item(staff_id)
        if staff is None or staff.kind != "staff":
            return
        wand = player.belongings.get_item(wand_id)
        if wand is None or not isinstance(wand, Wand):
            return
        player.belongings.backpack.detach(wand.id)
        displaced = staff.imbue_wand(wand, player)
        if displaced is not None:
            floor = self._get_or_create_floor(player.floor_id)
            displaced.pos = Position(x=player.pos.x, y=player.pos.y)
            floor.items[displaced.id] = displaced
        # Notify client of the change
        player.quickslot.clear_item(wand_id)
        self.add_event("IMBUE_WAND_DONE", {
            "player": player.id,
            "staff_id": staff_id,
            "old_wand_id": wand_id,
        }, floor_id=player.floor_id, source_player_id=player.id)

    def equip_ghost_item(self, player_id: str, rose_id: str, slot: str,
                         item_id: Optional[str] = None):
        from app.engine.entities.items_artifacts import DriedRose
        from app.engine.entities.items_equip import Armor, MeleeWeapon
        player = self.players.get(player_id)
        if not player or not player.is_alive or player.is_downed:
            return
        rose = player.belongings.get_item(rose_id)
        if not isinstance(rose, DriedRose) or not rose.has_ghost():
            return

        if item_id is None:
            if slot == "weapon" and rose.weapon:
                player.belongings.backpack.collect(rose.weapon)
                rose.weapon = None
            elif slot == "armor" and rose.armor:
                player.belongings.backpack.collect(rose.armor)
                rose.armor = None
            return

        item = player.belongings.get_item(item_id)
        if item is None:
            return

        if slot == "weapon":
            if not isinstance(item, MeleeWeapon):
                return
            if item.cursed:
                return
            if item.strength_requirement > rose.ghost_strength():
                return
            player.belongings.backpack.detach(item.id)
            if rose.weapon:
                player.belongings.backpack.collect(rose.weapon)
            rose.weapon = item
        elif slot == "armor":
            if not isinstance(item, Armor):
                return
            if item.cursed:
                return
            if item.strength_requirement > rose.ghost_strength():
                return
            player.belongings.backpack.detach(item.id)
            if rose.armor:
                player.belongings.backpack.collect(rose.armor)
            rose.armor = item

    def choose_enchant(self, player_id: str, target_id: str, choice_index: int):
        """Handle exotic Scroll of Enchantment choice."""
        player = self.players.get(player_id)
        if not player:
            return
        from app.engine.entities.scroll_actions import choose_enchant_apply
        choose_enchant_apply(self, player, choice_index)

    def use_magical_infusion(self, player_id: str, item_id: str, infusion_id: Optional[str] = None):
        """MagicalInfusion: upgrade a weapon/armor by 1 level."""
        player = self.players.get(player_id)
        if not player:
            return
        item = player.belongings.get_item(item_id)
        if item is None:
            return
        if infusion_id:
            infusion = player.belongings.get_item(infusion_id)
        else:
            infusion = next((it for it in player.belongings.all_items() if it.kind == "magical_infusion"), None)
        if infusion is None:
            return
        if not getattr(item, "is_upgradable", lambda: True)():
            return
        item.level += 1
        item.level_known = True
        player.remove_buff("degrade")
        # Consume one infusion
        detached = player.belongings.backpack.detach(infusion.id)
        if detached is not None and player.belongings.get_item(infusion.id) is None:
            player.quickslot.convert_to_placeholder(detached)
        self.add_event("MESSAGE", {"text": f"Your {item.name} glows with magical energy and upgrades!"},
                       floor_id=player.floor_id, player_id=player.id)
        self.add_event("PLAY_SOUND", {"sound": "LEVELUP"}, floor_id=player.floor_id)

    def identify_kind(self, item):
        # Reveal a potion/scroll kind for the whole party (co-op shared knowledge).
        self.identified_kinds.add(item.kind)
        item.level_known = True
        item.cursed_known = True

    def pickup_floor_items(self, player_id: str) -> None:
        """Collect every eligible item on the player's current tile (PICKUP_FLOOR).
        Gold/energy are absorbed directly; dewdrops and armed bombs get their
        own pickup handling; everything else goes to the backpack if there's
        room."""
        player = self.players.get(player_id)
        if not player:
            return
        floor = self._get_or_create_floor(player.floor_id)
        items_to_pickup = [
            i_id for i_id, i in floor.items.items()
            if i.pos and i.pos.x == player.pos.x and i.pos.y == player.pos.y
            and i.type != "grave" and not getattr(i, 'for_sale', False)
        ]
        from app.engine.entities.items_consumable import Gold, Dewdrop, EnergyCrystal, LostBackpack
        from app.engine.entities.items_bombs import Bomb
        for i_id in items_to_pickup:
            item = floor.items[i_id]
            if isinstance(item, Gold):
                player.gold += item.quantity
                del floor.items[i_id]
                self.add_event("PICKUP_GOLD", {"player": player.id, "amount": item.quantity}, floor_id=player.floor_id)
            elif isinstance(item, EnergyCrystal):
                player.energy += item.quantity
                del floor.items[i_id]
                self.add_event("PICKUP_ENERGY", {"player": player.id, "amount": item.quantity}, floor_id=player.floor_id)
            elif isinstance(item, LostBackpack):
                # Only the owner can pick up their lost backpack.
                if item.owner_id == player.id:
                    for stored in item.stored_items:
                        player.add_to_inventory(stored)
                    del floor.items[i_id]
                    self.add_event("PICKUP", {
                        "player": player.id, "item": "Lost Backpack",
                        "x": player.pos.x, "y": player.pos.y,
                        "item_type": "lost_backpack",
                    }, floor_id=player.floor_id)
            elif isinstance(item, Dewdrop):
                self._pickup_dewdrop(player, floor, player.floor_id, i_id, item)
            elif isinstance(item, Bomb) and item.fuse_ticks is not None and \
                    self.handle_bomb_pickup(player, floor, player.floor_id, i_id, item):
                pass
            elif item.name == "Guide Page":
                # Guide Page floor items unlock a random missing page instead
                # of going into the backpack (SPD Guidebook.doPickUp).
                page_id = self._next_missing_guide_page(player)
                if page_id and player.discover_guide_page(page_id):
                    del floor.items[i_id]
                    self.add_event("GUIDE_PAGE_DISCOVERED",
                                   {"player": player.id, "page": page_id},
                                   player_id=player.id)
            elif player.add_to_inventory(item):
                del floor.items[i_id]
                self.add_event("PICKUP", {"player": player.id, "item": item.name, "x": player.pos.x, "y": player.pos.y, "item_type": item.type}, floor_id=player.floor_id)

    # All Adventurer's Guide page IDs in discovery order (SPD Document
    # ADVENTURERS_GUIDE pageNames). Used by Guide Page floor item pickup.
    _ALL_GUIDE_PAGES = [
        "Intro", "Examining", "Surprise_Attacks", "Identifying",
        "Food", "Alchemy", "Dieing", "Searching", "Strength",
        "Upgrades", "Looting", "Levelling", "Positioning", "Magic",
    ]

    def _next_missing_guide_page(self, player) -> Optional[str]:
        """Return the first undiscovered guide page, or None if all found
        (SPD Document.ADVENTURERS_GUIDE missingPages logic)."""
        for page_id in self._ALL_GUIDE_PAGES:
            if not player.has_guide_page(page_id):
                return page_id
        return None
