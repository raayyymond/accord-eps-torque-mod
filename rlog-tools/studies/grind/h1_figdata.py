# -*- coding: utf-8 -*-
"""studies/grind/h1_figdata.py -- FIGURE DATA for the H1 ("torque-table resolution") explanation that goes on the
V289/V290 close-out artifact.  Subagent `h1fig2`, 2026-09-09.  ANALYSIS ONLY: builds nothing, flashes nothing, sends
nothing.

Companion to `h1_table_resolution.py` (subagent `hyptable`, same day) -- that script TESTED H1; this one produces the
numbers a page can PLOT.  Every series is re-derived from the BUILT IMAGES and the WIRE CACHES; nothing is copied out
of the report text.  Where a number here disagrees with the report, the disagreement is recorded in the JSON under
"deviations_from_hyptable" and explained in docs/review/H1-FIGURES-README-2026-09-09.md.

Series produced (JSON: analysis-2020accord/_scratch/out/h1_figdata_2026-09-09.json)
  1 map_curves      setpoint (sp counts and deg/s) vs raw 0xE4 command 0..4096, staircase (every index LSB, 241 pts)
                    + the continuous LERP for overlay + knot positions + the index quantiser (idx vs cmd)
  2 step_per_lsb    setpoint step per index LSB vs command, stock vs 6x, in sp counts / deg/s / output counts after P
  3 wire_dcmd       |dcmd| per 100 Hz frame, grinding vs quiet windows, r39 (V282) + r5e_v288 (V288 rev 2), 123 cap
                    marked, plus the two-value-dither and change fractions
  4 amplitude_budget  spectra 3-50 Hz of the map quantisation residual (pushed through P and the gain) vs the 427 tap
                    torque and the 0x18F bar, grinding vs quiet -- the decisive plot
  5 record_table    f0 / presence per build and map scale, each row citing its source file
  6 signal_path     a mermaid-ready description of 0xE4 -> ... -> motor with the quantiser box highlighted

Stages (the wire stage is ~4 min/route the first time; the episode mask is then cached):
    python h1_figdata.py wire r39
    python h1_figdata.py wire r5e_v288
    python h1_figdata.py assemble
    python h1_figdata.py all            # all of the above, in order
"""
import json
import os
import re
import struct
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
OUTDIR = os.path.join(KIT, "analysis-2020accord", "_scratch", "out")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import wire_0xe4_20hz as W                    # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMAGES = {
    "stock": "stock_fw_dump/code.bin",
    "V112": "_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin",
    "V282": "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V289": "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-"
            "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
SEL = 7
FS, FST = 100.0, 50.0          # 0x18F / 0xE4 frame rate, 0x1AB (427 tap) frame rate -- both measured, not assumed
W2, STEP = 200, 50             # census window 2 s, step 0.5 s (grind1_census_v282.py's recipe)
LO, HI = 18.0, 22.0
CPD = 8.0                      # raw 0x18F counts per deg/s
DATE = "2026-09-09"


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base, n):
    return [u16(b, base + 2 + 2 * i) for i in range(n)], [u16(b, base + 2 + 2 * n + 2 * i) for i in range(n)]


def lerp_fw(X, Y, idx):
    """0x29D18-0x29D68 (stock code.bin): memoryless knot walk, divq truncates toward zero (all operands >= 0 -> floor)."""
    idx = int(idx)
    if idx <= X[0]:
        return Y[0]
    if idx >= X[-1]:
        return Y[-1]
    k = 0
    while idx >= X[k + 1]:
        k += 1
    return Y[k] + ((idx - X[k]) * (Y[k + 1] - Y[k])) // (X[k + 1] - X[k])


def lut(X, Y):
    return np.array([lerp_fw(X, Y, i) for i in range(241)], float)


# ======================================================================================================
# images
# ======================================================================================================
def read_images():
    """every cell read from the image; the gain is read through the 0x2A1EE displacement, NOT a hard-coded address."""
    out = {}
    for name, f in IMAGES.items():
        path = FW + f
        b = open(path, "rb").read()
        c = LG.read_build(path)
        cells = GI.read_cells(path)
        p = u32(b, 0xC9A88 + 4 * SEL)
        X, Y = rec(b, p, 10)
        import hashlib
        out[name] = dict(
            file=f, sha256=hashlib.sha256(b).hexdigest(), map_addr="0x%X" % p, X=X, Y=Y,
            kp_X=c["kp_X"].astype(int).tolist(), kp_Y=c["kp_Y"].astype(int).tolist(),
            kd_Y=c["kd_Y"].astype(int).tolist(),
            idx_clamp=int(c["idx_clamp"]), fb_a=int(c["fb_a"]), fb_b=int(c["fb_b"]),
            fb_clamp=int(c["fb_clamp"]), p_clamp=int(c["p_clamp"]), d_clamp=int(c["d_clamp"]),
            sum_clamp=int(c["sum_clamp"]), out_clamp=int(c["t_clamp"]),
            lag_a=int(c["lag_a"]), lag_b=int(c["lag_b"]), ki=int(c["ki"]),
            gain=int(c["gain"]), gain_addr="0x%X" % c["gain_addr"],
            taperS_X=cells["taperS"][0].astype(int).tolist(), taperS_Y=cells["taperS"][1].astype(int).tolist(),
            taperO_X=cells["taperO"][0].astype(int).tolist(), taperO_Y=cells["taperO"][1].astype(int).tolist(),
            speedF=cells["speedF"].astype(int).tolist(),
        )
    return out


