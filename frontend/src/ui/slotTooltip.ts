import i18n from '../i18n';
import { ItemStatusService, type ItemStatusContext, type ItemLike } from './itemStatusFormatter';

export function slotTooltipText(item: ItemLike | null | undefined, slotIndex: number, context?: ItemStatusContext): string | null {
  if (!item) return null;
  const name = item.name || item.kind || '';
  const status = ItemStatusService.getItemStatus(item, context);
  if (status?.skillId) {
    const localizedSkillName = i18n.t(`skills.${status.skillId}.name`, { defaultValue: status.skillName || status.skillId });
    const usageCountText = status.usageCount !== undefined
      ? i18n.t('ui.weaponSkillUsage', { count: status.usageCount, defaultValue: `${status.usageCount} uses` })
      : null;
    const usageLabel = usageCountText
      ? `${localizedSkillName} (${usageCountText}, ${status.text})`
      : `${localizedSkillName} (${status.text})`;
    return `${name} - ${usageLabel}  [${slotIndex + 1}]`;
  }
  return `${name}  [${slotIndex + 1}]`;
}
