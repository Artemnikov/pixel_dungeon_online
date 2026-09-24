import type { WeaponSkillContext } from '../../data/weaponSkills';

/** The toolbar-facing subset of an item the click/double-click handlers need. */
export interface ToolbarItem {
  id: string;
  name?: string;
  kind?: string;
  type?: string;
  default_action?: string | null;
  throw_behavior?: string;
  range?: number;
  attack_cooldown?: number;
}

export interface DuelistStats {
  classType?: string;
  subclass?: string;
  weaponCharge?: number;
  effects?: unknown[];
}

/** WeaponSkillContext with a concrete `weaponCharge` (normalized to 0). */
export interface WeaponSkillContextWithCharge extends WeaponSkillContext {
  weaponCharge: number;
}

/** Builds the WeaponSkillContext fed to skill.isReady() from the local player's stats. */
export function buildWeaponSkillContext(stats?: DuelistStats): WeaponSkillContextWithCharge {
  return {
    classType: stats?.classType,
    weaponCharge: stats?.weaponCharge ?? 0,
    effects: stats?.effects,
    subclass: stats?.subclass,
  } as WeaponSkillContextWithCharge;
}