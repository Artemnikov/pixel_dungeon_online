// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 ArtemNikov
//
// Adapted from Shattered Pixel Dungeon (C) 2014-2024 Evan Debenham
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
// Blood-burst particle system, mirroring CharSprite.bloodBurstA / Splash from
// the original Shattered Pixel Dungeon: a short spray of particles thrown away
// from the attacker, with gravity and a fade-out.
//
// Coordinates are in world pixels (tile * TILE_SIZE). Particles are advanced and
// drawn inside the render loop's camera transform.

const GRAVITY = 320;        // px/s^2
const SPREAD = Math.PI / 2; // total cone width (matches bloodBurstA)
const MIN_SPEED = 24;       // px/s
const MAX_SPEED = 96;       // px/s
const MIN_LIFE = 0.35;      // s
const MAX_LIFE = 0.6;       // s

let lastNow = null;

// count is precomputed by the caller (damage-scaled). awayAngle points away
// from the attacker, in radians.
export function spawnBlood(particlesRef, cx, cy, awayAngle, count, color = '#bb0000') {
  for (let i = 0; i < count; i++) {
    const angle = awayAngle + (Math.random() - 0.5) * SPREAD;
    const speed = MIN_SPEED + Math.random() * (MAX_SPEED - MIN_SPEED);
    const life = MIN_LIFE + Math.random() * (MAX_LIFE - MIN_LIFE);
    particlesRef.current.push({
      x: cx,
      y: cy,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 1 + Math.floor(Math.random() * 2), // 1-2 px squares
      color,
      gravity: true,
    });
  }
}

// Healing sparkles, mirroring Speck.HEALING: green specks drifting straight up
// (~20 px/s) over ~1s, no gravity. Spawned spread across the sprite's width.
export function spawnHeal(particlesRef, cx, cy, count, color = '#2ecc71') {
  for (let i = 0; i < count; i++) {
    const life = 0.8 + Math.random() * 0.4;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 14,
      y: cy + (Math.random() - 0.5) * 6,
      vx: (Math.random() - 0.5) * 6,
      vy: -20,
      life,
      maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      color,
      gravity: false,
    });
  }
}

// Dust puff, matching Trap's visual poof in the original game (WornDartTrap).
// Neutral gray-brown specks spreading outward with gravity, no directional bias.
export function spawnDust(particlesRef, cx, cy, count = 6, color = '#997a4d') {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 16 + Math.random() * 40;
    const life = 0.3 + Math.random() * 0.3;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 20,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color,
      gravity: true,
    });
  }
}

// Golden crit sparkles, matching a more dramatic version of the original's
// Speck.POSITION effect: wider spread, faster, no gravity, golden color.
export function spawnCritSparkle(particlesRef, cx, cy, count = 12, color = '#ffcc00') {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 48 + Math.random() * 96;
    const life = 0.5 + Math.random() * 0.3;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 12,
      y: cy + (Math.random() - 0.5) * 12,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 30,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2), // 2-3 px squares
      color,
      gravity: false,
    });
  }
}

// Grim shadow burst, mirroring ShadowParticle.UP from the original: dark
// upward-floating specks (no gravity, slow upward drift, fade out).
export function spawnGrimShadow(particlesRef, cx, cy, count = 8, color = '#000000') {
  for (let i = 0; i < count; i++) {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI;
    const speed = 16 + Math.random() * 32;
    const life = 0.6 + Math.random() * 0.4;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 20,
      y: cy + (Math.random() - 0.5) * 20,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 10,
      life,
      maxLife: life,
      size: 3 + Math.floor(Math.random() * 3), // 3-5 px squares
      color,
      gravity: false,
    });
  }
}

// Musical notes floating upward — Speck.NOTE pattern for Scroll of Lullaby.
export function spawnNote(particlesRef, cx, cy, count = 8) {
  for (let i = 0; i < count; i++) {
    const life = 0.7 + Math.random() * 0.5;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 20,
      y: cy + (Math.random() - 0.5) * 8,
      vx: (Math.random() - 0.5) * 8,
      vy: -18 - Math.random() * 12,
      life,
      maxLife: life,
      size: 2,
      color: '#ffffaa',
      gravity: false,
    });
  }
}

