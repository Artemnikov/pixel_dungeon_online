import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import './heroSelect.css';
import AudioManager from './audio/AudioManager';
import Icon from './menu/Icon';
import { effectiveMusicVolume, subscribe } from './menu/menuSettings';

import themeMusic from './assets/pixel-dungeon/themes/theme_1.ogg';
import descendSound from './assets/pixel-dungeon/audio/descend.mp3';

import warriorSplash from './assets/pixel-dungeon/splashes/warrior.jpg';
import mageSplash from './assets/pixel-dungeon/splashes/mage.jpg';
import rogueSplash from './assets/pixel-dungeon/splashes/rogue.jpg';
import huntressSplash from './assets/pixel-dungeon/splashes/huntress.jpg';

import warriorSheet from './assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from './assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from './assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from './assets/pixel-dungeon/sprites/huntress.png';

const HERO_FRAME = { x: 0, y: 90, w: 12, h: 15 };
const SHEET_W = 256, SHEET_H = 128;

const HERO_IDS = ['warrior', 'mage', 'rogue', 'huntress'];

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

const CharacterSelection = ({ onSelect }) => {
  const { t } = useTranslation();
  const [selectedClass, setSelectedClass] = useState('warrior');
  const [difficulty, setDifficulty] = useState('normal');
  const [strongerBosses, setStrongerBosses] = useState(false);
  const [playerName, setPlayerName] = useState('');
  const [landscape, setLandscape] = useState(
    typeof window !== 'undefined' ? window.innerWidth > window.innerHeight : true
  );
  const audioRef = useRef(null);

  const heroId = HERO_IDS.includes(selectedClass) ? selectedClass : 'warrior';

  const HEROES = [
    { id: 'warrior', sheet: warriorSheet, splash: warriorSplash },
    { id: 'mage', sheet: mageSheet, splash: mageSplash },
    { id: 'rogue', sheet: rogueSheet, splash: rogueSplash },
    { id: 'huntress', sheet: huntressSheet, splash: huntressSplash },
  ];
  const hero = HEROES.find(h => h.id === heroId) || HEROES[0];

  useEffect(() => {
    const onResize = () => setLandscape(window.innerWidth > window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    const audio = new Audio(themeMusic);
    audio.loop = true;
    audio.volume = effectiveMusicVolume();
    audioRef.current = audio;

    const tryPlay = () => { audio.play().catch(() => {}); };
    tryPlay();
    document.addEventListener('pointerdown', tryPlay, { once: true });
    const unsub = subscribe(() => { audio.volume = effectiveMusicVolume(); });

    return () => {
      unsub();
      document.removeEventListener('pointerdown', tryPlay);
      audio.pause();
      audio.currentTime = 0;
    };
  }, []);

  const pick = (id) => { AudioManager.play('CLICK'); setSelectedClass(id); };

  const start = () => {
    AudioManager.play('CLICK');
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.currentTime = 0; }
    new Audio(descendSound).play().catch(() => {});
    onSelect(selectedClass, difficulty, playerName.trim(), strongerBosses);
  };

  return (
    <div className={`hero-select ${landscape ? 'landscape' : 'portrait'}`}>
      <img key={hero.id} className="hero-splash" src={hero.splash} alt="" />
      <div className="hero-vignette-left" />
      <div className="hero-vignette-right" />

      <div className="hero-ui">
        <h1 className="hero-title">{t('hero.title')}</h1>

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

        <div className="hero-options">
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
          <label className="hero-challenge-toggle">
            <input
              type="checkbox"
              checked={strongerBosses}
              onChange={(e) => { AudioManager.play('CLICK'); setStrongerBosses(e.target.checked); }}
            />
            {t('hero.strongerBosses')}
          </label>
          <input
            className="hero-name-input"
            type="text"
            placeholder={t('hero.namePlaceholder')}
            maxLength={20}
            value={playerName}
            onChange={e => setPlayerName(e.target.value)}
          />
        </div>

        <button className="hero-start-btn" onClick={start}>
          <Icon name="ENTER" scale={2} />
          <span>{t('hero.enterDungeon')}</span>
        </button>
      </div>
    </div>
  );
};

export default CharacterSelection;
