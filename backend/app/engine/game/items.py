"""Item-action dispatch for GameInstance.

Routes item actions (equip/drop/drink/read/throw/zap...) through the
``item_actions`` handler table, plus quickslot wiring and party-shared
identification of potion/scroll kinds.
"""

from typing import Optional

from app.engine.entities import item_actions, scroll_actions
from app.engine.entities.base import Position, QuickSlotEntry, Wand
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
            return
        predicate = PREDICATE.get(scroll.kind)
        if predicate is None:
            return
        target = player.belongings.get_item(item_id)
        if target is None or not predicate(target, self):
            return
        scroll_actions.apply_scroll_target(self, player, scroll, target)

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
        from app.engine.entities.base import Armor, DriedRose, MeleeWeapon
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

    def identify_kind(self, item):
        # Reveal a potion/scroll kind for the whole party (co-op shared knowledge).
        self.identified_kinds.add(item.kind)
        item.level_known = True
        item.cursed_known = True
