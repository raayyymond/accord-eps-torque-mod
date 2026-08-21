#!/usr/bin/env python3
r"""stock_r97_ringdown.py -- ring-down zeta/Q on STOCK, with the full EDGE ACCOUNTING.

`stock_r97_resonance.r2` returned only ONE usable ring-down on stock at the frozen
(4 s pre / 4 s post) criterion, so this file prints WHY each latActive falling edge was rejected
and re-runs the fit at a relaxed (2.5 s pre / 3.0 s post) criterion.  A rejection census is the
difference between "stock has no resonance" and "stock never disengaged where one could be seen".

Envelope is `scipy.signal.hilbert` on a 2nd-order Butterworth band-pass -- the construction
`qd_lib.envelope_stats` and `qd_final.py` use.  The kit's `_r31_common.band_envelope` /
`_r2b_common.band_envelope` (one-sided `H = 2X` + `irfft` => rectified, not analytic) is NEVER
called here.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0, bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")
ARMS = [(r, l) for r, l in
        [("97", "V9b STOCK 1x"), ("85", "V100 4x"), ("95", "V101 8x"), ("96", "V102 6x")]
        if L._segs(r)]
OUT = {}


def env(x, fs, lo, hi):
    b = butter(2, [max(lo, 0.5), hi], btype="band", fs=fs)
    return np.abs(hilbert(filtfilt(*b, np.asarray(x, float))))


def run(pre_s, post_s, fit_s=2.0, tag=""):
    print("\n" + "=" * 104)
    print("RING-DOWN, %.1f s engaged before / %.1f s manual after, %.1f s log-fit   %s"
          % (pre_s, post_s, fit_s, tag))
    print("=" * 104)
    for rt, lab in ARMS:
        why = Counter()
        rows = []
        for blk in L.all_blocks(rt):
            t, fs = blk["t"], L.FS
            x = np.asarray(blk["tq"], float)
            lat = blk["cc_lat"] > 0.5
            v = np.abs(blk["v_rear"])
            npre, npost = int(pre_s * fs), int(post_s * fs)
            for i in np.flatnonzero(lat[:-1] & ~lat[1:]):
                why["raw falling edges"] += 1
                if i - npre < 0 or i + npost >= len(t):
                    why["  too near a block edge"] += 1
                    continue
                if not lat[i - npre:i + 1].all():
                    why["  not continuously engaged before"] += 1
                    continue
                if lat[i + 1:i + 1 + npost].any():
                    why["  re-engaged inside the post window"] += 1
                    continue
                if v[i] < 1.0:
                    why["  stationary (v < 1 m/s) -- nothing to ring"] += 1
                    continue
                f0 = 7.79
                pre = x[max(i - int(8 * fs), 0):i]
                if len(pre) > 256:
                    f, p = L.psd(pre[-256:], fs, np.hanning(256))
                    m = (f >= 5) & (f <= 12)
                    if m.any():
                        f0 = float(f[m][np.argmax(p[m])])
                seg = x[i - npre:i + npost]
                e = env(seg, fs, max(f0 - 1.5, 0.5), f0 + 1.5)
                pre_env = float(np.percentile(e[:npre], 75))
                post = e[npre:]
                floor = float(np.percentile(post[int(min(2.5, post_s - 0.5) * fs):], 25))
                tt = np.arange(len(post)) / fs
                m = tt <= fit_s
                y = np.sqrt(np.clip(post[m] ** 2 - floor ** 2, 1e-9, None))
                if pre_env <= 1.2 * floor:
                    why["  no line to ring (pre-env <= 1.2 x floor)"] += 1
                    continue
                if np.count_nonzero(y > 1.5e-4) < 20:
                    why["  fit sample count too low"] += 1
                    continue
                c = np.polyfit(tt[m], np.log(y), 1)
                lam = -float(c[0])
                if not np.isfinite(lam) or lam <= 0:
                    why["  envelope GREW after disengagement"] += 1
                    continue
                z = lam / (2 * np.pi * f0)
                why["USABLE"] += 1
                rows.append(dict(seg=int(blk["_seg"]), t=float(t[i]), v=float(v[i]), f0=f0,
                                 pre_env=pre_env, floor=floor, lam=lam, zeta=z, q=1 / (2 * z)))
        print("\n  --- %s ---" % lab)
        for k, n in why.most_common():
            print("      %-46s %d" % (k, n))
        for r in rows:
            print("      seg%-3d t=%6.1f s  v=%5.2f m/s  f0=%5.2f Hz  pre-env %8.1f ct "
                  "(floor %6.1f)  zeta=%.4f  Q=%6.1f"
                  % (r["seg"], r["t"], r["v"], r["f0"], r["pre_env"], r["floor"],
                     r["zeta"], r["q"]))
        if rows:
            z = np.array([r["zeta"] for r in rows])
            a = np.array([r["pre_env"] for r in rows])
            print("      => n=%d   zeta median %.4f  [%.4f, %.4f]   Q median %.1f  "
                  "[%.1f, %.1f]   pre-edge line amplitude median %.1f ct"
                  % (len(z), np.median(z), z.min(), z.max(), 1 / (2 * np.median(z)),
                     1 / (2 * z.max()), 1 / (2 * z.min()), np.median(a)))
        OUT.setdefault(tag or "%.1f/%.1f" % (pre_s, post_s), {})[rt] = dict(
            build=lab, census=dict(why), edges=rows)


if __name__ == "__main__":
    run(4.0, 4.0, tag="FROZEN (qd_final.py's own criterion)")
    run(2.5, 3.0, tag="RELAXED")
    Path(__file__).with_name("_stock_r97_ringdown.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _stock_r97_ringdown.json")
