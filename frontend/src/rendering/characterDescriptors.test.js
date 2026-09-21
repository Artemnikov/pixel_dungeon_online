import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isHeroClass,
  getCharacterDescriptor,
  getAvatarCropRect,
} from './characterDescriptors.ts';

test('characterDescriptors: identifies hero classes vs mob classes', () => {
  assert.equal(isHeroClass('warrior'), true);
  assert.equal(isHeroClass('Mage'), true);
  assert.equal(isHeroClass('rogue'), true);
  assert.equal(isHeroClass('huntress'), true);
  assert.equal(isHeroClass('duelist'), true);
  assert.equal(isHeroClass('cleric'), true);

  assert.equal(isHeroClass('rat'), false);
  assert.equal(isHeroClass('gnoll'), false);
  assert.equal(isHeroClass('skeleton'), false);
  assert.equal(isHeroClass('thief'), false);
  assert.equal(isHeroClass('necromancer'), false);
  assert.equal(isHeroClass(undefined), false);
});

test('characterDescriptors: returns correct descriptor for hero classes', () => {
  const desc = getCharacterDescriptor('warrior');
  assert.equal(desc.isHero, true);
  assert.equal(desc.frameWidth, 12);
  assert.equal(desc.frameHeight, 15);
  assert.equal(desc.assetKey, 'warrior');
  assert.deepEqual(desc.defaultFrame, { x: 0, y: 90, w: 12, h: 15 });
});

test('characterDescriptors: returns correct descriptor for mob classes', () => {
  const rat = getCharacterDescriptor('rat');
  assert.equal(rat.isHero, false);
  assert.equal(rat.frameWidth, 16);
  assert.equal(rat.frameHeight, 15);
  assert.equal(rat.assetKey, 'rat');
  assert.deepEqual(rat.defaultFrame, { x: 0, y: 0, w: 16, h: 15 });

  const necro = getCharacterDescriptor('necromancer');
  assert.equal(necro.isHero, false);
  assert.equal(necro.frameWidth, 16);
  assert.equal(necro.frameHeight, 16);
  assert.equal(necro.assetKey, 'necromancer');

  const gnoll = getCharacterDescriptor('gnoll');
  assert.equal(gnoll.isHero, false);
  assert.equal(gnoll.frameWidth, 12);
  assert.equal(gnoll.frameHeight, 15);
});

test('characterDescriptors: calculates avatar crop rect for heroes with armor tiers', () => {
  const tier0 = getAvatarCropRect('warrior', 0);
  assert.deepEqual(tier0, { sx: 12, sy: 0, sw: 12, sh: 15 });

  const tier2 = getAvatarCropRect('warrior', 2);
  assert.deepEqual(tier2, { sx: 12, sy: 30, sw: 12, sh: 15 });

  const tier6 = getAvatarCropRect('mage', 6);
  assert.deepEqual(tier6, { sx: 12, sy: 90, sw: 12, sh: 15 });
});

test('characterDescriptors: calculates avatar crop rect for mobs without armor tiers', () => {
  const ratCrop = getAvatarCropRect('rat', 3);
  assert.deepEqual(ratCrop, { sx: 0, sy: 0, sw: 16, sh: 15 });

  const necroCrop = getAvatarCropRect('necromancer', 5);
  assert.deepEqual(necroCrop, { sx: 0, sy: 0, sw: 16, sh: 16 });

  const gnollCrop = getAvatarCropRect('gnoll', 0);
  assert.deepEqual(gnollCrop, { sx: 0, sy: 0, sw: 12, sh: 15 });
});
