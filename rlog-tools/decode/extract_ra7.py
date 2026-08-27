#!/usr/bin/env python3
r"""Extract the V107 drive route(s) into `analysis-2020accord/_scratch/cache/r<key>/`.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly the `decode/extract_ra6.py` pattern: add a row to
`decode_v84_probe_r6d.ROUTES`, then call `extract_r7d.extract_route()` -- the SAME code that wrote
every cache since `_scratch/cache/r6d/`.

===================================================================================================
ROUTE(S) == V107.  V106 BASE + 19 BYTES IN 6 RUNS.  CAVE BYTE-IDENTICAL.  427 TAP RE-AIMED.
===================================================================================================
Byte diff V106 -> V107, MEASURED here (not quoted) by differencing the two plain images:

    0x55DF2  2 B   7a94 -> d493     E2  427 tap source:  gp-0x6b86 -> gp-0x6c2c
    0x55E10  1 B   a4   -> a3       E2  427 tap scaler:  sar 4 -> sar 3
    0xD7A5E  4 B   cebcf6e8 -> 40a280c1   E1 mode 26 Y[1],Y[2]: (-17202,-5898) -> (-24000,-16000)
    0xD7A6E  4 B   cebcf6e8 -> 40a280c1   E1 mode 27 Y[1],Y[2]: same
    0xC4FFC  4 B   CRC trailer
    0xD7FFC  4 B   CRC trailer

🛑 **Y[0] IS BYTE-IDENTICAL** -- the E1 runs start at 0xD7A5E, not 0xD7A5C, so V106's -29490 stands
   at the creep knot BY CONSTRUCTION.  Creep clamp duty and the relay index are unchanged.
🛑 **THE CAVE IS BYTE-IDENTICAL TO V106** (verified: `v106[0xC4B34:0xC4B34+0xA4] == v107[...]`), so
   **every rung means exactly what it meant on `a6` and `a5`**:
        byte4 b7 0x80 = gp-0x6b4c < 0                 *** NOT the sign of the 427 cell ***
        byte4 b6 0x40 = |gp-0x6b94| >= |gp-0x4f64|    GOVERNOR CLIP DUTY  (a6 duty was 0.0000)
        byte4 b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|    COMPARATOR: friction vs inertia
                                                      *** OPERAND B IS THE CELL E1 RESHAPES ***
        byte4 b4 0x10 = gp-0x6ada < 0                 sign of r24
        byte4 b3 0x08 = gp-0x3680 < 0                 D_state (PID D-term) SIGN
        byte7[7:6]    = 3                             SAME CODE as V101..V106

===================================================================================================
🛑 THE 427 PACKER -- VERIFIED FROM THE BINARY, AND THE BUILDER'S PRINTED SCALE IS 5x WRONG
===================================================================================================
`FUN_00055d80`, disassembled from `code.bin` (stock; E2 moves only the disp16 and the imm5):

    00055df0  ld.h   -0x6c18, gp, r6     2437 e893   <- E2 patches e893 -> d493  (gp-0x6c2c)
    00055df4  jarl   0x00049a5a, lp                  <- abs()      [verified: returns -x for x<0]
    00055dfa  ori    0xffff, r0, r7                  <- r7 = 65535, the min() ceiling
    00055dfe  jarl   0x00049a78, lp                  <- min(r6, 65535)   [verified: returns min]
    00055e06  mul    0x5, r6, r0         e537 4002   <- *** THE x5.  Honda's, untouched by E2. ***
    00055e0a  movea  0x3ff, r0, r8                   <- clamp hi = 1023
    00055e0e  mov    0x0, r7                         <- clamp lo = 0
    00055e10  sar    0x3, r6             a332        <- E2 patches the low byte a4 -> a3
    00055e12  jarl   0x00049a90, lp                  <- clamp(x, 0, 0x3ff)

    =>  wire   = clamp( (min(|gp-0x6c2c|, 65535) * 5) >> 3, 0, 0x3FF )
        counts = wire * 2**3 / 5 = wire * 1.6
        full scale = 1023 * 1.6 = 1636.8 counts of |gp-0x6c2c|

⚠ **DEFECT IN `build_v107_tva.py` (reported, NOT patched here).**  Its console print at the E2 step
  says `LSB = {1 << sar} counts` / `full scale {(1 << sar) * 1023}`, i.e. **8 counts / 8184 counts**.
  It omits the `mul 0x5` and is therefore **5x too large**.  The print is cosmetic -- the builder
  writes the correct bytes and the V107 image hashes to the value STATE records -- but anything
  sized off that printed full scale would be 5x out.  The 2**sar/5 form is what every prior route
  used (`extract_r7d.WIRE_SCALE`: 7d 2/5 @ sar 1, 77/78 8/5 @ sar 3, 79 16/5 @ sar 4).
⚠ **`min(|cell|, 65535)` is NOT a live cap** for an int16 cell, so percentiles below the field rail
  are clean; the only saturation is the 10-bit wire itself at 1636.8 counts.

===================================================================================================
🛑🛑 TRAPS -- REPRODUCED FROM `ra6`, DELIBERATELY, PLUS ONE NEW TO V107
===================================================================================================
* **NO SIGN BIT FOR THE 427 CELL.**  `byte4 b7` is the sign of `gp-0x6b4c`, NOT of `gp-0x6c2c`.
  This cache emits **`x6c2c_mag` -- UNSIGNED, RECTIFIED counts** (the `abs()` above) and emits the
  sign bit only under its true name `sgn_6b4c`.  **NO signed `x6c2c` key exists.  Do not create one.**
* **`raw14` OFF-BY-ONE:** `t == raw14_t[1:]` and `probe == raw14_b4[1:]`.
  **SAFE PAIRS: `(t, probe)` or `(raw14_t, raw14_b4)`.  NEVER `(t, raw14_b4)`.**
* **0x18F STALENESS IS 12.5 ms, NOT 10.**  Nyquist on 0x18F is 50.57 Hz.  **CAN CANNOT SEE 100 Hz**,
  so no CAN column in this cache can address the operator's several-hundred-Hz grinding.  Only
  `rawAudioData` (16 kHz) can -- see `audio_plan()`.
* **SEGMENT DISCOVERY IS GLOB-BASED AND ASSERTED.**  `extract_audio.py:segments()` walks indices
  until the first absent one and stops, which silently truncated a whole route once.  `discover()`
  here globs, sorts numerically, and **asserts the index set is contiguous from 0**.
* 🆕 **THE SCALER BYTE IS NOT A WITNESS ON V107.**  V107's `0x55E10 = a3` is *stock's own value*
  (V104/V105/V106 were the deviation at `a4`).  Only the disp16 `d4 93` is unique to V107, and that
  is an image byte, not a wire byte.  ⇒ **The identity leg must come from the wire DISTRIBUTION.**

===================================================================================================
IDENTITY -- WHAT SEPARATES V107 FROM V106 IN THE TELEMETRY
===================================================================================================
  LEG 1  byte7[7:6]==3 AND b3 varies   -- separates V103..V107 from V101/V102.  WEAK, carried.
  LEG 2  🆕 **THE TAP MOVED -- THE STRUCTURAL LEG.**  The 427 lane now carries a RAW first-difference
         of motor rate (`gp-0x6c2c`) at sar 3, where a6 carried a NOTCH-FILTERED lane (`gp-0x6b86`)
         at sar 4.  Different cell, different shaping, different LSB.  a6's own reference:
             nonzero 0.7207   distinct 914   p50 2   p90 53   p99 616   max 1023   sat 0.1687 %
         A V107 wire that matches a6's shape within noise is EVIDENCE THE TAP DID NOT MOVE -- i.e.
         the log is not V107.  This is the leg the orchestrator asked to be established from the
         wire rather than from a doc.
  LEG 3  `b5` duty at MATCHED alpha, engaged vs manual -- the dose proof for the reshape.
         🛑 A POOLED duty is the WRONG estimator (the K*alpha product is invariant to K); a6 closed
         RULE 7 only at matched alpha.  `b5` pooled on a6 was 0.2436.
🛑 E1 raises |Y| at the 20 km/h and >=90 km/h knots ONLY.  Below ~20 km/h V107 IS V106, so a
  low-speed-only drive cannot witness E1 at all -- see `census()`'s speed exposure gate.

Usage:
    python decode/extract_ra7.py                 # discover + full pipeline on every new route
    python decode/extract_ra7.py discover        # just list what is on disk (SAFE, no cache write)
    python decode/extract_ra7.py census          # the Step-2 report
    python decode/extract_ra7.py extract|derive|identity|lane427|audio_plan
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  Put EVERY `.pkgroot` kit root and every code
# subfolder under each on sys.path, so those imports resolve from any CWD.
#
# 🛑 WALKS **BOTH** ROOTS ON PURPOSE.  The stock block walks only the root above THIS file
# (`rlog-tools/`) and then adds `analysis-2020accord/` flat.  Since the 2026-08-26 reorg that is not
# enough: the import chain `extract_r7d -> decode_v84_probe_r6d -> compare_v75_v76_v80_grind ->
# _grind2_lib` needs `analysis-2020accord/lib/`, where the reorg moved `_grind2_lib.py` from
# `analysis-2020accord/`.  With the stock block that import raises ModuleNotFoundError and the whole
# extractor family is dead on arrival -- `extract_ra6.py` included.  Reported, NOT patched there.
import os as _os, sys as _sys
_here = _os.path.dirname(_os.path.abspath(__file__))
_roots, _c = [], _here
while True:
    if _os.path.isfile(_os.path.join(_c, ".pkgroot")):
        _roots.append(_c)
    _n = _os.path.dirname(_c)
    if _n == _c:
        break
    _c = _n
if not _roots:
    raise RuntimeError("no .pkgroot marker above " + __file__)
# every sibling kit root too (analysis-2020accord/ when we started in rlog-tools/, and vice versa)
_top = _os.path.dirname(_roots[0])
for _e in sorted(_os.listdir(_top)):
    _cand = _os.path.join(_top, _e)
    if _os.path.isfile(_os.path.join(_cand, ".pkgroot")) and _cand not in _roots:
        _roots.append(_cand)
_p = []
for _r in _roots:
    _p.append(_r)
    for _b, _ds, _fs in _os.walk(_r):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _here, _roots, _c, _n, _top, _e, _cand, _p, _r, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402
import rlog_parse        # noqa: E402

D = X.D
RLOGS = ROOT / "analysis-2020accord" / "rlogs"

# =====================================================================================
# 🛑🛑 THE ROUTE COUNTER RESET.  DO NOT ORDER BUILDS BY ROUTE NUMBER.
# =====================================================================================
# The device was REFLASHED between `a6` (V106) and these drives: the route counter went
# BACKWARDS from 0xa6 to 0x1b/0x1e, the SSH host key regenerated, and authorized_keys was
# wiped.  Consequences, all live:
#
#  1. **"newest = highest counter" IS FALSE.**  Sorting numerically puts these V107 drives
#     BEFORE the stock baseline.  This module orders by **log-file mtime** and states so.
#  2. **THERE IS A REAL COLLISION.**  Counter `0000001b` exists TWICE on disk with different
#     hashes:
#         0000001b--d2abf1af1c   1 segment,   2026-07-27   OLD, pre-reflash
#         0000001b--d7c81cf9b5   2 segments,  2026-08-26   *** THIS IS V107 ***
#     Keying a cache on the bare counter would silently MERGE TWO DRIVES FROM DIFFERENT
#     FIRMWARE BUILDS.  Every key below is therefore the **full `counter--hash`**, and the
#     explicit map is the ONLY route selector -- there is no numeric threshold any more.
#     (An old `0000001c--ade8fd5b4a` also exists; the NEW batch has no 1c/1d.)
#  3. Cache dirs are named `r1b` / `r1e` for continuity with the kit's convention, but
#     **THESE ARE V107** -- the newest builds in the kit, not old ones.  A low route number
#     no longer implies an old build.
# =====================================================================================
V107_ROUTES = {
    "1b": "75604b0a432fdc89_0000001b--d7c81cf9b5",   # 2 segments,  ~2 min
    "1e": "75604b0a432fdc89_0000001e--28ef595061",   # 23 segments, ~23 min  <- the real drive
}
SEG_RE = re.compile(r"^(?P<dongle>[0-9a-f]+)_(?P<route>(?P<ctr>[0-9a-f]{8})--[0-9a-f]+)"
                    r"--(?P<seg>\d+)--rlog\.zst$")

# ---- V107 427 spec, VERIFIED from the image (see the module docstring).
SAR = 3
COUNTS_PER_LSB = (1 << SAR) / 5.0                      # 1.6 counts per wire LSB
WIRE_SAT_FIELD = 1023                                  # the 10-bit CAN field
SAT_CELL_COUNTS = WIRE_SAT_FIELD * COUNTS_PER_LSB      # 1636.8 counts of |gp-0x6c2c|
MIN_CEILING = 65535                                    # `ori 0xffff` -- not live for an int16 cell

M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
IDENT_MASK = 0xC0

# ---- route `a6` (V106) reference, read from its own cache, for LEG 2 and LEG 3.
RA6 = dict(nonzero=0.7207, distinct=914, p50=2.0, p90=53.0, p99=616.0, sat=0.001687,
           b5_pooled=0.2436, b6_pooled=0.0000, b7_pooled=0.2650, b4_pooled=0.3844,
           b3_pooled=0.4647)

# ---- the operator's symptom windows are in mph; bin so they are readable in BOTH units.
#      grinding 15-40 mph = 24.1-64.4 km/h · drop-off <=5-6 mph = <=8-10 km/h · hard turn 50 mph = 80
SPEED_BINS = [(0, 10), (10, 25), (25, 40), (40, 65), (65, 90), (90, 1e9)]
SPEED_LAB = ["<10", "10-25", "25-40", "40-65", "65-90", "90+"]
SPEED_MPH = ["<6.2", "6.2-15.5", "15.5-24.9", "24.9-40.4", "40.4-55.9", "55.9+"]

DERIVED = ["v107_b7", "v107_b6", "v107_b5", "v107_b4", "v107_b3",
           "mag427", "sgn_6b4c", "x6c2c_mag", "v_rear", "lp_yaw"]

_TAPPED_READ = rlog_parse.read_messages
MISSING_SEGMENTS = []
LP = {"t": [], "z": []}


# ======================================================================================
#  DISCOVERY -- glob-based, contiguity ASSERTED.  Never index-walk-until-absent.
# ======================================================================================
def discover(verbose=True):
    """Register the V107 routes from the EXPLICIT map.  Returns {key: (prefix, nseg)}.

    🛑 Selection is by the explicit `V107_ROUTES` map keyed on the full `counter--hash`, NOT by a
    route-number threshold: the counter reset from 0xa6 to 0x1b/0x1e and `0000001b` now collides
    with a pre-reflash drive of the same number.  Ordering, where it matters, is by log mtime.
    🛑 Globs and asserts contiguity rather than walking indices until one is absent, which is the
    failure that silently dropped a whole route once (`extract_audio.py:segments()`).
    """
    found = {}
    for p in RLOGS.glob("*--rlog.zst"):
        m = SEG_RE.match(p.name)
        if not m:
            continue
        found.setdefault(f"{m.group('dongle')}_{m.group('route')}", []).append(int(m.group("seg")))

    out = {}
    for key, prefix in V107_ROUTES.items():
        assert prefix in found, (
            f"route {key} ({prefix}) has no rlog segments in {RLOGS}. Do not substitute a "
            f"same-numbered route -- 0000001b exists twice with different hashes.")
        segs = sorted(found[prefix])
        expected = list(range(len(segs)))
        contiguous = segs == expected
        cdir = f"analysis-2020accord/_scratch/cache/r{key}"
        D.ROUTES[key] = (prefix, len(segs), cdir, f"r{key}s", f"r{key}", "V107")
        X.WIRE_SCALE[key] = COUNTS_PER_LSB
        X.WIRE_SOURCE[key] = ("gp-0x6c2c (RAW motor-rate derivative -- the inertia term's INPUT, "
                              "pre-gain, pre-clamp), sar 3  [V107 E2 re-aim from gp-0x6b86/sar 4]")
        X.BITNAMES[key] = {
            "b7_sign_6b4c_neg__NOT_THE_427_CELL": M_B7,
            "b6_CMP_abs6b94_ge_abs4f64__GOVERNOR_CLIP": M_B6,
            "b5_CMP_absfriction_ge_absinertia__OPERAND_B_IS_RESHAPED": M_B5,
            "b4_sign_r24_neg": M_B4,
            "b3_sign_Dstate_neg": M_B3,
        }
        out[key] = (prefix, len(segs))
        if verbose:
            flag = "" if contiguous else f"  🛑 NON-CONTIGUOUS: have {segs}, expected {expected}"
            print(f"  route {key} (V107)  {prefix}  {len(segs)} segments on disk, "
                  f"indices {segs[0]}..{segs[-1]}{flag}")
        assert contiguous, (
            f"route {key}: segment indices {segs} are not contiguous from 0. The extractor builds "
            f"paths as range(nseg) and would SILENTLY read the wrong set. Fetch the missing "
            f"segments before caching.")
    return out


def _read_guarded(path):
    p = Path(path)
    if not p.exists():
        MISSING_SEGMENTS.append(p.name)
        print("  segment file ABSENT, skipped: %s" % p.name, flush=True)
        return
    for evt in _TAPPED_READ(path):
        try:
            if evt.which() == "livePose":
                LP["t"].append(evt.logMonoTime * 1e-9)
                LP["z"].append(float(evt.livePose.angularVelocityDevice.z))
        except Exception:
            pass
        yield evt


rlog_parse.read_messages = _read_guarded


def extract_route(route):
    MISSING_SEGMENTS.clear()
    LP["t"].clear()
    LP["z"].clear()
    rep = X.extract_route(route)
    rep["segments_absent"] = list(MISSING_SEGMENTS)
    rep["livePose_samples"] = len(LP["t"])
    print("\n  segments absent from disk: %d   livePose samples: %d"
          % (len(MISSING_SEGMENTS), len(LP["t"])))
    assert not MISSING_SEGMENTS, (
        f"route {route}: {MISSING_SEGMENTS} were absent. The cache would be a partial drive with "
        f"no marker in the npz. Fetch them and re-run.")
    cdir = ROOT / D.ROUTES[route][2]
    cdir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cdir / (D.ROUTES[route][4] + "_lp.npz"),
                        t=np.array(LP["t"], float), z=np.array(LP["z"], float))
    return rep


def derive(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / (stem + ".npz")
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the SAFE pairing contract is broken"
    for nm, m in (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3)):
        z["v107_" + nm] = ((p & m) != 0).astype(float)

    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    z["mag427"] = mag
    # 🛑 b7 is gp-0x6b4c's sign, NOT gp-0x6c2c's.  Named for what it is; never applied to mag427.
    z["sgn_6b4c"] = np.where(z["v107_b7"] > 0.5, -1.0, 1.0)
    z["x6c2c_mag"] = mag * COUNTS_PER_LSB          # UNSIGNED counts of |gp-0x6c2c|

    for dead in ("x6b94", "x6b4c", "x6b86_mag", "sgn427", "damp_nz", "g6ac2"):
        if dead in z:
            del z[dead]
            print("  removed stale/mislabelled key: %s" % dead)

    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    z["v_rear"] = 0.5 * (rl + rr)

    lpf = ROOT / cdir / (stem + "_lp.npz")
    z["lp_yaw"] = np.full(n, np.nan)
    if lpf.exists():
        L = np.load(lpf)
        lt, lz = np.asarray(L["t"], float), np.asarray(L["z"], float)
        if len(lt) > 1:
            t0 = float(z["t0_mono"][0])
            rel = lt - t0
            o = np.argsort(rel)
            z["lp_yaw"] = np.interp(t, rel[o], lz[o])

    np.savez_compressed(f, **z)
    for k in DERIVED:
        if k not in D.PASS_1D:
            D.PASS_1D.append(k)
    for dead in ("x6b94", "x6b4c", "x6b86_mag", "sgn427", "damp_nz", "g6ac2"):
        while dead in D.PASS_1D:
            D.PASS_1D.remove(dead)
    D.split(route)

    print("\n  === DERIVED COLUMNS, route %s (%s) ===" % (route, lab))
    print("    v107_b7..b3 decoded from `probe` (%d rows, SAFE pairing with `t`)" % n)
    print("    x6c2c_mag (UNSIGNED counts of the RAW motor-rate derivative)  "
          "p50 %.1f  p95 %.1f  p99 %.1f  max %.1f   [field rails at %.1f]"
          % (np.percentile(z["x6c2c_mag"], 50), np.percentile(z["x6c2c_mag"], 95),
             np.percentile(z["x6c2c_mag"], 99), z["x6c2c_mag"].max(), SAT_CELL_COUNTS))
    print("    v_rear  median %.2f km/h   lp_yaw finite %.1f %%"
          % (np.nanmedian(z["v_rear"]), 100 * np.mean(np.isfinite(z["lp_yaw"]))))
    return z


def identity(route):
    """V107 witness.  🛑 LEG 2 (the tap moved) is the STRUCTURAL one and the only leg that
    separates V107 from V106 on the wire -- the scaler byte is stock's own value on V107."""
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)
    bits = {k: ((b4 & m) != 0) for k, m in
            (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3))}
    duty3 = float((code == 3).mean())
    live = {k: float(bits[k].mean()) for k in bits}
    b3_varies = bool(0.0005 < live["b3"] < 0.9995)
    nlive = sum(1 for k in ("b6", "b5", "b4") if 0.001 < live[k] < 0.999)

    mt = np.asarray(z["ab_mt"], int)
    shape = dict(nonzero=float(np.mean(mt > 0)), distinct=int(len(np.unique(mt))),
                 p50=float(np.percentile(mt, 50)), p90=float(np.percentile(mt, 90)),
                 p99=float(np.percentile(mt, 99)), max=int(mt.max()),
                 sat=float(np.mean(mt >= WIRE_SAT_FIELD)))
    # LEG 2: the tap moved iff the wire's SHAPE is unlike a6's.  Deliberately a coarse,
    # multi-statistic test -- any single percentile could coincide.
    devs = {k: abs(shape[k] - RA6[k]) / max(RA6[k], 1e-9)
            for k in ("nonzero", "distinct", "p50", "p90", "p99")}
    leg2 = bool(sum(1 for v in devs.values() if v > 0.25) >= 3)

    leg3_moved = bool(abs(live["b5"] - RA6["b5_pooled"]) > 0.03)

    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code3_duty=duty3, b3_duty=live["b3"], b3_varies=b3_varies,
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               bit_duties=live, n_nonconstant_of_b6b5b4=int(nlive),
               wire_shape=shape, ra6_wire_shape={k: RA6[k] for k in
                                                 ("nonzero", "distinct", "p50", "p90", "p99", "sat")},
               wire_rel_dev_vs_ra6=devs,
               counts_per_lsb=COUNTS_PER_LSB, cell_counts_at_saturation=SAT_CELL_COUNTS,
               ra6_b5_pooled=RA6["b5_pooled"], b5_duty_pooled=live["b5"],
               leg1_pass=bool(duty3 >= 0.9999 and b3_varies and nlive >= 1),
               leg2_pass=leg2, leg3_b5_moved=leg3_moved,
               rule=("LEG1 byte7[7:6]==3 AND b3 varies (V103..V107 vs V101/V102), WEAK.  "
                     "LEG2 THE STRUCTURAL ONE: the 427 tap moved gp-0x6b86/sar4 -> gp-0x6c2c/sar3, "
                     "so the wire DISTRIBUTION must differ from a6's; >=3 of 5 shape statistics "
                     "off by >25 % is the criterion.  A wire that MATCHES a6 is evidence the log "
                     "is NOT V107.  LEG3 b5 duty -- 🛑 POOLED IS THE WRONG ESTIMATOR, quote it at "
                     "MATCHED alpha; pooled is reported only as a coarse flag.  "
                     "🛑 The 0x55E10 scaler byte is STOCK's own value on V107 and is not a witness."))
    out["identity_pass"] = bool(out["leg1_pass"] and out["leg2_pass"])

    print("\n  === IDENTITY, route %s (expected %s): %d 0x14A frames ===" % (route, lab, n))
    print("    byte7[7:6] code histogram: " +
          "  ".join("%d:%d" % (int(v), int(c)) for v, c in zip(cu, cc)))
    print("    byte7[7:6]==3 duty %.6f   b3 duty %.6f  VARIES=%s" % (duty3, live["b3"], b3_varies))
    print("    byte4 field hist: " + "  ".join("%d:%d" % (int(v), int(c))
                                               for v, c in zip(fu, fc)))
    print("    bit duties: " + "  ".join("%s=%.4f (a6 %.4f)" % (k, v, RA6[k + "_pooled"])
                                         for k, v in sorted(live.items(), reverse=True)))
    print("    LEG 1 (V103..V107 vs V101/V102): %s" % ("PASS" if out["leg1_pass"] else "FAIL"))
    print("    LEG 2 (THE TAP MOVED -- structural):")
    for k in ("nonzero", "distinct", "p50", "p90", "p99"):
        print("        %-9s V107 %10.4f   a6 %10.4f   rel dev %6.1f %%  %s"
              % (k, shape[k], RA6[k], 100 * devs[k], "DIFFERENT" if devs[k] > 0.25 else "same"))
    print("        => %s" % ("PASS -- the wire is a different cell, as E2 intended" if leg2
                             else "🛑 FAIL -- the wire looks like a6's. Either the tap did not "
                                  "move (log is NOT V107) or the lane is quiet; adjudicate on "
                                  "SPECTRAL SHAPE before concluding"))
    print("    LEG 3 (dose flag): b5 pooled %.4f vs a6's %.4f => %s   "
          "🛑 quote this at MATCHED alpha, not pooled"
          % (live["b5"], RA6["b5_pooled"], "moved" if leg3_moved else "unchanged"))
    (ROOT / cdir / (stem + "_identity.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


def lane427(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    mt = np.asarray(z["ab_mt"], int)
    n = len(mt)
    out = dict(route=route, build=lab, frames=int(n), source=X.WIRE_SOURCE[route],
               counts_per_lsb=COUNTS_PER_LSB, sar=SAR, rectified=True,
               sign_bit_available=False, min_ceiling=MIN_CEILING,
               packer="wire = clamp((min(|gp-0x6c2c|,65535) * 5) >> 3, 0, 0x3FF)",
               nonzero_frac=float(np.mean(mt > 0)), distinct=int(len(np.unique(mt))),
               p50=float(np.percentile(mt, 50)), p90=float(np.percentile(mt, 90)),
               p99=float(np.percentile(mt, 99)), max=int(mt.max()),
               sat_field_1023_frac=float(np.mean(mt >= WIRE_SAT_FIELD)),
               cell_counts_at_saturation=SAT_CELL_COUNTS)
    print("\n  === CAN 427 LANE, route %s (%s) ===" % (route, lab))
    print("    source: %s" % out["source"])
    print("    packer (VERIFIED from the binary): %s" % out["packer"])
    print("    🛑 RECTIFIED AND UNSIGNED -- byte4 b7 is gp-0x6b4c's sign, not this cell's.")
    print("       Band statistics only; NO directed cross-spectrum is available.")
    print("    %d frames  nonzero %.2f %%  distinct %d  p50 %.0f  p90 %.0f  p99 %.0f  max %d"
          % (n, 100 * out["nonzero_frac"], out["distinct"], out["p50"], out["p90"],
             out["p99"], out["max"]))
    print("    sat@1023 %.4f %%   (field saturates at |gp-0x6c2c| >= %.1f counts)"
          % (100 * out["sat_field_1023_frac"], SAT_CELL_COUNTS))
    (ROOT / cdir / (stem + "_lane427.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  CENSUS -- the Step-2 report.  Engaged exposure, speed census, faults, transitions.
# ======================================================================================
def _episodes(mask, t, min_gap=1.0):
    """Contiguous runs of `mask` as (t_start, t_end, i_start, i_end).  Runs separated by less
    than `min_gap` seconds of un-set mask are NOT merged -- an episode is a real engagement."""
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    d = np.diff(m.astype(np.int8))
    starts = list(np.where(d == 1)[0] + 1)
    ends = list(np.where(d == -1)[0])
    if m[0]:
        starts = [0] + starts
    if m[-1]:
        ends = ends + [len(m) - 1]
    return [(float(t[a]), float(t[b]), int(a), int(b)) for a, b in zip(starts, ends)]


def census(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    # 🛑 `cs_v` IS METRES PER SECOND (openpilot `carState.vEgo`), NOT km/h.  Verified on route a6:
    #    max 35.66 -> 128.4 km/h, and `cs_v*3.6 >= 70` gives 809.8 engaged s against STATE's
    #    "809 of its 1,224 engaged seconds above 70 km/h".  Reading it as km/h puts a whole highway
    #    drive in the 25-40 bin and reports 0.0 s above 40 -- which is what this code did first.
    #    ⚠ `v_rear` (and `ws_*`) are m/s too; `extract_ra6.py:derive()` prints v_rear "km/h".
    v = np.asarray(z["cs_v"], float) * 3.6
    assert np.nanmax(v) < 400, (
        f"speed p100 = {np.nanmax(v):.1f} km/h after the m/s->km/h conversion. `cs_v` was probably "
        f"already km/h in this cache; check before trusting any bin.")
    eng = np.asarray(z["cc_lat"], float) > 0.5
    sstat = np.asarray(z["sstat"], int)
    dt = float(np.median(np.diff(t)))

    epi = _episodes(eng, t)
    durs = sorted((b - a for a, b, _i, _j in epi), reverse=True)
    eng_s = float(eng.sum() * dt)

    print("\n  === CENSUS, route %s (%s) ===" % (route, lab))
    print("    duration %.1f s   dt %.4f s   engaged %.1f s (%.1f %%) in %d episode(s)"
          % (t[-1] - t[0], dt, eng_s, 100 * eng.mean(), len(epi)))
    print("    episode durations (s), longest first: %s"
          % ("  ".join("%.1f" % d for d in durs[:12]) + (" ..." if len(durs) > 12 else "")))

    print("\n    SPEED CENSUS of ENGAGED frames  (operator's windows: grinding 15-40 mph = "
          "24-64 km/h; drop-off <=5-6 mph = <=8-10 km/h; hard turn 50 mph = 80 km/h)")
    print("      %-8s %-10s %9s %9s %8s" % ("km/h", "mph", "eng s", "manual s", "eng %"))
    rows = {}
    for (lo, hi), lab_k, lab_m in zip(SPEED_BINS, SPEED_LAB, SPEED_MPH):
        sel = (v >= lo) & (v < hi)
        e_s = float((sel & eng).sum() * dt)
        m_s = float((sel & ~eng).sum() * dt)
        rows[lab_k] = dict(engaged_s=e_s, manual_s=m_s)
        print("      %-8s %-10s %9.1f %9.1f %7.1f %%"
              % (lab_k, lab_m, e_s, m_s, 100 * e_s / max(eng_s, 1e-9)))

    # 🛑 E1 is INERT below ~20 km/h (Y[0] byte-identical to V106).  A drive that lives there
    #    cannot witness the reshape at all -- say so rather than letting a null be read as one.
    e1_live_s = sum(rows[k]["engaged_s"] for k in ("25-40", "40-65", "65-90", "90+"))
    hwy_s = sum(rows[k]["engaged_s"] for k in ("65-90", "90+"))
    print("\n    🛑 E1 EXPOSURE GATE: V107 == V106 below ~20 km/h (Y[0] byte-identical).")
    print("       engaged >=25 km/h : %.1f s      engaged >=65 km/h : %.1f s  <- the residual band"
          % (e1_live_s, hwy_s))
    if hwy_s < 60:
        print("       ⚠ under 60 s above 65 km/h: the PRIMARY band endpoint (drive card #1) is "
              "UNDERPOWERED on this route.")

    # ---- FAULTS: the gate on everything else.
    dtc = np.asarray(z["dtc_active"], float) if "dtc_active" in z.files else None
    su, sc = np.unique(sstat, return_counts=True)
    ss_eng = sstat[eng]
    su_e, sc_e = np.unique(ss_eng, return_counts=True) if ss_eng.size else (np.array([]), np.array([]))
    print("\n    FAULTS  (the gate on everything else)")
    print("      STEER_STATUS all   : " + "  ".join("%d:%d" % (a, b) for a, b in zip(su, sc)))
    print("      STEER_STATUS engaged: " + "  ".join("%d:%d" % (a, b) for a, b in zip(su_e, sc_e)))
    dtc_frac = float(np.mean(dtc > 0.5)) if dtc is not None else float("nan")
    print("      dtc_active duty    : %.6f %s"
          % (dtc_frac, "" if not (dtc_frac > 0) else "  🛑 NON-ZERO -- investigate before scoring"))

    # ---- DISENGAGEMENT TRANSITIONS: the operator's NEW observation.
    #      "the grinding persists for a few seconds after openpilot disengages"
    trans = []
    for _a, b, _i, j in epi:
        after = min(j + 1, len(t) - 1)
        # keep only transitions with real driving after them -- a key-off is not the phenomenon
        tail = t[-1] - t[after]
        moving_after = float(np.mean(v[after:min(after + int(5 / dt), len(v))] > 5.0))
        trans.append(dict(t_disengage=float(t[after]), speed_kmh=float(v[after]),
                          speed_mph=float(v[after] / 1.609344),
                          seconds_of_log_after=float(tail),
                          frac_moving_next_5s=moving_after,
                          usable=bool(tail >= 5.0 and moving_after > 0.8)))
    usable = [x for x in trans if x["usable"]]
    print("\n    DISENGAGEMENT TRANSITIONS (engaged -> manual), the NEW diagnostic")
    print("      %d transition(s); %d with >=5 s of continued driving after (USABLE)"
          % (len(trans), len(usable)))
    print("      %-12s %10s %8s %12s %s" % ("t_diseng s", "km/h", "mph", "log after s", "usable"))
    for x in trans:
        print("      %-12.2f %10.1f %8.1f %12.1f %s"
              % (x["t_disengage"], x["speed_kmh"], x["speed_mph"], x["seconds_of_log_after"],
                 "YES" if x["usable"] else "no"))
    if not usable:
        print("      ⚠ NO usable transition: every disengagement is at the end of the log or is "
              "followed by a stop. The post-disengage persistence CANNOT be tested on this route.")

    out = dict(route=route, build=lab, duration_s=float(t[-1] - t[0]), dt=dt,
               engaged_s=eng_s, engaged_frac=float(eng.mean()), n_episodes=len(epi),
               episode_durations_s=durs, speed_census=rows,
               engaged_s_ge25=e1_live_s, engaged_s_ge65=hwy_s,
               steer_status_all={int(a): int(b) for a, b in zip(su, sc)},
               steer_status_engaged={int(a): int(b) for a, b in zip(su_e, sc_e)},
               dtc_active_duty=dtc_frac, transitions=trans, n_usable_transitions=len(usable))
    (ROOT / cdir / (stem + "_census.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  AUDIO -- the ONLY instrument that can see the operator's several-hundred-Hz grinding.
# ======================================================================================
def audio_plan(route):
    """Report `rawAudioData` presence/coverage and state the within-drive contrasts to run.

    🛑 THE HEADLINE INSTRUMENT.  Every CAN channel is Nyquist-limited to ~50 Hz (0x18F staleness is
    12.5 ms => 50.57 Hz) and is STRUCTURALLY BLIND to a several-hundred-Hz grind.  Only the 16 kHz
    `rawAudioData` can address it.
    🛑 ABSOLUTE ACOUSTIC LEVEL IS NOT COMPARABLE ACROSS DRIVES -- the parked-engine-on cabin differs
    3-12x between drives.  Every statistic below therefore lives INSIDE one drive.
    """
    pref, nseg, _cdir, _pfx, _stem, lab = D.ROUTES[route]
    segs = sorted(RLOGS.glob("%s--*--rlog.zst" % pref),
                  key=lambda p: int(p.name.split("--")[2]))
    assert len(segs) == nseg, (f"route {route}: globbed {len(segs)} segments but ROUTES says "
                               f"{nseg}. Do not proceed on a partial route.")
    n_blk = n_seg_with = 0
    for p in segs:
        seen = False
        for evt in rlog_parse.read_messages(str(p)):
            try:
                if evt.which() == "rawAudioData":
                    n_blk += 1
                    seen = True
            except Exception:
                continue
        n_seg_with += int(seen)
    print("\n  === AUDIO, route %s (%s) ===" % (route, lab))
    print("    %d segments, %d carry rawAudioData, %d blocks total" % (len(segs), n_seg_with, n_blk))
    print("    🛑 CAN is blind here: 0x18F staleness 12.5 ms => Nyquist 50.57 Hz. Audio is the "
          "ONLY instrument for the operator's several-hundred-Hz grind.")
    print("    🛑 Absolute level does NOT travel between drives. Run these WITHIN this drive:")
    print("       1. engaged vs manual, MATCHED speed bin, 100-300 / 300-1000 Hz third-octaves")
    print("       2. speed bin vs speed bin while engaged (the 24-64 km/h grinding window)")
    print("       3. before vs after each USABLE disengagement (census `transitions`) -- the "
             "operator's persistence claim, and the one contrast that needs no matching at all")
    print("    Reuse `decode/extract_audio_grind.py` (its `segments()` globs and is SAFE) and "
          "`extract_audio_env.py`; add this route to their ROUTES dicts and point `cache` at "
          "`_scratch/cache/r%s/`. 🛑 Do NOT reuse `extract_audio.py:segments()` -- it walks "
          "indices until the first absent one and silently truncates." % route)
    return dict(route=route, segments=len(segs), segments_with_audio=n_seg_with, blocks=n_blk,
                coverage_frac=float(n_seg_with / max(len(segs), 1)))


if __name__ == "__main__":
    args = sys.argv[1:]
    routes = discover()
    if not routes:
        sys.exit(0)
    fns = {"extract": extract_route, "derive": derive, "identity": identity,
           "lane427": lane427, "census": census, "audio_plan": audio_plan,
           "health": X.health, "discover": lambda r: None}
    keys = list(routes)
    if not args:
        for r in keys:
            extract_route(r)
            derive(r)
            identity(r)
            lane427(r)
            census(r)
            audio_plan(r)
    elif args[0] != "discover":
        for r in (args[1:] or keys):
            fns[args[0]](r)
