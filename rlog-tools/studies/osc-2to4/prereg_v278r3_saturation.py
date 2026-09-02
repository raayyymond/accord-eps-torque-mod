# -*- coding: utf-8 -*-
"""PRE-REGISTRATION for V278 rev 3: predicted SATURATION duty, clamp duties and the damping read, per K,
simulated frame by frame on the V276 rlog (r2e) through the LKAS rate PID as decompiled (FUN_00028ea6).

Chain (every line mirrors the decompile of FUN_00028ea6 on code.bin, Ghidra, 2026-09-02; addresses = V268):
  v        = clamp(((taper*255)&0xFFFF) * clamp(-4*cmd, +-LIMIT) >> 16 >> 6, +-240)   LIMIT = 0xCB844[7] = 16384 (slot 7)
  idx      = |v|                                    -> gp-0x674b  (the map AND Kp index: uVar33 @0x29CFA)
  sp       = sign(v) * LERP(map[7], idx) * K        -> gp-0x6a32
  fb       = clamp(s_old + s_new, +-0xC62E6)         s_new = (923*s_old>>10) + (1560*x>>10), x = -0x18F wire   (1 kHz)
  E        = 32*sp - fb                              0x29D76 shl 0x5 / 0x29D78 sub          -> gp-0x6cf8
  I        = 0                                       Ki 0xC63E6 = 0; accumulator stays 0
  P        = clamp((E * Kp(idx)) >> 8, +-0xC61BC)    ONE factor 32 -- it is already inside E (decompile: iVar31*Kp >> 8)
  D        = clamp(((E - E_prev) * Kd) >> 3, +-0xC61B6)   Kd = 128 flat; E_prev sentinel -> 0 on the first engaged tick
  sum      = clamp(((tapA*tapB & 0xFFFF) >> 8) * (P + D) >> 8, +-0xC61BE)   BELIEF: tapA=tapB=255 -> x253/256
  lag      = (s_o + s_n) >> 5,  s_n = (992*s_o + 507*sum) >> 10          DC 2*15.84/32 = 0.990  (5.05 Hz at 1 kHz)
  T        = clamp((lag * ramp >> 15) * (-1) * 0xC6CD0 >> 15, +-0xC61B4)   ramp = 0x8000 once engaged (BELIEF)
  tap      = (sign(T) << 9) | (|T| >> 3)            CAN-427, 8-count resolution

Run:  python prereg_v278r3_saturation.py        (needs _direct_read_v276.npz from direct_read_v276.py)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
FS = 100.0
FS1K = 1000.0
KS = (1.0, 1.5, 2.0, 3.0, 6.0)

# ---- slot-7 records and cells, read from the V268 base image (rev 3 = base + map x K + fb clamp x K) ----
MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
MAP_Y = np.array([0, 24, 42, 50, 62, 100, 126, 154, 166, 172], float)     # 0xE502C
KP_X = np.array([0, 68, 112, 136, 208], float)
KP_Y = np.array([248, 512, 645, 696, 696], float)                          # 0xE5378
KD = 128                                                                    # 0xE511C flat
TAPER_X = np.array([70, 72, 78, 80], float)
TAPER_Y = np.array([254, 234, 12, 0], float)                                # 0xE5404 (shape A)
LIMIT = 16384                       # 0xCB844[7] Y flat -- dose_e_sign_by_k.py used 15360; effect: none below |cmd| 3840
IDX_CLAMP = 240
A_COEF, B_COEF = 923, 1560          # 0xC63E8 / 0xC63EA
OA, OB = 992, 507                   # 0xC63EC / 0xC63EE
FB_CLAMP_STOCK = 7680               # 0xC62E6
P_CLAMP, D_CLAMP, SUM_CLAMP = 15360, 10240, 15360   # 0xC61BC / 0xC61B6 / 0xC61BE
GAIN, OUT_CAP = 5346, 3072          # 0xC6CD0 / 0xC61B4
SUM_MULT = (255 * 255 & 0xFFFF) >> 8            # 254 -> x254/256 (BELIEF: both post-sum tapers at 255)
FB_DC = 2 * B_COEF / (1024 - A_COEF)
COUNTS_PER_DEGS = 8.0
SAT_BRIEF = 2496                    # the brief's threshold (reads 312)
E_LIN_BRIEF = 440                   # the brief's "linear band" figure


def lerp(xk, yk, u):
    return np.interp(np.asarray(u, float), xk, yk)


def demand(cmd, tq_raw):
    S = np.clip(-4.0 * np.round(cmd), -LIMIT, LIMIT)
    taper = lerp(TAPER_X, TAPER_Y, np.abs(tq_raw) // 32)
    prod = (taper * 255).astype(np.int64) & 0xFFFF
    v = np.floor(prod * S / 65536.0)
    v = np.floor(v / 64.0)
    v = np.clip(v, -IDX_CLAMP, IDX_CLAMP)
    return np.abs(v), np.where(v < 0, -1.0, 1.0)


def feedback_1khz(x1k):
    s = 0.0
    fb = np.empty_like(x1k)
    for i, xv in enumerate(x1k):
        s_new = (A_COEF * s) // 1024 + (B_COEF * xv) // 1024
        fb[i] = s + s_new
        s = s_new
    return fb


def output_lag(u):
    """s_n = (992 s_o + 507 u)/1024 ; out = (s_o + s_n)/32  (float; integer truncation < 1 count)."""
    s = signal.lfilter([OB / 1024.0], [1.0, -OA / 1024.0], u)      # s_n as a function of u
    s_prev = np.r_[0.0, s[:-1]]
    return (s_prev + s) / 32.0


def ceiling_of(W, G):
    """Steady-state delivered |T| for sum clamp W and gain G, through the lag readout, then the 3072 cap."""
    lag = np.floor((2 * np.floor(W * OB / (1024 - OA))) / 32)
    return int(min(np.floor(lag * G / 32768), OUT_CAP))


def main():
    D = dict(np.load(os.path.join(HERE, "_direct_read_v276.npz")))
    t0 = D["t18"][0]
    T100 = D["t18"] - t0
    tg = np.arange(0.0, T100[-1], 1 / FS)
    wire = np.interp(tg, T100, D["rate"])
    tq_raw = np.interp(tg, T100, D["tq"] * 1.024)
    sca = np.interp(tg, T100, D["sca"]) > 0.5
    req = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    cmd = np.interp(tg, D["te4"] - t0, D["cmd"])
    vego = np.interp(tg, D["tcs"] - t0, D["vego"])
    eng = sca & req

    # episodes, same criterion as dose_e_sign_by_k.py / direct_read_v276.py
    sos = signal.butter(4, [2.5, 6.0], btype="bandpass", fs=FS, output="sos")
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
    print("episodes: %d (%.1f s), normal engaged %.1f s, threshold %.0f wire; vego osc p50 %.1f, normal p50 %.1f m/s"
          % (len(merged), osc.sum() / FS, normal.sum() / FS, thr, np.median(vego[osc]), np.median(vego[normal])))

    # ---- 1 kHz grid -------------------------------------------------------------------------------
    t1k = np.arange(0, len(tg) / FS, 1 / FS1K)
    up = lambda a: np.interp(t1k, tg, a)                                   # noqa: E731
    x1k = -up(wire)
    fb_un = feedback_1khz(x1k)
    idx100, sgn100 = demand(cmd, tq_raw)
    idx1k = np.round(up(idx100))
    sgn1k = np.sign(up(sgn100)) ; sgn1k[sgn1k == 0] = 1
    eng1k = up(eng.astype(float)) > 0.5
    kp1k = lerp(KP_X, KP_Y, idx1k)
    y1k = lerp(MAP_X, MAP_Y, idx1k)
    e_rail = P_CLAMP * 256 / kp1k                                          # |E| where P rails, per tick
    i100 = np.clip(np.round(tg * FS1K).astype(int), 0, len(t1k) - 1)      # 1 kHz tick nearest each CAN frame

    def simulate(K, sum_mult=SUM_MULT):
        sp = sgn1k * y1k * K
        fb = np.clip(fb_un, -FB_CLAMP_STOCK * K, FB_CLAMP_STOCK * K)
        E = 32 * sp - fb
        P_raw = np.floor(E * kp1k / 256)
        P = np.clip(P_raw, -P_CLAMP, P_CLAMP)
        dE = np.r_[0.0, np.diff(E)]
        onset = eng1k & ~np.r_[False, eng1k[:-1]]
        dE[onset] = 0.0                                                    # E_prev sentinel -> no D on the first tick
        Dt = np.clip(np.floor(dE * KD / 8), -D_CLAMP, D_CLAMP)
        S_raw = np.floor(sum_mult * (P + Dt) / 256)
        S = np.clip(S_raw, -SUM_CLAMP, SUM_CLAMP)
        S[~eng1k] = 0.0
        lag = output_lag(S)
        T = np.clip(np.floor(-lag * GAIN / 32768), -OUT_CAP, OUT_CAP)
        return dict(E=E, P=P, P_raw=P_raw, D=Dt, S=S, S_raw=S_raw, T=T, fb=fb)

    def duties(R, m1k, m100):
        T, E, fb = R["T"], R["E"], R["fb"]
        Tc = T[i100]
        out = dict(
            sat=np.mean(np.abs(Tc[m100]) >= SAT_THR),
            sat_brief=np.mean(np.abs(Tc[m100]) >= SAT_BRIEF),
            p_rail=np.mean(np.abs(R["P_raw"][m1k]) >= P_CLAMP),
            s_rail=np.mean(np.abs(R["S_raw"][m1k]) >= SUM_CLAMP),
            d_rail=np.mean(np.abs(R["D"][m1k]) >= D_CLAMP),
            lin440=np.mean(np.abs(E[m1k]) < E_LIN_BRIEF),
            lin_true=np.mean(np.abs(E[m1k]) < e_rail[m1k]),
            T_p50=np.median(np.abs(Tc[m100])), T_p90=np.percentile(np.abs(Tc[m100]), 90),
        )
        mm = m1k & (fb != 0)
        out["damp_E"] = np.mean(np.sign(E[mm]) != np.sign(fb[mm]))          # rev 2's comparator (reference)
        w = wire[m100]
        mt = (Tc[m100] != 0) & (w != 0)
        out["damp_T"] = np.mean(np.sign(Tc[m100][mt]) != np.sign(w[mt]))    # rev 3: sign(T) == sign(fb) <=> T opposes 0x18F
        return out

    # the steady-state ceiling and the saturation threshold, from the cells
    CEIL = ceiling_of(SUM_CLAMP, GAIN)
    global SAT_THR
    SAT_THR = (CEIL // 8 - 1) * 8                                          # one tap LSB below the ceiling reading
    print("steady-state ceiling through the lag readout: |T| = %d (tap reads %d); brief's 2505 (313) is NOT reachable"
          % (CEIL, CEIL // 8))
    print("=> SATURATION := |T| >= %d (tap reading >= %d)\n" % (SAT_THR, SAT_THR // 8))

    osc1k = up(osc.astype(float)) > 0.5
    nor1k = up(normal.astype(float)) > 0.5
    hdr = "%-4s | %-6s %-6s %-6s %-6s | %-6s %-6s %-6s %-6s | %-6s %-6s | %-6s %-6s | %-6s %-6s"
    print(hdr % ("K", "satO", "satN", "PrlO", "PrlN", "SrlO", "SrlN", "DrlO", "DrlN", "l440O", "l440N", "linO", "linN", "dmpEO", "dmpTO"))
    rows = {}
    for K in KS:
        R = simulate(K)
        o = duties(R, osc1k, osc)
        n = duties(R, nor1k, normal)
        rows[K] = (o, n)
        print("%-4.1f | %-6.3f %-6.3f %-6.3f %-6.3f | %-6.3f %-6.3f %-6.3f %-6.3f | %-6.3f %-6.3f | %-6.3f %-6.3f | %-6.3f %-6.3f   |T| osc p50/p90 %4.0f/%4.0f  normal %4.0f/%4.0f  (sat@2496: %.3f/%.3f)"
              % (K, o["sat"], n["sat"], o["p_rail"], n["p_rail"], o["s_rail"], n["s_rail"], o["d_rail"], n["d_rail"],
                 o["lin440"], n["lin440"], o["lin_true"], n["lin_true"], o["damp_E"], o["damp_T"],
                 o["T_p50"], o["T_p90"], n["T_p50"], n["T_p90"], o["sat_brief"], n["sat_brief"]))
    print("  satO/N = P(|T|>=%d) osc/normal; Prl/Srl/Drl = P/sum/D clamp railed; l440 = |E|<440; lin = |E| < 15360*256/Kp(idx);"
          % SAT_THR)
    print("  dmpE = rev-2 comparator sign(E)!=sign(fb); dmpT = rev-3 read sign(T)!=sign(0x18F) -- osc frames")
    print("  normal-frame damping: " + "  ".join("K=%.1f E %.3f T %.3f" % (K, rows[K][1]["damp_E"], rows[K][1]["damp_T"]) for K in KS))

    # per-episode spread at K=2 (the tolerance), K=1.5 and K=6
    print("\nPER-EPISODE (100 Hz frames): sat duty | damp_T | damp_E")
    print("%3s %7s %5s %6s | " % ("#", "start", "dur", "vego") + "  ".join("K=%.1f" % K for K in (1.5, 2.0, 6.0)))
    sims = {K: simulate(K) for K in (1.5, 2.0, 6.0)}
    spread = {K: [] for K in sims}
    for k, (s, e) in enumerate(merged):
        m100 = np.zeros_like(osc); m100[s:e] = True
        m1k = up(m100.astype(float)) > 0.5
        line = "%3d %7.1f %5.1f %6.1f | " % (k, tg[s], (e - s) / FS, np.median(vego[s:e]))
        for K, R in sims.items():
            d = duties(R, m1k, m100)
            spread[K].append((d["sat"], d["damp_T"], d["damp_E"]))
            line += "%.2f/%.2f/%.2f  " % (d["sat"], d["damp_T"], d["damp_E"])
        print(line)
    for K in sims:
        a = np.array(spread[K])
        print("K=%.1f episode spread: sat %.2f..%.2f (sd %.2f) | damp_T %.2f..%.2f (sd %.2f) | damp_E %.2f..%.2f (sd %.2f)"
              % (K, a[:, 0].min(), a[:, 0].max(), a[:, 0].std(), a[:, 1].min(), a[:, 1].max(), a[:, 1].std(),
                 a[:, 2].min(), a[:, 2].max(), a[:, 2].std()))

    # sensitivity: the post-sum multiplier (BELIEF: 254/256) -- if the speed tapers bite, sum rails less often
    print("\nSENSITIVITY: post-sum multiplier (0xCBB54/0xCBC34 x 0xCBAE4/0xCBBC4 product), K=2:")
    for mult in (254, 205, 164, 125):
        R = simulate(2.0, sum_mult=mult)
        o, n = duties(R, osc1k, osc), duties(R, nor1k, normal)
        print("  mult %3d/256: sat osc %.3f normal %.3f | sum-rail osc %.3f normal %.3f | damp_T osc %.3f"
              % (mult, o["sat"], n["sat"], o["s_rail"], n["s_rail"], o["damp_T"]))

    # ---- the widening table ------------------------------------------------------------------------
    print("\nWIDENING 0xC61BC = 0xC61BE = W (0xC6CD0 = G re-sized to hold the ceiling), from the cells:")
    W_bind = int(np.ceil(OUT_CAP * 32768 / GAIN))
    print("  0xC61B4 = 3072 binds at W*5346>>15 >= 3072  ->  W >= %d (through the 0.990 lag readout: W >= %d)"
          % (W_bind, int(np.ceil(W_bind / 0.9902))))
    print("  %-6s | %-12s | %-9s | %-9s | %-22s | %-22s" % ("W", "G=0xC6CD0", "ceil(G)", "ceil@5346", "|E|<W*256/Kp  Kp=248", "Kp=696"))
    for W in (15360, 18432, 20480, 24576, 30720):
        G = int(round(2505 * 32768 / W))
        for kp in (248, 696):
            pass
        e248, e696 = W * 256 / 248, W * 256 / 696
        print("  %-6d | %-12d | %-9d | %-9d | %6.0f op = %5.1f deg/s | %6.0f op = %5.1f deg/s"
              % (W, G, ceiling_of(W, G), ceiling_of(W, GAIN), e248, e248 / FB_DC / COUNTS_PER_DEGS, e696, e696 / FB_DC / COUNTS_PER_DEGS))
    print("  (deg/s = operand / 30.89 / 8; the brief's '|E| = 440 = 1.8 deg/s' band is 32x narrower than the decompiled rail)")


if __name__ == "__main__":
    main()
