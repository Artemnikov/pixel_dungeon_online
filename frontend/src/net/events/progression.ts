import AudioManager from '../../audio/AudioManager';
import { addGameLog, dispatchToast } from '../../ui/gameLogHelpers';
import type { GameEvent } from '../../types/contract';
import type { HandlerCtx } from '../types';

export function handleProgressionEvents(event: GameEvent, ctx: HandlerCtx): boolean {
  const {
    myPlayerIdRef,
    onLevelUp, onSubclassChoiceAvailable, onArmorAbilityChoiceAvailable,
    onImbueWandChoiceAvailable, onTalentUpgraded, onMetamorphOpen, onMetamorphOptions,
    onGooFightStarted: _g, onTenguFightStarted: _t,
    onShopOpen, onImpDialogue, onGhostDialogue, onScrollSelectTarget, onGhostGearOpen, onBossSlain, onGhostQuestGiven, onGhostQuestComplete,
    onStoneSelectTarget, onStoneIntuitionPickItem, onStoneIntuitionGuessKind, onStoneAugmentPickItem,
    onEnchantChoiceAvailable,
  } = ctx;

  if (event.type === 'LEVEL_UP') {
    if (event.data.player === myPlayerIdRef.current) {
      addGameLog(`Level up! You are now level ${event.data.level}`, 'positive');
      onLevelUp?.({
        level: event.data.level,
        tier_unlocked: event.data.tier_unlocked,
        talent_points: event.data.talent_points,
        can_choose_subclass: event.data.can_choose_subclass,
        can_choose_armor_ability: event.data.can_choose_armor_ability,
      });
    }
    return true;
  }

  if (event.type === 'SUBCLASS_CHOICE_AVAILABLE') {
    if (event.data.player === myPlayerIdRef.current) {
      onSubclassChoiceAvailable?.({ options: event.data.options });
    }
    return true;
  }

  if (event.type === 'ARMOR_ABILITY_CHOICE_AVAILABLE') {
    if (event.data.player === myPlayerIdRef.current) {
      onArmorAbilityChoiceAvailable?.({ options: event.data.options });
    }
    return true;
  }

  if (event.type === 'IMBUE_WAND_CHOICE_AVAILABLE') {
    if (event.data.player === myPlayerIdRef.current) {
      onImbueWandChoiceAvailable?.({ staff_id: event.data.staff_id, candidates: event.data.candidates });
    }
    return true;
  }

  if (event.type === 'IMBUE_WAND_DONE') {
    if (event.data.player === myPlayerIdRef.current) {
      AudioManager.play('CLICK');
      addGameLog('Your wand has been imbued into the staff', 'positive');
    }
    return true;
  }

  if (event.type === 'TALENT_UPGRADED') {
    if (event.data.player === myPlayerIdRef.current) {
      onTalentUpgraded?.({ talent: event.data.talent, level: event.data.level });
    }
    return true;
  }

  if (event.type === 'METAMORPH_OPEN') {
    if (event.data.player === myPlayerIdRef.current) onMetamorphOpen?.();
    return true;
  }

  if (event.type === 'METAMORPH_OPTIONS') {
    if (event.data.player === myPlayerIdRef.current) onMetamorphOptions?.(event.data);
    return true;
  }

  if (event.type === 'SHOP_OPEN') {
    if (event.data.player === myPlayerIdRef.current) {
      onShopOpen?.({ npc: event.data.npc, stock: event.data.stock, gold: event.data.gold });
    }
    return true;
  }

  if (event.type === 'SHOP_BUY' || event.type === 'SHOP_SELL') {
    if (event.data.player === myPlayerIdRef.current) AudioManager.play('CLICK');
    return true;
  }

  if (event.type === 'IMP_DIALOGUE') {
    if (event.data.player === myPlayerIdRef.current) {
      onImpDialogue?.({
        npc: event.data.npc, text: event.data.text,
        can_claim: event.data.can_claim, tokens: event.data.tokens,
      });
    }
    return true;
  }

  if (event.type === 'IMP_REWARD') {
    if (event.data.player === myPlayerIdRef.current) AudioManager.play('BOSS');
    return true;
  }

  if (event.type === 'GHOST_DIALOGUE') {
    if (event.data.player === myPlayerIdRef.current) {
      onGhostDialogue?.({
        npc: event.data.npc, text: event.data.text,
        can_claim: event.data.can_claim, weapon: event.data.weapon, armor: event.data.armor,
      });
      // Quest was given (can_claim=false, no reward items present)
      if (!event.data.can_claim && !event.data.weapon && !event.data.armor) {
        onGhostQuestGiven?.();
      }
    }
    return true;
  }

  if (event.type === 'GHOST_REWARD') {
    if (event.data.player === myPlayerIdRef.current) {
      AudioManager.play('BOSS');
      onGhostQuestComplete?.();
    }
    return true;
  }

  if (event.type === 'GHOST_GEAR_OPEN') {
    if (event.data.player === myPlayerIdRef.current) {
      onGhostGearOpen?.(event.data);
    }
    return true;
  }

  if (event.type === 'COLLECT_DEW') {
    if (event.data.player === myPlayerIdRef.current) AudioManager.play('DEWDROP');
    return true;
  }

  if (event.type === 'SCROLL_SELECT_TARGET') {
    if (event.data.player === myPlayerIdRef.current) onScrollSelectTarget?.(event.data);
    return true;
  }

  if (event.type === 'STONE_SELECT_TARGET') {
    if (event.data.player === myPlayerIdRef.current) onStoneSelectTarget?.(event.data);
    return true;
  }

  if (event.type === 'STONE_INTUITION_PICK_ITEM') {
    if (event.data.player === myPlayerIdRef.current) onStoneIntuitionPickItem?.(event.data);
    return true;
  }

  if (event.type === 'STONE_INTUITION_GUESS_KIND') {
    if (event.data.player === myPlayerIdRef.current) onStoneIntuitionGuessKind?.(event.data);
    return true;
  }

  if (event.type === 'STONE_AUGMENT_PICK_ITEM') {
    if (event.data.player === myPlayerIdRef.current) onStoneAugmentPickItem?.(event.data);
    return true;
  }

  if (event.type === 'TALENT_METAMORPHED') {
    if (event.data.player === myPlayerIdRef.current) AudioManager.play('LEVELUP', 1.2);
    return true;
  }

  if (event.type === 'BOSS_SLAIN') {
    AudioManager.play('BOSS');
    onBossSlain?.(event.data);
    return true;
  }

  if (event.type === 'MESSAGE') {
    addGameLog(event.data.text, event.data.color || 'default');
    return true;
  }

  if (event.type === 'TOAST') {
    dispatchToast(event.data.text);
    return true;
  }

  if (event.type === 'ENCHANT_CHOICE_AVAILABLE') {
    if (event.data.player === myPlayerIdRef.current) {
      onEnchantChoiceAvailable?.({
        scroll_id: event.data.scroll_id,
        target_id: event.data.target_id,
        is_weapon: event.data.is_weapon,
        options: event.data.options,
      });
    }
    return true;
  }

  if (event.type === 'ENCHANT') {
    if (event.data.player === myPlayerIdRef.current) {
      AudioManager.play('LEVELUP', 1.3);
    }
    return true;
  }

  return false;
}
