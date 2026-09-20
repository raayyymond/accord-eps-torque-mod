"""STEP 6  the crux of MY headline number, attacked.

The direction-averaged read  hold = (cmd|rate>0 + cmd|rate<0)/2 * sign(aa)  cancels Coulomb friction
ONLY exactly; the VISCOUS term b*rate cancels only if the two legs have symmetric rate MAGNITUDES.
With the fork's own model b = 1/G(v) ~ 0.0018-0.0021 torque per deg/s at 5-7 m/s, a 12 deg/s
magnitude asymmetry alone would fake the whole +0.022 intercept.  So:
 (1) census the per-leg rate magnitudes in every cell;
 (2) redo the read with the legs RATE-MATCHED (same |sr| histogram) -- the leak cannot survive that;
 (3) redo it with an explicit b*rate subtraction at b = 0.0006 (identified plant) and b = 1/G(v) (fork model);
 (4) fit the missing term's SHAPE: A * tanh(|aa| / w) with w free, and report A, w;
 (5) figure: the three profiles the orchestrator asked for on one axis.
"""
import numpy as np
from attr_lib import build, fit_lin, quintiles, bins, BK, PRE, CHAN
from sslib import G_BP, G_V

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; route = D['route']
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']
NF = aaW.shape[1]
rmask = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
FM = np.repeat(rmask[:, None], NF, 1) & (vW >= 2) & (vW < 8)
Sf = np.sign(aaW); MOV = FM & (np.abs(srW) > 3.0)
MAPL = np.abs(D['hold_aa_lev'])
BMODEL = 1.0 / np.interp(vW, G_BP, G_V)
ABINS = [(0.3, 0.7), (0.7, 1.2), (1.2, 2.0), (2.0, 3.2), (3.2, 5.0), (5.0, 8.0), (8.0, 13.0), (13.0, 40.0)]
VBINS = [(4, 6), (6, 8)]
NMIN = 120

print("=" * 112)
print("(1) PER-LEG RATE MAGNITUDES.  leak = b * (med|sr|_away - med|sr|_toward) / 2")
print(f"    {'v':>7s} {'|aa|':>11s} {'n_aw':>6s} {'n_tw':>6s} {'|sr|aw':>8s} {'|sr|tw':>8s} {'asym':>7s}"
      f" {'leak b=6e-4':>12s} {'leak b=1/G':>11s} {'GAP':>9s}")
ROWS = []
for v0, v1 in VBINS:
    for a0, a1 in ABINS:
        base = MOV & (vW >= v0) & (vW < v1) & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1)
        mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
        if mp.sum() < NMIN or mn.sum() < NMIN:
            continue
        ra, rt = np.median(np.abs(srW)[mp]), np.median(np.abs(srW)[mn])
        bm = np.median(BMODEL[base])
        a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
        hold = (a_ + t_) / 2; mp_ = np.median(MAPL[base])
        ROWS.append(dict(v0=v0, v1=v1, a0=a0, a1=a1, v=float(np.median(vW[base])), aa=float(np.median(np.abs(aaW)[base])),
                         hold=hold, F=(a_ - t_) / 2, map=mp_, n=int(mp.sum() + mn.sum()), ra=ra, rt=rt, bm=bm))
        print(f"    {v0}-{v1:<4d} {a0:5.1f}-{a1:5.1f} {int(mp.sum()):6d} {int(mn.sum()):6d} {ra:8.2f} {rt:8.2f}"
              f" {ra-rt:+7.2f} {6e-4*(ra-rt)/2:+12.4f} {bm*(ra-rt)/2:+11.4f} {hold-mp_:+9.4f}")
print("    (a POSITIVE asym with a positive b inflates hold_meas; compare the leak columns to GAP)")

print()
print("=" * 112)
print("(2) RATE-MATCHED read.  Within each cell, bin |sr| into 1 deg/s slices, and use only slices")
print("    where BOTH legs have >= 25 frames; average the per-slice hold with equal slice weights.")
print("    Any viscous leak is removed by construction (matched |sr| on both legs).")
print(f"    {'v':>7s} {'|aa|':>11s} {'slices':>7s} {'n':>7s} {'hold_matched':>13s} {'hold_raw':>9s}"
      f" {'map':>8s} {'GAP_matched':>12s} {'GAP_raw':>9s}")
