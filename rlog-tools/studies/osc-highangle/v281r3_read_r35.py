# -*- coding: utf-8 -*-
"""studies/osc-highangle/v281r3_read_r35.py -- the pre-registered read of V281 rev 3 (LKAS rate-PID Kp FLAT 248; everything
else V280 rev 2: line map to x6, fb clamp 46080, CAN-427 delivered-torque tap) on route r35, scored EXACTLY as
PREREG-V281-READ.md (a)-(k) with the r32/r33/r34 scripts (strongturn_r34.py / strongturn_r32_r33.py, highangle_stutter.py,
lanechange_osc.py, curve_oversteer_r34.py, backcalc_laf_friction.py), against r32/r33/r34 (V280 rev 2) as baselines.
Subagent v281read, 2026-09-03.  Companion: V281R3-READ-r35-2026-09-03.md.

Sections
  0  the StarPilot tune as used (toggle backup decoded) and as seen on the wire (LAF = -(p+i+d+f)/output, kp = p/error,
     liveParameters.steerRatio, torqueState.actualLateralAccel / livePose lat-accel ratio)
  1  build attribution from the tap: the map is V280 rev 2's on both builds, so the discriminator is Kp -- chain T_sim under
     the stock Kp LERP (248..696) vs flat 248 vs the superseded rev 2 (341 from idx 24), per demand-index bin; the tap's
     |T| against the chain's |E| (P-rail onset: 5650 counts of E at Kp 696, 15855 at Kp 248); the T-per-E slope; and the
     live-fade chain of twist_taper_loop.py (0xCBBC4 / 0xCBC34 multipliers) as a second reading
  2  PREREG-V281-READ.md (a)-(k), same code paths and thresholds as HIGHANGLE-r34-2026-09-03.md
  3  the understeer / deadband hypothesis: tracking error on curves by demand index and |angle|, the SR 12.5 measurement
     bias separated from the physical (livePose) error, statistic (k), and the chain's own prediction on r35's frames
  4  oversteer bins as curve_oversteer_r34.py (the "oversteering largely gone" note)

Run: python v281r3_read_r35.py   (caches: analysis-2020accord/_scratch/cache/v280/r3{2,3,4,5}.npz, _scratch/_ha_*.npz,
     _scratch/_lc_r3{2,3,4,5}.npz, analysis-2020accord/studies/optune/_scratch/r3{2,3,4,5}_backcalc.npz)
"""
import base64
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import strongturn_r34 as S34  # noqa: E402  (registers r32/r33/r34, patches V.load with the tap)
import twist_taper_loop as TT  # noqa: E402
import lanechange_osc as L  # noqa: E402
import curve_oversteer_r34 as CO  # noqa: E402
import backcalc_laf_friction as B  # noqa: E402
import highangle_stutter as H  # noqa: E402

V, ST = S34.V, S34.ST
FS, FS1K = ST.FS, V.FS1K
CPD = V.CPD

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------------------------------- registration
NEW = "r35"
PREFIX35 = "75604b0a432fdc89_00000035--580292087d"
V.ROUTE_PREFIX[NEW] = PREFIX35
V.ROUTE_BUILD[NEW] = "V281r3 Kp flat 248 (line x6, SR 12.5 tune)"
V.ROUTE_K[NEW] = 6.0
ST.TAP_TAGS.add(NEW)
# HIGHANGLE-r35.txt (highangle_stutter.py --build v278r3, own threshold 100 wire): 3 episodes, 2 at |angle| >= 30
ST.EPIS[NEW] = [(275.9, 1.7, 4.65), (444.4, 1.2, 4.20)]
ST.HIGH_ANG_S[NEW] = 79.8
L.ROUTES[NEW] = (PREFIX35, "V281r3", os.path.join(HERE, "_scratch"))
L.HAS_TAP.add(NEW)
L.CHAIN_CFG[NEW] = dict(mapY=L.MAP_Y_V280R2, fb_clamp=46080, name="V281 rev 3 (V280r2 line, clamp 46080; Kp flat 248 -- chain() uses the stock LERP for P only)")
CO.LAF[NEW] = 2.11
ROUTES = ("r32", "r33", "r34", NEW)
BASE = ("r32", "r33", "r34")
V280R2 = ST.V280R2
IMG_V281R3 = TT.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"

T280 = TT.read_tables(TT.IMG_V280)
T281 = TT.read_tables(IMG_V281R3)
KP_STOCK = (T280["kp"][1], T280["kp"][2])          # X 0,68,112,136,208 / Y 248,512,645,696,696  (V280 rev 2 image)
KP_FLAT = (T281["kp"][1], T281["kp"][2])           # read from the V281 rev 3 image
KP_R2 = (np.array([0, 24, 68, 136, 208], float), np.array([248, 341, 341, 341, 341], float))   # superseded rev 2
KP_OF = {"r32": KP_STOCK, "r33": KP_STOCK, "r34": KP_STOCK, NEW: KP_FLAT}

LINES = []


def pr(s=""):
    print(s); LINES.append(s)


