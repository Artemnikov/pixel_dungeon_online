import { useEffect, useState, useCallback, useRef, memo } from 'react';
import { useTranslation } from 'react-i18next';
import warriorSprite from '../assets/pixel-dungeon/sprites/warrior.png';
import ratSprite from '../assets/pixel-dungeon/sprites/rat.png';

const SLIDE_DURATION = 10000;

// ── Attack demo ──────────────────────────────────────────────────────────
const DEMO_COLS = 7;
const DEMO_TILE = 32;
const DEMO_W = DEMO_COLS * DEMO_TILE;
const DEMO_H = 3 * DEMO_TILE;
const DEMO_CYCLE = 3500;
const WARRIOR_FW = 12;
const WARRIOR_DW = 24;
const RAT_FW = 16;
const RAT_DW = 32;
const SRC_H = 16;

function demoDrawSprite(ctx, img, x, y, frame, srcFW, destW) {
  const offset = (DEMO_TILE - destW) / 2;
  ctx.drawImage(img, frame * srcFW, 0, srcFW, SRC_H, x + offset, y, destW, DEMO_TILE);
}

function demoFloatText(ctx, t, hit, text, x, y) {
  const e = t - hit;
  if (e < 0 || e > 600) return;
  const p = e / 600;
  ctx.save();
  ctx.globalAlpha = 1 - p;
  ctx.fillStyle = '#ffcc00';
  ctx.font = 'bold 11px monospace';
  ctx.textAlign = 'center';
  ctx.fillText(text, x, y - p * 20);
  ctx.restore();
}

function demoBlood(ctx, t, hit, x, y, dir) {
  const e = t - hit;
  if (e < 0 || e > 400) return;
  const p = e / 400;
  ctx.save();
  ctx.globalAlpha = 1 - p;
  ctx.fillStyle = '#cc0000';
  for (let i = 0; i < 4; i++) {
    const a = dir + (i - 1.5) * 0.4;
    const d = p * 18;
    ctx.fillRect(x + Math.cos(a) * d - 1, y + Math.sin(a) * d + p * 6 - 1, 2, 2);
  }
  ctx.restore();
}

