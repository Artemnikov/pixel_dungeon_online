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
import sewersSplash from './assets/pixel-dungeon/splashes/sewers.jpg';
import cavesSplash from './assets/pixel-dungeon/splashes/caves.jpg';
import prisonSplash from './assets/pixel-dungeon/splashes/prison.jpg';
import citySplash from './assets/pixel-dungeon/splashes/city.jpg';

import warriorSheet from './assets/pixel-dungeon/sprites/warrior.png';
import mageSheet from './assets/pixel-dungeon/sprites/mage.png';
import rogueSheet from './assets/pixel-dungeon/sprites/rogue.png';
import huntressSheet from './assets/pixel-dungeon/sprites/huntress.png';
import duelistSheet from './assets/pixel-dungeon/sprites/duelist.png';
import clericSheet from './assets/pixel-dungeon/sprites/cleric.png';
import ratSheet from './assets/pixel-dungeon/sprites/rat.png';
import gnollSheet from './assets/pixel-dungeon/sprites/gnoll.png';
import skeletonSheet from './assets/pixel-dungeon/sprites/skeleton.png';
import thiefSheet from './assets/pixel-dungeon/sprites/thief.png';
import necromancerSheet from './assets/pixel-dungeon/sprites/necromancer.png';

const HERO_FRAME = { x: 0, y: 90, w: 12, h: 15 };
const SHEET_W = 256;
const PICKER_SCALE = 6;

function CharacterBust({ charDef, scale = 3, selected }) {
  const f = charDef.frame || HERO_FRAME;
  const sw = charDef.sheetW || SHEET_W;
  return (
    <span
      className="hero-bust"
      style={{
        width: f.w * scale,
        height: f.h * scale,
        backgroundImage: `url(${charDef.sheet})`,
        backgroundRepeat: 'no-repeat',
        backgroundSize: `${sw * scale}px auto`,
        backgroundPosition: `-${f.x * scale}px -${f.y * scale}px`,
        imageRendering: 'pixelated',
        filter: selected ? 'none' : 'brightness(0.6)',
      }}
    />
  );
}

function RosterGrid({ rows, selectedClass, onPick, showNames = true, scale = 3, isPicker = false, t }) {
  const rowClass = isPicker ? 'hero-picker-row' : 'hero-busts-row';
  const btnClass = isPicker ? 'hero-picker-btn' : 'hero-bust-btn';

  return rows.map((row, rowIdx) => (
    <div key={rowIdx} className={rowClass}>
      {row.map(h => (
        <button
          key={h.id}
          className={`${btnClass} ${selectedClass === h.id ? 'selected' : ''}`}
          onClick={() => onPick(h.id)}
          aria-label={t(`hero.classes.${h.id}.name`)}
        >
          <CharacterBust charDef={h} scale={scale} selected={selectedClass === h.id} />
          {showNames && <span className="hero-picker-name">{t(`hero.classes.${h.id}.name`)}</span>}
        </button>
      ))}
    </div>
  ));
}

const HERO_ROSTER = [
  { id: 'warrior', sheet: warriorSheet, splash: warriorSplash, frame: HERO_FRAME },
  { id: 'mage', sheet: mageSheet, splash: mageSplash, frame: HERO_FRAME },
  { id: 'rogue', sheet: rogueSheet, splash: rogueSplash, frame: HERO_FRAME },
  { id: 'huntress', sheet: huntressSheet, splash: huntressSplash, frame: HERO_FRAME },
  { id: 'duelist', sheet: duelistSheet, splash: duelistSplash, frame: HERO_FRAME },
  { id: 'cleric', sheet: clericSheet, splash: clericSplash, frame: HERO_FRAME },
];

const MONSTER_ROSTER = [
  { id: 'gnoll', sheet: gnollSheet, splash: cavesSplash, frame: { x: 0, y: 0, w: 12, h: 15 } },
  { id: 'skeleton', sheet: skeletonSheet, splash: prisonSplash, frame: { x: 0, y: 0, w: 12, h: 15 } },
  { id: 'thief', sheet: thiefSheet, splash: prisonSplash, frame: { x: 0, y: 0, w: 12, h: 15 } },
  { id: 'rat', sheet: ratSheet, splash: sewersSplash, frame: { x: 0, y: 0, w: 16, h: 15 } },
  { id: 'necromancer', sheet: necromancerSheet, splash: citySplash, frame: { x: 0, y: 0, w: 16, h: 16 } },
];

const FACTION_ROSTERS = {
  player: [HERO_ROSTER],
  dungeon: [HERO_ROSTER, MONSTER_ROSTER],
};

const CharacterSelection = ({ onSelect, showDifficulty = true, allowDungeon = true, initialFaction = 'player' }) => {
  const { t } = useTranslation();
  const [faction, setFaction] = useState(initialFaction || 'player');
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

  const rosterRows = FACTION_ROSTERS[faction] || FACTION_ROSTERS.player;
  const availableList = rosterRows.flat();
  const charDef = availableList.find(h => h.id === selectedClass);
  const heroId = charDef ? charDef.id : null;

  useParallaxBackground(parallaxRef);

  useEffect(() => {
    const onResize = () => setLandscape(window.innerWidth > window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const changeFaction = (f) => {
    AudioManager.play('CLICK');
    setFaction(f);
    setSelectedClass(null);
  };

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
    onSelect(selectedClass, difficulty, playerName.trim(), strongerBosses, faction);
  };

  return (
    <div className={`hero-select ${landscape ? 'landscape' : 'portrait'} ${heroId ? 'picked' : ''}`}>
      <canvas ref={parallaxRef} className="hero-parallax" />
      {charDef?.splash && <img key={charDef.id} className="hero-splash" src={charDef.splash} alt="" />}
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
              <RosterGrid
                rows={rosterRows}
                selectedClass={selectedClass}
                onPick={pick}
                showNames={true}
                t={t}
              />
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
              <RosterGrid
                rows={rosterRows}
                selectedClass={selectedClass}
                onPick={pick}
                showNames={false}
                t={t}
              />
            </div>

            <h2 className="hero-name">{t(`hero.classes.${heroId}.name`)}</h2>
            <p className="hero-desc">{t(`hero.classes.${heroId}.desc`)}</p>
          </>
        ) : (
          <div className="hero-picker">
            <RosterGrid
              rows={rosterRows}
              selectedClass={selectedClass}
              onPick={pick}
              showNames={true}
              scale={PICKER_SCALE}
              isPicker={true}
              t={t}
            />
          </div>
        )}

        <div className="hero-options">
          {allowDungeon && (
            <div className="hero-difficulty">
              <span className="hero-opt-label">{t('hero.faction')}</span>
              <div className="hero-diff-btns">
                <button
                  className={`hero-diff-btn ${faction === 'player' ? 'active' : ''}`}
                  onClick={() => changeFaction('player')}
                >
                  {t('hero.factionHeroes')}
                </button>
                <button
                  className={`hero-diff-btn ${faction === 'dungeon' ? 'active' : ''}`}
                  onClick={() => changeFaction('dungeon')}
                >
                  {t('hero.factionDungeon')}
                </button>
              </div>
            </div>
          )}

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
