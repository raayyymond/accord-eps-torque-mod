# -*- coding: utf-8 -*-
"""V278 dose sizing: the SIGN of the LKAS rate-loop error E, frame by frame on the V276 drive, per K.

E = 32*setpoint - feedback  (0x29D78, `sub r26,r16` after `shl 0x5`).  E > 0 the lane PUSHES,
E < 0 the lane DAMPS.  V276 scaled the reference x6 so E never went negative; V278 backs it to K.
This script recomputes E from the operator's own 0x18F/0xE4 frames with the COMMAND-DEPENDENT
setpoint (not the map ceiling) at each candidate K.

EVERY arithmetic line below mirrors the stock decompile/disassembly of FUN_00028ea6 (code.bin):

  demand index (gp-0x674b), 0x29A80..0x29CFA:
    S      = clamp(-4*cmd, +-LIMIT)          LIMIT = LERP(0xCB844[sel] by speed) = 15360 flat, slot 7
    taper  = LERP(shape A: X 70,72,78,80  Y 254,234,12,0 ; index |tq_raw| >> 5)   (0xCBA04/0xCBA74)
    speedF = LERP(0xC6976: X 4,6,8,10  Y 255,255,255,255) = 255 flat
    v      = ((taper*speedF) & 0xFFFF) * S >> 16          (signed, 0x29CE0-ish)
    v      = clamp(v >> 6, -0xC64F1, +0xC64F0) = clamp(v>>6, -240, 240)
    index  = |v|  -> st.b gp-0x674b                     (`subr r0,r7` @0x29CFA discards the sign)
  setpoint (gp-0x6a32) = sign(v) * LERP(map slot 7 @0xE502C, index) * K       [K = the V278 dose]
  feedback, 0x28F7C..0x28FBC (ASSEMBLY-CONFIRMED this session):
    s_new  = (923*s_old >> 10) + (1560*x >> 10)         x = gp-0x6a56 (raw rate), 0xC63E8/0xC63EA
    fb     = s_old + s_new                              `add r9,r26` @0x28FA4  <-- TWO-SAMPLE SUM
    fb     = clamp(fb, +-0xC62E6) = +-7680*K            ld.hu @0x28F96/0x28F9C/0x28FB8
    store  s_new -> gp-0x3d30                           `st.w r9,-0x3d30[gp]` @0x28FA8
    => DC gain of fb is 2*1560/101 = 30.89 per raw count, NOT 15.45.  Corner 16.5 Hz at 1 kHz.
  E = 32*setpoint - fb                                  0x29D76 shl 0x5 / 0x29D78 sub

Wire: 0x18F b2-3 = -gp-0x6a56 exactly (sibling, bytes); measured here 7.94 counts per deg/s of the
0x14A angle derivative (corr 0.997), so raw = 8 counts/deg/s.  0xE4 b0-1 = cmd (src 129).

Run:  python dose_e_sign_by_k.py            (uses _direct_read_v276.npz from direct_read_v276.py)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
FS = 100.0
KS = (1.0, 1.5, 2.0, 2.5, 3.0, 6.0)

MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
MAP_Y = np.array([0, 24, 42, 50, 62, 100, 126, 154, 166, 172], float)     # slot 7, record 0xE502C
TAPER_X = np.array([70, 72, 78, 80], float)
TAPER_Y = np.array([254, 234, 12, 0], float)                                # shape A (the cliff)
SPEED_F = 255                                                                # 0xC6976 Y, flat
LIMIT = 15360                                                                # 0xCB844[7] Y, flat
IDX_CLAMP = 240                                                              # 0xC64F0 / 0xC64F1
A_COEF, B_COEF = 923, 1560                                                   # 0xC63E8 / 0xC63EA
FB_CLAMP_STOCK = 7680                                                        # 0xC62E6
FB_DC = 2 * B_COEF / (1024 - A_COEF)                                         # 30.89 per raw count
COUNTS_PER_DEGS = 8.0


def lerp_u16(x_knots, y_knots, u):
    """Firmware LERP: below X0 -> Y0, at/above Xlast -> Ylast, integer division inside."""
    u = np.asarray(u, float)
    return np.interp(u, x_knots, y_knots)   # knots are monotone; integer truncation ignored (<1 count)


def demand_index_and_sign(cmd, tq_raw, apply_taper=True):
    """gp-0x674b and the sign that multiplies the map output, per frame."""
    S = np.clip(-4.0 * np.round(cmd), -LIMIT, LIMIT)
    if apply_taper:
        taper = lerp_u16(TAPER_X, TAPER_Y, np.abs(tq_raw) // 32)
    else:
        taper = np.full_like(S, 254.0)
    prod = (taper * SPEED_F).astype(np.int64) & 0xFFFF
    v = np.floor(prod * S / 65536.0)             # arithmetic >>16 on a signed product
    v = np.floor(v / 64.0)                       # sar 6
    v = np.clip(v, -IDX_CLAMP, IDX_CLAMP)
    sign = np.where(v < 0, -1.0, 1.0)            # bVar4 = (v < 0); sign = !bVar4 - bVar4
    return np.abs(v), sign, taper


def feedback_1khz(x100):
    """Run the 1 kHz IIR on linearly interpolated 100 Hz raw-rate samples; return fb (unclamped) at 100 Hz.
    fb = s_old + s_new.  Clamp applied by the caller (it is K-dependent)."""
    n = len(x100)
    t100 = np.arange(n) / FS
    t1k = np.arange(0, n / FS, 1e-3)
    x1k = np.interp(t1k, t100, x100)
    s = 0.0
    fb = np.empty_like(x1k)
    for i, xv in enumerate(x1k):
        s_new = (A_COEF * s) // 1024 + (B_COEF * xv) // 1024   # floor == sar on negatives
        fb[i] = s + s_new
        s = s_new
    # sample back to the 100 Hz grid (value at the tick nearest each 100 Hz sample)
    return np.interp(t100, t1k, fb)


def main():
    D = dict(np.load(os.path.join(HERE, "_direct_read_v276.npz")))
    t0 = D["t18"][0]
    T = D["t18"] - t0
    tg = np.arange(0.0, T[-1], 1 / FS)
    wire = np.interp(tg, T, D["rate"])                       # 0x18F b2-3, wire counts
    tq_raw = np.interp(tg, T, D["tq"] * 1.024)
    sca = np.interp(tg, T, D["sca"]) > 0.5
    req = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    cmd = np.interp(tg, D["te4"] - t0, D["cmd"])
    ang = np.interp(tg, D["t14"] - t0, D["ang"])
    eng = sca & req

    # ---- wire units: 0x18F rate vs d/dt of the 0x14A angle -----------------------------------------
    sos5 = signal.butter(2, 5, fs=FS, output="sos")
    dang = np.gradient(signal.sosfiltfilt(sos5, ang), 1 / FS)
    ws = signal.sosfiltfilt(sos5, wire)
    m = np.abs(dang) > 5
    slope = np.polyfit(dang[m], ws[m], 1)[0]
    print("UNITS: 0x18F rate = %.3f x d(0x14A angle)/dt  (corr %.3f, n=%d)  => %.2f counts/deg/s"
          % (slope, np.corrcoef(dang[m], ws[m])[0, 1], m.sum(), abs(slope)))

    # ---- episodes, same criterion as direct_read_v276.py -------------------------------------------
    sos = signal.butter(4, [2.5, 6.0], btype="bandpass", fs=FS, output="sos")   # pass-2 band (the 3.9 Hz mode)
    rb = signal.sosfiltfilt(sos, wire)
    env = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb)))
    thr = max(2.5 * np.percentile(env[~eng], 95), 150.0)
    on = (env > thr) & eng
    edges = np.diff(np.r_[0, on.astype(int), 0])
    eps = [(s, e) for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]) if (e - s) / FS >= 1.0]
    merged = []
    for s, e in eps:
        if merged and s - merged[-1][1] < FS:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    osc = np.zeros_like(eng)
    for s, e in merged:
        osc[s:e] = True
    normal = eng & ~osc
    print("episodes: %d, %.1f s oscillating; normal engaged %.1f s; threshold %.0f wire" %
          (len(merged), osc.sum() / FS, normal.sum() / FS, thr))
    pk, _ = signal.find_peaks(np.abs(wire) * osc, distance=int(0.12 * FS), height=thr / 2)
    print("half-cycle peaks in episodes: n=%d, |wire| p50 %.0f p90 %.0f (%.1f / %.1f deg/s)"
          % (len(pk), np.median(np.abs(wire[pk])), np.percentile(np.abs(wire[pk]), 90),
             np.median(np.abs(wire[pk])) / COUNTS_PER_DEGS, np.percentile(np.abs(wire[pk]), 90) / COUNTS_PER_DEGS))
    cmd_med_osc = np.median(np.abs(cmd[osc]))
    cmd_med_norm = np.median(np.abs(cmd[normal]))
    print("|cmd| median: oscillating %.0f, normal engaged %.0f (p90 %.0f)" %
          (cmd_med_osc, cmd_med_norm, np.percentile(np.abs(cmd[normal]), 90)))

    # ---- the firmware chain --------------------------------------------------------------------------
    x_raw = -wire                                            # gp-0x6a56 = -(0x18F b2-3)
    fb_unclamped = feedback_1khz(x_raw)
    idx, sgn, taper = demand_index_and_sign(cmd, tq_raw, apply_taper=True)
    idx_nt, sgn_nt, _ = demand_index_and_sign(cmd, tq_raw, apply_taper=False)
    y = lerp_u16(MAP_X, MAP_Y, idx)
    y_nt = lerp_u16(MAP_X, MAP_Y, idx_nt)
    past_knee = taper < 254
    print("frames past the taper knee (|tq_raw| >= 2240): oscillating %.1f%%, normal %.1f%%"
          % (100 * past_knee[osc].mean(), 100 * past_knee[normal].mean()))
    print("demand index: oscillating p50 %.0f p90 %.0f; normal p50 %.0f p90 %.0f  (ceiling 240)"
          % (np.median(idx[osc]), np.percentile(idx[osc], 90), np.median(idx[normal]), np.percentile(idx[normal], 90)))

    # polarity check: in normal engaged driving with a real command the wheel moves WITH the setpoint
    strong = normal & (np.abs(cmd) > 300) & (np.abs(fb_unclamped) > 200)
    agree = (np.sign(sgn[strong]) == np.sign(fb_unclamped[strong])).mean()
    print("POLARITY: sign(setpoint) == sign(feedback) on %.1f%% of strong normal frames (n=%d) -- expect >50%%"
          % (100 * agree, strong.sum()))
    if agree < 0.5:
        print("  !! polarity FAILS under the derived convention -- results below would be sign-inverted")

    def stats(K, mask, use_nt=False):
        sp = (sgn_nt * y_nt if use_nt else sgn * y) * K
        fb = np.clip(fb_unclamped, -FB_CLAMP_STOCK * K, FB_CLAMP_STOCK * K)
        E = 32 * sp - fb
        fneg = (E[mask] < 0).mean()
        mm = mask & (fb != 0)
        fopp = (np.sign(E[mm]) != np.sign(fb[mm])).mean()
        fdom = (np.abs(fb[mask]) > 32 * np.abs(sp[mask])).mean()     # feedback dominates: pure damper
        return fneg, fopp, E, fb, fdom, sp

    print("\n%-5s | %-25s | %-25s | %-27s | %s" % ("K", "OSC frames", "NORMAL engaged frames", "half-cycle PEAKS", "ceiling @ |cmd| med osc"))
    print("%-5s | %-12s %-12s | %-12s %-12s | %-13s %-13s | %s" % ("", "E<0", "E opp fb", "E<0", "E opp fb", "E<0 at pk", "E opp fb pk", "raw / deg/s (idx, Y)"))
    rows = []
    for K in KS:
        fneg_o, fopp_o, E, fb, fdom_o, sp = stats(K, osc)
        fneg_n, fopp_n, _, _, fdom_n, _ = stats(K, normal)
        pk_neg = (E[pk] < 0).mean()
        pk_opp = (np.sign(E[pk]) != np.sign(fb[pk])).mean()
        pk_dom = (np.abs(fb[pk]) > 32 * np.abs(sp[pk])).mean()
        i_med = np.abs(np.clip(np.floor(64770 * np.clip(-4 * cmd_med_osc, -LIMIT, LIMIT) / 65536 / 64), -240, 240))
        Y_med = lerp_u16(MAP_X, MAP_Y, i_med)
        x_cross = 32 * K * Y_med / FB_DC
        x_ceil = 32 * K * 172 / FB_DC
        rows.append((K, fneg_o, fopp_o, fneg_n, fopp_n, pk_neg, pk_opp, x_cross))
        print("%-5.1f | %-10.3f %-10.3f %-10.3f | %-10.3f %-10.3f %-10.3f | %-10.3f %-10.3f %-10.3f | %4.0f / %5.1f  (idx %3.0f, Y %3.0f)   [map ceiling: %4.0f / %4.1f]"
              % (K, fneg_o, fopp_o, fdom_o, fneg_n, fopp_n, fdom_n, pk_neg, pk_opp, pk_dom, x_cross, x_cross / COUNTS_PER_DEGS, i_med, Y_med, x_ceil, x_ceil / COUNTS_PER_DEGS))

    # sensitivity: taper ignored
    print("\nSENSITIVITY (taper ignored, factor 254 everywhere):")
    for K in KS:
        fneg_o, fopp_o, E, fb, _, _ = stats(K, osc, use_nt=True)
        fneg_n, fopp_n, _, _, _, _ = stats(K, normal, use_nt=True)
        print("  K=%.1f osc E<0 %.3f opp %.3f | normal E<0 %.3f opp %.3f | peaks E<0 %.3f" %
              (K, fneg_o, fopp_o, fneg_n, fopp_n, (E[pk] < 0).mean()))
    # sensitivity: alternative mapping index = |cmd| >> 4 (no 0.988 factor) and index = |cmd| >> 5
    print("\nSENSITIVITY (alternative index mappings, taper ignored):")
    for name, idx_alt in (("|cmd|>>4", np.minimum(np.abs(cmd) // 16, 240)), ("|cmd|>>5", np.minimum(np.abs(cmd) // 32, 240))):
        y_alt = lerp_u16(MAP_X, MAP_Y, idx_alt)
        for K in KS:
            sp = -np.sign(cmd) * y_alt * K
            fb = np.clip(fb_unclamped, -FB_CLAMP_STOCK * K, FB_CLAMP_STOCK * K)
            E = 32 * sp - fb
            print("  %-8s K=%.1f osc E<0 %.3f | normal E<0 %.3f | peaks E<0 %.3f" %
                  (name, K, (E[osc] < 0).mean(), (E[normal] < 0).mean(), (E[pk] < 0).mean()))
    # sensitivity: single-state feedback (the sibling's fb = s, DC 15.45) -- what the V278 docstring assumed
    print("\nSENSITIVITY (fb = s_new only, DC 15.45 -- the reading the V278 docstring table used):")
    for K in KS:
        sp = sgn * y * K
        fb = np.clip(fb_unclamped / 2.0, -FB_CLAMP_STOCK * K, FB_CLAMP_STOCK * K)
        E = 32 * sp - fb
        print("  K=%.1f osc E<0 %.3f | normal E<0 %.3f | peaks E<0 %.3f" % (K, (E[osc] < 0).mean(), (E[normal] < 0).mean(), (E[pk] < 0).mean()))

    # per-episode detail at K=2 and K=1.5
    print("\nPER-EPISODE peaks E<0 fraction:")
    print("%3s %7s %5s %7s %7s | " % ("#", "start", "dur", "|cmd|50", "pk|w|50") + " ".join("K=%.1f" % K for K in KS))
    for k, (s, e) in enumerate(merged):
        pkm = pk[(pk >= s) & (pk < e)]
        line = "%3d %7.1f %5.1f %7.0f %7.0f | " % (k, tg[s], (e - s) / FS, np.median(np.abs(cmd[s:e])), np.median(np.abs(wire[pkm])) if len(pkm) else 0)
        for K in KS:
            _, _, E, fb, _, sp = stats(K, osc)
            line += "%5.2f " % ((np.abs(fb[pkm]) > 32 * np.abs(sp[pkm])).mean() if len(pkm) else np.nan)
        print(line)


if __name__ == "__main__":
    main()
