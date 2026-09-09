import useTalentData from './useTalentData';
import useTalentUI from './useTalentUI';

export default function useTalents({ gameState, selectedClass, myStats, send }) {
  const data = useTalentData({ gameState, selectedClass, myStats });
  const ui = useTalentUI();

  const sendUpgradeTalent = (talent) => send({ type: 'UPGRADE_TALENT', talent });
  const sendMetamorphChoose = (talent) => send({ type: 'METAMORPH_CHOOSE', talent });
  const sendMetamorphReplace = (oldTalent, newTalent) =>
    send({ type: 'METAMORPH_REPLACE', old_talent: oldTalent, new_talent: newTalent });

  const handleChooseSubclass = (subclass) => {
    send({ type: 'CHOOSE_SUBCLASS', subclass });
    ui.setShowHeroWindow(false);
  };

  const handleChooseArmorAbility = (ability) => {
    send({ type: 'CHOOSE_ARMOR_ABILITY', ability });
    ui.setShowHeroWindow(false);
  };

  const onLevelUp = (levelUpPayload) => {
    ui.setLevelUpData(levelUpPayload);
    ui.setShowLevelUpBanner(true);
  };

  const onSubclassChoiceAvailable = (choicePayload) => {
    ui.setSubclassOptions(choicePayload.options);
    ui.setShowSubclassChoice(true);
  };

  const onArmorAbilityChoiceAvailable = (choicePayload) => {
    ui.setArmorAbilityOptions(choicePayload.options);
    ui.setShowArmorAbilityChoice(true);
  };

  const onMetamorphOpen = () => {
    ui.setShowMetamorphMode(true);
    ui.openHero(1);
  };

  const onMetamorphOptions = ({ old_talent, options }) => {
    ui.setMetamorphOldTalent(old_talent);
    ui.setMetamorphOptions(options);
  };

  return {
    ...data,
    ...ui,
    sendUpgradeTalent,
    sendMetamorphChoose,
    sendMetamorphReplace,
    handleChooseSubclass,
    handleChooseArmorAbility,
    onLevelUp,
    onSubclassChoiceAvailable,
    onArmorAbilityChoiceAvailable,
    onMetamorphOpen,
    onMetamorphOptions,
  };
}
