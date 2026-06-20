/**
 * Client <-> server WebSocket contract.
 *
 * The entity shapes (Player, Mob, every item variant) are auto-generated from the
 * backend Pydantic models into ./generated/entities.ts -- regenerate with
 * `npm run gen:types` whenever those models change.
 *
 * This file hand-writes the parts that are NOT Pydantic models: the message
 * envelopes (INIT / STATE_UPDATE), the per-tick event payloads, and the outgoing
 * client messages. Those are assembled as plain dicts in backend/app/main.py,
 * engine/game/*.py and engine/game/serialization.py, so they have no schema to
 * generate from and must be kept in sync by hand.
 */
import type {
  Player,
  Mob,
  MeleeWeapon,
  Dagger,
  Bow,
  Staff,
  MissileWeapon,
  Armor,
  Ring,
  Artifact,
  Wand,
  HealthPotion,
  RevivingPotion,
  FuryPotion,
  Potion,
  Scroll,
  WornShortsword,
  BrokenSeal,
  ScrollOfRage,
  ScrollOfMetamorphosis,
  Gold,
  Food,
  MysteryMeat,
  Key,
  Seed,
  Stone,
  Boomerang,
  ThrowableDagger,
  Throwable,
  VelvetPouch,
  ScrollHolder,
  MagicalHolster,
  PotionBandolier,
  Bag,
} from './generated/entities';

export type { Player, Mob } from './generated/entities';

/** A grid cell coordinate pair `[x, y]` as sent in `visible_tiles` / `open_doors`. */
export type Vec2 = [number, number];

// --- items -----------------------------------------------------------------

/** The `AnyItem` discriminated union (on `kind`), mirroring base.py's AnyItem. */
export type GeneratedItem =
  | MeleeWeapon
  | Dagger
  | WornShortsword
  | Bow
  | Staff
  | MissileWeapon
  | Armor
  | Ring
  | Artifact
  | BrokenSeal
  | Wand
  | HealthPotion
  | RevivingPotion
  | FuryPotion
  | Potion
  | Scroll
  | ScrollOfRage
  | ScrollOfMetamorphosis
  | Gold
  | Food
  | MysteryMeat
  | Key
  | Seed
  | Stone
  | Boomerang
  | ThrowableDagger
  | Throwable
  | VelvetPouch
  | ScrollHolder
  | MagicalHolster
  | PotionBandolier
  | Bag;

/**
 * Fields the server attaches during serialization (serialization.py) that are not
 * on the Pydantic item models: the per-player action menu, and the per-run
 * colour/rune sprite for potions/scrolls.
 */
export interface SerializationExtras {
  actions: string[];
  default_action: string | null;
  description: string;
  /** Sprite cell for a potion/scroll's per-run appearance; only on those kinds. */
  appearance?: { col: number; row: number };
}

/** An item as it actually arrives over the wire (model + serialization extras). */
export type SerializedItem = GeneratedItem & SerializationExtras;

// --- shared small shapes ---------------------------------------------------

export type Difficulty = 'normal' | 'easy' | 'hard';

export type Direction =
  | 'UP'
  | 'DOWN'
  | 'LEFT'
  | 'RIGHT'
  | 'UP_LEFT'
  | 'UP_RIGHT'
  | 'DOWN_LEFT'
  | 'DOWN_RIGHT';

export interface TrapInfo {
  x: number;
  y: number;
  trap_type: string;
}

/** A single tile mutation in a MAP_PATCH event. */
export interface TilePatch {
  x: number;
  y: number;
  tile: number;
}

// --- server -> client: events ----------------------------------------------
// Payloads mirror the add_event(...) call sites across engine/game/*.py and
// engine/entities/item_actions.py.

export interface AttackEvent {
  type: 'ATTACK';
  data: {
    source: string;
    target: string;
    damage: number;
    surprise: boolean;
    crit: boolean;
    grim_proc: boolean;
  };
}

export interface MissEvent {
  type: 'MISS';
  data: { source: string; target: string; defense_verb: string };
}

