#!/usr/bin/env python3
"""Extract route `54` (**V71B**, segments 0-20) to .npz caches. THE CANONICAL ROUTE-54 EXTRACTOR.

Route `75604b0a432fdc89_00000054--4e67ae1164`, segments 0..20 -- 21 segments, a LONG route, unlike
route 50's 181 s. Treat its highway exposure as real and score grind #2 at speed separately.

🛑 ONE ROUTE, ONE EXTRACTOR. Two agents once wrote `extract/extract_r4f_cache.py` and `r4f_extract_cache.py`
in the same session, both writing `_scratch/cache/r4f/r4fs*.npz` with DIFFERENT field sets, and whichever
ran last silently dropped the other's channels. If you need a variant, add a flag, not a file.

Every non-probe channel is byte-for-byte `extract/extract_r50_cache.py`'s, so `_grind2_lib.wrecs`,
`_r31_common.load` and `_r4f_lib.avg_periodogram` read this cache with the identical instrument they
read every prior route with. The ONE substantive change is the byte4 decoder, which is
BUILD-SPECIFIC and here carries **V71B's**.

THE BUILD ON THIS ROUTE
-----------------------
    39990-TVA,A160-V71B-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-gainA-rec0rec1-x2-
    SPEEDSHAPED-sarSTOCK-probe2-671d-67fa4-6adcABS128-sign-can330byte4-0x13000-0x100000.rwd

V71B doses **r26 ALONE**: `sar` sites STOCK (r24 fully byte-stock), `gain_A` rec0/rec1 Y[0..3]
doubled, giving 2.000000x at <= 10 km/h tapering to EXACTLY 1.000000x at >= 50 km/h. It also
restores V42's state-4 governor kill (0x454FE bne->br), which is what bit5 measures the
counterfactual of.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
----------------------------------------
    bit7 = 1                     LIVENESS. field == 0 => the cave did not fire => the frame is VOID.
    bit6 = gp-0x671d != 0        THE MASK. Which gain arm is in force; it OUTRANKS every other arm.
                                 📋 PRE-REGISTERED PREDICTION: reads 0 (V64: 0; V67: 0/186,321).
    bit5 = gp-0x67fa == 4        THE RATCHET STATE. V71B DISABLES the substitution, so this rung is
                                 the counterfactual: how often stock/V53-V70 WOULD have ratcheted.
                                 🛑 `gp-0x67fa` is NOT the bus STEER_STATUS. Never cross-read them.
    bit4 = |gp-0x6adc| >= 128    THE POSITIVE CONTROL, TWO-SIDED. See the asymmetry note below.
    bit3 = gp-0x6adc >= 0        THE SIGN. Read WITH bit4: side AND magnitude.
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved.

🛑🛑 **bit4/bit3 WATCH `gp-0x6ADC` -- r26's OWN post-clip mirror, NOT r24's `gp-0x6ada`.**
This is the ONE place a V71B reader goes wrong, and `rlog-tools/probe/decode_v71_probe.py`'s prose has a
STALE paragraph (its "the one-byte fix was NOT applied") that says otherwise. The executable record
disagrees with that prose and wins:
  * `builds/v50_v79/build_v71b_tva.py:194`  `MIRROR = A.R26_MIRROR_DISP`  (0x6ADC, `st.h r26,-0x6adc[gp]` @0x3AD4E)
  * `builds/v50_v79/build_v71b_tva.py:531`  asserts `code[CAVE_BASE + 0x1A] == 0x24` (V71A's is 0x26)
  * the .rwd TAG itself carries `6adcABS128`, not `6adaABS128`
  * `decode_v71_probe.BUILDS["v71b"]` -> `cell=0x6ADC, lane="r26"`, and its CAVE_HEX_B[0x1A] == 0x24
`_assert_mirror_byte()` below re-reads CAVE_HEX_B out of the decoder's source at import time and
fails this extractor if that byte ever stops being 0x24 -- so the cell cannot drift silently.
⇒ **V71B's bit4 is the ONLY reading in the kit that bounds `avg(gp-0x69a4)`** (|r26| >= 128 at
  gain_A 3072 implies |dtorque| * avg >= 43,690), and it is NOT comparable to V71A's or V71C's bit4,
  which watch r24 on a different scale.

⚠ THE ONE-COUNT ASYMMETRY, because it is real and must not be glossed:

        bit4  =  (gp-0x6adc >= +128)  OR  (gp-0x6adc <= -129)

`sar` FLOORS, so `x sar 7 == -1` spans x in [-128,-1] and no single shifted compare can split
x = -128 from x = -127. The negative arm therefore trips at -129. That is |x| >= 128 for every value
EXCEPT x == -128 exactly -- one count out of a +/-8192 lane. `_self_check()` below proves it
exhaustively over all 65,536 halfword patterns rather than asserting it in prose.

🛑 V71's FOUR RUNGS ARE INDEPENDENT. All 16 payloads are reachable and NONE is forbidden. V70's
order invariant (`bit6 => bit3`, because x >= +512 implies x >= 0) DOES NOT APPLY here and is not
ported: there is no `order_viol` channel in this cache, and writing one full of zeros would have
asserted an invariant this build does not carry. Likewise there is no `sign_agree` channel -- on
V70 that compared TWO cells (r26's sign vs r24's), but V71's bit4 and bit3 read the SAME cell, so
their agreement is arithmetic, not evidence. Identification is by the .rwd FILENAME.

RPM (0x17C bytes 2:3, big-endian, src 1) is pulled in the SAME pass -- the engine-order veto needs
it and a second walk over 21 x ~11 MB segments is pure cost.

★ SAMPLE RATE comes from `_r4f_lib.fs_lattice`, never `1/median(dt)`. CAN frames are timestamped per
LOG PACKET, so several share a timestamp and the legacy estimator is biased HIGH by a
ROUTE-DEPENDENT ~1.3% -- three quarters of a bin at 21 Hz, sitting between the arms of exactly the
cross-build contrast this route exists to serve.

Usage:  python extract/extract_r54_cache.py            # all 21 segments
        python extract/extract_r54_cache.py 0 1        # chosen segments
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
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))
from rlog_parse import read_messages          # noqa: E402
from _r4f_lib import fs_lattice, install_fs   # noqa: E402  -- the ONE owner of the fs estimator

install_fs()

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000054--4e67ae1164"
SEGS = list(range(21))
OUT = Path(os.environ.get("R54_CACHE", ROOT / "_scratch/cache/r54"))
PFX = "r54s"

BUILD = "V71B"
RWD_NAME = ("39990-TVA,A160-V71B-LKAS-4x-mss0-decouple0xC646C-RESTORE-0x454FE-gainA-rec0rec1-x2-"
            "SPEEDSHAPED-sarSTOCK-probe2-671d-67fa4-6adcABS128-sign-can330byte4-"
            "0x13000-0x100000.rwd")
# 🛑 THE MIRROR CELL bit4/bit3 WATCH. V71B = r26 = 0x6ADC. Asserted against the decoder's CAVE_HEX_B
# at import time by `_assert_mirror_byte()`; do not edit this without editing the build.
MIRROR_CELL = 0x6ADC
MIRROR_LANE = "r26"

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

BIT_LIVE = 0x80
BIT_MASK671D = 0x40           # bit6  gp-0x671d != 0        THE MASK -- outranks every arm
BIT_STATE4 = 0x20             # bit5  gp-0x67fa == 4        THE RATCHET STATE this build disables
BIT_ABS = 0x10                # bit4  |gp-0x6adc| >= 128    THE POSITIVE CONTROL, TWO-SIDED
BIT_SIGN = 0x08               # bit3  gp-0x6adc >= 0        THE SIGN
PROBE_MASK = 0xF8
THRESHOLD = 128
NEG_THRESHOLD = -129          # ⚠ `sar` FLOORS: the NEGATIVE arm trips at -129, not -128.
STATE_VALUE = 4

# ⚠ ALL SIXTEEN are legal -- the rungs are INDEPENDENT. This is a liveness test, nothing more.
LEGAL_FIELD = {BIT_LIVE | a | b | c | d
               for a in (0, BIT_MASK671D) for b in (0, BIT_STATE4)
               for c in (0, BIT_ABS) for d in (0, BIT_SIGN)}
assert len(LEGAL_FIELD) == 16, "V71's rungs are independent -- all 16 payloads must be legal"
assert BIT_LIVE | BIT_MASK671D | BIT_STATE4 | BIT_ABS | BIT_SIGN == PROBE_MASK
assert PROBE_MASK & 0x07 == 0, "the probe bits collide with STEER_SENSOR_STATUS"


def wire_byte4(v671d, v67fa, vmirror, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order.

    0xC4B34 movea 0x10,r0,r7 / ld.bu -0x671d[gp],r6 / cmp 0x1 / blt / add 0x8 ...
    """
    r7 = 0x10                                       # movea 0x10,r0,r7      -> bit7 LIVENESS
    if not ((v671d & 0xFF) < 1):                    # cmp 0x1,r6 ; blt +4
        r7 += 0x08                                  # bit6
    if not ((v67fa & 0xFF) != STATE_VALUE):         # cmp 0x4,r6 ; bne +4
        r7 += 0x04                                  # bit5
    x = (vmirror - 0x10000) if vmirror & 0x8000 else vmirror
    s = x >> 7                                      # ld.h ; sar 0x7   (Python >> floors == `sar`)
    if (s >= 1) or not (s >= -1):                   # cmp 0x1 ; bge SET ; cmp -0x1 ; bge SKIP ; SET
        r7 += 0x02                                  # bit4
    if not (s < 0):                                 # cmp r0,r6 ; blt +4
        r7 += 0x01                                  # bit3
    return ((r7 << 3) & 0xFF) | (status_bits & 0x07)


