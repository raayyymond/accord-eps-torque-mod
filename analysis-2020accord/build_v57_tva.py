#!/usr/bin/env python3
"""build_v57_tva.py -- V57 = V55 + the 0xC646C DECOUPLING. The 4x gain hits the LKAS path ONLY.

V57 = V55 + exactly 6 bytes (2 code + 4 cal) + both CRC trailers.

    0x2A1F0  ld.h displacement  0x746C -> 0x7CD0   (tp+0x7CD0 = 0xC6CD0)   [MAIN block]
    0xC6CD0  new private forward-path gain word   0xFFFF -> 3564          [CAL block]
    0xC646C  the SHARED sensor scale               3564  -> 891 (stock)    [CAL block]

=======================================================================================================
WHY -- and an honest statement of what this does NOT do
=======================================================================================================
`0xC646C` was raised 891 -> 3564 in V22 to obtain 4x LKAS authority. It is NOT an LKAS gain. It is the
firmware's single shared Q15 sensor-to-command-domain scale with SIX readers across three subsystems.
Re-enumerated from scratch 2026-07-29 by independent Python byte scan (both V850E2 encodings, unaligned
sweep over [0x13000,0xC4FFC), plus an LE32 absolute-pointer scan) and corroborated instruction-by-
instruction in Ghidra -- exactly 6, zero discrepancy:

    0x2A1EE  ld.h   FUN_00028ea6   FORWARD -- the CAN LKAS setpoint path. 4x is INTENDED here.
    0x2A904  --     (none)         DEAD -- not disassembled at all on the fully-analysed image;
                                   sits in the unclaimed gap above FUN_00028ea6's end at 0x2a30d,
                                   inside the known-dead FUN_0002a30e / FUN_0002a93a copies.
    0x2B656  ld.hu  FUN_0002b62c   FEEDBACK (assist-shaping task)
    0x2C488  ld.hu  FUN_0002c478   FEEDBACK (1 kHz task) -- (gp-0x4f60_RAW * GAIN) >> 15
    0x36686  ld.hu  FUN_00036682   FEEDBACK -- and its RETURN VALUE is an aggregator summand
    0x3684A  ld.hu  FUN_00036828   FEEDBACK -- modulates FUN_00036682's hysteresis dead-band width

So raising the gain for LKAS authority silently quadrupled four in-loop feedback paths that have nothing
to do with LKAS -- two of them applying it to the RAW torsion bar on a path that reaches the motor.
That is a real, unintended defect and this build fixes it: the forward reader gets its own private word
while every other reader falls back to the factory 891.

*** THIS IS A CORRECTNESS FIX. IT IS NOT EXPECTED TO FIX THE 20-25 Hz GRINDING. Say so plainly. ***
Quantified 2026-07-29 from the exact recursion (not a continuous approximation): FUN_00036682 is
    y[n] = y[n-1]*(1-2a) + a*K*x[n],  a = 6/1024 (0xC63D2, byte-read 06 00), K = GAIN/32768
    => |H(21 Hz)| = -46.3 dB at 3564, -58.3 dB at 891.
Across all four feedback readers the total loop-gain change at 22 Hz is <= 0.28 dB, against a MEASURED
on-car sensor->command transfer of 0.221. That cannot move a 20-25 Hz mode. An independent lane audit
confirms it from the other side: of the ELEVEN aggregator summands, exactly ONE reads 0xC646C
(FUN_00036682), and it is the most deeply attenuated lane in the entire table.

=======================================================================================================
WHY NOT THE OTHER CANDIDATES CONSIDERED THIS SESSION
=======================================================================================================
* The 0xC61B8 pre-gain deadband + sign relay (FUN_00028ea6 @0x2a1ae-0x2a206). Genuinely un-rescaled --
  102 in stock/V38/V55/V56 while its siblings 0xC61B2/0xC61B4 went 512 -> 2048 with the gain -- and it
  IS on the forward path (verified by the lead: r9 -> add r9,r11 @0x2a1fc -> xPOLARITYxGAIN -> clamp ->
  mov r11,r1 @0x2a226 -> cmove 0x0,r1,r16 @0x2a2c2 -> st.h r16,-0x6b3c @0x2a2ea, the arbitration output;
  the st.h r1,-0x6b38 @0x2a23c is a DIAGNOSTIC COPY, not the only consumer -- a subagent stopped at that
  store and wrongly concluded the block was diagnostic-only).
  *** BUT the gate is INERT in the operating point where the grinding lives. *** Its enable requires
  gp-0x6806 == 0, and every zero-writer sits in a ramp-DOWN or reset state (0x29696 and 0x2970e both
  decrement gp-0x69b0 immediately after; 0x29724 zeroes it outright), while the ramp SATURATING to
  0x8000 -- steady engaged driving -- writes gp-0x6806 = 1 at 0x2948c/0x2958c. The grinding is hands-off,
  engaged, delivering torque: ramp saturated, gate off. NOT SHIPPED. Left as a known-real defect on the
  engage ramp for a future, separately-justified build.
  (Correction of record: a 2026-07-20 note said the zero-writers require STEER_STATUS in {3,4,7}. Two of
  them have paths that never test STEER_STATUS -- 0x29696 via (r8==0 AND gp-0x6803==2), 0x2970e via
  (r8==0 AND gp-0x679e==0). The conclusion survives; the stated reasoning does not.)
* r24 / r26 (the unfiltered torque-rate lanes). Nominated by a lane audit as "never previously proposed".
  FALSE -- r24 = V39 (0xC6440/42/46, 0xC61F6), r26 = V42 ch.2 (0xC643E + 0xC6A72/86/9A/AE). Both
  FLASHED, both FALSIFIED. V42's own builder even records why V39's r24 kill was inert (r24 carries a
  +-3 deadzone, cal 0xC61F6). Checked against docs/BUILD-LINEAGE.md and a grep of build_v*_tva.py.
* gp-0x6bbe boost (0xC6372). The strongest SURVIVING vibration candidate -- same-signed with the torque
  sensor, i.e. reinforcing, with no velocity sign flip. But its attenuation at 21 Hz is -1.30 dB if
  FUN_00022ca0 runs at 1 kHz and -14.9 dB if it runs at 100 Hz, and THAT RATE IS UNRESOLVED. Shipping a
  lag edit into the always-on base power-steering loop on an unresolved sample rate is precisely the
  V48B brick class. NOT SHIPPED until the rate is pinned.
* gp-0x6ad4 / FUN_0003a382. ELIMINATED on-car by V56.

=======================================================================================================
GATES
=======================================================================================================
GATE 1 (RAM ownership): VACUOUS. No cave, no new RAM, no register-indirect access. Two instruction bytes
  (a displacement field, same opcode, same registers, still even so still decodes ld.h not ld.w) and two
  calibration words. 0xC6CD0 verified free by a fresh full-image scan: zero disp16 loads, zero stores,
  zero 6-byte extended-disp hits, zero LE32 absolute-pointer hits; byte-dumped 0xFF from 0xC6CA4 through
  0xC6FEF, with the preceding 4-point LERP table at 0xC6C90 ending cleanly at 0xC6CA4 and non-FF footer
  bytes not resuming until 0xC6FF0. 0xC6CD0 sits 0x2C into that desert.

GATE 2 (closed-loop stability): the direction of travel is TOWARD the factory operating point on every
  feedback path, and the forward path is bit-for-bit unchanged in behaviour.
  - CLOSED -- no float mirror. A fresh scan for ANY 32-bit tp-relative access with displacement in
    [0x7440,0x74A0) -- a generous window bracketing 0xC646C -- returned ZERO hits. There is no float twin
    of the gain word, so this cannot repeat the V27 mirror-desync brick. (The V31 boost-floor mirror at
    0xC65C4/0xC6768 is a different, already-accounted-for pair and is untouched here.)
  - CLOSED -- forward authority preserved. The LKAS path reads 3564 before and after; only the ADDRESS it
    reads from moves. Steering authority is unchanged by construction.
  - REASONED -- reducing a feedback gain can in principle destabilise. Here all four affected readers move
    from an accidentally-quadrupled value back to the factory-shipped 891, i.e. to the operating point
    Honda validated. There is no structural reason to expect stock to be less stable than 4x stock on
    paths that were never meant to carry 4x. No plant model was used, so this is reasoning, not proof.
  - EXPECTED -- manual steering feel WILL change. Readers #3/#4/#5/#6 are not gated on openpilot
    engagement, so this alters assist behaviour when disengaged too. That is the POINT of the fix (those
    paths should never have been at 4x), but it is a real, perceptible change and the operator should
    expect it. V52C is the precedent for "changed manual feel, null for the vibration".

  => V57 is a CORRECTNESS fix with an expected-null vibration result, deliberately built so that a null
     is INFORMATIVE rather than ambiguous: it isolates one variable and touches no lane under suspicion.

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

# ---- the edit ------------------------------------------------------------------------------------
GAIN_ADDR = 0xC646C          # the shared sensor scale -- reverts to stock
GAIN_4X = 3564
GAIN_STOCK = 891

PRIVATE_ADDR = 0xC6CD0       # the new LKAS-forward-only gain word
PRIVATE_FREE = 0xFFFF        # what must be there before we write

LOAD_ADDR = 0x2A1EE          # ld.h 0x746c, tp, r7
DISP_OFF = LOAD_ADDR + 2     # the hw2 displacement field
DISP_OLD = 0x746C            # tp+0x746C = 0xC646C
DISP_NEW = 0x7CD0            # tp+0x7CD0 = 0xC6CD0
INSN_HW1 = 0x3F25            # the opcode/register halfword -- MUST NOT move
TP = 0xBF000

TAG = "LKAS-4x-V38base-minsteerspeed0-v55probe-plus-0xC646C-decouple"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V57-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v57_plain_image.bin"))
V55_BIN = str(plain_image_path("_v55_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def assert_decoupled(code, label):
    """Everything V53's shared guard checks, minus the gain word which V57 deliberately moves."""
    for address, (value, note) in V53.STOCK_CALS.items():
        if address == GAIN_ADDR:
            continue                     # V57 owns this one
        got = u16(code, address)
        assert got == value, f"{label}: 0x{address:05X} is {got}, expected {value} ({note})"
    assert u16(code, V53.RATCHET_ADDR) == V53.RATCHET_STOCK_HW, \
        f"{label}: 0x{V53.RATCHET_ADDR:05X} is not the stock bne -- V57 is cut from V38 like V55"


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
    assert u16(v55, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V55 source lost the lockout edit"
    V53.assert_stock_cals(v55, "V55 source")     # the UNMODIFIED shared guard, incl. gain == 3564

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v55)

    # ---- pre-flight on the three sites -----------------------------------------------------------
    assert u16(code, GAIN_ADDR) == GAIN_4X, \
        f"0x{GAIN_ADDR:05X} is {u16(code, GAIN_ADDR)}, expected the 4x value {GAIN_4X}"
    assert u16(code, PRIVATE_ADDR) == PRIVATE_FREE, \
        f"0x{PRIVATE_ADDR:05X} is not free (reads 0x{u16(code, PRIVATE_ADDR):04X}, expected 0xFFFF)"
    assert u16(code, LOAD_ADDR) == INSN_HW1, \
        f"0x{LOAD_ADDR:05X} hw1 is 0x{u16(code, LOAD_ADDR):04X}, expected 0x{INSN_HW1:04X}"
    assert u16(code, DISP_OFF) == DISP_OLD, \
        f"0x{DISP_OFF:05X} disp is 0x{u16(code, DISP_OFF):04X}, expected 0x{DISP_OLD:04X}"
    assert TP + DISP_OLD == GAIN_ADDR, "tp+disp_old must resolve to the shared gain"
    assert TP + DISP_NEW == PRIVATE_ADDR, "tp+disp_new must resolve to the private word"
    assert DISP_NEW % 2 == 0, "disp must stay EVEN or the opcode decodes as ld.w instead of ld.h"

    # The private word must be far from its neighbours: the 4-point LERP above it ends at 0xC6CA4,
    # and the non-FF footer resumes at 0xC6FF0. Assert the local desert rather than trusting a note.
    for a in range(PRIVATE_ADDR - 0x10, PRIVATE_ADDR + 0x10, 2):
        assert u16(code, a) == 0xFFFF, f"0x{a:05X} is not 0xFFFF -- 0xC6CD0's neighbourhood is not free"

    # ---- THE EDIT --------------------------------------------------------------------------------
    print("\n  THE EDIT -- give the LKAS forward path its own gain word:")
    struct.pack_into("<H", code, DISP_OFF, DISP_NEW)
    print(f"    0x{DISP_OFF:05X}  ld.h displacement  0x{DISP_OLD:04X} -> 0x{u16(code, DISP_OFF):04X}   "
          f"(tp+0x{DISP_NEW:04X} = 0x{PRIVATE_ADDR:05X})   [MAIN]")
    struct.pack_into("<H", code, PRIVATE_ADDR, GAIN_4X)
    print(f"    0x{PRIVATE_ADDR:05X}  private LKAS gain  0x{PRIVATE_FREE:04X} -> "
          f"{u16(code, PRIVATE_ADDR)}   [CAL]")
    struct.pack_into("<H", code, GAIN_ADDR, GAIN_STOCK)
    print(f"    0x{GAIN_ADDR:05X}  shared sensor scale  {GAIN_4X} -> {u16(code, GAIN_ADDR)} (stock) "
          f"  [CAL]")

    assert u16(code, LOAD_ADDR) == INSN_HW1, "the opcode/register halfword moved -- only disp may change"
    assert u16(code, DISP_OFF) == DISP_NEW
    assert u16(code, PRIVATE_ADDR) == GAIN_4X
    assert u16(code, GAIN_ADDR) == GAIN_STOCK

    # the forward path must still see 3564, via the new address
    assert u16(code, TP + u16(code, DISP_OFF)) == GAIN_4X, \
        "the retargeted load does not resolve to the 4x value -- LKAS authority would change"

    # everything V55 established must still hold
    assert_decoupled(code, "V57")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "the 0xC6AF0 LERP must stay STOCK -- V56's mute is falsified"
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC61B2, "fwd clamp"), (0xC61B4, "fwd clamp"),
                    (0xC6440, "r24"), (0xC6442, "r24"), (0xC6446, "r24"), (0xC61F6, "r24 deadzone"),
                    (0xC643E, "r26")):
        assert u16(code, a) == u16(v55, a), f"{name} 0x{a:05X} moved -- V57 changes ONE lever only"
    assert code[0xC64A3] == v55[0xC64A3] == 1, "the deadband enable byte must stay stock in V57"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A):
        assert u16(code, a) == u16(baseline, a), f"damper cal 0x{a:05X} moved"

    # ---- CRC -------------------------------------------------------------------------------------
    assert V53.owning_block(code, PRIVATE_ADDR) == CAL_BLOCK, "0xC6CD0 is not in the CAL CRC block"
    assert V53.owning_block(code, GAIN_ADDR) == CAL_BLOCK, "0xC646C is not in the CAL CRC block"
    assert V53.owning_block(code, DISP_OFF) == MAIN_BLOCK, "0x2A1F0 is not in the MAIN CRC block"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
    # unlike V55/V56 this one DOES touch code, so the MAIN CRC must move
    assert struct.unpack_from("<I", code, MAIN_BLOCK[1])[0] != \
        struct.unpack_from("<I", v55, MAIN_BLOCK[1])[0], \
        "MAIN block CRC did NOT move -- but V57 edits an instruction, so it must"

    # ---- exact diff vs V55, and vs V38 -----------------------------------------------------------
    d55 = [i for i in range(0x13000, 0x100000) if code[i] != v55[i]]
    permitted = ({DISP_OFF, DISP_OFF + 1, PRIVATE_ADDR, PRIVATE_ADDR + 1, GAIN_ADDR, GAIN_ADDR + 1}
                 | set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
                 | set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)))
    stray = [i for i in d55 if i not in permitted]
    assert not stray, f"V57 vs V55 touches bytes outside the edit + CRCs: {[hex(x) for x in stray]}"
    for lo, name in ((DISP_OFF, "displacement"), (PRIVATE_ADDR, "private gain"), (GAIN_ADDR, "shared gain")):
        assert any(i in d55 for i in (lo, lo + 1)), f"{name} did not actually change"
    assert set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4)) <= set(d55), "the CAL CRC trailer did not move"
    assert set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)) <= set(d55), "the MAIN CRC trailer did not move"
    print(f"\n  V57 vs V55: {len(d55)} bytes -- {len(d55) - 8} edit + 8 CRC, all inside the "
          f"permitted footprint")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V57 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates on the BUILT image -----------------------------------------------------
    FF.assert_crc_chain(code, "V57")
    assert walk(bytes(code), label="V57") == 0
    assert walk_all_blocks(bytes(code), label="V57") == 0
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
    FF.assert_x31_checksum(rwd, "V57 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V57 readback")
    assert walk(bytes(readback), label="V57 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V57 readback") == 0
    V55.assert_probe_sites(readback, hook_is_stock=False)
    V55.assert_variant_tables(readback)
    assert u16(readback, DISP_OFF) == DISP_NEW, "the retarget did not survive the RWD round trip"
    assert u16(readback, LOAD_ADDR) == INSN_HW1, "the opcode halfword corrupted in the readback"
    assert u16(readback, PRIVATE_ADDR) == GAIN_4X, "the private gain did not survive"
    assert u16(readback, GAIN_ADDR) == GAIN_STOCK, "the shared gain revert did not survive"
    assert u16(readback, TP + u16(readback, DISP_OFF)) == GAIN_4X, \
        "readback: the retargeted load does not resolve to 3564"
    assert bytes(readback[V55.CAVE_BASE:V55.CAVE_BASE + len(V55.CAVE_BYTES)]) == V55.CAVE_BYTES, \
        "cave does not survive the RWD round trip"

    print(f"  wrote {OUT}")
    print(f"    SHA256 {hashlib.sha256(rwd).hexdigest()}")

    print("\n  GATE 1 (RAM): VACUOUS -- no cave, no RAM, 2 instruction bytes + 2 cal words.")
    print("  GATE 2 (loop): no float mirror (fresh 32-bit scan of [0x7440,0x74A0) -> 0 hits);")
    print("                 forward authority unchanged (still 3564, new address);")
    print("                 all four feedback readers move TOWARD stock 891.")
    print("                 EXPECTED: manual steering feel changes -- those readers are not gated on")
    print("                 openpilot engagement. That is the point of the fix.")
    print("  *** CORRECTNESS FIX. Expected NULL for the 20-25 Hz grinding (<=0.28 dB at 22 Hz).")
    print("\n  *** Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    build()