def taper_live(img):
    """the taper value the live arm produces at low |driver bar| (tx = |bar|//32 below the first knot -> Y[0])."""
    return int(img["taperS_Y"][0]), int(img["taperO_Y"][0])


def idx_of_cmd_vec(cmd, taper, speedF=255, limit=16384, idx_clamp=240):
    """0x29032..0x29CFA mirrored, vectorised.  taper is the LIVE arm value (0xCB924 slot 7), not the cliff arm."""
    S = np.clip(-4.0 * np.asarray(cmd, float), -limit, limit)
    prod = int(taper * speedF) & 0xFFFF
    v = np.floor(prod * S / 65536.0)
    v = np.floor(v / 64.0)
    v = np.clip(v, -idx_clamp, idx_clamp)
    return np.abs(v).astype(int), np.where(v < 0, -1.0, 1.0)


def cont_idx_of_cmd(cmd, taper, speedF=255, limit=16384, idx_clamp=240):
    """the SAME chain with the two floors removed -- the continuous index the quantiser is measured against."""
    S = np.clip(-4.0 * np.asarray(cmd, float), -limit, limit)
    prod = int(taper * speedF) & 0xFFFF
    return np.minimum(np.abs(prod * S / 65536.0 / 64.0), float(idx_clamp))


def series_map_curves(imgs):
    """1. map curves + the index quantiser."""
    taperS, taperO = taper_live(imgs["V282"])
    assert taperS == taper_live(imgs["stock"])[0], "live taper differs between images"
    prod = (taperS * 255) & 0xFFFF
    lsb = 2.0 ** 22 / (prod * 4.0)                       # raw 0xE4 counts per idx LSB
    cmds = np.arange(0, 4097)
    idx, _ = idx_of_cmd_vec(cmds, taperS)
    # bin edges: first cmd of each idx value
    first = np.full(241, -1)
    for i in range(241):
        w = np.flatnonzero(idx == i)
        first[i] = int(w[0]) if len(w) else -1
    last = np.r_[first[1:] - 1, 4096]
    widths = np.diff(first[first >= 0])

    FB_DC = 2.0 * imgs["V282"]["fb_b"] / (1024 - imgs["V282"]["fb_a"])
    sp_lsb_degs = 32.0 / (FB_DC * CPD)                   # 1 sp count in deg/s of rate setpoint
    # reference loop for the "output counts" axis: Kp 248 flat, gain 5346>>15 (the V282/V289 loop). Using ONE loop for
    # both maps is deliberate -- it isolates the MAP.  Each image's own cells are in the "images" block.
    KP_REF, GAIN_REF = 248, 5346
    out_per_sp = 32.0 * KP_REF / 256.0 * GAIN_REF / 32768.0

    builds = {}
    for name in ("stock", "V282", "V289"):
        X, Y = imgs[name]["X"], imgs[name]["Y"]
        L = lut(X, Y)
        sub = np.linspace(0, 4096, 1025)
        ci = cont_idx_of_cmd(sub, taperS)
        spc = np.interp(ci, X, Y)
        builds[name] = dict(
            X=X, Y=Y,
            knot_cmd=[float(x * lsb) for x in X], knot_sp=[float(y) for y in Y],
            knot_sp_degs=[float(y * sp_lsb_degs) for y in Y],
            stair_idx=list(range(241)),
            stair_cmd_lo=[float(v) for v in first], stair_cmd_hi=[float(v) for v in last],
            stair_sp=[float(v) for v in L], stair_sp_degs=[float(v * sp_lsb_degs) for v in L],
            stair_sp_out=[float(v * out_per_sp) for v in L],
            cont_cmd=[float(v) for v in sub], cont_sp=[float(v) for v in spc],
            cont_sp_degs=[float(v * sp_lsb_degs) for v in spc],
            trunc_min=float((L - np.interp(np.arange(241), X, Y)).min()),
            trunc_max=float((L - np.interp(np.arange(241), X, Y)).max()),
        )
    return dict(
        idx_lsb_raw_counts=float(lsb),
        idx_lsb_pct_of_full_scale=float(100.0 * lsb / 4096),
        taper_live_same_sign=taperS, taper_live_opposite_sign=taperO,
        taper_product=int(prod),
        idx_quantiser=dict(cmd=[int(v) for v in cmds[::4]], idx=[int(v) for v in idx[::4]],
                           bin_first_cmd=[int(v) for v in first], bin_last_cmd=[int(v) for v in last],
                           bin_width_min=int(widths.min()), bin_width_max=int(widths.max()),
                           bin_width_median=float(np.median(widths)),
                           cmd_at_idx240=int(first[240]),
                           first_cmd_reaching_idx1_positive=int(np.flatnonzero(idx_of_cmd_vec(np.arange(0, 64), taperS)[0] >= 1)[0]),
                           first_cmd_reaching_idx1_negative=int(np.flatnonzero(idx_of_cmd_vec(-np.arange(0, 64), taperS)[0] >= 1)[0]),
                           sign_asymmetry_note="the two shifts are V850 `sar` = arithmetic shift = FLOOR, so for one "
                                               "command sign the quantiser floors AWAY from zero and for the other "
                                               "TOWARD it: index 1 is reached at cmd +1 but not until cmd -17. A "
                                               "fixed one-index offset between the two steering directions near "
                                               "centre; it is not a dither and it does not scale with the map."),
        sp_count_in_degs=float(sp_lsb_degs), fb_dc=float(FB_DC),
        out_counts_per_sp_count=float(out_per_sp),
        reference_loop=dict(Kp=KP_REF, gain=GAIN_REF, note="Kp 248 flat, gain 5346>>15 -- the V282/V289 loop, applied to "
                            "BOTH maps so the curves isolate the map. stock's own cells are in images.stock."),
        builds=builds,
    )


