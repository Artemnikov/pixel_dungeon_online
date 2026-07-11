import { useState, useRef, useEffect } from 'react';
import { getApiBaseUrl } from '../config/urls';

export default function useModalState() {
  const [showInventory, setShowInventory] = useState(false);
  const [useItemTarget, setUseItemTarget] = useState(null);
  const [ctxMenu, setCtxMenu] = useState(null);
  const [shopWindow, setShopWindow] = useState(null);
  const [impWindow, setImpWindow] = useState(null);
  const [ghostWindow, setGhostWindow] = useState(null);
  const [scrollPickerData, setScrollPickerData] = useState(null);
  const [stonePickerData, setStonePickerData] = useState(null);
  const [intuitionData, setIntuitionData] = useState(null);
  const [intuitionGuessData, setIntuitionGuessData] = useState(null);
  const [augmentSelectData, setAugmentSelectData] = useState(null);
  const [enchantChoiceData, setEnchantChoiceData] = useState(null);
  const [imbueWandData, setImbueWandData] = useState(null);
  const [showItemBrowser, setShowItemBrowser] = useState(false);
  const [itemCatalog, setItemCatalog] = useState([]);
  const [showQuickBag, setShowQuickBag] = useState(false);
  const [swappedQuickslots, setSwappedQuickslots] = useState(false);
  const [quickslotPicker, setQuickslotPicker] = useState(null);
  const [gameMenuOpen, setGameMenuOpen] = useState(false);
  const gameMenuOpenRef = useRef(false);
  const showItemBrowserRef = useRef(false);

  useEffect(() => { gameMenuOpenRef.current = gameMenuOpen; }, [gameMenuOpen]);
  useEffect(() => { showItemBrowserRef.current = showItemBrowser; }, [showItemBrowser]);

  useEffect(() => {
    if (!showItemBrowser || itemCatalog.length > 0) return;
    fetch(`${getApiBaseUrl()}/api/items/catalog`)
      .then(r => r.json())
      .then(setItemCatalog)
      .catch(() => {});
  }, [showItemBrowser, itemCatalog.length]);

  const handleQuickBag = () => setShowQuickBag(true);
  const handleSwap = () => setSwappedQuickslots(v => !v);
  const openQuickslotPicker = (idx) => setQuickslotPicker(idx);

  // Socket callbacks for useGameSocket
  const onShopOpen = ({ npc, stock, gold: shopGold }) => setShopWindow({ npc, stock, gold: shopGold });
  const onImpDialogue = ({ npc, text, can_claim, tokens }) => setImpWindow({ npc, text, canClaim: can_claim, tokens });
  const [ghostGearData, setGhostGearData] = useState(null);
  const onGhostDialogue = ({ npc, text, can_claim, weapon, armor }) =>
    setGhostWindow({ npc, text, canClaim: can_claim, weapon, armor });
  const onImbueWand = (data) => setImbueWandData(data);
  const onScrollSelectTarget = (data) => setScrollPickerData(data);
  const onStoneSelectTarget = (data) => setStonePickerData(data);
  const onStoneIntuitionPickItem = (data) => setIntuitionData(data);
  const onStoneIntuitionGuessKind = (data) => setIntuitionGuessData(data);
  const onStoneAugmentSelect = (data) => setAugmentSelectData(data);
  const onStoneAugmentPickItem = (data) => setAugmentSelectData(data);
  const onEnchantChoiceAvailable = (data) => setEnchantChoiceData(data);
  const onGhostGearOpen = (data) => setGhostGearData(data);
  const [chasmPrompt, setChasmPrompt] = useState(null);
  const onChasmPrompt = (data) => setChasmPrompt(data);

  const [alchemyOpen, setAlchemyOpen] = useState(false);
  const [alchemyPreview, setAlchemyPreview] = useState(null);
  const [alchemyBrewed, setAlchemyBrewed] = useState(null);
  const [trinketChoice, setTrinketChoice] = useState(null);
  const [toolkitEnergize, setToolkitEnergize] = useState(null);

  const onAlchemyPreviewResult = (data) => setAlchemyPreview(data);
  const onAlchemyBrewed = (data) => setAlchemyBrewed(data);
  const onTrinketChoice = (data) => setTrinketChoice(data);
  const onToolkitEnergizePrompt = (data) => setToolkitEnergize(data);
  const onOpenAlchemy = () => setAlchemyOpen(true);

  return {
    showInventory, setShowInventory,
    useItemTarget, setUseItemTarget,
    ctxMenu, setCtxMenu,
    shopWindow, setShopWindow,
    impWindow, setImpWindow,
    ghostWindow, setGhostWindow,
    ghostGearData, setGhostGearData,
    scrollPickerData, setScrollPickerData,
    stonePickerData, setStonePickerData,
    intuitionData, setIntuitionData,
    intuitionGuessData, setIntuitionGuessData,
    augmentSelectData, setAugmentSelectData,
    enchantChoiceData, setEnchantChoiceData,
    imbueWandData, setImbueWandData,
    showItemBrowser, setShowItemBrowser,
    itemCatalog,
    showQuickBag, setShowQuickBag,
    swappedQuickslots, setSwappedQuickslots,
    quickslotPicker, setQuickslotPicker,
    gameMenuOpen, setGameMenuOpen,
    gameMenuOpenRef,
    showItemBrowserRef,
    handleQuickBag,
    handleSwap,
    openQuickslotPicker,
    onShopOpen,
    onImpDialogue,
    onGhostDialogue,
    onImbueWand,
    onScrollSelectTarget,
    onStoneSelectTarget,
    onStoneIntuitionPickItem,
    onStoneIntuitionGuessKind,
    onStoneAugmentSelect,
    onStoneAugmentPickItem,
    onEnchantChoiceAvailable,
    onGhostGearOpen,
    chasmPrompt, setChasmPrompt,
    onChasmPrompt,
    alchemyOpen, setAlchemyOpen,
    alchemyPreview, setAlchemyPreview,
    alchemyBrewed, setAlchemyBrewed,
    trinketChoice, setTrinketChoice,
    toolkitEnergize, setToolkitEnergize,
    onAlchemyPreviewResult,
    onAlchemyBrewed,
    onTrinketChoice,
    onToolkitEnergizePrompt,
    onOpenAlchemy,
  };
}
