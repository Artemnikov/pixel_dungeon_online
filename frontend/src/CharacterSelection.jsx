import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import './heroSelect.css';
import AudioManager from './audio/AudioManager';
import Icon from './menu/Icon';
import useParallaxBackground from './menu/useParallaxBackground';
import { effectiveMusicVolume } from './menu/menuSettings';

import descendSound from './assets/pixel-dungeon/audio/descend.mp3';

import warriorSplash from './assets/pixel-dungeon/splashes/warrior.jpg';
import mageSplash from './assets/pixel-dungeon/splashes/mage.jpg';
import rogueSplash from './assets/pixel-dungeon/splashes/rogue.jpg';
import huntressSplash from './assets/pixel-dungeon/splashes/huntress.jpg';
import duelistSplash from './assets/pixel-dungeon/splashes/duelist.jpg';
import clericSplash from './assets/pixel-dungeon/splashes/cleric.jpg';

import warriorSheet from './assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from './assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from './assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from './assets/pixel-dungeon/sprites/huntress.png';
import duelistSheet from './assets/pixel-dungeon/sprites/duelist.png';
import clericSheet from './assets/pixel-dungeon/sprites/cleric.png';

const HERO_FRAME = { x: 0, y: 90, w: 12, h: 15 };
const SHEET_W = 256, SHEET_H = 128;

const HERO_IDS = ['warrior', 'mage', 'rogue', 'huntress', 'duelist', 'cleric'];
const PICKER_SCALE = 6;

function HeroBust({ sheet, scale = 3, selected }) {
  const f = HERO_FRAME;
  return (
    <span
      className="hero-bust"
      style={{
        width: f.w * scale,
        height: f.h * scale,
        backgroundImage: `url(${sheet})`,
        backgroundRepeat: 'no-repeat',
        backgroundSize: `${SHEET_W * scale}px ${SHEET_H * scale}px`,
        backgroundPosition: `-${f.x * scale}px -${f.y * scale}px`,
        imageRendering: 'pixelated',
        filter: selected ? 'none' : 'brightness(0.6)',
      }}
    />
  );
}

