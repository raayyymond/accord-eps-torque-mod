#!/usr/bin/env python3
"""The two operator-remembered instances on V62 route 37, with the validated instruments.

  10:12:15 -> seg 1,  t ~= 10 s
  10:23:24 -> seg 12, t ~= 19 s

Tracking bands (frequencies now KNOWN from the free-locator pass, so a strict band is finally the
right instrument): ratchet 6.3-8.3, mode 19.4-22.4, harmonic 39.9-43.9 Hz.

Reported per 2.56 s window at 0.64 s hop, with NYQFRAC and lag-1 autocorrelation alongside so an
aliasing claim can be checked rather than assumed.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402
import analyze_r37_newgrind as A  # noqa: E402
import analyze_r37_nyquist as N  # noqa: E402

C.CACHE = C.ROOT / "_cache_r37"
NF = 256
BANDS = (("rat", 6.3, 8.3), ("mode", 19.4, 22.4), ("harm", 39.9, 43.9))


def run(s, tc, label, half=8.0):
    d = C.load(s, C.CACHE, "r37s")
    fs = C.fs_of(d)
    w0 = float(d["wall_t0"][0])
    f = np.fft.rfftfreq(NF, 1 / fs)
    lo, hi = tc - half, tc + half
    m = (d["t"] >= lo) & (d["t"] <= hi)
    a = int(np.flatnonzero(m)[0])
    b = int(np.flatnonzero(m)[-1]) + 1
    envs = {k: C.band_envelope(d["tq"][a:b], fs, l, h) for k, l, h in BANDS}
    print(f"\n{'='*126}")
    print(f"SEG {s}  {label}  t {lo:.1f}..{hi:.1f}  fs={fs:.3f}  Nyquist={fs/2:.2f}")
    print(f"{'='*126}")
    print("  t0    wall     | free f0  prom |  ratchet 6.3-8.3   |   mode 19.4-22.4   | "
          " harm 39.9-43.9   | NYQ   lag1 | vEgo  |ang|  eff   |e4|  prs")
    for i in range(0, b - a - NF + 1, 64):
        sg = d["tq"][a + i:a + i + NF]
        P = C.periodogram(sg, fs, NF)
        if P is None:
            continue
        sl = slice(a + i, a + i + NF)
        f0, pr = A.locate(f, P, 5.0, 48.0)
        y = sg - sg.mean()
        r1 = float(np.dot(y[:-1], y[1:]) / (np.dot(y, y) + 1e-30))
        nyq = float(P[f >= 0.90 * fs / 2].sum() / max(P[1:].sum(), 1e-30))
        cells = ""
        for k, l, h in BANDS:
            fk, pk = C.peak_prom(f, P, l, h)
            e = float(np.percentile(envs[k][i:i + NF], 99))
            cells += f" {fk:5.2f} p{pk:6.1f} e{e:6.0f} |"
        print(f" {d['t'][a+i]:6.2f} {time.strftime('%H:%M:%S', time.localtime(w0+d['t'][a+i]))} "
              f"| {f0:6.2f} {pr:6.1f} |{cells} {nyq:5.3f} {r1:+5.2f} | "
              f"{np.mean(d['cs_v'][sl]):5.2f} {np.mean(np.abs(d['ang'][sl])):6.1f} "
              f"{np.mean(np.abs(C.sustained(d['tq'][sl], fs))):6.0f} "
              f"{np.mean(np.abs(d['e4tq'][sl])):5.0f} "
              f"{np.mean(d['cs_press'][sl] > 0.5):4.2f}")
    # health
    ev = json.loads((C.CACHE / f"r37s{s}_events.json").read_text())
    near = [e for e in ev if lo - 2 <= e["t"] <= hi + 2 and
            e["name"] not in ("pedalPressed", "gasPressedOverride", "laneChange")]
    nm = sorted({e["name"] for e in near})
    print(f"  HEALTH: STEER_STATUS nonzero frames in window = "
          f"{int((d['sstat'][a:b] != 0).sum())}, ST==4 = {int((d['sstat'][a:b] == 4).sum())}; "
          f"events near window: {nm if nm else 'none'}")


if __name__ == "__main__":
    run(1, 10.0, "operator instance 1 -- 10:12:15")
    run(12, 19.0, "operator instance 2 -- 10:23:24")
