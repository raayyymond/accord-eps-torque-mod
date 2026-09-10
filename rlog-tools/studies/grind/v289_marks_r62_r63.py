# -*- coding: utf-8 -*-
"""studies/grind/v289_marks_r62_r63.py -- the operator's own grinding bookmarks on the first two V289 rev 1 drives
(routes 75604b0a432fdc89_00000062--1c7daa54e8 = tag r62_v289 and 75604b0a432fdc89_00000063--1d4b188022 = tag r63_v289,
2026-09-09), read with the SAME instruments as the V288 bookmark read (v288_marks_r5e.py, imported, not copied) plus the
V289-specific reads the brief asks for, and re-run like for like on the V288 marks (r5e_v288) and the V282 marks (r39).
Subagent `marks62`, 2026-09-09.  Analysis only: builds nothing, flashes nothing, sends nothing.

Per bookmark (or, if a route carries none, the 5 loudest 18-22 Hz census episodes, labelled NOT OPERATOR-MARKED):
  A. v288_marks_r5e.analyse_mark  -- the V288 anatomy verbatim: 0.1 s context table over [mark-20, mark+3], edges, the
     V282 census recipe over the window, band-envelope peaks, the 7 Hz and 20 Hz cores, trigger anatomy at onsets.
  B. THE 10 s BEFORE THE MARK (new): dominant 15-26 Hz line and its -3 dB width (periodogram, hann, 10 s, 0.012 Hz bins),
     Hilbert envelope at f0 +-2 Hz (same units as the V288 marks: raw driver-torque counts x 1.024), its peak, the
     contiguous time above half-peak, growth / decay time constants (log-envelope slopes -> tau = 1/|slope|), zeta_eff,
     and a SUSTAINED / DECAYING-BURST call.
  C. TRIGGER at the envelope rise: v, |angle|, angle rate, driver torque, 0xE4 level and slope, slew-cap hits, and a
     turn-entry / turn-exit / hold / straight class from the |angle| trend over the prior 1 s.
  D. V289's OWN INSTRUMENT in the window: b4.5 = sign(S - y) (the notched-out component) -> cross-spectrum with the 0x18F
     wheel rate at the line (coherence, phase, sign of Re); b4.7 = |S - y| >= |y| duty ENGAGED-ONLY (reads 1.000
     disengaged); b4.4 / b4.6 (V282's r24 comparators) duties; the 0x1AB torque tap T at the line (amplitude) and its
     phase vs the rate (T on its native 50 Hz instants; the rate band-limited 15-26 Hz first, then sampled at T's instants,
     so nothing above 30 Hz can alias onto the line).  On V288 / V282 routes b5 / b7 mean something else and are printed
     only as duties.
  E. REVERT SIGNATURES: band amplitude at 13-17 Hz and 22-24 Hz (bar, wheel rate, T) over the 10 s and the 2 s core,
     relative to 18-22 Hz, and any prominent line there.
Then the like-for-like table across every bookmark of every route, the route-wide census on the V282 yardstick, and a
build-identity read from the tap (b7 disengaged duty = 1.000 is the V289 signature; b5 engaged duty ~0.50).

Caches: analysis-2020accord/_scratch/cache/v280/{tag}{,_b4}.npz + {tag}_marks.json (the v280-format trio, written by the
route's extractor); corpus extras (IMU, brake, blinkers, lane change, steeringPressed) from _scratch/cache/{tag}/{tag}.npz
when present.  Cells (tapers for the demand index) read from the built images.
Run: python v289_marks_r62_r63.py [tags...]   -> _scratch/v289_marks_r62_r63.txt, _scratch/v289_marks_r62_r63_*.png
"""
import glob
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v288_marks_r5e as M288                    # noqa: E402  the V288 bookmark instruments, reused verbatim
import creep20_loop_id as C20                    # noqa: E402
import grind_incident_r35 as GI                  # noqa: E402
import grind1_census_v282 as CEN                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG      # noqa: E402

import matplotlib                                # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST = M288.FS, M288.FST
CACHE = C20.CACHE
CORPUS_ROOT = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache")
IMG = dict(M288.IMG)
IMG["V289"] = LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
ROUTES = {"r62_v289": ("V289", "V289 rev 1, 2026-09-09 (r62)"),
          "r63_v289": ("V289", "V289 rev 1, 2026-09-09 (r63)"),
          "r5e_v288": ("V288", "V288 rev 2, 2026-09-08"),
          "r39": ("V282", "V282 LAF 2.11, 2026-09-04")}
RID = {"r62_v289": "75604b0a432fdc89_00000062--1c7daa54e8", "r63_v289": "75604b0a432fdc89_00000063--1d4b188022",
       "r5e_v288": "75604b0a432fdc89_0000005e--03a9714d78", "r39": "(r39, V282)"}
V289_TAGS = {"r62_v289", "r63_v289"}
PRE10 = 10.0
HANDS = M288.HANDS
CAP = M288.CAP
OUT = M288.OUT                                   # share the output buffer with the reused printers
pr = M288.pr
EXTRA_KEYS = ("imu_lat", "imu_vert", "cs_brake", "cs_lblink", "cs_rblink", "cs_lchg", "cs_press", "cs_std", "cs_brakev", "cc_lat", "cs_eng")
COLR = {"r62_v289": "#1f5fbf", "r63_v289": "#1b9e77", "r5e_v288": "#d95f02", "r39": "#7570b3"}


