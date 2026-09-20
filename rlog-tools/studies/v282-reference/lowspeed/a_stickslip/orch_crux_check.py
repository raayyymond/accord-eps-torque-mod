"""ORCHESTRATOR HAND-CHECK of the three cruxes behind the 'no-reopen-design' verdict on the
one-sided static-friction candidate.  Independent of the adjudicating agent's code.

Gate 0  reproduce ss_centring_fit exactly (validates the loader before anything else is trusted).
Crux a  is the '+0.020 outward intercept' an INTERCEPT?  Bin the band by |angle| under the fit's own
        spring: a Coulomb intercept must be FLAT in angle, a spring/integrator deficit rises with it.
Crux b  the design's load-bearing premise: does the OUTWARD direction need more command travel than
        the inward one?  (The design says yes: 0.053 vs 0.014.)
Crux c  is 'the command starts at the band centre' (fitted half-width 0.0004) a finding or a mix
        artefact of cancelling history classes?

Run:  python orch_crux_check.py
"""
import numpy as np
from ss_load import load_all, boot_ci, PRE

EP, W, EX, VAL = load_all()
N = len(EP)
ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route = col('group'), col('v'), col('sjump'), col('route')
d0 = np.maximum(col('w_d0'), 0)
kind = col('kind') if 'kind' in EP[0] else np.array(['?'] * N)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3                                     # the fit's breakaway sample
aa_pre = W['aa'][:, PRE]
toward = (sj == -np.sign(aa_pre)).astype(float)
LOW = TQ & (v >= 2) & (v < 8)


def fit(m, idx):
    X = np.vstack([W['aa'][ar, idx], sj, sj * toward, np.ones(N)]).T[m]
    c = np.linalg.lstsq(X, W['cmd'][ar, idx][m], rcond=None)[0]
    return dict(away=c[1], toward=c[1] + c[2], halfwidth=c[1] + c[2] / 2,
                centring_offset=-c[2] / 2, k=c[0], const=c[3])


print("=" * 78)
print("GATE 0 -- reproduce ss_centring_fit, torque|2-8|breakaway")
f0 = fit(LOW, np.full(N, BK))
exp = dict(away=0.052564, toward=0.014006, halfwidth=0.033285, centring_offset=0.019279, k=0.005560)
for kk, want in exp.items():
    got = f0[kk]
    print(f"  {kk:16s} got {got:+.6f}   expected {want:+.6f}   d {got-want:+.2e}"
          f"   {'OK' if abs(got-want) < 5e-5 else '** MISMATCH **'}")
print(f"  n {int(LOW.sum())} (expect 145)   n_toward {int(toward[LOW].sum())} (expect 93)")
K, C = f0['k'], f0['const']

print()
print("=" * 78)
print("CRUX (a)  BAND BY ANGLE, under the fit's OWN spring  k=%.5f  c=%+.5f" % (K, C))
print("  y = (cmd[bk-3] - k*aa[bk-3] - c) * sign(aa[PRE])")
print("  centre = (med_away + med_toward)/2      half-width = (med_away - med_toward)/2")
y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - C) * np.sign(aa_pre)
aabs = np.abs(aa_pre)
qs = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
print(f"\n  {'|angle| bin (deg)':>22s} {'n_aw':>5s} {'n_tw':>5s} {'med_away':>10s} {'med_toward':>11s}"
      f" {'CENTRE':>9s} {'HALF-WIDTH':>11s}")
