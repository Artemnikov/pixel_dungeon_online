import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import WndOverlay from './WndOverlay';
import { WindowLevel } from '../game/window/WindowTypes';

export function WndDwarfKingJoinPrompt({ initiatorName, onApprove, onDecline }) {
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
      id="wnd-dwarf-king-join"
      level={WindowLevel.DIALOG}
      onClose={onDecline}
    >
      <div className="wnd-chasm-jump" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-chasm-jump__title">{t('game.dwarfKingPrompt.title', 'King of Dwarves Boss Fight')}</div>
        <div className="wnd-chasm-jump__desc">
          {t('game.dwarfKingPrompt.joinDesc', {
            name: initiatorName,
            defaultValue: '{{name}} is challenging the King of Dwarves! Do you want to join the boss fight?',
          })}
        </div>
        <div className="wnd-chasm-jump__actions">
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--yes" onClick={onApprove}>
            {t('game.dwarfKingPrompt.joinYes', 'Join Fight')}
          </button>
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--no" onClick={onDecline}>
            {t('game.dwarfKingPrompt.joinNo', 'Not Ready')}
          </button>
        </div>
      </div>
    </WndOverlay>
  );
}

export function WndDwarfKingPartyStatus({ status, onStartWithout, onWait }) {
  const { t } = useTranslation();
  const { pending_names = [], declined_names = [], can_decide } = status || {};

  return (
    <WndOverlay
      id="wnd-dwarf-king-status"
      level={WindowLevel.DIALOG}
      onClose={onWait}
    >
      <div className="wnd-chasm-jump" onClick={(e) => e.stopPropagation()}>
        <div className="wnd-chasm-jump__title">{t('game.dwarfKingPrompt.title', 'King of Dwarves Boss Fight')}</div>
        {declined_names.length > 0 && (
          <div className="wnd-chasm-jump__desc">
            {t('game.dwarfKingPrompt.declinedDesc', {
              names: declined_names.join(', '),
              defaultValue: '{{names}} is not ready to join the fight.',
            })}
          </div>
        )}
        {pending_names.length > 0 && (
          <div className="wnd-chasm-jump__desc">
            {t('game.dwarfKingPrompt.waitingDesc', {
              names: pending_names.join(', '),
              defaultValue: 'Waiting for {{names}} to respond...',
            })}
          </div>
        )}
        <div className="wnd-chasm-jump__actions">
          {(can_decide || pending_names.length > 0) && (
            <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--yes" onClick={onStartWithout}>
              {t('game.dwarfKingPrompt.startWithout', 'Start Without Them')}
            </button>
          )}
          <button className="wnd-chasm-jump__btn wnd-chasm-jump__btn--no" onClick={onWait}>
            {t('game.dwarfKingPrompt.wait', 'Wait')}
          </button>
        </div>
      </div>
    </WndOverlay>
  );
}
