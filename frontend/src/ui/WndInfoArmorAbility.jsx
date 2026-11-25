import { useTranslation } from 'react-i18next';
import { getHeroIconIndex } from '../data/heroIcons';
import HeroIcon from './HeroIcon';
import WndOverlay from './WndOverlay';
import { WindowLevel, WindowBackdrop } from '../game/window/WindowTypes';

export default function WndInfoArmorAbility({ ability, onClose }) {
  const { t } = useTranslation();
  return (
    <WndOverlay
      id="wnd-armor-ability-info"
      level={WindowLevel.SECONDARY}
      backdrop={WindowBackdrop.DARK}
      onClose={onClose}
      className="choice-overlay"
    >
      <div className="wnd-info-ability" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-info-title">
          <HeroIcon index={getHeroIconIndex('ability', ability)} size={32} />
          <span className="wnd-info-name">{t(`ability.${ability}.name`, { defaultValue: ability.replace(/_/g, ' ') })}</span>
        </div>
        <div className="wnd-info-desc">{t(`ability.${ability}.desc`)}</div>
        <button className="wnd-close-btn" onClick={onClose}>{t('subclass.close')}</button>
      </div>
    </WndOverlay>
  );
}
