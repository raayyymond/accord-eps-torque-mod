# -*- coding: utf-8 -*-
"""studies/osc-highangle/twist_taper_loop.py -- the DRIVER-TORQUE-FED multipliers on the LKAS lane, per frame, on the
r32/r33/r34 F7 strong-turn episodes (V280 rev 2 on the car), and the chain mirror re-run WITH them.
Subagent twistloop, 2026-09-03.  Companion: TWIST-TAPER-LOOP-2026-09-03.md.

Arithmetic mirrors the Ghidra decompile of FUN_00028ea6 (stock code.bin; the function is byte-identical on V280 rev 2
except the V112 gain-read redirect at 0x2A1F0).  Every table is READ FROM THE V280 REV 2 IMAGE at run time.

  gp-0x682f = min(|gp-0x4f60| >> 5, 254/255)                                   st.b @0x29068   (driver torque BYTE)
  s'        = (s*cal[0xC63E2]=31 >> 5) + (tq*cal[0xC63E4]=634 >> 5) ; d = (s' - s) >> 4 ; clamp +-0x3200
  gp-0x6830 = |d| >> 6                                                          st.b @0x290de   (grab-rate BYTE)
  mode      = gp-0x6803 = bits 3:2 of 0xE4 byte 2 (FUN_00052676 @0x526ac: (b << 0x1c) >> 0x1e)  -- openpilot sends 0
  arm select (0x29a74..0x29a8a): bVar1 = (gp-0x6803 == 2)
     same-sign(S, tq)  : taper = bVar1 ? LERP(0xCBA74[sel]) : LERP(0xCB924[sel])   on gp-0x682f
     opposite-sign     : taper = bVar1 ? LERP(0xCBA04[sel]) : LERP(0xCB8B4[sel])   on gp-0x682f
     (S = clamp(-4*cmd) -- so same-sign(S,tq) is OPPOSITE-sign(cmd,tq) in wire units)
  v    = ((taper*speedF)&0xFFFF) * S >> 16 ; v >>= 6 ; clamp +-240 ; idx = |v|
  sp   = sign(v) * LERP(map[sel], idx) ; E = 32*sp - fb ; P = E*Kp>>8 ; D = dE*Kd>>3
  post (0x29fe2-0x2a0c2): A = bVar1 ? LERP(0xCBB54[sel], gp-0x6830) : LERP(0xCBC34[sel], gp-0x6830)
                          B = bVar1 ? LERP(0xCBAE4[sel], gp-0x682f) : LERP(0xCBBC4[sel], gp-0x682f)
        sum = (((A*B) & 0xFFFF) >> 8) * (P + D) >> 8 ; clamp +-0xC61BE
  lag  ; T = clamp((y * ramp >> 15) * (-1) * GAIN >> 15, +-0xC61B4)

Run: python twist_taper_loop.py   (needs analysis-2020accord/_scratch/cache/v280/r32,r33,r34.npz and the V280 rev 2 image)
"""
import os
import struct
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strongturn_r34 as S34  # noqa: E402  (registers r32/r33/r34, patches V.load with the tap)

V, ST = S34.V, S34.ST
FS = ST.FS
FS1K = V.FS1K
FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
IMG_V280 = FW + "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
IMG_V281 = FW + "_v281r2_V281R2-V280R2BASE-KP.FLAT341.FROM24.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
SEL = 7
OUT_TXT = os.path.join(HERE, "TWIST-TAPER-LOOP.txt")

# episodes: F7 = fdom >= 6 from the strongturn lists (|angle| >= 30 already applied there); control = r34 stall 250-264 s
F7 = {tag: [(t0, d, f) for (t0, d, f) in ST.EPIS[tag] if f >= 6.0] for tag in ("r32", "r33", "r34")}
CONTROL = ("r34", 250.0, 14.0, 0.0)
CLIFF = [("r33", 805.8, 1.1, 1.90), ("r34", 227.9, 1.1, 2.78), ("r34", 172.2, 1.3, 2.36), ("r34", 747.8, 1.1, 2.75)]


# ---------------------------------------------------------------------------------------------- image reads
def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, table, n, sel=SEL):
    r = u32(b, table + 4 * sel)
    assert u16(b, r) == n, (hex(table), u16(b, r))
    X = np.array([u16(b, r + 2 + 2 * i) for i in range(n)], float)
    Y = np.array([u16(b, r + 2 + 2 * n + 2 * i) for i in range(n)], float)
    return r, X, Y


