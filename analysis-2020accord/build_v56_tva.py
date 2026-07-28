#!/usr/bin/env python3
"""build_v56_tva.py -- V56 = V55 (unchanged, probe and all) + the 0xC6AF0 AUTHORITY-LERP MUTE.

V56 = V55 + exactly 4 bytes of calibration + the CAL CRC trailer.

    0xC6AFC  Y[0]  32768 -> 0
    0xC6AFE  Y[1]  32768 -> 0

This builder is a POST-PROCESSOR over `_v55_plain_image.bin`. It transcribes NOTHING from V55 -- not
the cave, not the hook, not the encoders. It loads V55's SHA-verified image and writes two halfwords.
That is deliberate: V53's builder took the same approach with FOURFRAME2's cave and it removed the
whole class of transcription defects.

=======================================================================================================
WHY THIS EDIT, AND WHY IT IS NOT A FOURTH TRY AT AN ALREADY-FALSIFIED LANE
=======================================================================================================
The V55 drive (route 1c, 2026-07-28) measured, on-car:

  * the ~21 Hz mode IS in gp-0x6b98, the final merged motor command, in the SAME 0.195 Hz bin as the
    torsion-bar sensor (coherence 0.93 at the peak bin; route 1b is a clean null control because
    V54's constant field yields exactly zero command power);
  * openpilot is NOT the source -- while its command is RAILED its own 21 Hz content is exactly 0,
    yet the command still carries 105.8 counts at 21 Hz. Even with the LKAS lane's low-pass deleted
    from the model entirely, openpilot is 8.7x too small to explain it (38x with the real IIR);
  * the sensor -> command transfer is FLAT at ~0.19-0.22 counts/count from 1 Hz to 21 Hz.

A flat transfer to 21 Hz cannot come from a lane behind a pole. That rules out FUN_00036682
(0xC63D2 = 6/1024 -> fc 0.933 Hz, -27.1 dB at 21 Hz) and with it the whole 0xC646C reader set.
gp-0x6ad4 / FUN_0003a382 is the structural match: unfiltered input at unity, and its Stage A and
Stage C poles (0xC6450, 0xC644A) are BOTH exact algebraic identities (1024/1024) -- zero lag, not
merely fast.

V43 (0xC644A -> 64, -7.1 dB), V46 (0xC6450 -> 32, -12.6 dB) and V48A (one carrier muted) each
attenuated ONE of this lane's three PARALLEL branches and each was null on-car. That is exactly what
you would predict if the lane matters and you filter one branch at a time. THIS edit is different in
kind: it zeroes the lane's OUTPUT BOUND, so it is branch-agnostic.

Dataflow confirmed in Ghidra on stock code.bin (lead, 2026-07-28), LERP result -> final store:

    0x3a69c  andi 0xffff,r6,r21              r6 = the 0xC6AF0 LERP result
    0x3a794  cmovnh r21,r15,r15              authority <= 32768 -> r15 = LERP Y
    0x3a79e  mul r15,r10,r0
    0x3a7aa  sar 0xf,r10                     Q15 scale  => r10 IS THE LIMIT
    0x3a88c  cmp r10,r14 ; bgt 0x3a8a0       symmetric +-limit clamp of the COMBINED value
    0x3a890  subr r0,r10 ; cmovle r14,r10,r10
    0x3a8a0  st.h r10,-0x6ad4[gp]

With Y = 0 the limit is 0 and all three phi predecessors of the store resolve to 0: the `bgt` path
stores the limit itself, the `cmovle` path resolves to 0, and the third path is an explicit
`mov 0x0,r10` at 0x3a89e. Every path stores zero.

Why Y[0] AND Y[1]: the walker at 0x3a648 compares the authority against X[0] = 0 with `bh`, so an
authority of exactly 0 takes the below-knot path and loads Y[0] (tp+0x7afc) directly, while 1..3276
interpolates between Y[0] and Y[1]. V54 measured gp-0x6966 in [0,127] for 5,989/5,989 frames, which
straddles that boundary. Zeroing both covers the whole measured range.

=======================================================================================================
GATES
=======================================================================================================
GATE 1 (RAM ownership): VACUOUS. Cal-only on top of V55; no new code, no scratch RAM, no cave change.

GATE 2 (closed-loop stability): PARTIALLY CLOSED. State it plainly, do not oversell it.
  CLOSED -- monitor divergence. gp-0x6ad4 has exactly TWO true gp-relative accesses image-wide: the
    writer at 0x3a8a0 (plain st.h, no compare-and-fault) and the aggregator's read at 0x3aca8. It is
    in no lockstep/shadow/mirror pair and no monitor reads it. That is the mechanism behind the V27
    and V48B bricks, and it does not apply here.
  CLOSED -- protection removal. The derate arms of this LERP (Y[2..4] = 0) are never invoked: V54
    measured the authority pinned in the first flat segment for 100% of frames, so muting Y[0]/Y[1]
    disables nothing that is live.
  *** OPEN -- the damping sign. Whether gp-0x6ad4 is net-damping or net-anti-damping at 21 Hz is NOT
    determined. The on-car data cannot settle it: this is closed-loop identification with no external
    excitation, so plant and controller cannot be separated. If the lane is a DAMPING term, muting it
    could make the vibration worse rather than better.
  *** OPEN -- manual steering feel. gp-0x6ad4 is NOT gated on openpilot engagement. Its limit chain
    is gated by gp-0x67fe, the EPS's own FOC/assist substate (gp-0x6772 == 5 -> 2), which V31P
    telemetry measured at 1 in 100% of frames INCLUDING disengaged stretches -- it means "the motor
    drive is running", i.e. power steering is on, all ignition cycle. So this lane is live during
    manual driving and muting it will change manual feel. V52C is the precedent: null for the
    vibration, but it did change manual feel.

  => V56 is a REVERSIBLE EXPERIMENT, not a known-good fix. It is cal-only and 4 bytes; reverting is
     a reflash of V55. The probe is carried forward deliberately: if the vibration persists but the
     command's 21 Hz content drops, the lane was a carrier but not the loop -- a graded answer rather
     than pass/fail.

*** Flash only on explicit operator instruction naming the file and the bus.
"""
import hashlib
import os
import struct
import zlib

