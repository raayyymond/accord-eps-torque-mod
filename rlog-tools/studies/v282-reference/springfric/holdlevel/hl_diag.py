"""STREAM holdlevel, step 2: diagnostics before any contrast.

(1) Is the STORED hold_aa channel levelled or unlevelled?  ss_extract.py:64 was hard-coded level=False
    until 2026-09-19; the source is now fixed but out/*_ss.npz may predate the fix.  Decide by
    recomputing both and comparing, per route.
(2) The stored decomposition's own validation numbers (val) per route -- how well cmd is accounted for.
(3) Per-route episode counts, speed and angle distributions in the 2-8 m/s hands-off torque set,
    and the DOB fade each episode actually ran at.
"""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SS = HERE.parents[1] / 'lowspeed' / 'a_stickslip'
sys.path.insert(0, str(SS))
from ss_load import load_all, PRE
from sslib import hold_torque, k_of_v, HOLD_LEVEL_BP, HOLD_LEVEL_V, HOLD_SAT

DOB_FADE_BP = [3.0, 6.0]                 # HONDA_ACCORD_DOB_FADE_V_BP
LEVEL = {'0000006c--68c6e94b17': True, '0000006d--05e83bb04f': True, '0000006e--6ca3e014fd': False,
         '00000075--6c8687d5bd': False, '00000076--d0b7ea7e4d': False}   # from initData, hl_params.py

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route = col('group'), col('v'), col('sjump'), col('route')
dwell = col('dwell_s'); kind = col('kind')
d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
aa_pre = W['aa'][:, PRE]
toward = (sj == -np.sign(aa_pre)).astype(float)
LOW = TQ & (v >= 2) & (v < 8)

print("=" * 100)
print("(1) IS THE STORED hold_aa CHANNEL LEVELLED?  (recompute both from the stored aa,v channels)")
print("    rms|stored - recomputed| for level=flown vs level=False, per route, over the whole window")
for rk in sorted(set(route)):
    m = route == rk
    if not m.any():
        continue
    aa = W['aa'][m].ravel(); vv = W['v'][m].ravel(); st = W['hold_aa'][m].ravel()
    ok = np.isfinite(aa) & np.isfinite(vv) & np.isfinite(st)
    aa, vv, st = aa[ok], vv[ok], st[ok]
    hF = hold_torque(aa, vv, False); hT = hold_torque(aa, vv, True)
    lv = LEVEL.get(rk, None)
    print(f"  {rk}  grp {EP[int(np.where(m)[0][0])]['group']:5s} flown_level {lv}"
          f"   vs level=False {np.sqrt(np.mean((st-hF)**2)):.3e}"
          f"   vs level=True {np.sqrt(np.mean((st-hT)**2)):.3e}"
          f"   |True-False| rms {np.sqrt(np.mean((hT-hF)**2)):.3e}")

print()
print("=" * 100)
print("(2) STORED DECOMPOSITION VALIDATION (ss_extract val: z vs the log's implied z residual)")
for rk in sorted(VAL):
    if VAL[rk]:
        print(f"  {rk}  " + "  ".join(f"{k}={x:.4f}" for k, x in VAL[rk].items()))

print()
print("=" * 100
      )
print("(3) EPISODES IN THE 2-8 m/s HANDS-OFF TORQUE SET, per route")
print(f"  {'route':22s} {'grp':5s} {'lvl':4s} {'n':>4s} {'n_out':>6s} {'n_in':>5s} {'v med':>6s} {'v rng':>12s}"
      f" {'|ang| med':>10s} {'|ang| rng':>14s} {'dwell med':>10s} {'fade med':>9s} {'fade=0':>7s} {'fade=1':>7s}")
for rk in sorted(set(route[LOW])):
    m = LOW & (route == rk)
    fade = np.interp(v[m], DOB_FADE_BP, [0.0, 1.0])
    ab = np.abs(aa_pre[m])
    print(f"  {rk:22s} {EP[int(np.where(m)[0][0])]['group']:5s} {str(LEVEL.get(rk)):4s} {int(m.sum()):4d}"
          f" {int((m & (toward == 0)).sum()):6d} {int((m & (toward == 1)).sum()):5d}"
          f" {np.median(v[m]):6.2f} {v[m].min():5.2f}-{v[m].max():5.2f}"
          f" {np.median(ab):10.2f} {ab.min():6.2f}-{ab.max():6.2f}"
          f" {np.median(dwell[m]):10.2f} {np.median(fade):9.2f}"
          f" {int((fade <= 0.01).sum()):7d} {int((fade >= 0.99).sum()):7d}")
print("  fade = HONDA_ACCORD_DOB_FADE_V_BP interp(v,[3,6],[0,1]): the observer's authority multiplier")

print()
print("  kind mix per route (cont/rest/rev) and angle-speed correlation (the fit-misspec confound):")
for rk in sorted(set(route[LOW])):
    m = LOW & (route == rk)
    ks = {k: int((m & (kind == k)).sum()) for k in ('cont', 'rest', 'rev')}
    r = np.corrcoef(np.abs(aa_pre[m]), v[m])[0, 1] if m.sum() > 3 else np.nan
    rl = np.corrcoef(np.log10(np.maximum(np.abs(aa_pre[m]), 1e-3)), v[m])[0, 1] if m.sum() > 3 else np.nan
    print(f"  {rk}  {ks}   corr(|ang|,v) {r:+.2f}  corr(log|ang|,v) {rl:+.2f}")
m = LOW
print(f"  POOLED  corr(|ang|,v) {np.corrcoef(np.abs(aa_pre[m]), v[m])[0,1]:+.2f}"
      f"  corr(log|ang|,v) {np.corrcoef(np.log10(np.maximum(np.abs(aa_pre[m]),1e-3)), v[m])[0,1]:+.2f}")

print()
print("  the fork's hold stiffness k(v)*level over 2-8 m/s, against the band fit's single k=0.005560:")
for vq in (2, 3, 4, 5, 6, 7, 8):
    print(f"    v {vq:2d}  k {k_of_v(vq):.5f}   k*1.15 {k_of_v(vq)*1.15:.5f}"
          f"   sat {HOLD_SAT[0]+HOLD_SAT[1]*np.exp(-vq/HOLD_SAT[2]):7.1f} deg")
