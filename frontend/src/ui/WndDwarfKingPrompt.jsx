import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';
import { DWARF_KING_TEXT } from './bossPromptText';

export function WndDwarfKingJoinPrompt({ initiatorName, onApprove, onDecline, text = DWARF_KING_TEXT }) {
  const { t } = useTranslation();

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Enter') onApprove();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onApprove]);

  return (
    <WndOverlay
      id={`${text.id}-join`}
      level={WindowLevel.DIALOG}
      onClose={onDecline}
    >
      <div className="wnd-chasm-jump" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-chasm-jump__title">{t(`${text.prefix}.title`, text.title)}</div>
        <div className="wnd-chasm-jump__desc">
          {t(`${text.prefix}.joinDesc`, {
            name: initiatorName,
            defaultValue: text.joinDesc,
          })}
        </div>
        <div className="wnd-chasm-jump__actions">
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--yes" onClick={onApprove}>
            {t(`${text.prefix}.joinYes`, 'Join Fight')}
          </button>
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--no" onClick={onDecline}>
            {t(`${text.prefix}.joinNo`, 'Not Ready')}
          </button>
        </div>
      </div>
    </WndOverlay>
  );
}

export function WndDwarfKingPartyStatus({ status, onStartWithout, onWait, text = DWARF_KING_TEXT }) {
  const { t } = useTranslation();
  const { pending_names = [], declined_names = [], can_decide } = status || {};

  return (
    <WndOverlay
      id={`${text.id}-status`}
      level={WindowLevel.DIALOG}
      onClose={onWait}
    >
      <div className="wnd-chasm-jump" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-chasm-jump__title">{t(`${text.prefix}.title`, text.title)}</div>
        {declined_names.length > 0 && (
          <div className="wnd-chasm-jump__desc">
            {t(`${text.prefix}.declinedDesc`, {
              names: declined_names.join(', '),
              defaultValue: '{{names}} is not ready to join the fight.',
            })}
          </div>
        )}
        {pending_names.length > 0 && (
          <div className="wnd-chasm-jump__desc">
            {t(`${text.prefix}.waitingDesc`, {
              names: pending_names.join(', '),
              defaultValue: 'Waiting for {{names}} to respond...',
            })}
          </div>
        )}
        <div className="wnd-chasm-jump__actions">
          {(can_decide || pending_names.length > 0) && (
            <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--yes" onClick={onStartWithout}>
              {t(`${text.prefix}.startWithout`, 'Start Without Them')}
            </button>
          )}
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--no" onClick={onWait}>
            {t(`${text.prefix}.wait`, 'Wait')}
          </button>
        </div>
      </div>
    </WndOverlay>
  );
}
