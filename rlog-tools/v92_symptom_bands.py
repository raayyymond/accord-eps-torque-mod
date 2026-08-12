#!/usr/bin/env python3
r"""THE SYMPTOM BANDS across routes 77 / 78 / 79 — column-torque energy, matched exposure.

🛑🛑 READ THIS BEFORE READING ANY NUMBER BELOW.
    The operator scores SYMPTOMS.  This file scores BANDS.  They are not the same thing, and a band
    moving is NOT a symptom being fixed.  "grind #1", "grind #2" and "the ratchet" are KIT JARGON
    for frequency bands; his words are grinding, vibrating, micro-ratcheting, ratcheting.

🛑 AND THE THREE ROUTES ARE THE SAME FUNCTIONAL CAR.  V91/V92's only calibration edit was measured
   INERT this session at its own single documented output (`v91_v92_dose_threeway.py`).  So every
   cross-route number here is DRIVE VARIATION, and it is reported as the kit's best available
   estimate of the same-firmware measurement floor — NOT as a firmware effect.

   ⊕ That makes this table genuinely useful in one specific way: it is a THREE-ROUTE, SAME-FIRMWARE
     PLACEBO SET, the largest the kit has ever had.  Whatever spread appears here is the noise any
     future build's claimed effect has to beat.

METHOD.  Windows are taken on the physical mask (engaged, hands-off, moving) and then classified by
their OWN median |wheel rate|, so every window is scoreable and the regimes partition the drive.
Band energy is the column torque `tq` (0x18F bytes 0-1) power density, normalised within each window
by that window's own 1-35 Hz total — a WITHIN-WINDOW normalisation, so a window that simply saw more
road does not inflate a band.

Usage:  python v92_symptom_bands.py
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

RNG = np.random.default_rng(24680)
CACHE = ROOT / "analysis-2020accord"
DEG2RAD = np.pi / 180.0
NBOOT = 3000

SYMPTOM_BANDS = [("micro-ratchet 6-9", 6.0, 9.0),
                 ("9-12", 9.0, 12.0),
                 ("grind #1  18-22", 18.0, 22.0),
                 ("grind #2  26-31", 26.0, 31.0),
                 ("control   32-38", 32.0, 38.0)]
REGIMES = [("static  <1 °/s", 0.0, 1.0), ("MICRO   1-13 °/s", 1.0, 13.0)]


def route_windows(route, stem):
    z = np.load(CACHE / f"_cache_r{route}" / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    tq = np.asarray(z["tq"], float)
    rate = np.asarray(z["rate_f"], float) * DEG2RAD
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    fs = 1.0 / float(np.median(np.diff(t)))
    W = P._wins(lat & (~press) & (v > 0.5), t, P.NW_Z, P.HOP_Z, (rate, tq, v))
    return W, fs


def band_shares(W, fs, nw):
    """Per-window within-window-normalised band shares of the column torque."""
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    tot_m = (f >= 1.0) & (f <= 38.0)
    out = {nm: [] for nm, _, _ in SYMPTOM_BANDS}
    meta = []
    for w in W:
        y = w[1] - np.mean(w[1])
        S = np.abs(np.fft.rfft(y * np.hanning(nw))) ** 2
        tot = S[tot_m].sum()
        if tot <= 0:
            continue
        for nm, lo, hi in SYMPTOM_BANDS:
            m = (f >= lo) & (f <= hi)
            out[nm].append(float(S[m].sum() / tot / (hi - lo)))
        meta.append((float(np.median(np.abs(w[0]))) / DEG2RAD, float(np.mean(np.abs(w[2])))))
    return {k: np.array(v, float) for k, v in out.items()}, np.array(meta, float)


def boot_median(x, nboot=NBOOT):
    if len(x) < 6:
        return float("nan"), float("nan")
    b = [np.median(RNG.choice(x, len(x), replace=True)) for _ in range(nboot)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def main():
    ROUTES = (("77", "r77", "V90"), ("78", "r78", "V91"), ("79", "r79", "V92"))
    data = {}
    for route, stem, lab in ROUTES:
        W, fs = route_windows(route, stem)
        sh, meta = band_shares(W, fs, P.NW_Z)
        data[route] = dict(shares=sh, meta=meta, label=lab, n=len(meta))

    OUT = {"note": ("routes 77/78/79 are CALIBRATION-IDENTICAL — the ×1.5 dose was measured inert. "
                    "This is a three-route SAME-FIRMWARE placebo set, i.e. the measurement floor.")}

    for rgnm, rlo, rhi in REGIMES:
        print("\n" + "=" * 100)
        print(f" COLUMN-TORQUE BAND DENSITY — {rgnm} windows  (same firmware on all three routes)")
        print("=" * 100)
        print(f"    {'band':<20} " + "".join(f"{lab + ' r' + r:>26}" for r, _s, lab in ROUTES) +
              f"{'spread':>10}")
        rows = {}
        for bnm, _lo, _hi in SYMPTOM_BANDS:
            cells, meds = [], []
            for route, _stem, _lab in ROUTES:
                d = data[route]
                sel = (d["meta"][:, 0] >= rlo) & (d["meta"][:, 0] < rhi) if len(d["meta"]) else \
                    np.zeros(0, bool)
                x = d["shares"][bnm][sel]
                if len(x) < 6:
                    cells.append("        n<6, n/s        ")
                    meds.append(np.nan)
                    continue
                m = float(np.median(x))
                lo_, hi_ = boot_median(x)
                meds.append(m)
                cells.append(f"{m:.4f} [{lo_:.4f},{hi_:.4f}]".rjust(26))
            meds = np.array(meds, float)
            spread = (np.nanmax(meds) / np.nanmin(meds)) if np.isfinite(meds).all() else np.nan
            rows[bnm] = dict(medians=meds.tolist(), spread=float(spread))
            print(f"    {bnm:<20} " + "".join(cells) + f"{spread:>10.3f}×")
        ns = [int(((data[r]['meta'][:, 0] >= rlo) & (data[r]['meta'][:, 0] < rhi)).sum())
              for r, _s, _l in ROUTES]
        print(f"    {'windows':<20} " + "".join(f"{n:>26,}" for n in ns))
        OUT[rgnm] = dict(bands=rows, n_windows=ns)

    print("\n" + "=" * 100)
    print(" 🛑 HOW TO READ THE 'spread' COLUMN")
    print("=" * 100)
    print("    It is max/min across THREE DRIVES OF THE SAME FIRMWARE.  It is therefore a PLACEBO")
    print("    spread — the floor any future build's claimed band effect must beat.  A build that")
    print("    moves a band by less than its own row here has not been shown to do anything.")

    (CACHE / "_cache_r79" / "symptom_bands.json").write_text(json.dumps(OUT, indent=1,
                                                                       default=float))
    print("\n  wrote analysis-2020accord/_cache_r79/symptom_bands.json")


if __name__ == "__main__":
    main()
