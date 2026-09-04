# -*- coding: utf-8 -*-
"""studies/osc-highangle/v283_read_r36_r38.py -- the pre-registered read of V283 (V282 + the LKAS rate-PID
INTEGRAL GAIN 0xC63E6 0 -> 50) on routes r36/r37/r38, scored EXACTLY as PREREG-V283-READ.md (a)-(i), with
r35 (V281 rev 3, the like-for-like Ki-0 baseline) and r34 (V280 rev 2) as controls.
Subagent v283read, 2026-09-03.  Companion: V283-READ-r36-r38-2026-09-03.md.

Sections
  0  THE TUNE ON THE WIRE.  No toggle backup was supplied for these drives, so every StarPilot parameter is
     BACK-CALCULATED from the log the way v281r3_read_r35.py sec.0 does: LAF = -(p+i+d+f)/output, kp = p/error,
     friction from a regression of f, liveParameters.steerRatio, and the controller-vs-road lat-accel ratio.
  1  BUILD ATTRIBUTION FROM THE TAP, not from the label.  Three independent instruments:
       1a  Ki fitted from the CAN-427 delivered-torque tap by a WINDOW-LOCAL linear regression (the slope IS Ki)
       1b  the Kp table (stock LERP / flat 248 / superseded rev-2 341) by window-local corr and scale
       1c  V282's 0x14A byte-4 comparator bits: present and non-degenerate, or absent
  2  PREREG-V283-READ.md (a)-(i), thresholds EXACTLY as registered
  3  WHAT THE INTEGRATOR ACTUALLY DID: wind-up rate, the rail, stall release, disengage clearing, and the
     0.2-1 Hz straight-road hunt the prereg named as the Cost-FAIL signature
  4  the operator's "consistently oversteers" report: curve_oversteer_r34.py bins, r34 / r35 / r36 / r37 / r38

Run: python v283_read_r36_r38.py
  caches: analysis-2020accord/_scratch/cache/v280/r3{4..8}.npz and r3{4..8}_b4.npz
          analysis-2020accord/studies/optune/_scratch/r3{4..8}_backcalc.npz
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import strongturn_r34 as S34            # noqa: E402  (registers r32/r33/r34; patches V.load with the 427 tap)
import curve_oversteer_r34 as CO        # noqa: E402
import backcalc_laf_friction as B       # noqa: E402

V, ST = S34.V, S34.ST
FS, FS1K, CPD = ST.FS, V.FS1K, V.CPD

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ------------------------------------------------------------------------------------------- registration
PREFIX = {"r35": "75604b0a432fdc89_00000035--580292087d",
          "r36": "75604b0a432fdc89_00000036--f4be1a18e9",
          "r37": "75604b0a432fdc89_00000037--4a79da5d18",
          "r38": "75604b0a432fdc89_00000038--f77bddf4bd"}
BUILD = {"r34": "V280 rev 2 (stock Kp LERP, Ki 0)", "r35": "V281 rev 3 (Kp flat 248, Ki 0)",
         "r36": "V283 claimed", "r37": "V283 claimed", "r38": "V283 claimed"}
for t, p in PREFIX.items():
    V.ROUTE_PREFIX[t] = p; V.ROUTE_BUILD[t] = BUILD[t]; V.ROUTE_K[t] = 6.0; ST.TAP_TAGS.add(t)
CO.LAF.update({t: 2.11 for t in ("r35", "r36", "r37", "r38")})

NEW = ("r36", "r37", "r38")
ALL = ("r34", "r35") + NEW
V280R2 = ST.V280R2                                   # (map Y knots, fb clamp 46080)
KP_STOCK = (V.KP_X, V.KP_Y)                          # 248, 512, 645, 696, 696
KP_FLAT = (V.KP_X, np.full(5, 248.0))                # V281 rev 3 / V282 / V283
KP_R2 = (V.KP_X, np.array([248, 341, 341, 341, 341], float))     # superseded V281 rev 2
KP_OF = {"r34": KP_STOCK, "r35": KP_FLAT, "r36": KP_FLAT, "r37": KP_FLAT, "r38": KP_FLAT}
KI_OF = {"r34": 0, "r35": 0, "r36": 50, "r37": 50, "r38": 50}    # set by section 1; these are the CLAIMS

# the integral arithmetic, from the decompile of FUN_00028ea6 (build_v283_tva.py docstring / ki_sizing.py):
#   excess = deadband(E >> 5, 0xC62E4 = 4) ; acc = clamp(acc + ((excess*Ki) >> 3), +-0xC61BA*128) ; I = acc >> 7
I_CLAMP, DEADBAND = 10240, 4
GK = (V.SUM_MULT / 256.0) * (ST.GAIN / 32768.0)      # sum multiplier * output gain: T = -GK * lag(S_pre)
CACHE = V.CACHE
LINES = []


def pr(s=""):
    print(s); LINES.append(s)


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def runs_of(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def band_amp(x, lo=6.0, hi=8.5):
    return ST.band_amp(np.asarray(x, float), lo, hi) if len(x) > 40 else np.nan


def excess_of(E):
    """deadband(E >> 5, 4) -- sar is an arithmetic shift, i.e. floor division."""
    ex = np.floor(E / 32.0)
    return np.sign(ex) * np.maximum(np.abs(ex) - DEADBAND, 0.0)


def accum(E, eng1k, ki):
    """the real accumulator: acc = clamp(acc + floor(excess*Ki/8), +-I_CLAMP*128) ; I = floor(acc/128).
    Cleared whenever not engaged (0x2A164, the single live writer)."""
    if ki == 0:
        return np.zeros_like(E)
    step = np.floor(excess_of(E) * ki / 8.0)
    lim = I_CLAMP * 128.0
    acc = np.empty_like(E); a = 0.0
    for i in range(len(E)):
        a = 0.0 if not eng1k[i] else min(max(a + step[i], -lim), lim)
        acc[i] = a
    return np.floor(acc / 128.0)


def unit_J(E, eng1k):
    """the accumulator at Ki = 1, UNCLAMPED -- the linear predictor whose regression slope is Ki."""
    step = excess_of(E) / 8.0
    acc = np.empty_like(E); a = 0.0
    for i in range(len(E)):
        a = 0.0 if not eng1k[i] else a + step[i]
        acc[i] = a
    return acc / 128.0


def sim(r, kp, ki, Y=None, clamp=None, kd=V.KD):
    """FUN_00028ea6 mirrored exactly, open loop on the MEASURED 0x18F rate, with the integral term."""
    Y = V280R2[0] if Y is None else Y
    clamp = V280R2[1] if clamp is None else clamp
    V.GAIN, V.OUT_CAP = ST.GAIN, ST.CAP
    y = V.lerp(V.MAP_X, Y, r.idx1k)
    kpv = V.lerp(kp[0], kp[1], r.idx1k)
    sp = r.sgn1k * y
    fb = np.clip(r.fb_un, -clamp, clamp)
    E = 32 * sp - fb
    P_raw = np.floor(E * kpv / 256)
    P = np.clip(P_raw, -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    dE[r.eng1k & ~np.r_[False, r.eng1k[:-1]]] = 0.0
    D_raw = np.floor(dE * kd / 8)
    Dt = np.clip(D_raw, -V.D_CLAMP, V.D_CLAMP)
    I = accum(E, r.eng1k, ki)
    S_raw = np.floor(V.SUM_MULT * np.clip(I + P + Dt, -V.SUM_CLAMP, V.SUM_CLAMP) / 256)
    S = np.clip(S_raw, -V.SUM_CLAMP, V.SUM_CLAMP)
    S[~r.eng1k] = 0.0
    lag = V.output_lag(S)
    T = np.clip(np.floor(-lag * ST.GAIN / 32768), -ST.CAP, ST.CAP)
    R = dict(E=E, P_raw=P_raw, P=P, D=Dt, I=I, S_raw=S_raw, T=T, fb=fb, sp=sp, kp=kpv)
    R["clamped"] = np.abs(r.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(sp) / V.FB_DC / CPD
    return R


def load_b4(tag, r):
    f = os.path.join(CACHE, tag + "_b4.npz")
    if not os.path.exists(f):
        return None
    B4 = dict(np.load(f))
    t0 = dict(np.load(os.path.join(CACHE, tag + ".npz")))["t18"][0]
    j = np.clip(np.searchsorted(B4["t14b"] - t0, r.tg), 0, len(B4["b4"]) - 1)
    return B4["b4"].astype(int)[j]


# ------------------------------------------------------------------------------------------- 0. the tune
def section0(grids):
    pr("=" * 165)
    pr("SECTION 0 -- THE STARPILOT TUNE, BACK-CALCULATED FROM THE WIRE.  No toggle backup was supplied for r36/r37/r38,")
    pr("  so NOTHING here is assumed: LAF = -(p+i+d+f)/output, kp = p/error, friction from a regression of f,")
    pr("  liveParameters.steerRatio, and the controller's own lat-accel instrument against the road (livePose).")
    pr("  r35 EXPECTED (its backup was recorded): SR 12.5, LAF 2.11, friction 0.03, SteerKP 0.6, ForceAutoTune OFF.")
    pr("=" * 165)
    out = {}
    for tag in ALL:
        g = grids[tag]
        o = B.live_values(g)
        D = B.load(tag)
        sr = D["lpar_sr"]; sr = sr[~np.isnan(sr)]
        cp = D["cp"]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (np.abs(g["desiredLateralAccel"]) > 0.5) & (g["v"] > 8)
        ratio = g["actualLateralAccel"][ok] / g["lat_torqued"][ok]
        ratio = ratio[np.isfinite(ratio) & (np.abs(g["lat_torqued"][ok]) > 0.5)]
        row = dict(LAF=o.get("LAF_from_pid_p50", np.nan), kp=o.get("kp_p50", np.nan), friction=o.get("friction_from_f", np.nan),
                   SR=float(np.median(sr)) if len(sr) else np.nan, SR_first=float(sr[0]) if len(sr) else np.nan,
                   SR_last=float(sr[-1]) if len(sr) else np.nan, SR_cp=float(cp["steerRatio"]),
                   useParams=o.get("useParams_p50", np.nan), liveValid=o.get("liveValid_p50", np.nan),
                   ltp_first=o.get("latAccelFactorFiltered_first", np.nan), ltp_last=o.get("latAccelFactorFiltered_last", np.nan),
                   m_over_pose=med(ratio))
        out[tag] = row
        pr("  %-4s LAF -(p+i+d+f)/output p50 %.3f (p5-p95 %.3f-%.3f) | kp = p/error p50 %.3f | friction from f %.3f | ltp latAccelFactorFiltered first/last %.3f/%.3f useParams %.2f liveValid %.2f | liveParameters.steerRatio p50 %.2f (first %.2f last %.2f; carParams %.2f) | controller m / road pose on curves p50 %.3f (n %d)"
           % (tag, row["LAF"], o.get("LAF_from_pid_p5", np.nan), o.get("LAF_from_pid_p95", np.nan), row["kp"], row["friction"],
              row["ltp_first"], row["ltp_last"], row["useParams"], row["liveValid"], row["SR"], row["SR_first"], row["SR_last"], row["SR_cp"], row["m_over_pose"], len(ratio)))
    pr("")
    ref = out["r35"]
    pr("  DELTA vs r35 (the like-for-like baseline).  Any non-trivial delta CONFOUNDS every r35 contrast below.")
    for tag in NEW:
        d = out[tag]
        flags = []
        for k, tol, lab in (("SR", 0.4, "steerRatio"), ("LAF", 0.08, "LAF"), ("kp", 0.03, "kp"), ("friction", 0.012, "friction")):
            if np.isfinite(d[k]) and np.isfinite(ref[k]) and abs(d[k] - ref[k]) > tol:
                flags.append("%s %+.3f" % (lab, d[k] - ref[k]))
        pr("    %-4s SR %+.2f  LAF %+.3f  kp %+.3f  friction %+.3f  ->  %s"
           % (tag, d["SR"] - ref["SR"], d["LAF"] - ref["LAF"], d["kp"] - ref["kp"], d["friction"] - ref["friction"],
              "TUNE MOVED: " + ", ".join(flags) if flags else "same tune as r35 within tolerance"))
    return out


# ------------------------------------------------------------------------------------ 1. attribution
def ki_fit(r, kp, win_s=2.0, step_s=0.25, tqmax=512, std_min=0.3):
    """WINDOW-LOCAL regression of the tap residual on the unit-Ki predictor.  The slope IS Ki (0xC63E6).
    De-meaning inside the window removes the accumulated open-loop integration offset, which is what
    defeats a whole-route fit."""
    R0 = sim(r, kp, 0)
    J = unit_J(R0["E"], r.eng1k)
    du = (-GK * V.output_lag(J))[r.i100]
    resid = r.T_meas - R0["T"][r.i100]
    P100, D100, I50 = R0["P"][r.i100], R0["D"][r.i100], 50 * J[r.i100]
    ok = (r.eng & (np.abs(r.tq_raw) < tqmax) & (np.abs(r.T_meas) < ST.CAP - 8) & (np.abs(P100) < V.P_CLAMP)
          & (np.abs(I50) < I_CLAMP) & (np.abs(I50 + P100 + D100) < V.SUM_CLAMP))
    n, st = int(win_s * FS), int(step_s * FS)
    xs, ys, sl = [], [], []
    for a in range(0, len(ok) - n, st):
        if ok[a:a + n].mean() < 0.98:
            continue
        x, y = du[a:a + n], resid[a:a + n]
        x = x - x.mean(); y = y - y.mean()
        if x.std() < std_min or np.sum(x * x) < 1e-6:
            continue
        xs.append(x); ys.append(y); sl.append(np.sum(x * y) / np.sum(x * x))
    if len(sl) < 8:
        return dict(n=len(sl), pooled=np.nan, median=np.nan, lo=np.nan, hi=np.nan, iqr=(np.nan, np.nan))
    sl = np.array(sl)
    x = np.concatenate(xs); y = np.concatenate(ys)
    rng = np.random.default_rng(7)
    bs = np.array([np.median(rng.choice(sl, len(sl))) for _ in range(4000)])
    return dict(n=len(sl), pooled=float(np.sum(x * y) / np.sum(x * x)), median=float(np.median(sl)),
                lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                iqr=(float(np.percentile(sl, 25)), float(np.percentile(sl, 75))))


def section1(routes):
    pr("\n" + "=" * 165)
    pr("SECTION 1 -- BUILD ATTRIBUTION FROM THE TAP, NOT FROM THE LABEL")
    pr("  (kit rule feedback-attribute-the-build-from-the-tap-not-from-the-label: r32/r33 were FILED as V278 and the wire said V280 rev 2.)")
    pr("=" * 165)
    res = {}
    pr("\n  1a -- Ki (0xC63E6) FITTED FROM THE 427 DELIVERED-TORQUE TAP.  The integrator is in series with the tap, so")
    pr("        T_meas - T_sim(Ki=0) = Ki * [-(254/256)(5346/32768) * lag(J)], J = the Ki=1 accumulator.  The regression")
    pr("        slope IS Ki.  Windows are de-meaned locally (the open-loop accumulator's ABSOLUTE level drifts; its SLOPE does not).")
    pr("        r34 and r35 ship Ki = 0 and are the NEGATIVE CONTROLS -- they calibrate the method's floor.")
    pr("        %-5s %-32s | %-46s | %s" % ("route", "build (claimed)", "Ki_hat window-median [95% CI] (pooled)", "by window length"))
    for tag in ALL:
        r = routes[tag]
        rows = {w: ki_fit(r, KP_OF[tag], w) for w in (1.0, 2.0, 4.0)}
        f = rows[2.0]
        res[tag] = dict(ki={str(k): v for k, v in rows.items()})
        pr("        %-5s %-32s | %6.1f  [%5.1f, %5.1f]  (pooled %6.1f)       | %s"
           % (tag, BUILD[tag], f["median"], f["lo"], f["hi"], f["pooled"],
              "  ".join("%.0fs: %.1f (n%d)" % (w, rows[w]["median"], rows[w]["n"]) for w in (1.0, 2.0, 4.0))))
    pr("\n  1b -- WHICH Kp TABLE?  Same window-local method: median per-window corr and LS scale of the chain's T against the tap,")
    pr("        Ki pinned at the value fitted in 1a.  A scale of 1.00 means the candidate reproduces the tap; r35's known-correct")
    pr("        answer (flat 248) calibrates what right looks like.")
    n, st = int(2.0 * FS), int(0.25 * FS)
    for tag in ALL:
        r = routes[tag]; ki = KI_OF[tag]
        pr("        %s (Ki pinned %d, %.0f s engaged):" % (tag, ki, r.eng.sum() / FS))
        for name, kp in (("stock LERP 248..696", KP_STOCK), ("FLAT 248", KP_FLAT), ("rev2 341 from idx 24", KP_R2)):
            Ts = sim(r, kp, ki)["T"][r.i100]
            ok = r.eng & (r.idx > 0) & (np.abs(r.tq_raw) < 512)
            cs, sls = [], []
            for a in range(0, len(ok) - n, st):
                if ok[a:a + n].mean() < 0.98:
                    continue
                x, y = Ts[a:a + n] - Ts[a:a + n].mean(), r.T_meas[a:a + n] - r.T_meas[a:a + n].mean()
                if x.std() < 4 or y.std() < 4:
                    continue
                cs.append(np.corrcoef(x, y)[0, 1]); sls.append(np.sum(x * y) / np.sum(x * x))
            cells = []
            for lo, hi in ((1, 40), (40, 68), (68, 112), (112, 241)):
                m = ok & (r.idx >= lo) & (r.idx < hi)
                cells.append("%3d-%3d %.3f" % (lo, hi, np.corrcoef(Ts[m], r.T_meas[m])[0, 1]) if m.sum() > 100 else "%3d-%3d --" % (lo, hi))
            pr("          %-22s window corr %s scale %s (n %4d) | whole-route corr by idx: %s"
               % (name, ("%.3f" % np.median(cs)) if len(cs) >= 8 else "  -- ", ("%.2f" % np.median(sls)) if len(sls) >= 8 else " -- ", len(cs), "  ".join(cells)))
    pr("\n  1c -- V282's INERT r24 COMPARATOR TAP on 0x14A byte 4.")
    pr("        %-5s %-8s %-9s | %s" % ("route", "frames", "distinct", "engaged duty and flip rate per bit"))
    for tag in ALL:
        r = routes[tag]; b4 = load_b4(tag, r)
        if b4 is None:
            pr("        %-5s no _b4 cache" % tag); continue
        e = r.eng
        duty = [float(np.mean((b4[e] >> k) & 1)) for k in range(8)]
        flips = [float((np.diff((b4[e] >> k) & 1) != 0).sum() / max(e.sum() / FS, 1)) for k in (6, 5, 4)]
        res.setdefault(tag, {})["b4"] = dict(duty=duty, flips_b6=flips[0], flips_b5=flips[1], flips_b4=flips[2],
                                             distinct=int(len(np.unique(b4))))
        pr("        %-5s %-8d %-9d | b6 duty %.3f flips %5.1f/s | b5 duty %.3f flips %5.1f/s | b4 duty %.3f flips %5.1f/s | b7 %.3f b3 %.3f b2-b0 %.0f%.0f%.0f"
           % (tag, len(b4), len(np.unique(b4)), duty[6], flips[0], duty[5], flips[1], duty[4], flips[2], duty[7], duty[3], duty[2], duty[1], duty[0]))
    return res


# ------------------------------------------------------------------------------------ 2. the prereg
def moving_runs(r, R, idx_lo=68, ang=30.0, minlen=100, moving=0.5):
    """v281r3_read_r35.moving_runs, verbatim in criterion: runs >= 1 s of engaged & |angle| >= ang & idx >= idx_lo,
    classified MOVING when the median wheel rate reaches half the map's reference."""
    ref = R["ref_deg"][r.i100]
    m = r.eng & (np.abs(r.ang) >= ang) & (r.idx >= idx_lo)
    out = []
    for a, b in runs_of(m, minlen):
        w = np.abs(r.wire[a:b]) / CPD; rf = ref[a:b]; ok = rf > 0
        rr = float(np.median(w[ok] / rf[ok])) if ok.any() else np.nan
        row = dict(t0=a / FS, dur=(b - a) / FS, rr=rr, idx=float(np.median(r.idx[a:b])), ang=float(np.median(np.abs(r.ang[a:b]))),
                   v=float(r.vego[a:b].mean()), lvl=float(np.median(np.abs(r.T_meas[a:b]))), amp=band_amp(r.T_meas[a:b]),
                   tq_ring=band_amp(r.tq_raw[a:b]), rate_amp=band_amp(r.wire[a:b]) / CPD,
                   tq50=float(np.median(np.abs(r.tq_raw[a:b]))), Prail=float(np.mean(np.abs(R["P_raw"][r.i100][a:b]) >= V.P_CLAMP)),
                   Irail=float(np.mean(np.abs(R["I"][r.i100][a:b]) >= I_CLAMP - 1)),
                   I50=float(np.median(np.abs(R["I"][r.i100][a:b]))),
                   rate=float(np.median(w)), ref=float(np.median(rf[ok])) if ok.any() else np.nan, a=a, b=b)
        row["ratio"] = row["amp"] / max(row["lvl"], 1)
        row["moving"] = rr >= moving
        out.append(row)
    return out


