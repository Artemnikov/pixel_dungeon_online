"""Typed payloads for the per-tick game events placed in STATE_UPDATE.events.

Mirrors the `GameEvent` union in frontend/src/types/contract.ts and the
add_event(...) call sites across engine/game/*.py and engine/entities/item_actions.py.

These models do NOT change the wire format: `add_event` still appends plain dicts.
They exist as a single source of truth and to power an opt-in development check
(see EventsMixin.add_event, gated on the PXD_VALIDATE_EVENTS env var) that validates
each event's `data` against the model below and warns on drift — catching payload
mistakes while building new features without touching production behaviour.
"""

from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict


class _EventData(BaseModel):
    # Events may carry extra context fields; only flag missing/mistyped known ones.
    model_config = ConfigDict(extra="allow")


class AttackData(_EventData):
    source: str
    target: str
    damage: int
    surprise: bool
    crit: bool
    grim_proc: bool


class MissData(_EventData):
    source: str
    target: str
    defense_verb: str


class DamageData(_EventData):
    target: str
    amount: int
    crit: Optional[bool] = None
    grim_proc: Optional[bool] = None
    bleed: Optional[bool] = None
    projectile: Optional[str] = None
    splash_count: Optional[int] = None
    source_x: Optional[int] = None
    source_y: Optional[int] = None
    beam_type: Optional[str] = None


class DeathData(_EventData):
    target: str


class MoveData(_EventData):
    entity: str
    x: int
    y: int


class RangedAttackData(_EventData):
    source: str
    x: int
    y: int
    target_x: int
    target_y: int
    projectile: str
    crit: bool
    grim_proc: bool
    beam_type: Optional[str] = None
    sound: Optional[str] = None
    is_wand: Optional[bool] = None
    # Present for thrown inventory items (not wands); a serialized item dict.
    item: Optional[dict] = None


class PlaySoundData(_EventData):
    sound: str
    rate: Optional[float] = None
    x: Optional[int] = None
    y: Optional[int] = None


class SearchData(_EventData):
    player: str
    x: int
    y: int
    cells: List[Tuple[int, int]]
    revealed_tiles: int


class HealData(_EventData):
    target: str
    amount: int
    x: int
    y: int


class TrapTriggeredData(_EventData):
    player: str
    trap: str
    damage: int


class DrinkData(_EventData):
    player: str
    type: str


class ReadData(_EventData):
    player: str
    item: str


class _Tile(_EventData):
    x: int
    y: int
    tile: int


class MapPatchData(_EventData):
    tiles: List[_Tile]


class PickupData(_EventData):
    player: str
    item: str


class DropData(_EventData):
    player: str
    item: str
    item_name: str


class GoldDropData(_EventData):
    x: int
    y: int


class CollectDewData(_EventData):
    player: str
    item: str


class PickupGoldData(_EventData):
    player: str
    amount: int


class PickupEnergyData(_EventData):
    player: str
    amount: int


class PickupKeyData(_EventData):
    player: str
    key_id: str
    name: str


class ToastData(_EventData):
    text: str


class AlchemyPreviewEntry(BaseModel):
    recipe_index: int
    cost: int
    affordable: bool
    output_kind: Optional[str] = None
    output_name: str
    output_quantity: int
    known: bool


class AlchemyPreviewResultData(_EventData):
    player: str
    ingredient_ids: List[str]
    recipes: List[AlchemyPreviewEntry]
    available_energy: int


class AlchemyBrewedData(_EventData):
    player: str
    item_id: str
    item_kind: str
    item_name: str
    quantity: int
    cost: int
    energy: int


class AlchemyEnergizedData(_EventData):
    player: str
    amount: int
    energy: int


class TrinketChoiceData(_EventData):
    player: str
    catalyst_id: str
    kinds: List[str]


class ToolkitBrewData(_EventData):
    player: str
    item_id: str
    charges: int


class ToolkitEnergizePromptData(_EventData):
    player: str
    toolkit_id: str
    max_levels: int


class ToolkitEnergizedData(_EventData):
    player: str
    toolkit_id: str
    levels: int
    level: int


class ShopOpenData(_EventData):
    player: str
    npc: str
    stock: List[dict]
    gold: int


