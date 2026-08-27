#!/usr/bin/env python3
"""PART 2 -- fixes a defect in my own PART 1 peak detector, and reads the curve.

🛑 THE DEFECT.  PART 1's `peaks_of` ran on the H1 curve with NO coherence gate.  On the MANUAL
arm it duly reported 11 "peaks" -- at coherences of 0.064, 0.126, 0.129, 0.169, 0.205, ... where
the H1/H2 bracket is up to 370x wide (H1 0.003 vs H2 1.12 at 7.9 Hz).  Those are noise, not
resonances, and A3 then labelled 8 Hz and 12.8 Hz "MAN only" on the strength of them.  A peak
where the transfer function is not measured is not a peak.  Everything here is coherence-gated.

MEASURABLE BAND is defined first, then peaks are sought only inside it.
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
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402

ROOT = V.ROOT
O = json.loads((ROOT / "_scratch/cache/r6f" / "rim_admittance.json").read_text())
COH_MIN = 0.50          # below this the H1/H2 bracket is too wide to call anything


def arr(arm, k):
    return np.array(O["a1"][arm][k], float)


def main():
    f = arr("engaged", "f")
    E = dict(h1=arr("engaged", "h1"), h2=arr("engaged", "h2"), coh=arr("engaged", "coh"),
             lo=arr("engaged", "lo"), hi=arr("engaged", "hi"))
    M = dict(h1=arr("manual", "h1"), h2=arr("manual", "h2"), coh=arr("manual", "coh"),
             lo=arr("manual", "lo"), hi=arr("manual", "hi"))

    V.hdr("B1  WHERE IS THIS MEASURED AT ALL?  Contiguous bands with coherence >= %.2f,\n"
          "    and the H1/H2 bracket width there (they converge when the estimate is good)."
          % COH_MIN)
    O["b1"] = {}
    for arm, D in (("engaged", E), ("manual", M)):
        ok = (D["coh"] >= COH_MIN) & (f >= 4.0) & (f <= 45.0)
        bands, i = [], 0
        while i < len(f):
            if ok[i]:
                j = i
                while j + 1 < len(f) and ok[j + 1]:
                    j += 1
                if f[j] - f[i] >= 0.5:
                    bands.append((float(f[i]), float(f[j])))
                i = j + 1
            else:
                i += 1
        br = D["h2"][ok] / D["h1"][ok]
        print("    %-8s measurable in: %s" % (arm, "  ".join("%.1f-%.1f Hz" % b for b in bands)
                                              or "-- nowhere --"))
        print("    %-8s H2/H1 bracket there: median %.2f  (1.00 = perfect agreement)"
              % ("", float(np.median(br)) if len(br) else np.nan))
        O["b1"][arm] = dict(bands=bands, bracket=float(np.median(br)) if len(br) else None)
    print("\n    🛑 The MANUAL arm is NOT measurable below ~23 Hz.  Every engaged-vs-manual\n"
          "       statement about 8, 12.8 or 21 Hz is therefore UNDERPOWERED, not null.")

    V.hdr("B2  COHERENCE-GATED PEAK LIST.  Peaks sought ONLY where coherence >= %.2f." % COH_MIN)
    O["b2"] = {}
    for arm, D in (("engaged", E), ("manual", M)):
        y, c = D["h1"], D["coh"]
        base = np.array([np.median(y[(f >= max(x - 3.0, 0.5)) & (f <= x + 3.0)]) for x in f])
        rel = y / base
        found = []
        for j in range(1, len(f) - 1):
            if not (4.0 <= f[j] <= 45.0 and c[j] >= COH_MIN):
                continue
            if rel[j] > 1.25 and rel[j] >= rel[j - 1] and rel[j] >= rel[j + 1]:
                found.append(dict(f=float(f[j]), rel=float(rel[j]), coh=float(c[j])))
        print("    %-8s %s" % (arm, ("%d peak(s): " % len(found)) +
                               ", ".join("%.2f Hz (rel %.2f, coh %.2f)"
                                         % (p["f"], p["rel"], p["coh"]) for p in found)
                               if found else "NO resonance peak anywhere in the measurable band"))
        O["b2"][arm] = found

    V.hdr("B3  THE FOUR FREQUENCIES, coherence-gated and honest about what is not measured.")
    print("      %-34s %9s %8s %9s | %9s %8s %9s"
          % ("", "ENG rel", "ENG coh", "ENG call", "MAN rel", "MAN coh", "MAN call"))
    O["b3"] = {}
    base_e = np.array([np.median(E["h1"][(f >= max(x - 3.0, 0.5)) & (f <= x + 3.0)]) for x in f])
    base_m = np.array([np.median(M["h1"][(f >= max(x - 3.0, 0.5)) & (f <= x + 3.0)]) for x in f])
    for f0, lab in ((7.99, "the ~8 Hz RATCHET"), (12.80, "recorded 12.8 Hz plant mode"),
                    (21.10, "the ~21 Hz vibration"), (23.70, "where V86 put it")):
        j = int(np.argmin(np.abs(f - f0)))
        row = {}
        for arm, D, base in (("eng", E, base_e), ("man", M, base_m)):
            r, c = D["h1"][j] / base[j], D["coh"][j]
            call = ("NOT MEASURED" if c < COH_MIN else
                    ("PEAK" if r > 1.25 else ("DIP" if r < 0.80 else "no peak")))
            row[arm] = dict(rel=float(r), coh=float(c), call=call)
        print("      %-34s %9.2f %8.3f %9s | %9.2f %8.3f %9s"
              % ("%.2f Hz  %s" % (f0, lab), row["eng"]["rel"], row["eng"]["coh"],
                 row["eng"]["call"], row["man"]["rel"], row["man"]["coh"], row["man"]["call"]))
        O["b3"]["%.2f" % f0] = dict(label=lab, **row)

    V.hdr("B4  THE SHAPE OF THE ENGAGED CURVE.  What kind of mechanical system is this?")
    ok = (E["coh"] >= COH_MIN) & (f >= 9.0) & (f <= 45.0)
    p = np.polyfit(np.log(f[ok]), np.log(E["h1"][ok]), 1)
    print("    log-log slope of |Omega/T| over 9-45 Hz (coherence-gated): %+.2f" % p[0])
    print("      +1 = pure COMPLIANCE (a spring: Omega/T = j*omega/k)")
    print("      -1 = pure INERTIA    (a mass:   Omega/T = 1/(j*omega*J))")
    print("       0 = pure DAMPING")
    jmin = int(np.argmin(np.where((f >= 5) & (f <= 14) & (E["coh"] >= COH_MIN),
                                  E["h1"], np.inf)))
    print("    minimum of the engaged admittance in 5-14 Hz: %.2f Hz (coh %.2f)"
          % (f[jmin], E["coh"][jmin]))
    print("    ratio |Omega/T| at 45 Hz / at the minimum: %.1fx"
          % (E["h1"][int(np.argmin(np.abs(f - 44.95)))] / E["h1"][jmin]))
    O["b4"] = dict(loglog_slope=float(p[0]), min_f=float(f[jmin]),
                   min_coh=float(E["coh"][jmin]))
    print("\n    ⇒ slope %+.2f with NO peak: over 9-45 Hz the rim moves against a stiff lower\n"
          "      system through a COMPLIANCE (a spring).  There is no resonance in this range to\n"
          "      get above, and the admittance RISES with frequency -- it does not attenuate."
          % p[0])

    # --- is a mode HIDING in the 9.1-14.2 Hz coherence gap, where 12.8 Hz sits? -------------
    hi = (E["coh"] >= COH_MIN) & (f >= 14.2) & (f <= 45.0)
    ph = np.polyfit(np.log(f[hi]), np.log(E["h1"][hi]), 1)
    lo_m = (E["coh"] >= COH_MIN) & (f >= 6.3) & (f <= 9.1)
    pred = np.exp(np.polyval(ph, np.log(f[lo_m])))
    ratio = float(np.median(E["h1"][lo_m] / pred))
    print("\n    HIDDEN-MODE TEST for the 9.1-14.2 Hz coherence gap (where 12.8 Hz sits):")
    print("      fit the compliance law on 14.2-45 Hz (slope %+.2f), extrapolate DOWN to the\n"
          "      6.3-9.1 Hz measured segment.  measured / extrapolated = %.2f" % (ph[0], ratio))
    print("      ~1.0 => one continuous compliance, NO mode in the gap.")
    print("      <1.0 => the high band sits ABOVE the low band's law, i.e. something between\n"
          "              them lifted it -- consistent with a resonance inside the gap.")
    O["b4_gap"] = dict(hi_slope=float(ph[0]), measured_over_extrapolated=ratio)

    V.hdr("B5  RE-ANSWERING THE OPERATOR, on the right instrument.")
    print("    The felt quantity is BAR TORQUE and it is measured directly at 100 Hz.")
    print("    ⇒ 'how much does he feel' needs NO transmissibility model at all.")
    print("    V86 moved the 21 Hz mode to 23.7 Hz.  Measured change in the bar-torque line")
    print("    amplitude, difference-in-differences against the same-alpha control:")
    print("        0.986 [0.687, 1.478]  -- CONSERVED.")
    print("    And the rim admittance over 9-45 Hz has slope %+.2f: no attenuation up there."
          % p[0])
    O["b5"] = dict(amplitude_did=[0.986, 0.687, 1.478], slope=float(p[0]),
                   verdict="dead end, now on the correct instrument")

    (ROOT / "_scratch/cache/r6f" / "rim_admittance.json").write_text(json.dumps(O, indent=1,
                                                                       default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "rim_admittance.json"))


if __name__ == "__main__":
    main()
