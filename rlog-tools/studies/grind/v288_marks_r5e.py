# -*- coding: utf-8 -*-
"""studies/grind/v288_marks_r5e.py -- the anatomy of the THREE BOOKMARKED grinding episodes on the first V288 rev 2
drive (route 75604b0a432fdc89_0000005e--03a9714d78, 2026-09-08, tag r5e_v288), and whether the grinding MOVED vs V282.
Subagent `marks`, 2026-09-08.  Analysis only: builds nothing, flashes nothing, sends nothing.

The operator: "This route has multiple bookmarks where I noticed the grinding and flagged it with a bookmark
immediately after."  Three userBookmark events, route t 129.36 / 331.56 / 820.15 s (segments 2 / 5 / 13, times on
the v280-cache clock = first 0x18F frame).  Earlier guess: the residual grind "is probably attenuated and higher
frequency than it was stock".

What this does, per bookmark, window [mark-20 s, mark+3 s]:
  1. context at 0.1 s: v, angle, wheel rate, driver torque (hands on/off at |bar| 400), 0xE4 command and its
     CAPPED-frame share (|dcmd| >= 122 raw per 100 Hz 0xE4 frame, on the 0xE4 stream's own frame counter), lateral
     engaged / steeringPressed edges, brake, blinkers, lane change, IMU lateral.
  2. the census recipe (grind1_census_v282.py, copied line for line: 2 s windows, 0.5 s step, present = most
     prominent 15-26 Hz peak prominence >= 8 AND bar 18-22 >= 40 raw; episode = >= 0.5 s contiguous present run
     inside an engaged run; BURST / RIDE-ALONG / SUSTAINED) run over the window, so every episode is on the same
     yardstick as V282's 130.
  3. broadband anatomy 3-48 Hz (bar, wheel rate, 0xE4 command, IMU lateral: 100 Hz streams -> Nyquist 50; the 0x1AB
     torque tap T: 50 Hz native -> nothing above 25 Hz is observable on it): Hilbert band envelopes, peak and time of
     peak of every band before the mark; two "cores" (2 s around the bar 5-12 Hz envelope peak and around the bar
     15-26 Hz envelope peak, both before the mark, the r39-read's recipe) with every prominent line (f, prominence,
     band amplitude), growth_fit rise/decay slopes, zeta_eff = -decay/(2 pi f0) and Q = 1/(2 zeta).
  4. trigger anatomy at each census-episode onset: capped 0xE4 frames in the 0.5 s before, |dangle| over the prior
     1 s, wheel rate, hands, blinker / lane change within +-3 s, brake, speed, idx, engage edges in the prior 3 s.
Then the SAME code on r39's two V282 bookmarks (t 689.66 / 927.70 s, the only V282 marks -- r3a/r3c have none), a
route-wide census of r5e_v288 on the V282 yardstick (r39 re-run alongside as a check that this copy of the recipe
reproduces the census's 79 episodes / 364 present windows), and a V288 cave-bit sanity read (b4.5 = sign(filtered
setpoint) on THIS build; bit 6 = |r24| >= |T|; bits 3/4/7 the three-sign rung).

Instruments reused verbatim (imported, not copied): grind_incident_r35.{read_cells, demand_live, line_of, envelope,
growth_fit, band}; creep20_loop_id.{load, dejitter, runs, bandpass, bamp}; grind1_census_v282.{onset_transient,
steady_creep_at}.  Caches: analysis-2020accord/_scratch/cache/v280/{r5e_v288,r39}{,_b4}.npz + _marks.json (never
rewritten); corpus extras (IMU, brake, blinkers, lane change, steeringPressed) from _scratch/cache/r5e_v288/r5e_v288.npz.
Run: python v288_marks_r5e.py   -> _scratch/v288_marks_r5e.txt, _scratch/v288_marks_r5e_*.png
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20            # noqa: E402
import grind_incident_r35 as GI          # noqa: E402
import grind1_census_v282 as CEN         # noqa: E402  (onset_transient, steady_creep_at; the loop below mirrors its main())
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V            # noqa: E402
import _grind2_lib as G2                 # noqa: E402

import matplotlib                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
FST = 50.0
W, STEP = 200, 50
CACHE = C20.CACHE
CORPUS = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "r5e_v288", "r5e_v288.npz")
IMG = {"V288": LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V282": LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"}
ROUTES = {"r5e_v288": ("V288", "V288 rev 2, 2026-09-08"), "r39": ("V282", "V282 LAF 2.11, 2026-09-04")}
PRE, POST = 20.0, 3.0
CAP = 122.0                                    # |dcmd| >= 122 raw / 0xE4 frame = openpilot's 0.03*4096 slew cap (WIRE-0XE4 §1b)
HANDS = 400.0
BANDS = [("3-5", 3, 5), ("5-12", 5, 12), ("12-17", 12, 17), ("18-22", 18, 22), ("25-35", 25, 35), ("35-48", 35, 48)]
# fixed categorical order for every figure (dataviz: assign by entity, never cycle)
COL = {"bar": "#1f5fbf", "wire": "#d95f02", "T": "#1b9e77", "imu": "#7570b3", "cmd": "#66666f"}
OUT = []


def pr(s=""):
    print(s)
    OUT.append(s)


# ======================================================================================================================
def load_route(tag, cells):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], cells)
    B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
    k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
    b4 = B["b4"].astype(int)
    for bit in (3, 4, 5, 6, 7):
        g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
    g["rate"] = np.abs(g["wire"]) / V.CPD
    g["rate_s"] = g["wire"] / V.CPD                         # signed deg/s
    # the 0xE4 stream on ITS OWN frame counter: capped-frame mask per 0xE4 frame, then a per-18F-frame share
    D = np.load(os.path.join(CACHE, tag + ".npz"))
    ke4, Pe4, tne4, _ = C20.dejitter(D["te4"], 0.01, 100)
    cmd_e4 = D["cmd"].astype(float)
    dk = np.diff(ke4)
    cap = np.r_[False, (np.abs(np.diff(cmd_e4)) >= CAP) & (dk == 1)]
    g["cap_t"] = tne4 - g["t"][0]
    g["cap"] = cap
    g["cmd_e4"] = cmd_e4
    g["dcmd_e4"] = np.r_[0.0, np.diff(cmd_e4)]
    # T on its native 50 Hz instants, route-relative
    g["T_tr"] = g["T_t"] - g["t"][0]
    # corpus extras (r5e_v288 only)
    g["extras"] = None
    if tag == "r5e_v288" and os.path.exists(CORPUS):
        Cc = np.load(CORPUS, allow_pickle=True)
        off = float(Cc["t0_mono"][0]) - g["t"][0]           # corpus clock -> v280 clock
        tc = Cc["t"] + off
        ex = {}
        for k in ("imu_lat", "imu_vert", "cs_brake", "cs_lblink", "cs_rblink", "cs_lchg", "cs_press", "cs_std", "cs_brakev", "cc_lat", "cs_eng"):
            ex[k] = np.interp(g["tr"], tc, Cc[k].astype(float))
        # is imu_lat a real 100 Hz stream or a hold?  fraction of frames whose value changes
        ex["imu_change_frac"] = float(np.mean(np.diff(Cc["imu_lat"]) != 0))
        g["extras"] = ex
    return g


def marks_of(tag):
    M = json.load(open(os.path.join(CACHE, tag + "_marks.json")))
    return [(m["t_route"], m["seg"]) for m in M["marks"]]


# ======================================================================================================================
# the census recipe, restricted to [a, b) frames -- a line-for-line mirror of grind1_census_v282.main() §1-2
# ======================================================================================================================
def census(g, a, b):
    rows = []
    msk = g["eng"].copy()
    msk[:a] = False; msk[b:] = False
    for aa, bb in C20.runs(msk, W):
        for s in range(aa, bb - W + 1, STEP):
            e = s + W
            f0w, promw = CEN.line_of(g["bar"][s:e], FS)
            rows.append(dict(t=g["tr"][s], f0=f0w, prom=promw, amp=GI.band(g["bar"][s:e], 18, 22),
                             amp610=GI.band(g["bar"][s:e], 6, 10),
                             v=float(g["vego"][s:e].mean()), tq=float(np.median(np.abs(g["bar"][s:e]))),
                             creep=bool(1.0 <= g["vego"][s:e].mean() < 3.0),
                             hoff=bool(np.median(np.abs(g["bar"][s:e])) < HANDS)))
    if not rows:
        return {"n": 0, "pres": np.zeros(0, bool), "rows": rows}, []
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)
    episodes = []
    wt, wp = R["t"], pres
    j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
    near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
    hot = msk & near & wp[j]
    for a0, b0 in C20.runs(hot, int(0.5 * FS)):
        f0, prom = CEN.line_of(g["bar"][a0:b0], FS)
        if not np.isfinite(f0):
            continue
        lo, hi = max(0, a0 - 100), min(len(g["tr"]), b0 + 100)
        env = GI.envelope(g["bar"][lo:hi], f0, FS)
        env7 = GI.envelope(g["bar"][lo:hi], 7.5, FS, bw=2.5)
        tloc = g["tr"][lo:hi]
        gu, gd = GI.growth_fit(tloc, env)[0::2]
        amp = GI.band(g["bar"][a0:b0], 18, 22); amp6 = GI.band(g["bar"][a0:b0], 6, 10)
        n25 = max(4, int(0.25 * FS))
        e20 = env[100:100 + (b0 - a0)] if b0 - a0 <= len(env) - 100 else env[:b0 - a0]
        e7 = env7[100:100 + (b0 - a0)] if b0 - a0 <= len(env7) - 100 else env7[:b0 - a0]
        m = min(len(e20), len(e7))
        e20b = e20[:m][:m - m % n25].reshape(-1, n25).mean(1) if m >= n25 else e20[:m]
        e7b = e7[:m][:m - m % n25].reshape(-1, n25).mean(1) if m >= n25 else e7[:m]
        corr7 = float(np.corrcoef(e20b, e7b)[0, 1]) if len(e20b) >= 4 and np.std(e20b) > 0 and np.std(e7b) > 0 else np.nan
        if np.isfinite(gu) and np.isfinite(gd) and gu >= 1.0 and gd <= -1.0 and (b0 - a0) / FS <= 3.0:
            cls = "BURST"
        elif amp6 >= 1.2 * amp and np.isfinite(corr7) and corr7 >= 0.5:
            cls = "RIDE-ALONG"
        else:
            cls = "SUSTAINED"
        episodes.append(dict(a=a0, b=b0, t0=g["tr"][a0], t1=g["tr"][b0 - 1], dur=(b0 - a0) / FS, f0=f0, prom=prom, cls=cls,
                             env=float(np.nanmax(env)), amp=amp, amp6=amp6, corr7=corr7, gu=gu, gd=gd,
                             v=float(g["vego"][a0:b0].mean()), ang0=float(g["ang"][a0]), rate0=float(g["rate"][a0]),
                             idx0=float(g["idx"][a0]), hands=float(np.median(np.abs(g["bar"][a0:b0]))),
                             T=float(np.median(np.abs(g["T100"][a0:b0]))),
                             trans=CEN.onset_transient(g, a0), creep_onset=CEN.steady_creep_at(g, a0)))
    return {"n": len(rows), "pres": pres, "rows": rows, "R": R}, episodes


# ======================================================================================================================
def lines_in(x, fs, lo, hi, prom_min=8.0, nfft=4096):
    """every local maximum of the prominence spectrum in [lo, hi] with prominence >= prom_min: (f, prom, amp_pm2Hz)."""
    x = np.asarray(x, float)
    if len(x) < 32:
        return []
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    keep = (f >= max(0.0, lo - 8.0)) & (f <= hi + 8.0)          # prom_spectrum builds an n x n mask: subset first
    f, P = f[keep], P[keep]
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    m = (f >= lo) & (f <= hi) & np.isfinite(Rp)
    out = []
    idx = np.flatnonzero(m)
    for j in idx[1:-1]:
        if Rp[j] >= prom_min and Rp[j] >= Rp[j - 1] and Rp[j] >= Rp[j + 1]:
            # keep only the top of each +-1.5 Hz cluster
            if out and abs(out[-1][0] - f[j]) < 1.5:
                if Rp[j] > out[-1][1]:
                    out[-1] = (float(f[j]), float(Rp[j]))
                continue
            out.append((float(f[j]), float(Rp[j])))
    res = []
    for f0, p in out:
        res.append((f0, p, C20.bamp(x, max(f0 - 2, 1.0), min(f0 + 2, 0.98 * fs / 2), fs)))
    return sorted(res, key=lambda r: -r[1])


def core_anatomy(g, tc, half=1.0, label=""):
    """2 s core around tc: lines on bar / wire / cmd / imu (100 Hz, 3-48) and T (50 Hz native, 3-24); growth fit +-1 s context."""
    a = int(np.searchsorted(g["tr"], tc - half)); b = int(np.searchsorted(g["tr"], tc + half))
    a2 = max(0, a - 100); b2 = min(len(g["tr"]), b + 100)
    res = {"a": a, "b": b, "t0": g["tr"][a], "t1": g["tr"][b - 1]}
    streams = [("bar", g["bar"][a:b], FS, 48), ("wire", g["rate_s"][a:b], FS, 48), ("cmd", g["cmd"][a:b], FS, 48)]
    if g["extras"] is not None:
        streams.append(("imu", g["extras"]["imu_lat"][a:b], FS, 48))
    ta = int(np.searchsorted(g["T_tr"], tc - half)); tb = int(np.searchsorted(g["T_tr"], tc + half))
    streams.append(("T", g["T"][ta:tb], FST, 24))
    res["lines"] = {}
    for name, x, fs, hi in streams:
        res["lines"][name] = lines_in(x, fs, 3.0, hi)
    # the two named lines, on the bar: 15-26 and 5-12 (the census's line_of), with growth fits on +-1 s context
    for key, lo, hi, bw in (("L20", 15.0, 26.0, 2.0), ("L7", 5.0, 12.0, 2.5)):
        f0, prom = CEN.line_of(g["bar"][a:b], FS, lo, hi)[:2]
        if np.isfinite(f0):
            env = GI.envelope(g["bar"][a2:b2], f0, FS, bw=bw)
            gu, du, gd, dd = GI.growth_fit(g["tr"][a2:b2], env)
            zeta = -gd / (2 * np.pi * f0) if np.isfinite(gd) and gd < 0 else np.nan
            res[key] = dict(f0=f0, prom=prom, amp=C20.bamp(g["bar"][a:b], max(f0 - bw, 1), f0 + bw, FS),
                            env_pk=float(np.nanmax(env)), t_pk=float(g["tr"][a2:b2][int(np.nanargmax(env))]),
                            gu=gu, du=du, gd=gd, dd=dd, zeta=zeta, Q=(1 / (2 * zeta) if np.isfinite(zeta) and zeta > 0 else np.nan),
                            wire_amp=C20.bamp(g["rate_s"][a:b], max(f0 - bw, 1), f0 + bw, FS),
                            T_amp=(C20.bamp(g["T"][ta:tb], max(f0 - bw, 1), min(f0 + bw, 24), FST) if f0 < 24 else np.nan),
                            cmd_amp=C20.bamp(g["cmd"][a:b], max(f0 - bw, 1), f0 + bw, FS),
                            imu_amp=(C20.bamp(g["extras"]["imu_lat"][a:b], max(f0 - bw, 1), f0 + bw, FS) if g["extras"] is not None else np.nan))
        else:
            res[key] = None
    # operating point
    res["op"] = dict(v=float(g["vego"][a:b].mean()), ang=(float(g["ang"][a]), float(g["ang"][b - 1])),
                     angabs=float(np.median(np.abs(g["ang"][a:b]))), rate50=float(np.percentile(g["rate"][a:b], 50)),
                     rate90=float(np.percentile(g["rate"][a:b], 90)), idx50=float(np.median(g["idx"][a:b])),
                     idx90=float(np.percentile(g["idx"][a:b], 90)), tq50=float(np.median(np.abs(g["bar"][a:b]))),
                     tq90=float(np.percentile(np.abs(g["bar"][a:b]), 90)), T50=float(np.median(np.abs(g["T100"][a:b]))),
                     cmd50=float(np.median(g["cmd"][a:b])), eng=float(g["eng"][a:b].mean()),
                     cap=float(np.mean(g["cap"][(g["cap_t"] >= tc - half) & (g["cap_t"] < tc + half)])) if np.any((g["cap_t"] >= tc - half) & (g["cap_t"] < tc + half)) else np.nan)
    # broadband split of the bar's band amplitudes in the core
    res["bands"] = {nm: C20.bamp(g["bar"][a:b], lo, hi, FS) for nm, lo, hi in BANDS}
    res["bands_wire"] = {nm: C20.bamp(g["rate_s"][a:b], lo, hi, FS) for nm, lo, hi in BANDS}
    return res


def fmt_lines(L, k=6):
    return "  ".join("%.2f Hz x%.0f (%.0f)" % (f, p, amp) for f, p, amp in L[:k]) if L else "(none >= x8)"


def print_core(res, label):
    op = res["op"]
    pr("    %s core t %.1f-%.1f s: v %.1f  ang %+.0f->%+.0f  |rate| p50/p90 %.1f/%.1f  idx p50/p90 %.0f/%.0f  |tq| p50/p90 %.0f/%.0f  |T| p50 %.0f  cmd p50 %+.0f  eng %.2f  capped-frame share %.3f" % (
        label, res["t0"], res["t1"], op["v"], op["ang"][0], op["ang"][1], op["rate50"], op["rate90"], op["idx50"], op["idx90"],
        op["tq50"], op["tq90"], op["T50"], op["cmd50"], op["eng"], op["cap"]))
    pr("      bar  band amps raw : " + "  ".join("%s %.0f" % (nm, res["bands"][nm]) for nm, _, _ in BANDS))
    pr("      wire band amps d/s : " + "  ".join("%s %.2f" % (nm, res["bands_wire"][nm]) for nm, _, _ in BANDS))
    for nm in ("bar", "wire", "cmd", "imu", "T"):
        if nm in res["lines"]:
            pr("      lines %-4s (f x prom (amp+-2Hz)) : %s" % (nm, fmt_lines(res["lines"][nm])))
    for key, nm in (("L20", "15-26 Hz line"), ("L7", "5-12 Hz line")):
        L = res[key]
        if L is None:
            pr("      %s: none" % nm); continue
        pr("      %-13s f0 %.2f x%.0f  bar amp %.0f  env pk %.0f @ t %.1f  rise %+.2f/s over %.2f s  decay %+.2f/s over %.2f s  zeta_eff %.3f  Q %.0f | wire %.2f d/s  T %.0f  cmd %.0f  imu %.3f" % (
            nm, L["f0"], L["prom"], L["amp"], L["env_pk"], L["t_pk"], L["gu"], L["du"], L["gd"], L["dd"], L["zeta"], L["Q"],
            L["wire_amp"], L["T_amp"], L["cmd_amp"], L["imu_amp"]))


# ======================================================================================================================
def env_of(x, lo, hi, fs):
    return np.abs(signal.hilbert(C20.bandpass(x, lo, hi, fs)))


def window_envelopes(g, a, b):
    """Hilbert envelopes of every band for bar / wire / cmd / imu (100 Hz) and T (50 Hz native) over frames [a,b)."""
    E = {}
    tr = g["tr"][a:b]
    for nm, x in (("bar", g["bar"][a:b]), ("wire", g["rate_s"][a:b]), ("cmd", g["cmd"][a:b])):
        E[nm] = {bn: env_of(x, lo, hi, FS) for bn, lo, hi in BANDS}
    if g["extras"] is not None:
        E["imu"] = {bn: env_of(g["extras"]["imu_lat"][a:b], lo, hi, FS) for bn, lo, hi in BANDS}
    ta = int(np.searchsorted(g["T_tr"], tr[0])); tb = int(np.searchsorted(g["T_tr"], tr[-1]))
    E["T"] = {bn: env_of(g["T"][ta:tb], lo, min(hi, 24), FST) for bn, lo, hi in BANDS if lo < 24}
    E["T_t"] = g["T_tr"][ta:tb]
    E["t"] = tr
    return E


def peak_before(t, env, tm, edge=0.5):
    m = (t < tm) & (t > t[0] + edge)
    if not m.any():
        return np.nan, np.nan
    j = np.flatnonzero(m)[int(np.nanargmax(env[m]))]
    return float(env[j]), float(t[j])


# ======================================================================================================================
def analyse_mark(g, tag, tm, seg, tagline):
    pr("\n" + "=" * 172)
    pr("%s -- BOOKMARK at route t %.2f s (segment %d)  window [%.1f, %.1f]" % (tagline, tm, seg, tm - PRE, tm + POST))
    pr("=" * 172)
    a = int(np.searchsorted(g["tr"], tm - PRE)); b = int(np.searchsorted(g["tr"], tm + POST))
    ex = g["extras"]

    # ---- 1. context at 0.1 s
    pr("\n  1. CONTEXT at 0.1 s  (cap = capped 0xE4 frames in the 0.1 s / frames; eng = lateral engaged; prs = steeringPressed; brk; bl = blinker L/R; lc = laneChange; env columns = bar Hilbert envelopes raw, T env raw, imu m/s2)")
    Ew = window_envelopes(g, a, b)
    hdr = "   %7s %5s %6s %6s %6s %3s %6s %5s %3s %3s %3s %2s %2s | %6s %6s %6s %6s %6s | %6s %6s" % (
        "t", "v", "ang", "rate", "bar", "hnd", "cmd", "cap", "eng", "prs", "brk", "bl", "lc", "b5-12", "b18-22", "b25-35", "b35-48", "T18-22", "imu", "b4.5")
    pr(hdr)
    Tenv = np.interp(g["tr"][a:b], Ew["T_t"], Ew["T"]["18-22"]) if len(Ew["T_t"]) else np.full(b - a, np.nan)
    for s in range(a, b, 10):
        e = min(s + 10, b)
        t0, t1 = g["tr"][s], g["tr"][e - 1]
        cm = (g["cap_t"] >= t0) & (g["cap_t"] <= t1 + 0.005)
        k = s - a
        pr("   %7.1f %5.1f %6.0f %6.1f %6.0f %3s %6.0f %2d/%-2d %3d %3s %3s %s%s %2s | %6.0f %6.0f %6.0f %6.0f %6.0f | %6.2f %6.2f" % (
            t0, g["vego"][s], g["ang"][s], g["rate_s"][s], g["bar"][s], "on" if abs(g["bar"][s]) >= HANDS else "off",
            g["cmd"][s], int(g["cap"][cm].sum()), int(cm.sum()), int(g["eng"][s]),
            ("%d" % round(ex["cs_press"][s])) if ex else "-", ("%d" % round(ex["cs_brake"][s])) if ex else "-",
            ("L" if ex and ex["cs_lblink"][s] > 0.5 else "."), ("R" if ex and ex["cs_rblink"][s] > 0.5 else "."),
            ("%d" % round(ex["cs_lchg"][s])) if ex else "-",
            Ew["bar"]["5-12"][k], Ew["bar"]["18-22"][k], Ew["bar"]["25-35"][k], Ew["bar"]["35-48"][k], Tenv[k],
            (ex["imu_lat"][s] if ex else np.nan), g["bit5"][s]))

    # ---- 1b. edges
    pr("\n  1b. EDGES in the window (lateral engaged, steeringPressed, brake, blinkers, lane change):")
    def edges(x, name):
        d = np.diff(np.r_[x[a], np.round(x[a:b])])
        for j in np.flatnonzero(d != 0):
            pr("     t %7.2f  %s %s" % (g["tr"][a + j], name, "ON" if d[j] > 0 else "off"))
    edges(g["eng"].astype(float), "lateral-engaged")
    if ex:
        edges(ex["cs_press"], "steeringPressed"); edges(ex["cs_brake"], "brake")
        edges(ex["cs_lblink"], "blinker-L"); edges(ex["cs_rblink"], "blinker-R"); edges(ex["cs_lchg"], "laneChange")

    # ---- 2. census episodes in the window
    pr("\n  2. CENSUS RECIPE over the window (2 s / 0.5 s step; present = 15-26 Hz prom >= 8 AND bar 18-22 >= 40; episode >= 0.5 s):")
    Rw, eps = census(g, a, b)
    if Rw["n"]:
        pr("     windows %d, present %d (%.0f %%)" % (Rw["n"], Rw["pres"].sum(), 100 * Rw["pres"].mean()))
    pr("     %-10s %7s %6s %6s %6s %8s %6s %6s %6s %5s %5s %6s %5s %6s %5s %5s" % (
        "class", "t0", "t1", "dur", "f0", "env pk", "18-22", "6-10", "corr7", "rise", "decay", "v", "|ang|", "rate0", "idx0", "|tq|"))
    for e in eps:
        pr("     %-10s %7.2f %6.2f %6.2f %6.2f %8.0f %6.0f %6.0f %6.2f %+5.1f %+5.1f %6.1f %5.0f %6.1f %5.0f %6.0f  trans %s creep %s  (mark - t0 = %.1f s, mark - t1 = %.1f s)" % (
            e["cls"], e["t0"], e["t1"], e["dur"], e["f0"], e["env"], e["amp"], e["amp6"],
            e["corr7"] if np.isfinite(e["corr7"]) else -9, e["gu"] if np.isfinite(e["gu"]) else 0, e["gd"] if np.isfinite(e["gd"]) else 0,
            e["v"], abs(e["ang0"]), e["rate0"], e["idx0"], e["hands"], "Y" if e["trans"] else "n", "Y" if e["creep_onset"] else "n",
            tm - e["t0"], tm - e["t1"]))
    if not eps:
        pr("     (no census episode in the window at the V282 yardstick)")

    # ---- 3. band envelope peaks before the mark
    pr("\n  3. BAND ENVELOPE PEAKS before the mark (Hilbert, peak value @ time; mark - t in brackets):")
    for nm in ("bar", "wire", "cmd", "imu", "T"):
        if nm not in Ew:
            continue
        t_ = Ew["T_t"] if nm == "T" else Ew["t"]
        cells = []
        for bn, lo, hi in BANDS:
            if bn not in Ew[nm]:
                continue
            pk, tp = peak_before(t_, Ew[nm][bn], tm)
            cells.append("%s %6.1f @ %.1f [%4.1f]" % (bn, pk, tp, tm - tp) if nm in ("wire", "imu") else "%s %6.0f @ %.1f [%4.1f]" % (bn, pk, tp, tm - tp))
        pr("     %-4s " % nm + " | ".join(cells))

    # ---- 4. the two cores
    pk7, t7 = peak_before(Ew["t"], Ew["bar"]["5-12"], tm)
    pk20, t20 = peak_before(Ew["t"], Ew["bar"]["18-22"], tm)
    pk30, t30 = peak_before(Ew["t"], Ew["bar"]["25-35"], tm)
    pr("\n  4. CORES (2 s around the bar envelope peak before the mark):")
    cores = {"7": core_anatomy(g, t7), "20": core_anatomy(g, t20)}
    print_core(cores["7"], "5-12 Hz-peak")
    print_core(cores["20"], "18-22 Hz-peak")
    if pk30 > 0.5 * pk20:
        cores["30"] = core_anatomy(g, t30)
        print_core(cores["30"], "25-35 Hz-peak")

    # ---- 5. trigger anatomy at each census onset (and at the 20 Hz envelope rise if no episode)
    pr("\n  5. TRIGGER ANATOMY at episode onsets (0.5 s before onset; +-3 s for blinker / lane change; prior 3 s for engage edges):")
    onsets = [(e["t0"], e["cls"]) for e in eps]
    if not onsets:
        L = cores["20"]["L20"]
        if L is not None and np.isfinite(L["du"]):
            onsets = [(L["t_pk"] - L["du"], "20Hz-env-rise")]
    trig = []
    for t0, cls in onsets:
        i0 = int(np.searchsorted(g["tr"], t0))
        cm = (g["cap_t"] >= t0 - 0.5) & (g["cap_t"] < t0)
        ncap = int(g["cap"][cm].sum())
        capruns = C20.runs(g["cap"][cm], 1)
        maxrun = max([bb - aa for aa, bb in capruns], default=0)
        dang = g["ang"][i0] - g["ang"][max(0, i0 - 100)]
        d = dict(t0=t0, cls=cls, ncap=ncap, maxrun=maxrun, dang1s=dang, rate0=g["rate"][i0], ratemax1s=float(g["rate"][max(0, i0 - 100):i0 + 1].max()),
                 hands=float(np.median(np.abs(g["bar"][max(0, i0 - 50):i0 + 1]))), v=g["vego"][i0], idx=g["idx"][i0],
                 didx1s=g["idx"][i0] - g["idx"][max(0, i0 - 100)], ang0=g["ang"][i0],
                 eng_edge=bool(np.any(np.diff(g["eng"][max(0, i0 - 300):i0 + 1].astype(int)) != 0)),
                 blink=(bool(np.any(ex["cs_lblink"][max(0, i0 - 300):i0 + 300] > 0.5) or np.any(ex["cs_rblink"][max(0, i0 - 300):i0 + 300] > 0.5)) if ex else None),
                 lchg=(bool(np.any(ex["cs_lchg"][max(0, i0 - 300):i0 + 300] > 0.5)) if ex else None),
                 brake=(bool(np.any(ex["cs_brake"][max(0, i0 - 100):i0 + 1] > 0.5)) if ex else None),
                 press=(bool(np.any(ex["cs_press"][max(0, i0 - 50):i0 + 1] > 0.5)) if ex else None))
        trig.append(d)
        pr("     onset t %.2f (%s): capped frames in prior 0.5 s = %d/50 (longest run %d)  dangle(1 s) %+.0f deg  |rate| at onset %.1f, max prior 1 s %.1f deg/s  hands |tq| %.0f (%s)  v %.1f  idx %.0f (didx 1 s %+.0f)  ang %+.0f  engage-edge<3s %s  blinker+-3s %s  laneChange+-3s %s  brake<1s %s  pressed %s" % (
            t0, cls, ncap, maxrun, dang, d["rate0"], d["ratemax1s"], d["hands"], "on" if d["hands"] >= HANDS else "off", d["v"], d["idx"], d["didx1s"], d["ang0"],
            d["eng_edge"], d["blink"], d["lchg"], d["brake"], d["press"]))
    return dict(tm=tm, seg=seg, a=a, b=b, eps=eps, cores=cores, Ew=Ew, trig=trig, pk=dict(pk7=pk7, t7=t7, pk20=pk20, t20=t20, pk30=pk30, t30=t30))


# ======================================================================================================================
def fig_mark(g, tag, M, fn):
    a, b, tm = M["a"], M["b"], M["tm"]
    tr = g["tr"][a:b]
    panels = [("driver torque (bar, raw)", g["bar"][a:b], FS, "bar"), ("wheel rate (deg/s)", g["rate_s"][a:b], FS, "wire"),
              ("0xE4 command (raw)", g["cmd"][a:b], FS, "cmd")]
    if g["extras"] is not None:
        panels.append(("IMU lateral (m/s2)", g["extras"]["imu_lat"][a:b], FS, "imu"))
    ta = int(np.searchsorted(g["T_tr"], tr[0])); tb = int(np.searchsorted(g["T_tr"], tr[-1]))
    panels.append(("0x1AB torque tap T (raw, 50 Hz)", g["T"][ta:tb], FST, "T"))
    n = len(panels)
    fig, ax = plt.subplots(n + 1, 1, figsize=(13, 2.2 * (n + 1)), sharex=True, constrained_layout=True)
    for i, (title, x, fs, key) in enumerate(panels):
        nper = int(1.28 * fs)
        f, tt, S = signal.spectrogram(x - np.mean(x), fs=fs, nperseg=nper, noverlap=nper - int(0.1 * fs), nfft=8 * nper, window="hann", mode="psd")
        tt = tt + (tr[0] if key != "T" else g["T_tr"][ta])
        m = (f >= 3) & (f <= (48 if fs > 60 else 24))
        Sd = 10 * np.log10(S[m] + 1e-12)
        vmax = np.percentile(Sd, 99.5); vmin = vmax - 45
        ax[i].pcolormesh(tt, f[m], Sd, shading="nearest", cmap="Blues", vmin=vmin, vmax=vmax, rasterized=True)
        ax[i].axvline(tm, color="#222", lw=1.2, ls="--")
        for e in M["eps"]:
            ax[i].axvspan(e["t0"], e["t1"], color="#d95f02", alpha=0.12, lw=0)
        ax[i].axhline(20, color="#888", lw=0.5, ls=":"); ax[i].axhline(7, color="#888", lw=0.5, ls=":")
        ax[i].set_ylabel("Hz"); ax[i].set_title(title, loc="left", fontsize=9)
    Ew = M["Ew"]
    axl = ax[-1]
    axl.plot(Ew["t"], Ew["bar"]["5-12"], color="#7570b3", lw=1.2, label="bar 5-12 Hz")
    axl.plot(Ew["t"], Ew["bar"]["18-22"], color=COL["bar"], lw=1.6, label="bar 18-22 Hz")
    axl.plot(Ew["t"], Ew["bar"]["25-35"], color="#e7298a", lw=1.0, label="bar 25-35 Hz")
    axl.plot(Ew["t"], Ew["bar"]["35-48"], color="#a6761d", lw=0.8, label="bar 35-48 Hz")
    axl.axhline(40, color="#888", lw=0.5, ls=":")
    axl.axvline(tm, color="#222", lw=1.2, ls="--")
    axl.set_ylabel("env raw"); axl.set_xlabel("route t (s)"); axl.legend(ncol=4, fontsize=8, frameon=False)
    axl.set_title("bar Hilbert band envelopes (dotted = 40 raw presence floor; dashed = bookmark; shaded = census episodes)", loc="left", fontsize=9)
    fig.suptitle("%s -- bookmark at t %.2f s (seg %d): spectrograms 3-48 Hz (T: 3-24 Hz), dB, 1.28 s window" % (tag, tm, M["seg"]), fontsize=10)
    fig.savefig(fn, dpi=110)
    plt.close(fig)


def fig_compare(marks_all, fn):
    """one figure: bar 18-22 and 5-12 envelopes vs (t - mark) for every bookmark, V288 vs V282."""
    fig, ax = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True, constrained_layout=True)
    styles = {"r5e_v288": ("-", COL["bar"]), "r39": ("--", COL["wire"])}
    for tag, Ms in marks_all.items():
        ls, c = styles[tag]
        for k, M in enumerate(Ms):
            t = M["Ew"]["t"] - M["tm"]
            al = 0.45 + 0.55 * (k / max(1, len(Ms) - 1))
            ax[0].plot(t, M["Ew"]["bar"]["18-22"], ls=ls, color=c, lw=1.3, alpha=al, label="%s mark %d (t %.0f)" % (tag, k + 1, M["tm"]))
            ax[1].plot(t, M["Ew"]["bar"]["5-12"], ls=ls, color=c, lw=1.3, alpha=al, label="%s mark %d" % (tag, k + 1))
    ax[0].axhline(40, color="#888", lw=0.5, ls=":")
    ax[0].set_ylabel("bar 18-22 Hz env (raw)"); ax[1].set_ylabel("bar 5-12 Hz env (raw)"); ax[1].set_xlabel("t - bookmark (s)")
    ax[0].legend(fontsize=8, ncol=3, frameon=False)
    ax[0].set_title("driver-torque band envelopes around every bookmark: V288 r5e (solid) vs V282 r39 (dashed)", loc="left", fontsize=10)
    fig.savefig(fn, dpi=110)
    plt.close(fig)


# ======================================================================================================================
def route_census(g, tag, label):
    Rw, eps = census(g, 0, len(g["tr"]))
    R = Rw["R"]; pres = Rw["pres"]
    engs = g["eng"].sum() / FS
    pr("  %-9s %-28s engaged %6.0f s | windows %5d present %4d (%4.1f %%) f %.2f+-%.2f  amp p50/p90/max %3.0f/%3.0f/%3.0f | episodes %3d (%.1f /100 s): BURST %d SUSTAINED %d RIDE-ALONG %d" % (
        tag, label, engs, Rw["n"], pres.sum(), 100 * pres.mean(),
        R["f0"][pres].mean() if pres.any() else np.nan, R["f0"][pres].std() if pres.any() else np.nan,
        *np.percentile(R["amp"], (50, 90)), R["amp"].max(), len(eps), 100 * len(eps) / engs,
        sum(e["cls"] == "BURST" for e in eps), sum(e["cls"] == "SUSTAINED" for e in eps), sum(e["cls"] == "RIDE-ALONG" for e in eps)))
    sel = R["creep"] & R["hoff"]
    if sel.sum() >= 5:
        pr("  %-9s creep 1-3 m/s hands-off: n %d present %d (%.0f %%) amp p50/p90/max %.0f/%.0f/%.0f" % (
            tag, sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(), np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max()))
    if eps:
        env = np.array([e["env"] for e in eps]); dur = np.array([e["dur"] for e in eps]); f0 = np.array([e["f0"] for e in eps])
        pr("  %-9s episode env pk p50/p90/max %.0f/%.0f/%.0f  dur p50/p90/max %.1f/%.1f/%.1f  f0 p10/p50/p90 %.1f/%.1f/%.1f  onset idx p50 %.0f  rate0 p50 %.1f  |ang0| p50 %.0f  v p50 %.1f  hands-on share %.2f" % (
            tag, *np.percentile(env, (50, 90)), env.max(), *np.percentile(dur, (50, 90)), dur.max(), *np.percentile(f0, (10, 50, 90)),
            np.median([e["idx0"] for e in eps]), np.median([e["rate0"] for e in eps]), np.median([abs(e["ang0"]) for e in eps]),
            np.median([e["v"] for e in eps]), np.mean([e["hands"] >= HANDS for e in eps])))
        # capped-frame enrichment at onset, the census §6b predicate on the cmd side only (|dcmd| >= 122 within +-0.5 s)
        near = []
        for e in eps:
            cm = (g["cap_t"] >= e["t0"] - 0.5) & (g["cap_t"] <= e["t0"] + 0.5)
            near.append(bool(g["cap"][cm].any()))
        # baseline: one draw per engaged second
        base = []
        for aa, bb in C20.runs(g["eng"], 100):
            for s in range(aa, bb, 100):
                t0 = g["tr"][s]
                cm = (g["cap_t"] >= t0 - 0.5) & (g["cap_t"] <= t0 + 0.5)
                base.append(bool(g["cap"][cm].any()))
        pr("  %-9s onsets near a capped 0xE4 frame (+-0.5 s): %.2f (n %d) vs baseline %.3f (n %d) -> enrichment %.2fx" % (
            tag, np.mean(near), len(near), np.mean(base), len(base), np.mean(near) / max(np.mean(base), 1e-9)))
    return Rw, eps


def cave_sanity(g, tag):
    m = g["eng"] > 0.5
    pr("  %-9s engaged %.0f s: b4 duty bit3 %.3f bit4 %.3f bit5 %.3f bit6 %.3f bit7 %.3f" % (
        tag, m.sum() / FS, *[g["bit%d" % k][m].mean() for k in (3, 4, 5, 6, 7)]))
    if tag == "r5e_v288":
        # bit 5 = sign(y), y = filtered sp; sp = -4*cmd clipped, so sign(sp) = -sign(cmd).  agreement and best lag vs the raw sign
        s_raw = np.sign(-np.round(g["cmd"]))
        sel = m & (s_raw != 0)
        b5 = np.where(g["bit5"] > 0.5, 1.0, -1.0)
        for lab, s in (("-sign(cmd)", s_raw), ("+sign(cmd)", -s_raw)):
            agree = np.mean(b5[sel] == s[sel])
            pr("  %-9s bit5 agreement with %s: %.3f" % (tag, lab, agree))
        # lag: shift bit5 earlier by k frames and re-measure agreement with -sign(cmd)
        s_use = s_raw if np.mean(b5[sel] == s_raw[sel]) >= 0.5 else -s_raw
        best = []
        for k in range(-5, 6):
            b = np.roll(b5, -k)
            best.append((np.mean(b[sel] == s_use[sel]), k))
        best.sort(reverse=True)
        pr("  %-9s bit5 vs the better-matching sign convention: best agreement %.3f at lag %+d frames (10 ms/frame; the filter's group delay is 15 ms -> expect +1..+2)" % (tag, best[0][0], best[0][1]))
        # zero crossings: median delay from sign(sp_raw) flip to bit5 flip, engaged only
        zr = np.flatnonzero(np.diff(s_use) != 0)
        zb = np.flatnonzero(np.diff(b5) != 0)
        lags = []
        for z in zr:
            if not m[z]:
                continue
            j = np.searchsorted(zb, z)
            if j < len(zb) and zb[j] - z <= 30:
                lags.append(zb[j] - z)
        if lags:
            pr("  %-9s sign flips: raw setpoint %d engaged; bit5 follows within 0.3 s for %d; delay p50/p90 %.0f/%.0f frames" % (
                tag, len([z for z in zr if m[z]]), len(lags), np.percentile(lags, 50), np.percentile(lags, 90)))


# ======================================================================================================================
# AUDIO -- the comma device microphone (rawAudioData, 20 blocks/s) around each bookmark.  Independent of the EPS and of
# CAN timing.  PASS A: direct sub-100 Hz content (NFFT 16384 -> 0.98 Hz bins).  PASS B: amplitude modulation of the
# cabin's broadband noise (carriers 300-1000 / 1000-3000 / 3000-6000 Hz -> Hilbert envelope -> 200 Hz LP -> 500 Hz),
# the physical signature a rough mechanism radiates (extract_audio_grind.py's argument).  Coherence env<->bar at the line.
# ======================================================================================================================
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
ROUTE_R5E = "75604b0a432fdc89_0000005e--03a9714d78"
CARRIERS = [(300, 1000), (1000, 3000), (3000, 6000)]
PCM_CACHE = os.path.join(SCR, "v288_marks_r5e_pcm.npz")


def load_pcm(segs, t0_mono):
    if os.path.exists(PCM_CACHE):
        Z = np.load(PCM_CACHE, allow_pickle=True)
        return {int(k): (Z["x_%d" % k], Z["t_%d" % k]) for k in Z["segs"]}, int(Z["sr"])
    sys.path.insert(0, os.path.join(KIT, "rlog-tools", "lib"))
    import rlog_parse
    out, sr = {}, None
    for seg in segs:
        blocks, bt = [], []
        for evt in rlog_parse.read_messages(os.path.join(RLOGS, "%s--%d--rlog.zst" % (ROUTE_R5E, seg))):
            try:
                if evt.which() != "rawAudioData":
                    continue
            except Exception:
                continue
            sr = int(evt.rawAudioData.sampleRate) or sr
            blocks.append(np.frombuffer(bytes(evt.rawAudioData.data), dtype="<i2").astype(np.float64))
            bt.append(evt.logMonoTime * 1e-9 - t0_mono)
        x = np.concatenate(blocks)
        t = np.concatenate([tb + np.arange(len(b)) / sr for tb, b in zip(bt, blocks)])
        out[seg] = (x - x.mean(), t)
        print("  audio seg %d: %d blocks, %d samples, sr %d, t %.1f-%.1f" % (seg, len(blocks), len(x), sr, t[0], t[-1]), flush=True)
    np.savez_compressed(PCM_CACHE, segs=np.array(list(out)), sr=sr, **{"x_%d" % k: v[0] for k, v in out.items()}, **{"t_%d" % k: v[1] for k, v in out.items()})
    return out, sr


def audio_stage(g, Ms):
    pr("\n" + "=" * 172)
    pr("AUDIO (comma device microphone, rawAudioData) around each V288 bookmark -- an instrument independent of the EPS")
    pr("=" * 172)
    pcm, sr = load_pcm(sorted({M["seg"] for M in Ms} | {M["seg"] - 1 for M in Ms}), g["t"][0])
    # stitch: one continuous stream per mark from seg-1 + seg (the -20 s reach crosses the segment boundary)
    pr("  sample rate %d Hz; PASS A = direct 3-100 Hz (0.98 Hz bins, 1.02 s frames); PASS B = AM envelope of %s Hz carriers at 500 Hz" % (sr, CARRIERS))
    NF = 16384
    for k, M in enumerate(Ms):
        x = np.concatenate([pcm[M["seg"] - 1][0], pcm[M["seg"]][0]]); t = np.concatenate([pcm[M["seg"] - 1][1], pcm[M["seg"]][1]])
        tm = M["tm"]
        sel = (t >= tm - PRE) & (t < tm + POST)
        xw, tw = x[sel], t[sel]
        if len(xw) < NF:
            pr("  mark %d: no audio in the window" % (k + 1)); continue
        # PASS A works on a 500 Hz decimate (anti-aliased at 200 Hz): the sub-100 Hz content is all we read directly
        lpA = signal.butter(6, 200, btype="low", fs=sr, output="sos")
        xa = signal.sosfiltfilt(lpA, xw)[::sr // 500]; ta = tw[::sr // 500]
        # PASS B envelopes at 500 Hz
        dec = sr // 500
        lp = signal.butter(4, 200, btype="low", fs=sr, output="sos")
        env = {}
        for lo, hi in CARRIERS:
            sos = signal.butter(4, (lo, hi), btype="bandpass", fs=sr, output="sos")
            a = np.abs(signal.hilbert(signal.sosfiltfilt(sos, xw)))
            env[(lo, hi)] = signal.sosfiltfilt(lp, a)[::dec]
        te = tw[::dec]
        pr("\n  mark %d (t %.2f, seg %d): audio window %.1f-%.1f s, rms %.0f" % (k + 1, tm, M["seg"], tw[0], tw[-1], xw.std()))
        for lab, key in (("5-12 Hz-peak core", "7"), ("18-22 Hz-peak core", "20")):
            c = M["cores"][key]
            m = (ta >= c["t0"]) & (ta < c["t1"] + 0.01)
            LA = lines_in(xa[m], 500.0, 3.0, 100.0, prom_min=6.0, nfft=1 << 13)
            pr("    %s t %.1f-%.1f:  PASS A direct lines 3-100 Hz: %s" % (lab, c["t0"], c["t1"], fmt_lines(LA, 8)))
            me = (te >= c["t0"]) & (te < c["t1"] + 0.01)
            for key2, e in env.items():
                LB = lines_in(e[me], 500.0, 3.0, 60.0, prom_min=6.0, nfft=1 << 13)
                pr("      PASS B AM env %4d-%4d Hz: lines 3-60 Hz: %s | env band amps 5-12 %.3g  18-22 %.3g  25-35 %.3g (rel. to env mean %.3g)" % (
                    key2[0], key2[1], fmt_lines(LB, 6), C20.bamp(e[me], 5, 12, 500.0), C20.bamp(e[me], 18, 22, 500.0), C20.bamp(e[me], 25, 35, 500.0), e[me].mean()))
        # coherence env <-> bar over the whole window, at the two named lines
        i0, i1 = M["a"], M["b"]
        bar = g["bar"][i0:i1]; tb = g["tr"][i0:i1]
        for key2, e in env.items():
            e100 = np.interp(tb, te, e)
            f, C = signal.coherence(bar - bar.mean(), e100 - e100.mean(), fs=FS, nperseg=256, noverlap=192)
            L20 = M["cores"]["20"]["L20"]; L7 = M["cores"]["7"]["L7"]
            c20 = float(np.interp(L20["f0"], f, C)) if L20 else np.nan
            c7 = float(np.interp(L7["f0"], f, C)) if L7 else np.nan
            pr("    coherence bar <-> AM env %4d-%4d Hz over the 23 s window: at the 15-26 Hz line %.2f, at the 5-12 Hz line %.2f (null level ~ 1/(n seg) = %.2f)" % (
                key2[0], key2[1], c20, c7, 1.0 / max(1, (len(bar) - 192) // 64)))
        # figure: PASS A spectrogram 3-100 Hz, PASS B (1-3 kHz) envelope spectrogram 3-60 Hz, bar spectrogram for reference
        fig, ax = plt.subplots(3, 1, figsize=(13, 7.5), sharex=True, constrained_layout=True)
        f, tt, S = signal.spectrogram(xw, fs=sr, nperseg=NF, noverlap=NF - sr // 10, nfft=NF, window="hann", mode="psd")
        mm = (f >= 3) & (f <= 100); Sd = 10 * np.log10(S[mm] + 1e-12); vmax = np.percentile(Sd, 99.5)
        ax[0].pcolormesh(tt + tw[0], f[mm], Sd, shading="nearest", cmap="Blues", vmin=vmax - 40, vmax=vmax, rasterized=True)
        ax[0].set_title("PASS A: microphone direct spectrogram 3-100 Hz (dB)", loc="left", fontsize=9); ax[0].set_ylabel("Hz")
        e = env[(1000, 3000)]
        nper = 640
        f2, t2, S2 = signal.spectrogram(e - e.mean(), fs=500.0, nperseg=nper, noverlap=nper - 50, nfft=4 * nper, window="hann", mode="psd")
        m2 = (f2 >= 3) & (f2 <= 60); S2d = 10 * np.log10(S2[m2] + 1e-12); v2 = np.percentile(S2d, 99.5)
        ax[1].pcolormesh(t2 + te[0], f2[m2], S2d, shading="nearest", cmap="Blues", vmin=v2 - 40, vmax=v2, rasterized=True)
        ax[1].set_title("PASS B: AM envelope of the 1-3 kHz cabin noise, spectrogram 3-60 Hz (dB)", loc="left", fontsize=9); ax[1].set_ylabel("Hz")
        nper = 128
        f3, t3, S3 = signal.spectrogram(bar - bar.mean(), fs=FS, nperseg=nper, noverlap=nper - 10, nfft=8 * nper, window="hann", mode="psd")
        m3 = (f3 >= 3) & (f3 <= 48); S3d = 10 * np.log10(S3[m3] + 1e-12); v3 = np.percentile(S3d, 99.5)
        ax[2].pcolormesh(t3 + tb[0], f3[m3], S3d, shading="nearest", cmap="Blues", vmin=v3 - 45, vmax=v3, rasterized=True)
        ax[2].set_title("reference: driver torque (bar) spectrogram 3-48 Hz (dB)", loc="left", fontsize=9); ax[2].set_ylabel("Hz"); ax[2].set_xlabel("route t (s)")
        for a_ in ax:
            a_.axvline(tm, color="#222", lw=1.2, ls="--"); a_.axhline(20, color="#888", lw=0.5, ls=":"); a_.axhline(7, color="#888", lw=0.5, ls=":")
        fig.suptitle("r5e_v288 mark %d (t %.2f s): microphone vs driver torque" % (k + 1, tm), fontsize=10)
        fig.savefig(os.path.join(SCR, "v288_marks_r5e_audio_m%d.png" % (k + 1)), dpi=110)
        plt.close(fig)


# ======================================================================================================================
def main():
    os.makedirs(SCR, exist_ok=True)
    cells = {k: GI.read_cells(p) for k, p in IMG.items()}
    pr("=" * 172)
    pr("V288 rev 2 -- THE THREE BOOKMARKED GRINDING EPISODES on r5e_v288 (75604b0a432fdc89_0000005e--03a9714d78, 2026-09-08), like for like vs r39's two V282 bookmarks")
    pr("=" * 172)
    G = {}
    for tag, (bld, lab) in ROUTES.items():
        G[tag] = load_route(tag, cells[bld])
        g = G[tag]
        pr("loaded %-9s %-28s %.1f s, %.1f s lateral engaged; 0xE4 frames %d, capped %d (%.2f %%)%s" % (
            tag, lab, g["tr"][-1], g["eng"].sum() / FS, len(g["cap"]), g["cap"].sum(), 100 * g["cap"].mean(),
            ("; imu_lat changes on %.0f %% of 100 Hz frames" % (100 * g["extras"]["imu_change_frac"]) if g["extras"] else "")))
    marks = {tag: marks_of(tag) for tag in ROUTES}
    pr("marks: " + "; ".join("%s %s" % (tag, ["%.2f (seg %d)" % m for m in ms]) for tag, ms in marks.items()))
    pr("NOTE r3a and r3c carry NO userBookmark events (their _marks.json lists are empty) -- r39's two marks are the only V282 bookmarked episodes.")

    # ---- per-mark anatomy
    marks_all = {}
    for tag, (bld, lab) in ROUTES.items():
        Ms = []
        for k, (tm, seg) in enumerate(marks[tag]):
            M = analyse_mark(G[tag], tag, tm, seg, "%s (%s) mark %d" % (tag, lab, k + 1))
            fig_mark(G[tag], tag, M, os.path.join(SCR, "v288_marks_r5e_%s_m%d.png" % (tag, k + 1)))
            Ms.append(M)
        marks_all[tag] = Ms
    fig_compare(marks_all, os.path.join(SCR, "v288_marks_r5e_compare.png"))
    try:
        audio_stage(G["r5e_v288"], marks_all["r5e_v288"])
    except Exception as ex:           # audio is a bonus instrument; never let it take the CAN read down with it
        pr("  AUDIO STAGE FAILED: %r" % (ex,))

    # ---- like-for-like table
    pr("\n" + "=" * 172)
    pr("LIKE FOR LIKE -- every bookmark, same window, same instruments (cores = 2 s around the bar band-envelope peak before the mark)")
    pr("=" * 172)
    pr("  %-14s %7s | %-52s | %-52s | %7s %6s %5s" % ("mark", "t", "15-26 Hz line: f0 xprom bar/wire/T/cmd/imu  rise decay zeta", "5-12 Hz line: f0 xprom bar/wire/T  rise decay zeta", "pk20/pk7", "cap", "class"))
    for tag, Ms in marks_all.items():
        for k, M in enumerate(Ms):
            L = M["cores"]["20"]["L20"]; S = M["cores"]["7"]["L7"]
            s20 = ("%.2f x%3.0f %4.0f/%4.1f/%4.0f/%4.0f/%5.3f %+5.2f %+5.2f %.3f" % (L["f0"], L["prom"], L["amp"], L["wire_amp"], L["T_amp"], L["cmd_amp"], L["imu_amp"], L["gu"], L["gd"], L["zeta"])) if L else "none"
            s7 = ("%.2f x%3.0f %4.0f/%4.1f/%4.0f %+5.2f %+5.2f %.3f" % (S["f0"], S["prom"], S["amp"], S["wire_amp"], S["T_amp"], S["gu"], S["gd"], S["zeta"])) if S else "none"
            cls = ",".join(sorted(set(e["cls"] for e in M["eps"]))) or "none"
            pr("  %-14s %7.1f | %-52s | %-52s | %3.0f/%3.0f %6.3f %s" % (
                "%s m%d" % (tag, k + 1), M["tm"], s20, s7, M["pk"]["pk20"], M["pk"]["pk7"], M["cores"]["20"]["op"]["cap"], cls))

    # ---- route-wide census on the V282 yardstick
    pr("\n" + "=" * 172)
    pr("ROUTE-WIDE CENSUS on the V282 yardstick (grind1_census_v282 recipe; r39 re-run here must reproduce 1742 windows / 364 present / 79 episodes)")
    pr("=" * 172)
    for tag, (bld, lab) in ROUTES.items():
        route_census(G[tag], tag, lab)
    pr("  V282 pooled (census doc): 130 episodes / 1957 s engaged = 6.6 per 100 s; 48 BURST / 51 SUSTAINED / 31 RIDE-ALONG; presence r39 21 %, r3a 8 %, r3c 12 %; onsets near a top-1 % tick 0.31 vs baseline 0.110 (2.80x).")

    # ---- outer-loop check: the pre-registered V288 risk was a slow wallow at 1-3 Hz; the marks show 3.4-3.7 Hz command swings at full lock
    pr("\n" + "=" * 172)
    pr("OUTER-LOOP CHECK -- 0xE4 command and steering-angle 2-5 Hz band amplitude, 2 s windows, engaged, by hands / speed stratum (V288 vs V282 r39)")
    pr("=" * 172)
    pr("  %-9s %-26s %6s | %-24s | %-24s | %-22s" % ("route", "stratum", "n win", "cmd 2-5 Hz p50/p90/max", "ang 2-5 Hz p50/p90/max", "cmd 1-2 Hz p50/p90"))
    for tag in ROUTES:
        g = G[tag]
        rows = []
        for aa, bb in C20.runs(g["eng"], W):
            for s_ in range(aa, bb - W + 1, STEP):
                e_ = s_ + W
                rows.append(dict(c25=C20.bamp(g["cmd"][s_:e_], 2, 5, FS), a25=C20.bamp(g["ang"][s_:e_], 2, 5, FS), c12=C20.bamp(g["cmd"][s_:e_], 1, 2, FS),
                                 hon=bool(np.median(np.abs(g["bar"][s_:e_])) >= HANDS), v=float(g["vego"][s_:e_].mean()),
                                 lock=bool(np.median(np.abs(g["ang"][s_:e_])) >= 150)))
        R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
        for lab, m in (("all engaged", np.ones(len(rows), bool)), ("hands off, v >= 8", (~R["hon"]) & (R["v"] >= 8)), ("hands off, v < 8", (~R["hon"]) & (R["v"] < 8)),
                       ("hands on, v < 8", R["hon"] & (R["v"] < 8)), ("hands on, |ang| >= 150", R["hon"] & R["lock"])):
            if m.sum() < 5:
                pr("  %-9s %-26s %6d   (too thin)" % (tag, lab, m.sum())); continue
            pr("  %-9s %-26s %6d | %6.0f/%6.0f/%6.0f | %6.1f/%6.1f/%6.1f | %6.0f/%6.0f" % (
                tag, lab, m.sum(), *np.percentile(R["c25"][m], (50, 90)), R["c25"][m].max(), *np.percentile(R["a25"][m], (50, 90)), R["a25"][m].max(),
                *np.percentile(R["c12"][m], (50, 90))))

    # ---- cave-bit sanity
    pr("\n" + "=" * 172)
    pr("CAVE-BIT SANITY (0x14A byte 4; on V288 b4.5 = sign(filtered setpoint y), b4.6 = |r24| >= |T|, b4.3/4/7 the three-sign rung; on V282 b4.5 was the |r24| >= |aggregator| comparator)")
    pr("=" * 172)
    for tag in ROUTES:
        cave_sanity(G[tag], tag)

    with open(os.path.join(SCR, "v288_marks_r5e.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "v288_marks_r5e.txt"))


if __name__ == "__main__":
    main()
