import test from 'node:test';
import assert from 'node:assert/strict';
import { levelDisplayText, levelColorClass } from './itemLevelColor.js';

const it = (o) => ({ level_known: true, ...o });

test('unknown level: no text, no color', () => {
  assert.equal(levelDisplayText({ level_known: false, level: 3 }), null);
  assert.equal(levelColorClass({ level_known: false, level: 3 }), null);
});

test('plain upgrade is green (up)', () => {
  assert.equal(levelDisplayText(it({ level: 2 })), '+2');
  assert.equal(levelColorClass(it({ level: 2 })), 'up');
});

test('plain degrade is red (down)', () => {
  assert.equal(levelDisplayText(it({ level: -1 })), '-1');
  assert.equal(levelColorClass(it({ level: -1 })), 'down');
});

test('buffed above true is enhanced (blue) and shows buffed number', () => {
  const staff = it({ level: 0, buffed_level: 3 });
  assert.equal(levelDisplayText(staff), '+3');
  assert.equal(levelColorClass(staff), 'enhanced');
});

test('buffed below true is warning (orange)', () => {
  const weakened = it({ level: 3, buffed_level: 1 });
  assert.equal(levelColorClass(weakened), 'warning');
});

test('zero level: no color', () => {
  assert.equal(levelColorClass(it({ level: 0 })), null);
});