function renderDemo(ctx, now, imgs) {
  ctx.imageSmoothingEnabled = false;
  const t = now % DEMO_CYCLE;
  const wy = DEMO_TILE;

  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, DEMO_W, DEMO_H);

  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let c = 0; c <= DEMO_COLS; c++) {
    const x = c * DEMO_TILE + 0.5;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, DEMO_H); ctx.stroke();
  }
  for (let r = 0; r <= 3; r++) {
    const y = r * DEMO_TILE + 0.5;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(DEMO_W, y); ctx.stroke();
  }

  let wx = DEMO_TILE;
  let wFrame = 0;
  let showR1 = false, r1Frame = 0, r1Alpha = 1, r1Flash = false;
  let showR2 = false, r2Frame = 0, r2Alpha = 1, r2Flash = false;
  let showProj = false, projT = 0;

  if (t < 500) {
    showR1 = true;
    wFrame = [0, 0, 0, 1][Math.floor(now / 1000) % 4];
    r1Frame = [0, 0, 0, 1][Math.floor(now / 500) % 4];
  } else if (t < 800) {
    showR1 = true;
    const p = (t - 500) / 300;
    wx = (1 + p) * DEMO_TILE;
    wFrame = [2, 3, 4, 5, 6, 7][Math.floor(p * 6) % 6];
    r1Frame = [0, 0, 0, 1][Math.floor(now / 500) % 4];
  } else if (t < 1070) {
    showR1 = true;
    wx = 2 * DEMO_TILE;
    wFrame = [13, 14, 15, 0][Math.min(Math.floor((t - 800) / 67.5), 3)];
    r1Frame = [0, 0, 0, 1][Math.floor(now / 500) % 4];
    r1Flash = t >= 930 && t < 980;
  } else if (t < 1470) {
    showR1 = true;
    wx = 2 * DEMO_TILE;
    wFrame = [0, 0, 0, 1][Math.floor(now / 1000) % 4];
    r1Frame = [11, 12, 13, 14][Math.min(Math.floor((t - 1070) / 100), 3)];
    r1Alpha = Math.max(0, 1 - (t - 1070) / 400);
  } else if (t < 1700) {
    wx = 2 * DEMO_TILE;
    wFrame = [0, 0, 0, 1][Math.floor(now / 1000) % 4];
    showR2 = true;
    r2Alpha = Math.min(1, (t - 1470) / 230);
  } else if (t < 2000) {
    wx = 2 * DEMO_TILE;
    wFrame = [0, 0, 0, 1][Math.floor(now / 1000) % 4];
    showR2 = true;
    showProj = true;
    projT = (t - 1700) / 300;
  } else if (t < 2400) {
    wx = 2 * DEMO_TILE;
    wFrame = [0, 0, 0, 1][Math.floor(now / 1000) % 4];
    showR2 = true;
    r2Frame = [11, 12, 13, 14][Math.min(Math.floor((t - 2000) / 100), 3)];
    r2Alpha = Math.max(0, 1 - (t - 2000) / 400);
    r2Flash = t < 2050;
  } else {
    wx = 2 * DEMO_TILE;
    wFrame = [0, 0, 0, 1][Math.floor(now / 1000) % 4];
  }

  demoDrawSprite(ctx, imgs.warrior, wx, wy, wFrame, WARRIOR_FW, WARRIOR_DW);

  if (showR1) {
    const rx = 3 * DEMO_TILE;
    ctx.save();
    ctx.globalAlpha = r1Alpha;
    demoDrawSprite(ctx, imgs.rat, rx, wy, r1Frame, RAT_FW, RAT_DW);
    if (r1Flash) { ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.fillRect(rx, wy, DEMO_TILE, DEMO_TILE); }
    ctx.restore();
  }

  if (showR2) {
    const rx = 5 * DEMO_TILE;
    ctx.save();
    ctx.globalAlpha = r2Alpha;
    demoDrawSprite(ctx, imgs.rat, rx, wy, r2Frame, RAT_FW, RAT_DW);
    if (r2Flash) { ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.fillRect(rx, wy, DEMO_TILE, DEMO_TILE); }
    ctx.restore();
  }

  if (showProj) {
    const sx = 2 * DEMO_TILE + 22;
    const sy = wy + 16;
    const ex = 5 * DEMO_TILE + 16;
    const ey = wy + 16;
    const p = Math.min(1, projT);
    const px = sx + (ex - sx) * p;
    const py = sy + (ey - sy) * p;
    ctx.strokeStyle = 'rgba(255,170,0,0.3)';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(px - 8, py); ctx.lineTo(px, py); ctx.stroke();
    ctx.fillStyle = '#ffcc00';
    ctx.beginPath(); ctx.arc(px, py, 2, 0, Math.PI * 2); ctx.fill();
  }

  demoFloatText(ctx, t, 930, '-5', 3 * DEMO_TILE + 16, wy);
  demoFloatText(ctx, t, 2000, '-7', 5 * DEMO_TILE + 16, wy);
  demoBlood(ctx, t, 930, 3 * DEMO_TILE + 16, wy + 16, 0);
  demoBlood(ctx, t, 2000, 5 * DEMO_TILE + 16, wy + 16, Math.PI);
}

const AttackDemo = memo(function AttackDemo() {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);
  const visibleRef = useRef(true);
  const imgsRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let destroyed = false;
    const wImg = new Image();
    const rImg = new Image();
    wImg.src = warriorSprite;
    rImg.src = ratSprite;

    Promise.all([
      new Promise(r => { wImg.onload = r; }),
      new Promise(r => { rImg.onload = r; }),
    ]).then(() => {
      if (destroyed) return;
      imgsRef.current = { warrior: wImg, rat: rImg };
      kick();
    });

    const observer = new IntersectionObserver(([entry]) => {
      visibleRef.current = entry.isIntersecting;
      if (visibleRef.current && imgsRef.current && !rafRef.current) kick();
    });
    observer.observe(canvas);

    function kick() {
      function frame(now) {
        rafRef.current = null;
        if (!visibleRef.current) return;
        renderDemo(ctx, now, imgsRef.current);
        rafRef.current = requestAnimationFrame(frame);
      }
      rafRef.current = requestAnimationFrame(frame);
    }

    return () => {
      destroyed = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      observer.disconnect();
    };
  }, []);

  return <canvas ref={canvasRef} className="tutorial-demo-canvas" width={DEMO_W} height={DEMO_H} />;
});

function SlideMovement({ t }) {
  return (
    <>
      <h2 className="tutorial-slide-title">{t('tutorial.movement.title')}</h2>
      <p className="tutorial-slide-body">{t('tutorial.movement.body')}</p>
      <div className="tutorial-keys">
        <span className="tutorial-key">W</span>
        <span className="tutorial-key">A</span>
        <span className="tutorial-key">S</span>
        <span className="tutorial-key">D</span>
      </div>
      <div className="tutorial-keys">
        <span className="tutorial-key">&uarr;</span>
        <span className="tutorial-key">&larr;</span>
        <span className="tutorial-key">&darr;</span>
        <span className="tutorial-key">&rarr;</span>
      </div>
    </>
  );
}

