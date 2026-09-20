# -*- coding: utf-8 -*-
"""GATE #2 ADVERSARY -- attack the ONE new term itself.

Rebuilds gate #1's loop (r2_stat.py's L, re-derived here, not imported) and asks:

  1. can `Kj * friction_jerk` move a -180 crossing AT ALL, given what friction_jerk IS in source?
  2. under the MAXIMALLY GENEROUS (and, per source, false) reading -- jerk = d/dt of the error,
     through the fork's own 1.2 Hz jerk filter -- how far UP does the crossing actually move?
  3. the (a)-vs-(b) conflict: r73 and r72 differ in EXACTLY ONE parameter (SteerFriction).
     Sweep the only knob and show clause (a) and clause (b) pull it opposite ways.
  4. b-sensitivity and the V282-vs-r71 dose problem.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
R1 = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/retrodict/repair/out/r1_ident.json")

DT = 0.01
J = 8e-5
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
FRIC_THR = 0.30
RATE_RC, RATE_TAPER_V = 0.01, 12.0
KJ = 0.22          # JERK_GAIN, read from fork source (all 8 flown commits)
JERK_LP_HZ = 1.2   # LP_FILTER_CUTOFF_HZ, read from fork source
P = print

k_of = lambda v: float(np.interp(v, HOLD_V_BP, HOLD_K_V))
mode_hz = lambda v: float(np.sqrt(k_of(v) / J) / (2 * np.pi))
lsf_of = lambda v: float((np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, 1.0)) ** 2)


def notch_H(f, f0, q):
    z = np.exp(-2j * np.pi * np.asarray(f) * DT)
    k = np.tan(np.pi * min(f0, 0.45 / DT) * DT)
    n = 1.0 / (1.0 + k / q + k * k)
    b0, b1, a2 = (1.0 + k * k) * n, 2.0 * (k * k - 1.0) * n, (1.0 - k / q + k * k) * n
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def L_of(f, v, alpha, c, p, D, b_plant, relay_mult=1.0, jerk_in_loop=False):
    """gate #1's L, with two adversary switches.
    relay_mult : scalar on the relay DF gain (the ONLY knob the repair has, per source)
    jerk_in_loop : if True, multiply the relay path by (1 + Kj*s/(1+s/wc)) -- the MAXIMALLY
                   GENEROUS reading in which friction_jerk were the error's own derivative."""
    s = 2j * np.pi * np.asarray(f)
    z = np.exp(-s * DT)
    lsf = lsf_of(v)
    Pl = alpha * np.exp(-s * D) / (J * s ** 2 + b_plant * s + k_of(v))
    I = p["ki"] * DT / (1.0 - z)
    relay = p["fric"] / FRIC_THR * relay_mult
    if jerk_in_loop:
        wc = 2 * np.pi * JERK_LP_HZ
        relay = relay * (1.0 + KJ * s / (1.0 + s / wc))
    C = (1.0 + lsf / max(p["kp"], 1e-3)) * ((p["kp"] + I) / p["laf"] + relay)
    if p.get("notch"):
        C = C * notch_H(f, mode_hz(v), p["notch"])
    a = DT / (RATE_RC + DT)
    Hrc = a / (1.0 - (1.0 - a) * np.exp(-s * DT))
    g = p["rate"] * min(1.0, RATE_TAPER_V / max(v, 0.1))
    return C * c * Pl + g * Hrc * s * Pl


def crossings(f, L, lo=1.0, hi=8.0):
    ph = np.unwrap(np.angle(L))
    mag = np.abs(L)
    sel = (f >= lo) & (f <= hi)
    ff, pp, mm = f[sel], ph[sel], mag[sel]
    pp = pp - 2 * np.pi * np.round(pp[0] / (2 * np.pi))
    out = []
    for i in np.where((pp[:-1] > -np.pi) & (pp[1:] <= -np.pi))[0]:
        w = (pp[i] + np.pi) / (pp[i] - pp[i + 1])
        fx = float(ff[i] + w * (ff[i + 1] - ff[i]))
        out.append((fx, float(np.exp(np.interp(fx, ff, np.log(mm))))))
    return out


F = np.linspace(0.2, 12.0, 24000)

