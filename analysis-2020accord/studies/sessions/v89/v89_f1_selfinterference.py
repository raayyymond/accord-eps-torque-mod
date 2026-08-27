#!/usr/bin/env python3
r"""THE DISCRIMINATOR the orchestrator asked for: is `r(0x0E4, column torque) = +0.55..+0.79`
SELF-INTERFERENCE, or is the car SIMPLY TURNING?

The two live explanations for the in-phase command<->column relation `v89_e4`/`v89_e5` measured:
  (a) SELF-INTERFERENCE -- the overlay's own reaction lands on the torque sensor co-directionally,
      so the assist law reads its own output as apparent driver torque.
  (b) THE CAR IS TURNING -- at 0.2-3 Hz the command steers the vehicle, the tyres make self-aligning
      torque, and that loads the column.  Normal, intended road feel from a commanded manoeuvre.
Both predict a large positive r with high coherence and a small phase lag.  Neither the manual arm
nor the time-shift control separates them: both only show the relation is not spurious.

FOUR TESTS:
  T1  PARTIAL OUT WHAT THE CAR IS ACTUALLY DOING -- steering angle, wheel rate, lateral acceleration
      and yaw rate, all band-passed, residualised WITHIN each window.  If the relation survives, (b)
      is excluded.  🛑 Read the caveat in the output: partialling on the angle also removes part of
      (a), because self-interference is partly MEDIATED by column motion.  ⇒ a surviving partial r
      is strong evidence FOR (a); a collapsing one is NOT clean evidence for (b).
  T2  STRATIFY STRAIGHT vs CORNERING on |imu_lat|.  (a) predicts the relation persists on the
      straight, where lane-centring still commands torque but the tyres make almost no SAT;
      (b) predicts it collapses there.
  T3  🛑 THE HANDS-OFF STRUCTURAL ARGUMENT, which the orchestrator's option (b) may not survive.
      With the driver's hands OFF the rim, the upper column is a FREE INERTIA.  The torsion bar can
      then only transmit what moves the upper column -- tyre self-aligning torque is reacted by the
      motor and the rack, NOT by a free column.  So (b) needs a reaction point the hands-off arm
      does not have.  This test reports the hands-off / hands-on split of the PARTIAL r.
  T4  THE FREQUENCY ARGUMENT, MADE EXPLICIT.  How much 0x0E4 energy actually exists at 6-9 Hz, and
      is the 6-9 Hz correlation leakage from the 100x larger 0.2-3 Hz band?  A 2nd-order Butterworth
      is NOT clean enough to answer that, so this uses SPECTRAL coherence on Hann-windowed FFT bins,
      where a 1 Hz component is ~17 bins away and its sidelobe contribution is negligible, plus an
      explicit HIGH-PASS-FIRST variant of the correlation.
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
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))

import _r31_common as C31        # noqa: E402
import _r4f_lib as R4F           # noqa: E402
from v89_e4_inertia import ARMS, NFFT, HOP, fs_of, boot_med   # noqa: E402

R4F.install_fs()
RNG = np.random.default_rng(89_7070)
OUTJ = ROOT / "_scratch/cache/r75" / "v89_f1_selfinterference.json"
BANDS = [(0.2, 1.0), (1.0, 3.0), (0.2, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 12.0)]
COV = ["ang", "rate_f", "imu_lat", "cs_yaw"]     # "what the car is actually doing"
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + f"\n{s}\n" + "=" * 112, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def bp(x, fs, lo, hi, order=4):
    return filtfilt(*butter(order, [lo, hi], btype="band", fs=fs), np.asarray(x, float))


def resid(y, X):
    """y with the column space of X (plus an intercept) projected out."""
    A = np.column_stack([np.ones(len(y))] + list(X))
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ b


def pearson(a, b):
    sa, sb = np.std(a), np.std(b)
    if sa <= 0 or sb <= 0:
        return np.nan
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb))


def windows(name, shift_s=0.0, hp_first=False):
    cache, pfx, segs = ARMS[name]
    rows = []
    for s in segs:
        if not (cache / f"{pfx}{s}.npz").exists():
            continue
        d = C31.load(s, cache, pfx)
        fs = fs_of(d)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        raw = {"cmd": np.asarray(d["e4tq"], float), "tq": np.asarray(d["tq"], float)}
        for k in COV:
            raw[k] = np.asarray(d[k], float)
        pr = np.asarray(d.get("cs_press", np.zeros_like(lat, float)), float)
        for a, b in C31.runs_of(lat, d["t"], NFFT):
            seg = {k: v[a:b].copy() for k, v in raw.items()}
            if shift_s:
                k_ = int(round(shift_s * fs)) % max(len(seg["cmd"]), 1)
                seg["cmd"] = np.roll(seg["cmd"], k_)
            if hp_first:      # kill everything under 5 Hz BEFORE the band-pass
                hb = butter(4, 5.0, btype="high", fs=fs)
                for k in seg:
                    seg[k] = filtfilt(*hb, seg[k])
            if not all(np.all(np.isfinite(v)) for v in seg.values()):
                continue
            F = {(lo, hi): {k: bp(v, fs, lo, hi) for k, v in seg.items()} for lo, hi in BANDS}
            nwin = 0
            for i in range(0, (b - a) - NFFT + 1, HOP):
                sl = slice(i, i + NFFT)
                gl = slice(a + i, a + i + NFFT)
                r = dict(build=name, blk=(name, s, a, nwin // 8),
                         press=float(np.mean(pr[gl] > 0.5)),
                         v=float(np.mean(np.abs(d["cs_v"][gl]))),
                         latacc=float(np.mean(np.abs(d["imu_lat"][gl]))),
                         angmag=float(np.mean(np.abs(d["ang"][gl]))),
                         cmdmag=float(np.mean(np.abs(raw["cmd"][gl]))))
                han = np.hanning(NFFT)
                CM = np.fft.rfft((seg["cmd"][sl] - seg["cmd"][sl].mean()) * han)
                TQ = np.fft.rfft((seg["tq"][sl] - seg["tq"][sl].mean()) * han)
                f = np.fft.rfftfreq(NFFT, 1 / fs)
                for lo, hi in BANDS:
                    k = f"{lo}-{hi}"
                    x, z = F[(lo, hi)]["cmd"][sl], F[(lo, hi)]["tq"][sl]
                    r["raw_" + k] = pearson(x, z)
                    C = [F[(lo, hi)][c][sl] for c in COV]
                    r["par_" + k] = pearson(resid(x, C), resid(z, C))
                    m = (f >= lo) & (f <= hi)
                    pc, pt = np.sum(np.abs(CM[m]) ** 2), np.sum(np.abs(TQ[m]) ** 2)
                    S = np.sum(TQ[m] * np.conj(CM[m]))
                    r["coh_" + k] = float(np.abs(S) ** 2 / (pc * pt)) if pc > 0 and pt > 0 else np.nan
                    r["cmdrms_" + k] = float(np.sqrt(pc)) / (NFFT / 2)
                nwin += 1
                rows.append(r)
    return rows


def table(rows, keys, label):
    print(f"    {label}  (n={len(rows)})")
    print(f"      {'band':>10s} | " + " ".join(f"{k:>26s}" for k in keys))
    out = {}
    for lo, hi in BANDS:
        cells = []
        for k in keys:
            m, l, h, n = boot_med(rows, f"{k}_{lo}-{hi}")
            cells.append(f"{m:7.3f} [{l:6.3f},{h:6.3f}]")
            out[f"{k}/{lo}-{hi}"] = [m, l, h, n]
        print(f"      {f'{lo}-{hi}':>10s} | " + " ".join(f"{c:>26s}" for c in cells))
    return out


# =================================================================================================
if __name__ == "__main__":
    hdr("SETUP -- engaged windows, HANDS-OFF is the decisive arm (see T3)")
    E = {n: windows(n) for n in ARMS}
    S = {n: windows(n, shift_s=5.0) for n in ARMS}
    OFF = {n: [r for r in E[n] if r["press"] <= 0.02] for n in ARMS}
    OFFS = {n: [r for r in S[n] if r["press"] <= 0.02] for n in ARMS}
    ON = {n: [r for r in E[n] if r["press"] >= 0.5] for n in ARMS}
    for n in ARMS:
        print(f"    {n:10s} engaged {len(E[n])}   hands-off {len(OFF[n])}   hands-on {len(ON[n])}")

    hdr("T4  THE FREQUENCY ARGUMENT FIRST -- how much 0x0E4 energy is there at 6-9 Hz at all?")
    for n in ARMS:
        r0 = np.median([r["cmdrms_0.2-3.0"] for r in OFF[n]])
        print(f"    {n:10s} 0x0E4 band rms (ct):  " +
              "  ".join(f"{lo}-{hi} {np.median([r[f'cmdrms_{lo}-{hi}'] for r in OFF[n]]):7.2f}"
                        f" ({100*np.median([r[f'cmdrms_{lo}-{hi}'] for r in OFF[n]])/r0:5.2f}%)"
                        for lo, hi in BANDS if (lo, hi) != (0.2, 3.0)))
    print("\n    ⇒ the 6-9 Hz command content is a small but NON-ZERO fraction of the 0.2-3 Hz band.")
    print("      A 2nd-order Butterworth cannot cleanly separate them, so the 6-9 Hz claim below is")
    print("      carried by SPECTRAL COHERENCE (Hann bins, a 1 Hz line is ~17 bins away) and by the")
    print("      HIGH-PASS-FIRST variant, not by the band-pass correlation.")

    hdr("T1 + T3  PARTIAL OUT WHAT THE CAR IS DOING (steering angle, wheel rate, lateral accel,\n"
        "         yaw rate), HANDS-OFF -- and the same on the 5 s time-shifted control")
    OUT["t1"] = {}
    for n in ARMS:
        sub(f"{n}  HANDS-OFF")
        OUT["t1"][n] = table(OFF[n], ["raw", "par", "coh"], "engaged, hands-off")
        OUT["t1"][n + "/shift"] = table(OFFS[n], ["raw", "par", "coh"],
                                        "5 s TIME-SHIFTED CONTROL")

    hdr("T3  HANDS-ON, where a reaction point for tyre self-aligning torque DOES exist")
    OUT["t3"] = {}
    for n in ARMS:
        if len(ON[n]) < 20:
            print(f"    {n}: {len(ON[n])} hands-on windows -- too few")
            continue
        sub(f"{n}  hands-on")
        OUT["t3"][n] = table(ON[n], ["raw", "par"], "engaged, hands-on")

    hdr("T2  STRAIGHT vs CORNERING, hands-off.  (b) needs the tyres to be working; (a) does not.")
    OUT["t2"] = {}
    allof = [r for n in ARMS for r in OFF[n]]
    la = np.array([r["latacc"] for r in allof])
    q1, q3 = np.percentile(la, [25, 75])
    print(f"    |imu_lat| quartiles over {len(allof)} hands-off windows: "
          f"p25 {q1:.3f}  p50 {np.median(la):.3f}  p75 {q3:.3f}")
    for tag, sel in (("STRAIGHT  (|imu_lat| < p25)", [r for r in allof if r["latacc"] < q1]),
                     ("CORNERING (|imu_lat| > p75)", [r for r in allof if r["latacc"] > q3])):
        sub(tag)
        OUT["t2"][tag] = table(sel, ["raw", "par", "coh"], tag)

    hdr("T4b  HIGH-PASS-FIRST (everything under 5 Hz removed BEFORE band-passing) -- the leakage\n"
        "     control for the 6-9 and 9-12 Hz rows")
    OUT["t4b"] = {}
    for n in ARMS:
        H = [r for r in windows(n, hp_first=True) if r["press"] <= 0.02]
        HS = [r for r in windows(n, shift_s=5.0, hp_first=True) if r["press"] <= 0.02]
        sub(f"{n}  hands-off, HP>5 Hz first")
        OUT["t4b"][n] = {}
        for lo, hi in ((6.0, 9.0), (9.0, 12.0)):
            a = boot_med(H, f"raw_{lo}-{hi}")
            p = boot_med(H, f"par_{lo}-{hi}")
            c = boot_med(HS, f"raw_{lo}-{hi}")
            print(f"      {lo}-{hi} Hz   raw r {a[0]:7.3f} [{a[1]:6.3f},{a[2]:6.3f}]   "
                  f"PARTIAL r {p[0]:7.3f} [{p[1]:6.3f},{p[2]:6.3f}]   "
                  f"shifted control {c[0]:7.3f} [{c[1]:6.3f},{c[2]:6.3f}]")
            OUT["t4b"][n][f"{lo}-{hi}"] = dict(raw=list(a[:3]), partial=list(p[:3]),
                                               shifted=list(c[:3]))

    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
