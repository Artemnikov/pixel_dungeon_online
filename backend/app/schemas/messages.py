"""Incoming client -> server WebSocket messages.

A discriminated union (on `type`) validated at the socket boundary in main.py so
malformed input is rejected with a clear error instead of raising KeyError deep in
a handler. Mirrors the `ClientMessage` union in frontend/src/types/contract.ts and
the handler branches in main.py.

`extra="ignore"` keeps the layer forward/backward compatible: a client that sends
an extra field (or one we've since dropped) still validates on its known fields.
"""

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .common import Difficulty, Direction


class _ClientMessageBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Ping(_ClientMessageBase):
    type: Literal["PING"]


class Move(_ClientMessageBase):
    type: Literal["MOVE"]
    direction: Direction


class MoveIntent(_ClientMessageBase):
    type: Literal["MOVE_INTENT"]
    dx: int = 0
    dy: int = 0


class MoveStop(_ClientMessageBase):
    type: Literal["MOVE_STOP"]


class MoveTo(_ClientMessageBase):
    type: Literal["MOVE_TO"]
    x: int
    y: int


class ExecuteItemAction(_ClientMessageBase):
    type: Literal["EXECUTE_ITEM_ACTION"]
    item_id: str
    action: str
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class SetQuickslot(_ClientMessageBase):
    type: Literal["SET_QUICKSLOT"]
    index: int
    item_id: Optional[str] = None


class UseQuickslot(_ClientMessageBase):
    type: Literal["USE_QUICKSLOT"]
    index: int
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class EquipItem(_ClientMessageBase):
    type: Literal["EQUIP_ITEM"]
    item_id: str


class DropItem(_ClientMessageBase):
    type: Literal["DROP_ITEM"]
    item_id: str


class UseItem(_ClientMessageBase):
    type: Literal["USE_ITEM"]
    item_id: str


class RangedAttack(_ClientMessageBase):
    type: Literal["RANGED_ATTACK"]
    item_id: str
    target_x: int
    target_y: int


class ChangeDifficulty(_ClientMessageBase):
    type: Literal["CHANGE_DIFFICULTY"]
    difficulty: Difficulty


class Search(_ClientMessageBase):
    type: Literal["SEARCH"]


class Wait(_ClientMessageBase):
    type: Literal["WAIT"]


class ChooseSubclass(_ClientMessageBase):
    type: Literal["CHOOSE_SUBCLASS"]
    subclass: str


class UpgradeTalent(_ClientMessageBase):
    type: Literal["UPGRADE_TALENT"]
    talent: str


class ChooseArmorAbility(_ClientMessageBase):
    type: Literal["CHOOSE_ARMOR_ABILITY"]
    ability: str


class UseComboMove(_ClientMessageBase):
    type: Literal["USE_COMBO_MOVE"]
    move: str
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class UseArmorAbility(_ClientMessageBase):
    type: Literal["USE_ARMOR_ABILITY"]
    ability: str
    target_x: Optional[int] = None
    target_y: Optional[int] = None


class TriggerBerserk(_ClientMessageBase):
    type: Literal["TRIGGER_BERSERK"]


class PreparationStrike(_ClientMessageBase):
    type: Literal["PREPARATION_STRIKE"]
    target_x: int
    target_y: int


class MetamorphChoose(_ClientMessageBase):
    type: Literal["METAMORPH_CHOOSE"]
    talent: str


class MetamorphReplace(_ClientMessageBase):
    type: Literal["METAMORPH_REPLACE"]
    old_talent: str
    new_talent: str


class AdminTeleport(_ClientMessageBase):
    type: Literal["ADMIN_TELEPORT"]
    target_floor: int


class AdminLevelUp(_ClientMessageBase):
    type: Literal["ADMIN_LEVEL_UP"]


class AdminGiveItem(_ClientMessageBase):
    type: Literal["ADMIN_GIVE_ITEM"]
    item_kind: str


class NpcInteract(_ClientMessageBase):
    type: Literal["NPC_INTERACT"]
    npc_id: str


class ShopBuy(_ClientMessageBase):
    type: Literal["SHOP_BUY"]
    npc_id: str
    item_id: str


class ShopSell(_ClientMessageBase):
    type: Literal["SHOP_SELL"]
    item_id: str