CTRL = {  # from each route's own initData + its own flown commit (params_all.json, guard rule)
    "r71  POS": dict(kp=0.85, laf=14.0, ki=0.30, fric=0.011, rate=0.0, notch=None),
    "r73  POS": dict(kp=0.85, laf=14.0, ki=0.60, fric=0.2120497, rate=0.0006, notch=1.0),
    "r72 clean": dict(kp=0.85, laf=14.0, ki=0.60, fric=0.0, rate=0.0006, notch=1.0),
    "rev6.4 cln": dict(kp=1.00, laf=14.0, ki=0.30, fric=0.0, rate=0.0010, notch=1.0),
    "V282 clean": dict(kp=0.90, laf=6.00, ki=0.30, fric=0.010, rate=0.0, notch=None),
    "V282old cln": dict(kp=0.80, laf=2.11, ki=0.30, fric=0.030, rate=0.0, notch=None),
}

S = json.load(open(R1))
plants = {}
for key, d in S["cells"].items():
    wu = np.array(d["wSwu_re"]) + 1j * np.array(d["wSwu_im"])
    wy = np.array(d["wSwy_re"]) + 1j * np.array(d["wSwy_im"])
    plants[key] = dict(route=d["route"], bin=d["bin"], v=d["v"], c=d["c"], secs=d["secs"],
                       alpha=abs(np.mean(wy.mean(0) / wu.mean(0))) * k_of(d["v"]))

# the three plants NOT taken from either positive's own log, 22+ bin (the bin r71's LC was in)
USE = ["00000072--8001fc3048|22+", "0000006c--68c6e94b17|22+", "0000006e--6ca3e014fd|22+"]
D0, B0 = 0.065, 0.0006

P("=" * 112)
P("A1.  WHAT IS `friction_jerk`?  -- read from the fork source, all 8 flown commits")
P("=" * 112)
P("""  latcontrol_torque.py (e8e62f0e1:583-586, identical shape at 66cf4454a:553 and all others):

      expected_lateral_accel = self.curvature_request_buffer[-delay_frames] * CS.vEgo ** 2
      raw_lateral_jerk       = (future_desired_lateral_accel - expected_lateral_accel) / max(lat_delay, dt)
      desired_lateral_jerk   = clip(self.jerk_filter.update(raw_lateral_jerk), +/-2.5)
      friction_jerk          = copysign(max(|desired_lateral_jerk| - deadzone, 0), desired_lateral_jerk)
      ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, ...)

  `future_desired_lateral_accel` is the PLANNER's.  `expected_lateral_accel` is the controller's own
  PAST COMMAND replayed out of curvature_request_buffer.  NEITHER contains `measurement`.
  `measurement` enters the relay argument ONLY through error_with_lsf = (setpoint - measurement)*(1+lsf/kp).

  =>  d(relay argument)/d(measurement)  =  d(error_with_lsf)/d(measurement)  -- the jerk term drops out.
  =>  Kj * friction_jerk is EXOGENOUS to the loop.  It contributes EXACTLY ZERO to L(s), hence
      exactly zero to any -180 deg crossing frequency.  The prereg's stated mechanism --
      "a jerk term is phase LEAD, and lead moves a -180 crossing UP in frequency" -- is FALSE
      of the term the prereg actually names.""")

P("\n" + "=" * 112)
P("A2.  EVEN IF IT WERE IN-LOOP: how much lead can the fork's own jerk path supply?")
P("=" * 112)
wc = 2 * np.pi * JERK_LP_HZ
P("  the fork filters the jerk at LP_FILTER_CUTOFF_HZ = 1.2 Hz, so the best case is a LEAD-LAG")
P("  1 + Kj*s/(1+s/wc), Kj = 0.22 s (JERK_GAIN, source), wc = 2*pi*1.2.")
P(f"  {'f Hz':>6} {'|1+Kj s/(1+s/wc)|':>18} {'phase deg':>10}")
for fq in (1.5, 2.0, 2.34, 3.0, 4.0, 5.0, 6.5, 8.0):
    s = 2j * np.pi * fq
    H = 1.0 + KJ * s / (1.0 + s / wc)
    P(f"  {fq:6.2f} {abs(H):18.3f} {np.degrees(np.angle(H)):10.2f}")
P("  max lead over 1.5-8 Hz is bounded and small; and it applies ONLY to the relay branch,")
P("  which is in PARALLEL with (kp + I)/LAF, so the loop sees even less.")

