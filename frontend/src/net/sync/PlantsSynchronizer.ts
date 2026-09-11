import type { StateUpdateMessage } from '../../types/contract';
import type { RenderPlant } from '../types';
import type { IStateSynchronizer, StateSyncContext } from './IStateSynchronizer';

export class PlantsSynchronizer implements IStateSynchronizer {
  public sync(data: StateUpdateMessage, ctx: StateSyncContext): void {
    if (!data.plants) return;

    const prevPlantsMap = new Map<string, RenderPlant>();
    for (const p of ctx.entities.getPlants()) {
      prevPlantsMap.set(`${p.x},${p.y}`, p);
    }

    const now = performance.now();
    const nextPlants: RenderPlant[] = [];

    for (const serverPlant of data.plants) {
      const key = `${serverPlant.x},${serverPlant.y}`;
      const existing = prevPlantsMap.get(key);

      if (existing) {
        existing.plant_type = serverPlant.plant_type;
        nextPlants.push(existing);
      } else {
        nextPlants.push({
          ...serverPlant,
          renderPos: { x: serverPlant.x, y: serverPlant.y },
          revealStartTime: now,
        });
      }
    }

    ctx.entities.setPlants(nextPlants);
  }
}
