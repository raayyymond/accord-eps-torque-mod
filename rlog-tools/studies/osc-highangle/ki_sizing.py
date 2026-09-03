# -*- coding: utf-8 -*-
"""studies/osc-highangle/ki_sizing.py -- sizing a small Ki on the LKAS rate PID (0xC63E6, ships 0) against the
STALLED-WHEEL class and the command deadband, without spending the 7-9 Hz crossover margin or touching the
20 Hz creep mode.  Deep-analysis subagent, 2026-09-03.

The integral arithmetic is re-derived from the disassembly of FUN_00028ea6 this session (0x29d72-0x29dc6,
0x29f18-0x29f24, 0x2a190), NOT taken from any prior report:

    E        = 32*sp - fb                                        # 0x29d76 shl 0x5 ; 0x29d78 sub r26
    excess   = deadband(E >> 5, 0xC62E4 = 4)                     # 0x29d7c..0x29d9a, a DEADBAND on the error
    acc      = clamp(acc + ((excess * Ki) >> 3), +-0xC61BA*128)  # 0x29da8..0x29dc2, acc == gp-0x6dd0 >> 3
    I_term   = acc >> 7                                          # 0x29f18 sar 0x7   -> |I_term| <= 0xC61BA
    sum      = clamp(I_term + P + D, +-0xC61BE = 15360)          # 0x29f1e add r9 ; 0x29f24 add r8
    gp-0x6dd0 = acc << 3                                         # 0x29de4 shl 0x3, r24 ; 0x2a190 st.w

  => I_term gains  excess * Ki / 1024  per 1 ms tick, and is hard-limited at 0xC61BA = 10240,
     which is exactly two thirds of the sum clamp.  The deadband is +-4 in (E>>5), i.e. +-128 counts of E,
     i.e. +-0.52 deg/s of rate error (fb DC = 30.89 per raw count, 8 raw counts per deg/s -> 247.1 per deg/s).

Sections
  A  the PI corner frequency and the phase/magnitude cost at 7, 9 and 20 Hz, vs Kp
  B  the cost folded into the measured 7.3 Hz loop share (r24_deembed's plant-free identity)
  C  closed-loop transient: a stalled wheel that breaks free, and a driver hold that is released
  D  open-loop replay of the wind-up on r31's real stall episodes
  E  the deadband cal 0xC62E4 as a "stall-only" gate -- and why it makes the overshoot WORSE

Run:  python ki_sizing.py
"""
import os
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FS1K = 1000.0
CPD = 8.0                       # 0x18F rate wire counts per deg/s
A_FB, B_FB = 923, 1560          # 0xC63E8 / 0xC63EA
FB_DC = 2 * B_FB / (1024 - A_FB)          # 30.89 counts of fb per raw rate count
E_PER_DEGS = FB_DC * CPD                  # 247.1 counts of E per deg/s of steady rate
OA, OB = 992, 507               # 0xC63EC / 0xC63EE
GAIN = 5346                     # 0xC6CD0
KD = 128
P_CLAMP, D_CLAMP, SUM_CLAMP, OUT_CAP = 15360, 10240, 15360, 3072
I_CLAMP = 10240                 # 0xC61BA
DEADBAND = 4                    # 0xC62E4
MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
MAP_V280 = np.array([0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], float)
PLANT_K, PLANT_POLE, PLANT_DELAY = 0.382, 0.80, 0.0084     # deg/s per count, Hz, s (kit fit 1)


def sp_of(idx):
    return float(np.interp(idx, MAP_X, MAP_V280))


def ref_degs(idx):
    return 32 * sp_of(idx) / FB_DC / CPD


# ------------------------------------------------------------------------------------------------------
# A -- the PI corner and its phase cost
# ------------------------------------------------------------------------------------------------------
def pid_tf(f, kp, ki, kd=KD):
    z1 = np.exp(-2j * np.pi * f / FS1K)
    d = 1 - z1
    out = kp / 256.0 + (kd / 8.0) * d
    if ki:
        out = out + (ki / 32768.0) / d
    return out


