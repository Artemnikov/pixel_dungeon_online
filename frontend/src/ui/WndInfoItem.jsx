import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import ItemIcon from './ItemIcon';
import { titleColor } from './itemActions';
import { statLines } from './itemStatLines';
import { comparisonLines } from './itemComparison';

export default function WndInfoItem({ item, belongings }) {
  const { t } = useTranslation();
  if (!item) return null;

  const name = item.locale_key ? t(item.locale_key, { defaultValue: item.name }) : item.name;
  const level = item.level_known ? item.level : null;
  const lines = statLines(item, t);

  const compare = findComparison(item, belongings, t);

  return (
    <div className="wnd-info-card">
      <IconTitle
        icon={<ItemIcon item={item} size={16} />}
        title={name}
        level={level}
        color={titleColor(item)}
      />
      {item.kind === 'chest' && item.chest_type === 'CRYSTAL_CHEST' && item.item_category && (
        <div className="wnd-info-desc">
          {`You can see through the crystal — this chest contains a ${item.item_category.toLowerCase()}.`}
        </div>
      )}
      {!(item.kind === 'chest' && item.chest_type === 'CRYSTAL_CHEST' && item.item_category) && item.description && (
        <div className="wnd-info-desc">{item.description}</div>
      )}
      {lines.length > 0 && (
        <div className="wnd-info-stats">
          {lines.map((l, i) => <div key={i} className="wnd-info-stat-row">{l}</div>)}
        </div>
      )}
      {compare && (
        <div className="wnd-info-compare">
          <div className="wnd-info-compare-header">{t('ui.comparedToEquipped')}</div>
          {compare.map((row, i) => (
            <div key={i} className="wnd-info-compare-row">
              <span className="wnd-info-compare-label">{row.label}</span>
              <span className="wnd-info-compare-val wnd-info-compare-eq">{row.eqVal}</span>
              <span className="wnd-info-compare-arrow">&rarr;</span>
              <span className="wnd-info-compare-val wnd-info-compare-item">{row.itemVal}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function findComparison(item, belongings, t) {
  if (!belongings || !item) return null;

  const wTypes = ['weapon', 'melee_weapon', 'staff', 'missile_weapon'];
  const isWeapon = wTypes.includes(item.type) || wTypes.includes(item.kind);
  const isArmor = item.type === 'wearable' || item.kind === 'armor';
  const isRing = item.kind === 'ring' || item.type === 'ring';

  if (isWeapon && belongings.weapon && belongings.weapon.id !== item.id) {
    return comparisonLines(item, belongings.weapon, t);
  }
  if (isArmor && belongings.armor && belongings.armor.id !== item.id) {
    return comparisonLines(item, belongings.armor, t);
  }
  if (isRing && belongings.ring && belongings.ring.id !== item.id) {
    return comparisonLines(item, belongings.ring, t);
  }

  return null;
}
