#!/usr/bin/env python3
"""studies/sessions/v70/v70_plot_data.py -- emit the plotting dataset for "what V70 does", from the image bytes.

Every multiplier here is `slope()` = gain / 2^sar, so V62/V65's `sar 0x9` route and V67/V68's
scalar-arm route are priced on the SAME scale as V69/V70's surface route. Nothing is transcribed
from a design doc; the Build class mirrors FUN_0003aa2c / FUN_0003ad74 instruction-for-instruction.

Emits _scratch/out/_v70_plot_data.json next to this file.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
from pathlib import Path

import v70_rate_lane_gain_model as M

ROOT = M.ROOT
OUT = Path(__file__).resolve().parents[3] / "_scratch/out/_v70_plot_data.json"

# ---------------------------------------------------------------------------------------------
# builds
# ---------------------------------------------------------------------------------------------
imgs = {"stock": (ROOT / "stock_fw_dump" / "code.bin").read_bytes()}
for v in ("v62", "v67", "v68", "v69", "v70"):
    imgs[v] = (ROOT / f"_{v}_plain_image.bin").read_bytes()
B = {k: M.Build(k, v) for k, v in imgs.items()}

# The four arms we contrast. V67 and V68 share the control path (gate fb + arm 5244); assert it
# rather than assume it, then carry one of them.
assert (B["v67"].buf[M.GATE_BYTE], B["v67"].arm2) == (B["v68"].buf[M.GATE_BYTE], B["v68"].arm2)
assert B["v70"].buf[M.GATE_BYTE] == 0xC5 and B["v70"].arm2 == 512, "V70 must be gateless, arm stock"
assert B["v70"].sar == 10 and B["v69"].sar == 10
assert B["v62"].sar == 9, "V62 is the sar route"
assert B["v69"].Y[2] == B["stock"].Y[2] and B["v69"].Y[3] == B["stock"].Y[3]
assert B["v70"].Y[2] == B["stock"].Y[2] and B["v70"].Y[3] == B["stock"].Y[3]

ARMS = [
    ("stock", "stock", "Stock"),
    ("V62 / V65", "v62", "flat 2x (sar route)"),
    ("V67 / V68", "v67", "scalar arm 5244"),
    ("V69", "v69", "speed surface x4"),
    ("V70", "v70", "speed surface x2"),
]

KMH = M.SPEED_CTS_PER_KMH


def mult(name, kmh, rate):
    """delivered r24 slope, relative to stock at the same operating point."""
    sc = int(round(kmh * KMH))
    num = B[name].slope(sc, rate, engaged=True)
    den = B["stock"].slope(sc, rate, engaged=True)
    return num / den


# ---------------------------------------------------------------------------------------------
# operating points -- the SAME ones builds/v50_v79/build_v70_tva.py prices, so these numbers are comparable to
# the build note rather than a second opinion at a different speed.
# ---------------------------------------------------------------------------------------------
CREEP_KMH, HWY_KMH = 7.2, 93.0
OP = {"grind1": 603, "grind2_creep": 1206, "grind2_hwy": 170}

data = {}

# --- Panel A: multiplier vs vehicle speed, at grind #1's rate operating point -------------------
speeds = [round(0.5 * i, 1) for i in range(0, 201)]
data["speed_axis"] = {
    "rate_key": OP["grind1"],
    "kmh": speeds,
    "series": {lab: [round(mult(k, s, OP["grind1"]), 4) for s in speeds] for lab, k, _ in ARMS},
}

# --- Panel B: multiplier vs rate key, at creep -------------------------------------------------
rates = list(range(0, 2001, 5))
data["rate_axis"] = {
    "kmh": CREEP_KMH,
    "rate_key": rates,
    "series": {lab: [round(mult(k, CREEP_KMH, r), 4) for r in rates] for lab, k, _ in ARMS},
}

# --- the headline table: three operating points x five arms ------------------------------------
POINTS = [
    ("grind #1 — creep 7.2 km/h, rateKey 603", CREEP_KMH, OP["grind1"]),
    ("grind #2 creep — 7.2 km/h, rateKey 1206", CREEP_KMH, OP["grind2_creep"]),
    ("engaged highway — 93 km/h, rateKey 170", HWY_KMH, OP["grind2_hwy"]),
]
data["table"] = [
    {"point": nm, "kmh": s, "rate": r,
     "values": {lab: round(mult(k, s, r), 3) for lab, k, _ in ARMS}}
    for nm, s, r in POINTS
]

# --- grind #1 dose-response, median e_18-22 engaged creep (HANDOFF 2026-08-04 §2) ---------------
# Cross-route medians WITHOUT covariate matching -- carried with that caveat attached.
data["dose_response"] = [
    {"dose": 0.0, "build": "V61", "median_e": 2501, "measured": True},
    {"dose": 1.0, "build": "stock", "median_e": 879, "measured": True},
    {"dose": 2.0, "build": "V62 / V65", "median_e": 168, "measured": True},
    {"dose": 2.0, "build": "V67 / V68 (gated)", "median_e": 109, "measured": True, "gated": True},
    {"dose": 4.0, "build": "V69", "median_e": 746, "measured": True},
]
data["v70_dose_at_grind1"] = round(mult("v70", CREEP_KMH, OP["grind1"]), 3)

# --- grind #2: where the bursts actually live on the rate axis ---------------------------------
# Kd=2 pool burst RATE per second, per rateKey stratum, from _scratch/out/_r4f_rate_axis.json (r4f_rate_axis_
# grind2.py). The [0,400) stratum is absent from that table because Kd=2 produced ZERO bursts there
# (0 of 96 windows) -- recorded explicitly rather than left as a missing row.
_ra = json.load(open(Path(__file__).resolve().parents[3] / "_scratch/out/_r4f_rate_axis.json"))
sp = _ra["stratum_power"]
data["grind2_strata"] = [
    {"lo": 0, "hi": 400, "kd2_rate_on": 0.0, "kd2_rate_off": 0.0, "zero_by_construction": True},
    {"lo": 400, "hi": 1126,
     "kd2_rate_on": sp["400-1126|LKAS ON|V69 r4f  *** THIS ROUTE ***"]["kd2_rate"],
     "kd2_rate_off": sp["400-1126|LKAS OFF|V69 r4f  *** THIS ROUTE ***"]["kd2_rate"]},
    {"lo": 1126, "hi": 1400,
     "kd2_rate_on": sp["1126-1400|LKAS ON|V69 r4f  *** THIS ROUTE ***"]["kd2_rate"],
     "kd2_rate_off": sp["1126-1400|LKAS OFF|V69 r4f  *** THIS ROUTE ***"]["kd2_rate"]},
    {"lo": 1400, "hi": 2000,
     "kd2_rate_on": sp["1400-inf|LKAS ON|V69 r4f  *** THIS ROUTE ***"]["kd2_rate"],
     "kd2_rate_off": sp["1400-inf|LKAS OFF|V69 r4f  *** THIS ROUTE ***"]["kd2_rate"]},
]
# the dose each arm delivers in each stratum, at the stratum midpoint
for st in data["grind2_strata"]:
    mid = (st["lo"] + st["hi"]) // 2
    st["mid"] = mid
    st["dose"] = {lab: round(mult(k, CREEP_KMH, mid), 3) for lab, k, _ in ARMS}
data["grind2_burst_census"] = {"total_kd2_bursts": 24, "at_or_above_1126": 19,
                               "below_400": 0, "windows_below_400": 96}

# --- raw surface bytes, so the plot can be checked against the image ---------------------------
data["records"] = {
    n: {"X": B[n].X, "Y": B[n].Y, "sar": B[n].sar,
        "gate": "gp-0x6806" if B[n].gate_live else "gp-0x683c (dead)", "arm2": B[n].arm2}
    for n in ("stock", "v62", "v67", "v69", "v70")
}
data["cross_axis_counts"] = B["stock"].cross
data["cross_axis_kmh"] = [round(c / KMH, 2) for c in B["stock"].cross]

# --- rail headroom: smallest |dtorque| that clips the +/-8192 lane clamp ------------------------
# Priced at PEAK gain (rateKey <= 400, where every build's gain is largest) -- the worst case, and
# the same point builds/v50_v79/build_v70_tva.py quotes. Pricing it at rateKey 603 instead flatters every build.
data["rail"] = {lab: B[k].rail_dt(0, 0, engaged=True) for lab, k, _ in ARMS}
data["rail_note"] = {"recorded_max_dtorque": 839, "v69_flight_max_dtorque": 633.9,
                     "priced_at": "peak gain, rateKey <= 400"}
assert data["rail"]["V69"] == 683, data["rail"]          # the build record's own figure
assert data["rail"]["V70"] == 1366, data["rail"]

json.dump(data, open(OUT, "w"), indent=1)

# ---------------------------------------------------------------------------------------------
print("=" * 92)
print("DELIVERED r24 MULTIPLIER vs STOCK  (slope = gain / 2^sar; engaged)")
print("=" * 92)
hdr = f"{'operating point':<40}" + "".join(f"{lab:>13}" for lab, _, _ in ARMS)
print(hdr)
print("-" * len(hdr))
for row in data["table"]:
    print(f"{row['point']:<40}" + "".join(f"{row['values'][lab]:>13.2f}" for lab, _, _ in ARMS))
print()
print(f"{'rail |dtorque| at grind #1':<40}" +
      "".join(f"{str(data['rail'][lab]):>13}" for lab, _, _ in ARMS))
print(f"{'':<40}  (recorded max 839; V69 flight max 633.9)")
print()
print("speed cross-axis 0xC6010 =", data["cross_axis_counts"], "counts =",
      data["cross_axis_kmh"], "km/h")
for n in ("stock", "v69", "v70"):
    print(f"  {n:<6} record0 X={B[n].X[0]} Y={B[n].Y[0]}   record1 Y={B[n].Y[1]}")
print(f"\nwrote {OUT}")
