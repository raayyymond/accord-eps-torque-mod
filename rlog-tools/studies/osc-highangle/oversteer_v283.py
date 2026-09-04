# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v283.py -- DECOMPOSING THE OVERSTEER the operator reports on V283
(r36/r37/r38) against r35 (V281 rev 3, Ki 0, same tune) and r34 (V280 rev 2, SR 16.1).

V283 = V282 (= V281 rev 3 + the inert r24 comparator cave) + 0xC63E6 Ki 0 -> 50 on the LKAS rate PID.
Verified from the images this session: v282 -> v283 differs in exactly 0xC63E6 (00 -> 32) and the 0xC6FFC CRC.

Sections
  0  the tune BACK-CALCULATED from the wire (no toggle backup was supplied for these drives)
  1  build attribution from the 427 tap: Kp table, and whether the INTEGRATOR is visible (chain with Ki 0 vs Ki 50)
  2  the OVERSTEER statistic, identical code/bins to curve_oversteer_r34.analyse
  3  PREREG-V283-READ.md (a)(b)(c): the stall/deadband class that Ki was cut to fix
  4  the integrator's SHARE of the delivered torque (accumulator reconstructed offline from the wire)
  5  the outer loop (StarPilot's own p/i/f), the exit overshoot, the post-curve residual, the 0.2-1 Hz straight hunt

Run: python oversteer_v283.py   (needs analysis-2020accord/_scratch/cache/v280/r3{4..8}.npz and
     analysis-2020accord/studies/optune/_scratch/r3{4..8}_backcalc.npz)
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
import strongturn_r34 as S34  # noqa: E402  (registers r32/r33/r34 and patches V.load with the tap)
import twist_taper_loop as TT  # noqa: E402
import curve_oversteer_r34 as CO  # noqa: E402
import backcalc_laf_friction as B  # noqa: E402
import highangle_stutter as H  # noqa: E402

V, ST = S34.V, S34.ST
FS, FS1K = ST.FS, V.FS1K
CPD = V.CPD

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NEW = ("r36", "r37", "r38")
PREFIX = {"r35": "75604b0a432fdc89_00000035--580292087d",
          "r36": "75604b0a432fdc89_00000036--f4be1a18e9",
          "r37": "75604b0a432fdc89_00000037--4a79da5d18",
          "r38": "75604b0a432fdc89_00000038--f77bddf4bd"}
for t, p in PREFIX.items():
    V.ROUTE_PREFIX[t] = p
    V.ROUTE_K[t] = 6.0
    ST.TAP_TAGS.add(t)
    CO.LAF[t] = 2.11
V.ROUTE_BUILD["r35"] = "V281r3 Kp flat 248, Ki 0 (SR 12.5 tune)"
for t in NEW:
    V.ROUTE_BUILD[t] = "V283 Kp flat 248 + Ki 50 (SR 12.5 tune)"

ROUTES = ("r34", "r35") + NEW
V280R2 = ST.V280R2
FW = TT.FW
IMG = {"V280r2": TT.IMG_V280,
       "V281r3": FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V283": FW + "_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"}
T280 = TT.read_tables(IMG["V280r2"])
T283 = TT.read_tables(IMG["V283"])
KP_STOCK = (T280["kp"][1], T280["kp"][2])
KP_FLAT = (T283["kp"][1], T283["kp"][2])
KP_OF = {"r34": KP_STOCK, "r35": KP_FLAT, "r36": KP_FLAT, "r37": KP_FLAT, "r38": KP_FLAT}
KI_OF = {"r34": 0, "r35": 0, "r36": 50, "r37": 50, "r38": 50}

# integral cells, read from the images (LE u16)
def u16(img, off):
    d = open(img, "rb").read()
    return d[off] | (d[off + 1] << 8)


KI_CELL = {k: u16(v, 0xC63E6) for k, v in IMG.items()}
I_CLAMP = u16(IMG["V283"], 0xC61BA)      # 10240
DEADBAND = u16(IMG["V283"], 0xC62E4)     # 4

LAG_DC = (V.OB / 1024.0) / (1 - V.OA / 1024.0) * 2 / 32.0      # 0.9902, the output lag's DC gain
T_PER_S = LAG_DC * V.GAIN / 32768.0                             # 0.16155 counts of tap T per count of the PID sum S

LINES = []


def pr(s=""):
    print(s, flush=True); LINES.append(s)


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def runs_of(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def band_amp(x, lo=6.0, hi=8.5):
    return ST.band_amp(np.asarray(x, float), lo, hi) if len(x) > 40 else np.nan


# ------------------------------------------------------------------------------------------------ the chain, with I
def sim(r, Y=None, clamp=None, kp=KP_STOCK, kd=V.KD, ki=0):
    """v281r3_read_r35.sim() with the INTEGRAL rung of FUN_00028ea6 added (ki_sizing.py's re-derivation):
         excess = deadband(E >> 5, 0xC62E4=4) ; acc = clamp(acc + (excess*Ki >> 3), +- 0xC61BA*128)
         I      = acc >> 7  (so |I| <= 10240) ; S = clamp(254*(P + I + D) >> 8, +- 15360)
       Ki == 0 reproduces sim() exactly (no accumulation).  1 kHz grid, integer semantics."""
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
    onset = r.eng1k & ~np.r_[False, r.eng1k[:-1]]
    dE[onset] = 0.0
    D_raw = np.floor(dE * kd / 8)
    Dt = np.clip(D_raw, -V.D_CLAMP, V.D_CLAMP)
    if ki:
        Iterm = integrate(E, r.eng1k, ki)
    else:
        Iterm = np.zeros_like(E)
    S_raw = np.floor(V.SUM_MULT * (P + Iterm + Dt) / 256)
    S = np.clip(S_raw, -V.SUM_CLAMP, V.SUM_CLAMP)
    S[~r.eng1k] = 0.0
    lag = V.output_lag(S)
    T = np.clip(np.floor(-lag * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
    R = dict(E=E, P_raw=P_raw, P=P, I=Iterm, D_raw=D_raw, D=Dt, S_raw=S_raw, S=S, T=T, fb=fb, sp=sp, kp=kpv)
    R["clamped"] = np.abs(r.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(sp) / V.FB_DC / CPD
    return R


def integrate(E, eng, ki, db=None, clamp=None):
    """acc += (deadband(E>>5, db) * ki) >> 3 ; acc clamped to +-clamp*128 ; returns I = acc >> 7 (float mirror of the
    integer path; >> on negatives is floor in V850 sar too, so np.floor is the right mirror)."""
    db = DEADBAND if db is None else db
    clamp = I_CLAMP if clamp is None else clamp
    e5 = np.floor(E / 32.0)
    excess = np.where(e5 > db, e5 - db, np.where(e5 < -db, e5 + db, 0.0))
    step = np.floor(excess * ki / 8.0)
    acc = np.zeros(len(E))
    lim = clamp * 128.0
    a = 0.0
    prev_eng = False
    for i in range(len(E)):
        if not eng[i]:
            a = 0.0                      # reset path (disengaged); see FUN_00028ea6 reset rung
        else:
            a = min(max(a + step[i], -lim), lim)
        acc[i] = a
    return np.floor(acc / 128.0)


# ------------------------------------------------------------------------------------------------ 0. tune
def section0(grids):
    pr("=" * 170)
    pr("SECTION 0 -- THE TUNE, BACK-CALCULATED FROM THE WIRE (no toggle backup was supplied for r36/r37/r38; r34/r35 have one and are the control on the method)")
    pr("  method = v281r3_read_r35.section0: LAF = -(p+i+d+f)/output, kp = p/error, friction from the f regression, liveParameters.steerRatio, and the")
    pr("  vehicle-model constant |m|/(|angle_rad| v^2) (proportional to 1/SR). Reference (toggle backups): r34 SR 16.1, r35 SR 12.5, both LAF 2.11 fr 0.03 KP 0.6.")
    pr("=" * 170)
    out = {}
    for tag in ROUTES:
        g = grids[tag]
        o = B.live_values(g)
        D = B.load(tag)
        sr = D["lpar_sr"]; sr = sr[~np.isnan(sr)]
        cp = D["cp"]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (np.abs(g["desiredLateralAccel"]) > 0.5) & (g["v"] > 8)
        ratio = g["actualLateralAccel"][ok] / g["lat_torqued"][ok]
        ratio = ratio[np.isfinite(ratio) & (np.abs(g["lat_torqued"][ok]) > 0.5)]
        okk = ok & (np.abs(g["ang"]) > 3) & (np.abs(g["actualLateralAccel"]) > 0.3)
        k = np.abs(g["actualLateralAccel"][okk]) / (np.abs(np.radians(g["ang"][okk])) * g["v"][okk] ** 2)
        row = dict(LAF=o.get("LAF_from_pid_p50", np.nan), LAF5=o.get("LAF_from_pid_p5", np.nan), LAF95=o.get("LAF_from_pid_p95", np.nan),
                   kp=o.get("kp_p50", np.nan), fric=o.get("friction_from_f", np.nan), ltp=o.get("latAccelFactorFiltered_last", np.nan),
                   useParams=o.get("useParams_p50", np.nan), sr=float(np.median(sr)) if len(sr) else np.nan,
                   sr_first=float(sr[0]) if len(sr) else np.nan, sr_last=float(sr[-1]) if len(sr) else np.nan,
                   cp_sr=cp["steerRatio"], m_over_pose=med(ratio), vm=med(k), delay=cp["steerActuatorDelay"], lag=med(g["lag"]))
        out[tag] = row
        pr("  %s (%s): LAF %.3f (p5-p95 %.3f-%.3f) | kp %.3f | friction %.3f | ltp LAFfilt(last) %.3f useParams %.0f | liveParameters.SR %.2f (first %.2f last %.2f; carParams %.2f) | m/pose %.3f | VM const %.4f 1/m | liveDelay p50 %.2f s"
           % (tag, V.ROUTE_BUILD.get(tag, "?"), row["LAF"], row["LAF5"], row["LAF95"], row["kp"], row["fric"], row["ltp"], row["useParams"],
              row["sr"], row["sr_first"], row["sr_last"], row["cp_sr"], row["m_over_pose"], row["vm"], row["lag"]))
    base = out["r35"]["vm"]
    pr("  VM constant relative to r35 (SR 12.5): " + " | ".join("%s %.3f" % (t, out[t]["vm"] / base) for t in ROUTES)
       + "   [r34/r35 = 16.1/12.5 = 1.288 is the known-good calibration of this estimator]")
    return out


# ------------------------------------------------------------------------------------------------ 1. attribution
IDX_BINS = ((1, 40), (40, 68), (68, 112), (112, 136), (136, 241))


def section1(routes):
    pr("\n" + "=" * 170)
    pr("SECTION 1 -- BUILD ATTRIBUTION FROM THE 427 TAP: is Kp still flat 248, and IS THE INTEGRATOR ON THE WIRE?")
    pr("  cells read from the images: 0xC63E6 Ki  V280r2/V281r3 %d, V283 %d | 0xC61BA I clamp %d | 0xC62E4 deadband %d | Kp Y V283 %s (V280 rev 2 %s)"
       % (KI_CELL["V281r3"], KI_CELL["V283"], I_CLAMP, DEADBAND, KP_FLAT[1].astype(int).tolist(), KP_STOCK[1].astype(int).tolist()))
    pr("  frames: engaged, idx > 0, hands-light |tq_raw| < 512. LS slope = sum(Ts*Tm)/sum(Ts^2); 1.00 = the candidate reproduces the tap's scale.")
    pr("=" * 170)
    res = {}
    for tag in ROUTES:
        r = routes[tag]
        e = r.eng & (r.idx > 0) & (np.abs(r.tq_raw) < 512)
        pr("  %s (%s): %.0f s hands-light engaged idx>0" % (tag, V.ROUTE_BUILD[tag], e.sum() / FS))
        row = {}
        for name, kp, ki in (("stock LERP, Ki 0", KP_STOCK, 0), ("flat 248, Ki 0", KP_FLAT, 0), ("flat 248, Ki 50", KP_FLAT, 50), ("flat 248, Ki 25", KP_FLAT, 25), ("flat 248, Ki 100", KP_FLAT, 100)):
            R = sim(r, kp=kp, ki=ki); Ts = R["T"][r.i100]; Tm = r.T_meas
            cells = []
            for lo, hi in IDX_BINS:
                m = e & (r.idx >= lo) & (r.idx < hi)
                cells.append("%3d-%3d: %.3f/%.2f" % (lo, hi, np.corrcoef(Ts[m], Tm[m])[0, 1], np.sum(Ts[m] * Tm[m]) / np.sum(Ts[m] ** 2)) if m.sum() >= 100 else "%3d-%3d: --" % (lo, hi))
            rmse = float(np.sqrt(np.mean((Ts[e] - Tm[e]) ** 2)))
            row[name] = dict(corr=float(np.corrcoef(Ts[e], Tm[e])[0, 1]), slope=float(np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2)), rmse=rmse)
            pr("    %-18s all: corr %.4f slope %.3f rmse %5.0f | corr/slope by idx  %s" % (name, row[name]["corr"], row[name]["slope"], rmse, "  ".join(cells)))
        res[tag] = row
    return res


# ------------------------------------------------------------------------------------------------ 2. oversteer
def section2():
    pr("\n" + "=" * 170)
    pr("SECTION 2 -- THE OVERSTEER STATISTIC, curve_oversteer_r34.analyse UNCHANGED (same curve definition, same entry/steady windows, same bins)")
    pr("  os = dir*(actual - desired) lat accel [+ = MORE than asked = oversteer]; rel = actual/des - 1 at |des| > 0.5;")
    pr("  instruments: pose = livePose yaw*v - g sin(roll) [the road] ; vyaw = yaw*v [no roll term] ; m = the controller's own steering-angle model.")
    pr("=" * 170)
    out = {}
    for tag in ROUTES:
        CO.LINES.clear()
        out[tag] = CO.analyse(tag)
        LINES.extend(CO.LINES)
    pr("\n  SIDE BY SIDE (medians over curves)   r34 = V280r2 SR 16.1 | r35 = V281r3 Ki 0 SR 12.5 | r36/r37/r38 = V283 Ki 50 SR 12.5")
    keys = ["n", "entry_os_pose", "entry_os_vyaw", "entry_os_m", "entry_rel_pose", "entry_rel_m", "entry_f", "entry_p", "entry_i", "entry_ff_share",
            "steady_os_pose", "steady_os_vyaw", "steady_os_m", "steady_rel_pose", "steady_rel_m", "steady_f", "steady_p", "steady_i", "steady_ff_share",
            "steady_fight_p", "steady_fight_i", "i_exc", "i_t63", "steady_os_pose_dir-1", "steady_os_pose_dir+1", "straight_pose_bias", "straight_m_bias"]
    pr("  %-22s %9s %9s %9s %9s %9s" % ("", *ROUTES))
    for k in keys:
        pr("  %-22s %9s %9s %9s %9s %9s" % (k, *["%+.3f" % out[t]["summary"].get(k, np.nan) if k != "n" else "%d" % out[t]["summary"][k] for t in ROUTES]))
    for ph in ("steady", "entry"):
        pr("  BINS %s os_pose/rel_pose [secs] by |angle|:" % ph)
        for lo, hi in CO.ANG_BINS:
            cells = []
            for t in ROUTES:
                b = out[t]["bins"].get("%s ang %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f[%3.0f]" % (b["os_pose"], b["rel_pose"], b["secs"]) if b else "      --      ")
            pr("    ang %-8s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), " ".join(cells)))
        pr("  BINS %s os_pose/rel_pose [secs] by speed:" % ph)
        for lo, hi in CO.V_BINS:
            cells = []
            for t in ROUTES:
                b = out[t]["bins"].get("%s v %g-%g" % (ph, lo, hi))
                cells.append("%+.3f/%+.2f[%3.0f]" % (b["os_pose"], b["rel_pose"], b["secs"]) if b else "      --      ")
            pr("    v %-10s %s" % ("%g-%s" % (lo, "inf" if hi > 1e8 else "%g" % hi), " ".join(cells)))
    pr("  ALIGNED trajectory os_pose (and os_vyaw) at t = 0/0.5/1/2/3 s from curve entry:")
    for t in ROUTES:
        tr = out[t]["traj"]
        pr("    %s os_pose %s | os_vyaw %s" % (t, "  ".join("%.1fs %+.3f" % (float(k), tr[k][3]) for k in tr if float(k) in (0, 0.5, 1.0, 2.0, 3.0)),
                                               "  ".join("%.1fs %+.3f" % (float(k), tr[k][2]) for k in tr if float(k) in (0, 0.5, 1.0, 2.0, 3.0))))
    return {t: dict(summary=out[t]["summary"], bins=out[t]["bins"], traj=out[t]["traj"], curves=out[t]["curves"]) for t in out}


# ------------------------------------------------------------------------------------------------ 3. the stall class
def moving_runs(r, R, idx_lo=68, ang=30.0, minlen=100):
    ref = R["ref_deg"][r.i100]
    m = r.eng & (np.abs(r.ang) >= ang) & (r.idx >= idx_lo)
    out = []
    for a, b in runs_of(m, minlen):
        w = np.abs(r.wire[a:b]) / CPD
        rf = ref[a:b]
        ok = rf > 0
        rr = float(np.median(w[ok] / rf[ok])) if ok.any() else np.nan
        row = dict(t0=a / FS, dur=(b - a) / FS, rr=rr, idx=float(np.median(r.idx[a:b])), ang=float(np.median(np.abs(r.ang[a:b]))),
                   v=float(r.vego[a:b].mean()), lvl=float(np.median(np.abs(r.T_meas[a:b]))), amp=band_amp(r.T_meas[a:b]),
                   tq_ring=band_amp(r.tq_raw[a:b]), rate_amp=band_amp(r.wire[a:b]) / CPD, tq50=float(np.median(np.abs(r.tq_raw[a:b]))),
                   Prail=float(np.mean(np.abs(R["P_raw"][r.i100][a:b]) >= V.P_CLAMP)), rate=float(np.median(w)),
                   ref=float(np.median(rf[ok])) if ok.any() else np.nan, Ip50=float(np.median(np.abs(R["I"][r.i100][a:b]))))
        row["ratio"] = row["amp"] / max(row["lvl"], 1)
        row["moving"] = rr >= 0.5
        out.append(row)
    return out


def section3(routes, sims):
    pr("\n" + "=" * 170)
    pr("SECTION 3 -- PREREG-V283-READ.md (a)(b)(c): the STALL / DEADBAND class Ki was cut to fix (same code and thresholds as the r35 read)")
    pr("=" * 170)
    res = {}
    for tag in ROUTES:
        r = routes[tag]
        R = sims[tag]
        o = {}
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS)
        o["eng_s"] = float(r.eng.sum() / FS)
        o["high_s"] = hs
        st_all = moving_runs(r, R, 40)
        stalls = [x for x in st_all if (not x["moving"]) and x["tq50"] < 1000]
        long_st = [x for x in stalls if x["dur"] > 1.5]
        o["a_runs"] = len(stalls)
        o["a_secs"] = sum(x["dur"] for x in stalls)
        o["a_long"] = len(long_st)
        o["a_T_p50"] = med([x["lvl"] for x in stalls])
        o["a_idx_p50"] = med([x["idx"] for x in stalls])
        o["a_per100"] = 100 * len(stalls) / max(hs, 1e-9)
        pr("  %s: engaged %.0f s, high-angle (|ang|>=30) %.1f s | (a) STALLED runs >= 1 s (idx 40-240, rate/ref < 0.5, |tq| p50 < 1000): %d (%.1f s, %.1f per 100 s of high-angle), > 1.5 s: %d | |T| p50 %.0f | idx p50 %.0f"
           % (tag, o["eng_s"], hs, len(stalls), o["a_secs"], o["a_per100"], len(long_st), o["a_T_p50"], o["a_idx_p50"]))
        for x in sorted(stalls, key=lambda z: -z["dur"])[:6]:
            pr("      t0 %6.1f dur %4.1f idx %3.0f ang %4.0f v %4.1f | rate %5.1f ref %5.1f r/ref %.2f | |T| %5.0f |I| %5.0f | tq50 %4.0f rAmp %4.1f" %
               (x["t0"], x["dur"], x["idx"], x["ang"], x["v"], x["rate"], x["ref"], x["rr"], x["lvl"], x["Ip50"], x["tq50"], x["rate_amp"]))
        ref = R["ref_deg"][r.i100]
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx < 80) & (np.abs(r.tq_raw) < 400)
        o["b_secs"] = m.sum() / FS
        if m.sum() > 50:
            o["b_rate"] = float(np.median(np.abs(r.wire[m]) / CPD))
            o["b_ref"] = float(np.median(ref[m]))
            o["b_frac"] = o["b_rate"] / o["b_ref"]
            o["b_T"] = float(np.median(np.abs(r.T_meas[m])))
            o["b_I"] = float(np.median(np.abs(R["I"][r.i100][m])))
        else:
            o["b_rate"] = o["b_ref"] = o["b_frac"] = o["b_T"] = o["b_I"] = np.nan
        pr("     (b) idx 40-80, |ang|>=30, hands-light (%.1f s): wheel rate p50 %.1f deg/s vs reference %.1f = %.0f %% | tap |T| p50 %.0f | chain |I| p50 %.0f"
           % (o["b_secs"], o["b_rate"], o["b_ref"], 100 * o["b_frac"], o["b_T"], o["b_I"]))
        for lo, hi, lab in ((20, 40, "k2040"), (40, 80, "k4080")):
            base = r.eng & (r.idx >= lo) & (r.idx < hi)
            dead = base & (np.abs(r.wire) < CPD) & (np.abs(r.ang) > 10)
            o[lab + "_cell"] = float(dead.sum() / max(base.sum(), 1))
            o[lab + "_secs"] = dead.sum() / FS
            for vlo, vhi, vlab in ((3, 8, "38"), (8, 12, "812")):
                bb = base & (r.vego >= vlo) & (r.vego < vhi) & (np.abs(r.tq_raw) < 400)
                dd = bb & (np.abs(r.wire) < CPD) & (np.abs(r.ang) > 10)
                o["%s_v%s" % (lab, vlab)] = float(dd.sum() / max(bb.sum(), 1)) if bb.sum() > 50 else np.nan
                o["%s_v%s_s" % (lab, vlab)] = dd.sum() / FS
            pr("     (c) idx %d-%d & |rate| < 1 deg/s & |ang| > 10: %.3f of the cell (%.1f s) | speed-matched hands-light: 3-8 m/s %.3f (%.1f s), 8-12 m/s %.3f (%.1f s)"
               % (lo, hi, o[lab + "_cell"], o[lab + "_secs"], o[lab + "_v38"], o[lab + "_v38_s"], o[lab + "_v812"], o[lab + "_v812_s"]))
        res[tag] = o
    return res


# ------------------------------------------------------------------------------------------------ 4. the integrator's share
def curve_mask(tag, r, ovs, only_over=False):
    """the steady window of each curve from section 2, on the Route's own time base."""
    m = np.zeros(len(r.tg), bool)
    for c in ovs[tag]["curves"]:
        if only_over and not (c["steady_os_pose"] > 0):
            continue
        a = int((c["t0"] + 1.5) * FS)
        b = int((c["t0"] + c["dur"]) * FS)
        if b > a and b < len(m):
            m[a:b] = True
    return m & r.eng


def xcorr_lag(x, y, m, maxlag=50):
    x = np.asarray(x, float).copy()
    y = np.asarray(y, float).copy()
    x[~m] = 0.0
    y[~m] = 0.0
    x = x - x[m].mean()
    y = y - y[m].mean()
    best, bl = -1e18, 0
    for L in range(-maxlag, maxlag + 1):
        c = float(np.dot(np.roll(x, -L), y))
        if c > best:
            best, bl = c, L
    return bl / FS


def section4(routes, sims, ovs):
    pr("\n" + "=" * 170)
    pr("SECTION 4 -- THE INTEGRATOR'S SHARE OF THE DELIVERED TORQUE (accumulator reconstructed offline from the wire)")
    pr("  arithmetic re-read from FUN_00028ea6 this session: I = acc >> 7 (0x29f18 sar 0x7 ; 0x29f1e add r9 ; 0x29f24 add r8),")
    pr("  acc += (deadband(E>>5, 0xC62E4=4) * 0xC63E6) >> 3, clamped to +-(0xC61BA<<10)>>3 = +-1310720, and ZEROED on the")
    pr("  not-enabled branch of the same function (decompile: the else-arm sets iVar34 = 0 before the store to gp-0x6dd0).")
    pr("  share = |I| / (|P| + |I| + |D|) at the summing junction. dT = T(Ki 50) - T(Ki 0) on the SAME measured rate =")
    pr("  the integrator's OPEN-LOOP contribution to the delivered surface (EVIDENCE for the decomposition; the closed-loop")
    pr("  counterfactual is BELIEF -- with Ki 0 the wheel would have moved differently and E would have followed).")
    pr("=" * 170)
    res = {}
    for tag in ROUTES:
        r = routes[tag]
        R = sims[tag]
        ki = KI_OF[tag]
        R0 = R if ki == 0 else sim(r, kp=KP_OF[tag], ki=0)
        i100 = r.i100
        I, P, D = R["I"][i100], R["P"][i100], R["D"][i100]
        T, T0 = R["T"][i100], R0["T"][i100]
        den = np.abs(P) + np.abs(I) + np.abs(D)
        share = np.where(den > 0, np.abs(I) / np.maximum(den, 1), 0.0)
        o = {}
        eng = r.eng
        cur = curve_mask(tag, r, ovs, only_over=False)
        ovr = curve_mask(tag, r, ovs, only_over=True)
        for lab, m in (("engaged", eng), ("curves (steady)", cur), ("OVERSTEERING curves", ovr)):
            if m.sum() < 100:
                pr("  %s %-22s: n/a (n %d)" % (tag, lab, m.sum()))
                continue
            x = dict(secs=m.sum() / FS, I=float(np.median(np.abs(I[m]))), P=float(np.median(np.abs(P[m]))), D=float(np.median(np.abs(D[m]))),
                     share=float(np.median(share[m])), share_p90=float(np.percentile(share[m], 90)),
                     T=float(np.median(np.abs(r.T_meas[m]))), dT=float(np.median(np.abs(T[m] - T0[m]))),
                     dT_rel=float(np.median(np.abs(T[m] - T0[m]) / np.maximum(np.abs(T0[m]), 1))),
                     rail=float(np.mean(np.abs(I[m]) >= I_CLAMP - 1)))
            o[lab] = x
            pr("  %s %-22s %6.0f s | |P| %5.0f |I| %5.0f |D| %5.0f | I share of the sum p50 %.3f (p90 %.3f) | tap |T| %5.0f | dT = T(Ki%d)-T(Ki0) p50 %5.0f (%3.0f %% of |T(Ki0)|) | I railed %.3f"
               % (tag, lab, x["secs"], x["P"], x["I"], x["D"], x["share"], x["share_p90"], x["T"], ki, x["dT"], 100 * x["dT_rel"], x["rail"]))
        # MODEL-FREE: the I term IMPLIED by the tap.  T = -lag(S)*GAIN/32768 and S = 254*(P+I+D)/256, so
        #   I_implied = -T_meas/(lagDC*GAIN/32768) * 256/254 - P - D.   On r35 (Ki 0 in the image) this returns ~0,
        # which is the control on the method: |I_imp| p50 233 counts against |P| 770.  EVIDENCE.
        I_imp = (-r.T_meas / T_PER_S) * 256.0 / 254.0 - P - D
        den_i = np.abs(P) + np.abs(I_imp) + np.abs(D)
        share_i = np.where(den_i > 0, np.abs(I_imp) / np.maximum(den_i, 1), 0.0)
        for lab, m in (("engaged", eng), ("curves (steady)", cur), ("OVERSTEERING curves", ovr),
                       ("idx 1-40", eng & (r.idx > 0) & (r.idx < 40)), ("idx 40-136", eng & (r.idx >= 40) & (r.idx < 136)),
                       ("|ang| >= 30", eng & (np.abs(r.ang) >= 30))):
            if m.sum() < 100:
                continue
            o["imp_" + lab] = dict(secs=m.sum() / FS, I=float(np.median(np.abs(I_imp[m]))), P=float(np.median(np.abs(P[m]))),
                                   share=float(np.median(share_i[m])), share_p90=float(np.percentile(share_i[m], 90)),
                                   corr=float(np.corrcoef(I_imp[m], I[m])[0, 1]) if np.std(I[m]) > 0 else np.nan,
                                   ratio=float(np.sum(I_imp[m] * I[m]) / np.sum(I[m] ** 2)) if np.sum(I[m] ** 2) > 0 else np.nan)
            x = o["imp_" + lab]
            pr("     TAP-IMPLIED I  %-20s %6.0f s | |I_imp| p50 %5.0f vs |P| %5.0f (I/P %.2f) | I share of |P|+|I|+|D| p50 %.3f (p90 %.3f) | corr with the reconstruction %+.3f, LS ratio %+.3f"
               % (lab, x["secs"], x["I"], x["P"], x["I"] / max(x["P"], 1), x["share"], x["share_p90"], x["corr"], x["ratio"]))
        E = R["E"][i100]
        m = eng & (np.abs(r.T_meas) > 40)
        o["push_after_sign_flip"] = float(np.mean(np.sign(r.T_meas[m]) != np.sign(-E[m]))) if m.sum() > 100 else np.nan
        db_m = eng & (np.abs(E) <= 32 * DEADBAND)
        o["dead_T"] = float(np.median(np.abs(r.T_meas[db_m]))) if db_m.sum() > 50 else np.nan
        o["dead_secs"] = db_m.sum() / FS
        mm = eng & (np.abs(r.ang) > 5)
        o["lag_T_E"] = xcorr_lag(r.T_meas, -E, mm)
        pr("     sign(T) != sign(-E) duty %.3f | frames with |E| inside the +-128-count deadband (%.1f s): tap |T| p50 %.0f | T-vs-(-E) peak cross-correlation lag %+.0f ms"
           % (o["push_after_sign_flip"], o["dead_secs"], o["dead_T"], o["lag_T_E"] * 1000))
        res[tag] = o
    return res


# ------------------------------------------------------------------------------------------------ 5. the outer loop
def section5(grids, routes, sims):
    pr("\n" + "=" * 170)
    pr("SECTION 5 -- THE OUTER LOOP (StarPilot's own p/i/f), the CURVE-EXIT overshoot, the POST-CURVE residual, and the 0.2-1 Hz straight hunt")
    pr("  If the EPS now delivers more per unit command, openpilot's own output should FALL on the same curves. If both are winding, it RISES.")
    pr("=" * 170)
    res = {}
    for tag in ROUTES:
        g = grids[tag]
        r = routes[tag]
        R = sims[tag]
        des = g["desiredLateralAccel"]
        pose = g["lat_torqued"]
        m_ = g["actualLateralAccel"]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
        curve = ok & (np.abs(des) > CO.DES_THR)
        runs = CO.merge_runs(curve, int(1.5 * FS), int(0.3 * FS))
        o = {}
        # outer-loop terms on the steady part of curves
        steady = np.zeros(len(des), bool)
        dirf = np.zeros(len(des))
        for a, b in runs:
            d = np.sign(np.median(des[a:b])) or 1.0
            dirf[a:b] = d
            steady[a + 150:b] = True
        s = steady
        o["curve_secs"] = s.sum() / FS
        for k in ("output", "p", "i", "f"):
            o["out_" + k] = med(np.abs(g[k][s]))
            o["sgn_" + k] = med(g[k][s] * dirf[s])
        o["cmd_abs"] = med(np.abs(g["cmd"][s]))
        o["err_pose"] = med((pose[s] - des[s]) * dirf[s])
        o["des"] = med(np.abs(des[s]))
        pr("  %s curves steady (%.0f s): |output| %.3f | f %+.3f p %+.3f i %+.3f (dir-projected) | |0xE4 cmd| p50 %.0f | |des| %.2f | err_pose %+.3f"
           % (tag, o["curve_secs"], o["out_output"], o["sgn_f"], o["sgn_p"], o["sgn_i"], o["cmd_abs"], o["des"], o["err_pose"]))
        # per-unit-command delivery: the EPS's tap torque per 0xE4 command count, hands-light engaged
        e = r.eng & (r.idx > 20) & (np.abs(r.tq_raw) < 400)
        o["T_per_idx"] = float(np.sum(np.abs(r.T_meas[e]) * r.idx[e]) / np.sum(r.idx[e] ** 2)) if e.sum() > 500 else np.nan
        o["T_p50_idx2080"] = float(np.median(np.abs(r.T_meas[r.eng & (r.idx >= 20) & (r.idx < 80) & (np.abs(r.tq_raw) < 400)])))
        pr("     delivery: tap |T| per demand index (idx > 20, hands-light) %.2f counts/idx | |T| p50 at idx 20-80 %.0f" % (o["T_per_idx"], o["T_p50_idx2080"]))
        # CURVE EXIT: the 3 s after a curve run ends, how far past the (now near-zero) request does the car go?
        ex_pose, ex_i, ex_T, ex_ang = [], [], [], []
        for a, b in runs:
            if b - a < 300 or b + 300 >= len(des):
                continue
            d = np.sign(np.median(des[a:b])) or 1.0
            w = slice(b, b + 150)                       # 0 - 1.5 s after the curve window closes
            ex_pose.append(med((pose[w] - des[w]) * d))
            ex_i.append(med(g["i"][w] * d))
            k0, k1 = int(b), min(int(b) + 150, len(r.tg) - 1)
            if k1 > k0:
                ex_T.append(float(np.median(R["I"][r.i100][k0:k1] * np.sign(np.median(r.T_meas[a:b] + 1e-9)))))
                ex_ang.append(float(np.median(np.abs(r.ang[k0:k1]))))
        o["exit_os_pose"] = med(ex_pose)
        o["exit_i"] = med(ex_i)
        o["exit_I_signed"] = med(ex_T)
        o["exit_n"] = len(ex_pose)
        pr("     curve EXIT (0-1.5 s after the curve window, n %d): os_pose %+.3f | outer i (dir) %+.3f | chain I in the curve's own direction %+.0f counts"
           % (o["exit_n"], o["exit_os_pose"], o["exit_i"], o["exit_I_signed"]))
        # POST-CURVE residual: after LONG one-sided curves (>= 4 s), the chain I decay on straights
        long_runs = [(a, b) for a, b in runs if b - a >= 400]
        res_I = []
        for a, b in long_runs:
            k = min(int(b) + 400, len(r.tg) - 1)
            if k <= b:
                continue
            seg = R["I"][r.i100][int(b):k]
            if len(seg) > 50:
                res_I.append(float(np.median(np.abs(seg))))
        o["post_I"] = med(res_I)
        o["post_n"] = len(res_I)
        pr("     POST-CURVE (long curves >= 4 s, n %d): chain |I| in the 4 s after %.0f counts (I clamp %d; 0.25 Hz corner => ~4 s memory)" % (o["post_n"], o["post_I"], I_CLAMP))
        # 0.2-1 Hz hunt on straights (the prereg cost-FAIL clause)
        st = r.eng & (np.abs(r.ang) < 5) & (r.vego >= 8)
        rs = runs_of(st, 1024)
        if sum(b - a for a, b in rs) > 1024:
            acc, n, f = None, 0, None
            for a, b in rs:
                x = r.wire[a:b] - r.wire[a:b].mean()
                f, P = signal.welch(x, fs=FS, nperseg=min(1024, b - a))
                if acc is None or len(P) != len(acc):
                    if acc is not None:
                        continue
                    acc = P * (b - a)
                else:
                    acc = acc + P * (b - a)
                n += b - a
            P = acc / n
            df = f[1] - f[0]
            band = lambda lo, hi: float(np.sqrt(P[(f >= lo) & (f < hi)].sum() * df * 2)) / CPD  # noqa: E731
            o["hunt_02_1"] = band(0.2, 1.0)
            o["hunt_1_2"] = band(1.0, 2.0)
            o["hunt_2_4"] = band(2.0, 4.0)
            o["hunt_secs"] = n / FS
            # the same bands on the ANGLE (the position the operator sees), and on the outer command
            aa = None
            for a, b in rs:
                x = r.ang[a:b] - r.ang[a:b].mean()
                f2, Pa = signal.welch(x, fs=FS, nperseg=min(1024, b - a))
                if aa is None or len(Pa) != len(aa):
                    if aa is not None:
                        continue
                    aa = Pa * (b - a)
                else:
                    aa = aa + Pa * (b - a)
            Pa = aa / n
            o["hunt_ang_02_1"] = float(np.sqrt(Pa[(f2 >= 0.2) & (f2 < 1.0)].sum() * df * 2))
            o["hunt_ang_1_2"] = float(np.sqrt(Pa[(f2 >= 1.0) & (f2 < 2.0)].sum() * df * 2))
            pr("     STRAIGHTS (|ang| < 5, v >= 8, %.0f s of >= 10.24 s runs): rate amp-equivalent deg/s 0.2-1 Hz %.3f | 1-2 Hz %.3f | 2-4 Hz %.3f || angle amp 0.2-1 Hz %.3f deg | 1-2 Hz %.3f deg"
               % (o["hunt_secs"], o["hunt_02_1"], o["hunt_1_2"], o["hunt_2_4"], o["hunt_ang_02_1"], o["hunt_ang_1_2"]))
        else:
            pr("     STRAIGHTS: no runs >= 10.24 s")
        res[tag] = o
    return res


def main():
    routes, grids, sims = {}, {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
        grids[tag] = B.grid(B.load(tag))
        sims[tag] = sim(routes[tag], kp=KP_OF[tag], ki=KI_OF[tag])
    tune = section0(grids)
    attr = section1(routes)
    ovs = section2()
    stall = section3(routes, sims)
    ish = section4(routes, sims, ovs)
    outer = section5(grids, routes, sims)
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    out = os.path.join(HERE, "_scratch", "oversteer_v283.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    json.dump(dict(tune=tune, attribution=attr, oversteer={t: dict(summary=ovs[t]["summary"], bins=ovs[t]["bins"], traj=ovs[t]["traj"]) for t in ovs},
                   stall=stall, integrator=ish, outer=outer),
              open(os.path.join(HERE, "oversteer_v283.json"), "w"), indent=1,
              default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else str(o)))
    print("wrote", out)


if __name__ == "__main__":
    main()
