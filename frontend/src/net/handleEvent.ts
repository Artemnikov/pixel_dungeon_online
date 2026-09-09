import AudioManager from '../audio/AudioManager';
import type { GameEvent } from '../types/contract';
import type { HandlerCtx } from './types';
import { WorldManager } from './services/WorldManager';
import { EntityManager } from './services/EntityManager';
import { VisualEffectsManager } from './services/VisualEffectsManager';
import { GameCallbacks } from './services/GameCallbacks';
import { defaultEventDispatcher } from './events/defaultDispatcher';
import type { GameEventContext } from './events/IGameEventHandler';

export function handleEvent(event: GameEvent, ctx: HandlerCtx): void {
  const world = new WorldManager({
    gridRef: ctx.gridRef,
    setGrid: ctx.setGrid,
    visionRef: ctx.visionRef,
    depthRef: ctx.depth !== undefined ? { current: ctx.depth } : undefined,
    blobAreasRef: ctx.blobAreasRef,
  });

  const entities = new EntityManager({
    entitiesRef: ctx.entitiesRef,
    dyingMobsRef: ctx.dyingMobsRef,
    myPlayerIdRef: ctx.myPlayerIdRef,
    selectedEnemyIdRef: ctx.selectedEnemyIdRef,
  });

  const effects = new VisualEffectsManager({
    projectilesRef: ctx.projectilesRef,
    mobAnimRef: ctx.mobAnimRef,
    playerAnimRef: ctx.playerAnimRef,
    particlesRef: ctx.particlesRef,
    searchEffectsRef: ctx.searchEffectsRef,
    floatingTextRef: ctx.floatingTextRef,
    warnedTilesRef: ctx.warnedTilesRef,
    screenFlashRef: ctx.screenFlashRef,
    transmuteEffectsRef: ctx.transmuteEffectsRef,
    flareEffectsRef: ctx.flareEffectsRef,
    spellSpriteEffectsRef: ctx.spellSpriteEffectsRef,
    lightningRef: ctx.lightningRef,
    shieldHaloRef: ctx.shieldHaloRef,
    stateEffectsRef: ctx.stateEffectsRef,
    screenShakeRef: ctx.screenShakeRef,
    magicMissileRef: ctx.magicMissileRef,
    beamRef: ctx.beamRef,
    surpriseRef: ctx.surpriseRef,
    flyingItemsRef: ctx.flyingItemsRef,
  });

  const ui = new GameCallbacks({
    onLevelUp: ctx.onLevelUp,
    onSubclassChoiceAvailable: ctx.onSubclassChoiceAvailable,
    onArmorAbilityChoiceAvailable: ctx.onArmorAbilityChoiceAvailable,
    onImbueWandChoiceAvailable: ctx.onImbueWandChoiceAvailable,
    onMetamorphOpen: ctx.onMetamorphOpen,
    onMetamorphOptions: ctx.onMetamorphOptions,
    onGooFightStarted: ctx.onGooFightStarted,
    onTenguFightStarted: ctx.onTenguFightStarted,
    onChasmPrompt: ctx.onChasmPrompt,
    onDM300FightStarted: ctx.onDM300FightStarted,
    onDwarfKingFightStarted: ctx.onDwarfKingFightStarted,
    onDwarfKingPhase2: ctx.onDwarfKingPhase2,
    onYogFightStarted: ctx.onYogFightStarted,
    onYogFinalPhase: ctx.onYogFinalPhase,
    onShopOpen: ctx.onShopOpen,
    onImpDialogue: ctx.onImpDialogue,
    onGhostDialogue: ctx.onGhostDialogue,
    onWandmakerDialogue: ctx.onWandmakerDialogue,
    onGhostQuestGiven: ctx.onGhostQuestGiven,
    onGhostQuestProcessed: ctx.onGhostQuestProcessed,
    onGhostQuestComplete: ctx.onGhostQuestComplete,
    onScrollSelectTarget: ctx.onScrollSelectTarget,
    onStoneSelectTarget: ctx.onStoneSelectTarget,
    onStoneIntuitionPickItem: ctx.onStoneIntuitionPickItem,
    onStoneIntuitionGuessKind: ctx.onStoneIntuitionGuessKind,
    onStoneAugmentSelect: ctx.onStoneAugmentSelect,
    onStoneAugmentPickItem: ctx.onStoneAugmentPickItem,
    onGhostGearOpen: ctx.onGhostGearOpen,
    onEnchantChoiceAvailable: ctx.onEnchantChoiceAvailable,
    onBossSlain: ctx.onBossSlain,
    onPlayerDeath: ctx.onPlayerDeath,
    onAlchemyPreviewResult: ctx.onAlchemyPreviewResult,
    onAlchemyBrewed: ctx.onAlchemyBrewed,
    onAlchemyEnergized: ctx.onAlchemyEnergized,
    onTrinketChoice: ctx.onTrinketChoice,
    onToolkitEnergizePrompt: ctx.onToolkitEnergizePrompt,
    onOpenAlchemy: ctx.onOpenAlchemy,
  });

  const eventContext: GameEventContext = {
    myPlayerId: ctx.myPlayerIdRef.current,
    world,
    entities,
    effects,
    ui,
    audio: AudioManager,
  };

  defaultEventDispatcher.dispatch(event, eventContext);
}
