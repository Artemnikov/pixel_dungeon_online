import SubclassChoice from './SubclassChoice';
import ArmorAbilityChoice from './ArmorAbilityChoice';
import LevelUpBanner from './LevelUpBanner';
import WndHero from './WndHero';
import AdminItemBrowser from './AdminItemBrowser';
import WndOptions from './WndOptions';
import { findTalentDef } from '../game/talents/talentQueries';

export default function TalentLayer({
  talent, myStats, gameState, depth, gold,
  showItemBrowser, setShowItemBrowser, itemCatalog,
  effects,
  send,
}) {
  const {
    showHeroWindow, openHero, closeHero,
    heroTab, setHeroTab,
    talentDefs,
    talentDefsLoading,
    talentDefsError,
    talentPoints,
    showSubclassChoice, setShowSubclassChoice,
    subclassOptions,
    showArmorAbilityChoice, setShowArmorAbilityChoice,
    armorAbilityOptions,
    showLevelUpBanner, setShowLevelUpBanner,
    levelUpData,
    showMetamorphMode,
    metamorphOldTalent,
    metamorphOptions,
    sendUpgradeTalent,
    sendMetamorphChoose,
    sendMetamorphReplace,
    handleChooseSubclass,
    handleChooseArmorAbility,
    resetMetamorph,
  } = talent;

  const talentPaneProps = {
    talentDefs,
    talentLevels: myStats.talentLevels || {},
    talentPoints,
    level: myStats.level || 1,
    subclass: myStats.subclass || null,
    armorAbility: myStats.armorAbility || null,
    effects,
    isAdmin: myStats.isAdmin,
    onAdminLevelUp: () => send({ type: 'ADMIN_LEVEL_UP' }),
    onUpgradeTalent: sendUpgradeTalent,
    loading: talentDefsLoading,
    error: talentDefsError,
    metamorphMode: showMetamorphMode,
    onMetamorphChoose: sendMetamorphChoose,
  };

  return (
    <>
      {showSubclassChoice && (
        <SubclassChoice
          options={subclassOptions}
          onChoose={(sc) => {
            handleChooseSubclass(sc);
            setShowSubclassChoice(false);
          }}
          onSkip={() => setShowSubclassChoice(false)}
        />
      )}

      {showArmorAbilityChoice && (
        <ArmorAbilityChoice
          options={armorAbilityOptions}
          abilitySelectors={talentDefs?.ability_selectors || {}}
          onChoose={(tid) => {
            handleChooseArmorAbility(tid);
            setShowArmorAbilityChoice(false);
          }}
          onSkip={() => setShowArmorAbilityChoice(false)}
        />
      )}

      {showLevelUpBanner && levelUpData && gameState === 'PLAYING' && (
        <LevelUpBanner
          level={levelUpData.level}
          tierUnlocked={levelUpData.tier_unlocked}
          talentPoints={talentPoints}
          canChooseSubclass={levelUpData.can_choose_subclass}
          canChooseArmorAbility={levelUpData.can_choose_armor_ability}
          onOpenTalents={() => openHero(1)}
          onDismiss={() => setShowLevelUpBanner(false)}
        />
      )}

      {showHeroWindow && (
        <WndHero
          myStats={myStats}
          depth={depth}
          gold={gold}
          heroTab={heroTab}
          onTabChange={setHeroTab}
          onClose={closeHero}
          talentPaneProps={talentPaneProps}
        />
      )}

      {showItemBrowser && myStats.isAdmin && (
        <AdminItemBrowser
          catalog={itemCatalog}
          onClose={() => setShowItemBrowser(false)}
          onGiveItem={(msg) => send({ type: 'ADMIN_GIVE_ITEM', ...msg })}
        />
      )}

      {metamorphOptions && (
        <WndOptions
          icon="§"
          title="Choose replacement talent"
          message="Pick a talent from another class to replace your current one."
          options={metamorphOptions.map(tid => findTalentDef(talentDefs, tid)?.name || tid)}
          onSelect={(idx) => {
            const tid = metamorphOptions[idx];
            if (metamorphOldTalent && tid) {
              sendMetamorphReplace(metamorphOldTalent, tid);
            }
            resetMetamorph();
          }}
          onClose={resetMetamorph}
        />
      )}
    </>
  );
}