def read_tables(path):
    b = open(path, "rb").read()
    T = {}
    for name, tbl, n in (("taperA_m2_same", 0xCBA74, 4), ("taperA_m2_opp", 0xCBA04, 4), ("taperA_m0_same", 0xCB924, 4),
                         ("taperA_m0_opp", 0xCB8B4, 4), ("postA_m2", 0xCBB54, 6), ("postA_m0", 0xCBC34, 6),
                         ("postB_m2", 0xCBAE4, 6), ("postB_m0", 0xCBBC4, 6)):
        T[name] = rec(b, tbl, n)
    T["kp"] = rec(b, 0xCB994, 5)
    T["map"] = rec(b, 0xC9A88, 10)
    T["speedF_Y"] = np.array([u16(b, 0xC6980 + 2 * i) for i in range(4)], float)
    T["cal"] = dict(c63e2=u16(b, 0xC63E2), c63e4=u16(b, 0xC63E4), c64b8=b[0xC64B8], c64f0=b[0xC64F0], c61be=u16(b, 0xC61BE),
                    c61b4=u16(b, 0xC61B4), gain=u16(b, 0xC6CD0), c62e6=u16(b, 0xC62E6), c61bc=u16(b, 0xC61BC), c61b6=u16(b, 0xC61B6))
    return T


def lerp_fw(X, Y, u):
    """Firmware LERP: u <= X0 -> Y0; u >= Xlast -> Ylast; else integer-division interpolation (C trunc toward zero)."""
    u = np.asarray(u, float)
    out = np.full_like(u, Y[0])
    out[u >= X[-1]] = Y[-1]
    for i in range(len(X) - 1):
        m = (u > X[i]) & (u < X[i + 1]) if i else (u > X[0]) & (u < X[1])
        out[m] = np.fix((Y[i + 1] - Y[i]) * (u[m] - X[i]) / (X[i + 1] - X[i])) + Y[i]
    return out


# ---------------------------------------------------------------------------------------------- per-frame multipliers
def torque_byte(tq_raw):
    return np.minimum(np.floor(np.abs(tq_raw) / 32.0), 255.0)      # st.b @0x29068 : (byte)min(|tq|>>5, 254) with 255 above


def grab_byte_1k(tq1k, c):
    """gp-0x6830 at 1 kHz: s' = (s*31>>5) + (tq*634>>5); d = (s'-s)>>4; clamp +-12800; |d|>>6."""
    s = 0
    g = np.empty(len(tq1k))
    a, bb = c["c63e2"], c["c63e4"]
    for i, t in enumerate(tq1k):
        s2 = ((s * a) >> 5) + ((int(t) * bb) >> 5)
        d = (s2 - s) >> 4
        d = max(-12800, min(12800, d))
        g[i] = abs(d) >> 6
        s = s2
    return g


def demand_idx(cmd, tq_raw, taper_same, taper_opp, speedF=255.0):
    """idx and sign from cmd and tq with the arm chosen by sign(S) vs sign(tq) (decompile 0x29a8a-0x29b7c)."""
    S = np.clip(-4.0 * np.round(cmd), -V.LIMIT, V.LIMIT)
    tb = torque_byte(tq_raw)
    same = (np.sign(S) == np.sign(tq_raw)) | (S == 0) | (tq_raw == 0)      # tq >= 0 and S >= 0 both go to the 'same' label
    same = np.where((S < 0) & (tq_raw < 0), True, np.where((S >= 0) & (tq_raw >= 0), True, False))
    taper = np.where(same, lerp_fw(*taper_same[1:], tb), lerp_fw(*taper_opp[1:], tb))
    prod = (taper * speedF).astype(np.int64) & 0xFFFF
    v = np.floor(prod * S / 65536.0)
    v = np.floor(v / 64.0)
    v = np.clip(v, -V.IDX_CLAMP, V.IDX_CLAMP)
    return np.abs(v), np.where(v < 0, -1.0, 1.0), taper


def post_mult(A_tab, B_tab, grab, tb):
    A = lerp_fw(*A_tab[1:], grab)
    B = lerp_fw(*B_tab[1:], tb)
    m = ((A.astype(np.int64) * B.astype(np.int64)) & 0xFFFF) >> 8
    return m.astype(float), A, B


