#!/usr/bin/env python3
r"""V87 / route 71 -- what `|gp-0x6b98|` actually does, measured for the first time.

WHAT THE PROBE IS
    V87 edit #6, `0x55DF2` `e893` -> `6894`, repoints the 427 (`0x1AB`) transmit packer's SOURCE
    load from `gp-0x6c18` to `gp-0x6b98`, the delivered motor command.  Honda's own packer then runs
    unchanged:

        wire = clamp( (|gp-0x6b98| * 5) >> 3 , 0, 0x3FF )          # abs, x5/8, 10-bit clamp
      => counts = wire * 8/5 = wire * 1.6      (quantisation 1.6 counts, sigma 0.462 counts)
      => saturates at |gp-0x6b98| >= 1637 counts

    🛑 TWO STRUCTURAL HAZARDS, both handled below rather than assumed away:
    (1) RECTIFICATION.  `abs()` is transparent ONLY while the signal keeps one sign inside the
        window.  If `gp-0x6b98` crosses zero, a 7.79 Hz oscillation appears at 15.6 Hz.  Every
        spectral window is therefore screened for a zero approach (Stage 2) and the screened and
        unscreened answers are BOTH reported.
    (2) CLIPPING.  3.2 % of frames rail at 1023.  Any window containing a railed sample is a
        hard-limiter and is excluded from the spectral stages (reported, never silently dropped).

    ⚠ NYQUIST.  427 transmits at 49.81 Hz => Nyquist 24.9 Hz.  The ~7.8 Hz ratcheting is resolved
    6.4 samples/cycle.  Grind #1 (18-22 Hz) is inside the band but within 3 Hz of the fold.  The
    ~28 Hz lane-change transient ALIASES to ~21.8 Hz and is NOT separable here -- so this file
    makes NO claim above 15 Hz.  That is a limit of the instrument, not a result.

THE FORK THIS FILE EXISTS TO DECIDE
    The ratcheting is a lightly-damped resonance, Q 14-29, whose mode lives motor/rack-side where no
    channel on this bus observes (`accord-ratchet-is-a-lightly-damped-resonance`).  Two readings
    remain live:
        (A) a PASSIVE structure being driven -- the command is broadband, the plant rings.
        (B) a CLOSED-LOOP pole -- the delivered command itself oscillates at the line.
    (A) says a command-side filter cannot help and may hurt.  (B) says it can.
    `gp-0x6b98` is the last node before the FOC, so its spectrum decides it.

CONTROLS, run BEFORE the measurements they qualify (`feedback-run-the-control-before-the-measurement`)
    * white noise through the prominence estimator      -- what "no line" reads as
    * phase-randomised surrogate of the probe itself    -- kills any line the envelope alone explains
    * split-half null within the route                  -- the build-to-build floor, in-route form
    🛑 No Q is estimated from a spectrum anywhere in this file: every spectral Q estimator in this
    kit fails its own control (`STATE.md` Instrument defects #2).

Usage:  python v87_probe_6b98.py            # all stages
        python v87_probe_6b98.py 3          # one stage
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, csd, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G          # noqa: E402
import _r31_common as C31        # noqa: E402

CACHE = ROOT / "_cache_r71"
NW, HOP = 512, 256               # 10.28 s @ 49.81 Hz -> 0.0973 Hz bins (corpus is 0.0987)
FLO, FHI = 5.0, 12.0             # the corpus's free search band
RATCHET = (6.0, 9.0)             # AMP_BAND_TIGHT, verbatim from ratchet_discriminators
CTRL_BANDS = {"ratchet_6_9": (6.0, 9.0), "lo_2_4": (2.0, 4.0),
              "mid_11_15": (11.0, 15.0), "grind1_18_22": (18.0, 22.0)}
LSB = 8.0 / 5.0                  # counts per wire LSB
SAT_WIRE = 1023
RNG = np.random.default_rng(87_6598)
NBOOT = 4000
OUT = {}


def hdr(s):
    print("\n" + "=" * 108 + f"\n{s}\n" + "=" * 108, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


# =================================================================================================
#  the 50 Hz analysis grid: the probe on its OWN timestamps, everything else brought to them
# =================================================================================================
def grid():
    z = np.load(CACHE / "r71.npz", allow_pickle=True)
    t = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    keep = np.argsort(t, kind="stable")
    t, wire = t[keep], wire[keep]
    rt = np.asarray(z["t"], float)                       # the 100 Hz row grid
    g = dict(t=t, wire=wire, cts=wire * LSB, clip=(wire >= SAT_WIRE).astype(float),
             dt=np.median(np.diff(t)))
    for k, col in (("tq", "tq"), ("ang", "ang"), ("rate_c", "rate_c"), ("wang", "wang"),
                   ("v", "cs_v"), ("cstq", "cs_tq"), ("press", "cs_press"),
                   ("e4tq", "e4tq"), ("ccreq", "cc_req"), ("coreq", "co_req"),
                   ("sctq", "sc_tq"), ("csrate", "cs_rate")):
        g[k] = np.interp(t, rt, np.asarray(z[col], float))
    g["lat"] = np.interp(t, rt, np.asarray(z["cc_lat"], float)) > 0.5
    g["seg"] = np.round(np.interp(t, rt, np.asarray(z["seg"], float))).astype(int)
    g["fs"] = 1.0 / g["dt"]
    return g


def windows(g, engaged=True, nw=NW, hop=HOP):
    """Contiguous engaged / manual runs, chopped into half-overlapped `nw` windows."""
    mask = g["lat"] if engaged else ~g["lat"]
    out = []
    for a, b in C31.runs_of(mask, g["t"], nw, max_gap=0.10):
        for j0 in range(0, (b - a) - nw + 1, hop):
            sl = slice(a + j0, a + j0 + nw)
            w = {k: g[k][sl] for k in ("t", "wire", "cts", "clip", "tq", "ang", "rate_c",
                                       "v", "e4tq", "ccreq", "coreq", "sctq", "press", "csrate")}
            if not np.all(np.isfinite(w["cts"])):
                continue
            out.append(dict(w, fs=g["fs"], seg=int(np.median(g["seg"][sl])),
                            t0=float(g["t"][sl][0]), engaged=engaged,
                            blk=f"{int(np.median(g['seg'][sl]))}:{a}:{j0 // (hop * 2)}",
                            ep=f"{int(np.median(g['seg'][sl]))}:{a}",
                            vmed=float(np.median(g["v"][sl])),
                            clipfrac=float(np.mean(g["clip"][sl])),
                            wmin=int(g["wire"][sl].min()), wmax=int(g["wire"][sl].max())))
    return out


def spec(x, fs, nw=NW):
    P = C31.periodogram(x, fs, nfft=nw, detrend=True)
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    R = G.prom_spectrum(f, P, halfwin=3.0, exclude=0.6)
    return f, P, R


def band_stats(f, P, R, lo, hi):
    m = (f >= lo) & (f <= hi) & np.isfinite(R)
    if not m.any():
        return dict(f=np.nan, prom=np.nan, pwr=np.nan)
    j = int(np.argmax(np.where(m, R, -np.inf)))
    return dict(f=float(f[j]), prom=float(R[j]), pwr=float(np.sum(P[(f >= lo) & (f <= hi)])))


def block_boot(vals, units, stat=np.median, nboot=NBOOT):
    vals = np.asarray(vals, float)
    ok = np.isfinite(vals)
    vals, units = vals[ok], np.asarray(units)[ok]
    if len(vals) < 4:
        return dict(v=np.nan, lo=np.nan, hi=np.nan, n=int(len(vals)), k=0)
    groups = {}
    for v, u in zip(vals, units):
        groups.setdefault(u, []).append(v)
    keys = list(groups)
    draws = np.empty(nboot)
    for k in range(nboot):
        idx = RNG.integers(0, len(keys), len(keys))
        draws[k] = stat(np.concatenate([groups[keys[i]] for i in idx]))
    return dict(v=float(stat(vals)), lo=float(np.percentile(draws, 2.5)),
                hi=float(np.percentile(draws, 97.5)), n=int(len(vals)), k=len(keys))


def phase_randomise(x):
    """Surrogate with the EXACT amplitude spectrum and randomised phase -- kills line structure
    that a broadband envelope alone would reproduce."""
    X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
    ph = RNG.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0.0
    if len(x) % 2 == 0:
        ph[-1] = 0.0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(x))


# =================================================================================================
# STAGE 0 -- controls FIRST: what does "no line" read as on this instrument, at this nw and fs?
# =================================================================================================
def stage0(g):
    hdr("STAGE 0 -- CONTROLS, RUN BEFORE ANY MEASUREMENT THEY QUALIFY")
    fs = g["fs"]
    sub("white noise through the prominence estimator (the 'no line' reading)")
    proms, frees = [], []
    for _ in range(400):
        f, P, R = spec(RNG.standard_normal(NW), fs)
        b = band_stats(f, P, R, *RATCHET)
        proms.append(b["prom"]); frees.append(b["f"])
    proms = np.array(proms)
    q = {p: float(np.percentile(proms, p)) for p in (50, 90, 95, 99)}
    print(f"    white-noise prominence in {RATCHET[0]}-{RATCHET[1]} Hz: "
          f"p50 {q[50]:.2f}  p90 {q[90]:.2f}  p95 {q[95]:.2f}  p99 {q[99]:.2f}   (n=400)")
    print(f"    ⇒ a per-window prominence below ~{q[95]:.2f} is INDISTINGUISHABLE FROM NOISE here.")

    sub("a synthetic line at 7.79 Hz, buried in white noise -- the estimator's positive control")
    tt = np.arange(NW) / fs
    for snr in (0.1, 0.25, 0.5, 1.0, 2.0):
        pr = []
        for _ in range(120):
            x = RNG.standard_normal(NW) + snr * np.sqrt(2) * np.sin(2 * np.pi * 7.79 * tt +
                                                                    RNG.uniform(0, 6.28))
            f, P, R = spec(x, fs)
            pr.append(band_stats(f, P, R, *RATCHET)["prom"])
        print(f"    line/noise amplitude ratio {snr:4.2f} -> median prominence "
              f"{np.median(pr):7.2f}   (detected at p95 floor: "
              f"{100 * np.mean(np.array(pr) > q[95]):5.1f}% of draws)")
    OUT["stage0"] = dict(white_prom=q, nw=NW, fs=float(fs))
    return q


# =================================================================================================
# STAGE 1 -- the headline number: how big IS the delivered motor command?
# =================================================================================================
def stage1(g):
    hdr("STAGE 1 -- |gp-0x6b98| AMPLITUDE CENSUS  (the number four analyses called blocking)")
    c, lat, v = g["cts"], g["lat"], g["v"]
    print(f"    frames {len(c):,}   {g['fs']:.2f} Hz   {g['t'][-1] - g['t'][0]:.1f} s")
    print(f"    🛑 THE ASSUMED VALUE WAS ~120 COUNTS p-p.  Measured, whole route:")
    for tag, m in (("ALL", np.ones(len(c), bool)), ("engaged", lat), ("manual", ~lat),
                   ("parked v<0.2", np.abs(v) < 0.2), ("creep 0.2-2", (np.abs(v) >= 0.2) & (np.abs(v) < 2)),
                   ("2-6 m/s", np.abs(v) >= 2)):
        if m.sum() < 50:
            continue
        x = c[m]
        print(f"      {tag:14s} n={m.sum():6d}  p50 {np.percentile(x, 50):7.1f}  "
              f"p90 {np.percentile(x, 90):7.1f}  p99 {np.percentile(x, 99):7.1f}  "
              f"max {x.max():7.1f}  railed {100 * np.mean(g['wire'][m] >= SAT_WIRE):5.2f}%")
    OUT["stage1"] = {}
    for tag, m in (("all", np.ones(len(c), bool)), ("engaged", lat), ("manual", ~lat)):
        OUT["stage1"][tag] = dict(n=int(m.sum()), p50=float(np.percentile(c[m], 50)),
                                  p90=float(np.percentile(c[m], 90)),
                                  p99=float(np.percentile(c[m], 99)),
                                  railed=float(np.mean(g["wire"][m] >= SAT_WIRE)))
    sub("band-limited content -- how much of that magnitude MOVES, and in which band")
    for lo, hi in ((0.5, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 15.0), (15.0, 22.0)):
        b = butter(2, [lo, hi], btype="band", fs=g["fs"])
        for tag, m in (("engaged", lat), ("manual", ~lat)):
            y = filtfilt(*b, c)
            print(f"      {lo:4.1f}-{hi:4.1f} Hz  {tag:8s}  rms {np.std(y[m]):7.2f} counts   "
                  f"p-p(p1..p99) {np.percentile(y[m], 99) - np.percentile(y[m], 1):7.2f} counts")
    return


# =================================================================================================
# STAGE 2 -- is the rectification transparent?  (the `abs()` trap, made a measurement)
# =================================================================================================
def stage2(g, recs_e, recs_m):
    hdr("STAGE 2 -- RECTIFICATION TRANSPARENCY: can a 7.8 Hz line survive `abs()` unfolded?")
    print("    `abs()` is transparent iff the signal keeps one sign across the window.  The probe")
    print("    cannot show sign, but it CAN show approach to zero: a window whose minimum is well")
    print("    above the band-limited ripple never crossed.  Screen = wmin_counts > 2 x ripple_pp.")
    rows = []
    b = butter(2, list(RATCHET), btype="band", fs=g["fs"])
    for tag, recs in (("engaged", recs_e), ("manual", recs_m)):
        ok = 0
        for r in recs:
            rip = np.percentile(filtfilt(*b, r["cts"]), 99) - np.percentile(filtfilt(*b, r["cts"]), 1)
            r["ripple_pp"] = float(rip)
            r["floor_cts"] = float(r["cts"].min())
            r["transparent"] = bool(r["cts"].min() > 2.0 * rip and rip > 0)
            ok += r["transparent"]
        rows.append((tag, len(recs), ok))
        print(f"      {tag:8s}: {ok}/{len(recs)} windows transparent "
              f"({100 * ok / max(len(recs), 1):.0f}%)")
    print("    ⚠ A NON-transparent window is not useless -- it just puts a 7.8 Hz oscillation at")
    print("      15.6 Hz.  Stage 3 therefore reads BOTH 6-9 and its rectified image 12-18 Hz.")
    OUT["stage2"] = {t: dict(n=n, transparent=k) for t, n, k in rows}


# =================================================================================================
# STAGE 3 -- THE FORK.  Is the ratchet line in the DELIVERED COMMAND?
# =================================================================================================
def stage3(g, recs_e, recs_m, white_q):
    hdr("STAGE 3 -- THE FORK: does `|gp-0x6b98|` itself carry the ~7.8 Hz line?")
    print("    Reference: the same window, same estimator, on the COLUMN TORQUE `tq` (0x18F) -- the")
    print("    channel the ratchet was originally characterised in at 7.79 Hz, and on openpilot's")
    print("    own command `e4tq`, which the record says does NOT carry it.")
    res = {}
    for tag, recs in (("engaged", recs_e), ("manual", recs_m)):
        clean = [r for r in recs if r["clipfrac"] == 0.0]
        print(f"\n    {tag}: {len(recs)} windows, {len(clean)} with ZERO railed samples "
              f"({len(recs) - len(clean)} excluded as hard-limited)")
        if len(clean) < 4:
            print("      too few clean windows to score")
            continue
        for sig, label in (("cts", "|gp-0x6b98|  DELIVERED COMMAND"),
                           ("tq", "column torque 0x18F"),
                           ("e4tq", "openpilot command 0x0E4"),
                           ("rate_c", "column rate 0x14A")):
            fr, pr, pw = [], [], []
            for r in clean:
                f, P, R = spec(r[sig], r["fs"])
                bs = band_stats(f, P, R, *RATCHET)
                fr.append(bs["f"]); pr.append(bs["prom"]); pw.append(bs["pwr"])
            bb = block_boot(pr, [r["blk"] for r in clean])
            bf = block_boot(fr, [r["blk"] for r in clean])
            hit = 100 * np.mean(np.array(pr) > white_q[95])
            print(f"      {label:34s} prominence {bb['v']:6.2f} [{bb['lo']:5.2f},{bb['hi']:5.2f}]"
                  f"   f {bf['v']:5.2f} Hz [{bf['lo']:.2f},{bf['hi']:.2f}]"
                  f"   above noise floor in {hit:5.1f}% of windows")
            res[f"{tag}/{sig}"] = dict(prom=bb, f=bf, above_floor_pct=float(hit), n=len(clean))

        sub(f"  {tag}: the surrogate control on the probe itself (phase-randomised)")
        sp = []
        for r in clean:
            f, P, R = spec(phase_randomise(r["cts"]), r["fs"])
            sp.append(band_stats(f, P, R, *RATCHET)["prom"])
        sb = block_boot(sp, [r["blk"] for r in clean])
        print(f"      surrogate prominence {sb['v']:6.2f} [{sb['lo']:5.2f},{sb['hi']:5.2f}]  "
              f"vs real {res[f'{tag}/cts']['prom']['v']:.2f}")
        res[f"{tag}/cts_surrogate"] = sb

        sub(f"  {tag}: the rectified image -- 12-18 Hz, where a zero-crossing 6-9 Hz line would land")
        im = []
        for r in clean:
            f, P, R = spec(r["cts"], r["fs"])
            im.append(band_stats(f, P, R, 12.0, 18.0)["prom"])
        ib = block_boot(im, [r["blk"] for r in clean])
        print(f"      12-18 Hz prominence {ib['v']:6.2f} [{ib['lo']:5.2f},{ib['hi']:5.2f}]")
        res[f"{tag}/cts_image"] = ib
    OUT["stage3"] = res
    return res


# =================================================================================================
# STAGE 4 -- coherence: is the command's motion the SAME motion as the column's?
# =================================================================================================
def stage4(g, recs_e):
    hdr("STAGE 4 -- COHERENCE `|gp-0x6b98|` <-> column torque, and the transfer magnitude")
    clean = [r for r in recs_e if r["clipfrac"] == 0.0]
    if len(clean) < 4:
        print("    too few clean engaged windows")
        return
    fs = g["fs"]
    Sxx = Syy = Sxy = None
    for r in clean:
        x = r["cts"] - r["cts"].mean()
        y = r["tq"] - r["tq"].mean()
        f, pxx = welch(x, fs, nperseg=NW, nfft=NW)
        _, pyy = welch(y, fs, nperseg=NW, nfft=NW)
        _, pxy = csd(x, y, fs, nperseg=NW, nfft=NW)
        Sxx = pxx if Sxx is None else Sxx + pxx
        Syy = pyy if Syy is None else Syy + pyy
        Sxy = pxy if Sxy is None else Sxy + pxy
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
    trans = np.abs(Sxy) / Sxx
    ph = np.degrees(np.angle(Sxy))
    print(f"    pooled over {len(clean)} clean engaged windows")
    print(f"    {'f [Hz]':>8} {'coh^2':>7} {'|tq/cmd|':>9} {'phase':>8}")
    for lo, hi in ((2, 4), (5, 6), (6, 7), (7, 8), (8, 9), (9, 11), (11, 15), (15, 20)):
        m = (f >= lo) & (f < hi)
        print(f"    {lo:3d}-{hi:<4d} {np.mean(coh[m]):7.3f} {np.mean(trans[m]):9.4f} "
              f"{np.mean(ph[m]):8.1f}")
    j = np.argmin(np.abs(f - 7.79))
    print(f"    at 7.79 Hz: coh^2 {coh[j]:.3f}  |tq/cmd| {trans[j]:.4f}  phase {ph[j]:+.1f} deg")
    OUT["stage4"] = dict(n=len(clean), f=f.tolist()[:200],
                         coh=coh.tolist()[:200], trans=trans.tolist()[:200],
                         phase=ph.tolist()[:200])


# =================================================================================================
# STAGE 5 -- split-half null: the in-route floor any cross-build ratio must beat
# =================================================================================================
def stage5(recs_e):
    hdr("STAGE 5 -- SPLIT-HALF NULL: the floor a V88-vs-V87 ratio would have to clear")
    clean = [r for r in recs_e if r["clipfrac"] == 0.0]
    if len(clean) < 8:
        print("    too few clean engaged windows for a split-half null")
        OUT["stage5"] = dict(n=len(clean), note="underpowered")
        return
    pw = []
    for r in clean:
        f, P, R = spec(r["cts"], r["fs"])
        pw.append(band_stats(f, P, R, *RATCHET)["pwr"])
    pw = np.array(pw)
    blks = np.array([r["blk"] for r in clean])
    ub = list(dict.fromkeys(blks))
    ratios = []
    for _ in range(2000):
        perm = RNG.permutation(len(ub))
        A = set(np.array(ub)[perm[:len(ub) // 2]])
        ma = np.array([b in A for b in blks])
        if ma.sum() < 3 or (~ma).sum() < 3:
            continue
        ratios.append(np.median(pw[ma]) / np.median(pw[~ma]))
    ratios = np.array(ratios)
    print(f"    n={len(clean)} clean windows in {len(ub)} blocks")
    print(f"    split-half power ratio: median {np.median(ratios):.3f}  "
          f"central 95% [{np.percentile(ratios, 2.5):.3f}, {np.percentile(ratios, 97.5):.3f}]")
    print(f"    ⇒ 🛑 a V88/V87 6-9 Hz power ratio inside that interval IS A NULL, whatever it is.")
    OUT["stage5"] = dict(n=len(clean), k=len(ub), med=float(np.median(ratios)),
                         lo=float(np.percentile(ratios, 2.5)),
                         hi=float(np.percentile(ratios, 97.5)))


# =================================================================================================
# STAGE 6 -- where does the command's magnitude sit against the levers that would filter it?
# =================================================================================================
def stage6(g, recs_e):
    hdr("STAGE 6 -- CLIPPING AND HEADROOM: what the measured magnitude does to the filter argument")
    c, lat = g["cts"], g["lat"]
    print("    A command-side filter's phase budget is set by how much of the signal is RIPPLE")
    print("    against how much is DC.  Both are now measured rather than assumed.")
    b = butter(2, list(RATCHET), btype="band", fs=g["fs"])
    rip = filtfilt(*b, c)
    for tag, m in (("engaged", lat), ("manual", ~lat)):
        dc = np.abs(c[m])
        rr = rip[m]
        print(f"      {tag:8s}  DC p50 {np.median(dc):7.1f} counts   "
              f"6-9 Hz ripple rms {np.std(rr):6.2f}  ratio {np.std(rr) / max(np.median(dc), 1e-9):.4f}")
    railed = np.mean(g["wire"] >= SAT_WIRE)
    print(f"\n    railed at 1637 counts: {100 * railed:.2f}% of ALL frames "
          f"({100 * np.mean(g['wire'][lat] >= SAT_WIRE):.2f}% engaged, "
          f"{100 * np.mean(g['wire'][~lat] >= SAT_WIRE):.2f}% manual)")
    print("    🛑 The probe's ceiling is the PROBE's, not the command's -- 1637 counts is where")
    print("       Honda's x5/8 packer hits 10 bits.  The true magnitude above that is UNMEASURED.")
    OUT["stage6"] = dict(railed_all=float(railed),
                         railed_engaged=float(np.mean(g["wire"][lat] >= SAT_WIRE)),
                         railed_manual=float(np.mean(g["wire"][~lat] >= SAT_WIRE)))


if __name__ == "__main__":
    only = sys.argv[1:] or None
    g = grid()
    print(f"grid: {len(g['t']):,} probe frames at {g['fs']:.3f} Hz, "
          f"{g['t'][-1] - g['t'][0]:.1f} s, engaged {100 * g['lat'].mean():.1f}%")
    recs_e = windows(g, engaged=True)
    recs_m = windows(g, engaged=False)
    print(f"windows nw={NW} ({NW / g['fs']:.2f} s, {g['fs'] / NW:.4f} Hz bins): "
          f"{len(recs_e)} engaged, {len(recs_m)} manual")
    q = stage0(g)
    if not only or "1" in only:
        stage1(g)
    stage2(g, recs_e, recs_m)
    if not only or "3" in only:
        stage3(g, recs_e, recs_m, q)
    if not only or "4" in only:
        stage4(g, recs_e)
    if not only or "5" in only:
        stage5(recs_e)
    if not only or "6" in only:
        stage6(g, recs_e)
    (CACHE / "v87_probe_6b98.json").write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {CACHE / 'v87_probe_6b98.json'}")