def series_step_per_lsb(imgs, mc):
    """2. setpoint step per index LSB vs command."""
    lsb = mc["idx_lsb_raw_counts"]
    out = dict(idx=list(range(1, 241)), cmd=[float(i * lsb) for i in range(1, 241)], builds={})
    for name in ("stock", "V282", "V289"):
        L = np.array(mc["builds"][name]["stair_sp"])
        d = np.diff(L)
        out["builds"][name] = dict(
            dsp_counts=[float(v) for v in d],
            dsp_degs=[float(v * mc["sp_count_in_degs"]) for v in d],
            dT_out_counts=[float(v * mc["out_counts_per_sp_count"]) for v in d],
            step_multiset={str(int(k)): int(c) for k, c in zip(*np.unique(d, return_counts=True))},
        )
    # per-interval slopes (the report's A3 table), recomputed
    X = imgs["stock"]["X"]
    rows = []
    for k in range(len(X) - 1):
        r = dict(idx_lo=X[k], idx_hi=X[k + 1], dcmd_raw=float((X[k + 1] - X[k]) * lsb))
        for name in ("stock", "V282"):
            Y = imgs[name]["Y"]
            s = (Y[k + 1] - Y[k]) / (X[k + 1] - X[k])
            r[name] = dict(dsp_counts=float(s), dsp_degs=float(s * mc["sp_count_in_degs"]),
                           dT_out_counts=float(s * mc["out_counts_per_sp_count"]))
        rows.append(r)
    out["per_interval"] = rows
    # relative resolution (step / value) -- identical on both maps by construction
    rel = {}
    for name in ("stock", "V282"):
        L = np.array(mc["builds"][name]["stair_sp"])
        d = np.diff(L)
        rel[name] = {str(i): float(d[i - 1] / max(1.0, L[i])) for i in (6, 12, 30, 60, 120, 200)}
    out["relative_step"] = rel
    return out


# ======================================================================================================
# wire
# ======================================================================================================
def hot_mask(tag, g):
    """episodes_of is ~3.5 min/route -- cache the mask so re-runs are cheap."""
    f = os.path.join(SCR, "h1_figdata_hot_%s.npz" % tag)
    if os.path.exists(f):
        z = np.load(f)
        if len(z["hot"]) == len(g["t"]):
            return z["hot"].astype(bool), z["eps"]
    print("  computing episodes for %s (slow, ~3.5 min) ..." % tag, flush=True)
    eps, hot = W.episodes_of(g)
    e = np.array([[a, b, f0] for a, b, f0 in eps], float) if eps else np.zeros((0, 3))
    np.savez(f, hot=hot, eps=e)
    return hot, e


def bandamp_from_spec(f, amp2, lo, hi):
    s = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.sum(amp2[s])))


