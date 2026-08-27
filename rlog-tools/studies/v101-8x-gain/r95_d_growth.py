#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- **D. THE GROWTH ENVELOPE** + the limit-cycle vs noise-driven-resonance
discriminators, and **F-2. CAUSALITY** (does openpilot's command LEAD or FOLLOW the oscillation).

🛑 CONTROL FIRST.  "It grows into a steady state" is the signature of a self-excited limit cycle,
but a LINEAR resonance driven by broadband road/motor noise produces envelope excursions that look
exactly like growth.  Three controls run before any sigma is quoted:

  C1  PHASE-RANDOMISED SURROGATE.  Randomise the phases of the band-passed signal inside each
      engaged run.  This preserves the PSD exactly -- hence the linear resonance and its Q -- and
      destroys every nonlinearity.  The onset detector is run on the surrogate identically.  If
      the observed sigma distribution is inside the surrogate's, THE GROWTH IS NOT EVIDENCE OF
      SELF-EXCITATION.
  C2  KURTOSIS.  A pure sinusoid has kurtosis 1.5; a narrowband GAUSSIAN process has 3.0.  A
      saturating limit cycle drives the kurtosis DOWN toward 1.5.  Reported per band with the
      CTRL bands as the comparison.
  C3  ENVELOPE DISTRIBUTION.  A narrowband Gaussian process has a RAYLEIGH envelope
      (std/mean = 0.5227).  A limit cycle concentrates near its saturation amplitude
      (std/mean -> 0).
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

import numpy as np

import r95_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.fs()
lat = L.engaged()
t = L.col("t")
tq = L.col("tq")
rate_f = L.col("rate_f")
ang = L.col("ang")
x6b94 = L.col("x6b94")
sc_tq = L.col("sc_tq")
vms = np.abs(L.col("cs_v"))
tq_sus = L.lowpass(tq, FS, 3.0, mask=lat)

BANDS = {"B8": (7.3, 9.3), "B23": (21.5, 25.5), "CTRL": (2.5, 4.5), "CTRL2": (33.0, 43.0)}
CH = {"tq": tq, "rate_f": rate_f}
out = {}


def runs(mask, min_n):
    idx = np.where(mask)[0]
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


RUNS = runs(lat, 512)
print(f"FS {FS:.3f}   {len(RUNS)} engaged runs: " +
      "  ".join(f"{t[a]:.1f}-{t[b-1]:.1f}s ({(b-a)/FS:.1f}s)" for a, b in RUNS))


def smooth(x, w):
    k = np.ones(w) / w
    return np.convolve(x, k, mode="same")


def surrogate(bp_seg, rng):
    """Phase-randomise: identical PSD, no nonlinearity."""
    X = np.fft.rfft(bp_seg)
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0
    if len(bp_seg) % 2 == 0:
        ph[-1] = 0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=len(bp_seg))


# ======================================================================================
#  C2 / C3 -- the DISCRIMINATORS.  These need no detector and no threshold.
# ======================================================================================
print("\n" + "=" * 104)
print("C2 / C3.  LIMIT CYCLE vs NOISE-DRIVEN RESONANCE -- threshold-free discriminators")
print("   kurtosis:  1.50 = pure sinusoid    3.00 = narrowband GAUSSIAN noise")
print("   env std/mean: 0.000 = fixed amplitude    0.5227 = RAYLEIGH (Gaussian narrowband)")
print("=" * 104)
print(f"    {'channel':8s} {'band':6s} {'kurtosis':>9s} {'env std/mean':>13s} {'env p50':>10s} "
      f"{'env p95':>10s}   verdict")
disc = []
for ch, x in CH.items():
    for bn, (lo, hi) in BANDS.items():
        bp = L.bandpass(x, FS, lo, hi, mask=lat)
        env = L.band_envelope(x, FS, lo, hi, mask=lat)
        v = bp[lat]
        v = v[np.isfinite(v)]
        e = env[lat]
        e = e[np.isfinite(e)]
        kur = float(np.mean((v - v.mean()) ** 4) / np.var(v) ** 2)
        cv = float(e.std() / e.mean())
        vd = ("SINUSOIDAL/limit-cycle-like" if kur < 2.3 else
              "GAUSSIAN/noise-driven" if kur > 2.7 else "intermediate")
        print(f"    {ch:8s} {bn:6s} {kur:9.3f} {cv:13.3f} {np.percentile(e,50):10.1f} "
              f"{np.percentile(e,95):10.1f}   {vd}")
        disc.append(dict(ch=ch, band=bn, kurtosis=kur, env_cv=cv,
                         env_p50=float(np.percentile(e, 50)),
                         env_p95=float(np.percentile(e, 95)), verdict=vd))
