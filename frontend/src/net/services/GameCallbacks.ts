import type {
  SerializedItem,
  AlchemyPreviewResultEvent,
  AlchemyBrewedEvent,
  AlchemyEnergizedEvent,
  TrinketChoiceEvent,
  ToolkitEnergizePromptEvent,
} from '../../types/contract';

export interface GameCallbacksConfig {
  onLevelUp?: (data: { level: number; tier_unlocked?: number | null; talent_points?: Record<string, number>; can_choose_subclass: boolean; can_choose_armor_ability: boolean }) => void;
  onSubclassChoiceAvailable?: (data: { options: string[] }) => void;
  onArmorAbilityChoiceAvailable?: (data: { options: string[] }) => void;
  onImbueWandChoiceAvailable?: (data: { staff_id: string; candidates: string[] }) => void;
  onMetamorphOpen?: () => void;
  onMetamorphOptions?: (data: { old_talent: string; options: string[] }) => void;
  onGooFightStarted?: (data: { mob: string }) => void;
  onTenguFightStarted?: (data: { mob: string }) => void;
  onChasmPrompt?: (data: { x: number; y: number }) => void;
  onDM300FightStarted?: (data: { mob: string }) => void;
  onDwarfKingFightStarted?: (data: { mob: string }) => void;
  onDwarfKingPhase2?: (data: { mob: string }) => void;
  onYogFightStarted?: (data: { mob: string }) => void;
  onYogFinalPhase?: (data: { mob: string }) => void;
  onShopOpen?: (data: { npc: string; stock: SerializedItem[]; gold: number }) => void;
  onImpDialogue?: (data: { npc: string; text: string; can_claim: boolean; tokens?: number | null }) => void;
  onGhostQuestGiven?: () => void;
  onGhostQuestProcessed?: () => void;
  onGhostQuestComplete?: () => void;
  onGhostDialogue?: (data: { npc: string; text: string; can_claim: boolean; weapon?: SerializedItem | null; armor?: SerializedItem | null }) => void;
  onWandmakerDialogue?: (data: { npc: string; text: string; can_claim: boolean; wand1?: SerializedItem | null; wand2?: SerializedItem | null }) => void;
  onScrollSelectTarget?: (data: { player: string; scroll_id: string; scroll_kind: string; candidates: string[] }) => void;
  onStoneSelectTarget?: (data: { player: string; stone_id: string; stone_kind: string; candidates: string[] }) => void;
  onStoneIntuitionPickItem?: (data: { player: string; stone_id: string; candidates: string[] }) => void;
  onStoneIntuitionGuessKind?: (data: { player: string; stone_id: string; item_id: string; possible_kinds: string[] }) => void;
  onStoneAugmentSelect?: (data: { player: string; stone_id: string; candidates: string[] }) => void;
  onStoneAugmentPickItem?: (data: { player: string; stone_id: string; candidates: string[] }) => void;
  onEnchantChoiceAvailable?: (data: { scroll_id: string; target_id: string; is_weapon: boolean; options: string[] }) => void;
  onGhostGearOpen?: (data: {
    player: string; rose_id: string; ghost_id: string;
    ghost_hp: number; ghost_max_hp: number;
    weapon?: Record<string, unknown> | null; armor?: Record<string, unknown> | null;
  }) => void;
  onBossSlain?: (data: { mob: string; depth: number; badge_image: number }) => void;
  onPlayerDeath?: (data: {
    score_breakdown?: { kills: number; floors: number; gold: number };
    can_resurrect?: boolean;
    has_ankh?: boolean;
    victory?: boolean;
    respawns_used?: number;
    max_respawns?: number;
    loot_dropped?: boolean;
    death_cause?: string;
  }) => void;
  onAlchemyPreviewResult?: (data: AlchemyPreviewResultEvent['data']) => void;
  onAlchemyBrewed?: (data: AlchemyBrewedEvent['data']) => void;
  onAlchemyEnergized?: (data: AlchemyEnergizedEvent['data']) => void;
  onTrinketChoice?: (data: TrinketChoiceEvent['data']) => void;
  onToolkitEnergizePrompt?: (data: ToolkitEnergizePromptEvent['data']) => void;
  onOpenAlchemy?: () => void;
  onLoreNeeded?: (depth: number, finishTransition: () => void) => void;
}

export class GameCallbacks {
  private config: GameCallbacksConfig;

  constructor(config: GameCallbacksConfig = {}) {
    this.config = config;
  }

  public levelUp(data: { level: number; tier_unlocked?: number | null; talent_points?: Record<string, number>; can_choose_subclass: boolean; can_choose_armor_ability: boolean }): void {
    this.config.onLevelUp?.(data);
  }

  public subclassChoiceAvailable(data: { options: string[] }): void {
    this.config.onSubclassChoiceAvailable?.(data);
  }

  public armorAbilityChoiceAvailable(data: { options: string[] }): void {
    this.config.onArmorAbilityChoiceAvailable?.(data);
  }

  public imbueWandChoiceAvailable(data: { staff_id: string; candidates: string[] }): void {
    this.config.onImbueWandChoiceAvailable?.(data);
  }

