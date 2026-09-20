"""STEP 2  who carries the centre, and is the centre even angle-PROPORTIONAL?
 (a) the SHAPE of the centre: finer bins + a like-for-like test of 'proportional to |aa|' against
     'a saturating step'.  The 454x span quoted is min-driven (bin 1 sits at +0.0001).
 (b) COMPOSITION confounds: history class (kind), route, speed, dwell length vs |aa|.
 (c) the centre profile WITHIN each history class (the confound that would manufacture an
     angle-rising centre out of nothing).
 (d) the two natural experiments:
       AccordHoldLevel ON (6c,6d) vs OFF (6e)     -- cause (A) test
       observer ON (6c,6d,6e,76) vs OFF (75)      -- cause (B)-via-DOB test
 (e) route 75 alone: does it carry the offset with the observer off, and who carries it there?
"""
import numpy as np
from attr_lib import build, fit_lin, fit_hold, quintiles, bins, CHAN, BK, PRE, boot_ci, boot_ci_ev

D = build(); W, ar = D['W'], D['ar']
LOW = D['LOW']; sj = D['sjump']; tw = D['toward']; route = D['route']; kind = D['kind']
f0 = fit_lin(D, LOW, np.full(D['N'], BK)); K, C = f0['k'], f0['const']
S = np.sign(D['aa_pre']); aabs = np.abs(D['aa_pre'])
Y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * S
ych = {c: W[c][ar, BK] * S for c in CHAN}
ych['hold_ff_net'] = (W['hold_ff'][ar, BK] - K * W['aa'][ar, BK] - C) * S
ych['PI'] = (W['P'][ar, BK] + W['I'][ar, BK]) * S
ych['slow'] = (W['I'][ar, BK] + W['dob'][ar, BK]) * S
ych['TOTAL'] = Y


