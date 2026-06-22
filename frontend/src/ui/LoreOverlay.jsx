import { useTranslation } from 'react-i18next';

export default function LoreOverlay({ title, body, onContinue }) {
  const { t } = useTranslation();

  const paragraphs = body.split('\n');

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 200,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0,0,0,0.92)',
      padding: 24,
    }}>
      <div style={{
        maxWidth: 480,
        width: '100%',
        color: '#c0c0c0',
        fontFamily: 'monospace',
        fontSize: 14,
        lineHeight: 1.6,
        textAlign: 'center',
      }}>
        <div style={{
          fontSize: 20,
          fontWeight: 'bold',
          color: '#f0d9a0',
          marginBottom: 20,
          letterSpacing: 2,
          textTransform: 'uppercase',
        }}>
          {title}
        </div>

        {paragraphs.map((p, i) => (
          <p key={i} style={{
            margin: '0 0 12px 0',
            textAlign: i === 0 ? 'center' : 'left',
            color: i === 0 ? '#a0a0a0' : '#b0b0b0',
            fontStyle: i === 0 ? 'italic' : 'normal',
            fontSize: i === 0 ? 12 : 14,
          }}>
            {p}
          </p>
        ))}

        <button
          onClick={onContinue}
          style={{
            marginTop: 28,
            padding: '10px 36px',
            border: '1px solid #6a6a6a',
            background: 'rgba(255,255,255,0.08)',
            color: '#f0d9a0',
            fontFamily: 'monospace',
            fontSize: 14,
            cursor: 'pointer',
            borderRadius: 3,
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.15)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
        >
          {t('lore.continue', 'Continue')} ▼
        </button>
      </div>
    </div>
  );
}
