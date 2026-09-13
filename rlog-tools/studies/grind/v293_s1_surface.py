# -*- coding: utf-8 -*-
"""v293_s1_surface.py -- DELIVERABLE 1: the delivered torque surface, byte-exact, read from the IMAGES.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

    T(idx) for V293 (torque mode, fb == 0) and for V282
      - V282 at fb = 0   (the like-for-like comparison: same command, no wheel motion)
      - V282 at the wheel-rate operating points of the operator's recorded STALLS
        (10-20 deg/s achieved against a 36-45 deg/s reference)
    with the post-PID fade, the peak, the counts per idx, and the +-x1.00 check on the peak.

POSITIVE CONTROLS, run before any V293 number is printed:
  C1  V282 peak forward torque from the image cells == 2505 (the record's published number)
  C2  stock  peak == 417
  C3  P = 64*idx exactly at Kp 256 / sp = 2*idx (V279's published identity)
  C4  the closed-form output-lag DC == 0.990234375 (the record's dc_held_lag)
  C5  `surface` (closed form) == `surface_march` (byte-exact tick march to steady state)
Run: python v293_s1_surface.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v293_lib as L                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


CPD = 8.0        # raw 0x18F wire counts per deg/s
FADE = 254       # the live post-PID multiplier m with no driver torque (0xCBBC4 arm, |bar| = 0)


def main():
    c282 = L.read_cells(L.IMG282)
    c292 = L.read_cells(L.IMG292)
    c279 = L.read_cells(L.IMG279)

    pr("=" * 118)
    pr("V293 TORQUE MODE -- THE DELIVERED SURFACE, BYTE-EXACT FROM THE IMAGES        tmdesign 2026-09-13")
    pr("=" * 118)
    pr("V282 image : %s" % os.path.basename(c282["img"]))
    pr("V292 image : %s" % os.path.basename(c292["img"]))
    pr("V279r2 img : %s" % os.path.basename(c279["img"]))
    pr("")
    pr("%-14s %10s %10s %10s   what" % ("cell", "V282", "V292", "V279r2"))
    for k, nm in (("fb_clamp", "0xC62E6 feedback saturation clamp"),
                  ("fb_a", "0xC63E8 fb lag a"), ("fb_b", "0xC63EA fb lag b"),
                  ("lag_a", "0xC63EC out lag a"), ("lag_b", "0xC63EE out lag b"),
                  ("gain", "forward LKAS gain (0xC6CD0 via 0x2A1F0)"),
                  ("p_clamp", "0xC61BC P clamp"), ("sum_clamp", "0xC61BE sum clamp"),
                  ("d_clamp", "0xC61B6 D clamp"), ("t_clamp", "0xC61B4 output clamp"),
                  ("pre_clamp", "0xC61B2 pre-gain clamp"), ("ki", "0xC63E6 Ki"),
                  ("r24_arm", "0xC6446 r24 engaged arm"), ("r24_honda", "0xC6440 Honda arm"),
                  ("r24_dead", "0xC61F6 r24 deadband")):
        pr("%-14s %10s %10s %10s   %s" % (k, c282[k], c292[k], c279[k], nm))
    pr("%-14s %10s %10s %10s   Kp bank (record slot 7)" % ("kp_Y", c282["kp_Y"], c292["kp_Y"], c279["kp_Y"]))
    pr("%-14s %10s %10s %10s   Kd bank" % ("kd_Y", c282["kd_Y"], c292["kd_Y"], c279["kd_Y"]))
    pr("map_X  V282 %s" % np.asarray(c282["map_X"], int).tolist())
    pr("map_Y  V282 %s" % np.asarray(c282["map_Y"], int).tolist())
    pr("map_Y  V279 %s" % np.asarray(c279["map_Y"], int).tolist())
    pr("kp_X   V282 %s" % np.asarray(c282["kp_X"], int).tolist())
    pr("")

    # ---------------------------------------------------------------- POSITIVE CONTROLS
    pr("-" * 118)
    pr("POSITIVE CONTROLS")
    pr("-" * 118)
    pk282 = min((c282["sum_clamp"] * c282["gain"]) >> 15, c282["t_clamp"])
    pk_stock = min((15360 * 891) >> 15, 512)
    ok1 = (pk282 == 2505)
    ok2 = (pk_stock == 417)
    pr("C1 V282 peak = min((sum_clamp %d * gain %d)>>15, t_clamp %d) = %d   (record: 2505)  %s"
       % (c282["sum_clamp"], c282["gain"], c282["t_clamp"], pk282, "PASS" if ok1 else "FAIL"))
    pr("C2 stock peak = min((15360*891)>>15, 512) = %d   (record: 417)  %s" % (pk_stock, "PASS" if ok2 else "FAIL"))
    ii = np.arange(0, 241)
    P_id = np.floor(32.0 * (2.0 * ii) * 256.0 / 256.0)
    ok3 = bool(np.all(P_id == 64.0 * ii)) and P_id[-1] == 15360
    pr("C3 P = (32*sp*Kp)>>8 with Kp 256, sp = 2*idx  ->  64*idx for all idx 0..240, P(240) = %d  %s"
       % (int(P_id[-1]), "PASS" if ok3 else "FAIL"))
    dclag = 2.0 * c282["lag_b"] / ((1024.0 - c282["lag_a"]) * 32.0)
    ok4 = abs(dclag - 0.990234375) < 1e-9
    pr("C4 output-lag DC = 2*%d/((1024-%d)*32) = %.9f   (record dc_held_lag 0.990234375)  %s"
       % (c282["lag_b"], c282["lag_a"], dclag, "PASS" if ok4 else "FAIL"))

    # C5 -- the closed-form surface against a byte-exact tick march
    tm = L.torque_mode(c282, kp=119)
    probe = np.array([0, 12, 24, 48, 96, 160, 200, 240], float)
    sc = L.surface(tm, probe, fb=0.0, fade=FADE)["T"]
    sm = L.surface_march(tm, probe, fb=0.0, kd=0, fade=FADE)
    ok5 = bool(np.all(np.abs(np.abs(sc) - sm) <= 1.0))
    pr("C5 closed form vs byte-exact march (V293 Kp 119), idx %s" % probe.astype(int).tolist())
    pr("       closed  %s" % np.abs(sc).astype(int).tolist())
    pr("       march   %s   max|diff| %.0f  %s"
       % (sm.astype(int).tolist(), float(np.max(np.abs(np.abs(sc) - sm))), "PASS" if ok5 else "FAIL"))
    sc0 = L.surface(c282, probe, fb=0.0, fade=FADE)["T"]
    sm0 = L.surface_march(c282, probe, fb=0.0, kd=128, fade=FADE)
    pr("   same control on V282 at fb=0:  closed %s  march %s  max|diff| %.0f"
       % (np.abs(sc0).astype(int).tolist(), sm0.astype(int).tolist(),
          float(np.max(np.abs(np.abs(sc0) - sm0)))))
    if not (ok1 and ok2 and ok3 and ok4 and ok5):
        pr("")
        pr("!!! A POSITIVE CONTROL FAILED -- nothing below is reportable.")
        return

    # ---------------------------------------------------------------- THE Kp DERIVATION
    pr("")
    pr("-" * 118)
    pr("WHY Kp 119 -- the rail point of the torque-mode surface, integer by integer")
    pr("-" * 118)
    sp_top = float(np.max(c282["map_Y"]))
    pr("map top sp = %.0f counts (idx 240).   P = (32*sp*Kp)>>8 ; P clamp = %d" % (sp_top, c282["p_clamp"]))
    pr("%6s %12s %12s %10s %10s %12s" % ("Kp", "P at idx240", "clips?", "sp_rail", "idx_rail", "0xE4 rail"))
    for kp in (119, 120, 130, 160, 200, 248, 256, 300):
        Ptop = int((32 * int(sp_top) * kp) >> 8)
        sp_rail = c282["p_clamp"] * 256.0 / (32.0 * kp)
        idx_rail = float(np.interp(min(sp_rail, sp_top), c282["map_Y"], c282["map_X"]))
        wire_rail = idx_rail * 16.125736
        pr("%6d %12d %12s %10.1f %10.1f %12.0f  (%.1f %% of 4096)"
           % (kp, Ptop, "YES" if Ptop > c282["p_clamp"] else "no", sp_rail,
              idx_rail if sp_rail < sp_top else 240.0,
              wire_rail if sp_rail < sp_top else 240 * 16.125736,
              100.0 * (wire_rail if sp_rail < sp_top else 240 * 16.125736) / 4096.0))

    # ---------------------------------------------------------------- THE SURFACE
    pr("")
    pr("=" * 118)
    pr("THE DELIVERED SURFACE  T(idx), counts at the 427 tap, fade m = %d (no driver torque)" % FADE)
    pr("=" * 118)
    idx = np.array([0, 6, 12, 20, 24, 32, 48, 64, 80, 96, 112, 115, 128, 160, 192, 208, 224, 240], float)

    # V282 at the recorded stall operating points: achieved wheel rate 10-20 deg/s while the reference
    # asks 36-45 deg/s.  fb = DC_fb * (rate_degs * CPD) with DC_fb = 2*b/(1024-a).
    dcfb = 2.0 * c282["fb_b"] / (1024.0 - c282["fb_a"])
    rows = []
    rows.append(("V293  torque mode, Kp 119, fb == 0", L.surface(tm, idx, 0.0, fade=FADE)["T"], None))
    tm248 = L.torque_mode(c282, kp=248)
    rows.append(("V293' torque mode, Kp 248, fb == 0", L.surface(tm248, idx, 0.0, fade=FADE)["T"], None))
    rows.append(("V282  Kp 248, fb = 0 (wheel still)", L.surface(c282, idx, 0.0, fade=FADE)["T"], None))
    for rate in (10.0, 15.0, 20.0, 30.0, 45.0):
        fb = dcfb * rate * CPD
        rows.append(("V282  Kp 248, wheel %4.0f deg/s (fb %6.0f)" % (rate, fb),
                     L.surface(c282, idx, fb, fade=FADE)["T"], rate))
    pr("%-40s %s" % ("idx ->", " ".join("%6d" % i for i in idx.astype(int))))
    sp = np.interp(idx, c282["map_X"], c282["map_Y"])
    pr("%-40s %s" % ("setpoint sp (counts)", " ".join("%6.0f" % s for s in sp)))
    pr("%-40s %s" % ("reference rate (deg/s) = sp/CPD", " ".join("%6.1f" % (s / CPD) for s in sp)))
    pr("%-40s %s" % ("0xE4 command (of 4096)", " ".join("%6.0f" % (i * 16.125736) for i in idx)))
    pr("-" * 118)
    for lab, T, _ in rows:
        pr("%-40s %s" % (lab, " ".join("%6.0f" % abs(t) for t in T)))
    pr("-" * 118)
    T293 = np.abs(rows[0][1])
    T282_0 = np.abs(rows[2][1])
    with np.errstate(divide="ignore", invalid="ignore"):
        rat = np.where(T282_0 > 0, T293 / np.maximum(T282_0, 1e-9), np.nan)
    pr("%-40s %s" % ("V293 / V282(fb=0)", " ".join(("%6.2f" % r) if np.isfinite(r) else "     -" for r in rat)))
    pr("")
    pr("PEAK, read from the built-image cells:")
    pr("   V282  peak |T| over idx 0..240 at fb = 0 : %6.0f   (structural ceiling %d)" % (T282_0.max(), pk282))
    pr("   V293  peak |T| over idx 0..240 at fb = 0 : %6.0f   ratio x%.4f" % (T293.max(), T293.max() / T282_0.max()))
    pr("   V292  peak (cells identical to V282 on gain/clamps) : %d" %
       min((c292["sum_clamp"] * c292["gain"]) >> 15, c292["t_clamp"]))
    pr("")

    # ---- the fade, read from the image, applied to the peak ------------------------------------
    pr("-" * 118)
    pr("THE POST-PID FADE 0xCBBC4 (live arm, record slot %d) -- the only thing that backs the lane off" % L.SEL)
    pr("-" * 118)
    fx, fy = c282["fadeB"]
    pr("   X (|bar|>>5) %s" % np.asarray(fx, float).tolist())
    pr("   Y            %s" % np.asarray(fy, float).tolist())
    pr("%10s %10s %12s %12s %12s" % ("|bar| raw", "|bar| Nm*", "m = (255B)>>8", "V293 peak T", "V282 peak T"))
    for bar in (0, 200, 400, 800, 1200, 1600, 2000, 2400, 3000, 3600):
        B = float(np.interp(bar // 32, fx, fy))
        m = (int(255.0 * B) & 0xFFFF) >> 8
        t93 = float(np.abs(L.surface(tm, np.array([240.0]), 0.0, fade=m)["T"][0]))
        t82 = float(np.abs(L.surface(c282, np.array([240.0]), 0.0, fade=m)["T"][0]))
        pr("%10d %10.2f %12d %12.0f %12.0f" % (bar, bar / 1.024 / 100.0, m, t93, t82))
    pr("   * |bar| Nm is indicative only: wire torque = raw x 1.024, and the raw-to-Nm scale is the")
    pr("     record's, not re-derived here.  The COLUMN THAT MATTERS is m: the fade is the same LERP on")
    pr("     both builds, so it multiplies both surfaces identically.")

    # ---- what the peak means as a physical push ----------------------------------------------
    pr("")
    pr("-" * 118)
    pr("WHAT THE DRIVER FEELS INSTEAD OF A SERVO: a CONSTANT push at f(cmd), through the fade")
    pr("-" * 118)
    pr("V282 nulls: at a steady wheel rate r the feedback subtracts %0.3f*CPD = %.2f counts of E per deg/s," % (dcfb, dcfb * CPD))
    pr("            so the lane backs off to zero once the wheel reaches the reference rate.")
    pr("V293 does not null: T depends ONLY on the command and the driver's bar torque.")
    pr("%8s %10s %12s %12s %12s %12s" % ("idx", "ref deg/s", "V293 T", "V282 T @ref", "V282 T @0", "null rate"))
    for i in (12, 24, 48, 96, 160, 240):
        spv = float(np.interp(i, c282["map_X"], c282["map_Y"]))
        ref = spv / CPD
        t93 = float(abs(L.surface(tm, np.array([float(i)]), 0.0, fade=FADE)["T"][0]))
        t82r = float(abs(L.surface(c282, np.array([float(i)]), dcfb * ref * CPD, fade=FADE)["T"][0]))
        t82z = float(abs(L.surface(c282, np.array([float(i)]), 0.0, fade=FADE)["T"][0]))
        # V282's null rate: where 32*sp = fb  =>  rate = 32*sp/(dcfb*CPD)
        nullr = 32.0 * spv / (dcfb * CPD)
        pr("%8d %10.1f %12.0f %12.0f %12.0f %12.1f" % (i, ref, t93, t82r, t82z, nullr))
    pr("   'null rate' = the wheel rate at which V282's error crosses zero = 32*sp/(DC_fb*CPD) deg/s.")
    pr("   DC_fb = 2*%d/(1024-%d) = %.4f counts of fb per raw rate count." % (c282["fb_b"], c282["fb_a"], dcfb))
    pr("   NOTE the null rate is 32/DC_fb = %.2f x the reference rate -- Honda's setpoint:feedback ratio." % (32.0 / dcfb))

    scr = os.path.join(HERE, "_scratch")
    os.makedirs(scr, exist_ok=True)
    open(os.path.join(scr, "v293_s1_surface.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s1_surface.txt")


if __name__ == "__main__":
    main()