def ch(y, m):
    """(centre, halfwidth, n_aw, n_tw) by MEDIAN for mask m."""
    ma, mt = m & (tw == 0), m & (tw == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        return None
    a_, t_ = np.median(y[ma]), np.median(y[mt])
    return (a_ + t_) / 2, (a_ - t_) / 2, int(ma.sum()), int(mt.sum())


print("=" * 104)
print("(a) SHAPE OF THE CENTRE -- finer bins (deciles where n allows), TOTAL only")
print("    a Coulomb intercept is flat in angle; a STIFFNESS deficit is proportional to angle;")
print("    a saturating/step offset is neither.")
edges = np.quantile(aabs[LOW], np.linspace(0, 1, 9))
print(f"\n    {'|aa| bin':>18s} {'med|aa|':>8s} {'n_aw':>5s} {'n_tw':>5s} {'CENTRE':>9s} {'HALFWID':>9s}"
      f" {'ctr/|aa|':>9s}")
pts = []
for i in range(8):
    lo, hi = edges[i], edges[i + 1]
    m = LOW & (aabs >= lo) & ((aabs <= hi) if i == 7 else (aabs < hi))
    r = ch(Y, m)
    if r is None:
        print(f"    {lo:8.2f}-{hi:8.2f}  (n too small: {int((m&(tw==0)).sum())}/{int((m&(tw==1)).sum())})")
        continue
    a_ = np.median(aabs[m]); pts.append((a_, r[0], int(m.sum())))
    print(f"    {lo:8.2f}-{hi:8.2f} {a_:8.2f} {r[2]:5d} {r[3]:5d} {r[0]:+9.4f} {r[1]:+9.4f} {r[0]/a_:+9.4f}")
pa = np.array([p[0] for p in pts]); pc = np.array([p[1] for p in pts]); pw = np.array([p[2] for p in pts], float)
print("\n    like-for-like fits of the CENTRE profile (weighted by bin n):")
for nm, X in (("proportional  b*|aa|", np.vstack([pa]).T),
              ("linear        a+b*|aa|", np.vstack([np.ones_like(pa), pa]).T),
              ("flat          a", np.vstack([np.ones_like(pa)]).T),
              ("step          a*1(|aa|>0.6)", np.vstack([(pa > 0.6).astype(float)]).T),
              ("sat           a*tanh(|aa|/0.5)", np.vstack([np.tanh(pa / 0.5)]).T),
              ("sat+prop      a*tanh(|aa|/0.5)+b*|aa|", np.vstack([np.tanh(pa / 0.5), pa]).T)):
    Wt = np.sqrt(pw)[:, None]
    c, *_ = np.linalg.lstsq(X * Wt, pc * Wt[:, 0], rcond=None)
    res = pc - X @ c
    print(f"      {nm:38s} coef {np.round(c,5)}  wrms {np.sqrt(np.average(res**2, weights=pw)):.5f}")
print("      (a 'proportional' law must pass through the origin; a step/sat cannot be a stiffness error)")

print()
print("=" * 104)
print("(b) COMPOSITION vs |angle|  -- what else changes across the bins?")
qs, _ = quintiles(D)
print(f"\n    {'med|aa|':>8s} {'n':>4s} {'med_v':>6s} {'dwell_s':>8s} {'cont':>6s} {'rest':>6s} {'rev':>6s}"
      f" {'gap_bk':>8s} {'6c':>5s} {'6d':>5s} {'6e':>5s} {'75':>5s} {'76':>5s} {'lev%':>6s} {'dob%':>6s}")
BROWS = []
for lo, hi, m in bins(D, LOW, qs, aabs):
    BROWS.append(m)
    rr = [np.mean(route[m] == r) for r in sorted(set(route[LOW]))]
    print(f"    {np.median(aabs[m]):8.2f} {int(m.sum()):4d} {np.median(D['v'][m]):6.2f} {np.median(D['dwell_s'][m]):8.2f}"
          f" {np.mean(kind[m]=='cont'):6.2f} {np.mean(kind[m]=='rest'):6.2f} {np.mean(kind[m]=='rev'):6.2f}"
          f" {np.median(D['gap_bk'][m]):8.3f}" + "".join(f" {x:5.2f}" for x in rr)
          + f" {np.mean(D['is_lev'][m]):6.2f} {np.mean(D['is_dob'][m]):6.2f}")

print()
print("=" * 104)
print("(c) CENTRE PROFILE WITHIN EACH HISTORY CLASS (tertiles of |aa| inside the class)")
for kd in ('cont', 'rest', 'rev'):
    mk = LOW & (kind == kd)
    e = np.quantile(aabs[mk], [0, 1 / 3, 2 / 3, 1.0])
    print(f"\n    kind={kd}  n={int(mk.sum())}")
    for i in range(3):
        m = mk & (aabs >= e[i]) & ((aabs <= e[i + 1]) if i == 2 else (aabs < e[i + 1]))
        r = ch(Y, m)
        if r is None:
            print(f"      {e[i]:7.2f}-{e[i+1]:7.2f}  n {int((m&(tw==0)).sum())}/{int((m&(tw==1)).sum())}  (too small)")
            continue
        print(f"      {e[i]:7.2f}-{e[i+1]:7.2f}  med|aa| {np.median(aabs[m]):6.2f}  n {r[2]}/{r[3]}"
              f"  CENTRE {r[0]:+.4f}  HW {r[1]:+.4f}")

print()
print("=" * 104)
print("(d1) NATURAL EXPERIMENT 1 -- AccordHoldLevel ON (6c,6d: x1.15 below 12.5 m/s) vs OFF (6e)")
print("     Prediction if cause (A) (a hold-map LEVEL/stiffness deficit the FF must cover):")
print("       level OFF removes 0.15*hold_unlev(aa) of FF authority, so the SLOW channels (I+dob)")
print("       must carry MORE on 6e by that amount, while the TOTAL centre -- a PLANT property -- stays.")
print("     Prediction if the deficit is NOT a level error: hold_ff moves by the map arithmetic and")
print("       nothing else has to move.")
ON = LOW & D['is_lev']; OFF = LOW & (~D['is_lev']) & np.isin(route, ['0000006e--6ca3e014fd'])
print(f"\n     n ON {int(ON.sum())} (6c+6d)   n OFF {int(OFF.sum())} (6e only, same fork otherwise)")
print(f"     med v  ON {np.median(D['v'][ON]):.2f}  OFF {np.median(D['v'][OFF]):.2f}"
      f"   med|aa| ON {np.median(aabs[ON]):.2f}  OFF {np.median(aabs[OFF]):.2f}")
print(f"     kind mix ON cont/rest/rev {np.mean(kind[ON]=='cont'):.2f}/{np.mean(kind[ON]=='rest'):.2f}/{np.mean(kind[ON]=='rev'):.2f}"
      f"   OFF {np.mean(kind[OFF]=='cont'):.2f}/{np.mean(kind[OFF]=='rest'):.2f}/{np.mean(kind[OFF]=='rev'):.2f}")
# matched |aa| cells so the comparison is like-for-like
cells = [(0.0, 1.0), (1.0, 3.0), (3.0, 1e9)]
print(f"\n     {'|aa| cell':>12s} {'chan':>12s} {'ON ctr':>9s} {'OFF ctr':>9s} {'OFF-ON':>9s}"
      f" {'pred 0.15*hold':>15s}  n_on  n_off")
for lo, hi in cells:
    mo = ON & (aabs >= lo) & (aabs < hi); mf = OFF & (aabs >= lo) & (aabs < hi)
    pred = np.median(np.abs(D['hold_aa_unlev'][ar, BK])[mf]) * 0.15
    for c in ('TOTAL', 'hold_ff', 'hold_ff_net', 'I', 'dob', 'slow', 'P', 'z'):
        r1, r2 = ch(ych[c], mo), ch(ych[c], mf)
        if r1 is None or r2 is None:
            print(f"     {lo:5.1f}-{hi:5.1f} {c:>12s}   n too small ({0 if r1 is None else 1}/{0 if r2 is None else 1})"
                  f"  n_on {int(mo.sum())} n_off {int(mf.sum())}")
            continue
        print(f"     {lo:5.1f}-{hi:5.1f} {c:>12s} {r1[0]:+9.4f} {r2[0]:+9.4f} {r2[0]-r1[0]:+9.4f}"
              f" {pred:+15.4f}  {r1[2]}/{r1[3]}  {r2[2]}/{r2[3]}")
    print()

print("=" * 104)
print("(d2) NATURAL EXPERIMENT 2 -- observer ON vs OFF, and route 75 alone")
DON = LOW & D['is_dob']; DOFF = LOW & (~D['is_dob'])
print(f"     n dob-ON {int(DON.sum())} (6c,6d,6e,76)   n dob-OFF {int(DOFF.sum())} (75 only)")
print(f"     75 also ran Ki 0.6 (vs 0.3), SteerKP 0.85 (vs 1.00), RefFilter 0.12, RateLoopGain 0.0006")
print(f"\n     {'|aa| cell':>12s} {'chan':>12s} {'dobON':>9s} {'dobOFF(75)':>11s} {'diff':>9s}  n_on  n_off")
for lo, hi in cells:
    mo = DON & (aabs >= lo) & (aabs < hi); mf = DOFF & (aabs >= lo) & (aabs < hi)
    for c in ('TOTAL', 'hold_ff_net', 'I', 'dob', 'slow', 'P', 'z'):
        r1, r2 = ch(ych[c], mo), ch(ych[c], mf)
        if r1 is None or r2 is None:
            continue
        print(f"     {lo:5.1f}-{hi:5.1f} {c:>12s} {r1[0]:+9.4f} {r2[0]:+11.4f} {r2[0]-r1[0]:+9.4f}"
              f"  {r1[2]}/{r1[3]}  {r2[2]}/{r2[3]}")
    print()

print("=" * 104)
print("(e) PER-ROUTE band fit at breakaway (linear spring), episode bootstrap CI on centre")
print(f"     {'route':>22s} {'lev':>4s} {'dob':>4s} {'n':>4s} {'k':>8s} {'away':>8s} {'toward':>8s}"
      f" {'HALFWID':>9s} {'CENTRE':>9s} {'CI':>22s}")
for rk in sorted(set(route[LOW])):
    m = LOW & (route == rk)
    f = fit_lin(D, m, np.full(D['N'], BK))
    # centre via the pooled-K residual, for a like-for-like number with the table above
    r = ch(Y, m)
    est, ci = boot_ci_ev(Y[m & (tw == 0)]) if (m & (tw == 0)).sum() >= 4 else (np.nan, (np.nan, np.nan))
    ea, ca = boot_ci_ev(Y[m & (tw == 0)]); et, ct = boot_ci_ev(Y[m & (tw == 1)])
    lo_, hi_ = (ca[0] + ct[0]) / 2, (ca[1] + ct[1]) / 2
    print(f"     {rk:>22s} {int(D['lev'][rk]):4d} {int(D['dob_on'][rk]):4d} {int(m.sum()):4d}"
          f" {f['k']:8.5f} {f['away']:+8.4f} {f['toward']:+8.4f} {f['halfwidth']:+9.4f}"
          f" {f['centring_offset']:+9.4f}  resid-ctr {r[0]:+.4f} [{lo_:+.4f},{hi_:+.4f}]")
print("     (the 'CENTRE' column is the FIT's centring_offset = -d/2; 'resid-ctr' is the median-based")
print("      centre of the pooled-K residual, i.e. the quantity binned above)")