out["C2_C3_discriminators"] = disc

# ======================================================================================
#  D.  ONSET DETECTION + EXPONENTIAL ENVELOPE FIT, with the SURROGATE control
# ======================================================================================
SM = int(round(0.30 * FS))          # 0.30 s smoother -- kills the 2*omega beat, keeps the ramp
MIN_RISE = int(round(0.30 * FS))
MAX_RISE = int(round(6.0 * FS))


def onsets(env, lo_thr, hi_thr):
    """Rising excursions from below lo_thr to above hi_thr.  Returns (i_start, i_end)."""
    o = []
    below = env < lo_thr
    i = 0
    n = len(env)
    while i < n - 1:
        if not below[i]:
            i += 1
            continue
        j = i
        while j < n and env[j] < hi_thr:
            j += 1
        if j >= n:
            break
        k = j
        while k > i and env[k] > lo_thr:
            k -= 1
        if MIN_RISE <= (j - k) <= MAX_RISE:
            o.append((k, j))
        i = max(j, i + 1)
    return o


def fit_sigma(env, a, b):
    """log-linear fit of the envelope over [a,b) -> sigma (1/s) and R^2."""
    y = np.log(np.maximum(env[a:b], 1e-9))
    xx = np.arange(b - a) / FS
    A = np.vstack([xx, np.ones_like(xx)]).T
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    r2 = 1 - np.var(y - A @ beta) / max(np.var(y), 1e-30)
    return float(beta[0]), float(r2)


print("\n" + "=" * 104)
print("D.  ONSETS -- envelope rises from the 25th to the 75th engaged percentile in 0.3-6.0 s.")
print("    sigma is the log-linear slope of the analytic envelope over the rise (1/s).")
print("    🛑 SURROGATE = phase-randomised, same PSD, 20 realisations, SAME detector.")
print("=" * 104)
rng = np.random.default_rng(31)
res = []
for ch, x in CH.items():
    for bn in ("B8", "B23", "CTRL"):
        lo, hi = BANDS[bn]
        env_all = L.band_envelope(x, FS, lo, hi, mask=lat)
        ee = env_all[lat]
        ee = ee[np.isfinite(ee)]
        lo_thr, hi_thr = np.percentile(ee, 25), np.percentile(ee, 75)
        sig, sat, dur = [], [], []
        for a, b in RUNS:
            e = smooth(env_all[a:b], SM)
            for (i0, i1) in onsets(e, lo_thr, hi_thr):
                s, r2 = fit_sigma(e, i0, i1)
                if r2 < 0.7:
                    continue
                sig.append(s)
                dur.append((i1 - i0) / FS)
                j1 = min(i1 + int(1.0 * FS), len(e))
                sat.append(float(np.median(e[i1:j1])) if j1 > i1 else float(e[i1]))
        # ---- surrogate
        ssig = []
        for _ in range(20):
            for a, b in RUNS:
                bp = L.bandpass(x, FS, lo, hi, mask=lat)[a:b]
                sg = surrogate(bp, rng)
                X = np.fft.fft(sg)
                f = np.fft.fftfreq(len(sg), 1 / FS)
                H = np.zeros(len(sg), complex)
                sel = (f >= lo) & (f <= hi)
                H[sel] = 2 * X[sel]
                e = smooth(np.abs(np.fft.ifft(H)), SM)
                for (i0, i1) in onsets(e, lo_thr, hi_thr):
                    s, r2 = fit_sigma(e, i0, i1)
                    if r2 >= 0.7:
                        ssig.append(s)
        if not sig:
            print(f"    {ch:7s} {bn:5s}  NO qualifying onsets")
            continue
        sig = np.array(sig)
        ssig = np.array(ssig) if len(ssig) else np.array([np.nan])
        onsets_per_min = len(sig) / (lat.sum() / FS / 60)
        surr_per_min = len(ssig) / 20 / (lat.sum() / FS / 60)
        print(f"\n    {ch:7s} {bn:5s}  {len(sig)} onsets ({onsets_per_min:.1f}/min)   "
              f"rise {np.median(dur):.2f} s (p10 {np.percentile(dur,10):.2f}, "
              f"p90 {np.percentile(dur,90):.2f})")
        print(f"             sigma  p25 {np.percentile(sig,25):6.2f}  p50 "
              f"{np.percentile(sig,50):6.2f}  p75 {np.percentile(sig,75):6.2f}  max "
              f"{sig.max():6.2f}  1/s")
        print(f"             SURROGATE sigma p25 {np.nanpercentile(ssig,25):6.2f}  p50 "
              f"{np.nanpercentile(ssig,50):6.2f}  p75 {np.nanpercentile(ssig,75):6.2f}   "
              f"({surr_per_min:.1f} onsets/min)")
        d50 = np.percentile(sig, 50) / np.nanpercentile(ssig, 50)
        print(f"             ⇒ observed/surrogate median sigma = {d50:5.3f}   "
              f"{'🛑 INSIDE the surrogate -- growth is NOT evidence of self-excitation' if 0.8 < d50 < 1.25 else '⚠ differs from surrogate'}")
        print(f"             saturation amplitude p50 {np.median(sat):8.1f}  "
              f"p90 {np.percentile(sat,90):8.1f}")
        res.append(dict(ch=ch, band=bn, n=len(sig), per_min=float(onsets_per_min),
                        sigma_p25=float(np.percentile(sig, 25)),
                        sigma_p50=float(np.percentile(sig, 50)),
                        sigma_p75=float(np.percentile(sig, 75)),
                        surr_p50=float(np.nanpercentile(ssig, 50)),
                        obs_over_surr=float(d50),
                        rise_s=float(np.median(dur)), sat_p50=float(np.median(sat))))
