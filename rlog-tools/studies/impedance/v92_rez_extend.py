#!/usr/bin/env python3
r"""Extend route 77's driving-point impedance `Re(Z)` from 16 Hz to 35 Hz.

WHY: the D-term sweep needs the SIGN of the dissipative product at 18-22 and 26-31 Hz.  Cutting `Kd`
to remove a +0.076 pump at the ratchet could remove a -0.25..-0.36 DAMPING term in the grinding
bands -- 3-5x larger than the effect being bought.  The trade cannot be priced without these phases.

🛑 READ-ONLY.  `_scratch/cache/r77/` and `probe/decode_v90_probe.py` are frozen inputs.  This file imports the
frozen estimator (`_wins`, `_band_transfer`) so the extension is the SAME instrument as §4.1, and it
re-runs §4.1's own bands as a positive control -- if 2-16 Hz does not reproduce, nothing else counts.

★ THE SKEW QUESTION, SETTLED FROM THE EXTRACTOR'S SOURCE -- AND THE ANSWER IS THE OPPOSITE OF THE
  BRIEF'S ASSUMPTION.  The brief warns that the `0x18F`/`0x14A` skew (|H| 0.93 and <=5.4 deg at 23 Hz)
  limits the phase.  It does not, because BOTH channels come from the SAME `0x18F` frame:

      last18 = (i16be(d,0) * -1.0,   i16be(d,2) * -0.1,   ...)          # 0x18F payload
      rows.append((tm, ..., last18[0], last18[1], ...))
      names  = [ "t","ang","rate_c","wang","probe", "tq", "rate_f", ... ]
                                                     ^^^^   ^^^^^^
                                              last18[0]     last18[1]

  ⇒ `tq` AND `rate_f` are both fields of the held `0x18F` message, so any staleness is COMMON to
  numerator and denominator and CANCELS EXACTLY in `Z = S_Tw / S_ww`.  The skew would only bite if
  the rate were taken from `0x14A` (`rate_c` / `ang` / `wang`).  §3 below MEASURES that difference by
  recomputing Z with `rate_c` and showing the phase separates by ~3.29 deg/Hz, which is the 9.15 ms
  skew -- a positive control for the claim rather than an assertion of it.

⚠ WHAT STILL LIMITS THE ESTIMATE, stated per the brief:
  - `rate_f`'s ~25 % scale error CANCELS in a phase but NOT in |Z|.  Phases are the deliverable.
  - Both channels are sampled at ~100 Hz with no anti-alias filter; content above 50 Hz folds in.
  - 🛑 COHERENCE IS THE GATE, and the rule is PRE-DECLARED, not chosen after seeing the numbers:
        a band's phase is reported as MEASURABLE only if  coh^2 >= 0.10  AND  coh^2 >= 5x shuffled.
    Anything failing that is reported as UNMEASURABLE.  "Cannot establish" is a real answer here.

🛑 THE ORDER VETO IS PER-BAND, AND THAT IS DELIBERATE.  The symmetric veto exists to stop a CONTRAST
being taken between two different window sets.  These are six INDEPENDENT phase estimates, not a
contrast, so a per-band veto is legitimate -- and a union veto is impossible anyway: orders 1-6 cover
11-36 Hz at every speed above ~3.9 m/s, so a union veto drops essentially every moving window.  Both
the vetoed and unvetoed estimates are reported side by side; agreement is the evidence.

Usage:  python studies/impedance/v92_rez_extend.py
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
sys.path.insert(0, str(ROOT / "_scratch/cache/r73"))

import decode_v90_probe as P          # noqa: E402  -- FROZEN, imported read-only

RNG = np.random.default_rng(92_2211)
DEG2RAD = np.pi / 180.0
OUTJ = ROOT / "analysis-2020accord" / "_scratch/cache/r77" / "v92_rez_to_35hz.json"

# §4.1's own bands first (POSITIVE CONTROL -- must reproduce), then the extension
BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
         ("12-16", 12.0, 16.0),
         ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0), ("22-26", 22.0, 26.0),
         ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)]
COH_ABS, COH_REL = 0.10, 5.0          # PRE-DECLARED trust gate


def order_conflict(v, lo, hi):
    """True if any wheel order 1-6 can land inside [lo-GUARD, hi+GUARD] at this speed."""
    for k in P.ORDERS:
        for c in (P.CIRC_LO, P.CIRC_HI):
            if lo - P.GUARD <= k * v / c <= hi + P.GUARD:
                return True
    return False


def trust(coh, shuf):
    return bool(np.isfinite(coh) and coh >= COH_ABS and coh >= COH_REL * max(shuf, 1e-9))


def run(tag, rate_col, z, mask, t, tq, speed, fs):
    W = P._wins(mask, t, P.NW_Z, P.HOP_Z, (rate_col, tq, speed))
    print(f"\n  === {tag}: {len(W)} engaged hands-off moving windows ===")
    rows = {}
    print(f"    {'band':7s} {'n':>5s} {'v med':>7s} {'Re(Z)':>11s} {'|Z|':>10s} {'phase':>9s} "
          f"{'coh²':>7s} {'shuf':>7s} {'TRUST':>6s}")
    for nm, lo, hi in BANDS:
        for vet in (False, True):
            sel = [w for w in W
                   if (not vet) or (not order_conflict(float(np.mean(np.abs(w[2]))), lo, hi))]
            if len(sel) < 6:
                if vet:
                    rows[f"{nm}/vetoed"] = dict(n=len(sel), scoreable=False)
                    print(f"    {nm:7s} {len(sel):5d}   -- too few after the order veto, "
                          f"NOT SCOREABLE")
                continue
            pairs = [(w[0], w[1]) for w in sel]
            r = P._band_transfer(pairs, fs, P.NW_Z, [(nm, lo, hi)])[nm]
            idx = RNG.permutation(len(pairs))
            rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                                   for i in range(len(pairs))], fs, P.NW_Z,
                                  [(nm, lo, hi)])[nm]
            vmed = float(np.median([np.mean(np.abs(w[2])) for w in sel]))
            ok = trust(r["coh2"], rs["coh2"])
            key = f"{nm}/vetoed" if vet else f"{nm}/all"
            rows[key] = dict(n=len(sel), v_med=vmed, re_z=r["re_over_sxx"], absz=r["gain"],
                             phase_deg=r["phase_deg"], coh2=r["coh2"], coh2_shuf=rs["coh2"],
                             trustworthy=ok, scoreable=True)
            lbl = f"{nm}{'*' if vet else ' '}"
            print(f"    {lbl:7s} {len(sel):5d} {vmed:7.2f} {r['re_over_sxx']:11.1f} "
                  f"{r['gain']:10.1f} {r['phase_deg']:8.1f}° {r['coh2']:7.3f} {rs['coh2']:7.3f} "
                  f"{'YES' if ok else '🛑 NO':>6s}")
    print("    (* = wheel-order vetoed for that band; the row above it is all windows)")
    return rows


if __name__ == "__main__":
    z = P._load77()
    t = np.asarray(z["t"], float)
    tq = np.asarray(z["tq"], float)                       # 0x18F bytes 0-1  (last18[0])
    rate_f = np.asarray(z["rate_f"], float) * DEG2RAD     # 0x18F bytes 2-3  (last18[1])
    rate_c = np.asarray(z["rate_c"], float) * DEG2RAD     # 0x14A bytes 2-4  -- the SKEWED pair
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    mask = lat & (~press) & (v > 0.5)
    fs = 1.0 / float(np.median(np.diff(t)))
    print(f"  route 77, fs {fs:.2f} Hz, mask = engaged & hands-off & moving: "
          f"{int(mask.sum()):,} frames = {mask.sum()/fs:.1f} s")
    print(f"  PRE-DECLARED TRUST GATE: coh² >= {COH_ABS} AND coh² >= {COH_REL}x shuffled")

    OUT = {"trust_gate": dict(abs=COH_ABS, rel=COH_REL)}
    OUT["rate_f_0x18F"] = run("Z from rate_f (0x18F) -- SKEW-FREE, the deliverable",
                              rate_f, z, mask, t, tq, v, fs)
    OUT["rate_c_0x14A"] = run("CONTROL: Z from rate_c (0x14A) -- the SKEWED pair, for comparison "
                              "only", rate_c, z, mask, t, tq, v, fs)

    print("\n  === SKEW POSITIVE CONTROL: phase(rate_c) - phase(rate_f) vs the 9.15 ms prediction ===")
    print(f"    {'band':7s} {'f_c':>6s} {'rate_f':>9s} {'rate_c':>9s} {'diff':>9s} "
          f"{'predicted':>10s}")
    OUT["skew_control"] = {}
    for nm, lo, hi in BANDS:
        a = OUT["rate_f_0x18F"].get(f"{nm}/all")
        b = OUT["rate_c_0x14A"].get(f"{nm}/all")
        if not (a and b and a.get("scoreable") and b.get("scoreable")):
            continue
        fc = 0.5 * (lo + hi)
        d = ((b["phase_deg"] - a["phase_deg"] + 180) % 360) - 180
        pred = -3.294 * fc                       # 9.15 ms of extra delay on the 0x14A channel
        OUT["skew_control"][nm] = dict(f_c=fc, diff_deg=float(d), predicted_deg=float(pred))
        print(f"    {nm:7s} {fc:6.1f} {a['phase_deg']:8.1f}° {b['phase_deg']:8.1f}° "
              f"{d:8.1f}° {pred:9.1f}°")
    print("    ⇒ a difference tracking the prediction confirms the skew is REAL and that the")
    print("      `rate_f` pair is FREE of it (both fields come from the same 0x18F frame).")

    OUTJ.write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\n  wrote {OUTJ}")
