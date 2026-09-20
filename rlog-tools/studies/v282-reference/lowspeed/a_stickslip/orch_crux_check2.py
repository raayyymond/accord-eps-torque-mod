"""ORCHESTRATOR HAND-CHECK #2 -- the three cruxes behind the spring-vs-friction verdict.

This also RE-CHECKS MY OWN earlier reading.  In orch_crux_check.py I called the band centre
"angle-proportional, 454x" and concluded the 0.020 constant does not exist.  The adjudication says
that was a parameterisation artefact of subtracting a linear k*|angle|, and that the decision-relevant
quantity is the shortfall against the FORK'S OWN NONLINEAR MAP.  Settle it here.

(a) REQUIRED MULTIPLIER vs angle.  S = (med u_away + med u_toward)/2 with u = cmd*sign(angle) needs no
    fit at all: outward breakaways sit on the band's upper edge S+F, inward on the lower S-F.  Compare S
    against the per-route levelled map.  If the required multiplier S/MAP varies strongly with angle, every
    MULTIPLICATIVE lever (AccordHoldLevel, HOLD_K_V, AccordEpsSpringScale) is dominated, whatever its dose.
(b) DOES ANYTHING WIND DURING THE STICK?  Per-bin median change in the dob and I channels from dwell start
    to breakaway, outward frame.  If they do not move, the deficit is a STANDING condition the stick does
    not create, and the "integrator winding" cause is dead.
(c) IS THE 0.033 HALF-WIDTH A COULOMB MAGNITUDE?  S and F at successive instants from dwell start to
    detection.  If F grows while S holds, F is an UPPER bound polluted by command overshoot and detector
    lag -- and F is the number any AccordFrictionHyst re-size would be sized against.

Run:  python orch_crux_check2.py
"""
import numpy as np
from ss_load import load_all, boot_ci, PRE
from sslib import hold_torque, params

EP, W, EX, VAL = load_all()
N = len(EP); ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g, v, sj, route = col('group'), col('v'), col('sjump'), col('route')
d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
BK = PRE - 3
LOW = TQ & (v >= 2) & (v < 8)
aa_bk = W['aa'][ar, BK]
sgn = np.sign(W['aa'][:, PRE])
toward = (sj == -sgn).astype(float)

# ---- per-route flown AccordHoldLevel, read from each route's own params ----
lev = {}
for rk in sorted(set(route[LOW])):
    try:
        p, _ = params(rk)
        lev[rk] = p.get('AccordHoldLevel', '0') == '1'
    except Exception as e:
        lev[rk] = False
        print(f"  !! params unreadable for {rk} ({e}); assuming level OFF")
print("flown AccordHoldLevel per route:", {k[:10]: ('ON' if b else 'off') for k, b in lev.items()})
MAP = np.array([hold_torque(aa_bk[i], v[i], lev.get(route[i], False)) for i in range(N)])

u = W['cmd'][ar, BK] * sgn            # outward-positive command at breakaway
BINS = [(0.0, 0.6), (0.6, 2.5), (2.5, 10.0), (10.0, 1e9)]
aabs = np.abs(aa_bk)

print()
print("=" * 96)
print("CRUX (a)  S = (med u_away + med u_toward)/2  -- NO FIT, no k, no c.  vs the per-route levelled map")
print(f"  {'|angle| (deg)':>14s} {'n_aw':>5s} {'n_tw':>5s} {'S':>9s} {'MAP':>9s} {'SHORTFALL':>10s}"
      f" {'MULT S/MAP':>11s} {'F=(aw-tw)/2':>12s}")
rows = []
for lo, hi in BINS:
    m = LOW & (aabs >= lo) & (aabs < hi)
    ma, mt = m & (toward == 0), m & (toward == 1)
    if ma.sum() < 3 or mt.sum() < 3:
        print(f"  {lo:6.2f}-{hi:7.2f} {int(ma.sum()):5d} {int(mt.sum()):5d}   (too few)")
        continue
    a_, t_ = np.median(u[ma]), np.median(u[mt])
    S, F = (a_ + t_) / 2, (a_ - t_) / 2
    mp = np.median(MAP[m])
    rows.append((np.median(aabs[m]), S, mp, S - mp, S / mp if mp else np.nan, F))
    print(f"  {lo:6.2f}-{hi:7.2f} {int(ma.sum()):5d} {int(mt.sum()):5d} {S:+9.4f} {mp:+9.4f}"
          f" {S-mp:+10.4f} {S/mp if mp else float('nan'):11.2f} {F:+12.4f}")
