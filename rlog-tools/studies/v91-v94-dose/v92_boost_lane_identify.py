#!/usr/bin/env python3
r"""WHAT IS `gp-0x6bbe`?  Identify the boost lane from its own telemetry before interpreting it.

===================================================================================================
🛑 WHY THIS STEP EXISTS, AND WHY IT COMES BEFORE ANY "DAMPING" CLAIM
===================================================================================================
`studies/v91-v94-dose/v92_boost_lane_and_rez.py` measured Re(boost/rate) = +87..+89 counts per rad/s, FLAT across
2-12 Hz and stable across the whole skew sweep.  A FLAT real transfer against rate is the signature
of a PURE VISCOUS GAIN (boost = k * rate), not of a phase-shifted lane -- but `re_over_sxx` alone
cannot tell a flat gain from a large quadrature term with a small real part.  The gain and the phase
have to be printed, and they were not.

🛑 AND A SIGN-CONVENTION TRAP GOVERNS THE WHOLE READING.  STATE.md §C: *"Two opposite sign
conventions are in play and confusing them inverts this."*  `Re(Z)` for (rate, tq) has
POSITIVE = damping.  But `gp-0x6bbe` is an INTERNAL firmware cell whose polarity into the
aggregator, and the aggregator's polarity into the motor, and the motor's into the column, are each
separate facts.  ⇒ **NO "damping" or "anti-damping" claim may be made about this lane from a
correlation alone.**  What this file establishes is the lane's IDENTITY (what signal it is a
function of), which is a claim the polarity chain does not gate.

THE FOUR CANDIDATE IDENTITIES, and the signature each predicts against wheel rate:
    viscous / rate-derived     ->  phase ~   0 deg, gain FLAT in frequency
    inertial / accel-derived   ->  phase ~ +90 deg, gain RISING  ~ f
    stiffness / angle-derived  ->  phase ~ -90 deg, gain FALLING ~ 1/f
    torque-sensor-derived      ->  tracks `tq`, not `rate`: high coh vs tq at LOW phase

Usage:  python studies/v91-v94-dose/v92_boost_lane_identify.py
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

import decode_v90_probe as P          # noqa: E402
from v92_boost_lane_and_rez import boost_lane, BANDS50, trust, order_conflict  # noqa: E402

RNG = np.random.default_rng(60119)
CACHE = ROOT / "analysis-2020accord"


def pair_report(title, W, fs, nw, note=""):
    """gain / phase / coh per band for a list of (x, y, v) windows."""
    print(f"\n  --- {title} ---")
    if note:
        print(f"      {note}")
    print(f"    {'band':8s} {'n':>5s} {'gain':>10s} {'phase':>9s} {'Re':>10s} "
          f"{'coh²':>7s} {'shuf':>7s} {'TRUST':>6s}")
    rows = {}
    for nm, lo, hi in BANDS50:
        if len(W) < 6:
            continue
        pairs = [(w[0], w[1]) for w in W]
        r = P._band_transfer(pairs, fs, nw, [(nm, lo, hi)])[nm]
        idx = RNG.permutation(len(pairs))
        rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                               for i in range(len(pairs))], fs, nw, [(nm, lo, hi)])[nm]
        ok = trust(r["coh2"], rs["coh2"])
        rows[nm] = dict(gain=r["gain"], phase_deg=r["phase_deg"], re=r["re_over_sxx"],
                        coh2=r["coh2"], coh2_shuf=rs["coh2"], trustworthy=ok, n=len(pairs))
        print(f"    {nm:8s} {len(pairs):5d} {r['gain']:10.1f} {r['phase_deg']:8.1f}° "
              f"{r['re_over_sxx']:10.1f} {r['coh2']:7.3f} {rs['coh2']:7.3f} "
              f"{'YES' if ok else '🛑 NO':>6s}")
    return rows


def main():
    OUT = {}
    B = boost_lane(0)
    fs, nw, hop = B["fs"], P.NW50, P.HOP50
    print("=" * 100)
    print(" IDENTIFYING gp-0x6bbe — route 79 (V92), the first build ever to telemeter it")
    print("=" * 100)
    print(f"  50 Hz 427 grid, fs {fs:.2f} Hz, window {nw} samples = {nw/fs:.2f} s")

    # ---------- 1. against WHEEL RATE (the viscous / inertial / stiffness discriminator)
    W = P._wins(B["mask"], B["t"], nw, hop, (B["rate"], B["signed"], B["v"]))
    OUT["vs_rate"] = pair_report(
        "boost vs WHEEL RATE (x = rate_f, y = signed gp-0x6bbe)", W, fs, nw,
        "viscous ⇒ phase ~0°, gain flat · inertial ⇒ +90°, gain ∝ f · stiffness ⇒ −90°, gain ∝ 1/f")

    # ---------- 2. against COLUMN TORQUE
    W2 = P._wins(B["mask"], B["t"], nw, hop, (B["tq"], B["signed"], B["v"]))
    OUT["vs_tq"] = pair_report(
        "boost vs COLUMN TORQUE (x = tq from 0x18F, y = signed gp-0x6bbe)", W2, fs, nw,
        "STATE.md flagged gp-0x6bbe as 'same-signed as the raw torque sensor ⇒ REINFORCING'")

    # ---------- 3. the lane's OWN spectrum — is there a 6-9 Hz line?
    print("\n  --- THE BOOST LANE'S OWN SPECTRUM (magnitude channel, no skew) ---")
    Wm = P._wins(B["mask"], B["t"], nw, hop, (B["mag"], B["signed"], B["v"]))
    spec = {}
    accs = None
    for w in Wm:
        x = w[1] - np.mean(w[1])
        X = np.fft.rfft(x * np.hanning(len(x)))
        S = np.abs(X) ** 2
        accs = S if accs is None else accs + S
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    accs = accs / max(1, len(Wm))
    tot = accs[(f >= 1.0) & (f <= 24.0)].sum()
    print(f"    {len(Wm)} windows.  Band share of 1-24 Hz power in the SIGNED lane:")
    for nm, lo, hi in BANDS50:
        m = (f >= lo) & (f <= hi)
        sh = float(accs[m].sum() / tot)
        dens = sh / (hi - lo)
        spec[nm] = dict(share=sh, density_per_hz=dens)
        bar = "█" * int(round(dens * 200))
        print(f"      {nm:8s} share {100*sh:5.2f} %   density {dens:.4f} /Hz  {bar}")
    OUT["own_spectrum"] = spec

    # ---------- 4. the MICRO-RATCHET regime specifically (the operator's live complaint)
    print("\n  --- THE MICRO-RATCHET REGIME (engaged, 1-13 °/s — the operator's unfixed symptom) ---")
    rate_dps = np.abs(B["rate"]) * 180.0 / np.pi
    micro = B["mask"] & (rate_dps >= 1.0) & (rate_dps < 13.0)
    print(f"      {micro.sum():,} of {B['mask'].sum():,} masked 427 samples "
          f"({100*micro.mean():.1f} % of all)")
    Wmi = P._wins(micro, B["t"], nw, hop, (B["rate"], B["signed"], B["v"]))
    if len(Wmi) >= 6:
        OUT["vs_rate_micro"] = pair_report(
            f"boost vs WHEEL RATE, MICRO-RATCHET regime only ({len(Wmi)} windows)",
            Wmi, fs, nw)
    else:
        print(f"      🛑 only {len(Wmi)} contiguous windows survive the 1-13 °/s mask — "
              f"NOT SCOREABLE.  The regime is defined by an instantaneous rate, so it does not\n"
              f"      form {nw/fs:.1f} s contiguous runs.  This is a CENSUS limit, not a null.")
        OUT["vs_rate_micro"] = dict(scoreable=False, n_windows=len(Wmi))

    # ---------- 5. magnitude vs |rate| — the sizing question, regression-free
    print("\n  --- SIZING: |gp-0x6bbe| by wheel-rate bin, ENGAGED (is it rate-proportional?) ---")
    sz = {}
    print(f"    {'|rate| °/s':<14} {'n':>8} {'p50':>8} {'p90':>8}  {'p50 / rate':>11}")
    for lo, hi in ((0.0, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0), (13.0, 25.0), (25.0, 50.0),
                   (50.0, 1e9)):
        s = B["mask"] & (rate_dps >= lo) & (rate_dps < hi)
        if s.sum() < 50:
            continue
        mid = (lo + min(hi, 100.0)) / 2
        p50 = float(np.median(B["mag"][s]))
        sz[f"{lo}-{hi if hi < 1e8 else '+'}"] = dict(
            n=int(s.sum()), p50=p50, p90=float(np.percentile(B["mag"][s], 90)))
        print(f"    {lo:>5.0f}-{hi if hi < 1e8 else 999:<7.0f} {int(s.sum()):>8,} {p50:>8.1f} "
              f"{np.percentile(B['mag'][s], 90):>8.1f}  {p50/mid:>11.2f}")
    OUT["sizing_by_rate"] = sz
    print("    ⇒ a FLAT p50/rate column means rate-proportional (viscous); a p50 that saturates")
    print("      means a relay/clamp; a p50 that is large at ~0 °/s means a DC term.")

    (CACHE / "_scratch/cache/r79" / "boost_identify.json").write_text(json.dumps(OUT, indent=1,
                                                                        default=float))
    print("\n  wrote analysis-2020accord/_scratch/cache/r79/boost_identify.json")


if __name__ == "__main__":
    main()
