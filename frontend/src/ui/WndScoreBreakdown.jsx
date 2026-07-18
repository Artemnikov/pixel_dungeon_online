import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';

// SPD WndScoreBreakdown.java port: detailed score breakdown with categories
// (progress, treasure, explore, boss, quest), multipliers, and total.
// Replaces the 3-row stub in GameOverScreen/VictoryScreen.
export default function WndScoreBreakdown({ scoreBreakdown, onClose }) {
  const { t } = useTranslation();
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!scoreBreakdown) return null;

  const categories = [
    { key: 'progress', score: scoreBreakdown.progress_score, desc: t('score.progress.desc') },
    { key: 'treasure', score: scoreBreakdown.treasure_score, desc: t('score.treasure.desc') },
    { key: 'explore', score: scoreBreakdown.explore_score, desc: t('score.explore.desc') },
    { key: 'bosses', score: scoreBreakdown.boss_score, desc: t('score.bosses.desc') },
    { key: 'quests', score: scoreBreakdown.quest_score, desc: t('score.quests.desc') },
  ].filter(c => c.score != null);

  const mults = [];
  if (scoreBreakdown.win_multiplier && scoreBreakdown.win_multiplier > 1)
    mults.push({ label: t('score.winMultiplier'), value: `${scoreBreakdown.win_multiplier.toFixed(2)}x` });
  if (scoreBreakdown.challenge_multiplier && scoreBreakdown.challenge_multiplier > 1)
    mults.push({ label: t('score.challengeMultiplier'), value: `${scoreBreakdown.challenge_multiplier.toFixed(2)}x` });
  if (scoreBreakdown.respawn_multiplier != null && scoreBreakdown.respawn_multiplier < 1)
    mults.push({ label: t('score.respawnMultiplier'), value: `${scoreBreakdown.respawn_multiplier.toFixed(2)}x` });
  if (scoreBreakdown.witness_multiplier != null && scoreBreakdown.witness_multiplier < 1)
    mults.push({ label: t('score.witnessMultiplier'), value: `${scoreBreakdown.witness_multiplier.toFixed(2)}x` });

  return (
    <div className="wnd-overlay" onClick={onClose}>
      <div className="wnd-info-card" onClick={(e) => e.stopPropagation()}>
        <IconTitle
          icon={<div style={{ width: 16, height: 16, background: '#4a6a9a' }} />}
          title={t('score.title')}
        />
        <div className="wnd-score-categories">
          {categories.map(c => (
            <div key={c.key} className="wnd-score-cat">
              <div className="wnd-score-cat-header">
                <span className="wnd-score-cat-label">{t(`score.${c.key}.title`)}</span>
                <span className="wnd-score-cat-value">{(c.score || 0).toLocaleString()}</span>
              </div>
              <div className="wnd-score-cat-desc">{c.desc}</div>
            </div>
          ))}
        </div>
        {mults.length > 0 && (
          <div className="wnd-score-mults">
            {mults.map((m, i) => (
              <div key={i} className="wnd-score-cat-header">
                <span className="wnd-score-cat-label">{m.label}</span>
                <span className="wnd-score-cat-value">{m.value}</span>
              </div>
            ))}
          </div>
        )}
        <div className="wnd-score-total">
          <span>{t('score.total')}</span>
          <span>{(scoreBreakdown.total_score || 0).toLocaleString()}</span>
        </div>
        <div className="wnd-info-stats">
          <div className="wnd-info-stat-row">{t('game.score.kills', 'Enemies slain')}: {scoreBreakdown.kills}</div>
          <div className="wnd-info-stat-row">{t('game.score.floors', 'Floors explored')}: {scoreBreakdown.floors}</div>
          <div className="wnd-info-stat-row">{t('game.score.gold', 'Gold collected')}: {scoreBreakdown.gold}</div>
        </div>
        <button className="wnd-close-btn" onClick={onClose}>{t('ui.close')}</button>
      </div>
    </div>
  );
}
