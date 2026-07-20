import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import os
import uuid
from pydantic import ValidationError
from app.api.connection_manager import manager
from app.api.routes import router
from app.engine.entities.base import Position
from app.schemas import (
    CLIENT_MESSAGE_ADAPTER,
    PongMessage,
)
from app.schemas import messages as msg

logger = logging.getLogger(__name__)

app = FastAPI(title="Online Pixel Dungeon API")

# Allow cross-origin requests from the frontend (different port in development,
# different domain in production).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str, class_type: str = "warrior", difficulty: str = "normal", name: str = None, admin_secret: str = "", session: str = None, seed: str = "", challenges: str = "", room_password: str = ""):
    session_id = session or str(uuid.uuid4())

    rejection = manager.check_room_join(game_id, session_id, room_password)
    if rejection is not None:
        # Must accept() before close() so the browser's WebSocket actually
        # receives our code/reason -- closing pre-accept only surfaces to the
        # client as a bare HTTP 403 handshake failure (verified empirically),
        # which loses the reason and would look like a generic network error.
        await websocket.accept()
        close_code = 4001 if rejection == "wrong password" else 4002
        await websocket.close(code=close_code, reason=rejection)
        return

    player_id, is_new = await manager.connect(game_id, websocket, session_id, seed=seed)

    game = manager.game_instances[game_id]
    if is_new:
        if game.player_count == 0: # First player sets difficulty
            game.change_difficulty(difficulty)
            game.set_challenges(challenges)

        is_admin = bool(admin_secret and admin_secret == os.environ.get("ADMIN_SECRET", "admin"))
        player_name = "admin" if is_admin else (name.strip()[:20] if name and name.strip() else f"Player_{player_id[:4]}")
        game.add_player(player_id, player_name, class_type, is_admin=is_admin)
        game.add_event("MESSAGE", {"text": f"{player_name} joined the game."})
    await manager.send_player_init(game_id, websocket, player_id, is_new=is_new)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = CLIENT_MESSAGE_ADAPTER.validate_json(data)
            except ValidationError as e:
                # Log and ignore malformed input; a bad frame must never kill the
                # connection or the game loop.
                logger.warning("Invalid WS message from %s: %s", player_id, e)
                continue

            if isinstance(message, msg.Ping):
                await websocket.send_json(PongMessage().model_dump())
                continue

            if isinstance(message, msg.Move):
                dx, dy = message.direction.delta
                if player_id in game.players:
                    # A single tap-step overrides any held keyboard intent / travel path.
                    game.players[player_id].path_queue = []
                    game.players[player_id].move_intent = None
                game.move_entity(player_id, dx, dy)

            elif isinstance(message, msg.MoveIntent):
                # Held keyboard direction. The update tick paces the actual stepping
                # (see GameInstance.update_tick), so movement speed is server-authoritative.
                game.set_move_intent(player_id, message.dx, message.dy)

            elif isinstance(message, msg.MoveStop):
                game.set_move_intent(player_id, 0, 0)

            elif isinstance(message, msg.Resume):
                if player_id in game.players:
                    player = game.players[player_id]
                    if player.path_queue:
                        player.last_auto_move_time = 0.0

            elif isinstance(message, msg.PickupFloor):
                game.pickup_floor_items(player_id)

            elif isinstance(message, msg.MoveTo):
                if player_id in game.players:
                    player = game.players[player_id]
                    player.move_intent = None
                    path = game._bfs_full_path(player.pos, Position(x=message.x, y=message.y), player.floor_id)
                    player.path_queue = list(path)
                    player.last_auto_move_time = 0.0

            elif isinstance(message, msg.ExecuteItemAction):
                # Generic SPD-style dispatch: {item_id, action, target_x?, target_y?}.
                game.execute_item_action(
                    player_id, message.item_id, message.action,
                    message.target_x, message.target_y,
                )

            elif isinstance(message, msg.SetQuickslot):
                game.set_quickslot(player_id, message.index, message.item_id)

            elif isinstance(message, msg.UseQuickslot):
                game.use_quickslot(
                    player_id, message.index,
                    message.target_x, message.target_y,
                )

            # --- legacy handlers (thin wrappers over the generic dispatch) ---
            elif isinstance(message, msg.EquipItem):
                game.execute_item_action(player_id, message.item_id, "EQUIP")

            elif isinstance(message, msg.DropItem):
                game.execute_item_action(player_id, message.item_id, "DROP")

            elif isinstance(message, msg.UseItem):
                game.use_item(player_id, message.item_id)

            elif isinstance(message, msg.SelectScrollTarget):
                game.select_scroll_target(player_id, message.scroll_id, message.item_id)

            elif isinstance(message, msg.ChooseImbueWand):
                game.imbue_wand(player_id, message.staff_id, message.wand_id)

            elif isinstance(message, msg.EquipGhostItem):
                game.equip_ghost_item(
                    player_id, message.rose_id, message.slot, message.item_id,
                )

            elif isinstance(message, msg.ChangeDifficulty):
                game.change_difficulty(message.difficulty)

            elif isinstance(message, msg.Attack):
                game.attack_mob(player_id, message.target_id)

            elif isinstance(message, msg.ConfirmChasmFall):
                game.confirm_chasm_fall(player_id, message.x, message.y)

            elif isinstance(message, msg.AlchemyPreview):
                game.alchemy_preview(player_id, message.ingredient_ids)

            elif isinstance(message, msg.AlchemyBrew):
                game.alchemy_brew(player_id, message.ingredient_ids, message.recipe_index)

            elif isinstance(message, msg.AlchemyEnergize):
                game.alchemy_energize(player_id, message.item_id, message.all_items)

            elif isinstance(message, msg.AlchemyTrinketChoose):
                game.alchemy_trinket_choose(player_id, message.catalyst_id, message.kind)

            elif isinstance(message, msg.ToolkitEnergize):
                game.toolkit_energize(player_id, message.toolkit_id, message.levels)

            elif isinstance(message, msg.Resurrect):
                game.resurrect_player(player_id)

            elif isinstance(message, msg.RangedAttack):
                game.perform_ranged_attack(
                    player_id, message.item_id, message.target_x, message.target_y,
                    message.target_entity_id,
                )

            elif isinstance(message, msg.Search):
                game.search(player_id)

            elif isinstance(message, msg.Wait):
                pass

            elif isinstance(message, msg.ChooseSubclass):
                game.choose_subclass(player_id, message.subclass)

            elif isinstance(message, msg.UpgradeTalent):
                if not game.upgrade_talent(player_id, message.talent):
                    print(f"Upgrade talent failed for {player_id}: {message.talent}")

            elif isinstance(message, msg.ChooseArmorAbility):
                game.choose_armor_ability(player_id, message.ability)

            elif isinstance(message, msg.UseComboMove):
                game.use_combo_move(player_id, message.move, message.target_x, message.target_y)

            elif isinstance(message, msg.UseArmorAbility):
                game.use_armor_ability(player_id, message.ability, message.target_x, message.target_y)

            elif isinstance(message, msg.TriggerBerserk):
                game.trigger_berserk(player_id)

            elif isinstance(message, msg.PreparationStrike):
                game.preparation_strike(player_id, message.target_x, message.target_y)

            elif isinstance(message, msg.MetamorphChoose):
                game.metamorph_choose(player_id, message.talent)

            elif isinstance(message, msg.MetamorphReplace):
                game.metamorph_replace(player_id, message.old_talent, message.new_talent)

            elif isinstance(message, msg.AdminTeleport):
                game.admin_teleport(player_id, message.target_floor)

            elif isinstance(message, msg.AdminLevelUp):
                game.admin_level_up(player_id)

            elif isinstance(message, msg.AdminGiveItem):
                game.admin_give_item(player_id, message.item_kind)

            elif isinstance(message, msg.NpcInteract):
                game.npc_interact(player_id, message.npc_id)

            elif isinstance(message, msg.ShopBuy):
                game.shop_buy(player_id, message.npc_id, message.item_id)

            elif isinstance(message, msg.ShopSell):
                game.shop_sell(player_id, message.item_id)

            elif isinstance(message, msg.ImpClaimReward):
                game.imp_claim_reward(player_id, message.npc_id)

            elif isinstance(message, msg.GhostClaimReward):
                game.ghost_claim_reward(player_id, message.npc_id, message.choice)

            elif isinstance(message, msg.WandmakerClaimReward):
                game.wandmaker_claim_reward(player_id, message.npc_id, message.choice)

            elif isinstance(message, msg.SelectStoneTarget):
                game.select_stone_target(player_id, message.stone_id, message.item_id)

            elif isinstance(message, msg.StoneIntuitionChooseItem):
                game.stone_intuition_pick(player_id, message.stone_id, message.item_id)

            elif isinstance(message, msg.StoneIntuitionGuess):
                game.stone_intuition_guess(player_id, message.stone_id, message.item_id, message.guessed_kind)

            elif isinstance(message, msg.StoneAugmentChoose):
                game.stone_augment_choose(player_id, message.stone_id, message.item_id, message.augment_type)

            elif isinstance(message, msg.ChooseEnchant):
                game.choose_enchant(player_id, message.target_id, message.choice_index)

    except WebSocketDisconnect:
        # Emit a user-left event before disconnecting so other players see it.
        if player_id in game.players:
            game.add_event("MESSAGE", {"text": f"{game.players[player_id].name} left the game."})
        # Keep the hero alive for the reconnect grace window (see reaper); the
        # player is only removed once the deadline elapses without a reconnect.
        manager.disconnect(game_id, websocket)

async def global_game_loop():
    while True:
        for game_id in list(manager.game_instances.keys()):
            try:
                manager.reap_expired_players(game_id)
                await manager.broadcast_state(game_id)
                manager.cleanup_if_empty(game_id)
            except Exception:
                # One game's bug must never freeze broadcast_state for every
                # other game on the server -- this loop is a single shared
                # task with no other supervision, so an unhandled exception
                # here previously killed ticking/broadcasting globally until
                # a manual server restart.
                logger.exception("global_game_loop: error ticking game_id=%s", game_id)
        await asyncio.sleep(0.05)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(global_game_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
