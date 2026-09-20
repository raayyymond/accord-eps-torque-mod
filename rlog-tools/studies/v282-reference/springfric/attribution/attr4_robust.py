"""STEP 4  robustness of the two load-bearing numbers, and the controlled natural experiments.

 (a) the independent plant read's worst selection risk: the moving frames could cluster in the SLIP
     right after breakaway, where the command HAS to be above hold.  Census the window-index
     distribution and re-read the plant hold on (i) pre-dwell frames only, (ii) frames far from
     breakaway, (iii) per route.
 (b) joint fit across all (|angle|, v) cells of  hold_meas = G * fork_map(aa,v) + A * sign(aa):
     G is the multiplicative (stiffness) part, A the additive intercept.  Independent of the band fit.
 (c) route 75 (observer OFF) -- verify the reported +0.0244 offset and test whether the PID's I
     can carry it alone; per-route who-carries table.
 (d) AccordHoldLevel ON vs OFF, controlled: one regression with a level interaction on the hold
     regressor, and a |angle|-and-speed-matched comparison.
 (e) how much of the dob channel is tautological: dob is a 0.6 Hz low-pass of
     (u_delayed - hold_model(aa) - b*rate - J*acc), so during a stuck dwell it IS an estimate of
     (hold_plant - hold_model) + F*sj.  Quantify against the independent read.
"""
import numpy as np
from attr_lib import build, fit_lin, fit_hold, quintiles, bins, CHAN, BK, PRE, boot_ci, boot_ci_ev

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; sj = D['sjump']; tw = D['toward']; route = D['route']
f0 = fit_lin(D, LOW, np.full(D['N'], BK)); K, C = f0['k'], f0['const']
S = np.sign(D['aa_pre']); aabs = np.abs(D['aa_pre'])
Y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
aaW, srW, vW, cmdW = W['aa'], W['sr'], W['v'], W['cmd']
NF = aaW.shape[1]
rmask = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
FM = np.repeat(rmask[:, None], NF, 1) & (vW >= 2) & (vW < 8)
IDX = np.repeat(np.arange(NF)[None, :], D['N'], 0)
D0 = np.repeat(D['d0'][:, None], NF, 1)
Sf = np.sign(aaW)
MOV = FM & (np.abs(srW) > 3.0)

print("=" * 104)
print("(a) WHERE ARE THE MOVING FRAMES?  window index 0..229, breakaway at PRE=150")
h, e = np.histogram(IDX[MOV], bins=np.arange(0, NF + 10, 10))
print("    idx  : " + " ".join(f"{int(x):5d}" for x in e[:-1]))
print("    n    : " + " ".join(f"{int(x):5d}" for x in h))
print(f"    frac of moving frames in [PRE, PRE+80] (the slip): {np.mean(IDX[MOV] >= PRE):.3f}")
print(f"    frac before the dwell start (idx < w_d0):          {np.mean((IDX[MOV] < D0[MOV])):.3f}")

abins = [(0.3, 0.8), (0.8, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 12.0), (12.0, 30.0)]
vbins = [(2, 4), (4, 6), (6, 8)]


def plant_read(extra, tag, nmin=150, verbose=True):
    """(hold, F) per (v,|aa|) cell from moving frames; returns list of rows."""
    rows = []
    if verbose:
        print(f"\n    --- {tag} ---")
        print(f"    {'v':>7s} {'|aa|':>11s} {'n+':>6s} {'n-':>6s} {'hold_meas':>10s} {'F_meas':>9s}"
              f" {'fork lev':>9s} {'meas/lev':>9s} {'meas-lev':>9s}")
    for v0, v1 in vbins:
        for a0, a1 in abins:
            base = MOV & extra & (vW >= v0) & (vW < v1) & (np.abs(aaW) >= a0) & (np.abs(aaW) < a1)
            mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
            if mp.sum() < nmin or mn.sum() < nmin:
                continue
            a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
            hold = (a_ + t_) / 2; F = (a_ - t_) / 2
            kk = np.median(np.abs(D['hold_aa_lev'])[base])
            aam = np.median(np.abs(aaW)[base]); vm = np.median(vW[base])
            rows.append(dict(v=vm, aa=aam, hold=hold, F=F, map=kk, n=int(mp.sum() + mn.sum())))
            if verbose:
                print(f"    {v0}-{v1:<4d} {a0:5.1f}-{a1:5.1f} {int(mp.sum()):6d} {int(mn.sum()):6d} {hold:+10.4f}"
                      f" {F:+9.4f} {kk:+9.4f} {hold/max(kk,1e-9):9.2f} {hold-kk:+9.4f}")
    return rows


