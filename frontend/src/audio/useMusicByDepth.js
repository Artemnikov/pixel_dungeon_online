import { useEffect, useRef } from 'react';
import { effectiveMusicVolume, subscribe } from '../menu/menuSettings';

const musicModules = import.meta.glob('../assets/pixel-dungeon/themes/*.ogg', { eager: true, query: '?url' });
const MUSIC = {};
for (const [path, mod] of Object.entries(musicModules)) {
  const name = path.split('/').pop().replace(/\.ogg$/, '');
  MUSIC[name] = mod.default;
}

const FADE_MS = 200;
const FADE_STEPS = 20;

const BIOME = (tracks, tense, boss, bossFinale) => ({ tracks, tense, boss, bossFinale });

const BIOMES = {
  sewers: BIOME(
    ['sewers_1','sewers_2','sewers_2','sewers_1','sewers_3','sewers_3'],
    'sewers_tense', 'sewers_boss', null
  ),
  prison: BIOME(
    ['prison_1','prison_2','prison_2','prison_1','prison_3','prison_3'],
    'prison_tense', 'prison_boss', null
  ),
  caves: BIOME(
    ['caves_1','caves_2','caves_2','caves_1','caves_3','caves_3'],
    'caves_tense', 'caves_boss', 'caves_boss_finale'
  ),
  city: BIOME(
    ['city_1','city_2','city_2','city_1','city_3','city_3'],
    'city_tense', 'city_boss', 'city_boss_finale'
  ),
  halls: BIOME(
    ['halls_1','halls_2','halls_2','halls_1','halls_3','halls_3'],
    'halls_tense', 'halls_boss', 'halls_boss_finale'
  ),
};

function biome(d) {
  return d >= 21 ? BIOMES.halls : d >= 16 ? BIOMES.city : d >= 11 ? BIOMES.caves : d >= 6 ? BIOMES.prison : BIOMES.sewers;
}

function buildPlaylist(tracks) {
  const q = [...tracks];
  for (let i = q.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [q[i], q[j]] = [q[j], q[i]]; }
  return q;
}

export default function useMusicByDepth({ enabled, menu, depth, bossFightActive, bossBleeding, tense, amuletObtained, musicRef }) {
  const playlist = useRef([]);
  const fadeTimer = useRef(null);
  const volSub = useRef(null);

  useEffect(() => {
    if (!enabled) { musicRef.current = null; return; }

    const isBossFloor = depth === 5 || depth === 10 || depth === 15 || depth === 20 || depth === 25;
    const b = biome(depth);

    let musicId;
    let track = null;
    let loop = false;
    let genPlaylist = false;

    if (menu) {
      musicId = 'menu';
      genPlaylist = true;
    } else if (depth === 1 && amuletObtained) {
      musicId = 'theme_finale';
      track = 'theme_finale';
      loop = true;
    } else if (tense) {
      musicId = `tense:${b.tense}`;
      track = b.tense;
      loop = true;
    } else if (bossFightActive && isBossFloor) {
      const t = bossBleeding && b.bossFinale ? b.bossFinale : b.boss;
      musicId = `boss:${t}`;
      track = t;
      loop = true;
    } else {
      musicId = `play:${depth}`;
      genPlaylist = true;
    }

    if (musicRef.current?._mid === musicId) return;

    const outgoing = musicRef.current;
    musicRef.current = null;

    if (genPlaylist) {
      playlist.current = menu ? buildPlaylist(['theme_1', 'theme_2']) : buildPlaylist(b.tracks);
    } else {
      playlist.current = [];
    }

    let incomingFade = outgoing ? 0 : 1;
    let outgoingFade = outgoing ? 1 : 0;

    const applyVol = () => {
      const vol = effectiveMusicVolume();
      if (musicRef.current) musicRef.current.volume = (musicRef.current === outgoing ? outgoingFade : incomingFade) * vol;
      if (outgoing && musicRef.current !== outgoing) outgoing.volume = outgoingFade * vol;
    };

    const playNext = () => {
      if (playlist.current.length === 0 && genPlaylist) {
        playlist.current = menu ? buildPlaylist(['theme_1', 'theme_2']) : buildPlaylist(b.tracks);
      }
      const name = playlist.current.shift();
      if (!name) return;
      const url = MUSIC[name];
      if (!url) { playNext(); return; }

      const el = new Audio(url);
      el.loop = loop;
      el._mid = musicId;
      musicRef.current = el;
      applyVol();
      el.play().catch(() => {});
      el.addEventListener('ended', () => { if (el._mid === musicId) playNext(); });
    };

    if (track) {
      const url = MUSIC[track];
      if (url) {
        const el = new Audio(url);
        el.loop = loop;
        el._mid = musicId;
        musicRef.current = el;
        applyVol();
        el.play().catch(() => {});
      }
    } else {
      playNext();
    }

    // crossfade
    if (outgoing) {
      let step = 0;
      fadeTimer.current = setInterval(() => {
        step++;
        const t = step / FADE_STEPS;
        outgoingFade = Math.max(0, 1 - t);
        incomingFade = Math.min(1, t);
        applyVol();
        if (step >= FADE_STEPS) {
          clearInterval(fadeTimer.current);
          fadeTimer.current = null;
          outgoing.pause();
          outgoing.currentTime = 0;
        }
      }, FADE_MS / FADE_STEPS);
    }

    volSub.current = subscribe(() => {
      const v = effectiveMusicVolume();
      if (musicRef.current) musicRef.current.volume = (musicRef.current === outgoing ? outgoingFade : incomingFade) * v;
      if (outgoing && musicRef.current !== outgoing) outgoing.volume = outgoingFade * v;
    });

    return () => {
      if (volSub.current) volSub.current();
      if (fadeTimer.current) clearInterval(fadeTimer.current);
      if (musicRef.current) { musicRef.current.pause(); musicRef.current.currentTime = 0; }
      if (outgoing && outgoing !== musicRef.current) { outgoing.pause(); outgoing.currentTime = 0; }
      musicRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, menu, depth, bossFightActive, bossBleeding, tense, amuletObtained]);
}
