import { useState, useRef, useLayoutEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import { CLERIC_SPELLS, isSpellUnlocked } from '../data/clericSpells';
import { getPopupPos, getSpellLabel, getSpellTitle } from './clericPickerUtils';
import useRegisterWindow from '../game/window/useRegisterWindow';
import { WindowLevel, WindowBackdrop } from '../game/window/WindowTypes';

const BAR_MAX_WIDTH = 820;

export default function WndClericCastBar({
  spellCooldowns = {},
  anchor = null,
  onCastSpell,
  onClose,
  myStats = {},
  belongings = {},
  setTargetingMode,
  onSetQuickSpell,
}) {
  const { t } = useTranslation();
  const barRef = useRef(null);
  const [barPos, setBarPos] = useState(() => getPopupPos(anchor, BAR_MAX_WIDTH));

  useLayoutEffect(() => {
    const updatePos = () => {
      const width = barRef.current?.offsetWidth || BAR_MAX_WIDTH;
      setBarPos(getPopupPos(anchor, width));
    };
    updatePos();
    window.addEventListener('resize', updatePos);
    return () => window.removeEventListener('resize', updatePos);
  }, [anchor]);

  const tome = useMemo(() => {
    if (belongings?.artifact?.kind === 'holy_tome') return belongings.artifact;
    if (belongings?.misc?.kind === 'holy_tome') return belongings.misc;
    if (belongings?.backpack?.items) {
      return belongings.backpack.items.find(it => it.kind === 'holy_tome') || null;
    }
    return null;
  }, [belongings]);

  const tomeCharge = tome?.charge ?? 3;
  const tomeChargeCap = tome?.charge_cap ?? 3;

  const unlockedSpells = useMemo(() => {
    return CLERIC_SPELLS.filter(spell => isSpellUnlocked(spell, {
      talentLevels: myStats?.talentLevels || {},
      subclass: myStats?.subclass || null,
      ascendedFormActive: myStats?.ascendedFormActive || false,
      poweredAllyId: myStats?.poweredAllyId || null,
    }));
  }, [myStats]);

  const handleSpellClick = useCallback((spell) => {
    const cd = spellCooldowns[spell.id] || 0;
    if (cd > 0) return;
    if (tomeCharge < spell.cost) return;

    AudioManager.play('CLICK');
    onClose?.();

    if (spell.targeting && spell.targeting !== 'none') {
      setTargetingMode?.({ clericSpell: spell.id });
    } else {
      onCastSpell?.(spell.id);
    }
  }, [spellCooldowns, tomeCharge, onClose, setTargetingMode, onCastSpell]);

  const digitActions = useMemo(() => {
    return unlockedSpells.map(spell => () => handleSpellClick(spell));
  }, [unlockedSpells, handleSpellClick]);

  useRegisterWindow({
    id: 'wnd-cleric-castbar',
    level: WindowLevel.SECONDARY,
    onClose,
    closeOnEscape: true,
    closeOnBackdrop: false,
    backdrop: WindowBackdrop.NONE,
    modal: false,
    digitActions,
  });

  const handleContextMenu = (e, spell) => {
    e.preventDefault();
    AudioManager.play('CLICK');
    onSetQuickSpell?.(spell.id);
  };

  return (
    <div
      ref={barRef}
      className="wnd-cleric-castbar wnd-cleric-surface"
      style={{
        position: 'fixed',
        left: `${barPos.left}px`,
        bottom: `${barPos.bottom}px`,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="wnd-cleric-header">
        <span>📖 Holy Tome</span>
        <div className="wnd-cleric-header-right">
          <span>⚡ {tomeCharge} / {tomeChargeCap}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="wnd-cleric-close-btn"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="wnd-cleric-spells">
        {unlockedSpells.map((spell, idx) => {
          const cd = spellCooldowns[spell.id] || 0;
          const notEnoughEnergy = tomeCharge < spell.cost;
          const onCd = cd > 0 || notEnoughEnergy;
          const isQuick = myStats?.clericQuickSpell === spell.id;
          const label = getSpellLabel(t, spell);
          const keyNumber = idx < 9 ? idx + 1 : null;

          return (
            <button
              key={spell.id}
              type="button"
              className={`wnd-cleric-cast-btn ${onCd ? 'on-cooldown' : 'ready'} ${isQuick ? 'is-quick-spell' : ''}`}
              onClick={() => handleSpellClick(spell)}
              onContextMenu={(e) => handleContextMenu(e, spell)}
              title={`${getSpellTitle(t, spell, cd)} (Cost: ⚡${spell.cost})${keyNumber ? ` [Key: ${keyNumber}]` : ''} - Right-click to set Quick-Cast`}
              style={{ position: 'relative' }}
            >
              {keyNumber && <span className="wnd-cleric-cast-key">{keyNumber}</span>}
              <span className="wnd-cleric-cast-icon">{spell.icon}</span>
              <span className="wnd-cleric-cast-name">{label}</span>
              <span style={{ fontSize: '9px', opacity: 0.8, marginLeft: '3px' }}>⚡{spell.cost}</span>
              {onCd && cd > 0 && <span className="wnd-cleric-cast-cd">{Math.ceil(cd)}s</span>}
              {isQuick && <span style={{ position: 'absolute', top: -2, right: 2, fontSize: '8px', color: '#ffd700' }}>★</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
