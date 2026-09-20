"""STEP 5  THE CRUX OF MY VERDICT, verified independently of the band fit.

Is the gap between the command that actually holds the wheel and the fork's hold map
  (i)  MULTIPLICATIVE  (a stiffness / level deficit: gap grows with the map)           -> cause (A)
  (ii) ADDITIVE        (a missing constant intercept, flat in |angle| beyond a small
                        threshold)                                                     -> NOT a stiffness lever
  (iii) something else (a bump)?

Method: the direction-averaged hold read of attr3/attr4 (Coulomb cancels), over a finer grid of
(|angle|, v) cells, with a ROUTE-CLUSTER bootstrap that recomputes every cell inside each draw, and
a leave-one-cell-out check.  Nothing here uses the band fit, k, c, or the episode selection beyond
"these window frames are hands-off at 2-8 m/s".
"""
import numpy as np
from attr_lib import build, fit_lin, quintiles, bins, BK, PRE

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; route = D['route']
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']
NF = aaW.shape[1]
rmask = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
FM = np.repeat(rmask[:, None], NF, 1) & (vW >= 2) & (vW < 8)
Sf = np.sign(aaW)
MOV = FM & (np.abs(srW) > 3.0)
MAPL = np.abs(D['hold_aa_lev'])
ABINS = [(0.3, 0.7), (0.7, 1.2), (1.2, 2.0), (2.0, 3.2), (3.2, 5.0), (5.0, 8.0), (8.0, 13.0), (13.0, 40.0)]
VBINS = [(2, 4), (4, 6), (6, 8)]
NMIN = 120


def cells(rows_mask, nmin=NMIN):
    out = []
    for v0, v1 in VBINS:
        for a0, a1 in ABINS:
            base = MOV & rows_mask & (vW >= v0) & (vW < v1) & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1)
            mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
            np_, nn_ = int(mp.sum()), int(mn.sum())
            if np_ < nmin or nn_ < nmin:
                continue
            a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
            out.append(dict(v0=v0, v1=v1, a0=a0, a1=a1, v=float(np.median(vW[base])),
                            aa=float(np.median(np.abs(aaW)[base])), hold=(a_ + t_) / 2, F=(a_ - t_) / 2,
                            map=float(np.median(MAPL[base])), n=np_ + nn_))
    return out


ALLR = np.ones_like(MOV)
R = cells(ALLR)
print("=" * 110)
print("(1) THE GRID  -- direction-averaged hold read per (|angle|, v) cell, |sr| > 3 deg/s")
print(f"    {'v band':>8s} {'|aa| band':>12s} {'med v':>6s} {'med|aa|':>8s} {'n':>7s} {'hold_meas':>10s}"
      f" {'F_meas':>9s} {'fork map':>9s} {'GAP':>9s} {'ratio':>7s}")
for r in R:
    print(f"    {r['v0']}-{r['v1']:<6d} {r['a0']:5.1f}-{r['a1']:5.1f} {r['v']:6.2f} {r['aa']:8.2f} {r['n']:7d}"
          f" {r['hold']:+10.4f} {r['F']:+9.4f} {r['map']:+9.4f} {r['hold']-r['map']:+9.4f}"
          f" {r['hold']/max(r['map'],1e-9):7.2f}")
print(f"    {len(R)} cells;  GAP = hold_meas - fork levelled map at the same (|aa|, v)")