def sim(r, Y, clamp, kp=KP_STOCK, kd=V.KD):
    """strongturn's sim() with an explicit Kp table."""
    V.GAIN, V.OUT_CAP = ST.GAIN, ST.CAP
    y = V.lerp(V.MAP_X, Y, r.idx1k)
    kpv = V.lerp(kp[0], kp[1], r.idx1k)
    sp = r.sgn1k * y
    fb = np.clip(r.fb_un, -clamp, clamp)
    E = 32 * sp - fb
    P_raw = np.floor(E * kpv / 256)
    P = np.clip(P_raw, -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    onset = r.eng1k & ~np.r_[False, r.eng1k[:-1]]
    dE[onset] = 0.0
    D_raw = np.floor(dE * kd / 8)
    Dt = np.clip(D_raw, -V.D_CLAMP, V.D_CLAMP)
    S_raw = np.floor(V.SUM_MULT * (P + Dt) / 256)
    S = np.clip(S_raw, -V.SUM_CLAMP, V.SUM_CLAMP)
    S[~r.eng1k] = 0.0
    lag = V.output_lag(S)
    T = np.clip(np.floor(-lag * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
    R = dict(E=E, P_raw=P_raw, D_raw=D_raw, S_raw=S_raw, T=T, fb=fb, sp=sp, kp=kpv)
    R["clamped"] = np.abs(r.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(sp) / V.FB_DC / CPD
    return R


def live_chain(r, kp):
    """twist_taper_loop's 'live (m0 arm, live m, Kd)' chain: the driver-torque-fed taper and the post multipliers read
    from the V280 rev 2 image (byte-identical on V281 rev 3), explicit Kp table."""
    c = T280["cal"]
    if not hasattr(r, "mL1k"):
        r.tq_fw = -r.tq_raw
        r.idxL, r.sgnL, _ = TT.demand_idx(r.cmd, r.tq_fw, T280["taperA_m0_same"], T280["taperA_m0_opp"])
        tq1k = np.round(r.up(r.tq_raw))
        r.grab1k = TT.grab_byte_1k(tq1k, c)
        r.tb1k = TT.torque_byte(tq1k)
        r.mL1k, _, _ = TT.post_mult(T280["postA_m0"], T280["postB_m0"], r.grab1k, r.tb1k)
        r.idxL1k = np.round(r.up(r.idxL))
        sL = np.sign(r.up(r.sgnL)); sL[sL == 0] = 1
        r.sgnL1k = sL
    return TT.simulate(r, V280R2[0], V280R2[1], kp[0], kp[1], r.idxL1k, r.sgnL1k, r.mL1k)


def band_amp(x, lo=6.0, hi=8.5):
    return ST.band_amp(np.asarray(x, float), lo, hi) if len(x) > 40 else np.nan


def runs_of(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def welch_runs(x, runs, nperseg):
    acc, n, f = None, 0, None
    for a, b in runs:
        s = x[a:b] - x[a:b].mean()
        f, P = signal.welch(s, fs=FS, nperseg=min(nperseg, b - a))
        if acc is None or len(P) != len(acc):
            if acc is not None:
                continue
            acc = P * (b - a)
        else:
            acc = acc + P * (b - a)
        n += b - a
    return (f, acc / n) if n else (None, None)


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


# ---------------------------------------------------------------------------------------------------- 0. tune
def decode_toggles(path):
    j = json.load(open(path))
    raw = base64.b64decode(j["data"])
    key = b"s8#pL3*Xj!aZ@dWq"
    return json.loads(bytes(c ^ key[i % len(key)] for i, c in enumerate(raw)))


def section0(grids):
    pr("=" * 160)
    pr("SECTION 0 -- THE STARPILOT TUNE AS USED (toggle backup, decoded) AND AS SEEN ON THE WIRE (backcalc grids)")
    pr("=" * 160)
    for lab, fn in (("V281R3 (r35)", "toggle-backup_V281R3.json"), ("20260902 (r34)", "toggle-backup_20260902.json")):
        t = decode_toggles(os.path.join(KIT, "analysis-2020accord", "reference", fn))
        pr("  %-16s ForceAutoTune %s  ForceAutoTuneOff %s  ForceTorqueController %s | SteerKP %s  SteerFriction %s  SteerLatAccel %s  SteerRatio %s  SteerDelay %s  UseAutoSteerDelay %s | HondaLateralPidKpScale %s KiScale %s (inert: torque controller)"
           % (lab, t["ForceAutoTune"], t["ForceAutoTuneOff"], t["ForceTorqueController"], t["SteerKP"], t["SteerFriction"], t["SteerLatAccel"], t["SteerRatio"], t["SteerDelay"],
              t["UseAutoSteerDelay"], t["HondaLateralPidKpScale"], t["HondaLateralPidKiScale"]))
    for tag in ROUTES:
        g = grids[tag]
        o = B.live_values(g)
        D = B.load(tag)
        sr = D["lpar_sr"]; sr = sr[~np.isnan(sr)]
        cp = D["cp"]
        # the controller's own lat-accel instrument vs the road (livePose): m / pose on curves, hands off
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (np.abs(g["desiredLateralAccel"]) > 0.5) & (g["v"] > 8)
        ratio = g["actualLateralAccel"][ok] / g["lat_torqued"][ok]
        ratio = ratio[np.isfinite(ratio) & (np.abs(g["lat_torqued"][ok]) > 0.5)]
        pr("  %s: LAF on the wire -(p+i+d+f)/output p50 %.3f (p5-p95 %.3f-%.3f) | kp = p/error p50 %.3f | friction*LAF from f %.3f -> friction %.3f | ltp latAccelFactorFiltered first/last %.3f/%.3f useParams %s liveValid %s | liveParameters.steerRatio %.2f (first %.2f, last %.2f; carParams %.2f) | m/pose on curves (|des|>0.5, v>8) p50 %.3f (n %d)"
           % (tag, o.get("LAF_from_pid_p50", np.nan), o.get("LAF_from_pid_p5", np.nan), o.get("LAF_from_pid_p95", np.nan), o.get("kp_p50", np.nan), o.get("fricLAF_from_f", np.nan),
              o.get("friction_from_f", np.nan), o.get("latAccelFactorFiltered_first", np.nan), o.get("latAccelFactorFiltered_last", np.nan), o.get("useParams_p50", np.nan),
              o.get("liveValid_p50", np.nan), float(np.median(sr)) if len(sr) else np.nan, sr[0] if len(sr) else np.nan, sr[-1] if len(sr) else np.nan, cp["steerRatio"], med(ratio), len(ratio)))
        # the vehicle-model constant: m / (angle * v^2) -- proportional to 1/steerRatio if VM.calc_curvature is angle/(SR*L) with the same stiffness
        okk = ok & (np.abs(g["ang"]) > 3) & (np.abs(g["actualLateralAccel"]) > 0.3)
        k = np.abs(g["actualLateralAccel"][okk]) / (np.abs(np.radians(g["ang"][okk])) * g["v"][okk] ** 2)
        pr("        vehicle-model constant |m| / (|angle_rad| * v^2) p50 %.4f 1/m  -> implied SR*L(1+K v^2) %.1f m ; wheelbase %.2f -> SR-equivalent %.1f" % (
            med(k), 1 / med(k) if med(k) else np.nan, cp["wheelbase"], 1 / med(k) / cp["wheelbase"] if med(k) else np.nan))


# ---------------------------------------------------------------------------------------------------- 1. attribution
IDX_BINS = ((1, 40), (40, 68), (68, 112), (112, 136), (136, 241))
E_BINS = ((0, 2000), (2000, 4000), (4000, 5650), (5650, 8000), (8000, 12000), (12000, 15855), (15855, 30000), (30000, 1e9))


def section1(routes):
    pr("\n" + "=" * 160)
    pr("SECTION 1 -- BUILD ATTRIBUTION FROM THE TAP: WHICH Kp WAS ON THE CAR? (map = V280 rev 2 line, clamp 46080 on both; chain open loop on the measured rate)")
    pr("  Kp tables read from the images: V280 rev 2 X %s / Y %s ; V281 rev 3 X %s / Y %s ; superseded rev 2 Y %s" % (
        KP_STOCK[0].astype(int).tolist(), KP_STOCK[1].astype(int).tolist(), KP_FLAT[0].astype(int).tolist(), KP_FLAT[1].astype(int).tolist(), KP_R2[1].astype(int).tolist()))
    pr("  frames: engaged, idx>0, hands-light |tq_raw| < 512 (the live post multiplier is 255 there), no override cliff; LS slope = sum(Ts*Tm)/sum(Ts^2) -- 1.00 = the candidate reproduces the tap's scale")
    pr("=" * 160)
    cands = (("stock LERP 248..696", KP_STOCK), ("FLAT 248 (V281r3)", KP_FLAT), ("rev2 341 from 24", KP_R2))
    for tag in ("r34", NEW):
        r = routes[tag]
        e = r.eng & (r.idx > 0) & (np.abs(r.tq_raw) < 512)
        pr("  %s (%s): %.0f s of hands-light engaged idx>0 frames" % (tag, V.ROUTE_BUILD[tag], e.sum() / FS))
        for name, kp in cands:
            R = sim(r, *V280R2, kp=kp); Ts = R["T"][r.i100]; Tm = r.T_meas
            cells = []
            for lo, hi in IDX_BINS:
                m = e & (r.idx >= lo) & (r.idx < hi)
                if m.sum() < 100:
                    cells.append("idx %3d-%3d:  --  (n %5d)" % (lo, hi, m.sum())); continue
                cells.append("idx %3d-%3d: corr %.3f slope %.2f (n %5d)" % (lo, hi, np.corrcoef(Ts[m], Tm[m])[0, 1], np.sum(Ts[m] * Tm[m]) / np.sum(Ts[m] ** 2), m.sum()))
            pr("    kit chain, %-22s all: corr %.3f slope %.3f | %s" % (name, np.corrcoef(Ts[e], Tm[e])[0, 1], np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2), " | ".join(cells)))
        for name, kp in cands[:2]:
            R = live_chain(r, kp); Ts = R["T"][r.i100]; Tm = r.T_meas
            ee = r.eng & (r.idx > 0)
            cells = []
            for lo, hi in IDX_BINS:
                m = ee & (r.idx >= lo) & (r.idx < hi)
                cells.append("idx %3d-%3d: corr %.3f slope %.2f" % (lo, hi, np.corrcoef(Ts[m], Tm[m])[0, 1], np.sum(Ts[m] * Tm[m]) / np.sum(Ts[m] ** 2)) if m.sum() >= 100 else "idx %3d-%3d:  --" % (lo, hi))
            pr("    LIVE-fade chain, %-17s all engaged idx>0: corr %.3f slope %.3f | %s" % (name, np.corrcoef(Ts[ee], Tm[ee])[0, 1], np.sum(Ts[ee] * Tm[ee]) / np.sum(Ts[ee] ** 2), " | ".join(cells)))
        # P-rail onset: |T_meas| by |E| bin (E is Kp-independent), idx >= 100 (Kp 596..696 on V280 rev 2), hands-light
        R = sim(r, *V280R2, kp=KP_OF[tag]); E = np.abs(R["E"][r.i100])
        for lo_i, hi_i in ((100, 241), (40, 100)):
            m0 = e & (r.idx >= lo_i) & (r.idx < hi_i)
            cells = []
            for lo, hi in E_BINS:
                m = m0 & (E >= lo) & (E < hi)
                cells.append("%5.0f-%5.0f: |T| p50 %4.0f rail %.2f (n %4d)" % (lo, min(hi, 99999), np.median(np.abs(r.T_meas[m])), np.mean(np.abs(r.T_meas[m]) >= 2400), m.sum()) if m.sum() >= 30 else "%5.0f-%5.0f: -- (n %4d)" % (lo, min(hi, 99999), m.sum()))
            pr("    tap |T| by chain |E| at idx %d-%d (expected rail: |E| >= 5650 at Kp 696, >= 15855 at Kp 248): %s" % (lo_i, hi_i, " | ".join(cells)))
        # T-per-E slope in the P-linear region, per idx bin; chain DC: T = -0.163*0.99*(254/256)*Kp/256*E => 0.000625*Kp per count of E
        Tl = np.abs(V.output_lag(np.abs(R["E"])))   # lag-filtered |E| on the 1 kHz grid (same lag as T), so the ratio is DC-correct
        El = Tl[r.i100] * 32 / (2 * 507 / 32)        # undo the readout scale (output_lag DC = 2*507/32/32 = 0.99): El ~ |E| lagged
        cells = []
        for lo, hi in IDX_BINS:
            m = e & (r.idx >= lo) & (r.idx < hi) & (El > 500) & (El < 5000) & (np.abs(r.T_meas) < 2400)
            if m.sum() < 100:
                cells.append("idx %3d-%3d: -- (n %d)" % (lo, hi, m.sum())); continue
            slope = np.sum(np.abs(r.T_meas[m]) * El[m]) / np.sum(El[m] ** 2)
            cells.append("idx %3d-%3d: |T|/|E| %.4f -> Kp %3.0f (n %5d)" % (lo, hi, slope, slope / 0.000625, m.sum()))
        pr("    T-per-E slope (|E| 500-5000 lagged, |T| < 2400): %s" % " | ".join(cells))
        # tap saturation and the brake ladder (as HIGHANGLE-r34 SECTION A)
        w = np.abs(r.wire) / CPD
        base = r.eng & (np.sign(-r.wire) == r.sgn) & (r.idx >= 200)
        Rf = sim(r, *V280R2, kp=KP_OF[tag]); Ts = Rf["T"][r.i100]
        cells = []
        for lo, hi in ((40, 60), (60, 80), (80, 100), (100, 130), (130, 400)):
            m = base & (w >= lo) & (w < hi)
            cells.append("%.2f/%.2f (n%4d)" % (np.mean(np.sign(r.T_meas[m]) == r.sgn[m]), np.mean(np.sign(Ts[m]) == r.sgn[m]), m.sum()) if m.sum() >= 20 else "-- (n%4d)" % m.sum())
        pr("    brake fraction meas/sim (route's own Kp) at idx>=200 by rate 40-60 60-80 80-100 100-130 130+: %s" % "  ".join(cells))


# ---------------------------------------------------------------------------------------------------- 2. prereg
def moving_runs(r, R, idx_lo=68, ang=30.0, minlen=100, moving=0.5):
    """runs >= 1 s of engaged & |angle| >= 30 & idx >= idx_lo with the wheel MOVING (rate/ref >= 0.5 over the run)."""
    ref = R["ref_deg"][r.i100]
    m = r.eng & (np.abs(r.ang) >= ang) & (r.idx >= idx_lo)
    out = []
    for a, b in runs_of(m, minlen):
        w = np.abs(r.wire[a:b]) / CPD; rf = ref[a:b]; ok = rf > 0
        rr = float(np.median(w[ok] / rf[ok])) if ok.any() else np.nan
        row = dict(t0=a / FS, dur=(b - a) / FS, rr=rr, idx=float(np.median(r.idx[a:b])), ang=float(np.median(np.abs(r.ang[a:b]))), v=float(r.vego[a:b].mean()),
                   lvl=float(np.median(np.abs(r.T_meas[a:b]))), amp=band_amp(r.T_meas[a:b]), tq_ring=band_amp(r.tq_raw[a:b]), rate_amp=band_amp(r.wire[a:b]) / CPD,
                   tq50=float(np.median(np.abs(r.tq_raw[a:b]))), Prail=float(np.mean(np.abs(R["P_raw"][r.i100][a:b]) >= V.P_CLAMP)), rate=float(np.median(w)), ref=float(np.median(rf[ok])) if ok.any() else np.nan)
        row["ratio"] = row["amp"] / max(row["lvl"], 1)
        # f0 and |bar|/|rate| at f0 (Welch on the run, 5-12 Hz search)
        n = b - a
        f, Pr = signal.welch(r.wire[a:b] - r.wire[a:b].mean(), fs=FS, nperseg=min(128, n))
        _, Pb = signal.welch(r.tq_raw[a:b] - r.tq_raw[a:b].mean(), fs=FS, nperseg=min(128, n))
        sel = (f >= 5) & (f <= 12); k = int(np.argmax(Pr[sel]))
        row["f0"] = float(f[sel][k]); row["bar_over_rate"] = float(np.sqrt(Pb[sel][k] / Pr[sel][k])) if Pr[sel][k] > 0 else np.nan
        row["moving"] = rr >= moving
        out.append(row)
    return out


def section2(routes, Gs):
    pr("\n" + "=" * 160)
    pr("SECTION 2 -- PREREG-V281-READ.md (a)-(k) on r32/r33/r34 (V280 rev 2, stock Kp LERP in the chain) and r35 (V281 rev 3, Kp flat 248 in the chain)")
    pr("=" * 160)
    res = {}
    for tag in ROUTES:
        r = routes[tag]; R = sim(r, *V280R2, kp=KP_OF[tag]); Rkd0 = sim(r, *V280R2, kp=KP_OF[tag], kd=0)
        o = {}
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS); o["high_s"] = hs; o["eng_s"] = float(r.eng.sum() / FS)
        # (a) fixed threshold 103
        eps = ST.fixed_thr_episodes(r); hi = [x for x in eps if x["ang"] >= 30]; f7 = [x for x in hi if x["fdom"] >= 6]
        o["a_fixed_n"] = len(f7); o["a_fixed_per100"] = 100 * len(f7) / hs; o["a_fixed_secs"] = sum(x["dur"] for x in f7)
        own = ST.EPIS[tag]; f7o = [x for x in own if x[2] >= 6]
        o["a_own_n"] = len(f7o); o["a_own_per100"] = 100 * len(f7o) / ST.HIGH_ANG_S[tag]
        pr("%s: engaged %.0f s, high-angle (|angle|>=30) %.1f s | (a) F7 FIXED-103: %d episodes (%.1f s) = %.1f per 100 s [fdom list at >=30: %s] ; own-threshold list: %d F7 = %.1f per 100 s"
           % (tag, o["eng_s"], hs, len(f7), o["a_fixed_secs"], o["a_fixed_per100"], " ".join("%.1f" % x["fdom"] for x in hi), len(f7o), o["a_own_per100"]))
        for lo, hi_ in ((0, 3), (3, 6), (6, 10), (10, 99)):
            mm = r.eng & (np.abs(r.ang) >= 30) & (r.vego >= lo) & (r.vego < hi_)
            o["high_v_%d_%d" % (lo, hi_)] = float(mm.sum() / FS)
        pr("     high-angle time at v 0-3 / 3-6 / 6-10 / 10+ m/s: %.1f / %.1f / %.1f / %.1f s" % tuple(o["high_v_%d_%d" % b] for b in ((0, 3), (3, 6), (6, 10), (10, 99))))
        # (b),(c),(i) in-episode (own list F7 and fixed-103 F7)
        rows = []
        for (t0, dur, fd) in own:
            M, a, b = ST.episode_row(r, R, t0, dur, fd, Rkd0)
            M["cmd_amp7"] = band_amp(r.cmd[b]); M["bar_over_rate"] = M["tq_ring"] / max(M["rate_amp"] * CPD, 1)
            rows.append((t0, dur, fd, M))
            pr("     ep t0 %6.1f dur %3.1f fdom %.2f %s ang %4.0f v %3.1f idx %3.0f | rate %5.1f ref %5.1f r/ref %.2f %-5s | Prail %.2f Drail %.2f fbclp %.2f cliff %.2f | rAmp %4.1f | rip/L sim %.2f meas %.2f (|T| %4.0f) | tqRng %4.0f | bar/rate %.1f | cAmp7 %4.0f | corr %.2f | T re rate %+.0f"
               % (t0, dur, fd, "F7" if fd >= 6 else "F2", M["ang"], M["v"], M["idx50"], M["rate_p50"], M["ref_p50"], M["rate_over_ref"], M["cls"], M["P_rail"], M["D_rail"], M["clamped"], M["cliff"],
                  M["rate_amp"], M["Tsim_ripple_level"], M["Tmeas_ripple_level"], M["absT_meas_p50"], M["tq_ring"], M["bar_over_rate"], M["cmd_amp7"], M.get("corr_T", np.nan), M["ph_Tmeas_re_rate"]))
        f7r = [x for x in rows if x[2] >= 6]
        o["b_ep_median"] = med([x[3]["Tmeas_ripple_level"] for x in f7r]); o["c_ep_median"] = med([x[3]["tq_ring"] for x in f7r])
        o["i_ep_f0"] = med([x[2] for x in f7r]); o["i_ep_bar_rate"] = med([x[3]["bar_over_rate"] for x in f7r])
        o["e_ep_stall"] = sum(1 for x in f7r if x[3]["rate_over_ref"] < 0.5)
        # fixed-103 F7 episodes through the same row (for routes whose own list is empty this is the only in-episode read)
        rows_f = []
        for x in f7:
            M, a, b = ST.episode_row(r, R, x["t0"], x["dur"], x["fdom"], Rkd0)
            M["bar_over_rate"] = M["tq_ring"] / max(M["rate_amp"] * CPD, 1)
            rows_f.append((x["t0"], x["dur"], x["fdom"], M))
        o["b_fixed_median"] = med([x[3]["Tmeas_ripple_level"] for x in rows_f]); o["c_fixed_median"] = med([x[3]["tq_ring"] for x in rows_f])
        o["e_fixed_stall"] = sum(1 for x in rows_f if x[3]["rate_over_ref"] < 0.5)
        pr("     in-episode (own F7, n %d): rip/L median %s ; tq ring median %s ; f0 median %s ; bar/rate median %s ; stalled (r/ref<0.5) %d | fixed-103 F7 (n %d): rip/L %s tq ring %s stalled %d"
           % (len(f7r), "%.2f" % o["b_ep_median"], "%.0f" % o["c_ep_median"], "%.2f" % o["i_ep_f0"], "%.1f" % o["i_ep_bar_rate"], o["e_ep_stall"], len(rows_f), "%.2f" % o["b_fixed_median"], "%.0f" % o["c_fixed_median"], o["e_fixed_stall"]))
        # (b),(c),(i) FRAME-BASED: runs >= 1 s, |angle| >= 30, idx >= 68, wheel moving (rate/ref >= 0.5) -- the read that survives when there are no episodes
        mr = moving_runs(r, R, 68)
        mv = [x for x in mr if x["moving"]]
        o["b_frames_median"] = med([x["ratio"] for x in mv]); o["b_frames_n"] = len(mv); o["b_frames_secs"] = sum(x["dur"] for x in mv)
        o["b_frames_p90"] = float(np.percentile([x["ratio"] for x in mv], 90)) if mv else np.nan
        o["c_frames_median"] = med([x["tq_ring"] for x in mv]); o["i_frames_f0"] = med([x["f0"] for x in mv]); o["i_frames_bar_rate"] = med([x["bar_over_rate"] for x in mv])
        o["rate_amp_frames_median"] = med([x["rate_amp"] for x in mv]); o["lvl_frames_median"] = med([x["lvl"] for x in mv])
        o["Prail_frames_median"] = med([x["Prail"] for x in mv])
        pr("     FRAME-BASED (runs >= 1 s, |angle| >= 30, idx >= 68, wheel moving r/ref >= 0.5): n %d, %.1f s | (b) T rip/L median %.2f (p90 %.2f) | (c) tq ring median %.0f raw | rate 6-8.5 amp median %.1f deg/s | |T| level median %.0f | P-rail median %.2f | (i) f0 median %.2f Hz, bar/rate at f0 median %.1f"
           % (len(mv), o["b_frames_secs"], o["b_frames_median"], o["b_frames_p90"], o["c_frames_median"], o["rate_amp_frames_median"], o["lvl_frames_median"], o["Prail_frames_median"], o["i_frames_f0"], o["i_frames_bar_rate"]))
        for x in sorted(mv, key=lambda x: -x["ratio"])[:6]:
            pr("        t0 %6.1f dur %4.1f idx %3.0f ang %4.0f v %4.1f | rate %5.1f ref %5.1f r/ref %.2f | rip/L %.2f (amp %4.0f lvl %5.0f) | tq ring %4.0f rAmp %4.1f | f0 %.2f bar/rate %.1f | Prail %.2f tq50 %4.0f"
               % (x["t0"], x["dur"], x["idx"], x["ang"], x["v"], x["rate"], x["ref"], x["rr"], x["ratio"], x["amp"], x["lvl"], x["tq_ring"], x["rate_amp"], x["f0"], x["bar_over_rate"], x["Prail"], x["tq50"]))
        # V280-prereg (i): idx >= 200 runs
        st_i = ST.stat_i(r, R)
        o["i280_median"] = med([x["ratio"] for x in st_i]); o["i280_n"] = len(st_i)
        pr("     V280-prereg (i) idx>=200 runs: n %d ratio p50 %.2f, level p50 %.0f, tq ring p50 %.0f" % (len(st_i), o["i280_median"], med([x["lvl"] for x in st_i]), med([x["tq_ring"] for x in st_i])))
        # (e) stalled-wheel class: runs >= 1 s, |angle| >= 30, idx 40-240, rate/ref < 0.5, hands-light (|tq| < 1000, so not the driver holding)
        st_all = moving_runs(r, R, 40)
        stalls = [x for x in st_all if (not x["moving"]) and x["tq50"] < 1000]
        stalls_ring = [x for x in stalls if x["rate_amp"] >= 10]
        o["e_stall_runs"] = len(stalls); o["e_stall_secs"] = sum(x["dur"] for x in stalls); o["e_stall_ring"] = len(stalls_ring)
        o["e_stall_T_p50"] = med([x["lvl"] for x in stalls]); o["e_stall_idx_p50"] = med([x["idx"] for x in stalls])
        pr("     (e) STALLED runs (|angle|>=30, idx 40-240, r/ref < 0.5, |tq| p50 < 1000, >= 1 s): %d runs, %.1f s ; with the r31 stutter signature (6-8.5 Hz rate amp >= 10 deg/s): %d ; |T| p50 %.0f ; idx p50 %.0f ; F7-episode stalls (own/fixed) %d/%d"
           % (len(stalls), o["e_stall_secs"], len(stalls_ring), o["e_stall_T_p50"], o["e_stall_idx_p50"], o["e_ep_stall"], o["e_fixed_stall"]))
        for x in sorted(stalls, key=lambda x: -x["dur"])[:8]:
            pr("        t0 %6.1f dur %4.1f idx %3.0f ang %4.0f v %4.1f | rate %5.1f ref %5.1f r/ref %.2f | |T| %5.0f | tq50 %4.0f | rAmp %4.1f Prail %.2f%s"
               % (x["t0"], x["dur"], x["idx"], x["ang"], x["v"], x["rate"], x["ref"], x["rr"], x["lvl"], x["tq50"], x["rate_amp"], x["Prail"], "  <-- stutter signature" if x["rate_amp"] >= 10 else ""))
        # (d) stat_iv
        iv = ST.stat_iv(r)
        o["d_p50"], o["d_p90"], o["d_n"] = iv[400][1], iv[400][2], iv[400][0]
        o["d_tap_p50"] = iv["tap"][0]
        pr("     (d) hands-light (|tq|<400) sustained full demand: n %d rate p50/p90 %.1f/%.1f deg/s (ceiling %.1f) | tq<2240: %.1f/%.1f | (v) tap |T| p50/p90 %.0f/%.0f | winding %.1f/%.1f (|T| %.0f) returning %.1f/%.1f (|T| %.0f) | v50 %.1f"
           % (iv[400][0], iv[400][1], iv[400][2], V.ceiling_degs(V280R2[0]), iv[2240][1], iv[2240][2], iv["tap"][0], iv["tap"][1], iv["wind"][1], iv["wind"][2], iv["wind"][5], iv["return"][1], iv["return"][2], iv["return"][5], iv["v"]))
        # (f) straight-road rate bands
        for vlo, lab in ((8, "f_8"), (20, "f_20")):
            st = r.eng & (np.abs(r.ang) < 5) & (r.vego >= vlo)
            rs = runs_of(st, 512)
            if sum(b - a for a, b in rs) > 512:
                f, P = welch_runs(r.wire, rs, 512); df = f[1] - f[0]
                band = lambda lo, hi: float(np.sqrt(P[(f >= lo) & (f < hi)].sum() * df * 2)) / CPD  # noqa: E731  amplitude-equivalent deg/s
                o[lab + "_secs"] = sum(b - a for a, b in rs) / FS
                o[lab + "_8.5_10"] = band(8.5, 10); o[lab + "_6_8.5"] = band(6, 8.5); o[lab + "_2_4"] = band(2, 4); o[lab + "_3.5_4.3"] = band(3.5, 4.3); o[lab + "_10_15"] = band(10, 15)
                pr("     (f) straight (|angle|<5) engaged >= %d m/s, %.0f s of >= 5.12 s runs: rate amp-equivalent deg/s 2-4 %.2f | 3.5-4.3 %.2f | 6-8.5 %.2f | 8.5-10 %.3f | 10-15 %.2f"
                   % (vlo, o[lab + "_secs"], o[lab + "_2_4"], o[lab + "_3.5_4.3"], o[lab + "_6_8.5"], o[lab + "_8.5_10"], o[lab + "_10_15"]))
            else:
                pr("     (f) straight >= %d m/s: no runs" % vlo)
        # (h) saturation
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz"))); t0 = D["t18"][0]
        e1 = np.interp(D["t1ab"] - t0, r.tg, r.eng.astype(float)) > 0.5
        o["h_sat"] = float(np.mean((r.fld[e1] & 511) >= 309)); o["h_max"] = int((r.fld[e1] & 511).max()); o["h_313"] = int(np.sum(r.fld == 313))
        m = r.eng & (np.abs(r.cmd) < 1300) & (r.T_meas != 0) & (r.wire != 0)
        o["vi_damp"] = float(np.mean(np.sign(r.T_meas[m]) != np.sign(r.wire[m])))
        pr("     (h) saturation P(|field|>=309) engaged %.4f, max |field| %d, field==313 anywhere %d | (vi) low-command damping fraction %.3f" % (o["h_sat"], o["h_max"], o["h_313"], o["vi_damp"]))
        # (k) held command, unmoving wheel
        for lo, hi_, lab in ((20, 40, "k"), (40, 80, "k4080"), (10, 20, "k1020")):
            base = r.eng & (r.idx >= lo) & (r.idx < hi_)
            dead = base & (np.abs(r.wire) < CPD) & (np.abs(r.ang) > 10)
            o[lab + "_frac_eng"] = float(dead.sum() / max(r.eng.sum(), 1)); o[lab + "_frac_cell"] = float(dead.sum() / max(base.sum(), 1)); o[lab + "_secs"] = dead.sum() / FS
            hl = dead & (np.abs(r.tq_raw) < 400)
            o[lab + "_hl_secs"] = hl.sum() / FS
            o[lab + "_T_dead"] = float(np.median(np.abs(r.T_meas[hl]))) if hl.sum() else np.nan
            mv_ = base & (np.abs(r.wire) >= CPD) & (np.abs(r.ang) > 10) & (np.abs(r.tq_raw) < 400)
            o[lab + "_T_moving"] = float(np.median(np.abs(r.T_meas[mv_]))) if mv_.sum() else np.nan
            o[lab + "_v_dead"] = float(np.median(r.vego[hl])) if hl.sum() else np.nan
            pr("     (%s) idx %d-%d & |rate| < 1 deg/s & |angle| > 10: %.1f s = %.4f of engaged, %.3f of the idx cell (%.1f s) ; hands-light (|tq|<400) %.1f s, tap |T| p50 there %.0f vs %.0f when the wheel moves in the same cell ; v p50 %.1f"
               % (lab, lo, hi_, o[lab + "_secs"], o[lab + "_frac_eng"], o[lab + "_frac_cell"], base.sum() / FS, o[lab + "_hl_secs"], o[lab + "_T_dead"], o[lab + "_T_moving"], o[lab + "_v_dead"]))
        res[tag] = o
    # (g) highway: OSC episodes, strata b48, lane-change windows
    pr("\n  (g) HIGHWAY (engaged, v >= 20, |angle| < 8): OSC episodes (2-12 Hz rate env > 40 wire >= 0.6 s) ; strata 4-8 Hz rate power (wire^2, Welch 1.28 s runs) ; lane-change windows (laneChangeState != off, +2 s settle)")
    for tag in ROUTES:
        G = Gs[tag]; hw = G["hw"]; o = res[tag]
        if hw.sum() < 500:
            pr("     %s: no highway frames" % tag); o["g_hw_secs"] = 0; continue
        eps = L.merge_runs(hw & (G["env"] > L.ENV_THR), int(0.6 * FS), int(0.5 * FS))
        P412, _ = H.band_power(G["rate"], hw, nperseg=256)
        st = L.strata_table(G, tag)
        o["g_hw_secs"] = hw.sum() / FS; o["g_osc_n"] = len(eps); o["g_osc_secs"] = sum(b - a for a, b in eps) / FS
        o["g_P48"] = P412["4-8"]; o["g_P24"] = P412["2-4"]; o["g_P815"] = P412["8-15"]
        o["g_strata"] = [dict(v=s["v"], cmd=s["cmd"], secs=s["secs"], b48=s["b48"], b812=s["b812"], b24=s["b24"], fpk=s["fpk"], osc_duty=s["osc_duty"], cmd50=s["cmd50"]) for s in st]
        pr("     %s highway %.0f s, v p50/max %.1f/%.1f, |cmd| p50/p90 %.0f/%.0f | rate Welch power 2-4/4-8/8-15: %.0f/%.0f/%.0f wire^2 | OSC episodes %d (%.1f s) ; env p50/p95/p99 %s"
           % (tag, o["g_hw_secs"], np.median(G["v"][hw]), G["v"][hw].max(), np.median(np.abs(G["cmd"][hw])), np.percentile(np.abs(G["cmd"][hw]), 90), P412["2-4"], P412["4-8"], P412["8-15"],
              len(eps), o["g_osc_secs"], np.percentile(G["env"][hw], [50, 95, 99]).round(0)))
        for a, b in eps:
            pr("        OSC t0 %6.1f dur %.1f v %.1f |cmd|50 %.0f env pk %.0f fdom %.2f" % (a / FS, (b - a) / FS, G["v"][a:b].mean(), np.median(np.abs(G["cmd"][a:b])), G["env"][a:b].max(), L.fdom(G["rate"][a:b])[0]))
        for s in st:
            pr("        stratum v %d-%d |cmd| %d-%s: %5.0f s | 2-4 %5.0f 4-8 %5.0f 8-12 %5.0f wire^2 | fpk %.2f | osc duty %.3f | cmd50 %.0f" % (
                s["v"][0], s["v"][1], s["cmd"][0], "inf" if s["cmd"][1] > 1e8 else "%d" % s["cmd"][1], s["secs"], s["b24"], s["b48"], s["b812"], s["fpk"], s["osc_duty"], s["cmd50"]))
        lcf = os.path.join(HERE, "_scratch", "_lc_%s.npz" % tag)
        if os.path.exists(lcf):
            lc = dict(np.load(lcf, allow_pickle=True))
            t0 = np.load(os.path.join(HERE, "_scratch", "_ha_%s.npz" % L.ROUTES[tag][0]))["t18"][0]
            code = np.array([{"off": 0, "preLaneChange": 1, "laneChangeStarting": 2, "laneChangeFinishing": 3}.get(s, 0) for s in lc["lcs"]])
            on = np.interp(G["t"], lc["tm"] - t0, code) > 0.5
            wins = L.merge_runs(on, 1, int(1.0 * FS))
            wins = [(a, min(b + int(2 * FS), len(G["t"]))) for a, b in wins]
            rows = []
            for a, b in wins:
                if G["v"][a:b].mean() < 17.7 or (G["eng"][a:b].mean() < 0.5):
                    continue
                ring_runs = L.merge_runs(G["env"][a:b] > L.ENV_THR, int(0.6 * FS), int(0.5 * FS))
                rs = H.runs_of(G["eng"][a:b] & (np.abs(G["tq"][a:b]) < 1000), 128)
                b48 = np.nan
                if rs:
                    f, Pw = welch_runs(G["rate"][a:b], rs, 128); b48 = float(Pw[(f >= 4) & (f < 8)].sum() * (f[1] - f[0])) if f is not None else np.nan
                rows.append(dict(t0=a / FS, dur=(b - a) / FS, v=float(G["v"][a:b].mean()), ring=bool(ring_runs), ring_secs=sum(y - x for x, y in ring_runs) / FS, b48=b48,
                                 env_pk=float(G["env"][a:b].max()), amp48=band_amp(G["rate"][a:b], 4, 8) / CPD, tq50=float(np.median(np.abs(G["tq"][a:b]))), cmd_pk=float(np.abs(G["cmd"][a:b]).max())))
            o["g_lc_n"] = len(rows); o["g_lc_ring"] = sum(x["ring"] for x in rows); o["g_lc_b48"] = med([x["b48"] for x in rows])
            pr("     %s lane-change windows >= 17.7 m/s engaged: %d, ring (env>40 >= 0.6 s, ungated) %d ; b48 median %.0f wire^2 | %s" % (
                tag, len(rows), o["g_lc_ring"], o["g_lc_b48"], "; ".join("t0 %.0f v %.1f amp48 %.1f deg/s envpk %.0f b48 %.0f %s tq50 %.0f cmdpk %.0f" % (x["t0"], x["v"], x["amp48"], x["env_pk"], x["b48"], "RING %.1fs" % x["ring_secs"] if x["ring"] else "no-ring", x["tq50"], x["cmd_pk"]) for x in rows)))
        else:
            pr("     %s: no _lc_ cache" % tag)
    return res


# ---------------------------------------------------------------------------------------------------- 3. understeer / deadband
IDX_BINS3 = ((0, 20), (20, 40), (40, 80), (80, 241))
ANG_BINS3 = ((0, 10), (10, 20), (20, 50), (50, 120), (120, 1e9))


def section3(routes, grids, res):
    pr("\n" + "=" * 160)
    pr("SECTION 3 -- THE UNDERSTEER / DEADBAND HYPOTHESIS: tracking error on curves (|desired lat accel| > 0.3, engaged, hands off, runs >= 1.5 s) by demand index and |angle|")
    pr("  err_pose = dir*(livePose lat accel - desired) [physical; torqued's instrument, incl. the roll term] ; err_m = dir*(torqueState.actualLateralAccel - desired) [the controller's own, steering-angle model, SR 12.5 on r35 / 16.1 on r34 / 14.0 on r32-r33]")
    pr("  negative = UNDERSTEER (less lat accel than asked in the curve's direction). rel = actual/des - 1 at |des| > 0.5. dead = |0x18F rate| < 1 deg/s. idx from 0xE4 cmd and 0x18F driver torque (V.demand).")
    pr("=" * 160)
    out = {}
    for tag in ROUTES:
        g = grids[tag]
        des = g["desiredLateralAccel"]; m = g["actualLateralAccel"]; pose = g["lat_torqued"]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
        curve = ok & (np.abs(des) > CO.DES_THR)
        runs = CO.merge_runs(curve, int(1.5 * FS), int(0.3 * FS))
        dirf = np.zeros(len(des)); cm = np.zeros(len(des), bool)
        for a, b in runs:
            d = np.sign(np.median(des[a:b])) or 1.0
            dirf[a:b] = d; cm[a:b] = True
        idx, _ = V.demand(g["cmd"], g["drv18"] * 1.024)
        rate = np.abs(g["rate18"]) / CPD
        ep = dirf * (pose - des); em = dirf * (m - des)
        big = np.abs(des) > 0.5
        o = dict(n_curves=len(runs), curve_secs=cm.sum() / FS)
        pr("  %s (%s): %d curves, %.0f s | ALL curve frames: err_pose p50 %+.3f (p25/p75 %+.3f/%+.3f) err_m %+.3f | rel_pose %+.3f rel_m %+.3f | m/pose p50 %.3f | |des| p50 %.2f | idx p50 %.0f | dead frac %.3f"
           % (tag, V.ROUTE_BUILD.get(tag, ""), len(runs), o["curve_secs"], med(ep[cm]), np.percentile(ep[cm], 25), np.percentile(ep[cm], 75), med(em[cm]), med(pose[cm & big] / des[cm & big] - 1), med(m[cm & big] / des[cm & big] - 1),
              med(m[cm & big] / pose[cm & big]), med(np.abs(des[cm])), med(idx[cm]), float(np.mean(rate[cm] < 1))))
        o["ep_all"] = med(ep[cm]); o["em_all"] = med(em[cm]); o["relp_all"] = med(pose[cm & big] / des[cm & big] - 1); o["relm_all"] = med(m[cm & big] / des[cm & big] - 1)
        o["m_over_pose"] = med(m[cm & big] / pose[cm & big])
        pr("     by idx:   " + " | ".join("idx %3d-%3d: %5.0f s err_pose %+.3f err_m %+.3f rel_pose %+.2f dead %.3f |des| %.2f v %4.1f" % (
            lo, hi, (cm & (idx >= lo) & (idx < hi)).sum() / FS, med(ep[cm & (idx >= lo) & (idx < hi)]), med(em[cm & (idx >= lo) & (idx < hi)]),
            med(pose[cm & big & (idx >= lo) & (idx < hi)] / des[cm & big & (idx >= lo) & (idx < hi)] - 1), float(np.mean(rate[cm & (idx >= lo) & (idx < hi)] < 1)) if (cm & (idx >= lo) & (idx < hi)).any() else np.nan,
            med(np.abs(des[cm & (idx >= lo) & (idx < hi)])), med(g["v"][cm & (idx >= lo) & (idx < hi)])) for lo, hi in IDX_BINS3))
        pr("     by |ang|: " + " | ".join("ang %3d-%3s: %5.0f s err_pose %+.3f err_m %+.3f rel_pose %+.2f dead %.3f idx %3.0f v %4.1f" % (
            lo, "inf" if hi > 1e8 else "%d" % hi, (cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)).sum() / FS, med(ep[cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)]),
            med(em[cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)]),
            med(pose[cm & big & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)] / des[cm & big & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)] - 1),
            float(np.mean(rate[cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)] < 1)) if (cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)).any() else np.nan,
            med(idx[cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)]), med(g["v"][cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)])) for lo, hi in ANG_BINS3))
        for lo, hi in IDX_BINS3:
            s = cm & (idx >= lo) & (idx < hi)
            o["ep_idx_%d_%d" % (lo, hi)] = med(ep[s]); o["em_idx_%d_%d" % (lo, hi)] = med(em[s]); o["secs_idx_%d_%d" % (lo, hi)] = s.sum() / FS
            o["dead_idx_%d_%d" % (lo, hi)] = float(np.mean(rate[s] < 1)) if s.any() else np.nan
        for lo, hi in ANG_BINS3:
            s = cm & (np.abs(g["ang"]) >= lo) & (np.abs(g["ang"]) < hi)
            o["ep_ang_%d_%d" % (lo, min(hi, 999))] = med(ep[s]); o["em_ang_%d_%d" % (lo, min(hi, 999))] = med(em[s]); o["secs_ang_%d_%d" % (lo, min(hi, 999))] = s.sum() / FS
        # the controller's error and the sign of P/I in the curves (does the controller SEE the understeer?)
        s = cm & (np.abs(g["error"]) < 5)
        pr("     controller: torqueState.error*dir p50 %+.3f (its own m-based error; >0 = it thinks it is UNDER) | p*dir %+.3f i*dir %+.3f f*dir %+.3f | |output| p50 %.3f p90 %.3f | 0xE4 |cmd| p50 %.0f p90 %.0f"
           % (med(dirf[s] * (des[s] - m[s])), med(g["p"][s] * dirf[s]), med(g["i"][s] * dirf[s]), med(g["f"][s] * dirf[s]), med(np.abs(g["output"][s])), np.percentile(np.abs(g["output"][s]), 90),
              med(np.abs(g["cmd"][s])), np.percentile(np.abs(g["cmd"][s]), 90)))
        # straight-road bias reference
        st = ok & (np.abs(des) < 0.2) & (g["v"] > 10)
        o["straight_pose_bias"] = med(pose[st] - des[st]); o["straight_m_bias"] = med(m[st] - des[st])
        pr("     straight reference (|des|<0.2, v>10, %.0f s): pose-des p50 %+.3f, m-des %+.3f" % (st.sum() / FS, o["straight_pose_bias"], o["straight_m_bias"]))
        out[tag] = o
    # SR bias separated: on r35 m is inflated by ~16.1/12.5 = 1.288 relative to the same angle on r34 (the vehicle model is angle/SR)
    pr("\n  SR bias: the controller closes its loop on m (steering-angle model). With SR 12.5 the model reads 16.1/12.5 = 1.288x the r34 reading for the same angle,")
    pr("  so the loop is satisfied (m = des) when the REAL lat accel is ~1/1.288 = 0.776 of the request, before any EPS deadband. Measured m/pose per route above; expected r34 ~1.10 (VM stiffness term), r35 ~1.42.")
    # the chain's own prediction on r35's low-demand frames
    pr("\n  THE CHAIN ON THE LOW-DEMAND FRAMES (engaged, |angle| > 10, hands-light |tq| < 400): E from the measured rate, P under the route's own Kp and the counterfactual, T_sim vs the tap")
    for tag in ("r34", NEW):
        r = routes[tag]
        Rown = sim(r, *V280R2, kp=KP_OF[tag]); Rcf = sim(r, *V280R2, kp=(KP_FLAT if tag == "r34" else KP_STOCK))
        for lo, hi in ((10, 20), (20, 40), (40, 80), (80, 120)):
            s = r.eng & (r.idx >= lo) & (r.idx < hi) & (np.abs(r.ang) > 10) & (np.abs(r.tq_raw) < 400)
            if s.sum() < 100:
                pr("     %s idx %d-%d: n %d -- skipped" % (tag, lo, hi, s.sum())); continue
            To, Tc = np.abs(Rown["T"][r.i100][s]), np.abs(Rcf["T"][r.i100][s]); Tm = np.abs(r.T_meas[s])
            dead = np.abs(r.wire[s]) < CPD
            E = np.abs(Rown["E"][r.i100][s]); kpo = Rown["kp"][r.i100][s]
            pr("     %s idx %3d-%3d: %5.1f s | Kp own p50 %3.0f | |E| p50 %5.0f | T_sim own p50 %4.0f (p90 %4.0f) vs counterfactual %4.0f | tap |T| p50 %4.0f (p90 %4.0f) | frac |T_sim own| < 690 %.2f, < 555 %.2f | wheel dead %.3f ; tap |T| when dead %4.0f, when moving %4.0f | ref p50 %4.1f rate p50 %4.1f deg/s"
               % (tag, lo, hi, s.sum() / FS, med(kpo), med(E), med(To), np.percentile(To, 90), med(Tc), med(Tm), np.percentile(Tm, 90), float(np.mean(To < 690)), float(np.mean(To < 555)), float(np.mean(dead)),
                  med(Tm[dead]), med(Tm[~dead]), med(Rown["ref_deg"][r.i100][s]), med(np.abs(r.wire[s]) / CPD)))
    # the deadband in command units: 0.02-0.03 torque = 82-123 counts of 0xE4 -> idx and T at Kp 248
    pr("\n  the r34 back-calc deadband 0.02-0.03 openpilot torque = 82-123 counts of 0xE4 command -> idx %.0f-%.0f -> map sp %.0f-%.0f -> 32*sp %.0f-%.0f counts of E (wheel stopped, fb = 0) -> P at Kp 248: %.0f-%.0f -> T_sim %.0f-%.0f counts (V280 rev 2 Kp there %.0f-%.0f -> T %.0f-%.0f)"
       % tuple(np.r_[[V.demand(np.array([-c]), np.array([0.0]))[0][0] for c in (82, 123)],
                     [V.lerp(V.MAP_X, V280R2[0], V.demand(np.array([-c]), np.array([0.0]))[0][0]) for c in (82, 123)],
                     [32 * V.lerp(V.MAP_X, V280R2[0], V.demand(np.array([-c]), np.array([0.0]))[0][0]) for c in (82, 123)],
                     [32 * V.lerp(V.MAP_X, V280R2[0], V.demand(np.array([-c]), np.array([0.0]))[0][0]) * 248 / 256 for c in (82, 123)],
                     [32 * V.lerp(V.MAP_X, V280R2[0], V.demand(np.array([-c]), np.array([0.0]))[0][0]) * 248 / 256 * 254 / 256 * 0.99 * 5346 / 32768 for c in (82, 123)],
                     [V.lerp(*KP_STOCK, V.demand(np.array([-c]), np.array([0.0]))[0][0]) for c in (82, 123)],
                     [32 * V.lerp(V.MAP_X, V280R2[0], V.demand(np.array([-c]), np.array([0.0]))[0][0]) * V.lerp(*KP_STOCK, V.demand(np.array([-c]), np.array([0.0]))[0][0]) / 256 * 254 / 256 * 0.99 * 5346 / 32768 for c in (82, 123)]]))
    return out


