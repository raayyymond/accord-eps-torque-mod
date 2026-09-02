# -*- coding: utf-8 -*-
"""V280 map design: (1) the achieved column rate per build, from the wire; (2) NON-UNIFORM map profiles
through the exact LKAS rate-PID chain (FUN_00028ea6) on the V276 (r2e) and V278 rev 3 (r31) logs;
(3) Kp's own LERP as a shaping lever.

Chain (mirrors prereg_v278r3_saturation.py, which mirrors the decompile; addresses = V268):
  v    = clamp(((taper*255)&0xFFFF) * clamp(-4*cmd, +-16384) >> 16 >> 6, +-240)    LIMIT = 0xCB844[7]
  idx  = |v|                                                   -> gp-0x674b (map AND Kp index)
  sp   = sign(v) * LERP(mapY, idx)                             -> gp-0x6a32   (mapY = the build's slot-7 Y knots)
  fb   = clamp(s_old + s_new, +-FBCLAMP)   s_new = (923 s_old >> 10) + (1560 x >> 10), x = -0x18F wire, 1 kHz
  E    = 32 sp - fb ;  P = clamp(E*Kp(idx) >> 8, +-15360) ;  D = clamp(dE*128 >> 3, +-10240)
  S    = clamp(254*(P+D) >> 8, +-15360) ;  lag (992/507, readout >>5) ;  T = clamp(-lag*5346 >> 15, +-3072)
  tap  = sign(T)<<9 | |T|>>3 on CAN 427 in the ((d0&3)<<8)|d1 field  (rev 3; measured on r31 here)

Routes (analysis-2020accord/rlogs, raw CAN read; cache analysis-2020accord/_scratch/cache/v280/<tag>.npz):
  r97 = STOCK baseline (handoffs 2026-08-20/21/22)   r22/r23 = V112 (HANDOFF-2026-08-28)
  r2e = V276 (427 field == 35 = 7x5 on every frame)   r31 = V278 rev 3 (427 field is a signed torque, see main)

Run:  python analysis-2020accord/studies/v280/v280_map_profiles.py [--routes r97,r22,r23,r2e,r31]
"""
import argparse
import glob
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))                    # analysis-2020accord
RLOGS = os.path.join(ROOT, "rlogs")
CACHE = os.path.join(ROOT, "_scratch", "cache", "v280")
ROUTE_PREFIX = {"r97": "75604b0a432fdc89_00000097--489d7896b3", "r22": "75604b0a432fdc89_00000022--00f57626e0",
                "r23": "75604b0a432fdc89_00000023--fc5f268959", "r2e": "75604b0a432fdc89_0000002e--855ecfcf30",
                "r31": "75604b0a432fdc89_00000031--a680e9b2ac"}
ROUTE_BUILD = {"r97": "STOCK", "r22": "V112", "r23": "V112", "r2e": "V276 (map x6)", "r31": "V278r3 (map x2)"}
ROUTE_K = {"r97": 1.0, "r22": 1.0, "r23": 1.0, "r2e": 6.0, "r31": 2.0}     # the map factor ON THE CAR for that route

FS, FS1K = 100.0, 1000.0
MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
MAP_Y = np.array([0, 24, 42, 50, 62, 100, 126, 154, 166, 172], float)     # slot 7 @0xE502C, stock
KP_X = np.array([0, 68, 112, 136, 208], float)
KP_Y = np.array([248, 512, 645, 696, 696], float)                          # @0xE5378, stock
KD = 128
TAPER_X = np.array([70, 72, 78, 80], float)
TAPER_Y = np.array([254, 234, 12, 0], float)
LIMIT, IDX_CLAMP = 16384, 240
A_COEF, B_COEF = 923, 1560
OA, OB = 992, 507
FB_CLAMP_STOCK = 7680
P_CLAMP, D_CLAMP, SUM_CLAMP = 15360, 10240, 15360
GAIN, OUT_CAP = 5346, 3072
SUM_MULT = 254
FB_DC = 2 * B_COEF / (1024 - A_COEF)         # 30.89 per raw count
CPD = 8.0                                    # raw counts per deg/s on the 0x18F rate wire
SAT_THR = 2472                               # one tap LSB under the 2481 rail


