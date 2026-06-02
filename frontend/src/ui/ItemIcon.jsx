import itemsSrc from '../assets/pixel-dungeon/sprites/items.png';
import { coordsForItem } from '../rendering/sprites';

// Renders a single 16x16 item sprite from items.png as a scaled, pixelated tile.
// Used by the SPD-style inventory window and quickslot bar. Resolution order:
// explicit `coords` (e.g. an empty-slot holder) -> server-sent per-run appearance
// (potion colour / scroll rune) -> name/type lookup table.
export default function ItemIcon({ item, size = 32, coords: override }) {
  if (!override && !item) return null;
  const coords = override || coordsForItem(item) || [8, 13];
  const [col, row] = coords;
  const scale = size / 16;
  return (
    <div
      className="item-icon"
      style={{
        width: size,
        height: size,
        backgroundImage: `url(${itemsSrc})`,
        backgroundPosition: `-${col * 16 * scale}px -${row * 16 * scale}px`,
        backgroundSize: `${256 * scale}px ${512 * scale}px`,
        imageRendering: 'pixelated',
      }}
    />
  );
}