# ---------------------------------------------------------------------------------------------------- 4. oversteer
def section4():
    pr("\n" + "=" * 160)
    pr("SECTION 4 -- OVERSTEER BINS exactly as curve_oversteer_r34.py (signed overshoot, + = more lat accel than asked), r34 (V280 rev 2) vs r35 (V281 rev 3)")
    pr("=" * 160)
    out = {}
    for tag in ("r34", NEW):
        CO.LINES.clear()
        o = CO.analyse(tag)
        LINES.extend(CO.LINES)
        out[tag] = o
    pr("\n  SIDE BY SIDE (medians over curves)")
    keys = ["n", "entry_os_m", "entry_os_vyaw", "entry_os_pose", "entry_rel_m", "entry_rel_pose", "entry_f", "entry_p", "entry_i", "entry_ff_share", "entry_fight_p", "entry_fight_i",
            "steady_os_m", "steady_os_vyaw", "steady_os_pose", "steady_rel_m", "steady_rel_pose", "steady_f", "steady_p", "steady_i", "steady_ff_share", "steady_fight_p", "steady_fight_i", "i_exc", "i_t63",
            "steady_os_pose_dir-1", "steady_os_pose_dir+1", "entry_slope_des", "steady_slope_des", "straight_pose_bias", "straight_m_bias"]
    pr("  %-22s %10s %10s" % ("", "r34", "r35"))
    for k in keys:
        pr("  %-22s %10s %10s" % (k, *["%+.3f" % out[t]["summary"].get(k, np.nan) if k != "n" else "%d" % out[t]["summary"][k] for t in ("r34", NEW)]))
    for ph in ("steady", "entry"):
        pr("  BINS %s os_pose/rel_pose | os_m/rel_m by |angle| [secs]  (r34 | r35):" % ph)
        for lo, hi in CO.ANG_BINS:
            cells = []
            for t in ("r34", NEW):
                r = out[t]["bins"].get("%s ang %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f | %+.3f/%+.2f [%3.0f]" % (r["os_pose"], r["rel_pose"], r["os_m"], r["rel_m"], r["secs"]) if r else "         --         ")
            pr("    ang %-8s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "   ".join(cells)))
        pr("  BINS %s by speed:" % ph)
        for lo, hi in CO.V_BINS:
            cells = []
            for t in ("r34", NEW):
                r = out[t]["bins"].get("%s v %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f | %+.3f/%+.2f [%3.0f]" % (r["os_pose"], r["rel_pose"], r["os_m"], r["rel_m"], r["secs"]) if r else "         --         ")
            pr("    v %-10s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), "   ".join(cells)))
    pr("  aligned trajectory (curves >= 3 s) t: |des| os_m os_vyaw os_pose f p i |out|:")
    for t in ("r34", NEW):
        for tt, v_ in out[t]["traj"].items():
            pr("    %s %4.2f | " % (t, float(tt)) + "  ".join("%+.3f" % x for x in v_))
    return {t: dict(summary=out[t]["summary"], bins=out[t]["bins"], traj=out[t]["traj"]) for t in out}


def main():
    routes, grids, Gs = {}, {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
        grids[tag] = B.grid(B.load(tag))
        Gs[tag] = L.load(tag)
    section0(grids)
    section1(routes)
    res = section2(routes, Gs)
    und = section3(routes, grids, res)
    ovs = section4()
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    out = os.path.join(HERE, "_scratch", "v281r3_read_r35.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    json.dump(dict(prereg=res, understeer=und, oversteer=ovs), open(os.path.join(HERE, "v281r3_read_r35.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else str(o)))
    print("wrote", out)


if __name__ == "__main__":
    main()