# ----------------------------------------------------------------------------------------------------
# raw CAN read (a guarded copy of osc-2to4/direct_read_v276.read_route: a truncated last segment is skipped)
# ----------------------------------------------------------------------------------------------------
def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def read_route(prefix):
    import zstandard
    sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "rlog-tools"))
    from cereal import log as clog
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    t18, tq, rate, sca, t14, ang, t1ab, b0, b1, te4, cmd, req, tcs, vego = ([] for _ in range(14))
    for p in segs:
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:                       # truncated tail segment
                print("  truncated: %s" % str(e)[:60]); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    d = bytes(m.dat)
                    if m.src == 1:
                        if m.address == 0x18F and len(d) >= 5:
                            t18.append(tm); tq.append(i16be(d, 0)); rate.append(i16be(d, 2)); sca.append((d[4] >> 3) & 1)
                        elif m.address == 0x14A and len(d) >= 4:
                            t14.append(tm); ang.append(i16be(d, 0) * -0.1)
                        elif m.address == 0x1AB and len(d) >= 2:
                            t1ab.append(tm); b0.append(d[0]); b1.append(d[1])
                    elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                        te4.append(tm); cmd.append(i16be(d, 0)); req.append((d[2] >> 7) & 1)
            elif w == "carState":
                tcs.append(tm); vego.append(evt.carState.vEgo)
        print("  read %s" % os.path.basename(p), flush=True)
    A = lambda x, dt=float: np.asarray(x, dt)              # noqa: E731
    return dict(t18=A(t18), tq=A(tq), rate=A(rate), sca=A(sca, int), t14=A(t14), ang=A(ang),
                t1ab=A(t1ab), b0=A(b0, int), b1=A(b1, int), te4=A(te4), cmd=A(cmd), req=A(req, int),
                tcs=A(tcs), vego=A(vego))


def load(tag):
    f = os.path.join(CACHE, tag + ".npz")
    if not os.path.exists(f):
        os.makedirs(CACHE, exist_ok=True)
        D = read_route(ROUTE_PREFIX[tag]); np.savez(f, **D)
    D = dict(np.load(f))
    t0 = D["t18"][0]
    T = D["t18"] - t0
    tg = np.arange(0.0, T[-1], 1 / FS)
    g = dict(tg=tg)
    g["wire"] = np.interp(tg, T, D["rate"])
    g["tq_raw"] = np.interp(tg, T, D["tq"] * 1.024)
    g["sca"] = np.interp(tg, T, D["sca"]) > 0.5
    g["req"] = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    g["cmd"] = np.interp(tg, D["te4"] - t0, D["cmd"])
    g["vego"] = np.interp(tg, D["tcs"] - t0, D["vego"])
    g["eng"] = g["sca"] & g["req"]
    if "b1" in D and tag == "r31":                           # signed torque tap: ONLY rev 3 / V279 rev 2 carry it
        fld = ((D["b0"] & 3) << 8) | D["b1"]
        Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
        g["T_meas"] = np.interp(tg, D["t1ab"] - t0, Tm)
        g["fld"] = fld
    elif "sel" in D:
        g["sel"] = D["sel"]
    return g


# ----------------------------------------------------------------------------------------------------
# the chain
# ----------------------------------------------------------------------------------------------------
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
    s = signal.lfilter([OB / 1024.0], [1.0, -OA / 1024.0], u)
    return (np.r_[0.0, s[:-1]] + s) / 32.0


def episodes(wire, eng):
    """Same criterion as dose_e_sign_by_k.py: 2.5-6 Hz envelope > max(2.5 x p95 of the disengaged envelope, 150)."""
    sos = signal.butter(4, [2.5, 6.0], btype="bandpass", fs=FS, output="sos")
    rb = signal.sosfiltfilt(sos, wire)
    env = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb)))
    thr = max(2.5 * np.percentile(env[~eng], 95), 150.0) if (~eng).sum() > 100 else 150.0
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
    return osc, merged, thr


