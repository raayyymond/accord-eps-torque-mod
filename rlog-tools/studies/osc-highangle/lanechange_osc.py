#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/lanechange_osc.py -- the operator's report on V278 rev 3 (routes r32, r33, 2026-09-02):
"on the highway, when changing lanes (low torque request), the steering wheel oscillates. before, this manoeuvre
was smooth like on V112."  and  "seems like an LKAS PID loop tuning issue, I don't think openpilot is in the loop."

Reads the `_ha_<route>.npz` caches written by highangle_stutter.py (same wire conventions -- see its docstring:
0x18F rate i16be b2-3 = 8 counts/deg/s, driver torque b0-1, 0x14A angle x-0.1, 0xE4 src>=128 command + STEER_REQUEST,
0x1AB tap field ((b0&3)<<8)|b1, T = (-1 if bit9 else 1)*((field&0x1ff)<<3) on rev 3 ONLY; engaged = 0x18F b4.3 AND
STEER_REQUEST) and its grid()/demand_index().  Then:

  1. HIGHWAY frames: engaged, vEgo >= 20 m/s, |angle| < 8 deg.  Two event classes on them:
       (a) COMMAND EXCURSIONS (the lane-change manoeuvre): |cmd| low-passed at 1 Hz above CMD_EXC for >= 0.5 s.
       (b) OSCILLATION EPISODES: 2-12 Hz rate envelope (Hilbert of a 4th-order band-pass, 1 Hz smoothed) above a
           FIXED physical threshold ENV_THR wire counts (= ENV_THR/8 deg/s amplitude) for >= 0.6 s, gaps < 0.5 s merged.
           A fixed threshold so every route is scored on the same ruler (the r31 study used a per-route reference;
           here the reference routes ARE the comparison).
     Per episode: dominant frequency of the rate (Welch, 1.28 s segments, and a Hilbert instantaneous-frequency
     median of the band-passed rate), of T and of the command; amplitude (sqrt(2) x band RMS, wire counts and deg/s);
     angle swing; |cmd| and demand index; damping fraction P(sign(T) != sign(raw rate)); T saturation duty and |T|
     percentiles; coherence and phase of the 0xE4 command vs the rate at f_dom; the command's own band amplitude and
     spectral prominence at f_dom; controlsState torqueState desiredLateralAccel / error swing.
  2. Cross-route 4-12 Hz rate band energy (Welch on contiguous runs) at matched speed (20-25 / 25-32 m/s) and
     |cmd| (0-100 / 100-300 / 300-1000 / >1000) on r22 (V112), r97 (stock), r31/r32/r33 (V278 rev 3; r31 has no
     highway frames).  Plus the rate envelope percentiles on the same strata.
  3. The chain arithmetic of studies/osc-2to4/dose_e_sign_by_k.py / studies/v280/v280_map_profiles.py on the
     highway frames of r32/r33 with rev 3's cells (map x2 all knots, fb clamp 15360, Kp LERP 248..696, P clamp 15360):
       E = 32*sp - fb ; P = E*Kp(idx) >> 8 ; P rails at |P| >= 15360 ; fb clamp binds at |fb_un| >= 15360.
     P-rail duty and fb-clamp duty on all highway frames, on the excursions and on the oscillation episodes.

Run:  python lanechange_osc.py            (writes LANECHANGE-<tag>.txt and lanechange_events.json beside itself)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import highangle_stutter as H  # noqa: E402  (grid, demand_index, runs_of, band_power, FS)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CPD = 8.0
V_HW = 20.0
ANG_HW = 8.0
CMD_EXC = 120.0          # |cmd| (1 Hz LPF) above this = a manoeuvre; rev 3 highway |cmd| p90 is 160
ENV_THR = 40.0           # 2-12 Hz rate envelope, wire counts = 5 deg/s amplitude
OSC_BAND = (2.0, 12.0)
BAND_412 = (4.0, 12.0)

