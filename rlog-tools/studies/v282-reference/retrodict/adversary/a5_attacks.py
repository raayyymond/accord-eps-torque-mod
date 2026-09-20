"""A5 - the four attacks on the repaired statistic.

  (i)   does it order its own anchors?  (clause a / c)      -- with and without the notch term
  (ii)  amplitude:  at what A does the r71 verdict flip?
  (iii) plant:      what does the 0.20 Hz -> 2.4 Hz extrapolation cost, measured?
  (iv)  sample size: how often does a useless statistic pass clause (a)?
"""
import json
import math
import os
import numpy as np
import a4_repaired_statistic as R

OUT = os.path.dirname(__file__)
A3 = json.load(open(os.path.join(OUT, "a3_plant_transfer.json")))

print("=" * 100)
print("(i)  RANKING.  Clause (a): r71's controller must be RISKIEST on >=2 of 3 non-r71 plants.")
print("=" * 100)
for use_notch in (False, True):
    saved = {c: R.CTRL[c]["notchQ"] for c in R.CTRL}
    if not use_notch:
        for c in R.CTRL:
            R.CTRL[c]["notchQ"] = 0.0
    print(f"\n--- notch term {'INCLUDED (a THIRD repair term)' if use_notch else 'OMITTED (the two pre-registered terms only)'} ---")
    for D in (0.055, 0.065, 0.075):
        tab = R.run(v=25.0, D=D, A=0.20, verbose=False)
        rank = {}
        for pn in R.PLANTS:
            order = sorted(R.CTRL, key=lambda c: -(tab[pn][c][1] if np.isfinite(tab[pn][c][1]) else -1))
            rank[pn] = order
        n_r71_top = sum(1 for pn in R.PLANTS if pn != "r71" and rank[pn][0].startswith("r71"))
        print(f"  D={D*1000:.0f} ms  r71 ratio to r72 = "
              f"{tab['r72']['r71   (LIMIT CYCLE)'][1]/tab['r72']['r72   (clean)'][1]:.3f}   "
              f"r71 riskiest on {n_r71_top}/4 non-r71 plants  -> clause (a) "
              f"{'PASS' if n_r71_top >= 2 else 'FAIL'}")
        for pn in R.PLANTS:
            if pn == "r71":
                continue
            print(f"      plant {pn:5}: " + " > ".join(f"{c.split()[0]}({tab[pn][c][1]:.2f})" for c in rank[pn]))
    for c in R.CTRL:
        R.CTRL[c]["notchQ"] = saved[c]

print()
print("=" * 100)
print("(ii) AMPLITUDE.  The describing function is 4F/(pi*A) above the 0.30 threshold.")
print("=" * 100)
# calibrate my absolute scale to the brief's own quoted r71 number so the flip point is
# expressed in the brief's units, not mine
for c in R.CTRL:
    R.CTRL[c]["notchQ"] = 0.0
w, L = R.loop(R.CTRL["r71   (LIMIT CYCLE)"], A3["00000071--f2c9d073a3"]["T02"], 25.0, 0.065, 0.20)
f0, m0 = R.crossing(w, L)
SCALE = 1.43 / m0
print(f"  my |L|(r71, A<=0.30, D=65 ms) = {m0:.3f} at {f0:.2f} Hz; the brief quotes 1.43 at 2.53 Hz")
print(f"  -> scale factor {SCALE:.3f} applied below so the flip point is read in the BRIEF's calibration\n")
print(f"  {'A (m/s^2)':>11} {'A as wheel deg':>15} {'N_df':>9} {'|L| r71':>9} {'|L| r72':>9} {'|L| V282':>9} {'|L| r73':>9}")
Mdeg = R.M_lat_per_deg(25.0, 16.88)
rows = []
for A in (0.05, 0.10, 0.20, 0.30, 0.40, 0.60, 0.80, 1.00, 1.37, 2.0, 3.0):
    vals = {}
    for cn in R.CTRL:
        w, L = R.loop(R.CTRL[cn], A3["00000071--f2c9d073a3"]["T02"], 25.0, 0.065, A)
        _, m = R.crossing(w, L)
        vals[cn] = m * SCALE
    rows.append((A, vals))
    print(f"  {A:11.2f} {A/Mdeg:15.2f} {R.df_sat(0.011, A):9.5f} "
          f"{vals['r71   (LIMIT CYCLE)']:9.3f} {vals['r72   (clean)']:9.3f} "
          f"{vals['V282  (clean,ref)']:9.3f} {vals['r73   (clean)']:9.3f}")
