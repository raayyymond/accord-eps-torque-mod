"""STREAM holdlevel, step 6: verify the cruxes of my own decision-bearing claims before reporting them.

L  de-tautologise the observer correlation.  In step 5 I regressed dob@bk on mis@d0 where
   mis = (cmd - hold_flown - b*rate)*sgn and cmd ITSELF CONTAINS dob, so corr 0.945 was partly an
   identity.  Redo against the EXOGENOUS mismatch (cmd - dob - hold_flown - b*rate)*sgn.
M  the spring excess with a route-cluster CI, and with the LEVELLED map as the regressor, so the
   question "does the flown feedforward under-hold?" is asked directly.
N  is the excess angle-PROPORTIONAL or an intercept?  fit  cmd = a*hold + e*sign(angle) + Fa*sj + d*sj*toward + c
   -- a Coulomb/static intercept loads e, an angle-proportional stiffness deficit loads a.
O  the power statement: route-to-route scatter of a, against the 0.15 the toggle moves.
P  half-width per route (must be flat if it is Coulomb friction) and the toggle's effect on it.
"""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
SS = HERE.parents[1] / 'lowspeed' / 'a_stickslip'
sys.path.insert(0, str(SS))
from ss_load import load_all, boot_ci, PRE
from sslib import hold_torque, G_BP, G_V

LEVEL = {'0000006c--68c6e94b17': True, '0000006d--05e83bb04f': True, '0000006e--6ca3e014fd': False,
         '00000075--6c8687d5bd': False, '00000076--d0b7ea7e4d': False}
NO_DOB = '00000075--6c8687d5bd'
OBS = [r for r in LEVEL if r != NO_DOB]

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route, dwell = col('group'), col('v'), col('sjump'), col('route'), col('dwell_s')
d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
aa_pre = W['aa'][:, PRE]; sgn = np.sign(aa_pre); aabs = np.abs(aa_pre)
toward = (sj == -np.sign(aa_pre)).astype(float)
LOW = TQ & (v >= 2) & (v < 8)
fade = np.interp(v, [3.0, 6.0], [0.0, 1.0])
hold_unlev = hold_torque(W['aa'], W['v'], False)
hold_flown = np.zeros_like(W['aa'])
for rk, L in LEVEL.items():
    m = route == rk
    if m.any():
        hold_flown[m] = hold_torque(W['aa'][m], W['v'][m], L)
b_mod = 1.0 / np.interp(W['v'], G_BP, G_V)
O = []; P_ = O.append


def cluster_ci(fn, mask, nb=1000, seed=13):
    u = np.unique(route[mask]); rng = np.random.default_rng(seed)
    idxs = {c: np.where(route[mask] == c)[0] for c in u}
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idxs[c] for c in pick])
        try:
            bs.append(fn(ii))
        except Exception:
            pass
    return fn(np.arange(int(mask.sum()))), tuple(np.percentile(bs, [2.5, 97.5]).tolist()), len(u)


P_("=" * 116)
P_("L.  DE-TAUTOLOGISED: the observer vs the mismatch it does NOT itself contain")
P_("    mis_all = (cmd          - hold_flown - b*rate) . sgn   <- contains dob (step 5 used this: corr 0.945)")
P_("    mis_ex  = (cmd - dob    - hold_flown - b*rate) . sgn   <- exogenous, the observer's actual input driver")
MO = LOW & np.isin(route, OBS) & (fade >= 0.9)
dob_bk = W['dob'][ar, BK] * sgn
mis_all = (W['cmd'][ar, d0] - hold_flown[ar, d0] - b_mod[ar, d0] * W['sr'][ar, d0]) * sgn
mis_ex = (W['cmd'][ar, d0] - W['dob'][ar, d0] - hold_flown[ar, d0] - b_mod[ar, d0] * W['sr'][ar, d0]) * sgn
for nm, x in (('mis_all (tautological)', mis_all), ('mis_ex  (exogenous)', mis_ex)):
    sl = np.polyfit(x[MO], dob_bk[MO], 1)
    P_(f"    dob@bk vs {nm:24s} n {int(MO.sum()):3d}  slope {sl[0]:+.3f}  intercept {sl[1]:+.4f}"
       f"  corr {np.corrcoef(x[MO], dob_bk[MO])[0,1]:+.3f}   median {np.median(x[MO]):+.4f}")
