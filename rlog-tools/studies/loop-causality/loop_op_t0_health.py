#!/usr/bin/env python3
"""T0 -- INSTRUMENT HEALTH AND TWO KNOWN-ANSWER CALIBRATIONS.

🛑 Nothing downstream is quotable unless this passes.  The V85 brief is explicit that a 10 ms
alignment error is 97 deg at 27 Hz and "if you get this wrong the answer inverts", so the phase
machinery is validated against two pairs whose answer is known a priori:

  CAL-1  ang -> rate_c   (SAME message, 0x14A).  A derivative leads its integral by exactly +90 deg
         at every frequency.  Expect g2 ~ 1 at low f, phase +90 deg, group delay ~ 0 ms.
         This validates the DFT / phase / unwrap / weighted-slope code on a same-clock pair.
         🛑 It is also the exact invariant `memory/accord/signals/accord-0x18f-payload-one-frame-stale.md` used;
         its residual (-2.2 ms on `rate_c`) is EPS-internal and is quoted here for continuity.

  CAL-2  sc_cmd -> cmd   (THE SAME SIGNAL on TWO INDEPENDENT CLOCKS): openpilot's `sendcan` publish
         time vs the panda's TX-completion echo in the `can` batch stream.  `loop_op_probe` measured
         the latency directly in the TIME domain as 6.52 ms (p5 5.48, p95 7.58) and the payloads are
         identical on 99.97% of frames.  If the native-lattice epoch referencing is correct, the
         FREQUENCY-domain group delay must reproduce ~+6.5 ms with g2 ~ 1 across the whole band.
         🛑 THIS IS THE CROSS-CLOCK CALIBRATION THAT DECIDES WHETHER ANY cmd->bar PHASE IS
         TRUSTWORTHY.  A cross-clock pair with a known 6.5 ms answer is exactly the failure mode
         the brief warns about, deliberately provoked.

Writes `_scratch/cache/loop_op/t0_health.json`.
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

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    out = {"routes": {}, "cal1": {}, "cal2": {}}
    for route in L.ROUTES:
        segs = L.load_route(route)
        rows = []
        for d in segs:
            m = L.native_meta(d)
            if "bar" not in m or "cmd" not in m:
                continue
            rows.append(dict(seg=d["_seg"], n=len(d["t"]),
                             fs_18f=m["bar"]["fs"], fs_14a=m.get("ang", {}).get("fs", np.nan),
                             fs_e4=m["cmd"]["fs"], fs_sc=m.get("sc_cmd", {}).get("fs", np.nan),
                             jit_18f=m["bar"]["jit_ms"], jit_e4=m["cmd"]["jit_ms"],
                             n18=m["bar"]["n"], n14=m.get("ang", {}).get("n", 0),
                             ne4=m["cmd"]["n"]))
        if not rows:
            continue
        fs18 = np.array([r["fs_18f"] for r in rows])
        fse4 = np.array([r["fs_e4"] for r in rows])
        mism = (fs18 - fse4) / fse4
        # worst-case within-block phase error from the fs mismatch, at 27.34 Hz over one block
        dur = L.NPERSEG / 100.0
        slip_ms = np.abs(mism) * dur * 1e3
        print(f"=== {route}")
        print(f"  fs 0x18F  {fs18.min():.5f}..{fs18.max():.5f} Hz   "
              f"fs 0x0E4echo {fse4.min():.5f}..{fse4.max():.5f} Hz")
        print(f"  |fs mismatch| max {np.abs(mism).max()*1e6:.1f} ppm  -> block-end time slip "
              f"max {slip_ms.max():.3f} ms = {360*27.34*slip_ms.max()*1e-3:.2f} deg at 27.34 Hz")
        print(f"  lattice-fit residual (batch-timestamp jitter): 0x18F "
              f"{np.mean([r['jit_18f'] for r in rows]):.2f} ms  0x0E4 "
              f"{np.mean([r['jit_e4'] for r in rows]):.2f} ms  "
              f"(/sqrt(n) -> epoch error < {np.mean([r['jit_18f'] for r in rows])/np.sqrt(5000):.4f} ms)")
        out["routes"][route] = dict(
            rows=rows, fs18=[float(fs18.min()), float(fs18.max())],
            fse4=[float(fse4.min()), float(fse4.max())],
            max_mismatch_ppm=float(np.abs(mism).max() * 1e6),
            max_block_slip_ms=float(slip_ms.max()),
            max_slip_deg_at_2734=float(360 * 27.34 * slip_ms.max() * 1e-3))

    # ---------------------------------------------------------------- CAL-1 and CAL-2 -----------
    for name, xch, ych, expect in (("cal1", "ang", "rate_c", "+90 deg, tau ~ 0"),
                                   ("cal2", "sc_cmd", "cmd", "tau = +6.5 ms, g2 ~ 1")):
        print(f"\n=== {name.upper()}  {xch} -> {ych}   (expect {expect})")
        allrec = []
        for route in L.ROUTES:
            recs = L.collect_native(route, L.mask_engaged, xch=xch, ych=ych)
            allrec += recs
        f, Sxx, Syy, Sxy, K = L.stack(allrec)
        if K == 0:
            print("  NO EPISODES")
            continue
        res = {}
        print(f"  K = {K} episodes,  g2_crit = {L.g2_crit(K):.4f}")
        print(f"  {'band':>8} {'g2':>7} {'|H|':>10} {'phase':>9} {'tau_ms':>9} {'r2':>6}")
        for bn, (lo, hi) in L.BANDS.items():
            s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
            res[bn] = s
            print(f"  {bn:>8} {s['g2']:7.4f} {s['H']:10.4g} {s['ph']:9.2f} "
                  f"{s['tau_ms']:9.3f} {s['r2']:6.3f}")
        # wideband delay over the trustworthy phase band
        w = L.coh(Sxx, Syy, Sxy) * Sxx
        tau, ph0, r2, nb = L.band_delay(f, Sxy, 2.0, 25.0, wgt=w)
        print(f"  WIDEBAND 2-25 Hz: tau = {tau*1e3:+.3f} ms, intercept {ph0:+.2f} deg, "
              f"r2 = {r2:.4f}, nbins = {nb}")
        res["_wideband_2_25"] = dict(tau_ms=tau * 1e3, phi0_deg=ph0, r2=r2, nbin=nb, K=K)
        out[name] = res

    (L.CACHE / "t0_health.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\n-> {L.CACHE / 't0_health.json'}")

    # ------------------------------------------------------------------- verdict ----------------
    c1 = out["cal1"]["_wideband_2_25"]
    c2 = out["cal2"]["_wideband_2_25"]
    print("\n=== VERDICT")
    print(f"  CAL-1 ang->rate_c : intercept {c1['phi0_deg']:+.1f} deg (expect +90), "
          f"tau {c1['tau_ms']:+.2f} ms (expect ~0, EPS-internal residual known to be -2.2 ms)")
    print(f"  CAL-2 sc->echo    : tau {c2['tau_ms']:+.2f} ms (expect +6.5 from the time-domain "
          f"measurement), r2 {c2['r2']:.4f}")
    ok1 = abs(c1["phi0_deg"] - 90) < 15 and abs(c1["tau_ms"]) < 5
    ok2 = abs(c2["tau_ms"] - 6.5) < 1.5
    print(f"  CAL-1 {'PASS' if ok1 else 'FAIL'}   CAL-2 {'PASS' if ok2 else 'FAIL'}")


if __name__ == "__main__":
    main()