SCRATCH = (r"C:\Users\dudei\AppData\Local\Temp\claude\C--Users-dudei-Desktop-Projects-accord-eps-torque-mod"
           r"\1129e2c5-0c63-4cae-b75a-e528b96d16ef\scratchpad\r3stutter")
ROUTES = {
    "r22": ("75604b0a432fdc89_00000022--00f57626e0", "V112", SCRATCH),
    "r97": ("75604b0a432fdc89_00000097--489d7896b3", "stock", SCRATCH),
    "r31": ("75604b0a432fdc89_00000031--a680e9b2ac", "V278r3", SCRATCH),
    "r32": ("75604b0a432fdc89_00000032--33a5dbbcb3", "V280r2", os.path.join(HERE, "_scratch")),
    "r33": ("75604b0a432fdc89_00000033--1948a2c354", "V280r2", os.path.join(HERE, "_scratch")),
    "r34": ("75604b0a432fdc89_00000034--e2d2d5381f", "V280r2-newtune", os.path.join(HERE, "_scratch")),   # 2026-09-03: same firmware, NEW StarPilot tune
}
HAS_TAP = {"r31", "r32", "r33", "r34"}

# --- chain constants (dose_e_sign_by_k.py / v280_map_profiles.py; FUN_00028ea6 decompile) ---------------------
MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
MAP_Y_STOCK = np.array([0, 24, 42, 50, 62, 100, 126, 154, 166, 172], float)
KP_X = np.array([0, 68, 112, 136, 208], float)
KP_Y = np.array([248, 512, 645, 696, 696], float)
A_COEF, B_COEF = 923, 1560
FB_DC = 2 * B_COEF / (1024 - A_COEF)          # 30.89 per raw count
P_CLAMP = 15360
REV3 = dict(K=2.0, fb_clamp=15360)
# 🛑 BUILD CORRECTION 2026-09-02 (orchestrator, verified from the tap; strongturn study): r32/r33 were driven on V280 rev 2
# (slot-7 map a straight line to the x6 top, 0xC62E6 = 46080), NOT rev 3.  r31 is rev 3 (x2 / 15360).  r22 V112 / r97 stock: x1 / 7680.
MAP_Y_V280R2 = np.array([0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], float)
CHAIN_CFG = {"r31": dict(mapY=MAP_Y_STOCK * 2, fb_clamp=15360, name="V278 rev 3 (map x2, clamp 15360)"),
             "r32": dict(mapY=MAP_Y_V280R2, fb_clamp=46080, name="V280 rev 2 (line to x6 top, clamp 46080)"),
             "r33": dict(mapY=MAP_Y_V280R2, fb_clamp=46080, name="V280 rev 2 (line to x6 top, clamp 46080)"),
             "r34": dict(mapY=MAP_Y_V280R2, fb_clamp=46080, name="V280 rev 2 (line to x6 top, clamp 46080) + new tune"),
             "r22": dict(mapY=MAP_Y_STOCK, fb_clamp=7680, name="V112 (map x1, clamp 7680)"),
             "r97": dict(mapY=MAP_Y_STOCK, fb_clamp=7680, name="stock (map x1, clamp 7680)")}


def feedback_1khz(x100):
    n = len(x100)
    t100 = np.arange(n) / FS
    t1k = np.arange(0, n / FS, 1e-3)
    x1k = np.interp(t1k, t100, x100)
    s = 0.0
    fb = np.empty_like(x1k)
    for i, xv in enumerate(x1k):
        s_new = (A_COEF * s) // 1024 + (B_COEF * xv) // 1024
        fb[i] = s + s_new
        s = s_new
    return np.interp(t100, t1k, fb)


def bp(x, lo, hi):
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x - np.mean(x))


def envelope(x, lo, hi):
    rb = bp(x, lo, hi)
    return signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb))), rb


def lpf(x, fc):
    return signal.sosfiltfilt(signal.butter(2, fc, fs=FS, output="sos"), x)


def band_amp(x, lo, hi):
    if len(x) < 40:
        return np.nan
    return float(np.sqrt(2) * bp(x, lo, hi).std())


