# -*- coding: utf-8 -*-
"""v293_s2_replay.py -- DELIVERABLE 2: TORQUE MODE replayed through the operator's OWN recorded
grinding episodes, with the LKAS loop FULLY OPEN (fb == 0, Kd 0, Kp flat), byte-exact.

Agent `tmdesign`, subagent of `main`, 2026-09-13.  ANALYSIS ONLY -- nothing built, flashed or sent.

WHAT THIS IS.  The V292 replay machinery (`v292_replay_lib`), extended so the B arm can be a
TORQUE-MODE build: 0xC62E6 = 0 (the feedback operand is identically zero on all three branches),
Kd = 0, Kp flat, r24 arm 0xC6446 swept.  Same 10 loudest r39 windows, same r6c and r35 windows, same
plant family, same causal marching disturbance inversion, same r24 arm-delta fold.

PRE-REGISTERED, written before the first run (mirrors the V292 replay's own F-list so the two are
directly comparable):
  F1  pooled 18-22 Hz DELIVERED-TORQUE ring ratio V293/V282  >= 0.85          -> "does not help"
  F2  pooled 18-22 Hz WHEEL-RATE ring ratio V293/V282        >= 0.85          -> "does not help"
      (the wheel is the operator-facing channel; the torque channel in torque mode is trivially
       quiet because T no longer contains any feedback -- F1 alone would be a TAUTOLOGY, so F2 is
       the load-bearing one.  Declared here, before the run.)
  F3  9-18 Hz shoulder on the WHEEL >= 1.50 while the ring ratio is < x2      -> "a relocation"
  F4  6-9 Hz strong-turn TORQUE ripple in situ > 1.05                         -> the 7 Hz gate, in situ
  F5  delivered torque outside the ring bands moves by more than +-20 %       -> AUTHORITY
      (+-2 % was V292's limit because V292 is a same-topology edit.  Torque mode CHANGES the
       delivered quantity, so +-2 % is unachievable by construction; +-20 % is declared here as the
       honest bar and the actual number is reported whatever it is.)
  CONTROL: the V282 arm must reproduce the recording EXACTLY (max|dT| = 0) on every window and fit.

Run:  python v293_s2_replay.py [stage]
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_echo_sizing as ES                     # noqa: E402
import design290b_candidates as D                  # noqa: E402
import adv_v290_physics as A                       # noqa: E402
import v292_replay_lib as R                        # noqa: E402
import v292_replay_s2 as S2                        # noqa: E402
import v293_lib as L                               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K = 100.0, 1000.0
SCR = os.path.join(HERE, "_scratch")
OUT = []
RNG = np.random.default_rng(20260913)
NAMED = [225, 215, 38, 117]
BANDS = dict(ring=(18.0, 22.0), shoulder=(9.0, 18.0), low=(5.0, 9.0), turn=(6.0, 9.0))
ARMS = [5244, 4451, 2048]
KPS = [119, 160, 200, 248]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def boot(v, n=3000):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 3:
        return np.nan, np.nan
    bs = np.median(v[RNG.integers(0, len(v), (n, len(v)))], axis=1)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


# ------------------------------------------------------------------------------------------------
def replay_tm(g, a0, b0, c282, c293, pl, arm=5244, n_iter=4, motor_gain=True):
    """ONE window, ONE fit.  A arm = V282 (must reproduce the recording).  B arm = V293 torque mode.

    The disturbance `d` is inverted from the V282 electronics on the recorded wire, exactly as the
    V292 replay does, so both arms share the same road/driver/plant-mismatch residual.
    The r24 arm delta (5244 -> arm) is folded as a parallel branch by fixed-point iteration.
    """
    W = R.prep_window(g, a0, b0, c282)
    W9 = R.prep_window(g, a0, b0, c293)          # same command/fade/eng; sp and kp from V293's banks
    el = R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True)
    d, S_ol = R.invert_d(el, R.PlantIIR(pl), W, W["wire1k"])
    Aarm = R.closed_run(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W, d)
    recon = float(np.max(np.abs(Aarm["T"] - S_ol["T"])))

    def run_b(ex):
        return R.closed_run(R.Elec(c293, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0),
                            R.PlantIIR(pl), W9, d, extra_T=ex)
    Barm = run_b(None)
    iters = []
    if arm != 5244:
        H = lambda f: R.r24_delta_response(f, arm_from=5244, arm_to=arm,        # noqa: E731
                                           with_motor_gain=motor_gain)
        ex = np.zeros(W9["n"])
        for _ in range(n_iter):
            ex_new = R.apply_fr(Barm["wire"], H)
            iters.append(float(np.max(np.abs(ex_new - ex))))
            ex = ex_new
            Barm = run_b(ex)
    return dict(W=W, W9=W9, d=d, A=Aarm, B=Barm, recon=recon, iters=iters)


def measure(Aarm, Barm, f0, skip=800):
    o = {}
    for nm, (lo, hi) in BANDS.items():
        ta = R.band_amp(Aarm["T"][skip:], lo, hi)
        tb = R.band_amp(Barm["T"][skip:], lo, hi)
        o["T_" + nm] = (ta, tb, tb / ta if ta > 0 else np.nan)
        wa = R.band_amp(Aarm["wire"][skip:], lo, hi)
        wb = R.band_amp(Barm["wire"][skip:], lo, hi)
        o["W_" + nm] = (wa, wb, wb / wa if wa > 0 else np.nan)
    oa = R.out_of_band_rms(Aarm["T"][skip:], [(5.0, 22.0)])
    ob = R.out_of_band_rms(Barm["T"][skip:], [(5.0, 22.0)])
    o["auth_oob"] = (oa, ob, ob / oa if oa > 0 else np.nan)
    la = R.band_amp(Aarm["T"][skip:], 0.3, 3.0)
    lb = R.band_amp(Barm["T"][skip:], 0.3, 3.0)
    o["auth_lf"] = (la, lb, lb / la if la > 0 else np.nan)
    ma = float(np.mean(np.abs(Aarm["T"][skip:])))
    mb = float(np.mean(np.abs(Barm["T"][skip:])))
    o["auth_absmean"] = (ma, mb, mb / ma if ma > 0 else np.nan)
    wa = float(np.std(Aarm["wire"][skip:]))
    wb = float(np.std(Barm["wire"][skip:]))
    o["wire_rms"] = (wa, wb, wb / wa if wa > 0 else np.nan)
    return o


def pooled(rows, key):
    v = np.array([r[key][2] for r in rows], float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return np.nan, (np.nan, np.nan)
    return float(np.median(v)), boot(v)


def abs_pooled(rows, key, j):
    v = np.array([r[key][j] for r in rows], float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else np.nan


HDR = {"T_ring": "T 18-22", "W_ring": "W 18-22", "T_shoulder": "T 9-18", "W_shoulder": "W 9-18",
       "T_low": "T 5-9", "W_low": "W 5-9", "T_turn": "T 6-9", "W_turn": "W 6-9",
       "T_sel": "T sel-band", "W_sel": "W sel-band", "auth_oob": "auth oob",
       "auth_lf": "auth LF", "auth_absmean": "auth |T|", "wire_rms": "wire rms"}
KEYS = ("T_ring", "W_ring", "W_shoulder", "T_shoulder", "T_low", "W_low",
        "auth_oob", "auth_lf", "auth_absmean")


def table(res, fits, title, keys=KEYS):
    pr("")
    pr(title)
    pr("-" * 126)
    pr("  %-22s" % "fit" + "".join("%11s" % HDR.get(k, k) for k in keys))
    allrows = []
    for f in fits:
        rows = res[f["id"]]
        allrows += rows
        tag = "%d%s" % (f["id"], {225: " (median)", 215: " (lo-auth)", 38: " (hi-auth)",
                                  117: " (worst B4)"}.get(f["id"], ""))
        pr("  %-22s" % tag + "".join("%11.3f" % pooled(rows, k)[0] for k in keys))
    pr("  " + "-" * 124)
    ms = [pooled(allrows, k)[0] for k in keys]
    ci = ["[%.2f,%.2f]" % pooled(allrows, k)[1] for k in keys]
    pr("  %-22s" % "POOLED (all fits)" + "".join("%11.3f" % v for v in ms))
    pr("  %-22s" % "  95% CI" + "".join("%11s" % v for v in ci))
    return allrows


def run_route(g, wins, c282, c293, fits, arm=5244, skip=800, motor_gain=True):
    res = {}
    for f in fits:
        pl = D.mkplant(f)
        rows = []
        for (a0, b0, p0) in wins:
            rep = replay_tm(g, a0, b0, c282, c293, pl, arm=arm, motor_gain=motor_gain)
            assert rep["recon"] == 0.0, "V282 arm did NOT reproduce the recording (fit %d)" % f["id"]
            rows.append(measure(rep["A"], rep["B"], g["f0"], skip=skip))
        res[f["id"]] = rows
    return res


# ------------------------------------------------------------------------------------------------
def ringdown_tm(g, wins, c282, c293, fits, arm=5244, amp=512.0, nwin=6):
    """the MATCHED free ring-down, and the LINEAR closed-loop pole, for the OPEN LKAS lane.

    In torque mode the LKAS return ratio is ZERO, so the linear pole is the PLANT's own pole with
    whatever r24 still closes around it -- which is exactly the `zeta_open >= 0.05` question.
    """
    rows, lin = {}, {}
    for f in fits:
        pl = D.mkplant(f)
        e2 = A.Blocks(dict(c282, fb_a=R.V282_FB[0], fb_b=R.V282_FB[1]), False, 0.0)
        e9 = L.BlocksTM(c293, notch=False, g=0.0, kp=c293["kp_Y"][0], kd=0.0, fb_zero=True)
        f2, z2 = A.mode_pole(e2, pl, 10, 32)
        f9, z9 = A.mode_pole(e9, pl, 10, 32)
        if not np.isfinite(f9):
            # with L == 0 the closed-loop poles ARE the plant's own; read them directly
            w = np.roots(pl.den[::-1])
            w = w[np.abs(w) > 1e-12]
            z = 1.0 / w
            s = np.log(z) * A.FS
            ff = np.abs(s.imag) / (2 * np.pi)
            zz = -s.real / np.abs(s)
            m = (ff >= 10) & (ff <= 32)
            if m.any():
                k = int(np.argmin(zz[m]))
                f9, z9 = float(ff[m][k]), float(zz[m][k])
        h2 = np.log(2) / (2 * np.pi * z2 * f2) * 1e3 if z2 > 0 else np.inf
        h9 = np.log(2) / (2 * np.pi * z9 * f9) * 1e3 if (np.isfinite(z9) and z9 > 0) else np.inf
        lin[f["id"]] = (f2, z2, h2, f9, z9, h9, h9 / h2 if np.isfinite(h2) and h2 > 0 else np.nan)
        rr = []
        for (a0, b0, p0) in wins[:nwin]:
            W = R.prep_window(g, a0, b0, c282)
            W9 = R.prep_window(g, a0, b0, c293)
            d, _ = R.invert_d(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W, W["wire1k"])
            k0 = (p0 - (a0 - 50)) * 10
            dT2, dW2 = R.kick_response(dict(c=c282, fb=R.V282_FB, ef=False, two_floor=True), pl, W, d, k0, amp=amp)
            base = R.closed_run(R.Elec(c293, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0), R.PlantIIR(pl), W9, d)
            d2 = np.array(d, float)
            d2[k0] += amp
            pert = R.closed_run(R.Elec(c293, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0), R.PlantIIR(pl), W9, d2)
            dW9 = pert["wire"] - base["wire"]
            h2w = R.decay_halflife(dW2, k0)
            h9w = R.decay_halflife(dW9, k0)
            rr.append((h2w[0], h9w[0], h9w[0] / h2w[0] if h2w[0] > 0 else np.nan, h2w[2], h9w[2]))
        rows[f["id"]] = np.array(rr, float)
    return rows, lin


# ------------------------------------------------------------------------------------------------
def forced_comb(g, wins, c282, c293, fits, skip=800):
    """THE FORCED RESPONSE: how much 18-22 Hz does the COMMAND itself put into T and into the wheel?

    In torque mode T = f(cmd) exactly, so the delivered torque's whole 18-22 Hz content is the
    command's own (the 20 Hz camera comb), shaped by the map LERP, the fade and the output lag.
    This is the number that says whether a fully open lane can still be rung by openpilot's staircase.
    """
    out = []
    for f in fits:
        pl = D.mkplant(f)
        for (a0, b0, p0) in wins:
            W = R.prep_window(g, a0, b0, c282)
            W9 = R.prep_window(g, a0, b0, c293)
            d, ol = R.invert_d(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W, W["wire1k"])
            Bv = R.closed_run(R.Elec(c293, fb=R.V282_FB, ef=False, two_floor=True, kd=0.0), R.PlantIIR(pl), W9, d)
            # the V282 CMD leg, the record's own decomposition: run V282 open loop with the wire frozen
            xz = np.zeros(W["n"], dtype=np.int64)
            cmdleg = R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True).run(
                xz, W["sp"], W["kp"], W["m"], W["eng"])
            out.append(dict(
                Tcmd293=R.band_amp(Bv["T"][skip:], 18.0, 22.0),
                Tcmd282=R.band_amp(cmdleg["T"][skip:], 18.0, 22.0),
                Ttot282=R.band_amp(ol["T"][skip:], 18.0, 22.0),
                Wd=R.band_amp(d[skip:], 18.0, 22.0),
                W293=R.band_amp(Bv["wire"][skip:], 18.0, 22.0),
                W282=R.band_amp(W["wire1k"][skip:], 18.0, 22.0)))
    return out


# ================================================================================================
def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    named = [byid[i] for i in NAMED]
    spread = named + [f for f in stable[::6] if f["id"] not in NAMED]

    c282 = L.read_cells(L.IMG282)
    c293 = L.torque_mode(c282, kp=119)
    c293_248 = L.torque_mode(c282, kp=248)

    pr("=" * 126)
    pr("V293 TORQUE MODE ON THE OPERATOR'S OWN RECORDED GRINDING EPISODES -- byte-exact closed-loop replay")
    pr("agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.")
    pr("=" * 126)
    pr("A arm = V282 as flown (0xC62E6 = %d, Kp %s, Kd %s, fb lag %d/%d, r24 %d)"
       % (c282["fb_clamp"], c282["kp_Y"][0], c282["kd_Y"][0], c282["fb_a"], c282["fb_b"], c282["r24_arm"]))
    pr("B arm = V293 TORQUE MODE (0xC62E6 = 0 => fb == 0 => E = 32*sp ; Kd = 0 ; Kp flat 119 ; map, gain,")
    pr("        clamps, output lag, fade all V282).  r24 arm 0xC6446 swept over %s." % ARMS)
    pr("Cells read from the IMAGES.  Plant family design290b: %d fits, %d linear-stable.  Fits: %s"
       % (len(fam), len(stable), ", ".join(str(f["id"]) for f in spread)))
    pr("")
    pr("PRE-REGISTERED FAIL CRITERIA (see the module docstring): F1 T-ring >= 0.85 ; F2 W-ring >= 0.85 ;")
    pr("F3 W 9-18 >= 1.50 ; F4 T 6-9 in loaded turns > 1.05 ; F5 |auth oob - 1| > 0.20.")

    # ------------------------------------------------------------------ the LINEAR second method
    pr("")
    pr("=" * 126)
    pr("TASK 2.0  SECOND METHOD, no time-domain march: the SENSITIVITY |1/(1+L)| V282 vs OPEN")
    pr("=" * 126)
    pr("With the LKAS feedback at zero, L_servo == 0 and the closed-loop sensitivity is EXACTLY 1 at")
    pr("every frequency.  So the predicted wheel-rate band ratio for a disturbance-driven band is")
    pr("simply 1/|S_V282(f)| -- a ratio with no plant inversion and no replay in it.")
    pr("")
    fgrid = np.array([3.0, 5.0, 6.0, 7.3, 9.0, 12.0, 14.0, 16.0, 18.0, 20.3, 22.0, 26.0, 30.0])
    pr("  %-14s" % "fit" + "".join("%8.1f" % f for f in fgrid))
    Srows = []
    for f in spread:
        pl = D.mkplant(f)
        e2 = A.Blocks(dict(c282, fb_a=R.V282_FB[0], fb_b=R.V282_FB[1]), False, 0.0)
        S = 1.0 / np.abs(1.0 + A.Lf(e2, pl, fgrid))
        Srows.append(1.0 / S)                      # open / closed  == |1 + L|
        if f["id"] in NAMED:
            pr("  %-14s" % ("%d" % f["id"]) + "".join("%8.2f" % v for v in 1.0 / S))
    Sm = np.median(np.array(Srows), axis=0)
    pr("  " + "-" * 124)
    pr("  %-14s" % "MEDIAN x(open)" + "".join("%8.2f" % v for v in Sm))
    pr("  %-14s" % "  p10" + "".join("%8.2f" % v for v in np.percentile(np.array(Srows), 10, axis=0)))
    pr("  %-14s" % "  p90" + "".join("%8.2f" % v for v in np.percentile(np.array(Srows), 90, axis=0)))
    pr("")
    pr("  READ IT LIKE THIS: a value > 1 at f means V282's loop was SUPPRESSING disturbance there and")
    pr("  opening it makes the wheel move MORE; a value < 1 means the loop was AMPLIFYING (de-damping)")
    pr("  and opening it makes the wheel move LESS.  The 18-22 Hz column is the grinding; the 5-9 Hz")
    pr("  column is the strong-turn band.")

    # ------------------------------------------------------------------ r39
    g39 = S2.route("r39", (18.0, 22.0))
    w39 = ES.loud_windows(g39)
    pr("")
    pr("=" * 126)
    pr("TASK 2A  r39 (V282), the 10 loudest 3 s engaged windows, f0 %.3f Hz" % g39["f0"])
    pr("=" * 126)
    t0 = time.time()
    res = {}
    for arm in ARMS:
        res[arm] = run_route(g39, w39, c282, L.torque_mode(c282, kp=119, r24_arm=arm), spread, arm=arm)
        table(res[arm], spread, "r39  V293 torque mode, Kp 119, 0xC6446 = %d  (k = %.4f, gate73 = %.4f)"
              % (arm, arm / 5244.0, L.gate73_tm(arm / 5244.0)))
    pr("")
    pr("(%.0f s)" % (time.time() - t0))

    # Kp ladder -- authority is the only thing Kp moves with the loop open
    pr("")
    pr("r39  THE Kp LADDER -- with the loop open Kp is a pure output scale, so only AUTHORITY moves")
    pr("-" * 126)
    pr("  %-14s" % "Kp" + "".join("%11s" % HDR.get(k, k) for k in KEYS))
    for kp in KPS:
        rk = run_route(g39, w39, c282, L.torque_mode(c282, kp=kp), named, arm=5244)
        rows = [r for f in named for r in rk[f["id"]]]
        pr("  %-14s" % kp + "".join("%11.3f" % pooled(rows, k)[0] for k in KEYS))
    pr("  Kp 119 = peak-neutral (rails exactly at the map top).  The rms-neutral Kp is where auth |T| = 1.")

    # ------------------------------------------------------------------ ring-down + forced comb
    pr("")
    pr("=" * 126)
    pr("TASK 2B  THE 18-22 Hz OBJECT WITH THE LOOP OPEN -- matched free ring-down on the WHEEL")
    pr("=" * 126)
    rd, lin = ringdown_tm(g39, w39, c282, c293, named)
    pr("  %-14s %26s | %34s" % ("fit", "LINEAR closed-loop pole", "MATCHED free ring-down (wheel), byte-exact"))
    pr("  %-14s %12s %12s | %11s %11s %7s %5s" %
       ("", "V282 f/zeta", "V293 f/zeta", "V282 t1/2", "V293 t1/2", "ratio", "r2"))
    for f in named:
        f2, z2, h2, f9, z9, h9, lr = lin[f["id"]]
        rr = rd[f["id"]]
        pr("  %-14s %5.2f/%.4f %5.2f/%.4f | %8.0f ms %8.0f ms %7.3f %5.2f" %
           (f["id"], f2, z2, f9, z9, np.nanmedian(rr[:, 0]), np.nanmedian(rr[:, 1]),
            np.nanmedian(rr[:, 2]), np.nanmedian(rr[:, 4])))
    pr("")
    pr("  The V293 column is the PLANT's own pole with r24 still closed around it at 5244 -- the LKAS")
    pr("  return ratio is exactly zero, so nothing of the servo is left in the characteristic equation.")
    pr("  Compare the record's OPEN-LOOP measurement: zeta_open >= 0.05 or non-modal, 35 routes.")

    pr("")
    pr("=" * 126)
    pr("TASK 2C  THE FORCED RESPONSE -- what the COMMAND alone still drives at 18-22 Hz")
    pr("=" * 126)
    fc = forced_comb(g39, w39, c282, c293, named)
    def med(k):
        return float(np.median([o[k] for o in fc]))
    pr("  V282 total delivered-torque 18-22 Hz amplitude (open-loop mirror) : %7.2f counts" % med("Ttot282"))
    pr("  V282 CMD leg alone (wire frozen at zero)                          : %7.2f counts" % med("Tcmd282"))
    pr("  V293 delivered torque 18-22 Hz  (= its CMD leg, by construction)  : %7.2f counts   x%.3f of V282 total"
       % (med("Tcmd293"), med("Tcmd293") / med("Ttot282")))
    pr("  recorded wheel-rate ring 18-22 Hz                                 : %7.2f raw counts (%.2f deg/s)"
       % (med("W282"), med("W282") / 8.0))
    pr("  V293 replayed wheel-rate ring                                     : %7.2f raw counts   x%.3f"
       % (med("W293"), med("W293") / med("W282")))
    pr("  residual disturbance d's own 18-22 Hz content                     : %7.2f raw counts   x%.3f of recorded"
       % (med("Wd"), med("Wd") / med("W282")))
    pr("")
    pr("  => the disturbance floor is the FLOOR the open lane can reach: with L == 0 the wheel ring is")
    pr("     d filtered by the plant's own 1/(1) -- i.e. d itself plus the plant's response to T_cmd.")

    # ------------------------------------------------------------------ r6c
    pr("")
    pr("=" * 126)
    pr("TASK 2D  r6c -- the FRESHEST V282 route (3701 s, mostly motorway)")
    pr("=" * 126)
    spread6 = named + [f for f in stable[::12] if f["id"] not in NAMED]
    for band, lab in (((18.0, 22.0), "the ring band"), ((12.0, 17.0), "the 12-17 Hz band")):
        g6 = S2.route("r6c", band)
        w6 = ES.loud_windows(g6, n=5)
        pr("")
        pr("  r6c, %s: f0 %.3f Hz, %d loudest engaged 3 s windows" % (lab, g6["f0"], len(w6)))
        for (a0, b0, p0) in w6:
            pr("      t %7.1f s   idx p50 %5.0f   v %4.1f m/s   env peak %6.1f" %
               (g6["t"][p0] - g6["t"][0], np.median(g6["idx_live"][a0:b0]),
                np.median(g6["vego"][a0:b0]), g6["env"][p0]))
        if not w6:
            continue
        BANDS["sel"] = band
        r6 = run_route(g6, w6, c282, c293, spread6, arm=5244)
        table(r6, spread6, "  r6c / %s -- V293(Kp 119, r24 5244) / V282" % lab,
              keys=("T_sel", "W_sel", "T_ring", "W_ring", "W_shoulder", "W_low",
                    "auth_oob", "auth_lf", "auth_absmean"))
        BANDS.pop("sel", None)

    json.dump({str(a): {str(k): [[list(map(float, r[kk][:3])) for kk in KEYS] for r in v]
                        for k, v in res[a].items()} for a in ARMS},
              open(os.path.join(SCR, "v293_s2_r39.json"), "w"))
    with open(os.path.join(SCR, "v293_s2_replay.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/v293_s2_replay.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
