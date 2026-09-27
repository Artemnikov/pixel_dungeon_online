"""Costed turn actions for turn-based rooms.

This is the turn-mode counterpart of `app/api/ws_handlers.py`: it maps an
incoming client message to the game call that performs it plus the SPD time
cost of performing it, which is what the scheduler charges the actor.

Costs live in `app/engine/game/constants.py` alongside their Java references.
Three rules decide how a message is treated here:

* An action costs time, and therefore ends the actor's turn.
* A menu-ish message (talent pick, quickslot assignment, chat, shop UI, admin)
  costs nothing and does not end the turn -- SPD lets you rearrange the
  inventory between actions without spending a turn.
* Movement plumbing (held-key intent, auto-walk path steps) is dropped
  entirely: a turn room reads no continuous input, because the scheduler
  already decides when a player may act. A turn is spent per action message.
  `PATH_STEPS` is the one exception -- it is not plumbing but the far-tap
  *request*, and the hero's own following turns drain it, one tile each
  (see `turn/walk.py`).

`build_turn_action` returns `None` for anything it won't turn into an action --
unknown types, the movement plumbing above, and moves that would do nothing.
A `None` return consumes the message and spends no time, so the player stays on
turn and can try again.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, get_args

from app.engine.dungeon.constants import TileType
from app.engine.entities.items.union import Chest
from app.engine.game.constants import (
    TIME_TO_ABILITY,
    TIME_TO_ATTACK,
    TIME_TO_DRINK,
    TIME_TO_DROP,
    TIME_TO_EAT,
    TIME_TO_EQUIP,
    TIME_TO_INSCRIBE,
    TIME_TO_LIGHT,
    TIME_TO_MOVE_BASE,
    TIME_TO_PICK_UP,
    TIME_TO_READ,
    TIME_TO_REST,
    TIME_TO_SEARCH,
    TIME_TO_THROW,
    TIME_TO_UNLOCK,
    TIME_TO_WAIT,
    TIME_TO_ZAP,
)
from app.engine.turn.walk import refresh_visible_enemies, sanitize_path_steps
from app.schemas import messages as msg

# Tiles whose bump-to-enter resolves as an interaction rather than a step, so
# walking into one is a real turn. Mirrors the tile branches in
# MovementMixin.move_entity; a plain wall is not in this set.
_INTERACTABLE_TILES = frozenset(
    {
        TileType.DOOR,
        TileType.OPEN_DOOR,
        TileType.HERO_LKD_DR,
        TileType.LOCKED_DOOR,
        TileType.CRYSTAL_DOOR,
        TileType.LOCKED_EXIT,
        TileType.SECRET_DOOR,
        TileType.WELL,
        TileType.CHASM,
    }
)

# Builder signature: (game, player, message) -> TurnAction | None.
Builder = Callable[[Any, Any, Any], Optional["TurnAction"]]
Runner = Callable[[Any, Any, Any], None]


def _msg_type(model) -> str:
    """The wire discriminator of a client message model.

    Pydantic v2 has no class-level attribute for a `Literal` field and leaves
    its default undefined, so read the single allowed value out of the
    annotation rather than hardcoding the strings a second time.
    """
    return get_args(model.model_fields["type"].annotation)[0]


@dataclass(frozen=True)
class TurnAction:
    """One costed player action, ready to run and charge.

    The originating `message` is kept rather than re-read at execution time:
    menu calls and abilities need its fields, and they may run long after the
    scheduler handed the turn back (or, for free calls, never queue at all).
    """

    cost: float
    run: Runner
    label: str = "action"
    message: Any = None

    def execute(self, game, player) -> float:
        self.run(game, player, self.message)
        return self.cost


# --- cost helpers --------------------------------------------------------


def _move_cost(game, player) -> float:
    """SPD Char.move(): `spend(1 / speed())` -- actors/Char.java:298.

    A speed-1.3 mob therefore pays 0.77 per step and acts more often than a
    speed-1.0 hero, exactly as in SPD.
    """
    floor = game._get_or_create_floor(player.floor_id)
    nearby = game._has_enemies_nearby(floor, player, radius=3)
    return TIME_TO_MOVE_BASE / player.get_movement_speed(enemies_nearby=nearby)


_ITEM_ACTION_COSTS: Dict[str, float] = {
    "READ": TIME_TO_READ,
    "DRINK": TIME_TO_DRINK,
    "EAT": TIME_TO_EAT,
    "THROW": TIME_TO_THROW,
    "ZAP": TIME_TO_ZAP,
    "SHOOT": TIME_TO_ABILITY,
    "UNLOCK": TIME_TO_UNLOCK,
    "OPEN": TIME_TO_UNLOCK,
    "INSCRIBE": TIME_TO_INSCRIBE,
    "LIGHT": TIME_TO_LIGHT,
    "BREW": TIME_TO_ABILITY,
    "ENERGIZE": TIME_TO_ABILITY,
    "DIRECT": TIME_TO_ABILITY,
    "PRICK": TIME_TO_ABILITY,
    "EQUIP": TIME_TO_EQUIP,
    "UNEQUIP": TIME_TO_EQUIP,
    "DROP": TIME_TO_DROP,
}

_TARGETED_STONES = frozenset(
    {
        "magical_infusion",
        "stone_of_detect_magic",
        "stone_of_enchantment",
        "stone_of_intuition",
        "stone_of_augmentation",
        "arcane_stylus",
    }
)


def _item_action_cost(action: str) -> float:
    return _ITEM_ACTION_COSTS.get(action, TIME_TO_ABILITY)


def _attack_cost(game, player) -> float:
    return player.get_attack_delay()


def _equip_cost(player, item) -> float:
    if item is not None and (getattr(item, "type", "") == "weapon" or getattr(item, "slot_type", None) == "weapon"):
        if hasattr(player, "can_swift_equip") and player.can_swift_equip():
            return 0.0
    return TIME_TO_EQUIP


def _is_targeted_scroll_action(item, action: str) -> bool:
    if action != "READ" or item is None:
        return False
    from app.engine.entities.scroll_predicates import PREDICATE
    return getattr(item, "kind", "") in PREDICATE


def _is_targeted_stone_action(item, action: str) -> bool:
    if action != "USE" or item is None:
        return False
    return getattr(item, "kind", "") in _TARGETED_STONES


def _resolve_item_action_cost(player, item, action_name: str) -> float:
    """Resolve turn cost for executing an item action."""
    if action_name == "EQUIP":
        return _equip_cost(player, item)
    if action_name == "DROP":
        return TIME_TO_DROP
    if _is_targeted_scroll_action(item, action_name) or _is_targeted_stone_action(item, action_name):
        return 0.0
    return _item_action_cost(action_name)


def _action(cost: float, run: Runner, label: str) -> Builder:
    """An action that spends `cost` and ends the turn."""
    return lambda game, player, message: TurnAction(cost, run, label, message)


def _free(run: Runner, label: str) -> Builder:
    """A zero-cost call: the hero may do it between actions without a turn."""
    return lambda game, player, message: TurnAction(0.0, run, label, message)


def _noop(game, player, message) -> None:
    return None


# --- builders ------------------------------------------------------------


def _bump_is_actionable(game, player, dx: int, dy: int) -> bool:
    """Reject a step that would visibly do nothing.

    SPD never offers an illegal move, so bumping a bare wall is not a turn.
    Everything else -- an occupied cell (bump attack), an interactable tile, a
    chest, or a passable one -- is left to move_entity, which owns the rules.
    """
    floor = game._get_or_create_floor(player.floor_id)
    nx, ny = player.pos.x + dx, player.pos.y + dy
    if not (0 <= nx < floor.width and 0 <= ny < floor.height):
        return False
    if game._entity_at(floor, player.floor_id, nx, ny, player.id, active_players_only=True):
        return True
    if floor.grid[ny][nx] in _INTERACTABLE_TILES:
        return True
    if any(isinstance(item, Chest) for item in game._items_at(floor, nx, ny)):
        return True
    if not floor.flags:
        return True
    return bool(floor.flags.passable[ny][nx] or floor.flags.avoid[ny][nx])


def _build_move(game, player, message):
    dx, dy = message.direction.delta
    if not _bump_is_actionable(game, player, dx, dy):
        return None
    return TurnAction(
        _move_cost(game, player),
        lambda g, p, _m: g.step_player_move(p.id, dx, dy),
        "MOVE",
        message,
    )


def _build_attack(game, player, message):
    target_id = message.target_id
    return TurnAction(
        _attack_cost(game, player),
        lambda g, p, _m: g.attack_mob(p.id, target_id),
        "ATTACK",
        message,
    )


def _build_use_weapon_ability(game, player, message):
    weapon = (
        player.belongings.secondary_weapon
        if message.use_secondary
        else player.belongings.weapon
    )
    cost = (
        _attack_cost(game, player)
        if weapon is not None and getattr(weapon, "type", "") != "shield"
        else TIME_TO_ABILITY
    )
    return TurnAction(
        cost,
        lambda g, p, m: g.use_weapon_ability(
            p.id,
            target_x=m.target_x,
            target_y=m.target_y,
            use_secondary=m.use_secondary,
        ),
        "ABILITY",
        message,
    )


def _build_equip(game, player, message):
    item = player.belongings.get_item(message.item_id)
    cost = _equip_cost(player, item)
    return TurnAction(
        cost,
        lambda g, p, m: g.execute_item_action(p.id, m.item_id, "EQUIP"),
        "EQUIP",
        message,
    )


def _build_drop(game, player, message):
    return TurnAction(
        TIME_TO_DROP,
        lambda g, p, m: g.execute_item_action(p.id, m.item_id, "DROP"),
        "DROP",
        message,
    )


def _build_use_item(game, player, message):
    item = player.belongings.get_item(message.item_id)
    if item is None:
        return None
    default_act = item.default_action()
    if not default_act:
        return None
    cost = _resolve_item_action_cost(player, item, default_act)

    return TurnAction(
        cost,
        lambda g, p, m: g.use_item(p.id, m.item_id),
        "USE",
        message,
    )


def _build_execute_item_action(game, player, message):
    item = player.belongings.get_item(message.item_id)
    action_name = message.action
    cost = _resolve_item_action_cost(player, item, action_name)

    return TurnAction(
        cost,
        lambda gg, pp, _m: gg.execute_item_action(
            pp.id, message.item_id, action_name, message.target_x, message.target_y
        ),
        action_name,
        message,
    )


def _build_path_steps(game, player, message):
    """A far tap: walk the client's path, one tile per turn.

    Costs one move, not the length of the path, because the scheduler only
    charges the turn it runs: the first tile is walked here and the rest are
    the hero's own following turns (`TurnBasedGameInstance._player_walk_turn`).
    An empty path means the client found no route, which is not a turn.
    """
    steps = sanitize_path_steps(message.steps)
    if not steps:
        return None
    return TurnAction(
        _move_cost(game, player),
        lambda g, p, _m: _start_turn_walk(g, p, steps),
        "PATH_STEPS",
        message,
    )


def _start_turn_walk(game, player, steps) -> None:
    from app.engine.turn.actors import PlayerActor

    player.movement.set_path(steps)
    actor = game._player_actors.get(player.id)
    if not isinstance(actor, PlayerActor):
        # No actor to drain the queue: this is a one-shot tap, so walk the first
        # step and drop the rest rather than stranding a path nobody will read.
        if steps:
            game.step_player_move(player.id, steps[0][0], steps[0][1])
        player.movement.path_queue.clear()
        return
    actor.walk_floor_id = player.floor_id
    # Seed the interrupt baseline with what the hero can already see, so only an
    # enemy that arrives *during* the trip stops it.
    refresh_visible_enemies(game, actor)
    game._player_walk_turn(actor)


def _build_use_quickslot(game, player, message):
    index = message.index
    cost = TIME_TO_ABILITY
    if 0 <= index < len(player.quickslot.slots):
        item = player.belongings.get_item(player.quickslot.slots[index].item_id)
        if item is not None:
            default_act = item.default_action()
            if default_act:
                cost = _resolve_item_action_cost(player, item, default_act)
    return TurnAction(
        cost,
        lambda g, p, _m: g.use_quickslot(p.id, index, message.target_x, message.target_y),
        "QUICKSLOT",
        message,
    )


# Paid actions: each one ends the actor's turn.
_BUILDERS: Dict[str, Builder] = {
    _msg_type(msg.Move): _build_move,
    _msg_type(msg.Attack): _build_attack,
    _msg_type(msg.PathSteps): _build_path_steps,
    _msg_type(msg.Wait): _action(TIME_TO_WAIT, lambda g, p, m: g.wait(p.id), "WAIT"),
    _msg_type(msg.Search): _action(
        TIME_TO_SEARCH, lambda g, p, m: g.search(p.id), "SEARCH"
    ),
    _msg_type(msg.PickupFloor): _action(
        TIME_TO_PICK_UP, lambda g, p, m: g.pickup_floor_items(p.id), "PICKUP"
    ),
    _msg_type(msg.EquipItem): _build_equip,
    _msg_type(msg.DropItem): _build_drop,
    _msg_type(msg.UseItem): _build_use_item,
    _msg_type(msg.ExecuteItemAction): _build_execute_item_action,
    _msg_type(msg.UseQuickslot): _build_use_quickslot,
    _msg_type(msg.UseWeaponAbility): _build_use_weapon_ability,
    _msg_type(msg.UseMonkAbility): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.use_monk_ability(
            p.id, ability_id=m.ability, target_x=m.target_x, target_y=m.target_y
        ),
        "ABILITY",
    ),
    _msg_type(msg.CastClericSpell): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.cast_spell(p, m.spell, m.target_x, m.target_y),
        "SPELL",
    ),
    _msg_type(msg.UseArmorAbility): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.use_armor_ability(p.id, m.ability, m.target_x, m.target_y),
        "ABILITY",
    ),
    _msg_type(msg.UseComboMove): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.use_combo_move(p.id, m.move, m.target_x, m.target_y),
        "COMBO",
    ),
    _msg_type(msg.TriggerBerserk): _action(
        TIME_TO_ABILITY, lambda g, p, m: g.trigger_berserk(p.id), "BERSERK"
    ),
    _msg_type(msg.PreparationStrike): lambda g, p, m: TurnAction(
        _attack_cost(g, p),
        lambda gg, pp, mm: gg.preparation_strike(pp.id, mm.target_x, mm.target_y),
        "STRIKE",
        m,
    ),
    _msg_type(msg.DuelistFinisher): lambda g, p, m: TurnAction(
        _attack_cost(g, p),
        lambda gg, pp, mm: gg.action_duelist_finisher(pp, mm.target_x, mm.target_y),
        "FINISHER",
        m,
    ),
    _msg_type(msg.AlchemyBrew): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.alchemy_brew(p.id, m.ingredient_ids, m.recipe_index),
        "BREW",
    ),
    _msg_type(msg.RangedAttack): _action(
        TIME_TO_ZAP,
        lambda g, p, m: g.perform_ranged_attack(
            p.id, m.item_id, m.target_x, m.target_y, m.target_entity_id
        ),
        "ZAP",
    ),
    _msg_type(msg.SelectScrollTarget): _action(
        TIME_TO_READ,
        lambda g, p, m: g.select_scroll_target(p.id, m.scroll_id, m.item_id),
        "READ",
    ),
    _msg_type(msg.SelectStoneTarget): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.select_stone_target(p.id, m.stone_id, m.item_id),
        "USE",
    ),
    _msg_type(msg.StoneIntuitionGuess): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.stone_intuition_guess(
            p.id, m.stone_id, m.item_id, m.guessed_kind
        ),
        "USE",
    ),
    _msg_type(msg.StoneAugmentChoose): _action(
        TIME_TO_ABILITY,
        lambda g, p, m: g.stone_augment_choose(
            p.id, m.stone_id, m.item_id, m.augment_type
        ),
        "USE",
    ),
}

# Menus and metadata: free, and never end a turn.
_FREE_MENUS: Dict[str, tuple] = {
    _msg_type(msg.SetQuickslot): (
        lambda g, p, m: g.set_quickslot(p.id, m.index, m.item_id),
        "QUICKSLOT",
    ),
    _msg_type(msg.SetClericQuickSpell): (
        lambda g, p, m: g.set_cleric_quick_spell(p, m.spell),
        "SPELL_SLOT",
    ),
    _msg_type(msg.UpgradeTalent): (lambda g, p, m: g.upgrade_talent(p.id, m.talent), "TALENT"),
    _msg_type(msg.ChooseSubclass): (
        lambda g, p, m: g.choose_subclass(p.id, m.subclass),
        "SUBCLASS",
    ),
    _msg_type(msg.ChooseArmorAbility): (
        lambda g, p, m: g.choose_armor_ability(p.id, m.ability),
        "ARMOR",
    ),
    _msg_type(msg.SwapWeapons): (lambda g, p, m: g.swap_weapons(p.id), "SWAP"),
    _msg_type(msg.MetamorphChoose): (
        lambda g, p, m: g.metamorph_choose(p.id, m.talent),
        "METAMORPH",
    ),
    _msg_type(msg.MetamorphReplace): (
        lambda g, p, m: g.metamorph_replace(p.id, m.old_talent, m.new_talent),
        "METAMORPH",
    ),
    _msg_type(msg.ChooseImbueWand): (
        lambda g, p, m: g.imbue_wand(p.id, m.staff_id, m.wand_id),
        "IMBUE",
    ),
    _msg_type(msg.EquipGhostItem): (
        lambda g, p, m: g.equip_ghost_item(p.id, m.rose_id, m.slot, m.item_id),
        "GHOST",
    ),
    _msg_type(msg.ChooseEnchant): (
        lambda g, p, m: g.choose_enchant(p.id, m.target_id, m.choice_index),
        "ENCHANT",
    ),
    _msg_type(msg.AlchemyPreview): (
        lambda g, p, m: g.alchemy_preview(p.id, m.ingredient_ids),
        "ALCHEMY",
    ),
    _msg_type(msg.AlchemyEnergize): (
        lambda g, p, m: g.alchemy_energize(p.id, m.item_id, m.all_items),
        "ALCHEMY",
    ),
    _msg_type(msg.AlchemyTrinketChoose): (
        lambda g, p, m: g.alchemy_trinket_choose(p.id, m.catalyst_id, m.kind),
        "ALCHEMY",
    ),
    _msg_type(msg.ToolkitEnergize): (
        lambda g, p, m: g.toolkit_energize(p.id, m.toolkit_id, m.levels),
        "ALCHEMY",
    ),
    _msg_type(msg.AnkhChoice): (
        lambda g, p, m: g.ankh_choice(p.id, m.kept_item_ids),
        "ANKH",
    ),
    _msg_type(msg.Resurrect): (lambda g, p, m: g.resurrect_player(p.id), "RESURRECT"),
    _msg_type(msg.ConfirmChasmFall): (
        lambda g, p, m: g.confirm_chasm_fall(p.id, m.x, m.y),
        "CHASM",
    ),
    _msg_type(msg.NpcInteract): (lambda g, p, m: g.npc_interact(p.id, m.npc_id), "NPC"),
    _msg_type(msg.ShopBuy): (lambda g, p, m: g.shop_buy(p.id, m.npc_id, m.item_id), "SHOP"),
    _msg_type(msg.ShopSell): (lambda g, p, m: g.shop_sell(p.id, m.item_id), "SHOP"),
    _msg_type(msg.ImpClaimReward): (lambda g, p, m: g.imp_claim_reward(p.id, m.npc_id), "REWARD"),
    _msg_type(msg.GhostClaimReward): (
        lambda g, p, m: g.ghost_claim_reward(p.id, m.npc_id, m.choice),
        "REWARD",
    ),
    _msg_type(msg.WandmakerClaimReward): (
        lambda g, p, m: g.wandmaker_claim_reward(p.id, m.npc_id, m.choice),
        "REWARD",
    ),
    _msg_type(msg.ChangeDifficulty): (
        lambda g, p, m: g.change_difficulty(m.difficulty),
        "DIFFICULTY",
    ),
    _msg_type(msg.StoneIntuitionChooseItem): (
        lambda g, p, m: g.stone_intuition_pick(p.id, m.stone_id, m.item_id),
        "USE",
    ),
    _msg_type(msg.SendChat): (lambda g, p, m: g.handle_chat(p.id, m.channel, m.text), "CHAT"),
    _msg_type(msg.AdminTeleport): (lambda g, p, m: g.admin_teleport(p.id, m.target_floor), "ADMIN"),
    _msg_type(msg.AdminLevelUp): (lambda g, p, m: g.admin_level_up(p.id), "ADMIN"),
    _msg_type(msg.AdminGiveItem): (
        lambda g, p, m: g.admin_give_item(
            p.id, m.item_kind, level=m.level, cursed=m.cursed, enchant=m.enchant
        ),
        "ADMIN",
    ),
    _msg_type(msg.AdminSetHp): (
        lambda g, p, m: g.admin_set_hp(p.id, hp=m.hp, hp_pct=m.hp_pct),
        "ADMIN",
    ),
    _msg_type(msg.Resume): (_noop, "RESUME"),
    _msg_type(msg.Ping): (_noop, "PING"),
}

for _type_name, (_run, _label) in _FREE_MENUS.items():
    _BUILDERS[_type_name] = _free(_run, _label)


def build_turn_action(game, player, message) -> Optional[TurnAction]:
    """Costed action for `message`, or None to consume it for free."""
    if player is None or not player.is_active:
        return None
    builder = _BUILDERS.get(message.type)
    if builder is None:
        return None
    return builder(game, player, message)
