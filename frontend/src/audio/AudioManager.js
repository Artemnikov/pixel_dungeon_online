const atkBowSound = new URL('../assets/pixel-dungeon/audio/atk_bow.mp3', import.meta.url).href;
const zapSound = new URL('../assets/pixel-dungeon/audio/zap.mp3', import.meta.url).href;
const hitMagicSound = new URL('../assets/pixel-dungeon/audio/hit_magic.mp3', import.meta.url).href;
const stepSound = new URL('../assets/pixel-dungeon/audio/step.mp3', import.meta.url).href;
const hitArrowSound = new URL('../assets/pixel-dungeon/audio/hit_arrow.mp3', import.meta.url).href;
const hitSlashSound = new URL('../assets/pixel-dungeon/audio/hit_slash.mp3', import.meta.url).href;
const hitBodySound = new URL('../assets/pixel-dungeon/audio/hit.mp3', import.meta.url).href;
const hitStrongSound = new URL('../assets/sounds/hit_strong.mp3', import.meta.url).href;
const hitStabSound = new URL('../assets/sounds/hit_stab.mp3', import.meta.url).href;
const hitCrushSound = new URL('../assets/sounds/hit_crush.mp3', import.meta.url).href;
const hitParrySound = new URL('../assets/sounds/hit_parry.mp3', import.meta.url).href;
const healthWarnSound = new URL('../assets/pixel-dungeon/audio/health_warn.mp3', import.meta.url).href;
const healthCriticalSound = new URL('../assets/pixel-dungeon/audio/health_critical.mp3', import.meta.url).href;
const clickSound = new URL('../assets/pixel-dungeon/audio/click.mp3', import.meta.url).href;
const itemSound = new URL('../assets/sounds/item.mp3', import.meta.url).href;
const deathSound = new URL('../assets/sounds/death.mp3', import.meta.url).href;
const secretSound = new URL('../assets/sounds/secret.mp3', import.meta.url).href;
const waterStepSound = new URL('../assets/sounds/water.mp3', import.meta.url).href;
const grassStepSound = new URL('../assets/sounds/grass.mp3', import.meta.url).href;
const plantSound = new URL('../assets/sounds/plant.mp3', import.meta.url).href;
const woodStepSound = new URL('../assets/sounds/sturdy.mp3', import.meta.url).href;
const descendSound = new URL('../assets/pixel-dungeon/audio/descend.mp3', import.meta.url).href;
const fallingSound = new URL('../assets/pixel-dungeon/audio/falling.mp3', import.meta.url).href;
const drinkSound = new URL('../assets/sounds/drink.mp3', import.meta.url).href;
const eatSound = new URL('../assets/sounds/eat.mp3', import.meta.url).href;
const throwSound = new URL('../assets/sounds/miss.mp3', import.meta.url).href;
const levelUpSound = new URL('../assets/sounds/levelup.mp3', import.meta.url).href;
const trapSound = new URL('../assets/sounds/trap.mp3', import.meta.url).href;
const chargeupSound = new URL('../assets/pixel-dungeon/audio/chargeup.mp3', import.meta.url).href;
const burningSound = new URL('../assets/pixel-dungeon/audio/burning.mp3', import.meta.url).href;
const bossSound = new URL('../assets/pixel-dungeon/audio/boss.mp3', import.meta.url).href;
const ghostSound = new URL('../assets/pixel-dungeon/audio/ghost.mp3', import.meta.url).href;
const alertSound = new URL('../assets/pixel-dungeon/audio/alert.mp3', import.meta.url).href;
const unlockSound = new URL('../assets/sounds/unlock.mp3', import.meta.url).href;
const lockedSound = new URL('../assets/sounds/locked.mp3', import.meta.url).href;
const readSound = new URL('../assets/sounds/read.mp3', import.meta.url).href;
const raySound = new URL('../assets/sounds/ray.mp3', import.meta.url).href;
const blastSound = new URL('../assets/sounds/blast.mp3', import.meta.url).href;
const lightningSound = new URL('../assets/sounds/lightning.mp3', import.meta.url).href;
const puffSound = new URL('../assets/sounds/puff.mp3', import.meta.url).href;
const goldSound = new URL('../assets/pixel-dungeon/audio/gold.mp3', import.meta.url).href;
const dewdropSound = new URL('../assets/pixel-dungeon/audio/dewdrop.mp3', import.meta.url).href;
const lullabySound = new URL('../assets/sounds/lullaby.mp3', import.meta.url).href;
const challengeSound = new URL('../assets/sounds/challenge.mp3', import.meta.url).href;
const teleportSound = new URL('../assets/sounds/teleport.mp3', import.meta.url).href;
const meldSound = new URL('../assets/sounds/meld.mp3', import.meta.url).href;
const gasSound = new URL('../assets/sounds/gas.mp3', import.meta.url).href;
const shatterSound = new URL('../assets/sounds/shatter.mp3', import.meta.url).href;
const bonesSound = new URL('../assets/sounds/bones.mp3', import.meta.url).href;
const sheepSound = new URL('../assets/sounds/sheep.mp3', import.meta.url).href;
const tombSound = new URL('../assets/sounds/tomb.mp3', import.meta.url).href;
const chainsSound = new URL('../assets/sounds/chains.mp3', import.meta.url).href;
const cursedSound = new URL('../assets/sounds/cursed.mp3', import.meta.url).href;
import { effectiveSfxVolume, subscribe } from '../menu/menuSettings';
import { isGrassTile } from '../constants';

