import { useTranslation } from 'react-i18next';

// Hook version for React components.
export default function useEntityName(entity) {
  const { t } = useTranslation();
  return entityDisplayName(entity, t);
}

// Pure function version (pass t() from useTranslation or i18n.t directly).
export function entityDisplayName(entity, t) {
  if (!entity) return '';
  if (entity.locale_key) return t(entity.locale_key, { defaultValue: entity.name || '' });
  return entity.name || '';
}