class ShopBuyData(_EventData):
    player: str
    item: str
    price: int


class ShopSellData(_EventData):
    player: str
    item: str
    price: int


class StairsDownData(_EventData):
    player: str
    first_visit: bool


class StairsUpData(_EventData):
    player: str


class ReviveData(_EventData):
    target: str
    source: str


class UnlockData(_EventData):
    player: str
    x: int
    y: int


class LevelUpData(_EventData):
    player: str
    level: int = 0
    tier_unlocked: Optional[int] = None
    talent_points: Optional[dict] = None
    can_choose_subclass: bool = False
    can_choose_armor_ability: bool = False


class SubclassChosenData(_EventData):
    player: str
    subclass: str


class TalentUpgradedData(_EventData):
    player: str
    talent: str
    level: int


class SubclassChoiceAvailableData(_EventData):
    player: str
    options: List[str]


class ArmorAbilityChoiceAvailableData(_EventData):
    player: str
    options: List[str]


class ComboUpdateData(_EventData):
    player: str
    count: int


class ComboMoveUnlockedData(_EventData):
    player: str
    move: str


class BerserkActivatedData(_EventData):
    player: str


class RageChangedData(_EventData):
    player: str
    power: float


class AffixSealData(_EventData):
    player: str
    armor: str


class MetamorphOpenData(_EventData):
    player: str


class MetamorphOptionsData(_EventData):
    player: str
    old_talent: str
    options: List[dict]
    """[{id, name, tier, subclass, max_pts, description}] eligible replacements."""


class TalentMetamorphData(_EventData):
    player: str
    old_talent: str
    new_talent: str


class BossSlainData(_EventData):
    mob: str
    depth: int
    badge_image: int


class TenguBadgeQualifiedData(_EventData):
    pass  # no required payload


class GooBadgeQualifiedData(_EventData):
    pass  # no required payload


class ChasmPromptData(_EventData):
    x: int
    y: int


class MessageData(_EventData):
    text: str
    color: Optional[str] = None


class ImpDialogueData(_EventData):
    player: str
    npc: str
    text: str
    can_claim: bool
    tokens: Optional[int] = None


class ImpRewardData(_EventData):
    player: str
    npc: str
    item: str


class GhostDialogueData(_EventData):
    player: str
    npc: str
    text: str
    can_claim: bool
    weapon: Optional[dict] = None
    armor: Optional[dict] = None


class GhostRewardData(_EventData):
    player: str
    npc: str
    item: str


class TeleportData(_EventData):
    player: str
    x: int
    y: int


class MirrorImageData(_EventData):
    player: str
    clones: List[str]


class GhostSummonData(_EventData):
    player: str
    ghost_id: str
    x: int
    y: int


class GhostDirectData(_EventData):
    player: str
    ghost_id: str
    x: int
    y: int


class GhostGearOpenData(_EventData):
    player: str
    rose_id: str
    ghost_id: str
    ghost_hp: int
    ghost_max_hp: int
    weapon: Optional[dict] = None
    armor: Optional[dict] = None


class ScrollSelectTargetData(_EventData):
    player: str
    scroll_id: str
    scroll_kind: str
    candidates: List[str]


class ShockingProcData(_EventData):
    attacker_id: str
    target_id: str
    defender_x: int
    defender_y: int
    chain_targets: List[dict]


class BlobUpdateData(_EventData):
    id: str
    type: str
    cells: List[Tuple[int, int, int]]


class BlobDepletedData(_EventData):
    id: str


class StateEffectData(_EventData):
    entity_id: str
    effect: str
    x: int
    y: int


class FireImbueActivatedData(_EventData):
    player: str
    x: int
    y: int


class InfernoActivatedData(_EventData):
    x: int
    y: int


class SacrificialFireData(_EventData):
    x: int
    y: int


class LeafBurstData(_EventData):
    x: int
    y: int


class SpellSpriteData(_EventData):
    x: int
    y: int
    index: int


class EyeChargeData(_EventData):
    mob: str
    target_x: int
    target_y: int


class EyeDeathRayData(_EventData):
    mob: str
    source_x: int
    source_y: int
    target_x: int
    target_y: int