export interface DamageEvent {
  type: 'DAMAGE';
  data: {
    target: string;
    amount: number;
    crit?: boolean;
    grim_proc?: boolean;
    bleed?: boolean;
    projectile?: string;
    splash_count?: number;
    source_x?: number;
    source_y?: number;
    beam_type?: string;
  };
}

export interface SpellSpriteEvent {
  type: 'SPELL_SPRITE';
  data: {
    index: number;
    x: number;
    y: number;
  };
}

export interface DeathEvent {
  type: 'DEATH';
  data: {
    target: string;
    score_breakdown?: { kills: number; floors: number; gold: number };
    can_resurrect?: boolean;
    victory?: boolean;
  };
}

export interface MoveEvent {
  type: 'MOVE';
  data: { entity: string; x: number; y: number };
}

export interface RangedAttackEvent {
  type: 'RANGED_ATTACK';
  data: {
    source: string;
    x: number;
    y: number;
    target_x: number;
    target_y: number;
    projectile: string;
    crit: boolean;
    grim_proc: boolean;
    beam_type?: string;
    target_hp_ratio?: number;
    sound?: string;
    is_wand?: boolean;
    /** Serialized thrown item, present for thrown inventory items (not wands). */
    item?: SerializedItem;
  };
}

export interface PlaySoundEvent {
  type: 'PLAY_SOUND';
  data: { sound: string; rate?: number };
}

export interface ShockingProcEvent {
  type: 'SHOCKING_PROC';
  data: {
    source: string;
    defender: string;
    defender_x: number;
    defender_y: number;
    chain_targets: Array<{ id: string; x: number; y: number }>;
  };
}

export interface SearchEvent {
  type: 'SEARCH';
  data: {
    player: string;
    x: number;
    y: number;
    cells: Vec2[];
    revealed_tiles: number;
  };
}

export interface HealEvent {
  type: 'HEAL';
  data: { target: string; amount: number; x: number; y: number };
}

export interface TrapTriggeredEvent {
  type: 'TRAP_TRIGGERED';
  data: { player: string; trap: string; damage: number };
}

export interface DrinkEvent {
  type: 'DRINK';
  data: { player: string; type: string };
}

export interface ReadEvent {
  type: 'READ';
  data: { player: string; item: string; sound?: string; visual?: string };
}

export interface TeleportEvent {
  type: 'TELEPORT';
  data: { player: string; from_x: number; from_y: number; x: number; y: number };
}

export interface MirrorImageEvent {
  type: 'MIRROR_IMAGE';
  data: { player: string; clones: { id: string; x: number; y: number }[] };
}

export interface MessageEvent {
  type: 'MESSAGE';
  data: { text: string; color?: string };
}

export interface ToastEvent {
  type: 'TOAST';
  data: { text: string };
}

export interface MapPatchEvent {
  type: 'MAP_PATCH';
  data: { tiles: TilePatch[] };
}

export interface PickupEvent {
  type: 'PICKUP';
  data: { player: string; item: string };
}

export interface DropEvent {
  type: 'DROP';
  data: { player: string; item: string };
}

/** Waterskin auto-collects a Dewdrop underfoot (mirrors Waterskin.collect()). */
export interface CollectDewEvent {
  type: 'COLLECT_DEW';
  data: { player: string; item: string };
}

/** Gold pile picked up — added directly to the gold counter, not the inventory. */
export interface PickupGoldEvent {
  type: 'PICKUP_GOLD';
  data: { player: string; amount: number };
}

/** Key picked up — added directly to the per-floor key counter, not the inventory. */
export interface PickupKeyEvent {
  type: 'PICKUP_KEY';
  data: { player: string; key_id: string; name: string };
}

/** Player interacted with a Shopkeeper NPC — opens the shop window. */
export interface ShopOpenEvent {
  type: 'SHOP_OPEN';
  data: { player: string; npc: string; stock: SerializedItem[]; gold: number };
}

/** Player bought an item from a Shopkeeper. */
export interface ShopBuyEvent {
  type: 'SHOP_BUY';
  data: { player: string; item: string; price: number };
}

/** Player sold an item to a Shopkeeper. */
export interface ShopSellEvent {
  type: 'SHOP_SELL';
  data: { player: string; item: string; price: number };
}

