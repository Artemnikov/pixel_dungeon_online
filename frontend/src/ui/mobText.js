// Localized mob name / description lookups shared by the examine popups.

/** Mob display name. A ratmogrified mob (SPD TransmogRat.name) reads
 *  "ratmogrified <original name>". */
export function mobDisplayName(t, mob, fallback = '') {
  if (mob.mob_type === 'transmog_rat') {
    const original = mob.original_locale_key
      ? t(mob.original_locale_key, { defaultValue: mob.original_name || '' })
      : (mob.original_name || '');
    return t('mob.transmog_rat', { name: original, defaultValue: mob.name || '' });
  }
  return mob.locale_key ? t(mob.locale_key, { defaultValue: mob.name || '' }) : (mob.name || fallback);
}

/** Description key. SPD RatKing.description(): the crowned text while the
 *  viewing hero has Ratmogrify. */
export function mobDescriptionKey(mob, heroArmorAbility) {
  if (!mob.locale_key) return null;
  const key = mob.locale_key.replace(/^mob\./, 'mob.desc.');
  if (key === 'mob.desc.rat_king' && heroArmorAbility === 'ratmogrify') return 'mob.desc.rat_king_crown';
  return key;
}
