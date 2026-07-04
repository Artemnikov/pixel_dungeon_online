import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Panel from './Panel';
import { getSettings, setSetting, subscribe } from './menuSettings';

function Slider({ label, value, onChange, disabled }) {
  return (
    <div className="opd-setting-row">
      <label>{label}</label>
      <input
        type="range" min="0" max="1" step="0.05"
        value={value} disabled={disabled}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <span className="opd-setting-val">{Math.round(value * 100)}%</span>
    </div>
  );
}

function Toggle({ label, checked, onChange }) {
  const { t } = useTranslation();
  return (
    <div className="opd-setting-row">
      <label>{label}</label>
      <button
        className={`opd-toggle ${checked ? 'on' : ''}`}
        onClick={() => onChange(!checked)}
      >
        {checked ? t('settings.on') : t('settings.off')}
      </button>
    </div>
  );
}

export default function SettingsPanel({ onClose }) {
  const { t, i18n } = useTranslation();
  const [s, setS] = useState(getSettings());
  useEffect(() => subscribe(setS), []);

  const update = (key, val) => { setSetting(key, val); setS(getSettings()); };

  const changeLang = (lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('i18nextLng', lang);
  };

  return (
    <Panel title={t('panel.settings')} icon="PREFS" onClose={onClose}>
      <h3 className="opd-section-title">{t('settings.audio')}</h3>
      <Toggle label={t('settings.masterMute')} checked={s.muted} onChange={(v) => update('muted', v)} />
      <Slider label={t('settings.musicVolume')} value={s.musicVolume} disabled={s.muted}
        onChange={(v) => update('musicVolume', v)} />
      <Slider label={t('settings.sfxVolume')} value={s.sfxVolume} disabled={s.muted}
        onChange={(v) => update('sfxVolume', v)} />

      <h3 className="opd-section-title">{t('settings.display')}</h3>
      <Toggle label={t('settings.bgAnimations')} checked={s.bgMotion}
        onChange={(v) => update('bgMotion', v)} />

      <h3 className="opd-section-title">{t('settings.language')}</h3>
      <div className="opd-setting-row">
        <select
          className="opd-lang-select"
          value={i18n.language}
          onChange={(e) => changeLang(e.target.value)}
        >
          <option value="en">English</option>
          <option value="ru">Русский</option>
        </select>
      </div>
    </Panel>
  );
}
