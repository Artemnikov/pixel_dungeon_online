import AudioManager from '../audio/AudioManager';
import InventoryPane from './InventoryPane';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';

export default function WndBag({
  belongings, gold, energy, strength, myStats, onOpenItem, onContextMenu,
  onDefaultAction, onClose, selectMode, onSelectItem, itemFilter,
  title, extraFooter, onInspectItem,
}) {
  const level = selectMode ? WindowLevel.SECONDARY : WindowLevel.BASE;

  return (
    <WndOverlay
      id={selectMode ? 'wnd-bag-select' : 'wnd-bag'}
      level={level}
      onClose={onClose}
      className="wnd-bag-overlay"
    >
      <div className="wnd-bag" onClick={(e) => e.stopPropagation()}>
        <button
          className="wnd-bag-close"
          onClick={() => { AudioManager.play('CLICK'); onClose(); }}
          aria-label="Close inventory"
        >
          ✕
        </button>
        <InventoryPane
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={strength}
          myStats={myStats}
          prompt={title}
          onOpenItem={onOpenItem}
          onContextMenu={onContextMenu}
          onDefaultAction={onDefaultAction}
          selectMode={selectMode}
          onSelectItem={onSelectItem}
          itemFilter={itemFilter}
          onInspect={onInspectItem}
        />
        {extraFooter}
      </div>
    </WndOverlay>
  );
}
