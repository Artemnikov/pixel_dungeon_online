import { TILE_SIZE, ENTITY_LIFT } from '../../constants';
import {
  FRAME_W,
  FRAME_H,
  SCORPIO_FW,
   GNOLL_FW,
   GNOLL_FH,
   SHAMAN_FW,
   SHAMAN_FH,
   SNAKE_FW,
  SNAKE_FH,
  SNAKE_DEST,
  SKELETON_FW,
  SKELETON_FH,
  SKELETON_DEST,
  THIEF_FW,
  THIEF_FH,
  THIEF_DEST,
   DM100_FW,
   DM100_FH,
   DM100_DEST,
   DM200_FW,
   DM200_FH,
   DM200_DEST,
   GUARD_FW,
  GUARD_FH,
  GUARD_DEST,
  GOO_FW,
  GOO_FH,
  GOO_DEST,
  SLIME_FW,
  SLIME_FH,
  SLIME_DEST,
  WRAITH_FW,
  WRAITH_FH,
  WRAITH_DEST,
  PIRANHA_FW,
  PIRANHA_FH,
  PIRANHA_DEST,
  STATUE_FW,
  STATUE_FH,
  STATUE_DEST,
  GHOUL_FW,
  GHOUL_FH,
  GHOUL_DEST,
  MONK_FW,
  MONK_FH,
  MONK_DEST,
  WARLOCK_FW,
  WARLOCK_FH,
  WARLOCK_DEST,
  GOLEM_FW,
  GOLEM_FH,
  GOLEM_DEST,
  YOG_FW,
  YOG_FH,
  YOG_DEST,
  FIST_FW,
  FIST_FH,
  FIST_DEST,
  EYE_FW,
  EYE_FH,
  EYE_DEST,
  RIPPER_FW,
  RIPPER_FH,
  RIPPER_DEST,
  PYLON_FW,
  PYLON_FH,
  PYLON_DEST,
  TENGU_FW,
  TENGU_FH,
  TENGU_DEST,
  DM300_FW,
  DM300_FH,
  DM300_DEST,
  BRUTE_FW,
  BRUTE_FH,
  BRUTE_DEST,
  SWARM_FW,
  SWARM_FH,
  SWARM_DEST,
   KEEPER_FW,
   KEEPER_FH,
    KEEPER_DEST,
    SHEEP_FW,
    SHEEP_FH,
    SHEEP_DEST,
    IMP_FW,
   IMP_FH,
   IMP_DEST,
   WANDMAKER_FW,
   WANDMAKER_FH,
   WANDMAKER_DEST,
   ROT_HEART_FW,
   ROT_HEART_FH,
   ROT_HEART_DEST,
   ROT_LASHER_FW,
   ROT_LASHER_FH,
   ROT_LASHER_DEST,
   NEWBORN_ELEMENTAL_FW,
   NEWBORN_ELEMENTAL_FH,
   NEWBORN_ELEMENTAL_DEST,
   RATKING_FW,
   RATKING_FH,
   RATKING_DEST,
   GHOST_FW,
   GHOST_FH,
   GHOST_DEST,
   SUCCUBUS_FW,
   SUCCUBUS_FH,
   SUCCUBUS_DEST,
   drawMobSprite,
   getGhostFrame,
   getFetidRatFrame,
   getGnollTricksterFrame,
   getGreatCrabFrame,
  getCrabFrame,
  getHermitCrabFrame,
   getGnollFrame,
   getShamanFrame,
   getGooFrame,
  getSlimeFrame,
  getRatFrame,
  getSnakeFrame,
  getScorpioFrame,
  getSkeletonFrame,
  getThiefFrame,
   getDM100Frame,
   getDM200Frame,
   getGuardFrame,
  getNecromancerFrame,
  getWraithFrame,
  getPiranhaFrame,
  getMimicFrame,
  getBeeFrame,
  getDwarfKingFrame,
  getGhoulFrame,
  getMonkFrame,
  getWarlockFrame,
   getGolemFrame,
   getSpinnerFrame,
   getYogFrame,
  getFistFrame,
  getEyeFrame,
  getRipperFrame,
  getSpawnerFrame,
  getSuccubusFrame,
  getPylonFrame,
  getStatueFrame,
  getTenguFrame,
  getDM300Frame,
  getBruteFrame,
  getBanditFrame,
  getSwarmFrame,
  getKeeperFrame,
  getImpFrame,
  getWandmakerFrame,
  getRotHeartFrame,
  getRotLasherFrame,
  getNewbornElementalFrame,
   getRatKingFrame,
   getSheepFrame,
} from '../mobs';
import { drawShieldHalo } from './shieldHalo';

// Gnoll's 12x15 frame, centered/bottom-aligned in the 32px tile per SPD placement
// (x=(col+0.5)*16-w/2, y=(row+1)*16-h), scaled 2x -> 24x30 at offset (+4,+2).
const GNOLL_DEST = { dx: 4, dy: 2, dw: 24, dh: 30 };
const SHAMAN_DEST = { dx: 4, dy: 2, dw: 24, dh: 30 };

// Track previous ai_state per mob to detect sleeping→hunting transitions.
const prevAiState = {};

// EmoIcons: ai_state → short text shown above mob head (SPD EmoIcon).
const aiStateEmo = {
  hunting: '!',
  fleeing: '!!',
  sleeping: 'zZ',
  wandering: '?',
  lost: '?¿',
};

// Icons.SLEEP in icons.png (Icons.java): uvRectBySize(7, 88, 9, 8).
const SLEEP_ICON_X = 7;
const SLEEP_ICON_Y = 88;
const SLEEP_ICON_W = 9;
const SLEEP_ICON_H = 8;

// Icons.ALERT in icons.png (Icons.java): uvRectBySize(16, 80, 8, 8).
const ALERT_ICON_X = 16;
const ALERT_ICON_Y = 80;
const ALERT_ICON_W = 8;
const ALERT_ICON_H = 8;
const ALERT_DURATION = 1500; // ms
const LOST_DURATION = 1500; // ms — how long the confused icon shows after losing target