def _assert_mirror_byte():
    """🛑 THE MECHANICAL LINK TO THE IMAGE. Re-read CAVE_HEX_B out of the decoder's SOURCE (the same
    way `builds/v50_v79/build_v71b_tva.py` does) and fail if cave+0x1A is not 0x24 = `ld.h -0x6adc[gp],r6`.

    Read by REGEX, not by import, so this cannot be defeated by the decoder's stale prose and does
    not drag in its import chain. If this ever fires, the cache would have been labelled with the
    wrong lane -- which is the exact defect that ran for four builds.
    """
    src = (ROOT / "rlog-tools" / "probe/decode_v71_probe.py").read_text(encoding="utf-8")
    m = re.search(r'^CAVE_HEX_B\s*=\s*"([0-9a-f]+)"', src, re.M)
    assert m, "CAVE_HEX_B not found in probe/decode_v71_probe.py -- cannot verify the mirror cell"
    raw = bytes.fromhex(m.group(1))
    assert len(raw) == 68, f"CAVE_HEX_B is {len(raw)} bytes, expected the 68-byte cave"
    assert raw[0x18:0x1A] == bytes.fromhex("2437"), "cave+0x18 is not an `ld.h ...,r6`"
    want = ((0x10000 - MIRROR_CELL) & 0xFFFF).to_bytes(2, "little")
    assert raw[0x1A:0x1C] == want, (
        f"CAVE_HEX_B's mirror load does not carry -0x{MIRROR_CELL:04x} "
        f"(got {raw[0x1A:0x1C].hex()}, want {want.hex()}) -- V71B watches r26, NOT r24")
    assert raw[0x1A] == 0x24, "V71B's mirror byte must be 0x24 (gp-0x6adc); 0x26 is V71A/V71C's"
    assert raw[28:30] == bytes.fromhex("a732"), \
        "cave+28 is not `sar 0x7,r6` -- a932 would be V71's FIRST CUT, which read ZERO on two routes"
    for off, want_hw, what in ((32, "be05", "bge +6 (bit4 POSITIVE bound)"),
                               (36, "ae05", "bge +4 (bit4 NEGATIVE bound)"),
                               (20, "aa05", "bne +4 (bit5 state-4)"),
                               (42, "a605", "blt +4 (bit3 SIGN)")):
        assert raw[off:off + 2] == bytes.fromhex(want_hw), \
            f"cave+{off} is not {want_hw} ({what}) -- a wrong condition nibble INVERTS the rung"