# event "type" -> payload model. Used by the opt-in dev validation hook.
EVENT_MODELS = {
    "ATTACK": AttackData,
    "MISS": MissData,
    "DAMAGE": DamageData,
    "DEATH": DeathData,
    "MOVE": MoveData,
    "RANGED_ATTACK": RangedAttackData,
    "PLAY_SOUND": PlaySoundData,
    "SEARCH": SearchData,
    "HEAL": HealData,
    "TRAP_TRIGGERED": TrapTriggeredData,
    "DRINK": DrinkData,
    "READ": ReadData,
    "MAP_PATCH": MapPatchData,
    "PICKUP": PickupData,
    "DROP": DropData,
    "COLLECT_DEW": CollectDewData,
    "PICKUP_GOLD": PickupGoldData,
    "PICKUP_ENERGY": PickupEnergyData,
    "GOLD_DROP": GoldDropData,
    "PICKUP_KEY": PickupKeyData,
    "SHOP_OPEN": ShopOpenData,
    "SHOP_BUY": ShopBuyData,
    "SHOP_SELL": ShopSellData,
    "STAIRS_DOWN": StairsDownData,
    "STAIRS_UP": StairsUpData,
    "REVIVE": ReviveData,
    "UNLOCK": UnlockData,
    "LEVEL_UP": LevelUpData,
    "SUBCLASS_CHOSEN": SubclassChosenData,
    "TALENT_UPGRADED": TalentUpgradedData,
    "SUBCLASS_CHOICE_AVAILABLE": SubclassChoiceAvailableData,
    "ARMOR_ABILITY_CHOICE_AVAILABLE": ArmorAbilityChoiceAvailableData,
    "COMBO_UPDATE": ComboUpdateData,
    "COMBO_MOVE_UNLOCKED": ComboMoveUnlockedData,
    "BERSERK_ACTIVATED": BerserkActivatedData,
    "RAGE_CHANGED": RageChangedData,
    "AFFIX_SEAL": AffixSealData,
    "METAMORPH_OPEN": MetamorphOpenData,
    "METAMORPH_OPTIONS": MetamorphOptionsData,
    "TALENT_METAMORPHED": TalentMetamorphData,
    "BOSS_SLAIN": BossSlainData,
    "TENGU_BADGE_QUALIFIED": TenguBadgeQualifiedData,
    "GOO_BADGE_QUALIFIED": GooBadgeQualifiedData,
    "CHASM_PROMPT": ChasmPromptData,
    "IMP_DIALOGUE": ImpDialogueData,
    "IMP_REWARD": ImpRewardData,
    "GHOST_DIALOGUE": GhostDialogueData,
    "GHOST_REWARD": GhostRewardData,
    "GHOST_SUMMON": GhostSummonData,
    "GHOST_DIRECT": GhostDirectData,
    "GHOST_GEAR_OPEN": GhostGearOpenData,
    "SCROLL_SELECT_TARGET": ScrollSelectTargetData,
    "TELEPORT": TeleportData,
    "MIRROR_IMAGE": MirrorImageData,
    "SHOCKING_PROC": ShockingProcData,
    "MESSAGE": MessageData,
    "BLOB_UPDATE": BlobUpdateData,
    "BLOB_DEPLETED": BlobDepletedData,
    "STATE_EFFECT": StateEffectData,
    "FIRE_IMBUE_ACTIVATED": FireImbueActivatedData,
    "INFERNO_ACTIVATED": InfernoActivatedData,
    "SACRIFICIAL_FIRE": SacrificialFireData,
    "LEAF_BURST": LeafBurstData,
    "SPELL_SPRITE": SpellSpriteData,
    "EYE_CHARGE": EyeChargeData,
    "EYE_DEATH_RAY": EyeDeathRayData,
    "TOAST": ToastData,
    "ALCHEMY_PREVIEW_RESULT": AlchemyPreviewResultData,
    "ALCHEMY_BREWED": AlchemyBrewedData,
    "ALCHEMY_ENERGIZED": AlchemyEnergizedData,
    "TRINKET_CHOICE": TrinketChoiceData,
    "TOOLKIT_BREW": ToolkitBrewData,
    "TOOLKIT_ENERGIZE_PROMPT": ToolkitEnergizePromptData,
    "TOOLKIT_ENERGIZED": ToolkitEnergizedData,
}