import build_vfourframe_tva as FF
import build_v53_tva as V53
import build_v55_tva as V55

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from firmware_paths import plain_image_path, RWD_DIR
from verify_bootloader_crc import walk, walk_all_blocks

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

LERP = V53.AUTHORITY_LERP_ADDR                  # 0xC6AF0
LERP_STOCK = V53.AUTHORITY_LERP_STOCK           # (5, 0,3277,3604,19661,32768, 32768,32768,0,0,0)
# layout: [0] = point count, [1..5] = X row, [6..10] = Y row.  Verified four ways: against this
# tuple, against the walker's own `addi 0xc,r15,r13` (Y base = LERP+12) and `addi 0x2,r15,ep`
# (X base = LERP+2) at 0x3a63a/0x3a63e, and against three sibling tables (0xD27BC, 0xD27F8, 0xD07BC).
Y0_ADDR = LERP + 12                             # 0xC6AFC
Y1_ADDR = LERP + 14                             # 0xC6AFE
MUTE = 0

TAG = "LKAS-4x-V38base-minsteerspeed0-v55probe-plus-0xC6AF0-mute"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V56-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v56_plain_image.bin"))
V55_BIN = str(plain_image_path("_v55_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


# V53.assert_stock_cals() bundles three checks, one of which is "the 0xC6AF0 LERP must be stock --
# its edit direction is UNRESOLVED". V54's on-car probe RESOLVED that direction (authority pinned in
# the first flat segment for 5,989/5,989 frames), so V56 edits it deliberately. Rather than weaken a
# guard that five other builders rely on, run the UNMODIFIED guard on the pre-edit source, and
# re-expand its other two components here against the post-edit image.
def assert_stock_cals_except_lerp(code, label):
    for address, (value, note) in V53.STOCK_CALS.items():
        got = u16(code, address)
        assert got == value, f"{label}: 0x{address:05X} is {got}, expected {value} ({note})"
    assert u16(code, V53.RATCHET_ADDR) == V53.RATCHET_STOCK_HW, \
        f"{label}: 0x{V53.RATCHET_ADDR:05X} is not the stock bne -- V56 is cut from V38 like V55"
    expected = list(LERP_STOCK)
    expected[6] = expected[7] = MUTE
    assert struct.unpack_from("<11H", code, LERP) == tuple(expected), \
        f"{label}: the 0xC6AF0 LERP is not exactly stock-with-Y[0]/Y[1]-muted"


def build():
    if not os.path.exists(V55_BIN):
        print(f"  {V55_BIN} missing -- running the V55 builder first\n")
        V55.build()
    v55 = bytearray(open(V55_BIN, "rb").read())
    print(f"  V55 source {V55_BIN}")
    print(f"    SHA256 {hashlib.sha256(bytes(v55)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v55, "V55 source")
    assert walk(bytes(v55), label="V55 source") == 0
    assert walk_all_blocks(bytes(v55), label="V55 source") == 0
    V55.assert_probe_sites(v55, hook_is_stock=False)
    V55.assert_variant_tables(v55)
    assert struct.unpack_from("<11H", v55, LERP) == tuple(LERP_STOCK), \
        "the 0xC6AF0 authority LERP is not stock in the V55 source"
    assert u16(v55, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V55 source lost the lockout edit"
    V53.assert_stock_cals(v55, "V55 source")   # the UNMODIFIED guard, incl. the stock-LERP check

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v55)

    # ---- THE EDIT (CAL, 2 halfwords) -------------------------------------------------------------
    print(f"\n  THE EDIT (CAL, 2 halfwords) -- mute the FUN_0003a382 residual lane's output bound:")
    print(f"    LERP @0x{LERP:05X}   count={LERP_STOCK[0]}  "
          f"X={list(LERP_STOCK[1:6])}  Y={list(LERP_STOCK[6:11])}")
    for addr, idx in ((Y0_ADDR, 6), (Y1_ADDR, 7)):
        before = u16(code, addr)
        struct.pack_into("<H", code, addr, MUTE)
        print(f"    0x{addr:05X}  Y[{idx - 6}]  {before} -> {u16(code, addr)}")
    assert u16(code, Y0_ADDR) == MUTE and u16(code, Y1_ADDR) == MUTE
    # X row and the point count must be untouched -- writing to 0xC6AF0/0xC6AF2 instead of the Y row
    # would corrupt the count and X[0]. That is the trap this assert exists to catch.
    assert struct.unpack_from("<6H", code, LERP) == tuple(LERP_STOCK[:6]), \
        "point count or X row disturbed -- the mute must write the Y row at LERP+12/+14"
    assert struct.unpack_from("<3H", code, LERP + 16) == tuple(LERP_STOCK[8:11]), \
        "Y[2..4] disturbed -- the derate arms must stay stock"

    # everything V55 established must still hold
    assert_stock_cals_except_lerp(code, "V56")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    for a, name in ((0xC646C, "4x gain"), (0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"),
                    (0xC63D2, "FUN_36682 EMA"), (0xC6372, "boost input EMA"),
                    (0xC636E, "damping input EMA")):
        assert u16(code, a) == u16(v55, a), f"{name} 0x{a:05X} moved -- V56 changes ONE lever only"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A):
        assert u16(code, a) == u16(baseline, a), f"damper cal 0x{a:05X} moved"

    # ---- CRC ------------------------------------------------------------------------------------
    assert V53.owning_block(code, Y0_ADDR) == CAL_BLOCK, "Y[0] is not in the CAL CRC block"
    assert V53.owning_block(code, Y1_ADDR) == CAL_BLOCK, "Y[1] is not in the CAL CRC block"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
    assert struct.unpack_from("<I", code, MAIN_BLOCK[1])[0] == \
        struct.unpack_from("<I", v55, MAIN_BLOCK[1])[0], \
        "MAIN block CRC moved -- V56 touches calibration only"

    # ---- exact diff vs V55, and vs V38 ------------------------------------------------------------
    d55 = [i for i in range(0x13000, 0x100000) if code[i] != v55[i]]
    # 32768 = `00 80` little-endian, so muting to 0 changes only the HIGH byte of each halfword.
    # Assert containment (not equality) in the permitted footprint; the exact halfword values are
    # asserted above, and the CRC trailer is required to have moved below.
    permitted = {Y0_ADDR, Y0_ADDR + 1, Y1_ADDR, Y1_ADDR + 1} | set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
    stray = [i for i in d55 if i not in permitted]
    assert not stray, f"V56 vs V55 touches bytes outside the mute + CAL CRC: {[hex(x) for x in stray]}"
    assert set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4)) <= set(d55), "the CAL CRC trailer did not move"
    assert any(i in d55 for i in (Y0_ADDR, Y0_ADDR + 1)), "Y[0] did not actually change"
    assert any(i in d55 for i in (Y1_ADDR, Y1_ADDR + 1)), "Y[1] did not actually change"
    print(f"\n  V56 vs V55: {len(d55)} bytes -- {len(d55) - 4} cal + 4 CRC, all inside the "
          f"permitted footprint")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V56 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates on the BUILT image ------------------------------------------------------
    FF.assert_crc_chain(code, "V56")
    assert walk(bytes(code), label="V56") == 0
    assert walk_all_blocks(bytes(code), label="V56") == 0
    V55.assert_probe_sites(code, hook_is_stock=False)
    V55.assert_variant_tables(code)
    assert bytes(code[V55.CAVE_BASE:V55.CAVE_BASE + len(V55.CAVE_BYTES)]) == V55.CAVE_BYTES, \
        "the V55 cave did not survive"

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}")
    print(f"    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback -------------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == FF.EXPECTED_HEADERS
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V56 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V56 readback")
    assert walk(bytes(readback), label="V56 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V56 readback") == 0
    V55.assert_probe_sites(readback, hook_is_stock=False)
    V55.assert_variant_tables(readback)
    assert u16(readback, Y0_ADDR) == MUTE and u16(readback, Y1_ADDR) == MUTE, \
        "the mute did not survive the RWD round trip"
    assert struct.unpack_from("<6H", readback, LERP) == tuple(LERP_STOCK[:6]), \
        "X row corrupted in the readback"
    assert bytes(readback[V55.CAVE_BASE:V55.CAVE_BASE + len(V55.CAVE_BYTES)]) == V55.CAVE_BYTES, \
        "cave does not survive the RWD round trip"

    print(f"  wrote {OUT}")
    print(f"    SHA256 {hashlib.sha256(rwd).hexdigest()}")

    print("\n  GATE 1 (RAM): VACUOUS -- cal-only on top of V55; no new code, no scratch RAM.")
    print("  GATE 2 (loop): monitor divergence CLOSED (gp-0x6ad4 has 1 writer / 1 reader, no lockstep,")
    print("                 no monitor). Protection removal CLOSED (the derate arms are never invoked).")
    print("                 *** OPEN: the damping sign at 21 Hz, and manual steering feel -- the lane")
    print("                 is live when disengaged too (gp-0x67fe = FOC substate, not LKAS).")
    print("                 => a REVERSIBLE EXPERIMENT, not a known-good fix. Revert = reflash V55.")
    print("\n  *** Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    build()
