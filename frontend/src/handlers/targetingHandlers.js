import { useCallback } from 'react';
import { pickAutoAimTarget } from '../game/autoAim';
import { isAttackReady, consumeAttackCooldown } from '../net/events/combat';
import { WeaponSkillRegistry } from '../data/weaponSkills';

export function useTargetingHandlers({
  send,
  entitiesRef,
  myPlayerIdRef,
  visionRef,
  selectedEnemyIdRef,
  myStats,
  equippedItems,
  belongings,
  setTargetingMode,
}) {
  const handleToolbarDoubleClick = useCallback((item) => {
    if (!item) return;

    if (myStats?.classType === 'duelist') {
      const isPrimary = equippedItems?.weapon && equippedItems.weapon.id === item.id;
      const isSecondary = belongings?.secondary_weapon && belongings.secondary_weapon.id === item.id;
      if (isPrimary || isSecondary) {
        const skill = WeaponSkillRegistry.getSkillForWeapon(item);
        if (skill) {
          const context = {
            classType: myStats.classType,
            weaponCharge: myStats.weaponCharge ?? 0,
            effects: myStats.effects,
            subclass: myStats.subclass,
          };
          if (skill.isReady(myStats.weaponCharge ?? 0, item, context)) {
            if (!skill.requiresTarget) {
              if (isSecondary) {
                send({ type: 'USE_WEAPON_ABILITY', use_secondary: true });
              } else {
                send({ type: 'DUELIST_FINISHER' });
              }
              setTargetingMode?.(false);
              return;
            }

            const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
            if (!myPlayer) return;

            const myFaction = myPlayer.faction || 'player';
            const enemyPlayers = Object.fromEntries(
              Object.entries(entitiesRef.current.players || {})
                .filter(
                  ([id, p]) => id !== myPlayer.id && p.is_alive !== false && !p.is_downed && (p.faction || 'player') !== myFaction
                )
                .map(([id, p]) => [id, { ...p, faction: p.faction || 'player' }])
            );
            const candidateTargets = { ...entitiesRef.current.mobs, ...enemyPlayers };

            const isReach2Skill = skill.id === 'lunge' || skill.id === 'spike';
            const queryRange = isReach2Skill ? 2.85 : Math.max(1.5, (item.range || 1) * 1.45);
            if (skill.id !== 'sneak') {
              const pick = pickAutoAimTarget(
                selectedEnemyIdRef.current,
                candidateTargets,
                visionRef.current.visible,
                { x: myPlayer.renderPos.x, y: myPlayer.renderPos.y },
                queryRange,
                myFaction,
              );
              if (pick) {
                const px = Math.round(myPlayer.renderPos.x);
                const py = Math.round(myPlayer.renderPos.y);
                const dist = Math.max(Math.abs(pick.x - px), Math.abs(pick.y - py));
                if ((isReach2Skill && dist === 2) || (!isReach2Skill && dist <= (item.range || 1))) {
                  if (isSecondary) {
                    send({ type: 'USE_WEAPON_ABILITY', target_x: pick.x, target_y: pick.y, use_secondary: true });
                  } else {
                    send({ type: 'DUELIST_FINISHER', target_x: pick.x, target_y: pick.y });
                  }
                  setTargetingMode?.(false);
                  return;
                }
              }
            }

            setTargetingMode?.({ duelistFinisher: true, itemId: item.id, useSecondary: isSecondary });
          }
          return;
        }
      }
    }

    const isTargeted = item.type === 'wand'
      || item.throw_behavior === 'missile'
      || item.type === 'throwable'
      || (item.type === 'weapon' && item.range && item.range > 1)
      || item.kind === 'staff';
    if (!isTargeted) return;
    if (!isAttackReady()) return;

    const myPlayer = entitiesRef.current.players[myPlayerIdRef.current];
    if (!myPlayer) return;

    const myFaction = myPlayer.faction || 'player';
    const enemyPlayers = Object.fromEntries(
      Object.entries(entitiesRef.current.players || {})
        .filter(
          ([id, p]) => id !== myPlayer.id && p.is_alive !== false && !p.is_downed && (p.faction || 'player') !== myFaction
        )
        .map(([id, p]) => [id, { ...p, faction: p.faction || 'player' }])
    );
    const candidateTargets = { ...entitiesRef.current.mobs, ...enemyPlayers };

    // SPD QuickSlotButton.autoAim: prefer the remembered/locked target, else
    // the nearest visible mob in range.
    const pick = pickAutoAimTarget(
      selectedEnemyIdRef.current,
      candidateTargets,
      visionRef.current.visible,
      { x: myPlayer.renderPos.x, y: myPlayer.renderPos.y },
      item.range,
      myFaction,
    );
    if (pick) {
      consumeAttackCooldown((item.attack_cooldown ?? 1.0) * 1000);
      send({ type: 'RANGED_ATTACK', item_id: item.id, target_x: pick.x, target_y: pick.y, target_entity_id: pick.id });
    }
  }, [send, entitiesRef, myPlayerIdRef, visionRef, selectedEnemyIdRef, myStats, equippedItems, belongings, setTargetingMode]);

  return { handleToolbarDoubleClick };
}
