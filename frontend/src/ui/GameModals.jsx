import { useState, memo } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import WndBag from './WndBag';
import WndUseItem from './WndUseItem';
import WndInfoItem from './WndInfoItem';
import WndJournal from './WndJournal';
import RightClickMenu from './RightClickMenu';
import WndShop from './WndShop';
import WndImp from './WndImp';
import WndSadGhost from './WndSadGhost';
import WndGhostGear from './WndGhostGear';
import WndChasmJump from './WndChasmJump';
import WndQuickBag from './WndQuickBag';
import RadialMenu from './RadialMenu';

import WndStoneIntuition from './WndStoneIntuition';
import WndStoneAugment from './WndStoneAugment';
import WndChooseEnchant from './WndChooseEnchant';
import AlchemyOverlay from './AlchemyOverlay';
import WndTrinketChoice from './WndTrinketChoice';

const SCROLL_PICKER_KEYS = {
  scroll_of_upgrade: 'modal.upgrade',
  scroll_of_identify: 'modal.identify',
  scroll_of_remove_curse: 'modal.uncurse',
  scroll_of_transmutation: 'modal.transmute',
};

function GameModals({
  modals, itemsById, toolbarItems,
  belongings, gold, energy, strength,
  isDesktop, depth,
  executeItemAction, assignQuickslot, sendSelectScrollTarget, sendStoneTarget,
  send, handleToolbarClick,
}) {
  const { t } = useTranslation();
  const [ghostEquipSlot, setGhostEquipSlot] = useState(null);
  const [inspectItem, setInspectItem] = useState(null);
  const [journalOpen, setJournalOpen] = useState(false);
  const {
    useItemTarget, setUseItemTarget,
    ctxMenu, setCtxMenu,
    shopWindow, setShopWindow,
    impWindow, setImpWindow,
    ghostWindow, setGhostWindow,
    ghostGearData, setGhostGearData,
    chasmPrompt, setChasmPrompt,
    showQuickBag, setShowQuickBag,
    radialOpen, setRadialOpen,
    quickslotPicker, setQuickslotPicker,
    scrollPickerData, setScrollPickerData,
    stonePickerData, setStonePickerData,
    intuitionData, setIntuitionData,
    intuitionGuessData, setIntuitionGuessData,
    augmentSelectData, setAugmentSelectData,
    enchantChoiceData, setEnchantChoiceData,
    imbueWandData, setImbueWandData,
    openQuickslotPicker,
    alchemyOpen, setAlchemyOpen,
    alchemyPreview, setAlchemyPreview,
    alchemyBrewed, setAlchemyBrewed,
    trinketChoice, setTrinketChoice,
    toolkitEnergize, setToolkitEnergize,
  } = modals;

  return (
    <>
      {useItemTarget && (
        <WndUseItem
          item={itemsById[useItemTarget.id] || useItemTarget}
          belongings={belongings}
          onAction={executeItemAction}
          onAssignQuickslot={assignQuickslot}
          onClose={() => setUseItemTarget(null)}
          onOpenJournal={() => { setUseItemTarget(null); setJournalOpen(true); }}
        />
      )}

      {ctxMenu && (
        <RightClickMenu
          item={itemsById[ctxMenu.item.id] || ctxMenu.item}
          x={ctxMenu.x}
          y={ctxMenu.y}
          onAction={executeItemAction}
          onAssignQuickslot={assignQuickslot}
          onClose={() => setCtxMenu(null)}
        />
      )}

      {shopWindow && (
        <WndShop
          npcId={shopWindow.npc}
          stock={shopWindow.stock}
          gold={gold}
          backpackItems={Object.values(itemsById)}
          onBuy={(npcId, itemId) => {
            send({ type: 'SHOP_BUY', npc_id: npcId, item_id: itemId });
            setShopWindow(w => w && { ...w, stock: w.stock.filter(i => i.id !== itemId) });
          }}
          onSell={(itemId) => send({ type: 'SHOP_SELL', item_id: itemId })}
          onClose={() => setShopWindow(null)}
        />
      )}

      {impWindow && (
        <WndImp
          npcId={impWindow.npc}
          text={impWindow.text}
          canClaim={impWindow.canClaim}
          onClaim={(npcId) => {
            send({ type: 'IMP_CLAIM_REWARD', npc_id: npcId });
            setImpWindow(null);
          }}
          onClose={() => setImpWindow(null)}
        />
      )}

      {ghostWindow && (
        <WndSadGhost
          npcId={ghostWindow.npc}
          text={ghostWindow.text}
          canClaim={ghostWindow.canClaim}
          weapon={ghostWindow.weapon}
          armor={ghostWindow.armor}
          onChoose={(npcId, choice) => {
            send({ type: 'GHOST_CLAIM_REWARD', npc_id: npcId, choice });
            setGhostWindow(null);
          }}
          onClose={() => setGhostWindow(null)}
        />
      )}

      {ghostGearData && !ghostEquipSlot && (
        <WndGhostGear
          ghostHp={ghostGearData.ghost_hp}
          ghostMaxHp={ghostGearData.ghost_max_hp}
          weapon={ghostGearData.weapon}
          armor={ghostGearData.armor}
          onEquip={(slot) => setGhostEquipSlot(slot)}
          onUnequip={(slot) => {
            send({ type: 'EQUIP_GHOST_ITEM', rose_id: ghostGearData.rose_id, slot });
          }}
          onClose={() => setGhostGearData(null)}
        />
      )}

      {chasmPrompt && (
        <WndChasmJump
          onConfirm={() => {
            send({ type: 'CONFIRM_CHASM_FALL', x: chasmPrompt.x, y: chasmPrompt.y });
            setChasmPrompt(null);
          }}
          onDecline={() => setChasmPrompt(null)}
        />
      )}

      {ghostGearData && ghostEquipSlot && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          onInspectItem={setInspectItem}
          itemFilter={(item) => item.type === ghostEquipSlot}
          title={t(ghostEquipSlot === 'weapon' ? 'ghostGear.selectWeapon' : 'ghostGear.selectArmor')}
          onSelectItem={(item) => {
            send({
              type: 'EQUIP_GHOST_ITEM',
              rose_id: ghostGearData.rose_id,
              slot: ghostEquipSlot,
              item_id: item.id,
            });
            setGhostEquipSlot(null);
            setGhostGearData(null);
          }}
          onClose={() => setGhostEquipSlot(null)}
        />
      )}

      {showQuickBag && (
        <WndQuickBag
          belongings={belongings}
          onUse={(itemId, action) => executeItemAction(itemId, action)}
          onClose={() => setShowQuickBag(false)}
        />
      )}

      {radialOpen && (
        <RadialMenu
          items={toolbarItems}
          size={isDesktop ? 200 : 140}
          onSelect={(idx) => { handleToolbarClick(toolbarItems[idx]); }}
          onAssign={(idx) => openQuickslotPicker(idx)}
          onClose={() => setRadialOpen(false)}
        />
      )}

      {quickslotPicker !== null && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          onInspectItem={setInspectItem}
          title={t('modal.quickslot')}
          onSelectItem={(item) => {
            send({ type: 'SET_QUICKSLOT', index: quickslotPicker, item_id: item.id });
            setQuickslotPicker(null);
          }}
          onClose={() => setQuickslotPicker(null)}
          extraFooter={toolbarItems[quickslotPicker] ? (
            <button
              className="wnd-bag-clear-btn"
              onClick={() => {
                AudioManager.play('CLICK');
                send({ type: 'SET_QUICKSLOT', index: quickslotPicker });
                setQuickslotPicker(null);
              }}
            >
              {t('ui.clearQuickslot')}
            </button>
          ) : null}
        />
      )}

      {scrollPickerData && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          onInspectItem={setInspectItem}
          itemFilter={(item) => scrollPickerData.candidates.includes(item.id)}
          title={t(SCROLL_PICKER_KEYS[scrollPickerData.scroll_kind] ?? 'ui.chooseItem')}
          onSelectItem={(item) => {
            sendSelectScrollTarget(scrollPickerData.scroll_id, item.id);
            setScrollPickerData(null);
          }}
          onClose={() => setScrollPickerData(null)}
        />
      )}

      {imbueWandData && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          onInspectItem={setInspectItem}
          itemFilter={(item) => imbueWandData.candidates.includes(item.id)}
          title={t('ui.chooseWandToImbue')}
          onSelectItem={(item) => {
            send({ type: 'CHOOSE_IMBUE_WAND', staff_id: imbueWandData.staff_id, wand_id: item.id });
            setImbueWandData(null);
          }}
          onClose={() => setImbueWandData(null)}
        />
      )}

      {stonePickerData && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
          onInspectItem={setInspectItem}
          itemFilter={(item) => stonePickerData.candidates.includes(item.id)}
          title={t('ui.chooseItem')}
          onSelectItem={(item) => {
            sendStoneTarget(stonePickerData.stone_id, item.id);
            setStonePickerData(null);
          }}
          onClose={() => setStonePickerData(null)}
        />
      )}

      {intuitionData && (
        <WndStoneIntuition
          belongings={belongings}
          candidates={intuitionData.candidates}
          gold={gold}
          energy={energy}
          strength={strength}
          onPickItem={(itemId) => {
            send({ type: 'STONE_INTUITION_CHOOSE_ITEM', stone_id: intuitionData.stone_id, item_id: itemId });
            setIntuitionData(null);
          }}
          onClose={() => setIntuitionData(null)}
        />
      )}

      {intuitionGuessData && (
        <WndStoneIntuition
          belongings={belongings}
          pickMode="guess"
          possibleKinds={intuitionGuessData.possible_kinds}
          gold={gold}
          energy={energy}
          strength={strength}
          onGuess={(guessedKind) => {
            send({
              type: 'STONE_INTUITION_GUESS',
              stone_id: intuitionGuessData.stone_id,
              item_id: intuitionGuessData.item_id,
              guessed_kind: guessedKind,
            });
            setIntuitionGuessData(null);
          }}
          onClose={() => setIntuitionGuessData(null)}
        />
      )}

      {augmentSelectData && augmentSelectData.candidates && (
        <WndStoneAugment
          belongings={belongings}
          candidates={augmentSelectData.candidates}
          gold={gold}
          energy={energy}
          strength={strength}
          onChoose={(itemId, augmentType) => {
            send({ type: 'STONE_AUGMENT_CHOOSE', stone_id: augmentSelectData.stone_id, item_id: itemId, augment_type: augmentType });
            setAugmentSelectData(null);
          }}
          onClose={() => setAugmentSelectData(null)}
        />
      )}

      {enchantChoiceData && (
        <WndChooseEnchant
          options={enchantChoiceData.options}
          isWeapon={enchantChoiceData.is_weapon}
          onChoose={(choiceIndex) => {
            send({ type: 'CHOOSE_ENCHANT', target_id: enchantChoiceData.target_id, choice_index: choiceIndex });
            setEnchantChoiceData(null);
          }}
          onClose={() => setEnchantChoiceData(null)}
        />
      )}

      {alchemyOpen && (
        <AlchemyOverlay
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          itemsById={itemsById}
          preview={alchemyPreview}
          brewed={alchemyBrewed}
          send={send}
          onClose={() => {
            setAlchemyOpen(false);
            setAlchemyPreview(null);
            setAlchemyBrewed(null);
          }}
        />
      )}

      {trinketChoice && (
        <WndTrinketChoice
          kinds={trinketChoice.kinds}
          onChoose={(kind) => {
            send({ type: 'ALCHEMY_TRINKET_CHOOSE', catalyst_id: trinketChoice.catalyst_id, kind });
            setTrinketChoice(null);
          }}
          onClose={() => setTrinketChoice(null)}
        />
      )}

      {toolkitEnergize && (
        <div className="choice-modal-backdrop" onClick={() => setToolkitEnergize(null)}>
          <div className="choice-modal" onClick={e => e.stopPropagation()}>
            <h3>{t('alchemy.toolkitEnergize')}</h3>
            <button onClick={() => {
              send({ type: 'TOOLKIT_ENERGIZE', toolkit_id: toolkitEnergize.toolkit_id, levels: 1 });
              setToolkitEnergize(null);
            }}>
              {t('alchemy.toolkitEnergizeOne')}
            </button>
            {toolkitEnergize.max_levels > 1 && (
              <button onClick={() => {
                send({ type: 'TOOLKIT_ENERGIZE', toolkit_id: toolkitEnergize.toolkit_id, levels: toolkitEnergize.max_levels });
                setToolkitEnergize(null);
              }}>
                {t('alchemy.toolkitEnergizeAll', { cost: 6 * toolkitEnergize.max_levels, levels: toolkitEnergize.max_levels })}
              </button>
            )}
            <button onClick={() => setToolkitEnergize(null)}>{t('alchemy.cancel')}</button>
          </div>
        </div>
      )}

      {inspectItem && (
        <div className="wnd-overlay" onClick={() => setInspectItem(null)}>
          <div className="wnd-item" onClick={(e) => e.stopPropagation()}>
            <WndInfoItem item={itemsById[inspectItem.id] || inspectItem} belongings={belongings} />
          </div>
        </div>
      )}

      {journalOpen && (
        <WndJournal depth={depth} onClose={() => setJournalOpen(false)} />
      )}
    </>
  );
}

export default memo(GameModals);
