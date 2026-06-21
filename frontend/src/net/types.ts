import type { Dispatch, SetStateAction } from 'react';
import type {
  Player,
  Mob,
  Difficulty,
  GameEvent,
  SerializedItem,
  TrapInfo,
  CustomTileLayer,
} from '../types/contract';

export type { Player, Mob, Difficulty, GameEvent, SerializedItem, TrapInfo, CustomTileLayer };

export interface RenderVec {
  x: number;
  y: number;
}

export interface RenderPlayer extends Player {
  renderPos: RenderVec;
  animStartPos: RenderVec;
  animStartTime: number | null;
  targetPos?: RenderVec;
  facing: string;
  flipX: boolean;
  deathStart: number | null;
}

export interface RenderMob extends Mob {
  renderPos: RenderVec;
  animStartPos: RenderVec;
  animStartTime: number | null;
  targetPos?: RenderVec;
  facing: string;
  flipX?: boolean;
}

export type DyingMob = RenderMob & { deathStart: number };

export interface AnimState {
  attackUntil?: number;
  flashUntil?: number;
  operateUntil?: number;
  readUntil?: number;
  pumpUntil?: number;
}

export interface Projectile {
  x: number;
  y: number;
  startX: number;
  startY: number;
  targetX: number;
  targetY: number;
  type: string;
  spriteCoords: unknown;
  progress: number;
  rotation: number;
  finished: boolean;
}

export interface EntitiesState {
  players: Record<string, RenderPlayer>;
  mobs: Record<string, RenderMob>;
  items: SerializedItem[];
}

export interface VisionState {
  visible: Set<string>;
  discovered: Set<string>;
}

export interface Ref<T> {
  current: T;
}

export interface MyStats {
  hp: number;
  maxHp: number;
  name: string;
  isDowned: boolean | undefined;
  isAdmin: boolean;
  isRegen: boolean;
  exp: number;
  level: number;
  maxExp: number;
  effects: Player['active_effects'];
  classType: string;
  armorTier: number;
  shield: number;
  strength: number;
  subclass?: string | null;
  armorAbility?: string | null;
  armorCharge?: number;
  berserkPower?: number;
  invisible?: number;
  prepSeconds?: number;
  comboCount?: number;
  talentLevels?: Record<string, number>;
  talentPoints?: Record<string, number>;
  bonusTalentPoints?: Record<string, number>;
  pos?: { x: number; y: number } | null;
  keys?: Player['keys'];
}

export interface HookProps {
  enabled: boolean;
  gameId: string;
  sessionId: string;
  selectedClass: string;
  difficulty: string;
  challenges?: string;
  playerName: string;
  setConnectionStatus?: (status: string) => void;
  socketRef: Ref<WebSocket | null>;
  gridRef: Ref<number[][]>;
  myPlayerIdRef: Ref<string | null>;
  entitiesRef: Ref<EntitiesState>;
  visionRef: Ref<VisionState>;
  openDoorsRef: Ref<Set<string>>;
  projectilesRef: Ref<Projectile[]>;
  trapsRef: Ref<TrapInfo[]>;
  customTilesRef: Ref<CustomTileLayer[]>;
  customWallsRef: Ref<CustomTileLayer[]>;
  mobAnimRef: Ref<Record<string, AnimState>>;
  dyingMobsRef: Ref<Record<string, DyingMob>>;
  playerAnimRef: Ref<Record<string, AnimState>>;
  particlesRef: Ref<unknown[]>;
  searchEffectsRef: Ref<unknown[]>;
  floatingTextRef: Ref<unknown[]>;
  warnedTilesRef?: Ref<{ tiles: [number, number][]; untilMs: number } | null>;
  screenFlashRef?: Ref<{ until: number } | null>;
  transmuteEffectsRef?: Ref<unknown[]>;
  flareEffectsRef?: Ref<unknown[]>;
  spellSpriteEffectsRef?: Ref<unknown[]>;
  lightningRef?: Ref<unknown[]>;
  shieldHaloRef?: Ref<unknown[]>;
  stateEffectsRef?: Ref<unknown[]>;
  screenShakeRef?: Ref<{ intensity: number; until: number } | null>;
  magicMissileRef?: Ref<unknown[]>;
  beamRef?: Ref<unknown[]>;
  blobAreasRef?: Ref<Record<string, { type: string; cells: Map<string, number> }>>;
  wasDownedRef: Ref<boolean | undefined>;
  surpriseRef?: Ref<unknown[]>;
  selectedEnemyIdRef?: Ref<string | null>;
  floorFadeRef?: Ref<unknown>;
  cameraLerpRef?: Ref<{ x: number; y: number }>;
  isCameraDetachedRef?: Ref<boolean>;
  setGrid: Dispatch<SetStateAction<number[][]>>;
  setDepth: (depth: number) => void;
  setMyPlayerId: (id: string) => void;
  setInventory: (items: Player['inventory']) => void;
  setEquippedItems: (e: { weapon: Player['equipped_weapon']; wearable: Player['equipped_wearable'] }) => void;
  setMyStats: (stats: MyStats) => void;
  setDifficulty: (difficulty: Difficulty) => void;
  setBossInfo?: (info: { name: string; hp: number; maxHp: number; shield?: number; effects?: { key?: string; name?: string; icon?: number; remaining?: number; duration?: number }[] } | null) => void;
  setGold?: (gold: number) => void;
  setEnergy?: (energy: number) => void;
  setHasAmulet?: (hasAmulet: boolean) => void;
  setExitPos?: (pos: [number, number] | null) => void;
  setBelongings?: (belongings: Player['belongings'] | null) => void;
  setQuickslot?: (quickslot: Player['quickslot'] | null) => void;
  onLevelUp?: (data: { level: number; tier_unlocked?: number | null; talent_points?: Record<string, number>; can_choose_subclass: boolean; can_choose_armor_ability: boolean }) => void;
  onSubclassChoiceAvailable?: (data: { options: string[] }) => void;
  onArmorAbilityChoiceAvailable?: (data: { options: string[] }) => void;
  onImbueWandChoiceAvailable?: (data: { staff_id: string; candidates: string[] }) => void;
  onTalentUpgraded?: (data: { talent: string; level: number }) => void;
  onMetamorphOpen?: () => void;
  onMetamorphOptions?: (data: { old_talent: string; options: string[] }) => void;
  onGooFightStarted?: (data: { mob: string }) => void;
  onTenguFightStarted?: (data: { mob: string }) => void;
  onDM300FightStarted?: (data: { mob: string }) => void;
  onDwarfKingFightStarted?: (data: { mob: string }) => void;
  onDwarfKingPhase2?: (data: { mob: string }) => void;
  onYogFightStarted?: (data: { mob: string }) => void;
  onYogFinalPhase?: (data: { mob: string }) => void;
  onShopOpen?: (data: { npc: string; stock: SerializedItem[]; gold: number }) => void;
  onImpDialogue?: (data: { npc: string; text: string; can_claim: boolean; tokens?: number | null }) => void;
  onGhostQuestGiven?: () => void;
  onGhostQuestComplete?: () => void;
  onGhostDialogue?: (data: { npc: string; text: string; can_claim: boolean; weapon?: SerializedItem | null; armor?: SerializedItem | null }) => void;
  onScrollSelectTarget?: (data: { player: string; scroll_id: string; scroll_kind: string; candidates: string[] }) => void;
  onGhostGearOpen?: (data: {
    player: string; rose_id: string; ghost_id: string;
    ghost_hp: number; ghost_max_hp: number;
    weapon?: Record<string, unknown> | null; armor?: Record<string, unknown> | null;
  }) => void;
  onBossSlain?: (data: { mob: string; depth: number; badge_image: number }) => void;
  onPlayerDeath?: (data: { score_breakdown?: { kills: number; floors: number; gold: number }; can_resurrect?: boolean; victory?: boolean }) => void;
}