// Per-sound minimum replay interval, enforced manager-side so a single game
// moment (e.g. a fire blob igniting N entities at once) can never stack plays.
const MIN_PLAY_INTERVAL_MS = {
    BURNING: 1000,
    MIMIC: 300,
};

class AudioManager {
    constructor() {
        this.sounds = {};
        this.enabled = true;
        this.loadedSounds = {};

        if (typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext)) {
            this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this.masterGain = this.audioCtx.createGain();
            this.masterGain.gain.value = effectiveSfxVolume();
            this.masterGain.connect(this.audioCtx.destination);
            subscribe(() => { if (this.masterGain) this.masterGain.gain.value = effectiveSfxVolume(); });
        } else {
            this.audioCtx = null;
            this.masterGain = null;
        }

        this.loadSound('ATTACK_BOW', atkBowSound);
        this.loadSound('THROW', throwSound);
        this.loadSound('MISS', throwSound);
        this.loadSound('ATTACK_MAGIC', zapSound);
        this.loadSound('HIT_MAGIC', hitMagicSound);
        this.loadSound('STEP', stepSound);
        this.loadSound('STEP_WATER', waterStepSound);
        this.loadSound('STEP_GRASS', grassStepSound);
        this.loadSound('PLANT', plantSound);
        this.loadSound('STEP_WOOD', woodStepSound);
        this.loadSound('HIT_ARROW', hitArrowSound);
        this.loadSound('HIT_SLASH', hitSlashSound);
        this.loadSound('HIT_STAB', hitStabSound);
        this.loadSound('HIT_CRUSH', hitCrushSound);
        this.loadSound('HIT_PARRY', hitParrySound);
        this.loadSound('HIT_STRONG', hitStrongSound);
        this.loadSound('HIT_BODY', hitBodySound);
        this.loadSound('HEALTH_WARN', healthWarnSound);
        this.loadSound('HEALTH_CRITICAL', healthCriticalSound);
        this.loadSound('CLICK', clickSound);
        this.loadSound('PICKUP', itemSound);
        this.loadSound('DEATH', deathSound);
        this.loadSound('SECRET', secretSound);
        this.loadSound('STAIRS_DOWN', descendSound);
        this.loadSound('FALLING', fallingSound);
        this.loadSound('DRINK', drinkSound);
        this.loadSound('EAT', eatSound);
        this.loadSound('LEVELUP', levelUpSound);
        this.loadSound('TRAP', trapSound);
        this.loadSound('CHARGEUP', chargeupSound);
        this.loadSound('BURNING', burningSound);
        this.loadSound('BOSS', bossSound);
        this.loadSound('GHOST', ghostSound);
        this.loadSound('ALERT', alertSound);
        this.loadSound('UNLOCK', unlockSound);
        this.loadSound('LOCKED', lockedSound);
        this.loadSound('READ', readSound);
        this.loadSound('RAY', raySound);
        this.loadSound('BLAST', blastSound);
        this.loadSound('LIGHTNING', lightningSound);
        this.loadSound('PUFF', puffSound);
        this.loadSound('GOLD', goldSound);
        this.loadSound('DEWDROP', dewdropSound);
        this.loadSound('LULLABY', lullabySound);
        this.loadSound('CHALLENGE', challengeSound);
        this.loadSound('TELEPORT', teleportSound);
        this.loadSound('MELD', meldSound);
        this.loadSound('GAS', gasSound);
        this.loadSound('SHATTER', shatterSound);
        this.loadSound('BONES', bonesSound);
        this.loadSound('SHEEP', sheepSound);
        this.loadSound('TOMB', tombSound);
        this.loadSound('CHAINS', chainsSound);
        this.loadSound('CURSED', cursedSound);

