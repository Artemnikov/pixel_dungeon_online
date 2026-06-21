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
  const [imbueWandData, setImbueWandData] = useState(null);
  const [showItemBrowser, setShowItemBrowser] = useState(false);
  const [itemCatalog, setItemCatalog] = useState([]);
  const [showQuickBag, setShowQuickBag] = useState(false);
  const [radialOpen, setRadialOpen] = useState(false);
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
  const handleRadialSelect = () => setRadialOpen(true);
  const openQuickslotPicker = (idx) => setQuickslotPicker(idx);

  // Socket callbacks for useGameSocket
  const onShopOpen = ({ npc, stock, gold: shopGold }) => setShopWindow({ npc, stock, gold: shopGold });
  const onImpDialogue = ({ npc, text, can_claim, tokens }) => setImpWindow({ npc, text, canClaim: can_claim, tokens });
  const onGhostDialogue = ({ npc, text, can_claim, weapon, armor }) =>
    setGhostWindow({ npc, text, canClaim: can_claim, weapon, armor });
  const onImbueWand = (data) => setImbueWandData(data);
  const onScrollSelectTarget = (data) => setScrollPickerData(data);

  return {
    showInventory, setShowInventory,
    useItemTarget, setUseItemTarget,
    ctxMenu, setCtxMenu,
    shopWindow, setShopWindow,
    impWindow, setImpWindow,
    ghostWindow, setGhostWindow,
    scrollPickerData, setScrollPickerData,
    imbueWandData, setImbueWandData,
    showItemBrowser, setShowItemBrowser,
    itemCatalog,
    showQuickBag, setShowQuickBag,
    radialOpen, setRadialOpen,
    swappedQuickslots, setSwappedQuickslots,
    quickslotPicker, setQuickslotPicker,
    gameMenuOpen, setGameMenuOpen,
    gameMenuOpenRef,
    showItemBrowserRef,
    handleQuickBag,
    handleSwap,
    handleRadialSelect,
    openQuickslotPicker,
    onShopOpen,
    onImpDialogue,
    onGhostDialogue,
    onImbueWand,
    onScrollSelectTarget,
  };
}