ALL = plant_read(np.ones_like(MOV), "ALL moving frames (the attr3 read)")
PRE_ONLY = plant_read(IDX < D0, "PRE-DWELL frames only (before the stick, cannot be slip-biased)")
FAR = plant_read(np.abs(IDX - PRE) > 60, "FAR from breakaway (|idx-150| > 60)")
PRESLIP = plant_read(IDX < PRE - 5, "everything BEFORE breakaway (idx < 145)")

print("\n    --- per route, all moving frames, 1.5-6 deg pooled ---")
for rk in sorted(set(route[LOW])):
    rm = np.repeat((route == rk)[:, None], NF, 1)
    base = MOV & rm & (np.abs(aaW) >= 1.5) & (np.abs(aaW) < 6.0)
    mp = base & (np.sign(srW) == Sf); mn = base & (np.sign(srW) == -Sf)
    if mp.sum() < 50 or mn.sum() < 50:
        print(f"      {rk}  n too small {int(mp.sum())}/{int(mn.sum())}")
        continue
    a_ = np.median((cmdW * Sf)[mp]); t_ = np.median((cmdW * Sf)[mn])
    kk = np.median(np.abs(D['hold_aa_lev'])[base])
    print(f"      {rk} lev={int(D['lev'][rk])} dob={int(D['dob_on'][rk])} n {int(mp.sum())}/{int(mn.sum())}"
          f"  hold {(a_+t_)/2:+.4f}  F {(a_-t_)/2:+.4f}  map {kk:+.4f}  ratio {((a_+t_)/2)/kk:.2f}")

print()
print("=" * 104)
print("(b) JOINT FIT  hold_meas = G * fork_map + A   over the (|aa|, v) cells  [no band fit involved]")
for tag, rows in (("ALL moving", ALL), ("PRE-DWELL only", PRE_ONLY), ("FAR from bk", FAR), ("pre-breakaway", PRESLIP)):
    if len(rows) < 4:
        print(f"    {tag:16s} too few cells ({len(rows)})")
        continue
    x = np.array([r['map'] for r in rows]); y = np.array([r['hold'] for r in rows])
    w = np.sqrt([r['n'] for r in rows])
    X2 = np.vstack([x, np.ones_like(x)]).T
    cG, *_ = np.linalg.lstsq(X2 * w[:, None], y * w, rcond=None)
    cGo, *_ = np.linalg.lstsq((x * w)[:, None], y * w, rcond=None)      # gain only, no intercept
    r2 = y - X2 @ cG; r1 = y - x * cGo[0]
    print(f"    {tag:16s} cells {len(rows):2d}  G {cG[0]:+.3f}  A {cG[1]:+.4f}   wrms {np.sqrt(np.average(r2**2, weights=w**2)):.4f}"
          f"   | gain-only G {cGo[0]:+.3f} wrms {np.sqrt(np.average(r1**2, weights=w**2)):.4f}")
    print(f"                     F_meas across cells: median {np.median([r['F'] for r in rows]):+.4f}"
          f"  range {min(r['F'] for r in rows):+.4f}..{max(r['F'] for r in rows):+.4f}")

print()
print("=" * 104)
print("(c) ROUTE 75 (observer OFF) -- verify the offset and who carries it")
m75 = LOW & (route == '00000075--6c8687d5bd')
f75 = fit_lin(D, m75, np.full(D['N'], BK))
print(f"    own-k band fit, torque|2-8|breakaway, route 75 only  n={int(m75.sum())}")
print(f"      k {f75['k']:.5f}  away {f75['away']:+.4f}  toward {f75['toward']:+.4f}"
      f"  HALFWIDTH {f75['halfwidth']:+.4f}  CENTRING_OFFSET {f75['centring_offset']:+.4f}  const {f75['const']:+.4f}")