MR = []
for r in ROWS:
    base = MOV & (vW >= r['v0']) & (vW < r['v1']) & (np.abs(aaW) >= r['a0']) & (np.abs(aaW) < r['a1'])
    mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
    srmag = np.abs(srW)
    hs, ns, sl = [], 0, 0
    for s0 in np.arange(3, 40, 1.0):
        sa = mp & (srmag >= s0) & (srmag < s0 + 1); st = mn & (srmag >= s0) & (srmag < s0 + 1)
        if sa.sum() < 25 or st.sum() < 25:
            continue
        hs.append((np.median((cmdW * Sf)[sa]) + np.median((cmdW * Sf)[st])) / 2)
        ns += int(sa.sum() + st.sum()); sl += 1
    if sl == 0:
        print(f"    {r['v0']}-{r['v1']:<4d} {r['a0']:5.1f}-{r['a1']:5.1f}  no matched slices")
        continue
    hm = float(np.mean(hs))
    MR.append(dict(r, hold_m=hm, nslice=sl, nm=ns))
    print(f"    {r['v0']}-{r['v1']:<4d} {r['a0']:5.1f}-{r['a1']:5.1f} {sl:7d} {ns:7d} {hm:+13.4f}"
          f" {r['hold']:+9.4f} {r['map']:+8.4f} {hm-r['map']:+12.4f} {r['hold']-r['map']:+9.4f}")

print()
print("=" * 112)
print("(3) EXPLICIT b*rate SUBTRACTION, both b estimates, on the raw read")
print(f"    {'v':>7s} {'|aa|':>11s} {'map':>8s} {'GAP raw':>9s} {'GAP b=6e-4':>11s} {'GAP b=1/G':>10s}")
for r in ROWS:
    base = MOV & (vW >= r['v0']) & (vW < r['v1']) & (np.abs(aaW) >= r['a0']) & (np.abs(aaW) < r['a1'])
    mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
    out = []
    for b in (6e-4, None):
        bb = (np.full_like(srW, 6e-4) if b is not None else BMODEL)
        cc = (cmdW - bb * srW) * Sf
        out.append((np.median(cc[mp]) + np.median(cc[mn])) / 2 - r['map'])
    r['gap_b6'], r['gap_bG'] = out
    print(f"    {r['v0']}-{r['v1']:<4d} {r['a0']:5.1f}-{r['a1']:5.1f} {r['map']:+8.4f} {r['hold']-r['map']:+9.4f}"
          f" {out[0]:+11.4f} {out[1]:+10.4f}")


def wfit(X, y, w, off=0.0):
    c, *_ = np.linalg.lstsq(X * w[:, None], (y - off) * w, rcond=None)
    r = y - off - X @ c
    return c, float(np.sqrt(np.average(r ** 2, weights=w ** 2)))


print("\n    refit  hold = G*map + A  on each version:")
x = np.array([r['map'] for r in ROWS]); w = np.sqrt([r['n'] for r in ROWS])
for nm, yv in (('raw', np.array([r['hold'] for r in ROWS])),
               ('b=6e-4 removed', np.array([r['gap_b6'] + r['map'] for r in ROWS])),
               ('b=1/G(v) removed', np.array([r['gap_bG'] + r['map'] for r in ROWS])),
               ('rate-matched', np.array([d['hold_m'] for d in MR]) if len(MR) == len(ROWS) else None)):
    if yv is None:
        print(f"      {nm:20s} skipped (matched grid has {len(MR)} of {len(ROWS)} cells)")
        continue
    c2, w2 = wfit(np.vstack([x, np.ones_like(x)]).T, yv, w)
    c1, w1 = wfit(np.vstack([x]).T, yv, w)
    print(f"      {nm:20s} G {c2[0]:+.3f}  A {c2[1]:+.4f}  wrms {w2:.4f}"
          f"   | gain-only G {c1[0]:+.3f} wrms {w1:.4f}")
if len(MR) != len(ROWS):
    xm = np.array([d['map'] for d in MR]); ym = np.array([d['hold_m'] for d in MR]); wm = np.sqrt([d['nm'] for d in MR])
    c2, w2 = wfit(np.vstack([xm, np.ones_like(xm)]).T, ym, wm)
    c1, w1 = wfit(np.vstack([xm]).T, ym, wm)
    print(f"      {'rate-matched':20s} G {c2[0]:+.3f}  A {c2[1]:+.4f}  wrms {w2:.4f}"
          f"   | gain-only G {c1[0]:+.3f} wrms {w1:.4f}   ({len(MR)} cells)")

