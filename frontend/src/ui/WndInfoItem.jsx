import { useTranslation } from 'react-i18next';
import IconTitle from './IconTitle';
import ItemIcon from './ItemIcon';
import { titleColor } from './itemActions';
import { statLines } from './itemStatLines';

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
    </div>
  );
}