// Icons.LOST in icons.png (Icons.java): uvRectBySize(24, 80, 8, 8).
const LOST_ICON_X = 24;
const LOST_ICON_Y = 80;
const LOST_ICON_W = 8;
const LOST_ICON_H = 8;

// Track alert expiry timestamps per mob.
const mobAlertUntil = {};
// Track lost (confused) expiry timestamps per mob.
const mobLostUntil = {};

// SPD's beckon()→notice()→showAlert() is unconditional, even for already-hunting mobs.
// Call this from the socket handler after a Scroll of Rage to force the ! icon.
export function forceAlertMob(mobId, durationMs = ALERT_DURATION) {
  mobAlertUntil[mobId] = performance.now() + durationMs;
}

export function drawMobs(ctx, { entitiesRef, visionRef, assetImages, mobAnimRef, dyingMobsRef }) {
  const now = performance.now();

  Object.values(entitiesRef.current.mobs).forEach(mob => {
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;

    // Rogue's Shadow Clone: a translucent dark copy of the rogue hero sprite.
    if (mob.type === 'shadow_clone' && assetImages.rogue) {
      const cx = mob.renderPos.x * TILE_SIZE;
      const cy = mob.renderPos.y * TILE_SIZE - ENTITY_LIFT;
      const fw = 12;
      const dw = fw * (TILE_SIZE / 16);
      const off = (TILE_SIZE - dw) / 2;
      ctx.save();
      ctx.globalAlpha = 0.7;
      ctx.drawImage(assetImages.rogue, 0, 0, fw, 16, cx + off, cy, dw, TILE_SIZE);
      // Darken toward shadow.
      ctx.globalCompositeOperation = 'source-atop';
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = '#000';
      ctx.fillRect(cx + off, cy, dw, TILE_SIZE);
      ctx.restore();
      const w = TILE_SIZE - 8;
      const pct = (mob.hp || 0) / (mob.max_hp || 1);
      ctx.fillStyle = '#111';
      ctx.fillRect(cx + 4, cy - 4, w, 3);
      ctx.fillStyle = '#9b59b6';
      ctx.fillRect(cx + 4, cy - 4, w * pct, 3);
      return;
    }

    // Scroll of Mirror Image: a translucent copy of the owner's hero sprite.
    if (mob.type === 'mirror_image') {
      const ownerPlayer = entitiesRef.current.players?.[mob.owner_id];
      let cloneSprite = assetImages.warrior;
      if (ownerPlayer?.class_type === 'mage' && assetImages.mage) cloneSprite = assetImages.mage;
      else if (ownerPlayer?.class_type === 'rogue' && assetImages.rogue) cloneSprite = assetImages.rogue;
      else if (ownerPlayer?.class_type === 'huntress' && assetImages.huntress) cloneSprite = assetImages.huntress;

      if (cloneSprite) {
        const cx = mob.renderPos.x * TILE_SIZE;
        const cy = mob.renderPos.y * TILE_SIZE - ENTITY_LIFT;
        const fw = 12;
        const dw = fw * (TILE_SIZE / 16);
        const off = (TILE_SIZE - dw) / 2;
        ctx.save();
        ctx.globalAlpha = 0.5;
        ctx.drawImage(cloneSprite, 0, 0, fw, 16, cx + off, cy, dw, TILE_SIZE);
        ctx.restore();
        const w = TILE_SIZE - 8;
        const pct = (mob.hp || 0) / (mob.max_hp || 1);
        ctx.fillStyle = '#111';
        ctx.fillRect(cx + 4, cy - 4, w, 3);
        ctx.fillStyle = '#9b59b6';
        ctx.fillRect(cx + 4, cy - 4, w * pct, 3);
      }
      return;
    }

    let mobSprite = assetImages.rat;
    let sx = 0;
    if (mob.name === 'Rat') {
      mobSprite = assetImages.rat;
      sx = getRatFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Crab') {
      mobSprite = assetImages.crab;
      sx = getCrabFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Hermit Crab') {
      mobSprite = assetImages.crab;
      sx = getHermitCrabFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Slime' || mob.name === 'Caustic Slime') {
      mobSprite = assetImages.slime;
      sx = getSlimeFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Snake') {
      mobSprite = assetImages.snake;
      sx = getSnakeFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Bat') {
      mobSprite = assetImages.bat;
    } else if (mob.name === 'Gnoll') {
      mobSprite = assetImages.gnoll;
      sx = getGnollFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Red Shaman' || mob.name === 'Blue Shaman' || mob.name === 'Purple Shaman') {
      mobSprite = assetImages.shaman;
      sx = getShamanFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Goo') {
      mobSprite = assetImages.goo;
      sx = getGooFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Scorpio') {
      mobSprite = assetImages.scorpio;
      sx = getScorpioFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Skeleton' || mob.name === 'NecroSkeleton') {
      mobSprite = assetImages.skeleton;
      sx = getSkeletonFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Thief') {
      mobSprite = assetImages.thief;
      sx = getThiefFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Bandit') {
      mobSprite = assetImages.thief;
      sx = getBanditFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Swarm') {
      mobSprite = assetImages.swarm;
      sx = getSwarmFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'DM-100') {
      mobSprite = assetImages.dm100;
      sx = getDM100Frame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'DM-200' || mob.name === 'DM-201') {
      mobSprite = assetImages.dm200;
      sx = getDM200Frame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Guard') {
      mobSprite = assetImages.guard;
      sx = getGuardFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Necromancer') {
      mobSprite = assetImages.necromancer;
      sx = getNecromancerFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Wraith' || mob.name === 'Tormented Spirit' || mob.name === 'Dust Wraith') {
      mobSprite = assetImages.wraith;
      sx = getWraithFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Piranha' || mob.name === 'Phantom Piranha') {
      mobSprite = assetImages.piranha;
      sx = getPiranhaFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Mimic' || mob.name === 'Golden Mimic' || mob.name === 'Crystal Mimic' || mob.name === 'Ebony Mimic') {
      mobSprite = assetImages.mimic;
      sx = getMimicFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Statue' || mob.name === 'Armored Statue') {
      mobSprite = assetImages.statue;
      sx = getStatueFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Bee') {
      mobSprite = assetImages.bee;
      sx = getBeeFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Dwarf King') {
      mobSprite = assetImages.king;
      sx = getDwarfKingFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Ghoul' || mob.name === 'DK Ghoul') {
      mobSprite = assetImages.ghoul;
      sx = getGhoulFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'DK Monk') {
      mobSprite = assetImages.monk;
      sx = getMonkFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Warlock' || mob.name === 'DK Warlock') {
      mobSprite = assetImages.warlock;
      sx = getWarlockFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Golem' || mob.name === 'DK Golem') {
      mobSprite = assetImages.golem;
      sx = getGolemFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Spinner') {
      mobSprite = assetImages.spinner;
      sx = getSpinnerFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Yog-Dzewa') {
      mobSprite = assetImages.yog;
      sx = getYogFrame(mob, mobAnimRef.current, now);
    } else if (
      mob.name === 'Burning Fist' || mob.name === 'Soiled Fist' || mob.name === 'Rotting Fist' ||
      mob.name === 'Rusted Fist' || mob.name === 'Bright Fist' || mob.name === 'Dark Fist'
    ) {
      mobSprite = assetImages.fists;
      sx = getFistFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Evil Eye' || mob.name === 'Yog Eye') {
      mobSprite = assetImages.eye;
      sx = getEyeFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Yog Scorpio') {
      mobSprite = assetImages.scorpio;
      sx = getScorpioFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Yog Ripper') {
      mobSprite = assetImages.ripper;
      sx = getRipperFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Demon Spawner') {
      mobSprite = assetImages.spawner;
      sx = getSpawnerFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Succubus') {
      mobSprite = assetImages.succubus;
      sx = getSuccubusFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Ripper Demon') {
      mobSprite = assetImages.ripper;
      sx = getRipperFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Pylon') {
      mobSprite = assetImages.pylon;
      sx = getPylonFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Tengu') {
      mobSprite = assetImages.tengu;
      sx = getTenguFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'DM-300') {
      mobSprite = assetImages.dm300;
      sx = getDM300Frame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Brute' || mob.name === 'Armored Brute') {
      mobSprite = assetImages.brute;
      sx = getBruteFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Shopkeeper') {
      mobSprite = assetImages.shopkeeper;
      sx = getKeeperFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Imp') {
      mobSprite = assetImages.imp;
      sx = getImpFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Wandmaker') {
      mobSprite = assetImages.wandmaker;
      sx = getWandmakerFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Rot Heart') {
      mobSprite = assetImages.rotHeart;
      sx = getRotHeartFrame();
    } else if (mob.name === 'Rot Lasher') {
      mobSprite = assetImages.rotLasher;
      sx = getRotLasherFrame();
    } else if (mob.name === 'Newborn Fire Elemental') {
      mobSprite = assetImages.elemental;
      sx = getNewbornElementalFrame();
    } else if (mob.name === 'Rat King') {
      mobSprite = assetImages.ratking;
      sx = getRatKingFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Ghost' || mob.name === 'Ghost Hero') {
      mobSprite = assetImages.ghost;
      sx = getGhostFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Sheep') {
      mobSprite = assetImages.sheep;
      sx = getSheepFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Fetid Rat') {
      mobSprite = assetImages.rat;
      sx = getFetidRatFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Gnoll Trickster') {
      mobSprite = assetImages.gnoll;
      sx = getGnollTricksterFrame(mob, mobAnimRef.current, now);
    } else if (mob.name === 'Great Crab') {
      mobSprite = assetImages.crab;
      sx = getGreatCrabFrame(mob, mobAnimRef.current, now);
    }

    const isScorpio = mob.name === 'Scorpio' || mob.name === 'Yog Scorpio';
    const isCrab = mob.name === 'Crab';
    const isHermitCrab = mob.name === 'Hermit Crab';
    const isSlime = mob.name === 'Slime';
    const isCausticSlime = mob.name === 'Caustic Slime';
    const isGnoll = mob.name === 'Gnoll';
    const isSnake = mob.name === 'Snake';
    const isSkeleton = mob.name === 'Skeleton' || mob.name === 'NecroSkeleton';
    const isThief = mob.name === 'Thief';
    const isBandit = mob.name === 'Bandit';
    const isSwarm = mob.name === 'Swarm';
    const isDM100 = mob.name === 'DM-100';
    const isDM200 = mob.name === 'DM-200' || mob.name === 'DM-201';
    const isGuard = mob.name === 'Guard';
    const isGoo = mob.name === 'Goo';
    const isWraith = mob.name === 'Wraith' || mob.name === 'Tormented Spirit' || mob.name === 'Dust Wraith';
    const isPiranha = mob.name === 'Piranha';
    const isPhantomPiranha = mob.name === 'Phantom Piranha';
    const shamanRow = { 'Red Shaman': 0, 'Blue Shaman': 1, 'Purple Shaman': 2 }[mob.name];
    const isShaman = shamanRow !== undefined;
    const isMimic = mob.name === 'Mimic';
    const isGoldenMimic = mob.name === 'Golden Mimic';
    const isCrystalMimic = mob.name === 'Crystal Mimic';
    const isEbonyMimic = mob.name === 'Ebony Mimic';
    const isStatue = mob.name === 'Statue';
    const isArmoredStatue = mob.name === 'Armored Statue';
    const isGhoul = mob.name === 'Ghoul' || mob.name === 'DK Ghoul';
    const isMonk = mob.name === 'DK Monk';
    const isWarlock = mob.name === 'Warlock' || mob.name === 'DK Warlock';
    const isGolem = mob.name === 'Golem' || mob.name === 'DK Golem';
    const isSpinner = mob.name === 'Spinner';
    const isYog = mob.name === 'Yog-Dzewa';
    const fistRow = { 'Burning Fist': 0, 'Soiled Fist': 1, 'Rotting Fist': 2, 'Rusted Fist': 3, 'Bright Fist': 4, 'Dark Fist': 5 }[mob.name];
    const isFist = fistRow !== undefined;
    const isEye = mob.name === 'Evil Eye' || mob.name === 'Yog Eye';
    const isRipper = mob.name === 'Yog Ripper';
    const isRipperDemon = mob.name === 'Ripper Demon';
    const isSuccubus = mob.name === 'Succubus';
    const isPylon = mob.name === 'Pylon';
    const isTengu = mob.name === 'Tengu';
    const isDM300 = mob.name === 'DM-300';
    const isBrute = mob.name === 'Brute';
    const isArmoredBrute = mob.name === 'Armored Brute';
    const isShopkeeper = mob.name === 'Shopkeeper';
    const isImp = mob.name === 'Imp';
    const isWandmaker = mob.name === 'Wandmaker';
    const isRotHeart = mob.name === 'Rot Heart';
    const isRotLasher = mob.name === 'Rot Lasher';
    const isNewbornElemental = mob.name === 'Newborn Fire Elemental';
    const isRatKing = mob.name === 'Rat King';
    const isGhost = mob.name === 'Ghost' || mob.name === 'Ghost Hero';
    const isSheep = mob.name === 'Sheep';
    const isFetidRat = mob.name === 'Fetid Rat';
    const isGnollTrickster = mob.name === 'Gnoll Trickster';
    const isGreatCrab = mob.name === 'Great Crab';
    const flash = !!(mobAnimRef.current[mob.id]?.flashUntil && now < mobAnimRef.current[mob.id].flashUntil);
    ctx.save();
    if (mob.fadeAlpha != null && mob.fadeAlpha < 1) ctx.globalAlpha = mob.fadeAlpha;
    if (isGnoll) {
      drawMobSprite(ctx, mob, mobSprite, sx, GNOLL_FW, GNOLL_FH, flash, GNOLL_DEST);
    } else if (isShaman) {
      drawMobSprite(ctx, mob, mobSprite, sx, SHAMAN_FW, SHAMAN_FH, flash, SHAMAN_DEST, 1, shamanRow * SHAMAN_FH);
    } else if (isSnake) {
      drawMobSprite(ctx, mob, mobSprite, sx, SNAKE_FW, SNAKE_FH, flash, SNAKE_DEST);
    } else if (isSkeleton) {
      const tint = mob.tinted ? 0.75 : 1;
      drawMobSprite(ctx, mob, mobSprite, sx, SKELETON_FW, SKELETON_FH, flash, SKELETON_DEST, 1, 0, tint);
    } else if (isThief || isBandit) {
      drawMobSprite(ctx, mob, mobSprite, sx, THIEF_FW, THIEF_FH, flash, THIEF_DEST);
    } else if (isSwarm) {
      drawMobSprite(ctx, mob, mobSprite, sx, SWARM_FW, SWARM_FH, flash, SWARM_DEST);
    } else if (isDM100) {
      drawMobSprite(ctx, mob, mobSprite, sx, DM100_FW, DM100_FH, flash, DM100_DEST);
    } else if (isDM200) {
      drawMobSprite(ctx, mob, mobSprite, sx, DM200_FW, DM200_FH, flash, DM200_DEST);
    } else if (isGuard) {
      drawMobSprite(ctx, mob, mobSprite, sx, GUARD_FW, GUARD_FH, flash, GUARD_DEST);
    } else if (isGoo) {
      drawMobSprite(ctx, mob, mobSprite, sx, GOO_FW, GOO_FH, flash, GOO_DEST);
    } else if (isCrab || isHermitCrab) {
      // crab.png stacks variants in 16px rows: Crab = row 0, Hermit Crab = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, FRAME_W, FRAME_H, flash, null, 1, isHermitCrab ? FRAME_H : 0);
    } else if (isSlime || isCausticSlime) {
      // slime.png stacks variants in 12px rows: Slime = row 0, Caustic Slime = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, SLIME_FW, SLIME_FH, flash, SLIME_DEST, 1, isCausticSlime ? SLIME_FH : 0);
    } else if (isWraith) {
      drawMobSprite(ctx, mob, mobSprite, sx, WRAITH_FW, WRAITH_FH, flash, WRAITH_DEST);
    } else if (isPiranha || isPhantomPiranha) {
      // piranha.png stacks variants in 16px rows: Piranha = row 0, Phantom Piranha = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, PIRANHA_FW, PIRANHA_FH, flash, PIRANHA_DEST, 1, isPhantomPiranha ? PIRANHA_FH : 0);
    } else if (isMimic || isGoldenMimic || isCrystalMimic || isEbonyMimic) {
      // mimic.png stacks variants in 16px rows: Mimic = row 0, Golden = row 1, Crystal = row 2, Ebony = row 3.
      const sy = isGoldenMimic ? FRAME_H : isCrystalMimic ? FRAME_H * 2 : isEbonyMimic ? FRAME_H * 3 : 0;
      drawMobSprite(ctx, mob, mobSprite, sx, FRAME_W, FRAME_H, flash, null, 1, sy);
    } else if (isStatue || isArmoredStatue) {
      // statue.png stacks variants in 16px rows: Statue = row 0, Armored Statue = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, STATUE_FW, STATUE_FH, flash, STATUE_DEST, 1, isArmoredStatue ? 16 : 0);
    } else if (isGhoul) {
      drawMobSprite(ctx, mob, mobSprite, sx, GHOUL_FW, GHOUL_FH, flash, GHOUL_DEST);
    } else if (isMonk) {
      drawMobSprite(ctx, mob, mobSprite, sx, MONK_FW, MONK_FH, flash, MONK_DEST);
    } else if (isWarlock) {
      drawMobSprite(ctx, mob, mobSprite, sx, WARLOCK_FW, WARLOCK_FH, flash, WARLOCK_DEST);
    } else if (isGolem) {
      drawMobSprite(ctx, mob, mobSprite, sx, GOLEM_FW, GOLEM_FH, flash, GOLEM_DEST);
    } else if (isSpinner) {
      // Spinner: 16x16 frames, standard rendering, sent to back (drawn first).
      drawMobSprite(ctx, mob, mobSprite, sx, FRAME_W, FRAME_H, flash);
    } else if (isYog) {
      drawMobSprite(ctx, mob, mobSprite, sx, YOG_FW, YOG_FH, flash, YOG_DEST);
    } else if (isFist) {
      // yog_fists.png stacks the 6 fist variants in rows of FIST_FH.
      drawMobSprite(ctx, mob, mobSprite, sx, FIST_FW, FIST_FH, flash, FIST_DEST, 1, fistRow * FIST_FH);
    } else if (isEye) {
      drawMobSprite(ctx, mob, mobSprite, sx, EYE_FW, EYE_FH, flash, EYE_DEST);
    } else if (isRipper || isRipperDemon) {
      drawMobSprite(ctx, mob, mobSprite, sx, RIPPER_FW, RIPPER_FH, flash, RIPPER_DEST);
    } else if (isSuccubus) {
      drawMobSprite(ctx, mob, mobSprite, sx, SUCCUBUS_FW, SUCCUBUS_FH, flash, SUCCUBUS_DEST);
    } else if (isPylon) {
      drawMobSprite(ctx, mob, mobSprite, sx, PYLON_FW, PYLON_FH, flash, PYLON_DEST);
    } else if (isTengu) {
      drawMobSprite(ctx, mob, mobSprite, sx, TENGU_FW, TENGU_FH, flash, TENGU_DEST);
    } else if (isDM300) {
      const sy = mob.supercharged ? DM300_FH : 0;
      drawMobSprite(ctx, mob, mobSprite, sx, DM300_FW, DM300_FH, flash, DM300_DEST, 1, sy);
    } else if (isBrute || isArmoredBrute) {
      // brute.png stacks variants in 16px rows: Brute = row 0, Armored Brute = row 1.
      drawMobSprite(ctx, mob, mobSprite, sx, BRUTE_FW, BRUTE_FH, flash, BRUTE_DEST, 1, isArmoredBrute ? BRUTE_FH : 0);
    } else if (isShopkeeper) {
      drawMobSprite(ctx, mob, mobSprite, sx, KEEPER_FW, KEEPER_FH, flash, KEEPER_DEST);
    } else if (isImp) {
      drawMobSprite(ctx, mob, mobSprite, sx, IMP_FW, IMP_FH, flash, IMP_DEST);
    } else if (isWandmaker) {
      drawMobSprite(ctx, mob, mobSprite, sx, WANDMAKER_FW, WANDMAKER_FH, flash, WANDMAKER_DEST);
    } else if (isRotHeart) {
      drawMobSprite(ctx, mob, mobSprite, sx, ROT_HEART_FW, ROT_HEART_FH, flash, ROT_HEART_DEST);
    } else if (isRotLasher) {
      drawMobSprite(ctx, mob, mobSprite, sx, ROT_LASHER_FW, ROT_LASHER_FH, flash, ROT_LASHER_DEST);
    } else if (isNewbornElemental) {
      drawMobSprite(ctx, mob, mobSprite, sx, NEWBORN_ELEMENTAL_FW, NEWBORN_ELEMENTAL_FH, flash, NEWBORN_ELEMENTAL_DEST);
    } else if (isRatKing) {
      drawMobSprite(ctx, mob, mobSprite, sx, RATKING_FW, RATKING_FH, flash, RATKING_DEST);
    } else if (isGhost) {
      // Ghost: additive blending for translucent glow (SPD Blending.setLightMode)
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.85;
      drawMobSprite(ctx, mob, mobSprite, sx, GHOST_FW, GHOST_FH, flash, GHOST_DEST);
      ctx.restore();
    } else if (isSheep) {
      drawMobSprite(ctx, mob, mobSprite, sx, SHEEP_FW, SHEEP_FH, flash, SHEEP_DEST);
    } else if (isFetidRat) {
      // Fetid Rat: rat.png row 2 (16x15 frames, sy = 2 * FRAME_H = 30)
      drawMobSprite(ctx, mob, mobSprite, sx, FRAME_W, FRAME_H, flash, null, 1, 2 * FRAME_H);
    } else if (isGnollTrickster) {
      // Gnoll Trickster: gnoll.png row 2 (12x15 frames, sy = 2 * GNOLL_FH = 30)
      drawMobSprite(ctx, mob, mobSprite, sx, GNOLL_FW, GNOLL_FH, flash, GNOLL_DEST, 1, 2 * GNOLL_FH);
    } else if (isGreatCrab) {
      // Great Crab: crab.png row 2 (16x16 frames, sy = 2 * FRAME_H = 32)
      drawMobSprite(ctx, mob, mobSprite, sx, FRAME_W, FRAME_H, flash, null, 1, 2 * FRAME_H);
    } else {
      drawMobSprite(ctx, mob, mobSprite, sx,
        isScorpio ? SCORPIO_FW : FRAME_W,
        isScorpio ? SCORPIO_FW : FRAME_W,
        flash);
    }
    ctx.restore();

    const x = mob.renderPos.x * TILE_SIZE;
    const y = mob.renderPos.y * TILE_SIZE - ENTITY_LIFT;

    // Sleeping indicator: SPD's EmoIcon.Sleep (Icons.SLEEP, icons.png 7,88 9x8)
    // floats above sleeping mobs, gently pulsing between scale 1 and 1.2
    // ('idle' is the default spawn state and maps to SPD's default SLEEPING
    // state). Shopkeeper/Imp are friendly NPCs that default to "sleeping" but
    // are awake (never_wakes just means their AI never transitions) - skip them.
    if ((mob.ai_state === 'sleeping' || mob.ai_state === 'idle') && !isShopkeeper && !isImp && !isWandmaker && !isSheep && assetImages.icons) {
      const pulse = 1 + 0.1 * (Math.sin(now * 0.008) + 1);
      const dw = SLEEP_ICON_W * 2 * pulse;
      const dh = SLEEP_ICON_H * 2 * pulse;
      ctx.drawImage(assetImages.icons, SLEEP_ICON_X, SLEEP_ICON_Y, SLEEP_ICON_W, SLEEP_ICON_H,
        x + TILE_SIZE / 2 - dw / 2, y - dh, dw, dh);
    }

    // Alert indicator: SPD's EmoIcon.Alert (Icons.ALERT, icons.png 16,80 8x8).
    // Record expiry timestamp on non-hunting → hunting transition; draw each frame until expired.
    const prev = prevAiState[mob.id];
    if (prev && prev !== 'hunting' && mob.ai_state === 'hunting') {
      mobAlertUntil[mob.id] = now + ALERT_DURATION;
    }
    if (mobAlertUntil[mob.id] && now < mobAlertUntil[mob.id] && assetImages.icons) {
      const dw = ALERT_ICON_W * 2;
      const dh = ALERT_ICON_H * 2;
      ctx.drawImage(assetImages.icons, ALERT_ICON_X, ALERT_ICON_Y, ALERT_ICON_W, ALERT_ICON_H,
        x + TILE_SIZE / 2 - dw / 2, y - dh, dw, dh);
    }

    // Lost (confused) indicator: SPD's EmoIcon.Lost (Icons.LOST, icons.png 24,80 8x8).
    // Shown when a hunting mob loses its target (hunting → wandering transition).
    if (prev && prev === 'hunting' && mob.ai_state === 'wandering') {
      mobLostUntil[mob.id] = now + LOST_DURATION;
    }
    if (mobLostUntil[mob.id] && now < mobLostUntil[mob.id] && assetImages.icons) {
      const dw = LOST_ICON_W * 2;
      const dh = LOST_ICON_H * 2;
      ctx.drawImage(assetImages.icons, LOST_ICON_X, LOST_ICON_Y, LOST_ICON_W, LOST_ICON_H,
        x + TILE_SIZE / 2 - dw / 2, y - dh, dw, dh);
    }

    const totalMobShield = (mob.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0);
    if (totalMobShield > 0) {
      drawShieldHalo(ctx, x + TILE_SIZE / 2, y, totalMobShield, mob.fadeAlpha ?? 1);
    }

    // EmoIcons text fallback for states without a sprite icon.
    // Skip when a sprite icon is already showing (sleep, alert, lost timers).
    const hasSpriteIcon = (mob.ai_state === 'sleeping' || mob.ai_state === 'idle')
      || (mobAlertUntil[mob.id] && now < mobAlertUntil[mob.id])
      || (mobLostUntil[mob.id] && now < mobLostUntil[mob.id]);
    if (!hasSpriteIcon) {
      const emoIcon = aiStateEmo[mob.ai_state];
      if (emoIcon) {
        ctx.font = 'bold 14px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.strokeText(emoIcon, x + TILE_SIZE / 2, y - 6);
        ctx.fillText(emoIcon, x + TILE_SIZE / 2, y - 6);
      }
    }

    prevAiState[mob.id] = mob.ai_state;
  });

  Object.entries(dyingMobsRef.current).forEach(([id, mob]) => {
    const elapsed = now - mob.deathStart;
    const isScorpioDeath = mob.name === 'Scorpio';
    const isGooDeath = mob.name === 'Goo';
    const isRatDeath = mob.name === 'Rat';
    const isCrabDeath = mob.name === 'Crab';
    const isHermitCrabDeath = mob.name === 'Hermit Crab';
    const isSlimeDeath = mob.name === 'Slime';
    const isCausticSlimeDeath = mob.name === 'Caustic Slime';
    const isSnakeDeath = mob.name === 'Snake';
    const isSkeletonDeath = mob.name === 'Skeleton' || mob.name === 'NecroSkeleton';
    const isThiefDeath = mob.name === 'Thief';
    const isBanditDeath = mob.name === 'Bandit';
    const isSwarmDeath = mob.name === 'Swarm';
    const isDM100Death = mob.name === 'DM-100';
    const isGuardDeath = mob.name === 'Guard';
    const isNecromancerDeath = mob.name === 'Necromancer';
    const isTenguDeath = mob.name === 'Tengu';
    const isDM300Death = mob.name === 'DM-300';
    const isBruteDeath = mob.name === 'Brute' || mob.name === 'Armored Brute';
    const isFetidRatDeath = mob.name === 'Fetid Rat';
    const isGnollTricksterDeath = mob.name === 'Gnoll Trickster';
    const isShamanDeath = mob.name === 'Red Shaman' || mob.name === 'Blue Shaman' || mob.name === 'Purple Shaman';
    const isGreatCrabDeath = mob.name === 'Great Crab';
    const isSheepDeath = mob.name === 'Sheep';
    const isEvilEyeDeath = mob.name === 'Evil Eye' || mob.name === 'Yog Eye';
    const isDM200Death = mob.name === 'DM-200' || mob.name === 'DM-201';
    const isSpinnerDeath = mob.name === 'Spinner';
    const isSuccubusDeath = mob.name === 'Succubus';
    const isWarlockDeath = mob.name === 'Warlock' || mob.name === 'DK Warlock';
    const isRipperDeath = mob.name === 'Yog Ripper' || mob.name === 'Ripper Demon';
    // Gnoll: die frames [8,9,10] over 250ms, then a 3s alpha fade (SPD AlphaTweener).
    // Snake: die frames [11,12,13] over 300ms, then a 3s alpha fade.
    const deathDuration = isScorpioDeath ? 417 : isGooDeath ? 300 : isRatDeath ? 400 : (isCrabDeath || isHermitCrabDeath) ? 333 : (isSlimeDeath || isCausticSlimeDeath) ? 400 : isSnakeDeath ? 3300 : isSkeletonDeath ? 332 : isThiefDeath ? 500 : isBanditDeath ? 500 : isSwarmDeath ? 333 : isDM100Death ? 498 : isGuardDeath ? 500 : isNecromancerDeath ? 400 : isTenguDeath ? 1000 : isDM300Death ? 1000 : isBruteDeath ? 250 : isFetidRatDeath ? 400 : isGnollTricksterDeath ? 3250 : isGreatCrabDeath ? 400 : isSheepDeath ? 1000 : isEvilEyeDeath ? 375 : isDM200Death ? 375 : isSpinnerDeath ? 332 : isSuccubusDeath ? 100 : isWarlockDeath ? 335 : isRipperDeath ? 333 : isShamanDeath ? 375 : 3250;
    if (elapsed > deathDuration) { delete dyingMobsRef.current[id]; return; }
    if (!visionRef.current.visible.has(`${Math.round(mob.renderPos.x)},${Math.round(mob.renderPos.y)}`)) return;
    if (isScorpioDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 4);
      drawMobSprite(ctx, mob, assetImages.scorpio, [0, 7, 8, 9, 10][fi] * SCORPIO_FW, SCORPIO_FW, SCORPIO_FW);
    } else if (isGooDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 2);
      drawMobSprite(ctx, mob, assetImages.goo, [5, 6, 7][fi] * GOO_FW, GOO_FW, GOO_FH, false, GOO_DEST);
    } else if (isRatDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      drawMobSprite(ctx, mob, assetImages.rat, [11, 12, 13, 14][fi] * FRAME_W);
    } else if (isCrabDeath || isHermitCrabDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 3);
      const sy = isHermitCrabDeath ? FRAME_H : 0;
      drawMobSprite(ctx, mob, assetImages.crab, [10, 11, 12, 13][fi] * FRAME_W, FRAME_W, FRAME_H, false, null, 1, sy);
    } else if (isSlimeDeath || isCausticSlimeDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      const sy = isCausticSlimeDeath ? SLIME_FH : 0;
      drawMobSprite(ctx, mob, assetImages.slime, [0, 5, 6, 7][fi] * SLIME_FW, SLIME_FW, SLIME_FH, false, SLIME_DEST, 1, sy);
    } else if (isSkeletonDeath) {
      const fi = Math.min(Math.floor(elapsed / 83), 3);
      const tint = mob.tinted ? 0.75 : 1;
      drawMobSprite(ctx, mob, assetImages.skeleton, [10, 11, 12, 13][fi] * SKELETON_FW, SKELETON_FW, SKELETON_FH, false, SKELETON_DEST, 1, 0, tint);
    } else if (isThiefDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 4);
      drawMobSprite(ctx, mob, assetImages.thief, [5, 6, 7, 8, 9][fi] * THIEF_FW, THIEF_FW, THIEF_FH, false, THIEF_DEST);
    } else if (isBanditDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 4);
      drawMobSprite(ctx, mob, assetImages.thief, [25, 27, 28, 29, 30][fi] * THIEF_FW, THIEF_FW, THIEF_FH, false, THIEF_DEST);
    } else if (isSwarmDeath) {
      const fi = Math.min(Math.floor(elapsed / 67), 4);
      drawMobSprite(ctx, mob, assetImages.swarm, [10, 11, 12, 13, 14][fi] * SWARM_FW, SWARM_FW, SWARM_FH, false, SWARM_DEST);
    } else if (isDM100Death) {
      const fi = Math.min(Math.floor(elapsed / 83), 5);
      drawMobSprite(ctx, mob, assetImages.dm100, [10, 11, 12, 13, 14, 15][fi] * DM100_FW, DM100_FW, DM100_FH, false, DM100_DEST);
    } else if (isGuardDeath) {
      const fi = Math.min(Math.floor(elapsed / 125), 3);
      drawMobSprite(ctx, mob, assetImages.guard, [11, 12, 13, 14][fi] * GUARD_FW, GUARD_FW, GUARD_FH, false, GUARD_DEST);
    } else if (isNecromancerDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      drawMobSprite(ctx, mob, assetImages.necromancer, [9, 10, 11, 12][fi] * FRAME_W, FRAME_W, FRAME_W);
    } else if (isSnakeDeath) {
      const fi = Math.min(Math.floor(elapsed / 100), 2);
      const sx = [11, 12, 13][fi] * SNAKE_FW;
      const alpha = elapsed <= 300 ? 1 : Math.max(0, 1 - (elapsed - 300) / 3000);
      drawMobSprite(ctx, mob, assetImages.snake, sx, SNAKE_FW, SNAKE_FH, false, SNAKE_DEST, alpha);
    } else if (isTenguDeath) {
      // Tengu death: [8,9,10,10,10,10,10,10] @ 8fps (~125ms/frame), last frame holds.
      const fi = Math.min(Math.floor(elapsed / 125), 7);
      const sx = [8, 9, 10, 10, 10, 10, 10, 10][fi] * TENGU_FW;
      drawMobSprite(ctx, mob, assetImages.tengu, sx, TENGU_FW, TENGU_FH, false, TENGU_DEST);
    } else if (isDM300Death) {
      // DM-300 death: alternate frames [0,1] (row-relative) over ~1000ms.
      const sy = mob.supercharged ? DM300_FH : 0;
      const fi = Math.floor(elapsed / 50) % 2;
      const sx = [0, 1][fi] * DM300_FW;
      drawMobSprite(ctx, mob, assetImages.dm300, sx, DM300_FW, DM300_FH, false, DM300_DEST, 1, sy);
    } else if (isBruteDeath) {
      // Brute / Armored Brute death: [8,9,10] @ 12fps (~83ms/frame, ~250ms total).
      const sy = mob.name === 'Armored Brute' ? BRUTE_FH : 0;
      const fi = Math.min(Math.floor(elapsed / 83), 2);
      const sx = [8, 9, 10][fi] * BRUTE_FW;
      drawMobSprite(ctx, mob, assetImages.brute, sx, BRUTE_FW, BRUTE_FH, false, BRUTE_DEST, 1, sy);
    } else if (isFetidRatDeath) {
      // Fetid Rat death: [8,9,10,11] @ 10fps (~100ms/frame, ~400ms total).
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      const sx = [8, 9, 10, 11][fi] * FRAME_W;
      drawMobSprite(ctx, mob, assetImages.rat, sx, FRAME_W, FRAME_H, false, null, 1, 2 * FRAME_H);
    } else if (isGnollTricksterDeath) {
      // Gnoll Trickster death: [8,9,10] @ 12fps (~83ms/frame), then fade over 3s.
      const fi = Math.min(Math.floor(elapsed / 83), 2);
      const sx = [8, 9, 10][fi] * GNOLL_FW;
      const alpha = elapsed <= 250 ? 1 : Math.max(0, 1 - (elapsed - 250) / 3000);
      drawMobSprite(ctx, mob, assetImages.gnoll, sx, GNOLL_FW, GNOLL_FH, false, GNOLL_DEST, alpha, 2 * GNOLL_FH);
    } else if (isGreatCrabDeath) {
      // Great Crab death: [8,9,10,11] @ 10fps (~100ms/frame, ~400ms total).
      const fi = Math.min(Math.floor(elapsed / 100), 3);
      const sx = [8, 9, 10, 11][fi] * FRAME_W;
      drawMobSprite(ctx, mob, assetImages.crab, sx, FRAME_W, FRAME_H, false, null, 1, 2 * FRAME_H);
    } else if (isSuccubusDeath) {
      // Succubus death: single frame 12 (SPD SuccubusSprite die = [12] @ 10fps).
      drawMobSprite(ctx, mob, assetImages.succubus, 12 * SUCCUBUS_FW, SUCCUBUS_FW, SUCCUBUS_FH, false, SUCCUBUS_DEST);
    } else if (isWarlockDeath) {
      // Warlock death: [0,7,8,8,9,10] @ 15fps (~67ms/frame, ~335ms total per SPD WarlockSprite).
      const fi = Math.min(Math.floor(elapsed / 67), 4);
      const sx = [0, 7, 8, 8, 9, 10][fi] * WARLOCK_FW;
      drawMobSprite(ctx, mob, assetImages.warlock, sx, WARLOCK_FW, WARLOCK_FH, false, WARLOCK_DEST);
    } else if (isRipperDeath) {
      // Ripper death: [1,13,14,15,16] @ 15fps (~67ms/frame, ~333ms total per SPD RipperSprite).
      const fi = Math.min(Math.floor(elapsed / 67), 4);
      const sx = [1, 13, 14, 15, 16][fi] * RIPPER_FW;
      drawMobSprite(ctx, mob, assetImages.ripper, sx, RIPPER_FW, RIPPER_FH, false, RIPPER_DEST);
    } else if (isEvilEyeDeath) {
      // Eye death: [7,8,9] @ 8fps (~125ms/frame, ~375ms total per SPD EyeSprite).
      const fi = Math.min(Math.floor(elapsed / 125), 2);
      const sx = [7, 8, 9][fi] * EYE_FW;
      drawMobSprite(ctx, mob, assetImages.eye, sx, EYE_FW, EYE_FH, false, EYE_DEST);
    } else if (isDM200Death) {
      // DM-200/201 death: [9,10,11] @ 8fps (~125ms/frame, ~375ms total per SPD DM200Sprite).
      const fi = Math.min(Math.floor(elapsed / 125), 2);
      const sx = [9, 10, 11][fi] * DM200_FW;
      drawMobSprite(ctx, mob, assetImages.dm200, sx, DM200_FW, DM200_FH, false, DM200_DEST);
    } else if (isSpinnerDeath) {
      // Spinner death: [6,7,8,9] @ 12fps (~83ms/frame, ~332ms total per SPD SpinnerSprite).
      const fi = Math.min(Math.floor(elapsed / 83), 3);
      const sx = [6, 7, 8, 9][fi] * FRAME_W;
      drawMobSprite(ctx, mob, assetImages.spinner, sx, FRAME_W, FRAME_H, false);
    } else if (isShamanDeath) {
      // Shaman death: [8,9,10] @ 12fps (~83ms/frame, ~375ms total per SPD ShamanSprite).
      const fi = Math.min(Math.floor(elapsed / 83), 2);
      const sx = [8, 9, 10][fi] * SHAMAN_FW;
      const shamanRow = mob.name === 'Red Shaman' ? 0 : mob.name === 'Blue Shaman' ? SHAMAN_FH : 2 * SHAMAN_FH;
      drawMobSprite(ctx, mob, assetImages.shaman, sx, SHAMAN_FW, SHAMAN_FH, false, SHAMAN_DEST, 1, shamanRow);
    } else if (isSheepDeath) {
      // Sheep death: fade alpha 1→0 over 1s, no anim (SPD SheepSprite die = single frame 0).
      const alpha = Math.max(0, 1 - elapsed / 1000);
      drawMobSprite(ctx, mob, assetImages.sheep, 0, SHEEP_FW, SHEEP_FH, false, SHEEP_DEST, alpha);
    } else {
      // Gnoll death: [8,9,10] @ 83ms, then hold frame 10 and fade alpha 1->0 over 3s.
      const fi = Math.min(Math.floor(elapsed / 83), 2);
      const sx = [8, 9, 10][fi] * GNOLL_FW;
      const alpha = elapsed <= 250 ? 1 : Math.max(0, 1 - (elapsed - 250) / 3000);
      drawMobSprite(ctx, mob, assetImages.gnoll, sx, GNOLL_FW, GNOLL_FH, false, GNOLL_DEST, alpha);
    }
  });
}
