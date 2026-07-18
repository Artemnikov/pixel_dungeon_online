// Chrome-style title menu button: small pixel icon + label, matching the
// look of StyledButton on SPD's TitleScene.
import AudioManager from '../audio/AudioManager';
import Icon from './Icon';

export default function MenuButton({ icon, label, onClick, accent = false, className = '', disabled = false }) {
  return (
    <button
      className={`opd-menu-btn ${accent ? 'accent' : ''} ${className}`}
      onClick={() => { AudioManager.play('CLICK'); onClick?.(); }}
      disabled={disabled}
    >
      {icon && <Icon name={icon} scale={2} />}
      <span className="opd-menu-btn-label">{label}</span>
    </button>
  );
}
