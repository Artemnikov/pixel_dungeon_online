import { useTranslation } from 'react-i18next';
import WndBag from './WndBag';
import WndUseItem from './WndUseItem';
import RightClickMenu from './RightClickMenu';
import WndShop from './WndShop';
import WndImp from './WndImp';
import WndQuickBag from './WndQuickBag';
import RadialMenu from './RadialMenu';

const SCROLL_PICKER_KEYS = {
  scroll_of_upgrade: 'modal.upgrade',
  scroll_of_identify: 'modal.identify',
  scroll_of_remove_curse: 'modal.uncurse',
  scroll_of_transmutation: 'modal.transmute',
};

export default function GameModals({
  modals, itemsById, toolbarItems,
  belongings, gold, energy, strength,
  isDesktop,
  executeItemAction, assignQuickslot, sendSelectScrollTarget,
  send, handleToolbarClick,
}) {
  const { t } = useTranslation();
  const {
    useItemTarget, setUseItemTarget,
    ctxMenu, setCtxMenu,
    shopWindow, setShopWindow,
    impWindow, setImpWindow,
    showQuickBag, setShowQuickBag,
    radialOpen, setRadialOpen,
    quickslotPicker, setQuickslotPicker,
    scrollPickerData, setScrollPickerData,
    imbueWandData, setImbueWandData,
    openQuickslotPicker,
  } = modals;

  return (
    <>
      {useItemTarget && (
        <WndUseItem
          item={itemsById[useItemTarget.id] || useItemTarget}
          onAction={executeItemAction}
          onAssignQuickslot={assignQuickslot}
          onClose={() => setUseItemTarget(null)}
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
          title={t('modal.quickslot')}
          onSelectItem={(item) => {
            send({ type: 'SET_QUICKSLOT', index: quickslotPicker, item_id: item.id });
            setQuickslotPicker(null);
          }}
          onClose={() => setQuickslotPicker(null)}
        />
      )}

      {scrollPickerData && (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          selectMode
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
          itemFilter={(item) => imbueWandData.candidates.includes(item.id)}
          title={t('ui.chooseWandToImbue')}
          onSelectItem={(item) => {
            send({ type: 'CHOOSE_IMBUE_WAND', staff_id: imbueWandData.staff_id, wand_id: item.id });
            setImbueWandData(null);
          }}
          onClose={() => setImbueWandData(null)}
        />
      )}
    </>
  );
}