out["D_onsets"] = res

# ======================================================================================
#  D-2.  THE 'STEADY STATE' -- how long does a HIGH-amplitude state persist?
# ======================================================================================
print("\n" + "=" * 104)
print("D-2. PERSISTENCE.  Fraction of engaged time above the 75th-percentile envelope, and the")
print("     duration of contiguous runs above it.  A limit cycle SITS there; noise passes through.")
print("=" * 104)
for ch, x in CH.items():
    for bn in ("B8", "B23", "CTRL"):
        lo, hi = BANDS[bn]
        env_all = L.band_envelope(x, FS, lo, hi, mask=lat)
        ee = env_all[lat]
        ee = ee[np.isfinite(ee)]
        thr = np.percentile(ee, 75)
        obs, sur = [], []
        for a, b in RUNS:
            e = smooth(env_all[a:b], SM)
            m = e > thr
            obs += [(q - p) / FS for p, q in runs(m, 1)] if m.any() else []
        for _ in range(20):
            for a, b in RUNS:
                bp = L.bandpass(x, FS, lo, hi, mask=lat)[a:b]
                sg = surrogate(bp, rng)
                X = np.fft.fft(sg)
                f = np.fft.fftfreq(len(sg), 1 / FS)
                H = np.zeros(len(sg), complex)
                sel = (f >= lo) & (f <= hi)
                H[sel] = 2 * X[sel]
                e = smooth(np.abs(np.fft.ifft(H)), SM)
                m = e > thr
                sur += [(q - p) / FS for p, q in runs(m, 1)] if m.any() else []
        if obs:
            print(f"    {ch:7s} {bn:5s}  above-p75 run length  p50 {np.median(obs):5.2f} s  "
                  f"p90 {np.percentile(obs,90):5.2f} s  max {max(obs):5.2f} s   |   SURROGATE "
                  f"p50 {np.median(sur):5.2f}  p90 {np.percentile(sur,90):5.2f}  "
                  f"max {max(sur):5.2f} s")
            out.setdefault("D2_persistence", []).append(
                dict(ch=ch, band=bn, obs_p50=float(np.median(obs)),
                     obs_p90=float(np.percentile(obs, 90)), obs_max=float(max(obs)),
                     sur_p50=float(np.median(sur)), sur_p90=float(np.percentile(sur, 90)),
                     sur_max=float(max(sur))))