# ======================================================================================================================
def load_route(tag, cells):
    g = M288.load_route(tag, cells)              # v280 trio + bits 3..7 gridded on the 0x18F frame axis
    if g["extras"] is None:
        cand = [p for p in glob.glob(os.path.join(CORPUS_ROOT, tag, "*.npz")) if os.path.basename(p) == tag + ".npz"]
        if cand:
            Cc = np.load(cand[0], allow_pickle=True)
            off = float(np.atleast_1d(Cc["t0_mono"])[0]) - g["t"][0]
            tc = Cc["t"] + off
            ex = {}
            missing = []
            for k in EXTRA_KEYS:
                if k in Cc.files:
                    ex[k] = np.interp(g["tr"], tc, Cc[k].astype(float))
                else:
                    ex[k] = np.zeros_like(g["tr"]); missing.append(k)
            ex["imu_change_frac"] = float(np.mean(np.diff(Cc["imu_lat"]) != 0)) if "imu_lat" in Cc.files else np.nan
            ex["missing"] = missing
            g["extras"] = ex
    return g


def marks_of(tag):
    p = os.path.join(CACHE, tag + "_marks.json")
    if not os.path.exists(p):
        return None
    Mj = json.load(open(p))
    return [(m["t_route"], m["seg"]) for m in Mj["marks"]]


# ======================================================================================================================
# B. the 10 s before the mark
# ======================================================================================================================
def line_and_width(x, fs, lo=15.0, hi=26.0, nfft=8192):
    """dominant line in [lo, hi] by prominence (the census's line_of) and the -3 dB width of its PSD peak."""
    f0, prom = CEN.line_of(x, fs, lo, hi)[:2]
    if not np.isfinite(f0):
        return f0, prom, np.nan, np.nan, np.nan
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    m = (f >= f0 - 1.0) & (f <= f0 + 1.0)
    j = np.flatnonzero(m)[int(np.argmax(P[m]))]
    half = P[j] / 2
    l = j
    while l > 0 and P[l - 1] >= half:
        l -= 1
    r = j
    while r < len(P) - 1 and P[r + 1] >= half:
        r += 1
    return float(f[j]), prom, float(f[r] - f[l]), float(f[l]), float(f[r])


def envelope_shape(g, a, b, f0, bw=2.0, pad=100):
    """Hilbert envelope at f0 over frames [a, b) (computed on a padded span), peak, contiguous half-peak duration,
    growth / decay slopes and time constants."""
    a2, b2 = max(0, a - pad), min(len(g["tr"]), b + pad)
    env_full = GI.envelope(g["bar"][a2:b2], f0, FS, bw=bw)
    env = env_full[a - a2:a - a2 + (b - a)]
    t = g["tr"][a:b]
    k = int(np.nanargmax(env)); pk = float(env[k])
    l = k
    while l > 0 and env[l - 1] >= 0.5 * pk:
        l -= 1
    r = k
    while r < len(env) - 1 and env[r + 1] >= 0.5 * pk:
        r += 1
    dur_half = (r - l + 1) / FS
    tot_half = float(np.sum(env >= 0.5 * pk)) / FS
    gu, du, gd, dd = GI.growth_fit(t, env)
    tau_up = 1.0 / gu if np.isfinite(gu) and gu > 0 else np.nan
    tau_dn = -1.0 / gd if np.isfinite(gd) and gd < 0 else np.nan
    zeta = -gd / (2 * np.pi * f0) if np.isfinite(gd) and gd < 0 else np.nan
    # is the envelope still above half-peak at the end of the window (i.e. at the mark)?
    at_end = bool(env[-1] >= 0.5 * pk)
    if dur_half >= 1.5 or (np.isfinite(gd) and gd > -1.0):
        cls = "SUSTAINED"
    elif dur_half < 1.5 and np.isfinite(gd) and gd <= -1.0:
        cls = "DECAYING BURST"
    else:
        cls = "RING"
    return dict(env=env, t=t, pk=pk, t_pk=float(t[k]), t_half0=float(t[l]), t_half1=float(t[r]), dur_half=dur_half, tot_half=tot_half,
                gu=gu, du=du, gd=gd, dd=dd, tau_up=tau_up, tau_dn=tau_dn, zeta=zeta, cls=cls, at_end=at_end,
                t_on=(float(t[k]) - du) if np.isfinite(du) else float(t[l]))


