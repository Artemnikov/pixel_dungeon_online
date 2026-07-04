import { useState, useRef, useEffect } from 'react';
import { getApiBaseUrl } from '../config/urls';

export default function useTalentFlow({ gameState, selectedClass, myStats, send }) {
  const [showTalentPane, setShowTalentPane] = useState(false);
  const [talentDefs, setTalentDefs] = useState(null);
  const [talentDefsLoading, setTalentDefsLoading] = useState(false);
  const [talentDefsError, setTalentDefsError] = useState(null);
  const [talentPoints, setTalentPoints] = useState({});
  const [showSubclassChoice, setShowSubclassChoice] = useState(false);
  const [subclassOptions, setSubclassOptions] = useState([]);
  const [showArmorAbilityChoice, setShowArmorAbilityChoice] = useState(false);
  const [armorAbilityOptions, setArmorAbilityOptions] = useState([]);
  const [showLevelUpBanner, setShowLevelUpBanner] = useState(false);
  const [levelUpData, setLevelUpData] = useState({});
  const [upgradedTalentId, setUpgradedTalentId] = useState(null);
  const [showMetamorphMode, setShowMetamorphMode] = useState(false);
  const [metamorphOldTalent, setMetamorphOldTalent] = useState(null);
  const [metamorphOptions, setMetamorphOptions] = useState(null);

  const onOpenTalentsRef = useRef(() => setShowTalentPane(v => !v));
  useEffect(() => { onOpenTalentsRef.current = () => setShowTalentPane(v => !v); }, []);

  // Sync talentPoints from myStats (updated every STATE_UPDATE)
  const [syncedTalentPoints, setSyncedTalentPoints] = useState(myStats.talentPoints);
  if (myStats.talentPoints !== syncedTalentPoints) {
    setSyncedTalentPoints(myStats.talentPoints);
    if (myStats.talentPoints) setTalentPoints(myStats.talentPoints);
  }

  useEffect(() => {
    if (gameState !== 'PLAYING') return;
    const classType = myStats.classType || selectedClass;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- resetting loading/error before the fetch is intentional
    setTalentDefsLoading(true);
    setTalentDefsError(null);
    fetch(`${getApiBaseUrl()}/api/talents/${classType}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => {
        setTalentDefs(data);
        setTalentDefsLoading(false);
      })
      .catch(e => {
        setTalentDefsError(e.message);
        setTalentDefsLoading(false);
      });
  }, [gameState, selectedClass, myStats.classType]);

  const sendUpgradeTalent = (talent) => send({ type: 'UPGRADE_TALENT', talent });
  const sendMetamorphChoose = (talent) => send({ type: 'METAMORPH_CHOOSE', talent });
  const sendMetamorphReplace = (oldTalent, newTalent) =>
    send({ type: 'METAMORPH_REPLACE', old_talent: oldTalent, new_talent: newTalent });

  const handleChooseSubclass = (subclass) => {
    send({ type: 'CHOOSE_SUBCLASS', subclass });
    setShowTalentPane(false);
    setUpgradedTalentId(null);
  };

  const handleChooseArmorAbility = (ability) => {
    send({ type: 'CHOOSE_ARMOR_ABILITY', ability });
    setShowTalentPane(false);
    setUpgradedTalentId(null);
  };

  const resetMetamorph = () => {
    setShowMetamorphMode(false);
    setMetamorphOptions(null);
    setMetamorphOldTalent(null);
  };

  // Socket callbacks passed to useGameSocket
  const onLevelUp = (data) => {
    if (data.talent_points) setTalentPoints(data.talent_points);
    setLevelUpData(data);
    setShowLevelUpBanner(true);
  };
  const onSubclassChoiceAvailable = (data) => {
    setSubclassOptions(data.options);
    setShowSubclassChoice(true);
  };
  const onArmorAbilityChoiceAvailable = (data) => {
    setArmorAbilityOptions(data.options);
    setShowArmorAbilityChoice(true);
  };
  const onMetamorphOpen = () => {
    setShowTalentPane(true);
    setShowMetamorphMode(true);
  };
  const onMetamorphOptions = ({ old_talent, options }) => {
    setMetamorphOldTalent(old_talent);
    setMetamorphOptions(options);
  };
  const onTalentUpgraded = ({ talent }) => {
    setUpgradedTalentId(talent);
  };

  return {
    showTalentPane, setShowTalentPane,
    talentDefs,
    talentDefsLoading,
    talentDefsError,
    talentPoints, setTalentPoints,
    showSubclassChoice, setShowSubclassChoice,
    subclassOptions,
    showArmorAbilityChoice, setShowArmorAbilityChoice,
    armorAbilityOptions,
    showLevelUpBanner, setShowLevelUpBanner,
    levelUpData,
    upgradedTalentId, setUpgradedTalentId,
    showMetamorphMode, setShowMetamorphMode,
    metamorphOldTalent, setMetamorphOldTalent,
    metamorphOptions, setMetamorphOptions,
    onOpenTalentsRef,
    sendUpgradeTalent,
    sendMetamorphChoose,
    sendMetamorphReplace,
    handleChooseSubclass,
    handleChooseArmorAbility,
    resetMetamorph,
    onLevelUp,
    onSubclassChoiceAvailable,
    onArmorAbilityChoiceAvailable,
    onMetamorphOpen,
    onMetamorphOptions,
    onTalentUpgraded,
  };
}