class Route:
    def __init__(self, tag):
        self.tag = tag
        g = load(tag)
        self.__dict__.update(g)
        self.osc, self.eps, self.thr = episodes(self.wire, self.eng)
        self.normal = self.eng & ~self.osc
        self.idx, self.sgn = demand(self.cmd, self.tq_raw)
        n = len(self.tg)
        self.t1k = np.arange(0, n / FS, 1 / FS1K)
        up = lambda a: np.interp(self.t1k, self.tg, a)      # noqa: E731
        self.up = up
        self.fb_un = feedback_1khz(-up(self.wire))
        self.idx1k = np.round(up(self.idx))
        s = np.sign(up(self.sgn)); s[s == 0] = 1
        self.sgn1k = s
        self.eng1k = up(self.eng.astype(float)) > 0.5
        self.osc1k = up(self.osc.astype(float)) > 0.5
        self.nor1k = self.eng1k & ~self.osc1k
        self.i100 = np.clip(np.round(self.tg * FS1K).astype(int), 0, len(self.t1k) - 1)

    def simulate(self, mapY, kpY=KP_Y, fb_clamp=FB_CLAMP_STOCK, kd=KD):
        y = lerp(MAP_X, mapY, self.idx1k)
        kp = lerp(KP_X, kpY, self.idx1k)
        sp = self.sgn1k * y
        fb = np.clip(self.fb_un, -fb_clamp, fb_clamp)
        E = 32 * sp - fb
        P_raw = np.floor(E * kp / 256)
        P = np.clip(P_raw, -P_CLAMP, P_CLAMP)
        dE = np.r_[0.0, np.diff(E)]
        onset = self.eng1k & ~np.r_[False, self.eng1k[:-1]]
        dE[onset] = 0.0
        D_raw = np.floor(dE * kd / 8)
        Dt = np.clip(D_raw, -D_CLAMP, D_CLAMP)
        S_raw = np.floor(SUM_MULT * (P + Dt) / 256)
        S = np.clip(S_raw, -SUM_CLAMP, SUM_CLAMP)
        S[~self.eng1k] = 0.0
        lag = output_lag(S)
        T = np.clip(np.floor(-lag * GAIN / 32768), -OUT_CAP, OUT_CAP)
        return dict(E=E, P_raw=P_raw, D_raw=D_raw, S_raw=S_raw, T=T, fb=fb, sp=sp)

    def metrics(self, R, m1k, m100):
        E, fb, T = R["E"], R["fb"], R["T"]
        Tc = T[self.i100]
        mm = m1k & (fb != 0)
        out = dict(n100=int(m100.sum()))
        out["damp_E"] = np.mean(np.sign(E[mm]) != np.sign(fb[mm])) if mm.any() else np.nan
        w = self.wire[m100]
        mt = (Tc[m100] != 0) & (w != 0)
        out["damp_T"] = np.mean(np.sign(Tc[m100][mt]) != np.sign(w[mt])) if mt.any() else np.nan
        out["p_rail"] = np.mean(np.abs(R["P_raw"][m1k]) >= P_CLAMP)
        out["d_rail"] = np.mean(np.abs(R["D_raw"][m1k]) > D_CLAMP)
        out["s_rail"] = np.mean(np.abs(R["S_raw"][m1k]) >= SUM_CLAMP)
        out["sat"] = np.mean(np.abs(Tc[m100]) >= SAT_THR)
        out["T_p50"] = np.median(np.abs(Tc[m100])); out["T_p90"] = np.percentile(np.abs(Tc[m100]), 90)
        out["fb_dom"] = np.mean(np.abs(fb[m1k]) > 32 * np.abs(R["sp"][m1k]))
        return out


