#!/usr/bin/env python3
r"""
V175 -- REVERT THE ENGAGED APPARENT-INERTIA DOSE TO HONDA'S OWN NUMBERS.  Base = V173.  12 bytes.
        A SUBTRACTIVE build.  Two int16 triples.  No new lever, no cave, no code edit.

WHAT THIS IS, IN ONE SENTENCE
------------------------------
The flight build amplifies a DESTABILISING, omega^2-weighted apparent-inertia term by 3.0x (and its
third knot by 8.1x) on the ENGAGED modes ONLY -- and the ratcheting is engaged-amplified ~15x.
This puts that term back to Honda's values.

THE MECHANISM, TRACED THIS SESSION (decompile-first, both ends confirmed)
-------------------------------------------------------------------------
`FUN_00036c12` is the sole writer of `gp-0x6b26` (one `st.h -0x6b26[gp]` at 0x36CF0; the other five
disp16 sites are `ld.h`, confirmed by raw LE byte scan AND by decompile):

    gp-0x6b26 = clamp( ((gp-0x6c2c * validgate) * LERP_0xCBE74[mode](gp-0x6a5e) >> 6) * 0x111 >> 0x12,
                       +-cal[0xC407E] )

  * `gp-0x6c2c` is the ACCELERATION -- `FUN_00041464` @0x41602 `sub r7,r9` is a FIRST DIFFERENCE of
    the EMA-filtered resolver rate, then *32, clamped, EMA'd, >>9.  Confirmed in assembly.
  * the acceleration enters LINEARLY.  The LERP is indexed by `gp-0x6a5e`, a SCHEDULING variable,
    not by alpha.  So gp-0x6b26 = K(mode, sched) * alpha -- a pure apparent-inertia term.
  * therefore its contribution to the loop scales as omega^2: at 8.17 Hz it is 66.7x its value at
    1 Hz for the same displacement.  ** That selectivity is STRUCTURAL -- no filter, no added phase. **

`FUN_00038148` admits it into the six-term Path-2 sum with weight `w[3]` = `tp+0x73a6` = `0xC63A6`:

    sum = ... + ((gp-0x6b26 * gate) * w[3]) >> 10 + ...      gate: (gp-0x6b26 + 0x400) < 0x801

  ** THE GATE CAN NEVER CLOSE. ** `0xC407E` clamps the writer to +-511 and the gate admits +-1024,
  so 511 < 1024 and the term is admitted unconditionally.  [EVIDENCE, read from all three images.]

THE SIGN -- WHY THIS TERM IS DESTABILISING
-------------------------------------------
The Y rows are NEGATIVE, so gp-0x6b26 = -|K|*alpha.  Following the verified polarity chain
([[accord-friction-polarity-more-friction-is-more-assist]], corrected 2026-08-23, whose step 4
establishes `f' >= 0` EVERYWHERE at the residual LERP, with a measured cross-check
d(gp-0x6b94)/d(gp-0x6b70) = +0.2529 / +0.2565 / +0.2617 and a passing positive control):

    alpha UP -> MODEL DOWN (the term is negative) -> res UP -> gp-0x6b70 UP (f' >= 0)
             -> target felt effort DOWN -> MORE ASSIST

=> assist rises with acceleration.  That is POSITIVE ACCELERATION FEEDBACK, i.e. NEGATIVE apparent
inertia: it lowers effective mass AND lowers the damping ratio of the resonance.  Amplifying it is
the wrong direction, and the record already says so -- [[accord-gp6b26-is-inertia-not-damping]]:
"the whole V74/V75/V91/V92 dose direction was aimed at the wrong physics."

** This is why 0xC63A6 was struck on 2026-08-11/12: its Q2 gate was that Path 2's sign depended on
an UNKNOWN LERP slope.  That slope is now known (f' >= 0, measured p50 2.174 hands-off / 0.346
hands-on).  The gate is cleared -- but this build does NOT spend it.  See "WHY NOT w[3]" below. **

THE RELAY HAZARD, WHICH IS UNEXCLUDED ON THE CURRENT BUILD
-----------------------------------------------------------
Saturation of the +-511 clamp turns -K*alpha into sign(alpha)*511 -- a RELAY.  V80's lesson was
exactly this ("the damper became a RELAY ... worst grinding ever"), and a relay inside a lightly
damped loop is a textbook ratchet source.

    K            alpha to saturate     equivalent STOCK-referred gp-0x6b26
    Honda 1.0x       ~3195                       511
    flown 3.0x       ~1065                       170          <== the CURRENT build

The only on-car measurement is V76's: at Honda's K, `|gp-0x6b26| > 448` fired **0 / 63,477 frames**
on route 65 with a 99.926% positive control [EVIDENCE].  ** That null is at 448.  The threshold that
matters at 3.0x is 170 -- 2.6x lower, and NEVER MEASURED. ** So the relay hazard is bounded at
Honda's K and simply unknown at the flown K.  Reverting restores the configuration in which it is
measured to be unexercised.

WHY NOT SPEND w[3] (`0xC63A6`) INSTEAD
---------------------------------------
Because a revert to Honda's own numbers is a strictly lower risk class than a virgin cell, it is
ENGAGED-ONLY (mode 24 is already stock and stays untouched, so manual feel cannot change), and it
restores a configuration with an on-car saturation measurement behind it.  `0xC63A6` remains
available and is now UNBLOCKED -- it is asserted FROZEN at 1024 here so the record shows this build
did not spend it.  If V175 moves the ratchet, w[3] is the fine adjustment; if V175 does nothing,
w[3] would not have either, since they multiply the same quantity.

HOW THE DRIVE SEPARATES THIS FROM V173's POLE MOVE
---------------------------------------------------
They stack (different cells, different mechanisms) and BOTH attenuate the ratchet, so amplitude
alone cannot attribute.  ** The discriminator is ENGAGED vs MANUAL. ** V173's poles act in both;
this revert is mode-26/27 only and CANNOT act in manual.  So:
  * ratchet falls in ENGAGED but the engaged/manual RATIO also falls  -> the inertia dose was
    carrying it, and this build is the cause.
  * ratchet falls with the ratio UNCHANGED                            -> V173's poles did it.
  * neither moves                                                     -> both accounts fail together.
Score with `rlog-tools/score/grind_engaged_vs_manual.py` alongside `score_band_excess.py`.

RISK
----
A pure calibration revert to values Honda ships, in a lane the kit has moved on-car many times
(V73/V74/V75/V81/V91/V92/V106/V107 all touched it) and which has never faulted at Honda's value.
`0xC407E` stays 511, one count under its own 512 trip -- asserted frozen.  Mode 24 untouched.
No cave, no code edit, no RAM claim.  ** It removes drag: creep effort will be lighter than the
operator is used to.  That is intended and he should be told. **
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

# --- PATH BOOTSTRAP -------------------------------------------------------------------------
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V175_WRITE", "").strip().lower()

BASE_NAME = "_v173_V173-V158BASE-ASSIST.SECTION.POLES.NOTCH.KEPT_plain_image.bin"
BASE_SHA = "a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7"

# ---- THE EDIT -------------------------------------------------------------------------------
HONDA_Y = (-9830, -5734, -1966)        # Honda's own row, read from stock and asserted below
FLOWN_Y = (-29490, -17202, -16000)     # what the base carries on the ENGAGED modes
ENGAGED_ROWS = {0xD7A5C: "mode 26 (ENGAGED)", 0xD7A6C: "mode 27 (ENGAGED)"}
MANUAL_ROW = 0xD6A6C                   # mode 24 -- already Honda's, asserted UNTOUCHED

CLAMP_CAL, CLAMP_VAL = 0xC407E, 511    # the hard-fault interlock -- asserted FROZEN
W3_CAL, W3_VAL = 0xC63A6, 1024         # w[3] -- deliberately NOT spent by this build
GATE_WINDOW = 1024                     # FUN_00038148 admits |gp-0x6b26| <= 1024
BIQUAD = {0xC60A8: 0xBFB8F5C3, 0xC60AC: 0x3EEBE76D,
          0xC60B0: 0xBFF0BE0E, 0xC60B4: 0x3E074D3C}   # V173's section -- asserted CARRIED

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def row(buf, off):
    return tuple(struct.unpack_from("<h", buf, off + 2 * i)[0] for i in range(3))


def build():
    print("=" * 102)
    print("  V175 -- ENGAGED APPARENT-INERTIA DOSE REVERTED TO HONDA   (base V173)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V173 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] HONDA'S ROW IS READ FROM THE STOCK IMAGE, NEVER TYPED")
    stock_p = Path(plain_image_path("../stock_fw_dump/code.bin"))
    if not stock_p.exists():
        stock_p = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                      "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                       "analysis-2020accord", "stock_fw_dump", "code.bin")
    stock = stock_p.read_bytes()
    for off in list(ENGAGED_ROWS) + [MANUAL_ROW]:
        check(row(stock, off) == HONDA_Y,
              f"stock 0x{off:05X} is Honda's {HONDA_Y} -- the constant is VERIFIED, not typed")

    print("\n  [3] THE BASE CARRIES THE 3.0x ENGAGED DOSE, AND MANUAL IS ALREADY STOCK")
    for off, what in ENGAGED_ROWS.items():
        check(row(base, off) == FLOWN_Y, f"0x{off:05X} {what} = {FLOWN_Y} on the base")
    check(row(base, MANUAL_ROW) == HONDA_Y,
          f"0x{MANUAL_ROW:05X} mode 24 (MANUAL) is ALREADY Honda's -- this build cannot change "
          f"manual feel")
    ratios = tuple(round(FLOWN_Y[i] / HONDA_Y[i], 2) for i in range(3))
    print(f"      the dose being removed, knot by knot: {ratios[0]}x / {ratios[1]}x / {ratios[2]}x")

    print("\n  [4] THE GATE IN FUN_00038148 CANNOT CLOSE -- w[3] is an UNCONDITIONAL multiplier")
    clamp = struct.unpack_from("<H", base, CLAMP_CAL)[0]
    check(clamp == CLAMP_VAL, f"0x{CLAMP_CAL:05X} clamp = {clamp} (Honda's, one under the 512 trip)")
    check(clamp <= GATE_WINDOW,
          f"clamp {clamp} <= gate window {GATE_WINDOW} => the lane is admitted EVERY frame")

    print("\n  [5] THE EDIT -- two int16 triples, 12 bytes")
    attributed = set()
    for off, what in ENGAGED_ROWS.items():
        for i, v in enumerate(HONDA_Y):
            struct.pack_into("<h", code, off + 2 * i, v)
        attributed |= set(range(off, off + 6))
        print(f"      0x{off:05X}  {what}  {row(base, off)} -> {row(code, off)}")

    print("\n  [6] THE RESULT, AND WHAT THIS BUILD DELIBERATELY DOES NOT TOUCH")
    for off, what in ENGAGED_ROWS.items():
        check(row(code, off) == HONDA_Y, f"0x{off:05X} {what} is now Honda's {HONDA_Y}")
    check(row(code, MANUAL_ROW) == HONDA_Y, f"0x{MANUAL_ROW:05X} mode 24 UNTOUCHED")
    check(struct.unpack_from("<H", code, W3_CAL)[0] == W3_VAL,
          f"0x{W3_CAL:05X} w[3] FROZEN at {W3_VAL} -- this build does NOT spend the virgin weight")
    check(struct.unpack_from("<H", code, CLAMP_CAL)[0] == CLAMP_VAL,
          f"0x{CLAMP_CAL:05X} clamp FROZEN at {CLAMP_VAL}")
    for off, word in BIQUAD.items():
        check(struct.unpack_from("<I", code, off)[0] == word,
              f"0x{off:05X} V173's section coefficient CARRIED ({word:08X})")
    sat_before = CLAMP_VAL * HONDA_Y[0] / FLOWN_Y[0]
    print(f"      saturation threshold, stock-referred: {sat_before:.0f} -> {CLAMP_VAL} counts")
    print(f"      V76 measured |gp-0x6b26| > 448 at 0/63,477 frames AT HONDA'S K "
          f"=> the relay hazard returns to MEASURED-UNEXERCISED")

    print("\n  [7] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = struct.unpack_from("<I", code, blk[1])[0]
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [8] FULL BYTE DIFF vs V173 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(payload == 12, f"{payload} payload bytes (exactly 12: two int16 triples)")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V175 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V175-V173BASE-GP6B26.ENGAGED.Y.REVERT.HONDA"
    img_out = plain_image_path(f"_v175_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V175_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** Discriminator vs V173's poles: ENGAGED vs MANUAL. This revert cannot act in "
          "manual. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
