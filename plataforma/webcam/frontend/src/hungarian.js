/**
 * hungarian.js — Ticket 042 Hungarian per-class locks 0.90/0.10
 * e-maxx O(n³) port, <0.1ms n≤13. Fallback IoU greedy si quality<0.35.
 * Copy-free: no npm dep.
 */
export function hungarian(cost) {
  const n = cost.length;
  const m = cost[0]?.length ?? 0;
  if (n === 0 || m === 0) return [];
  const N = Math.max(n, m);
  const a = Array.from({ length: N + 1 }, () => Array(N + 1).fill(0));
  for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) a[i][j] = cost[i - 1][j - 1];
  const u = Array(N + 1).fill(0), v = Array(N + 1).fill(0), p = Array(N + 1).fill(0), way = Array(N + 1).fill(0);
  for (let i = 1; i <= N; i++) {
    p[0] = i;
    let j0 = 0;
    const minv = Array(N + 1).fill(Infinity);
    const used = Array(N + 1).fill(false);
    do {
      used[j0] = true;
      const i0 = p[j0];
      let delta = Infinity, j1 = 0;
      for (let j = 1; j <= N; j++) if (!used[j]) {
        const cur = a[i0][j] - u[i0] - v[j];
        if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
        if (minv[j] < delta) { delta = minv[j]; j1 = j; }
      }
      for (let j = 0; j <= N; j++) if (used[j]) { u[p[j]] += delta; v[j] -= delta; } else minv[j] -= delta;
      j0 = j1;
    } while (p[j0] !== 0);
    do { const j1 = way[j0]; p[j0] = p[j1]; j0 = j1; } while (j0);
  }
  const ans = Array(N + 1).fill(0);
  for (let j = 1; j <= N; j++) if (p[j] !== 0) ans[p[j]] = j;
  const res = [];
  for (let i = 1; i <= n; i++) {
    const j = ans[i];
    if (j >= 1 && j <= m) res.push([i - 1, j - 1]);
  }
  return res;
}
export function iou(a, b) {
  const x1 = Math.max(a.x, b.x), y1 = Math.max(a.y, b.y);
  const x2 = Math.min(a.x + a.w, b.x + b.w), y2 = Math.min(a.y + a.h, b.y + b.h);
  if (x2 <= x1 || y2 <= y1) return 0;
  const inter = (x2 - x1) * (y2 - y1);
  return inter / (a.w * a.h + b.w * b.h - inter);
}