def trigger_at(g, t_on):
    """operating point and command activity around the envelope rise."""
    i0 = int(np.searchsorted(g["tr"], t_on)); i0 = min(max(i0, 1), len(g["tr"]) - 1)
    im = max(0, i0 - 100); ip = min(len(g["tr"]), i0 + 50)
    ang = g["ang"]
    dabs = abs(ang[i0]) - abs(ang[im])
    rate_on = float(g["rate"][i0]); rate_max = float(g["rate"][im:i0 + 1].max())
    if abs(ang[i0]) < 15 and rate_max < 10:
        turn = "STRAIGHT"
    elif dabs > 10:
        turn = "TURN-ENTRY"
    elif dabs < -10:
        turn = "TURN-EXIT"
    else:
        turn = "HOLD (mid-turn)" if abs(ang[i0]) >= 15 else "near-centre"
    cm = (g["cap_t"] >= t_on - 1.0) & (g["cap_t"] < t_on + 0.5)
    cmd_seg = g["cmd_e4"][cm]; dcmd = g["dcmd_e4"][cm]
    ex = g["extras"]
    d = dict(t_on=t_on, v=float(g["vego"][i0]), ang=float(ang[i0]), dabs1s=float(dabs), rate_on=rate_on, rate_max=rate_max,
             rate_s=float(g["rate_s"][i0]), tq=float(np.median(np.abs(g["bar"][max(0, i0 - 50):i0 + 1]))),
             tq_max=float(np.abs(g["bar"][im:ip]).max()),
             cmd=float(np.median(g["cmd"][max(0, i0 - 50):i0 + 1])), cmd_min=float(g["cmd"][im:ip].min()), cmd_max=float(g["cmd"][im:ip].max()),
             dcmd_max=float(np.abs(dcmd).max()) if dcmd.size else np.nan, dcmd_p50=float(np.median(np.abs(dcmd))) if dcmd.size else np.nan,
             ncap=int(g["cap"][cm].sum()), nfr=int(cm.sum()), turn=turn, idx=float(g["idx"][i0]),
             eng=float(g["eng"][im:i0 + 1].mean()),
             blink=(bool(np.any(ex["cs_lblink"][max(0, i0 - 300):i0 + 300] > 0.5) or np.any(ex["cs_rblink"][max(0, i0 - 300):i0 + 300] > 0.5)) if ex else None),
             lchg=(bool(np.any(ex["cs_lchg"][max(0, i0 - 300):i0 + 300] > 0.5)) if ex else None),
             brake=(bool(np.any(ex["cs_brake"][max(0, i0 - 100):i0 + 1] > 0.5)) if ex else None),
             press=(bool(np.any(ex["cs_press"][max(0, i0 - 50):i0 + 1] > 0.5)) if ex else None))
    d["hands"] = "on" if d["tq"] >= HANDS else "off"
    return d


