import { useTranslation } from 'react-i18next';
import { findTalentDef } from '../game/talents/talentQueries';

export default function RankingsPane({
  playerName,
  classType,
  level,
  depth,
  gold,
  subclass,
  armorAbility,
  talentLevels,
  talentDefs,
  inventory,
  onNewGame,
  onMenu,
  onClose,
}) {
  const { t } = useTranslation();
  const score = depth * 100 + level * 50 + gold * 2;

  const ownedTalents = Object.entries(talentLevels || {})
    .filter(([, lvl]) => lvl > 0)
    .sort(([a], [b]) => {
      const ta = talentDefs?.tiers ? findTier(a, talentDefs) : 0;
      const tb = talentDefs?.tiers ? findTier(b, talentDefs) : 0;
      return (ta - tb) || a.localeCompare(b);
    });

  function findTier(tid, defs) {
    return findTalentDef(defs, tid)?.tier ?? 0;
  }

  function talentName(tid) {
    const found = findTalentDef(talentDefs, tid);
    return found?.name || tid.replace(/_/g, ' ');
  }

  return (
    <div className="rankings-overlay" onClick={onClose || (() => {})}>
      <div className="rankings-pane" onClick={e => e.stopPropagation()}>
        <h2 className="rankings-title">{t('rankings.title')}</h2>

        <div className="rankings-score">{t('rankings.pts', { score: score.toLocaleString() })}</div>

        <div className="rankings-stats">
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">{t('rankings.name')}</span>
            <span className="rankings-stat-value">{playerName}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">{t('rankings.class')}</span>
            <span className="rankings-stat-value">{classType} {subclass || ''}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">{t('rankings.depth')}</span>
            <span className="rankings-stat-value">{depth}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">{t('rankings.level')}</span>
            <span className="rankings-stat-value">{level}</span>
          </div>
          <div className="rankings-stat-row">
            <span className="rankings-stat-label">{t('rankings.gold')}</span>
            <span className="rankings-stat-value">{gold}</span>
          </div>
          {armorAbility && (
            <div className="rankings-stat-row">
              <span className="rankings-stat-label">{t('rankings.armorAbility')}</span>
              <span className="rankings-stat-value">{armorAbility.replace(/_/g, ' ')}</span>
            </div>
          )}
        </div>

        <h3 className="rankings-section-title">{t('rankings.talents')}</h3>
        <div className="rankings-talents">
          {ownedTalents.length === 0 && (
            <div className="rankings-empty">{t('rankings.noTalents')}</div>
          )}
          {ownedTalents.map(([tid, lvl]) => (
            <div key={tid} className="rankings-talent-row">
              <span className="rankings-talent-name">{talentName(tid)}</span>
              <span className="rankings-talent-level">{'★'.repeat(lvl)}</span>
            </div>
          ))}
        </div>

        <h3 className="rankings-section-title">{t('rankings.items')}</h3>
        <div className="rankings-items">
          {(inventory || []).length === 0 && (
            <div className="rankings-empty">{t('rankings.noItems')}</div>
          )}
          {(inventory || []).slice(0, 20).map((item, i) => (
            <div key={i} className="rankings-item-row">
              {item.name}
            </div>
          ))}
        </div>

        <div className="rankings-buttons">
          <button className="rankings-btn" onClick={onNewGame}>{t('game.newGame')}</button>
          <button className="rankings-btn" onClick={onMenu}>{t('game.menuBtn')}</button>
          {onClose && (
            <button className="rankings-btn" onClick={onClose}>{t('ui.close', 'Close')}</button>
          )}
        </div>
      </div>
    </div>
  );
}