def fdom(x, lo=1.0, hi=20.0):
    n = min(128, len(x))
    if n < 64:
        return np.nan, np.nan
    f, P = signal.welch(x - x.mean(), fs=FS, nperseg=n)
    sel = (f >= lo) & (f < hi)
    i = int(np.argmax(P[sel]))
    return float(f[sel][i]), float(P[sel][i] / max(np.median(P[sel]), 1e-30))


def inst_freq(rb):
    """median instantaneous frequency of an analytic band-passed signal, weighted by envelope."""
    if len(rb) < 40:
        return np.nan
    a = signal.hilbert(rb)
    ph = np.unwrap(np.angle(a))
    fi = np.diff(ph) * FS / (2 * np.pi)
    w = np.abs(a[1:])
    m = w > np.percentile(w, 50)
    return float(np.median(fi[m])) if m.any() else np.nan


def coh_phase(x, y, f0):
    n = min(128, len(x))
    if n < 64 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan
    f, C = signal.coherence(x, y, fs=FS, nperseg=n)
    _, P = signal.csd(x, y, fs=FS, nperseg=n)
    j = int(np.argmin(np.abs(f - f0)))
    return float(C[j]), float(np.degrees(np.angle(P[j])))


def merge_runs(mask, minlen, gap):
    runs = H.runs_of(mask, 1)
    out = []
    for a, b in runs:
        if out and a - out[-1][1] < gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a >= minlen]


def load(tag):
    prefix, build, d = ROUTES[tag]
    D = dict(np.load(os.path.join(d, "_ha_%s.npz" % prefix)))
    G = H.grid(D)
    G["hw"] = G["eng"] & (G["v"] >= V_HW) & (np.abs(G["ang"]) < ANG_HW)
    G["env"], G["rb"] = envelope(G["rate"], *OSC_BAND)
    G["cmd_lp"] = lpf(G["cmd"], 1.0)
    if tag not in HAS_TAP:
        G["T"] = np.zeros_like(G["rate"])
    return G