# ----------------------------------------------------------------------------------------------------
# map profiles: K(x) at the ten slot-7 X knots; Y_new = round(Y_stock * K(x))
# ----------------------------------------------------------------------------------------------------
def profile(k_lo, x_knee, k_top, x_top=240.0):
    """K = k_lo up to idx x_knee, linear to k_top at idx x_top, flat after."""
    def K(x):
        x = np.asarray(x, float)
        if x_top <= x_knee:
            return np.where(x >= x_top, float(k_top), float(k_lo))
        return np.where(x <= x_knee, k_lo,
                        np.where(x >= x_top, k_top, k_lo + (k_top - k_lo) * (x - x_knee) / (x_top - x_knee)))
    return K


PROFILES = [
    ("U1 stock", profile(1, 240, 1)),
    ("U2 (V278r3)", profile(2, 240, 2)),
    ("U3", profile(3, 240, 3)),
    ("U6 (V276)", profile(6, 240, 6)),
    ("2@32->4", profile(2, 32, 4)),
    ("2@32->6", profile(2, 32, 6)),
    ("2@64->4", profile(2, 64, 4)),
    ("2@64->6", profile(2, 64, 6)),
    ("2@96->4", profile(2, 96, 4)),
    ("2@96->6", profile(2, 96, 6)),
    ("2@64->6@160", profile(2, 64, 6, 160)),
    ("2@128->6", profile(2, 128, 6)),
    ("2@160->6", profile(2, 160, 6)),
]


def map_knots(K):
    return np.round(MAP_Y * K(MAP_X))


def ceiling_degs(mapY):
    return 32 * mapY[-1] / FB_DC / CPD


# ----------------------------------------------------------------------------------------------------
def part1_rates(routes):
    print("\n" + "=" * 110)
    print("PART 1 -- ACHIEVED COLUMN RATE ON THE WIRE (0x18F b2-3 / 8 = deg/s), engaged frames (STEER_CONTROL_ACTIVE & STEER_REQUEST)")
    print("=" * 110)
    print("%-5s %-16s %7s %7s | %6s %6s %6s | %6s %6s %6s | %s" %
          ("route", "build", "eng_s", "ceil", "p95", "p99", "max", "p95L", "p99L", "maxL", "idx p50/p90/max, frac idx=240 | idx at top-20 |rate| frames (LKAS-driven)"))
    print("   ceil = 32*Y(240)*K/30.89/8 = the map-set crossover rate;  L = LKAS-driven subset: |tq_raw| < 2240 AND sign(rate) == sign(setpoint)")
    for r in routes:
        e = r.eng
        w = np.abs(r.wire) / CPD
        K = ROUTE_K[r.tag]
        # LKAS-driven: wheel moving in the setpoint's direction with the driver's hands light.
        # sign convention: gp-0x6a56 = -wire, fb ~ +30.89 * gp-0x6a56; the lane pushes the wheel until fb = 32 sp,
        # i.e. gp-0x6a56 has the sign of sp  =>  wire has sign -sp.
        drv = e & (np.abs(r.tq_raw) < 2240) & (np.sign(-r.wire) == r.sgn) & (r.idx > 0)
        top = np.argsort(-(w * drv))[:20]
        line = "%-5s %-16s %7.0f %7.1f | %6.1f %6.1f %6.1f | %6.1f %6.1f %6.1f | %3.0f/%3.0f/%3.0f %.3f | %s" % (
            r.tag, ROUTE_BUILD[r.tag], e.sum() / FS, ceiling_degs(MAP_Y * K),
            np.percentile(w[e], 95), np.percentile(w[e], 99), w[e].max(),
            np.percentile(w[drv], 95), np.percentile(w[drv], 99), w[drv].max(),
            np.median(r.idx[e]), np.percentile(r.idx[e], 90), r.idx[e].max(), np.mean(r.idx[e] >= 240),
            " ".join("%d" % v for v in sorted(r.idx[top])))
        print(line)
    print("\n  rate CONDITIONAL on demand index, LKAS-driven frames:  n | |rate| p50 / p90 / max  (deg/s)")
    bins = [(0, 32), (32, 64), (64, 128), (128, 200), (200, 240), (240, 241)]
    print("%-5s " % "route" + " ".join("%-24s" % ("idx[%d,%d)" % b if b[1] < 241 else "idx=240") for b in bins))
    for r in routes:
        w = np.abs(r.wire) / CPD
        drv = r.eng & (np.abs(r.tq_raw) < 2240) & (np.sign(-r.wire) == r.sgn)
        cells = []
        for lo, hi in bins:
            m = drv & (r.idx >= lo) & (r.idx < hi)
            cells.append("%5d %5.1f/%5.1f/%5.1f" % (m.sum(), np.median(w[m]), np.percentile(w[m], 90), w[m].max()) if m.sum() > 20 else "%5d  --" % m.sum())
        print("%-5s " % r.tag + " ".join("%-24s" % c for c in cells))
    print("\n  demand index histogram, engaged frames (%% of engaged):  " + "  ".join("[%d,%d)" % b if b[1] < 241 else "=240" for b in bins))
    for r in routes:
        e = r.eng
        print("  %-5s %-16s " % (r.tag, ROUTE_BUILD[r.tag]) + "  ".join("%6.1f" % (100 * np.mean((r.idx[e] >= lo) & (r.idx[e] < hi))) for lo, hi in bins)
              + "   |cmd| p50/p90/max %4.0f/%4.0f/%4.0f" % (np.median(np.abs(r.cmd[e])), np.percentile(np.abs(r.cmd[e]), 90), np.abs(r.cmd[e]).max()))