/** Imp NPC dialogue (quest offer / reminder / reward-ready). */
export interface ImpDialogueEvent {
  type: 'IMP_DIALOGUE';
  data: { player: string; npc: string; text: string; can_claim: boolean; tokens?: number | null };
}

/** Player claimed the Imp's quest reward; the Imp despawns. */
export interface ImpRewardEvent {
  type: 'IMP_REWARD';
  data: { player: string; npc: string; item: string };
}

export interface StairsDownEvent {
  type: 'STAIRS_DOWN';
  data: { player: string; first_visit: boolean };
}

export interface StairsUpEvent {
  type: 'STAIRS_UP';
  data: { player: string };
}

export interface ReviveEvent {
  type: 'REVIVE';
  data: { target: string; source: string };
}

export interface UnlockEvent {
  type: 'UNLOCK';
  data: { player: string; x: number; y: number };
}

export interface LevelUpEvent {
  type: 'LEVEL_UP';
  data: {
    player: string;
    level: number;
    tier_unlocked?: number | null;
    talent_points?: Record<string, number>;
    can_choose_subclass: boolean;
    can_choose_armor_ability: boolean;
  };
}

export interface SubclassChoiceAvailableEvent {
  type: 'SUBCLASS_CHOICE_AVAILABLE';
  data: { player: string; options: string[] };
}

export interface ArmorAbilityChoiceAvailableEvent {
  type: 'ARMOR_ABILITY_CHOICE_AVAILABLE';
  data: { player: string; options: string[] };
}

export interface ImbueWandChoiceAvailableEvent {
  type: 'IMBUE_WAND_CHOICE_AVAILABLE';
  data: { player: string; staff_id: string; candidates: string[] };
}

export interface ImbueWandDoneEvent {
  type: 'IMBUE_WAND_DONE';
  data: { player: string; staff_id: string; old_wand_id: string };
}

export interface SubclassChosenEvent {
  type: 'SUBCLASS_CHOSEN';
  data: { player: string; subclass: string };
}

export interface TalentUpgradedEvent {
  type: 'TALENT_UPGRADED';
  data: { player: string; talent: string; level: number };
}

export interface ComboUpdateEvent {
  type: 'COMBO_UPDATE';
  data: { player: string; count: number };
}

export interface ComboMoveUnlockedEvent {
  type: 'COMBO_MOVE_UNLOCKED';
  data: { player: string; move: string };
}

export interface BerserkActivatedEvent {
  type: 'BERSERK_ACTIVATED';
  data: { player: string };
}

export interface RageChangedEvent {
  type: 'RAGE_CHANGED';
  data: { player: string; power: number };
}

export interface AffixSealEvent {
  type: 'AFFIX_SEAL';
  data: { player: string; armor: string };
}

/** Rogue: Cloak of Shadows stealth toggled on/off. */
export interface StealthEvent {
  type: 'STEALTH';
  data: { player: string; active: boolean };
}

/** Rogue: an enemy was Death-Marked. */
export interface DeathMarkEvent {
  type: 'DEATH_MARK';
  data: { player: string; target: string };
}

/** Rogue: a Shadow Clone ally was summoned. */
export interface ShadowCloneEvent {
  type: 'SHADOW_CLONE';
  data: { player: string; clone: string; x: number; y: number };
}

/** A shielding/barrier amount was granted to a player. */
export interface ShieldEvent {
  type: 'SHIELD';
  data: { player: string; amount: number };
}

/** Every event the server can place in `STATE_UPDATE.events`. */
export interface MetamorphOpenEvent {
  type: 'METAMORPH_OPEN';
  data: { player: string };
}

export interface MetamorphOptionsEvent {
  type: 'METAMORPH_OPTIONS';
  data: { player: string; old_talent: string; options: string[] };
}

export interface TalentMetamorphedEvent {
  type: 'TALENT_METAMORPHED';
  data: { player: string; old_talent: string; new_talent: string };
}

/** Scroll item-selector flow: server asks the player to pick a target item
 * for a scroll (e.g. Scroll of Upgrade). `candidates` lists valid item ids. */