def run_wire(tag):
    print("wire stage: %s" % tag, flush=True)
    imgs = read_images()
    cells = GI.read_cells(FW + IMAGES["V282"])
    taperS = taper_live(imgs["V282"])[0]
    g = W.load_route(tag, cells)
    e = g["e4"]
    hot, eps = hot_mask(tag, g)
    print("  engaged %.0f s, %d episodes" % (g["eng"].sum() / FS, len(eps)), flush=True)

    # ---- whole-route quantisation residual, vectorised (table lookup for the integer LERP) --------------
    cmd_grid = np.round(e["grid"]).astype(int)
    bar_e = np.interp(e["tgrid"], g["t"], g["bar"])
    idx_live, sgn = GI.demand_live(cmd_grid, bar_e, cells)     # LIVE taper arm, from the image
    idx_live = idx_live.astype(int)
    # continuous index through the SAME live taper (this is the fix vs hyptable, which used the cliff arm's 254 here)
    S = np.clip(-4.0 * cmd_grid, -16384, 16384)
    same = np.sign(S) == np.sign(bar_e)
    tx = np.abs(bar_e) // 32
    tp = np.where(same, np.interp(tx, cells["taperS"][0], cells["taperS"][1]),
                  np.interp(tx, cells["taperO"][0], cells["taperO"][1]))
    prod_live = (tp * 255).astype(np.int64) & 0xFFFF
    cont_idx = np.minimum(np.abs(prod_live * S / 65536.0 / 64.0), 240.0)
    cont_idx_254 = np.minimum(np.abs(np.clip(-4.0 * cmd_grid, -16384, 16384)) * 64770 / 65536.0 / 64.0, 240.0)

    out_per_sp = 32.0 * 248 / 256.0 * 5346 / 32768.0
    resid = {}
    for name in ("V282", "stock"):
        X, Y = imgs[name]["X"], imgs[name]["Y"]
        L = lut(X, Y)
        sp_stair = L[idx_live] * sgn
        resid[name] = (sp_stair - np.interp(cont_idx, X, Y) * sgn) * out_per_sp
        resid[name + "_hyptable"] = (sp_stair - np.interp(cont_idx_254, X, Y) * sgn) * out_per_sp

    # ---- windows -----------------------------------------------------------------------------------
    NPS = 200
    f100 = np.fft.rfftfreq(NPS, 1.0 / FS)
    NPST = 100
    f50 = np.fft.rfftfreq(NPST, 1.0 / FST)
    HIST = np.r_[np.arange(0, 201), 1e9]                      # 1-count bins to 200, then overflow
    acc = {}
    for st in ("grind", "quiet"):
        acc[st] = dict(n=0, hist=np.zeros(len(HIST) - 1), nframes=0,
                       spec={k: np.zeros(len(f100)) for k in ("q6", "qs", "q6_hyp", "cmd", "bar", "rate")},
                       speclist={k: [] for k in ("q6", "qs", "q6_hyp", "cmd", "bar", "rate")},
                       specT=np.zeros(len(f50)), specTlist=[], nT=0,
                       stats={k: [] for k in ("f0", "amp", "T_band", "T_band_native", "q6_band", "qs_band",
                                              "q6_hyp_band", "cmd_band", "alt_frac", "two_c", "two_i", "one_i",
                                              "chg_frac", "cap_frac", "idx_rate", "v", "bar", "q6_rms", "qs_rms")})
    win = signal.get_window("hann", NPS)
    winT = signal.get_window("hann", NPST)

    def amp2(x, w, fs):
        """per-bin PEAK-amplitude^2, DENSITY-scaled so that sum over a band = (sqrt(2)*sigma_band)^2 = GI.band^2
        for a broadband signal, and ~= A^2 over the mainlobe for a pure sinusoid of amplitude A."""
        x = np.asarray(x, float)
        n = len(x)
        Xf = np.fft.rfft((x - x.mean()) * w)
        P = 2.0 * (np.abs(Xf) ** 2) / (fs * (w ** 2).sum())     # single-sided PSD, units^2/Hz
        P[0] /= 2.0
        if n % 2 == 0:
            P[-1] /= 2.0
        return 2.0 * P * (fs / n)                               # x2*df -> peak-amplitude^2 per bin

    nwin = 0
    for aa, bb in C20.runs(g["eng"], W2):
        for s in range(aa, bb - W2 + 1, STEP):
            b_ = s + W2
            ta, tb = g["t"][s], g["t"][b_ - 1]
            ka = int(np.searchsorted(e["tgrid"], ta)); kb = int(np.searchsorted(e["tgrid"], tb))
            if kb - ka < 150 or e["have"][ka:kb].mean() < 0.9:
                continue
            nwin += 1
            grind = bool(hot[s:b_].mean() > 0.5)
            v = float(np.median(g["vego"][s:b_])); barm = float(np.median(np.abs(g["bar"][s:b_])))
            if grind:
                st = "grind"
            elif v < 12 and barm < 400:
                st = "quiet"
            else:
                continue
            A = acc[st]
            c = cmd_grid[ka:kb]
            d = np.abs(np.diff(c))
            A["hist"] += np.histogram(d, bins=HIST)[0]
            A["nframes"] += len(d)
            n = kb - ka
            ii = idx_live[ka:kb]
            di = np.diff(ii)
            dd = np.diff(c.astype(int))
            alt = (dd[1:] * dd[:-1] < 0) & (np.abs(dd[1:]) <= 2) & (np.abs(dd[:-1]) <= 2)
            n10 = n // 10
            c10 = c[:n10 * 10].reshape(n10, 10); i10 = ii[:n10 * 10].reshape(n10, 10)
            nvc = np.array([len(np.unique(r)) for r in c10]); nvi = np.array([len(np.unique(r)) for r in i10])
            # spectra, on 200-sample (2 s) slices of each stream
            if ka + NPS <= len(resid["V282"]) and s + NPS <= len(g["bar"]):
                segs = dict(q6=resid["V282"][ka:ka + NPS], qs=resid["stock"][ka:ka + NPS],
                            q6_hyp=resid["V282_hyptable"][ka:ka + NPS],
                            cmd=cmd_grid[ka:ka + NPS].astype(float),
                            bar=g["bar"][s:s + NPS], rate=g["wire"][s:s + NPS])
                for k, x in segs.items():
                    a = amp2(x, win, FS)
                    A["spec"][k] += a
                    A["speclist"][k].append(a)
                A["n"] += 1
            # the 427 tap on its own 50 Hz clock
            jt = np.flatnonzero((g["T_t"] >= ta) & (g["T_t"] < tb))
            if len(jt) >= NPST:
                aT = amp2(g["T"][jt[:NPST]], winT, FST)
                A["specT"] += aT
                A["specTlist"].append(aT)
                A["nT"] += 1
                S0 = A["stats"]["T_band_native"]
                S0.append(GI.band(g["T"][jt[:NPST]], LO, HI, FST))
            else:
                A["stats"]["T_band_native"].append(np.nan)
            f0, prom, _, _ = GI.line_of(g["bar"][s:b_], FS, 15.0, 26.0)
            S_ = A["stats"]
            S_["f0"].append(float(f0) if (prom >= 8) else np.nan)
            S_["amp"].append(GI.band(g["bar"][s:b_], LO, HI, FS))
            S_["T_band"].append(GI.band(g["T100"][s:b_], LO, HI, FS))
            S_["q6_band"].append(GI.band(resid["V282"][ka:kb], LO, HI, FS))
            S_["qs_band"].append(GI.band(resid["stock"][ka:kb], LO, HI, FS))
            S_["q6_hyp_band"].append(GI.band(resid["V282_hyptable"][ka:kb], LO, HI, FS))
            S_["cmd_band"].append(GI.band(c.astype(float), LO, HI, FS))
            S_["q6_rms"].append(float(np.std(resid["V282"][ka:kb])))
            S_["qs_rms"].append(float(np.std(resid["stock"][ka:kb])))
            S_["alt_frac"].append(float(alt.mean()))
            S_["two_c"].append(float(np.mean(nvc == 2)))
            S_["two_i"].append(float(np.mean(nvi == 2)))
            S_["one_i"].append(float(np.mean(nvi == 1)))
            S_["chg_frac"].append(float(np.mean(dd != 0)))
            S_["cap_frac"].append(float(np.mean(np.abs(dd) >= 122)))
            S_["idx_rate"].append(float(np.sum(di != 0) / (n / FS)))
            S_["v"].append(v)
            S_["bar"].append(barm)

    res = dict(tag=tag, engaged_s=float(g["eng"].sum() / FS), n_episodes=int(len(eps)),
               windows_total=int(nwin), f100=[float(x) for x in f100], f50=[float(x) for x in f50],
               hist_edges=[float(x) for x in HIST[:-1]] + [1e9], strata={})
    for st in ("grind", "quiet"):
        A = acc[st]
        S_ = A["stats"]
        hp = A["hist"] / max(1.0, A["hist"].sum())
        d = dict(n_windows=len(S_["v"]), n_spec=A["n"], n_specT=A["nT"], n_frames=int(A["nframes"]),
                 hist=[float(x) for x in hp],
                 hist_pooled_groups=dict(zero=float(hp[0]), one=float(hp[1]), two=float(hp[2]),
                                         g3_7=float(hp[3:8].sum()), g8_15=float(hp[8:16].sum()),
                                         g16_63=float(hp[16:64].sum()), g64_121=float(hp[64:122].sum()),
                                         cap_ge122=float(hp[122:].sum())),
                 spec={}, specT=[])
        d["spec_median"] = {}
        for k, v in A["spec"].items():
            d["spec"][k] = [float(x) for x in np.sqrt(v / max(1, A["n"]))]        # per-bin amplitude, MEAN power
            L = np.array(A["speclist"][k]) if A["speclist"][k] else np.zeros((1, len(f100)))
            d["spec_median"][k] = [float(x) for x in np.sqrt(np.median(L, axis=0))]   # per-bin amplitude, MEDIAN power
        d["specT"] = [float(x) for x in np.sqrt(A["specT"] / max(1, A["nT"]))]
        LT = np.array(A["specTlist"]) if A["specTlist"] else np.zeros((1, len(f50)))
        d["specT_median"] = [float(x) for x in np.sqrt(np.median(LT, axis=0))]
        for k, v in S_.items():
            v = np.array(v, float)
            d[k] = dict(p10=float(np.nanpercentile(v, 10)) if np.isfinite(v).any() else None,
                        p50=float(np.nanpercentile(v, 50)) if np.isfinite(v).any() else None,
                        p90=float(np.nanpercentile(v, 90)) if np.isfinite(v).any() else None,
                        mean=float(np.nanmean(v)) if np.isfinite(v).any() else None)
        # band checks read straight off the pooled spectra
        a2 = {k: np.array(v) ** 2 for k, v in d["spec"].items()}
        d["band_from_spec"] = {k: bandamp_from_spec(np.array(res["f100"]), a2[k], LO, HI) for k in a2}
        d["band_from_spec"]["T"] = bandamp_from_spec(np.array(res["f50"]), np.array(d["specT"]) ** 2, LO, HI)
        a2m = {k: np.array(v) ** 2 for k, v in d["spec_median"].items()}
        d["band_from_spec_median"] = {k: bandamp_from_spec(np.array(res["f100"]), a2m[k], LO, HI) for k in a2m}
        d["band_from_spec_median"]["T"] = bandamp_from_spec(np.array(res["f50"]),
                                                            np.array(d["specT_median"]) ** 2, LO, HI)
        res["strata"][st] = d
    f = os.path.join(SCR, "h1_figdata_wire_%s.json" % tag)
    json.dump(res, open(f, "w"), separators=(",", ":"))
    print("  wrote %s  (grind %d win, quiet %d win)" % (f, res["strata"]["grind"]["n_windows"],
                                                        res["strata"]["quiet"]["n_windows"]), flush=True)
    return res