print()
print("=" * 110)
print("(2) MODEL COMPARISON on the grid.  weights = sqrt(n).  A 'stiffness/level deficit' is the")
print("    MULTIPLICATIVE row; a missing intercept is the ADDITIVE row.")
x = np.array([r['map'] for r in R]); y = np.array([r['hold'] for r in R])
a = np.array([r['aa'] for r in R]); w = np.sqrt([r['n'] for r in R])
MODELS = {
    'multiplicative   G*map': lambda x, a: np.vstack([x]).T,
    'additive         map + A': lambda x, a: np.vstack([np.ones_like(x)]).T,
    'both             G*map + A': lambda x, a: np.vstack([x, np.ones_like(x)]).T,
    'stiff+sat        G*map + A*tanh(|aa|/0.6)': lambda x, a: np.vstack([x, np.tanh(a / 0.6)]).T,
    'prop in angle    G*map + B*|aa|': lambda x, a: np.vstack([x, a]).T,
    'additive only    A  (no map at all)': lambda x, a: np.vstack([np.ones_like(x)]).T,
}


def wfit(X, y, w, off=0.0):
    c, *_ = np.linalg.lstsq(X * w[:, None], (y - off) * w, rcond=None)
    r = y - off - X @ c
    return c, float(np.sqrt(np.average(r ** 2, weights=w ** 2)))


print(f"    {'model':46s} {'coefs':>28s} {'wrms':>9s} {'max|resid|':>11s}")
for nm, f in MODELS.items():
    off = x if nm.startswith('additive         ') else 0.0
    X = f(x, a)
    c, wr = wfit(X, y, w, off)
    r = y - (off if isinstance(off, np.ndarray) else 0.0) - X @ c
    print(f"    {nm:46s} {str(np.round(c,4)):>28s} {wr:9.4f} {np.max(np.abs(r)):11.4f}")

print()
print("    ROUTE-CLUSTER BOOTSTRAP of the two-parameter fit (every cell recomputed inside each draw)")
u = np.unique(route[LOW]); rng = np.random.default_rng(31)
bs = []
for _ in range(400):
    pick = rng.choice(u, len(u))
    rm = np.zeros(D['N'], bool)
    # concatenate route blocks: build a frame mask that repeats a route's rows once per draw
    sel = np.concatenate([np.where(route == c)[0] for c in pick])
    rm2 = np.zeros((len(sel), NF), bool); rm2[:] = True
    # recompute the grid on the resampled episode set
    def cells_sel(sel):
        out = []
        for v0, v1 in VBINS:
            for a0, a1 in ABINS:
                b = MOV[sel] & (vW[sel] >= v0) & (vW[sel] < v1) & (np.abs(aaW[sel]) >= a0) & (np.abs(aaW[sel]) < a1)
                sp = Sf[sel]
                mp = b & (np.sign(srW[sel]) == sp); mn = b & (np.sign(srW[sel]) == -sp)
                if mp.sum() < NMIN or mn.sum() < NMIN:
                    continue
                a_ = np.median((cmdW[sel] * sp)[mp]); t_ = np.median((cmdW[sel] * sp)[mn])
                out.append(((a_ + t_) / 2, float(np.median(MAPL[sel][b])), mp.sum() + mn.sum()))
        return out
    cs = cells_sel(sel)
    if len(cs) < 4:
        continue
    yy = np.array([c[0] for c in cs]); xx = np.array([c[1] for c in cs]); ww = np.sqrt([c[2] for c in cs])
    c2, _ = wfit(np.vstack([xx, np.ones_like(xx)]).T, yy, ww)
    c1, _ = wfit(np.vstack([xx]).T, yy, ww)
    bs.append([c2[0], c2[1], c1[0]])
bs = np.array(bs)
print(f"    draws {len(bs)}")
print(f"      G (with intercept)   point {wfit(np.vstack([x,np.ones_like(x)]).T,y,w)[0][0]:+.3f}"
      f"   CI [{np.percentile(bs[:,0],2.5):+.3f},{np.percentile(bs[:,0],97.5):+.3f}]")
print(f"      A (the intercept)    point {wfit(np.vstack([x,np.ones_like(x)]).T,y,w)[0][1]:+.4f}"
      f"   CI [{np.percentile(bs[:,1],2.5):+.4f},{np.percentile(bs[:,1],97.5):+.4f}]")