def chain(G, cfg=None):
    """the chain on the 100 Hz grid (fb from the 1 kHz IIR); cfg = CHAIN_CFG[tag] (map knots + fb clamp)."""
    cfg = cfg or dict(mapY=MAP_Y_STOCK * REV3["K"], fb_clamp=REV3["fb_clamp"])
    x_raw = -G["rate"]
    fb_un = feedback_1khz(x_raw)
    S = np.clip(-4.0 * np.round(G["cmd"]), -15360, 15360)
    taper = np.interp(np.abs(G["tq"]) // 32, H.TAPER_X, H.TAPER_Y)
    prod = (taper * 255).astype(np.int64) & 0xFFFF
    v = np.floor(prod * S / 65536.0)
    v = np.clip(np.floor(v / 64.0), -240, 240)
    idx, sgn = np.abs(v), np.where(v < 0, -1.0, 1.0)
    sp = sgn * np.interp(idx, MAP_X, cfg["mapY"])
    kp = np.interp(idx, KP_X, KP_Y)
    fb = np.clip(fb_un, -cfg["fb_clamp"], cfg["fb_clamp"])
    E = 32 * sp - fb
    P_raw = np.floor(E * kp / 256)
    return dict(fb_un=fb_un, fb=fb, sp=sp, kp=kp, E=E, P_raw=P_raw, idx=idx,
                p_rail=np.abs(P_raw) >= P_CLAMP, fb_clamped=np.abs(fb_un) >= cfg["fb_clamp"],
                ref_deg=32 * np.abs(sp) / FB_DC / CPD, window_deg=P_CLAMP * 256 / kp / FB_DC / CPD)


def chain_stats(C, m):
    if not m.any():
        return {}
    return dict(n=int(m.sum()), p_rail=float(C["p_rail"][m].mean()), fb_clamped=float(C["fb_clamped"][m].mean()),
                absE_p50=float(np.median(np.abs(C["E"][m]))), absE_p90=float(np.percentile(np.abs(C["E"][m]), 90)),
                absE_max=float(np.abs(C["E"][m]).max()),
                absP_p50=float(np.median(np.abs(C["P_raw"][m]))), absP_p90=float(np.percentile(np.abs(C["P_raw"][m]), 90)),
                fb_p50=float(np.median(np.abs(C["fb"][m]))), fb_p90=float(np.percentile(np.abs(C["fb"][m]), 90)),
                sp32_p50=float(np.median(32 * np.abs(C["sp"][m]))), sp32_p90=float(np.percentile(32 * np.abs(C["sp"][m]), 90)),
                ref_p50=float(np.median(C["ref_deg"][m])), ref_p90=float(np.percentile(C["ref_deg"][m], 90)),
                kp_p50=float(np.median(C["kp"][m])), window_p50=float(np.median(C["window_deg"][m])),
                fb_dom=float(np.mean(np.abs(C["fb"][m]) > 32 * np.abs(C["sp"][m]))),
                E_over_window=float(np.mean(np.abs(C["E"][m]) >= P_CLAMP * 256 / C["kp"][m])))


def event_row(G, C, a, b, tag, kind):
    w = slice(a, b)
    rate, T, cmd, ang = G["rate"][w], G["T"][w], G["cmd"][w], G["ang"][w]
    rb = G["rb"][w]
    fr, promr = fdom(rate)
    fi = inst_freq(rb)
    fT, promT = fdom(T) if tag in HAS_TAP else (np.nan, np.nan)
    fc, promc = fdom(cmd)
    f0 = fr if np.isfinite(fr) else 5.0
    cohc, phc = coh_phase(rate, cmd, f0)
    cohT, phT = coh_phase(rate, T, f0) if tag in HAS_TAP else (np.nan, np.nan)
    coha, pha = coh_phase(ang, cmd, f0)
    # coherence in the whole 4-12 band (mean) so a broad-band ring is not missed at one bin
    nn = min(128, b - a)
    if nn >= 64 and np.std(cmd) > 0:
        f, Cc = signal.coherence(rate, cmd, fs=FS, nperseg=nn)
        cohc_band = float(Cc[(f >= 4) & (f < 12)].mean())
    else:
        cohc_band = np.nan
    mt = (T != 0) & (rate != 0)
    damp = float(np.mean(np.sign(T[mt]) != np.sign(rate[mt]))) if (tag in HAS_TAP and mt.any()) else np.nan
    row = dict(tag=tag, kind=kind, t0=float(G["t"][a]), dur=float((b - a) / FS),
               v=float(np.median(G["v"][w])), ang50=float(np.median(ang)), ang_swing=float(ang.max() - ang.min()),
               cmd_pk=float(np.abs(cmd).max()), cmd50=float(np.median(np.abs(cmd))),
               idx50=float(np.median(G["idx"][w])), idx_pk=float(G["idx"][w].max()),
               tq50=float(np.median(np.abs(G["tq"][w]))), tq_pk=float(np.abs(G["tq"][w]).max()),
               f_rate=fr, prom_rate=promr, f_inst=fi, f_T=fT, prom_T=promT, f_cmd=fc, prom_cmd=promc,
               env_pk=float(G["env"][w].max()), env_mean=float(G["env"][w].mean()),
               amp_rate=band_amp(rate, *OSC_BAND), amp_rate_412=band_amp(rate, *BAND_412),
               amp_cmd=band_amp(cmd, *OSC_BAND), amp_cmd_412=band_amp(cmd, *BAND_412),
               amp_T=band_amp(T, *OSC_BAND) if tag in HAS_TAP else np.nan,
               absT50=float(np.median(np.abs(T))) if tag in HAS_TAP else np.nan,
               absT90=float(np.percentile(np.abs(T), 90)) if tag in HAS_TAP else np.nan,
               absT_max=float(np.abs(T).max()) if tag in HAS_TAP else np.nan,
               T_sat=float(np.mean(np.abs(G["fld"][w] & 0x1FF) >= H.T_SAT_FIELD)) if tag in HAS_TAP else np.nan,
               damp=damp, coh_cmd=cohc, ph_cmd=phc, coh_cmd_band=cohc_band, coh_ang_cmd=coha, ph_ang_cmd=pha,
               coh_T=cohT, ph_T=phT,
               eng_frac=float(G["eng"][w].mean()), hw_frac=float(G["hw"][w].mean()))
    if G["des"] is not None:
        row["des_amp"] = float(G["des"][w].max() - G["des"][w].min())
        row["err_amp"] = float(G["err"][w].max() - G["err"][w].min())
        row["err_amp_412"] = band_amp(G["err"][w], *BAND_412)
        row["des_amp_412"] = band_amp(G["des"][w], *BAND_412)
    if C is not None:
        row.update({"ch_" + k: v for k, v in chain_stats(C, np.zeros_like(G["hw"]).astype(bool) | np.isin(np.arange(len(G["t"])), np.arange(a, b))).items()})
    return row


def strata_table(G, tag):
    """4-12 Hz rate band power and envelope stats by speed x |cmd| stratum on highway frames."""
    rows = []
    aCmd = np.abs(G["cmd_lp"])
    for vlo, vhi in ((20, 25), (25, 32), (20, 32)):
        for clo, chi in ((0, 100), (100, 300), (300, 1000), (1000, 1e9), (0, 1e9)):
            m = G["hw"] & (G["v"] >= vlo) & (G["v"] < vhi) & (aCmd >= clo) & (aCmd < chi)
            secs = m.sum() / FS
            if secs < 3:
                continue
            P, tot = H.band_power(G["rate"], m, nperseg=128)
            f, Pw = None, None
            runs = H.runs_of(m, 128)
            acc, n = None, 0
            for a, b in runs:
                f, Pw = signal.welch(G["rate"][a:b] - G["rate"][a:b].mean(), fs=FS, nperseg=128)
                acc = Pw * (b - a) if acc is None else acc + Pw * (b - a); n += b - a
            if acc is None:
                continue
            Pw = acc / n; df = f[1] - f[0]
            b412 = float(Pw[(f >= 4) & (f < 12)].sum() * df)
            b48 = float(Pw[(f >= 4) & (f < 8)].sum() * df)
            b812 = float(Pw[(f >= 8) & (f < 12)].sum() * df)
            b24 = float(Pw[(f >= 2) & (f < 4)].sum() * df)
            sel = (f >= 2) & (f < 15); i = int(np.argmax(Pw[sel]))
            rows.append(dict(tag=tag, v=(vlo, vhi), cmd=(clo, chi), secs=float(secs), welch_s=float(n / FS),
                             b24=b24, b48=b48, b812=b812, b412=b412, fpk=float(f[sel][i]),
                             prom=float(Pw[sel][i] / np.median(Pw[sel])),
                             env50=float(np.median(G["env"][m])), env95=float(np.percentile(G["env"][m], 95)),
                             env99=float(np.percentile(G["env"][m], 99)),
                             osc_duty=float(np.mean(G["env"][m] > ENV_THR)),
                             idx50=float(np.median(G["idx"][m])), idx90=float(np.percentile(G["idx"][m], 90)),
                             cmd50=float(np.median(np.abs(G["cmd"][m]))), tq50=float(np.median(np.abs(G["tq"][m])))))
    return rows


def main():
    out_json = dict(events={}, strata={}, chain={})
    for tag in ("r32", "r33", "r22", "r97", "r31"):
        G = load(tag)
        build = ROUTES[tag][1]
        lines = []
        pr = lambda s="": (print(s), lines.append(s))  # noqa: E731
        pr("=" * 130)
        pr("ROUTE %s  %s  (%s)   engaged %.0f s   HIGHWAY (engaged, v>=%.0f, |ang|<%.0f) %.0f s" %
           (tag, ROUTES[tag][0], build, G["eng"].sum() / FS, V_HW, ANG_HW, G["hw"].sum() / FS))
        hw = G["hw"]
        if hw.sum() < 500:
            pr("  no highway frames -- skipped"); out_json["events"][tag] = []
            open(os.path.join(HERE, "LANECHANGE-%s.txt" % tag), "w", encoding="utf-8").write("\n".join(lines)); continue
        pr("  highway v p50/max %.1f/%.1f   |cmd| p50/p90/p99 %s   idx p50/p90/p99 %s   |tq_raw| p50/p90 %s" % (
            np.median(G["v"][hw]), G["v"][hw].max(), np.percentile(np.abs(G["cmd"][hw]), [50, 90, 99]).round(0),
            np.percentile(G["idx"][hw], [50, 90, 99]).round(0), np.percentile(np.abs(G["tq"][hw]), [50, 90]).round(0)))
        pr("  2-12 Hz rate envelope on highway: p50/p95/p99/max %s wire (/8 = deg/s)   duty>%.0f: %.3f" % (
            np.percentile(G["env"][hw], [50, 95, 99, 100]).round(0), ENV_THR, np.mean(G["env"][hw] > ENV_THR)))
        fr, pm = fdom(G["rate"][hw]) if hw.sum() > 200 else (np.nan, np.nan)
        P412, _ = H.band_power(G["rate"], hw, nperseg=256)
        pr("  highway rate spectrum: 2-4 %.0f  4-8 %.0f  8-15 %.0f (Welch power, wire^2)" % (P412["2-4"], P412["4-8"], P412["8-15"]))

        C = chain(G, CHAIN_CFG[tag])
        if C is not None:
            cs = chain_stats(C, hw)
            pr("  CHAIN [%s] on highway frames:" % CHAIN_CFG[tag]["name"])
            pr("    P-rail duty %.4f  fb-clamp duty %.4f  |E| p50/p90/max %.0f/%.0f/%.0f  "
               "|P| p50/p90 %.0f/%.0f  |fb| p50/p90 %.0f/%.0f  32|sp| p50/p90 %.0f/%.0f  ref p50/p90 %.1f/%.1f deg/s  "
               "Kp p50 %.0f (window %.1f deg/s)  fb-dominant %.2f  |E| past P window %.4f" % (
                   cs["p_rail"], cs["fb_clamped"], cs["absE_p50"], cs["absE_p90"], cs["absE_max"], cs["absP_p50"], cs["absP_p90"],
                   cs["fb_p50"], cs["fb_p90"], cs["sp32_p50"], cs["sp32_p90"], cs["ref_p50"], cs["ref_p90"], cs["kp_p50"],
                   cs["window_p50"], cs["fb_dom"], cs["E_over_window"]))
            out_json["chain"][tag] = dict(highway=cs)

        # --- (a) command excursions --------------------------------------------------------------------
        exc = merge_runs(hw & (np.abs(G["cmd_lp"]) > CMD_EXC), int(0.5 * FS), int(0.5 * FS))
        # extend each by 1.5 s after (the settle) while still engaged on highway
        exc = [(a, min(b + int(1.5 * FS), len(G["t"]))) for a, b in exc]
        # --- (b) oscillation episodes --------------------------------------------------------------------
        eps = merge_runs(hw & (G["env"] > ENV_THR), int(0.6 * FS), int(0.5 * FS))
        eps = [(max(a - int(0.3 * FS), 0), min(b + int(0.3 * FS), len(G["t"]))) for a, b in eps]
        rows = [event_row(G, C, a, b, tag, "EXC") for a, b in exc] + [event_row(G, C, a, b, tag, "OSC") for a, b in eps]
        # overlap flag
        for r in rows:
            if r["kind"] == "EXC":
                r["osc_inside"] = any(not (e["t0"] + e["dur"] < r["t0"] or e["t0"] > r["t0"] + r["dur"]) for e in rows if e["kind"] == "OSC")
            else:
                r["in_exc"] = any(not (e["t0"] + e["dur"] < r["t0"] or e["t0"] > r["t0"] + r["dur"]) for e in rows if e["kind"] == "EXC")
        out_json["events"][tag] = rows
        hdr = ("  kind    t0    dur     v  ang50 swing | cmdpk cmd50 idx50 idxpk  tq50 | f_rate prom f_inst  f_T  f_cmd promc | "
               "envpk amp  amp412 (deg/s) | ampcmd cmd412 | coh_c ph_c cohband cohA | ampT |T|50 |T|90 Tsat damp cohT phT | des err err412 | ch_prail ch_fbcl |E|50 ref50 win")
        pr("  COMMAND EXCURSIONS (|cmd|_1Hz > %.0f, +1.5 s): %d;   OSC EPISODES (env > %.0f wire, >= 0.6 s): %d, %.1f s" % (
            CMD_EXC, len(exc), ENV_THR, len(eps), sum(b - a for a, b in eps) / FS))
        pr(hdr)
        for r in sorted(rows, key=lambda r: r["t0"]):
            pr("  %-4s%s %6.1f %4.1f %5.1f %6.1f %5.1f | %5.0f %5.0f %5.0f %5.0f %5.0f | %5.2f %4.0f %5.2f %5.2f %5.2f %4.0f | "
               "%5.0f %4.0f %5.0f (%4.1f) | %5.0f %5.0f | %4.2f %5.0f %5.2f %4.2f | %4.0f %5.0f %5.0f %4.2f %4.2f %4.2f %5.0f | %5.3f %5.3f %5.3f | %6.4f %6.4f %6.0f %5.1f %4.1f" % (
                   r["kind"], "*" if r.get("osc_inside") or r.get("in_exc") else " ", r["t0"], r["dur"], r["v"], r["ang50"], r["ang_swing"],
                   r["cmd_pk"], r["cmd50"], r["idx50"], r["idx_pk"], r["tq50"],
                   r["f_rate"], r["prom_rate"], r["f_inst"], r["f_T"], r["f_cmd"], r["prom_cmd"],
                   r["env_pk"], r["amp_rate"], r["amp_rate_412"], r["amp_rate_412"] / CPD,
                   r["amp_cmd"], r["amp_cmd_412"], r["coh_cmd"], r["ph_cmd"], r["coh_cmd_band"], r["coh_ang_cmd"],
                   r["amp_T"], r["absT50"], r["absT90"], r["T_sat"], r["damp"], r["coh_T"], r["ph_T"],
                   r.get("des_amp", np.nan), r.get("err_amp", np.nan), r.get("err_amp_412", np.nan),
                   r.get("ch_p_rail", np.nan), r.get("ch_fb_clamped", np.nan), r.get("ch_absE_p50", np.nan),
                   r.get("ch_ref_p50", np.nan), r.get("ch_window_p50", np.nan)))
        # --- strata ------------------------------------------------------------------------------------
        st = strata_table(G, tag)
        out_json["strata"][tag] = st
        pr("  STRATA (highway; Welch 1.28 s runs):  v      |cmd|      secs  welch_s |  2-4    4-8   8-12   4-12 (wire^2) | fpk prom | env50 env95 env99 osc_duty | idx50 idx90 cmd50 tq50")
        for s in st:
            pr("    %-8s %-12s %6.0f %6.0f | %6.0f %6.0f %6.0f %6.0f | %5.2f %4.0f | %4.0f %4.0f %4.0f %5.3f | %4.0f %4.0f %5.0f %5.0f" % (
                "%d-%d" % s["v"], "%d-%s" % (s["cmd"][0], "inf" if s["cmd"][1] > 1e8 else "%d" % s["cmd"][1]), s["secs"], s["welch_s"],
                s["b24"], s["b48"], s["b812"], s["b412"], s["fpk"], s["prom"], s["env50"], s["env95"], s["env99"], s["osc_duty"],
                s["idx50"], s["idx90"], s["cmd50"], s["tq50"]))
        open(os.path.join(HERE, "LANECHANGE-%s.txt" % tag), "w", encoding="utf-8").write("\n".join(lines))

    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, tuple):
            return list(o)
        raise TypeError(type(o))
    json.dump(out_json, open(os.path.join(HERE, "lanechange_events.json"), "w"), indent=1, default=conv)


if __name__ == "__main__":
    main()
