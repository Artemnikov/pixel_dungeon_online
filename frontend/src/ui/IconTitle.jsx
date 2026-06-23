// SPD IconTitle.java port: a title row with a 16x16 icon slot, a label, and an
// optional level marker. The icon slot accepts a React node (the caller is
// responsible for rendering the icon image) so it works for items, mobs, buffs,
// and tile images alike.
export default function IconTitle({ icon, title, level, color, sub }) {
  const titleColor = color || '#ffe070';
  const levelStr = level != null
    ? (level > 0 ? `+${level}` : `${level}`)
    : null;

  return (
    <div className="wnd-info-title">
      <div className="wnd-info-title__icon">{icon}</div>
      <div className="wnd-info-title__text">
        <span className="wnd-info-name" style={{ color: titleColor }}>{title}</span>
        {levelStr && <span className="wnd-info-level">{levelStr}</span>}
        {sub && <span className="wnd-info-title__sub">{sub}</span>}
      </div>
    </div>
  );
}
