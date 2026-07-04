import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ItemIcon from './ItemIcon';

export default function AdminItemBrowser({ catalog, onClose, onGiveItem }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter(
      (entry) => entry.name.toLowerCase().includes(q) || entry.category.toLowerCase().includes(q)
    );
  }, [catalog, query]);

  return (
    <div className="talent-overlay" onClick={onClose}>
      <div className="talent-pane item-browser-pane" onClick={(e) => e.stopPropagation()}>
        <div className="talent-header">
          <h2 className="talent-title">{t('admin.giveItem')}</h2>
          <button className="talent-close" onClick={onClose}>&times;</button>
        </div>
        <div className="item-browser-search">
          <input
            type="text"
            placeholder={t('admin.searchItems')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
        </div>
        <div className="talent-body item-browser-list">
          {filtered.map((entry) => (
            <div
              key={entry.kind}
              className="item-browser-row"
              onClick={() => onGiveItem(entry.kind)}
            >
              <ItemIcon item={{ kind: entry.kind, name: entry.name }} size={28} />
              <span className="item-browser-name">{entry.name}</span>
              <span className="item-browser-category">{entry.category}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="item-browser-empty">{t('admin.noMatch', { query })}</div>
          )}
        </div>
      </div>
    </div>
  );
}
