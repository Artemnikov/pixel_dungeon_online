import logging
from app.api.dispatcher import dispatcher
from app.engine.manager import GameInstance
from app.schemas import messages as msg

logger = logging.getLogger(__name__)


@dispatcher.register(msg.Move)
def handle_move(game: GameInstance, player_id: str, message: msg.Move):
    player = game.players.get(player_id)
    if player is None or player.is_downed or not player.is_alive:
        return
    player.movement.stop()
    # Pace the legacy one-shot MOVE through the same server-side step cooldown
    # the tick uses for queued steps -- otherwise a flood of MOVE messages
    # moves the hero once per message, faster than the client can animate.
    # (The live client sends paced MOVE_STEP instead; this guards compat paths.)
    if not player.movement.is_ready_for_step():
        return
    dx, dy = message.direction.delta
    floor = game._get_or_create_floor(player.floor_id)
    pre_x, pre_y = player.pos.x, player.pos.y
    game.move_entity(player_id, dx, dy)
    if (player.pos.x, player.pos.y) != (pre_x, pre_y):
        step_duration = player.get_step_duration(
            enemies_nearby=game._has_enemies_nearby(floor, player, radius=3)
        )
        player.movement.on_step_executed(None, step_duration, dx, dy)
    else:
        player.movement.on_step_failed(None)


@dispatcher.register(msg.MoveIntent)
def handle_move_intent(game: GameInstance, player_id: str, message: msg.MoveIntent):
    # Held keyboard direction. The update tick paces the actual stepping
    # (see GameInstance.update_tick), so movement speed is server-authoritative.
    game.set_move_intent(player_id, message.dx, message.dy)


@dispatcher.register(msg.MoveStep)
def handle_move_step(game: GameInstance, player_id: str, message: msg.MoveStep):
    game.queue_move_step(player_id, message.seq, message.dx, message.dy, replaces=message.replaces)


@dispatcher.register(msg.MoveStop)
def handle_move_stop(game: GameInstance, player_id: str, message: msg.MoveStop):
    game.stop_move(player_id, message.last_seq)


@dispatcher.register(msg.Resume)
def handle_resume(game: GameInstance, player_id: str, message: msg.Resume):
    if player_id in game.players:
        player = game.players[player_id]
        if player.path_queue:
            player.last_auto_move_time = 0.0
            player.reset_move_cooldown()


@dispatcher.register(msg.PickupFloor)
def handle_pickup_floor(game: GameInstance, player_id: str, message: msg.PickupFloor):
    game.pickup_floor_items(player_id)


@dispatcher.register(msg.PathSteps)
def handle_path_steps(game: GameInstance, player_id: str, message: msg.PathSteps):
    if player_id in game.players:
        # Path steps are 8-dir unit deltas; drop anything else so a crafted
        # path can't warp the player (the auto-walker feeds these to
        # move_entity).
        steps = [
            (int(s[0]), int(s[1]))
            for s in message.steps
            if max(abs(int(s[0])), abs(int(s[1]))) <= 1
        ]
        game.players[player_id].movement.set_path(steps)


@dispatcher.register(msg.ExecuteItemAction)
def handle_execute_item_action(
    game: GameInstance, player_id: str, message: msg.ExecuteItemAction
):
    # Generic SPD-style dispatch: {item_id, action, target_x?, target_y?}.
    game.execute_item_action(
        player_id,
        message.item_id,
        message.action,
        message.target_x,
        message.target_y,
    )


@dispatcher.register(msg.SetQuickslot)
def handle_set_quickslot(game: GameInstance, player_id: str, message: msg.SetQuickslot):
    game.set_quickslot(player_id, message.index, message.item_id)


@dispatcher.register(msg.UseQuickslot)
def handle_use_quickslot(game: GameInstance, player_id: str, message: msg.UseQuickslot):
    game.use_quickslot(
        player_id,
        message.index,
        message.target_x,
        message.target_y,
    )


# --- legacy handlers (thin wrappers over the generic dispatch) ---


@dispatcher.register(msg.EquipItem)
def handle_equip_item(game: GameInstance, player_id: str, message: msg.EquipItem):
    game.execute_item_action(player_id, message.item_id, "EQUIP")


@dispatcher.register(msg.DropItem)
def handle_drop_item(game: GameInstance, player_id: str, message: msg.DropItem):
    game.execute_item_action(player_id, message.item_id, "DROP")


@dispatcher.register(msg.UseItem)
def handle_use_item(game: GameInstance, player_id: str, message: msg.UseItem):
    game.use_item(player_id, message.item_id)


