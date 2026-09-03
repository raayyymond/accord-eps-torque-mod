# -*- coding: utf-8 -*-
"""studies/grind/grind_incident_r35.py -- the operator's "largely pronounced grinding incident" on r35 (V281 rev 3: Kp flat 248 on the
LKAS rate PID, else V280 rev 2), 23:48:21 local, segment 16.  Everything the standard rlog streams and the custom telemetry can say
about that one event, against the r34 "very very attenuated" creep seconds and the creep-line census.  Subagent grindr35, 2026-09-03.
Analysis only: builds nothing, sends nothing.

Inputs
  analysis-2020accord/_scratch/cache/v280/r35.npz, r34.npz     (0x18F, 0x14A angle, 0x1AB tap, 0xE4, carState.vEgo; raw CAN, v280_map_profiles.read_route)
  analysis-2020accord/_scratch/cache/v280/r35_b4.npz            (0x14A byte 4 = the cave probe byte, 100 Hz; extract_14a_b4.py)
  _scratch/r35_extra.npz                                        (gps anchor, IMU, carState extras, controlsState, liveTorqueParameters; grind_r35_extra_read.py, segs 13-18)
  the V281r3 and V280r2 images (cells read at run time via lowcmd_loopgain_v112_v278_v280.read_build)
Method notes
  * every CAN stream is put back on its nominal frame counter before any spectrum or phase (creep20_loop_id.dejitter): the logged receive
    times are batch-jittered 0-10 ms, half a cycle at 20 Hz.
  * the chain mirror is FUN_00028ea6 with the LIVE arms (TWIST-TAPER-LOOP 2026-09-03): setpoint taper 0xCB924 (flat to 2560 raw), post-PID
    multiplier m = (A*B)>>8 with A = 255 (grab byte < 10 assumed) and B = LERP(0xCBBC4, |tq|>>5) -- the fade from 512 raw; Kp from the image
    (flat 248 on V281r3), Kd 128, lag 992/507, fb 923/1560 two-sample sum clamped 46080, gain 5346, cap 3072; open loop on the measured rate.
  * "bar" = 0x18F signed driver torque x 1.024 (raw), "rate_x" = -wire/8 deg/s (the sign the PID sees), T = the CAN-427 tap at its own 50 Hz instants.
Run: python grind_incident_r35.py      (writes _scratch/grind_incident_r35.txt beside it)
"""
import datetime
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20            # noqa: E402  dejitter, load, Pool, L_fw, margins, bamp, bandpass, runs, up1k
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V            # noqa: E402
import _grind2_lib as G2                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K, FST = 100.0, 1000.0, 50.0
CACHE = C20.CACHE
TZ_H = -7                                 # PDT, as the r32/r34 anchors
DATE, HHMMSS, OP_SEG = "2026-09-02", "23:48:21", 16
HALF = 20.0
IMG281 = LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
IMG280 = LG.FW + LG.IMAGES["V280r2"]
# live arms (TWIST-TAPER-LOOP-2026-09-03, read from the V280r2 image there; re-read below from both images)
TAPER_LIVE_X, TAPER_LIVE_Y = np.array([32, 42, 80, 112.0]), np.array([255, 255, 255, 0.0])
OUT = []
R34_OP = [(336.0, 342.0), (419.0, 422.5), (437.0, 440.5)]   # creep20 / HIGHANGLE-r34 s8


def pr(s=""):
    print(s); OUT.append(s)


def lerp(x, y, u):
    return np.interp(np.asarray(u, float), x, y)


def read_cells(path):
    c = LG.read_build(path)
    b = open(path, "rb").read()
    c["fadeB"] = LG.lerp_rec(b, LG.u32(b, 0xCBBC4 + 4 * LG.SEL), 6)       # post-PID multiplier B (driver torque >> 5), live arm
    c["fadeA"] = LG.lerp_rec(b, LG.u32(b, 0xCBC34 + 4 * LG.SEL), 6)       # post-PID multiplier A (grab byte), live arm
    c["taperS"] = LG.lerp_rec(b, LG.u32(b, 0xCB924 + 4 * LG.SEL), 4)      # setpoint taper, same sign, live arm
    c["taperO"] = LG.lerp_rec(b, LG.u32(b, 0xCB8B4 + 4 * LG.SEL), 4)      # opposite sign
    return c


# ======================================================================================================================
# the chain mirror with the LIVE arms and a Kp table argument (FUN_00028ea6; line refs in creep20_loop_id / v280_map_profiles)
# ======================================================================================================================
def demand_live(cmd, bar, c):
    S = np.clip(-4.0 * np.round(cmd), -V.LIMIT, V.LIMIT)
    same = np.sign(S) == np.sign(bar)
    tx = np.abs(bar) // 32
    taper = np.where(same, lerp(c["taperS"][0], c["taperS"][1], tx), lerp(c["taperO"][0], c["taperO"][1], tx))
    prod = (taper * 255).astype(np.int64) & 0xFFFF          # speedF = 255 assumed (the kit's standing assumption)
    v = np.floor(prod * S / 65536.0); v = np.floor(v / 64.0); v = np.clip(v, -V.IDX_CLAMP, V.IDX_CLAMP)
    return np.abs(v), np.where(v < 0, -1.0, 1.0)