// Fast outward burst — Speck.SCREAM for Scroll of Rage.
export function spawnScream(particlesRef, cx, cy, count = 10) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 60 + Math.random() * 80;
    const life = 0.25 + Math.random() * 0.2;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 10,
      y: cy + (Math.random() - 0.5) * 10,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color: '#ff4422',
      gravity: false,
    });
  }
}

// Upward energy sparkles — EnergyParticle.FACTORY for Scroll of Recharging.
export function spawnEnergy(particlesRef, cx, cy, count = 12) {
  for (let i = 0; i < count; i++) {
    const life = 0.5 + Math.random() * 0.4;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 16,
      y: cy + (Math.random() - 0.5) * 12,
      vx: (Math.random() - 0.5) * 20,
      vy: -30 - Math.random() * 40,
      life,
      maxLife: life,
      size: 1 + Math.floor(Math.random() * 2),
      color: Math.random() < 0.5 ? '#44ccff' : '#aaddff',
      gravity: false,
    });
  }
}

// Bright white specks that fade quickly — Speck.LIGHT for Scroll of Teleportation.
export function spawnLight(particlesRef, cx, cy, count = 10) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 20 + Math.random() * 50;
    const life = 0.2 + Math.random() * 0.25;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 10,
      y: cy + (Math.random() - 0.5) * 10,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color: '#ffffff',
      gravity: false,
    });
  }
}

// Gold sparkles drifting upward — Identification effect for Scroll of Identify.
export function spawnIdentify(particlesRef, cx, cy, count = 8) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 16 + Math.random() * 32;
    const life = 0.6 + Math.random() * 0.4;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 14,
      y: cy + (Math.random() - 0.5) * 14,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 20,
      life,
      maxLife: life,
      size: 2,
      color: '#ffdd44',
      gravity: false,
    });
  }
}

// Upward green specks — Speck.UP for Scroll of Upgrade.
export function spawnUp(particlesRef, cx, cy, count = 6) {
  for (let i = 0; i < count; i++) {
    const life = 0.5 + Math.random() * 0.3;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 14,
      y: cy + (Math.random() - 0.5) * 6,
      vx: (Math.random() - 0.5) * 10,
      vy: -28 - Math.random() * 20,
      life,
      maxLife: life,
      size: 2,
      color: '#55ff88',
      gravity: false,
    });
  }
}

// Purple/magenta sparkles — Speck.CHANGE for Scroll of Transmutation / Metamorphosis.
export function spawnChange(particlesRef, cx, cy, count = 10) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 36 + Math.random() * 60;
    const life = 0.5 + Math.random() * 0.3;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 12,
      y: cy + (Math.random() - 0.5) * 12,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 15,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color: Math.random() < 0.5 ? '#cc44ff' : '#ff88ff',
      gravity: false,
    });
  }
}

// White burst — Flare(6, 32) white for Scroll of Remove Curse.
export function spawnCurse(particlesRef, cx, cy, count = 10) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 50;
    const life = 0.35 + Math.random() * 0.25;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color: '#ffffff',
      gravity: false,
    });
  }
}

// Red outward burst — Flare(5, 32) red for Scroll of Terror.
export function spawnTerror(particlesRef, cx, cy, count = 10) {
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 50;
    const life = 0.35 + Math.random() * 0.25;
    particlesRef.current.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life,
      maxLife: life,
      size: 2 + Math.floor(Math.random() * 2),
      color: '#ff2200',
      gravity: false,
    });
  }
}

export function advanceAndDrawParticles(ctx, { particlesRef }) {
  const now = performance.now();
  if (lastNow == null) lastNow = now;
  const dt = Math.min((now - lastNow) / 1000, 0.05); // clamp to avoid jumps
  lastNow = now;

  const particles = particlesRef.current;
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) {
      particles.splice(i, 1);
      continue;
    }
    if (p.gravity !== false) p.vy += GRAVITY * dt;
    p.x += p.vx * dt;
    p.y += p.vy * dt;

    ctx.save();
    ctx.globalAlpha = Math.max(0, Math.min(1, p.life / p.maxLife));
    ctx.fillStyle = p.color;
    ctx.fillRect(Math.round(p.x), Math.round(p.y), p.size, p.size);
    ctx.restore();
  }
}
