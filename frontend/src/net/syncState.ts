import AudioManager from '../audio/AudioManager';
import { INVIS_ALPHA } from '../constants';
import type { StateUpdateMessage, SerializedItem } from '../types/contract';
import type { SyncCtx, RenderPlayer, RenderMob } from './types';

interface DropBounce {
  startTime: number;
  startY: number;
}

type Fadeable = {
  invisible?: number;
  fadeAlpha?: number;
  fadeStartAlpha?: number;
  fadeTargetAlpha?: number;
  fadeStartTime?: number | null;
};

function applyInvisFade(entity: Fadeable, newInvis: number): void {
  const prev = entity.invisible || 0;
  const next = newInvis || 0;
  if (prev === 0 && next > 0) {
    entity.fadeStartAlpha = entity.fadeAlpha ?? 1;
    entity.fadeTargetAlpha = INVIS_ALPHA;
    entity.fadeStartTime = performance.now();
  } else if (prev > 0 && next === 0) {
    entity.fadeStartAlpha = entity.fadeAlpha ?? INVIS_ALPHA;
    entity.fadeTargetAlpha = 1;
    entity.fadeStartTime = performance.now();
  }
  entity.invisible = next;
}

export function syncState(data: StateUpdateMessage, ctx: SyncCtx): void {
  const {
    myPlayerIdRef, gridRef, entitiesRef, visionRef, openDoorsRef, trapsRef,
    dyingMobsRef, wasDownedRef,
    setInventory, setEquippedItems, setMyStats, setBossInfo, setBelongings, setQuickslot,
  } = ctx;

  // --- Players ---
  const currentServerPlayerIds = new Set(data.players.map(p => p.id));
  Object.keys(entitiesRef.current.players).forEach(id => {
    if (!currentServerPlayerIds.has(id)) delete entitiesRef.current.players[id];
  });

  data.players.forEach(p => {
    if (p.id === myPlayerIdRef.current) {
      setInventory(p.inventory || []);
      setEquippedItems({ weapon: p.equipped_weapon, wearable: p.equipped_wearable });
      if (setBelongings) setBelongings(p.belongings || null);
      if (setQuickslot) setQuickslot(p.quickslot || null);
      wasDownedRef.current = p.is_downed;
      setMyStats({
        hp: p.hp,
        maxHp: p.max_hp,
        name: p.name,
        isDowned: p.is_downed,
        isAdmin: p.is_admin || false,
        isRegen: (p.heal_left || 0) > 0,
        exp: p.experience || 0,
        level: p.level || 1,
        maxExp: 5 + (p.level || 1) * 5,
        effects: p.active_effects || [],
        classType: p.class_type || 'warrior',
        armorTier: (() => { const a = p.belongings?.armor; return a && 'tier' in a ? a.tier ?? 0 : 0; })(),
        shield: (p.shields || []).reduce((sum: number, s: { amount?: number }) => sum + (s.amount || 0), 0),
        strength: p.strength ?? 10,
        subclass: p.subclass_info?.subclass || null,
        armorAbility: p.armor_ability || null,
        armorCharge: p.armor_charge || 0,
        berserkPower: p.berserk_power || 0,
        invisible: p.invisible || 0,
        prepSeconds: p.prep_seconds || 0,
        comboCount: p.combo_count || 0,
        pos: p.pos ? { x: p.pos.x, y: p.pos.y } : null,
        talentLevels: p.subclass_info?.talent_info?.talents || {},
        talentPoints: p.subclass_info?.talent_points || {},
        bonusTalentPoints: p.subclass_info?.bonus_talent_points || {},
        keys: p.keys || [],
      });
    }

    if (!entitiesRef.current.players[p.id]) {
      entitiesRef.current.players[p.id] = {
        ...p,
        renderPos: { x: p.pos.x, y: p.pos.y },
        animStartPos: { x: p.pos.x, y: p.pos.y },
        animStartTime: null,
        facing: 'RIGHT',
        flipX: false,
        deathStart: p.is_downed ? performance.now() : null,
        fadeAlpha: (p.invisible || 0) > 0 ? INVIS_ALPHA : 1,
        fadeStartTime: null,
      } as RenderPlayer;
    } else {
      const existing = entitiesRef.current.players[p.id];
      const moved = !existing.targetPos
        || existing.targetPos.x !== p.pos.x || existing.targetPos.y !== p.pos.y;
      if (moved) {
        const currentTarget = existing.targetPos || existing.renderPos;
        const dx = p.pos.x - currentTarget.x;
        const dy = p.pos.y - currentTarget.y;
        if (Math.abs(dx) >= Math.abs(dy)) {
          if (dx > 0) { existing.facing = 'RIGHT'; existing.flipX = false; }
          else if (dx < 0) { existing.facing = 'LEFT'; existing.flipX = true; }
        } else {
          if (dy > 0) existing.facing = 'DOWN';
          else if (dy < 0) existing.facing = 'UP';
        }
        existing.animStartPos = { x: existing.renderPos.x, y: existing.renderPos.y };
        existing.animStartTime = performance.now();
        existing.targetPos = p.pos;
      }
      existing.name = p.name;
      existing.hp = p.hp;
      existing.max_hp = p.max_hp;
      existing.equipped_wearable = p.equipped_wearable;
      applyInvisFade(existing, p.invisible || 0);
      if (p.is_downed && !existing.is_downed) {
        existing.deathStart = performance.now();
        if (p.id === myPlayerIdRef.current) AudioManager.play('DEATH');
      }
      existing.is_downed = p.is_downed;
      existing.heal_left = p.heal_left;
      existing.class_type = p.class_type;
    }
  });

  // --- Mobs ---
  const currentServerMobIds = new Set(data.mobs.map(m => m.id));

  if (data.events) {
    data.events.forEach(ev => {
      if (ev.type !== 'DEATH') return;
      const id = ev.data.target;
      const mob = entitiesRef.current.mobs[id];
      if (mob && !dyingMobsRef.current[id]) {
        dyingMobsRef.current[id] = { ...mob, renderPos: { ...mob.renderPos }, deathStart: performance.now() };
      }
    });
  }

  Object.keys(entitiesRef.current.mobs).forEach(id => {
    if (!currentServerMobIds.has(id)) delete entitiesRef.current.mobs[id];
  });

  data.mobs.forEach(m => {
    if (!entitiesRef.current.mobs[m.id]) {
      entitiesRef.current.mobs[m.id] = {
        ...m,
        renderPos: { x: m.pos.x, y: m.pos.y },
        animStartPos: { x: m.pos.x, y: m.pos.y },
        animStartTime: null,
        facing: 'RIGHT',
        fadeAlpha: (m.invisible || 0) > 0 ? INVIS_ALPHA : 1,
        fadeStartTime: null,
      } as RenderMob;
    } else {
      const existing = entitiesRef.current.mobs[m.id];
      const moved = !existing.targetPos
        || existing.targetPos.x !== m.pos.x || existing.targetPos.y !== m.pos.y;
      if (moved) {
        const currentTarget = existing.targetPos || existing.renderPos;
        if (m.pos.x > currentTarget.x) existing.facing = 'RIGHT';
        else if (m.pos.x < currentTarget.x) existing.facing = 'LEFT';
        existing.animStartPos = { x: existing.renderPos.x, y: existing.renderPos.y };
        existing.animStartTime = performance.now();
        existing.targetPos = m.pos;
      }
      existing.hp = m.hp;
      existing.ai_state = m.ai_state;
      applyInvisFade(existing, m.invisible || 0);
    }
  });

  if (setBossInfo) {
    const boss = data.mobs.find(m => m.type === 'boss' && m.is_alive !== false);
    setBossInfo(boss ? {
      name: boss.name, hp: boss.hp, maxHp: boss.max_hp,
      shield: (boss.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0),
      effects: boss.buffs || [],
    } : null);
  }

  // --- Items with drop bounce animation ---
  // Preserve active dropBounce state from previous items by id, so
  // mid-animation items continue bouncing across state updates.
  const oldItems = entitiesRef.current.items || [];
  const oldDropBounce = new Map<string, DropBounce>();
  for (const item of oldItems) {
    if (!item.id) continue;
    const bounce = (item as SerializedItem & { dropBounce?: DropBounce }).dropBounce;
    if (bounce) oldDropBounce.set(item.id, bounce);
  }
  const oldItemIds = new Set<string>();
  for (const i of oldItems) { if (i.id) oldItemIds.add(i.id); }
  entitiesRef.current.items = (data.items || []).map(newItem => {
    const id = newItem.id;
    if (!id) return newItem;
    const newItemWithBounce = newItem as SerializedItem & { dropBounce?: DropBounce };
    const existing = oldDropBounce.get(id);
    if (existing) {
      newItemWithBounce.dropBounce = existing;
    } else if (!oldItemIds.has(id) && newItem.pos) {
      // Brand-new server item — start the drop-from-above animation
      newItemWithBounce.dropBounce = {
        startTime: performance.now(),
        startY: newItem.pos.y - 1.5,
      };
    }
    return newItem;
  });

  if (data.visible_tiles) {
    const newVisible = new Set(data.visible_tiles.map(t => `${t[0]},${t[1]}`));
    visionRef.current.visible = newVisible;
    newVisible.forEach(t => visionRef.current.discovered.add(t));
  }

  if (data.mapped_tiles && data.mapped_tiles.length > 0) {
    data.mapped_tiles.forEach(t => visionRef.current.discovered.add(`${t[0]},${t[1]}`));
  }

  const myPlayer = data.players.find(p => p.id === myPlayerIdRef.current);
  if (myPlayer?.is_admin && gridRef.current.length > 0) {
    const allTiles = new Set<string>();
    for (let y = 0; y < gridRef.current.length; y++) {
      for (let x = 0; x < gridRef.current[0].length; x++) {
        allTiles.add(`${x},${y}`);
      }
    }
    visionRef.current.visible = allTiles;
    allTiles.forEach(t => visionRef.current.discovered.add(t));
  }

  if (data.open_doors) {
    openDoorsRef.current = new Set(data.open_doors.map(d => `${d[0]},${d[1]}`));
  }

  if (data.traps) trapsRef.current = data.traps;
}
