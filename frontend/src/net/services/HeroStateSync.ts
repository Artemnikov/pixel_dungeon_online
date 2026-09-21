import type { Dispatch, SetStateAction } from 'react';
import type { Player, Mob, Difficulty } from '../../types/contract';
import type { MyStats } from '../types';
import { calculateMaxCharges } from '../../data/weaponSkills';

export interface HeroStateSetters {
  setMyStats: Dispatch<SetStateAction<MyStats>>;
  setInventory: Dispatch<SetStateAction<Player['inventory']>>;
  setEquippedItems: Dispatch<SetStateAction<{ weapon: Player['equipped_weapon']; wearable: Player['equipped_wearable'] }>>;
  setBelongings?: Dispatch<SetStateAction<Player['belongings'] | null>>;
  setQuickslot?: Dispatch<SetStateAction<Player['quickslot'] | null>>;
  setGold?: (gold: number) => void;
  setEnergy?: (energy: number) => void;
  setHasAmulet?: (hasAmulet: boolean) => void;
  setBossInfo?: (info: { name: string; hp: number; maxHp: number; shield?: number; effects?: { key?: string; name?: string; icon?: number; remaining?: number; duration?: number }[] } | null) => void;
  setBossLurking?: (bossLurking: boolean) => void;
  setDifficulty?: (difficulty: Difficulty) => void;
}

export class HeroStateSync {
  private setters: HeroStateSetters;

  constructor(setters: HeroStateSetters) {
    this.setters = setters;
  }

  public syncGold(gold: number): void {
    this.setters.setGold?.(gold);
  }

  public syncEnergy(energy: number): void {
    this.setters.setEnergy?.(energy);
  }

  public setDifficulty(difficulty: Difficulty): void {
    this.setters.setDifficulty?.(difficulty);
  }

  public syncSelfPlayer(
    sp: Player,
    hasAmuletPayload?: { player_id?: string; depth?: number } | null,
    myPlayerId?: string | null,
  ): void {
    this.setters.setInventory(sp.inventory || []);
    this.setters.setEquippedItems({ weapon: sp.equipped_weapon, wearable: sp.equipped_wearable });
    if (this.setters.setBelongings) this.setters.setBelongings(sp.belongings || null);
    if (this.setters.setQuickslot) this.setters.setQuickslot(sp.quickslot || null);

    if (typeof sp.gold === 'number' && this.setters.setGold) this.setters.setGold(sp.gold);
    if (typeof sp.energy === 'number' && this.setters.setEnergy) this.setters.setEnergy(sp.energy);

    if (this.setters.setHasAmulet) {
      const holdsAmulet = Boolean(hasAmuletPayload && hasAmuletPayload.player_id === myPlayerId)
        || (sp.belongings?.backpack?.items || []).some((i: { kind?: string }) => i.kind === 'Amulet');
      this.setters.setHasAmulet(holdsAmulet);
    }

    this.setters.setMyStats({
      hp: sp.hp,
      maxHp: sp.max_hp,
      name: sp.name,
      isDowned: sp.is_downed,
      isAdmin: sp.is_admin || false,
      isRegen: (sp.heal_left || 0) > 0,
      exp: sp.experience || 0,
      level: sp.level || 1,
      maxExp: 5 + (sp.level || 1) * 5,
      effects: sp.active_effects || [],
      classType: sp.class_type || 'warrior',
      armorTier: (() => { const a = sp.belongings?.armor; return a && 'tier' in a ? a.tier ?? 0 : 0; })(),
      shield: (sp.shields || []).reduce((sum: number, s: { amount?: number }) => sum + (s.amount || 0), 0),
      strength: sp.strength ?? 10,
      subclass: sp.subclass_info?.subclass || null,
      armorAbility: sp.armor_ability || null,
      armorCharge: sp.armor_charge || 0,
      berserkPower: sp.berserk_power || 0,
      invisible: sp.invisible || 0,
      prepSeconds: sp.prep_seconds || 0,
      comboCount: sp.combo_count || 0,
      weaponCharge: sp.weapon_charge || 0,
      maxWeaponCharges: (sp as { max_weapon_charges?: number }).max_weapon_charges ?? calculateMaxCharges(sp.level || 1, sp.subclass_info?.subclass),
      finisherReady: sp.finisher_ready || false,
      spellCooldowns: sp.spell_cooldowns || {},
      clericQuickSpell: sp.cleric_quick_spell || null,
      ascendedFormActive: sp.ascended_form_active || false,
      poweredAllyId: sp.powered_ally_id || null,
      pos: sp.pos ? { x: sp.pos.x, y: sp.pos.y } : null,
      talentLevels: sp.subclass_info?.talent_info?.talents || {},
      talentPoints: sp.subclass_info?.talent_points || {},
      bonusTalentPoints: sp.subclass_info?.bonus_talent_points || {},
      keys: sp.keys || [],
      guidePages: sp.guide_pages || [],
      respawnsUsed: sp.respawns_used ?? 0,
      faction: sp.faction || 'player',
    });
  }

  public syncStatsFromPlayer(p: Player): void {
    this.setters.setMyStats(prev => ({
      ...prev,
      hp: p.hp,
      maxHp: p.max_hp,
      level: p.level || prev.level,
      maxExp: 5 + (p.level || prev.level) * 5,
      isDowned: p.is_downed,
      isRegen: (p.heal_left || 0) > 0,
      shield: (p.shields || []).reduce((sum: number, s: { amount?: number }) => sum + (s.amount || 0), 0),
      pos: p.pos ? { x: p.pos.x, y: p.pos.y } : prev.pos,
      faction: p.faction || prev.faction || 'player',
    }));
  }

  public syncBossInfo(mobs: Mob[]): void {
    if (!this.setters.setBossInfo) return;
    const boss = (mobs || []).find(m => m.type === 'boss' && m.is_alive !== false);
    this.setters.setBossInfo(boss ? {
      name: boss.name,
      hp: boss.hp,
      maxHp: boss.max_hp,
      shield: (boss.shields || []).reduce((sum, s) => sum + (s.amount || 0), 0),
      effects: boss.buffs || [],
    } : null);
  }

  public syncBossLurking(mobs: Mob[]): void {
    if (!this.setters.setBossLurking) return;
    const isBossLurking = (mobs || []).some(m => m.is_alive !== false && (m as { fight_started?: boolean }).fight_started === false);
    this.setters.setBossLurking(isBossLurking);
  }
}
