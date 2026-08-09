#!/usr/bin/env python3
"""WHAT IS THE ~8 Hz FEATURE, ACTUALLY?  Two things the linewidth number depends on and that
nobody has checked:

  A. Is it ONE line?  Per-window argmax f0 scatters 0.5-0.7 Hz INSIDE V86's single 139.6 s engaged
     run, yet the whole-run peak is 0.0119 Hz wide (FWHM/window-limit = 1.15, i.e. a coherent tone
     for ~1000 cycles).  Both cannot be true of one drifting line.  Enumerate the peaks.

  B. Is the ultra-narrow part an INSTRUMENT ARTEFACT?  `tq` is 0x18F word0 zero-order-held onto the
     0x14A arrival grid.  Two asynchronous ~100 Hz streams beat at |f_18F - f_14A|; the ZOH
     sampling-phase sawtooth at that beat multiplies d(tq)/dt and plants a CRYSTAL-STABLE line.
     A crystal line is exactly what "coherent for 1000 cycles" looks like.
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
import qd_lib as Q                                                    # noqa: E402

ROUTES = {"V86": "r6f", "V86B": "r70", "V85": "r6e"}
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + "\n" + s + "\n" + "=" * 112, flush=True)


def load(route):
    z = np.load(ROOT / f"_cache_{route}" / f"{route}.npz", allow_pickle=True)
    return {k: np.asarray(z[k]) for k in z.files}


# ============================================================================================
hdr("A  PEAK CENSUS on the longest engaged run -- how many lines are in 5-11 Hz?")
peaks = {}
for b, r in ROUTES.items():
    d = load(r)
    fs = 1.0 / np.median(np.diff(d["t"]))
    lat = np.asarray(d["cc_lat"], float) > 0.5
    x = np.asarray(d["tq"], float)
    runs = sorted(Q.contiguous_runs(lat, d["t"], int(20 * fs)), key=lambda ab: ab[0] - ab[1])
    a, bb = runs[0]
    T = (bb - a) / fs
    f, P = Q.hires_spec(x[a:bb], fs)
    m = (f >= 4.0) & (f <= 12.0)
    fm, Pm = f[m], P[m]
    floor = np.median(Pm)
    # local maxima at least 3 window-limits apart, prominence > 8x the band floor
    wl = Q.HANN_FWHM / T
    sep = max(int(3 * wl / (f[1] - f[0])), 1)
    cand = []
    j = 1
    while j < len(Pm) - 1:
        if Pm[j] >= Pm[j - 1] and Pm[j] > Pm[j + 1] and Pm[j] > 8 * floor:
            cand.append((float(Pm[j]), float(fm[j])))
        j += 1
    cand.sort(reverse=True)
    picked = []
    for p, fq in cand:
        if all(abs(fq - q) > 3 * wl for _, q in picked):
            picked.append((p, fq))
        if len(picked) >= 8:
            break
    print(f"\n  {b:5s} longest engaged run {T:6.1f} s   window limit {wl:.4f} Hz   "
          f"band floor {floor:.3g}")
    rows = []
    for p, fq in picked:
        L = Q.linewidth(x[a:bb], fs, flo=fq - 0.25, fhi=fq + 0.25)
        rows.append(dict(f=fq, prom=p / floor, fwhm=L["fwhm"],
                         ratio=L["fwhm"] / wl if np.isfinite(L["fwhm"]) else np.nan,
                         q=L["q_app"]))
        print(f"      f = {fq:7.4f} Hz   prominence {p/floor:8.1f}x   FWHM {L['fwhm']:.4f} Hz "
              f"({rows[-1]['ratio']:5.2f} x limit)   Q_app {L['q_app']:9.1f}")
    peaks[b] = dict(T=T, wl=wl, rows=rows)
OUT["peaks"] = peaks

# ============================================================================================
hdr("B  ZOH BEAT TEST -- are 0x18F and 0x14A asynchronous, and at what beat frequency?")
zoh = {}
for b, r in ROUTES.items():
    d = load(r)
    t14, t18 = np.asarray(d["raw14_t"], float), np.asarray(d["raw18_t"], float)
    t14, t18 = t14[np.isfinite(t14)], t18[np.isfinite(t18)]
    r14 = 1.0 / np.median(np.diff(t14))
    r18 = 1.0 / np.median(np.diff(t18))
    # sample-and-hold AGE: for each row, how old was the held 0x18F sample?
    idx = np.searchsorted(t18, t14, side="right") - 1
    ok = idx >= 0
    age = t14[ok] - t18[idx[ok]]
    # the age sawtooth's own spectrum -- if the two streams beat, the beat line lives HERE
    n = len(age)
    ag = age - age.mean()
    f, P = Q.hires_spec(ag, r14, pad=4)
    m = (f >= 0.2) & (f <= 20.0)
    j = int(np.flatnonzero(m)[np.argmax(P[m])])
    fl = float(np.median(P[m]))
    print(f"\n  {b:5s}  0x14A rate {r14:9.5f} Hz   0x18F rate {r18:9.5f} Hz   "
          f"|difference| {abs(r14-r18)*1000:7.3f} mHz")
    print(f"         hold age: median {np.median(age)*1e3:6.2f} ms  p99 {np.percentile(age,99)*1e3:6.2f} ms"
          f"  max {age.max()*1e3:6.2f} ms  sd {np.std(age)*1e3:5.2f} ms")
    print(f"         strongest line in the AGE sawtooth: {f[j]:7.4f} Hz  "
          f"prominence {P[j]/fl:8.1f}x   (n={n})")
    zoh[b] = dict(rate14=float(r14), rate18=float(r18), beat_mHz=float(abs(r14 - r18) * 1e3),
                  age_med_ms=float(np.median(age) * 1e3), age_sd_ms=float(np.std(age) * 1e3),
                  age_line_hz=float(f[j]), age_line_prom=float(P[j] / fl))
OUT["zoh"] = zoh

# ============================================================================================
hdr("B2 DOES THE HOLD-AGE CARRY THE 7.5 Hz LINE?  coherence of `tq` with the age sawtooth")
for b, r in ROUTES.items():
    d = load(r)
    fs = 1.0 / np.median(np.diff(d["t"]))
    lat = np.asarray(d["cc_lat"], float) > 0.5
    x = np.asarray(d["tq"], float)
    t14 = np.asarray(d["raw14_t"], float)
    t18 = np.asarray(d["raw18_t"], float)
    nrow = len(x)
    t14 = t14[:nrow] if len(t14) >= nrow else np.pad(t14, (0, nrow - len(t14)), mode="edge")
    idx = np.searchsorted(t18, t14, side="right") - 1
    idx = np.clip(idx, 0, len(t18) - 1)
    age = t14 - t18[idx]
    runs = sorted(Q.contiguous_runs(lat, d["t"], int(20 * fs)), key=lambda ab: ab[0] - ab[1])
    a, bb = runs[0]
    La = Q.linewidth(age[a:bb], fs, flo=4.0, fhi=12.0)
    Lx = Q.linewidth(x[a:bb], fs, flo=4.0, fhi=12.0)
    print(f"  {b:5s}  tq line {Lx['f0']:7.4f} Hz (prom {Lx['prom']:7.1f}x)   |   "
          f"hold-age line {La['f0']:7.4f} Hz (prom {La['prom']:7.1f}x)   |   "
          f"separation {abs(Lx['f0']-La['f0']):7.4f} Hz")
    OUT.setdefault("b2", {})[b] = dict(tq_f0=Lx["f0"], tq_prom=Lx["prom"],
                                       age_f0=La["f0"], age_prom=La["prom"])

json.dump(OUT, open(ROOT / "_cache_r6f" / "qd_lines.json", "w"), indent=1, default=float)
print("\nwrote _cache_r6f/qd_lines.json")
