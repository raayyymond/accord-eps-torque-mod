#!/usr/bin/env python3
r"""IS THE RATCHET THE ENVELOPE OF THE 21-28 Hz CARRIER?  THE DISCRIMINATOR, PRE-REGISTERED.

WHY THIS FILE EXISTS AND WHAT IT ADDS OVER `hf_lf_03/04`
  `hf_lf_04` already ran the coupling / sideband / bicoherence battery on routes 9e, 97, 96, 85 and
  came back NEGATIVE (no sidebands anywhere; the two statistics that fired fired equally in the
  negative control band).  Three things were left undone and each one can flip the verdict:

  🛑 G1  A BANDWIDTH ERROR THAT MAKES `hf_lf_04`'s ENVELOPE TEST UNABLE TO SEE THE ANSWER.
        The analytic envelope of a band of width W Hz cannot carry envelope content above ~W Hz,
        and is unambiguous only to W/2.  `hf_lf_04` searched 3-9 Hz using bands of width
        4 Hz (22-26), 5 Hz (26-31), 6 Hz (32-38), 7 Hz (15-22), 9 Hz (40-49), 10 Hz (20-30).
        **The 22-26 Hz band CANNOT show an envelope line above ~4 Hz by construction** -- which is
        exactly why its envelope peak landed on the 3.12 Hz bottom bin in every single arm.
        ⇒ testing a 6-12 Hz envelope on a ~25 Hz carrier needs a band of width >= ~24 Hz.
        T0 below MEASURES this failure rather than asserting it.
  G2  9-12 Hz was never searched (`LFWIN` = 3-9) and the operator placed the ratchet at 6-12.
  G3  Routes `a5` (V105) and `a4` (V104) -- the two newest drives, and V105 is the build that
        deliberately MOVES the carrier -- were never analysed at all.
  G4  The discriminator that actually separates the hypotheses -- does ratchet energy survive when
        the carrier is ABSENT -- has never been run in any form, on any route.
  G5  `hf_lf_01`'s pipeline positive control only ever tested f_LF = 0.6 / 1.2 / 2.5 Hz.  The
        estimator has never been validated at 6-12 Hz, which is the only band that matters here.

TWO DISTINCT CLAIMS, TESTED SEPARATELY -- they are NOT the same claim
  CLAIM A (perceptual)  the operator's felt ratchet IS the amplitude envelope of the carrier.
        A linear sensor sees NO energy at f_m from a pure AM signal -- only f_c +- f_m.  What the
        hand feels is the envelope, because flesh rectifies.  So Claim A is tested by asking
        whether the ENVELOPE ITSELF fluctuates at 6-12 Hz (T1), NOT by 6-12 Hz energy in `tq`.
  CLAIM B (instrumental)  the kit's MEASURED ~7.8 Hz line in the torsion bar is a product of the
        carrier.  Tested by sidebands (T2) and by survival-when-carrier-absent (T3).
  Reporting them merged is how this question has stayed open.  They are reported apart.

THE PRE-REGISTRATION.  Written before any number was computed; nothing below is edited after.
  T0  CONTROLS FIRST, and they gate everything.
      T0a POSITIVE  synthetic carrier at the measured f_c, amplitude-modulated at f_m = 8.0 Hz,
          depth m in {0.15, 0.35}, added to the REAL `tq` at a realistic amplitude, pushed through
          the IDENTICAL estimator.  PASS = the wide (f_c +- 14 Hz) envelope recovers a line within
          0.5 Hz of 8.0 with prominence above the null.  Simultaneously run at f_c +- 2 Hz, which
          is PREDICTED TO FAIL.  If narrow fails and wide passes, G1 is demonstrated, not asserted.
      T0b NEGATIVE  the same carrier with NO modulation plus an INDEPENDENT additive 8 Hz
          oscillation of matched RMS.  Every statistic must separate T0a from T0b.  A statistic
          that fires on both is discarded before it is applied to real data.
      T0c the pre-declared CONTROL BAND, equal width, centred away from f_c, on every real arm.
  T1  CLAIM A.  Envelope-line prominence in 5-13 Hz of the analytic envelope of the WIDE
      carrier-centred band, against a null that phase-randomises ONLY that band (200 draws), so
      all low-frequency structure and all burstiness is preserved.  Plus the per-window speed and
      wheel-order census, because a line that tracks speed is a tyre order, not an envelope.
  T2  CLAIM B.  Symmetric sideband excess at f_c +- f_m against the local background, both
      sidebands required, phase-randomised-record null.
  T3  CLAIM B, THE DISCRIMINATOR.  Per-window log band RMS, windows split into terciles of CARRIER
      (21-28 Hz) energy.
      🛑 THE CONFOUND THAT DECIDES THIS TEST: `HANDOFF-2026-08-22` section 5.3 establishes the
      carrier is driven by STEERING RATE (~90x stock at 15-40 deg/s, collapsing to stock above
      100).  So carrier-LOW windows are also low-RATE windows, and ANY quantity that grows with
      steering activity will look "carrier-coupled".  Two defences, both pre-registered:
        (i)  a RATE-MATCHED tercile split -- terciles taken WITHIN each rate bin, then pooled;
        (ii) a DIFFERENCE IN SLOPES.  beta_c = d log(ratchet) / d log(carrier) and
             beta_x = d log(ratchet) / d log(CTRL band) over the same windows.  Common driving
             intensity moves both identically, so it cancels in  DELTA = beta_c - beta_x.
      PRE-REGISTERED PREDICTIONS
        H_ENVELOPE (ONE mechanism)  ratchet in the bottom carrier tercile falls to the STOCK floor
             at matched speed, AND DELTA is clearly positive (pure AM gives beta_c ~ +1).
        H_TWO (TWO mechanisms)      ratchet SURVIVES in the bottom tercile well above the stock
             floor, AND DELTA ~ 0 once the control band is subtracted.
      CIs by bootstrap over EPISODES, never windows (`feedback-episodes-not-windows`).
  T4  V105 CARRIER-MOVE TEST.  V105 notches 25.5 Hz.  If the ratchet is the carrier's envelope,
      a build that removes the carrier must remove the ratchet.  a5 (V105) vs a4 (V104) vs 9e/96
      (6x, no notch) vs 97 (stock), carrier and ratchet reported side by side.

CHANNEL  `tq` (0x18F column torsion bar).  NOT 427: the source cell changes build to build, it is
  rectified, and 20-24 Hz aliases with fold ratio 0.23-2.57 -- a valid null there, never a
  magnitude.  `tq` transfer through the interp pipeline is 0.99 at 6-9 Hz and 0.83 at 22-26 Hz
  (`_hf_lf_controls.json`), and the interpolation artefact is 0.8-7.5 % of band amplitude.
ENVELOPE  TRUE ANALYTIC (complex ifft of the one-sided 2X band, then |.|).  NOT the retired
  rectified `band_envelope`, which manufactures exactly the sidebands under test.

OUTPUT `rlog-tools/_hf_lf_discriminator.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, KMH, CIRC = L.FS, 3.6, 2.0805
ROUTE_LABEL = {"97": "STOCK 1x", "85": "V100 4x", "96": "V102 6x", "9e": "V103 6x",
               "a4": "V104 6x", "a5": "V105 6x+NOTCH"}
ROUTES = ["a5", "a4", "9e", "96", "85", "97"]

CARRIER = (21.0, 28.0)          # the mode, per HANDOFF-2026-08-22 s5
RATCHET = (6.0, 12.0)           # the operator's own placement, "several per second"
CTRL1 = (32.0, 38.0)            # ⚠ overlaps wheel order 3 (32.7-40.1 Hz) at these speeds
CTRL2 = (45.0, 49.0)            # ⚠ pipeline transfer only ~0.57 here
WIDE_HALF = 14.0                # carrier-centred wide band half-width: supports envelope to 14 Hz
NARROW_HALF = 2.0               # the width class hf_lf_04 used -- PREDICTED TO FAIL T0a
ENVWIN = (5.0, 13.0)            # T1 search window (G2: hf_lf_04 stopped at 9)

NSEG, HOP = 512, 256            # 5.12 s -> 0.1953 Hz bins
WSEG, WHOP = 256, 128           # 2.56 s discriminator windows
NSURR = 200
RNG0 = 12345

_W = np.hanning(NSEG)
_R = np.arange(NSEG, dtype=float)
_SCALE = float(np.mean(_W ** 2))
FREQ = np.fft.rfftfreq(NSEG, 1.0 / FS)


def hdr(s):
    print("\n" + "=" * 112)
    print(s)
    print("=" * 112, flush=True)


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


# ---------------------------------------------------------------- blocks / episodes -------------
def blocks(rt):
    out = []
    for s in L.ROUTES[rt]["segs"]:
        d = L.load_seg(rt, s)
        t = d["t"]
        brk = np.nonzero(np.diff(t) > L.GAP_S)[0]
        for a, b in zip([0] + [int(x) + 1 for x in brk], [int(x) + 1 for x in brk] + [len(t)]):
            if b - a < 4 or t[b - 1] - t[a] < 2.0:
                continue
            tt = np.arange(t[a], t[b - 1], 1.0 / FS)
            blk = {"t": tt, "_seg": s}
            for k, v in d.items():
                if k.startswith("_") or k == "t" or np.shape(v) != np.shape(t):
                    continue
                blk[k] = np.interp(tt, t[a:b], v[a:b])
            out.append(blk)
    return out


def episodes(rt, engaged=True, vlo=0.0, vhi=200.0, minlen=NSEG):
    out = []
    for blk in blocks(rt):
        v = np.asarray(blk["v_rear"], float) * KMH
        eng = np.asarray(blk["cc_lat"], float) > 0.5
        want = (eng if engaged else ~eng) & (v >= vlo) & (v < vhi)
        idx = np.nonzero(np.diff(want.astype(int)) != 0)[0] + 1
        for a, b in zip([0] + list(idx), list(idx) + [len(want)]):
            if not want[a] or (b - a) < minlen:
                continue
            ep = {k: np.asarray(blk[k], float)[a:b] for k in blk
                  if not k.startswith("_") and np.shape(blk[k]) == np.shape(blk["t"])}
            ep["_seg"], ep["_v"] = blk["_seg"], float(np.median(v[a:b]))
            ep["_vall"] = v[a:b]
            out.append(ep)
    return out


# ---------------------------------------------------------------- estimators --------------------
def analytic_env(x, lo, hi, fs=FS):
    """TRUE analytic envelope.  NOT the retired rectified `band_envelope`."""
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.fft(x - x.mean())
    f = np.fft.fftfreq(n, 1.0 / fs)
    Z = np.zeros(n, complex)
    m = (f >= lo) & (f < hi)
    Z[m] = 2.0 * X[m]
    return np.abs(np.fft.ifft(Z))


def band_rms(x, lo, hi, fs=FS):
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X = np.where((f >= lo) & (f < hi), X, 0.0)
    return float(np.sqrt(np.mean(np.fft.irfft(X, n=len(x)) ** 2)))


def phase_rand_band(x, lo, hi, rng, fs=FS):
    n = len(x)
    X = np.fft.rfft(np.asarray(x, float))
    f = np.fft.rfftfreq(n, 1.0 / fs)
    m = (f >= lo) & (f < hi)
    X = X.copy()
    X[m] = np.abs(X[m]) * np.exp(1j * rng.uniform(0, 2 * np.pi, int(m.sum())))
    return np.fft.irfft(X, n=n)


def phase_rand_full(x, rng):
    X = np.fft.rfft(np.asarray(x, float))
    X = np.abs(X) * np.exp(1j * rng.uniform(0, 2 * np.pi, len(X)))
    X[0] = np.abs(X[0])
    return np.fft.irfft(X, n=len(x))


def parts(series, nseg=NSEG, hop=HOP):
    w, r = np.hanning(nseg), np.arange(nseg, dtype=float)
    Xs = []
    for x in series:
        x = np.asarray(x, float)
        for s in range(0, len(x) - nseg + 1, hop):
            y = x[s:s + nseg]
            c = np.polyfit(r, y, 1)
            Xs.append(np.fft.rfft((y - (c[0] * r + c[1])) * w))
    return np.asarray(Xs)


def welch_P(X):
    P = (np.abs(X) ** 2).mean(0) * 2.0 / (NSEG ** 2) / _SCALE
    P[0] /= 2.0
    P[-1] /= 2.0
    return P


def norm_env(envs):
    return [(e - e.mean()) / max(e.mean(), 1e-9) for e in envs]


def env_line(series, lo, hi, win=ENVWIN, half=1.5, gap=0.4):
    """Local prominence of the strongest line of the envelope's OWN spectrum inside `win`.
    Local prominence is blind to a smooth 1/f rise, which is what killed hf_lf_03 v1."""
    ne = norm_env([analytic_env(x, lo, hi) for x in series])
    X = parts(ne)
    if not len(X):
        return None
    P = welch_P(X)
    m = (FREQ >= win[0]) & (FREQ <= win[1])
    idx = np.flatnonzero(m)
    best = (-1.0, np.nan)
    for i in idx:
        f0 = FREQ[i]
        bg = (np.abs(FREQ - f0) <= half) & (np.abs(FREQ - f0) > gap)
        if bg.sum() < 4:
            continue
        pr = P[i] / max(float(np.median(P[bg])), 1e-30)
        if pr > best[0]:
            best = (float(pr), float(f0))
    return dict(prom=best[0], f=best[1])


def env_line_null(series, lo, hi, rng, n=NSURR, win=ENVWIN):
    out = np.empty(n)
    for k in range(n):
        r = env_line([phase_rand_band(x, lo, hi, rng) for x in series], lo, hi, win=win)
        out[k] = r["prom"] if r else np.nan
    return out


def sideband_score(P, fc, fm, half=1.5, gap=0.4):
    def val(f0):
        i = int(np.argmin(np.abs(FREQ - f0)))
        bg = (np.abs(FREQ - f0) <= half) & (np.abs(FREQ - f0) > gap)
        return P[i] / max(float(np.median(P[bg])), 1e-30)
    lo, hi = val(fc - fm), val(fc + fm)
    return float(min(lo, hi)), float(lo), float(hi)


# ---------------------------------------------------------------- T0 controls -------------------
def t0_controls(car, fc, rng):
    """T0a positive (AM), T0b negative (independent additive tone).  Same estimator for both."""
    fm = 8.0
    amp = float(np.median([band_rms(x, *CARRIER) for x in car])) or 1.0
    out = {"fc": fc, "fm": fm, "carrier_rms": amp, "cases": []}
    for depth in (0.15, 0.35):
        for kind in ("AM", "INDEP"):
            syn = []
            for x in car:
                n = len(x)
                t = np.arange(n) / FS
                ph = rng.uniform(0, 2 * np.pi)
                if kind == "AM":
                    s = amp * np.sqrt(2) * (1.0 + depth * np.cos(2 * np.pi * fm * t)) \
                        * np.cos(2 * np.pi * fc * t + ph)
                else:
                    # unmodulated carrier + an INDEPENDENT 8 Hz tone of matched added RMS
                    s = amp * np.sqrt(2) * np.cos(2 * np.pi * fc * t + ph) \
                        + amp * depth * np.sqrt(2) / np.sqrt(2) \
                        * np.cos(2 * np.pi * fm * t + rng.uniform(0, 2 * np.pi))
                syn.append(np.asarray(x, float) + s)
            row = dict(depth=depth, kind=kind)
            for tag, hw in (("wide", WIDE_HALF), ("narrow", NARROW_HALF)):
                lo, hi = max(fc - hw, 0.5), fc + hw
                r = env_line(syn, lo, hi)
                nl = env_line_null(syn, lo, hi, np.random.default_rng(RNG0 + 7), n=40)
                row[tag] = dict(band=[lo, hi], prom=r["prom"], f=r["f"],
                                null_p95=float(np.nanpercentile(nl, 95)),
                                hit=bool(abs(r["f"] - fm) <= 0.5
                                         and r["prom"] > float(np.nanpercentile(nl, 95))))
            P = welch_P(parts(syn))
            row["sideband"] = sideband_score(P, fc, fm)[0]
            out["cases"].append(row)
    return out


# ---------------------------------------------------------------- T3 discriminator --------------
def window_table(eps):
    """Per-window log band RMS + speed + steering rate, tagged by episode index."""
    rows = []
    for ei, e in enumerate(eps):
        x = np.asarray(e["tq"], float)
        v = np.asarray(e["_vall"], float)
        rc = np.abs(np.asarray(e.get("rate_c", np.zeros_like(x)), float))
        for s in range(0, len(x) - WSEG + 1, WHOP):
            y = x[s:s + WSEG]
            rows.append(dict(ep=ei,
                             car=band_rms(y, *CARRIER), rat=band_rms(y, *RATCHET),
                             c1=band_rms(y, *CTRL1), c2=band_rms(y, *CTRL2),
                             v=float(np.median(v[s:s + WSEG])),
                             rate=float(np.median(rc[s:s + WSEG]))))
    return rows


def _slopes(rows):
    if len(rows) < 12:
        return dict(b_car=np.nan, b_c1=np.nan, delta=np.nan)
    lr = np.log(np.maximum([r["rat"] for r in rows], 1e-9))
    lc = np.log(np.maximum([r["car"] for r in rows], 1e-9))
    lx = np.log(np.maximum([r["c1"] for r in rows], 1e-9))
    b_car = float(np.polyfit(lc, lr, 1)[0])
    b_c1 = float(np.polyfit(lx, lr, 1)[0])
    return dict(b_car=b_car, b_c1=b_c1, delta=b_car - b_c1)


def _terciles(rows, key="car"):
    v = np.asarray([r[key] for r in rows], float)
    lo, hi = np.percentile(v, [33.333, 66.667])
    return [r for r in rows if r[key] <= lo], [r for r in rows if r[key] >= hi]


def discriminator(eps, rng):
    rows = window_table(eps)
    if len(rows) < 12:
        return None
    out = dict(n_win=len(rows), n_ep=len(eps))
    botr, topr = _terciles(rows)
    out["plain"] = dict(
        rat_bot=float(np.median([r["rat"] for r in botr])),
        rat_top=float(np.median([r["rat"] for r in topr])),
        car_bot=float(np.median([r["car"] for r in botr])),
        car_top=float(np.median([r["car"] for r in topr])),
        c1_bot=float(np.median([r["c1"] for r in botr])),
        c1_top=float(np.median([r["c1"] for r in topr])),
        v_bot=float(np.median([r["v"] for r in botr])),
        v_top=float(np.median([r["v"] for r in topr])),
        rate_bot=float(np.median([r["rate"] for r in botr])),
        rate_top=float(np.median([r["rate"] for r in topr])))
    out["plain"]["rat_ratio"] = out["plain"]["rat_bot"] / max(out["plain"]["rat_top"], 1e-9)
    out["plain"]["car_ratio"] = out["plain"]["car_bot"] / max(out["plain"]["car_top"], 1e-9)
    out["plain"]["c1_ratio"] = out["plain"]["c1_bot"] / max(out["plain"]["c1_top"], 1e-9)

    # --- RATE-MATCHED: terciles taken WITHIN each rate bin, then pooled -------------------
    edges = [0.0, 5.0, 15.0, 40.0, 100.0, 1e9]
    mb, mt = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sub = [r for r in rows if a <= r["rate"] < b]
        if len(sub) < 9:
            continue
        lo, hi = _terciles(sub)
        mb += lo
        mt += hi
    out["rate_matched"] = dict(n_bot=len(mb), n_top=len(mt))
    if len(mb) >= 6 and len(mt) >= 6:
        out["rate_matched"].update(
            rat_bot=float(np.median([r["rat"] for r in mb])),
            rat_top=float(np.median([r["rat"] for r in mt])),
            car_bot=float(np.median([r["car"] for r in mb])),
            car_top=float(np.median([r["car"] for r in mt])),
            c1_bot=float(np.median([r["c1"] for r in mb])),
            c1_top=float(np.median([r["c1"] for r in mt])),
            rate_bot=float(np.median([r["rate"] for r in mb])),
            rate_top=float(np.median([r["rate"] for r in mt])))
        out["rate_matched"]["rat_ratio"] = (out["rate_matched"]["rat_bot"]
                                            / max(out["rate_matched"]["rat_top"], 1e-9))
        out["rate_matched"]["car_ratio"] = (out["rate_matched"]["car_bot"]
                                            / max(out["rate_matched"]["car_top"], 1e-9))
        out["rate_matched"]["c1_ratio"] = (out["rate_matched"]["c1_bot"]
                                           / max(out["rate_matched"]["c1_top"], 1e-9))

    # --- slopes + EPISODE bootstrap ------------------------------------------------------
    out["slopes"] = _slopes(rows)
    by_ep = {}
    for r in rows:
        by_ep.setdefault(r["ep"], []).append(r)
    keys = list(by_ep)
    if len(keys) >= 2:
        bs_d, bs_r = [], []
        for _ in range(1000):
            pick = rng.choice(keys, size=len(keys), replace=True)
            samp = [r for k in pick for r in by_ep[k]]
            s = _slopes(samp)
            if np.isfinite(s["delta"]):
                bs_d.append(s["delta"])
            b2, t2 = _terciles(samp)
            if len(b2) >= 3 and len(t2) >= 3:
                bs_r.append(float(np.median([r["rat"] for r in b2]))
                            / max(float(np.median([r["rat"] for r in t2])), 1e-9))
        if bs_d:
            out["slopes"]["delta_ci"] = [float(np.percentile(bs_d, 2.5)),
                                         float(np.percentile(bs_d, 97.5))]
        if bs_r:
            out["plain"]["rat_ratio_ci"] = [float(np.percentile(bs_r, 2.5)),
                                            float(np.percentile(bs_r, 97.5))]
    else:
        out["slopes"]["delta_ci"] = None
        out["plain"]["rat_ratio_ci"] = None
    # split-half episode null on the ratio (feedback-episodes-not-windows)
    if len(keys) >= 4:
        h = len(keys) // 2
        sh = []
        for _ in range(400):
            k = list(rng.permutation(keys))
            A = [r for kk in k[:h] for r in by_ep[kk]]
            B = [r for kk in k[h:] for r in by_ep[kk]]
            if len(A) < 6 or len(B) < 6:
                continue
            sh.append(float(np.median([r["rat"] for r in A]))
                      / max(float(np.median([r["rat"] for r in B])), 1e-9))
        if sh:
            out["splithalf_ratio_ci"] = [float(np.percentile(sh, 2.5)),
                                         float(np.percentile(sh, 97.5))]
    return out


# ---------------------------------------------------------------- per arm -----------------------
def score_arm(rt, eps, label):
    rng = np.random.default_rng(RNG0 + (abs(hash((rt, label))) % 9973))
    car = [e["tq"] for e in eps]
    X = parts(car)
    P = welch_P(X)
    mhf = (FREQ >= 15.0) & (FREQ <= 35.0)
    fc = float(FREQ[mhf][np.argmax(P[mhf])])
    mr = (FREQ >= 5.5) & (FREQ <= 12.5)
    fm = float(FREQ[mr][np.argmax(P[mr])])
    vmed = float(np.median([e["_v"] for e in eps]))
    res = dict(route=rt, label=label, n_ep=len(eps),
               s=float(sum(len(e["t"]) for e in eps) / FS), v_med=vmed,
               v_p10=float(np.percentile(np.concatenate([e["_vall"] for e in eps]), 10)),
               v_p90=float(np.percentile(np.concatenate([e["_vall"] for e in eps]), 90)),
               wo1=vmed / KMH / CIRC, wo2=2 * vmed / KMH / CIRC, wo3=3 * vmed / KMH / CIRC,
               n_seg=int(X.shape[0]), f_carrier=fc, f_ratchet=fm,
               rms_car=float(np.median([band_rms(x, *CARRIER) for x in car])),
               rms_rat=float(np.median([band_rms(x, *RATCHET) for x in car])),
               rms_c1=float(np.median([band_rms(x, *CTRL1) for x in car])))

    # --- T1: wide carrier-centred envelope, plus the narrow band and the control band -----
    res["T1"] = {}
    bands = {"WIDE(fc+-14)": (max(fc - WIDE_HALF, 0.5), fc + WIDE_HALF),
             "NARROW(fc+-2)": (max(fc - NARROW_HALF, 0.5), fc + NARROW_HALF),
             "CTRL_WIDE(45+-14)": (31.0, 59.0)}
    for bn, (lo, hi) in bands.items():
        r = env_line(car, lo, hi)
        if r is None:
            continue
        nl = env_line_null(car, lo, hi, rng, n=NSURR)
        res["T1"][bn] = dict(band=[lo, hi], prom=r["prom"], f=r["f"],
                             null_p95=float(np.nanpercentile(nl, 95)),
                             null_med=float(np.nanmedian(nl)),
                             p=float((1 + np.sum(nl >= r["prom"])) / (NSURR + 1)))

    # --- T2: sidebands --------------------------------------------------------------------
    s, a, b = sideband_score(P, fc, fm)
    sn = [sideband_score(welch_P(parts([phase_rand_full(x, rng) for x in car])), fc, fm)[0]
          for _ in range(60)]
    res["T2"] = dict(fc=fc, fm=fm, both=s, lower=a, upper=b,
                     null_p95=float(np.percentile(sn, 95)),
                     p=float((1 + np.sum(np.asarray(sn) >= s)) / 61))

    # --- T3: the discriminator ------------------------------------------------------------
    res["T3"] = discriminator(eps, rng)
    return res


def main():
    out = {"pre_registered": True, "carrier": CARRIER, "ratchet": RATCHET,
           "ctrl1": CTRL1, "ctrl2": CTRL2, "envwin": ENVWIN, "routes": {}}
    arms = [("ENGAGED hwy", True, 70.0, 200.0),
            ("ENGAGED mid", True, 40.0, 70.0),
            ("ENGAGED low", True, 16.0, 40.0),
            ("ENGAGED micro", True, 0.0, 16.0),
            ("manual hwy", False, 70.0, 200.0)]

    # ---- T0 controls, once, on the richest engaged-highway arm available ------------------
    ctl_rt = None
    for rt in ROUTES:
        if reg(rt):
            e = episodes(rt, True, 70.0, 200.0)
            if len(e) >= 2:
                ctl_rt = (rt, e)
                break
    if ctl_rt:
        rt, e = ctl_rt
        rng = np.random.default_rng(RNG0)
        Pc = welch_P(parts([x["tq"] for x in e]))
        mhf = (FREQ >= 15.0) & (FREQ <= 35.0)
        fc = float(FREQ[mhf][np.argmax(Pc[mhf])])
        hdr("T0  CONTROLS FIRST -- run on route %s (%s) ENGAGED hwy, fc=%.2f Hz, f_m=8.0 Hz"
            % (rt, ROUTE_LABEL.get(rt, rt), fc))
        t0 = t0_controls([x["tq"] for x in e], fc, rng)
        out["T0"] = t0
        print("  %-5s %-6s | %-34s | %-34s | sideband" % ("depth", "kind",
                                                          "WIDE  fc+-14 (predicted PASS on AM)",
                                                          "NARROW fc+-2 (predicted FAIL on AM)"))
        for row in t0["cases"]:
            print("  %-5.2f %-6s | prom %6.2f @ %5.2f Hz null95 %5.2f %-4s | "
                  "prom %6.2f @ %5.2f Hz null95 %5.2f %-4s | %.2f"
                  % (row["depth"], row["kind"],
                     row["wide"]["prom"], row["wide"]["f"], row["wide"]["null_p95"],
                     "HIT" if row["wide"]["hit"] else "miss",
                     row["narrow"]["prom"], row["narrow"]["f"], row["narrow"]["null_p95"],
                     "HIT" if row["narrow"]["hit"] else "miss",
                     row["sideband"]))

    for rt in ROUTES:
        if not reg(rt):
            print("  route %s: no segments" % rt)
            continue
        out["routes"][rt] = {}
        for lab, eng, vlo, vhi in arms:
            eps = episodes(rt, engaged=eng, vlo=vlo, vhi=vhi, minlen=NSEG)
            if len(eps) < 1:
                continue
            r = score_arm(rt, eps, lab)
            out["routes"][rt][lab] = r
            hdr("ROUTE %s (%s)  %s  %d ep, %.1f s, v=%.1f km/h [p10 %.0f, p90 %.0f] "
                "wheel orders %.1f/%.1f/%.1f Hz"
                % (rt, ROUTE_LABEL.get(rt, rt), lab, r["n_ep"], r["s"], r["v_med"],
                   r["v_p10"], r["v_p90"], r["wo1"], r["wo2"], r["wo3"]))
            print("  carrier peak %.2f Hz | ratchet peak %.2f Hz | band RMS  car %.3g  rat %.3g "
                  " ctrl %.3g" % (r["f_carrier"], r["f_ratchet"], r["rms_car"], r["rms_rat"],
                                  r["rms_c1"]))
            print("  T1 ENVELOPE LINE in %.0f-%.0f Hz (CLAIM A)" % ENVWIN)
            for bn, d in r["T1"].items():
                print("     %-18s [%5.1f,%5.1f] prom %6.2f @ %5.2f Hz  null med %5.2f p95 %5.2f "
                      " p=%.3f %s" % (bn, d["band"][0], d["band"][1], d["prom"], d["f"],
                                      d["null_med"], d["null_p95"], d["p"],
                                      "<== LINE" if d["p"] < 0.05 else ""))
            t2 = r["T2"]
            print("  T2 SIDEBANDS (CLAIM B) at fc=%.2f +- fm=%.2f -> %.2f / %.2f Hz : both %.2f "
                  "(lo %.2f hi %.2f) null95 %.2f p=%.3f %s"
                  % (t2["fc"], t2["fm"], t2["fc"] - t2["fm"], t2["fc"] + t2["fm"], t2["both"],
                     t2["lower"], t2["upper"], t2["null_p95"], t2["p"],
                     "<== SIDEBANDS" if t2["p"] < 0.05 else "NULL"))
            t3 = r["T3"]
            if t3:
                p_, s_ = t3["plain"], t3["slopes"]
                ci = p_.get("rat_ratio_ci")
                sh = t3.get("splithalf_ratio_ci")
                print("  T3 DISCRIMINATOR  %d windows / %d episodes" % (t3["n_win"], t3["n_ep"]))
                print("     carrier terciles  bot/top:  CARRIER %.3g/%.3g (%.3f)   "
                      "RATCHET %.3g/%.3g (%.3f%s)   CTRL %.3g/%.3g (%.3f)"
                      % (p_["car_bot"], p_["car_top"], p_["car_ratio"],
                         p_["rat_bot"], p_["rat_top"], p_["rat_ratio"],
                         "" if not ci else " [%.2f,%.2f]" % tuple(ci),
                         p_["c1_bot"], p_["c1_top"], p_["c1_ratio"]))
                print("     census  speed bot/top %.1f/%.1f km/h   |rate_c| bot/top %.1f/%.1f"
                      % (p_["v_bot"], p_["v_top"], p_["rate_bot"], p_["rate_top"]))
                rm = t3.get("rate_matched", {})
                if "rat_ratio" in rm:
                    print("     RATE-MATCHED (terciles within rate bin, n=%d/%d): CARRIER %.3f  "
                          "RATCHET %.3f  CTRL %.3f   |rate| %.1f/%.1f"
                          % (rm["n_bot"], rm["n_top"], rm["car_ratio"], rm["rat_ratio"],
                             rm["c1_ratio"], rm["rate_bot"], rm["rate_top"]))
                print("     SLOPES  d log(rat)/d log(car) = %+.3f   vs CTRL %+.3f   "
                      "DELTA %+.3f%s   %s"
                      % (s_["b_car"], s_["b_c1"], s_["delta"],
                         "" if not s_.get("delta_ci") else " [%+.3f,%+.3f]" % tuple(s_["delta_ci"]),
                         "" if not sh else "| split-half null on ratio [%.2f,%.2f]" % tuple(sh)))

    (HERE / "_hf_lf_discriminator.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote", HERE / "_hf_lf_discriminator.json")


if __name__ == "__main__":
    main()