# ======================================================================================================================
# D. V289's own instrument
# ======================================================================================================================
def xspec_at(x, y, fs, f0, nperseg):
    """coherence, phase (deg, y relative to x) and sign of Re(Pxy) at f0; nan if the span is too short."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < nperseg or not np.isfinite(f0):
        return np.nan, np.nan, np.nan
    x = x - x.mean(); y = y - y.mean()
    f, Pxy = signal.csd(x, y, fs=fs, nperseg=nperseg, noverlap=3 * nperseg // 4, nfft=4 * nperseg)
    _, Coh = signal.coherence(x, y, fs=fs, nperseg=nperseg, noverlap=3 * nperseg // 4, nfft=4 * nperseg)
    j = int(np.argmin(np.abs(f - f0)))
    return float(Coh[j]), float(np.degrees(np.angle(Pxy[j]))), float(np.sign(np.real(Pxy[j])))


def instrument_read(g, tag, a, b, f0, label):
    """bits and tap in frames [a, b) at the line f0."""
    m = g["eng"][a:b] > 0.5
    n_eng = int(m.sum())
    res = dict(n_eng=n_eng, f0=f0)
    for bit in (3, 4, 5, 6, 7):
        res["b%d" % bit] = float(g["bit%d" % bit][a:b][m].mean()) if n_eng else np.nan
    # b5 as +-1 vs the wheel rate and vs the bar
    s5 = 1.0 - 2.0 * g["bit5"][a:b]
    rate = g["rate_s"][a:b]
    nps = 256 if (b - a) >= 512 else 128
    res["c5r"], res["ph5r"], res["sg5r"] = xspec_at(s5, rate, FS, f0, nps)
    res["c5b"], res["ph5b"], res["sg5b"] = xspec_at(s5, g["bar"][a:b], FS, f0, nps)
    res["c5T"], res["ph5T"], _ = xspec_at(s5, g["T100"][a:b], FS, f0, nps)
    res["amp5"] = C20.bamp(s5, max(f0 - 2, 1), f0 + 2, FS) if np.isfinite(f0) else np.nan   # +-1 stream's band amplitude
    # the tap at the line, native 50 Hz, phase vs the band-limited rate sampled at T's instants
    ta = int(np.searchsorted(g["T_tr"], g["tr"][a])); tb = int(np.searchsorted(g["T_tr"], g["tr"][b - 1]))
    T = g["T"][ta:tb]
    if len(T) > 64 and np.isfinite(f0) and f0 < 24:
        res["T_amp"] = C20.bamp(T, max(f0 - 2, 1), min(f0 + 2, 24), FST)
        rate_bl = C20.bandpass(g["rate_s"], 15.0, 26.0, FS)
        rate50 = np.interp(g["T_tr"][ta:tb], g["tr"], rate_bl)
        bar_bl = C20.bandpass(g["bar"], 15.0, 26.0, FS)
        bar50 = np.interp(g["T_tr"][ta:tb], g["tr"], bar_bl)
        npsT = 128 if len(T) >= 256 else 64
        res["cTr"], res["phTr"], res["sgTr"] = xspec_at(T, rate50, FST, f0, npsT)
        res["cTb"], res["phTb"], _ = xspec_at(T, bar50, FST, f0, npsT)
    else:
        for k in ("T_amp", "cTr", "phTr", "sgTr", "cTb", "phTb"):
            res[k] = np.nan
    res["rate_amp"] = C20.bamp(rate, max(f0 - 2, 1), f0 + 2, FS) if np.isfinite(f0) else np.nan
    res["bar_amp"] = C20.bamp(g["bar"][a:b], max(f0 - 2, 1), f0 + 2, FS) if np.isfinite(f0) else np.nan
    res["label"] = label
    return res


def print_instrument(res, tag):
    v289 = tag in V289_TAGS
    pr("     %-12s engaged frames %4d | duties b3 %.3f b4 %.3f b5 %.3f b6 %.3f b7 %.3f%s" % (
        res["label"], res["n_eng"], res["b3"], res["b4"], res["b5"], res["b6"], res["b7"],
        "" if v289 else "   (V288/V282 bit meanings; b5/b7 are NOT the notch bits here)"))
    if v289:
        pr("       b4.5 = sign(S-y) vs 0x18F rate at %.2f Hz: coherence %.2f  phase(rate rel. sign) %+.0f deg  sign(Re) %+.0f | vs bar: coh %.2f phase %+.0f | vs T100: coh %.2f phase %+.0f | +-1 stream band amp %.3f" % (
            res["f0"], res["c5r"], res["ph5r"], res["sg5r"], res["c5b"], res["ph5b"], res["c5T"], res["ph5T"], res["amp5"]))
    pr("       0x1AB tap T at the line: amp %.0f raw (rate %.2f deg/s, bar %.0f raw) | T vs rate (50 Hz native): coh %.2f  phase(rate rel. T) %+.0f deg  sign(Re) %+.0f | T vs bar: coh %.2f phase %+.0f" % (
        res["T_amp"], res["rate_amp"], res["bar_amp"], res["cTr"], res["phTr"], res["sgTr"], res["cTb"], res["phTb"]))


# ======================================================================================================================
# E. revert signatures
# ======================================================================================================================
REV = [("13-17", 13, 17), ("18-22", 18, 22), ("22-24", 22, 24)]


def revert_read(g, a, b):
    out = {}
    for nm, x, fs in (("bar", g["bar"][a:b], FS), ("wire", g["rate_s"][a:b], FS)):
        out[nm] = {bn: C20.bamp(x, lo, hi, fs) for bn, lo, hi in REV}
    ta = int(np.searchsorted(g["T_tr"], g["tr"][a])); tb = int(np.searchsorted(g["T_tr"], g["tr"][b - 1]))
    T = g["T"][ta:tb]
    out["T"] = {bn: (C20.bamp(T, lo, min(hi, 24), FST) if len(T) > 64 else np.nan) for bn, lo, hi in REV}
    out["lines_lo"] = M288.lines_in(g["bar"][a:b], FS, 12.0, 17.5)
    out["lines_hi"] = M288.lines_in(g["bar"][a:b], FS, 21.8, 25.0)
    return out


def print_revert(R, label):
    def cell(nm):
        d = R[nm]
        r1 = d["13-17"] / d["18-22"] if d["18-22"] > 0 else np.nan
        r2 = d["22-24"] / d["18-22"] if d["18-22"] > 0 else np.nan
        fmt = "%.2f" if nm == "wire" else "%.0f"
        return ("%s: 13-17 " + fmt + "  18-22 " + fmt + "  22-24 " + fmt + "  (ratios %.2f / %.2f)") % (nm, d["13-17"], d["18-22"], d["22-24"], r1, r2)
    pr("     %-12s %s | %s | %s" % (label, cell("bar"), cell("wire"), cell("T")))
    pr("     %-12s bar lines 12-17.5 Hz: %s | 21.8-25 Hz: %s" % ("", M288.fmt_lines(R["lines_lo"], 3), M288.fmt_lines(R["lines_hi"], 3)))


# ======================================================================================================================
def analyse_v289(g, tag, tm, seg, k, operator_marked=True):
    tagline = "%s (%s) %s %d" % (tag, ROUTES[tag][1], "mark" if operator_marked else "LOUDEST-EPISODE (NOT operator-marked)", k + 1)
    M = M288.analyse_mark(g, tag, tm, seg, tagline)          # A. the V288 anatomy verbatim (sections 1-5)
    pr("\n  6. THE 10 s BEFORE THE MARK [%.1f, %.1f) -- the brief's per-mark read" % (tm - PRE10, tm))
    a = int(np.searchsorted(g["tr"], tm - PRE10)); b = int(np.searchsorted(g["tr"], tm))
    f0, prom, w3, fl, fr = line_and_width(g["bar"][a:b], FS)
    core = M["cores"]["20"]
    fc = core["L20"]["f0"] if core["L20"] else np.nan
    pr("     dominant 15-26 Hz line over the 10 s: %.2f Hz (prominence x%.0f), -3 dB width %.2f Hz [%.2f, %.2f] ; the 2 s core's line: %s" % (
        f0, prom, w3, fl, fr, ("%.2f Hz x%.0f" % (fc, core["L20"]["prom"])) if core["L20"] else "none"))
    f_use = f0 if np.isfinite(f0) else (fc if np.isfinite(fc) else 20.0)
    E = envelope_shape(g, a, b, f_use)
    pr("     envelope at %.2f +-2 Hz (bar, raw): PEAK %.0f @ t %.2f (mark - %.2f s) ; above half-peak %.2f s contiguous [%.2f, %.2f] (%.2f s total in the 10 s) ; still above half-peak at the mark: %s" % (
        f_use, E["pk"], E["t_pk"], tm - E["t_pk"], E["dur_half"], E["t_half0"], E["t_half1"], E["tot_half"], E["at_end"]))
    pr("     growth %+.2f /s over %.2f s (tau %.2f s) ; decay %+.2f /s over %.2f s (tau %.2f s) ; zeta_eff %.3f ; CALL: %s" % (
        E["gu"], E["du"], E["tau_up"], E["gd"], E["dd"], E["tau_dn"], E["zeta"], E["cls"]))
    # wire / T amplitude at the line in the loudest 2 s around the envelope peak
    ac = int(np.searchsorted(g["tr"], E["t_pk"] - 1.0)); bc = int(np.searchsorted(g["tr"], E["t_pk"] + 1.0))
    pr("     at the envelope peak (2 s): bar %.0f raw, wheel rate %.2f deg/s, 0xE4 cmd %.0f raw at the line" % (
        C20.bamp(g["bar"][ac:bc], f_use - 2, f_use + 2, FS), C20.bamp(g["rate_s"][ac:bc], f_use - 2, f_use + 2, FS), C20.bamp(g["cmd"][ac:bc], f_use - 2, f_use + 2, FS)))
    # C. trigger
    T = trigger_at(g, E["t_on"])
    pr("     TRIGGER at the envelope rise t %.2f: %s ; v %.1f m/s ; angle %+.0f deg (|ang| change over prior 1 s %+.0f) ; wheel rate %+.1f deg/s (|max| prior 1 s %.1f) ; driver |tq| %.0f raw (%s; max %.0f) ; idx %.0f ; engaged share prior 1 s %.2f" % (
        T["t_on"], T["turn"], T["v"], T["ang"], T["dabs1s"], T["rate_s"], T["rate_max"], T["tq"], T["hands"], T["tq_max"], T["idx"], T["eng"]))
    pr("       0xE4: level %+.0f raw (range %+.0f..%+.0f over -1..+0.5 s) ; |dcmd| per frame p50 %.0f, max %.0f ; SLEW-CAP hits %d of %d frames ; blinker+-3s %s ; laneChange %s ; brake<1s %s ; pressed %s" % (
        T["cmd"], T["cmd_min"], T["cmd_max"], T["dcmd_p50"], T["dcmd_max"], T["ncap"], T["nfr"], T["blink"], T["lchg"], T["brake"], T["press"]))
    # D. instrument
    pr("     V289 INSTRUMENT (bits on 0x14A byte 4; engaged-only duties):")
    I10 = instrument_read(g, tag, a, b, f_use, "10 s window")
    I2 = instrument_read(g, tag, ac, bc, f_use, "2 s peak core")
    print_instrument(I10, tag); print_instrument(I2, tag)
    # E. revert
    pr("     REVERT SIGNATURES (band amplitudes; ratios = band / 18-22):")
    R10 = revert_read(g, a, b); R2 = revert_read(g, ac, bc)
    print_revert(R10, "10 s window"); print_revert(R2, "2 s peak core")
    M.update(dict(f0_10=f0, prom_10=prom, w3=w3, E=E, T=T, I10=I10, I2=I2, R10=R10, R2=R2, f_use=f_use, operator_marked=operator_marked, k=k))
    return M


# ======================================================================================================================
def fig_compare(marks_all, fn):
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    for tag, Ms in marks_all.items():
        c = COLR.get(tag, "#666")
        ls = "-" if tag in V289_TAGS else "--"
        for k, M in enumerate(Ms):
            t = M["Ew"]["t"] - M["tm"]
            al = 0.45 + 0.55 * (k / max(1, len(Ms) - 1))
            ax[0].plot(t, M["Ew"]["bar"]["18-22"], ls=ls, color=c, lw=1.3, alpha=al, label="%s m%d (t %.0f)%s" % (tag, k + 1, M["tm"], "" if M["operator_marked"] else " *not marked*"))
            ax[1].plot(t, M["Ew"]["bar"]["5-12"], ls=ls, color=c, lw=1.3, alpha=al)
    ax[0].axhline(40, color="#888", lw=0.5, ls=":")
    ax[0].set_ylabel("bar 18-22 Hz env (raw)"); ax[1].set_ylabel("bar 5-12 Hz env (raw)"); ax[1].set_xlabel("t - bookmark (s)")
    ax[0].legend(fontsize=7, ncol=3, frameon=False)
    ax[0].set_title("driver-torque band envelopes around every bookmark: V289 r62/r63 (solid) vs V288 r5e / V282 r39 (dashed)", loc="left", fontsize=10)
    fig.savefig(fn, dpi=110); plt.close(fig)


def fig_mark10(g, tag, M, fn):
    """the 10 s read: bar band-passed at the line + envelope, wheel rate, cmd with capped frames, b5/b7, T."""
    tm = M["tm"]; E = M["E"]; f0 = M["f_use"]
    a = int(np.searchsorted(g["tr"], tm - PRE10)); b = int(np.searchsorted(g["tr"], tm + 2))
    tr = g["tr"][a:b]
    fig, ax = plt.subplots(5, 1, figsize=(12, 10), sharex=True, constrained_layout=True)
    bp = C20.bandpass(g["bar"][max(0, a - 100):b + 100], f0 - 2, f0 + 2, FS)[a - max(0, a - 100):][:b - a]
    ax[0].plot(tr, bp, color="#1f5fbf", lw=0.7, label="bar %.1f+-2 Hz" % f0)
    ax[0].plot(E["t"], E["env"], color="#d95f02", lw=1.5, label="envelope")
    ax[0].axhline(0.5 * E["pk"], color="#888", lw=0.6, ls=":"); ax[0].axvspan(E["t_half0"], E["t_half1"], color="#d95f02", alpha=0.1, lw=0)
    ax[0].legend(fontsize=8, frameon=False, ncol=2); ax[0].set_ylabel("raw"); ax[0].set_title("%s -- bookmark t %.2f (seg %d): the 10 s before" % (tag, tm, M["seg"]), loc="left", fontsize=10)
    ax[1].plot(tr, g["ang"][a:b], color="#333", lw=0.9, label="angle (deg)"); ax[1].set_ylabel("deg")
    ax1b = ax[1].twinx(); ax1b.plot(tr, g["rate_s"][a:b], color="#1b9e77", lw=0.6, label="wheel rate"); ax1b.set_ylabel("deg/s")
    ax[1].legend(fontsize=8, frameon=False, loc="upper left"); ax1b.legend(fontsize=8, frameon=False, loc="upper right")
    ax[2].plot(tr, g["cmd"][a:b], color="#66666f", lw=0.9, label="0xE4 cmd")
    cm = (g["cap_t"] >= tr[0]) & (g["cap_t"] <= tr[-1])
    tc = g["cap_t"][cm]; cc = g["cmd_e4"][cm]; kc = g["cap"][cm]
    ax[2].plot(tc[kc], cc[kc], ".", color="#e7298a", ms=4, label="slew-capped frame")
    ax[2].plot(tr, g["bar"][a:b], color="#1f5fbf", lw=0.5, alpha=0.7, label="driver torque (bar)")
    ax[2].legend(fontsize=8, frameon=False, ncol=3); ax[2].set_ylabel("raw")
    ax[3].step(tr, g["bit5"][a:b], where="post", color="#7570b3", lw=0.6, label="b4.5 sign(S-y)" if tag in V289_TAGS else "b4.5")
    ax[3].step(tr, g["bit7"][a:b] + 1.2, where="post", color="#a6761d", lw=0.6, label="b4.7 |S-y|>=|y| (+1.2)" if tag in V289_TAGS else "b4.7 (+1.2)")
    ax[3].step(tr, g["eng"][a:b] * 0.5 + 2.4, where="post", color="#1b9e77", lw=0.8, label="engaged (+2.4)")
    ax[3].legend(fontsize=8, frameon=False, ncol=3); ax[3].set_yticks([])
    ta = int(np.searchsorted(g["T_tr"], tr[0])); tb = int(np.searchsorted(g["T_tr"], tr[-1]))
    ax[4].plot(g["T_tr"][ta:tb], g["T"][ta:tb], color="#1b9e77", lw=0.7, label="0x1AB tap T (50 Hz)")
    ax[4].legend(fontsize=8, frameon=False); ax[4].set_ylabel("raw"); ax[4].set_xlabel("route t (s)")
    for a_ in ax:
        a_.axvline(tm, color="#222", lw=1.2, ls="--"); a_.axvline(E["t_pk"], color="#d95f02", lw=0.8, ls=":")
    fig.savefig(fn, dpi=110); plt.close(fig)


# ======================================================================================================================
def identity_from_tap(g, tag):
    m = g["eng"] > 0.5; d = ~m
    pr("  %-9s engaged %6.0f s | disengaged %6.0f s | b7 duty ENGAGED %.3f  DISENGAGED %.3f | b5 duty engaged %.3f disengaged %.3f | b3 %.3f b4 %.3f b6 %.3f (engaged)" % (
        tag, m.sum() / FS, d.sum() / FS, g["bit7"][m].mean(), g["bit7"][d].mean(), g["bit5"][m].mean(), g["bit5"][d].mean(),
        g["bit3"][m].mean(), g["bit4"][m].mean(), g["bit6"][m].mean()))


def seg_of(tag, t):
    p = os.path.join(CACHE, tag + "_marks.json")
    if not os.path.exists(p):
        return -1
    S = json.load(open(p)).get("segs", {})
    best = -1
    for k, v in S.items():
        if v["lo_can_route"] <= t:
            best = max(best, int(k))
    return best


def loudest_episodes(g, tag, n=5):
    Rw, eps = M288.census(g, 0, len(g["tr"]))
    eps = sorted(eps, key=lambda e: -e["env"])[:n]
    return [(e["t1"] + 0.3, seg_of(tag, e["t1"]), e) for e in eps]


# ======================================================================================================================
def main(tags):
    os.makedirs(SCR, exist_ok=True)
    cells = {k: GI.read_cells(p) for k, p in IMG.items() if os.path.exists(p)}
    pr("=" * 172)
    pr("V289 rev 1 -- THE OPERATOR'S GRINDING BOOKMARKS on r62_v289 / r63_v289 (2026-09-09), like for like vs the V288 marks (r5e_v288) and the V282 marks (r39)")
    pr("=" * 172)
    c289 = cells.get("V289"); c282 = cells.get("V282")
    if c289 is not None and c282 is not None:
        pr("cells read from the images: V289 fb pole %d/%d (V282 %d/%d) ; map Y %s ; Kp Y %s ; tapers/fades/map/Kp/Kd/clamps/gain %s" % (
            c289["fb_a"], c289["fb_b"], c282["fb_a"], c282["fb_b"], c289["map_Y"].astype(int).tolist(), c289["kp_Y"].astype(int).tolist(),
            "byte-identical V289 == V282" if all(np.array_equal(c289[k], c282[k]) for k in ("map_Y", "kp_Y", "kd_Y", "taperS", "taperO", "fadeA", "fadeB") if not isinstance(c289[k], tuple)) else "DIFFER (see above)"))
    G, marks = {}, {}
    for tag in tags:
        bld, lab = ROUTES[tag]
        if not os.path.exists(os.path.join(CACHE, tag + ".npz")):
            pr("!! %s: no v280 cache (%s.npz) -- skipped" % (tag, tag)); continue
        G[tag] = load_route(tag, cells[bld])
        g = G[tag]
        ms = marks_of(tag)
        marks[tag] = ms
        pr("loaded %-9s %-30s %.1f s, %.1f s lateral engaged; 0xE4 frames %d, capped %d (%.2f %%)%s%s" % (
            tag, lab, g["tr"][-1], g["eng"].sum() / FS, len(g["cap"]), g["cap"].sum(), 100 * g["cap"].mean(),
            ("; imu_lat changes on %.0f %% of frames" % (100 * g["extras"]["imu_change_frac"]) if g["extras"] else "; NO corpus extras (blinker/brake/laneChange/pressed unavailable)"),
            ("; corpus keys missing: %s" % g["extras"]["missing"] if g["extras"] and g["extras"].get("missing") else "")))
        pr("   bookmarks (userBookmark, v280 clock): %s" % (["%.2f (seg %d)" % m for m in ms] if ms else "NONE" if ms is not None else "no _marks.json"))

    # ---- per-mark anatomy
    marks_all = {}
    for tag in G:
        g = G[tag]
        Ms = []
        ms = marks[tag] or []
        if ms:
            for k, (tm, seg) in enumerate(ms):
                M = analyse_v289(g, tag, tm, seg, k, True)
                M288.fig_mark(g, tag, M, os.path.join(SCR, "v289_marks_%s_m%d.png" % (tag, k + 1)))
                fig_mark10(g, tag, M, os.path.join(SCR, "v289_marks_%s_m%d_10s.png" % (tag, k + 1)))
                Ms.append(M)
        if tag in V289_TAGS:
            n_extra = 5 if not ms else 3
            pr("\n" + "!" * 172)
            pr("%s: %s -- reading the %d loudest 18-22 Hz census episodes (V282 yardstick) outside +-15 s of any bookmark as CONTEXT. THESE ARE NOT OPERATOR-MARKED." % (
                tag, "NO operator bookmark" if not ms else "%d operator bookmark(s)" % len(ms), n_extra))
            pr("!" * 172)
            eps_far = [(tm, seg, e) for tm, seg, e in loudest_episodes(g, tag, n=40) if all(abs(e["t1"] - m[0]) > 15 for m in ms)][:n_extra]
            for k, (tm, seg, e) in enumerate(eps_far):
                pr("   episode %d: %s t %.2f-%.2f (%.1f s) f0 %.2f env pk %.0f  -> pseudo-mark at t %.2f" % (k + 1, e["cls"], e["t0"], e["t1"], e["dur"], e["f0"], e["env"], tm))
                M = analyse_v289(g, tag, tm, seg, k, False)
                M288.fig_mark(g, tag, M, os.path.join(SCR, "v289_marks_%s_e%d.png" % (tag, k + 1)))
                fig_mark10(g, tag, M, os.path.join(SCR, "v289_marks_%s_e%d_10s.png" % (tag, k + 1)))
                Ms.append(M)
        marks_all[tag] = Ms
    fig_compare(marks_all, os.path.join(SCR, "v289_marks_r62_r63_compare.png"))

    # ---- like-for-like tables
    pr("\n" + "=" * 172)
    pr("LIKE FOR LIKE (A) -- the 10 s before every bookmark: line, width, envelope, duration, time constants, call   [same code on every route]")
    pr("=" * 172)
    pr("  %-16s %7s %6s %5s %6s | %6s %6s %7s %7s | %6s %6s %6s %6s %6s | %-14s %5s %5s %6s" % (
        "mark", "t", "f0", "prom", "-3dB", "env pk", "mark-pk", "half s", "tot s", "rise/s", "tau_up", "decay", "tau_dn", "zeta", "call", "v", "cap", "turn"))
    for tag, Ms in marks_all.items():
        for M in Ms:
            E, T = M["E"], M["T"]
            pr("  %-16s %7.1f %6.2f %5.0f %6.2f | %6.0f %6.1f %7.2f %7.2f | %+6.2f %6.2f %+6.2f %6.2f %6.3f | %-14s %5.1f %2d/%-2d %s" % (
                "%s %s%d" % (tag, "m" if M["operator_marked"] else "e", M["k"] + 1), M["tm"], M["f0_10"], M["prom_10"], M["w3"], E["pk"], M["tm"] - E["t_pk"], E["dur_half"], E["tot_half"],
                E["gu"], E["tau_up"], E["gd"], E["tau_dn"], E["zeta"], E["cls"], T["v"], T["ncap"], T["nfr"], T["turn"]))
    pr("\n" + "=" * 172)
    pr("LIKE FOR LIKE (B) -- the V288 table's columns (2 s cores around the bar envelope peak before the mark; v288_marks_r5e.core_anatomy)")
    pr("=" * 172)
    pr("  %-16s %7s | %-58s | %-46s | %7s %6s %s" % ("mark", "t", "15-26 Hz line: f0 xprom bar/wire/T/cmd  rise decay zeta", "5-12 Hz line: f0 xprom bar/wire/T  rise decay zeta", "pk20/pk7", "cap", "census class"))
    for tag, Ms in marks_all.items():
        for M in Ms:
            L = M["cores"]["20"]["L20"]; S = M["cores"]["7"]["L7"]
            s20 = ("%.2f x%3.0f %4.0f/%4.1f/%4.0f/%4.0f %+5.2f %+5.2f %.3f" % (L["f0"], L["prom"], L["amp"], L["wire_amp"], L["T_amp"], L["cmd_amp"], L["gu"], L["gd"], L["zeta"])) if L else "none"
            s7 = ("%.2f x%3.0f %4.0f/%4.1f/%4.0f %+5.2f %+5.2f %.3f" % (S["f0"], S["prom"], S["amp"], S["wire_amp"], S["T_amp"], S["gu"], S["gd"], S["zeta"])) if S else "none"
            cls = ",".join(sorted(set(e["cls"] for e in M["eps"]))) or "none"
            pr("  %-16s %7.1f | %-58s | %-46s | %3.0f/%3.0f %6.3f %s" % ("%s %s%d" % (tag, "m" if M["operator_marked"] else "e", M["k"] + 1), M["tm"], s20, s7, M["pk"]["pk20"], M["pk"]["pk7"], M["cores"]["20"]["op"]["cap"], cls))
    pr("\n" + "=" * 172)
    pr("LIKE FOR LIKE (C) -- the instrument in the 2 s peak core and the revert bands in the 10 s window")
    pr("=" * 172)
    pr("  %-16s | %5s %5s %5s %5s %5s | %-30s | %-30s | %-34s" % ("mark", "b3", "b4", "b5", "b6", "b7", "b5 vs rate: coh / phase / sign", "T: amp / coh / phase vs rate", "bar 13-17 : 18-22 : 22-24 (10 s)"))
    for tag, Ms in marks_all.items():
        for M in Ms:
            I = M["I2"]; R = M["R10"]["bar"]
            pr("  %-16s | %5.3f %5.3f %5.3f %5.3f %5.3f | %-30s | %-30s | %4.0f : %4.0f : %4.0f" % (
                "%s %s%d" % (tag, "m" if M["operator_marked"] else "e", M["k"] + 1), I["b3"], I["b4"], I["b5"], I["b6"], I["b7"],
                ("%.2f / %+.0f deg / %+.0f" % (I["c5r"], I["ph5r"], I["sg5r"])) if tag in V289_TAGS else "(not the notch bit)",
                "%.0f / %.2f / %+.0f deg" % (I["T_amp"], I["cTr"], I["phTr"]), R["13-17"], R["18-22"], R["22-24"]))

    # ---- route-wide census on the V282 yardstick
    pr("\n" + "=" * 172)
    pr("ROUTE-WIDE CENSUS on the V282 yardstick (grind1_census_v282 recipe via v288_marks_r5e.route_census; r39 must reproduce 1742 / 364 / 79)")
    pr("=" * 172)
    for tag in G:
        M288.route_census(G[tag], tag, ROUTES[tag][1])

    # ---- identity from the tap
    pr("\n" + "=" * 172)
    pr("BUILD IDENTITY FROM THE TAP (0x14A byte 4): V289 => b7 reads 1.000 DISENGAGED (0 >= 0) and ~0.10 engaged; b5 ~0.50 engaged (zero-mean component). V288 r5e: b5 0.41 / b7 0.56 engaged. V282 r39: b5 0.13 / b7 0.51.")
    pr("=" * 172)
    for tag in G:
        identity_from_tap(G[tag], tag)

    with open(os.path.join(SCR, "v289_marks_r62_r63.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "v289_marks_r62_r63.txt"))


if __name__ == "__main__":
    main(sys.argv[1:] or list(ROUTES))
