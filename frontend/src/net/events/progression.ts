import { addGameLog, dispatchToast } from '../../ui/gameLogHelpers';
import type { GameEvent } from '../../types/contract';
import type { GameEventContext, IGameEventHandler } from './IGameEventHandler';

export function createProgressionEventHandlers(): IGameEventHandler[] {
  return [
    {
      eventType: 'LEVEL_UP',
      handle(event: Extract<GameEvent, { type: 'LEVEL_UP' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          addGameLog(`Level up! You are now level ${event.data.level}`, 'positive');
          ctx.ui.levelUp({
            level: event.data.level,
            tier_unlocked: event.data.tier_unlocked,
            talent_points: event.data.talent_points,
            can_choose_subclass: event.data.can_choose_subclass,
            can_choose_armor_ability: event.data.can_choose_armor_ability,
          });
        }
        return true;
      },
    },
    {
      eventType: 'SUBCLASS_CHOICE_AVAILABLE',
      handle(event: Extract<GameEvent, { type: 'SUBCLASS_CHOICE_AVAILABLE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.subclassChoiceAvailable({ options: event.data.options });
        }
        return true;
      },
    },
    {
      eventType: 'ARMOR_ABILITY_CHOICE_AVAILABLE',
      handle(event: Extract<GameEvent, { type: 'ARMOR_ABILITY_CHOICE_AVAILABLE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.armorAbilityChoiceAvailable({ options: event.data.options });
        }
        return true;
      },
    },
    {
      eventType: 'IMBUE_WAND_CHOICE_AVAILABLE',
      handle(event: Extract<GameEvent, { type: 'IMBUE_WAND_CHOICE_AVAILABLE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.imbueWandChoiceAvailable({ staff_id: event.data.staff_id, candidates: event.data.candidates });
        }
        return true;
      },
    },
    {
      eventType: 'IMBUE_WAND_DONE',
      handle(event: Extract<GameEvent, { type: 'IMBUE_WAND_DONE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('CLICK');
          addGameLog('Your wand has been imbued into the staff', 'positive');
        }
        return true;
      },
    },
    {
      eventType: 'TALENT_UPGRADED',
      handle(event: Extract<GameEvent, { type: 'TALENT_UPGRADED' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('LEVELUP', 1.2);
          ctx.effects.playTalentUpgrade(event.data.talent);
        }
        return true;
      },
    },
    {
      eventType: 'METAMORPH_OPEN',
      handle(event: Extract<GameEvent, { type: 'METAMORPH_OPEN' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.metamorphOpen();
        }
        return true;
      },
    },
    {
      eventType: 'METAMORPH_OPTIONS',
      handle(event: Extract<GameEvent, { type: 'METAMORPH_OPTIONS' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.metamorphOptions(event.data);
        }
        return true;
      },
    },
    {
      eventType: 'SHOP_OPEN',
      handle(event: Extract<GameEvent, { type: 'SHOP_OPEN' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.shopOpen({ npc: event.data.npc, stock: event.data.stock, gold: event.data.gold });
        }
        return true;
      },
    },
    {
      eventType: 'SHOP_BUY',
      handle(event: Extract<GameEvent, { type: 'SHOP_BUY' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.audio.play('GOLD');
        return true;
      },
    },
    {
      eventType: 'SHOP_SELL',
      handle(event: Extract<GameEvent, { type: 'SHOP_SELL' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.audio.play('GOLD');
        return true;
      },
    },
    {
      eventType: 'IMP_DIALOGUE',
      handle(event: Extract<GameEvent, { type: 'IMP_DIALOGUE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.impDialogue({
            npc: event.data.npc,
            text: event.data.text,
            can_claim: event.data.can_claim,
            tokens: event.data.tokens,
          });
        }
        return true;
      },
    },
    {
      eventType: 'IMP_REWARD',
      handle(event: Extract<GameEvent, { type: 'IMP_REWARD' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.audio.play('BOSS');
        return true;
      },
    },
    {
      eventType: 'GHOST_DIALOGUE',
      handle(event: Extract<GameEvent, { type: 'GHOST_DIALOGUE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.ghostDialogue({
            npc: event.data.npc,
            text: event.data.text,
            can_claim: event.data.can_claim,
            weapon: event.data.weapon,
            armor: event.data.armor,
          });
          if (!event.data.can_claim && !event.data.weapon && !event.data.armor) {
            ctx.ui.ghostQuestGiven();
          }
        }
        return true;
      },
    },
    {
      eventType: 'GHOST_QUEST_PROCESSED',
      handle(_event: Extract<GameEvent, { type: 'GHOST_QUEST_PROCESSED' }>, ctx: GameEventContext) {
        ctx.ui.ghostQuestProcessed();
        return true;
      },
    },
    {
      eventType: 'GHOST_REWARD',
      handle(event: Extract<GameEvent, { type: 'GHOST_REWARD' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('BOSS');
          ctx.ui.ghostQuestComplete();
        }
        return true;
      },
    },
    {
      eventType: 'WANDMAKER_DIALOGUE',
      handle(event: Extract<GameEvent, { type: 'WANDMAKER_DIALOGUE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.wandmakerDialogue({
            npc: event.data.npc,
            text: event.data.text,
            can_claim: event.data.can_claim,
            wand1: event.data.wand1,
            wand2: event.data.wand2,
          });
        }
        return true;
      },
    },
    {
      eventType: 'WANDMAKER_REWARD',
      handle(event: Extract<GameEvent, { type: 'WANDMAKER_REWARD' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('CLICK');
        }
        return true;
      },
    },
    {
      eventType: 'GHOST_GEAR_OPEN',
      handle(event: Extract<GameEvent, { type: 'GHOST_GEAR_OPEN' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.ghostGearOpen(event.data);
        }
        return true;
      },
    },
    {
      eventType: 'COLLECT_DEW',
      handle(event: Extract<GameEvent, { type: 'COLLECT_DEW' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.audio.play('DEWDROP');
        return true;
      },
    },
    {
      eventType: 'SCROLL_SELECT_TARGET',
      handle(event: Extract<GameEvent, { type: 'SCROLL_SELECT_TARGET' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.ui.scrollSelectTarget(event.data);
        return true;
      },
    },
    {
      eventType: 'STONE_SELECT_TARGET',
      handle(event: Extract<GameEvent, { type: 'STONE_SELECT_TARGET' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.ui.stoneSelectTarget(event.data);
        return true;
      },
    },
    {
      eventType: 'STONE_INTUITION_PICK_ITEM',
      handle(event: Extract<GameEvent, { type: 'STONE_INTUITION_PICK_ITEM' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.ui.stoneIntuitionPickItem(event.data);
        return true;
      },
    },
    {
      eventType: 'STONE_INTUITION_GUESS_KIND',
      handle(event: Extract<GameEvent, { type: 'STONE_INTUITION_GUESS_KIND' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.ui.stoneIntuitionGuessKind(event.data);
        return true;
      },
    },
    {
      eventType: 'STONE_AUGMENT_PICK_ITEM',
      handle(event: Extract<GameEvent, { type: 'STONE_AUGMENT_PICK_ITEM' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.ui.stoneAugmentPickItem(event.data);
        return true;
      },
    },
    {
      eventType: 'TALENT_METAMORPHED',
      handle(event: Extract<GameEvent, { type: 'TALENT_METAMORPHED' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) ctx.audio.play('LEVELUP', 1.2);
        return true;
      },
    },
    {
      eventType: 'BOSS_SLAIN',
      handle(event: Extract<GameEvent, { type: 'BOSS_SLAIN' }>, ctx: GameEventContext) {
        ctx.audio.play('BOSS');
        ctx.ui.bossSlain(event.data);
        return true;
      },
    },
    {
      eventType: 'MESSAGE',
      handle(event: Extract<GameEvent, { type: 'MESSAGE' }>) {
        addGameLog(event.data.text, event.data.color || 'default');
        return true;
      },
    },
    {
      eventType: 'TOAST',
      handle(event: Extract<GameEvent, { type: 'TOAST' }>) {
        dispatchToast(event.data.text);
        return true;
      },
    },
    {
      eventType: 'ENCHANT_CHOICE_AVAILABLE',
      handle(event: Extract<GameEvent, { type: 'ENCHANT_CHOICE_AVAILABLE' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.ui.enchantChoiceAvailable({
            scroll_id: event.data.scroll_id,
            target_id: event.data.target_id,
            is_weapon: event.data.is_weapon,
            options: event.data.options,
          });
        }
        return true;
      },
    },
    {
      eventType: 'ENCHANT',
      handle(event: Extract<GameEvent, { type: 'ENCHANT' }>, ctx: GameEventContext) {
        if (event.data.player === ctx.myPlayerId) {
          ctx.audio.play('LEVELUP', 1.3);
        }
        return true;
      },
    },
  ];
}
