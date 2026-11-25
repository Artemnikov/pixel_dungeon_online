import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import WndOptions from './WndOptions';
import WndInfoArmorAbility from './WndInfoArmorAbility';

const CROWN_YES = 0;
const CROWN_INFO = 1;

/** SPD RatKing.interact's crown WndOptions: trade the crown for Ratmogrify,
 *  read about it first (WndInfoArmorAbility), or decline. */
export default function WndRatKing({ npcId, onChoose, onClose }) {
  const { t } = useTranslation();
  const [showInfo, setShowInfo] = useState(false);
  const infoRequested = useRef(false);

  if (showInfo) {
    return <WndInfoArmorAbility ability="ratmogrify" onClose={onClose} />;
  }

  return (
    <WndOptions
      title={t('mob.rat_king')}
      message={t('mobText.rat_king_crown_desc')}
      options={[
        t('mobText.rat_king_crown_yes'),
        t('mobText.rat_king_crown_info'),
        t('mobText.rat_king_crown_no'),
      ]}
      onSelect={(i) => {
        if (i === CROWN_INFO) {
          infoRequested.current = true;
          setShowInfo(true);
          return;
        }
        onChoose(npcId, i === CROWN_YES);
      }}
      onClose={() => { if (!infoRequested.current) onClose(); }}
    />
  );
}
