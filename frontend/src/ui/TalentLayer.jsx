import SubclassChoice from './SubclassChoice';
import ArmorAbilityChoice from './ArmorAbilityChoice';
import LevelUpBanner from './LevelUpBanner';
import TalentPane from './TalentPane';
import AdminItemBrowser from './AdminItemBrowser';
import WndOptions from './WndOptions';

export default function TalentLayer({
  talent, myStats, gameState,
  showItemBrowser, setShowItemBrowser, itemCatalog,
  send,
}) {
  const {
    showTalentPane, setShowTalentPane,
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
    upgradedTalentId, setUpgradedTalentId,
    showMetamorphMode,
    metamorphOldTalent,
    metamorphOptions,
    onOpenTalentsRef,
    sendUpgradeTalent,
    sendMetamorphChoose,
    sendMetamorphReplace,
    handleChooseSubclass,
    handleChooseArmorAbility,
    resetMetamorph,
    setArmorAbilityOptions,
  } = talent;

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
          onOpenTalents={() => {
            setShowTalentPane(true);
            onOpenTalentsRef.current();
          }}
          onDismiss={() => setShowLevelUpBanner(false)}
        />
      )}

      {showTalentPane && (
        <TalentPane
          talentDefs={talentDefs}
          talentLevels={myStats.talentLevels || {}}
          talentPoints={talentPoints}
          bonusTalentPoints={myStats.bonusTalentPoints}
          level={myStats.level || 1}
          subclass={myStats.subclass || null}
          armorAbility={myStats.armorAbility || null}
          abilityTier4={talentDefs?.ability_tier4 || {}}
          upgradedTalentId={upgradedTalentId}
          isAdmin={myStats.isAdmin}
          onAdminLevelUp={() => send({ type: 'ADMIN_LEVEL_UP' })}
          onAnimationDone={() => setUpgradedTalentId(null)}
          onUpgradeTalent={sendUpgradeTalent}
          onChooseSubclass={handleChooseSubclass}
          onChooseArmorAbility={() => {
            setArmorAbilityOptions(talentDefs?.armor_abilities || []);
            setShowArmorAbilityChoice(true);
          }}
          onClose={() => {
            setShowSubclassChoice(false);
            setShowArmorAbilityChoice(false);
            setShowTalentPane(false);
            setUpgradedTalentId(null);
            resetMetamorph();
          }}
          loading={talentDefsLoading}
          error={talentDefsError}
          metamorphMode={showMetamorphMode}
          onMetamorphChoose={sendMetamorphChoose}
        />
      )}

      {showItemBrowser && myStats.isAdmin && (
        <AdminItemBrowser
          catalog={itemCatalog}
          onClose={() => setShowItemBrowser(false)}
          onGiveItem={(itemKind) => send({ type: 'ADMIN_GIVE_ITEM', item_kind: itemKind })}
        />
      )}

      {metamorphOptions && (
        <WndOptions
          icon="§"
          title="Choose replacement talent"
          message="Pick a talent from another class to replace your current one."
          options={metamorphOptions.map(tid => {
            for (const [, tier] of Object.entries(talentDefs?.tiers || {})) {
              const found = tier.talents.find(t => t.id === tid);
              if (found) return found.name || tid;
            }
            return tid;
          })}
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