rows = []
for i in range(5):
    lo, hi = qs[i], qs[i + 1]
    m = LOW & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)
    ma, mt = m & (toward == 0), m & (toward == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        continue
    a_, t_ = np.median(y[ma]), np.median(y[mt])
    ctr, hw = (a_ + t_) / 2, (a_ - t_) / 2
    rows.append((np.median(aabs[m]), ctr, hw))
    print(f"  {lo:8.2f} - {hi:8.2f} {int(ma.sum()):5d} {int(mt.sum()):5d}"
          f" {a_:+10.4f} {t_:+11.4f} {ctr:+9.4f} {hw:+11.4f}")
ctrs = np.array([r[1] for r in rows]); hws = np.array([r[2] for r in rows])
print(f"\n  CENTRE     spans {ctrs.min():+.4f} -> {ctrs.max():+.4f}"
      f"   ratio {ctrs.max()/max(ctrs.min(),1e-9):6.1f}x")
print(f"  HALF-WIDTH spans {hws.min():+.4f} -> {hws.max():+.4f}"
      f"   ratio {hws.max()/max(hws.min(),1e-9):6.1f}x")
print("  => a Coulomb intercept must be FLAT in angle.  Whichever of the two is flat is the")
print("     friction-shaped quantity; the one that rises with angle is a spring/integrator deficit.")
sm = LOW & (aabs < 1.0)
print(f"\n  busiest cell |angle| < 1 deg: n={int(sm.sum())} of {int(LOW.sum())}"
      f"  ({100*sm.sum()/LOW.sum():.0f}% of episodes)")
if (sm & (toward == 0)).sum() >= 3 and (sm & (toward == 1)).sum() >= 3:
    a_, t_ = np.median(y[sm & (toward == 0)]), np.median(y[sm & (toward == 1)])
    print(f"    centre here {(a_+t_)/2:+.4f}  vs the proposed dose 0.0200"
          f"  ({0.0200/max((a_+t_)/2,1e-9):.1f}x too large)")

print()
print("=" * 78)
print("CRUX (b)  PER-EPISODE COMMAND TRAVEL through the dwell, by direction")
print("  travel = (cmd[bk-3] - cmd[dwell_start]) * sign(jump)   [route-cluster bootstrap]")
trav = (W['cmd'][ar, BK] - W['cmd'][ar, d0]) * sj
for lbl, m in (("OUTWARD (away)", LOW & (toward == 0)), ("INWARD  (toward)", LOW & (toward == 1))):
    est, ci = boot_ci(trav[m], route[m])
    print(f"  {lbl:17s} n={int(m.sum()):3d}   median {est:+.5f}  CI [{ci[0]:+.5f}, {ci[1]:+.5f}]")
print("\n  per route (outward / inward):")
flip = 0
for r in np.unique(route[LOW]):
    ma, mt = LOW & (route == r) & (toward == 0), LOW & (route == r) & (toward == 1)
    if ma.sum() < 2 or mt.sum() < 2:
        continue
    a_, t_ = np.median(trav[ma]), np.median(trav[mt])
    flip += t_ > a_
    print(f"    route {r:>3}  {a_:+.4f} / {t_:+.4f}   n {int(ma.sum()):3d}/{int(mt.sum()):3d}"
          f"   {'inward needs MORE' if t_ > a_ else 'outward needs more'}")
print(f"\n  inward > outward on {flip} routes  -> the design's premise (outward is the")
print("  under-served direction) is INVERTED if this is most of them.")

print()
print("=" * 78)
print("CRUX (c)  DWELL-START LEVEL BY HISTORY CLASS  (is the ~0 pooled value a cancellation?)")
print("  y0 = (cmd[d0] - k*aa[d0] - c) * sign(jump)")
y0 = (W['cmd'][ar, d0] - K * W['aa'][ar, d0] - C) * sj
pooled, pci = boot_ci(y0[LOW], route[LOW])
print(f"  POOLED            n={int(LOW.sum()):3d}   median {pooled:+.5f}  CI [{pci[0]:+.5f}, {pci[1]:+.5f}]")
seen = []
for kd in np.unique(kind[LOW]):
    m = LOW & (kind == kd)
    if m.sum() < 5:
        continue
    est, ci = boot_ci(y0[m], route[m])
    seen.append(est)
    print(f"  {str(kd):16s}  n={int(m.sum()):3d}   median {est:+.5f}  CI [{ci[0]:+.5f}, {ci[1]:+.5f}]")
if len(seen) > 1:
    spread = max(seen) - min(seen)
    print(f"\n  spread across history classes {spread:.4f} = {spread/f0['halfwidth']:.2f}x the fitted"
          f" half-width {f0['halfwidth']:.4f}")
    print("  => if the classes straddle zero with a spread this large, the pooled ~0 is CANCELLATION,")
    print("     and 'both directions need the same travel from where the command sits' does not follow.")

print()
print("=" * 78)
print("BOOTSTRAP METHOD NOTE (read from ss_centring_fit.py:24-26)")
print("  it builds clusters with  mm |= m & (route == c)  -- an OR of masks, so a route drawn twice")
print("  collapses to one copy.  That is a random-subset jackknife, not a route-cluster bootstrap;")
print("  ss_load.boot_ci (used above) concatenates indices and is correct.")