# ======================================================================================================
# record
# ======================================================================================================
def series_record():
    src = os.path.join(SCR, "loopshape20_mode_nature.txt")
    rows = []
    txt = open(src, encoding="utf-8", errors="replace").read().splitlines()
    meta = {"V278r3": ("x2 concave", "LERP 248->696"), "V280r2": ("x6 linear", "LERP 248->696"),
            "V281r3": ("x6 linear", "flat 248"), "V282": ("x6 linear", "flat 248"),
            "V288": ("x6 linear + setpoint pre-filter (steps ~11x finer)", "flat 248")}
    for ln in txt:
        s = ln.strip()
        for b in meta:
            if s.startswith(b) and " f0 " in s:
                m = re.search(r"f0 ([\d.]+) \[([\d.]+)-([\d.]+)\] n=(\d+)", s)
                p = re.search(r"presence[^\d]*([\d.]+) ?%", s)
                if not m:
                    continue
                rows.append(dict(build=b, map=meta[b][0], Kp=meta[b][1], f0=float(m.group(1)),
                                 f0_lo=float(m.group(2)), f0_hi=float(m.group(3)), n=int(m.group(4)),
                                 presence_pct=float(p.group(1)) if p else None,
                                 source="rlog-tools/studies/grind/_scratch/loopshape20_mode_nature.txt",
                                 raw=s))
                break
    kp_bins, idx_bins = [], []
    for ln in txt:
        s = ln.strip()
        if s.startswith("Kp-LERP") or s.startswith("flat-Kp"):
            (kp_bins if s.startswith("Kp-LERP") else idx_bins).append(s)
    return dict(rows=rows, kp_bins=kp_bins, idx_or_bar_bins=idx_bins,
                stock_map_era=dict(
                    claim="the 18-22 Hz band is named in the V62 era and 21-26 Hz in the V112 era, both on the STOCK map; "
                          "the one stock creep sample (r97) carries 29 raw in the band vs ~113-146 raw pooled on x2/x6 builds",
                    source="docs/research/GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md (grind #1 row)",
                    kind="EVIDENCE (quoted from the ledger; not re-derived here)"),
                v288_null=dict(
                    claim="V288 rev 2 made every per-tick setpoint step ~11x finer and cut D-clamp binds x0.03; "
                          "grinding unchanged (258 vs 239 ep/h, f 20.06 vs 20.03, envelope p50 126 vs 127)",
                    source="docs/review/GRIND1-CENSUS-V288-R5E-2026-09-08.md",
                    kind="EVIDENCE (quoted; not re-derived here)"))


