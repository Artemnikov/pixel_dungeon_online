import { useEffect, useState, useCallback, useRef, memo } from 'react';

import sewersSplash from '../assets/pixel-dungeon/splashes/sewers.jpg';
import prisonSplash from '../assets/pixel-dungeon/splashes/prison.jpg';
import cavesSplash from '../assets/pixel-dungeon/splashes/caves.jpg';
import citySplash from '../assets/pixel-dungeon/splashes/city.jpg';
import hallsSplash from '../assets/pixel-dungeon/splashes/halls.jpg';

const SPLASH = {
  0: sewersSplash,
  1: sewersSplash,
  6: prisonSplash,
  11: cavesSplash,
  16: citySplash,
  21: hallsSplash,
};

function LoreOverlay({ depth, body, onContinue }) {
  const [phase, setPhase] = useState('enter');
  const dismissed = useRef(false);
  const overlayRef = useRef(null);
  const onContinueRef = useRef(onContinue);

  useEffect(() => { onContinueRef.current = onContinue; });
  useEffect(() => {
    const raf = requestAnimationFrame(() => setPhase('visible'));
    return () => cancelAnimationFrame(raf);
  }, []);

  const handleDismiss = useCallback(() => {
    if (dismissed.current) return;
    dismissed.current = true;
    setPhase('exit');
  }, []);

  useEffect(() => {
    if (phase !== 'exit') return;
    const el = overlayRef.current;
    const handler = (e) => {
      if (e.propertyName === 'opacity') onContinueRef.current();
    };
    el?.addEventListener('transitionend', handler);
    return () => el?.removeEventListener('transitionend', handler);
  }, [phase]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleDismiss();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleDismiss]);

  const splashSrc = SPLASH[depth] || sewersSplash;
  const paragraphs = body.split('\n');

  return (
    <div
      ref={overlayRef}
      onClick={phase === 'enter' ? undefined : handleDismiss}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        opacity: phase === 'visible' ? 1 : 0,
        transition: 'opacity 0.5s ease-in-out',
        pointerEvents: phase === 'exit' ? 'none' : 'auto',
        background: '#000',
      }}
    >
      <img
        src={splashSrc}
        alt=""
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
      />

      <div style={{
        position: 'absolute', top: 0, bottom: 0, left: 0, width: '48%',
        pointerEvents: 'none',
        background: 'linear-gradient(to right, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.7) 45%, transparent 100%)',
      }} />
      <div style={{
        position: 'absolute', top: 0, bottom: 0, right: 0, width: '12%',
        pointerEvents: 'none',
        background: 'linear-gradient(to left, rgba(0,0,0,0.92) 0%, transparent 80%)',
      }} />

      <div style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none',
      }}>
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            maxWidth: 300,
            width: '100%',
            background: 'rgba(0,0,0,0.55)',
            padding: '16px 20px 14px',
            borderRadius: 4,
            boxShadow: '0 0 30px rgba(0,0,0,0.9)',
            margin: '0 24px',
            pointerEvents: 'auto',
          }}
        >
          {paragraphs.map((p, i) => (
            <p key={i} style={{
              margin: i > 0 ? '0 0 10px 0' : '0 0 10px 0',
              color: '#ffffff',
              fontFamily: 'monospace',
              fontSize: 12,
              lineHeight: 1.7,
              textAlign: 'left',
              textShadow: '0 1px 3px rgba(0,0,0,0.5)',
            }}>
              {p}
            </p>
          ))}

          <div style={{ textAlign: 'center', marginTop: 6 }}>
            <button
              onClick={handleDismiss}
              style={{
                padding: '6px 18px',
                border: 'none',
                background: 'rgba(255,255,255,0.10)',
                color: '#ffffff',
                fontFamily: 'monospace',
                fontSize: 12,
                cursor: 'pointer',
                borderRadius: 2,
                lineHeight: 1.4,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.18)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.10)'; }}
            >
              ⬇ Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default memo(LoreOverlay);