def runs(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    out = np.zeros_like(mask)
    for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        if b - a >= minlen:
            out[a:b] = True
    return out


def part1c_sustained(routes):
    """The decisive table: FULL demand held >= 0.3 s, wheel moving WITH the setpoint, driver torque below a ceiling.
    At parking speeds the driver turns the wheel with < 2240 raw, so the |tq| ceiling is swept down to 200."""
    print("\n  SUSTAINED FULL DEMAND (idx = 240 for >= 0.3 s), wheel moving WITH the setpoint, by driver-torque ceiling: n | rate p50/p90 deg/s")
    print("  (every such frame on every route is below 10 m/s; the manual arm below 10 m/s is the driver's own rate for scale)")
    for r in routes:
        w = np.abs(r.wire) / CPD
        base = r.eng & (np.sign(-r.wire) == r.sgn) & runs(r.idx >= 240, 30)
        cells = []
        for thr in (2240, 1000, 400, 200):
            m = base & (np.abs(r.tq_raw) < thr)
            cells.append("<%4d: n=%4d %5.1f/%5.1f" % (thr, m.sum(), np.median(w[m]) if m.sum() else 0, np.percentile(w[m], 90) if m.sum() else 0))
        man = (~r.eng) & (r.vego < 10) & (r.vego > 0.5)
        extra = ""
        if hasattr(r, "T_meas"):
            m = base & (np.abs(r.tq_raw) < 400)
            Tm = np.abs(r.T_meas[m])
            extra = " | tap |T| p50/p90 %.0f/%.0f (rail 2481), rate > ceil %.2f, sign(T)==sign(sp) %.2f" % (
                np.median(Tm), np.percentile(Tm, 90), np.mean(w[m] > ceiling_degs(MAP_Y * ROUTE_K[r.tag])), np.mean(np.sign(r.T_meas[m]) == r.sgn[m]))
        print("  %-4s %-16s ceil %5.1f | " % (r.tag, ROUTE_BUILD[r.tag], ceiling_degs(MAP_Y * ROUTE_K[r.tag])) + " | ".join(cells)
              + " | manual v<10: %.1f/%.1f" % (np.median(w[man]), np.percentile(w[man], 90)) + extra)


def part1b_tap_check(r31):
    """The rev-3 tap on r31 against the chain simulated with the rev-3 cells (K=2, clamp 15360)."""
    if not hasattr(r31, "T_meas"):
        return
    print("\n--- r31: the delivered-torque tap vs the chain (validates the simulation ON THE WIRE) ---")
    R = r31.simulate(map_knots(profile(2, 240, 2)), fb_clamp=15360)
    Ts = R["T"][r31.i100]
    e = r31.eng
    Tm = r31.T_meas
    print("  427 field: b0 in %s, |T| max %d (rail 2481 -> tap 310), sign-bit duty %.3f" %
          (np.unique(r31.fld >> 8), (np.abs(Tm)).max(), np.mean(r31.fld >= 512)))
    for lab, s in (("sim T = +T_meas", 1), ("sim T = -T_meas", -1)):
        c = np.corrcoef(Ts[e], s * Tm[e])[0, 1]
        agree = np.mean(np.sign(Ts[e]) == np.sign(s * Tm[e]))
        print("  %s: corr %.3f, sign agreement %.3f" % (lab, c, agree))
    w = r31.wire[e]; mt = (Tm[e] != 0) & (w != 0)
    print("  MEASURED damping P(sign(T_meas) != sign(wire)) engaged = %.3f ; P(==) = %.3f  (pre-registered K=2 normal: 0.60 for '!=')"
          % (np.mean(np.sign(Tm[e][mt]) != np.sign(w[mt])), np.mean(np.sign(Tm[e][mt]) == np.sign(w[mt]))))
    print("  MEASURED saturation P(|T_meas| >= 2472) = %.4f ; |T_meas| p50/p90/p99 = %.0f/%.0f/%.0f ; sim |T| p50/p90/p99 = %.0f/%.0f/%.0f"
          % (np.mean(np.abs(Tm[e]) >= SAT_THR), np.median(np.abs(Tm[e])), np.percentile(np.abs(Tm[e]), 90), np.percentile(np.abs(Tm[e]), 99),
             np.median(np.abs(Ts[e])), np.percentile(np.abs(Ts[e]), 90), np.percentile(np.abs(Ts[e]), 99)))
    for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 20), (20, 99)):
        mm = e & (r31.vego >= lo) & (r31.vego < hi)
        if mm.sum() < 200:
            continue
        sl = np.sum(Ts[mm] * Tm[mm]) / np.sum(Ts[mm] ** 2)
        print("  T_meas vs T_sim, vego [%2d,%2d): n=%5d  LS slope %.3f  corr %.3f  |T_meas| p90 %4.0f  |T_sim| p90 %4.0f   (sim assumes post-sum multiplier 254/256)"
              % (lo, hi, mm.sum(), sl, np.corrcoef(Ts[mm], Tm[mm])[0, 1], np.percentile(np.abs(Tm[mm]), 90), np.percentile(np.abs(Ts[mm]), 90)))
    # delivered torque vs demand index (the surface the operator feels), measured
    print("  T_meas vs idx (LKAS-driven, |tq_raw|<2240): " + "  ".join(
        "idx[%d,%d) n=%d |T| p50 %.0f" % (lo, hi, m.sum(), np.median(np.abs(Tm[m])) if m.sum() else 0)
        for lo, hi in ((0, 32), (32, 64), (64, 128), (128, 241))
        for m in [e & (np.abs(r31.tq_raw) < 2240) & (r31.idx >= lo) & (r31.idx < hi)]))