MERMAID = {
    "note": "flowchart LR; the QUANTISER node is the one H1 is about. Addresses are instruction addresses in "
            "FUN_00028ea6 (stock code.bin) unless marked cal.",
    "nodes": [
        {"id": "OP", "label": "openpilot 0xE4 STEER_TORQUE_REQUEST\\n100 Hz, raw counts 0..4096\\nslew-capped 123/frame",
         "kind": "source"},
        {"id": "DEC", "label": "CAN decode  S = -4 x cmd\\nclamp +-16384 (cal 0xCB844 slot 7)", "kind": "step",
         "addr": "0x29032-0x29044"},
        {"id": "TAP", "label": "override taper x speed factor\\n(255 x 255) & 0xFFFF = 65025  [live arm 0xCB924 slot 7 = 255 below |bar| 2591 raw]",
         "kind": "step", "addr": "0x29CB4-0x29CC0"},
        {"id": "QNT", "label": "QUANTISER  >>16 then >>6, |.|, clamp 240\\n1 idx LSB = 16.13 raw 0xE4 counts (0.39 % FS)\\n"
                               "241 index values for the whole command range", "kind": "highlight",
         "addr": "0x29CC0-0x29CFA, cal 0xC64F0 = 240"},
        {"id": "MAP", "label": "assist map LERP  0xC9A88[7] -> 0xE502C\\n10 knots, integer divq (floor)\\n"
                               "stock Y 0..172   V282/V289 Y 0..1032 (6x linear)", "kind": "step",
         "addr": "0x29D18-0x29D6C"},
        {"id": "SP", "label": "rate setpoint sp  (gp-0x6a32)\\n1 sp count = 0.1295 deg/s", "kind": "signal"},
        {"id": "ERR", "label": "E = 32 x sp - fb", "kind": "step", "addr": "0x29D76-0x29D78"},
        {"id": "FB", "label": "feedback: 0x18F wheel rate\\ntwo-sample sum, DC 30.89, pole 16.5 Hz\\n"
                              "(V289: 25 Hz, cal 0xC63E8/EA)", "kind": "feedback"},
        {"id": "P", "label": "P = E x Kp >> 8   (Kp 248 flat)\\nclamp +-15360 (cal 0xC61BC)", "kind": "step"},
        {"id": "D", "label": "D = dE x Kd >> 3   (Kd 128)\\nclamp +-10240 (cal 0xC61B6)", "kind": "step"},
        {"id": "SUM", "label": "sum, post-PID fades, clamp +-15360 (cal 0xC61BE)", "kind": "step"},
        {"id": "NOTCH", "label": "V289 ONLY: 20.04 Hz Q3 notch cave @0xC4C00\\n(hook 0x2A174)", "kind": "v289"},
        {"id": "LAG", "label": "output lag 992/507 >>5  (5.05 Hz)", "kind": "step"},
        {"id": "GAIN", "label": "x GAIN >> 15   (5346 = 6x; read via 0x2A1EE displacement)", "kind": "step"},
        {"id": "CLP", "label": "clamp +-3072 (cal 0xC61B4) -> gp-0x6b38", "kind": "step"},
        {"id": "MOT", "label": "EME shaper -> FOC / PWM -> motor", "kind": "sink"},
    ],
    "edges": [["OP", "DEC"], ["DEC", "TAP"], ["TAP", "QNT"], ["QNT", "MAP"], ["MAP", "SP"], ["SP", "ERR"],
              ["FB", "ERR"], ["ERR", "P"], ["ERR", "D"], ["P", "SUM"], ["D", "SUM"], ["SUM", "NOTCH"],
              ["NOTCH", "LAG"], ["LAG", "GAIN"], ["GAIN", "CLP"], ["CLP", "MOT"], ["MOT", "FB"]],
    "mermaid": (
        "flowchart LR\n"
        "  OP[\"openpilot 0xE4<br/>100 Hz, 0..4096 raw<br/>slew cap 123/frame\"]\n"
        "  DEC[\"CAN decode<br/>S = -4 x cmd, clamp +-16384\"]\n"
        "  TAP[\"taper x speedF<br/>(255 x 255) & 0xFFFF\"]\n"
        "  QNT[\"QUANTISER  >>16 >>6, abs, clamp 240<br/><b>1 idx LSB = 16.13 raw counts</b><br/>241 index values total\"]\n"
        "  MAP[\"assist map LERP 0xE502C<br/>10 knots, divq floors<br/>stock 0..172 / V282 0..1032\"]\n"
        "  SP([\"setpoint sp<br/>1 count = 0.1295 deg/s\"])\n"
        "  ERR[\"E = 32*sp - fb\"]\n"
        "  P[\"P = E*Kp>>8 (248)<br/>clamp 15360\"]\n"
        "  D[\"D = dE*Kd>>3 (128)<br/>clamp 10240\"]\n"
        "  SUM[\"sum + post-PID fades<br/>clamp 15360\"]\n"
        "  NOTCH[\"V289: 20.04 Hz Q3 notch<br/>cave 0xC4C00\"]\n"
        "  LAG[\"output lag 5.05 Hz\"]\n"
        "  GAIN[\"x gain 5346>>15\"]\n"
        "  CLP[\"clamp +-3072<br/>gp-0x6b38\"]\n"
        "  MOT[\"EME -> FOC/PWM -> motor\"]\n"
        "  FB[\"feedback: 0x18F wheel rate<br/>two-sample sum, DC 30.89<br/>pole 16.5 Hz (V289 25 Hz)\"]\n"
        "  OP-->DEC-->TAP-->QNT-->MAP-->SP-->ERR-->P-->SUM\n"
        "  ERR-->D-->SUM-->NOTCH-->LAG-->GAIN-->CLP-->MOT\n"
        "  MOT-.->FB-.->ERR\n"
        "  style QNT fill:#fde68a,stroke:#b45309,stroke-width:3px\n"),
}