As = np.array([r[0] for r in rows])
Lr = np.array([r[1]["r71   (LIMIT CYCLE)"] for r in rows])
i = np.where(Lr < 1.0)[0]
if len(i):
    j = i[0]
    Acrit = np.interp(1.0, [Lr[j], Lr[j - 1]], [As[j], As[j - 1]])
    print(f"\n  r71's verdict flips to STABLE at A = {Acrit:.3f} m/s^2 = {Acrit/Mdeg:.2f} deg of wheel angle.")
print(f"  The limit cycle the model is retrodicting was +/-6 deg = {6*Mdeg:.2f} m/s^2 (fork's own record).")

print()
print("=" * 100)
print("(iii) PLANT EXTRAPOLATION.  model ratio |P(f)|/|P(0.20)| vs the MEASURED ratio")
print("=" * 100)
w2 = 2 * math.pi * np.array([0.20, 2.34, 2.50])
for v in (22.0, 25.0):
    k = R.k_of_v(v)
    print(f"  v={v} m/s  mode {R.mode_hz(v):.2f} Hz   k={k:.4f}")
    for b in (7e-5, 3e-4, 6e-4, 1.2e-3, 1.8e-3, 4.9e-3):
        s = 1j * w2
        P = 1.0 / (R.J * s ** 2 + b * s + k)
        print(f"     b={b:8.1e} (zeta {b/(2*math.sqrt(R.J*k)):.3f})  |P(2.34)|/|P(0.20)| = {abs(P[1])/abs(P[0]):7.3f}"
              f"   |P(2.50)|/|P(0.20)| = {abs(P[2])/abs(P[0]):7.3f}")
print("\n  MEASURED (a3, engaged hands-off >=15 m/s, u=commanded torque -> wheel angle):")
for pn, key in R.PLANTS.items():
    d = A3[key]
    f = np.array(d["f"])
    r = np.array(d["ratio"])
    c = np.array(d["coh"])
    i234 = int(np.argmin(np.abs(f - 2.34)))
    print(f"     {pn:5} ratio(2.34 Hz) = {r[i234]:6.3f}  coh {c[i234]:.2f}   ({d['nsec']:.0f} s)")

print()
print("=" * 100)
print("(iv) SAMPLE SIZE.  P(a useless statistic passes the whole gate) by simulation")
print("=" * 100)
rng = np.random.default_rng(7)
NT = 400000
for K in (4, 5):
    # K controllers ranked at random and INDEPENDENTLY on each of 3 plants
    ok_a = ok_ac = 0
    for _ in range(NT):
        ranks = [rng.permutation(K) for _ in range(3)]          # index 0 = r71, 1 = rev6.4
        top = sum(1 for r in ranks if r[0] == K - 1)            # r71 riskiest
        a = top >= 2
        c = all(r[0] > r[1] for r in ranks)                     # r71 above rev6.4 on every plant
        ok_a += a
        ok_ac += a and c
    print(f"  K={K} controllers, 3 INDEPENDENT plants:  P(clause a) = {ok_a/NT:.4f}   P(a and c) = {ok_ac/NT:.4f}")
# the plants are NOT independent: a multiplicative statistic orders controllers the same way
# on every plant, so the three plants carry ONE draw, not three
for K in (4, 5):
    p_a = 1.0 / K
    print(f"  K={K}, plants PERFECTLY correlated (what a gain-based statistic actually does):"
          f"  P(clause a) = {p_a:.4f}   P(a and c) = {p_a:.4f}")