def part2_profiles(r2e, r31):
    print("\n" + "=" * 110)
    print("PART 2 -- MAP PROFILES through the chain.  damp_E = P(sign(E) != sign(fb)) [rev-2 comparator], damp_T = P(sign(T) != sign(wire)) [the rev-3 tap]")
    print("          fb clamp 0xC62E6 = 7680 x K_top (ratio 1.395 to 32*Y(240) preserved);  Drail = P(|dE*16| > 10240) on engaged 1 kHz ticks")
    print("=" * 110)
    hdr = "%-13s %-5s %6s %7s | %6s %6s %6s %6s | %6s %6s %6s | %6s %6s %6s %6s | %6s %6s" % (
        "profile", "Ktop", "Y240", "ceil", "dE_osc", "dT_osc", "dE_nrm", "dT_nrm", "dE_r31", "dT_r31", "fbdom",
        "Drl2e", "Drl31", "Prl2e", "Prl31", "sat2e", "sat31")
    print(hdr)
    rows = []
    for name, K in PROFILES:
        Y = map_knots(K)
        ktop = K(240.0)
        clamp = FB_CLAMP_STOCK * ktop
        R2 = r2e.simulate(Y, fb_clamp=clamp)
        R3 = r31.simulate(Y, fb_clamp=clamp)
        o = r2e.metrics(R2, r2e.osc1k, r2e.osc)
        n = r2e.metrics(R2, r2e.nor1k, r2e.normal)
        m3 = r31.metrics(R3, r31.eng1k, r31.eng)
        rows.append((name, ktop, Y, o, n, m3))
        print("%-13s %-5.1f %6d %7.1f | %6.3f %6.3f %6.3f %6.3f | %6.3f %6.3f %6.3f | %6.4f %6.4f %6.3f %6.3f | %6.3f %6.3f" % (
            name, ktop, Y[-1], ceiling_degs(Y), o["damp_E"], o["damp_T"], n["damp_E"], n["damp_T"],
            m3["damp_E"], m3["damp_T"], m3["fb_dom"], o["d_rail"], m3["d_rail"], o["p_rail"], m3["p_rail"], o["sat"], m3["sat"]))
    print("\n  knots (Y at X = %s):" % ", ".join("%d" % x for x in MAP_X))
    for name, ktop, Y, o, n, m3 in rows:
        print("   %-13s %s" % (name, " ".join("%4d" % y for y in Y)))
    # ranking
    print("\n  RANKING: highest ceiling crossover with damp_E(V276 ringing frames) >= 0.86 (the K=2 value that flew clean):")
    ok = [(ceiling_degs(Y), name, o["damp_E"], o["damp_T"], n["damp_E"]) for name, ktop, Y, o, n, m3 in rows if o["damp_E"] >= 0.86 - 1e-9]
    for c, name, dE, dT, dEn in sorted(ok, reverse=True):
        print("   %-13s ceiling %6.1f deg/s  damp_E osc %.3f  damp_T osc %.3f  damp_E normal %.3f" % (name, c, dE, dT, dEn))
    bad = [(ceiling_degs(Y), name, o["damp_E"]) for name, ktop, Y, o, n, m3 in rows if o["damp_E"] < 0.86 - 1e-9]
    print("  FAIL the 0.86 gate: " + ", ".join("%s (%.3f)" % (nm, d) for c, nm, d in sorted(bad, reverse=True)))
    # where the ringing frames live on the map, and why the top does not matter to them
    print("\n  V276 ringing frames: demand idx p50 %.0f p90 %.0f p99 %.0f max %.0f; normal engaged r2e: p50 %.0f p90 %.0f; r31 engaged: p50 %.0f p90 %.0f p99 %.0f" % (
        np.median(r2e.idx[r2e.osc]), np.percentile(r2e.idx[r2e.osc], 90), np.percentile(r2e.idx[r2e.osc], 99), r2e.idx[r2e.osc].max(),
        np.median(r2e.idx[r2e.normal]), np.percentile(r2e.idx[r2e.normal], 90),
        np.median(r31.idx[r31.eng]), np.percentile(r31.idx[r31.eng], 90), np.percentile(r31.idx[r31.eng], 99)))
    # the clamp question: profiles with clamp held at 15360 (V278r3's) instead of 7680*Ktop
    print("\n  fb clamp sensitivity (clamp = 15360 for every profile, i.e. NOT raised with K_top):")
    for name, K in PROFILES:
        if K(240.0) <= 2:
            continue
        Y = map_knots(K)
        R2 = r2e.simulate(Y, fb_clamp=15360); R3 = r31.simulate(Y, fb_clamp=15360)
        o = r2e.metrics(R2, r2e.osc1k, r2e.osc); m3 = r31.metrics(R3, r31.eng1k, r31.eng)
        # the crossover the clamp imposes: E can only reach 0 at full demand if 32*Y(240) <= clamp
        print("   %-13s clamp 15360 vs 32*Y240 = %5d: %s ; damp_E osc %.3f (vs %.3f at 7680*Ktop) ; r31 damp_E %.3f ; fb-clamp railed r31 %.4f" % (
            name, 32 * Y[-1], "CLAMP SETS THE CEILING (fb rails before E crosses zero: crossover = %.1f deg/s)" % (15360 / FB_DC / CPD) if 32 * Y[-1] > 15360 else "map sets the ceiling",
            o["damp_E"], [r for r in rows if r[0] == name][0][3]["damp_E"], m3["damp_E"], np.mean(np.abs(R3["fb"][r31.eng1k]) >= 15360)))
    return rows