P_("    -> the exogenous figure is the honest one; the 0.945 in step 5 is retracted as partly an identity.")
P_("")
P_("    and the observer against |angle| alone (the quantity the centre is proportional to):")
f = lambda ii: float(np.polyfit(aabs[MO][ii], dob_bk[MO][ii], 1)[0])
e, ci, nc = cluster_ci(f, MO)
P_(f"    d(dob@bk)/d|angle| = {e:+.5f} per deg, {nc}-route-cluster 95% CI [{ci[0]:+.5f},{ci[1]:+.5f}]"
   f"   corr {np.corrcoef(aabs[MO], dob_bk[MO])[0,1]:+.3f}")

P_("")
P_("=" * 116)
P_("M.  THE SPRING EXCESS, with route-cluster CIs.  cmd[bk-3] = a*HOLD + Fa*sj + d*sj*toward + c")
P_("    HOLD = hold(aa, v, .) is the fork's own saturating, speed-scheduled map -- so a mis-specified")
P_("    single linear k CANNOT be what produces a != 1 here (that is the third hypothesis, tested).")
P_("    a is dimensionless: the multiple of that map the breakaway command actually sits at.")


def afit(HOLD, mask, seed=17):
    X = np.vstack([HOLD[ar, BK], sj, sj * toward, np.ones(N)]).T[mask]
    yv = W['cmd'][ar, BK][mask]

    def f(ii):
        return float(np.linalg.lstsq(X[ii], yv[ii], rcond=None)[0][0])
    return cluster_ci(f, mask, seed=seed)


for nm, HOLD in (('UNLEVELLED map (rev 3-5)  ', hold_unlev), ("each route's FLOWN map    ", hold_flown)):
    for lbl, mask in (('all five routes      ', LOW), ('observer routes only ', LOW & np.isin(route, OBS)),
                      ('level ON  (6c+6d)    ', LOW & np.isin(route, ['0000006c--68c6e94b17', '0000006d--05e83bb04f'])),
                      ('level OFF (6e+76+75) ', LOW & np.isin(route, ['0000006e--6ca3e014fd', '00000076--d0b7ea7e4d', NO_DOB]))):
        e, ci, nc = afit(HOLD, mask)
        flag = '' if ci[0] > 1.0 else '   <- CI includes 1.0'
        P_(f"    {nm} {lbl} n {int(mask.sum()):3d} clusters {nc}  a {e:+.3f}  95% CI [{ci[0]:+.3f},{ci[1]:+.3f}]{flag}")
P_("    a > 1 against the FLOWN map = the flown feedforward under-holds at breakaway, in proportion to")
P_("    the map's own shape.  That is hypothesis (A).  a = 1 would mean the map is right and the centre")
P_("    is something else.")

P_("")
P_("=" * 116)
P_("N.  IS THE EXCESS ANGLE-PROPORTIONAL, OR A CONSTANT?  add a sign(angle) intercept to the same fit:")
P_("    cmd = a*HOLD + e*sign(angle) + Fa*sj + d*sj*toward + c")
P_("    e loads a Coulomb / static-friction intercept (flat in angle); a loads a stiffness deficit.")
for nm, HOLD in (('UNLEVELLED', hold_unlev), ('FLOWN     ', hold_flown)):
    for lbl, mask in (('all five ', LOW), ('observer ', LOW & np.isin(route, OBS))):
        X = np.vstack([HOLD[ar, BK], sgn, sj, sj * toward, np.ones(N)]).T[mask]
        yv = W['cmd'][ar, BK][mask]

        def fa(ii):
            return float(np.linalg.lstsq(X[ii], yv[ii], rcond=None)[0][0])

        def fe(ii):
            return float(np.linalg.lstsq(X[ii], yv[ii], rcond=None)[0][1])
        ea, cia, nc = cluster_ci(fa, mask, seed=23)
        ee, cie, _ = cluster_ci(fe, mask, seed=23)
        P_(f"    {nm} {lbl} n {int(mask.sum()):3d}  a {ea:+.3f} [{cia[0]:+.3f},{cia[1]:+.3f}]"
           f"   e {ee:+.4f} [{cie[0]:+.4f},{cie[1]:+.4f}]")