def sec_A():
    print("=" * 150)
    print("SECTION A -- the PI corner and the phase it costs.  I gains excess*Ki/1024 per ms; P = E*Kp/256.")
    print("  |I| = |P| at  f_i = Ki * 1000 * 256 / (32768 * Kp * 2*pi)  =  1.2434 * Ki / Kp   Hz")
    print("=" * 150)
    for kp in (248, 341, 696):
        print("  Kp = %d" % kp)
        print("    %-6s %10s | %-28s | %-28s | %-28s" % ("Ki", "f_i (Hz)", "at 7 Hz: |pid| x, phase", "at 9 Hz", "at 20 Hz"))
        base = {f: pid_tf(f, kp, 0) for f in (7.0, 9.0, 20.0)}
        for ki in (0, 5, 20, 50, 100, 200, 400, 800):
            fi = 1.2434 * ki / kp
            row = "    %-6d %10.4f " % (ki, fi)
            for f in (7.0, 9.0, 20.0):
                r = pid_tf(f, kp, ki) / base[f]
                row += "| x%.4f  %+6.2f deg           " % (abs(r), np.degrees(np.angle(r)))
            print(row)
        print()


# ------------------------------------------------------------------------------------------------------
# B -- fold into the measured 7.3 Hz loop share
# ------------------------------------------------------------------------------------------------------
def sec_B():
    import r24_deembed as R
    print("=" * 150)
    print("SECTION B -- the cost in the MEASURED loop share at 7.3 Hz (r24_deembed sec.K identity:")
    print("  L_tot = kappa * L_servo + alpha * L_r24, per episode at its own f0, pooled).  alpha = 1 (r24 untouched).")
    print("=" * 150)
    gs = {t: R.load(t) for t in ("r32", "r33", "r34")}
    rows = [R.episode_row(gs[t], a, b) for t in ("r32", "r33", "r34") for a, b in R.EPIS[t]]
    print("    %-6s %-5s %-7s | %-26s | %-12s | %s" % ("Kp", "Ki", "N", "L_tot at f0 (pooled)", "|1 - L_tot|", "ring gain"))
    for N in (1.00, 0.70):
        for kp in (248, 341):
            for ki in (0, 50, 100, 200, 400):
                vals = []
                for r in rows:
                    zT = r["AT"] * np.exp(1j * np.radians(r["ph_T"]))
                    zr = r["Ar24"] * np.exp(1j * np.radians(r["ph_r24"]))
                    tot = zT + zr
                    pid_now = pid_tf(r["f0"], r["kp"] * N, 0)
                    pid_new = pid_tf(r["f0"], kp, ki)
                    vals.append((pid_new / pid_now) * (zT / tot) + (zr / tot))
                L = np.median([abs(v) for v in vals]) * np.exp(1j * np.radians(np.median([np.degrees(np.angle(v)) for v in vals])))
                print("    %-6d %-5d %-7.2f | %6.3f @ %+6.1f deg      | %12.3f | %.2f"
                      % (kp, ki, N, abs(L), np.degrees(np.angle(L)), abs(1 - L), 1 / max(abs(1 - L), 1e-3)))
            print()