function SlideExamine({ t }) {
  return (
    <>
      <h2 className="tutorial-slide-title">{t('tutorial.examine.title')}</h2>
      <p className="tutorial-slide-body">{t('tutorial.examine.body')}</p>
      <div className="tutorial-keys">
        <span className="tutorial-key">E</span>
      </div>
      <p className="tutorial-slide-body" style={{ marginTop: 8, fontSize: 11, color: '#999' }}>
        {t('tutorial.examine.sub')}
      </p>
    </>
  );
}

function SlideObjectives({ t }) {
  return (
    <>
      <h2 className="tutorial-slide-title">{t('tutorial.objectives.title')}</h2>
      <p className="tutorial-slide-body">{t('tutorial.objectives.body')}</p>
      <div className="tutorial-stairs" />
      <p className="tutorial-slide-body" style={{ marginTop: 4, fontSize: 11, color: '#999' }}>
        {t('tutorial.objectives.stairs')}
      </p>
      <p className="tutorial-slide-body" style={{ marginTop: 8, fontSize: 11, color: '#e8d5a3' }}>
        {t('tutorial.objectives.boss')}
      </p>
    </>
  );
}

function SlideAttack({ t }) {
  return (
    <>
      <h2 className="tutorial-slide-title">{t('tutorial.attack.title')}</h2>
      <AttackDemo />
      <p className="tutorial-slide-body">{t('tutorial.attack.body')}</p>
      <p className="tutorial-slide-body" style={{ marginTop: 8, fontSize: 11, color: '#999' }}>
        {t('tutorial.attack.sub')}
      </p>
    </>
  );
}

const SLIDES = [SlideMovement, SlideExamine, SlideAttack, SlideObjectives];

function TutorialOverlay({ onComplete }) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState(0);
  const [progress, setProgress] = useState(0);
  const [transition, setTransition] = useState(null);
  const [fading, setFading] = useState(false);
  const timerRef = useRef(null);
  const startRef = useRef(0);
  const rafRef = useRef(null);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => { onCompleteRef.current = onComplete; });

  const stopTimers = useCallback(() => {
    if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
  }, []);

  const goNext = useCallback(() => {
    if (fading || transition) return;
    stopTimers();
    setCurrent((prev) => {
      if (prev >= SLIDES.length - 1) {
        setFading(true);
        setTimeout(() => onCompleteRef.current(), 300);
        return prev;
      }
      setTransition({ from: prev });
      return prev + 1;
    });
  }, [stopTimers, fading, transition]);

  const skip = useCallback(() => {
    stopTimers();
    onCompleteRef.current();
  }, [stopTimers]);

  useEffect(() => {
    if (!transition) return;
    const id = setTimeout(() => setTransition(null), 400);
    return () => clearTimeout(id);
  }, [transition]);

  useEffect(() => {
    if (current >= SLIDES.length) return;
    startRef.current = performance.now();

    const tick = (now) => {
      const elapsed = now - startRef.current;
      const pct = Math.min(1, elapsed / SLIDE_DURATION);
      setProgress(pct);
      if (pct < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };
    rafRef.current = requestAnimationFrame(tick);

    timerRef.current = setTimeout(() => {
      goNext();
    }, SLIDE_DURATION);

    return stopTimers;
  }, [current, goNext, stopTimers]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        goNext();
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        skip();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [goNext, skip]);

  if (current >= SLIDES.length && !fading) return null;

  const SlideComponent = SLIDES[current];

  return (
    <div className={`tutorial-overlay${fading ? ' tutorial-overlay--fading' : ''}`} onClick={goNext}>
      <div className="tutorial-card" onClick={(e) => e.stopPropagation()}>
        <div className="tutorial-slides-viewport">
          {transition && (
            <div className="tutorial-slide tutorial-slide--exit-left">
              {SLIDES[transition.from]({ t })}
            </div>
          )}
          <div className={`tutorial-slide ${transition ? 'tutorial-slide--enter-right' : 'tutorial-slide--active'}`}>
            <SlideComponent t={t} />
          </div>
          <div className="tutorial-progress-bar" style={{ width: `${progress * 100}%` }} />
        </div>
        <div className="tutorial-footer">
          <div className="tutorial-dots">
            {SLIDES.map((_, i) => (
              <div key={i} className={`tutorial-dot${i === current ? ' tutorial-dot--active' : ''}`} />
            ))}
          </div>
          <button className="tutorial-skip-btn" onClick={skip}>
            {t('tutorial.skip')}
          </button>
        </div>
      </div>
    </div>
  );
}

export default memo(TutorialOverlay);