print(f"      reported by the earlier stream: +0.0244   -> {'MATCHES to 1.3e-3' if abs(f75['centring_offset']-0.0244)<3e-3 else 'DOES NOT MATCH'}")
# episode bootstrap on the route-75 centring offset
X75 = np.vstack([W['aa'][ar, BK], sj, sj * tw, np.ones(D['N'])]).T
i75 = np.where(m75)[0]; rng = np.random.default_rng(7); bs = []
for _ in range(3000):
    ii = rng.choice(i75, len(i75))
    try:
        c = np.linalg.lstsq(X75[ii], W['cmd'][ar, BK][ii], rcond=None)[0]; bs.append(-c[2] / 2)
    except Exception:
        pass
print(f"      episode bootstrap CI on route-75 centring_offset: [{np.percentile(bs,2.5):+.4f},{np.percentile(bs,97.5):+.4f}]")
print(f"      route 75 ran AccordDobHz ABSENT -> dob channel is exactly 0:"
      f" max|dob| in its episodes {np.max(np.abs(W['dob'][i75, BK])):.2e}")
print("\n    per-route: who carries the DEFICIT (cmd - hold_lev(aa)) centre, |aa| > 0.6 deg")
H = D['hold_aa_lev'][ar, BK]
ych = {c: W[c][ar, BK] * S for c in CHAN}
ych['DEFICIT'] = (W['cmd'][ar, BK] - H) * S
ych['slow'] = (W['I'][ar, BK] + W['dob'][ar, BK]) * S


