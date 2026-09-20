import { useTranslation } from 'react-i18next';
import { WeaponSkillRegistry } from '../data/weaponSkills';

export default function DuelistFinisherButton({
  classType,
  weaponCharge = 0,
  maxWeaponCharges,
  finisherReady = false,
  equippedWeapon,
  effects,
  subclass,
  onDuelistFinisher,
}) {
  const { t } = useTranslation();
  if (classType !== 'duelist') {
    return null;
  }

  const maxCharges = maxWeaponCharges || (subclass === 'champion' ? 4 : 2);
  const context = { classType, weaponCharge, maxWeaponCharges: maxCharges, effects, subclass };
  const skill = WeaponSkillRegistry.getSkillForWeapon(equippedWeapon);
  const skillName = skill
    ? t(`skills.${skill.id}.name`, { defaultValue: skill.name })
    : t('combat.duelistFinisher', { defaultValue: 'FINISHER' });
  const usageCount = skill ? skill.getUsageCount(weaponCharge, equippedWeapon, context) : Math.floor(weaponCharge);
  const ready = skill ? skill.isReady(weaponCharge, equippedWeapon, context) : (weaponCharge >= 1.0 || finisherReady);

  const pct = Math.min(1, Math.max(0, maxCharges > 0 ? weaponCharge / maxCharges : 0));
  const statusText = skill ? skill.formatStatus(weaponCharge, maxCharges, equippedWeapon, context) : `${Math.floor(weaponCharge)}/${maxCharges}`;

  const usageLabel = t('ui.weaponSkillUsage', { count: usageCount, defaultValue: `${usageCount} uses` });
  const buttonTitle = ready
    ? `${skillName} (${usageLabel}, ${statusText}) - ${t('combat.duelistFinisherReady', { defaultValue: 'Click target to strike' })}`
    : `${skillName} (${statusText}) - ${t('combat.duelistCharge', { defaultValue: 'Charging' })}`;

  return (
    <div className="duelist-btn-container">
      <button
        type="button"
        className={`duelist-btn ${ready ? 'duelist-btn-ready' : ''}`}
        onClick={() => ready && onDuelistFinisher?.()}
        disabled={!ready}
        title={buttonTitle}
      >
        <div className="duelist-btn-label">
          {skillName.toUpperCase()}
          <span className="duelist-btn-count" style={{ fontSize: '9px', color: '#f1c40f', marginLeft: '4px' }}>
            ({statusText})
          </span>
        </div>
        <div className="duelist-btn-bar">
          <div className="duelist-btn-fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </button>
    </div>
  );
}
