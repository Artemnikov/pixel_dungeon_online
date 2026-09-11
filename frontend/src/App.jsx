import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './styles/index.css';

import { TILE_SIZE, MAX_DPR } from './constants';
import { RESUME, clearResumeBundle, RESUME_SESSION_KEY, RESUME_RUN_KEY } from './game/useResumeBundle';
import useGameHooks from './hooks/gameHooks';
import useInputHooks from './hooks/inputHooks';
import useRenderingHooks from './hooks/renderingHooks';
import Screens from './screens';

import LoadingOverlay from './ui/LoadingOverlay';
import TutorialOverlay from './ui/TutorialOverlay';
import BossHealthBar from './ui/BossHealthBar';
import KeyDisplay from './ui/KeyDisplay';
import SideTags from './ui/SideTags';
import AttackIndicator from './ui/AttackIndicator';
import ActionIndicator from './ui/ActionIndicator';
import ResumeIndicator from './ui/ResumeIndicator';
import DangerIndicator from './ui/DangerIndicator';
import LootIndicator from './ui/LootIndicator';
import StatusPane from './ui/StatusPane';
import EmergencyHealPrompt from './ui/EmergencyHealPrompt';
import GameHud from './ui/GameHud';
import GameModals from './ui/GameModals';
import TalentLayer from './ui/TalentLayer';
import GameOverlay from './ui/GameOverlay';
import GameLog from './ui/GameLog';
import ToastOverlay from './ui/ToastOverlay';
import BossSlainBanner from './ui/BossSlainBanner';
import LoreOverlay from './ui/LoreOverlay';
import WndInfoBuff from './ui/WndInfoBuff';

// Refs that must live in App.jsx (used as JSX ref props — lint rules forbid
// passing refs returned from hooks directly to JSX).
const canvasRef = { current: null };
const inspectPopupRef = { current: null };
const inspectSubRef = { current: null };

