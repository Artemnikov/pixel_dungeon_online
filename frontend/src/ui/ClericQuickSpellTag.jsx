import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import AudioManager from '../audio/AudioManager';
import { getClericSpell } from '../data/clericSpells';

function ClericQuickSpellTag({ myStats, onCastSpell, setTargetingMode }) {
  const { t } = useTranslation();
  if (myStats?.classType !== 'cleric' || !myStats?.clericQuickSpell) {
    return null;
  }

  const spell = getClericSpell(myStats.clericQuickSpell);
  if (!spell) return null;

  const cd = myStats.spellCooldowns?.[spell.id] || 0;
  const onCd = cd > 0;
  const label = t(`spells.${spell.id}.name`, { defaultValue: spell.label });
  const title = onCd
    ? `${label} (${Math.ceil(cd)}s)`
    : `${label} (Quick Cast)`;

  return (
    <div
      className={`side-tag side-tag--cleric ${onCd ? 'on-cooldown' : 'ready'}`}
      style={{ borderColor: onCd ? '#556677' : '#e0a924' }}
      onClick={() => {
        if (!onCd) {
          AudioManager.play('CLICK');
          if (spell.targeting && spell.targeting !== 'none') {
            setTargetingMode?.({ clericSpell: spell.id });
          } else {
            onCastSpell?.(spell.id);
          }
        }
      }}
      title={title}
    >
      <span className="side-tag-icon" style={{ fontSize: 16 }}>{spell.icon}</span>
      {onCd && (
        <span className="side-tag-cd">{Math.ceil(cd)}</span>
      )}
    </div>
  );
}

export default memo(ClericQuickSpellTag);