print(f"      G (gain-only, no A)  point {wfit(np.vstack([x]).T,y,w)[0][0]:+.3f}"
      f"   CI [{np.percentile(bs[:,2],2.5):+.3f},{np.percentile(bs[:,2],97.5):+.3f}]")

print()
print("    LEAVE-ONE-CELL-OUT: does any single cell carry the verdict?")
for i in range(len(R)):
    k = np.ones(len(R), bool); k[i] = False
    c2, w2 = wfit(np.vstack([x[k], np.ones(k.sum())]).T, y[k], w[k])
    c1, w1 = wfit(np.vstack([x[k]]).T, y[k], w[k])
    print(f"      drop {R[i]['v0']}-{R[i]['v1']} m/s {R[i]['a0']:5.1f}-{R[i]['a1']:5.1f} deg:"
          f"  G {c2[0]:+.3f}  A {c2[1]:+.4f}  wrms {w2:.4f}   | gain-only G {c1[0]:+.3f} wrms {w1:.4f}")

print()
print("=" * 110)
print("(3) THE DISCRIMINATOR.  A multiplicative deficit must make the GAP grow with the map;")
print("    an additive one must make it FLAT.  GAP vs the map, sorted by the map:")
o = np.argsort(x)
print(f"    {'map':>8s} {'|aa|':>7s} {'v':>6s} {'GAP':>9s} {'GAP/map':>8s} {'pred x1.70':>11s} {'pred +A':>9s}")
Gg = wfit(np.vstack([x]).T, y, w)[0][0]; Aa = wfit(np.vstack([x, np.ones_like(x)]).T, y, w)[0]
for i in o:
    print(f"    {x[i]:8.4f} {a[i]:7.2f} {R[i]['v']:6.2f} {y[i]-x[i]:+9.4f} {(y[i]-x[i])/x[i]:8.2f}"
          f" {(Gg-1)*x[i]:+11.4f} {Aa[0]*x[i]+Aa[1]-x[i]:+9.4f}")
print("\n    correlation of GAP with the map:  "
      f"{np.corrcoef(x, y-x)[0,1]:+.3f}   (multiplicative requires strongly positive)")
print(f"    correlation of GAP/map with the map: {np.corrcoef(x, (y-x)/x)[0,1]:+.3f}"
      f"   (additive requires strongly negative)")

print()
print("=" * 110)
print("(4) SPEED dependence of the gap at roughly fixed angle (is this a LEVEL schedule problem?)")
for a0, a1 in ABINS:
    row = [r for r in R if (r['a0'], r['a1']) == (a0, a1)]
    if len(row) < 2:
        continue
    print(f"    |aa| {a0:5.1f}-{a1:5.1f}: " + "   ".join(
        f"v{r['v0']}-{r['v1']} map {r['map']:.4f} hold {r['hold']:+.4f} gap {r['hold']-r['map']:+.4f}" for r in row))

print()
print("=" * 110)
print("(5) COULOMB F from the same read vs the band half-width (a consistency check on the whole frame)")
print(f"    F_meas over cells: median {np.median([r['F'] for r in R]):+.4f}"
       f"  IQR [{np.percentile([r['F'] for r in R],25):+.4f},{np.percentile([r['F'] for r in R],75):+.4f}]")
f0 = fit_lin(D, LOW, np.full(D['N'], BK))
print(f"    band half-width from the episode fit: {f0['halfwidth']:+.4f}")
print(f"    fork's HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020 ; flown AccordFrictionHyst = 0.015")
print(f"    correlation of F_meas with |aa|: {np.corrcoef(a, [r['F'] for r in R])[0,1]:+.3f}"
      f"   with v: {np.corrcoef([r['v'] for r in R], [r['F'] for r in R])[0,1]:+.3f}")
np.savez('gap_grid.npz', x=x, y=y, a=a, w=w, v=np.array([r['v'] for r in R]),
         F=np.array([r['F'] for r in R]))
print("    grid saved to gap_grid.npz")