def simulate(g, a, b, c, kpY=None, kd=128, lag=(992, 507), fade=True, fb_single=False, rate_filter=None, freeze_cmd=False, cmd_mode="zoh"):
    seg = slice(max(0, a - 50), min(len(g["t"]), b + 10))
    n1 = (seg.stop - seg.start) * 10
    t1k = g["t"][seg.start] + np.arange(n1) * g["P18"] / 10
    wire = C20.up1k(g["wire"][seg])
    if rate_filter is not None:
        sos = signal.butter(4, rate_filter, btype="lowpass", fs=FS1K, output="sos"); wire = signal.sosfiltfilt(sos, wire)
    x = -wire
    s = 0.0; fb = np.empty(n1)
    for i in range(n1):
        s_new = np.floor((c["fb_a"] * s + c["fb_b"] * x[i]) / 1024.0)
        fb[i] = (2 * s_new) if fb_single else (s + s_new)
        s = s_new
    fb = np.clip(fb, -c["fb_clamp"], c["fb_clamp"])
    cmd = g["cmd"][seg]; bar = g["bar"][seg]
    if freeze_cmd:
        cmd = np.full_like(cmd, np.median(cmd))
    if cmd_mode == "zoh":
        cmd1k = np.repeat(cmd, 10); bar1k = np.repeat(bar, 10)
    else:
        cmd1k = np.interp(t1k, g["t"][seg], cmd); bar1k = np.interp(t1k, g["t"][seg], bar)
    idx, sgn = demand_live(cmd1k, bar1k, c); idx = np.round(idx)
    kpY = c["kp_Y"] if kpY is None else kpY
    sp = sgn * lerp(c["map_X"], c["map_Y"], idx)
    kp = lerp(c["kp_X"], kpY, idx)
    E = 32 * sp - fb
    P = np.clip(np.floor(E * kp / 256), -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    D = np.clip(np.floor(dE * kd / 8), -V.D_CLAMP, V.D_CLAMP)
    eng1k = np.repeat(g["eng"][seg], 10)
    if fade:
        B = lerp(c["fadeB"][0], c["fadeB"][1], np.abs(bar1k) // 32)
        m = ((255.0 * B).astype(np.int64) & 0xFFFF) >> 8
    else:
        m = np.full(n1, 254.0)

    def post(u):
        S = np.clip(np.floor(m * u / 256), -V.SUM_CLAMP, V.SUM_CLAMP); S[~eng1k] = 0.0
        st = signal.lfilter([lag[1] / 1024.0], [1.0, -lag[0] / 1024.0], S); y = (np.r_[0.0, st[:-1]] + st) / 32.0
        return np.clip(np.floor(-y * c["gain"] / 32768), -V.OUT_CAP, V.OUT_CAP)
    T = post(P + D); TP = post(P); TD = post(D)
    live = eng1k
    return dict(t1k=t1k, T=T, TP=TP, TD=TD, P=P, D=D, E=E, fb=fb, idx=idx, kp=kp, m=m, sp=sp, seg=seg,
                prail=float(np.mean(np.abs(E * kp / 256)[live] >= V.P_CLAMP)) if live.any() else np.nan,
                drail=float(np.mean(np.abs(dE * kd / 8)[live] > V.D_CLAMP)) if live.any() else np.nan,
                srail=float(np.mean(np.abs(m * (P + D) / 256)[live] >= V.SUM_CLAMP)) if live.any() else np.nan,
                tcap=float(np.mean(np.abs(T)[live] >= V.OUT_CAP)) if live.any() else np.nan,
                fbclp=float(np.mean(np.abs(fb)[live] >= c["fb_clamp"])) if live.any() else np.nan,
                fade_p50=float(np.median(m[live]) / 254.0) if live.any() else np.nan, fade_min=float(m[live].min() / 254.0) if live.any() else np.nan)


def eval_window(g, a, b, c, lo=18.0, hi=22.0, **kw):
    S = simulate(g, a, b, c, **kw)
    t0, t1 = g["t"][a], g["t"][b - 1]
    sel = (g["T_t"] >= t0) & (g["T_t"] <= t1)
    tt = g["T_t"][sel]; Tm = g["T"][sel]
    j = np.clip(np.round((tt - S["t1k"][0]) / (g["P18"] / 10)).astype(int), 0, len(S["T"]) - 1)
    Ts, TP, TD = S["T"][j], S["TP"][j], S["TD"][j]
    o = dict(n=len(tt), Tmeas=float(np.median(np.abs(Tm))), Tsim=float(np.median(np.abs(Ts))), corr=float(np.corrcoef(Tm, Ts)[0, 1]) if len(tt) > 4 else np.nan,
             amp_meas=C20.bamp(Tm, lo, hi, FST), amp_sim=C20.bamp(Ts, lo, hi, FST), amp_P=C20.bamp(TP, lo, hi, FST), amp_D=C20.bamp(TD, lo, hi, FST),
             prail=S["prail"], drail=S["drail"], srail=S["srail"], tcap=S["tcap"], fbclp=S["fbclp"], fade=S["fade_p50"], fademin=S["fade_min"],
             kp=float(np.median(S["kp"])), idx=float(np.median(S["idx"])))
    if len(tt) >= 64:
        bm, bs = C20.bandpass(Tm, lo, hi, FST), C20.bandpass(Ts, lo, hi, FST)
        o["corr_band"] = float(np.corrcoef(bm, bs)[0, 1])
        f, Sxy = signal.csd(bm, bs, fs=FST, nperseg=64); _, Sxx = signal.welch(bm, fs=FST, nperseg=64); _, Syy = signal.welch(bs, fs=FST, nperseg=64)
        j0 = int(np.argmin(np.abs(f - 0.5 * (lo + hi))))
        o["phase"] = float(np.degrees(np.angle(Sxy[j0]))); o["coh"] = float(abs(Sxy[j0]) ** 2 / (Sxx[j0] * Syy[j0]))
    else:
        o["corr_band"] = o["phase"] = o["coh"] = np.nan
    return o


def fmt_e(lab, o):
    return "    %-46s n %3d |T| meas/sim %4.0f/%4.0f corr %.2f | band amp meas %5.1f sim %5.1f (P %5.1f D %5.1f) corr_b %.2f ph %+4.0f coh %.2f | rails P %.2f D %.2f S %.2f cap %.2f fb %.2f | fade p50/min %.2f/%.2f | idx %3.0f Kp %3.0f" % (
        lab, o["n"], o["Tmeas"], o["Tsim"], o["corr"], o["amp_meas"], o["amp_sim"], o["amp_P"], o["amp_D"], o["corr_band"], o["phase"], o["coh"],
        o["prail"], o["drail"], o["srail"], o["tcap"], o["fbclp"], o["fade"], o["fademin"], o["idx"], o["kp"])


# ======================================================================================================================
def line_of(x, fs, lo=15.0, hi=26.0, nfft=4096):
    x = np.asarray(x, float)
    if len(x) < 32:
        return np.nan, np.nan, None, None
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    f0, prom = G2.locate(f, P, lo, hi, R=Rp)
    return f0, prom, f, P


def envelope(x, f0, fs, bw=2.0):
    y = C20.bandpass(x, max(f0 - bw, 1.0), f0 + bw, fs)
    return np.abs(signal.hilbert(y))


def growth_fit(t, env):
    """log-envelope slope on the rise (10 %->90 % of the peak before it) and on the decay (peak -> 10 % after)."""
    if len(env) < 20 or not np.isfinite(env).all():
        return np.nan, np.nan, np.nan, np.nan
    k = int(np.argmax(env)); pk = env[k]
    out = []
    for side in ("rise", "fall"):
        if side == "rise":
            lo_i = np.flatnonzero(env[:k] <= 0.1 * pk); hi_i = np.flatnonzero(env[:k] <= 0.9 * pk)
            a = lo_i[-1] if len(lo_i) else 0; b = hi_i[-1] if len(hi_i) else k
        else:
            lo_i = np.flatnonzero(env[k:] <= 0.9 * pk); hi_i = np.flatnonzero(env[k:] <= 0.1 * pk)
            a = k + (lo_i[0] if len(lo_i) else 0); b = k + (hi_i[0] if len(hi_i) else len(env) - k - 1)
        if b - a < 5:
            out += [np.nan, np.nan]; continue
        sl, ic, r, p, se = stats.linregress(t[a:b], np.log(np.maximum(env[a:b], 1e-9)))
        out += [sl, (t[b] - t[a])]
    return tuple(out)


def band(x, lo, hi, fs=FS):
    return C20.bamp(x, lo, hi, fs)


# ======================================================================================================================
def main():
    c281, c280 = read_cells(IMG281), read_cells(IMG280)
    pr("CELLS READ FROM THE IMAGES (slot %d): V281r3 map Y %s ; Kp X %s Y %s ; Kd %s ; lag %d/%d ; fb %d/%d clamp %d ; gain %d" % (
        LG.SEL, c281["map_Y"].astype(int).tolist(), c281["kp_X"].astype(int).tolist(), c281["kp_Y"].astype(int).tolist(), c281["kd_Y"].astype(int).tolist(),
        c281["lag_a"], c281["lag_b"], c281["fb_a"], c281["fb_b"], c281["fb_clamp"], c281["gain"]))
    pr("  V280r2 Kp Y %s ; live fade B 0xCBBC4 X %s Y %s (x32 raw) ; grab A 0xCBC34 X %s Y %s ; setpoint taper 0xCB924 X %s Y %s" % (
        c280["kp_Y"].astype(int).tolist(), c281["fadeB"][0].astype(int).tolist(), c281["fadeB"][1].astype(int).tolist(), c281["fadeA"][0].astype(int).tolist(),
        c281["fadeA"][1].astype(int).tolist(), c281["taperS"][0].astype(int).tolist(), c281["taperS"][1].astype(int).tolist()))
    same = all(np.array_equal(c281[k], c280[k]) for k in ("map_Y", "kd_Y", "fb_clamp") if not np.isscalar(c281[k])) and c281["fb_clamp"] == c280["fb_clamp"]
    pr("  V281r3 differs from V280r2 in the Kp table only (map/Kd/fb clamp identical: %s)" % same)

    # ---------------------------------------------------------------- load
    C20.MAPY["r35"] = c281["map_Y"]; C20.MAPY["r34"] = c280["map_Y"]; C20.BUILD["r35"] = "V281r3 Kp flat 248"
    G = {}
    for tag in ("r35", "r34"):
        print("loading %s ..." % tag, flush=True); G[tag] = C20.load(tag)
        g = G[tag]
        D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
        g["t0"] = float(D["t18"][0]); g["tr"] = g["t"] - g["t"][0]
        c = c281 if tag == "r35" else c280
        g["idx"], g["sgn"] = demand_live(np.round(g["cmd"]), g["bar"], c)      # live taper for idx (replaces C20.load's cliff arm)
        # the cave probe byte, on the 0x18F frame axis by nominal 0x14A time
        f_b4 = os.path.join(CACHE, tag + "_b4.npz")
        if os.path.exists(f_b4):
            B = np.load(f_b4); k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
            b4 = B["b4"].astype(int)
            for bit in (3, 4, 5, 6, 7):
                g["bit%d" % bit] = np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float))
                g["s%d" % bit] = 1.0 - 2.0 * np.round(g["bit%d" % bit])
        pr("  %s: %d frames, %.1f s, engaged %.1f s ; timing residual 0x18F p50/p90 %.1f/%.1f ms, 0x1AB %.1f/%.1f ms" % (
            tag, len(g["t"]), g["tr"][-1], g["eng"].sum() / FS, 1e3 * g["res"]["f18"][0], 1e3 * g["res"]["f18"][1], 1e3 * g["res"]["f1ab"][0], 1e3 * g["res"]["f1ab"][1]))
    g = G["r35"]
    X = dict(np.load(os.path.join(HERE, "_scratch", "r35_extra.npz")))

    # ---------------------------------------------------------------- 1. anchor and locate
    pr("\n" + "=" * 150); pr("1. WALL-CLOCK ANCHOR AND THE INCIDENT'S PLACE IN THE ROUTE"); pr("=" * 150)
    ok = X["unixms"] > 1.6e12
    off = float(np.median(X["unixms"][ok] * 1e-3 - X["tgps"][ok])); off_sd = float(np.std(X["unixms"][ok] * 1e-3 - X["tgps"][ok]))
    wall = X["wall"] * 1e-9 - X["tclk"]; off_clk = float(wall[wall > 1.6e9].max()) if (wall > 1.6e9).any() else np.nan
    t0 = g["t0"]
    start = datetime.datetime.fromtimestamp(t0 + off, datetime.timezone.utc)
    loc = lambda tr: (start + datetime.timedelta(hours=TZ_H, seconds=float(tr))).strftime("%H:%M:%S")   # noqa: E731
    pr("  unix = logMonoTime + %.3f s (GPS fix-valid n=%d, sd %.3f s; post-sync clocks offset %.3f, diff %.3f s) ; local = UTC%+d (PDT)" % (off, ok.sum(), off_sd, off_clk, off_clk - off, TZ_H))
    pr("  route t=0 (first 0x18F) = %s UTC = %s local %s ; route ends t=%.1f s = %s local" % (start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3], loc(0), DATE, g["tr"][-1], loc(g["tr"][-1])))
    local = datetime.datetime.strptime(DATE + " " + HHMMSS, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone(datetime.timedelta(hours=TZ_H)))
    t_inc = local.timestamp() - off - t0
    pr("  OPERATOR %s local -> route t = %.1f s = segment %d (operator said segment %d)" % (HHMMSS, t_inc, int(t_inc // 60), OP_SEG))
    if int(t_inc // 60) != OP_SEG:
        pr("  !! segment mismatch -- check the local-time offset; segment %d spans t %.0f-%.0f s = %s-%s local" % (OP_SEG, OP_SEG * 60, OP_SEG * 60 + 60, loc(OP_SEG * 60), loc(OP_SEG * 60 + 60)))
    # extras on the frame axis (route t)
    tx = lambda k: X[k] - t0    # noqa: E731
    ex = {}
    for k, tk in (("cstq", "tcs"), ("brake", "tcs"), ("gas", "tcs"), ("lblink", "tcs"), ("rblink", "tcs"), ("csang", "tcs"), ("curv", "tco"), ("dcurv", "tco"), ("tcact", "tco"), ("tcerr", "tco"), ("tcout", "tco"), ("tcsat", "tco")):
        if len(X[tk]):
            ex[k] = np.interp(g["tr"], tx(tk), np.nan_to_num(X[k]), left=np.nan, right=np.nan)
    if len(X["tlt"]):
        j = int(np.argmin(np.abs(tx("tlt") - t_inc)))
        pr("  liveTorqueParameters nearest the incident: latAccelFactor %.3f (raw %.3f) friction %.3f (raw %.3f) liveValid %d" % (X["laf"][j], X["lafraw"][j], X["fric"][j], X["fricraw"][j], X["ltvalid"][j]))
    w60 = (g["tr"] >= t_inc - 60) & (g["tr"] <= t_inc + 20)
    # events in the preceding minute
    pr("\n  THE PRECEDING MINUTE (t %.0f-%.0f s): engagement edges, stops, blinkers, angle/speed extremes" % (t_inc - 60, t_inc + 20))
    e = g["eng"][w60].astype(int); tt = g["tr"][w60]
    for k in np.flatnonzero(np.diff(e) != 0):
        pr("    t %.1f (%s): lateral %s" % (tt[k + 1], loc(tt[k + 1]), "ENGAGED" if e[k + 1] else "disengaged"))
    v = g["vego"][w60]
    for a, b in C20.runs(v < 0.3, 20):
        pr("    t %.1f-%.1f: stopped (v < 0.3)" % (tt[a], tt[b - 1]))
    for nm in ("lblink", "rblink", "brake", "gas"):
        if nm in ex:
            for a, b in C20.runs(np.nan_to_num(ex[nm][w60]) > 0.5, 10):
                pr("    t %.1f-%.1f: %s" % (tt[a], tt[b - 1], nm))
    pr("    v p10/p50/p90 %.1f/%.1f/%.1f m/s ; angle min/max %+.0f/%+.0f deg ; |tq| p50/p90 %.0f/%.0f raw ; engaged %.2f" % (
        *np.percentile(v, (10, 50, 90)), g["ang"][w60].min(), g["ang"][w60].max(), *np.percentile(np.abs(g["bar"][w60]), (50, 90)), g["eng"][w60].mean()))

    # per-second trace +-20 s
    pr("\n  1 s TRACE t %.0f..%.0f s (route t; local time) -- v | eng | ang | curv 1/m x1e3 | cmd | idx | |tq| | T p50 | bar 18-22 / 6-10 | rate 18-22 / 6-10 deg/s | tap 18-22 | bar line 12-30 | rails P/D/fb | fade | bit4 duty" % (t_inc - HALF, t_inc + HALF))
    S281 = None
    sec_rows = []
    for s in np.arange(np.floor(t_inc - HALF), np.ceil(t_inc + HALF), 1.0):
        m = (g["tr"] >= s) & (g["tr"] < s + 1.0)
        if m.sum() < 90:
            continue
        a, b = int(np.flatnonzero(m)[0]), int(np.flatnonzero(m)[-1] + 1)
        S = simulate(g, a, b, c281)
        live = slice((a - S["seg"].start) * 10, (b - S["seg"].start) * 10)
        f0, pm, _, _ = line_of(g["bar"][m], FS)
        selT = (g["T_t"] >= g["t"][a]) & (g["T_t"] < g["t"][b - 1])
        tap22 = C20.bamp(g["T"][selT], 18, 22, FST) if selT.sum() >= 32 else np.nan
        row = dict(t=s, v=g["vego"][m].mean(), eng=g["eng"][m].mean(), ang=np.median(g["ang"][m]), curv=np.nanmedian(ex["curv"][m]) if "curv" in ex else np.nan,
                   cmd=np.median(g["cmd"][m]), idx=np.median(g["idx"][m]), tq=np.median(np.abs(g["bar"][m])), T=np.median(g["T100"][m]),
                   b22=band(g["bar"][m], 18, 22), b610=band(g["bar"][m], 6, 10), r22=band(g["wire"][m], 18, 22) / V.CPD, r610=band(g["wire"][m], 6, 10) / V.CPD,
                   tap22=tap22, f0=f0, prom=pm, prail=np.mean(np.abs(S["E"][live] * S["kp"][live] / 256) >= V.P_CLAMP), drail=np.mean(np.abs(np.r_[0, np.diff(S["E"])][live] * 16) > V.D_CLAMP),
                   fbclp=np.mean(np.abs(S["fb"][live]) >= c281["fb_clamp"]), fade=np.median(S["m"][live]) / 254.0, bit4=g["bit4"][m].mean() if "bit4" in g else np.nan)
        sec_rows.append(row)
        pr("   %6.0f %s | %4.1f | %.2f | %+5.0f | %+6.2f | %+5.0f | %3.0f | %4.0f | %+5.0f | %4.0f / %4.0f | %5.2f / %5.2f | %4.0f | %4.1f x%5.1f | %.2f/%.2f/%.2f | %.2f | %.2f%s" % (
            row["t"], loc(row["t"]), row["v"], row["eng"], row["ang"], 1e3 * row["curv"], row["cmd"], row["idx"], row["tq"], row["T"], row["b22"], row["b610"], row["r22"], row["r610"], row["tap22"],
            row["f0"], row["prom"], row["prail"], row["drail"], row["fbclp"], row["fade"], row["bit4"], "  <== 23:48:21" if s <= t_inc < s + 1 else ""))

    # ---------------------------------------------------------------- 2. the incident core
    pr("\n" + "=" * 150); pr("2. THE INCIDENT: line, amplitude, duration, shape, rails, phase, command, IMU"); pr("=" * 150)
    R = {k: np.array([r[k] for r in sec_rows]) for k in sec_rows[0]}
    hot = (R["prom"] >= 8) & (R["b22"] >= 40) & (R["eng"] > 0.5)
    # the contiguous hot run nearest t_inc
    best = None
    for a, b in C20.runs(hot, 1):
        ta, tb = R["t"][a], R["t"][b - 1] + 1.0
        d = 0.0 if ta - 1 <= t_inc <= tb + 1 else min(abs(ta - t_inc), abs(tb - t_inc))
        if best is None or d < best[0]:
            best = (d, ta, tb)
    if best is None:
        pr("  NO line-present second in +-20 s (prominence >= 8 and bar 18-22 >= 40 raw). Falling back to the 6 s around the timestamp.")
        ta, tb = t_inc - 3, t_inc + 3
    else:
        ta, tb = best[1], best[2]
        pr("  incident core by the line detector: t %.1f-%.1f s (%s-%s local), %.1f s, %.1f s from the operator's timestamp" % (ta, tb, loc(ta), loc(tb), tb - ta, best[0]))
    core = (g["tr"] >= ta) & (g["tr"] < tb)
    a, b = int(np.flatnonzero(core)[0]), int(np.flatnonzero(core)[-1] + 1)
    ext = (g["tr"] >= ta - 4) & (g["tr"] < tb + 4)
    ae, be = int(np.flatnonzero(ext)[0]), int(np.flatnonzero(ext)[-1] + 1)
    # spectra, de-jittered
    f0b, pb, fb_, Pb = line_of(g["bar"][a:b], FS, 12, 30)
    f0r, prr, fr_, Pr = line_of(g["rate_x"][a:b], FS, 12, 30)
    selT = (g["T_t"] >= g["t"][a]) & (g["T_t"] < g["t"][b - 1])
    f0T, pT, fT_, PT = line_of(g["T"][selT], FST, 12, 24)
    pr("  LINE (Hann periodogram, nfft 4096, de-jittered): bar %.2f Hz x%.1f ; rate %.2f Hz x%.1f ; tap T (native 50 Hz) %.2f Hz x%.1f" % (f0b, pb, f0r, prr, f0T, pT))
    f0 = f0b
    # other lines: 5-12 Hz and the second harmonic
    for lo, hi, nm in ((5, 12, "5-12 Hz (the 7-9 Hz prediction)"), (30, 45, "30-45 Hz"), (f0 * 2 - 3, min(f0 * 2 + 3, 49), "2 f0")):
        fq, pq = G2.locate(fb_, Pb, lo, hi, R=G2.prom_spectrum(fb_, Pb, 6.0, 1.5)); fqr, pqr = G2.locate(fr_, Pr, lo, hi)
        pr("    %-32s bar %.2f Hz x%.1f  rate %.2f Hz x%.1f" % (nm, fq, pq, fqr, pqr))
    pr("  PSD ratio bar(f0)/bar(f0-5 Hz) %.1f ; bar band amps (raw): 6-10 %.0f  10-15 %.0f  15-18 %.0f  18-22 %.0f  22-26 %.0f  24-28 %.0f  30-45 %.0f" % (
        np.interp(f0, fb_, Pb) / max(np.interp(f0 - 5, fb_, Pb), 1e-9), *[band(g["bar"][a:b], lo, hi) for lo, hi in ((6, 10), (10, 15), (15, 18), (18, 22), (22, 26), (24, 28), (30, 45))]))
    pr("  rate band amps (deg/s): 6-10 %.2f 18-22 %.2f 24-28 %.2f ; tap T 18-22 %.0f 24-28 %.0f (native), |T| p50 %.0f, T mean %+.0f" % (
        band(g["wire"][a:b], 6, 10) / V.CPD, band(g["wire"][a:b], 18, 22) / V.CPD, band(g["wire"][a:b], 24, 28) / V.CPD,
        C20.bamp(g["T"][selT], 18, 22, FST), C20.bamp(g["T"][selT], 24, 28, FST), np.median(np.abs(g["T"][selT])), np.mean(g["T"][selT])))
    # coherence bar-rate, bar-T at f0
    npsq = 256 if b - a >= 512 else 128
    fc, Cq = signal.coherence(g["bar"][a:b], g["wire"][a:b], fs=FS, nperseg=npsq); j = int(np.argmin(np.abs(fc - f0)))
    fc2, Sqr = signal.csd(g["wire"][a:b], g["bar"][a:b], fs=FS, nperseg=npsq)
    selTc = (g["T_t"] >= g["t"][a]) & (g["T_t"] < g["t"][b - 1])
    Ti = np.interp(g["t"][a:b], g["T_t"], g["T"])
    fc3, CqT = signal.coherence(g["bar"][a:b], Ti, fs=FS, nperseg=npsq)
    pr("  coherence bar<->rate(wire) at %.1f Hz %.2f, phase(bar/wire) %+.0f deg (creep record: +114 hands-off) ; coherence bar<->tap %.2f  [nperseg %d]" % (f0, Cq[j], np.degrees(np.angle(Sqr[j])), CqT[j], npsq))
    ph_bar_wire = float(np.angle(Sqr[j]))
    # operating point in the core
    pr("  OPERATING POINT (core): v %.1f m/s (%.1f mph) ; |angle| p50 %.0f (range %+.0f..%+.0f) ; curvature p50 %.4f 1/m ; cmd p50 %+.0f (|cmd| p90 %.0f) ; idx p50/p90 %.0f/%.0f ; |tq| p50/p90 %.0f/%.0f raw ; T p50 %+.0f (|T| p90 %.0f) ; |rate| p50/p90 %.1f/%.1f deg/s ; engaged %.2f" % (
        g["vego"][a:b].mean(), g["vego"][a:b].mean() * 2.237, np.median(np.abs(g["ang"][a:b])), g["ang"][a:b].min(), g["ang"][a:b].max(), np.nanmedian(ex["curv"][a:b]) if "curv" in ex else np.nan,
        np.median(g["cmd"][a:b]), np.percentile(np.abs(g["cmd"][a:b]), 90), np.median(g["idx"][a:b]), np.percentile(g["idx"][a:b], 90), np.median(np.abs(g["bar"][a:b])), np.percentile(np.abs(g["bar"][a:b]), 90),
        np.median(g["T100"][a:b]), np.percentile(np.abs(g["T100"][a:b]), 90), np.median(np.abs(g["rate_x"][a:b])), np.percentile(np.abs(g["rate_x"][a:b]), 90), g["eng"][a:b].mean()))
    if "cstq" in ex:
        pr("    carState.steeringTorque p50 %.0f ; controlsState torque ctl: active %.2f, |error| p50 %.3f, |output| p50 %.3f, saturated %.2f" % (
            np.nanmedian(np.abs(ex["cstq"][a:b])), np.nanmean(ex["tcact"][a:b]), np.nanmedian(np.abs(ex["tcerr"][a:b])), np.nanmedian(np.abs(ex["tcout"][a:b])), np.nanmean(ex["tcsat"][a:b])))
    # envelope shape on the extended window
    tt = g["tr"][ae:be]
    envb = envelope(g["bar"][ae:be], f0, FS); envr = envelope(g["rate_x"][ae:be], f0, FS)
    selTe = (g["T_t"] >= g["t"][ae]) & (g["T_t"] < g["t"][be - 1]); ttT = g["T_t"][selTe] - g["t"][0]
    envT = envelope(g["T"][selTe], min(f0, 23.0), FST) if selTe.sum() >= 64 else None
    pr("\n  ENVELOPE at %.1f +-2 Hz (Hilbert of the band-passed signal), every 0.25 s from t %.1f: bar raw | rate deg/s | tap T | v | idx | |tq| | eng" % (f0, ta - 4))
    for s in np.arange(ta - 4, tb + 4, 0.25):
        m = (tt >= s) & (tt < s + 0.25)
        if not m.any():
            continue
        mT = (ttT >= s) & (ttT < s + 0.25)
        mg = (g["tr"] >= s) & (g["tr"] < s + 0.25)
        pr("    %7.2f | %5.0f | %5.2f | %5.0f | %4.1f | %3.0f | %4.0f | %.1f%s" % (s, envb[m].mean(), envr[m].mean(), envT[mT].mean() if envT is not None and mT.any() else np.nan,
                                                                          g["vego"][mg].mean(), np.median(g["idx"][mg]), np.median(np.abs(g["bar"][mg])), g["eng"][mg].mean(), "  <== 23:48:21" if s <= t_inc < s + 0.25 else ""))
    gr, tr_, gd, td = growth_fit(tt, envb)
    pr("  bar envelope peak %.0f raw at t %.2f ; log-slope on the rise %+.2f /s over %.2f s (e-fold %.2f s = %.1f cycles) ; on the decay %+.2f /s over %.2f s" % (
        envb.max(), tt[np.argmax(envb)], gr, tr_, 1 / gr if gr and gr > 0 else np.nan, f0 / gr if gr and gr > 0 else np.nan, gd, td))
    grr, trr, gdr, tdr = growth_fit(tt, envr)
    pr("  rate envelope peak %.2f deg/s at t %.2f ; rise %+.2f /s over %.2f s ; decay %+.2f /s over %.2f s" % (envr.max(), tt[np.argmax(envr)], grr, trr, gdr, tdr))
    # plateau vs growth: fraction of the core within 50 % of the peak
    pr("  fraction of the core with bar envelope >= 0.5 peak %.2f ; >= 0.25 peak %.2f ; envelope sd/mean in the core %.2f (a limit cycle at a rail sits flat; a driven resonance wanders)" % (
        np.mean(envb[(tt >= ta) & (tt < tb)] >= 0.5 * envb.max()), np.mean(envb[(tt >= ta) & (tt < tb)] >= 0.25 * envb.max()), envb[(tt >= ta) & (tt < tb)].std() / envb[(tt >= ta) & (tt < tb)].mean()))

    # fine envelope: 50 ms, with the raw wheel rate and its 6-10 Hz component -- do the 20 Hz bursts ride the 7 Hz cycle?
    r610 = C20.bandpass(g["rate_x"][ae:be], 6, 10, FS); env610 = np.abs(signal.hilbert(r610))
    pr("\n  FINE ENVELOPE (50 ms) t %.1f-%.1f: t | bar env @f0 | rate env @f0 | rate_x raw p50 deg/s | rate 6-10 Hz component | |tq| | idx | T100" % (ta - 1, tb + 1))
    for s_ in np.arange(ta - 1, tb + 1, 0.05):
        m = (tt >= s_) & (tt < s_ + 0.05)
        if not m.any():
            continue
        mg = (g["tr"] >= s_) & (g["tr"] < s_ + 0.05)
        pr("    %8.2f | %5.0f | %5.2f | %+6.1f | %+6.1f | %4.0f | %3.0f | %+5.0f" % (s_, envb[m].mean(), envr[m].mean(), np.median(g["rate_x"][mg]), r610[m].mean(), np.median(np.abs(g["bar"][mg])), np.median(g["idx"][mg]), np.median(g["T100"][mg])))
    cc = np.corrcoef(envb[(tt >= ta) & (tt < tb)], env610[(tt >= ta) & (tt < tb)])[0, 1]
    cr = np.corrcoef(envb[(tt >= ta) & (tt < tb)], np.abs(g["rate_x"][a:b]))[0, 1]
    pr("  corr(20 Hz bar envelope, 6-10 Hz rate envelope) in the core %+.2f ; corr(20 Hz bar envelope, |rate_x|) %+.2f" % (cc, cr))
    # the 7 Hz companion
    lo7, hi7 = 6.0, 8.5
    pr("\n  THE 7 Hz COMPANION in the core: bar %.0f raw, rate %.2f deg/s, tap %.0f (native) at 6-8.5 Hz ; tap ripple/level %.2f ; bar 7-Hz line %.2f Hz x%.1f ; bar/rate at the 7 Hz line: |H| %.1f ph %+.0f coh %.2f" % (
        band(g["bar"][a:b], lo7, hi7), band(g["wire"][a:b], lo7, hi7) / V.CPD, C20.bamp(g["T"][selT], lo7, hi7, FST), C20.bamp(g["T"][selT], lo7, hi7, FST) / max(np.median(np.abs(g["T"][selT])), 1),
        *G2.locate(fb_, Pb, 5, 12, R=G2.prom_spectrum(fb_, Pb, 6.0, 1.5)), abs(Sqr[int(np.argmin(np.abs(fc - 7.4)))]) / np.real(signal.welch(g["wire"][a:b], fs=FS, nperseg=npsq)[1][int(np.argmin(np.abs(fc - 7.4)))]),
        np.degrees(np.angle(Sqr[int(np.argmin(np.abs(fc - 7.4)))])), Cq[int(np.argmin(np.abs(fc - 7.4)))]))
    for lab, kw in (("as built (Kp 248)", {}), ("Kp = V280r2 table", dict(kpY=c280["kp_Y"])), ("Kd 0", dict(kd=0))):
        pr(fmt_e("    7 Hz band mirror " + lab, eval_window(g, a, b, c281, lo7, hi7, **kw)))
    # r34's loudest attenuated window, same envelope fit
    g34_ = G["r34"]; a34 = int(np.searchsorted(g34_["tr"], 334.0)); b34 = int(np.searchsorted(g34_["tr"], 344.0))
    e34 = envelope(g34_["bar"][a34:b34], 20.1, FS); t34 = g34_["tr"][a34:b34]
    gr34, tr34, gd34, td34 = growth_fit(t34, e34)
    pr("\n  r34 t 334-344 (the operator's loudest attenuated window) same envelope fit: peak %.0f raw at t %.2f ; rise %+.2f /s over %.2f s ; decay %+.2f /s over %.2f s ; env >= 0.5 peak fraction %.2f ; sd/mean %.2f" % (
        e34.max(), t34[np.argmax(e34)], gr34, tr34, gd34, td34, np.mean(e34 >= 0.5 * e34.max()), e34.std() / e34.mean()))
    pr("    r34 t 336-342 envelope every 0.5 s: " + " ".join("%.0f" % e34[(t34 >= s_) & (t34 < s_ + 0.5)].mean() for s_ in np.arange(336, 342, 0.5)))

    # rails over the core (V281 live chain, open loop on the measured rate)
    S = simulate(g, a, b, c281); live = slice((a - S["seg"].start) * 10, (b - S["seg"].start) * 10)
    E, kp, fbv, m_ = S["E"][live], S["kp"][live], S["fb"][live], S["m"][live]
    dE = np.r_[0, np.diff(S["E"])][live]
    pr("\n  RAILS in the core (1 kHz mirror, V281r3 cells, live fade): P rail (|E*Kp>>8| >= 15360) %.3f ; D rail (|dE*16| > 10240) %.3f ; sum rail %.3f ; T cap (3072) %.3f ; fb clamp (46080) %.3f" % (
        np.mean(np.abs(E * kp / 256) >= V.P_CLAMP), np.mean(np.abs(dE * 16) > V.D_CLAMP), S["srail"], S["tcap"], np.mean(np.abs(fbv) >= c281["fb_clamp"])))
    pr("    |P| p50/p90 %.0f/%.0f of 15360 ; |D| p50/p90 %.0f/%.0f of 10240 ; |fb| p50/p90 %.0f/%.0f of 46080 ; |E| p50 %.0f (P rails at |E| %.0f at Kp 248) ; fade m/254 p50/min %.2f/%.2f ; setpoint taper (|tq| >= 2560) %.3f ; old cliff (|tq| >= 2240, dead arm) %.3f ; tap saturation (|T| >= 2472) %.3f" % (
        *np.percentile(np.abs(S["P"][live]), (50, 90)), *np.percentile(np.abs(S["D"][live]), (50, 90)), *np.percentile(np.abs(fbv), (50, 90)), np.median(np.abs(E)), 15360 * 256 / 248,
        np.median(m_) / 254, m_.min() / 254, np.mean(np.abs(g["bar"][a:b]) >= 2560), np.mean(np.abs(g["bar"][a:b]) >= 2240), np.mean(np.abs(g["T"][selT]) >= V.SAT_THR)))
    pr("    delivered-torque content at f0 vs level: tap ripple / |T| p50 = %.2f ; D-term share of the mirror's f0 ripple below (section 4)" % (C20.bamp(g["T"][selT], f0 - 2, f0 + 2, FST) / max(np.median(np.abs(g["T"][selT])), 1)))

    # the cave bits: duties and bit-4 phase re rate at f0 (r24_sign_on_the_wire method; wire sign, cos > 0 = DAMP in that convention)
    if "bit4" in g:
        pr("\n  CAVE PROBE BYTE 0x14A b4 in the core: duties bit7 sign(gp-0x6b4c)<0 %.2f | bit6 %.2f | bit5 |6ae2|>=|6b26| %.2f | bit4 sign(r24)<0 %.2f | bit3 sign(gp-0x3680)<0 %.2f" % tuple(
            g["bit%d" % k][a:b].mean() for k in (7, 6, 5, 4, 3)))
        for lab, aa, bb in (("core", a, b), ("core +-4 s", ae, be)):
            n = bb - aa
            nps = 128 if n >= 256 else 64
            P = C20.Pool(FS, nps)
            P.add({"rate": g["wire"][aa:bb], "bar": g["bar"][aa:bb], "T": g["T100"][aa:bb], "sT": np.sign(g["T100"][aa:bb]), "sR": g["s4"][aa:bb], "sB": g["s7"][aa:bb], "s3": g["s3"][aa:bb], "s5": g["s5"][aa:bb]})
            if P.n == 0:
                continue
            f = P.f; j = int(np.argmin(np.abs(f - f0)))
            HT, HsT, HsB, HsR, Hs3 = P.tf("rate", "T"), P.tf("rate", "sT"), P.tf("rate", "sB"), P.tf("rate", "sR"), P.tf("rate", "s3")
            ctrl = np.degrees(np.angle(HsB[j] * np.conj(HT[j])))
            pr("    %-12s nps %d (%d w) at %.1f Hz: ph(T/rate) %+.0f coh %.2f | ph(sign T/rate) %+.0f | bit7/rate %+.0f coh %.2f | CONTROL bit7 - T %+.0f (must be ~0) | *** bit4 (r24)/rate %+.0f coh %.2f cos %+.2f -> %s *** | bit3/rate %+.0f coh %.2f" % (
                lab, nps, P.n, f[j], np.degrees(np.angle(HT[j])), P.coh("rate", "T")[j], np.degrees(np.angle(HsT[j])), np.degrees(np.angle(HsB[j])), P.coh("rate", "sB")[j], ctrl,
                np.degrees(np.angle(HsR[j])), P.coh("rate", "sR")[j], np.cos(np.angle(HsR[j])), "DAMP" if np.cos(np.angle(HsR[j])) > 0.2 else ("PUMP" if np.cos(np.angle(HsR[j])) < -0.2 else "~neut"),
                np.degrees(np.angle(Hs3[j])), P.coh("rate", "s3")[j]))
            pr("      bit4 re rate across 15-26 Hz: " + "  ".join("%.1f:%+.0f/%.2f" % (f[k], np.degrees(np.angle(HsR[k])), P.coh("rate", "sR")[k]) for k in range(len(f)) if 15 <= f[k] <= 26))
        D4 = lambda f_, N=4.0: 0.5 * (1.0 - np.exp(-2j * np.pi * f_ * N * 1e-3))   # noqa: E731
        pred = np.degrees(np.angle(-np.exp(1j * ph_bar_wire) * D4(f0)))
        pr("    CLOSED FORM for r24 re wire at f0 from the measured bar/wire phase (%+.0f): ang(bar/wire) + ang(D4) + 180 = %+.0f deg (the creep record measured bit4 +2..-16 = DAMP with bar/wire +114)" % (np.degrees(ph_bar_wire), pred))
    # command content
    fq, pq, fc_, Pc = line_of(g["cmd"][a:b], FS, f0 - 3, f0 + 3)
    dc = np.abs(np.diff(g["cmd"][a:b]))
    if b - a >= 256:
        fc, Ccb = signal.coherence(g["cmd"][a:b], g["bar"][a:b], fs=FS, nperseg=256); j = int(np.argmin(np.abs(fc - f0)))
    pr("\n  COMMAND 0xE4 in the core: p50 %+.0f, range %+.0f..%+.0f, |dcmd| p50/p90 %.0f/%.0f, P(changes) %.2f ; line near f0 %.2f Hz x%.1f ; coh cmd<->bar at f0 %.2f ; cmd 18-22 amp %.1f" % (
        np.median(g["cmd"][a:b]), g["cmd"][a:b].min(), g["cmd"][a:b].max(), *np.percentile(dc, (50, 90)), np.mean(dc > 0), fq, pq, Ccb[j] if b - a >= 256 else np.nan, band(g["cmd"][a:b], 18, 22)))
    # IMU
    if len(X["gtm"]):
        tg = X["gtm"] - t0; tacc = X["atm"] - t0
        base = (g["tr"] >= t_inc - 60) & (g["tr"] < ta - 4) & g["eng"]
        pr("\n  IMU (gyro rad/s, accel m/s2; uniform 100 Hz by interpolation on logMonoTime; gyro sample rate %.0f Hz): band amps at %.0f-%.0f (line) vs 24-28 (control) vs 6-10" % (1 / np.median(np.diff(X["gtm"])), f0 - 2, f0 + 2))
        for lab, msk in (("core", core), ("baseline engaged, the minute before", base)):
            if msk.sum() < 200:
                continue
            aa, bb = int(np.flatnonzero(msk)[0]), int(np.flatnonzero(msk)[-1] + 1)
            tgrid = g["tr"][aa:bb]
            row = []
            for nm, tsrc, src in (("gx", tg, X["gx"]), ("gy", tg, X["gy"]), ("gz", tg, X["gz"]), ("ax", tacc, X["ax"]), ("ay", tacc, X["ay"]), ("az", tacc, X["az"])):
                y = np.interp(tgrid, tsrc, src)
                row.append("%s %.4f/%.4f/%.4f" % (nm, band(y, f0 - 2, f0 + 2), band(y, 24, 28), band(y, 6, 10)))
            pr("    %-36s %s" % (lab, " | ".join(row)))
        aa, bb = a, b
        for nm, tsrc, src in (("gx", tg, X["gx"]), ("gz", tg, X["gz"]), ("ay", tacc, X["ay"])):
            y = np.interp(g["tr"][aa:bb], tsrc, src); fq2, pq2, _, _ = line_of(y, FS, 12, 30)
            if bb - aa >= 256:
                fc, Cc = signal.coherence(g["bar"][aa:bb], y, fs=FS, nperseg=256); j = int(np.argmin(np.abs(fc - f0)))
                pr("    %s: most prominent 12-30 Hz line %.1f Hz x%.1f ; coherence with the bar at f0 %.2f" % (nm, fq2, pq2, Cc[j]))

    # ---------------------------------------------------------------- 3. against r34 and the census
    pr("\n" + "=" * 150); pr("3. WHAT IS DIFFERENT: the incident vs the r34 attenuated seconds vs every creep window (r34 = V280r2 Kp table, r35 = V281r3 Kp flat 248)"); pr("=" * 150)
    W, STEP = 200, 50
    rows = []
    for tag, gg in G.items():
        msk = gg["eng"] & (gg["vego"] < 6.0)
        for aa, bb in C20.runs(msk, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw, _, _ = line_of(gg["bar"][s:e], FS)
                f0rw, promrw, _, _ = line_of(gg["rate_x"][s:e], FS)
                fq, pq_, _, _ = line_of(gg["bar"][s:e], FS, 5, 12)
                Tw = gg["T100"][s:e]
                rows.append(dict(tag=tag, t=gg["tr"][s], f0=f0w, prom=promw, f0r=f0rw, amp=band(gg["bar"][s:e], 18, 22), amp610=band(gg["bar"][s:e], 6, 10), f610=fq, p610=pq_,
                                 ramp=band(gg["wire"][s:e], 18, 22) / V.CPD, rate=float(np.mean(np.abs(gg["wire"][s:e])) / V.CPD), v=float(gg["vego"][s:e].mean()), ang=float(np.median(np.abs(gg["ang"][s:e]))),
                                 T=float(np.median(np.abs(Tw))), idx=float(np.median(gg["idx"][s:e])), tq=float(np.median(np.abs(gg["bar"][s:e]))), cmd=float(np.median(np.abs(gg["cmd"][s:e]))),
                                 creep=bool(1.0 <= gg["vego"][s:e].mean() < 3.0), inc=bool(tag == "r35" and ta - 2 <= gg["tr"][s] <= tb)))
    Rw = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (Rw["prom"] >= 8) & (Rw["amp"] >= 40)
    pr("  CENSUS: 2 s windows step 0.5 s, engaged, v < 6 m/s; line = most prominent 15-26 Hz (prominence >= 8 & bar 18-22 >= 40 raw)")
    pr("  %-5s %-20s %5s %5s %5s | %-24s | %-22s | %s" % ("route", "build", "n", "pres", "%", "f mean sd p10/p90", "amp p50/p90/max raw", "by idx bin: present % (amp p50, f) at 0 / 1-20 / 20-60 / >60"))
    for tag in ("r34", "r35"):
        sel = Rw["tag"] == tag; ps = sel & pres
        bins = []
        for lab, bsel in (("0", sel & (Rw["idx"] == 0)), ("1-20", sel & (Rw["idx"] > 0) & (Rw["idx"] <= 20)), ("20-60", sel & (Rw["idx"] > 20) & (Rw["idx"] <= 60)), (">60", sel & (Rw["idx"] > 60))):
            bins.append("%s: %.0f %% (%.0f, %.1f, n %d)" % (lab, 100 * pres[bsel].mean() if bsel.any() else np.nan, np.median(Rw["amp"][bsel]) if bsel.any() else np.nan,
                                                          Rw["f0"][bsel & pres].mean() if (bsel & pres).any() else np.nan, bsel.sum()))
        pr("  %-5s %-20s %5d %5d %5.0f | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f | %s" % (tag, C20.BUILD[tag], sel.sum(), ps.sum(), 100 * pres[sel].mean(), Rw["f0"][ps].mean(), Rw["f0"][ps].std(),
                                                                                       *np.percentile(Rw["f0"][ps], (10, 90)), *np.percentile(Rw["amp"][sel], (50, 90)), Rw["amp"][sel].max(), " ; ".join(bins)))
        cw = sel & Rw["creep"]
        if cw.sum() > 10:
            pr("        creep (1-3 m/s) windows n %d present %.0f %% amp p50 %.0f ; Spearman amp vs idx %+.2f, vs |T| %+.2f, vs |rate| %+.2f, vs v %+.2f ; f vs idx rho %+.2f (p %.3f)" % (
                cw.sum(), 100 * pres[cw].mean(), np.median(Rw["amp"][cw]), stats.spearmanr(Rw["idx"][cw], Rw["amp"][cw])[0], stats.spearmanr(Rw["T"][cw], Rw["amp"][cw])[0],
                stats.spearmanr(Rw["rate"][cw], Rw["amp"][cw])[0], stats.spearmanr(Rw["v"][cw], Rw["amp"][cw])[0], *stats.spearmanr(Rw["idx"][ps], Rw["f0"][ps])))
        # 5-12 Hz line census too
        pr("        5-12 Hz line present (prom >= 8 & bar 6-10 >= 40) in %.0f %% of windows (f mean %.1f Hz), bar 6-10 amp p50/p90 %.0f/%.0f" % (
            100 * np.mean((Rw["p610"][sel] >= 8) & (Rw["amp610"][sel] >= 40)), Rw["f610"][sel & (Rw["p610"] >= 8) & (Rw["amp610"] >= 40)].mean() if ((Rw["p610"] >= 8) & (Rw["amp610"] >= 40) & sel).any() else np.nan,
            *np.percentile(Rw["amp610"][sel], (50, 90))))
    # where the incident sits
    inc = Rw["inc"]
    pr("  the incident's 2 s windows (n %d): amp p50/max %.0f/%.0f raw = route pct %.0f/%.0f of r35's engaged v<6 windows, %.0f/%.0f of r34's ; f %.2f Hz" % (
        inc.sum(), np.median(Rw["amp"][inc]), Rw["amp"][inc].max(), 100 * np.mean(Rw["amp"][Rw["tag"] == "r35"] < np.median(Rw["amp"][inc])), 100 * np.mean(Rw["amp"][Rw["tag"] == "r35"] < Rw["amp"][inc].max()),
        100 * np.mean(Rw["amp"][Rw["tag"] == "r34"] < np.median(Rw["amp"][inc])), 100 * np.mean(Rw["amp"][Rw["tag"] == "r34"] < Rw["amp"][inc].max()), Rw["f0"][inc & pres].mean() if (inc & pres).any() else np.nan))
    top = np.argsort(Rw["amp"])[::-1][:12]
    pr("  top-12 windows by bar 18-22 amp, both routes: " + " ".join("%s@t%.0f(%.0f,%.1fHz,idx%.0f,v%.1f)" % (Rw["tag"][k], Rw["t"][k], Rw["amp"][k], Rw["f0"][k], Rw["idx"][k], Rw["v"][k]) for k in top))
    for tag in ("r34", "r35"):
        sel = Rw["tag"] == tag
        pr("  %s: Spearman(bar 18-22 amp, bar 6-10 amp) over engaged v<6 windows %+.2f (n %d) ; over idx>60 windows %+.2f (n %d)" % (
            tag, stats.spearmanr(Rw["amp"][sel], Rw["amp610"][sel])[0], sel.sum(), stats.spearmanr(Rw["amp"][sel & (Rw["idx"] > 60)], Rw["amp610"][sel & (Rw["idx"] > 60)])[0], (sel & (Rw["idx"] > 60)).sum()))
    sel = (Rw["tag"] == "r35") & (Rw["idx"] > 60) & (Rw["v"] < 6)
    pr("  r35 windows at idx > 60, v < 6 (the incident's class), sorted by bar 18-22 amp: t(amp, f, 6-10 amp, |rate|, |tq|, v, idx): " + " ".join(
        "%.0f(%.0f,%.1f,%.0f,%.0f,%.0f,%.1f,%.0f)" % (Rw["t"][k], Rw["amp"][k], Rw["f0"][k], Rw["amp610"][k], Rw["rate"][k], Rw["tq"][k], Rw["v"][k], Rw["idx"][k]) for k in np.flatnonzero(sel)[np.argsort(Rw["amp"][sel])[::-1][:16]]))
    sel = (Rw["tag"] == "r34") & (Rw["idx"] > 60) & (Rw["v"] < 6)
    pr("  r34 same class, top 12: " + " ".join(
        "%.0f(%.0f,%.1f,%.0f,%.0f,%.0f,%.1f,%.0f)" % (Rw["t"][k], Rw["amp"][k], Rw["f0"][k], Rw["amp610"][k], Rw["rate"][k], Rw["tq"][k], Rw["v"][k], Rw["idx"][k]) for k in np.flatnonzero(sel)[np.argsort(Rw["amp"][sel])[::-1][:12]]))
    # frequency vs Kp: r34 vs r35 present windows matched on idx
    pr("  f_line by idx bin, present windows -- V280r2 (r34) vs V281r3 (r35): " + " ; ".join("idx %s: %.2f (n %d) vs %.2f (n %d)" % (
        lab, Rw["f0"][pres & (Rw["tag"] == "r34") & bs].mean() if (pres & (Rw["tag"] == "r34") & bs).any() else np.nan, (pres & (Rw["tag"] == "r34") & bs).sum(),
        Rw["f0"][pres & (Rw["tag"] == "r35") & bs].mean() if (pres & (Rw["tag"] == "r35") & bs).any() else np.nan, (pres & (Rw["tag"] == "r35") & bs).sum())
        for lab, bs in (("0-20", Rw["idx"] <= 20), ("20-60", (Rw["idx"] > 20) & (Rw["idx"] <= 60)), ("60-120", (Rw["idx"] > 60) & (Rw["idx"] <= 120)), (">120", Rw["idx"] > 120))))
    pr("  amp by idx bin, all windows -- r34 vs r35 p50: " + " ; ".join("idx %s: %.0f vs %.0f" % (
        lab, np.median(Rw["amp"][(Rw["tag"] == "r34") & bs]) if ((Rw["tag"] == "r34") & bs).any() else np.nan, np.median(Rw["amp"][(Rw["tag"] == "r35") & bs]) if ((Rw["tag"] == "r35") & bs).any() else np.nan)
        for lab, bs in (("0-20", Rw["idx"] <= 20), ("20-60", (Rw["idx"] > 20) & (Rw["idx"] <= 60)), ("60-120", (Rw["idx"] > 60) & (Rw["idx"] <= 120)), (">120", Rw["idx"] > 120))))
    # operating-point table
    pr("\n  OPERATING POINT: medians -- v | idx | |ang| | |T| | |tq| | |rate| | bar 18-22 | rate 18-22 | f")
    def oprow(lab, sel):
        if not sel.any():
            return
        pr("    %-40s n %4d | %4.1f | %4.0f | %4.0f | %4.0f | %5.0f | %5.1f | %4.0f | %5.2f | %5.2f" % (
            lab, sel.sum(), np.median(Rw["v"][sel]), np.median(Rw["idx"][sel]), np.median(Rw["ang"][sel]), np.median(Rw["T"][sel]), np.median(Rw["tq"][sel]), np.median(Rw["rate"][sel]),
            np.median(Rw["amp"][sel]), np.median(Rw["ramp"][sel]), np.nanmean(Rw["f0"][sel & pres]) if (sel & pres).any() else np.nan))
    oprow("r35 INCIDENT windows", inc)
    for tag in ("r35", "r34"):
        sel = Rw["tag"] == tag
        oprow("%s creep, line present" % tag, sel & Rw["creep"] & pres); oprow("%s creep, line absent" % tag, sel & Rw["creep"] & ~pres)
        oprow("%s v<6 engaged, line present" % tag, sel & pres & ~inc); oprow("%s v<6 engaged, line absent" % tag, sel & ~pres & ~inc)
        oprow("%s v<6 engaged, amp >= 150" % tag, sel & (Rw["amp"] >= 150) & ~inc)
    g34 = G["r34"]
    for (u0, u1) in R34_OP:
        aa = int(np.searchsorted(g34["tr"], u0)); bb = int(np.searchsorted(g34["tr"], u1))
        f0w, pw, _, _ = line_of(g34["bar"][aa:bb], FS)
        selT34 = (g34["T_t"] >= g34["t"][aa]) & (g34["T_t"] < g34["t"][bb - 1])
        pr("    %-40s        | %4.1f | %4.0f | %4.0f | %4.0f | %5.0f | %5.1f | %4.0f | %5.2f | %5.2f  (tap 18-22 %.0f)" % (
            "r34 operator t %.0f-%.0f (attenuated)" % (u0, u1), g34["vego"][aa:bb].mean(), np.median(g34["idx"][aa:bb]), np.median(np.abs(g34["ang"][aa:bb])), np.median(np.abs(g34["T100"][aa:bb])),
            np.median(np.abs(g34["bar"][aa:bb])), np.mean(np.abs(g34["rate_x"][aa:bb])), band(g34["bar"][aa:bb], 18, 22), band(g34["wire"][aa:bb], 18, 22) / V.CPD, f0w, C20.bamp(g34["T"][selT34], 18, 22, FST)))
    pr("    %-40s        | %4.1f | %4.0f | %4.0f | %4.0f | %5.0f | %5.1f | %4.0f | %5.2f | %5.2f  (tap 18-22 %.0f)" % (
        "r35 INCIDENT core t %.0f-%.0f" % (ta, tb), g["vego"][a:b].mean(), np.median(g["idx"][a:b]), np.median(np.abs(g["ang"][a:b])), np.median(np.abs(g["T100"][a:b])),
        np.median(np.abs(g["bar"][a:b])), np.mean(np.abs(g["rate_x"][a:b])), band(g["bar"][a:b], 18, 22), band(g["wire"][a:b], 18, 22) / V.CPD, f0, C20.bamp(g["T"][selT], 18, 22, FST)))
    # r35's other loud stretches: list contiguous hot runs route-wide (>= 2 s) for context
    pr("\n  r35 route-wide: contiguous line-present stretches >= 1.5 s (2 s windows): t0-t1 | amp p50/max | f | v | idx | |tq| | local time")
    for tag in ("r35",):
        sel = np.flatnonzero((Rw["tag"] == tag) & pres)
        tsel = Rw["t"][sel]
        if not len(tsel):
            continue
        brk = np.flatnonzero(np.diff(tsel) > 0.75)
        starts = np.r_[0, brk + 1]; ends = np.r_[brk, len(tsel) - 1]
        for s_, e_ in zip(starts, ends):
            k = sel[s_:e_ + 1]
            if tsel[e_] + 2 - tsel[s_] < 1.5:
                continue
            pr("    %6.1f-%6.1f | %4.0f/%4.0f | %.1f | %4.1f | %3.0f | %4.0f | %s%s" % (tsel[s_], tsel[e_] + 2, np.median(Rw["amp"][k]), Rw["amp"][k].max(), Rw["f0"][k].mean(), np.median(Rw["v"][k]), np.median(Rw["idx"][k]),
                                                                         np.median(Rw["tq"][k]), loc(tsel[s_]), "  <== the incident" if tsel[s_] - 2 <= t_inc <= tsel[e_] + 2 else ""))

    # ---------------------------------------------------------------- 4. chain mirror
    pr("\n" + "=" * 150); pr("4. CHAIN MIRROR on the incident core (FUN_00028ea6, V281r3 cells, live fade, open loop on the measured rate) and counterfactuals"); pr("=" * 150)
    lo, hi = f0 - 2, f0 + 2
    pr("  band = %.1f-%.1f Hz (f0 +-2); amplitudes at the tap's own 50 Hz instants; P/D = the P-only and D-only mirror outputs" % (lo, hi))
    kp280 = c280["kp_Y"]
    for lab, kw in (("AS BUILT (Kp flat 248, Kd 128, fade live)", {}), ("  no fade (m = 254)", dict(fade=False)), ("  linear-interp cmd", dict(cmd_mode="lin")),
                    ("  Kp = V280r2 table (what V280 had at this idx)", dict(kpY=kp280)), ("  Kd 0", dict(kd=0)), ("  Kd 64", dict(kd=64)), ("  Kd 0 AND Kp V280", dict(kd=0, kpY=kp280)),
                    ("  lag 1008/253 (2.5 Hz pole)", dict(lag=(1008, 253))), ("  lag 960/1014 (10 Hz pole)", dict(lag=(960, 1014))), ("  fb single-sample x2", dict(fb_single=True)),
                    ("  rate low-passed < 15 Hz", dict(rate_filter=15.0)), ("  cmd frozen", dict(freeze_cmd=True)), ("  cmd frozen AND rate < 15 Hz", dict(freeze_cmd=True, rate_filter=15.0))):
        pr(fmt_e(lab, eval_window(g, a, b, c281, lo, hi, **kw)))
    pr("  the same on the r34 attenuated seconds (V280r2 cells, live fade) for reference, and with Kp flat 248 counterfactually:")
    for (u0, u1) in R34_OP:
        aa = int(np.searchsorted(g34["tr"], u0)); bb = int(np.searchsorted(g34["tr"], u1))
        pr(fmt_e("r34 t %.0f-%.0f as built (V280r2)" % (u0, u1), eval_window(g34, aa, bb, c280, 18, 22)))
        pr(fmt_e("  Kp flat 248", eval_window(g34, aa, bb, c280, 18, 22, kpY=c281["kp_Y"])))
    # loop margins with the creep plant? not re-estimated here: report L_fw magnitudes at f0 for 248 vs the V280 Kp at the incident idx
    idx50 = float(np.median(g["idx"][a:b])); kp280_at = float(lerp(c280["kp_X"], c280["kp_Y"], idx50))
    pr("  controller-only |L_fw| at f0 %.1f Hz (T counts per deg/s, one tick): Kp 248 %.1f ; Kp %.0f (V280 at idx %.0f) %.1f ; Kd 0 at 248 %.1f ; ratio D/P at f0 for Kp 248 = %.2f" % (
        f0, abs(C20.L_fw(c281, f0, 248)), kp280_at, idx50, abs(C20.L_fw(c280, f0, kp280_at)), abs(C20.L_fw(c281, f0, 248, kd=0)), 16 * 2 * np.sin(np.pi * f0 / 1000) / (248 / 256.0)))
    # measured T-per-rate in the core vs L_fw (the identity test)
    if b - a >= 200:
        segn = C20.native_tap_segment(g, a, b)
        if segn is not None and len(segn["T"]) >= 64:
            P = C20.Pool(FST, 64); P.add(segn); f = P.f
            H = P.tf("r", "T"); j = int(np.argmin(np.abs(f - f0)))
            pr("  identity test in the core: measured |T/rate_x| at %.1f Hz %.1f ph %+.0f coh %.2f vs L_fw(248) %.1f ph %+.0f -> ratio %.2f" % (
                f[j], abs(H[j]), np.degrees(np.angle(H[j])), P.coh("r", "T")[j], abs(C20.L_fw(c281, f[j], 248)), np.degrees(np.angle(C20.L_fw(c281, f[j], 248))), abs(H[j]) / abs(C20.L_fw(c281, f[j], 248))))
            Gd = P.tf("T", "r")
            pr("  closed-loop 'plant' rate_x/T in the core (x1e-3 deg/s per count; at a line this is 1/C by construction): " + "  ".join("%.0f Hz %.1f/%+.0f/%.2f" % (x, 1e3 * abs(np.interp(x, f, Gd)), np.degrees(np.angle(np.interp(x, f, Gd))), np.interp(x, f, P.coh("T", "r"))) for x in (10, 15, 18, 20, 22)))

    out = os.path.join(HERE, "_scratch", "grind_incident_r35.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
