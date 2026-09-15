import { memo } from 'react';
import Toolbar from './Toolbar';
import InventoryPane from './InventoryPane';
import WndBag from './WndBag';
import AbilityButton from './AbilityButton';
import BerserkButton from './BerserkButton';
import PrepStrikeButton from './PrepStrikeButton';
import ComboDisplay from './ComboDisplay';
import DuelistFinisherButton from './DuelistFinisherButton';

function GameHud({
  interfaceSize, isDesktop, canvasWidth,
  toolbarItems, equippedItems, targetingMode,
  swappedQuickslots, showInventory,
  belongings, gold, energy, strength, myStats,
  assetImages,
  onSearch, onInventory, onQuickBag, onSwap,
  onSlotClick, onSlotDoubleClick, onSlotLongPress, onSlotContextMenu,
  onUseAbility, onTriggerBerserk, onPrepStrike, onUseComboMove,
  onDuelistFinisher,
  onOpenItem, onContextMenu, onDefaultAction,
  onCloseInventory,
  onLayout,
}) {
  return (
    <div className="hud-bottom">
      <Toolbar
        mode={interfaceSize > 0 ? 'group' : 'split'}
        interfaceSize={interfaceSize}
        flipToolbar={false}
        quickSwapper={!isDesktop}
        canvasWidth={canvasWidth}
        items={toolbarItems}
        equippedItems={equippedItems}
        targetingMode={targetingMode}
        swappedQuickslots={swappedQuickslots}
        assetImages={assetImages}
        onSearch={onSearch}
        onInventory={onInventory}
        onQuickBag={onQuickBag}
        onSlotClick={onSlotClick}
        onSlotDoubleClick={onSlotDoubleClick}
        onSlotLongPress={onSlotLongPress}
        onSlotContextMenu={onSlotContextMenu}
        onSwap={onSwap}
        onLayout={onLayout}
      />
      <AbilityButton
        armorAbility={myStats.armorAbility || null}
        armorCharge={myStats.armorCharge || 0}
        onUseAbility={onUseAbility}
      />
      <BerserkButton
        berserkPower={myStats.berserkPower || 0}
        onTriggerBerserk={onTriggerBerserk}
      />
      <PrepStrikeButton
        subclass={myStats.subclass}
        invisible={myStats.invisible || 0}
        prepSeconds={myStats.prepSeconds || 0}
        onPrepStrike={onPrepStrike}
      />
      <ComboDisplay
        subclass={myStats.subclass}
        comboCount={myStats.comboCount || 0}
        onUseComboMove={onUseComboMove}
      />
      <DuelistFinisherButton
        classType={myStats.classType}
        weaponCharge={myStats.weaponCharge || 0}
        finisherReady={!!myStats.finisherReady}
        onDuelistFinisher={onDuelistFinisher}
      />
      {showInventory && (isDesktop ? (
        <InventoryPane
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          onOpenItem={onOpenItem}
          onContextMenu={onContextMenu}
          onDefaultAction={onDefaultAction}
        />
      ) : (
        <WndBag
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          onOpenItem={onOpenItem}
          onContextMenu={onContextMenu}
          onDefaultAction={onDefaultAction}
          onClose={onCloseInventory}
        />
      ))}
    </div>
  );
}

export default memo(GameHud);