# ======================================================================================
#  F-2.  CAUSALITY -- does openpilot's command ENVELOPE lead or follow the oscillation's?
#  The envelope is slow, so its lag is UNAMBIGUOUS (no 2*pi wrap, unlike a carrier phase).
# ======================================================================================
print("\n" + "=" * 104)
print("F-2. ENVELOPE CROSS-CORRELATION -- does the LKAS command's in-band amplitude LEAD or")
print("     FOLLOW the wheel's?  A carrier phase wraps every 43 ms at 23 Hz and cannot decide;")
print("     the ENVELOPE cannot wrap.  POSITIVE lag = the COMMAND leads (openpilot DRIVES).")
print("     NEGATIVE lag = the command FOLLOWS (openpilot is a PASSENGER echoing the wheel).")
print("=" * 104)
MAXLAG = int(round(0.50 * FS))
for bn in ("B8", "B23", "CTRL"):
    lo, hi = BANDS[bn]
    ec = L.band_envelope(sc_tq, FS, lo, hi, mask=lat)
    for ch, x in (("ang", ang), ("rate_f", rate_f), ("tq", tq)):
        ex = L.band_envelope(x, FS, lo, hi, mask=lat)
        num = np.zeros(2 * MAXLAG + 1)
        den = 0
        for a, b in RUNS:
            u = ec[a:b] - np.nanmean(ec[a:b])
            w = ex[a:b] - np.nanmean(ex[a:b])
            u = np.nan_to_num(u)
            w = np.nan_to_num(w)
            c = np.correlate(u, w, mode="full")
            mid = len(c) // 2
            num += c[mid - MAXLAG:mid + MAXLAG + 1]
            den += np.sqrt(np.sum(u ** 2) * np.sum(w ** 2))
        cc = num / den
        lags = np.arange(-MAXLAG, MAXLAG + 1) / FS
        i = int(np.argmax(cc))
        # sign convention: correlate(u,w) peak at index>MAXLAG means u must be shifted LEFT to
        # align with w, i.e. u (command) LEADS w by lags[i].
        print(f"    {bn:5s} cmd_env vs {ch:7s}_env :  peak r = {cc[i]:+.3f} at lag "
              f"{lags[i]*1000:+7.1f} ms   "
              f"{'⇒ COMMAND LEADS' if lags[i] > 0.005 else '⇒ COMMAND FOLLOWS' if lags[i] < -0.005 else '⇒ SIMULTANEOUS'}"
              f"   (r at 0 lag {cc[MAXLAG]:+.3f})")
        out.setdefault("F2_envelope_lag", []).append(
            dict(band=bn, ch=ch, r=float(cc[i]), lag_ms=float(lags[i] * 1000),
                 r_at_zero=float(cc[MAXLAG])))

# ======================================================================================
#  F-3.  THE TRANSFER GAIN |cmd| / |ang| vs FREQUENCY.
#  If openpilot is an ECHO, |cmd/ang| is its own feedback gain -- roughly flat/monotone
#  across the band.  If openpilot were DRIVING, the firmware's 1-5 Hz LKAS intake low-pass
#  would force |ang/cmd| to COLLAPSE above ~5 Hz -- it manifestly does not.
# ======================================================================================
print("\n" + "=" * 104)
print("F-3. TRANSFER GAIN, engaged.  |Pxy|/Pxx (cmd->ang) and its inverse, per band.")
print("=" * 104)
f, coh, ph, K = L.coherence(sc_tq, ang, lat, FS, nfft=256)
fa, Pa, _ = L.welch(ang, lat, FS, nfft=256)
fc, Pc, _ = L.welch(sc_tq, lat, FS, nfft=256)
print(f"    {'band':22s} {'sqrt(P_ang)':>12s} {'sqrt(P_cmd)':>12s} {'|ang|/|cmd|':>12s} "
      f"{'|cmd|/|ang|':>12s} {'coh²':>7s}")
for bn, (lo, hi) in [("0.5-3 Hz", (0.5, 3.0))] + list(BANDS.items()):
    m = (fa >= lo) & (fa <= hi)
    ra = float(np.sqrt(np.trapezoid(Pa[m], fa[m])))
    rc = float(np.sqrt(np.trapezoid(Pc[m], fc[m])))
    print(f"    {bn:22s} {ra:12.4f} {rc:12.2f} {ra/rc:12.6f} {rc/ra:12.2f} "
          f"{float(coh[(f>=lo)&(f<=hi)].mean()):7.4f}")
    out.setdefault("F3_gain", []).append(dict(band=bn, rms_ang=ra, rms_cmd=rc,
                                              ang_over_cmd=ra / rc, cmd_over_ang=rc / ra))

(L.CACHE / "r95_D_growth.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_D_growth.json'}")
