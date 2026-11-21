import { useEffect, useRef } from 'react';
import { getCurrentMusicId, playMusic, stopMusic } from './musicPlayer';

const musicModules = import.meta.glob('../assets/pixel-dungeon/themes/*.ogg', { eager: true, query: '?url' });
const MUSIC = {};
for (const [path, mod] of Object.entries(musicModules)) {
  const name = path.split('/').pop().replace(/\.ogg$/, '');
  MUSIC[name] = mod.default;
}

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

export default function useMusicByDepth({ enabled, menu, depth, bossFightActive, bossBleeding, bossLurking, tense, amuletObtained }) {
  const playlist = useRef([]);

  useEffect(() => {
    if (!enabled) { stopMusic(); return; }

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
    } else if (bossLurking && isBossFloor) {
      // SPD SewerBossLevel.playLevelMusic(): ambient track silenced while
      // the boss is alive but hasn't been engaged yet.
      musicId = 'silence';
    } else if (depth === 25) {
      // HallsBossLevel: unseal() fades into THEME_FINALE; with the Amulet the
      // level is silent (playLevelMusic -> Music.end()).
      if (amuletObtained) {
        musicId = 'silence';
      } else {
        musicId = 'theme_finale';
        track = 'theme_finale';
        loop = true;
      }
    } else {
      musicId = `play:${depth}`;
      genPlaylist = true;
    }

    if (getCurrentMusicId() === musicId) return;

    if (musicId === 'silence') { stopMusic(); return; }

    if (genPlaylist) {
      playlist.current = menu ? buildPlaylist(['theme_1', 'theme_2']) : buildPlaylist(b.tracks);
    } else {
      playlist.current = [];
    }

    const playNext = () => {
      if (playlist.current.length === 0 && genPlaylist) {
        playlist.current = menu ? buildPlaylist(['theme_1', 'theme_2']) : buildPlaylist(b.tracks);
      }
      const name = playlist.current.shift();
      if (!name) return;
      const url = MUSIC[name];
      if (!url) { playNext(); return; }

      const el = playMusic(musicId, url, { loop });
      el.addEventListener('ended', () => { if (getCurrentMusicId() === musicId) playNext(); });
    };

    if (track) {
      const url = MUSIC[track];
      if (url) playMusic(musicId, url, { loop });
    } else {
      playNext();
    }
  }, [enabled, menu, depth, bossFightActive, bossBleeding, bossLurking, tense, amuletObtained]);
}