const CharacterSelection = ({ onSelect, showDifficulty = true }) => {
  const { t } = useTranslation();
  const [selectedClass, setSelectedClass] = useState(null);
  const [difficulty, setDifficulty] = useState('normal');
  const [strongerBosses, setStrongerBosses] = useState(false);
  const [playerName, setPlayerName] = useState(
    () => (typeof localStorage !== 'undefined' && localStorage.getItem('opd_last_name')) || ''
  );
  const [landscape, setLandscape] = useState(
    typeof window !== 'undefined' ? window.innerWidth > window.innerHeight : true
  );
  const parallaxRef = useRef(null);
  const bustsRef = useRef(null);
  const flipFrom = useRef(null);
  const prevPicked = useRef(null);

  const heroId = HERO_IDS.includes(selectedClass) ? selectedClass : null;

  const HEROES = [
    { id: 'warrior', sheet: warriorSheet, splash: warriorSplash },
    { id: 'mage', sheet: mageSheet, splash: mageSplash },
    { id: 'rogue', sheet: rogueSheet, splash: rogueSplash },
    { id: 'huntress', sheet: huntressSheet, splash: huntressSplash },
    { id: 'duelist', sheet: duelistSheet, splash: duelistSplash },
    { id: 'cleric', sheet: clericSheet, splash: clericSplash },
  ];
  const hero = HEROES.find(h => h.id === heroId);

  useParallaxBackground(parallaxRef);

  useEffect(() => {
    const onResize = () => setLandscape(window.innerWidth > window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const pick = (id) => {
    AudioManager.play('CLICK');
    const el = bustsRef.current;
    if (el) flipFrom.current = el.getBoundingClientRect();
    setSelectedClass(id === selectedClass ? null : id);
  };

  const onFlipDone = (e) => {
    if (e.target !== e.currentTarget || e.propertyName !== 'transform') return;
    const el = e.currentTarget;
    el.style.transition = '';
    el.style.transform = '';
  };

  useLayoutEffect(() => {
    const nowPicked = heroId != null;
    const wasPicked = prevPicked.current != null;
    prevPicked.current = heroId;
    if (wasPicked === nowPicked) return;
    const el = bustsRef.current;
    const from = flipFrom.current;
    if (!el || !from) return;
    flipFrom.current = null;
    const to = el.getBoundingClientRect();
    const dx = from.left + from.width / 2 - (to.left + to.width / 2);
    const dy = from.top + from.height / 2 - (to.top + to.height / 2);
    el.style.transition = 'none';
    el.style.transform = `translate(${dx}px, ${dy}px)`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.transition = 'transform 0.35s ease';
        el.style.transform = '';
      });
    });
  }, [heroId]);

  const start = () => {
    if (!selectedClass) return;
    AudioManager.play('CLICK');
    const descendAudio = new Audio(descendSound);
    descendAudio.volume = effectiveMusicVolume();
    descendAudio.play().catch(() => {});
    onSelect(selectedClass, difficulty, playerName.trim(), strongerBosses);
  };

  return (
    <div className={`hero-select ${landscape ? 'landscape' : 'portrait'} ${heroId ? 'picked' : ''}`}>
      <canvas ref={parallaxRef} className="hero-parallax" />
      {hero?.splash && <img key={hero.id} className="hero-splash" src={hero.splash} alt="" />}
      <div className="hero-vignette-left" />
      <div className="hero-vignette-right" />

      <div className={`hero-ui ${landscape || heroId ? '' : 'center'}`}>
        <h1 className="hero-title">{t('hero.title')}</h1>

        {landscape ? (
          <>
            <div
              ref={bustsRef}
              className={`hero-busts named ${heroId ? '' : 'away'}`}
              onTransitionEnd={onFlipDone}
            >
              {HEROES.map(h => (
                <button
                  key={h.id}
                  className={`hero-bust-btn ${selectedClass === h.id ? 'selected' : ''}`}
                  onClick={() => pick(h.id)}
                  aria-label={t(`hero.classes.${h.id}.name`)}
                >
                  <HeroBust sheet={h.sheet} selected={selectedClass === h.id} />
                  <span className="hero-picker-name">{t(`hero.classes.${h.id}.name`)}</span>
                </button>
              ))}
            </div>

            {heroId && (
              <>
                <h2 className="hero-name">{t(`hero.classes.${heroId}.name`)}</h2>
                <p className="hero-desc">{t(`hero.classes.${heroId}.desc`)}</p>
              </>
            )}
          </>
        ) : heroId ? (
          <>
            <div className="hero-busts">
              {HEROES.map(h => (
                <button
                  key={h.id}
                  className={`hero-bust-btn ${selectedClass === h.id ? 'selected' : ''}`}
                  onClick={() => pick(h.id)}
                  aria-label={t(`hero.classes.${h.id}.name`)}
                >
                  <HeroBust sheet={h.sheet} selected={selectedClass === h.id} />
                </button>
              ))}
            </div>

            <h2 className="hero-name">{t(`hero.classes.${heroId}.name`)}</h2>
            <p className="hero-desc">{t(`hero.classes.${heroId}.desc`)}</p>
          </>
        ) : (
          <div className="hero-picker">
            {HEROES.map(h => (
              <button
                key={h.id}
                className="hero-picker-btn"
                onClick={() => pick(h.id)}
                aria-label={t(`hero.classes.${h.id}.name`)}
              >
                <HeroBust sheet={h.sheet} scale={PICKER_SCALE} />
                <span className="hero-picker-name">{t(`hero.classes.${h.id}.name`)}</span>
              </button>
            ))}
          </div>
        )}

        <div className="hero-options">
          {showDifficulty && (
            <div className="hero-difficulty">
              <span className="hero-opt-label">{t('hero.difficulty')}</span>
              <div className="hero-diff-btns">
                {['easy', 'normal', 'hard'].map(d => (
                  <button
                    key={d}
                    className={`hero-diff-btn ${difficulty === d ? 'active' : ''}`}
                    onClick={() => { AudioManager.play('CLICK'); setDifficulty(d); }}
                  >
                    {t(`hero.${d}`)}
                  </button>
                ))}
              </div>
            </div>
          )}
          <label className="hero-challenge-toggle">
            <input
              type="checkbox"
              checked={strongerBosses}
              onChange={(e) => { AudioManager.play('CLICK'); setStrongerBosses(e.target.checked); }}
            />
            {t('hero.strongerBosses')}
          </label>
          <input
            autoFocus
            className="hero-name-input"
            type="text"
            placeholder={t('hero.namePlaceholder')}
            maxLength={20}
            value={playerName}
            onChange={e => setPlayerName(e.target.value)}
          />
        </div>

        <button className="hero-start-btn" onClick={start} disabled={!selectedClass}>
          <Icon name="ENTER" scale={2} />
          <span>{t('hero.enterDungeon')}</span>
        </button>
      </div>
    </div>
  );
};

export default CharacterSelection;