if len(rows) >= 2:
    ms = [r[4] for r in rows]
    print(f"\n  REQUIRED MULTIPLIER spans {min(ms):.2f}x -> {max(ms):.2f}x  ({max(ms)/min(ms):.1f}x spread)")
    print("  => a single multiplicative lever sized for one end is wrong at the other by that factor.")
    print("     SHORTFALL is the additive quantity; check whether IT is the stabler one:")
    sh = [r[3] for r in rows]
    print(f"     SHORTFALL spans {min(sh):+.4f} -> {max(sh):+.4f}  ({max(sh)/max(min(sh),1e-9):.1f}x spread)")
m = LOW & (aabs >= 0.6) & (aabs < 2.5)
ma, mt = m & (toward == 0), m & (toward == 1)
sf = (u[ma].mean() * 0 + 0)  # placeholder to keep flake quiet
est_a, ci_a = boot_ci(u[ma], route[ma]); est_t, ci_t = boot_ci(u[mt], route[mt])
print(f"\n  the well-determined cell, 0.6-2.5 deg:  S = {(est_a+est_t)/2:+.4f}"
      f"   MAP = {np.median(MAP[m]):+.4f}   SHORTFALL = {(est_a+est_t)/2 - np.median(MAP[m]):+.4f}")
print(f"    (away median {est_a:+.4f} CI [{ci_a[0]:+.4f},{ci_a[1]:+.4f}],"
      f" toward {est_t:+.4f} CI [{ci_t[0]:+.4f},{ci_t[1]:+.4f}])")

print()
print("=" * 96)
print("CRUX (b)  DOES ANYTHING WIND DURING THE STICK?  median change dwell_start -> breakaway, outward frame")
print(f"  {'|angle| (deg)':>14s} {'n':>4s} {'d_dob':>9s} {'d_I':>9s} {'d_cmd':>9s} {'cmd@start':>10s} {'S here':>8s}")
for lo, hi in BINS:
    m = LOW & (aabs >= lo) & (aabs < hi)
    if m.sum() < 5:
        continue
    dd = (W['dob'][ar, BK] - W['dob'][ar, d0]) * sgn
    di = (W['I'][ar, BK] - W['I'][ar, d0]) * sgn
    dc = (W['cmd'][ar, BK] - W['cmd'][ar, d0]) * sgn
    c0 = W['cmd'][ar, d0] * sgn
    print(f"  {lo:6.2f}-{hi:7.2f} {int(m.sum()):4d} {np.median(dd[m]):+9.4f} {np.median(di[m]):+9.4f}"
          f" {np.median(dc[m]):+9.4f} {np.median(c0[m]):+10.4f}"
          f" {np.median(u[m & (toward==0)]) if (m&(toward==0)).sum()>2 else float('nan'):+8.4f}")
print("  => if d_dob and d_I are ~0 against a centre of 0.02-0.09, nothing winds: the deficit is a")
print("     STANDING condition, and 'integrator winding during the stick' is dead as the CAUSE.")

print()
print("=" * 96)
print("CRUX (c)  IS F A COULOMB MAGNITUDE?  S and F at successive instants, matched angle 0.6-2.5 deg")
m = LOW & (aabs >= 0.6) & (aabs < 2.5)
ma, mt = m & (toward == 0), m & (toward == 1)
print(f"  {'instant':>22s} {'S':>9s} {'F':>9s}")
inst = [('dwell start', d0), ('start+25%', (d0 + (BK - d0) // 4)), ('start+50%', (d0 + (BK - d0) // 2)),
        ('breakaway-3 (bk-3)', np.full(N, BK)), ('breakaway (PRE)', np.full(N, PRE))]
for nm, idx in inst:
    uu = W['cmd'][ar, np.clip(idx, 0, W['cmd'].shape[1] - 1)] * sgn
    a_, t_ = np.median(uu[ma]), np.median(uu[mt])
    print(f"  {nm:>22s} {(a_+t_)/2:+9.4f} {(a_-t_)/2:+9.4f}")
print("  => if S holds while F grows from ~0 to ~0.03, then F at detection is an UPPER BOUND containing")
print("     the command's overshoot past the true edge plus the detector's lag -- NOT clean Coulomb.")
print("     Any AccordFrictionHyst re-size against 0.033 would then be oversized.")
