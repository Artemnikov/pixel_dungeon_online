import { useTranslation } from 'react-i18next';

export default function LoadingOverlay({ visible }) {
  const { t } = useTranslation();
  if (!visible) return null;
  return (
    <div className="loading-screen">
      <div className="loading-spinner"></div>
      <div className="loading-text">{t('ui.loading')}</div>
    </div>
  );
}