export interface ScrollSelectTargetEvent {
  type: 'SCROLL_SELECT_TARGET';
  data: { player: string; scroll_id: string; scroll_kind: string; candidates: string[] };
}

/** Boss was slain — shows "BOSS SLAIN" banner + badge icon. */
export interface BossSlainEvent {
  type: 'BOSS_SLAIN';
  data: { mob: string; depth: number; badge_image: number };
}

/** Goo boss: pumped-up charge telegraph. `tiles` lists the threatened cells
 * (cleared with an empty array when the charge is released or cancelled). */
export interface GooChargeEvent {
  type: 'GOO_CHARGE';
  data: { mob: string; tiles: [number, number][]; duration_ms?: number };
}

/** Goo boss crossed the 50% HP enrage threshold. */
export interface GooEnrageEvent {
  type: 'GOO_ENRAGE';
  data: { mob: string };
}

/** Goo boss noticed the hero — the fight begins (mirrors SPD's Goo.notice()/seal()). */
export interface GooFightStartedEvent {
  type: 'GOO_FIGHT_STARTED';
  data: { mob: string };
}

/** DM-300 noticed the hero — the fight begins. */
export interface DM300FightStartedEvent {
  type: 'DM300_FIGHT_STARTED';
  data: { mob: string };
}

/** Dwarf King noticed the hero — the fight begins. */
export interface DwarfKingFightStartedEvent {
  type: 'DWARF_KING_FIGHT_STARTED';
  data: { mob: string };
}

/** Dwarf King enters phase 2 (HP <= 200). */
export interface DwarfKingPhase2Event {
  type: 'DWARF_KING_PHASE2';
  data: { mob: string };
}

/** Dwarf King enters phase 3 (HP <= 100). */
export interface DwarfKingPhase3Event {
  type: 'DWARF_KING_PHASE3';
  data: { mob: string };
}

/** Yog-Dzewa noticed the hero — the fight begins. */
export interface YogFightStartedEvent {
  type: 'YOG_FIGHT_STARTED';
  data: { mob: string };
}

/** Yog-Dzewa entered a new phase. */
export interface YogPhaseChangeEvent {
  type: 'YOG_PHASE_CHANGE';
  data: { mob: string; phase: number };
}

/** Yog-Dzewa entered the final phase (phase 5). */
export interface YogFinalPhaseEvent {
  type: 'YOG_FINAL_PHASE';
  data: { mob: string };
}

/** Tengu spawns and the prison cell seals behind it (mirrors PrisonBossLevel's START -> FIGHT_START). */
export interface TenguFightStartedEvent {
  type: 'TENGU_FIGHT_STARTED';
  data: { mob: string };
}

/** Necromancer zaps a cell — summon, heal, or buff its NecroSkeleton (mirrors NecromancerSprite.zap). */
export interface ZapSummonEvent {
  type: 'ZAP_SUMMON';
  data: { mob: string; x: number; y: number };
}

/** Necromancer's NecroSkeleton appears/teleports to a cell. */
export interface NecroSummonEvent {
  type: 'NECRO_SUMMON';
  data: { necromancer: string; skeleton: string; x: number; y: number };
}

/** Tengu boss teleports away after dropping into a new HP/8 bracket (Tengu.jump()). */
export interface TenguJumpEvent {
  type: 'TENGU_JUMP';
  data: { mob: string; x: number; y: number };
}

/** Tengu throws a bomb that detonates after a 3-turn countdown. */
export interface TenguBombEvent {
  type: 'TENGU_BOMB';
  data: { mob: string; x: number; y: number; timer: number };
}

/** Tengu bomb countdown tick (SPD: "3...", "2...", "1..." floating text). */
export interface TenguBombCountdownEvent {
  type: 'TENGU_BOMB_COUNTDOWN';
  data: { mob: string; x: number; y: number; count: number };
}

/** Tengu's bomb detonates, dealing radius-2 AoE damage. */
export interface TenguBlastEvent {
  type: 'TENGU_BLAST';
  data: { mob: string; x: number; y: number };
}