def simulate(r, mapY, fb_clamp, kpX, kpY, idx1k, sgn1k, m1k, kd=V.KD, c=None):
    """Route.simulate with an explicit idx/sign and a per-tick post multiplier m (0..255)."""
    y = V.lerp(V.MAP_X, mapY, idx1k)
    kp = V.lerp(kpX, kpY, idx1k)
    sp = sgn1k * y
    fb = np.clip(r.fb_un, -fb_clamp, fb_clamp)
    E = 32 * sp - fb
    P = np.clip(np.floor(E * kp / 256), -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    onset = r.eng1k & ~np.r_[False, r.eng1k[:-1]]
    dE[onset] = 0.0
    Dt = np.clip(np.floor(dE * kd / 8), -V.D_CLAMP, V.D_CLAMP)
    S_raw = np.floor(m1k * (P + Dt) / 256)
    S = np.clip(S_raw, -V.SUM_CLAMP, V.SUM_CLAMP)
    S[~r.eng1k] = 0.0
    lag = V.output_lag(S)
    T = np.clip(np.floor(-lag * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
    return dict(E=E, P=P, D=Dt, S=S, T=T)


def bamp(x, lo=6.0, hi=8.5):
    return ST.band_amp(np.asarray(x, float), lo, hi) if len(x) > 40 else np.nan


def lowpass(x, fc=1.0):
    return signal.sosfiltfilt(signal.butter(2, fc, fs=FS1K, output="sos"), x)


def xspec(x, y, f0):
    """coherence and phase (deg, y relative to x) at the bin nearest f0, 100 Hz series."""
    n = min(64, len(x))
    f, Pxy = signal.csd(x, y, fs=FS, nperseg=n, detrend="linear")
    _, Cxy = signal.coherence(x, y, fs=FS, nperseg=n, detrend="linear")
    k = int(np.argmin(np.abs(f - f0)))
    return float(Cxy[k]), float(np.degrees(np.angle(Pxy[k]))), float(f[k])


def main():
    L = []
    pr = lambda s="": (print(s), L.append(s))  # noqa: E731
    T280 = read_tables(IMG_V280)
    if os.path.exists(IMG_V281):
        T281 = read_tables(IMG_V281)
    else:                                   # image renamed/moved after the first run (2026-09-03): knots as read from it then
        T281 = dict(kp=(0xE5378, np.array([0, 24, 68, 136, 208], float), np.array([248, 341, 341, 341, 341], float)))
        print("V281r2 image not found; using its Kp knots as read on 2026-09-03 (X 0,24,68,136,208 / Y 248,341,341,341,341)")
    c = T280["cal"]
    pr("=" * 150)
    pr("TABLES READ FROM THE V280 REV 2 IMAGE, slot %d  (rec addr : X / Y)" % SEL)
    pr("=" * 150)
    for k in ("taperA_m2_same", "taperA_m2_opp", "taperA_m0_same", "taperA_m0_opp", "postA_m2", "postA_m0", "postB_m2", "postB_m0", "kp", "map"):
        a, X, Y = T280[k]
        pr("  %-15s 0x%05X : X %s / Y %s" % (k, a, X.astype(int).tolist(), Y.astype(int).tolist()))
    pr("  V281r2 kp        0x%05X : X %s / Y %s" % (T281["kp"][0], T281["kp"][1].astype(int).tolist(), T281["kp"][2].astype(int).tolist()))
    pr("  cals: %s ; speedF Y %s" % (c, T280["speedF_Y"].astype(int).tolist()))
    pr("  m0 = mode gp-0x6803 == 0 (openpilot's 0xE4 byte 2 bits 3:2 = 0, measured on r32/r33/r34) ; m2 = the kit's assumed mode-2 arms")
    pr("  raw driver torque at the LIVE arm knots (x32): postB_m0 %s ; taperA_m0_same %s ; postB_m2 %s ; taperA_m2 %s"
       % ((T280["postB_m0"][1] * 32).astype(int).tolist(), (T280["taperA_m0_same"][1] * 32).astype(int).tolist(),
          (T280["postB_m2"][1] * 32).astype(int).tolist(), (T280["taperA_m2_same"][1] * 32).astype(int).tolist()))

    mapY, fbc = ST.V280R2
    kpX, kpY = T280["kp"][1], T280["kp"][2]
    kpX1, kpY1 = T281["kp"][1], T281["kp"][2]
    flatB = (0, np.array([16, 26, 38, 48, 80, 96], float), np.array([255, 255, 255, 255, 255, 77], float))   # lever: fall from 2560 raw

    routes = {}
    for tag in ("r32", "r33", "r34"):
        print("loading %s ..." % tag, flush=True)
        r = V.Route(tag)
        # frame-level multipliers (100 Hz) and tick-level (1 kHz)
        r.tb = torque_byte(r.tq_raw)
        r.tq_fw = -r.tq_raw          # gp-0x4f60 = -(wire)*1.024: FUN_00055C42 sends -(raw*125>>7) and the cache applies no factor [EVIDENCE]
        r.idxL, r.sgnL, r.taperL = demand_idx(r.cmd, r.tq_fw, T280["taperA_m0_same"], T280["taperA_m0_opp"])
        r.idxK, r.sgnK, r.taperK = demand_idx(r.cmd, r.tq_fw, T280["taperA_m2_same"], T280["taperA_m2_opp"])
        tq1k = np.round(r.up(r.tq_raw))
        r.grab1k = grab_byte_1k(tq1k, c)
        r.tb1k = torque_byte(tq1k)
        r.mL1k, r.A1k, r.B1k = post_mult(T280["postA_m0"], T280["postB_m0"], r.grab1k, r.tb1k)
        r.mK1k, _, _ = post_mult(T280["postA_m2"], T280["postB_m2"], r.grab1k, r.tb1k)
        r.mF1k, _, _ = post_mult(T280["postA_m0"], flatB, r.grab1k, r.tb1k)
        r.mL = r.mL1k[r.i100]; r.A = r.A1k[r.i100]; r.B = r.B1k[r.i100]; r.grab = r.grab1k[r.i100]
        up = lambda a: np.interp(r.t1k, r.tg, a)  # noqa: E731
        r.idxL1k, r.idxK1k = np.round(up(r.idxL)), np.round(up(r.idxK))
        sL = np.sign(up(r.sgnL)); sL[sL == 0] = 1
        sK = np.sign(up(r.sgnK)); sK[sK == 0] = 1
        r.sgnL1k, r.sgnK1k = sL, sK
        m_slow = lowpass(r.mL1k, 1.0)                                    # the multiplier WITHOUT its ripple (>1 Hz removed)
        r.sim = {
            "kit (m2 arm, m=254, Kd)": simulate(r, mapY, fbc, kpX, kpY, r.idxK1k, r.sgnK1k, np.full(len(r.t1k), 254.0)),
            "live (m0 arm, live m, Kd)": simulate(r, mapY, fbc, kpX, kpY, r.idxL1k, r.sgnL1k, r.mL1k),
            "live, m frozen (<1 Hz)": simulate(r, mapY, fbc, kpX, kpY, r.idxL1k, r.sgnL1k, m_slow),
            "live, m frozen, Kd=0": simulate(r, mapY, fbc, kpX, kpY, r.idxL1k, r.sgnL1k, m_slow, kd=0),
            "live, Kd=0": simulate(r, mapY, fbc, kpX, kpY, r.idxL1k, r.sgnL1k, r.mL1k, kd=0),
            "live, postB FLAT to 2560": simulate(r, mapY, fbc, kpX, kpY, r.idxL1k, r.sgnL1k, r.mF1k),
            "V281r2 Kp, live m": simulate(r, mapY, fbc, kpX1, kpY1, r.idxL1k, r.sgnL1k, r.mL1k),
            "V281r2 Kp, m frozen": simulate(r, mapY, fbc, kpX1, kpY1, r.idxL1k, r.sgnL1k, m_slow),
        }
        routes[tag] = r

    # ------------------------------------------------------------------------------------------ whole-route census
    pr("\n" + "=" * 150)
    pr("WHOLE-ROUTE CENSUS, engaged frames: where the live multipliers sit")
    pr("=" * 150)
    for tag, r in routes.items():
        e = r.eng
        tqa = np.abs(r.tq_raw[e])
        pr("  %s engaged %5.0f s | |tq| p50/p90 %4.0f/%4.0f raw | frac |tq|>=512 (postB_m0 below 255) %.2f ; >=1216 (<=218) %.2f ; >=2048 (77) %.2f ; >=2560 (m0 taper falls) %.3f ; >=2240 (m2 cliff) %.3f"
           % (tag, e.sum() / FS, np.median(tqa), np.percentile(tqa, 90), np.mean(tqa >= 512), np.mean(tqa >= 1216), np.mean(tqa >= 2048), np.mean(tqa >= 2560), np.mean(tqa >= 2240)))
        pr("       live m p10/p50/p90 = %.0f/%.0f/%.0f (of 254) ; A(grab) p50/p10 %.0f/%.0f ; B(tq) p50/p10 %.0f/%.0f ; grab byte p50/p90/max %.0f/%.0f/%.0f"
           % (np.percentile(r.mL[e], 10), np.median(r.mL[e]), np.percentile(r.mL[e], 90), np.median(r.A[e]), np.percentile(r.A[e], 10),
              np.median(r.B[e]), np.percentile(r.B[e], 10), np.median(r.grab[e]), np.percentile(r.grab[e], 90), r.grab[e].max()))
        pr("       idx: live arm vs kit arm differ on %.3f of engaged frames (live > kit on %.3f)" % (np.mean(r.idxL[e] != r.idxK[e]), np.mean(r.idxL[e] > r.idxK[e])))
        for name in ("kit (m2 arm, m=254, Kd)", "live (m0 arm, live m, Kd)"):
            Ts = r.sim[name]["T"][r.i100]; Tm = r.T_meas
            mm = e & (r.idx > 0)
            pr("       %-28s vs tap, engaged idx>0: corr %.3f  LS slope %.3f  |T_sim| p50 %4.0f  |T_meas| p50 %4.0f"
               % (name, np.corrcoef(Ts[mm], Tm[mm])[0, 1], np.sum(Ts[mm] * Tm[mm]) / np.sum(Ts[mm] ** 2), np.median(np.abs(Ts[mm])), np.median(np.abs(Tm[mm]))))

    # ------------------------------------------------------------------------------------------ per-episode table
    def ep_frames(r, t0, dur):
        return (r.tg >= t0) & (r.tg < t0 + dur) & r.eng

    def ep_ticks(r, t0, dur):
        return (r.t1k >= t0) & (r.t1k < t0 + dur) & r.eng1k

    pr("\n" + "=" * 150)
    pr("PER-EPISODE: the multipliers' modulation depth (6-8.5 Hz amp / mean, and 12-17 Hz = 2*f0 for the rectified index), bar<->T cross-spectrum,")
    pr("             chain mirror corr/residual before (kit arm, m=254) and after (live arm, live m), and the P / taper / D decomposition of T's 6-8.5 Hz")
    pr("=" * 150)
    hdr = ("route t0     dur fdom | tq mean  ring | taper m0: mean d7 d14 | postB: mean d7 d14 | postA: mean d7 d14 | m: mean d7 d14 | coh phase(T re tq) f | "
           "corr kit/live | resid rip/L kit/live | rip/L meas (|T|) | sim rip/L kit/live | P-drv taper-drv D-drv (of |T|meas) | m-lever: |T| x, rip/L | V281: rip/L, taper-drv")
    pr(hdr)
    rows = []
    for tag in ("r32", "r33", "r34"):
        r = routes[tag]
        eps = [(tag, t0, d, f) for (t0, d, f) in F7[tag]]
        if tag == "r34":
            eps.append(CONTROL)
        for (tg_, t0, dur, fdom) in eps:
            m100 = ep_frames(r, t0, dur); m1k = ep_ticks(r, t0, dur)
            if m100.sum() < 50:
                pr("  %s %6.1f: too few engaged frames (%d)" % (tg_, t0, m100.sum())); continue
            f0 = fdom if fdom >= 6 else 7.0
            tq = r.tq_raw[m100]; Tm = r.T_meas[m100]
            Tp50 = np.median(np.abs(Tm))
            def depth(x, lo=6.0, hi=8.5):
                mu = np.mean(x)
                return mu, (bamp(x, lo, hi) / mu if mu > 0 else np.nan), (bamp(x, 12.0, 17.0) / mu if mu > 0 else np.nan)
            tp = depth(r.taperL[m100]); pb = depth(r.B[m100]); pa = depth(r.A[m100]); mm = depth(r.mL[m100])
            coh, ph, fb_ = xspec(tq, Tm, f0)
            out = {}
            for name in r.sim:
                Ts = r.sim[name]["T"][r.i100][m100]
                cc = np.corrcoef(Ts, Tm)[0, 1] if np.std(Ts) > 0 else np.nan
                sl = np.sum(Ts * Tm) / np.sum(Ts ** 2) if np.sum(Ts ** 2) > 0 else np.nan
                out[name] = dict(corr=cc, slope=sl, rip=bamp(Ts) / Tp50, resid=bamp(Tm - sl * Ts) / Tp50, p50=np.median(np.abs(Ts)))
            Tl = r.sim["live (m0 arm, live m, Kd)"]["T"][r.i100][m100]
            Tf = r.sim["live, m frozen (<1 Hz)"]["T"][r.i100][m100]
            Tf0 = r.sim["live, m frozen, Kd=0"]["T"][r.i100][m100]
            Pd, Td, Dd = bamp(Tf0) / Tp50, bamp(Tl - Tf) / Tp50, bamp(Tf - Tf0) / Tp50
            T81 = r.sim["V281r2 Kp, live m"]["T"][r.i100][m100]; T81f = r.sim["V281r2 Kp, m frozen"]["T"][r.i100][m100]
            Tfl = r.sim["live, postB FLAT to 2560"]["T"][r.i100][m100]
            sos = signal.butter(4, [6.0, 8.5], btype="bandpass", fs=FS, output="sos")
            bp = lambda x: signal.sosfiltfilt(sos, x) if len(x) > 40 else x  # noqa: E731
            tdrv, pdrv, wbp = bp(Tl - Tf), bp(Tf0), bp(-r.wire[m100])          # -wire = firmware rate sign (x = -0x18F rate)
            c_tp = np.corrcoef(tdrv, pdrv)[0, 1] if np.std(tdrv) > 0 else np.nan         # +1 in phase with P-driven (reinforces), -1 opposes
            _, ph_tr, _ = xspec(r.wire[m100], Tl - Tf, f0)                              # taper-driven re rate
            damp_t = np.mean(np.sign(tdrv) != np.sign(wbp))                               # damping fraction of the taper-driven part
            wmed = np.median(r.wire[m100]); rev = np.mean(np.sign(r.wire[m100]) != np.sign(wmed))
            row = dict(tag=tg_, t0=t0, dur=dur, fdom=fdom, tq_mean=np.mean(tq), ring=bamp(tq), taper=tp, postB=pb, postA=pa, m=mm, coh=coh, ph=ph, fb=fb_,
                       kit=out["kit (m2 arm, m=254, Kd)"], live=out["live (m0 arm, live m, Kd)"], Tp50=Tp50, meas_rip=bamp(Tm) / Tp50,
                       Pd=Pd, Td=Td, Dd=Dd, lever_x=np.median(np.abs(Tfl)) / max(np.median(np.abs(Tl)), 1), lever_rip=bamp(Tfl) / Tp50,
                       v281_rip=bamp(T81) / Tp50, v281_td=bamp(T81 - T81f) / Tp50, v281_p50=np.median(np.abs(T81)),
                       c_tp=c_tp, ph_tr=ph_tr, damp_t=damp_t, rev=rev)
            rows.append(row)
            pr("  %s %6.1f %3.1f %4.2f | %+5.0f %5.0f | %4.0f %.2f %.2f | %4.0f %.2f %.2f | %4.0f %.2f %.2f | %4.0f %.2f %.2f | %.2f %+4.0f %4.1f | %.2f/%.2f | %.2f/%.2f | %.2f (%4.0f) | %.2f/%.2f | %.2f %.2f %.2f | %.2f %.2f | %.2f %.2f | tdrv: c(P) %+.2f re-rate %+4.0f damp %.2f | rate-rev %.2f"
               % (tg_, t0, dur, fdom, row["tq_mean"], row["ring"], tp[0], tp[1], tp[2], pb[0], pb[1], pb[2], pa[0], pa[1], pa[2], mm[0], mm[1], mm[2], coh, ph, fb_,
                  row["kit"]["corr"], row["live"]["corr"], row["kit"]["resid"], row["live"]["resid"], row["meas_rip"], Tp50, row["kit"]["rip"], row["live"]["rip"],
                  Pd, Td, Dd, row["lever_x"], row["lever_rip"], row["v281_rip"], row["v281_td"], c_tp, ph_tr, damp_t, rev))
    f7 = [x for x in rows if x["fdom"] >= 6]
    med = lambda k: np.nanmedian([x[k] for x in f7])  # noqa: E731
    pr("  F7 MEDIANS (n %d): tq ring %.0f | taper d7 %.2f | postB mean %.0f d7 %.2f d14 %.2f | postA mean %.0f d7 %.2f d14 %.2f | m mean %.0f d7 %.2f d14 %.2f | coh %.2f phase %+.0f"
       % (len(f7), med("ring"), np.nanmedian([x["taper"][1] for x in f7]), np.nanmedian([x["postB"][0] for x in f7]), np.nanmedian([x["postB"][1] for x in f7]),
          np.nanmedian([x["postB"][2] for x in f7]), np.nanmedian([x["postA"][0] for x in f7]), np.nanmedian([x["postA"][1] for x in f7]), np.nanmedian([x["postA"][2] for x in f7]),
          np.nanmedian([x["m"][0] for x in f7]), np.nanmedian([x["m"][1] for x in f7]), np.nanmedian([x["m"][2] for x in f7]), med("coh"), med("ph")))
    pr("             corr kit %.3f -> live %.3f | resid rip/L kit %.2f -> live %.2f | meas rip/L %.2f | sim rip/L kit %.2f live %.2f | P-drv %.2f taper-drv %.2f D-drv %.2f | lever |T| x%.2f rip/L %.2f | V281 rip/L %.2f taper-drv %.2f"
       % (np.nanmedian([x["kit"]["corr"] for x in f7]), np.nanmedian([x["live"]["corr"] for x in f7]), np.nanmedian([x["kit"]["resid"] for x in f7]),
          np.nanmedian([x["live"]["resid"] for x in f7]), med("meas_rip"), np.nanmedian([x["kit"]["rip"] for x in f7]), np.nanmedian([x["live"]["rip"] for x in f7]),
          med("Pd"), med("Td"), med("Dd"), med("lever_x"), med("lever_rip"), med("v281_rip"), med("v281_td")))
    pr("  taper-driven component: corr with P-driven median %+.2f (min %+.2f max %+.2f) ; phase re rate median %+.0f ; damping fraction median %.2f ; rate-reversal fraction median %.2f (max %.2f)"
       % (med("c_tp"), np.nanmin([x["c_tp"] for x in f7]), np.nanmax([x["c_tp"] for x in f7]), med("ph_tr"), med("damp_t"), med("rev"), np.nanmax([x["rev"] for x in f7])))
    pr("  paired: live corr - kit corr: mean %+.3f, positive on %d of %d episodes" % (np.mean([x["live"]["corr"] - x["kit"]["corr"] for x in f7]),
                                                                                       sum(x["live"]["corr"] > x["kit"]["corr"] for x in f7), len(f7)))

    # ------------------------------------------------------------------------------------------ bar-fed lanes vs the LKAS lane at f0
    pr("\n" + "=" * 150)
    pr("DRIVER-SIDE (bar-fed) lanes at f0, per F7 episode, aggregator counts -- vs the LKAS lane's own measured 6-8.5 Hz T ripple")
    pr("  r24 = -(0.5*(tq[n]-tq[n-4]) * gainA/1024), gainA = 0xC6446 = 512 (Lever B cell dead, gp-0x683c = 0) [BELIEF for the arm];")
    pr("  FUN_00036682 = (tq*891>>15) through alpha=6/1024 IIR, clamp 512;  gp-0x6bbe ~ 90 ct per rad/s of wheel rate (V92 measured)")
    pr("=" * 150)
    for x in f7:
        f0 = x["fdom"]; w = 2 * np.pi * f0 / 1000.0
        h4 = 0.5 * abs(1 - np.exp(-1j * w * 4))
        r24 = x["ring"] * h4 * 512 / 1024.0
        a = 6 / 1024.0
        iir = a / abs(1 - (1 - a) * np.exp(-1j * w))
        f36 = x["ring"] * 891 / 32768.0 * iir
        pr("  %s %6.1f: tq ring %4.0f raw -> r24 %5.1f ct, FUN_00036682 %5.2f ct | LKAS lane T ripple meas %4.0f ct (= %.2f x |T| %4.0f)"
           % (x["tag"], x["t0"], x["ring"], r24, f36, x["meas_rip"] * x["Tp50"], x["meas_rip"], x["Tp50"]))

    # ------------------------------------------------------------------------------------------ the lever on the cliff / hand-on rows
    pr("\n" + "=" * 150)
    pr("LEVER 'postB flat to 2560 raw' on the HAND-ON rows (cliff / stall class): |T| p50 live vs lever, and frames with |tq| in [512,2560) / >= 2560")
    pr("=" * 150)
    for (tg_, t0, dur, fdom) in CLIFF:
        r = routes[tg_]; m100 = ep_frames(r, t0, dur)
        Tl = r.sim["live (m0 arm, live m, Kd)"]["T"][r.i100][m100]; Tf = r.sim["live, postB FLAT to 2560"]["T"][r.i100][m100]
        tqa = np.abs(r.tq_raw[m100])
        pr("  %s %6.1f (%3.1f s, fdom %.2f): |tq| p50 %4.0f | frames 512-2560: %.2f, >=2560: %.2f | |T| p50 live %4.0f -> lever %4.0f (x%.2f) | tap |T| p50 %4.0f | m live p50 %3.0f"
           % (tg_, t0, dur, fdom, np.median(tqa), np.mean((tqa >= 512) & (tqa < 2560)), np.mean(tqa >= 2560), np.median(np.abs(Tl)), np.median(np.abs(Tf)),
              np.median(np.abs(Tf)) / max(np.median(np.abs(Tl)), 1), np.median(np.abs(r.T_meas[m100])), np.median(r.mL[m100])))
    for tag, r in routes.items():
        e = r.eng & (r.idx > 0)
        Tl = r.sim["live (m0 arm, live m, Kd)"]["T"][r.i100]; Tf = r.sim["live, postB FLAT to 2560"]["T"][r.i100]
        hand = e & (np.abs(r.tq_raw) >= 1216)
        pr("  %s whole route engaged: |T| p50 live %4.0f -> lever %4.0f ; hands-on (|tq|>=1216, %.2f of frames): |T| p50 live %4.0f -> lever %4.0f ; frames T rail (3072) live %.4f lever %.4f"
           % (tag, np.median(np.abs(Tl[e])), np.median(np.abs(Tf[e])), np.mean(hand[e]), np.median(np.abs(Tl[hand])), np.median(np.abs(Tf[hand])),
              np.mean(np.abs(Tl[e]) >= 3072), np.mean(np.abs(Tf[e]) >= 3072)))

    # ------------------------------------------------------------------------------------------ r24: the engaged-only bar differentiator
    pr("\n" + "=" * 150)
    pr("r24 (FUN_0003aa2c) ON THE CAR: 0x3AA96 = 0xfb (stock 0xc5) => gate reads gp-0x6806 (engaged) => gainA = 0xC6446 = 5244 (stock 512), Q10.")
    pr("  r24 = clamp(-1 * deadband(clamp(0.5*(tq[n]-tq[n-4]), +-5120) * 5244 >> 10, 3), +-8192)  at 1 kHz on the 0x18F torque (raw = wire*1.024,")
    pr("  gp-0x4f60 = -(wire) * 1.024 by the frame builder FUN_00055C42, applied here).  Per F7 episode: 6-8.5 Hz amp of r24 (aggregator ct) vs the tap's T ripple; phase re T and re rate;")
    pr("  damping fraction = mean(sign(r24_bp) != sign(wire_bp)), the kit's T convention (positive counts push toward +wire rate).  Stock gain column = the same at 512.")
    pr("=" * 150)
    sos7 = signal.butter(4, [6.0, 8.5], btype="bandpass", fs=FS, output="sos")
    r24rows = []
    for tag in ("r32", "r33", "r34"):
        r = routes[tag]
        tq1k = np.round(r.up(r.tq_fw))                       # firmware-signed bar torque
        d = np.zeros_like(tq1k); d[4:] = 0.5 * (tq1k[4:] - tq1k[:-4])      # gp-0x4f62 (FUN_0007e74a: 2*(T[n]-T[n-4])/dt, dt = 4)
        d = np.clip(d, -5120, 5120)
        for gain, key in ((5244, "r24"), (512, "r24s")):
            x = np.floor(d * gain / 1024)
            x = np.where(np.abs(x) <= 3, 0.0, x - 3 * np.sign(x))
            x = np.clip(-x, -8192, 8192)
            x[~r.eng1k] = 0.0
            setattr(r, key, x[r.i100])
        eps = [(tag, t0, dd, f) for (t0, dd, f) in F7[tag]] + ([CONTROL] if tag == "r34" else [])
        for (tg_, t0, dur, fdom) in eps:
            m100 = ep_frames(r, t0, dur)
            if m100.sum() < 50:
                continue
            f0 = fdom if fdom >= 6 else 7.0
            Tm = r.T_meas[m100]; Tp50 = np.median(np.abs(Tm))
            a24, a24s, aT = bamp(r.r24[m100]), bamp(r.r24s[m100]), bamp(Tm)
            _, ph_T, _ = xspec(Tm, r.r24[m100], f0)
            _, ph_w, _ = xspec(r.wire[m100], r.r24[m100], f0)
            bp = lambda x: signal.sosfiltfilt(sos7, x)  # noqa: E731
            damp = np.mean(np.sign(bp(r.r24[m100])) != np.sign(bp(r.wire[m100])))       # kit convention: damping = sign(lane) != sign(0x18F rate)
            dampT = np.mean(np.sign(bp(Tm)) != np.sign(bp(r.wire[m100])))
            p90 = np.percentile(np.abs(r.r24[m100]), 90)
            r24rows.append(dict(tag=tg_, t0=t0, fdom=fdom, a24=a24, a24s=a24s, aT=aT, Tp50=Tp50, ph_T=ph_T, ph_w=ph_w, damp=damp, dampT=dampT, p90=p90))
            pr("  %s %6.1f f0 %.2f: r24 6-8.5 Hz amp %5.0f ct (stock gain %4.0f) | |r24| p90 %5.0f | T ripple %4.0f ct (|T| %4.0f) -> r24/T-ripple %.2f, r24/|T| %.2f | r24 re T %+4.0f deg, re rate %+4.0f | damp frac r24 %.2f (T %.2f)"
               % (tg_, t0, fdom, a24, a24s, p90, aT, Tp50, a24 / aT, a24 / Tp50, ph_T, ph_w, damp, dampT))
    f7r = [x for x in r24rows if x["fdom"] >= 6]
    pr("  F7 MEDIANS: r24 amp %.0f ct (stock-gain %.0f) | r24 / T ripple %.2f (min %.2f max %.2f) | r24 / |T| %.2f | r24 re T %+.0f | re rate %+.0f | damp frac r24 %.2f vs T %.2f"
       % (np.median([x["a24"] for x in f7r]), np.median([x["a24s"] for x in f7r]), np.median([x["a24"] / x["aT"] for x in f7r]), min(x["a24"] / x["aT"] for x in f7r),
          max(x["a24"] / x["aT"] for x in f7r), np.median([x["a24"] / x["Tp50"] for x in f7r]), np.median([x["ph_T"] for x in f7r]), np.median([x["ph_w"] for x in f7r]),
          np.median([x["damp"] for x in f7r]), np.median([x["dampT"] for x in f7r])))
    for tag, r in routes.items():
        e = r.eng
        pr("  %s whole route engaged: |r24| p50/p90/p99 %4.0f/%4.0f/%4.0f ct ; frames |r24| >= 8192 rail %.4f ; |T_meas| p50/p90 %4.0f/%4.0f"
           % (tag, np.median(np.abs(r.r24[e])), np.percentile(np.abs(r.r24[e]), 90), np.percentile(np.abs(r.r24[e]), 99), np.mean(np.abs(r.r24[e]) >= 8192),
              np.median(np.abs(r.T_meas[e])), np.percentile(np.abs(r.T_meas[e]), 90)))

    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", OUT_TXT)


if __name__ == "__main__":
    main()
