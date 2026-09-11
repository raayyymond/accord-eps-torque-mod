# -*- coding: utf-8 -*-
"""studies/grind/burst_onset_triggers.py -- does a DISCRETE COMMAND EVENT *TRIGGER* a grinding burst?
Subagent `slewburst`, 2026-09-10.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

THE QUESTION.  H1 (`docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md`) killed the quantiser on
AMPLITUDE: its whole residual carried through the loop is 2.3-2.5 output counts at 18-22 Hz against
29-41 measured, and it is identical in grinding and quiet windows.  It did NOT test TIMING.  A lightly
damped mode (zeta ~0.029, Q ~17) can be KICKED by an impulse far smaller than the ring it produces, and
the symptom's morphology -- "decaying bursts in trains" -- is what impulsive excitation looks like.  So:
are burst ONSETS time-locked to discrete command events?

METHOD, in one line: band-limited complex-demodulation envelope of the driver-torque bar at the per-build
ring frequency -> burst onsets to ~25 ms -> hazard ratio of onset rate inside a short window after each
candidate event class, against a CIRCULAR-SHIFT null that preserves both series' own clustering.

Per-build ring band (STATE correction #2: the 18-22 Hz census gate is BLIND to V289's relocated line):
  r39 (V282), r5e_v288 (V288 rev 2), r35 (V281 rev 3) -> 18-22 Hz     r62/r63 (V289 rev 1) -> 13-18 Hz

Sections
  1  DETECTOR     envelope, onsets, validation vs the r35 incident and the operator's own bookmarks
  2  EVENTS       cap binds, idx steps, |dcmd|, sign reversals, |d2cmd|, engagement (the control)
  3  HAZARD       onset rate in [0,+w] after each event class vs circular-shift null; RR, CI, base rate
  4  LEADLAG      full +-500 ms cross-correlogram against the same null
  5  DOSE         onsets/s vs slew statistics, stratified on speed x demand index (Poisson GLM)
  6  ROAD         the falsifier -- IMU vertical/lateral accel and gyro impulses as the rival trigger
  7  SIZING       what impulse a Q~17 ring needs to reach the measured envelope, vs what a capped
                 command step actually injects (byte-exact 1 kHz mirror)

Run: python rlog-tools/studies/grind/burst_onset_triggers.py            (all routes, all sections)
     python rlog-tools/studies/grind/burst_onset_triggers.py --fast     (skip section 7 mirror sweep)
Writes _scratch/burst_onset_triggers.txt beside it.
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
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
RNG = np.random.default_rng(20260910)
NSHIFT = 400                       # circular-shift surrogates
OUT = []

IMG = {
    "r39":      LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "r5e_v288": LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "r62_v289": LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "r63_v289": LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "r35":      LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
BAND = {"r39": (18.0, 22.0), "r5e_v288": (18.0, 22.0), "r35": (18.0, 22.0),
        "r62_v289": (14.0, 18.0), "r63_v289": (14.0, 18.0)}
BUILD = {"r39": "V282", "r5e_v288": "V288 rev 2", "r62_v289": "V289 rev 1",
         "r63_v289": "V289 rev 1", "r35": "V281 rev 3"}
ROUTES = ("r39", "r5e_v288", "r62_v289", "r63_v289", "r35")

# openpilot rate limit: STEER_DELTA_UP = 3 (Honda bosch, 1/100 s tick) -> the 0xE4 wire step cap.
# The record's figure, used verbatim: |dcmd| >= 122 raw counts/frame (rate_limit = 122.88).
CAP = 122.0
IDX_LSB = 16.125736                 # raw 0xE4 counts per demand-index LSB, live taper arm 255


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ======================================================================================================
# 0  loading
# ======================================================================================================
def load_route(tag):
    """C20.load (dejittered 100 Hz 0x18F frame axis) + the raw 0xE4 stream mapped onto that axis."""
    cells = GI.read_cells(IMG[tag])
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["cells"] = cells
    g["idx_live"], g["sgn_live"] = GI.demand_live(np.round(g["cmd"]), g["bar"], cells)
    D = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    # raw 0xE4 on its own dejittered 100 Hz clock, then sampled onto the 0x18F frame axis by nominal
    # time.  We need the RAW per-frame step, so take the step on the e4 grid and map its TIME across.
    ke4, Pe4, tne4, _ = C20.dejitter(D["te4"], 0.01, 100)
    cmd_e4 = D["cmd"].astype(float)
    g["e4"] = dict(k=ke4, t=tne4, cmd=cmd_e4, P=Pe4,
                   req=D["req"].astype(int) > 0)
    # per-frame command step on the e4 grid, only across CONSECUTIVE frames (k step == 1)
    dk = np.diff(ke4)
    dc = np.diff(cmd_e4)
    ok = dk == 1
    g["e4"]["step_t"] = tne4[1:][ok]          # time of the frame the step LANDS on
    g["e4"]["step"] = dc[ok]
    d2 = np.diff(dc)
    ok2 = (dk[:-1] == 1) & (dk[1:] == 1)
    g["e4"]["d2_t"] = tne4[2:][ok2]
    g["e4"]["d2"] = d2[ok2]
    return g


def marks_of(tag):
    p = os.path.join(C20.CACHE, tag + "_marks.json")
    if not os.path.exists(p):
        return []
    m = json.load(open(p))
    return [x["t_route"] for x in m.get("marks", [])]


# ======================================================================================================
# 1  envelope + onset detector
# ======================================================================================================
def ring_f0(g, lo, hi, idx_min=20.0, nps=1024):
    """DEMAND-GATED pooled spectral peak of the bar inside the band -- the GRINDING mode's frequency.

    The gate matters: the 12-26 Hz band holds TWO lines separable on LKAS demand, not on speed (a
    low-demand 12.4-13.8 Hz road line and the high-demand grinding mode).  A pooled median that
    ignores the gate lands at a spurious ~14.8 Hz -- MODE-NATURE-V289-RECENSUS-2026-09-09.md.
    """
    P = None
    n = 0
    for a, b in C20.runs(g["eng"] & (g["idx_live"] >= idx_min), nps):
        f, p = signal.welch(g["bar"][a:b], fs=FS, nperseg=nps, detrend="constant")
        P = p * (b - a) if P is None else P + p * (b - a)
        n += b - a
    if P is None:                       # fall back to all engaged time
        for a, b in C20.runs(g["eng"], nps):
            f, p = signal.welch(g["bar"][a:b], fs=FS, nperseg=nps, detrend="constant")
            P = p * (b - a) if P is None else P + p * (b - a)
            n += b - a
    m = (f >= lo) & (f <= hi)
    return float(f[m][np.argmax(P[m])])


def demod_env(x, f0, fs, sigma_s=0.035):
    """complex demodulation envelope: zero-phase, time resolution ~sigma, no bandpass group delay.

    z = x * exp(-2*pi*i*f0*t), Gaussian-smoothed (zero phase, symmetric) -> a = 2|z|.
    Effective one-sided bandwidth ~ 1/(2*pi*sigma) = 6.4 Hz at sigma 25 ms, so the whole ring band is
    inside the passband and the ONSET is smeared only +-sigma -- unlike a 4 Hz bandpass, whose own
    impulse response is ~250 ms long and would smear an onset by up to half of that.
    """
    n = len(x)
    t = np.arange(n) / fs
    z = (x - np.mean(x)) * np.exp(-2j * np.pi * f0 * t)
    half = int(np.ceil(3 * sigma_s * fs))
    k = np.arange(-half, half + 1) / fs
    w = np.exp(-0.5 * (k / sigma_s) ** 2)
    w /= w.sum()
    zr = np.convolve(z.real, w, mode="same")
    zi = np.convolve(z.imag, w, mode="same")
    return 2.0 * np.hypot(zr, zi)


def find_onsets(env, eng, fs=FS, hi_q=0.90, hi_abs=50.0, frac=0.30, refrac=0.35, quiet=0.15):
    """burst onsets: peak above threshold, walked back to the leading edge of its own rise.

    hi   = max(hi_abs, quantile hi_q of the ENGAGED envelope) -- a burst must clear both an absolute
           floor (so quiet routes do not manufacture onsets) and the route's own upper decile.
    lo   = frac * hi -- the level whose last upward crossing before the peak IS the onset.
    A candidate is kept only if the envelope sat below `lo` for at least `quiet` s beforehand (so this
    is a burst START, not a re-peak inside one) and no onset was accepted in the previous `refrac` s.
    Returns (onset sample indices, peak sample indices, peak envelope values).
    """
    e = env.copy()
    e[~eng] = 0.0
    hi = max(hi_abs, float(np.quantile(env[eng], hi_q))) if eng.any() else hi_abs
    lo = frac * hi
    above = e >= hi
    d = np.diff(np.r_[0, above.astype(int), 0])
    segs = list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))
    nq = int(quiet * fs)
    nr = int(refrac * fs)
    ons, pks, amps, last = [], [], [], -10 ** 9
    for a, b in segs:
        pk = a + int(np.argmax(e[a:b]))
        thr = max(lo, frac * e[pk])
        i = pk
        while i > 0 and e[i] > thr and eng[i]:
            i -= 1
        if i <= 0 or not eng[i]:
            continue
        if i - nq < 0 or not eng[max(0, i - nq):i].all():
            continue
        if (e[max(0, i - nq):i] > thr).any():
            continue
        if i - last < nr:
            continue
        ons.append(i); pks.append(pk); amps.append(float(e[pk])); last = i
    return np.array(ons, int), np.array(pks, int), np.array(amps, float), hi, lo


# ======================================================================================================
# 2  candidate excitation event series (all returned as SAMPLE INDICES on the 0x18F frame axis)
# ======================================================================================================
def map_e4_times(g, tsel):
    """map a set of 0xE4-clock times onto the 0x18F frame index axis."""
    if len(tsel) == 0:
        return np.zeros(0, int)
    k = np.searchsorted(g["t"], tsel)
    k = np.clip(k, 0, len(g["t"]) - 1)
    return np.unique(k)


def error_stream(g):
    """E = 32*sp - fb on a 1 kHz axis (linear mirror of FUN_00028ea6's E-former), decimated to frames.

    The firmware's floor() in the fb accumulator is dropped here ON PURPOSE: this stream is used only
    for SIGN CHANGES and their times, where a 1-LSB truncation cannot move a crossing by a frame.
    [BELIEF that the approximation is harmless for crossing TIMES; EVIDENCE for the pole values, which
    are read from the build image.]
    """
    c = g["cells"]
    wire1k = C20.up1k(g["wire"])
    x = -wire1k
    st = signal.lfilter([c["fb_b"] / 1024.0], [1.0, -c["fb_a"] / 1024.0], x)
    fb = np.r_[0.0, st[:-1]] + st                      # two-sample sum
    fb = np.clip(fb, -c["fb_clamp"], c["fb_clamp"])
    idx1k = np.repeat(g["idx_live"], 10)[:len(fb)]
    sgn1k = np.repeat(g["sgn_live"], 10)[:len(fb)]
    sp = sgn1k * np.interp(idx1k, c["map_X"], c["map_Y"])
    E = 32 * sp - fb[:len(sp)]
    return E[::10][:len(g["t"])]


def event_series(g):
    """every candidate trigger class, as frame indices."""
    e4 = g["e4"]
    st, stt = e4["step"], e4["step_t"]
    ev = {}
    ev["cap_bind"] = map_e4_times(g, stt[np.abs(st) >= CAP])
    for th in (20, 40, 60, 80, 100):
        ev["dcmd>=%d" % th] = map_e4_times(g, stt[np.abs(st) >= th])
    # demand-index steps: the quantiser's own crossings, through the LIVE arms (taper 255), on the
    # 0xE4 clock with the driver-torque bar carried across by nominal time.
    bar_e4 = np.interp(e4["t"], g["t"], g["bar"])
    idx_e4 = np.round(GI.demand_live(np.round(e4["cmd"]), bar_e4, g["cells"])[0])
    di = np.diff(idx_e4)
    okk = np.diff(e4["k"]) == 1
    ev["idx_step"] = map_e4_times(g, e4["t"][1:][okk & (np.abs(di) >= 1)])
    ev["idx_jump>=4"] = map_e4_times(g, e4["t"][1:][okk & (np.abs(di) >= 4)])
    ev["idx_jump>=7"] = map_e4_times(g, e4["t"][1:][okk & (np.abs(di) >= 7)])
    # sign reversals
    s = np.sign(e4["cmd"])
    ev["cmd_zerocross"] = map_e4_times(g, e4["t"][1:][okk & (s[1:] * s[:-1] < 0)])
    ds = np.sign(st)
    ev["slew_reversal"] = map_e4_times(g, stt[1:][(ds[1:] * ds[:-1] < 0) & (np.abs(st[1:]) >= 20)])
    # second difference
    d2, d2t = e4["d2"], e4["d2_t"]
    for th in (40, 80, 150):
        ev["d2cmd>=%d" % th] = map_e4_times(g, d2t[np.abs(d2) >= th])
    # error sign changes (the loop's own)
    E = error_stream(g)
    sE = np.sign(E)
    ev["E_zerocross"] = np.flatnonzero(np.r_[False, sE[1:] * sE[:-1] < 0])
    # controls
    ev["eng_rise"] = np.flatnonzero(np.r_[False, g["eng"][1:] & ~g["eng"][:-1]])
    ev["eng_fall"] = np.flatnonzero(np.r_[False, ~g["eng"][1:] & g["eng"][:-1]])
    return ev, E


# ======================================================================================================
# 3  hazard ratio with a circular-shift null
# ======================================================================================================
def eng_runs(g, minlen=200):
    return C20.runs(g["eng"], minlen)


def _window_mask(n, ev, w0, w1):
    """boolean mask of samples lying in [ev+w0, ev+w1] for any event."""
    m = np.zeros(n, bool)
    for e in ev:
        a, b = max(0, e + w0), min(n, e + w1 + 1)
        if b > a:
            m[a:b] = True
    return m


def hazard(g, onsets, ev, w0, w1, runs, nshift=NSHIFT):
    """RR = (onset rate inside [ev+w0, ev+w1]) / (onset rate over all engaged time), null = circular
    shift of the ONSET series inside each engaged run (preserves onset count, run structure and the
    within-run clustering of both series; destroys only the alignment).

    Returns dict with n_on, n_in, cover (base rate), RR_obs, RR_null_mean, RR null 95 % band, p.
    """
    n = len(g["t"])
    engm = g["eng"]
    m = _window_mask(n, ev, w0, w1) & engm
    cover = float(m.sum()) / max(1, engm.sum())
    non = len(onsets)
    if non == 0 or cover in (0.0, 1.0):
        return None
    nin = int(m[onsets].sum())
    rr = (nin / non) / cover
    # surrogate: shift onsets circularly inside their own engaged run
    runmap = {}
    for a, b in runs:
        runmap[(a, b)] = onsets[(onsets >= a) & (onsets < b)]
    null = np.empty(nshift)
    for s in range(nshift):
        tot = 0
        for (a, b), o in runmap.items():
            if len(o) == 0:
                continue
            L = b - a
            sh = RNG.integers(0, L)
            oo = a + ((o - a + sh) % L)
            tot += int(m[oo].sum())
        null[s] = (tot / non) / cover
    p = float((np.sum(null >= rr) + 1) / (nshift + 1))
    # bootstrap CI on the observed RR (resample onsets)
    bs = np.empty(2000)
    for s in range(2000):
        j = RNG.integers(0, non, non)
        bs[s] = (m[onsets[j]].sum() / non) / cover
    return dict(n_ev=len(ev), n_on=non, n_in=nin, cover=cover, RR=rr,
                lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                null=float(null.mean()), nlo=float(np.percentile(null, 2.5)),
                nhi=float(np.percentile(null, 97.5)), p=p)


def leadlag(g, onsets, ev, runs, half_ms=500, bin_ms=20, nshift=200):
    """cross-correlogram of onset times about each event, with the same circular-shift null."""
    n = len(g["t"])
    hb = int(half_ms / 10)
    nb = int(bin_ms / 10)
    edges = np.arange(-hb, hb + nb, nb)
    evs = np.asarray(ev)
    if len(evs) == 0 or len(onsets) == 0:
        return None

    def cc(o):
        d = []
        lo_j = np.searchsorted(evs, o - hb, side="left")
        hi_j = np.searchsorted(evs, o + hb, side="right")
        for i, oi in enumerate(o):
            if hi_j[i] > lo_j[i]:
                d.append(oi - evs[lo_j[i]:hi_j[i]])
        d = np.concatenate(d) if d else np.zeros(0)
        return np.histogram(d, bins=edges)[0]

    obs = cc(onsets)
    runmap = [(a, b, onsets[(onsets >= a) & (onsets < b)]) for a, b in runs]
    nul = np.empty((nshift, len(obs)))
    for s in range(nshift):
        oo = []
        for a, b, o in runmap:
            if len(o) == 0:
                continue
            L = b - a
            sh = RNG.integers(0, L)
            oo.append(a + ((o - a + sh) % L))
        oo = np.sort(np.concatenate(oo)) if oo else np.zeros(0, int)
        nul[s] = cc(oo)
    return edges, obs, nul


# ======================================================================================================
# main
# ======================================================================================================
def section1(G):
    pr("=" * 118)
    pr("1  DETECTOR -- envelope, onsets, and validation")
    pr("=" * 118)
    pr("Envelope: complex demodulation at the route's own DEMAND-GATED ring f0, Gaussian sigma 35 ms,")
    pr("Onset   : peak >= max(50 raw, p90 of engaged envelope), walked back to 0.30x of its own peak,")
    pr("          preceded by >= 150 ms below that level, 350 ms refractory.")
    pr("")
    pr("%-10s %-11s %7s %7s %7s %7s %7s %8s %8s %9s" %
       ("route", "build", "f0", "eng_s", "hi", "lo", "N_ons", "ons/min", "IOI_p50", "IOI_p90"))
    pr("-" * 118)
    for tag, g in G.items():
        d = g["det"]
        ioi = np.diff(g["on_t"]) if len(g["on_t"]) > 1 else np.array([np.nan])
        # only intervals inside one engaged run are meaningful
        pr("%-10s %-11s %7.2f %7.0f %7.0f %7.0f %7d %8.2f %8.2f %9.2f" %
           (tag, BUILD[tag], g["f0"], g["eng_s"], d["hi"], d["lo"], len(g["on"]),
            60 * len(g["on"]) / max(1e-9, g["eng_s"]),
            np.nanmedian(ioi), np.nanpercentile(ioi, 90)))
    pr("")
    pr("Inter-onset interval histogram, within-engaged-run intervals only (s):")
    for tag, g in G.items():
        d = []
        for a, b in g["runs"]:
            o = g["on"][(g["on"] >= a) & (g["on"] < b)]
            if len(o) > 1:
                d.extend(np.diff(o) / FS)
        d = np.array(d)
        if len(d) == 0:
            pr("  %-10s (none)" % tag); continue
        h, e = np.histogram(d, bins=[0.35, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 1e9])
        pr("  %-10s n=%4d  p25/p50/p75 %.2f/%.2f/%.2f s   bins .35-.7 .7-1 1-1.5 1.5-2 2-3 3-5 5-10 10+ : %s"
           % (tag, len(d), np.percentile(d, 25), np.percentile(d, 50), np.percentile(d, 75),
              " ".join("%d" % x for x in h)))
    pr("")
    pr("VALIDATION A -- the r35 'pronounced grinding' incident (operator 23:48:21 = route t 1016.7 s;")
    pr("  the record's envelope grows from 41 raw at ~1016.4 to a 500-raw peak at 1017.2):")
    g = G.get("r35")
    if g is not None:
        near = g["on_t"][(g["on_t"] > 1010) & (g["on_t"] < 1022)]
        pk = g["pk_t"][(g["pk_t"] > 1010) & (g["pk_t"] < 1022)]
        pr("  onsets in t 1010-1022 s : %s" % (np.round(near, 2).tolist() or "NONE"))
        pr("  their peak times        : %s" % (np.round(pk, 2).tolist() or "NONE"))
        pr("  their peak envelopes    : %s" % np.round(g["amp"][(g["pk_t"] > 1010) & (g["pk_t"] < 1022)], 0).tolist())
    pr("")
    pr("VALIDATION B -- the operator's own in-drive bookmarks (userBookmark -> route t):")
    for tag, g in G.items():
        mk = marks_of(tag)
        if not mk:
            pr("  %-10s (no bookmarks cached)" % tag); continue
        for m in mk:
            d = g["on_t"] - m
            near = d[np.abs(d) <= 6.0]
            pr("  %-10s mark t=%8.2f s : %2d onsets within +-6 s, nearest %+.2f s, env p90 there %.0f"
               % (tag, m, len(near), near[np.argmin(np.abs(near))] if len(near) else np.nan,
                  np.percentile(g["env"][max(0, int((m - 3) * FS)):int((m + 3) * FS)], 90)))
    pr("")


def section2(G):
    pr("=" * 118)
    pr("2  EVENTS -- candidate excitation classes and their BASE RATES (engaged frames only)")
    pr("=" * 118)
    keys = list(next(iter(G.values()))["ev"].keys())
    pr("%-16s" % "class" + "".join("%12s" % t for t in G))
    pr("%-16s" % "" + "".join("%12s" % "n/s eng" for t in G))
    pr("-" * 118)
    for k in keys:
        row = "%-16s" % k
        for tag, g in G.items():
            e = g["ev"][k]
            e = e[g["eng"][np.clip(e, 0, len(g["eng"]) - 1)]]
            row += "%12.3f" % (len(e) / max(1e-9, g["eng_s"]))
        pr(row)
    pr("")
    pr("Duty of the +-(0,+120 ms] window each class covers of engaged time -- the null a coincidence")
    pr("must beat.  A class covering 70 % of engaged time CANNOT show a large hazard ratio.")
    pr("%-16s" % "class" + "".join("%12s" % t for t in G))
    pr("-" * 118)
    for k in keys:
        row = "%-16s" % k
        for tag, g in G.items():
            m = _window_mask(len(g["t"]), g["ev"][k], 0, 12) & g["eng"]
            row += "%12.3f" % (m.sum() / max(1, g["eng"].sum()))
        pr(row)
    pr("")


def section3(G, windows):
    pr("=" * 118)
    pr("3  HAZARD -- onset rate inside a window after each event, vs a circular-shift null")
    pr("=" * 118)
    pr("RR = P(onset | in window) / P(onset | engaged), normalised by window coverage.  RR = 1 means")
    pr("'exactly what chance gives'.  CI is a 2000-draw bootstrap over onsets; the null column is the")
    pr("mean and 95 %% band of %d circular-shift surrogates; p is one-sided (RR >= obs under the null)." % NSHIFT)
    res = {}
    for w0, w1, lab in windows:
        pr("")
        pr("--- window %s (event at 0; positive = onset AFTER the event) ---" % lab)
        pr("%-10s %-16s %6s %5s %5s %7s %7s %-17s %8s %8s" %
           ("route", "class", "n_ev", "n_on", "n_in", "cover", "RR", "  95% CI", "null", "p"))
        pr("-" * 118)
        for tag, g in G.items():
            for k in g["ev"]:
                h = hazard(g, g["on"], g["ev"][k], w0, w1, g["runs"])
                if h is None:
                    continue
                res[(tag, k, lab)] = h
                star = " *" if h["p"] <= 0.05 else ""
                pr("%-10s %-16s %6d %5d %5d %7.3f %7.2f  [%5.2f,%5.2f] %8.2f %8.3f%s" %
                   (tag, k, h["n_ev"], h["n_on"], h["n_in"], h["cover"], h["RR"],
                    h["lo"], h["hi"], h["null"], h["p"], star))
    pr("")
    return res


def section4(G, classes):
    pr("=" * 118)
    pr("4  LEAD/LAG -- full +-500 ms cross-correlogram, 20 ms bins, vs the circular-shift null")
    pr("=" * 118)
    pr("Each row is one class on one route: observed count per bin, and the bin's z against the null.")
    pr("A TRIGGER shows a sharp excess in the bins just AFTER 0 (onset follows event).  An ECHO shows")
    pr("it just BEFORE 0.  A shared slow driver shows a broad, flat excess with no peak.")
    for tag, g in G.items():
        for k in classes:
            if k not in g["ev"]:
                continue
            r = leadlag(g, g["on"], g["ev"][k], g["runs"])
            if r is None:
                continue
            edges, obs, nul = r
            mu, sd = nul.mean(0), nul.std(0) + 1e-9
            z = (obs - mu) / sd
            ctr = (edges[:-1] + (edges[1] - edges[0]) / 2.0) * 10.0
            pr("")
            pr("  %s / %s   (n_ev %d, n_on %d)" % (tag, k, len(g["ev"][k]), len(g["on"])))
            pr("    lag ms : " + " ".join("%6.0f" % c for c in ctr))
            pr("    obs    : " + " ".join("%6d" % c for c in obs))
            pr("    null mu: " + " ".join("%6.1f" % c for c in mu))
            pr("    z      : " + " ".join("%6.1f" % c for c in z))
    pr("")


def section5(G):
    pr("=" * 118)
    pr("5  DOSE-RESPONSE -- onsets/s vs command-slew statistics, stratified on speed x demand index")
    pr("=" * 118)
    pr("5 s engaged windows.  Strata: speed {0-3,3-8,8-15,15-40 m/s} x idx p50 {0-5,5-20,20-60,60+}.")
    pr("Within each stratum, windows are split at the stratum median of the slew statistic and the")
    pr("onset rate compared; the pooled row is a Mantel-Haenszel-style sum over strata (so the known")
    pr("engaged/manual speed confound and the low-demand road line cannot drive it).")
    WIN = int(5 * FS)
    vb = [0, 3, 8, 15, 1e9]
    ib = [0, 5, 20, 60, 1e9]
    for tag, g in G.items():
        rows = []
        for a, b in g["runs"]:
            for s in range(a, b - WIN + 1, WIN):
                e = s + WIN
                sl = slice(s, e)
                st = g["step_f"][sl]
                rows.append(dict(
                    v=float(np.median(g["vego"][sl])), idx=float(np.median(g["idx_live"][sl])),
                    rms=float(np.sqrt(np.mean(st ** 2))),
                    cap=float(np.mean(np.abs(st) >= CAP)),
                    idxr=float(np.mean(np.abs(np.diff(np.floor(np.abs(np.round(g["cmd"][sl])) / IDX_LSB))) >= 1)),
                    d2=float(np.sqrt(np.mean(np.diff(st) ** 2))),
                    n=int(((g["on"] >= s) & (g["on"] < e)).sum())))
        if not rows:
            continue
        pr("")
        pr("  --- %s (%s), %d windows of 5 s ---" % (tag, BUILD[tag], len(rows)))
        pr("  %-8s %6s %6s %6s %6s %8s %8s %8s" %
           ("stat", "strata", "n_lo", "n_hi", "ons_lo", "ons_hi", "rate_lo", "rate_hi"))
        for stat in ("rms", "cap", "idxr", "d2"):
            nlo = nhi = olo = ohi = 0
            nstr = 0
            for i in range(4):
                for j in range(4):
                    sub = [r for r in rows if vb[i] <= r["v"] < vb[i + 1] and ib[j] <= r["idx"] < ib[j + 1]]
                    if len(sub) < 8:
                        continue
                    med = np.median([r[stat] for r in sub])
                    lo = [r for r in sub if r[stat] <= med]
                    hi = [r for r in sub if r[stat] > med]
                    if not lo or not hi:
                        continue
                    nstr += 1
                    nlo += len(lo); nhi += len(hi)
                    olo += sum(r["n"] for r in lo); ohi += sum(r["n"] for r in hi)
            if nstr == 0:
                continue
            rl = olo / max(1e-9, nlo * 5.0); rh = ohi / max(1e-9, nhi * 5.0)
            pr("  %-8s %6d %6d %6d %6d %8d %8.4f %8.4f   ratio hi/lo = %.2f" %
               (stat, nstr, nlo, nhi, olo, ohi, rl, rh, rh / max(1e-9, rl)))
    pr("")


# ======================================================================================================
# 6  THE FALSIFIER -- is the ROAD the trigger instead?
# ======================================================================================================
def load_imu(tag, g):
    p = os.path.join(SCR, "imu_%s.npz" % tag)
    if not os.path.exists(p):
        return None
    D = dict(np.load(p))
    if len(D["at"]) == 0 or len(D["t18"]) == 0:
        return None
    # both caches timestamp with logMonoTime, so the raw 0x18F t0 is a common origin
    Draw = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    t0 = Draw["t18"][0]
    out = {}
    for nm, tk, vk in (("a", "at", "av"), ("g", "gt", "gv")):
        t = D[tk] - t0
        v = D[vk]
        if len(t) < 100:
            continue
        ok = np.argsort(t)
        t, v = t[ok], v[ok]
        fs = 1.0 / np.median(np.diff(t))
        tu = np.arange(t[0], t[-1], 1.0 / fs)
        vu = np.stack([np.interp(tu, t, v[:, i]) for i in range(v.shape[1])], 1)
        out[nm] = dict(t=tu, v=vu, fs=fs)
    return out


def impulse_events(t, x, fs, hp=5.0, q=0.99, refrac=0.20):
    """road-impulse events: high-passed |signal| envelope peaks above its own q-quantile."""
    sos = signal.butter(4, hp, btype="highpass", fs=fs, output="sos")
    y = np.abs(signal.sosfiltfilt(sos, x))
    w = np.ones(max(1, int(0.03 * fs))) / max(1, int(0.03 * fs))
    e = np.convolve(y, w, mode="same")
    thr = np.quantile(e, q)
    pk, _ = signal.find_peaks(e, height=thr, distance=int(refrac * fs))
    return t[pk], e, thr


def section6(G):
    pr("=" * 118)
    pr("6  THE FALSIFIER -- is the ROAD the trigger?  Device IMU impulses vs burst onsets")
    pr("=" * 118)
    pr("Road-impulse events = peaks of the 30 ms envelope of the >5 Hz-high-passed channel above that")
    pr("channel's own p99, 200 ms refractory.  Same hazard machinery, same circular-shift null, same")
    pr("[0,+120] ms window.  A ROAD trigger would show RR >> 1 here and RR ~ 1 on every command class.")
    pr("")
    pr("%-10s %-14s %6s %6s %5s %5s %7s %7s %-17s %8s" %
       ("route", "channel", "fs", "n_ev", "n_on", "n_in", "cover", "RR", "  95% CI", "p"))
    pr("-" * 118)
    CH = [("a", 0, "accel_x(long)"), ("a", 1, "accel_y(lat)"), ("a", 2, "accel_z(vert)"),
          ("g", 0, "gyro_x(roll)"), ("g", 1, "gyro_y(pitch)"), ("g", 2, "gyro_z(yaw)")]
    for tag, g in G.items():
        I = load_imu(tag, g)
        if I is None:
            pr("%-10s (no IMU cache)" % tag); continue
        for nm, j, lab in CH:
            if nm not in I:
                continue
            d = I[nm]
            te, e, thr = impulse_events(d["t"], d["v"][:, j], d["fs"])
            ev = np.unique(np.clip(np.searchsorted(g["tr"], te), 0, len(g["tr"]) - 1))
            h = hazard(g, g["on"], ev, 0, 12, g["runs"])
            if h is None:
                pr("%-10s %-14s %6.1f (degenerate)" % (tag, lab, d["fs"])); continue
            star = " *" if h["p"] <= 0.05 else ""
            pr("%-10s %-14s %6.1f %6d %5d %5d %7.3f %7.2f  [%5.2f,%5.2f] %8.3f%s" %
               (tag, lab, d["fs"], h["n_ev"], h["n_on"], h["n_in"], h["cover"], h["RR"],
                h["lo"], h["hi"], h["p"], star))
    pr("")
    pr("AND the direct check the r35 incident already made: is the ring band PRESENT on the chassis at")
    pr("an onset at all?  Ratio of the in-band IMU rms in [onset, onset+300 ms] to matched engaged")
    pr("baseline.  A ratio of ~1 means the chassis never sees the mode, so the ring is torsional only.")
    pr("%-10s %-14s %10s %10s %8s" % ("route", "channel", "at onset", "baseline", "ratio"))
    pr("-" * 118)
    for tag, g in G.items():
        I = load_imu(tag, g)
        if I is None:
            continue
        lo, hi = BAND[tag]
        for nm, j, lab in CH[1:]:
            if nm not in I:
                continue
            d = I[nm]
            sos = signal.butter(4, [lo, hi], btype="bandpass", fs=d["fs"], output="sos")
            y = signal.sosfiltfilt(sos, d["v"][:, j])
            eng_t = g["tr"][g["eng"]]
            base = np.interp(d["t"], g["tr"], g["eng"].astype(float)) > 0.5
            m = np.zeros(len(d["t"]), bool)
            for ot in g["on_t"]:
                m |= (d["t"] >= ot) & (d["t"] < ot + 0.30)
            if m.sum() < 10 or (base & ~m).sum() < 10:
                continue
            a_on = float(np.sqrt(np.mean(y[m & base] ** 2)))
            a_bg = float(np.sqrt(np.mean(y[base & ~m] ** 2)))
            pr("%-10s %-14s %10.5f %10.5f %8.2f" % (tag, lab, a_on, a_bg, a_on / max(1e-12, a_bg)))
    pr("")


# ======================================================================================================
# 7  SIZING -- what a Q ~ 17 ring needs, vs what a capped command step actually injects
# ======================================================================================================
def resonator(f0, zeta, fs):
    """continuous 2nd-order resonance ωn²/(s²+2ζωn s+ωn²), DC gain 1, discretised (bilinear)."""
    wn = 2 * np.pi * f0
    return signal.bilinear([wn ** 2], [1.0, 2 * zeta * wn, wn ** 2], fs)


def section7(G, fast=False):
    pr("=" * 118)
    pr("7  SIZING -- an impulse framing does NOT buy a factor of Q.  The arithmetic, shown.")
    pr("=" * 118)
    zeta = 0.029
    for tag in ("r39", "r63_v289"):
        g = G[tag]
        f0 = g["f0"]
        wn = 2 * np.pi * f0
        b, a = resonator(f0, zeta, FS1K)
        n = int(3.0 * FS1K)
        u = np.zeros(n); u[100] = 1.0 * FS1K          # unit-AREA impulse (height 1/dt)
        y = signal.lfilter(b, a, u)
        env = np.abs(signal.hilbert(y))
        pr("")
        pr("  --- %s (%s), f0 %.2f Hz, zeta %.3f (Q %.1f) ---" % (tag, BUILD[tag], f0, zeta, 1 / (2 * zeta)))
        pr("  closed form   : peak of the impulse response of a unit-AREA impulse = wn/sqrt(1-z^2) = %.1f /s" % (wn / np.sqrt(1 - zeta ** 2)))
        pr("  numeric       : %.1f   (ringdown to 1/e in %.0f ms = %.1f cycles)"
           % (env.max(), 1000 / (zeta * wn), 1 / (2 * np.pi * zeta)))
        pr("  => a SINGLE-FRAME (10 ms) kick of height h delivers area h*0.01 and rings to a PEAK of")
        pr("     h*0.01*%.1f = %.2f * h.  A Q = %.0f resonance gives the ring its LENGTH (%.1f cycles),"
           % (wn, 0.01 * wn, 1 / (2 * zeta), 1 / (2 * np.pi * zeta)))
        pr("     NOT a factor of %.0f in AMPLITUDE over the kick that started it." % (1 / (2 * zeta)))
        # repeated kicks: random phase vs phase-locked at f0
        for lab, mode in (("random-phase Poisson train", "rand"), ("PHASE-LOCKED at f0", "lock")):
            for rate in (4.0, 8.0, f0):
                m = np.zeros(n)
                if mode == "rand":
                    kk = np.sort(RNG.choice(np.arange(50, n - 50), max(1, int(rate * n / FS1K)), replace=False))
                    m[kk] = 1.0 * FS1K
                else:
                    kk = np.arange(100, n - 50, int(FS1K / rate))
                    m[kk] = 1.0 * FS1K
                yy = signal.lfilter(b, a, m)
                ee = np.abs(signal.hilbert(yy))
                pr("     %-26s %5.1f kicks/s -> peak envelope %7.1f  = x%.2f of one kick"
                   % (lab, rate, ee.max(), ee.max() / env.max()))
        pr("  ANALYTIC CHECK of the phase-locked accumulation ceiling: kicks once per ring cycle")
        pr("     accumulate geometrically with r = exp(-2*pi*zeta) = %.3f, so the ceiling is"
           % np.exp(-2 * np.pi * zeta))
        pr("     1/(1-r) = %.2f, not Q = %.1f.  And phase-locked kicks at f0 ARE the closed-loop"
           % (1 / (1 - np.exp(-2 * np.pi * zeta)), 1 / (2 * zeta)))
        pr("     de-damping picture already in the record -- the command would be an ECHO, not a cause.")
    pr("")
    pr("WHAT A CAPPED COMMAND STEP ACTUALLY INJECTS -- byte-exact 1 kHz mirror (GI.simulate, live arms).")
    pr("A single frame of the command is displaced by +CAP counts and held (a slew-capped frame); every")
    pr("other input -- the measured wire rate, the bar, the engagement -- is left exactly as measured.")
    pr("The difference in the delivered torque T is the kick the step really lands on the plant.")
    pr("%-10s %8s %10s %10s %10s %12s %12s" %
       ("route", "n_win", "dT_peak", "dT_band", "T_band", "ring_env", "kick/ring"))
    pr("-" * 118)
    for tag in ("r39", "r5e_v288", "r63_v289"):
        g = G[tag]
        lo, hi = BAND[tag]
        rows = []
        # pick windows at the top of the onset amplitude distribution -- the loud grinding seconds
        sel = g["pk"][np.argsort(g["amp"])[-8:]] if len(g["pk"]) >= 8 else g["pk"]
        for p0 in sel:
            a0, b0 = p0 - 150, p0 + 150
            if a0 < 60 or b0 > len(g["t"]) - 20 or not g["eng"][a0:b0].all():
                continue
            g2 = dict(g)
            c2 = g["cmd"].copy()
            c2[p0:] += CAP * np.sign(c2[p0] if c2[p0] != 0 else 1.0)
            g2["cmd"] = c2
            S0 = GI.simulate(g, a0, b0, g["cells"])
            S1 = GI.simulate(g2, a0, b0, g["cells"])
            dT = S1["T"] - S0["T"]
            sos = signal.butter(4, [lo, hi], btype="bandpass", fs=FS1K, output="sos")
            dTb = signal.sosfiltfilt(sos, dT)
            Tb = signal.sosfiltfilt(sos, S0["T"])
            rows.append((np.abs(dT).max(), np.abs(signal.hilbert(dTb)).max(),
                         np.sqrt(np.mean(Tb ** 2)) * np.sqrt(2), g["env"][p0]))
        if not rows:
            pr("%-10s (no clean window)" % tag); continue
        R = np.array(rows)
        pr("%-10s %8d %10.1f %10.2f %10.1f %12.1f %12.3f" %
           (tag, len(R), np.median(R[:, 0]), np.median(R[:, 1]), np.median(R[:, 2]),
            np.median(R[:, 3]), np.median(R[:, 1]) / max(1e-9, np.median(R[:, 2]))))
    pr("")


# ======================================================================================================
# 8  POOLED hazard across routes + the POWER the corpus actually has
# ======================================================================================================
def section8(G, classes, w0=0, w1=12, nboot=4000):
    pr("=" * 118)
    pr("8  POOLED across all five routes -- and what effect size this corpus could actually SEE")
    pr("=" * 118)
    pr("Pooling: sum onsets-in-window and sum expected (cover x n_on) over routes, so each route enters")
    pr("weighted by its own coverage.  CI: 4000 bootstrap draws resampling ONSETS within route.")
    pr("MDE = the smallest true RR this corpus would reject RR=1 against, at 80 %% power, 5 %% one-sided,")
    pr("     from the pooled expected count alone (sqrt of a Poisson).")
    pr("")
    pr("%-16s %7s %8s %9s %8s %-17s %9s %9s" %
       ("class", "n_on", "n_in", "expected", "RR", "  95% CI", "p(perm)", "MDE"))
    pr("-" * 118)
    for k in classes:
        tot_in = tot_exp = tot_on = 0
        parts = []
        for tag, g in G.items():
            if k not in g["ev"]:
                continue
            n = len(g["t"])
            m = _window_mask(n, g["ev"][k], w0, w1) & g["eng"]
            cov = m.sum() / max(1, g["eng"].sum())
            on = g["on"]
            tot_in += int(m[on].sum()); tot_exp += cov * len(on); tot_on += len(on)
            parts.append((m, on, cov, g["runs"]))
        if tot_exp <= 0:
            continue
        rr = tot_in / tot_exp
        bs = np.empty(nboot)
        for s in range(nboot):
            a = e = 0.0
            for m, on, cov, _ in parts:
                j = RNG.integers(0, len(on), len(on))
                a += m[on[j]].sum(); e += cov * len(on)
            bs[s] = a / e
        # circular-shift permutation across all routes jointly
        nul = np.empty(400)
        for s in range(400):
            a = 0.0
            for m, on, cov, runs in parts:
                for aa, bb in runs:
                    o = on[(on >= aa) & (on < bb)]
                    if len(o) == 0:
                        continue
                    L = bb - aa
                    a += m[aa + ((o - aa + RNG.integers(0, L)) % L)].sum()
            nul[s] = a / tot_exp
        p = float((np.sum(nul >= rr) + 1) / 401)
        mde = 1.0 + (1.645 + 0.84) / np.sqrt(tot_exp)
        c = tot_exp / tot_on
        f = lambda R: max(0.0, c * (R - 1.0) / (1.0 - c))          # noqa: E731
        pr("%-16s %7d %8d %9.1f %8.2f  [%5.2f,%5.2f] %9.3f %9.2f   f_trig %.3f [%.3f,%.3f]" %
           (k, tot_on, tot_in, tot_exp, rr, np.percentile(bs, 2.5), np.percentile(bs, 97.5), p, mde,
            f(rr), f(np.percentile(bs, 2.5)), f(np.percentile(bs, 97.5))))
    pr("")
    pr("f_trig = the ATTRIBUTABLE FRACTION: the share of onsets that could be caused by this event")
    pr("class.  Model: a fraction f is triggered (and so lands in the window with probability 1); the")
    pr("rest fall at chance (probability = coverage c).  Observed in-window share p = f + (1-f)c, and")
    pr("RR = p/c, so f = c(RR-1)/(1-c).  This is the number that matters for a build decision: it says")
    pr("how much of the symptom removing the event class could possibly buy.")
    pr("")


# ======================================================================================================
# 9  ONSET-TRIGGERED AVERAGES -- the most direct picture: what does the command DO around an onset?
# ======================================================================================================
def ota(g, sig, half_s, bin_s, nshift=200):
    """average of `sig` in bins about each onset, with a circular-shift null band."""
    fs = FS
    hb = int(half_s * fs)
    nb = max(1, int(bin_s * fs))
    nbin = 2 * hb // nb
    n = len(sig)

    def avg(o):
        o = o[(o >= hb) & (o < n - hb)]
        if len(o) == 0:
            return np.full(nbin, np.nan)
        idxm = o[:, None] + np.arange(-hb, hb)[None, :]
        okm = g["eng"][idxm]
        X = np.where(okm, sig[idxm], np.nan)
        X = X[:, :nbin * nb].reshape(len(o), nbin, nb)
        return np.nanmean(np.nanmean(X, 2), 0)

    obs = avg(g["on"])
    nul = np.empty((nshift, nbin))
    for s in range(nshift):
        oo = []
        for a, b in g["runs"]:
            o = g["on"][(g["on"] >= a) & (g["on"] < b)]
            if len(o) == 0:
                continue
            L = b - a
            oo.append(a + ((o - a + RNG.integers(0, L)) % L))
        oo = np.sort(np.concatenate(oo)) if oo else np.zeros(0, int)
        nul[s] = avg(oo)
    return obs, nul


def section9(G):
    pr("=" * 118)
    pr("9  ONSET-TRIGGERED AVERAGES -- the direct picture, magnitude not threshold")
    pr("=" * 118)
    pr("For each onset, the average of a command statistic in bins around it, minus the circular-shift")
    pr("null mean, in units of the null's own sd (z).  This uses MAGNITUDE, so it is strictly more")
    pr("sensitive than any thresholded event class, and it separates the two hypotheses cleanly:")
    pr("  A TRIGGER   -> a SHARP, ONE-BIN spike in the 0-100 ms BEFORE the onset, flat elsewhere.")
    pr("  A REGIME    -> a BROAD, SLOW elevation over seconds, with no step at the onset itself.")
    pr("")
    for half, bs, lab in ((0.30, 0.02, "FINE  +-300 ms, 20 ms bins"), (3.0, 0.25, "COARSE +-3 s, 250 ms bins")):
        pr("--- %s ---" % lab)
        for tag, g in G.items():
            st = np.abs(g["step_f"])
            sigs = {"|dcmd|": st,
                    "cap_duty": (st >= CAP).astype(float),
                    "|d2cmd|": np.abs(np.r_[0.0, np.diff(g["step_f"])]),
                    "idx": g["idx_live"],
                    "|wheel rate|": np.abs(g["wire"]) / V.CPD,
                    "|bar|": np.abs(g["bar"]),
                    "v": g["vego"]}
            for nm, s in sigs.items():
                obs, nul = ota(g, s, half, bs)
                mu, sd = np.nanmean(nul, 0), np.nanstd(nul, 0) + 1e-12
                z = (obs - mu) / sd
                ctr = (np.arange(len(z)) - len(z) / 2 + 0.5) * bs * 1000
                pr("  %-10s %-12s base %9.3f   z: %s"
                   % (tag, nm, np.nanmean(mu), " ".join("%5.1f" % v for v in z)))
            pr("  %-10s %-12s        %9s   ms: %s"
               % ("", "", "", " ".join("%5.0f" % c for c in ctr)))
            pr("")
    pr("")


# ======================================================================================================
# 10  DOSE-RESPONSE with a confidence interval, and the IMU control band
# ======================================================================================================
def section10(G):
    pr("=" * 118)
    pr("10  DOSE-RESPONSE with a CI, and the IMU band-specificity control")
    pr("=" * 118)
    WIN = int(5 * FS)
    vb = [0, 3, 8, 15, 1e9]
    ib = [0, 5, 20, 60, 1e9]
    pr("Stratified hi/lo onset-rate ratio (5 s windows, strata = speed x demand index), with a 2000-")
    pr("draw bootstrap over WINDOWS inside each stratum.  This is a SECONDS-scale association; it is")
    pr("not evidence of frame-scale triggering (section 9 separates the two).")
    pr("")
    pr("%-10s %-8s %8s %9s %9s %-17s" % ("route", "stat", "n_win", "rate_lo", "rate_hi", "  ratio [95% CI]"))
    pr("-" * 118)
    allrows = {}
    for tag, g in G.items():
        rows = []
        for a, b in g["runs"]:
            for s in range(a, b - WIN + 1, WIN):
                e = s + WIN
                sl = slice(s, e)
                st = g["step_f"][sl]
                rows.append(dict(
                    v=float(np.median(g["vego"][sl])), idx=float(np.median(g["idx_live"][sl])),
                    rms=float(np.sqrt(np.mean(st ** 2))), cap=float(np.mean(np.abs(st) >= CAP)),
                    idxr=float(np.mean(np.abs(np.diff(np.floor(np.abs(np.round(g["cmd"][sl])) / IDX_LSB))) >= 1)),
                    d2=float(np.sqrt(np.mean(np.diff(st) ** 2))),
                    n=int(((g["on"] >= s) & (g["on"] < e)).sum())))
        allrows[tag] = rows
        for stat in ("rms", "cap", "idxr", "d2"):
            strata = []
            for i in range(4):
                for j in range(4):
                    sub = [r for r in rows if vb[i] <= r["v"] < vb[i + 1] and ib[j] <= r["idx"] < ib[j + 1]]
                    if len(sub) < 8:
                        continue
                    med = np.median([r[stat] for r in sub])
                    lo = [r for r in sub if r[stat] <= med]
                    hi = [r for r in sub if r[stat] > med]
                    if lo and hi:
                        strata.append((lo, hi))
            if not strata:
                continue

            def ratio(draw=False):
                nl = nh = ol = oh = 0
                for lo, hi in strata:
                    L = [lo[k] for k in RNG.integers(0, len(lo), len(lo))] if draw else lo
                    H = [hi[k] for k in RNG.integers(0, len(hi), len(hi))] if draw else hi
                    nl += len(L); nh += len(H)
                    ol += sum(r["n"] for r in L); oh += sum(r["n"] for r in H)
                return (oh / max(1e-9, nh)) / max(1e-9, (ol / max(1e-9, nl))), ol / (nl * 5.0), oh / (nh * 5.0)
            r0, rl, rh = ratio()
            bs = np.array([ratio(True)[0] for _ in range(2000)])
            pr("%-10s %-8s %8d %9.4f %9.4f   %.2f [%.2f,%.2f]" %
               (tag, stat, sum(len(l) + len(h) for l, h in strata), rl, rh, r0,
                np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    pr("")
    pr("IMU BAND-SPECIFICITY CONTROL -- if the chassis elevation at onsets is the RING, it must be")
    pr("larger in the ring band than in a control band at the same time.  ratio_ring / ratio_control")
    pr("near 1 means the chassis is just BROADBAND busier during bursts, i.e. not the mode.")
    pr("%-10s %-14s %10s %10s %10s" % ("route", "channel", "ring", "ctrl 28-38", "ring/ctrl"))
    pr("-" * 118)
    for tag, g in G.items():
        I = load_imu(tag, g)
        if I is None:
            continue
        lo, hi = BAND[tag]
        for nm, j, lab in (("a", 1, "accel_y(lat)"), ("a", 2, "accel_z(vert)"), ("g", 0, "gyro_x(roll)")):
            if nm not in I:
                continue
            d = I[nm]
            base = np.interp(d["t"], g["tr"], g["eng"].astype(float)) > 0.5
            m = np.zeros(len(d["t"]), bool)
            for ot in g["on_t"]:
                m |= (d["t"] >= ot) & (d["t"] < ot + 0.30)
            if m.sum() < 10 or (base & ~m).sum() < 10:
                continue
            out = []
            for bl, bh in ((lo, hi), (28.0, 38.0)):
                sos = signal.butter(4, [bl, min(bh, d["fs"] / 2 - 2)], btype="bandpass", fs=d["fs"], output="sos")
                y = signal.sosfiltfilt(sos, d["v"][:, j])
                out.append(np.sqrt(np.mean(y[m & base] ** 2)) / np.sqrt(np.mean(y[base & ~m] ** 2)))
            pr("%-10s %-14s %10.2f %10.2f %10.2f" % (tag, lab, out[0], out[1], out[0] / out[1]))
    pr("")


# ======================================================================================================
# 11  DIRECTION -- does the command LEAD the ring, or FOLLOW it?
# ======================================================================================================
def section11(G):
    pr("=" * 118)
    pr("11  DIRECTION -- the crux.  Does command activity LEAD the burst (trigger) or FOLLOW it (echo)?")
    pr("=" * 118)
    pr("11a  PRE/POST ASYMMETRY at each onset.  For every onset, the mean of a command statistic over")
    pr("     [-300,-100] ms (before) and over [+100,+300] ms (after).  A TRIGGER puts the excess BEFORE;")
    pr("     an ECHO puts it AFTER.  The null is the same circular shift, so the CI is on the DIFFERENCE.")
    pr("")
    pr("%-10s %-12s %10s %10s %10s %-19s %9s" %
       ("route", "stat", "pre", "post", "post-pre", "  95% CI (perm)", "p_echo"))
    pr("-" * 118)
    agg = {}
    for tag, g in G.items():
        st = np.abs(g["step_f"])
        sigs = {"|dcmd|": st, "cap_duty": (st >= CAP).astype(float),
                "|d2cmd|": np.abs(np.r_[0.0, np.diff(g["step_f"])])}
        for nm, s in sigs.items():
            n = len(s)
            a0, a1, b0, b1 = 30, 10, 10, 30      # frames: pre = [-300,-100], post = [+100,+300]

            def stat(o):
                o = o[(o >= 40) & (o < n - 40)]
                if len(o) == 0:
                    return np.nan, np.nan
                pre = np.array([np.nanmean(np.where(g["eng"][k - a0:k - a1], s[k - a0:k - a1], np.nan)) for k in o])
                post = np.array([np.nanmean(np.where(g["eng"][k + b0:k + b1], s[k + b0:k + b1], np.nan)) for k in o])
                return np.nanmean(pre), np.nanmean(post)
            pre, post = stat(g["on"])
            d = post - pre
            nul = []
            for _ in range(300):
                oo = []
                for a, b in g["runs"]:
                    o = g["on"][(g["on"] >= a) & (g["on"] < b)]
                    if len(o) == 0:
                        continue
                    L = b - a
                    oo.append(a + ((o - a + RNG.integers(0, L)) % L))
                oo = np.sort(np.concatenate(oo)) if oo else np.zeros(0, int)
                p0, p1 = stat(oo)
                nul.append(p1 - p0)
            nul = np.array(nul)
            p = float((np.sum(nul >= d) + 1) / 301)
            pr("%-10s %-12s %10.3f %10.3f %10.3f   [%6.3f,%6.3f] %9.3f%s" %
               (tag, nm, pre, post, d, np.percentile(nul, 2.5), np.percentile(nul, 97.5), p,
                " *" if p <= 0.05 else ""))
            agg.setdefault(nm, []).append((d, nul))
    pr("")
    pr("  POOLED over the five routes (equal weight), same permutation null:")
    for nm, rows in agg.items():
        d = np.mean([r[0] / max(1e-9, abs(np.std(r[1]))) for r in rows])     # z per route, averaged
        pr("    %-12s mean z(post-pre) over routes = %+.2f" % (nm, d))
    pr("")
    pr("11b  FULL CROSS-CORRELATION, engaged data only -- much higher power than any onset statistic,")
    pr("     because it uses every sample, not just the %d-%d detected onsets per route." % (78, 134))
    pr("     r(lag) between the ring ENVELOPE and |dcmd|.  POSITIVE lag = the command comes LATER, i.e.")
    pr("     the ENVELOPE LEADS = ECHO.  NEGATIVE lag = the command comes FIRST = TRIGGER.")
    pr("")
    pr("%-10s %12s %12s %12s %12s %12s" %
       ("route", "peak lag ms", "r at peak", "r at -50ms", "r at 0", "r at +50ms"))
    pr("-" * 118)
    for tag, g in G.items():
        st = np.abs(g["step_f"]).copy()
        en = g["env"].copy()
        m = g["eng"]
        # de-mean inside engaged runs, zero elsewhere, so gaps contribute nothing
        a = np.zeros(len(en)); b = np.zeros(len(en))
        for aa, bb in g["runs"]:
            a[aa:bb] = en[aa:bb] - en[aa:bb].mean()
            b[aa:bb] = st[aa:bb] - st[aa:bb].mean()
        L = 50
        num = np.array([np.dot(a[max(0, -k):len(a) - max(0, k)], b[max(0, k):len(b) - max(0, -k)])
                        for k in range(-L, L + 1)])
        den = np.sqrt(np.dot(a, a) * np.dot(b, b))
        r = num / den
        lags = np.arange(-L, L + 1) * 10.0
        # sign convention: r[k] = <env(t) * dcmd(t+k)>, so k > 0 means dcmd comes AFTER env
        j = int(np.argmax(r))
        pr("%-10s %12.0f %12.4f %12.4f %12.4f %12.4f" %
           (tag, lags[j], r[j], r[L - 5], r[L], r[L + 5]))
    pr("")
    pr("  full curve, r x 1000, lag ms (positive = command AFTER the ring envelope):")
    for tag, g in G.items():
        st = np.abs(g["step_f"])
        en = g["env"]
        a = np.zeros(len(en)); b = np.zeros(len(en))
        for aa, bb in g["runs"]:
            a[aa:bb] = en[aa:bb] - en[aa:bb].mean()
            b[aa:bb] = st[aa:bb] - st[aa:bb].mean()
        L = 40
        num = np.array([np.dot(a[max(0, -k):len(a) - max(0, k)], b[max(0, k):len(b) - max(0, -k)])
                        for k in range(-L, L + 1, 4)])
        den = np.sqrt(np.dot(a, a) * np.dot(b, b))
        r = 1000 * num / den
        if tag == ROUTES[0]:
            pr("    %-10s %s" % ("lag ms", " ".join("%5d" % (k * 10) for k in range(-L, L + 1, 4))))
        pr("    %-10s %s" % (tag, " ".join("%5.0f" % v for v in r)))
    pr("")


# ======================================================================================================
# 12  DIRECTION, DONE PROPERLY -- 11a is CONFOUNDED; this is the test that is not
# ======================================================================================================
def section12(G):
    pr("=" * 118)
    pr("12  DIRECTION, DONE PROPERLY.  *** 11a IS CONFOUNDED AND MUST NOT BE READ AS AN ECHO. ***")
    pr("=" * 118)
    pr("Why 11a cannot decide direction: an onset is DEFINED as a point where the envelope goes from")
    pr("low to high.  |dcmd| correlates with the envelope at r ~ 0.21-0.35 at ZERO lag (11b).  So")
    pr("|dcmd| is MECHANICALLY lower before an onset and higher after it, whatever the causal order.")
    pr("The circular-shift null does not remove this: it destroys alignment entirely, so its expected")
    pr("difference is 0, and ANY zero-lag correlation produces a 'significant' post-minus-pre excess.")
    pr("11a therefore measures 'does |dcmd| track the envelope?' (yes), not 'does it lag it?'.")
    pr("")
    pr("12a  THE CLEAN TEST: cross-correlation of the two series after removing the SECONDS-SCALE")
    pr("     co-modulation that dominates 11b (both rise together over a busy stretch of road).  Both")
    pr("     series are high-passed above 1.0 Hz inside each engaged run, then cross-correlated.")
    pr("     r(k) = <env(t) . |dcmd|(t+k)>.  k > 0 => the command comes LATER => the command is an ECHO.")
    pr("     k < 0 => the command comes FIRST => the command is a TRIGGER.")
    pr("     CI: moving-block bootstrap, 400 draws, 5 s blocks (long vs both the lag range and 1/f0).")
    pr("")
    pr("%-10s %12s %-22s %12s %12s %12s" %
       ("route", "peak lag", "  95% CI on the lag", "r at peak", "r(-100ms)", "r(+100ms)"))
    pr("-" * 118)
    curves = {}
    for tag, g in G.items():
        st = np.abs(g["step_f"])
        en = g["env"]
        sos = signal.butter(2, 1.0, btype="highpass", fs=FS, output="sos")
        a = np.zeros(len(en)); b = np.zeros(len(en))
        segs = []
        for aa, bb in g["runs"]:
            if bb - aa < 200:
                continue
            a[aa:bb] = signal.sosfiltfilt(sos, en[aa:bb])
            b[aa:bb] = signal.sosfiltfilt(sos, st[aa:bb])
            segs.append((aa, bb))
        L = 30

        def xc(mask):
            aa_ = a * mask; bb_ = b * mask
            num = np.array([np.dot(aa_[max(0, -k):len(aa_) - max(0, k)], bb_[max(0, k):len(bb_) - max(0, -k)])
                            for k in range(-L, L + 1)])
            return num / np.sqrt(np.dot(aa_, aa_) * np.dot(bb_, bb_) + 1e-30)
        full = np.ones(len(a))
        for aa, bb in segs:
            pass
        m0 = np.zeros(len(a)); [m0.__setitem__(slice(aa, bb), 1.0) for aa, bb in segs]
        r = xc(m0)
        lags = np.arange(-L, L + 1) * 10.0
        j = int(np.argmax(np.abs(r)))
        # moving-block bootstrap over 5 s blocks
        BL = int(5 * FS)
        blocks = [(aa, min(aa + BL, bb)) for s, e in segs for aa, bb in [(s, e)] for aa in range(s, e - BL + 1, BL)]
        pk = []
        for _ in range(400):
            m = np.zeros(len(a))
            for _ in range(len(blocks)):
                s0, e0 = blocks[RNG.integers(0, len(blocks))]
                m[s0:e0] += 1.0
            rr = xc(m)
            pk.append(lags[int(np.argmax(np.abs(rr)))])
        pk = np.array(pk)
        curves[tag] = (lags, r)
        pr("%-10s %9.0f ms   [%6.0f,%6.0f] ms %12.4f %12.4f %12.4f" %
           (tag, lags[j], np.percentile(pk, 2.5), np.percentile(pk, 97.5), r[j], r[L - 10], r[L + 10]))
    pr("")
    pr("  high-passed cross-correlation, r x 1000 (positive lag = command AFTER the ring envelope):")
    lags = curves[ROUTES[0]][0]
    sel = np.arange(0, len(lags), 2)
    pr("    %-10s %s" % ("lag ms", " ".join("%5.0f" % lags[i] for i in sel)))
    for tag in G:
        pr("    %-10s %s" % (tag, " ".join("%5.0f" % (1000 * curves[tag][1][i]) for i in sel)))
    pr("")
    pr("12b  SAME TEST, RESTRICTED TO THE LOUDEST DECILE OF ENGAGED TIME (the grinding seconds), so the")
    pr("     quiet majority cannot dilute a coupling that only exists during a burst.")
    pr("%-10s %12s %12s %12s %12s" % ("route", "peak lag", "r at peak", "r(-100ms)", "r(+100ms)"))
    pr("-" * 118)
    for tag, g in G.items():
        st = np.abs(g["step_f"]); en = g["env"]
        sos = signal.butter(2, 1.0, btype="highpass", fs=FS, output="sos")
        a = np.zeros(len(en)); b = np.zeros(len(en)); m0 = np.zeros(len(en))
        thr = np.quantile(en[g["eng"]], 0.90)
        loud = np.zeros(len(en), bool)
        for aa, bb in C20.runs(g["eng"] & (en >= thr), 20):
            loud[max(0, aa - 50):min(len(en), bb + 50)] = True
        for aa, bb in g["runs"]:
            if bb - aa < 200:
                continue
            a[aa:bb] = signal.sosfiltfilt(sos, en[aa:bb])
            b[aa:bb] = signal.sosfiltfilt(sos, st[aa:bb])
            m0[aa:bb] = 1.0
        m0 = m0 * loud
        L = 30
        aa_ = a * m0; bb_ = b * m0
        num = np.array([np.dot(aa_[max(0, -k):len(aa_) - max(0, k)], bb_[max(0, k):len(bb_) - max(0, -k)])
                        for k in range(-L, L + 1)])
        r = num / np.sqrt(np.dot(aa_, aa_) * np.dot(bb_, bb_) + 1e-30)
        lags = np.arange(-L, L + 1) * 10.0
        j = int(np.argmax(np.abs(r)))
        pr("%-10s %9.0f ms %12.4f %12.4f %12.4f" % (tag, lags[j], r[j], r[L - 10], r[L + 10]))
    pr("")


def main():
    fast = "--fast" in sys.argv
    G = {}
    for tag in ROUTES:
        pr("loading %s ..." % tag)
        g = load_route(tag)
        lo, hi = BAND[tag]
        g["f0"] = ring_f0(g, lo, hi)
        g["env"] = demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = find_onsets(g["env"], g["eng"])
        g["on"], g["pk"], g["amp"] = on, pk, amp
        g["on_t"], g["pk_t"] = g["tr"][on], g["tr"][pk]
        g["det"] = dict(hi=thi, lo=tlo)
        g["runs"] = eng_runs(g)
        g["eng_s"] = float(g["eng"].sum()) / FS
        g["ev"], g["E"] = event_series(g)
        # per-frame command step placed on its NEAREST 0x18F frame (no interpolation smoothing)
        sf = np.zeros(len(g["t"]))
        kk = np.clip(np.searchsorted(g["t"], g["e4"]["step_t"]), 0, len(g["t"]) - 1)
        np.maximum.at(sf, kk, np.abs(g["e4"]["step"]))
        sg = np.zeros(len(g["t"]))
        np.add.at(sg, kk, g["e4"]["step"])
        g["step_f"] = np.where(sf > 0, np.sign(sg) * sf, 0.0)
        g["idx_at_on"] = g["idx_live"][on] if len(on) else np.zeros(0)
        G[tag] = g
    OUT.clear()
    pr("=" * 118)
    pr("BURST-ONSET TRIGGERS -- is a grinding burst STARTED by a discrete command event?  2026-09-10")
    pr("=" * 118)
    pr("Routes: " + ", ".join("%s=%s" % (t, BUILD[t]) for t in ROUTES))
    pr("Ring band per build: " + ", ".join("%s %.0f-%.0f Hz" % (t, *BAND[t]) for t in ROUTES))
    pr("")
    section1(G)
    section2(G)
    windows = [(0, 12, "[0,+120] ms"), (0, 5, "[0,+50] ms"), (-12, 0, "[-120,0] ms (control: onset leads)")]
    section3(G, windows)
    section4(G, ["cap_bind", "idx_jump>=7", "dcmd>=80", "d2cmd>=150", "slew_reversal", "eng_rise"])
    section5(G)
    section6(G)
    section7(G, fast)
    section8(G, ["cap_bind", "dcmd>=80", "dcmd>=100", "idx_jump>=7", "idx_jump>=4",
                 "d2cmd>=150", "cmd_zerocross", "slew_reversal", "E_zerocross"])
    section9(G)
    section10(G)
    section11(G)
    section12(G)
    with open(os.path.join(SCR, "burst_onset_triggers.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    np.savez(os.path.join(SCR, "burst_onsets.npz"),
             **{("%s_on_t" % t): G[t]["on_t"] for t in G},
             **{("%s_pk_t" % t): G[t]["pk_t"] for t in G},
             **{("%s_amp" % t): G[t]["amp"] for t in G},
             **{("%s_f0" % t): np.array([G[t]["f0"]]) for t in G})
    print("\nwrote _scratch/burst_onset_triggers.txt and burst_onsets.npz")


if __name__ == "__main__":
    main()