def section2(routes):
    pr("\n" + "=" * 165)
    pr("SECTION 2 -- PREREG-V283-READ.md (a)-(i), THRESHOLDS EXACTLY AS REGISTERED.  Not one threshold moved after the logs landed.")
    pr("=" * 165)
    res = {}
    for tag in ALL:
        r = routes[tag]
        R = sim(r, KP_OF[tag], KI_OF[tag])
        o = {}
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS)
        o["eng_s"] = float(r.eng.sum() / FS); o["high_s"] = hs
        # ---------------------------------------------------------------- (a) stalled runs
        st_all = moving_runs(r, R, 40)
        stalls = [x for x in st_all if (not x["moving"]) and x["tq50"] < 1000 and x["idx"] <= 240]
        o["a_runs"] = len(stalls); o["a_secs"] = float(sum(x["dur"] for x in stalls))
        o["a_max_dur"] = float(max([x["dur"] for x in stalls], default=0.0))
        o["a_over_1p5"] = int(sum(1 for x in stalls if x["dur"] > 1.5))
        o["a_per100high"] = 100 * len(stalls) / hs if hs > 0 else np.nan
        o["a_T_p50"] = med([x["lvl"] for x in stalls]); o["a_idx_p50"] = med([x["idx"] for x in stalls])
        o["a_I_p50"] = med([x["I50"] for x in stalls]); o["a_Irail"] = med([x["Irail"] for x in stalls])
        # ---------------------------------------------------------------- (b) idx 40-80 rate vs reference
        hl = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx < 80) & (np.abs(r.tq_raw) < 1000)
        ref = R["ref_deg"][r.i100]
        o["b_secs"] = float(hl.sum() / FS)
        o["b_rate"] = med(np.abs(r.wire[hl]) / CPD); o["b_ref"] = med(ref[hl])
        o["b_frac"] = o["b_rate"] / o["b_ref"] if o["b_ref"] else np.nan
        o["b_T_p50"] = med(np.abs(r.T_meas[hl]))
        # ---------------------------------------------------------------- (c) prereg (k) dead fraction, speed-matched
        for lab, (vlo, vhi) in (("c", (8, 12)), ("c_all", (0, 99))):
            base = r.eng & (r.idx >= 20) & (r.idx < 40) & (np.abs(r.ang) > 10) & (r.vego >= vlo) & (r.vego < vhi) & (np.abs(r.tq_raw) < 400)
            dead = base & (np.abs(r.wire) < CPD)
            o[lab + "_secs"] = float(base.sum() / FS)
            o[lab + "_dead"] = float(dead.sum() / base.sum()) if base.sum() > 50 else np.nan
            o[lab + "_T_dead"] = med(np.abs(r.T_meas[dead])) if dead.sum() else np.nan
            o[lab + "_T_moving"] = med(np.abs(r.T_meas[base & ~dead])) if (base & ~dead).sum() else np.nan
        # ---------------------------------------------------------------- (d) stall-release overshoot
        ov = []
        for x in stalls:
            b = x["b"]
            w = min(b + int(3 * FS), len(r.wire))
            if w - b < int(1.0 * FS) or not r.eng[b:w].all():
                continue
            rate = np.abs(r.wire[b:w]) / CPD
            rf = ref[b:w]
            excess = rate - rf
            pk = float(np.max(excess))
            above = float(np.sum(excess > 0) / FS)
            ov.append(dict(t0=x["t0"], dur=x["dur"], peak=pk, above_s=above, ref=float(np.median(rf))))
        o["d_n"] = len(ov); o["d_peak_p50"] = med([x["peak"] for x in ov]); o["d_peak_max"] = float(max([x["peak"] for x in ov], default=np.nan))
        o["d_above_p50"] = med([x["above_s"] for x in ov]); o["d_above_max"] = float(max([x["above_s"] for x in ov], default=np.nan))
        o["d_rows"] = ov
        # ---------------------------------------------------------------- (e) F7 episodes and the idx>=68 ripple
        eps = ST.fixed_thr_episodes(r)
        hi_eps = [x for x in eps if x["ang"] >= 30]
        f7 = [x for x in hi_eps if x["fdom"] >= 6]
        o["e_F7_n"] = len(f7); o["e_F7_secs"] = float(sum(x["dur"] for x in f7))
        o["e_F7_per100"] = 100 * len(f7) / hs if hs > 0 else np.nan
        mv = [x for x in moving_runs(r, R, 68) if x["moving"]]
        o["e_mv_n"] = len(mv); o["e_mv_secs"] = float(sum(x["dur"] for x in mv))
        o["e_ripple"] = med([x["ratio"] for x in mv]); o["e_lvl"] = med([x["lvl"] for x in mv])
        o["e_tq_ring"] = med([x["tq_ring"] for x in mv]); o["e_rate_amp"] = med([x["rate_amp"] for x in mv])
        # ---------------------------------------------------------------- (f) 18-22 Hz creep bar amplitude
        creep = r.eng & (r.vego >= 1) & (r.vego < 3) & (np.abs(r.tq_raw) < 400)
        rs = runs_of(creep, 256)
        o["f_secs"] = float(sum(b - a for a, b in rs) / FS)
        if o["f_secs"] > 5:
            acc, nn, f = None, 0, None
            for a, b in rs:
                s = r.tq_raw[a:b] - r.tq_raw[a:b].mean()
                f, P = signal.welch(s, fs=FS, nperseg=min(256, b - a))
                if acc is None:
                    acc = P * (b - a)
                elif len(P) == len(acc):
                    acc = acc + P * (b - a)
                else:
                    continue
                nn += b - a
            P = acc / nn; df = f[1] - f[0]
            bnd = lambda lo, hi: float(np.sqrt(P[(f >= lo) & (f < hi)].sum() * df * 2))   # noqa: E731
            o["f_18_22"] = bnd(18, 22); o["f_6_8.5"] = bnd(6, 8.5); o["f_2_4"] = bnd(2, 4)
        else:
            o["f_18_22"] = o["f_6_8.5"] = o["f_2_4"] = np.nan
        # ---------------------------------------------------------------- (g) integrator windup signature
        I100 = R["I"][r.i100]
        e = r.eng & (r.idx > 0)
        o["g_I_p50"] = med(np.abs(I100[e])); o["g_I_p95"] = float(np.percentile(np.abs(I100[e]), 95)) if e.sum() else np.nan
        o["g_I_railfrac"] = float(np.mean(np.abs(I100[e]) >= I_CLAMP - 1)) if e.sum() else np.nan
        o["g_I_share"] = med(np.abs(I100[e]) / np.maximum(np.abs(I100[e]) + np.abs(R["P"][r.i100][e]) + np.abs(R["D"][r.i100][e]), 1))
        # tap |T| in the stall runs (what the prereg predicted would climb toward 2240)
        o["g_stall_T_p50"] = o["a_T_p50"]
        o["g_stall_T_p90"] = float(np.percentile([x["lvl"] for x in stalls], 90)) if stalls else np.nan
        # ---------------------------------------------------------------- (h) hands-on override at idx 40-84
        ho = r.eng & (r.idx >= 40) & (r.idx < 84) & (np.abs(r.tq_raw) >= 1000)
        o["h_secs"] = float(ho.sum() / FS)
        o["h_T_p50"] = med(np.abs(r.T_meas[ho])); o["h_T_p90"] = float(np.percentile(np.abs(r.T_meas[ho]), 90)) if ho.sum() > 20 else np.nan
        o["h_T_max"] = float(np.abs(r.T_meas[ho]).max()) if ho.sum() else np.nan
        # ---------------------------------------------------------------- (i) V282 bit-6 duty over engaged hands-off creep
        b4 = load_b4(tag, r)
        if b4 is not None:
            cm = r.eng & (r.vego >= 1) & (r.vego < 3) & (np.abs(r.tq_raw) < 400)
            o["i_secs"] = float(cm.sum() / FS)
            o["i_b6_duty"] = float(np.mean((b4[cm] >> 6) & 1)) if cm.sum() > 50 else np.nan
            o["i_b5_duty"] = float(np.mean((b4[cm] >> 5) & 1)) if cm.sum() > 50 else np.nan
            o["i_b4_duty"] = float(np.mean((b4[cm] >> 4) & 1)) if cm.sum() > 50 else np.nan
        else:
            o["i_secs"] = o["i_b6_duty"] = o["i_b5_duty"] = o["i_b4_duty"] = np.nan
        res[tag] = o
        # ---------------------------------------------------------------- print
        pr("\n  %s -- %s | engaged %.0f s, |angle| >= 30 for %.1f s" % (tag, BUILD[tag], o["eng_s"], hs))
        pr("    (a) STALLED runs (|angle|>=30, idx 40-240, rate/ref < 0.5, |tq| p50 < 1000, >= 1 s): %d runs, %.1f s, longest %.1f s, %d longer than 1.5 s | %.1f per 100 s of high-angle | tap |T| p50 %.0f | idx p50 %.0f | modelled |I| p50 %.0f (railed %.2f)"
           % (o["a_runs"], o["a_secs"], o["a_max_dur"], o["a_over_1p5"], o["a_per100high"], o["a_T_p50"], o["a_idx_p50"], o["a_I_p50"], o["a_Irail"]))
        for x in sorted(stalls, key=lambda z: -z["dur"])[:8]:
            pr("         t0 %6.1f dur %4.1f idx %3.0f ang %4.0f v %4.1f | rate %5.1f ref %5.1f r/ref %.2f | tap |T| %5.0f | tq50 %4.0f | |I| %5.0f Irail %.2f Prail %.2f"
               % (x["t0"], x["dur"], x["idx"], x["ang"], x["v"], x["rate"], x["ref"], x["rr"], x["lvl"], x["tq50"], x["I50"], x["Irail"], x["Prail"]))
        pr("    (b) idx 40-80 hands-light (|tq|<1000) strong turns, %.1f s: wheel rate p50 %.1f deg/s vs reference %.1f = %.0f%% | tap |T| p50 %.0f"
           % (o["b_secs"], o["b_rate"], o["b_ref"], 100 * o["b_frac"], o["b_T_p50"]))
        pr("    (c) dead fraction, idx 20-40 & |rate| < 1 deg/s & |angle| > 10, hands-light, SPEED-MATCHED 8-12 m/s: %.3f (%.1f s in cell) | tap |T| dead/moving %.0f/%.0f  [all speeds: %.3f over %.1f s]"
           % (o["c_dead"], o["c_secs"], o["c_T_dead"], o["c_T_moving"], o["c_all_dead"], o["c_all_secs"]))
        pr("    (d) STALL-RELEASE OVERSHOOT (3 s after each stall run ends, engaged): n %d | peak rate above reference p50 %+.1f deg/s, max %+.1f | time above reference p50 %.2f s, max %.2f s"
           % (o["d_n"], o["d_peak_p50"], o["d_peak_max"], o["d_above_p50"], o["d_above_max"]))
        for x in sorted(ov, key=lambda z: -z["peak"])[:5]:
            pr("         after stall t0 %6.1f (dur %.1f): peak %+.1f deg/s above ref %.1f, above for %.2f s" % (x["t0"], x["dur"], x["peak"], x["ref"], x["above_s"]))
        pr("    (e) F7 episodes (FIXED threshold 103 wire, 2-8 Hz envelope, |angle|>=30, fdom>=6): %d (%.1f s) = %.1f per 100 s of high-angle | idx>=68 MOVING runs n %d (%.1f s): tap ripple/level %.2f (level %.0f), bar 6-8.5 Hz ring %.0f raw, rate ripple %.1f deg/s"
           % (o["e_F7_n"], o["e_F7_secs"], o["e_F7_per100"], o["e_mv_n"], o["e_mv_secs"], o["e_ripple"], o["e_lvl"], o["e_tq_ring"], o["e_rate_amp"]))
        pr("    (f) creep 1-3 m/s engaged hands-off, %.1f s: bar amplitude 18-22 Hz %.1f raw | 6-8.5 Hz %.1f | 2-4 Hz %.1f"
           % (o["f_secs"], o["f_18_22"], o["f_6_8.5"], o["f_2_4"]))
        pr("    (g) integrator state (modelled at the fitted Ki, from the wire): |I| p50 %.0f p95 %.0f, railed at 10240 for %.3f of engaged idx>0 frames | I share of |I|+|P|+|D| p50 %.2f | tap |T| in stalls p50/p90 %.0f/%.0f (prereg predicted a climb toward 2240)"
           % (o["g_I_p50"], o["g_I_p95"], o["g_I_railfrac"], o["g_I_share"], o["g_stall_T_p50"], o["g_stall_T_p90"]))
        pr("    (h) hands-ON at idx 40-84 (|tq_raw| >= 1000), %.1f s: tap |T| p50 %.0f p90 %.0f max %.0f  (r35 was <= 1281; prereg predicted a rise to the 2462 cap)"
           % (o["h_secs"], o["h_T_p50"], o["h_T_p90"], o["h_T_max"]))
        pr("    (i) V282 bit-6 duty over engaged hands-off creep (%.1f s): b6 %.3f | b5 %.3f | b4 %.3f  (prereg: 0.300 at the 5244 arm / 0.065 at 1024)"
           % (o["i_secs"], o["i_b6_duty"], o["i_b5_duty"], o["i_b4_duty"]))
    return res