@dispatcher.register(msg.SelectScrollTarget)
def handle_select_scroll_target(
    game: GameInstance, player_id: str, message: msg.SelectScrollTarget
):
    game.select_scroll_target(player_id, message.scroll_id, message.item_id)


@dispatcher.register(msg.ChooseImbueWand)
def handle_choose_imbue_wand(
    game: GameInstance, player_id: str, message: msg.ChooseImbueWand
):
    game.imbue_wand(player_id, message.staff_id, message.wand_id)


@dispatcher.register(msg.EquipGhostItem)
def handle_equip_ghost_item(
    game: GameInstance, player_id: str, message: msg.EquipGhostItem
):
    game.equip_ghost_item(
        player_id,
        message.rose_id,
        message.slot,
        message.item_id,
    )


@dispatcher.register(msg.ChangeDifficulty)
def handle_change_difficulty(
    game: GameInstance, player_id: str, message: msg.ChangeDifficulty
):
    game.change_difficulty(message.difficulty)


@dispatcher.register(msg.Attack)
def handle_attack(game: GameInstance, player_id: str, message: msg.Attack):
    game.attack_mob(player_id, message.target_id)


@dispatcher.register(msg.ConfirmChasmFall)
def handle_confirm_chasm_fall(
    game: GameInstance, player_id: str, message: msg.ConfirmChasmFall
):
    game.confirm_chasm_fall(player_id, message.x, message.y)


@dispatcher.register(msg.AlchemyPreview)
def handle_alchemy_preview(
    game: GameInstance, player_id: str, message: msg.AlchemyPreview
):
    game.alchemy_preview(player_id, message.ingredient_ids)


@dispatcher.register(msg.AlchemyBrew)
def handle_alchemy_brew(game: GameInstance, player_id: str, message: msg.AlchemyBrew):
    game.alchemy_brew(player_id, message.ingredient_ids, message.recipe_index)


@dispatcher.register(msg.AlchemyEnergize)
def handle_alchemy_energize(
    game: GameInstance, player_id: str, message: msg.AlchemyEnergize
):
    game.alchemy_energize(player_id, message.item_id, message.all_items)


@dispatcher.register(msg.AlchemyTrinketChoose)
def handle_alchemy_trinket_choose(
    game: GameInstance, player_id: str, message: msg.AlchemyTrinketChoose
):
    game.alchemy_trinket_choose(player_id, message.catalyst_id, message.kind)


@dispatcher.register(msg.ToolkitEnergize)
def handle_toolkit_energize(
    game: GameInstance, player_id: str, message: msg.ToolkitEnergize
):
    game.toolkit_energize(player_id, message.toolkit_id, message.levels)


@dispatcher.register(msg.AnkhChoice)
def handle_ankh_choice(game: GameInstance, player_id: str, message: msg.AnkhChoice):
    game.ankh_choice(player_id, message.kept_item_ids)


@dispatcher.register(msg.Resurrect)
def handle_resurrect(game: GameInstance, player_id: str, message: msg.Resurrect):
    game.resurrect_player(player_id)


@dispatcher.register(msg.RangedAttack)
def handle_ranged_attack(
    game: GameInstance, player_id: str, message: msg.RangedAttack
):
    game.perform_ranged_attack(
        player_id,
        message.item_id,
        message.target_x,
        message.target_y,
        message.target_entity_id,
    )


@dispatcher.register(msg.Search)
def handle_search(game: GameInstance, player_id: str, message: msg.Search):
    game.search(player_id)


@dispatcher.register(msg.Wait)
def handle_wait(game: GameInstance, player_id: str, message: msg.Wait):
    pass


@dispatcher.register(msg.SendChat)
def handle_send_chat(game: GameInstance, player_id: str, message: msg.SendChat):
    game.handle_chat(player_id, message.channel, message.text)


@dispatcher.register(msg.ChooseSubclass)
def handle_choose_subclass(
    game: GameInstance, player_id: str, message: msg.ChooseSubclass
):
    game.choose_subclass(player_id, message.subclass)


@dispatcher.register(msg.UpgradeTalent)
def handle_upgrade_talent(
    game: GameInstance, player_id: str, message: msg.UpgradeTalent
):
    if not game.upgrade_talent(player_id, message.talent):
        logger.warning("Upgrade talent failed for %s: %s", player_id, message.talent)


@dispatcher.register(msg.ChooseArmorAbility)
def handle_choose_armor_ability(
    game: GameInstance, player_id: str, message: msg.ChooseArmorAbility
):
    game.choose_armor_ability(player_id, message.ability)


@dispatcher.register(msg.UseComboMove)
def handle_use_combo_move(
    game: GameInstance, player_id: str, message: msg.UseComboMove
):
    game.use_combo_move(player_id, message.move, message.target_x, message.target_y)


