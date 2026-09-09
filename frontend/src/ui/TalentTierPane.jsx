import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import TalentButton from './TalentButton';
import WndOptions from './WndOptions';

export default function TalentTierPane({
  tier,
  talents,
  talentLevels,
  talentPoints,
  subclass,
  armorAbility,
  effects,
  onUpgradeTalent,
  onInfo,
  metamorphMode,
  onMetamorphChoose,
}) {
  const { t } = useTranslation();
  const [showShuffle, setShowShuffle] = useState(false);

  const ptsAvailable = talentPoints?.[tier] || 0;

  function isTalentLocked(t) {
    if (t.subclass && t.subclass !== subclass) return true;
    if (t.ability && t.ability !== armorAbility) return true;
    return false;
  }

  const handleShuffleAll = useCallback(() => {
    let remaining = talentPoints?.[tier] || 0;
    let attempts = 0;
    while (remaining > 0 && attempts < 100) {
      const unlocked = talents.filter(t => {
        if (t.subclass && t.subclass !== subclass) return false;
        if (t.ability && t.ability !== armorAbility) return false;
        return (talentLevels?.[t.id] || 0) < t.max_pts;
      });
      if (unlocked.length === 0) break;
      const pick = unlocked[Math.floor(Math.random() * unlocked.length)];
      onUpgradeTalent?.(pick.id);
      remaining--;
      attempts++;
    }
  }, [tier, talents, talentLevels, talentPoints, onUpgradeTalent, subclass, armorAbility]);

  const handleShuffleOne = useCallback(() => {
    const unlocked = talents.filter(t => {
      if (t.subclass && t.subclass !== subclass) return false;
      if (t.ability && t.ability !== armorAbility) return false;
      return (talentLevels?.[t.id] || 0) < t.max_pts;
    });
    if (unlocked.length === 0) return;
    const pick = unlocked[Math.floor(Math.random() * unlocked.length)];
    onUpgradeTalent?.(pick.id);
  }, [talents, talentLevels, onUpgradeTalent, subclass, armorAbility]);

  return (
    <div className="tier-pane">
      {!metamorphMode && (
        <div className="tier-pane-header">
          <div className="tier-title">{t('talent.tier', { tier })}</div>
          {ptsAvailable > 0 && (
            <span className="tier-pts-badge">{ptsAvailable}</span>
          )}
          {ptsAvailable > 0 && (
            <button
              className="tier-random-btn"
              title={t('talent.randomTooltip')}
              onClick={() => setShowShuffle(true)}
            >
              ↻
            </button>
          )}
        </div>
      )}
      <div className="tier-buttons">
        {talents.map((t) => {
          const locked = isTalentLocked(t);
          const currentLevel = talentLevels?.[t.id] || 0;
          return (
            <TalentButton
              key={t.id}
              talentId={t.id}
              name={t.name || t.id}
              currentLevel={currentLevel}
              maxPoints={t.max_pts}
              pointsAvailable={ptsAvailable}
              locked={locked || (metamorphMode && currentLevel === 0)}
              onInfo={onInfo}
              effects={effects}
              metamorphMode={metamorphMode}
              onMetamorphChoose={onMetamorphChoose}
            />
          );
        })}
      </div>

      {showShuffle && (
        <WndOptions
          icon="↻"
          title={t('talent.randomTitle')}
          message={t('talent.randomMsg')}
          options={[t('talent.fillAll'), t('talent.fillOne'), t('talent.cancel')]}
          onSelect={(idx) => {
            if (idx === 0) handleShuffleAll();
            else if (idx === 1) handleShuffleOne();
          }}
          onClose={() => setShowShuffle(false)}
        />
      )}
    </div>
  );
}