# ------------------------------------------------------------------------------------------------------
# C -- closed-loop transient with Coulomb stall
# ------------------------------------------------------------------------------------------------------
def simulate(idx, kp, ki, load_hold, load_free=690.0, t_end=6.0, t_release=2.0, kd=KD, m=254.0):
    """1 kHz firmware chain closed on a CALIBRATED mechanical load:

         while |T| <= L and the wheel is stopped:   rate = 0                      (Coulomb stall)
         otherwise:  J*d(rate)/dt = T - L*sign(rate) - b*rate

       b is fixed by the measured hands-light full-demand point (T 2462 counts -> 124 deg/s at a ~690-count
       load): b = (2462 - 690)/124 = 14.3 counts per deg/s.  J = b*tau with tau = 1/(2*pi*0.80 Hz) = 0.199 s,
       the kit's identified plant pole.  Delay 8.4 ms.  Signs are taken in the loop's own frame (fb on +rate,
       T on +E), which is the same loop as the firmware's double inversion.
    """
    n = int(t_end * FS1K)
    sp = sp_of(idx)
    ref = ref_degs(idx)
    dly = int(round(PLANT_DELAY * FS1K))
    b = (2462.0 - 690.0) / 124.0
    tau = 1.0 / (2 * np.pi * PLANT_POLE)
    J = b * tau
    rate = np.zeros(n)
    Tq = np.zeros(n)
    Iq = np.zeros(n)
    s_fb = 0.0
    s_lag = 0.0
    lag_prev = 0.0
    acc = 0.0
    E_prev = None
    v = 0.0
    for k in range(n):
        raw = v * CPD
        s_new = (A_FB * s_fb) // 1024 + (B_FB * raw) // 1024
        fb = np.clip(s_fb + s_new, -46080, 46080)
        s_fb = s_new
        E = 32 * sp - fb
        ex = np.sign(E / 32.0) * max(abs(E / 32.0) - DEADBAND, 0.0)
        acc = np.clip(acc + np.trunc(ex * ki / 8.0), -I_CLAMP * 128, I_CLAMP * 128)
        I = np.trunc(acc / 128.0)
        P = np.clip(np.trunc(E * kp / 256.0), -P_CLAMP, P_CLAMP)
        dE = 0.0 if E_prev is None else E - E_prev
        E_prev = E
        D = np.clip(np.trunc(dE * kd / 8.0), -D_CLAMP, D_CLAMP)
        S = np.clip(I + P + D, -SUM_CLAMP, SUM_CLAMP)
        S = np.trunc(m * S / 256.0)
        s_lag = (OA * s_lag + OB * S) / 1024.0
        lag = (lag_prev + s_lag) / 32.0
        lag_prev = s_lag
        T = float(np.clip(np.trunc(lag * GAIN / 32768.0), -OUT_CAP, OUT_CAP))
        Tq[k], Iq[k], rate[k] = T, I, v
        L = load_hold if k < t_release * FS1K else load_free
        Td = Tq[max(k - dly, 0)]
        if v == 0.0 and abs(Td) <= L:
            v = 0.0
        else:
            sgn = np.sign(v) if v != 0 else np.sign(Td)
            v = v + (Td - L * sgn - b * v) / J / FS1K
            if v * sgn < 0:
                v = 0.0
    return dict(rate=rate, T=Tq, I=Iq, ref=ref, t=np.arange(n) / FS1K)


def sec_C():
    print("=" * 150)
    print("SECTION C -- closed-loop transient: a wheel held at a Coulomb break-away torque, then released at t = 2 s.")
    print("  Plant calibrated to the measured hands-light full-demand point: b = 14.3 counts per deg/s, tau = 0.199 s,")
    print("  Coulomb break-away L, delay 8.4 ms.  A MODEL, not a measurement: the stall is an ideal Coulomb threshold. [BELIEF]")
    print("=" * 150)
    for idx, brk, lab in ((26, 690, "idx 26 (ref 14.5 deg/s), ORDINARY road load 690 ct -- the COMMAND DEADBAND case"),
                          (58, 2000, "idx 58 (ref 32.3 deg/s), stiff stall: 2000-count break-away, released at t = 2 s"),
                          (60, 2600, "idx 60 (ref 33.4 deg/s), DRIVER HOLDING at 2600 ct -- the window where P alone does NOT rail"),
                          (120, 2600, "idx 120 (ref 60.7 deg/s), DRIVER HOLDING at 2600 ct -- P alone already rails the output")):
        print()
        print("  --- %s ---" % lab)
        print("    %-6s %-5s | %8s %9s | %10s %10s %9s | %s"
              % ("Kp", "Ki", "T stall", "rate stall", "t to rail", "peak rate", "overshoot", "time above ref after release"))
        for kp in (696, 248):
            for ki in (0, 5, 20, 50, 100, 200):
                r = simulate(idx, kp, ki, brk)
                pre = slice(int(1.5 * FS1K), int(2.0 * FS1K))
                post = slice(int(2.0 * FS1K), int(6.0 * FS1K))
                Tst = np.median(np.abs(r["T"][pre]))
                rst = np.median(r["rate"][pre])
                railed = np.abs(r["I"][:int(2 * FS1K)]) >= I_CLAMP - 1
                t_rail = np.argmax(railed) / FS1K if railed.any() else np.nan
                pk = np.max(np.abs(r["rate"][post]))
                over = pk - r["ref"]
                above = np.mean(np.abs(r["rate"][post]) > r["ref"] * 1.05) * 4.0
                print("    %-6d %-5d | %8.0f %9.1f | %10s %10.1f %9.1f | %.2f s"
                      % (kp, ki, Tst, rst, ("%.2f s" % t_rail) if np.isfinite(t_rail) else "  never",
                         pk, over, above))
            print()