        const doorUrl = new URL('../assets/sounds/door_open.mp3', import.meta.url).href;
        if (doorUrl) this.loadSound('DOOR_OPEN', doorUrl);
    }

    async loadSound(name, src) {
        if (!this.audioCtx || typeof fetch === 'undefined') return;
        try {
            const response = await fetch(src);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
            this.loadedSounds[name] = audioBuffer;
        } catch (e) {
            console.error(`[Audio] Failed to load sound ${name}:`, e);
        }
    }

    play(soundName, rate = 1.0, throttleMs = 0) {
        if (!this.enabled || !this.audioCtx) return;
        const minInterval = Math.max(throttleMs, MIN_PLAY_INTERVAL_MS[soundName] || 0);
        if (minInterval > 0) {
            if (!this._lastPlayedAt) this._lastPlayedAt = {};
            const now = performance.now();
            if (now - (this._lastPlayedAt[soundName] || 0) < minInterval) return;
            this._lastPlayedAt[soundName] = now;
        }
        this.masterGain.gain.value = effectiveSfxVolume();
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }

        if (this.loadedSounds[soundName]) {
            this.playSoundBuffer(this.loadedSounds[soundName], rate);
            return;
        }

        // Fallback to synthesized sounds for unmatched names
        switch (soundName) {
            case 'MOVE':
                this.playTone(200, 'sine', 0.05, 0.1);
                break;
            case 'ZAP':
                this.playTone(800, 'sine', 0.15, 0.12);
                this.playTone(500, 'sine', 0.12, 0.10, 0.03);
                this.playNoise(0.08, 0.1, 'highpass', 600);
                break;
            case 'ATTACK':
                this.playTone(100, 'sawtooth', 0.1, 0.3); // aggressive sound
                this.playTone(150, 'sawtooth', 0.1, 0.3, 0.05);
                break;
            case 'DAMAGE':
                this.playTone(100, 'square', 0.2, 0.3);
                this.playTone(80, 'square', 0.2, 0.3, 0.1);
                break;
            case 'DEATH':
                this.playTone(150, 'sawtooth', 0.5, 0.5);
                this.playTone(100, 'sawtooth', 0.5, 0.5, 0.2);
                this.playTone(50, 'sawtooth', 0.8, 0.8, 0.4);
                break;
            case 'PICKUP':
                this.playTone(400, 'sine', 0.1, 0.1);
                this.playTone(600, 'sine', 0.1, 0.1, 0.05);
                break;
            case 'DRINK':
                this.playTone(300, 'triangle', 0.1, 0.1);
                this.playTone(350, 'triangle', 0.1, 0.1, 0.1);
                this.playTone(400, 'triangle', 0.2, 0.2, 0.2);
                break;
            case 'EAT':
                this.playNoise(0.06, 0.18, 'bandpass', 900);
                this.playTone(180, 'triangle', 0.1, 0.12, 0.1);
                break;
            case 'STAIRS_DOWN':
                this.playTone(200, 'sine', 0.5, 0.5);
                this.playTone(150, 'sine', 0.5, 0.5, 0.2);
                this.playTone(100, 'sine', 0.5, 0.5, 0.4);
                break;
            case 'REVIVE':
                this.playTone(300, 'sine', 0.5, 0.5);
                this.playTone(400, 'sine', 0.5, 0.5, 0.2);
                this.playTone(500, 'sine', 0.5, 0.5, 0.4);
                break;
            case 'DOOR_OPEN':
                this.playTone(300, 'triangle', 0.15, 0.2);
                this.playTone(200, 'triangle', 0.25, 0.15, 0.1);
                break;
            case 'CHARMS':
                this.playTone(660, 'sine', 0.15, 0.15);
                this.playTone(880, 'sine', 0.15, 0.15, 0.08);
                this.playTone(1100, 'sine', 0.12, 0.2, 0.16);
                break;
            case 'LOCKED':
                this.playTone(190, 'triangle', 0.10, 0.25);
                this.playTone(165, 'triangle', 0.10, 0.2, 0.12);
                this.playTone(1100, 'square', 0.04, 0.06);
                break;
            case 'CURSE':
                this.playTone(120, 'sawtooth', 0.3, 0.4);
                this.playTone(90, 'sawtooth', 0.4, 0.3, 0.1);
                this.playNoise(0.2, 0.15, 'lowpass', 400);
                break;
            case 'HEAL':
                this.playTone(500, 'sine', 0.2, 0.15);
                this.playTone(700, 'sine', 0.2, 0.15, 0.1);
                this.playTone(900, 'sine', 0.3, 0.1, 0.2);
                break;
            case 'MIMIC':
                this.playTone(280 * rate, 'sawtooth', 0.14 / Math.max(0.1, rate), 0.35);
                this.playTone(420 * rate, 'sawtooth', 0.12 / Math.max(0.1, rate), 0.3, 0.04 / Math.max(0.1, rate));
                this.playTone(320 * rate, 'sawtooth', 0.16 / Math.max(0.1, rate), 0.35, 0.10 / Math.max(0.1, rate));
                this.playTone(540 * rate, 'square', 0.10 / Math.max(0.1, rate), 0.25, 0.16 / Math.max(0.1, rate));
                this.playNoise(0.24 / Math.max(0.1, rate), 0.2, 'bandpass', 1200 * rate);
                break;
            default:
                break;
        }
    }

    playStep(tileType) {
        if (!this.enabled || !this.audioCtx || !this.masterGain) return;
        this.masterGain.gain.value = effectiveSfxVolume();
        const rate = 0.9 + Math.random() * 0.2;
        let key = 'STEP';
        if (tileType === 7) key = 'STEP_WATER';
        else if (isGrassTile(tileType)) key = 'STEP_GRASS';
        else if (tileType === 6) key = 'STEP_WOOD';
        if (this.loadedSounds[key]) {
            this.playSoundBuffer(this.loadedSounds[key], rate);
        } else {
            this.playTone(200, 'sine', 0.05, 0.1);
        }
    }

    playNoise(duration, vol, filterType, filterFreq) {
        const bufferSize = this.audioCtx.sampleRate * duration;
        const buffer = this.audioCtx.createBuffer(1, bufferSize, this.audioCtx.sampleRate);
        const data = buffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.audioCtx.createBufferSource();
        noise.buffer = buffer;

        const gain = this.audioCtx.createGain();
        gain.gain.setValueAtTime(vol, this.audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + duration);

        if (filterType) {
            const filter = this.audioCtx.createBiquadFilter();
            filter.type = filterType;
            filter.frequency.value = filterFreq;
            noise.connect(filter);
            filter.connect(gain);
        } else {
            noise.connect(gain);
        }

        gain.connect(this.masterGain);
        noise.start();
    }

    playSoundBuffer(buffer, rate = 1.0) {
        const source = this.audioCtx.createBufferSource();
        source.buffer = buffer;
        source.playbackRate.value = rate;
        source.connect(this.masterGain);
        source.start(0);
    }

    playTone(freq, type, duration, vol, delay = 0) {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime + delay);

        gain.gain.setValueAtTime(vol, this.audioCtx.currentTime + delay);
        gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + delay + duration);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(this.audioCtx.currentTime + delay);
        osc.stop(this.audioCtx.currentTime + delay + duration);
    }
}

export default new AudioManager();
