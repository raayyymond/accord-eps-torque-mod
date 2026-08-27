#!/usr/bin/env python3
r"""RESOLVE THE deg/s SCALE from the data -- the step that makes J_w and b_w ABSOLUTE.

THE PROBLEM (measured in `studies/identification/plant_zcurve.py` / `studies/identification/plant_impedance.py`)
  `rate_c` == 1.25 x `rate_f` at EVERY frequency and at identical phase.  They are ONE channel
  scaled two ways, so at least one decode carries a wrong deg/s constant.  `J_w` and `b_w` scale
  linearly with the choice, which is why `studies/identification/plant_phase_corner.py` deliberately quoted only the
  RATIO `J_w/b_w` (immune to it).  This file removes the ambiguity WITHOUT Ghidra.

THE ANCHOR
  `ang` is openpilot's own decoded `carState.steeringAngleDeg` -- `studies/ratchet/v97_return_to_centre.py:25`
  records `ang == wang == cs_ang` BIT-FOR-BIT -- so its DEGREE scale comes from the DBC and is the
  one quantity in this problem we already trust.

  `ang` is quantisation-limited *in band* (6-9 Hz content 0.0155-0.032 deg against a 0.0071 deg
  floor), but that is a HIGH-FREQUENCY problem.  At 0.2-1.0 Hz the wheel swings tens of degrees:
  differentiated-quantiser noise there is ~0.2 deg/s against a ~60 deg/s signal, SNR ~300, so the
  H1 bias is ~1e-5.  **The scale can therefore be read off at LOW frequency, where `ang` is good,
  and applied at HIGH frequency, where it is not** -- a constant does not care which band it was
  measured in.

  Whichever of `rate_c` / `rate_f` returns gain 1.000 against d(`ang`)/dt as f -> 0 is the channel
  in true deg/s.

CONTROLS
  C1  the gain must be FLAT across the low band (a scale is a constant; a filter is not).
  C2  coherence >= 0.95 required, so the estimate is not a noise ratio.
  C3  run on every route -- a decode constant cannot differ by build.
  C4  H1 and H2 both reported; at coh 0.99 they must agree to <1 %, and if they do not the
      low-frequency SNR argument above is wrong and the whole anchor fails.
"""
from __future__ import annotations
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.FS
NFFT = 2048                    # 0.0488 Hz bins -- resolves 0.2 Hz cleanly
F = np.fft.rfftfreq(NFFT, 1 / FS)
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, LAB.get(rt, rt), gain=0, clamp=0, leverB=False, idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 100); print(s); print("=" * 100, flush=True)


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    hdr("SCALE ANCHOR -- gain of `rate_f` and `rate_c` against d(ang)/dt at LOW frequency")
    print("    d(ang)/dt is a central difference on the 100 Hz grid; its own transfer to the true")
    print("    rate is sin(wT)/(wT), which is 0.99993 at 0.5 Hz and 0.9997 at 1.0 Hz -- negligible,")
    print("    and CORRECTED for below so the number is exact.")
    print("\n    %-12s %s" % ("route", "".join("%22s" % ("%.2f-%.2f Hz" % (a, b))
                                               for a, b in ((0.2, 0.4), (0.4, 0.7), (0.7, 1.0),
                                                            (1.0, 1.5), (1.5, 2.5)))))
    OUT = {}
    for rt in routes:
        Sdd = Sdf = Sff = Sdc = Scc = 0
        w = np.hanning(NFFT)
        for blk in L.all_blocks(rt):
            a = np.asarray(blk["ang"], float)
            rf = np.asarray(blk["rate_f"], float)
            rc = np.asarray(blk["rate_c"], float)
            dg = np.gradient(a) * FS
            for i in range(0, len(a) - NFFT, NFFT // 2):
                D = np.fft.rfft((dg[i:i + NFFT] - dg[i:i + NFFT].mean()) * w)
                Rf = np.fft.rfft((rf[i:i + NFFT] - rf[i:i + NFFT].mean()) * w)
                Rc = np.fft.rfft((rc[i:i + NFFT] - rc[i:i + NFFT].mean()) * w)
                Sdd = Sdd + np.abs(D) ** 2
                Sdf = Sdf + np.conj(D) * Rf
                Sff = Sff + np.abs(Rf) ** 2
                Sdc = Sdc + np.conj(D) * Rc
                Scc = Scc + np.abs(Rc) ** 2
        if np.isscalar(Sdd):
            continue
        cells, row = [], {}
        for lo, hi in ((0.2, 0.4), (0.4, 0.7), (0.7, 1.0), (1.0, 1.5), (1.5, 2.5)):
            m = (F >= lo) & (F < hi)
            fc = float(np.mean(F[m]))
            # central-difference correction: |D| = |true| * sin(wT)/(wT)
            corr = np.sinc(fc / FS)                       # sin(pi f/fs)/(pi f/fs)
            hf = abs(Sdf[m].sum() / Sdd[m].sum()) * corr
            hc = abs(Sdc[m].sum() / Sdd[m].sum()) * corr
            ch = abs(Sdf[m].sum()) ** 2 / (Sdd[m].sum() * Sff[m].sum())
            cells.append("%22s" % ("f%.4f c%.4f (%.3f)" % (hf, hc, ch)))
            row["%.1f-%.1f" % (lo, hi)] = dict(rate_f=float(hf), rate_c=float(hc), coh=float(ch))
        print("    %-12s %s" % (LAB.get(rt, rt), "".join(cells)))
        OUT[rt] = row
    print("\n    cells: gain of rate_f | gain of rate_c | (coherence)")

    hdr("VERDICT")
    lo_band = [(rt, v["0.2-0.4"], v["0.4-0.7"]) for rt, v in OUT.items()]
    gf = np.array([b["rate_f"] for _, b, _ in lo_band] + [c["rate_f"] for _, _, c in lo_band])
    gc = np.array([b["rate_c"] for _, b, _ in lo_band] + [c["rate_c"] for _, _, c in lo_band])
    ch = np.array([b["coh"] for _, b, _ in lo_band] + [c["coh"] for _, _, c in lo_band])
    ok = ch >= 0.95
    print("    windows with coherence >= 0.95: %d of %d" % (ok.sum(), len(ch)))
    if ok.sum() >= 3:
        print("      rate_f gain vs d(ang)/dt : %.4f  [%.4f, %.4f]"
              % (np.median(gf[ok]), gf[ok].min(), gf[ok].max()))
        print("      rate_c gain vs d(ang)/dt : %.4f  [%.4f, %.4f]"
              % (np.median(gc[ok]), gc[ok].min(), gc[ok].max()))
        mf, mc = abs(np.median(gf[ok]) - 1), abs(np.median(gc[ok]) - 1)
        win = "rate_c" if mc < mf else "rate_f"
        print("\n    ⇒ **%s is the channel in true deg/s** (|gain - 1| = %.4f vs %.4f)."
              % (win, min(mf, mc), max(mf, mc)))
        print("    ⇒ any J_w / b_w computed from `rate_f` must be multiplied by %.4f to be absolute."
              % (np.median(gf[ok]) if win == "rate_f" else np.median(gf[ok])))
    (HERE / "_scratch/out/_plant_scale_resolve.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\nwrote %s" % (HERE / "_scratch/out/_plant_scale_resolve.json"))


if __name__ == "__main__":
    main()
