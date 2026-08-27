#!/usr/bin/env python3
r"""Extract route `7d` -- the V94 flight -- into `analysis-2020accord/_scratch/cache/r7d/`, tap the FULL
0x1AB payload and 0x14A byte 7, and run V94's own parameter-free IDENTITY test.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `decode/extract_r6e.py` .. `decode/extract_r78_r79.py` do,
this file adds a row to `decode_v84_probe_r6d.ROUTES` and calls that module's `extract()`/`split()`
-- the SAME code that wrote every cache since `_scratch/cache/r6d/`.  Field names, ZOH/interp convention,
IMU axis pick, sentinel definition and `PASS_1D` are therefore bit-for-bit the ones every prior
route was scored with.  0x1AB and byte 7 are added by PASS-THROUGH TAPS, not by editing the
extractor, and the byte-7 tap's own byte-4 column is asserted elementwise against the extractor's
`raw14_b4` -- so if the tap's filter ever drifts, the run dies rather than silently mispairing.

===================================================================================================
ROUTE 7d == V94.  V90 base + 22 cal bytes + ONE CODE BYTE.  THE CAVE IS V90'S, UNCHANGED.
===================================================================================================
    byte4 b7 0x80 = gp-0x6b26 <  0        SIGN of the damping-lane output
    byte4 b6 0x40 = |gp-0x6bf6| >= 512    |MODEL|
    byte4 b5 0x20 = gp-0x6ae2 != 0        friction relay active
    byte4 b4 0x10 = gp-0x6c00 <  0        the observer gate FAILED
    byte4 b3 0x08 = 1                     fingerprint => every field value ODD
    byte7        = NOT WRITTEN            <-- V92's cave only.  NEGATIVE control here.

    cal  0xD6A6C  mode 24 MANUAL   Y row x0.50
         0xD7A5C  mode 26 ENGAGED  Y row x0.25
         0xD7A6C  mode 27          Y row x0.25
         0xC640A  FALLBACK-2 flat gain  x0.75
         0xC640C  FALLBACK-1 flat gain  x0.75
    code 0x55E10  CAN 427 packer  `sar 0x3,r6` -> `sar 0x1,r6`

    427 (0x1AB) = clamp(|gp-0x6b26| * 5 >> 1, 0, 0x3FF)   at 50 Hz,  |b26| = wire * 2/5
    (route 77/78/79's V90/V91 packer was `>> 3`, i.e. |b26| = wire * 8/5)

===================================================================================================
★ THE IDENTITY TEST -- PARAMETER-FREE, SINGLE-FRAME, AND IT DOES NOT DEPEND ON THE DOSE
===================================================================================================
The build's own headline prediction -- "V94's 427 wire distribution REPRODUCES route 78's, because
the x4 packer cancels the x0.25 dose" -- is NOT an identity test, because route 78's distribution
is ALSO what an unmodified V90/V91 produces.  A wire distribution that matches r78 is therefore
consistent with BOTH "V94 with the dose in force" AND "the car is still on V90/V91".

The packer's ARITHMETIC separates them with no free parameter:

    sar 3:  wire = floor(5n/8),  n = |gp-0x6b26|   ->  n = 0..7 gives 0,0,1,1,2,3,3,4
                                                       EVERY residue mod 5 is reachable
    sar 1:  wire = floor(5n/2)                     ->  n even -> 5n/2       == 0 (mod 5)
                                                       n odd  -> (5n-1)/2   == 2 (mod 5)
            🛑 wire == 1, 3 or 4 (mod 5) IS ARITHMETICALLY IMPOSSIBLE.

So `P(wire mod 5 in {1,3,4})` is EXACTLY 0 on V94 and is a large positive number on any sar-3
build.  One frame with wire == 1 (mod 5) falsifies V94; a few thousand frames with none confirms
the code byte is on the car.  Routes 77 and 78 are the built-in positive controls for the test.

⊕ SECOND, INDEPENDENT LEG: the V90 cave (b4 == 0 reachable) rules out V86B..V89, and byte7[7:6]
  == 0 on every frame rules out V92.  Cave + packer + byte7 together name V94 uniquely.

🛑 SATURATION IS NEW AND MUST BE CHECKED.  Under `sar 1` the 10-bit wire saturates at 1023, which
   is |gp-0x6b26| = 409.2 counts -- BELOW the +-511 lane clamp (`0xC407E`).  On sar-3 builds the
   lane rail (511) mapped to wire 319 and the wire could never saturate.  A nonzero wire==1023 duty
   on route 7d is CENSORING, not a lane rail, and every percentile above it is a lower bound.

Usage:
    python decode/extract_r7d.py                 # extract + identity + health + census
    python decode/extract_r7d.py extract 7d
    python decode/extract_r7d.py identity 7d
    python decode/extract_r7d.py health 7d
    python decode/extract_r7d.py census 7d
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
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v84_probe_r6d as D  # noqa: E402  -- THE extractor that wrote every cache since r6d
import rlog_parse                 # noqa: E402

ROUTE_DEF = {
    "7d": ("75604b0a432fdc89_0000007d--83a5c80392", 3, "analysis-2020accord/_scratch/cache/r7d",
           "r7ds", "r7d", "V94"),
}
for _k, _v in ROUTE_DEF.items():
    D.ROUTES[_k] = _v
D.ROUTES.setdefault("77", ("75604b0a432fdc89_00000077--7411859c54", 21,
                           "analysis-2020accord/_scratch/cache/r77", "r77s", "r77", "V90"))
D.ROUTES.setdefault("78", ("75604b0a432fdc89_00000078--93548c06b3", 16,
                           "analysis-2020accord/_scratch/cache/r78", "r78s", "r78", "V91"))
D.ROUTES.setdefault("79", ("75604b0a432fdc89_00000079--cb7538ffae", 15,
                           "analysis-2020accord/_scratch/cache/r79", "r79s", "r79", "V92"))

# ---- byte4 masks.  V94's cave IS V90's, so these are route 78's names verbatim.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
FIELD_MASK = 0xF8

BITNAMES = {
    "7d": {"b7_sign_6b26": M_B7, "b6_model_ge512": M_B6, "b5_friction_nz": M_B5,
           "b4_gate_failed": M_B4, "b3_fingerprint": M_B3},
}

# 427 wire -> counts of gp-0x6b26.
WIRE_SCALE = {"7d": 2.0 / 5.0, "78": 8.0 / 5.0, "77": 8.0 / 5.0, "79": 16.0 / 5.0}
WIRE_SOURCE = {"7d": "gp-0x6b26 (damping/inertia lane), sar 1",
               "78": "gp-0x6b26 (damping lane), sar 3",
               "77": "gp-0x6b26 (damping lane), sar 3",
               "79": "gp-0x6bbe (BOOST lane), sar 4"}
LANE_CLAMP = 511                  # `0xC407E`, applies to gp-0x6b26 only
WIRE_SAT = 1023                   # the 10-bit field; on sar 1 this is REACHABLE (|b26| >= 409.2)

V90_V91_B4ZERO_SET = {1, 5, 9, 11, 13, 17, 19, 21, 25, 27, 29}   # field = (byte4>>3)&0x1F
PRE_V90_ALPHABET = {3, 7, 15, 23, 31}                            # V86B/V87/V88/V89, measured

# residues of floor(5n/2) mod 5 -- the ONLY ones a `sar 1` packer can emit
SAR1_LEGAL_RESIDUES = {0, 2}
SAR1_ILLEGAL_RESIDUES = {1, 3, 4}


# ======================================================================================
#  TAPS -- pass-through generators, so the extractor's event stream is unchanged.
#  Verbatim from `decode/extract_r78_r79.py`.
# ======================================================================================
_ORIG_READ = rlog_parse.read_messages
TAP = {"t": [], "b0": [], "b1": [], "b2": [], "src": [], "dlc": []}
TAP14 = {"t": [], "b4": [], "b7": [], "dlc": []}
TAP14_ALL_DLC = Counter()          # every 0x14A src==1 frame, no length filter
TRUNCATED, MSG_COUNT = {}, {}
_TAP_ON = False


def _read_messages_tapped(path):
    n = 0
    try:
        for evt in _ORIG_READ(path):
            n += 1
            if _TAP_ON:
                try:
                    if evt.which() == "can":
                        tm = evt.logMonoTime * 1e-9
                        for m in evt.can:
                            addr, src = int(m.address), int(m.src)
                            if addr == 0x1AB:
                                d = bytes(m.dat)
                                TAP["t"].append(tm)
                                TAP["b0"].append(d[0] if len(d) > 0 else 0)
                                TAP["b1"].append(d[1] if len(d) > 1 else 0)
                                TAP["b2"].append(d[2] if len(d) > 2 else 0)
                                TAP["src"].append(src)
                                TAP["dlc"].append(len(d))
                            elif addr == 0x14A and src == 1:
                                d = bytes(m.dat)
                                TAP14_ALL_DLC[len(d)] += 1
                                # 🛑 filter MUST match the extractor's: src==1, addr==0x14A, len>=7
                                if len(d) >= 7:
                                    TAP14["t"].append(tm)
                                    TAP14["b4"].append(d[4])
                                    TAP14["b7"].append(d[7] if len(d) > 7 else -1)
                                    TAP14["dlc"].append(len(d))
                except Exception:
                    pass
            yield evt
    except Exception as exc:                       # capnp KjException on a torn tail
        TRUNCATED[Path(path).name] = (n, str(exc).splitlines()[0])
        print(f"  ⚠ TRUNCATED rlog {Path(path).name}: {n:,} complete messages read, then "
              f"{str(exc).splitlines()[0]}", flush=True)
    finally:
        MSG_COUNT[Path(path).name] = n


rlog_parse.read_messages = _read_messages_tapped


def _tap_reset():
    for k in TAP:
        TAP[k].clear()
    for k in TAP14:
        TAP14[k].clear()
    TAP14_ALL_DLC.clear()
    TRUNCATED.clear()
    MSG_COUNT.clear()


def _tap_arrays(t0):
    t = np.array(TAP["t"], float) - t0
    b0 = np.array(TAP["b0"], int)
    b1 = np.array(TAP["b1"], int)
    b2 = np.array(TAP["b2"], int)
    mt = ((b0 & 0x03) << 8) | b1                       # MOTOR_TORQUE 1|10@0+
    return dict(t1ab=t, b0=b0.astype(np.uint8), b1=b1.astype(np.uint8), b2=b2.astype(np.uint8),
                src=np.array(TAP["src"], np.int16), dlc=np.array(TAP["dlc"], np.int16),
                mt=mt.astype(np.int16),
                config_valid=((b0 >> 7) & 1).astype(np.uint8),
                dtc_bit2=((b0 >> 2) & 1).astype(np.uint8),
                checksum=(b2 & 0x0F).astype(np.uint8),
                counter=((b2 >> 4) & 0x03).astype(np.uint8),
                output_disabled=((b2 >> 6) & 1).astype(np.uint8))


def _tap_report(tag, A, route):
    n = len(A["t1ab"])
    if not n:
        print(f"  {tag}: 🛑 ZERO 0x1AB frames")
        return {}
    src = Counter(int(s) for s in A["src"])
    mt = A["mt"].astype(int)
    dt = np.diff(A["t1ab"])
    dt = dt[(dt > 0) & (dt < 1.0)]
    hz = 1.0 / np.median(dt) if len(dt) else float("nan")
    ctr = A["counter"].astype(int)
    step = np.diff(ctr) % 4
    out = dict(frames=n, src=dict(src), rate_hz=float(hz),
               dlc=dict(Counter(int(x) for x in A["dlc"])),
               wire_source=WIRE_SOURCE[route], wire_scale_counts_per_lsb=WIRE_SCALE[route],
               mt_nonzero_frac=float(np.mean(mt != 0)), mt_distinct=int(len(np.unique(mt))),
               mt_min=int(mt.min()), mt_max=int(mt.max()),
               mt_p50=float(np.percentile(mt, 50)), mt_p95=float(np.percentile(mt, 95)),
               mt_p99=float(np.percentile(mt, 99)),
               mt_sat_frac=float(np.mean(mt >= 1023)),
               counter_step1_frac=float(np.mean(step == 1)) if len(step) else float("nan"),
               checksum_distinct=int(len(np.unique(A["checksum"]))),
               config_valid_duty=float(A["config_valid"].mean()),
               output_disabled_duty=float(A["output_disabled"].mean()))
    print(f"  {tag}: {n:,} frames  src={dict(src)}  {hz:.2f} Hz  dlc={out['dlc']}")
    print(f"      427 source = {WIRE_SOURCE[route]},  counts = wire * {WIRE_SCALE[route]:.2f}")
    print(f"      MOTOR_TORQUE  nonzero {100*out['mt_nonzero_frac']:.2f}%  distinct "
          f"{out['mt_distinct']}  range [{out['mt_min']},{out['mt_max']}]  "
          f"p50/p95/p99 {out['mt_p50']:.0f}/{out['mt_p95']:.0f}/{out['mt_p99']:.0f}  "
          f"saturated {100*out['mt_sat_frac']:.3f}%")
    print(f"      COUNTER +1 {100*out['counter_step1_frac']:.2f}%  CHECKSUM distinct "
          f"{out['checksum_distinct']}/16  CONFIG_VALID duty {out['config_valid_duty']:.4f}  "
          f"OUTPUT_DISABLED duty {out['output_disabled_duty']:.4f}")
    return out


# ======================================================================================
#  THE raw14 OFF-BY-ONE FIX -- derived and ASSERTED, never assumed.  Verbatim from extract_r77.
# ======================================================================================
def _row2raw14(z):
    t = np.asarray(z["t"], float)
    r14t = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    probe = np.asarray(z["probe"], int) & 0xFF
    lead = int(len(r14t) - len(t))
    ok_lead = bool(lead >= 0 and np.all(r14t[lead:] == t) and np.all(b4[lead:] == probe))
    ss = np.clip(np.searchsorted(r14t, t), 0, len(r14t) - 1)
    rep = dict(n_rows=int(len(t)), n_raw14=int(len(r14t)), lead=lead,
               constant_lead_holds=ok_lead,
               dup_raw14_timestamps=int(np.sum(np.diff(r14t) == 0)),
               searchsorted_would_mispair=int(np.sum(b4[ss] != probe)))
    assert ok_lead, ("row2raw14: the constant-lead map does NOT reproduce (t, probe) exactly -- "
                     "the extractor's append logic has changed")
    idx = np.arange(len(t), dtype=np.int32) + lead
    assert bool(np.all(r14t[idx] == t)), "row2raw14: timestamp check failed on the final map"
    assert bool(np.all(b4[idx] == probe)), "row2raw14: byte4 check failed on the final map"
    return idx, rep


def _attach_byte7(z, t0):
    """Align the 0x14A byte-7 tap onto `raw14_*`.  ASSERTS the byte-4 columns agree elementwise."""
    tb4 = np.array(TAP14["b4"], int)
    tb7 = np.array(TAP14["b7"], int)
    tt = np.array(TAP14["t"], float) - t0
    r14b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    r14t = np.asarray(z["raw14_t"], float)
    rep = dict(n_tap=int(len(tb4)), n_raw14=int(len(r14b4)),
               dlc_hist_all_0x14A={int(k): int(v) for k, v in sorted(TAP14_ALL_DLC.items())},
               dlc_hist_tapped={int(k): int(v) for k, v in
                                sorted(Counter(TAP14["dlc"]).items())},
               byte7_present=bool(len(tb7) and (tb7 >= 0).all()))
    assert len(tb4) == len(r14b4), (
        f"byte7 tap length {len(tb4)} != extractor raw14 length {len(r14b4)} -- the tap filter "
        f"has drifted from the extractor's")
    assert bool(np.all(tb4 == r14b4)), "byte7 tap byte-4 column disagrees with the extractor's"
    assert bool(np.allclose(tt, r14t, atol=0, rtol=0)), "byte7 tap timestamps disagree"
    rep["byte4_columns_identical"] = True
    b7u, b7c = np.unique(tb7, return_counts=True)
    rep["byte7_hist"] = {int(v): int(c) for v, c in zip(b7u, b7c)}
    print(f"  0x14A byte7 tap: {len(tb7):,} frames  DLC(all 0x14A)={rep['dlc_hist_all_0x14A']}  "
          f"byte4 columns identical to the extractor's: True")
    print("      byte7 histogram: " +
          "  ".join(f"0x{int(v):02X}:{int(c):,}" for v, c in zip(b7u, b7c))[:400])
    return tb7.astype(np.int16), rep


# ======================================================================================
def extract_route(route):
    global _TAP_ON
    _tap_reset()
    _TAP_ON = True
    D.extract(route)
    _TAP_ON = False
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    f = ROOT / cdir / f"{stem}.npz"
    z = dict(np.load(f, allow_pickle=True))
    t0 = float(z["t0_mono"][0])
    A = _tap_arrays(t0)
    print(f"\n  0x1AB FULL TAP, route {route} ({lab})")
    rep = _tap_report(f"r{route}", A, route)
    for k, v in A.items():
        z["ab_" + k] = v
    b7, b7rep = _attach_byte7(z, t0)
    z["raw14_b7"] = b7
    idx, r14rep = _row2raw14(z)
    z["row2raw14"] = idx
    print(f"  raw14 index map: rows {r14rep['n_rows']:,}  raw14 {r14rep['n_raw14']:,}  "
          f"lead {r14rep['lead']}  constant_lead_holds={r14rep['constant_lead_holds']}  "
          f"dup 0x14A timestamps {r14rep['dup_raw14_timestamps']:,}  "
          f"a searchsorted map would mispair {r14rep['searchsorted_would_mispair']:,} rows")
    np.savez_compressed(f, **z)
    rep["row2raw14"] = r14rep
    rep["byte7"] = b7rep
    (ROOT / cdir / f"{stem}_1ab.json").write_text(json.dumps(rep, indent=1, default=float))
    D.split(route)
    segs = {k: dict(complete_messages=v, truncated=k in TRUNCATED,
                    error=TRUNCATED.get(k, (0, None))[1]) for k, v in sorted(MSG_COUNT.items())}
    (ROOT / cdir / f"{stem}_segments.json").write_text(json.dumps(segs, indent=1))
    return rep


# ======================================================================================
#  IDENTITY -- parameter-free, single-frame.  THE PACKER RESIDUE IS THE PRIMARY LEG.
# ======================================================================================
def _residue_leg(mt):
    """P(wire mod 5 in {1,3,4}).  EXACTLY 0 under `sar 1`; large under `sar 3`."""
    mt = np.asarray(mt, int)
    nz = mt[mt > 0]                     # 0 is reachable under both; it carries no information
    r = nz % 5
    hist = {int(k): int(c) for k, c in zip(*np.unique(r, return_counts=True))}
    illegal = int(sum(hist.get(k, 0) for k in SAR1_ILLEGAL_RESIDUES))
    return dict(n_nonzero=int(len(nz)), residue_hist=hist,
                n_illegal_for_sar1=illegal,
                frac_illegal_for_sar1=float(illegal / len(nz)) if len(nz) else float("nan"))


def identity(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    field = (b4 >> 3) & 0x1F
    n = len(field)
    odd = (field & 1) == 1
    fu, fc = np.unique(field, return_counts=True)
    out = dict(route=route, build=lab, frames=int(n), all_odd=bool(odd.all()),
               n_even=int((~odd).sum()),
               field_hist={int(v): int(c) for v, c in zip(fu, fc)})
    print(f"\n  === IDENTITY, route {route} (expected {lab}): {n:,} 0x14A frames ===")
    print("    field = (byte4>>3)&0x1F histogram:")
    print("      " + "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(fu, fc)))
    print(f"    MAP VALIDATOR  b3 == 1 on every frame (all field values ODD): {out['all_odd']}"
          f"   even values: {out['n_even']:,}")

    # ---- LEG 1: the V90 cave (rules out V86B..V89)
    gate_ok = (b4 & M_B4) == 0
    v90 = np.isin(field, sorted(V90_V91_B4ZERO_SET))
    pre = np.isin(field, sorted(PRE_V90_ALPHABET))
    out["n_b4_zero"] = int(gate_ok.sum())
    out["frac_b4_zero"] = float(gate_ok.mean())
    out["n_v90v91_only_value"] = int(v90.sum())
    out["n_pre_v90_alphabet"] = int(pre.sum())
    print(f"    LEG 1  b4 == 0 (observer gate OK) : {out['n_b4_zero']:,} frames "
          f"({100*out['frac_b4_zero']:.4f} %)   <-- IMPOSSIBLE on V86B/V87/V88/V89")
    print(f"           field in the V90-cave-only set : {out['n_v90v91_only_value']:,}   "
          f"field in the pre-V90 alphabet: {out['n_pre_v90_alphabet']:,}")

    # ---- LEG 2: byte 7 must be STOCK (rules out V92)
    if "raw14_b7" in z.files:
        b7 = np.asarray(z["raw14_b7"], int) & 0xFF
        out["byte7_hi_nonzero_n"] = int(((b7 & 0xC0) != 0).sum())
        out["byte7_hi_nonzero_frac"] = float(((b7 & 0xC0) != 0).mean())
        b7u, b7c = np.unique(b7, return_counts=True)
        out["byte7_hist"] = {int(v): int(c) for v, c in zip(b7u, b7c)}
        print(f"    LEG 2  0x14A byte7[7:6] != 0 on {out['byte7_hi_nonzero_n']:,} frames "
              f"({100*out['byte7_hi_nonzero_frac']:.4f} %) -- MUST be 0 on V94 (only V92 writes it)")

    # ---- LEG 3: THE PACKER RESIDUE.  This is the one that separates V94 from V90/V91.
    mt = np.asarray(z["ab_mt"], int)
    leg3 = _residue_leg(mt)
    out["packer_residue"] = leg3
    out["mt_distinct"] = int(len(np.unique(mt)))
    out["mt_max"] = int(mt.max()) if len(mt) else -1
    out["mt_sat_n"] = int((mt >= WIRE_SAT).sum())
    out["mt_sat_frac"] = float((mt >= WIRE_SAT).mean()) if len(mt) else float("nan")
    print(f"    LEG 3  427 PACKER RESIDUE (the V94 discriminator, no free parameter)")
    print(f"           wire mod 5 histogram over {leg3['n_nonzero']:,} NONZERO frames: "
          + "  ".join(f"{k}:{v:,}" for k, v in sorted(leg3["residue_hist"].items())))
    print(f"           wire == 1, 3 or 4 (mod 5): {leg3['n_illegal_for_sar1']:,} frames "
          f"({100*leg3['frac_illegal_for_sar1']:.4f} %)")
    print(f"           `sar 1` (V94) predicts EXACTLY 0.  `sar 3` (V90/V91) predicts ~60 %.")
    print(f"           wire saturation (>= {WIRE_SAT}): {out['mt_sat_n']:,} frames "
          f"({100*out['mt_sat_frac']:.4f} %)  -- new failure mode under sar 1, |b26| >= 409")

    sar1 = leg3["n_illegal_for_sar1"] == 0 and leg3["n_nonzero"] > 200
    cave_ok = out["n_b4_zero"] > 0
    b7_ok = out.get("byte7_hi_nonzero_n", 0) == 0
    if sar1 and cave_ok and b7_ok:
        out["verdict"] = ("✅ V94 IS ON THE CAR -- the 427 packer is `sar 1` (zero illegal "
                          "residues), the cave is V90's, and byte 7 is stock.")
    elif not sar1:
        out["verdict"] = ("🛑 THE 427 PACKER IS NOT `sar 1` -- route 7d is NOT V94.  The illegal "
                          "residues below are arithmetically impossible for V94's packer.")
    else:
        out["verdict"] = ("⚠ PACKER says V94 but a supporting leg failed -- see LEG 1 / LEG 2. "
                          "Identity AMBIGUOUS; do not assume V94.")
    print(f"    VERDICT: {out['verdict']}")
    (ROOT / cdir / f"{stem}_identity.json").write_text(json.dumps(out, indent=1, default=float))
    return out


def identity_controls():
    """Run LEG 3 on routes 77 and 78 -- the POSITIVE CONTROLS for the residue test."""
    print("\n  === LEG-3 POSITIVE CONTROLS: the same statistic on known `sar 3` routes ===")
    res = {}
    for r in ("77", "78", "79"):
        _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[r]
        f = ROOT / cdir / f"{stem}.npz"
        if not f.exists():
            print(f"    route {r}: cache missing, skipped")
            continue
        z = np.load(f, allow_pickle=True)
        if "ab_mt" not in z.files:
            print(f"    route {r}: no 0x1AB tap in cache, skipped")
            continue
        leg = _residue_leg(np.asarray(z["ab_mt"], int))
        res[r] = dict(build=lab, **leg)
        print(f"    route {r} ({lab}, sar {'4' if r == '79' else '3'}): "
              f"illegal-for-sar1 residues {leg['n_illegal_for_sar1']:,} / {leg['n_nonzero']:,} "
              f"= {100*leg['frac_illegal_for_sar1']:.2f} %   hist "
              + "  ".join(f"{k}:{v:,}" for k, v in sorted(leg["residue_hist"].items())))
    return res


# ======================================================================================
#  PROBE HEALTH -- every rung's duty, engaged/manual, and by wheel rate
# ======================================================================================
RATE_BINS = [(0.0, 0.35), (0.35, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0),
             (13.0, 25.0), (25.0, 50.0), (50.0, 1e9)]


def health(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    # 🛑 SAFE PAIRING: (raw14_t, raw14_b4).  Never (t, raw14_b4).
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = (np.asarray(z["raw14_b7"], int) & 0xFF) if "raw14_b7" in z.files else None
    rt = np.asarray(z["t"], float)
    lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
    v = np.abs(np.interp(t14, rt, np.asarray(z["cs_v"], float)))
    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(rt)
    dt[dt <= 0] = np.median(dt[dt > 0]) if (dt > 0).any() else 0.01
    rate = np.interp(t14, rt, np.abs(np.gradient(ang) / dt))

    out = {"route": route, "build": lab, "n": int(len(b4)), "engaged_frac": float(lat.mean())}
    print(f"\n  === RUNG HEALTH, route {route} ({lab}, {len(b4):,} 0x14A frames, "
          f"{100*lat.mean():.2f} % engaged) ===")

    def _one(name, s):
        d = dict(all=float(s.mean()),
                 engaged=float(s[lat].mean()) if lat.sum() else float("nan"),
                 manual=float(s[~lat].mean()) if (~lat).sum() else float("nan"),
                 engaged_moving=float(s[lat & (v > 0.5)].mean())
                 if (lat & (v > 0.5)).sum() else float("nan"))
        d["interpretable"] = bool(0.0 < d["all"] < 1.0)
        by = {}
        for lo, hi in RATE_BINS:
            sel = lat & (rate >= lo) & (rate < hi)
            by[f"{lo}-{hi if hi < 1e9 else '+'}"] = dict(
                n=int(sel.sum()), duty=float(s[sel].mean()) if sel.sum() else float("nan"))
        d["by_rate_engaged"] = by
        out[name] = d
        flag = "" if d["interpretable"] else "   🛑 DEAD/RAILED -- NOT INTERPRETABLE"
        print(f"    {name:26s} all {d['all']:.4f}  engaged {d['engaged']:.4f}  "
              f"manual {d['manual']:.4f}  eng&moving {d['engaged_moving']:.4f}{flag}")
        print("        by |wheel rate| (engaged): " +
              "  ".join(f"{k}:{vv['duty']:.3f}(n={vv['n']:,})" for k, vv in by.items()))

    for name, m in BITNAMES[route].items():
        _one(name, (b4 & m) != 0)

    b6 = (b4 & M_B6) != 0
    b5 = (b4 & M_B5) != 0
    tab = {}
    for i in (0, 1):
        for j in (0, 1):
            sel = lat & (b6 == bool(i)) & (b5 == bool(j))
            tab[f"b6={i},b5={j}"] = dict(n=int(sel.sum()),
                                         frac=float(sel.sum() / max(1, lat.sum())))
    out["b6_b5_2x2_engaged"] = tab
    print("    (b6,b5) 2x2, ENGAGED: " + "  ".join(f"{k} {v['frac']:.4f}"
                                                   for k, v in tab.items()))
    if b7 is not None:
        out["byte7_hi_nonzero_frac"] = float(((b7 & 0xC0) != 0).mean())
        print(f"    ⊕ NEGATIVE CONTROL: 0x14A byte7[7:6] != 0 on "
              f"{100*out['byte7_hi_nonzero_frac']:.4f} % of frames -- MUST be 0.0000 % "
              f"(V94 does not write byte 7; only V92 ever did)")
    (ROOT / cdir / f"{stem}_health.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
#  EXPOSURE CENSUS -- verbatim from `decode/extract_r78_r79.py`
# ======================================================================================
SPEED_BANDS = [(0, 5), (5, 20), (20, 50), (50, 80), (80, 1e9)]
DT = 0.01


def _bands(vk, sel):
    return {f"{lo}-{hi if hi < 1e9 else '+'} km/h":
            dict(frames=int((sel & (vk >= lo) & (vk < hi)).sum()),
                 sec=float((sel & (vk >= lo) & (vk < hi)).sum() * DT))
            for lo, hi in SPEED_BANDS}


def census(route):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    C = ROOT / cdir
    z = np.load(C / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    seg = np.asarray(z["seg"], int)
    v = np.abs(np.asarray(z["cs_v"], float))
    vk = v * 3.6
    lat = np.asarray(z["cc_lat"], float) > 0.5
    n = len(t)
    dur = float(t[-1] - t[0])
    rate = (n - 1) / dur if dur > 0 else float("nan")

    out = {"route": route, "build": lab, "frames": n, "duration_s": dur,
           "row_rate_hz": float(rate),
           "engaged_frames": int(lat.sum()), "engaged_frac": float(lat.mean()),
           "engaged_sec": float(lat.sum() * DT), "engaged_min": float(lat.sum() * DT / 60.0),
           "manual_frames": int((~lat).sum()), "manual_sec": float((~lat).sum() * DT)}
    print(f"\n  === EXPOSURE CENSUS, route {route} ({lab}) ===")
    print(f"    {n:,} frames   {dur:.1f} s ({dur/60:.2f} min)   row grid {rate:.2f} Hz")
    print(f"    ENGAGED {out['engaged_frac']*100:.2f}%  =  {out['engaged_sec']:.1f} s "
          f"({out['engaged_min']:.2f} min)      MANUAL {out['manual_sec']:.1f} s")

    for tag, sel in (("all", np.ones(n, bool)), ("engaged", lat), ("manual", ~lat)):
        if not sel.sum():
            continue
        q = {p: float(np.percentile(vk[sel], p)) for p in (50, 90, 99)}
        out[f"speed_{tag}"] = dict(n=int(sel.sum()), median_kmh=q[50], p90_kmh=q[90],
                                   p99_kmh=q[99], max_kmh=float(vk[sel].max()))
        out[f"bands_{tag}"] = _bands(vk, sel)
        print(f"    {tag:8s} v median {q[50]:6.2f}  p90 {q[90]:6.2f}  p99 {q[99]:6.2f}  "
              f"max {vk[sel].max():6.2f} km/h")
        print("             " + "  ".join(f"{k}: {d['sec']:7.1f}s"
                                          for k, d in out[f"bands_{tag}"].items()))

    hi = lat & (vk >= 50)
    out["engaged_sec_ge_50kmh"] = float(hi.sum() * DT)
    out["engaged_sec_ge_80kmh"] = float((lat & (vk >= 80)).sum() * DT)
    print(f"    🛑 ENGAGED >= 50 km/h : {out['engaged_sec_ge_50kmh']:.1f} s   "
          f">= 80 km/h : {out['engaged_sec_ge_80kmh']:.1f} s")

    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(t)
    dt[dt <= 0] = np.median(dt[dt > 0]) if (dt > 0).any() else 0.01
    rate_dps = np.abs(np.gradient(ang) / dt)
    for lo, hi_, tag in ((1.0, 13.0, "micro_ratchet_1_13dps"),
                         (13.0, 50.0, "ratchet_13_50dps"),
                         (50.0, 1e9, "macro_gt50dps")):
        m = lat & (rate_dps >= lo) & (rate_dps < hi_)
        out[f"rate_{tag}_sec"] = float(m.sum() * DT)
        mm = (~lat) & (rate_dps >= lo) & (rate_dps < hi_)
        out[f"rate_{tag}_sec_manual"] = float(mm.sum() * DT)
    print(f"    RATE REGIMES engaged: micro (1-13 °/s) "
          f"{out['rate_micro_ratchet_1_13dps_sec']:.1f} s"
          f"   ratchet (13-50) {out['rate_ratchet_13_50dps_sec']:.1f} s"
          f"   macro (>50) {out['rate_macro_gt50dps_sec']:.1f} s")
    print(f"    RATE REGIMES manual : micro {out['rate_micro_ratchet_1_13dps_sec_manual']:.1f} s"
          f"   ratchet {out['rate_ratchet_13_50dps_sec_manual']:.1f} s"
          f"   macro {out['rate_macro_gt50dps_sec_manual']:.1f} s")

    # ---- grind #2's regime, the one STATE.md §F calls essentially unexposed
    g2 = lat & (v >= 22.2) & (rate_dps >= 5.0)
    out["grind2_regime_sec"] = float(g2.sum() * DT)
    print(f"    🛑 GRIND-#2 REGIME (engaged, v>=22.2 m/s = 80 km/h, |rate|>=5 °/s): "
          f"{out['grind2_regime_sec']:.1f} s")

    man = ~lat
    for thr in (0.1, 0.2, 0.5):
        out[f"manual_parked_frac_lt_{thr}"] = (float((man & (v < thr)).mean() / man.mean())
                                               if man.sum() else float("nan"))
    print(f"    manual frames PARKED: v<0.1 {100*out['manual_parked_frac_lt_0.1']:.1f}%   "
          f"v<0.2 {100*out['manual_parked_frac_lt_0.2']:.1f}%   "
          f"v<0.5 {100*out['manual_parked_frac_lt_0.5']:.1f}%")

    ep, cur = [], 0
    for x in lat:
        if x:
            cur += 1
        else:
            if cur:
                ep.append(cur)
            cur = 0
    if cur:
        ep.append(cur)
    eps = np.array(ep, float) * DT
    out["episodes"] = dict(n=int(len(eps)), n_ge_2s=int((eps >= 2).sum()),
                           n_ge_10s=int((eps >= 10).sum()),
                           longest_s=float(eps.max()) if len(eps) else 0.0,
                           median_s=float(np.median(eps)) if len(eps) else 0.0)
    print(f"    engagement episodes: {out['episodes']['n']} total, "
          f"{out['episodes']['n_ge_2s']} >=2 s, {out['episodes']['n_ge_10s']} >=10 s, "
          f"longest {out['episodes']['longest_s']:.1f} s")

    # ---- MANUAL HANDS-OFF COAST census -- STATE.md §C's gating experiment
    press = np.asarray(z["cs_press"], float) > 0.5
    brake = np.asarray(z["cs_brake"], float) > 0.5
    coast = (~lat) & (~press) & (~brake) & (v > 8.0) & (rate_dps < 3.0)
    cr, cur = [], 0
    for x in coast:
        if x:
            cur += 1
        else:
            if cur:
                cr.append(cur)
            cur = 0
    if cur:
        cr.append(cur)
    cr = np.array(cr, float) * DT
    out["manual_handsoff_coast"] = dict(
        total_sec=float(coast.sum() * DT), n_runs=int(len(cr)),
        n_runs_ge_5s=int((cr >= 5).sum()), n_runs_ge_15s=int((cr >= 15).sum()),
        longest_s=float(cr.max()) if len(cr) else 0.0)
    ch = out["manual_handsoff_coast"]
    print(f"    ★ MANUAL HANDS-OFF COAST (manual, !pressed, !brake, v>8 m/s, |rate|<3 °/s): "
          f"{ch['total_sec']:.1f} s in {ch['n_runs']} runs "
          f"({ch['n_runs_ge_5s']} >=5 s, {ch['n_runs_ge_15s']} >=15 s, "
          f"longest {ch['longest_s']:.1f} s)")

    persec = {}
    print(f"\n    {'seg':>4} {'frames':>8} {'sec':>7} {'v med':>7} {'v p90':>7} {'v max':>7} "
          f"{'eng%':>6} {'eng s':>7} {'eng>=50':>8} {'park%':>6}")
    for s in sorted(set(seg.tolist())):
        m = seg == s
        e = m & lat
        d = dict(frames=int(m.sum()), sec=float(m.sum() * DT),
                 v_median_kmh=float(np.median(vk[m])), v_p90_kmh=float(np.percentile(vk[m], 90)),
                 v_max_kmh=float(vk[m].max()),
                 engaged_frac=float(lat[m].mean()), engaged_sec=float(e.sum() * DT),
                 engaged_sec_ge_50=float((e & (vk >= 50)).sum() * DT),
                 engaged_sec_ge_80=float((e & (vk >= 80)).sum() * DT),
                 parked_frac=float((v[m] < 0.2).mean()))
        d["bands_engaged"] = _bands(vk, e)
        persec[int(s)] = d
        print(f"    {s:>4} {d['frames']:>8,} {d['sec']:>7.1f} {d['v_median_kmh']:>7.2f} "
              f"{d['v_p90_kmh']:>7.2f} {d['v_max_kmh']:>7.2f} {100*d['engaged_frac']:>5.1f}% "
              f"{d['engaged_sec']:>7.1f} {d['engaged_sec_ge_50']:>8.1f} "
              f"{100*d['parked_frac']:>5.1f}%")
    out["per_segment"] = persec

    ev = json.loads((C / f"{stem}_events.json").read_text())
    cnt = Counter(e["name"] for e in ev)
    out["events"] = dict(cnt)
    out["events_immediate"] = dict(Counter(e["name"] for e in ev if e.get("immediate")))
    out["events_soft"] = dict(Counter(e["name"] for e in ev if e.get("soft")))
    out["sentinels"] = dict(a14=int(z["sentinels"][0]), a18=int(z["sentinels"][1]))
    b0 = np.asarray(z["raw1ab_b0"], int)
    dtc = (b0 >> 2) & 1
    out["dtc_bit2_duty"] = float(dtc.mean()) if len(dtc) else float("nan")
    out["dtc_bit2_transitions"] = int(np.sum(np.diff(dtc) != 0)) if len(dtc) > 1 else 0
    if "ab_output_disabled" in z.files:
        out["output_disabled_duty"] = float(np.asarray(z["ab_output_disabled"], int).mean())
        out["config_valid_duty"] = float(np.asarray(z["ab_config_valid"], int).mean())
    st = np.asarray(z["raw18_st"], int)
    out["steer_status_hist"] = {int(k): int(c) for k, c in zip(*np.unique(st, return_counts=True))}
    print(f"\n    onroadEvents ({len(ev)} total): " +
          ", ".join(f"{k}:{c}" for k, c in cnt.most_common()))
    print(f"    sentinels 0x14A {out['sentinels']['a14']}  0x18F {out['sentinels']['a18']}   "
          f"DTC bit2 duty {out['dtc_bit2_duty']:.5f} ({out['dtc_bit2_transitions']} transitions)")
    print(f"    STEER_STATUS hist {out['steer_status_hist']}")
    if "output_disabled_duty" in out:
        print(f"    OUTPUT_DISABLED duty {out['output_disabled_duty']:.5f}   "
              f"CONFIG_VALID duty {out['config_valid_duty']:.5f}")
    (C / f"{stem}_census.json").write_text(json.dumps(out, indent=1, default=float))
    return out


# ======================================================================================
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        extract_route("7d")
        identity("7d")
        identity_controls()
        health("7d")
        census("7d")
    else:
        fn = {"extract": extract_route, "identity": identity, "health": health,
              "census": census, "controls": lambda _r: identity_controls()}[args[0]]
        for r in (args[1:] or ["7d"]):
            fn(r)
