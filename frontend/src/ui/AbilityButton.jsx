import { useTranslation } from 'react-i18next';

const ABILITY_COSTS = {
  heroic_leap: 30,
  shockwave: 30,
  endure: 15,
  smoke_bomb: 50,
  death_mark: 25,
  shadow_clone: 35,
};

export default function AbilityButton({
  armorAbility,
  armorCharge,
  onUseAbility,
}) {
  const { t } = useTranslation();
  if (!armorAbility) return null;

  const cost = ABILITY_COSTS[armorAbility] || 30;
  const pct = Math.min(1, armorCharge / (cost || 1));
  const label = t(`ability.${armorAbility}.name`, { defaultValue: armorAbility });

  return (
    <div className="ability-btn-container">
      <button
        type="button"
        className={`ability-btn ${pct >= 1 ? 'ability-btn-ready' : ''}`}
        onClick={() => onUseAbility?.(armorAbility)}
        title={t('combat.chargePct', { label, pct: Math.round(pct * 100) })}
      >
        <div className="ability-btn-label">{label}</div>
        <div className="ability-btn-charge-bar">
          <div className="ability-btn-charge-fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </button>
    </div>
  );
}
