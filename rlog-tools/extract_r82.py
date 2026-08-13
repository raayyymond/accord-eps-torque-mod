#!/usr/bin/env python3
r"""Extract route `82` -- THE V99 FLIGHT -- into `analysis-2020accord/_cache_r82/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  Like `extract_r80.py` / `extract_r81.py`, this file only
adds a row to the shared `ROUTES` table and calls `extract_r7d`'s `extract_route()` -- the SAME
code that wrote every cache since `_cache_r6d/`.  Field names, ZOH/interp convention, sentinel
definition and `PASS_1D` are bit-for-bit the ones every prior route was scored with.

===================================================================================================
ROUTE 82 == V99.  V98 BASE + 3 calibration/immediate bytes.  The CAVE IS BYTE-IDENTICAL except b5.
===================================================================================================
    byte4 b7 0x80 = gp-0x6b70 < 0                      V96's rung, byte-identical since V96
    byte4 b6 0x40 = |gp-0x6bfe| >= |gp-0x374c>>4|      ⭐ MODEL   vs ACTUAL -- THE PRIMARY INSTRUMENT
    byte4 b5 0x20 = 🛑 HARD-WIRED CONSTANT 1           ⭐ THE BUILD IDENTITY (was V98's REQUEST cmp)
    byte4 b4 0x10 = (gp-0x374c>>4) < 0                 the converse positive control
    byte4 b3 0x08 = gp-0x6752 >= 0                     the polarity constant's SIGN (V98: const 0)
    byte7[7:6]    = 2  (byte7 & 0xC0 == 0x80)          carried from V98 -- NO LONGER DISCRIMINATING

    427 (0x1AB) = clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF)  -- V96/V97/V98's packer, UNTOUCHED
                  => counts = wire * 64/5

🛑 **THE ~50-BUILD "byte4[7:3] IS ALWAYS ODD" CONVENTION DOES NOT HOLD.**  `b3` is a MEASURAND and
   `b5` is now a hard-wired 1, so byte4[7:3] == V98's field + 4 on every frame.  Liveness is
   byte7 + the b5 duty, NOT field parity.

🛑 **IDENTITY RULE, PRE-REGISTERED (`build_v99_tva.py` line ~159):**
       b5 duty >= 0.999 over the whole route  AND  byte7[7:6] == 2 at duty 1.0000.
   V98 measured b5 duty 0.0022 over 17,982 frames.  IF THE IDENTITY RULE FAILS, NOTHING IN THE
   READOUT MAY BE REPORTED.

🛑 **PRE-REGISTERED b6 EXCLUSION, carried from V98.**  `FUN_0003bc20` plausibility-latches
   `gp-0x6bfe` to `0x7FFF` when |model| > 20000; in that state b6 reads TRUE for an unrelated
   reason.  The latch rails `gp-0x6b70`, so **CAN 427 pins at exactly 1023** on those frames.
   Score b6 only on frames with `ab_mt != 1023`, and report the excluded count.
   (Prior: 0 / 87,423 frames on routes 7e/7f/80, 0 / 8,991 on route 81.)

🛑 **PAIRING CONVENTION PRODUCED BY THIS EXTRACTOR (asserted at the bottom of `extract_route`):**
       t == raw14_t[1:]   and   probe == raw14_b4[1:]   and   probe == raw14_b4[row2raw14]
   ⇒ **SAFE PAIRS: (t, probe) or (raw14_t, raw14_b4).**  Pairing `t` with `raw14_b4` reads the
   cave byte ~10 ms early = 28 deg of phase at 7.79 Hz.

Usage:
    python extract_r82.py                 # extract + identity + health + census
    python extract_r82.py extract 82
    python extract_r82.py identity 82
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
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402  -- installs the taps; brings D + rlog_parse with it

D = X.D

NEW = {
    "82": ("75604b0a432fdc89_00000082--e30d55731b", 2, "analysis-2020accord/_cache_r82",
           "r82s", "r82", "V99"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v
D.ROUTES.setdefault("81", ("75604b0a432fdc89_00000081--c7103d2cb4", 3,
                           "analysis-2020accord/_cache_r81", "r81s", "r81", "V98"))
D.ROUTES.setdefault("80", ("75604b0a432fdc89_00000080--6c8b103892", 2,
                           "analysis-2020accord/_cache_r80", "r80s", "r80", "V97"))

# V99 carries V96/V97/V98's 427 spec verbatim: gp-0x6b70, `sar 6`, magnitude + sign bit on byte4 b7.
for _k in NEW:
    X.WIRE_SCALE[_k] = 64.0 / 5.0
    X.WIRE_SOURCE[_k] = ("gp-0x6b70 (PID reference lane), sar 6  "
                         "[V96/V97/V98/V99 spec, UNTOUCHED]")
X.WIRE_SCALE.setdefault("81", 64.0 / 5.0)
X.WIRE_SOURCE.setdefault("81", "gp-0x6b70 (PID reference lane), sar 6")
X.WIRE_SCALE.setdefault("80", 64.0 / 5.0)
X.WIRE_SOURCE.setdefault("80", "gp-0x6b70 (PID reference lane), sar 6")

# ---- V99's byte-4 map, read off `build_v99_tva.py`'s PAYLOAD, not inferred.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
X.BITNAMES["82"] = {
    "b7_sign_6b70_neg": M_B7,          # gp-0x6b70 < 0
    "b6_MODEL_ge_ACTUAL": M_B6,        # |gp-0x6bfe| >= |gp-0x374c>>4|
    "b5_IDENTITY_const1": M_B5,        # 🛑 hard-wired 1 on V99
    "b4_sign_374c_neg": M_B4,          # (gp-0x374c>>4) < 0
    "b3_pol_6752_ge0": M_B3,           # gp-0x6752 >= 0
}
X.BITNAMES.setdefault("81", {"b7_sign_6b70_neg": 0x80, "b6_MODEL_ge_ACTUAL": 0x40,
                             "b5_REQUEST_ge_ACTUAL": 0x20, "b4_sign_374c_neg": 0x10,
                             "b3_pol_6752_ge0": 0x08})

IDENT_MASK, IDENT_CODE2 = 0xC0, 0x80      # byte7[7:6] == 2  ⇒  byte7 & 0xC0 == 0x80
LATCH_WIRE = 1023                         # 427 == 1023 ⇒ the observer plausibility latch fired


# ======================================================================================
#  IDENTITY -- the PRE-REGISTERED RULE.  b5 duty >= 0.999 AND byte7[7:6] == 2 at duty 1.0000.
# ======================================================================================
def identity(route="82"):
    _pref, _n, cdir, _pfx, stem, lab = D.ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    b7 = np.asarray(z["raw14_b7"], int) & 0xFF
    n = len(b4)
    code = (b7 & IDENT_MASK) >> 6
    cu, cc = np.unique(code, return_counts=True)
    duty2 = float((code == 2).mean())
    b5 = ((b4 & M_B5) != 0)
    b5_duty = float(b5.mean())
    field = (b4 >> 3) & 0x1F
    fu, fc = np.unique(field, return_counts=True)

    ok_b7 = duty2 >= 0.9999
    ok_b5 = b5_duty >= 0.999
    out = dict(route=route, build=lab, frames=int(n),
               byte7_code_hist={int(v): int(c) for v, c in zip(cu, cc)},
               byte7_code2_duty=duty2, byte7_code2_frames=int((code == 2).sum()),
               b5_duty=b5_duty, b5_zero_frames=int((~b5).sum()),
               byte4_field_hist={int(v): int(c) for v, c in zip(fu, fc)},
               pre_registered_rule="b5 duty >= 0.999 AND byte7[7:6] == 2 at duty 1.0000",
               ok_byte7=bool(ok_b7), ok_b5=bool(ok_b5), identity_pass=bool(ok_b7 and ok_b5))

    print(f"\n  === IDENTITY, route {route} (expected {lab}): {n:,} 0x14A frames ===")
    print("    byte7[7:6] code histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(cu, cc)))
    print(f"    byte7[7:6] == 2 duty = {duty2:.6f}  ({out['byte7_code2_frames']:,} frames)")
    print(f"    ⭐ b5 duty = {b5_duty:.6f}   ({out['b5_zero_frames']:,} frames with b5 == 0)"
          f"   -- V99 hard-wires 1; V98 MEASURED 0.0022")
    print("    byte4 field = (byte4>>3)&0x1F histogram: " +
          "  ".join(f"{int(v)}:{int(c):,}" for v, c in zip(fu, fc)))

    if out["identity_pass"]:
        out["verdict"] = ("✅ V99 IS ON THE CAR -- b5 duty >= 0.999 (V98 measured 0.0022 on the "
                          "byte-identical rung) AND byte7[7:6] == 2 at duty 1.0000.")
    elif not ok_b7:
        out["verdict"] = (f"🛑 IDENTITY FAILS -- byte7[7:6] == 2 duty {duty2:.6f} < 1.0000. "
                          f"NOTHING IN THE READOUT MAY BE REPORTED.")
    else:
        out["verdict"] = (f"🛑 IDENTITY FAILS -- b5 duty {b5_duty:.6f} < 0.999.  This is V98's "
                          f"measured comparator, not V99's constant.  NOTHING IN THE READOUT MAY "
                          f"BE REPORTED.")
    print(f"    VERDICT: {out['verdict']}")
    (ROOT / cdir / f"{stem}_identity.json").write_text(json.dumps(out, indent=1, default=float))
    return out


def health(route="82"):
    return X.health(route)


def census(route="82"):
    return X.census(route)


def extract_route(route="82"):
    return X.extract_route(route)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        extract_route("82")
        identity("82")
        health("82")
        census("82")
    else:
        fn = {"extract": extract_route, "identity": identity, "health": health,
              "census": census}[args[0]]
        for r in (args[1:] or ["82"]):
            fn(r)