P_("    (HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020 is the intercept the map was fitted WITHOUT, and the")
P_("     fork's comment at :227 says AccordFrictionHyst supplies it -- it flew at 0.015.  e is the")
P_("     measurement of what is still missing after that.)")

P_("")
P_("=" * 116)
P_("O.  POWER, RESTATED AS A NUISANCE-TO-SIGNAL RATIO -- why one route per arm cannot settle this")
P_("    the toggle moves the feedforward's supplied fraction of the map by exactly 0.15 (x1.15 -> x1.00,")
P_("    flat for all v <= 12.5).  The route-to-route scatter of a, measured, is:")
for rk in sorted(LEVEL):
    m = LOW & (route == rk)
    X = np.vstack([hold_unlev[ar, BK], sj, sj * toward, np.ones(N)]).T[m]
    yv = W['cmd'][ar, BK][m]
    c_ = np.linalg.lstsq(X, yv, rcond=None)[0]
    P_(f"      {rk}  lvl {str(LEVEL[rk]):5s}  n {int(m.sum()):3d}  a {c_[0]:+.3f}")
av = []
for rk in sorted(LEVEL):
    m = LOW & (route == rk)
    X = np.vstack([hold_unlev[ar, BK], sj, sj * toward, np.ones(N)]).T[m]
    av.append(float(np.linalg.lstsq(X, W['cmd'][ar, BK][m], rcond=None)[0][0]))
av = np.array(av)
P_(f"    spread {av.min():.3f} .. {av.max():.3f}, sd {av.std(ddof=1):.3f}, range/0.15 = {(av.max()-av.min())/0.15:.1f}x")
P_("    With ONE route in each arm the toggle is perfectly collinear with every route-level nuisance")
P_("    (road crown, tyre/temperature, the learned LiveParametersV2 and LiveDelay, which do differ between")
P_("    6c and 6e).  A %.0fx nuisance-to-signal ratio at 1 cluster per arm is not a resolvable experiment."
   % ((av.max() - av.min()) / 0.15))

P_("")
P_("=" * 116)
P_("P.  HALF-WIDTH per route (Fa + d/2 from the same fit) -- Coulomb friction must be route-flat")
for rk in sorted(LEVEL):
    m = LOW & (route == rk)
    X = np.vstack([hold_unlev[ar, BK], sj, sj * toward, np.ones(N)]).T[m]
    c_ = np.linalg.lstsq(X, W['cmd'][ar, BK][m], rcond=None)[0]
    P_(f"    {rk}  lvl {str(LEVEL[rk]):5s} obs {'no ' if rk == NO_DOB else 'yes':3s} n {int(m.sum()):3d}"
       f"  half-width {c_[1]+c_[2]/2:+.4f}   centring offset {-c_[2]/2:+.4f}")
P_("    AccordFrictionHyst flew 0.015 on all five; the fork's own static-friction constant is 0.020.")
P_("")
P_("  AccordFrictionHystBand is INERT in this whole band: HONDA_ACCORD_FRICTION_HYST_BAND_BP starts at")
P_("  8.0 m/s with value 3.0, and the flat fallback HONDA_ACCORD_FRICTION_HYST_BAND_DEG is also 3.0, so")
P_("  np.interp clamps to 3.0 for every v <= 8.  6c/6d/6e had the toggle on and 75/76 did not; below")
P_("  8 m/s that difference cannot act.  (EVIDENCE: source read, latcontrol_vehicle_tunes.py:319-321.)")

txt = "\n".join(O)
(HERE / 'out' / 'hl_verify.txt').write_text(txt, encoding='utf-8')
print(txt)