/** Tengu breathes fire in a 3-cell line toward its target. */
export interface TenguFireEvent {
  type: 'TENGU_FIRE';
  data: { mob: string; cells: Vec2[] };
}

/** Tengu calls down a lightning cross centered on its target. */
export interface TenguShockerEvent {
  type: 'TENGU_SHOCKER';
  data: { mob: string; cells: Vec2[] };
}

/** Persistent blob area (fire, gas, electricity) state update. */
export interface BlobUpdateEvent {
  type: 'BLOB_UPDATE';
  data: { id: string; type: string; cells: [number, number, number][] };
}

/** Blob area fully depleted. */
export interface BlobDepletedEvent {
  type: 'BLOB_DEPLETED';
  data: { id: string };
}

/** State effect (burning, frozen, etc.) triggered from buff. */
export interface StateEffectEvent {
  type: 'STATE_EFFECT';
  data: { entity_id: string; effect: string; x: number; y: number };
}

/** FireImbue activated — flame burst around player. */
export interface FireImbueActivatedEvent {
  type: 'FIRE_IMBUE_ACTIVATED';
  data: { player: string; x: number; y: number };
}

/** Inferno blob activated — green fire burst. */
export interface InfernoActivatedEvent {
  type: 'INFERNO_ACTIVATED';
  data: { x: number; y: number };
}

/** Sacrificial fire — blue flame particles. */
export interface SacrificialFireEvent {
  type: 'SACRIFICIAL_FIRE';
  data: { x: number; y: number };
}

/** Potion of Liquid Flame shatter — orange flame burst. */
export interface FlameBurstEvent {
  type: 'FLAME_BURST';
  data: { x: number; y: number };
}

export type GameEvent =
  | AttackEvent
  | MissEvent
  | DamageEvent
  | DeathEvent
  | MoveEvent
  | RangedAttackEvent
  | PlaySoundEvent
  | SearchEvent
  | HealEvent
  | TrapTriggeredEvent
  | DrinkEvent
  | ReadEvent
  | MapPatchEvent
  | PickupEvent
  | DropEvent
  | CollectDewEvent
  | PickupGoldEvent
  | PickupKeyEvent
  | ShopOpenEvent
  | ShopBuyEvent
  | ShopSellEvent
  | ImpDialogueEvent
  | ImpRewardEvent
  | StairsDownEvent
  | StairsUpEvent
  | ReviveEvent
  | UnlockEvent
  | LevelUpEvent
  | SubclassChosenEvent
  | TalentUpgradedEvent
  | ComboUpdateEvent
  | ComboMoveUnlockedEvent
  | BerserkActivatedEvent
  | RageChangedEvent
  | AffixSealEvent
  | StealthEvent
  | DeathMarkEvent
  | ShadowCloneEvent
  | ShieldEvent
  | SubclassChoiceAvailableEvent
  | ArmorAbilityChoiceAvailableEvent
  | ImbueWandChoiceAvailableEvent
  | ImbueWandDoneEvent
  | MetamorphOpenEvent
  | MetamorphOptionsEvent
  | TalentMetamorphedEvent
  | ScrollSelectTargetEvent
  | GooChargeEvent
  | GooEnrageEvent
  | GooFightStartedEvent
  | DM300FightStartedEvent
  | DwarfKingFightStartedEvent
  | DwarfKingPhase2Event
  | DwarfKingPhase3Event
  | YogFightStartedEvent
  | YogPhaseChangeEvent
  | YogFinalPhaseEvent
  | TenguFightStartedEvent
  | ZapSummonEvent
  | NecroSummonEvent
  | TenguJumpEvent
  | TenguBombEvent
  | TenguBombCountdownEvent
  | TenguBlastEvent
  | TenguFireEvent
  | TenguShockerEvent
  | TeleportEvent
  | MirrorImageEvent
  | MessageEvent
  | ToastEvent
  | BossSlainEvent
  | ShockingProcEvent
  | BlobUpdateEvent
  | BlobDepletedEvent
  | StateEffectEvent
  | FireImbueActivatedEvent
  | InfernoActivatedEvent
  | SacrificialFireEvent
  | FlameBurstEvent
  | SpellSpriteEvent;

