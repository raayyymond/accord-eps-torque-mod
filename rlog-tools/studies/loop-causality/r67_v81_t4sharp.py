#!/usr/bin/env python3
"""SHARPENED T4 -- the highway instability as the crux.  Six questions, in the orchestrator's order.

  S1  every highway event characterised: f0 / prominence / Q / p-p / duration / speed, ONE MODE
      OR SEVERAL (harmonic structure), against the kit's catalogue.
  S2  cross-build contrast at matched highway speed, and the route-5e speed ceiling stated plainly.
  S3  the damper-vs-highway test, binned on L2+L3 duty inside a NARROW speed band.
      🛑 The association is CIRCULAR by construction and this file says so: the thermometer measures
      the damper OUTPUT, which is a function of motor rate, which is a function of the oscillation.
      A positive association is predicted by BOTH hypotheses. The only non-circular thing available
      is TEMPORAL PRECEDENCE, so S3b cross-correlates the two at sub-second lags through the onset.
  S4  hand mass at highway, by driver-torque quartile and by `steerOverride`.
  S5  the disengage transient, time-resolved at 50 ms, against BOTH `cc_lat` (openpilot's request)
      and `sca` = 0x18F STEER_CONTROL_ACTIVE (the EPS's own acknowledgement).  If the ring dies with
      `sca` on a ~2 s debounce rather than with `cc_lat`, that time constant is the mode fingerprint.
  S6  lane change: trigger or coincidence?  Onset latency against blinker, angle excursion and the
      0x0E4 command.

🛑 fs = 100.5 Hz.  Every f is indistinguishable from 100.5 - f.
🛑 `tq` (0x18F) is zero-order-held onto the 0x14A row grid, a 9.96 ms median lag = 99.5 deg at
   27.8 Hz.  Magnitudes and line frequencies survive it (verified: raw-grid f0 27.810 vs
   resampled 27.756, inside one 0.393 Hz bin); PHASE does not.  Nothing here uses cross-channel phase.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import _grind2_lib as G  # noqa: E402
import _r31_common as C31  # noqa: E402
from r67_v81_t4t5 import ORDER, ROUTES, col, env, hdr, lowpass, runs_of, segs, windows  # noqa: E402
from r67_v81_t4f import burst_events, event_spectrum, smooth  # noqa: E402

KMH = 1.0 / 3.6
NFFT = G.NFFT
BURST = (18.0, 31.0)
RNG = np.random.default_rng(4747)
OUT = {}

# The kit's catalogue of named modes, for S1's identification step.
CATALOGUE = [("ratchet", 6.0, 9.0), ("grind #1", 18.0, 22.0), ("the ~28 Hz mode", 26.0, 31.0),
             ("grind #2", 40.0, 49.0)]
# ★ FactorC speed axis, from the orchestrator's byte-level mirror: 64 counts per km/h, so
# X = [2240, 3840, 5120, 8960] counts = 35 / 60 / 80 / 140 km/h, Y = [566, 234, 429, 908] on the
# V81 mode-26 engaged column. This file does NOT re-derive it; it is used only to LABEL strata.
FACTORC_KMH = [35.0, 60.0, 80.0, 140.0]
FACTORC_Y = [566.0, 234.0, 429.0, 908.0]


def factorc(kmh):
    return float(np.interp(kmh, FACTORC_KMH, FACTORC_Y))


def boot_med(v, nboot=2000):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (float(v[0]) if len(v) else np.nan), np.nan, np.nan
    dr = [np.median(v[RNG.integers(0, len(v), len(v))]) for _ in range(nboot)]
    return float(np.median(v)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


# =================================================================================================
def s1_s2(W, ALL):
    hdr("S1  EVERY HIGHWAY EVENT, CHARACTERISED.  One mode or several?  Harmonic structure is the\n"
        "    discriminator: a Coulomb RELAY drives strong ODD harmonics; a narrowband linear\n"
        "    instability is a near-pure sinusoid.  🛑 2f0 and 3f0 FOLD -- both are reported at the\n"
        "    frequency they are actually observed at.")
    OUT["s1"] = {}
    for b in ORDER:
        hw = sorted([e for e in ALL[b] if e["v"] >= 80 * KMH], key=lambda e: -e["peak"])
        if not hw:
            print(f"\n  ---- {b} ----  no >80 km/h burst "
                  f"(engaged >80 km/h exposure: see S2)")
            continue
        print(f"\n  ---- {b} ----")
        print(f"     {'seg':>3s} {'t0':>7s} {'dur':>6s} {'v kmh':>6s} | {'f0':>6s} {'prom':>8s} "
              f"{'Q':>5s} {'pp ct':>7s} | {'2f0->':>6s} {'prom':>7s} | {'3f0->':>6s} {'prom':>7s}"
              f" | mode")
        for e in hw:
            sp = event_spectrum(b, e["seg"], e["i0"], e["i1"], pad=64)
            if not sp or not np.isfinite(sp["f0"]):
                continue
            f, R, f0 = sp["f"], sp["R"], sp["f0"]
            fsr = 2 * f[-1]                       # the sample rate this spectrum was cut at
            rows = []
            for h in (2, 3):
                fa = h * f0
                while fa > fsr / 2:
                    fa = abs(fsr - fa) if fa < fsr else fa - fsr
                k = int(np.argmin(np.abs(f - fa)))
                rows += [fa, float(R[k])]
            name = next((nm for nm, lo, hi in CATALOGUE if lo <= f0 <= hi), "UNCATALOGUED")
            print(f"     {e['seg']:3d} {e['t0']:7.2f} {e['dur']:6.2f} {e['v'] * 3.6:6.1f} | "
                  f"{f0:6.2f} {sp['prom']:8.1f} {sp['Q']:5.1f} {sp['pp']:7.0f} | "
                  f"{rows[0]:6.2f} {rows[1]:7.2f} | {rows[2]:6.2f} {rows[3]:7.2f} | {name}")
            OUT["s1"].setdefault(b, []).append(dict(
                seg=e["seg"], t0=e["t0"], dur=e["dur"], v=e["v"] * 3.6, f0=float(f0),
                prom=float(sp["prom"]), Q=float(sp["Q"]), pp=float(sp["pp"]),
                h2=[rows[0], rows[1]], h3=[rows[2], rows[3]], name=name))

    hdr("S2  CROSS-BUILD AT HIGHWAY SPEED -- exposure first, because it decides what is comparable.")
    print(f"  {'build':10s} {'vmax kmh':>9s} {'eng frames >=80':>16s} {'eng s >=80':>11s} "
          f"{'burst s >=80':>13s} {'duty':>6s} {'peak env ct':>12s}")
    OUT["s2"] = {}
    for b in ORDER:
        vmax = 0.0
        n80 = 0
        fsm = []
        for s, d in segs(b):
            v = np.abs(d["cs_v"])
            vmax = max(vmax, float(v.max()))
            m = (d["cc_lat"] > 0.5) & (v >= 80 * KMH)
            n80 += int(m.sum())
            fsm.append(C31.fs_of(d))
        fsm = float(np.median(fsm)) if fsm else 100.0
        hwb = [e for e in ALL[b] if e["v"] >= 80 * KMH]
        bs = sum(e["dur"] for e in hwb)
        es = n80 / fsm
        print(f"  {b:10s} {vmax * 3.6:9.2f} {n80:16d} {es:11.1f} {bs:13.1f} "
              f"{(100 * bs / es if es else 0):5.1f}% {max((e['peak'] for e in hwb), default=0):12.0f}")
        OUT["s2"][b] = dict(vmax=vmax * 3.6, n80=n80, eng80=es, burst80=bs,
                            peak=max((e["peak"] for e in hwb), default=0.0))
    print("\n  🛑 ROUTE 5e (V75) NEVER EXCEEDED ITS OWN CEILING -- see the vmax column. If it reads")
    print("     ~65 km/h with 0 engaged frames >= 80, then 'V75 fixed the grinding' was measured")
    print("     ENTIRELY BELOW HIGHWAY SPEED and the V74->V81 damper arc rests on a low-speed result.")


# =================================================================================================
def s3(W):
    hdr("S3  THE DAMPER AT HIGHWAY, binned on L2+L3 duty (bit4 never fires, so L4 is unavailable).\n"
        "    🛑🛑 CIRCULARITY WARNING, stated before the numbers: `thermo` measures |gp-0x6bd0|,\n"
        "    the damper OUTPUT, which is a function of motor rate, which is a function of the very\n"
        "    oscillation being predicted. A positive association is predicted by BOTH 'the damper\n"
        "    drives the mode' AND 'the mode drives the damper'. This table is DESCRIPTIVE ONLY.\n"
        "    🛑 Speed and damper duty are confounded BY CONSTRUCTION (FactorC is a function of\n"
        "    speed), so everything below is inside a NARROW speed band.")
    d67 = [r for r in W["V81/r67"] if r["eng"] == 1]
    print(f"\n  FactorC on the V81 mode-26 engaged column (orchestrator's byte mirror, used as a\n"
          f"  LABEL only): 35 km/h -> {factorc(35):.0f} · 60 -> {factorc(60):.0f} · "
          f"80 -> {factorc(80):.0f} · 100 -> {factorc(100):.0f} · 140 -> {factorc(140):.0f}")
    print("\n  ★ THE MEASURED L2+L3 CENSUS AGAINST THAT CURVE (engaged, whole route):")
    print(f"     {'stratum':14s} {'FactorC':>8s} {'L2+L3 duty':>11s} {'mean thermo':>12s} {'n':>7s}")
    OUT["s3_axis"] = {}
    for nm, lo, hi, mid in (("creep <10", 0, 10, 7.0), ("10-40", 10, 40, 25.0),
                            ("40-80", 40, 80, 60.0), (">80", 80, 1e9, 95.0)):
        tot = l23 = 0
        th = []
        for s, dd in segs("V81/r67"):
            v = np.abs(dd["cs_v"]) * 3.6
            m = (dd["cc_lat"] > 0.5) & (v >= lo) & (v < hi)
            tot += int(m.sum())
            l23 += int((m & (dd["thermo"] >= 2)).sum())
            th.append(dd["thermo"][m])
        thv = np.concatenate(th) if th else np.array([])
        print(f"     {nm:14s} {factorc(mid):8.0f} {100 * l23 / max(tot,1):10.2f}% "
              f"{np.mean(thv) if len(thv) else np.nan:12.3f} {tot:7d}")
        OUT["s3_axis"][nm] = dict(factorc=factorc(mid), duty=100 * l23 / max(tot, 1), n=tot)

    hdr("S3a  INSIDE 85-105 km/h ENGAGED ONLY -- windows binned by their own mean thermometer.")
    hw = [r for r in d67 if 85 * KMH <= r["v"] < 105 * KMH]
    # attach the per-window thermometer
    by = {}
    for r in hw:
        by.setdefault(r["seg"], []).append(r)
    for s, group in by.items():
        dd = {k: v for k, v in np.load(ROUTES["V81/r67"][0] / f"r67xs{s}.npz").items()}
        t = np.asarray(dd["t"], float)
        for r in group:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            sl = slice(i0, i0 + NFFT)
            r["thermo"] = float(np.mean(dd["thermo"][sl]))
            r["l23"] = float(np.mean(dd["thermo"][sl] >= 2))
            r["bd"] = float(np.mean(dd["g6ac2"][sl]))
    hw = [r for r in hw if "thermo" in r]
    print(f"  n = {len(hw)} engaged windows in 85-105 km/h "
          f"(speed p5/p50/p95 = {np.percentile(col(hw,'v'),5)*3.6:.1f}/"
          f"{np.percentile(col(hw,'v'),50)*3.6:.1f}/{np.percentile(col(hw,'v'),95)*3.6:.1f} km/h)")
    if len(hw) >= 10:
        q = np.percentile(col(hw, "l23"), [33, 67])
        for lab, sel in ((f"L2+L3 duty < {q[0]:.3f}", lambda r: r["l23"] < q[0]),
                         (f"{q[0]:.3f} .. {q[1]:.3f}", lambda r: q[0] <= r["l23"] < q[1]),
                         (f"> {q[1]:.3f}", lambda r: r["l23"] >= q[1])):
            g = [r for r in hw if sel(r)]
            if not g:
                continue
            e18 = boot_med(col(g, "e_18-22"))
            e26 = boot_med(col(g, "e_26-31"))
            print(f"    {lab:24s} n={len(g):3d}  v {np.median(col(g,'v'))*3.6:6.1f} km/h  "
                  f"e_18-22 {e18[0]:8.1f} [{e18[1]:7.1f},{e18[2]:7.1f}]  "
                  f"e_26-31 {e26[0]:8.1f} [{e26[1]:7.1f},{e26[2]:7.1f}]")
        x, y = col(hw, "l23"), np.log(np.maximum(col(hw, "e_26-31"), 1e-9))
        m = np.isfinite(x) & np.isfinite(y)
        print(f"    corr(L2+L3 duty, log e_26-31) = {np.corrcoef(x[m], y[m])[0,1]:+.3f}   "
              f"corr(speed, L2+L3 duty) = {np.corrcoef(col(hw,'v'), x)[0,1]:+.3f}   "
              f"corr(speed, log e_26-31) = {np.corrcoef(col(hw,'v')[m], y[m])[0,1]:+.3f}")
        print("    ⇒ read the first correlation ONLY alongside the circularity warning above.")

    hdr("S3b  TEMPORAL PRECEDENCE -- the ONE non-circular test available.  Cross-correlate the\n"
        "     damper thermometer against the 18-31 Hz envelope through the seg-8 onset.  If the\n"
        "     damper LEADS the envelope, causation is at least possible; if it LAGS, the damper is\n"
        "     a consequence of the ring.  Positive lag = thermometer leads.")
    dd = {k: v for k, v in np.load(ROUTES["V81/r67"][0] / "r67xs8.npz").items()}
    fs = C31.fs_of(dd)
    e = smooth(env(dd["tq"], fs, *BURST), fs)
    th = smooth(dd["thermo"], fs)
    m = (dd["t"] >= 30.0) & (dd["t"] <= 55.0)
    a, c = e[m] - np.mean(e[m]), th[m] - np.mean(th[m])
    a, c = a / (np.std(a) or 1), c / (np.std(c) or 1)
    n = len(a)
    lags = np.arange(-int(2 * fs), int(2 * fs) + 1)
    xc = np.array([np.mean(c[max(0, L):n + min(0, L)] * a[max(0, -L):n + min(0, -L)])
                   for L in lags])
    k = int(np.argmax(xc))
    print(f"  window t 30-55 s, n={n}, peak cross-correlation {xc[k]:+.3f} at lag "
          f"{lags[k] / fs:+.3f} s  ({'thermometer LEADS' if lags[k] > 0 else 'thermometer LAGS'})")
    for L in (-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0):
        j = int(np.argmin(np.abs(lags / fs - L)))
        print(f"     lag {L:+5.2f} s : {xc[j]:+.3f}")
    print("\n  ONSET, 0.1 s resolution (t 39.0 - 42.5 s): does the thermometer move first?")
    print(f"     {'t':>6s} {'env18-31':>9s} {'thermo':>7s} {'|sc| cmd':>9s} {'|tq_lf|':>8s} "
          f"{'ang':>7s} {'bit3':>5s} {'sca':>4s} {'lat':>4s}")
    tql = np.abs(lowpass(dd["tq"], fs))
    for tt in np.arange(39.0, 42.55, 0.1):
        j = int(np.argmin(np.abs(dd["t"] - tt)))
        sl = slice(j, j + int(0.1 * fs))
        print(f"     {tt:6.1f} {np.max(e[sl]):9.0f} {np.mean(dd['thermo'][sl]):7.2f} "
              f"{np.mean(np.abs(dd['sc_tq'][sl])):9.0f} {np.mean(tql[sl]):8.0f} "
              f"{np.mean(dd['ang'][sl]):7.2f} {np.mean(dd['g6ac2'][sl]):5.2f} "
              f"{np.mean(dd['sca'][sl]):4.1f} {np.mean(dd['cc_lat'][sl]):4.1f}")
    OUT["s3b"] = dict(peak_xc=float(xc[k]), peak_lag=float(lags[k] / fs))


# =================================================================================================
def s4(W):
    hdr("S4  HAND MASS AT HIGHWAY.  A mechanical resonance is damped by added impedance; a\n"
        "    control-loop limit cycle is not.  Frame-level, inside the ring, and window-level.")
    dd = {k: v for k, v in np.load(ROUTES["V81/r67"][0] / "r67xs8.npz").items()}
    fs = C31.fs_of(dd)
    e = smooth(env(dd["tq"], fs, *BURST), fs)
    tql = np.abs(lowpass(dd["tq"], fs))
    m = (dd["t"] >= 41.0) & (dd["t"] <= 52.4)
    x, y = tql[m], e[m]
    print(f"  INSIDE the seg-8 ring (n={int(m.sum())} frames):")
    print(f"    corr(|tq_lf|, envelope) = {np.corrcoef(x, y)[0,1]:+.4f}")
    qs = np.percentile(x, [25, 50, 75])
    for lab, sel in ((f"Q1  |tq_lf| < {qs[0]:.0f}", x < qs[0]),
                     (f"Q2  {qs[0]:.0f}-{qs[1]:.0f}", (x >= qs[0]) & (x < qs[1])),
                     (f"Q3  {qs[1]:.0f}-{qs[2]:.0f}", (x >= qs[1]) & (x < qs[2])),
                     (f"Q4  |tq_lf| > {qs[2]:.0f}", x >= qs[2])):
        v = boot_med(y[sel])
        print(f"    {lab:22s} n={int(sel.sum()):5d}  envelope {v[0]:8.0f} [{v[1]:7.0f},{v[2]:7.0f}]")
    r = np.median(y[x >= qs[2]]) / max(np.median(y[x < qs[0]]), 1e-9)
    print(f"    Q4/Q1 envelope ratio = {r:.3f}   ⇒ "
          f"{'added driver torque does NOT damp it' if r > 0.8 else 'added driver torque DOES damp it'}")
    OUT["s4_inring"] = dict(corr=float(np.corrcoef(x, y)[0, 1]), q4q1=float(r))

    print("\n  steerOverride episodes (from onroadEvents) overlapping the ring:")
    ev = json.loads((ROUTES["V81/r67"][0] / "r67_events.json").read_text())
    so = [x_ for x_ in ev if x_["name"] == "steerOverride"]
    print(f"    {len(so)} steerOverride rows on the whole route; route-global t of the seg-8 ring "
          f"is not directly comparable (events carry route time, the cache carries segment time),")
    print("    so this is reported as a COUNT only and is NOT used for any verdict.")

    print("\n  WINDOW-LEVEL, engaged >80 km/h, by driver-torque tercile "
          "(the earlier >800 ct split had ZERO hands-on windows):")
    hw = [r for r in W["V81/r67"] if r["eng"] == 1 and r["v"] >= 80 * KMH]
    if len(hw) >= 9:
        q = np.percentile(col(hw, "eff"), [33, 67])
        for lab, sel in ((f"eff < {q[0]:.0f} ct", lambda r: r["eff"] < q[0]),
                         (f"{q[0]:.0f}-{q[1]:.0f}", lambda r: q[0] <= r["eff"] < q[1]),
                         (f"> {q[1]:.0f} ct", lambda r: r["eff"] >= q[1])):
            g = [r for r in hw if sel(r)]
            if not g:
                continue
            a1 = boot_med(col(g, "e_18-22"))
            a2 = boot_med(col(g, "e_26-31"))
            print(f"    {lab:16s} n={len(g):3d} v {np.median(col(g,'v'))*3.6:6.1f}  "
                  f"e_18-22 {a1[0]:8.1f} [{a1[1]:7.1f},{a1[2]:7.1f}]  "
                  f"e_26-31 {a2[0]:8.1f} [{a2[1]:7.1f},{a2[2]:7.1f}]")
        print(f"    ⚠ max driver effort in ANY engaged >80 km/h window is "
              f"{max(col(hw,'eff')):.0f} ct -- the driver never gripped hard at highway speed on\n"
              f"      this route, so this is a WEAK version of the hand-mass test. The in-ring\n"
              f"      frame-level test above is the stronger one.")


# =================================================================================================
def s5(W):
    hdr("S5  THE DISENGAGE TRANSIENT, time-resolved at 50 ms.  Does the ring die with `cc_lat`\n"
        "    (openpilot's request) or with `sca` = 0x18F STEER_CONTROL_ACTIVE (the EPS's own\n"
        "    acknowledgement)?  A ~2 s lag to `sca` would be the mode-debounce fingerprint.")
    OUT["s5"] = {}
    print("  First: how far does `sca` lag `cc_lat` on this route?")
    lags_on, lags_off = [], []
    for s, d in segs("V81/r67"):
        fs = C31.fs_of(d)
        lat = (d["cc_lat"] > 0.5).astype(int)
        sca = (d["sca"] > 0.5).astype(int)
        for arr, store in ((np.flatnonzero(np.diff(lat) > 0), lags_on),
                           (np.flatnonzero(np.diff(lat) < 0), lags_off)):
            for i in arr:
                w = sca[i:i + int(4 * fs)] if store is lags_on else sca[i:i + int(4 * fs)]
                if not len(w):
                    continue
                tgt = np.flatnonzero(w == (1 if store is lags_on else 0))
                if len(tgt):
                    store.append(tgt[0] / fs)
    for nm, v in (("cc_lat RISING -> sca=1", lags_on), ("cc_lat FALLING -> sca=0", lags_off)):
        if v:
            print(f"    {nm:26s} n={len(v):3d}  median {np.median(v):.3f} s  "
                  f"p90 {np.percentile(v,90):.3f} s  max {max(v):.3f} s")
            OUT["s5"][nm] = dict(n=len(v), med=float(np.median(v)))
    print("  ⇒ if these are ~0 s, `sca` and `cc_lat` are not separable on this route and the")
    print("    mode-debounce fingerprint CANNOT be tested here. Say that rather than inventing it.")

    print("\n  Envelope decay after every clean latActive falling edge, 50 ms resolution:")
    taus, rows = [], []
    for s, d in segs("V81/r67"):
        fs = C31.fs_of(d)
        e = smooth(env(d["tq"], fs, *BURST), fs)
        lat = d["cc_lat"] > 0.5
        W4 = int(4 * fs)
        for i in np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1:
            if i - W4 < 0 or i + W4 >= len(e):
                continue
            if lat[i - W4:i].mean() < 0.95 or lat[i:i + W4].mean() > 0.05:
                continue
            base = float(np.percentile(e[i - W4:i], 90))
            floor = float(np.percentile(e[i + int(2 * fs):i + W4], 50))
            tr = [(k / fs, float(np.max(e[i + k:i + k + max(1, int(0.05 * fs))])))
                  for k in range(0, int(2.5 * fs), max(1, int(0.05 * fs)))]
            half = next((t_ for t_, v_ in tr if v_ <= 0.5 * base), np.nan)
            tenth = next((t_ for t_, v_ in tr if v_ <= max(0.1 * base, floor)), np.nan)
            # exponential time constant over the falling part
            arr = np.array([v_ for _, v_ in tr])
            tt = np.array([t_ for t_, _ in tr])
            k2 = arr > max(floor, 1e-6)
            tau = np.nan
            if k2.sum() >= 4:
                sl_ = np.polyfit(tt[k2][:8], np.log(arr[k2][:8]), 1)[0]
                tau = -1.0 / sl_ if sl_ < 0 else np.nan
            taus.append(tau)
            rows.append((s, float(d["t"][i]), base, floor, half, tenth, tau,
                         float(np.mean(np.abs(d["cs_v"][i - W4:i]))) * 3.6))
    print(f"     {'seg':>3s} {'t edge':>8s} {'pre p90':>8s} {'floor':>7s} {'t_half':>7s} "
          f"{'t_10%':>7s} {'tau s':>7s} {'kmh':>6s}")
    for r in rows:
        print(f"     {r[0]:3d} {r[1]:8.2f} {r[2]:8.0f} {r[3]:7.0f} {r[4]:7.3f} {r[5]:7.3f} "
              f"{r[6]:7.3f} {r[7]:6.1f}")
    tv = np.array([r[6] for r in rows], float)
    hv = np.array([r[4] for r in rows], float)
    tb = boot_med(tv)
    hb = boot_med(hv)
    print(f"\n     time constant tau: median {tb[0]:.3f} s [{tb[1]:.3f}, {tb[2]:.3f}]  "
          f"(n={int(np.isfinite(tv).sum())} edges)")
    print(f"     time to half:      median {hb[0]:.3f} s [{hb[1]:.3f}, {hb[2]:.3f}]")
    print("     ⚠ n is small (every clean edge on the route). The CI is a bootstrap over edges and")
    print("       is honest about that; do not read it as a precise plant time constant.")
    OUT["s5"]["tau"] = list(tb)
    OUT["s5"]["t_half"] = list(hb)
    OUT["s5"]["edges"] = [list(map(float, r[1:])) for r in rows]


# =================================================================================================
def s6(W):
    hdr("S6  LANE CHANGE -- TRIGGER OR COINCIDENCE?  Every blinker-up episode while engaged above\n"
        "    40 km/h: did a burst follow, and with what latency relative to the angle excursion?")
    OUT["s6"] = []
    nlc = nburst = 0
    print(f"  {'seg':>3s} {'blink t0':>9s} {'dur':>6s} {'kmh':>6s} | {'d|ang| max':>10s} "
          f"{'|cmd| max':>9s} {'env pre':>8s} {'env peak':>9s} {'ratio':>7s} | "
          f"{'lat: blink->env':>15s} {'ang->env':>9s} {'cmd->env':>9s}")
    for s, d in segs("V81/r67"):
        fs = C31.fs_of(d)
        e = smooth(env(d["tq"], fs, *BURST), fs)
        lat = d["cc_lat"] > 0.5
        angl = lowpass(d["ang"], fs, 1.0)
        v = np.abs(d["cs_v"])
        for a, b in runs_of((d["cs_lchg"] > 0.5) & lat & (v >= 40 * KMH)):
            if (b - a) / fs < 0.5:
                continue
            nlc += 1
            w0, w1 = max(0, a - int(3 * fs)), min(len(e), b + int(8 * fs))
            pre = float(np.percentile(e[w0:a], 90)) if a > w0 + 10 else np.nan
            post = e[a:w1]
            pk = float(np.max(post)) if len(post) else np.nan
            base = float(np.median(angl[w0:a])) if a > w0 + 10 else np.nan
            dang = float(np.max(np.abs(angl[a:w1] - base))) if len(post) else np.nan
            cmax = float(np.max(np.abs(d["sc_tq"][a:w1]))) if len(post) else np.nan
            thr = max(400.0, 3 * pre) if np.isfinite(pre) else 400.0
            hit = np.flatnonzero(post > thr)
            t_env = (a + hit[0]) / fs if len(hit) else np.nan
            ai = np.flatnonzero(np.abs(angl[a:w1] - base) > 2.0)
            t_ang = (a + ai[0]) / fs if len(ai) else np.nan
            ci = np.flatnonzero(np.abs(d["sc_tq"][a:w1]) > 600)
            t_cmd = (a + ci[0]) / fs if len(ci) else np.nan
            if len(hit):
                nburst += 1
            print(f"  {s:3d} {d['t'][a]:9.2f} {(b - a) / fs:6.2f} "
                  f"{np.mean(v[a:b]) * 3.6:6.1f} | {dang:10.1f} {cmax:9.0f} {pre:8.0f} "
                  f"{pk:9.0f} {pk / max(pre,1e-9):7.2f} | "
                  f"{(t_env - a / fs) if np.isfinite(t_env) else np.nan:15.2f} "
                  f"{(t_env - t_ang) if np.isfinite(t_env) and np.isfinite(t_ang) else np.nan:9.2f} "
                  f"{(t_env - t_cmd) if np.isfinite(t_env) and np.isfinite(t_cmd) else np.nan:9.2f}")
            OUT["s6"].append(dict(seg=s, t0=float(d["t"][a]), dur=float((b - a) / fs),
                                  v=float(np.mean(v[a:b]) * 3.6), dang=dang, cmax=cmax,
                                  pre=pre, peak=pk,
                                  lat_blink=float(t_env - a / fs) if np.isfinite(t_env) else None,
                                  lat_ang=float(t_env - t_ang) if np.isfinite(t_env) and np.isfinite(t_ang) else None,
                                  lat_cmd=float(t_env - t_cmd) if np.isfinite(t_env) and np.isfinite(t_cmd) else None))
    print(f"\n  {nburst} of {nlc} engaged lane-change episodes above 40 km/h produced a burst "
          f"(envelope > max(400, 3x pre-episode p90)).")
    print("  ⇒ a lane change is NEITHER necessary NOR sufficient if this fraction is small; it is a")
    print("    TRIGGER only if the burst reliably FOLLOWS the angle excursion with positive latency.")
    OUT["s6_summary"] = dict(n_lc=nlc, n_burst=nburst)


def main():
    print("  cutting windows ...", flush=True)
    W = {b: windows(b) for b in ORDER}
    ALL = {b: burst_events(b) for b in ORDER}
    s1_s2(W, ALL)
    s3(W)
    s4(W)
    s5(W)
    s6(W)
    (ROOT / "_scratch/cache/r67x" / "r67_t4sharp.json").write_text(
        json.dumps(OUT, indent=1, default=lambda o: str(o)))
    print(f"\nwrote {ROOT / '_scratch/cache/r67x' / 'r67_t4sharp.json'}")


if __name__ == "__main__":
    main()
