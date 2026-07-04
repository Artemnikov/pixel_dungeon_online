import { useTranslation } from 'react-i18next';
import styles from './WndGhostGear.module.css';

export default function WndGhostGear({
  ghostHp, ghostMaxHp,
  weapon, armor,
  onEquip, onUnequip,
  onClose,
}) {
  const { t } = useTranslation();

  const hpPct = ghostMaxHp > 0 ? Math.round(ghostHp / ghostMaxHp * 100) : 0;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.window} onClick={e => e.stopPropagation()}>
        <h2 className={styles.title}>{t('ghostGear.title')}</h2>

        <div className={styles.hpBar}>
          <div className={styles.hpBarFill} style={{ width: `${hpPct}%` }} />
          <span className={styles.hpText}>HP {ghostHp}/{ghostMaxHp}</span>
        </div>

        <div className={styles.slot}>
          <label>{t('ghostGear.weapon')}</label>
          {weapon ? (
            <div className={styles.itemRow}>
              <span className={styles.itemName}>{weapon.name}</span>
              <span className={styles.itemStats}>
                T{weapon.tier} {weapon.damage_min}-{weapon.damage_max}
              </span>
              <button className={styles.actionBtn} onClick={() => onUnequip('weapon')}>
                {t('ghostGear.remove')}
              </button>
            </div>
          ) : (
            <div className={styles.itemRow}>
              <span className={styles.emptySlot}>{t('ghostGear.none')}</span>
              <button className={styles.actionBtn} onClick={() => onEquip('weapon')}>
                {t('ghostGear.equip')}
              </button>
            </div>
          )}
        </div>

        <div className={styles.slot}>
          <label>{t('ghostGear.armor')}</label>
          {armor ? (
            <div className={styles.itemRow}>
              <span className={styles.itemName}>{armor.name}</span>
              <span className={styles.itemStats}>
                T{armor.tier} {armor.dr_min}-{armor.dr_max}
              </span>
              <button className={styles.actionBtn} onClick={() => onUnequip('armor')}>
                {t('ghostGear.remove')}
              </button>
            </div>
          ) : (
            <div className={styles.itemRow}>
              <span className={styles.emptySlot}>{t('ghostGear.none')}</span>
              <button className={styles.actionBtn} onClick={() => onEquip('armor')}>
                {t('ghostGear.equip')}
              </button>
            </div>
          )}
        </div>

        <button className={styles.closeBtn} onClick={onClose}>
          {t('ui.close')}
        </button>
      </div>
    </div>
  );
}
