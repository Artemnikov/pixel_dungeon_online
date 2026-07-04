export function setLightMode(ctx) {
  ctx.globalCompositeOperation = 'lighter';
}

export function setNormalMode(ctx) {
  ctx.globalCompositeOperation = 'source-over';
}
