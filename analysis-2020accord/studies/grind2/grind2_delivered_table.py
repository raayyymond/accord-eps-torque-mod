#!/usr/bin/env python3
"""REBUILD THE TWO-LANE GRIND-#2 TABLE ON **DELIVERED** MULTIPLIERS, NOT NOMINAL ONES.

Answers, from the shipped images only:
  §1  what each build's rate lane actually contains (gate / arms / both `sar` sites)
  §2  are the gain_A (r26) and gain_B (r24) FALLBACK surfaces edited, and at WHICH modes
  §3  the delivered r24 / r26 multipliers vs stock, ENGAGED, at the operating point where every
      grind-#2 burst in the corpus actually lives (creep, high rate) -- and at rateKey 100 for
      contrast with the numbers already on record
  §4  the two-lane table rebuilt

Usage:  python studies/grind2/grind2_delivered_table.py
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

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_delivered_lib as D  # noqa: E402

ORDER = ["stock", "V58", "V59", "V61", "V64", "V62", "V65", "V67", "V68", "V69", "V70",
         "V71A", "V71B", "V71C", "V72", "V73", "V74", "V75", "V76"]
OUT = {}


def hdr(s):
    print("\n" + "=" * 118 + f"\n{s}\n" + "=" * 118)


B = D.load_all()
st = B["stock"]

# ================================================================= §1 ============================
hdr("§1  WHAT EACH IMAGE CONTAINS -- every value byte-read LE. `sar 9` = x2 on that lane, ALWAYS "
    "(mode-proof).\n    gate 0xFB = repointed to gp-0x6806 (LKAS-applying); 0xC5 = the DEAD cell "
    "gp-0x683c => the arms NEVER fire.")
print(f"   {'build':6s} {'route':7s} {'sar24':>5s} {'sar26':>5s} {'gate':>5s} {'r24 arm':>8s} "
      f"{'r26 arm':>8s}   note")
for n in ORDER:
    b = B[n]
    note = []
    if b.sar24 == 9:
        note.append("BOTH sar x2")
    if b.gated:
        note.append(f"GATED: r24<-{b.arm24_gate}, r26<-{b.arm26_gate} when engaged")
    else:
        note.append("ungated => arms inert")
    print(f"   {n:6s} {D.FLOWN.get(n, '-'):7s} {b.sar24:5d} {b.sar26:5d} "
          f"{'0x%02X' % b.gate_byte:>5s} {b.arm24_gate:8d} {b.arm26_gate:8d}   {'; '.join(note)}")

# ================================================================= §2 ============================
hdr("§2  THE FALLBACK SURFACES -- which builds edited them, and at which MODES.\n"
    "    gain_B (r24) is MODE-INDEXED [mode*4] => an edit at mode 10/11 is INERT on a mode-24/26 car."
    "\n    gain_A (r26) is NOT indexed (four hard-coded records) => an edit there is ALWAYS in force.")
print(f"   {'build':6s} | gain_B Y rows, mode 24 (manual) / mode 26 (engaged) vs stock | gain_A Y "
      f"rows vs stock")
for n in ORDER:
    b = B[n]
    dm = [i for i in range(4) if b.recB[24][1][i] != st.recB[24][1][i]]
    de = [i for i in range(4) if b.recB[26][1][i] != st.recB[26][1][i]]
    d10 = [i for i in range(4) if b.recB[10][1][i] != st.recB[10][1][i]]
    da = [i for i in range(4) if b.recA[1][i] != st.recA[1][i]]
    tag = []
    tag.append(f"B m24{'=stock' if not dm else ' EDITED rec' + str(dm)}")
    tag.append(f"B m26{'=stock' if not de else ' EDITED rec' + str(de)}")
    tag.append(f"B m10{'=stock' if not d10 else ' EDITED rec' + str(d10) + ' <- INERT'}")
    tag.append(f"A{'=stock' if not da else ' EDITED rec' + str(da) + ' <- IN FORCE'}")
    print(f"   {n:6s} | " + " | ".join(tag))
print(f"\n   stock gain_B mode-24 record ptrs: {[hex(p) for p in st.recB[24][2]]}")
print(f"   stock gain_B mode-26 record ptrs: {[hex(p) for p in st.recB[26][2]]}")
print(f"   stock gain_B mode-10 record ptrs: {[hex(p) for p in st.recB[10][2]]}")
print(f"   stock gain_A record ptrs        : {[hex(p) for p in st.recA[2]]}")
print(f"   ⇒ mode 24/26 and mode 10 select {'THE SAME' if st.recB[24][2] == st.recB[10][2] else 'DIFFERENT'} "
      f"gain_B records on stock.")
for m in (24, 26, 10):
    print(f"   stock gain_B m{m}: X={st.recB[m][0]}\n{'':21s}Y={st.recB[m][1]}")
print(f"   stock gain_A   : X={st.recA[0]}\n{'':21s}Y={st.recA[1]}")
print(f"   speed cross-axis 0xC6010 = {st.cross} counts = "
      f"{[round(c / 64.0, 1) for c in st.cross]} km/h")

# ================================================================= §3 ============================
# The burst-producing cell, verified in `studies/sessions/r59/d4_r59_grind2.py` §4: 20 of 25 V62/V65 bursts and 3 of 3
# V71C creep bursts sit at rate index >= 1400. Creep is 0.3-4 m/s = 1.1-14.4 km/h.
CREEP_KMH = [0, 5, 10, 14]
RATE_PTS = [(100, "plateau"), (400, "plateau edge"), (1400, "HIGH-RATE edge"), (2000, "high rate"),
            (3000, "high rate"), (13001, "fold -> MAX gain")]

hdr("§3  DELIVERED MULTIPLIER vs STOCK, **ENGAGED** (mode 26), across the creep band.\n"
    "    Each cell is (r24 x , r26 x). 1.000/1.000 means the build was byte-stock in that arm.")
for rk, lab in RATE_PTS:
    print(f"\n   --- rateKey (gp-0x6ac0) = {rk}  [{lab}] "
          f"= {rk / 4.7121:.0f} column deg/s ---")
    print(f"   {'build':6s} " + "".join(f"{str(k) + ' km/h':>21s}" for k in CREEP_KMH))
    for n in ORDER:
        row = ""
        for kmh in CREEP_KMH:
            a, c = D.delivered(B[n], st, kmh, rk, engaged=True)
            row += f"{a:9.3f} /{c:8.3f}  "
        print(f"   {n:6s} {row}")

hdr("§3b  DELIVERED MULTIPLIER vs STOCK, **MANUAL** (mode 24) -- the driver-only arm.")
for rk, lab in [(100, "plateau"), (2000, "high rate")]:
    print(f"\n   --- rateKey = {rk} [{lab}] ---")
    print(f"   {'build':6s} " + "".join(f"{str(k) + ' km/h':>21s}" for k in CREEP_KMH))
    for n in ORDER:
        row = ""
        for kmh in CREEP_KMH:
            a, c = D.delivered(B[n], st, kmh, rk, engaged=False)
            row += f"{a:9.3f} /{c:8.3f}  "
        print(f"   {n:6s} {row}")

# ================================================================= §4 ============================
# One representative operating point for the table: the burst cell's own centre.
OP_KMH, OP_RK = 5, 2000
hdr(f"§4  THE TWO-LANE TABLE REBUILT ON DELIVERED VALUES, at the burst cell's centre "
    f"({OP_KMH} km/h, rateKey {OP_RK}).\n    'nominal' = the number `docs/STATE.md` tabulates.")
NOMINAL = {"stock": (1.000, 1.000), "V69": (1.000, 1.000), "V70": (1.000, 1.000),
           "V71B": (1.000, 2.000), "V62": (3.414, 2.000), "V65": (3.414, 2.000),
           "V71C": (3.414, 1.500), "V67": (3.414, 0.250), "V68": (3.414, 0.250),
           "V72": (3.414, 0.250)}
print(f"   {'build':6s} {'route':7s} | {'DELIVERED eng r24':>18s} {'DELIVERED eng r26':>18s} | "
      f"{'DELIVERED man r24':>18s} {'DELIVERED man r26':>18s} | {'NOMINAL r24':>12s} "
      f"{'NOMINAL r26':>12s}")
for n in ORDER:
    ea, ec = D.delivered(B[n], st, OP_KMH, OP_RK, engaged=True)
    ma, mc = D.delivered(B[n], st, OP_KMH, OP_RK, engaged=False)
    nom = NOMINAL.get(n)
    ns = f"{nom[0]:12.3f} {nom[1]:12.3f}" if nom else f"{'-':>12s} {'-':>12s}"
    print(f"   {n:6s} {D.FLOWN.get(n, '-'):7s} | {ea:18.3f} {ec:18.3f} | {ma:18.3f} {mc:18.3f} | {ns}")
    OUT[n] = dict(route=D.FLOWN.get(n), eng_r24=ea, eng_r26=ec, man_r24=ma, man_r26=mc,
                  nominal=nom, sar24=B[n].sar24, sar26=B[n].sar26, gated=B[n].gated,
                  arm24=B[n].arm24_gate, arm26=B[n].arm26_gate)

(HERE / "_scratch/out/_grind2_delivered_table.json").write_text(json.dumps(OUT, indent=1), encoding="utf-8")
print(f"\nwrote {HERE / '_scratch/out/_grind2_delivered_table.json'}")