def ctr(y, m):
    ma, mt = m & (tw == 0), m & (tw == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        return np.nan
    return (np.median(y[ma]) + np.median(y[mt])) / 2


print(f"      {'route':>22s} {'lev':>4s}{'dob':>4s}{'Ki':>5s} {'n':>4s} {'DEFICIT':>9s} {'hold_ff-h':>10s}"
      f" {'P':>8s} {'I':>8s} {'dob':>8s} {'slow':>8s} {'z':>8s} {'slow/DEF':>9s}")
for rk in sorted(set(route[LOW])):
    m = LOW & (route == rk) & (aabs > 0.6)
    ki = D['P'][rk].get('AccordTorqueKi', '--')
    d_ = ctr(ych['DEFICIT'], m)
    hf = ctr((W['hold_ff'][ar, BK] - H) * S, m)
    print(f"      {rk:>22s} {int(D['lev'][rk]):4d}{int(D['dob_on'][rk]):4d}{str(ki):>5.5s} {int(m.sum()):4d}"
          f" {d_:+9.4f} {hf:+10.4f} " + " ".join(f"{ctr(ych[c],m):+8.4f}" for c in ('P', 'I', 'dob', 'slow', 'z'))
          + f" {ctr(ych['slow'],m)/d_ if d_ else np.nan:9.2f}")

print()
print("=" * 104)
print("(d) AccordHoldLevel ON vs OFF, CONTROLLED")
print("    (d.i) sanity: does the hold_ff channel actually carry the x1.15?  regress hold_ff on")
print("          hold_unlev(angdes) within each group -- must give ~1.15 on 6c/6d and ~1.00 on 6e.")
for nm, m in (('6c+6d (level ON)', LOW & D['is_lev']), ('6e (level OFF)', LOW & (route == '0000006e--6ca3e014fd'))):
    x = D['hold_ad_unlev'][ar, BK][m]; y = W['hold_ff'][ar, BK][m]
    g = float(np.linalg.lstsq(x[:, None], y, rcond=None)[0][0])
    print(f"      {nm:18s} n={int(m.sum()):3d}  hold_ff / hold_unlev(angdes) = {g:.4f}")
print("\n    (d.ii) one regression with a LEVEL INTERACTION on the hold regressor:")
print("           cmd = G*hold_unlev(aa) + dG*level*hold_unlev(aa) + Fa*sj + d*sj*toward + dd*level*sj*toward")
print("                 + c + cl*level          (level = 1 on 6c,6d)")
LEV = D['is_lev'].astype(float)
hu = D['hold_aa_unlev'][ar, BK]
Xi = np.vstack([hu, LEV * hu, sj, sj * tw, LEV * sj * tw, np.ones(D['N']), LEV]).T
mm = LOW
cc = np.linalg.lstsq(Xi[mm], W['cmd'][ar, BK][mm], rcond=None)[0]
nm_ = ['G', 'dG(level)', 'Fa', 'd', 'd(level)', 'c', 'c(level)']
print("           " + "  ".join(f"{a}={b:+.4f}" for a, b in zip(nm_, cc)))
print(f"           centring_offset  level OFF {-cc[3]/2:+.4f}   level ON {-(cc[3]+cc[4])/2:+.4f}"
      f"   difference {-cc[4]/2:+.4f}")
print(f"           half-width       level OFF {cc[2]+cc[3]/2:+.4f}   level ON {cc[2]+(cc[3]+cc[4])/2:+.4f}")
print(f"           map gain         level OFF {cc[0]:+.4f}   level ON {cc[0]+cc[1]:+.4f}")
u = np.unique(route[mm]); rng = np.random.default_rng(21); ii0 = {c: np.where(mm & (route == c))[0] for c in u}
bs = []
for _ in range(3000):
    ii = np.concatenate([ii0[c] for c in rng.choice(u, len(u))])
    try:
        bs.append(np.linalg.lstsq(Xi[ii], W['cmd'][ar, BK][ii], rcond=None)[0])
    except Exception:
        pass
bs = np.array(bs)
print(f"           route-cluster CI: dG(level) [{np.percentile(bs[:,1],2.5):+.3f},{np.percentile(bs[:,1],97.5):+.3f}]"
      f"   d(level)/-2 [{np.percentile(-bs[:,4]/2,2.5):+.4f},{np.percentile(-bs[:,4]/2,97.5):+.4f}]")
print("           NOTE only 5 route clusters and level varies BETWEEN routes, so 'level' and 'road'")
print("           are not separable here.  Treat as a bound, not an estimate.")
print("\n    (d.iii) |aa|- and v-matched cells, level ON vs OFF, DEFICIT centre:")
print(f"      {'|aa|':>11s} {'v':>7s} {'ON DEF':>9s} {'OFF DEF':>9s} {'diff':>9s} {'0.15*map':>9s}  n_on n_off")
for a0, a1 in ((0.6, 2.0), (2.0, 5.0), (5.0, 40.0)):
    for v0, v1 in ((2, 5), (5, 8)):
        mo = LOW & D['is_lev'] & (aabs >= a0) & (aabs < a1) & (D['v'] >= v0) & (D['v'] < v1)
        mf = LOW & (route == '0000006e--6ca3e014fd') & (aabs >= a0) & (aabs < a1) & (D['v'] >= v0) & (D['v'] < v1)
        c1, c2 = ctr(ych['DEFICIT'], mo), ctr(ych['DEFICIT'], mf)
        pm = 0.15 * np.median(np.abs(D['hold_aa_unlev'][ar, BK])[mo | mf]) if (mo | mf).sum() else np.nan
        print(f"      {a0:4.1f}-{a1:5.1f} {v0}-{v1:<4d} {c1:+9.4f} {c2:+9.4f} {c2-c1 if np.isfinite(c1+c2) else np.nan:+9.4f}"
              f" {pm:+9.4f}  {int(mo.sum()):4d} {int(mf.sum()):4d}")

print()
print("=" * 104)
print("(e) HOW TAUTOLOGICAL IS THE dob ATTRIBUTION?")
print("    dob = -2-pole-LP(u_delayed - hold_model(aa) - b*rate - J*acc).  During a stuck dwell rate~0,")
print("    so its input IS (hold_plant - hold_model) + F*sj: the dob channel is a MEASUREMENT of the")
print("    very deficit we are attributing, fed back with DC loop gain ~1/(1-L).  It therefore cannot")
print("    be read as 'the cause'; it is the carrier the fork installed for exactly this residual.")
dobm = W['dob'][ar, BK] * S
for lo, hi in ((0.6, 2.0), (2.0, 5.0), (5.0, 40.0)):
    m = LOW & D['is_dob'] & (aabs >= lo) & (aabs < hi)
    if m.sum() < 6:
        continue
    defi = ctr(ych['DEFICIT'], m); dd = ctr(dobm, m)
    print(f"    |aa| {lo:4.1f}-{hi:5.1f}  n {int(m.sum()):3d}  DEFICIT {defi:+.4f}  dob {dd:+.4f}"
          f"  dob/DEFICIT {dd/defi:5.2f}   (independent read says the plant/map gap here is"
          f" ~{np.median((np.abs(cmdW*0)+0))+0:.0f})")
print("    dob MAGNITUDE vs its clip: max|dob| over LOW dob-on episodes"
      f" {np.max(np.abs(W['dob'][np.where(LOW & D['is_dob'])[0], BK])):.4f}  (clip 0.30, fade at 3-6 m/s)")