  public metamorphOpen(): void {
    this.config.onMetamorphOpen?.();
  }

  public metamorphOptions(data: { old_talent: string; options: string[] }): void {
    this.config.onMetamorphOptions?.(data);
  }

  public gooFightStarted(data: { mob: string }): void {
    this.config.onGooFightStarted?.(data);
  }

  public tenguFightStarted(data: { mob: string }): void {
    this.config.onTenguFightStarted?.(data);
  }

  public dm300FightStarted(data: { mob: string }): void {
    this.config.onDM300FightStarted?.(data);
  }

  public dwarfKingFightStarted(data: { mob: string }): void {
    this.config.onDwarfKingFightStarted?.(data);
  }

  public dwarfKingPhase2(data: { mob: string }): void {
    this.config.onDwarfKingPhase2?.(data);
  }

  public yogFightStarted(data: { mob: string }): void {
    this.config.onYogFightStarted?.(data);
  }

  public yogFinalPhase(data: { mob: string }): void {
    this.config.onYogFinalPhase?.(data);
  }

  public bossSlain(data: { mob: string; depth: number; badge_image: number }): void {
    this.config.onBossSlain?.(data);
  }

  public shopOpen(data: { npc: string; stock: SerializedItem[]; gold: number }): void {
    this.config.onShopOpen?.(data);
  }

  public impDialogue(data: { npc: string; text: string; can_claim: boolean; tokens?: number | null }): void {
    this.config.onImpDialogue?.(data);
  }

  public ghostDialogue(data: { npc: string; text: string; can_claim: boolean; weapon?: SerializedItem | null; armor?: SerializedItem | null }): void {
    this.config.onGhostDialogue?.(data);
  }

  public ghostQuestGiven(): void {
    this.config.onGhostQuestGiven?.();
  }

  public ghostQuestProcessed(): void {
    this.config.onGhostQuestProcessed?.();
  }

  public ghostQuestComplete(): void {
    this.config.onGhostQuestComplete?.();
  }

  public wandmakerDialogue(data: { npc: string; text: string; can_claim: boolean; wand1?: SerializedItem | null; wand2?: SerializedItem | null }): void {
    this.config.onWandmakerDialogue?.(data);
  }

  public ghostGearOpen(data: {
    player: string; rose_id: string; ghost_id: string;
    ghost_hp: number; ghost_max_hp: number;
    weapon?: Record<string, unknown> | null; armor?: Record<string, unknown> | null;
  }): void {
    this.config.onGhostGearOpen?.(data);
  }

  public chasmPrompt(data: { x: number; y: number }): void {
    this.config.onChasmPrompt?.(data);
  }

  public openAlchemy(): void {
    this.config.onOpenAlchemy?.();
  }

  public scrollSelectTarget(data: { player: string; scroll_id: string; scroll_kind: string; candidates: string[] }): void {
    this.config.onScrollSelectTarget?.(data);
  }

  public stoneSelectTarget(data: { player: string; stone_id: string; stone_kind: string; candidates: string[] }): void {
    this.config.onStoneSelectTarget?.(data);
  }

  public stoneIntuitionPickItem(data: { player: string; stone_id: string; candidates: string[] }): void {
    this.config.onStoneIntuitionPickItem?.(data);
  }

  public stoneIntuitionGuessKind(data: { player: string; stone_id: string; item_id: string; possible_kinds: string[] }): void {
    this.config.onStoneIntuitionGuessKind?.(data);
  }

  public stoneAugmentSelect(data: { player: string; stone_id: string; candidates: string[] }): void {
    this.config.onStoneAugmentSelect?.(data);
  }

  public stoneAugmentPickItem(data: { player: string; stone_id: string; candidates: string[] }): void {
    this.config.onStoneAugmentPickItem?.(data);
  }

  public enchantChoiceAvailable(data: { scroll_id: string; target_id: string; is_weapon: boolean; options: string[] }): void {
    this.config.onEnchantChoiceAvailable?.(data);
  }

  public alchemyPreviewResult(data: AlchemyPreviewResultEvent['data']): void {
    this.config.onAlchemyPreviewResult?.(data);
  }

  public alchemyBrewed(data: AlchemyBrewedEvent['data']): void {
    this.config.onAlchemyBrewed?.(data);
  }

  public alchemyEnergized(data: AlchemyEnergizedEvent['data']): void {
    this.config.onAlchemyEnergized?.(data);
  }

  public trinketChoice(data: TrinketChoiceEvent['data']): void {
    this.config.onTrinketChoice?.(data);
  }

  public toolkitEnergizePrompt(data: ToolkitEnergizePromptEvent['data']): void {
    this.config.onToolkitEnergizePrompt?.(data);
  }

  public playerDeath(data: {
    score_breakdown?: { kills: number; floors: number; gold: number };
    can_resurrect?: boolean;
    has_ankh?: boolean;
    victory?: boolean;
    respawns_used?: number;
    max_respawns?: number;
    loot_dropped?: boolean;
    death_cause?: string;
  }): void {
    this.config.onPlayerDeath?.(data);
  }

  public loreNeeded(depth: number, finishTransition: () => void): void {
    this.config.onLoreNeeded?.(depth, finishTransition);
  }
}
