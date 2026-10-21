// Preserve the existing active-animation clock while making stalls observable.
// Wall time and credited play time are deliberately reported separately.
export function roundTickDelta(previous, now) {
  if (!Number.isFinite(previous) || !Number.isFinite(now) || now < previous) {
    throw new TypeError('A monotonic animation timestamp is required.');
  }
  const wallMs = now - previous;
  const creditedMs = Math.min(wallMs, 250);
  return {wallMs, creditedMs, stalledMs: wallMs - creditedMs};
}