# ------------------------------------------------------------------------------------------------------
# D -- open-loop wind-up replay on r31's real stall episodes
# ------------------------------------------------------------------------------------------------------
def sec_D():
    import r24_deembed as R
    import numpy as _np
    print("=" * 150)
    print("SECTION D -- open-loop wind-up on r31's real stall episodes (V278 rev 3, the r31 stutter class).")
    print("  E is computed from the MEASURED rate, so this bounds the wind-up; it cannot show the overshoot")
    print("  (the recorded rate is what happened WITHOUT the integrator).")
    print("=" * 150)
    R.EPIS["r31"] = [(158.1, 1.5), (217.1, 2.4), (221.5, 1.7), (266.2, 2.8), (303.7, 1.4), (312.7, 2.3),
                     (381.9, 3.2), (411.3, 3.0), (537.0, 2.1), (546.6, 2.0)]
    try:
        g = R.load("r31")
    except Exception as e:                                     # noqa: BLE001
        print("  r31 cache unavailable (%s) -- section skipped." % e)
        return
    idxs = R.demand_idx(g["cmd"], g["bar"])
    print("    %-8s %-5s %-8s %-9s | %s" % ("t0", "dur", "idx p50", "E p50", "I_term reached at Ki = 5 / 20 / 50 / 100 / 200 (clamp 10240)"))
    for t0, dur in R.EPIS["r31"]:
        s, e = int(t0 * 100), int((t0 + dur) * 100)
        if e > len(g["rate"]):
            continue
        idx = float(_np.median(idxs[s:e]))
        rate = g["rate"][s:e]
        E = 32 * sp_of(idx) - FB_DC * rate                     # steady-state fb approximation
        ex = _np.sign(E / 32) * _np.maximum(_np.abs(E / 32) - DEADBAND, 0)
        out = []
        for ki in (5, 20, 50, 100, 200):
            I = float(_np.clip(_np.cumsum(ex * ki / 1024.0)[-1] * 10, 0, I_CLAMP))   # 100 Hz samples -> 10 ms each
            out.append("%6.0f" % I)
        print("    %-8.1f %-5.1f %-8.0f %-9.0f | %s" % (t0, dur, idx, _np.median(E), "  ".join(out)))


def sec_E():
    print()
    print("=" * 150)
    print("SECTION E -- the deadband cal 0xC62E4 as a 'stall only' gate")
    print("=" * 150)
    print("    %-10s %-14s %-16s %s" % ("0xC62E4", "deadband in E", "deadband in deg/s", "note"))
    for db in (4, 16, 32, 64, 96, 128):
        print("    %-10d %-14d %-16.2f %s" % (db, db * 32, db * 32 / E_PER_DEGS,
              "SHIPPED -- a noise gate" if db == 4 else "would make the integrator stall-only"))
    print()
    print("    Steady tracking error the loop already runs at (kpflat sec.3, flat 295): 12.9-22.9 deg/s in a loaded")
    print("    turn.  A deadband big enough to exclude ordinary tracking (>= 64) is also big enough that the wound")
    print("    integrator will NOT unwind until the wheel overshoots the reference by that same amount -- so a large")
    print("    deadband makes the break-free lurch WORSE, not better.  Keep 0xC62E4 = 4.")


if __name__ == "__main__":
    sec_A()
    sec_B()
    sec_C()
    sec_D()
    sec_E()
