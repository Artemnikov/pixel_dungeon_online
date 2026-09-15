import { useTranslation } from 'react-i18next';

export default function DuelistFinisherButton({
  classType,
  weaponCharge = 0,
  finisherReady = false,
  onDuelistFinisher,
}) {
  const { t } = useTranslation();
  if (classType !== 'duelist' || (weaponCharge <= 0 && !finisherReady)) {
    return null;
  }

  const pct = Math.min(1, Math.max(0, weaponCharge / 100));

  return (
    <div className="duelist-btn-container">
      <button
        type="button"
        className={`duelist-btn ${finisherReady ? 'duelist-btn-ready' : ''}`}
        onClick={() => finisherReady && onDuelistFinisher?.()}
        disabled={!finisherReady}
        title={
          finisherReady
            ? t('combat.duelistFinisherReady', { defaultValue: 'Finisher Ready! Click to strike' })
            : t('combat.duelistChargePct', {
                defaultValue: `Weapon Charge: ${weaponCharge}%`,
                pct: weaponCharge,
              })
        }
      >
        <div className="duelist-btn-label">
          {finisherReady
            ? t('combat.duelistFinisher', { defaultValue: 'FINISHER' })
            : t('combat.duelistCharge', { defaultValue: 'CHARGE' })}
        </div>
        <div className="duelist-btn-bar">
          <div className="duelist-btn-fill" style={{ width: `${pct * 100}%` }} />
        </div>
      </button>
    </div>
  );
}