class ImpClaimReward(_ClientMessageBase):
    type: Literal["IMP_CLAIM_REWARD"]
    npc_id: str


class GhostClaimReward(_ClientMessageBase):
    type: Literal["GHOST_CLAIM_REWARD"]
    npc_id: str
    choice: Literal["weapon", "armor"]


class ChooseImbueWand(_ClientMessageBase):
    type: Literal["CHOOSE_IMBUE_WAND"]
    staff_id: str
    wand_id: str


class EquipGhostItem(_ClientMessageBase):
    type: Literal["EQUIP_GHOST_ITEM"]
    rose_id: str
    slot: Literal["weapon", "armor"]
    item_id: Optional[str] = None  # None = unequip


class SelectScrollTarget(_ClientMessageBase):
    type: Literal["SELECT_SCROLL_TARGET"]
    scroll_id: str
    item_id: str


class SelectStoneTarget(_ClientMessageBase):
    type: Literal["SELECT_STONE_TARGET"]
    stone_id: str
    item_id: str


class StoneIntuitionChooseItem(_ClientMessageBase):
    type: Literal["STONE_INTUITION_CHOOSE_ITEM"]
    stone_id: str
    item_id: str


class StoneIntuitionGuess(_ClientMessageBase):
    type: Literal["STONE_INTUITION_GUESS"]
    stone_id: str
    item_id: str
    guessed_kind: str


class StoneAugmentChoose(_ClientMessageBase):
    type: Literal["STONE_AUGMENT_CHOOSE"]
    stone_id: str
    item_id: str
    augment_type: str


class ChooseEnchant(_ClientMessageBase):
    type: Literal["CHOOSE_ENCHANT"]
    target_id: str
    choice_index: int


class Resume(_ClientMessageBase):
    type: Literal["RESUME"]


class PickupFloor(_ClientMessageBase):
    type: Literal["PICKUP_FLOOR"]


class Attack(_ClientMessageBase):
    type: Literal["ATTACK"]
    target_id: str


class ConfirmChasmFall(_ClientMessageBase):
    type: Literal["CONFIRM_CHASM_FALL"]
    x: int
    y: int


class AlchemyPreview(_ClientMessageBase):
    type: Literal["ALCHEMY_PREVIEW"]
    ingredient_ids: List[str]


class AlchemyBrew(_ClientMessageBase):
    type: Literal["ALCHEMY_BREW"]
    ingredient_ids: List[str]
    recipe_index: int


class AlchemyEnergize(_ClientMessageBase):
    type: Literal["ALCHEMY_ENERGIZE"]
    item_id: str
    all_items: bool = False


class AlchemyTrinketChoose(_ClientMessageBase):
    type: Literal["ALCHEMY_TRINKET_CHOOSE"]
    catalyst_id: str
    kind: str


class ToolkitEnergize(_ClientMessageBase):
    type: Literal["TOOLKIT_ENERGIZE"]
    toolkit_id: str
    levels: int = 1


ClientMessage = Annotated[
    Union[
        Ping,
        Move,
        MoveIntent,
        MoveStop,
        MoveTo,
        ExecuteItemAction,
        SetQuickslot,
        UseQuickslot,
        EquipItem,
        DropItem,
        UseItem,
        RangedAttack,
        ChangeDifficulty,
        Search,
        Wait,
        ChooseSubclass,
        UpgradeTalent,
        ChooseArmorAbility,
        UseComboMove,
        UseArmorAbility,
        TriggerBerserk,
        PreparationStrike,
        MetamorphChoose,
        MetamorphReplace,
        AdminTeleport,
        AdminLevelUp,
        AdminGiveItem,
        NpcInteract,
        ShopBuy,
        ShopSell,
        ImpClaimReward,
        GhostClaimReward,
        SelectScrollTarget,
        SelectStoneTarget,
        StoneIntuitionChooseItem,
        StoneIntuitionGuess,
        StoneAugmentChoose,
        ChooseImbueWand,
        EquipGhostItem,
        ChooseEnchant,
        Resume,
        PickupFloor,
        Attack,
        ConfirmChasmFall,
        AlchemyPreview,
        AlchemyBrew,
        AlchemyEnergize,
        AlchemyTrinketChoose,
        ToolkitEnergize,
    ],
    Field(discriminator="type"),
]

CLIENT_MESSAGE_ADAPTER: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)
