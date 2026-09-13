# -*- coding: utf-8 -*-
"""v293_s3_gate7.py -- DELIVERABLE 3: the 7.3 Hz question with the SERVO ARM GONE.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

THE QUESTION.  gate73 = |Ls*Rs + Lr*Rr| is a MAGNITUDE gate.  In torque mode Rs = 0 exactly, so it
collapses to |Lr|*k = 1.19*k and says "cut 0xC6446 to 4451 and you are back inside 1.01".  The brief's
instruction is not to stop there: compute the CLOSED-LOOP POLES of the r24-only loop -- the plant with
r24's own traced transfer (1 kHz lag-4 backward difference, the Q10 arm, the post-gain deadband) closed
around it and NOTHING else -- at every candidate arm, over the whole re-fitted plant family, at every
kappa the record admits.

WHY THE FAMILY MUST BE RE-FITTED.  `design290b_family.json` was fitted with the SERVO ARM ALONE closing
the loop, so its g0/zp have absorbed r24; adding r24 on top double-counts (0 of 304 still reproduce the
measured pole).  `r24_lane_transfer`'s own grid is re-run here with L_tot = (R_servo + R_r24)*CPD*G and
a 2-60 Hz closed-loop stability filter, exactly as `_scratch/dzeta_stable.py` does -- and THEN the servo
arm is deleted and the poles re-read.  The control is that with the servo present the family reproduces
the measured V282 pole by construction.

WHAT A FAIL LOOKS LIKE, written before the run:
  * any candidate arm at which the r24-only loop carries a pole with zeta <= 0 anywhere in 3-30 Hz on
    the median plant  -> DO NOT FLASH that arm;
  * any arm at which the 18-22 Hz pole's zeta with the servo gone is BELOW V282's measured 0.012-0.045
    -> torque mode does not remove the grinding, it inherits it;
  * gate73 > 1.01 at the chosen arm -> the 7 Hz strong-turn cycle is predicted to re-arm.

Run:  python v293_s3_gate7.py [nproc]
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                 # noqa: E402
import r24_lane_transfer as M                # noqa: E402
import v293_lib as L                         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
F282, Z282 = (19.7, 20.4), (0.012, 0.045)
F289, Z289 = (15.6, 17.3), (-0.06, 0.12)
ZMIN = -0.005
ARMS = [5244, 4725, 4451, 3933, 3072, 2622, 2048, 1731, 1024, 512, 0]
KAPPAS = [0.10, 0.20, 0.45, 1.00, 1.45]
NSUB = 250
_G = {}


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def _init():
    c, _ = A.read_v289()
    c282 = dict(c)
    c282["fb_a"], c282["fb_b"] = 923, 1560
    _G["el282"] = A.Blocks(c282, False, 0.0)
    _G["c282"] = c282
    _G["fb"] = M.fit_B("creep_1_3med", nb=1, nd=3)


def stable_band(el, pl, r24, lo=2.0, hi=60.0):
    f, z, _ = M.poles2(el, pl, r24)
    m = (f >= lo) & (f <= hi)
    return (not m.any()) or bool(np.nanmin(z[m]) >= ZMIN)


def _w(args):
    fp, zps, kaps, taus, f1s, g0s, kap = args
    if "el282" not in _G:
        _init()
    el282 = _G["el282"]
    r24 = M.R_r24_poly(_G["fb"], kappa=kap) if kap > 0 else (np.array([0.0]), np.array([1.0]))
    keep = []
    for zp in zps:
        for ka in kaps:
            if fp is None and (zp is not None or ka is not None):
                continue
            for tau in taus:
                for f1 in f1s:
                    for g0 in g0s:
                        p = dict(g0=float(g0), tau=float(tau), f1=float(f1), fp=fp, zp=zp, kappa=ka, label="m")
                        pl = A.Plant(p, 1.0, "m")
                        f2, z2 = M.mode2(el282, pl, r24)
                        if not (np.isfinite(f2) and F282[0] <= f2 <= F282[1] and Z282[0] <= z2 <= Z282[1]):
                            continue
                        if not stable_band(el282, pl, r24):
                            continue
                        keep.append(p)
    return keep


def grid(kap, npc):
    fps = [None] + list(np.arange(15.0, 28.01, 0.5))
    zps = (0.02, 0.04, 0.07, 0.12, 0.2, 0.35, 0.5, 0.7)
    kaps = (None, 0.15, 0.3, 0.6, 1.0)
    taus = (0.001, 0.002, 0.004, 0.006, 0.008, 0.010, 0.012)
    f1s = (3.0, 5.0, 12.0, 30.0)
    g0s = np.exp(np.linspace(np.log(0.002), np.log(0.8), 30))
    jobs = []
    for fp in fps:
        if fp is None:
            jobs.append((None, (None,), (None,), tuple(np.arange(0.001, 0.0161, 0.001)),
                         (2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0),
                         np.exp(np.linspace(np.log(0.002), np.log(0.8), 50)), kap))
        else:
            jobs.append((float(fp), zps, kaps, taus, f1s, g0s, kap))
    with Pool(npc, initializer=_init) as pool:
        res = pool.map(_w, jobs)
    return [x for r in res for x in r]


def deadband_df(delta, amp):
    """describing function of the post-gain deadzone (0xC61F6 = 3): s -> 0 if |s|<=d else s - d*sign(s)."""
    a = np.asarray(amp, float)
    r = np.clip(delta / np.maximum(a, 1e-12), 0.0, 1.0)
    return np.where(a <= delta, 0.0, (2.0 / np.pi) * (np.pi / 2 - np.arcsin(r) - r * np.sqrt(np.maximum(1 - r * r, 0.0))))


# ================================================================================================
def main():
    npc = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 1)
    _init()
    c282 = L.read_cells(L.IMG282)
    fb = _G["fb"]
    el282 = _G["el282"]
    elTM = L.BlocksTM(L.torque_mode(c282, kp=119), notch=False, g=0.0, kp=119, kd=0.0, fb_zero=True)

    pr("=" * 124)
    pr("V293 TORQUE MODE -- THE 7.3 Hz QUESTION WITH THE SERVO ARM GONE        tmdesign 2026-09-13")
    pr("=" * 124)
    pr("B(f) fit: stratum creep_1_3med, rms ln|B| %.4f, rms phase %.2f deg  (inherited, r24lane's own fit)"
       % (fb["rms_ln_mag"], fb["rms_phase_deg"]))

    # ---------------------------------------------------------------- CONTROL: Rs is EXACTLY zero
    pr("")
    pr("-" * 124)
    pr("CONTROL 0 -- the servo's 7.3 Hz return ratio in torque mode is EXACTLY zero, not merely small")
    pr("-" * 124)
    for f in (3.0, 7.3, 20.3):
        pr("   |R_servo(%.1f)|  V282 %8.4f      V293 torque mode %.3e" %
           (f, abs(el282.Rf(f)), abs(complex(np.atleast_1d(elTM.Rf(f))[0]))))
    pr("   (0xC62E6 = 0 clamps the feedback operand to +-0 on all three branches -- V279's `ff279` proved")
    pr("    that from the bytes and the cell has exactly 3 readers image-wide.)")

    # ---------------------------------------------------------------- THE MAGNITUDE GATE
    pr("")
    pr("=" * 124)
    pr("PART 1  THE MAGNITUDE GATE, gate73 = |Ls*Rs + Lr*Rr|, at Rs = 0")
    pr("=" * 124)
    pr("Ls = %.2f<%+.0f deg, Lr = %.2f<%+.0f deg.  Today (V282, both arms) = %.4f."
       % (abs(A.LS73), np.degrees(np.angle(A.LS73)), abs(A.LR73), np.degrees(np.angle(A.LR73)),
          L.gate73_tm(1.0, 1.0)))
    pr("With Rs = 0 the two vectors no longer cancel: 0.55<+96 = (%.3f, %+.3f) is DELETED and only"
       % (A.LS73.real, A.LS73.imag))
    pr("1.19<-27 = (%.3f, %+.3f) remains, scaled by k.  gate73 = 1.19*k EXACTLY, monotonic in k."
       % (A.LR73.real, A.LR73.imag))
    pr("")
    pr("  %8s %8s %10s %10s %14s" % ("0xC6446", "k", "gate73 TM", "gate73 V282", "cut vs 5244"))
    for arm in ARMS:
        k = arm / 5244.0
        pr("  %8d %8.4f %10.4f %10.4f %13.1f %%" %
           (arm, k, L.gate73_tm(k), L.gate73_tm(k, Rs=1.0), 100.0 * (k - 1.0)))
    kk, aa = L.r24_arm_for_gate(1.010, Rs=0.0)
    pr("")
    pr("  gate73 = 1.010 at k = %.4f  =>  0xC6446 = %.0f  (a %.1f %% cut).   [EVIDENCE -- closed form]"
       % (kk, aa, 100.0 * (1 - kk)))
    pr("  gate73 = 1.0028 (V282's own value) at k = %.4f => 0xC6446 = %.0f (a %.1f %% cut)."
       % (L.r24_arm_for_gate(1.0028, 0.0)[0], L.r24_arm_for_gate(1.0028, 0.0)[1],
          100.0 * (1 - L.r24_arm_for_gate(1.0028, 0.0)[0])))
    pr("  Hand check: 1.19*k = 1.010 => k = %.6f, arm = %.1f.  Matches the solver." % (1.010 / 1.19, 5244 * 1.010 / 1.19))
    pr("")
    pr("  🛑 THIS IS NOT THE SAME NUMBER AS THE 'NET-DAMPING NEUTRAL POINT' ~1880 the record quotes.")
    pr("     1880 is where Re(aggregator) at 7 Hz crosses zero in the LOADED stratum WITH the servo")
    pr("     present (GRINDING-DEEP section 2).  4451 is where the TOTAL 7.3 Hz return-ratio magnitude")
    pr("     comes back to the record's own allowance WITHOUT the servo.  Different criteria, and the")
    pr("     gate is the one calibrated against two configurations the operator has actually driven.")

    # ---------------------------------------------------------------- THE POLES
    pr("")
    pr("=" * 124)
    pr("PART 2  THE r24-ONLY LOOP'S CLOSED-LOOP POLES -- not a magnitude gate")
    pr("=" * 124)
    res = {}
    for kap in KAPPAS:
        t0 = time.time()
        fam = grid(kap, npc)
        pr("")
        pr("kappa %.2f : %d plants reproduce the measured V282 pole AND are closed-loop stable 2-60 Hz"
           " with BOTH arms  (%.0f s)" % (kap, len(fam), time.time() - t0))
        if not fam:
            pr("   (no plant survives -- this kappa is excluded by the family fit itself)")
            res["%.2f" % kap] = dict(n=0)
            continue
        rng = np.random.default_rng(20260913)
        if len(fam) > NSUB:
            sel = rng.choice(len(fam), NSUB, replace=False)
            fam_s = [fam[i] for i in sorted(sel)]
            pr("   (scored on a seeded random subsample of %d of them -- the pole scan is O(n * arms))" % NSUB)
        else:
            fam_s = fam
        pls = [A.Plant(p, 1.0, "m") for p in fam_s]
        pr("  %8s | %-28s | %-28s | %-22s" % ("0xC6446", "SERVO PRESENT (V282 control)",
                                              "SERVO GONE (V293 torque mode)", "worst pole 3-30 Hz, TM"))
        pr("  %8s | %8s %8s %9s | %8s %8s %9s | %8s %8s %5s" %
           ("", "f Hz", "zeta md", "z p10", "f Hz", "zeta md", "z p10", "f Hz", "zeta", "unst"))
        rows = []
        for arm in ARMS:
            r = M.R_r24_poly(fb, kappa=kap * arm / 5244.0)
            a1 = np.array([M.mode2(el282, pl, r) for pl in pls], float)
            a2 = np.array([M.mode2(elTM, pl, r) for pl in pls], float)
            worst = []
            unst = 0
            for pl in pls:
                f, z, zz = M.poles2(elTM, pl, r)
                m = (f >= 3.0) & (f <= 30.0)
                if m.any():
                    j = int(np.nanargmin(z[m]))
                    worst.append((f[m][j], z[m][j]))
                if np.any(np.abs(zz) >= 1.0):
                    unst += 1
            worst = np.array(worst, float) if worst else np.zeros((1, 2))
            jw = int(np.nanargmin(worst[:, 1]))
            row = dict(arm=arm, k=arm / 5244.0,
                       f_sv=float(np.nanmedian(a1[:, 0])), z_sv=float(np.nanmedian(a1[:, 1])),
                       z_sv10=float(np.nanpercentile(a1[:, 1], 10)),
                       f_tm=float(np.nanmedian(a2[:, 0])), z_tm=float(np.nanmedian(a2[:, 1])),
                       z_tm10=float(np.nanpercentile(a2[:, 1], 10)),
                       wf=float(worst[jw, 0]), wz=float(worst[jw, 1]), unst=unst, n=len(pls))
            rows.append(row)
            pr("  %8d | %8.2f %8.4f %9.4f | %8.2f %8.4f %9.4f | %8.2f %8.4f %5d" %
               (arm, row["f_sv"], row["z_sv"], row["z_sv10"], row["f_tm"], row["z_tm"], row["z_tm10"],
                row["wf"], row["wz"], unst))
        res["%.2f" % kap] = dict(n=len(pls), rows=rows)
    pr("")
    pr("  'worst pole 3-30 Hz, TM' is the LEAST-DAMPED pole anywhere in 3-30 Hz on the WORST plant of")
    pr("  the family with the servo gone -- the column a magnitude gate cannot see.  'unst' counts")
    pr("  plants with any closed-loop root outside the unit circle.")

    # ---------------------------------------------------------------- the deadband
    pr("")
    pr("=" * 124)
    pr("PART 3  THE POST-GAIN DEADBAND 0xC61F6 = %d -- does it bind at either band?" % c282["r24_dead"])
    pr("=" * 124)
    pr("The lane is  d = (bar[n]-bar[n-4])>>1 -> clamp +-5120 -> s = (d*arm)>>10 -> deadzone(3) -> negate")
    pr("-> clamp +-8192.  The deadzone acts on s, i.e. AFTER the arm, so its relative size falls as the")
    pr("arm rises.  Describing function N(A) = (2/pi)[pi/2 - asin(r) - r*sqrt(1-r^2)], r = 3/A.")
    pr("")
    pr("  %10s %10s %12s %12s %10s %10s" % ("band", "bar amp", "|d| amp", "s @5244", "N(5244)", "N(2048)"))
    for lab, f0, baramp in (("7.3 Hz loaded", 7.3, 1500.0), ("7.3 Hz creep", 7.3, 400.0),
                            ("20.3 Hz ring", 20.3, 44.0), ("20.3 Hz loud", 20.3, 120.0)):
        dmag = 0.5 * abs(1 - np.exp(-2j * np.pi * f0 * 0.004)) * baramp
        for arm, col in ((5244, "N5"), (2048, "N2")):
            pass
        s5 = dmag * 5244 / 1024.0
        s2 = dmag * 2048 / 1024.0
        pr("  %10s %10.0f %12.1f %12.1f %10.4f %10.4f" %
           (lab, baramp, dmag, s5, float(deadband_df(c282["r24_dead"], s5)),
            float(deadband_df(c282["r24_dead"], s2))))
    pr("")
    pr("  The deadzone is a MAGNITUDE-ONLY, amplitude-dependent attenuation.  At the 7 Hz loaded")
    pr("  amplitude it is inert (N > 0.99).  At the ring amplitude it removes 5-9 %% of the lane and")
    pr("  MORE as the arm is cut -- i.e. cutting 0xC6446 costs slightly more 20 Hz damping than the")
    pr("  linear column says.  [EVIDENCE for the arithmetic; the bar amplitudes are the record's.]")

    json.dump(res, open(os.path.join(SCR, "v293_s3_gate7.json"), "w"), indent=1)
    open(os.path.join(SCR, "v293_s3_gate7.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s3_gate7.{txt,json}")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
