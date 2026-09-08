import { useCallback } from 'react';
import { pickAutoAimTarget } from '../game/autoAim';
import { isAttackReady, consumeAttackCooldown } from '../net/events/combat';

export function useTargetingHandlers({ send, entitiesRef, myPlayerIdRef, visionRef, selectedEnemyIdRef }) {
  const handleToolbarDoubleClick = useCallback((item) => {
    if (!item) return;
    const isTargeted = item.type === 'wand'
      || item.type === 'throwable'
      || (item.type === 'weapon' && item.range && item.range > 1)
      || item.kind === 'staff';
    if (!isTargeted) return;
    if (!isAttackReady()) return;

    const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
    if (!myPlayer) return;

    // SPD QuickSlotButton.autoAim: prefer the remembered/locked target, else
    // the nearest visible mob in range.
    const pick = pickAutoAimTarget(
      selectedEnemyIdRef.current,
      entitiesRef.current.mobs,
      visionRef.current.visible,
      { x: myPlayer.renderPos.x, y: myPlayer.renderPos.y },
      item.range,
    );
    if (pick) {
      consumeAttackCooldown((item.attack_cooldown ?? 1.0) * 1000);
      send({ type: 'RANGED_ATTACK', item_id: item.id, target_x: pick.x, target_y: pick.y, target_entity_id: pick.id });
    }
  }, [send, entitiesRef, myPlayerIdRef, visionRef, selectedEnemyIdRef]);

  return { handleToolbarDoubleClick };
}