export type HandlerCtx = Pick<
  HookProps,
  | 'myPlayerIdRef'
  | 'gridRef'
  | 'setGrid'
  | 'entitiesRef'
  | 'visionRef'
  | 'projectilesRef'
  | 'mobAnimRef'
  | 'dyingMobsRef'
  | 'playerAnimRef'
  | 'particlesRef'
  | 'searchEffectsRef'
  | 'floatingTextRef'
  | 'warnedTilesRef'
  | 'screenFlashRef'
  | 'transmuteEffectsRef'
  | 'flareEffectsRef'
  | 'spellSpriteEffectsRef'
  | 'lightningRef'
  | 'shieldHaloRef'
  | 'stateEffectsRef'
  | 'magicMissileRef'
  | 'surpriseRef'
  | 'selectedEnemyIdRef'
  | 'screenShakeRef'
  | 'beamRef'
  | 'blobAreasRef'
> & {
  onLevelUp?: HookProps['onLevelUp'];
  onSubclassChoiceAvailable?: HookProps['onSubclassChoiceAvailable'];
  onArmorAbilityChoiceAvailable?: HookProps['onArmorAbilityChoiceAvailable'];
  onImbueWandChoiceAvailable?: HookProps['onImbueWandChoiceAvailable'];
  onTalentUpgraded?: HookProps['onTalentUpgraded'];
  onMetamorphOpen?: HookProps['onMetamorphOpen'];
  onMetamorphOptions?: HookProps['onMetamorphOptions'];
  onGooFightStarted?: HookProps['onGooFightStarted'];
  onTenguFightStarted?: HookProps['onTenguFightStarted'];
  onDM300FightStarted?: HookProps['onDM300FightStarted'];
  onDwarfKingFightStarted?: HookProps['onDwarfKingFightStarted'];
  onDwarfKingPhase2?: HookProps['onDwarfKingPhase2'];
  onYogFightStarted?: HookProps['onYogFightStarted'];
  onYogFinalPhase?: HookProps['onYogFinalPhase'];
  onShopOpen?: HookProps['onShopOpen'];
  onImpDialogue?: HookProps['onImpDialogue'];
  onGhostDialogue?: HookProps['onGhostDialogue'];
  onGhostQuestGiven?: HookProps['onGhostQuestGiven'];
  onGhostQuestComplete?: HookProps['onGhostQuestComplete'];
  onScrollSelectTarget?: HookProps['onScrollSelectTarget'];
  onGhostGearOpen?: HookProps['onGhostGearOpen'];
  onBossSlain?: HookProps['onBossSlain'];
  onPlayerDeath?: HookProps['onPlayerDeath'];
  depth?: number;
};

export type SyncCtx = Pick<
  HookProps,
  | 'myPlayerIdRef'
  | 'gridRef'
  | 'entitiesRef'
  | 'visionRef'
  | 'openDoorsRef'
  | 'trapsRef'
  | 'dyingMobsRef'
  | 'wasDownedRef'
  | 'setInventory'
  | 'setEquippedItems'
  | 'setMyStats'
  | 'setBossInfo'
  | 'setBelongings'
  | 'setQuickslot'
>;