function App() {
  const { t } = useTranslation();

  // --- screen flow / session state ---
  const [gameState, setGameState] = useState(RESUME ? 'PLAYING' : 'WELCOME');
  const [selectedClass, setSelectedClass] = useState(RESUME?.class || '');
  const [playerName, setPlayerName] = useState(RESUME?.name || '');
  const [difficulty, setDifficulty] = useState(RESUME?.difficulty || 'normal');
  const [challenges, setChallenges] = useState(RESUME?.challenges || '');
  const [gameId, setGameId] = useState(RESUME?.gameId || 'public');
  const [roomPassword, setRoomPassword] = useState('');
  const [roomJoinError, setRoomJoinError] = useState('');
  const [sessionId, setSessionId] = useState(
    () => sessionStorage.getItem(RESUME_SESSION_KEY) || ''
  );
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [showTutorial, setShowTutorial] = useState(false);

  // --- game state ---
  const [grid, setGrid] = useState([]);
  const [myPlayerId, setMyPlayerId] = useState(null);
  const [viewport, setViewport] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
    dpr: Math.min(window.devicePixelRatio || 1, MAX_DPR),
  });
  const [inventory, setInventory] = useState([]);
  const [equippedItems, setEquippedItems] = useState({ weapon: null, wearable: null });
  const [belongings, setBelongings] = useState(null);
  const [quickslot, setQuickslot] = useState(null);
  const [myStats, setMyStats] = useState({
    hp: 0,
    maxHp: 10,
    name: '',
    isDowned: false,
    isAdmin: false,
    isRegen: false,
    exp: 0,
    level: 1,
    maxExp: 10,
    effects: [],
    classType: '',
    armorTier: 0,
    shield: 0,
    strength: 10,
    subclass: null,
    armorAbility: null,
    armorCharge: 0,
    berserkPower: 0,
    invisible: 0,
    prepSeconds: 0,
    comboCount: 0,
    talentLevels: {},
    talentPoints: {},
    bonusTalentPoints: {},
    pos: null,
    keys: [],
    guidePages: [],
    respawnsUsed: 0,
  });
  const [bossInfo, setBossInfo] = useState(null);
  const [bossFightActive, setBossFightActive] = useState(false);
  const [bossBleeding, setBossBleeding] = useState(false);
  const [depth, setDepth] = useState(1);
  const [, setCamera] = useState({ x: 0, y: 0 });
  const [gold, setGold] = useState(0);
  const [energy, setEnergy] = useState(0);
  const [hasAmulet, setHasAmulet] = useState(false);
  const [bossLurking, setBossLurking] = useState(false);
  const [exitPos, setExitPos] = useState(null);
  const [scoreBreakdown, setScoreBreakdown] = useState(null);
  const [canResurrect, setCanResurrect] = useState(false);
  const [hasAnkh, setHasAnkh] = useState(false);
  const [keptItems, setKeptItems] = useState([]);
  const [isVictory, setIsVictory] = useState(false);
  const [respawnsUsed, setRespawnsUsed] = useState(0);
  const [maxRespawns, setMaxRespawns] = useState(3);
  const [lootDropped, setLootDropped] = useState(false);
  const [deathCause, setDeathCause] = useState(null);
  const [ghostQuestGiven, setGhostQuestGiven] = useState(false);
  const [showBossSlainBanner, setShowBossSlainBanner] = useState(false);
  const [bossSlainData, setBossSlainData] = useState(null);
  const [loreOverlay, setLoreOverlay] = useState(null);
  const [inspectBuff, setInspectBuff] = useState(null);
  const [inventoryPos, setInventoryPos] = useState(null);

  // --- game hooks ---
  const game = useGameHooks({
    canvasRef, inspectPopupRef, inspectSubRef,
    gameState, setGameState, selectedClass, setSelectedClass,
    playerName, setPlayerName, difficulty, setDifficulty,
    challenges, setChallenges, gameId, setGameId,
    roomPassword, setRoomPassword, sessionId, setSessionId,
    setConnectionStatus, showTutorial, setShowTutorial,
    grid, setGrid, myPlayerId, setMyPlayerId,
    viewport, setViewport,
    inventory, setInventory, equippedItems, setEquippedItems,
    belongings, setBelongings, quickslot, setQuickslot,
    myStats, setMyStats, bossInfo, setBossInfo,
    bossFightActive, setBossFightActive, bossBleeding, setBossBleeding,
    depth, setDepth, setCamera,
    gold, setGold, energy, setEnergy, hasAmulet, setHasAmulet,
    bossLurking, setBossLurking, exitPos, setExitPos,
    scoreBreakdown, setScoreBreakdown,
    canResurrect, setCanResurrect, hasAnkh, setHasAnkh,
    keptItems, setKeptItems, isVictory, setIsVictory,
    respawnsUsed, setRespawnsUsed, maxRespawns, setMaxRespawns,
    lootDropped, setLootDropped, deathCause, setDeathCause,
    ghostQuestGiven, setGhostQuestGiven,
    showBossSlainBanner, setShowBossSlainBanner,
    bossSlainData, setBossSlainData,
    loreOverlay, setLoreOverlay,
    roomJoinError, setRoomJoinError,
  });

  const input = useInputHooks({
    gameState, showTutorial, loreOverlay, myStats,
    gridRef: game.gridRef, entitiesRef: game.entitiesRef,
    myPlayerIdRef: game.myPlayerIdRef,
    visionRef: game.visionRef, socketRef: game.socketRef,
    playerAnimRef: game.playerAnimRef,
    canvasRef, zoomRef: game.zoomRef,
    cameraLerpRef: game.cameraLerpRef,
    isDraggingRef: game.isDraggingRef, isRefocusingRef: game.isRefocusingRef,
    isPinchingRef: game.isPinchingRef,
    isCameraDetachedRef: game.isCameraDetachedRef,
    detachedCameraRef: game.detachedCameraRef, floorFadeRef: game.floorFadeRef,
    panOffsetRef: game.panOffsetRef, onOpenAlchemyRef: game.onOpenAlchemyRef,
    hoveredCellRef: game.hoveredCellRef,
    targeting: game.targeting, modals: game.modals, talent: game.talent,
    handleToolbarClick: game.handleToolbarClick,
    handleToolbarDoubleClick: game.handleToolbarDoubleClick,
    handleEscape: game.handleEscape, quickslot, itemsById: game.itemsById,
    send: game.send, emergencyHealItem: game.emergencyHealItem,
    drinkEmergencyHeal: game.drinkEmergencyHeal,
    viewport,
  });

  const rendering = useRenderingHooks({
    canvasRef, inspectPopupRef, inspectSubRef,
    grid, myPlayerId, depth: game.depth,
    floorFadeRef: game.floorFadeRef,
    assetImages: game.assetImages,
    entitiesRef: game.entitiesRef, visionRef: game.visionRef,
    openDoorsRef: game.openDoorsRef, projectilesRef: game.projectilesRef,
    customTilesRef: game.customTilesRef,
    customWallsRef: game.customWallsRef, torchesRef: game.torchesRef,
    mobAnimRef: game.mobAnimRef, dyingMobsRef: game.dyingMobsRef,
    playerAnimRef: game.playerAnimRef, particlesRef: game.particlesRef,
    searchEffectsRef: game.searchEffectsRef,
    floatingTextRef: game.floatingTextRef, screenFlashRef: game.screenFlashRef,
    screenShakeRef: game.screenShakeRef, myPlayerIdRef: game.myPlayerIdRef,
    warnedTilesRef: game.warnedTilesRef, transmuteEffectsRef: game.transmuteEffectsRef,
    flareEffectsRef: game.flareEffectsRef, spellSpriteEffectsRef: game.spellSpriteEffectsRef,
    lightningRef: game.lightningRef, shieldHaloRef: game.shieldHaloRef,
    stateEffectsRef: game.stateEffectsRef, magicMissileRef: game.magicMissileRef,
    staffAmbientRef: game.staffAmbientRef, surpriseRef: game.surpriseRef,
    flyingItemsRef: game.flyingItemsRef, selectedEnemyIdRef: game.selectedEnemyIdRef,
    hoveredCellRef: game.hoveredCellRef, beamRef: game.beamRef,
    blobAreasRef: game.blobAreasRef,
    panOffsetRef: game.panOffsetRef, cameraLerpRef: game.cameraLerpRef,
    zoomRef: game.zoomRef,
    isRefocusingRef: game.isRefocusingRef, isDraggingRef: game.isDraggingRef,
    isCameraDetachedRef: game.isCameraDetachedRef,
    detachedCameraRef: game.detachedCameraRef,
    setCamera,
    targeting: game.targeting,
    quickslot, itemsById: game.itemsById,
  });

  // Destructure hook returns so the linter doesn't flag property access on
  // the hook-returned objects (react-hooks/refs).
  const {
    wrapperRef, isDesktop: gameDesktop, assetImages, bossBleedingEffective,
    interfaceSize, isBusy, send, executeItemAction, assignQuickslot,
    handleToolbarClick, handleToolbarDoubleClick, handleLoreDismiss,
    handleReplayTutorial, handleLeaveGame, resetForRestart, cycleEnemyCamera,
    emergencyHealItem, drinkEmergencyHeal, itemsById,
    visionRef, entitiesRef, myPlayerIdRef, modals, talent, targeting,
    sendSelectScrollTarget, sendStoneTarget, effects,
  } = game;

  const { handleCanvasClick, mouseCursorVal, controllerCursorVal } = input;

  const {
    examineMode, inspectInfo, handleExamineOrReveal,
    sendUseAbility, sendPrepStrike, sendUseComboMove, toolbarItems,
  } = rendering;

  // --- screen flow ---
  if (gameState !== 'PLAYING') {
    return (
      <Screens
        gameState={gameState} isDesktop={gameDesktop}
        mouseCursorVal={mouseCursorVal}
        roomJoinError={roomJoinError} setRoomJoinError={setRoomJoinError}
        setGameId={setGameId} setRoomPassword={setRoomPassword}
        setGameState={setGameState} gameId={gameId}
        setSelectedClass={setSelectedClass} setDifficulty={setDifficulty}
        setChallenges={setChallenges} setPlayerName={setPlayerName}
        setSessionId={setSessionId}
      />
    );
  }

  const cursorStyle = (targeting.targetingMode || examineMode)
    ? gameDesktop ? controllerCursorVal : 'crosshair'
    : gameDesktop ? mouseCursorVal.replace(', pointer', ', auto') : 'default';

  return (
    <>
      <title>{t('app.titlePlaying', { depth })}</title>
      <meta name="description" content={t('app.descPlaying', { depth })} />
      <div className={`game-container ${gameDesktop ? 'desktop-mode' : ''}`}
           style={gameDesktop ? { '--cursor-mouse': mouseCursorVal } : {}}>

        <LoadingOverlay visible={grid.length === 0} />

        {showTutorial && (
          <TutorialOverlay onComplete={() => {
            localStorage.setItem('opd-tutorial-completed', '1');
            setShowTutorial(false);
          }} />
        )}

        {connectionStatus === 'reconnecting' && (
          <div className="reconnect-banner" role="status">
            {t('app.reconnecting')}
          </div>
        )}

        <BossHealthBar boss={bossInfo} bleeding={bossBleedingEffective} interfaceSize={interfaceSize} assetImages={assetImages} />
        <KeyDisplay keys={myStats.keys} depth={depth} />

        <SideTags>
          <AttackIndicator
            myStats={myStats}
            onAttack={(targetId) => send({ type: 'ATTACK', target_id: targetId })}
          />
          <ActionIndicator
            myStats={myStats}
            onAction={(action) => {
              const weapon = myStats?.belongings?.weapon;
              if (weapon) executeItemAction(weapon.id, action);
            }}
          />
          <ResumeIndicator
            myStats={myStats}
            onResume={() => send({ type: 'RESUME' })}
          />
          <DangerIndicator
            visionRef={visionRef}
            entitiesRef={entitiesRef}
            myPlayerIdRef={myPlayerIdRef}
            onCycleEnemy={() => {
              const visible = visionRef.current.visible;
              if (!visible) return;
              const hostile = Object.values(entitiesRef.current.mobs).filter(m =>
                m.faction === 'enemy' && m.renderPos && visible.has(`${Math.round(m.renderPos.x)},${Math.round(m.renderPos.y)}`)
              );
              cycleEnemyCamera(hostile);
            }}
          />
        </SideTags>

        <LootIndicator
          entitiesRef={entitiesRef}
          myPlayerIdRef={myPlayerIdRef}
          onPickup={() => send({ type: 'PICKUP_FLOOR' })}
          position={inventoryPos}
        />

        <StatusPane
          myStats={myStats}
          interfaceSize={interfaceSize}
          depth={depth}
          exitPos={exitPos}
          isAdmin={myStats.isAdmin}
          onSearch={handleExamineOrReveal}
          hasTalentPoints={Object.values(talent.talentPoints || {}).some(p => p > 0)}
          onOpenHeroInfo={() => talent.openHero(0)}
          onTeleport={(floor) => send({ type: 'ADMIN_TELEPORT', target_floor: floor })}
          isBusy={isBusy}
          onBuffClick={(buff) => setInspectBuff(buff)}
          assetImages={assetImages}
        />

        {emergencyHealItem && (
          <EmergencyHealPrompt
            item={emergencyHealItem}
            onDrink={() => drinkEmergencyHeal(emergencyHealItem)}
          />
        )}

        <div className="canvas-wrapper" ref={wrapperRef}>
          <canvas
            ref={canvasRef}
            width={Math.round(viewport.width * viewport.dpr)}
            height={Math.round(viewport.height * viewport.dpr)}
            className="game-canvas"
            style={{ cursor: cursorStyle }}
            onClick={handleCanvasClick}
          />
        </div>

        {inspectInfo && (
          <div
            ref={inspectPopupRef}
            className={`inspect-popup${inspectInfo.cellInfo?.kind === 'player' ? ' inspect-popup-stack' : ''}`}
            style={{ display: 'none' }}
          >
            <span className="inspect-popup-name">{inspectInfo.name}</span>
            <span className="inspect-popup-sub" ref={inspectSubRef} style={{ display: 'none' }} />
          </div>
        )}

        {inspectBuff && (
          <WndInfoBuff
            buff={inspectBuff}
            onClose={() => setInspectBuff(null)}
          />
        )}

        <GameHud
          interfaceSize={interfaceSize}
          isDesktop={gameDesktop}
          canvasWidth={viewport.width}
          assetImages={assetImages}
          toolbarItems={toolbarItems}
          equippedItems={equippedItems}
          targetingMode={targeting.targetingMode}
          swappedQuickslots={modals.swappedQuickslots}
          showInventory={modals.showInventory}
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={myStats.strength}
          myStats={myStats}
          onSearch={handleExamineOrReveal}
          onInventory={() => modals.setShowInventory(v => !v)}
          onQuickBag={modals.handleQuickBag}
          onSwap={modals.handleSwap}
          onSlotClick={(item, idx) => {
            if (!item || item.is_placeholder || item.default_action == null) {
              modals.openQuickslotPicker(idx);
            } else {
              handleToolbarClick(item);
            }
          }}
          onSlotDoubleClick={handleToolbarDoubleClick}
          onSlotLongPress={(item, idx) => modals.openQuickslotPicker(idx)}
          onSlotContextMenu={(item, idx) => modals.openQuickslotPicker(idx)}
          onUseAbility={sendUseAbility}
          onTriggerBerserk={() => send({ type: 'TRIGGER_BERSERK' })}
          onPrepStrike={sendPrepStrike}
          onUseComboMove={sendUseComboMove}
          onOpenItem={modals.setUseItemTarget}
          onContextMenu={(item, x, y) => modals.setCtxMenu({ item, x, y })}
          onDefaultAction={(item) => executeItemAction(item.id, item.default_action)}
          onCloseInventory={() => modals.setShowInventory(false)}
          onLayout={setInventoryPos}
        />

        <GameLog send={send} />
        <ToastOverlay />

        {showBossSlainBanner && bossSlainData && (
          <BossSlainBanner
            badgeImage={bossSlainData.badge_image}
            onDismiss={() => setShowBossSlainBanner(false)}
          />
        )}

        <GameModals
          modals={modals}
          itemsById={itemsById}
          toolbarItems={toolbarItems}
          belongings={belongings}
          gold={gold}
          energy={energy}
          strength={myStats.strength}
          isDesktop={gameDesktop}
          depth={depth}
          guidePages={myStats.guidePages || []}
          executeItemAction={executeItemAction}
          assignQuickslot={assignQuickslot}
          sendSelectScrollTarget={sendSelectScrollTarget}
          sendStoneTarget={sendStoneTarget}
          send={send}
          handleToolbarClick={handleToolbarClick}
        />

        <TalentLayer
          talent={talent}
          myStats={myStats}
          gameState={gameState}
          depth={depth}
          gold={gold}
          showItemBrowser={modals.showItemBrowser}
          setShowItemBrowser={modals.setShowItemBrowser}
          itemCatalog={modals.itemCatalog}
          effects={effects}
          send={send}
        />

        {loreOverlay && (
          <LoreOverlay key={loreOverlay.depth} depth={loreOverlay.depth} body={loreOverlay.body} onContinue={handleLoreDismiss} />
        )}

        <GameOverlay
          gameMenuOpen={modals.gameMenuOpen}
          onCloseMenu={() => modals.setGameMenuOpen(false)}
          onLeaveGame={handleLeaveGame}
          isDowned={myStats.isDowned}
          playerName={myStats.name}
          classType={myStats.classType}
          level={myStats.level}
          depth={depth}
          guidePages={myStats.guidePages || []}
          gold={gold}
          subclass={myStats.subclass}
          armorAbility={myStats.armorAbility}
          talentLevels={myStats.talentLevels}
          talentDefs={talent.talentDefs}
          inventory={inventory}
          selectedClass={selectedClass}
          scoreBreakdown={scoreBreakdown}
          canResurrect={canResurrect}
          hasAnkh={hasAnkh}
          keptItems={keptItems}
          onToggleItem={(itemId) => setKeptItems(prev =>
            prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId].slice(0, 2)
          )}
          isVictory={isVictory}
          respawnsUsed={respawnsUsed}
          maxRespawns={maxRespawns}
          lootDropped={lootDropped}
          deathCause={deathCause}
          onResurrect={() => {
            if (hasAnkh && keptItems.length === 2) {
              send({ type: 'ANKH_CHOICE', kept_item_ids: keptItems });
            } else if (hasAnkh) {
              const autoSelect = inventory
                .filter(item => item.kind !== 'ankh' && item.kind !== 'lost_backpack' && !item.is_bag)
                .slice(0, 2)
                .map(i => i.id);
              if (autoSelect.length === 2) {
                send({ type: 'ANKH_CHOICE', kept_item_ids: autoSelect });
              }
            } else {
              send({ type: 'RESURRECT' });
            }
          }}
          onAnkhChoice={(ids) => send({ type: 'ANKH_CHOICE', kept_item_ids: ids })}
          onNewGame={() => { clearResumeBundle(); resetForRestart(); setGameState('SELECT'); }}
          onMenu={() => { clearResumeBundle(); resetForRestart(); setGameState('WELCOME'); }}
          challenges={challenges}
          onReplayTutorial={handleReplayTutorial}
        />
      </div>
    </>
  );
}

export default App;