@dispatcher.register(msg.UseArmorAbility)
def handle_use_armor_ability(
    game: GameInstance, player_id: str, message: msg.UseArmorAbility
):
    game.use_armor_ability(
        player_id, message.ability, message.target_x, message.target_y
    )


@dispatcher.register(msg.TriggerBerserk)
def handle_trigger_berserk(
    game: GameInstance, player_id: str, message: msg.TriggerBerserk
):
    game.trigger_berserk(player_id)


@dispatcher.register(msg.PreparationStrike)
def handle_preparation_strike(
    game: GameInstance, player_id: str, message: msg.PreparationStrike
):
    game.preparation_strike(player_id, message.target_x, message.target_y)


@dispatcher.register(msg.MetamorphChoose)
def handle_metamorph_choose(
    game: GameInstance, player_id: str, message: msg.MetamorphChoose
):
    game.metamorph_choose(player_id, message.talent)


@dispatcher.register(msg.MetamorphReplace)
def handle_metamorph_replace(
    game: GameInstance, player_id: str, message: msg.MetamorphReplace
):
    game.metamorph_replace(player_id, message.old_talent, message.new_talent)


@dispatcher.register(msg.AdminTeleport)
def handle_admin_teleport(
    game: GameInstance, player_id: str, message: msg.AdminTeleport
):
    game.admin_teleport(player_id, message.target_floor)


@dispatcher.register(msg.AdminLevelUp)
def handle_admin_level_up(
    game: GameInstance, player_id: str, message: msg.AdminLevelUp
):
    game.admin_level_up(player_id)


@dispatcher.register(msg.AdminGiveItem)
def handle_admin_give_item(
    game: GameInstance, player_id: str, message: msg.AdminGiveItem
):
    game.admin_give_item(
        player_id,
        message.item_kind,
        level=message.level,
        cursed=message.cursed,
        enchant=message.enchant,
    )


@dispatcher.register(msg.NpcInteract)
def handle_npc_interact(
    game: GameInstance, player_id: str, message: msg.NpcInteract
):
    game.npc_interact(player_id, message.npc_id)


@dispatcher.register(msg.ShopBuy)
def handle_shop_buy(game: GameInstance, player_id: str, message: msg.ShopBuy):
    game.shop_buy(player_id, message.npc_id, message.item_id)


@dispatcher.register(msg.ShopSell)
def handle_shop_sell(game: GameInstance, player_id: str, message: msg.ShopSell):
    game.shop_sell(player_id, message.item_id)


@dispatcher.register(msg.ImpClaimReward)
def handle_imp_claim_reward(
    game: GameInstance, player_id: str, message: msg.ImpClaimReward
):
    game.imp_claim_reward(player_id, message.npc_id)


@dispatcher.register(msg.GhostClaimReward)
def handle_ghost_claim_reward(
    game: GameInstance, player_id: str, message: msg.GhostClaimReward
):
    game.ghost_claim_reward(player_id, message.npc_id, message.choice)


@dispatcher.register(msg.WandmakerClaimReward)
def handle_wandmaker_claim_reward(
    game: GameInstance, player_id: str, message: msg.WandmakerClaimReward
):
    game.wandmaker_claim_reward(player_id, message.npc_id, message.choice)


@dispatcher.register(msg.SelectStoneTarget)
def handle_select_stone_target(
    game: GameInstance, player_id: str, message: msg.SelectStoneTarget
):
    game.select_stone_target(player_id, message.stone_id, message.item_id)


@dispatcher.register(msg.StoneIntuitionChooseItem)
def handle_stone_intuition_choose_item(
    game: GameInstance, player_id: str, message: msg.StoneIntuitionChooseItem
):
    game.stone_intuition_pick(player_id, message.stone_id, message.item_id)


@dispatcher.register(msg.StoneIntuitionGuess)
def handle_stone_intuition_guess(
    game: GameInstance, player_id: str, message: msg.StoneIntuitionGuess
):
    game.stone_intuition_guess(
        player_id, message.stone_id, message.item_id, message.guessed_kind
    )


@dispatcher.register(msg.StoneAugmentChoose)
def handle_stone_augment_choose(
    game: GameInstance, player_id: str, message: msg.StoneAugmentChoose
):
    game.stone_augment_choose(
        player_id, message.stone_id, message.item_id, message.augment_type
    )


@dispatcher.register(msg.ChooseEnchant)
def handle_choose_enchant(
    game: GameInstance, player_id: str, message: msg.ChooseEnchant
):
    game.choose_enchant(player_id, message.target_id, message.choice_index)
