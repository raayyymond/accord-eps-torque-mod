"""STREAM holdlevel, step 7: retract one of my own results, and finish the decomposition.

Q  RETRACTION CHECK.  Step 6 section N reported a flat outward intercept e = +0.0204 by adding sign(angle)
   to a design that already had sj and sj*toward.  But  sj = sgn*away - sgn*toward  and  sj*toward =
   -sgn*toward, so {sgn, sj, sj*toward} span only a 2-dimensional space -- the design is EXACTLY RANK
   DEFICIENT and lstsq returned an arbitrary minimum-norm split.  Proven numerically here.  The
   coefficient on hold (a) is unaffected because hold is outside that span; e is not a measurement.
R  the IDENTIFIED reparameterisation:  cmd = a*hold + A*(sgn*away) + B*(sgn*toward) + c
   half-width = (A-B)/2   flat outward offset = (A+B)/2   (= the study's -d/2, identified once hold is in)
S  the unsigned constant c: it is 0.007-0.015 on every route, the same size as the offset itself, and it
   is a LEFT/RIGHT asymmetry that the outward frame cannot represent.  How much of the binned centre is it?
T  THE SIGN FRAME IS DEGENERATE IN THE BOTTOM BIN.  Steering angle LSB is 0.1 deg and the bottom quintile
   runs 0.01-0.63 deg, so sign(angle) there is 0-6 LSB.  Redo the bottom bin with a sign guard.
U  the final decomposition of the CENTRE, and what each part would take to remove.
"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SS = HERE.parents[1] / 'lowspeed' / 'a_stickslip'
sys.path.insert(0, str(SS))
from ss_load import load_all, boot_ci, PRE
from sslib import hold_torque

LEVEL = {'0000006c--68c6e94b17': True, '0000006d--05e83bb04f': True, '0000006e--6ca3e014fd': False,
         '00000075--6c8687d5bd': False, '00000076--d0b7ea7e4d': False}
NO_DOB = '00000075--6c8687d5bd'
OBS = [r for r in LEVEL if r != NO_DOB]
K_FIT, C_FIT = 0.005560, -0.005620

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route = col('group'), col('v'), col('sjump'), col('route')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
aa_pre = W['aa'][:, PRE]; sgn = np.sign(aa_pre); aabs = np.abs(aa_pre)
toward = (sj == -np.sign(aa_pre)).astype(float); away = 1.0 - toward
LOW = TQ & (v >= 2) & (v < 8)
QS = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
hold_unlev = hold_torque(W['aa'], W['v'], False)
hold_flown = np.zeros_like(W['aa'])
for rk, L in LEVEL.items():
    m = route == rk
    if m.any():
        hold_flown[m] = hold_torque(W['aa'][m], W['v'][m], L)
O = []; P_ = O.append


def cci(fn, mask, nb=1200, seed=31):
    u = np.unique(route[mask]); rng = np.random.default_rng(seed)
    idxs = {c: np.where(route[mask] == c)[0] for c in u}
    bs = []
    for _ in range(nb):
        ii = np.concatenate([idxs[c] for c in rng.choice(u, len(u))])
        try:
            bs.append(fn(ii))
        except Exception:
            pass
    return fn(np.arange(int(mask.sum()))), tuple(np.percentile(bs, [2.5, 97.5]).tolist()), len(u)


P_("=" * 116)
P_("Q.  RETRACTION CHECK on my own step-6 section N")
X = np.vstack([hold_flown[ar, BK], sgn, sj, sj * toward, np.ones(N)]).T[LOW]
P_(f"    design [hold, sgn, sj, sj*toward, 1]  shape {X.shape}  matrix_rank {np.linalg.matrix_rank(X)}"
   f"   -> {'RANK DEFICIENT' if np.linalg.matrix_rank(X) < X.shape[1] else 'full rank'}")
P_(f"    max|sgn - (sj + 2*sj*toward)| over the set = {np.max(np.abs(sgn - (sj + 2*sj*toward))[LOW]):.2e}"
   f"   (an exact identity, so sgn adds no information)")
X2 = np.vstack([hold_flown[ar, BK], sj, sj * toward, np.ones(N)]).T[LOW]
P_(f"    design without sgn                     shape {X2.shape}  matrix_rank {np.linalg.matrix_rank(X2)}")
c1 = np.linalg.lstsq(X, W['cmd'][ar, BK][LOW], rcond=None)[0]
c2 = np.linalg.lstsq(X2, W['cmd'][ar, BK][LOW], rcond=None)[0]
P_(f"    a with sgn in the design {c1[0]:+.4f}   a without it {c2[0]:+.4f}   difference {c1[0]-c2[0]:+.2e}")
P_("    => a IS identified (hold lies outside the deficient span).  e IS NOT.  ** e = +0.0204 RETRACTED. **")

P_("")
P_("=" * 116)
P_("R.  THE IDENTIFIED REPARAMETERISATION   cmd[bk-3] = a*hold + A*(sgn*away) + B*(sgn*toward) + c")
P_("    A = outward-frame breakaway level breaking AWAY from centre; B = same breaking TOWARD centre")
P_("    half-width = (A-B)/2   (Coulomb, must be flat in angle)")
P_("    flat outward offset = (A+B)/2   (the part of the CENTRE that is NOT angle-proportional)")
P_("")
P_(f"  {'set':26s} {'n':>4s} {'cl':>3s} {'a':>7s} {'a 95% CI':>18s} {'half-width':>11s} {'CI':>18s}"
   f" {'flat offset':>12s} {'CI':>18s}")
DES = lambda: np.vstack([hold_flown[ar, BK], sgn * away, sgn * toward, np.ones(N)]).T


def fitset(mask, seed=37):
    X = DES()[mask]; yv = W['cmd'][ar, BK][mask]

    def mk(j):
        def f(ii):
            c = np.linalg.lstsq(X[ii], yv[ii], rcond=None)[0]
            return float(c[0]) if j == 0 else (float((c[1] - c[2]) / 2) if j == 1 else float((c[1] + c[2]) / 2))
        return f
    return [cci(mk(j), mask, seed=seed + j) for j in range(3)]


SETS = [('all five routes', LOW), ('observer routes (6c,6d,6e,76)', LOW & np.isin(route, OBS)),
        ('observer OFF (75 alone)', LOW & (route == NO_DOB)),
        ('level ON (6c+6d)', LOW & np.isin(route, ['0000006c--68c6e94b17', '0000006d--05e83bb04f'])),
        ('level OFF (6e+76+75)', LOW & np.isin(route, ['0000006e--6ca3e014fd', '00000076--d0b7ea7e4d', NO_DOB]))]
for lbl, mask in SETS:
    (ea, ca, nc), (eh, ch, _), (eo, co, _) = fitset(mask)
    P_(f"  {lbl:26s} {int(mask.sum()):4d} {nc:3d} {ea:+7.3f} [{ca[0]:+.3f},{ca[1]:+.3f}]"
       f" {eh:+11.4f} [{ch[0]:+.4f},{ch[1]:+.4f}] {eo:+12.4f} [{co[0]:+.4f},{co[1]:+.4f}]")
P_("  (a 1-cluster row's CI is degenerate by construction -- it is printed to show the absence of resolution)")

P_("")
P_("=" * 116)
P_("S.  THE UNSIGNED CONSTANT c -- a left/right asymmetry the outward frame cannot carry")
P_(f"  {'route':22s} {'n':>4s} {'c':>8s} {'n(aa>0)':>8s} {'n(aa<0)':>8s} {'sign balance':>13s}")
for rk in sorted(LEVEL):
    m = LOW & (route == rk)
    X = np.vstack([hold_flown[ar, BK], sj, sj * toward, np.ones(N)]).T[m]
    c_ = np.linalg.lstsq(X, W['cmd'][ar, BK][m], rcond=None)[0]
    npos, nneg = int((m & (aa_pre > 0)).sum()), int((m & (aa_pre < 0)).sum())
    P_(f"  {rk:22s} {int(m.sum()):4d} {c_[3]:+8.4f} {npos:8d} {nneg:8d} {npos/max(npos+nneg,1):13.2f}")
P_("  c is 0.004-0.015, the same size as the flat offset itself.  In the outward frame it contributes")
P_("  +c*sign(angle), whose per-bin median flips with that bin's left/right balance -- so a binned CENTRE")
P_("  carries a +-c wobble that has nothing to do with angle.  This is a property of the FIT, not the car.")

P_("")
P_("=" * 116)
P_("T.  THE SIGN FRAME IS DEGENERATE IN THE BOTTOM BIN (steering-angle LSB = 0.1 deg)")
mb0 = LOW & (aabs < QS[1])
P_(f"    bottom quintile |angle| < {QS[1]:.2f} deg: n = {int(mb0.sum())}")
for thr in (0.05, 0.1, 0.15, 0.2, 0.3):
    P_(f"      |angle| < {thr:.2f} deg ({thr/0.1:.0f} LSB): {int((LOW & (aabs < thr)).sum()):3d} episodes"
       f"  ({100*(LOW & (aabs<thr)).sum()/LOW.sum():.0f}% of the 2-8 m/s set)")
y_fit = (W['cmd'][ar, BK] - K_FIT * W['aa'][ar, BK] - C_FIT) * sgn
y_map = (W['cmd'][ar, BK] - hold_flown[ar, BK]) * sgn
P_("")
P_("    the orchestrator's bottom-bin CENTRE, with a sign guard applied:")
P_(f"    {'guard':22s} {'n_aw':>5s} {'n_tw':>5s} {'centre y_fit':>13s} {'centre y_map':>13s} {'hw y_fit':>10s}")
for lbl, gm in (('none (as measured)', mb0), ('|angle| >= 0.15 deg', mb0 & (aabs >= 0.15)),
                ('|angle| >= 0.30 deg', mb0 & (aabs >= 0.30)), ('|angle| >= 0.30, all bins', LOW & (aabs >= 0.30))):
    ma, mt = gm & (toward == 0), gm & (toward == 1)
    if ma.sum() < 2 or mt.sum() < 2:
        P_(f"    {lbl:22s} {int(ma.sum()):5d} {int(mt.sum()):5d}   (too few)")
        continue
    a1, t1 = np.median(y_fit[ma]), np.median(y_fit[mt])
    a2, t2 = np.median(y_map[ma]), np.median(y_map[mt])
    P_(f"    {lbl:22s} {int(ma.sum()):5d} {int(mt.sum()):5d} {(a1+t1)/2:+13.4f} {(a2+t2)/2:+13.4f} {(a1-t1)/2:+10.4f}")
P_("")
P_("    and the orchestrator's full five-bin CENTRE table with the >= 0.30 deg sign guard:")
ab2 = aabs[LOW & (aabs >= 0.30)]
Q2 = np.quantile(ab2, [0, .2, .4, .6, .8, 1.0])
P_(f"    {'|angle| bin':>20s} {'n_aw':>5s} {'n_tw':>5s} {'centre':>9s} {'half-width':>11s}")
cs = []
for i in range(5):
    lo, hi = Q2[i], Q2[i + 1]
    m = LOW & (aabs >= max(lo, 0.30)) & (aabs <= hi if i == 4 else aabs < hi)
    ma, mt = m & (toward == 0), m & (toward == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        continue
    a1, t1 = np.median(y_fit[ma]), np.median(y_fit[mt])
    cs.append((a1 + t1) / 2)
    P_(f"    {lo:8.2f}-{hi:8.2f} {int(ma.sum()):5d} {int(mt.sum()):5d} {(a1+t1)/2:+9.4f} {(a1-t1)/2:+11.4f}")
if len(cs) > 1:
    P_(f"    CENTRE spans {min(cs):+.4f} -> {max(cs):+.4f}   ratio {max(cs)/max(min(cs),1e-9):.1f}x"
       f"   (was 454x without the guard)")

P_("")
P_("=" * 116)
P_("U.  THE FINAL DECOMPOSITION of the breakaway band, all five routes, 5 route clusters")
(ea, ca, nc), (eh, ch, _), (eo, co, _) = fitset(LOW, seed=61)
P_(f"    cmd[bk-3] = a * hold_flown(aa, v)   +   offset * sign(angle)   +/-   half-width")
P_(f"      a            {ea:+.3f}  95% CI [{ca[0]:+.3f},{ca[1]:+.3f}]   (1.0 = the flown map is exactly right)")
P_(f"      offset       {eo:+.4f} 95% CI [{co[0]:+.4f},{co[1]:+.4f}]  torque, FLAT in angle")
P_(f"      half-width   {eh:+.4f} 95% CI [{ch[0]:+.4f},{ch[1]:+.4f}]  torque, FLAT in angle (Coulomb)")
P_("")
P_("    the two flat terms against the fork's own constants:")
P_("      HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020  (the intercept the map was fitted WITHOUT, :273)")
P_("      AccordFrictionHyst flew 0.015 on all five routes = 0.75 of it, and it is keyed to the direction")
P_("      of the last DESIRED motion (z follows d angle_des), not to the direction of the held angle.")
P_("")
P_("    how much of the CENTRE each part explains, at the bin median angles:")
P_(f"    {'|angle|':>9s} {'hold_flown':>11s} {'(a-1)*hold':>11s} {'flat offset':>12s} {'sum':>9s} {'measured ctr':>13s}")
for i in range(5):
    lo, hi = QS[i], QS[i + 1]
    m = LOW & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)
    ma, mt = m & (toward == 0), m & (toward == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        continue
    hm = float(np.median(hold_flown[ar, BK][m] * sgn[m]))
    meas = (np.median(y_map[ma]) + np.median(y_map[mt])) / 2
    P_(f"    {np.median(aabs[m]):9.2f} {hm:11.4f} {(ea-1)*hm:11.4f} {eo:12.4f} {(ea-1)*hm+eo:9.4f} {meas:+13.4f}")
P_("    (measured ctr is in the y_map frame = cmd - hold_flown, so it should equal (a-1)*hold + offset)")

txt = "\n".join(O)
(HERE / 'out' / 'hl_final.txt').write_text(txt, encoding='utf-8')
print(txt)