def part3_kp(r2e, r31):
    print("\n" + "=" * 110)
    print("PART 3 -- Kp's LERP (X 0,68,112,136,208 / Y 248,512,645,696,696): what it already shapes, and lowering it at low idx")
    print("=" * 110)
    for i, x in enumerate((0, 12, 22, 32, 64, 96, 128, 160, 240)):
        print("   idx %3d: Kp %4.0f  (x%.2f of Kp(136))  stock map slope %.2f Y/idx" % (
            x, lerp(KP_X, KP_Y, x), lerp(KP_X, KP_Y, x) / 696, np.gradient(lerp(MAP_X, MAP_Y, np.arange(241)))[x]))
    print("   the E-comparator is Kp-BLIND (Kp > 0 multiplies E, sign unchanged); Kp changes |P| relative to D (= 16 dE, Kp-free) and the loop gain.")
    variants = [
        ("Kp stock", KP_Y),
        ("Kp flat 248", np.array([248, 248, 248, 248, 248.0])),
        ("Kp low-idx /2", np.array([124, 256, 645, 696, 696.0])),
        ("Kp low-idx /2, flat 696 by 136", np.array([124, 256, 645, 696, 696.0])),
        ("Kp flat 696", np.array([696, 696, 696, 696, 696.0])),
    ]
    print("%-32s %-13s | %6s %6s %6s | %6s %6s %6s | %s" % ("Kp variant", "map", "dE_osc", "dT_osc", "dT_nrm", "dT_r31", "Prl2e", "sat31", "|T| p50 osc / r31"))
    for mname, K in (("U2 (V278r3)", profile(2, 240, 2)), ("2@64->6", profile(2, 64, 6)), ("U6 (V276)", profile(6, 240, 6))):
        Y = map_knots(K); clamp = FB_CLAMP_STOCK * K(240.0)
        for vname, kpY in variants[:3] + variants[4:]:
            R2 = r2e.simulate(Y, kpY=kpY, fb_clamp=clamp); R3 = r31.simulate(Y, kpY=kpY, fb_clamp=clamp)
            o = r2e.metrics(R2, r2e.osc1k, r2e.osc); n = r2e.metrics(R2, r2e.nor1k, r2e.normal); m3 = r31.metrics(R3, r31.eng1k, r31.eng)
            print("%-32s %-13s | %6.3f %6.3f %6.3f | %6.3f %6.3f %6.3f | %5.0f / %5.0f" % (
                vname, mname, o["damp_E"], o["damp_T"], n["damp_T"], m3["damp_T"], o["p_rail"], m3["sat"], o["T_p50"], m3["T_p50"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--routes", default="r97,r22,r23,r2e,r31")
    a = ap.parse_args()
    tags = [t.strip() for t in a.routes.split(",") if t.strip()]
    routes = []
    for t in tags:
        print("loading %s (%s) ..." % (t, ROUTE_BUILD[t]), flush=True)
        routes.append(Route(t))
    by = {r.tag: r for r in routes}
    for r in routes:
        print("  %s: %d episodes (%.1f s ringing), engaged %.1f s, threshold %.0f wire, vego engaged p50 %.1f m/s" % (
            r.tag, len(r.eps), r.osc.sum() / FS, r.eng.sum() / FS, r.thr, np.median(r.vego[r.eng])))
    part1_rates(routes)
    part1c_sustained(routes)
    if "r31" in by:
        part1b_tap_check(by["r31"])
    if "r2e" in by and "r31" in by:
        part2_profiles(by["r2e"], by["r31"])
        part3_kp(by["r2e"], by["r31"])


if __name__ == "__main__":
    main()
