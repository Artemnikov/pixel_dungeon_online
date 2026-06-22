// SPDX-License-Identifier: GPL-3.0-or-later
// Lore text for region intro pages (mirrors SPD Document.INTROS).
// First visit to depths 6, 11, 16, 21 shows the corresponding lore.

const LORE = {
  6: {
    title: 'Sewers',
    body: 'The upper floors of the dungeon actually constitute the city\'s sewer system.\n\nAs dark energy has crept up from below the usually harmless sewer creatures have become more and more ferocious. The city has had to send guard patrols down here to try and maintain safety for those above.\n\nThis place is dangerous, but at least the evil magic at work here is weak.',
  },
  11: {
    title: 'Prison',
    body: 'Many years ago a prison was built here to house dangerous criminals. Tightly regulated and secure, convicts from all over the land were brought here to serve time.\n\nBut soon dark miasma started to creep from below, twisting the minds of guard and prisoner alike.\n\nIn response to the mounting chaos, the city sealed off the entire prison. Nobody knows what became of those who were left for dead within these walls...',
  },
  16: {
    title: 'Caves',
    body: 'These sparsely populated caves stretch down under the abandoned prison. Rich in minerals, they were once a center of bustling trade and industry for the dwarven society below, but they were abandoned as the dwarves became obsessed with dark magic.\n\nThe caves are now mostly inhabited by subterranean wildlife, gnolls, and derelict machinery; likely corrupted by the same power that has affected the regions above.',
  },
  21: {
    title: 'Dwarven Metropolis',
    body: 'The Dwarven Metropolis was once the greatest of all dwarven city-states. In its heyday the dwarves built wondrous machines of metal and magic that allowed their city to expand rapidly.\n\nThen, one day, the city gates were barred and nobody heard from the dwarves again. The few who escaped the city as it closed told stories of a mad warlock who stole the throne, and the terrible magic he had learned to harness.',
  },
};

export function getLoreForDepth(depth) {
  return LORE[depth] || null;
}

export function shouldShowLore(depth, firstVisit) {
  return firstVisit && !!LORE[depth];
}
