#!/usr/bin/env python3
"""build_v60_tva.py -- V60 = V59 + ONE halfword: the boost-amplitude BLEND coefficient 102 -> 43.

*** THE INTERVENTION THAT SETTLES THE ~21 Hz GRINDING. ***

V59 measured a parametric gain pump at 42.19 Hz -- exactly 2x the 21.09 Hz mode -- present only when
LKAS applies (disengaged: the probe's bit5 never toggles once in 61.2 s, K=90). That pump is real and
byte-verified. What V59 could NOT settle is whether it DRIVES the mode or merely ECHOES it, because
gp-0x6ba6 is |x| of a bar-derived signal: 2f coupling is arithmetically forced once the ripple exists.
Nor can the Mathieu stability margin be computed, because eps_crit = 2/Q needs the PASSIVE Q and the
mode never freely decays (66 candidate ring-downs, longest 0.63 cycles).

**Only an intervention separates drive from echo.** This is it.

THE LEVER
-------------------------------------------------------------------------------------------------------
Both boost-amplitude LERP outputs pass through a slew blend before they multiply anything -- a filter
that was not in the golden model at all until 2026-07-30:

    y1 = blend(LERP(gp-0x6ba6, 0xD28DC), prev=gp-0x69bc, cal=0xCA06C[10] -> 0xD2006)   @0x34be4
    y4 = blend(LERP(gp-0x6ba6, 0xD2888), prev=gp-0x69ba, cal=same table)               @0x34fc4

Direction CONFIRMED at 0x34be4 (`cmp r25,r10 / ble` -> instant snap when raw <= old): **FALLING is
instant, RISING is slowed.** A fast-attack / slow-release gain reducer.

Lowering the coefficient attenuates the 42 Hz pump **without moving the static gain map at all** --
the blend converges to the same steady-state value, so DC assist and manual steering feel are
untouched. That is what makes this a better lever than flattening 0xD28DC/0xD2888 (which moves DC gain
across the whole driving envelope) or than 0xC63BA (which filters only the torque lane, while the
index also carries a resolver-rate-derivative lane).

WHY 43, AND THE HONEST CEILING ON THIS LEVER
-------------------------------------------------------------------------------------------------------
Simulating the literal integer arithmetic at 1 kHz with the confirmed asymmetric direction, against
V59's measured hands-off amplitude distribution (|tq| median 218, p90 829, p99 1451):

    cal    tau@1kHz   eps med   eps p90   eps p99
    102      10.0ms     0.020     0.104     0.169     <- stock
     64      16.0ms     0.020     0.079     0.123
     43      23.8ms     0.019     0.072     0.099     <- V60, the knee
     32      32.0ms     0.017     0.068     0.086

🛑 **The effect SATURATES, and the reason is structural: the FALLING edge is instant no matter what the
coefficient is, so this lever can never remove the modulation entirely.** It buys ~1.7x at p99 and then
flattens. 43 sits at the knee -- past it you double the time constant again for ~0.013 of eps.
43 is also already a value in this very calibration block (0xD200C, the gain scalar), i.e. inside the
calibration's own numeric vocabulary.

Time constant 10 -> 24 ms at 1 kHz (20 -> 48 ms if task 5 turns out to run at 500 Hz -- UNRESOLVED, see
STATE.md). Both are short against steering dynamics (>200 ms), so the feel risk is low: the only
change is that assist gain recovers slightly more slowly after a sharp torque transient.

WHAT THE RESULT WILL MEAN
-------------------------------------------------------------------------------------------------------
V60 keeps V59's boost-index depth probe UNCHANGED, and the probe reads gp-0x6ba6, which is UPSTREAM of
the blend. So the probe is a **control**: the index distribution must come back statistically identical
to V59. If it does, and the grinding changes, the blend is the only thing that moved.

  * grinding measurably reduced  => the pump is load-bearing; 0xD2006 is a real fix and can be tuned.
  * grinding unchanged           => the pump is an ECHO, not the drive. That closes a mechanism this
                                    kit has spent three builds on, and redirects the search. A null
                                    here is a RESULT, not a failure.
  * index distribution moved     => something upstream shifted; the comparison is void, re-derive.

GATE 1 -- RAM ownership: VACUOUS. This is a calibration halfword. No cave change, no new RAM, no code.
         The cave, hook and payload are byte-identical to V59 (asserted below).
GATE 2 -- closed-loop stability: this is the one to argue. 0xD2006 sits on the BASE ASSIST path, and
         the tracer established there is NO LKAS-only decoupling point anywhere in this chain (unlike
         V57's 0xC646C, which had 6 reader sites to fork). So this changes manual feel, not just the
         LKAS lane. The change is a pure DYNAMICS change on a gain-SCHEDULING variable -- it adds no
         gain, moves no static map, and cannot change any steady-state value. Phase lag is added only
         to the gain schedule's recovery edge, not to the forward torque path. tau stays under 50 ms
         in the worst case. This is a materially smaller perturbation than flattening either curve.

BLAST RADIUS -- byte-verified, whole-image scan for 32-bit pointers into [0xD2000,0xD2014):
    0xC7A80 -> 0xD2000 (mode10 ceiling)   0xCA094 -> 0xD2006 (mode10 BLEND, THIS EDIT)
    0xC7A84 -> 0xD2002 (mode11)           0xCA098 -> 0xD2008 (mode11)
    0xC7A88 -> 0xD2004 (mode12)           0xCA09C -> 0xD200A (mode12)
    0xCA34C -> 0xD200C (mode10 gain)      0xCA434 -> 0xD2012 (mode10, 1-byte table)
    0x8AEAC -> 0xD2000  -- the CRC/block-boundary directory, not a functional consumer
The three identical 102s are modes 10/11/12's INDEPENDENT entries, not one value read three times;
each table does a single pointer dereference, never an array walk. Mode 10's cell is private.

⚠ 0xD2006 is owned by CRC block [0xD2000,0xD2FFC) -- a THIRD block, touched by no previous build.
  MAIN and CAL CRCs must both come back UNCHANGED; that is asserted as machine proof.

🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.
"""
import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v58_tva as V58                # noqa: E402
import build_v59_tva as V59                # noqa: E402

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