# --------------------------------------------------------------- 3. what the integrator actually did
def section3(routes):
    pr("\n" + "=" * 165)
    pr("SECTION 3 -- WHAT THE INTEGRATOR ACTUALLY DID TO THE CAR")
    pr("  3a  the 0.2-1 Hz STRAIGHT-ROAD HUNT -- the prereg's Cost-FAIL signature (the integrator fighting the SteerRatio bias)")
    pr("  3b  wind-up: how long a held error takes to rail, measured on the wire")
    pr("  3c  the accumulator at disengage")
    pr("=" * 165)
    out = {}
    pr("\n  3a -- straight road (engaged, |angle| < 5, v >= 8), Welch on runs >= 5.12 s. Amplitude-equivalent deg/s of 0x18F rate,")
    pr("        and the same bands on the CAN-427 tap and on the driver-torque bar.  A NEW 0.2-1 Hz line = the integrator hunting.")
    pr("        %-5s %8s | %-42s | %-30s | %s" % ("route", "secs", "rate deg/s: 0.2-1 / 1-2 / 2-4 / 6-8.5", "tap |T| counts: 0.2-1 / 1-2", "bar raw: 0.2-1 / 1-2"))
    for tag in ALL:
        r = routes[tag]
        st = r.eng & (np.abs(r.ang) < 5) & (r.vego >= 8)
        rs = runs_of(st, 512)
        secs = sum(b - a for a, b in rs) / FS
        if secs < 10:
            pr("        %-5s %8.1f | too little straight-road time" % (tag, secs)); continue
        def bands(x):
            acc, nn, f = None, 0, None
            for a, b in rs:
                s = x[a:b] - x[a:b].mean()
                f, P = signal.welch(s, fs=FS, nperseg=min(512, b - a))
                if acc is None:
                    acc = P * (b - a)
                elif len(P) == len(acc):
                    acc = acc + P * (b - a)
                else:
                    continue
                nn += b - a
            P = acc / nn; df = f[1] - f[0]
            return lambda lo, hi: float(np.sqrt(P[(f >= lo) & (f < hi)].sum() * df * 2))
        br, bt, bb = bands(r.wire), bands(r.T_meas), bands(r.tq_raw)
        out[tag] = dict(secs=secs, rate_02_1=br(0.2, 1) / CPD, rate_1_2=br(1, 2) / CPD, rate_2_4=br(2, 4) / CPD,
                        rate_6_85=br(6, 8.5) / CPD, tap_02_1=bt(0.2, 1), tap_1_2=bt(1, 2), bar_02_1=bb(0.2, 1), bar_1_2=bb(1, 2))
        o = out[tag]
        pr("        %-5s %8.1f | %8.2f %8.2f %8.2f %8.2f            | %12.0f %12.0f      | %10.0f %10.0f"
           % (tag, secs, o["rate_02_1"], o["rate_1_2"], o["rate_2_4"], o["rate_6_85"], o["tap_02_1"], o["tap_1_2"], o["bar_02_1"], o["bar_1_2"]))
    pr("\n  3b -- WIND-UP RATE measured on the wire.  In a held error the tap must ramp at 0.1565 * excess * Ki counts/s.")
    pr("        Windows of >= 1.5 s, engaged, hands-light, same-signed excess, |T| unrailed: fitted d|T|/dt vs the prediction at the fitted Ki.")
    pr("        %-5s | %-40s | %s" % ("route", "measured d|T|/dt (counts/s) p50 [IQR]", "predicted at fitted Ki / at Ki 0"))
    for tag in ALL:
        r = routes[tag]; R = sim(r, KP_OF[tag], KI_OF[tag])
        ex = excess_of(R["E"])[r.i100]
        ok = r.eng & (np.abs(r.tq_raw) < 512) & (np.abs(r.T_meas) < ST.CAP - 8) & (np.abs(ex) > 20)
        meas, pred = [], []
        n = int(1.5 * FS)
        for a in range(0, len(ok) - n, int(0.5 * FS)):
            sl = slice(a, a + n)
            if ok[sl].mean() < 0.98 or np.abs(np.sign(ex[sl]).mean()) < 0.98:
                continue
            sg = np.sign(np.median(ex[sl]))
            t = np.arange(n) / FS
            y = -sg * r.T_meas[sl]                       # T opposes the error's sign
            meas.append(np.polyfit(t, y, 1)[0])
            pred.append(0.1565 * abs(np.median(ex[sl])) * KI_OF[tag])
        if len(meas) < 8:
            pr("        %-5s | only %d windows" % (tag, len(meas))); continue
        meas = np.array(meas); pred = np.array(pred)
        pr("        %-5s | %8.0f  [%8.0f, %8.0f]  (n %4d)      | %8.0f   /   0" % (tag, np.median(meas), np.percentile(meas, 25), np.percentile(meas, 75), len(meas), np.median(pred)))
    pr("\n  3c -- the tap immediately AFTER a disengage (the accumulator's clear path, 0x2A164): |T| in the 0.5 s before vs the 0.5 s after.")
    for tag in ALL:
        r = routes[tag]
        d = np.diff(np.r_[0, r.eng.astype(int), 0])
        offs = np.flatnonzero(d == -1)
        pre, post = [], []
        for k in offs:
            if k < int(0.5 * FS) or k + int(0.5 * FS) >= len(r.T_meas):
                continue
            pre.append(np.median(np.abs(r.T_meas[k - int(0.5 * FS):k])))
            post.append(np.median(np.abs(r.T_meas[k:k + int(0.5 * FS)])))
        pr("        %-5s %3d disengagements | tap |T| p50 in the 0.5 s before %5.0f -> after %5.0f" % (tag, len(pre), med(pre), med(post)))
    return out


