#!/usr/bin/env python3
"""ROUTE 50 -- deconfounding ENGAGEMENT from HANDS-OFF in burst #0's transition.

THE PROBLEM. `r50_discriminator.py` ss4 shows the ratchet going 173 -> 4,894 counts p-p across the
latActive transition at constant speed. But the manual arm is the operator CRANKING (sustained
|tq| 2,400-2,900) and the engaged arm is HANDS-OFF (113-285). So that contrast confounds
"engaged vs manual" with "hands-off vs hands-on", and the kit already knows a hand on the wheel
damps the bar.

THE FIX. Score the 2x2 -- {engaged, manual} x {hands-off, hands-on} -- at creep, on route 50 and on
every comparison route. HANDS-OFF is sustained |lowpass(tq, 3 Hz)| <= 300, the kit's convention,
never raw |tq|. If the ratchet needs ENGAGEMENT, the (manual, hands-off) cell stays quiet. If it
only needs a released wheel, that cell lights up.

Writes `_r50_handsoff.json`.  Usage: python r50_handsoff_deconfound.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

NFFT = 256
HANDS_OFF = 300.0
CREEP = 4.0          # m/s -- the ratchet's own creep cell
AMP = 600.0          # 6-9 Hz envelope p99; p-p = 1200
OUT = {}

ROUTES = {"V70 r50": ("_cache_r50", "r50s", [0, 1, 2]),
          "V69 r4f": ("_cache_r4f", "r4fs", list(range(8))),
          "V62 r37": ("_cache_r37", "r37s", list(range(15))),
          "V59 r2c": ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12])}


def hdr(s):
    print("\n" + "=" * 112 + f"\n{s}\n" + "=" * 112)


def scan(cache, pfx, segs):
    out = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        env = band_envelope(tq, fs, 6.0, 9.0)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        for i in range(0, len(tq) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            f0, pr = peak_prom(f, P, 6.0, 9.0)
            out.append(dict(seg=int(s), t0=float(d["t"][i]), v=float(v[w].mean()),
                            eff=float(np.median(eff[w])), lat=float(lat[w].mean()),
                            env=float(np.percentile(env[w], 99)), f0=float(f0), prom=float(pr)))
    return out


ALL = {k: scan(*v) for k, v in ROUTES.items()}

hdr("ss1  THE 2x2 -- {engaged, manual} x {hands-off, hands-on}, CREEP < 4 m/s")
print(f"   HANDS-OFF = sustained |lowpass(tq,3Hz)| <= {HANDS_OFF:.0f} counts (the kit's convention).")
print(f"   A 'hit' is a 2.56 s window with 6-9 Hz envelope p99 >= {AMP:.0f} (p-p >= {2 * AMP:.0f}).")
print("   Windows are cut on a fixed lattice and binned by their OWN covariates -- never masked "
      "first.\n")
print(f"   {'route':10s} {'cell':<22} {'n':>5s} {'secs':>6s} {'hits':>5s} {'hit %':>7s} "
      f"{'p-p p50':>8s} {'p-p max':>8s} {'prom p50':>9s}")
tab = {}
for name, rs in ALL.items():
    cr = [r for r in rs if r["v"] < CREEP]
    for lbl, sel in (("ENGAGED  hands-OFF", lambda r: r["lat"] > 0.9 and r["eff"] <= HANDS_OFF),
                     ("ENGAGED  hands-ON", lambda r: r["lat"] > 0.9 and r["eff"] > HANDS_OFF),
                     ("manual   hands-OFF", lambda r: r["lat"] < 0.1 and r["eff"] <= HANDS_OFF),
                     ("manual   hands-ON", lambda r: r["lat"] < 0.1 and r["eff"] > HANDS_OFF)):
        s = [r for r in cr if sel(r)]
        if not s:
            print(f"   {name:10s} {lbl:<22} {0:>5d} {0.0:>6.1f}     --      --       --       --"
                  f"        --")
            tab[f"{name}|{lbl}"] = dict(n=0)
            continue
        e = np.array([r["env"] for r in s], float)
        h = int((e >= AMP).sum())
        tab[f"{name}|{lbl}"] = dict(n=len(s), secs=len(s) * NFFT / 100.0, hits=h,
                                    rate=h / len(s), pp50=float(2 * np.median(e)),
                                    ppmax=float(2 * e.max()),
                                    prom=float(np.nanmedian([r["prom"] for r in s])))
        x = tab[f"{name}|{lbl}"]
        print(f"   {name:10s} {lbl:<22} {len(s):>5d} {x['secs']:>6.1f} {h:>5d} "
              f"{100 * x['rate']:>6.1f}% {x['pp50']:>8.0f} {x['ppmax']:>8.0f} {x['prom']:>9.1f}")
    print()
OUT["cells"] = tab

hdr("ss2  THE CRUX -- inside HANDS-OFF only, does ENGAGEMENT still matter?")
print("   This removes the hand-on-the-wheel confound entirely: both arms are hands-off.\n")
print(f"   {'route':10s} {'eng hands-off':>16s} {'man hands-off':>16s} {'Fisher p':>10s}   verdict")
cx = {}
for name, rs in ALL.items():
    cr = [r for r in rs if r["v"] < CREEP and r["eff"] <= HANDS_OFF]
    a = [r for r in cr if r["lat"] > 0.9]
    b = [r for r in cr if r["lat"] < 0.1]
    a11 = sum(1 for r in a if r["env"] >= AMP)
    a01 = sum(1 for r in b if r["env"] >= AMP)
    if not a or not b:
        print(f"   {name:10s} {f'{a11}/{len(a)}':>16s} {f'{a01}/{len(b)}':>16s} "
              f"{'--':>10s}   *** one arm EMPTY -- no test")
        cx[name] = dict(eng_hit=a11, eng_n=len(a), man_hit=a01, man_n=len(b), p=None)
        continue
    p = fisher2x2(a11, len(a) - a11, a01, len(b) - a01)
    cx[name] = dict(eng_hit=a11, eng_n=len(a), man_hit=a01, man_n=len(b), p=float(p))
    print(f"   {name:10s} {f'{a11}/{len(a)} = {100 * a11 / len(a):.0f}%':>16s} "
          f"{f'{a01}/{len(b)} = {100 * a01 / len(b):.0f}%':>16s} {p:>10.3g}   "
          f"{'ENGAGEMENT REQUIRED' if p < 0.05 else 'not separable at this n'}")
OUT["handsoff_only"] = cx

print("\n   POOLED over all four routes (hands-off, creep):")
ea = sum(cx[k]["eng_hit"] for k in cx)
en = sum(cx[k]["eng_n"] for k in cx)
ma = sum(cx[k]["man_hit"] for k in cx)
mn = sum(cx[k]["man_n"] for k in cx)
pp = fisher2x2(ea, en - ea, ma, mn - ma)
print(f"     engaged hands-off {ea}/{en} = {100 * ea / max(en, 1):.1f}%   "
      f"manual hands-off {ma}/{mn} = {100 * ma / max(mn, 1):.1f}%   Fisher p = {pp:.3g}")
OUT["pooled"] = dict(eng_hit=ea, eng_n=en, man_hit=ma, man_n=mn, p=float(pp))

hdr("ss3  AND THE OTHER DIRECTION -- does a HAND ON THE WHEEL kill it, while engaged?")
print("   If the driver's grip damps the mode, the (engaged, hands-ON) cell should be quiet even")
print("   though LKAS is applying. This is the t=44.8 collapse in the burst-#0 trace, generalised.\n")
print(f"   {'route':10s} {'eng hands-OFF hit%':>19s} {'eng hands-ON hit%':>19s} {'Fisher p':>10s}")
gx = {}
for name, rs in ALL.items():
    cr = [r for r in rs if r["v"] < CREEP and r["lat"] > 0.9]
    a = [r for r in cr if r["eff"] <= HANDS_OFF]
    b = [r for r in cr if r["eff"] > HANDS_OFF]
    if not a or not b:
        print(f"   {name:10s}   *** one arm EMPTY")
        continue
    a11 = sum(1 for r in a if r["env"] >= AMP)
    a01 = sum(1 for r in b if r["env"] >= AMP)
    p = fisher2x2(a11, len(a) - a11, a01, len(b) - a01)
    gx[name] = dict(off_hit=a11, off_n=len(a), on_hit=a01, on_n=len(b), p=float(p))
    print(f"   {name:10s} {f'{a11}/{len(a)} = {100 * a11 / len(a):.0f}%':>19s} "
          f"{f'{a01}/{len(b)} = {100 * a01 / len(b):.0f}%':>19s} {p:>10.3g}")
OUT["grip"] = gx

(HERE / "_r50_handsoff.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_r50_handsoff.json'}")
