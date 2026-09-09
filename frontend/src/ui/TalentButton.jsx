import { useCallback, useState } from 'react';
import TalentIcon from './TalentIcon';
import AudioManager from '../audio/AudioManager';

const BTN_W = 40;
const BTN_H = 52;

export default function TalentButton({
  talentId,
  iconIndex,
  name,
  currentLevel,
  maxPoints,
  pointsAvailable,
  locked,
  onInfo,
  effects,
  metamorphMode,
  onMetamorphChoose,
}) {
  const canUpgrade = !locked && currentLevel < maxPoints && pointsAvailable > 0;
  const frameCol = maxPoints - 1;
  const fillRatio = currentLevel / Math.max(maxPoints, 1);
  const [pressed, setPressed] = useState(false);

  // The upgrade burst animation is owned by the animation manager
  // (VisualEffectsManager). It plays when the backend confirms the upgrade
  // (TALENT_UPGRADED WS event) and imperatively appends/removes the burst to
  // this button's DOM node, so no state or effects are needed here.
  const registerBurstNode = useCallback(
    (node) => {
      effects?.registerTalentButton?.(talentId, node);
      return () => effects?.registerTalentButton?.(talentId, null);
    },
    [effects, talentId],
  );

  const handlePointerDown = () => {
    if (locked) return;
    setPressed(true);
    AudioManager.play('CLICK');
  };
  const handlePointerUp = () => setPressed(false);

  return (
    <button
      ref={registerBurstNode}
      className={`talent-btn ${locked ? 'locked' : ''} ${currentLevel > 0 ? 'has-pts' : ''} ${pressed ? 'pressed' : ''} ${metamorphMode && currentLevel > 0 ? 'metamorph-target' : ''}`}
      title={name}
      onClick={() => {
        if (metamorphMode) {
          onMetamorphChoose?.(talentId);
        } else {
          onInfo?.(talentId, name, currentLevel, maxPoints, canUpgrade);
        }
      }}
      onMouseDown={handlePointerDown}
      onMouseUp={handlePointerUp}
      onMouseLeave={handlePointerUp}
      onTouchStart={handlePointerDown}
      onTouchEnd={handlePointerUp}
      style={{
        width: BTN_W,
        height: BTN_H,
        backgroundImage: 'url(/assets/talent_button.png)',
        backgroundPosition: `-${frameCol * BTN_W}px 0`,
        backgroundSize: `${4 * BTN_W}px ${BTN_H}px`,
        imageRendering: 'pixelated',
        opacity: locked ? 0.4 : 1,
        position: 'relative',
        border: 'none',
        cursor: locked ? 'default' : 'pointer',
        padding: 0,
        flexShrink: 0,
      }}
    >
      <div style={{ position: 'absolute', top: 4, left: 4 }}>
        <TalentIcon talentId={talentId} iconIndex={iconIndex} alpha={locked ? 0.5 : 1} />
      </div>
      <div
        className="talent-fill"
        style={{
          position: 'absolute',
          bottom: 4,
          left: 4,
          width: `${fillRatio * 32}px`,
          height: 10,
          background: '#ffff44',
          borderRadius: 0,
        }}
      />
    </button>
  );
}