P("\n" + "=" * 112)
P("A3.  RUN IT.  r73's crossing, on the three non-positive plants, four readings of the repair")
P("=" * 112)
rows = []
for pk in USE:
    pl = plants[pk]
    for nm, mult, jl, lbl in [("baseline (gate #1, no jerk term)", 1.0, False, "base"),
                              ("jerk as EXOGENOUS  (what source says)", 1.0, False, "exog"),
                              ("jerk as IN-LOOP LEAD (maximally generous)", 1.0, True, "lead"),
                              ("in-loop lead, r72 for reference", 1.0, True, "r72lead")]:
        p = dict(CTRL["r72 clean" if lbl == "r72lead" else "r73  POS"])
        L = L_of(F, pl["v"], pl["alpha"], pl["c"], p, D0, B0, mult, jl)
        cs = crossings(F, L)
        s = "  ".join(f"{fx:.2f}Hz|L|={m:.2f}" for fx, m in cs[:3]) or "none in 1-8"
        rows.append(dict(plant=pl["route"], bin=pl["bin"], v=pl["v"], case=lbl, cross=cs))
        P(f"  plant {pl['route'][:8]} v={pl['v']:.1f}  {nm:42s} -> {s}")
    P("")

P("  r73's TARGET WINDOW is [3.000, 8.125] Hz (widest reading of '+/-25% of the 4.0-6.5 band').")
P("  Gate #1 placed r73 at 1.80-1.95 Hz.  Read the FIRST crossing above: the jerk term, at its")
P("  most generous, does not carry r73 anywhere near 3.0 Hz.")

P("\n" + "=" * 112)
P("A4.  THE (a)-vs-(b) CONFLICT.  r73 and r72 differ in EXACTLY ONE flown parameter.")
P("=" * 112)
d73 = {k: CTRL["r73  POS"][k] for k in CTRL["r73  POS"]}
d72 = {k: CTRL["r72 clean"][k] for k in CTRL["r72 clean"]}
P(f"  r73: {d73}")
P(f"  r72: {d72}")
P("  -> identical commit, kp, LAF, ki, rate loop, notch.  SteerFriction 0.21205 vs 0.0 is the ONLY")
P("     difference, so the relay gain is the ONLY knob any admissible repair has on this pair.")
P("")
pl = plants["00000072--8001fc3048|22+"]
P(f"  sweep the relay multiplier on r73, plant r72 (v={pl['v']:.1f}), D={D0 * 1e3:.0f} ms, b={B0}:")
P(f"  {'relay x':>9} {'f_cross Hz':>11} {'|L| r73':>9} {'|L| r72':>9} {'ratio':>7}  {'(a) r73 in [3.0,8.125]?':>24}")
Lr72 = L_of(F, pl["v"], pl["alpha"], pl["c"], d72, D0, B0)
c72 = crossings(F, Lr72)
m72 = c72[0][1] if c72 else np.nan
sweep = []
for mult in [1.0, 0.7, 0.5, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05, 0.03, 0.02, 0.01, 0.0]:
    L = L_of(F, pl["v"], pl["alpha"], pl["c"], d73, D0, B0, mult)
    cs = crossings(F, L)
    fx, m = cs[0] if cs else (np.nan, np.nan)
    ok = "YES" if (3.0 <= fx <= 8.125) else "no"
    sweep.append(dict(mult=mult, f=fx, L73=m, L72=m72, ratio=m / m72))
    P(f"  {mult:9.3f} {fx:11.3f} {m:9.3f} {m72:9.3f} {m / m72:7.3f}  {ok:>24}")
P("")
ok = [r for r in sweep if 3.0 <= r["f"] <= 8.125]
if ok:
    best = max(ok, key=lambda r: r["ratio"])
    P(f"  the LARGEST r73/r72 separation compatible with clause (a) is {best['ratio']:.3f}x, at relay x{best['mult']:.3f}")
    P(f"  (f_cross {best['f']:.2f} Hz).  At relay x1.0 the separation is {sweep[0]['ratio']:.2f}x but f_cross is")
    P(f"  {sweep[0]['f']:.2f} Hz -- outside the window.  CLAUSE (a) AND CLAUSE (b) PULL THE ONE KNOB")
    P("  IN OPPOSITE DIRECTIONS, and the knob is the only difference between the two routes.")
else:
    P("  NO relay multiplier in [0,1] puts r73's first crossing inside clause (a)'s window at all.")

json.dump(dict(sweep=sweep, rows=[{k: (v if k != 'cross' else [list(x) for x in v]) for k, v in r.items()} for r in rows]),
          open(OUT / "jerk_mech.json", "w"), indent=1)
P("\nwrote " + str(OUT / "jerk_mech.json"))
