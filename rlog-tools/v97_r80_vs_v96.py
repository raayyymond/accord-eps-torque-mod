#!/usr/bin/env python3
r"""Route 80 (V97) vs routes 7e/7f (V96): matched-regime availability, probe liveness cross-check,
and the cross-build band + phase comparison.

🛑 raw14 off-by-one: uses `row2raw14` (asserted elementwise at extraction time).  Never pairs `t`
with `raw14_b4`.
🛑 SIGN CONVENTION, stated once and sanity-checked in `_phase_selfcheck`:
       scipy.signal.csd(x, y)  ->  Pxy  ->  angle(Pxy) = arg(Y) - arg(X)
   so `phase(x, y) > 0` means **y LEADS x**.  The self-check delays a signal by a known lag and
   asserts the measured phase has the sign that lag implies.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
AN = ROOT / "analysis-2020accord"
KMH = 3.6
ROUTES = {"80": ("_cache_r80", "r80", "V97"),
          "7e": ("_cache_r7e", "r7e", "V96"),
          "7f": ("_cache_r7f", "r7f", "V96")}


def load(r):
    cdir, stem, build = ROUTES[r]
    z = np.load(AN / cdir / f"{stem}.npz", allow_pickle=True)
    d = {}
    t = np.asarray(z["t"], float)
    idx = np.asarray(z["row2raw14"], int)
    b4 = (np.asarray(z["raw14_b4"], int) & 0xFF)[idx]
    b7 = (np.asarray(z["raw14_b7"], int) & 0xFF)[idx]
    assert np.all(b4 == (np.asarray(z["probe"], int) & 0xFF))
    d.update(t=t, b4=b4, b7=b7, build=build, route=r,
             sign_6b70=(b4 >> 7) & 1, sign_374c=(b4 >> 6) & 1,
             Mhi=(b4 >> 4) & 3, Mlo=(b7 >> 7) & 1, mode=(b4 >> 3) & 1, ident=(b7 >> 6) & 1,
             eng=np.asarray(z["cc_lat"], float) > 0.5,
             v=np.asarray(z["cs_v"], float) * KMH,
             rate=np.asarray(z["cs_rate"], float),
             ang=np.asarray(z["cs_ang"], float),
             tq=np.asarray(z["tq"], float),
             press=np.asarray(z["cs_press"], float) > 0.5,
             sstat=np.asarray(z["sstat"], float),
             ab_t=np.asarray(z["ab_t1ab"], float),
             ab_mt=np.asarray(z["ab_mt"], int))
    d["M"] = 2 * d["Mhi"] + d["Mlo"]
    j = np.clip(np.searchsorted(t, d["ab_t"]), 0, len(t) - 1)
    d["ab_j"] = j
    d["ab_counts"] = d["ab_mt"] * (64.0 / 5.0)
    d["ab_signed"] = d["ab_counts"] * np.where(d["sign_6b70"][j] == 1, -1.0, 1.0)
    d["ab_eng"] = d["eng"][j]
    d["ab_v"] = d["v"][j]
    d["ab_rate"] = d["rate"][j]
    return d


def _phase_selfcheck():
    """Delay y by +5 samples relative to x.  y LAGS x, so arg(Y)-arg(X) must be NEGATIVE."""
    fs, f0, lag = 100.0, 7.79, 5
    n = 20000
    tt = np.arange(n) / fs
    rng = np.random.default_rng(0)
    x = np.sin(2 * np.pi * f0 * tt) + 0.1 * rng.standard_normal(n)
    y = np.roll(x, lag)
    f, P = signal.csd(x, y, fs=fs, nperseg=1024)
    k = int(np.argmin(np.abs(f - f0)))
    ph = np.degrees(np.angle(P[k]))
    expect = -360.0 * f0 * lag / fs
    ok = abs(ph - expect) < 5.0
    print(f"  SIGN SELF-CHECK: y = x delayed {lag} samples at {fs:.0f} Hz; measured "
          f"arg(Y)-arg(X) = {ph:+.2f} deg, expected {expect:+.2f} deg -> {'OK' if ok else 'FAIL'}")
    assert ok, "csd sign convention self-check FAILED"
    return dict(measured_deg=float(ph), expected_deg=float(expect), ok=bool(ok))


def band_rms(x, fs, lo, hi, nperseg):
    x = np.asarray(x, float)
    x = x - x.mean()
    if len(x) < nperseg:
        return float("nan")
    f, P = signal.welch(x, fs=fs, nperseg=nperseg)
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.trapezoid(P[m], f[m])))


def episodes(sel, t, min_s=1.0):
    """Contiguous True runs of `sel` lasting >= min_s.  Returns list of (i0, i1)."""
    sel = np.asarray(sel, bool)
    d = np.diff(sel.astype(int))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0] + 1)
    if sel[0]:
        starts = [0] + starts
    if sel[-1]:
        ends = ends + [len(sel)]
    return [(a, b) for a, b in zip(starts, ends) if t[b - 1] - t[a] >= min_s]


def main():
    out = {"sign_convention": "angle(csd(x,y)) = arg(Y) - arg(X); positive => y LEADS x"}
    print("=== SIGN CONVENTION ===")
    out["selfcheck"] = _phase_selfcheck()

    D = {r: load(r) for r in ROUTES}

    print("\n=== PROBE MAGNITUDE CHANNEL, ALL THREE V96-FAMILY ROUTES ===")
    print("  (M = |gp-0x374c>>4| >> 11, saturating at 3; LSB 2048 counts)")
    out["probe_M"] = {}
    for r, d in D.items():
        n = len(d["t"])
        hist = {int(a): int(b) for a, b in zip(*np.unique(d["M"], return_counts=True))}
        eh = {int(a): int(b) for a, b in zip(*np.unique(d["M"][d["eng"]], return_counts=True))}
        print(f"  r{r} ({d['build']}): n={n:,}  M hist {hist}")
        print(f"          engaged only (n={d['eng'].sum():,}): {eh}")
        print(f"          sign(374c) duty ALL {d['sign_374c'].mean():.4f}  "
              f"ENG {d['sign_374c'][d['eng']].mean():.4f}   "
              f"sign(6b70) duty ALL {d['sign_6b70'].mean():.4f}  "
              f"ENG {d['sign_6b70'][d['eng']].mean():.4f}")
        out["probe_M"][r] = dict(build=d["build"], n=n, M_hist=hist, M_hist_engaged=eh,
                                 sign374c_duty=float(d["sign_374c"].mean()),
                                 sign374c_duty_eng=float(d["sign_374c"][d["eng"]].mean()),
                                 sign6b70_duty=float(d["sign_6b70"].mean()),
                                 identity_duty=float(d["ident"].mean()),
                                 mode_rung_duty=float(d["mode"].mean()))

    # ---------------- MATCHED REGIME ----------------
    # Route 80's engaged envelope: speed 2.4 - 6.4 km/h (p05/p95), |rate| up to ~190 deg/s.
    VLO, VHI = 0.0, 7.0
    print(f"\n=== MATCHED REGIME: speed in [{VLO}, {VHI}) km/h ===")
    out["matched"] = {}
    for r, d in D.items():
        band = (d["v"] >= VLO) & (d["v"] < VHI)
        for nm, sel in (("ENG", band & d["eng"]), ("MAN", band & ~d["eng"])):
            eps = episodes(sel, d["t"], 1.0)
            dur = sel.sum() * 0.01
            out["matched"][f"{r}_{nm}"] = dict(frames=int(sel.sum()), seconds=float(dur),
                                               episodes=len(eps))
            print(f"  r{r} ({d['build']:3s}) {nm}: {sel.sum():6,} frames = {dur:7.1f} s   "
                  f"episodes>=1s: {len(eps):3d}")

    # ---------------- BANDS, matched regime, per EPISODE ----------------
    print("\n=== BANDS (0x18F STEER_TORQUE_SENSOR, 100 Hz), matched creep regime, per EPISODE ===")
    BANDS = {"6-9": (6.0, 9.0), "15-22": (15.0, 22.0), "18-28": (18.0, 28.0),
             "26-31": (26.0, 31.0), "0.5-3": (0.5, 3.0)}
    out["bands"] = {}
    for r, d in D.items():
        band = (d["v"] >= VLO) & (d["v"] < VHI)
        for nm, sel in (("ENG", band & d["eng"]), ("MAN", band & ~d["eng"])):
            eps = episodes(sel, d["t"], 2.56)
            vals = {k: [] for k in BANDS}
            for a, b in eps:
                seg = d["tq"][a:b]
                if len(seg) < 256:
                    continue
                for k, (lo, hi) in BANDS.items():
                    vals[k].append(band_rms(seg, 100.0, lo, hi, min(256, len(seg))))
            key = f"{r}_{nm}"
            out["bands"][key] = {k: dict(n=len(v),
                                         median=float(np.median(v)) if v else float("nan"))
                                 for k, v in vals.items()}
            if eps:
                s = "  ".join(f"{k} {np.median(v):7.2f}" for k, v in vals.items() if v)
                print(f"  r{r} ({d['build']:3s}) {nm} [{len(eps):3d} eps]: {s}")

    (AN / "_cache_r80" / "r80_vs_v96.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {AN/'_cache_r80'/'r80_vs_v96.json'}")


if __name__ == "__main__":
    main()
