"""Item-action dispatch for GameInstance.

Routes item actions (equip/drop/drink/read/throw/zap...) through the
``item_actions`` handler table, plus quickslot wiring and party-shared
identification of potion/scroll kinds.
"""

from typing import Optional

from app.engine.entities import item_actions, scroll_actions
from app.engine.entities.scroll_predicates import PREDICATE


class ItemsMixin:
    # --- generic item-action dispatch -------------------------------------
    def execute_item_action(self, player_id: str, item_id: str, action: str,
                            target_x: Optional[int] = None, target_y: Optional[int] = None):
        player = self.players.get(player_id)
        print(f"[execute_item_action] player={player_id}, item={item_id}, action={action}, tx={target_x}, ty={target_y}")
        if not player or not player.is_alive or player.is_downed:
            print(f"[execute_item_action] BAIL: player invalid (alive={player.is_alive if player else 'N/A'}, downed={player.is_downed if player else 'N/A'})")
            return
        item = player.belongings.get_item(item_id)
        if item is None:
            print(f"[execute_item_action] BAIL: item not found (id={item_id})")
            return
        print(f"[execute_item_action] found item: {item.name} ({type(item).__name__}), actions={item.actions(player)}")
        if action not in item.actions(player):
            print(f"[execute_item_action] BAIL: action {action} not in item actions {item.actions(player)}")
            return
        handler = item_actions.ITEM_ACTION_DISPATCH.get(action)
        print(f"[execute_item_action] dispatching to handler={handler}")
        if handler is not None:
            handler(self, player, item, target_x, target_y)

    def set_quickslot(self, player_id: str, index: int, item_id: str):
        player = self.players.get(player_id)
        if not player:
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

    def identify_kind(self, item):
        # Reveal a potion/scroll kind for the whole party (co-op shared knowledge).
        self.identified_kinds.add(item.kind)
        item.level_known = True
        item.cursed_known = True