def _self_check():
    """The payload claims as executable assertions, including the one-count asymmetry."""
    def s16(r):
        return r - 0x10000 if r & 0x8000 else r
    assert wire_byte4(0, 0, 0) & PROBE_MASK == BIT_LIVE | BIT_SIGN, \
        "an all-zero input is not `liveness + sign` (0 is >= 0, so bit3 fires)"
    assert wire_byte4(1, 0, 0) & BIT_MASK671D and not wire_byte4(0, 0, 0) & BIT_MASK671D
    assert wire_byte4(0, STATE_VALUE, 0) & BIT_STATE4, "bit5 does not fire on state 4"
    assert not wire_byte4(0, 10, 0) & BIT_STATE4, "bit5 fires on state 10 -- that is V70's rung"
    # ---- the VECTORISED decode this file actually uses, against the instruction model, over ALL
    # ---- 65,536 halfword patterns. Two independent methods, which is what the kit requires.
    r = np.arange(0x10000, dtype=np.int32)
    x = np.where(r & 0x8000, r - 0x10000, r).astype(np.int32)
    s = x >> 7                                      # numpy `>>` on signed ints IS arithmetic
    vec_abs = (s >= 1) | (s < -1)
    vec_sign = s >= 0
    ref = np.array([wire_byte4(0, 0, int(v)) for v in r], dtype=np.int32)
    assert np.array_equal(vec_abs, (ref & BIT_ABS) != 0), "the vectorised bit4 differs from the cave"
    assert np.array_equal(vec_sign, (ref & BIT_SIGN) != 0), "the vectorised bit3 differs"
    assert np.array_equal(vec_abs, (x >= THRESHOLD) | (x <= NEG_THRESHOLD))
    mismatch = set(x[vec_abs != (np.abs(x) >= THRESHOLD)].tolist())
    assert mismatch == {-THRESHOLD}, \
        f"bit4 differs from |x| >= {THRESHOLD} at {sorted(mismatch)[:6]}, expected exactly " \
        f"{{{-THRESHOLD}}} -- `sar` floors and that is the ONLY value it can miss"
    for status in range(8):
        assert wire_byte4(0xFF, STATE_VALUE, 0x7FFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"


_assert_mirror_byte()
_self_check()


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def held_last(t_out, t_in, v_in, fill):
    """Zero-order hold. For CATEGORICAL channels; np.interp would fabricate intermediate codes."""
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    idx = np.searchsorted(np.asarray(t_in), t_out, side="right") - 1
    out = np.where(idx < 0, fill, np.asarray(v_in, float)[np.clip(idx, 0, None)])
    return out.astype(float)


def extract(paths, tag, t0=None):
    rows, e4hist, events = [], [], []
    last18, lastE4 = None, (0.0, 0)
    raw = {0x14A: [], 0x18F: [], 0x1FA: [], 0x0E4: []}
    # 🛑 INDEPENDENT SECOND METHOD for the STEER_STATUS census and the byte4 histogram: every
    # 0x18F / 0x14A src-1 frame exactly as it arrived, no hold, no grid.
    raw18_st, raw14_b4 = [], []
    rpm_t, rpm_v = [], []
    cs = {"t": [], "v": [], "eng": [], "ang": [], "tq": [], "press": [], "gear": [], "std": [],
          "lblink": [], "rblink": []}
    cc = {"t": [], "lat": [], "en": [], "req": []}
    clk = {"t": [], "w": []}
    init_wall = []
    snd = {"t": [], "sp": [], "spw": []}

    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    src, addr = int(m.src), int(m.address)
                    d = bytes(m.dat)
                    if src == 1 and addr in raw:
                        raw[addr].append(tm)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        raw18_st.append((d[4] >> 4) & 0x0F)
                        last18 = (i16be(d, 0) * -1.0, i16be(d, 2) * -0.1,
                                  (d[4] >> 3) & 1, (d[4] >> 4) & 0x0F, d[4] & 0x07)
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        lastE4 = (float(i16be(d, 0)), (d[2] >> 7) & 1)
                        e4hist.append((tm, lastE4[0], lastE4[1], d[2]))
                    elif src == 1 and addr == 0x17C and len(d) >= 4:
                        rpm_t.append(tm)
                        rpm_v.append((d[2] << 8) | d[3])
                    elif src == 1 and addr == 0x14A and len(d) >= 7:
                        raw14_b4.append(d[4])
                        if last18 is None:
                            continue
                        rows.append((tm, i16be(d, 0) * -0.1, i16be(d, 2) * -1.0,
                                     i16be(d, 5) * -0.1, d[4],
                                     last18[0], last18[1], last18[2], last18[3], last18[4],
                                     lastE4[0], lastE4[1]))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm); cs["v"].append(c.vEgo)
                cs["eng"].append(float(bool(c.cruiseState.enabled)))
                cs["ang"].append(c.steeringAngleDeg)
                cs["tq"].append(c.steeringTorque)
                for k, attr in (("press", "steeringPressed"), ("std", "standstill"),
                                ("lblink", "leftBlinker"), ("rblink", "rightBlinker")):
                    try:
                        cs[k].append(float(bool(getattr(c, attr))))
                    except Exception:
                        cs[k].append(0.0)
                try:
                    cs["gear"].append(float(GEAR.index(str(c.gearShifter))))
                except Exception:
                    cs["gear"].append(0.0)
            elif w == "carControl":
                cc["t"].append(tm); cc["lat"].append(float(bool(evt.carControl.latActive)))
                cc["en"].append(float(bool(evt.carControl.enabled)))
                try:
                    cc["req"].append(float(evt.carControl.actuators.torque))
                except Exception:
                    cc["req"].append(np.nan)
            elif w == "soundPressure":
                try:
                    m = evt.soundPressure
                    snd["t"].append(tm)
                    snd["sp"].append(float(m.soundPressure))
                    snd["spw"].append(float(m.soundPressureWeighted))
                except Exception:
                    for k in ("t", "sp", "spw"):
                        if len(snd[k]) > min(len(snd[j]) for j in ("t", "sp", "spw")):
                            snd[k].pop()
            elif w == "clocks":
                try:
                    wn = int(evt.clocks.wallTimeNanos)
                except Exception:
                    continue
                if wn > 0:
                    clk["t"].append(tm); clk["w"].append(wn * 1e-9)
            elif w == "initData":
                try:
                    wn = int(evt.initData.wallTimeNanos)
                except Exception:
                    wn = 0
                if wn > 0:
                    init_wall.append((tm, wn * 1e-9))
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    try:
                        nm = str(e.name)
                    except Exception:
                        continue
                    events.append((tm, nm,
                                   bool(getattr(e, "enable", False)),
                                   bool(getattr(e, "softDisable", False)),
                                   bool(getattr(e, "immediateDisable", False)),
                                   bool(getattr(e, "noEntry", False))))

    a = np.array(rows, dtype=float)
    names = ["t", "ang", "rate_c", "wang", "probe", "tq", "rate_f", "sca", "sstat", "slow3",
             "e4tq", "e4req"]
    d = {n: a[:, i].copy() for i, n in enumerate(names)}
    if t0 is None:
        t0 = d["t"][0]
    d["t"] = d["t"] - t0
    cst = np.array(cs["t"]) - t0
    for k in ("v", "eng", "ang", "tq", "press"):
        d["cs_" + k] = np.interp(d["t"], cst, np.array(cs[k]))
    for k in ("gear", "std", "lblink", "rblink"):
        d["cs_" + k] = held_last(d["t"], cst, cs[k], 0.0)
    d["cs_lchg"] = np.maximum(d["cs_lblink"], d["cs_rblink"])
    cct = np.array(cc["t"]) - t0
    for k in ("lat", "en", "req"):
        d["cc_" + k] = np.interp(d["t"], cct, np.array(cc[k]))

    # ---- V71B probe decode --------------------------------------------------------------------
    # 🛑 bit4/bit3 watch gp-0x6ADC = **r26**'s post-clip mirror on this build. See the module
    # docstring; `_assert_mirror_byte()` pins it against the decoder's CAVE_HEX_B.
    p = d["probe"].astype(int)
    d["field"] = ((p >> 3) & 0x1F).astype(float)   # 0 => the cave did not fire => VOID
    live = ((p & BIT_LIVE) != 0)
    m671d = ((p & BIT_MASK671D) != 0)   # bit6  gp-0x671d != 0   THE MASK, outranks every arm
    st4 = ((p & BIT_STATE4) != 0)       # bit5  gp-0x67fa == 4   THE RATCHET STATE (counterfactual)
    mabs = ((p & BIT_ABS) != 0)         # bit4  |gp-0x6adc| >= 128, TWO-SIDED
    msgn = ((p & BIT_SIGN) != 0)        # bit3  gp-0x6adc >= 0   THE SIGN
    d["live"] = live.astype(float)
    # SEMANTIC names -- what the rung MEANS on this build.
    d["b6_671d"] = m671d.astype(float)
    d["b5_st4"] = st4.astype(float)
    d["b4_abs"] = mabs.astype(float)
    d["b3_sign"] = msgn.astype(float)
    # CELL-QUALIFIED aliases, matching the r50 cache's naming convention so a generic script that
    # reaches for a cell name finds the RIGHT cell and cannot silently read the wrong lane.
    d["b4_6adc"] = mabs.astype(float)
    d["b3_6adc"] = msgn.astype(float)
    # 🛑 NO `order_viol` CHANNEL. V70's `bit6 => bit3` invariant does NOT hold on V71 -- the four
    # rungs are INDEPENDENT and all 16 payloads are legal. Writing a zeroed channel would assert an
    # invariant this build does not carry. `_r50_lib.probe()` skips it when absent, by design.
    # 🛑 NO `sign_agree` CHANNEL either. On V70 that compared r26's sign to r24's (two cells); here
    # bit4 and bit3 read the SAME cell, so their relation is arithmetic, not evidence.
    # 🛑 NO firmware engagement bit: V71B spends all four rungs on 671d/67fa/mirror, and the LKAS
    # gate is not instrumented. Engagement is carControl.latActive (and CAN 0x18F b4 bit3 = `sca`).
    d["g6806"] = np.full(len(p), np.nan)
    d["illegal"] = (~live).astype(float)   # ≡ bit7 clear; all 16 field values are legal on V71

    e4 = np.array(e4hist, dtype=float)
    if len(e4):
        e4[:, 0] -= t0
    rawout = {f"raw{addr:03X}": (np.array(v, float) - t0) for addr, v in raw.items()}

    clk_mono = np.array(clk["t"], float) - t0
    clk_wall = np.array(clk["w"], float)
    if len(clk_wall) >= 2:
        off = float(np.median(clk_wall - clk_mono))
        off_sd = float(np.std(clk_wall - clk_mono, ddof=1))
    elif len(clk_wall) == 1:
        off, off_sd = float(clk_wall[0] - clk_mono[0]), np.nan
    else:
        off, off_sd = np.nan, np.nan
    iw = np.array(init_wall, float).reshape(-1, 2)
    if len(iw):
        iw[:, 0] -= t0
    n_snd = min(len(snd["t"]), len(snd["sp"]), len(snd["spw"]))
    snd_t = np.array(snd["t"][:n_snd], float) - t0

    # 🛑 RPM IS WRITTEN THREE WAYS ON PURPOSE, and the first one is load-bearing.
    #   `rpm`            gridded onto the 0x14A lattice -- what `_r4f_lib._add_rpm` and
    #                    `avg_periodogram` look for. If this is missing they silently return NaN
    #                    and every engine-order veto reads "unknown" instead of failing loudly.
    #   `rpm_t`/`rpm_v`  the raw 0x17C stream, un-gridded, for anything that needs true timing.
    #   `{tag}_rpm.npz`  a separate file, kept because `extract/extract_v68_rpm.py`'s convention reads it.
    rpm_ts = np.array(rpm_t, float) - t0
    rpm_vs = np.array(rpm_v, float)
    d["rpm"] = (np.interp(d["t"], rpm_ts, rpm_vs) if len(rpm_ts)
                else np.full(len(d["t"]), np.nan))
    np.savez_compressed(
        OUT / f"{tag}.npz", **d, e4hist=e4, **rawout,
        rpm_t=rpm_ts, rpm_v=rpm_vs,
        clk_mono=clk_mono, clk_wall=clk_wall, init_wall=iw,
        snd_t=snd_t, snd_sp=np.array(snd["sp"][:n_snd], float),
        snd_spw=np.array(snd["spw"][:n_snd], float),
        raw18_st=np.array(raw18_st, np.int16), raw14_b4=np.array(raw14_b4, np.int16),
        t0_mono=np.array([t0]), wall_t0=np.array([off]), wall_off_sd=np.array([off_sd]),
        # ★ PROVENANCE, so a downstream script can never mistake which lane bit4/bit3 watched.
        probe_build=np.array([BUILD]), probe_cell=np.array([MIRROR_CELL]),
        probe_lane=np.array([MIRROR_LANE]), probe_rwd=np.array([RWD_NAME]))
    np.savez_compressed(OUT / f"{tag}_rpm.npz", t=rpm_ts, rpm=rpm_vs)
    (OUT / f"{tag}_events.json").write_text(json.dumps(
        [{"t": tt - t0, "name": nm, "enable": en, "soft": sd, "immediate": im, "noEntry": ne}
         for tt, nm, en, sd, im, ne in events], indent=0))

    # ★ THE LATTICE ESTIMATOR, never 1/median(dt) -- see the module docstring.
    fs = fs_lattice(d)
    gsum = {GEAR[int(g)]: int((d["cs_gear"] == g).sum()) for g in np.unique(d["cs_gear"])}
    void = int((d["field"] == 0).sum())
    import time as _time
    wstr = (_time.strftime("%H:%M:%S", _time.localtime(off)) if np.isfinite(off) else "??")
    b4u, b4c = np.unique(np.array(raw14_b4, int), return_counts=True)
    bad_b4 = {int(v): int(c) for v, c in zip(b4u, b4c) if (int(v) & PROBE_MASK) not in LEGAL_FIELD}
    rp = np.array(rpm_v, float)
    rok = (rp > 400) & (rp < 7000)
    print(f"{tag}: {len(a)} samples  {d['t'][0]:.2f}..{d['t'][-1]:.2f} s  fs={fs:.3f}  "
          f"0xE4 {len(e4)}  vEgo {d['cs_v'].min():.2f}..{d['cs_v'].max():.2f} m/s\n"
          f"      wall_t0 {off:.3f} ({wstr} local)  clk n={len(clk_wall)} sd={off_sd:.4f}\n"
          f"      RAW byte4: " + " ".join(f"0x{v:02X}:{c}" for v, c in zip(b4u, b4c)) +
          (f"   *** bit7 CLEAR (VOID) {bad_b4}" if bad_b4 else "   (all bit7-set, live)") + "\n"
          f"      VOID {void}  "
          f"bit6 671d!=0 {100 * d['b6_671d'].mean():.4f}%  "
          f"bit5 state4 {100 * d['b5_st4'].mean():.4f}%  "
          f"bit4 |gp-0x{MIRROR_CELL:04X}|>=128 {100 * d['b4_abs'].mean():.4f}%  "
          f"bit3 sgn {100 * d['b3_sign'].mean():.4f}%  "
          f"illegal {int(d['illegal'].sum())}\n"
          f"      lat {100 * (d['cc_lat'] > 0.5).mean():.1f}%  "
          f"sca {100 * (d['sca'] == 1).mean():.1f}%  "
          f"blinker {100 * (d['cs_lchg'] > 0.5).mean():.1f}%  "
          f"ST==4 {int((d['sstat'] == 4).sum())}  ST==3 {int((d['sstat'] == 3).sum())}  "
          f"mic {n_snd}  rpm {len(rp)}"
          + (f" ({np.percentile(rp[rok], 5):.0f}..{np.percentile(rp[rok], 95):.0f})"
             if rok.any() else "") +
          f"  gears {gsum}  events {len(events)}")
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    args = [int(x) for x in sys.argv[1:]] or SEGS
    print(f"ROUTE 54 = {BUILD}   bit4/bit3 watch gp-0x{MIRROR_CELL:04X} = {MIRROR_LANE}'s "
          f"post-clip mirror\n  rwd: {RWD_NAME}")
    for s in args:
        extract([RLOGDIR / f"{ROUTE}--{s}--rlog.zst"], f"{PFX}{s}")
