// Brief, remake-specific changelog shown in the Changes panel.
export const APP_VERSION = '0.2.0';

const CHANGELOG = [
  {
    version: 'v0.2.0',
    title: 'Combat & Controls Update',
    changes: [
      'SPD-style critical hits: surprise attacks, damage floors, Fury and weapon enchants.',
      'Misses now show visual and audio feedback.',
      '8-directional movement with diagonal walking; smoother keyboard input.',
      'Line-of-sight rewritten with the original recursive shadowcasting.',
      'Visible traps with proper terrain rendering.',
      'Mobile toolbar: quick-bag, radial menu and slot swapping; fixed mobile travel and ranged attacks.',
      'Custom cursor across landing and hero screens; camera keeps the player centered at high zoom.',
      'Ported the original inventory and UI elements; fixed item inspect, throwing and labels.',
      'Reworked armor and damage flow; fixed mob attack timing and global passive healing.',
      'Entrance room is now a healing room.',
      'SEO: full meta tags, robots.txt and sitemap.',
    ],
  },
  {
    version: 'v0.1.0',
    title: 'Online Pixel Dungeon — Title Update',
    changes: [
      'New animated main menu: scrolling parallax background, banner with pulsing glow, and two flickering torches — ported from the original Shattered Pixel Dungeon title screen.',
      'Added Settings (audio + display), Changes, Guide, About, Rankings and News screens.',
      'Audio now has independent music and SFX volume controls plus a master mute.',
      'Display option to toggle background animations.',
    ],
  },
  {
    version: 'v0.0.x',
    title: 'Early Online Prototype',
    changes: [
      'Real-time multiplayer dungeon over WebSocket.',
      'Four playable classes: Warrior, Mage, Rogue, Archer.',
      'Canvas-rendered dungeon with mobs, items, inventory and combat.',
      'Depth-based music and sound effects.',
    ],
  },
];

export default CHANGELOG;
