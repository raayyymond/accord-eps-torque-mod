#!/usr/bin/env python3
r"""Extract route `a6` (**V106 -- gp-0x6b26 x3.0 ENGAGED**) into `analysis-2020accord/_scratch/cache/ra6/`.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly the `decode/extract_ra5.py` pattern: add a row to
`decode_v84_probe_r6d.ROUTES`, then call `extract_r7d.extract_route()` -- the SAME code that wrote
every cache since `_scratch/cache/r6d/`.

===================================================================================================
ROUTE a6 == V106.  V105 BASE + TWELVE CAL BYTES.  NO CAVE CHANGE.  NO 427 CHANGE.
===================================================================================================
Byte diff V105 -> V106 (from `builds/v80_v107/build_v106_tva.py`, re-stated here, NOT re-derived):
    0xD7A5C  mode 26 (ENGAGED) Y[0..2]  (-14745,-8601,-2949) -> (-29490,-17202,-5898)
    0xD7A6C  mode 27 (ENGAGED) Y[0..2]  (-14745,-8601,-2949) -> (-29490,-17202,-5898)
    0xC4FFC / 0xC6FFC  CRC trailers  (unchanged region -- the cal edit is in the 0xD7xxx block)
🛑 **THE CAVE IS BYTE-IDENTICAL TO V105** (builder assertion: `rd(code, 0xC4B34, 0xA4) ==
   rd(base, 0xC4B34, 0xA4)`), so **every rung means exactly what it meant on `a5`**:
        byte4 b7 0x80 = gp-0x6b4c < 0                 *** NOT the sign of the 427 cell ***
        byte4 b6 0x40 = |gp-0x6b94| >= |gp-0x4f64|    GOVERNOR CLIP DUTY
        byte4 b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|    COMPARATOR: friction vs inertia
                                                      *** OPERAND B IS THE CELL V106 DOSES ***
        byte4 b4 0x10 = gp-0x6ada < 0                 sign of r24
        byte4 b3 0x08 = gp-0x3680 < 0                 D_state (PID D-term) SIGN
        byte7[7:6]    = 3                             SAME CODE as V101..V105
   427 (0x1AB) = clamp(|gp-0x6b86| * 5 >> 4, 0, 0x3FF)   => counts = wire * 3.2   (`0x55DF2 = 7a`,
   `0x55E10 = a4`, both carried; builder asserts them).

===================================================================================================
🛑🛑 THE SAME TRAPS AS `ra5` -- REPRODUCED, NOT FIXED, DELIBERATELY
===================================================================================================
* **NO SIGN BIT FOR THE 427 CELL.**  `byte4 b7` is the sign of `gp-0x6b4c` (the LKAS command lane),
  NOT of `gp-0x6b86`.  This cache emits **`x6b86_mag` -- UNSIGNED, RECTIFIED counts** and emits the
  sign bit only under its true name `sgn_6b4c`.  **NO signed `x6b86` key exists.  Do not create one.**
* **NO `x6b94` AND NO `x6b4c` KEY.**  `damp_nz` / `g6ac2` are stale decodes on V100+ routes and are
  deleted after the shared extractor emits them.
* **`raw14` OFF-BY-ONE:** `t == raw14_t[1:]` and `probe == raw14_b4[1:]`.
  **SAFE PAIRS: `(t, probe)` or `(raw14_t, raw14_b4)`.  NEVER `(t, raw14_b4)`.**

===================================================================================================
IDENTITY -- V106 vs V105 IS **NOT** SEPARABLE FROM THE CAVE OR THE WIRE, AND THIS FILE SAYS SO
===================================================================================================
V106 changes **zero** instrumented bytes: same cave, same packer, same 427 source, same byte7 code.
There is **no structural witness** distinguishing V106 from V105 in the telemetry.  What IS available:

  LEG 1  byte7[7:6]==3 AND b3 varies      -- separates V103/V104/V105/V106 from V101/V102.  WEAK.
  LEG 2  427 wire code > 800 observed     -- separates V104+ from V103/V102.  STRUCTURAL.
         (V103's packer ceiling is (10240*5)>>6 = 800.)  A NULL IS NOT A REFUTATION.
  LEG 3  🆕 **`b5` DUTY SHIFT -- THE DOSE PROOF, and the only V106-specific leg.**
         `b5 = ( |gp-0x6ae2| >= |gp-0x6b26| )`.  Operand A (friction) is UNCHANGED by V106;
         operand B is the cell V106 doubles.  `a5` baseline: **0.2533 pooled, 0.4019 engaged
         <16 km/h**.  A collapse is EVIDENCE the dose arrived AND that the car reads modes 26/27
         engaged (RULE 7).  ⚠ It is a *comparator*, so it calibrates the delivered multiplier only
         through the |gp-0x6b26| distribution -- see `studies/ra6/ra6_dose.py`.
🛑 **The operator's symptom report is itself a leg**: V106 changed nothing else, and he felt a change.

Usage:
    python decode/extract_ra6.py                 # full pipeline
    python decode/extract_ra6.py extract
    python decode/extract_ra6.py derive
    python decode/extract_ra6.py identity
    python decode/extract_ra6.py lane427
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

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402
import rlog_parse        # noqa: E402

D = X.D

NEW = {
    "a6": ("75604b0a432fdc89_000000a6--78293a259e", 26,
           "analysis-2020accord/_scratch/cache/ra6", "ra6s", "ra6", "V106"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v

# ---- V106 427 spec: CARRIED from V105/V104 verbatim (source gp-0x6b86, `sar 4`).
X.WIRE_SCALE["a6"] = 16.0 / 5.0                       # 3.2 counts per wire LSB
X.WIRE_SOURCE["a6"] = ("gp-0x6b86 (BIQUAD OUTPUT -- V105's 25.5 Hz notch), sar 4  "
                       "[V104 repoint, CARRIED unchanged by V105 and V106]")

M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES["a6"] = {
    "b7_sign_6b4c_neg__NOT_THE_427_CELL": M_B7,
    "b6_CMP_abs6b94_ge_abs4f64__GOVERNOR_CLIP": M_B6,
    "b5_CMP_absfriction_ge_absinertia__THE_DOSED_CELL": M_B5,
    "b4_sign_r24_neg": M_B4,
    "b3_sign_Dstate_neg": M_B3,
}

IDENT_MASK = 0xC0
COUNTS_PER_LSB = 16.0 / 5.0            # sar 4
WIRE_SAT_FIELD = 1023                  # the 10-bit CAN field
V103_MAX_REACHABLE_WIRE = 800          # (10240*5)>>6 -- V103/V102's structural ceiling
SAT_CELL_COUNTS = WIRE_SAT_FIELD * COUNTS_PER_LSB      # 3273.6 counts of gp-0x6b86

# `a5` (V105) reference duties -- quoted from the V106 handoff §4.3 / §5 Q8, for LEG 3 and Q8.
RA5_B5_POOLED, RA5_B5_ENG_LOW = 0.2533, 0.4019

DERIVED = ["v106_b7", "v106_b6", "v106_b5", "v106_b4", "v106_b3",
           "mag427", "sgn_6b4c", "x6b86_mag", "v_rear", "lp_yaw"]

_TAPPED_READ = rlog_parse.read_messages
MISSING_SEGMENTS = []
LP = {"t": [], "z": []}


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


def extract_route(route="a6"):
    MISSING_SEGMENTS.clear()
    LP["t"].clear()
    LP["z"].clear()
    rep = X.extract_route(route)
    rep["segments_absent"] = list(MISSING_SEGMENTS)
    rep["livePose_samples"] = len(LP["t"])
    print("\n  segments absent from disk: %d   livePose samples: %d"
          % (len(MISSING_SEGMENTS), len(LP["t"])))
    cdir = ROOT / D.ROUTES[route][2]
    np.savez_compressed(cdir / (D.ROUTES[route][4] + "_lp.npz"),
                        t=np.array(LP["t"], float), z=np.array(LP["z"], float))
    return rep


def derive(route="a6"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / (stem + ".npz")
    z = dict(np.load(f, allow_pickle=True))
    t = np.asarray(z["t"], float)
    n = len(t)

    p = np.asarray(z["probe"], int) & 0xFF
    assert len(p) == n, "probe/t length mismatch -- the pairing contract is broken"
    for nm, m in (("b7", M_B7), ("b6", M_B6), ("b5", M_B5), ("b4", M_B4), ("b3", M_B3)):
        z["v106_" + nm] = ((p & m) != 0).astype(float)

    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(abt, t, side="right") - 1, 0, len(mt) - 1)
    mag = mt[j].astype(float)
    z["mag427"] = mag
    # 🛑 b7 is gp-0x6b4c's sign, NOT gp-0x6b86's.  Named for what it is; never applied to mag427.
    z["sgn_6b4c"] = np.where(z["v106_b7"] > 0.5, -1.0, 1.0)
    z["x6b86_mag"] = mag * COUNTS_PER_LSB          # UNSIGNED counts of |gp-0x6b86|

    for dead in ("x6b94", "x6b4c", "sgn427", "damp_nz", "g6ac2"):
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
    for dead in ("x6b94", "x6b4c", "sgn427", "damp_nz", "g6ac2"):
        while dead in D.PASS_1D:
            D.PASS_1D.remove(dead)
    D.split(route)

    print("\n  === DERIVED COLUMNS, route %s (%s) ===" % (route, lab))
    print("    v106_b7..b3 decoded from `probe` (%d rows, SAFE pairing with `t`)" % n)
    print("    mag427  nonzero %.2f %%  distinct %d  max %.0f   sat@1023 %.4f %%  "
          "ABOVE V103 CEILING (>=801) %.4f %%"
          % (100 * np.mean(mag > 0), len(np.unique(mag)), mag.max(),
             100 * np.mean(mag >= WIRE_SAT_FIELD),
             100 * np.mean(mag > V103_MAX_REACHABLE_WIRE)))
    print("    x6b86_mag (UNSIGNED counts)  p50 %.1f  p95 %.1f  p99 %.1f  max %.1f"
          % (np.percentile(z["x6b86_mag"], 50), np.percentile(z["x6b86_mag"], 95),
             np.percentile(z["x6b86_mag"], 99), z["x6b86_mag"].max()))
    print("    v_rear  median %.2f km/h   lp_yaw finite %.1f %%"
          % (np.nanmedian(z["v_rear"]), 100 * np.mean(np.isfinite(z["lp_yaw"]))))
    return z


def identity(route="a6"):
    """V106 witness.  🛑 V106 changes ZERO instrumented bytes vs V105 -- LEG 3 (`b5`) is the only
    V106-specific leg, and it is a DOSE proof rather than a structural one."""
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
    n_above = int((mt > V103_MAX_REACHABLE_WIRE).sum())

    leg3 = bool(abs(live["b5"] - RA5_B5_POOLED) > 0.03)

    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code3_duty=duty3, b3_duty=live["b3"], b3_varies=b3_varies,
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               bit_duties=live, n_nonconstant_of_b6b5b4=int(nlive),
               wire_n_frames=int(len(mt)), wire_max=int(mt.max()),
               wire_p50=float(np.percentile(mt, 50)), wire_p99=float(np.percentile(mt, 99)),
               n_above_v103_ceiling=n_above,
               frac_above_v103_ceiling=float(n_above / len(mt)) if len(mt) else float("nan"),
               ra5_b5_pooled=RA5_B5_POOLED, ra5_b5_engaged_low=RA5_B5_ENG_LOW,
               b5_duty_pooled=live["b5"], leg3_b5_moved=leg3,
               leg1_pass=bool(duty3 >= 0.9999 and b3_varies and nlive >= 1),
               leg2_pass=bool(n_above > 0),
               rule=("LEG1 byte7[7:6]==3 AND b3 varies (V103..V106 vs V101/V102);  "
                     "LEG2 any 427 wire code > 800 is impossible on V103/V102 (V104-or-later);  "
                     "LEG3 b5 pooled duty vs a5's 0.2533 -- the DOSE proof, V106-specific.  "
                     "🛑 V106 changes ZERO instrumented bytes; no structural separator from "
                     "V105 exists.  The operator's symptom report is itself a leg."))
    out["identity_pass"] = bool(out["leg1_pass"] and out["leg2_pass"])
    print("\n  === IDENTITY, route %s (expected %s): %d 0x14A frames ===" % (route, lab, n))
    print("    byte7[7:6] code histogram: " +
          "  ".join("%d:%d" % (int(v), int(c)) for v, c in zip(cu, cc)))
    print("    byte7[7:6]==3 duty %.6f   b3 duty %.6f  VARIES=%s" %
          (duty3, live["b3"], b3_varies))
    print("    byte4 field hist: " + "  ".join("%d:%d" % (int(v), int(c))
                                               for v, c in zip(fu, fc)))
    print("    bit duties: " + "  ".join("%s=%.4f" % (k, v)
                                         for k, v in sorted(live.items(), reverse=True)))
    print("    LEG 1 (V103..V106 vs V101/V102): %s" % ("PASS" if out["leg1_pass"] else "FAIL"))
    print("    LEG 2 (V104-or-later, 427 wire > 800): %d of %d frames (%.4f %%)  =>  %s"
          % (n_above, len(mt), 100 * out["frac_above_v103_ceiling"],
             "PASS -- structurally impossible on V103" if out["leg2_pass"]
             else "no evidence (lane never went loud enough); NOT a refutation"))
    print("    LEG 3 (THE DOSE PROOF): b5 pooled %.4f  vs  a5's %.4f  =>  %s"
          % (live["b5"], RA5_B5_POOLED, "MOVED" if leg3 else "unchanged"))
    print("    427 wire: p50 %.0f  p99 %.0f  max %d" %
          (out["wire_p50"], out["wire_p99"], out["wire_max"]))
    (ROOT / cdir / (stem + "_identity.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


def lane427(route="a6"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / (stem + ".npz"), allow_pickle=True)
    mt = np.asarray(z["ab_mt"], int)
    n = len(mt)
    out = dict(route=route, build=lab, frames=int(n), source=X.WIRE_SOURCE[route],
               counts_per_lsb=COUNTS_PER_LSB, rectified=True, sign_bit_available=False,
               nonzero_frac=float(np.mean(mt > 0)), distinct=int(len(np.unique(mt))),
               p50=float(np.percentile(mt, 50)), p90=float(np.percentile(mt, 90)),
               p99=float(np.percentile(mt, 99)), max=int(mt.max()),
               sat_field_1023_frac=float(np.mean(mt >= WIRE_SAT_FIELD)),
               cell_counts_at_saturation=SAT_CELL_COUNTS)
    print("\n  === CAN 427 LANE, route %s (%s) ===" % (route, lab))
    print("    source: %s" % out["source"])
    print("    🛑 RECTIFIED AND UNSIGNED on this route -- byte4 b7 is gp-0x6b4c's sign, not this")
    print("       cell's.  Band statistics only; NO directed cross-spectrum is available.")
    print("    %d frames  nonzero %.2f %%  distinct %d  p50 %.0f  p90 %.0f  p99 %.0f  max %d"
          % (n, 100 * out["nonzero_frac"], out["distinct"], out["p50"], out["p90"],
             out["p99"], out["max"]))
    print("    sat@1023 %.4f %%   (field saturates at |gp-0x6b86| >= %.1f counts)"
          % (100 * out["sat_field_1023_frac"], SAT_CELL_COUNTS))
    (ROOT / cdir / (stem + "_lane427.json")).write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    fns = {"extract": extract_route, "derive": derive, "identity": identity,
           "lane427": lane427, "health": X.health, "census": X.census}
    if not args:
        extract_route("a6")
        derive("a6")
        identity("a6")
        lane427("a6")
        X.health("a6")
        X.census("a6")
    else:
        for r in (args[1:] or ["a6"]):
            fns[args[0]](r)
