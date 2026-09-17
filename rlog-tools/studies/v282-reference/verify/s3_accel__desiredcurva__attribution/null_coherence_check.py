"""Adversarial check: is the observed 2-3 Hz coherence between desired-rate and steer-rate (s3_refloop.py)
distinguishable from the coherence you'd get between two INDEPENDENT (unrelated) signals, given the same
segment count (nperseg=512, Welch, at the route's own usable duration)?

If the null (no true coupling) already produces coherence in the observed range, the "phase" (and hence the
"wheel leads desired" / "reference in the loop" reading) cannot be trusted -- phase of a near-zero-coherence
cross-spectral estimate is close to uniformly random.
"""
import numpy as np
from scipy import signal

FS = 100.0
NPERSEG = 512

# route: total usable seconds pooled by s3_refloop.py (from s3_refloop.json 'sec'), and observed 2-3Hz coherence
OBS = {
    "00000064--ce6b0b0ebb (V282)": (26.48, 0.0884),
    "00000065--b9f78988bd (V282)": (48.85, 0.0900),
    "0000006c--2bc842dbac (V282)": (207.85, 0.0856),
    "0000006c--68c6e94b17 (T64)":  (26.21, 0.3156),
    "0000006d--05e83bb04f (T64)":  (29.29, 0.5886),
    "0000006e--6ca3e014fd (T64B)": (54.54, 0.2784),
    "00000075--6c8687d5bd (T4)":   (133.67, 0.0125),
    "00000076--d0b7ea7e4d (T5)":   (36.50, 0.0505),
}

rng = np.random.default_rng(0)


def null_coherence(sec, ntrials=400):
    """Monte Carlo: two independent white-noise-derived signals (roughly matched spectral shape: low-pass
    like desired-rate/steer-rate are), same total length, same Welch settings as s3_refloop.py. Returns the
    2-3 Hz band coherence distribution under H0 (no true relationship)."""
    n = int(sec * FS)
    if n < NPERSEG:
        return None
    vals = []
    ph = []
    for _ in range(ntrials):
        x = rng.standard_normal(n)
        y = rng.standard_normal(n)
        f, p = signal.welch(x, FS, nperseg=NPERSEG)
        _, q = signal.welch(y, FS, nperseg=NPERSEG)
        _, c = signal.csd(x, y, FS, nperseg=NPERSEG)
        m = (f >= 2.0) & (f < 3.0)
        coh = float(np.abs(c[m].sum()) ** 2 / (p[m].sum() * q[m].sum()))
        vals.append(coh)
        ph.append(float(np.degrees(np.angle(c[m].sum()))))
    return np.array(vals), np.array(ph)


print(f"{'route':32s} {'sec':>7s} {'obs_coh':>8s} {'null_mean':>10s} {'null_p50':>9s} {'null_p95':>9s} {'obs<=null_p95?':>15s} {'null_phase_sd':>14s}")
for rk, (sec, obs_coh) in OBS.items():
    out = null_coherence(sec)
    if out is None:
        print(f"{rk:32s} too short")
        continue
    vals, ph = out
    p50, p95 = np.percentile(vals, [50, 95])
    flag = "YES (indistinguishable)" if obs_coh <= p95 else "no (exceeds null)"
    print(f"{rk:32s} {sec:7.1f} {obs_coh:8.4f} {vals.mean():10.4f} {p50:9.4f} {p95:9.4f} {flag:>15s} {ph.std():14.1f}")