export type GameEventType = GameEvent['type'];

// --- server -> client: message envelopes -----------------------------------

/** Sent on connect and whenever the player changes floor (main.py:154). */
export interface InitMessage {
  type: 'INIT';
  depth: number;
  grid: number[][];
  width: number;
  height: number;
  traps: TrapInfo[];
  /** Decorative custom tilemaps (e.g. GooNest), cosmetic only. */
  custom_tiles?: CustomTileLayer[];
  /** Custom wall overlays rendered above characters (e.g. SewerExitOverhang). */
  custom_walls?: CustomTileLayer[];
  /** Only present on the very first INIT after connecting. */
  player_id?: string;
}

/** A decorative tilemap overlay (e.g. GooBossRoom's GooNest). */
export interface CustomTileLayer {
  texture: string;
  x: number;
  y: number;
  w: number;
  h: number;
  tiles: number[][];
}

/** The 20Hz per-player snapshot (main.py:168). */
export interface StateUpdateMessage {
  type: 'STATE_UPDATE';
  depth: number;
  difficulty: Difficulty;
  players: Player[];
  mobs: Mob[];
  items: SerializedItem[];
  visible_tiles: Vec2[];
  mapped_tiles?: Vec2[];
  traps: TrapInfo[];
  gold: number;
  energy: number;
  events: GameEvent[];
  /**
   * Read defensively by the client but not currently forwarded in STATE_UPDATE;
   * kept optional to document the consumer's guard.
   */
  open_doors?: Vec2[];
}

export interface PongMessage {
  type: 'PONG';
}

/** Any frame the client can receive. */
export type ServerMessage = InitMessage | StateUpdateMessage | PongMessage;

// --- client -> server: messages --------------------------------------------
// Mirrors the handlers in backend/app/main.py:211-293.

export type ClientMessage =
  | { type: 'PING' }
  | { type: 'MOVE'; direction: Direction }
  | { type: 'MOVE_INTENT'; dx: number; dy: number }
  | { type: 'MOVE_STOP' }
  | { type: 'MOVE_TO'; x: number; y: number }
  | {
      type: 'EXECUTE_ITEM_ACTION';
      item_id: string;
      action: string;
      target_x?: number;
      target_y?: number;
    }
  | { type: 'SET_QUICKSLOT'; index: number; item_id: string }
  | { type: 'USE_QUICKSLOT'; index: number; target_x?: number; target_y?: number }
  | { type: 'EQUIP_ITEM'; item_id: string }
  | { type: 'DROP_ITEM'; item_id: string }
  | { type: 'USE_ITEM'; item_id: string }
  | { type: 'RANGED_ATTACK'; item_id: string; target_x: number; target_y: number }
  | { type: 'CHANGE_DIFFICULTY'; difficulty: Difficulty }
  | { type: 'SEARCH' }
  | { type: 'WAIT' }
  | { type: 'CHOOSE_SUBCLASS'; subclass: string }
  | { type: 'UPGRADE_TALENT'; talent: string }
  | { type: 'USE_ARMOR_ABILITY'; ability: string; target_x?: number; target_y?: number }
  | { type: 'TRIGGER_BERSERK' }
  | { type: 'PREPARATION_STRIKE'; target_x: number; target_y: number }
  | { type: 'CHOOSE_IMBUE_WAND'; staff_id: string; wand_id: string }
  | { type: 'METAMORPH_CHOOSE'; talent: string }
  | { type: 'METAMORPH_REPLACE'; old_talent: string; new_talent: string }
  | { type: 'ADMIN_TELEPORT'; target_floor: number }
  | { type: 'ADMIN_LEVEL_UP' }
  | { type: 'ADMIN_GIVE_ITEM'; item_kind: string }
  | { type: 'NPC_INTERACT'; npc_id: string }
  | { type: 'SHOP_BUY'; npc_id: string; item_id: string }
  | { type: 'SHOP_SELL'; item_id: string }
  | { type: 'IMP_CLAIM_REWARD'; npc_id: string }
  | { type: 'SELECT_SCROLL_TARGET'; scroll_id: string; item_id: string };