# ---- THE EDIT ---------------------------------------------------------------------------------------
BLEND_ADDR = 0xD2006          # 0xCA06C[mode 10] -> this cell. The amplitude-LERP slew coefficient, Q10.
BLEND_STOCK = 102             # 0.0996 -- passes ~0.37 of 42 Hz
BLEND_NEW = 43                # 0.0420 -- passes ~0.17 of 42 Hz;  eps p99 0.169 -> 0.099

# Neighbours in the SHARED 0xD2000 block that must NOT move (modes 11/12 + the other two tables).
BLOCK_NEIGHBOURS = (0xD2000, 0xD2002, 0xD2004, 0xD2008, 0xD200A, 0xD200C, 0xD200E, 0xD2010, 0xD2012)

TAG = "LKAS-4x-mss0-decouple0xC646C-boostindexdepth-blend43-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V60-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v60_plain_image.bin"))
V59_BIN = str(plain_image_path("_v59_plain_image.bin"))


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def assert_blend(code, label, expect):
    assert u16(code, BLEND_ADDR) == expect, \
        f"{label}: blend coefficient 0x{BLEND_ADDR:05X} is {u16(code, BLEND_ADDR)}, expected {expect}"


def build():
    if not os.path.exists(V59_BIN):
        print(f"  {V59_BIN} missing -- running the V59 builder first\n")
        V59.build()
    v59 = bytearray(open(V59_BIN, "rb").read())
    print(f"  V59 source {V59_BIN}\n    SHA256 {hashlib.sha256(bytes(v59)).hexdigest()}")

    # ---- gate the SOURCE before touching it ----------------------------------------------------
    FF.assert_crc_chain(v59, "V59 source")
    assert walk(bytes(v59), label="V59 source") == 0
    assert walk_all_blocks(bytes(v59), label="V59 source") == 0
    V59.assert_probe_sites(v59, "V59 source")
    V59.assert_index_chain(v59, "V59 source")
    V55.assert_variant_tables(v59)
    V57.assert_decoupled(v59, "V59 source")
    assert u16(v59, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V59 source lost the lockout edit"
    assert_blend(v59, "V59 source", BLEND_STOCK)

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    assert u16(baseline, BLEND_ADDR) == BLEND_STOCK, \
        "the blend coefficient is not 102 in the V38 baseline -- provenance broken"

    code = bytearray(v59)

    # ---- the single edit -----------------------------------------------------------------------
    print(f"\n  THE EDIT -- boost-amplitude blend coefficient (0xCA06C[mode 10] -> 0x{BLEND_ADDR:05X}):")
    print(f"    0x{BLEND_ADDR:05X}  {BLEND_STOCK} -> {BLEND_NEW}   "
          f"(Q10 {BLEND_STOCK/1024:.4f} -> {BLEND_NEW/1024:.4f};  "
          f"42 Hz transmission ~0.37 -> ~0.17;  tau 10.0 -> 23.8 ms @1 kHz)")
    struct.pack_into("<H", code, BLEND_ADDR, BLEND_NEW)
    assert_blend(code, "V60", BLEND_NEW)

    # ---- everything else must be byte-identical to V59 -----------------------------------------
    # the cave, the hook, and V59's whole probe are untouched: V60 is a CALIBRATION-ONLY delta.
    assert bytes(code[V59.CAVE_BASE:V59.CAVE_BASE + len(V55.CAVE_BYTES)]) == \
        bytes(v59[V59.CAVE_BASE:V59.CAVE_BASE + len(V55.CAVE_BYTES)]), "the cave moved"
    assert bytes(code[V59.HOOK_ADDR:V59.HOOK_ADDR + 4]) == \
        bytes(v59[V59.HOOK_ADDR:V59.HOOK_ADDR + 4]), "the hook moved"
    V59.assert_probe_sites(code, "V60")
    V59.assert_index_chain(code, "V60")
    V57.assert_decoupled(code, "V60")
    V55.assert_variant_tables(code)

    for a in BLOCK_NEIGHBOURS:
        assert u16(code, a) == u16(v59, a) == u16(baseline, a), \
            f"shared 0xD2000-block neighbour 0x{a:05X} moved -- only mode 10's blend may change"
    # the two amplitude curves themselves must stay stock: V60 changes the FILTER, not the map.
    for addr, n in ((V59.LERP1_ADDR, 13), (V59.LERP4_ADDR, 13)):
        assert struct.unpack_from(f"<{n}H", code, addr) == \
            struct.unpack_from(f"<{n}H", baseline, addr), \
            f"amplitude curve 0x{addr:05X} moved -- V60 must not touch the static gain map"
    # every calibration lever on record stays where V59 left it
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC6440, "r24"), (0xC643E, "r26"),
                    (0xC6424, "shaper deadband"), (0xC646C, "shared sensor scale"),
                    (0xC6CD0, "private LKAS gain"), (0xC62EA, "low-speed lockout"),
                    (0xC63BA, "FUN_3b66a EMA alpha -- NOT this build's lever")):
        assert u16(code, a) == u16(v59, a), f"{name} 0x{a:05X} moved -- V60 edits ONE halfword"
    assert code[0xC64DE] == 27 and code[0xC64A3] == 1
    # FactorC stays stock: V59's drive DISFAVOURED that lever, so it must not ride along silently
    assert struct.unpack_from("<9H", code, 0xD27BC) == \
        struct.unpack_from("<9H", baseline, 0xD27BC), "FactorC 0xD27BC moved"

    # ---- CRC -----------------------------------------------------------------------------------
    blend_block = V53.owning_block(code, BLEND_ADDR)
    assert blend_block not in (MAIN_BLOCK, CAL_BLOCK), \
        "expected the blend cal to live in its own block, not MAIN or CAL"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK, blend_block}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
        if block in (MAIN_BLOCK, CAL_BLOCK):
            assert old_crc == new_crc, \
                f"{block} CRC moved -- V60 touches neither the cave nor the calibration block"

    # ---- exact diff ----------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff against a full_image(): 0xFF filler below 0x13000 reports ~51,000
    # bogus bytes. Restricted to [0x13000,0x100000).
    d59 = [i for i in range(0x13000, 0x100000) if code[i] != v59[i]]
    permitted = set(range(BLEND_ADDR, BLEND_ADDR + 2)) | set(range(blend_block[1], blend_block[1] + 4))
    stray = [i for i in d59 if i not in permitted]
    assert not stray, f"V60 vs V59 touches bytes outside the blend cal + its CRC: {[hex(x) for x in stray]}"
    # 102 = 0x0066, 43 = 0x002B -- both have a 0x00 high byte, so only the LOW byte actually differs.
    # Assert the CRC trailer moved and the changed set is exactly {low byte} or {both cal bytes} + CRC,
    # rather than a fixed count that silently encodes which bytes happened to differ.
    cal_changed = [i for i in d59 if BLEND_ADDR <= i < BLEND_ADDR + 2]
    crc_changed = [i for i in d59 if blend_block[1] <= i < blend_block[1] + 4]
    assert cal_changed == [BLEND_ADDR], \
        f"expected only the low cal byte to differ (102->43 share a 0x00 high byte), got {[hex(x) for x in cal_changed]}"
    assert len(crc_changed) == 4, f"the 0xD2000-block CRC trailer did not fully move: {crc_changed}"
    assert len(d59) == 5, f"expected 1 cal byte + 4 CRC bytes = 5, got {len(d59)}"
    print(f"\n  V60 vs V59: {len(d59)} bytes  (1 blend cal byte + its block CRC ONLY)")
    print("    => MAIN CRC unchanged = machine proof the cave/probe did not move")
    print("    => CAL  CRC unchanged = machine proof no 0xC6xxx calibration moved")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V60 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")

    # ---- post-write gates ----------------------------------------------------------------------
    FF.assert_crc_chain(code, "V60")
    assert walk(bytes(code), label="V60") == 0
    assert walk_all_blocks(bytes(code), label="V60") == 0
    V59.assert_probe_sites(code, "V60")
    V55.assert_variant_tables(code)
    assert_blend(code, "V60", BLEND_NEW)

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback ---------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == FF.EXPECTED_HEADERS
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    rwd = encode_x31(source_info["headers"], source_info["blocks"],
                     [bytes(code[START:END]).translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V60 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V60 readback")
    assert walk(bytes(readback), label="V60 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V60 readback") == 0
    V59.assert_probe_sites(readback, "V60 readback")
    V59.assert_index_chain(readback, "V60 readback")
    V57.assert_decoupled(readback, "V60 readback")
    V55.assert_variant_tables(readback)
    assert_blend(readback, "V60 readback", BLEND_NEW)
    for a in BLOCK_NEIGHBOURS:
        assert u16(readback, a) == u16(baseline, a), f"readback: neighbour 0x{a:05X} moved"

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("\n  THE DRIVE THAT MAKES THIS INTERPRETABLE -- same route shape as V59 (route 2c):")
    print("     parking-lot creep, v <= 5 m/s, LKAS applying, SUSTAINED hands-off stretches >= 3 s,")
    print("     deliberate LKAS on/off passes at matched speed and angle. The 10-13 m/s under-load")
    print("     population is worth a pass too. Decode with rlog-tools/decode_v59_boostindex.py --")
    print("     the probe is UNCHANGED, so it is a CONTROL: the index distribution must come back")
    print("     statistically identical to V59 (76.9/18.5/4.6/0.04 at engaged+creep+hands-off).")
    print("     If the index matches and the grinding moved, the blend is the only thing that did.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
