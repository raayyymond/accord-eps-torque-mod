#!/usr/bin/env python3
r"""THE MICRO-RATCHET REGIME — the operator's one UNFIXED symptom — scored properly.

===================================================================================================
🛑 THE METHOD FIX THIS FILE EXISTS FOR
===================================================================================================
`v92_boost_lane_identify.py` tried to isolate the micro regime with an INSTANTANEOUS mask
(1 <= |rate| < 13 deg/s) and got **0 scoreable windows out of 12,355 qualifying samples**.  That is
not a null -- it is a census artefact: an instantaneous rate band does not form 5.14 s CONTIGUOUS
runs, because the wheel rate crosses in and out of the band many times a second.

⇒ THE CORRECT METHOD, and the one the kit's band estimator already uses elsewhere: **window FIRST
   on the physical mask (engaged, hands-off, moving), then CLASSIFY each whole window by its own
   median |rate|.**  Every window is scoreable, each is assigned to exactly one regime, and the
   regimes partition the drive instead of shredding it.

WHAT IS BEING ASKED.  The operator, on these two drives:
    grind #1                       attenuated (sufficient)
    grind #2                       rare / attenuated (sufficient, but could be better)
    large ratcheting               generally fixed
    micro-ratcheting / stuttering  NOT fixed -- "turning angle rate still limited by this it seems"

🛑 AND THE FIRMWARE UNDER ALL THREE ROUTES IS FUNCTIONALLY THE SAME CAR.  V91/V92's only
   calibration edit was measured INERT this session, so routes 77, 78 and 79 differ in DRIVE, not in
   firmware.  ⇒ nothing here may be reported as a firmware effect.  What it CAN do is characterise
   the regime the operator says is unfixed, on the best exposure the kit has.

Usage:  python v92_micro_regime.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v90_probe as P          # noqa: E402
from v92_boost_lane_and_rez import boost_lane, trust, BANDS  # noqa: E402

RNG = np.random.default_rng(13579)
CACHE = ROOT / "analysis-2020accord"
DEG2RAD = np.pi / 180.0

# window-median |rate| classes.  The operator's own three regimes, plus a near-static class.
REGIMES = [("static  <1 °/s", 0.0, 1.0),
           ("MICRO   1-13 °/s", 1.0, 13.0),
           ("ratchet 13-50 °/s", 13.0, 50.0),
           ("macro   >50 °/s", 50.0, 1e9)]
BANDS50 = [b for b in BANDS if b[2] <= 24.0]


def classify(W, rate_idx=0):
    """Assign each window to a regime by its OWN median |rate| in deg/s."""
    out = {nm: [] for nm, _, _ in REGIMES}
    for w in W:
        m = float(np.median(np.abs(w[rate_idx]))) / DEG2RAD
        for nm, lo, hi in REGIMES:
            if lo <= m < hi:
                out[nm].append(w)
                break
    return out


def transfer(W, fs, nw, bands, xi, yi):
    rows = {}
    pairs = [(w[xi], w[yi]) for w in W]
    if len(pairs) < 6:
        return rows
    for nm, lo, hi in bands:
        r = P._band_transfer(pairs, fs, nw, [(nm, lo, hi)])[nm]
        idx = RNG.permutation(len(pairs))
        rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                               for i in range(len(pairs))], fs, nw, [(nm, lo, hi)])[nm]
        rows[nm] = dict(gain=r["gain"], phase_deg=r["phase_deg"], re=r["re_over_sxx"],
                        coh2=r["coh2"], coh2_shuf=rs["coh2"],
                        trustworthy=trust(r["coh2"], rs["coh2"]), n=len(pairs))
    return rows


def main():
    OUT = {}

    # ==================================================================================
    # A.  Re(Z) BY REGIME, on the 100 Hz 0x18F pair (skew-free), all three routes pooled
    #     and each route separately.  Routes 77/78/79 = same functional car.
    # ==================================================================================
    print("=" * 100)
    print(" A. Re(Z) BY WHEEL-RATE REGIME — windows classified by their OWN median |rate|")
    print("    (routes 77/78/79 are calibration-identical ⇒ this is the CAR, not a build contrast)")
    print("=" * 100)
    allW, fs100 = [], None
    for route, stem, lab in (("77", "r77", "V90"), ("78", "r78", "V91"), ("79", "r79", "V92")):
        z = np.load(CACHE / f"_cache_r{route}" / f"{stem}.npz", allow_pickle=True)
        t = np.asarray(z["t"], float)
        tq = np.asarray(z["tq"], float)
        rate = np.asarray(z["rate_f"], float) * DEG2RAD
        lat = np.asarray(z["cc_lat"], float) > 0.5
        press = np.asarray(z["cs_press"], float) > 0.5
        v = np.abs(np.asarray(z["cs_v"], float))
        fs100 = 1.0 / float(np.median(np.diff(t)))
        W = P._wins(lat & (~press) & (v > 0.5), t, P.NW_Z, P.HOP_Z, (rate, tq, v))
        allW += W
        print(f"    route {route} ({lab}): {len(W)} windows")
    byreg = classify(allW)
    OUT["rez_by_regime"] = {}
    for nm, _, _ in REGIMES:
        W = byreg[nm]
        print(f"\n  --- {nm}:  {len(W)} windows ({len(W)*P.HOP_Z/fs100:.0f} s of unique advance) ---")
        if len(W) < 6:
            print("      🛑 fewer than 6 windows — NOT SCOREABLE")
            OUT["rez_by_regime"][nm] = dict(scoreable=False, n=len(W))
            continue
        rows = transfer(W, fs100, P.NW_Z, BANDS, 0, 1)
        print(f"      {'band':8s} {'Re(Z)':>10s} {'phase':>9s} {'coh²':>7s} {'shuf':>7s} "
              f"{'TRUST':>6s}")
        for b, d in rows.items():
            print(f"      {b:8s} {d['re']:10.1f} {d['phase_deg']:8.1f}° {d['coh2']:7.3f} "
                  f"{d['coh2_shuf']:7.3f} {'YES' if d['trustworthy'] else '🛑 NO':>6s}")
        OUT["rez_by_regime"][nm] = dict(scoreable=True, n=len(W), bands=rows)

    # ==================================================================================
    # B.  THE BOOST LANE BY REGIME — route 79 only (the only route that telemeters it)
    # ==================================================================================
    print("\n" + "=" * 100)
    print(" B. THE BOOST LANE gp-0x6bbe BY REGIME — route 79 (V92)")
    print("=" * 100)
    B = boost_lane(0)
    fs = B["fs"]
    W = P._wins(B["mask"], B["t"], P.NW50, P.HOP50, (B["rate"], B["signed"], B["v"], B["mag"]))
    byreg = classify(W)
    OUT["boost_by_regime"] = {}
    for nm, _, _ in REGIMES:
        Wr = byreg[nm]
        if len(Wr) < 6:
            print(f"\n  --- {nm}: {len(Wr)} windows — 🛑 NOT SCOREABLE")
            OUT["boost_by_regime"][nm] = dict(scoreable=False, n=len(Wr))
            continue
        mags = np.concatenate([w[3] for w in Wr])
        print(f"\n  --- {nm}:  {len(Wr)} windows   |gp-0x6bbe| p50 {np.median(mags):.1f}  "
              f"p90 {np.percentile(mags, 90):.1f} counts ---")
        rows = transfer(Wr, fs, P.NW50, BANDS50, 0, 1)
        print(f"      {'band':8s} {'gain':>9s} {'phase':>9s} {'coh²':>7s} {'shuf':>7s} "
              f"{'TRUST':>6s}")
        for b, d in rows.items():
            print(f"      {b:8s} {d['gain']:9.1f} {d['phase_deg']:8.1f}° {d['coh2']:7.3f} "
                  f"{d['coh2_shuf']:7.3f} {'YES' if d['trustworthy'] else '🛑 NO':>6s}")
        OUT["boost_by_regime"][nm] = dict(scoreable=True, n=len(Wr),
                                          mag_p50=float(np.median(mags)),
                                          mag_p90=float(np.percentile(mags, 90)), bands=rows)

    (CACHE / "_cache_r79" / "micro_regime.json").write_text(json.dumps(OUT, indent=1,
                                                                      default=float))
    print("\n  wrote analysis-2020accord/_cache_r79/micro_regime.json")


if __name__ == "__main__":
    main()
