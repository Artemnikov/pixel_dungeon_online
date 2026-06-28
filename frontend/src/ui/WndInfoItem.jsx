import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import ItemIcon from './ItemIcon';
import { titleColor } from './itemActions';

export function statLines(item, t) {
  const lines = [];
  const wTypes = ['weapon', 'melee_weapon', 'staff', 'missile_weapon'];
  if (wTypes.includes(item.type) || wTypes.includes(item.kind)) {
    if (item.tier != null) lines.push(t('ui.tier', { tier: item.tier }));
    if (item.damage != null) lines.push(`${t('ui.damageStat')}: ${item.damage}`);
    if (item.strength_requirement != null)
      lines.push(t('ui.strengthReq', { str: item.strength_requirement }));
  }
  if (item.type === 'wearable' || item.kind === 'armor') {
    if (item.tier != null) lines.push(t('ui.tier', { tier: item.tier }));
    if (item.strength_requirement != null)
      lines.push(t('ui.strengthReq', { str: item.strength_requirement }));
    const bufLvl = item.level_known ? Math.max(0, item.level || 0) : 0;
    const drMin = bufLvl;
    const drMax = item.tier * (2 + bufLvl);
    lines.push(`${t('ui.defenseStat')}: ${drMin}-${drMax}`);
  }
  if (item.kind === 'ring' || item.type === 'ring') {
    if (item.level_known && item.level != null)
      lines.push(item.level >= 0 ? `+${item.level}` : `${item.level}`);
  }
  if (item.kind === 'artifact' || item.type === 'artifact') {
    if (item.charge != null && item.charge_cap != null)
      lines.push(t('ui.artifactCharge', { charge: item.charge, cap: item.charge_cap }));
  }
  if (item.kind === 'wand' || item.type === 'wand') {
    if (item.charges != null && item.max_charges != null)
      lines.push(t('ui.wandCharges', { charges: item.charges, max: item.max_charges }));
  }
  if (item.cursed_known && item.cursed) lines.push(t('ui.cursed'));
  if (item.cursed_known === false && (wTypes.includes(item.type) || item.type === 'wearable'
      || item.kind === 'ring' || item.kind === 'artifact' || item.kind === 'wand'))
    lines.push(t('ui.cursedUnknown'));
  if (item.enchantment && item.enchantment.type && item.enchantment.type !== 'none') {
    const glyphLabel = item.enchantment.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    lines.push(`Glyph of ${glyphLabel}`);
  }
  return lines;
}

export default function WndInfoItem({ item }) {
  const { t } = useTranslation();
  if (!item) return null;

  const name = item.locale_key ? t(item.locale_key, { defaultValue: item.name }) : item.name;
  const level = item.level_known ? item.level : null;
  const lines = statLines(item, t);

  return (
    <div className="wnd-info-card">
      <IconTitle
        icon={<ItemIcon item={item} size={16} />}
        title={name}
        level={level}
        color={titleColor(item)}
      />
      {item.description && <div className="wnd-info-desc">{item.description}</div>}
      {lines.length > 0 && (
        <div className="wnd-info-stats">
          {lines.map((l, i) => <div key={i} className="wnd-info-stat-row">{l}</div>)}
        </div>
      )}
    </div>
  );
}