print()
print("=" * 112)
print("(4) SHAPE of the missing term.  hold = G*map + A*tanh(|aa|/w), w scanned.")
a = np.array([r['aa'] for r in ROWS]); y = np.array([r['hold'] for r in ROWS])
best = None
for ww in [0.2, 0.4, 0.6, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0, 1e6]:
    c2, wr = wfit(np.vstack([x, np.tanh(a / ww)]).T, y, w)
    tag = 'linear in |aa|' if ww > 1e5 else ''
    print(f"      w={ww:8.1f} deg   G {c2[0]:+.3f}  A {c2[1]:+.4f}  wrms {wr:.4f}  {tag}")
    if best is None or wr < best[0]:
        best = (wr, ww, c2)
print(f"    BEST  w {best[1]} deg   G {best[2][0]:+.3f}  A {best[2][1]:+.4f}  wrms {best[0]:.4f}")
print("    for comparison, the fork's own HOLD_SAT at 5-7 m/s (the map's saturation scale):")
from sslib import HOLD_SAT
for vv in (3, 5, 7):
    print(f"      v={vv}: sat = {HOLD_SAT[0]+HOLD_SAT[1]*np.exp(-vv/HOLD_SAT[2]):.1f} deg"
          f"  (so the map is NEAR-LINEAR over 0-20 deg here)")

print()
print("=" * 112)
print("(5) FIGURE: the CENTRE and the I / dob profiles on one axis")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
f0 = fit_lin(D, LOW, np.full(D['N'], BK)); K, C = f0['k'], f0['const']
S = np.sign(D['aa_pre']); aabs = np.abs(D['aa_pre'])
Y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
qs, _ = quintiles(D)
tw = D['toward']


def prof(y, mask=None):
    xs, ys = [], []
    for lo, hi, m in bins(D, LOW if mask is None else mask, qs, aabs):
        ma, mt = m & (tw == 0), m & (tw == 1)
        if ma.sum() < 3 or mt.sum() < 3:
            xs.append(np.nan); ys.append(np.nan); continue
        xs.append(np.median(aabs[m])); ys.append((np.median(y[ma]) + np.median(y[mt])) / 2)
    return np.array(xs), np.array(ys)


fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
ax = axes[0]
for nm, y_, st in (('CENTRE (cmd - k*aa - c)', Y, 'k-o'),
                   ('dob', W['dob'][ar, BK] * S, 'C0-s'),
                   ('I (PID integral)', W['I'][ar, BK] * S, 'C1-^'),
                   ('P', W['P'][ar, BK] * S, 'C2-v'),
                   ('hold_ff net of k*aa', (W['hold_ff'][ar, BK] - K * W['aa'][ar, BK] - C) * S, 'C3-d'),
                   ('z (friction hyst)', W['z'][ar, BK] * S, 'C4-x')):
    xs, ys = prof(y_)
    ax.plot(xs, ys, st, label=nm, ms=5, lw=1.4)
ax.axhline(0, color='0.6', lw=0.8)
ax.set_xscale('log'); ax.set_xlabel('|steering angle| at breakaway (deg, log)')
ax.set_ylabel('band CENTRE contribution (torque)')
ax.set_title('Who carries the band centre\n(torque routes, 2-8 m/s, n=145)')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

ax = axes[1]
o = np.argsort(a)
ax.plot(a[o], y[o], 'k-o', label='measured hold (direction-averaged cmd)', ms=5)
ax.plot(a[o], x[o], 'C3--s', label='fork levelled hold map', ms=5)
ax.plot(a[o], (best[2][0] * x + best[2][1] * np.tanh(a / best[1]))[o], 'C0-.',
        label=f'G={best[2][0]:.2f} x map + {best[2][1]:.4f}*tanh(|aa|/{best[1]:g})')
gg = wfit(np.vstack([x]).T, y, w)[0][0]
ax.plot(a[o], (gg * x)[o], 'C2:', label=f'multiplicative only, x{gg:.2f} map')
ax.set_xscale('log'); ax.set_xlabel('|steering angle| (deg, log)'); ax.set_ylabel('hold torque')
ax.set_title('Independent plant-hold read vs the fork map\n(hands-off moving frames, Coulomb cancelled)')
ax.legend(fontsize=8); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig('attr_profiles.png', dpi=130)
print("    wrote attr_profiles.png")
