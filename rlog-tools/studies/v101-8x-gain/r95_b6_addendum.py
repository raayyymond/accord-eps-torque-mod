#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- ADDENDUM to `studies/v101-8x-gain/r95_b6_clamp.py`.

  A.  IS `gp-0x6b4c` ACTUALLY THE LKAS COMMAND?  b5 = sign(gp-0x6b4c) agrees with
      sign(openpilot's command) on only 60.5 % of engaged frames.  Chance-under-independence for
      that pair of duties is 51.0 %.  If the cell were a positive scaling of the low-passed CAN
      command, agreement would be ~100 % minus a low-pass lag.  Quantify it properly, conditioned
      on a LARGE, STEADY, one-signed command where a lag cannot explain a disagreement.
      🛑 This matters because b6 thresholds THE SAME CELL: "the clamp never binds" is a statement
      about gp-0x6b4c, and it only transfers to the 0xC61B2/0xC61B4 forward-path clamp if that
      cell really is the clamped LKAS lane.

  B.  THE PROTECTED METRIC, MATCHED.  V101 vs V100 wheel-angle-rate under max LKAS command with
      the SAME hands-light and speed conditioning on both routes.

  C.  EXPOSURE CONFOUND CHECK.  The two drives were not driven the same way -- state it.
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
import r95_lib as L  # noqa: E402

FS = L.fs()
lat = L.engaged()
tq, rate_f, ang = L.col("tq"), L.col("rate_f"), L.col("ang")
sc_tq = L.col("sc_tq")
b5, b6 = L.col("v101_b5"), L.col("v101_b6")
vk = np.abs(L.col("cs_v")) * 3.6
ts = np.abs(L.lowpass(tq, FS, 3.0, mask=lat))
out = {}

R85 = dict(np.load(ROOT / "analysis-2020accord/_scratch/cache/r85/r85.npz", allow_pickle=True))
lat85 = np.asarray(R85["cc_lat"], float) > 0.5
vk85 = np.abs(np.asarray(R85["cs_v"], float)) * 3.6
tq85, rate85, sc85 = (np.asarray(R85[k], float) for k in ("tq", "rate_f", "sc_tq"))
ts85 = np.abs(L.lowpass(tq85, FS, 3.0, mask=lat85))

# ======================================================================================
print("=" * 104)
print("A. IS gp-0x6b4c THE LKAS COMMAND?   b5 = (gp-0x6b4c < 0)  vs  sign(openpilot's command)")
print("=" * 104)
neg_cmd = (sc_tq < 0).astype(float)
d5, dc = float(b5[lat].mean()), float(neg_cmd[lat].mean())
chance = d5 * dc + (1 - d5) * (1 - dc)
agree = float((b5[lat] == neg_cmd[lat]).mean())
print(f"    duty: b5 {d5:.4f}   sign(cmd)<0 {dc:.4f}")
print(f"    AGREEMENT  {agree*100:6.2f} %      chance-under-INDEPENDENCE {chance*100:6.2f} %      "
      f"a positive scaling would give ~100 %")
print(f"    Cohen-style excess over chance: {(agree-chance)/(1-chance)*100:6.2f} % of the "
      f"available headroom")
out["A_agreement"] = dict(b5_duty=d5, cmd_neg_duty=dc, agreement=agree, chance=chance)

print("\n    Conditioned on a LARGE, STEADY, ONE-SIGNED command -- a low-pass LAG cannot explain")
print("    a disagreement here, because the command has not changed sign for >= 0.5 s.")
steady = np.zeros(len(sc_tq), bool)
W = int(0.5 * FS)
sgn = np.sign(sc_tq)
for i in range(W, len(sc_tq)):
    steady[i] = np.all(sgn[i - W:i + 1] == sgn[i]) and sgn[i] != 0
print(f"    {'|cmd| threshold':>18s} {'n':>7s} {'sec':>7s} {'agreement':>11s} {'chance':>8s} "
      f"{'b5 flips/s':>11s} {'cmd flips/s':>12s}")
for thr in (0, 500, 1000, 2000, 3000, 4095):
    m = lat & steady & (np.abs(sc_tq) >= thr)
    if m.sum() < 200:
        continue
    a = float((b5[m] == neg_cmd[m]).mean())
    d5m, dcm = float(b5[m].mean()), float(neg_cmd[m].mean())
    ch = d5m * dcm + (1 - d5m) * (1 - dcm)
    idx = np.where(m)[0]
    f5 = float(np.sum(np.abs(np.diff(b5[idx]))) / (m.sum() / FS))
    fc = float(np.sum(np.abs(np.diff(neg_cmd[idx]))) / (m.sum() / FS))
    print(f"    {thr:>18d} {int(m.sum()):7d} {m.sum()/FS:7.1f} {a*100:10.2f} % {ch*100:7.2f} % "
          f"{f5:11.2f} {fc:12.2f}")
    out.setdefault("A_steady", []).append(
        dict(thr=thr, n=int(m.sum()), agree=a, chance=ch, b5_flips=f5, cmd_flips=fc))
print("\n    ⇒ If agreement stays near chance while the command is large and one-signed for 0.5 s,")
print("      gp-0x6b4c is NOT a positive scaling of openpilot's command.")

# ======================================================================================
print("\n" + "=" * 104)
print("B. PROTECTED METRIC, MATCHED CONDITIONING ON BOTH ROUTES")
print("   |rate_f| = the EPS's own fine angle-rate channel (0x18F b2:4 x -0.1 deg/s) at 100 Hz.")
print("   hands-light = |lowpass(tq,3Hz)| < 150 counts.  All strata engaged only.")
print("=" * 104)
print(f"    {'stratum':>44s} | {'route':>5s} {'n':>6s} {'sec':>6s} {'p50':>7s} {'p90':>8s} "
      f"{'p99':>8s} {'max':>8s}")
STR = [
    ("ALL ENGAGED", lambda v, c, s: np.ones(len(v), bool)),
    ("|cmd| >= 4095 (openpilot railed)", lambda v, c, s: c >= 4095),
    ("|cmd| >= 4095 AND hands-light", lambda v, c, s: (c >= 4095) & (s < 150)),
    ("|cmd| >= 2000 AND hands-light", lambda v, c, s: (c >= 2000) & (s < 150)),
    ("|cmd| >= 2000, hands-light, v >= 20", lambda v, c, s: (c >= 2000) & (s < 150) & (v >= 20)),
    ("hands-light, any cmd", lambda v, c, s: s < 150),
]
for nm, fn in STR:
    for tag, m0, v, c, s, r in (("r95", lat, vk, np.abs(sc_tq), ts, rate_f),
                                ("r85", lat85, vk85, np.abs(sc85), ts85, rate85)):
        m = m0 & fn(v, c, s)
        if m.sum() < 60:
            print(f"    {nm if tag=='r95' else '':>44s} | {tag:>5s} {int(m.sum()):6d} "
                  f"{m.sum()/FS:6.1f}   -- SAMPLE TOO THIN, CANNOT ANSWER")
            out.setdefault("B_protected", []).append(dict(stratum=nm, route=tag,
                                                          n=int(m.sum()), thin=True))
            continue
        a = np.abs(r[m])
        print(f"    {nm if tag=='r95' else '':>44s} | {tag:>5s} {int(m.sum()):6d} "
              f"{m.sum()/FS:6.1f} {np.percentile(a,50):7.1f} {np.percentile(a,90):8.1f} "
              f"{np.percentile(a,99):8.1f} {a.max():8.1f}")
        out.setdefault("B_protected", []).append(
            dict(stratum=nm, route=tag, n=int(m.sum()), sec=float(m.sum() / FS),
                 p50=float(np.percentile(a, 50)), p90=float(np.percentile(a, 90)),
                 p99=float(np.percentile(a, 99)), max=float(a.max())))

print("\n    🛑 The 21.5-25.5 Hz BUZZ lives in this same channel.  Repeat with rate_f LOW-PASSED")
print("       below 5 Hz, which is the COMMANDED motion with the buzz removed:")
rs95 = L.lowpass(rate_f, FS, 5.0, mask=lat)
rs85 = L.lowpass(rate85, FS, 5.0, mask=lat85)
for nm, fn in STR[:5]:
    for tag, m0, v, c, s, r in (("r95", lat, vk, np.abs(sc_tq), ts, rs95),
                                ("r85", lat85, vk85, np.abs(sc85), ts85, rs85)):
        m = m0 & fn(v, c, s)
        if m.sum() < 60:
            continue
        a = np.abs(r[m])
        a = a[np.isfinite(a)]
        print(f"    {nm if tag=='r95' else '':>44s} | {tag:>5s} {len(a):6d} {len(a)/FS:6.1f} "
              f"{np.percentile(a,50):7.1f} {np.percentile(a,90):8.1f} "
              f"{np.percentile(a,99):8.1f} {a.max():8.1f}")
        out.setdefault("B_protected_slow", []).append(
            dict(stratum=nm, route=tag, n=int(len(a)), p50=float(np.percentile(a, 50)),
                 p90=float(np.percentile(a, 90)), p99=float(np.percentile(a, 99)),
                 max=float(a.max())))

# ======================================================================================
print("\n" + "=" * 104)
print("C. EXPOSURE CONFOUND -- the two drives were NOT driven the same way.  State it.")
print("=" * 104)
print(f"    {'quantity':>34s} {'r95 (V101)':>14s} {'r85 (V100)':>14s} {'ratio':>8s}")
for nm, a, b in (("engaged seconds", lat.sum() / FS, lat85.sum() / FS),
                 ("speed p50 km/h", np.median(vk[lat]), np.median(vk85[lat85])),
                 ("speed p90 km/h", np.percentile(vk[lat], 90), np.percentile(vk85[lat85], 90)),
                 ("|driver torque| p50 ct", np.median(np.abs(tq[lat])),
                  np.median(np.abs(tq85[lat85]))),
                 ("|sustained driver tq| p50 ct", np.median(ts[lat]), np.median(ts85[lat85])),
                 ("hands-light duty (<150 ct)", np.mean(ts[lat] < 150),
                  np.mean(ts85[lat85] < 150)),
                 ("|steer angle| p50 deg", np.median(np.abs(ang[lat])),
                  np.median(np.abs(np.asarray(R85["ang"], float)[lat85]))),
                 ("|cmd| p50 ct", np.median(np.abs(sc_tq)[lat]), np.median(np.abs(sc85)[lat85])),
                 ("|cmd| rail duty @4096", np.mean(np.abs(sc_tq)[lat] >= 4095),
                  np.mean(np.abs(sc85)[lat85] >= 4095))):
    print(f"    {nm:>34s} {a:14.4f} {b:14.4f} {a/max(b,1e-9):8.2f}")
    out.setdefault("C_exposure", []).append(dict(name=nm, r95=float(a), r85=float(b)))

(L.CACHE / "r95_b6_addendum.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_b6_addendum.json'}")