# ------------------------------------------------------------------------------------ 4. oversteer
def section4():
    pr("\n" + "=" * 165)
    pr("SECTION 4 -- THE OPERATOR'S REPORT: 'this firmware consistently oversteers'.  curve_oversteer_r34.py bins, unchanged code.")
    pr("  os = signed overshoot in the curve's direction (+ = MORE lateral accel than asked).  _pose = the road (livePose);")
    pr("  _m = the controller's own steering-angle model, which carries the SteerRatio bias.  rel = actual/desired - 1.")
    pr("=" * 165)
    out = {}
    for tag in ALL:
        CO.LINES.clear()
        try:
            out[tag] = CO.analyse(tag)
        except Exception as e:                                    # noqa: BLE001
            pr("  %s: curve_oversteer failed (%s)" % (tag, str(e)[:120])); continue
    keys = ["n", "entry_os_m", "entry_os_pose", "entry_rel_m", "entry_rel_pose", "entry_f", "entry_p", "entry_i",
            "steady_os_m", "steady_os_pose", "steady_rel_m", "steady_rel_pose", "steady_f", "steady_p", "steady_i",
            "i_exc", "i_t63", "straight_pose_bias", "straight_m_bias"]
    tags = [t for t in ALL if t in out]
    pr("\n  %-22s %s" % ("", "".join("%10s" % t for t in tags)))
    for k in keys:
        pr("  %-22s %s" % (k, "".join(("%10d" % out[t]["summary"][k]) if k == "n" else ("%+10.3f" % out[t]["summary"].get(k, np.nan)) for t in tags)))
    for ph in ("steady", "entry"):
        pr("  BINS %s -- os_pose / rel_pose [secs] by |angle|:" % ph)
        for lo, hi in CO.ANG_BINS:
            cells = []
            for t in tags:
                b = out[t]["bins"].get("%s ang %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f[%3.0f]" % (b["os_pose"], b["rel_pose"], b["secs"]) if b else "      --      ")
            pr("    ang %-9s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "  ".join(cells)))
        pr("  BINS %s -- os_pose / rel_pose [secs] by speed:" % ph)
        for lo, hi in CO.V_BINS:
            cells = []
            for t in tags:
                b = out[t]["bins"].get("%s v %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f[%3.0f]" % (b["os_pose"], b["rel_pose"], b["secs"]) if b else "      --      ")
            pr("    v %-11s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "  ".join(cells)))
    return {t: dict(summary=out[t]["summary"], bins=out[t]["bins"]) for t in out}


def jsonable(o):
    if isinstance(o, (np.floating, np.integer)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def main():
    routes, grids = {}, {}
    for tag in ALL:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
    for tag in ALL:
        try:
            grids[tag] = B.grid(B.load(tag))
        except Exception as e:                                     # noqa: BLE001
            print("  no backcalc grid for %s (%s)" % (tag, str(e)[:80]))
    tune = section0(grids) if len(grids) == len(ALL) else {}
    att = section1(routes)
    res = section2(routes)
    s3 = section3(routes)
    ovs = section4()
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    out = os.path.join(HERE, "_scratch", "v283_read_r36_r38.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    json.dump(dict(tune=tune, attribution=att, prereg=res, integrator=s3, oversteer=ovs),
              open(os.path.join(HERE, "v283_read_r36_r38.json"), "w"), indent=1, default=jsonable)
    print("wrote", out)


if __name__ == "__main__":
    main()