# ======================================================================================================
def assemble():
    imgs = read_images()
    mc = series_map_curves(imgs)
    st = series_step_per_lsb(imgs, mc)
    wire = {}
    for tag in ("r39", "r5e_v288"):
        f = os.path.join(SCR, "h1_figdata_wire_%s.json" % tag)
        if not os.path.exists(f):
            raise SystemExit("missing %s -- run:  python h1_figdata.py wire %s" % (f, tag))
        wire[tag] = json.load(open(f))
    doc = dict(
        meta=dict(
            title="H1 figure data -- 'OP switches between two points on the torque table; scaling loses resolution'",
            date=DATE, agent="h1fig2",
            produced_by="rlog-tools/studies/grind/h1_figdata.py",
            companion_report="docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md (subagent hyptable)",
            readme="docs/review/H1-FIGURES-README-2026-09-09.md",
            images_root=FW,
            stock_source="stock_fw_dump/code.bin -- the TRUE stock dump (present); _v83a's map bytes are identical to it "
                         "(checked: same X and Y at 0xE502C), so either can be used for the stock map curve",
            wire_routes={"r39": "V282", "r5e_v288": "V288 rev 2 (map + rate loop byte-identical to V282/V289)"},
            frame_rates={"0xE4 command": 100.0, "0x18F bar/rate": 100.0, "0x1AB 427 torque tap": 50.0},
            caveat_tap_nyquist="the 427 tap streams at 50 Hz, so its spectrum is only defined to 25 Hz; the 3-50 Hz "
                               "axis is honoured for the residual, the command and the 0x18F bar, and the tap curve "
                               "stops at 25 Hz. Do not draw the tap above 25 Hz.",
            evidence="every number in map_curves, step_per_lsb, wire_dcmd and amplitude_budget is EVIDENCE re-derived "
                     "from the images / caches by this script. record_table rows quoted from the named files are "
                     "EVIDENCE for the quotation, and each row names its source.",
        ),
        images=imgs,
        map_curves=mc,
        step_per_lsb=st,
        wire_dcmd={t: dict(tag=t, engaged_s=wire[t]["engaged_s"], n_episodes=wire[t]["n_episodes"],
                           hist_edges=wire[t]["hist_edges"],
                           slew_cap_raw=122.88, slew_cap_note="openpilot rate_limit 0.03/frame x 4096 = 122.88 raw counts",
                           strata={s: {k: wire[t]["strata"][s][k] for k in
                                       ("n_windows", "n_frames", "hist", "hist_pooled_groups",
                                        "alt_frac", "two_c", "two_i", "one_i",
                                        "chg_frac", "cap_frac", "idx_rate", "v", "bar")}
                                   for s in ("grind", "quiet")})
                   for t in wire},
        amplitude_budget={t: dict(tag=t, f100=wire[t]["f100"], f50=wire[t]["f50"],
                                  strata={s: dict(n_spec=wire[t]["strata"][s]["n_spec"],
                                                  n_specT=wire[t]["strata"][s]["n_specT"],
                                                  spec=wire[t]["strata"][s]["spec"],
                                                  spec_median=wire[t]["strata"][s]["spec_median"],
                                                  specT=wire[t]["strata"][s]["specT"],
                                                  specT_median=wire[t]["strata"][s]["specT_median"],
                                                  band_from_spec=wire[t]["strata"][s]["band_from_spec"],
                                                  band_from_spec_median=wire[t]["strata"][s]["band_from_spec_median"],
                                                  bands={k: wire[t]["strata"][s][k] for k in
                                                         ("amp", "T_band", "T_band_native", "q6_band", "qs_band",
                                                          "q6_hyp_band", "cmd_band", "q6_rms", "qs_rms", "f0")})
                                          for s in ("grind", "quiet")})
                          for t in wire},
        record_table=series_record(),
        signal_path=MERMAID,
        deviations_from_hyptable=[
            dict(what="index LSB in raw 0xE4 counts",
                 hyptable="16.19 (taper 254 x speedF 255 = 64770)",
                 here="%.3f (taper %d x speedF 255 = %d)" % (mc["idx_lsb_raw_counts"], mc["taper_live_same_sign"],
                                                             mc["taper_product"]),
                 why="hyptable used the SUPERSEDED cliff-arm taper table (v280_map_profiles.TAPER_Y[0] = 254). The LIVE "
                     "arm read from the image (0xCB924 slot 7, same-sign; 0xCB8B4 opposite-sign) is 255 below "
                     "|bar| = 2591 raw, which is the whole regime the census windows sit in. 0.4 % difference; it "
                     "changes no conclusion.",
                 impact="cosmetic on every figure; the knot cmd positions shift 0.4 %"),
            dict(what="the quantisation residual (staircase minus continuous)",
                 hyptable="staircase index used the LIVE taper, the continuous reference used the 254 cliff arm",
                 here="both use the LIVE taper, so the residual is purely the two floors and the integer LERP",
                 why="the mismatch injected a 0.39 %-of-setpoint scale bias into hyptable's residual, which is a "
                     "low-frequency term proportional to the command, not quantisation noise",
                 impact="the corrected residual is SMALLER; both are in this file (q6 vs q6_hyp) so the report's "
                        "numbers stay reproducible"),
        ],
    )
    os.makedirs(OUTDIR, exist_ok=True)
    f = os.path.join(OUTDIR, "h1_figdata_%s.json" % DATE)
    json.dump(doc, open(f, "w"), separators=(",", ":"))
    print("wrote %s  (%.2f MB)" % (f, os.path.getsize(f) / 1e6), flush=True)
    # a short human summary to stdout
    print("\nidx LSB %.3f raw counts (taper %d);  1 sp count = %.4f deg/s;  %.2f out counts per sp count" %
          (mc["idx_lsb_raw_counts"], mc["taper_live_same_sign"], mc["sp_count_in_degs"], mc["out_counts_per_sp_count"]))
    for t in wire:
        for s in ("grind", "quiet"):
            d = wire[t]["strata"][s]
            print("%-9s %-6s n=%4d  chg %.3f cap %.3f alt %.3f two-cmd %.3f | q6 18-22 %.2f  q6_hyp %.2f  qs %.2f  "
                  "tap %.1f  bar %.0f" % (t, s, d["n_windows"], d["chg_frac"]["p50"], d["cap_frac"]["p50"],
                                          d["alt_frac"]["p50"], d["two_c"]["p50"], d["q6_band"]["p50"],
                                          d["q6_hyp_band"]["p50"], d["qs_band"]["p50"], d["T_band"]["p50"],
                                          d["amp"]["p50"]))
    return f


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    a = sys.argv[1:] or ["all"]
    if a[0] == "wire":
        run_wire(a[1])
    elif a[0] == "assemble":
        assemble()
    else:
        for tg in ("r39", "r5e_v288"):
            run_wire(tg)
        assemble()
