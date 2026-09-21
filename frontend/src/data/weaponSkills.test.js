import test from 'node:test';
import assert from 'node:assert/strict';
import {
  WeaponSkillRegistry,
  CleaveSkill,
  LungeSkill,
  SneakSkill,
  SpinSkill,
  BrawlerStanceSkill,
  calculateMaxCharges,
} from './weaponSkills.ts';
import { ItemStatusService } from '../ui/itemStatusFormatter.ts';
import { slotTooltipText } from '../ui/slotTooltip.ts';

test('calculateMaxCharges computes base and champion caps correctly', () => {
  assert.equal(calculateMaxCharges(1, null), 2);
  assert.equal(calculateMaxCharges(4, null), 3);
  assert.equal(calculateMaxCharges(19, null), 8);
  assert.equal(calculateMaxCharges(25, null), 8);

  assert.equal(calculateMaxCharges(1, 'champion'), 4);
  assert.equal(calculateMaxCharges(4, 'champion'), 5);
  assert.equal(calculateMaxCharges(19, 'champion'), 10);
});

test('WeaponSkillRegistry maps weapon names correctly', () => {
  const rapierSkill = WeaponSkillRegistry.getSkillForWeapon({ name: 'Rapier', type: 'weapon' });
  assert.equal(rapierSkill?.id, 'lunge');
  assert.equal(rapierSkill?.name, 'Lunge');

  const daggerSkill = WeaponSkillRegistry.getSkillForWeapon({ name: 'Dagger', kind: 'dagger' });
  assert.equal(daggerSkill?.id, 'sneak');

  const swordSkill = WeaponSkillRegistry.getSkillForWeapon({ name: 'Sword', type: 'weapon' });
  assert.equal(swordSkill?.id, 'cleave');

  const wornSwordSkill = WeaponSkillRegistry.getSkillForWeapon({ name: 'Worn Shortsword', kind: 'worn_shortsword' });
  assert.equal(wornSwordSkill?.id, 'cleave');

  const rofSkill = WeaponSkillRegistry.getSkillForWeapon({ name: 'Ring of Force', type: 'ring' });
  assert.equal(rofSkill?.id, 'brawler_stance');
  assert.equal(rofSkill?.getChargeCost(), 0.0);
});

test('WeaponSkillRegistry rejects non-melee weapons', () => {
  const staff = { name: "Mage's Staff", kind: 'staff', type: 'weapon' };
  assert.equal(WeaponSkillRegistry.isMeleeWeapon(staff), false);
  assert.equal(WeaponSkillRegistry.getSkillForWeapon(staff), null);

  const bow = { name: 'Spirit Bow', kind: 'spirit_bow', type: 'weapon' };
  assert.equal(WeaponSkillRegistry.isMeleeWeapon(bow), false);
  assert.equal(WeaponSkillRegistry.getSkillForWeapon(bow), null);
});

test('CleaveSkill dynamic cost and status formatting with cleave_tracker', () => {
  const cleave = new CleaveSkill();
  assert.equal(cleave.getChargeCost({}, {}), 1.0);
  assert.equal(cleave.getUsageCount(2.0, {}, {}), 2);
  assert.equal(cleave.formatStatus(2.0, 4, {}, {}), '2/4');

  const withTracker = { effects: ['cleave_tracker'] };
  assert.equal(cleave.getChargeCost({}, withTracker), 0.0);
  assert.equal(cleave.formatStatus(0.0, 4, {}, withTracker), 'FREE');
});

test('SpinSkill dynamic cost with spin_tracker', () => {
  const spin = new SpinSkill();
  assert.equal(spin.getChargeCost({}, {}), 1.0);
  assert.equal(spin.getChargeCost({}, { effects: ['spin_tracker'] }), 0.0);
});

test('ItemStatusService formats Duelist melee weapons and wands/waterskin', () => {
  const duelistContext = {
    classType: 'duelist',
    weaponCharge: 3.5,
    maxWeaponCharges: 5,
  };

  const sword = { id: 'w1', name: 'Longsword', type: 'weapon' };
  const swordStatus = ItemStatusService.getItemStatus(sword, duelistContext);
  assert.deepEqual(swordStatus, {
    text: '3/5',
    refText: '5/5',
    skillId: 'cleave',
    skillName: 'Cleave',
    usageCount: 3,
  });

  const warriorContext = {
    classType: 'warrior',
    weaponCharge: 0,
    maxWeaponCharges: 0,
  };
  assert.equal(ItemStatusService.getItemStatus(sword, warriorContext), null);

  const wand = { kind: 'wand', charges: 2, max_charges: 4 };
  assert.deepEqual(ItemStatusService.getItemStatus(wand, duelistContext), {
    text: '2/4',
    refText: '4/4',
  });

  const waterskin = { kind: 'waterskin', volume: 15 };
  assert.deepEqual(ItemStatusService.getItemStatus(waterskin, duelistContext), {
    text: '15/20',
    refText: '20/20',
  });
});

test('slotTooltipText displays Duelist weapon skill and usage count', () => {
  const duelistContext = {
    classType: 'duelist',
    weaponCharge: 2,
    maxWeaponCharges: 2,
  };
  const rapier = { name: 'Rapier', type: 'weapon' };
  const tooltip = slotTooltipText(rapier, 0, duelistContext);
  assert.equal(tooltip, 'Rapier - Lunge (2 uses, 2/2)  [1]');
});

test('WeaponSkill requiresTarget flags', () => {
  assert.equal(new LungeSkill().requiresTarget, true);
  assert.equal(new CleaveSkill().requiresTarget, true);
  assert.equal(new SneakSkill().requiresTarget, true);
  assert.equal(new BrawlerStanceSkill().requiresTarget, false);
});
