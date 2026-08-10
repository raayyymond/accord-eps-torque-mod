#!/usr/bin/env python3
r"""build_v89_tva.py -- V89 = the FLOWN V88 + more MODELLED COULOMB FRICTION, and a probe for it.

    base   _v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256_plain_image.bin
           sha256 96b1e018d2058984ada1ba4add7ce42516d5ed9cab65c7be7db294c3d0ca47b8

    0xC40D2   102 -> 204     K1, the |model|-proportional Coulomb friction coefficient   (2.000x)
    0xC4B38  6894 -> 1e95    cave probe source: gp-0x6b98 -> gp-0x6ae2 (= friction x 1024)
    0xC4B46    a8 -> a6      cave magnitude rung: sar 0x8 -> sar 0x6, trips at +-64 counts

3 bytes on a flown base. Cal-only on the control side; no cave is created, moved, grown or shrunk.

===================================================================================================
WHY -- and this is a DIFFERENT CLASS FROM EVERY BUILD SINCE V38
===================================================================================================
The arc: V38-V52 authority/filters/poles/caves - V53-V61 telemetry + lane mutes - V62-V73 the rate
lane (r24/r26) - V74-V83a the base-assist damper - V84-V86B damper reverts and phase - V87 a
subtractive measurement build - V88 Lever B restored. **Every one of those either moved the LKAS
COMMAND or moved a lane that SUMS INTO it.** V89 moves neither. It edits the *plant model* that a
disturbance observer compares the assist against.

`FUN_0003b8f6` -> `FUN_0003bc20` -> `FUN_00038148`, all three read in Ghidra this session
(decompile first, then assembly, per the standing instruction):

    friction = clamp( EMA_a( |model| * ratio * K1/1024 + ratio * K0/1024 ), -10, +10 )   0x3BAF6..
               ratio = clamp( polarity * gp-0x6abc * 12 / cal[0xC40BC] , -1, +1 )        0x3BAAE..
    out      = clamp( (model - friction - damping) * cal[0xC6468], -20000, +20000 )      0x3BBBE..
    -> gp-0x6bfc -> FUN_0003bc20 (plausibility) -> gp-0x6bfe
    -> FUN_00038148:  residual = MODEL - ACTUAL ;  gp-0x6b70 = sign(res) * LERP(|res|)

**It is a DISTURBANCE OBSERVER.** If the model UNDER-states real Coulomb friction, the un-modelled
friction lands in the residual and the observer chases it. That is what a stick-slip ratchet is.

THE MEASUREMENT THAT PICKED THIS CELL (v89_c2 / v89_c3, 30 routes, 284 min, 235 episode blocks)
  * engaging LKAS multiplies the 6-9 Hz column mode by **2.8x**, and by **1.5x more than a
    32-38 Hz control band** -- band contrast +0.413 [+0.146, +0.667], EXCLUDES 0.
  * that amplification does **NOT** grow with wheel rate: +0.022 [-0.070, +0.116].
    => the target is a CONSTANT GAIN, so **nothing here limits the LKAS command's angle rate.**
  * friction DOSE, the only one this car has ever flown -- `0xC40BC` 600 vs 6000, within-route:
        gate  600 (more friction) : engaged/manual 6-9 Hz = 2.89x [2.14,  3.92]
        gate 6000 (less friction) : engaged/manual 6-9 Hz = 6.58x [3.19, 13.14]
        eng x FRIC6000 band contrast +0.682 [+0.213, +1.166], EXCLUDES 0
    => LESS friction, MORE ratchet. **The gradient points UP.**
  * independently, driver GRIP damps this band: log-hands slope -0.655 vs the control's -0.266,
    CIs DISJOINT. Two unrelated lines agree that column friction kills this mode.

WHY K1 AND NOT THE GATE
  `0xC40BC` changes |ratio|, which confounds friction MAGNITUDE with the ratio's RELAY-NESS.
  `0xC40D2` scales the |model| arm ALONE, leaving the ratio's shape untouched
  => it raises magnitude without flattening anything into a relay. It is NOT the V80 class.
  🛑 `0xC4080` (K0, the pure-Coulomb arm, 0 on every build) is the recorded "NEVER RAISE" relay
  hazard -- amplitude-INDEPENDENT and unbounded. **V89 does not touch it.** That note stands.

BLAST RADIUS -- `0xC40D2` has ONE reader and ZERO writers
  Byte-censused twice, through the recorded `hw2 = disp|1` trap (`ld.hu 0x50d2[tp]` encodes 0x50d3;
  a naive scan for 0x50d2 returns a FALSE ZERO, and did on the first pass this session):
      0x3BAFE  ld.hu 0x50d2[tp],r12      <- the only access in the whole 1 MiB image
  Virgin on all 88 builds. No int/float twin problem: `FUN_0003b8f6` is all-float and reads the
  cal once, so any lockstep monitor recomputing it reads the SAME edited cell.

GATE 1 (RAM ownership) -- vacuous: no cave is created and no RAM is claimed. The cave is edited
  IN PLACE inside the 62-byte payload that has now flown four times (V86, V86B, V87, V88).
GATE 2 (closed-loop stability) -- friction is a DAMPING term entering with a minus sign, and the
  +/-10.0 clamp sits ~50x above the working point (|model| would have to reach 50 to bind, while
  the model's own bar arm is clamped at 15). Raising it cannot flatten, saturate or invert anything.
  ⚠ It DOES reduce the model output by 0.0996*|model|*2639 counts, which shifts the observer's
  residual. That is the intended effect and it is the thing the flight scores.

===================================================================================================
PRE-REGISTRATION -- write it down before the drive
===================================================================================================
IDENTITY (parameter-free, its control already measured):
    On V88 the cave byte and the 427 packer read the SAME cell, so `b6 == (MOTOR_TORQUE >= 160)`
    held at **0.9654** (chance 0.6028). On V89 the cave reads gp-0x6ae2 instead, a different cell
    entirely, so that agreement MUST COLLAPSE toward chance.
    => ~0.60 means V89 flew - ~0.97 means V88 did.  The exact dual of V88's own test.
H1  the probe must FIRE: gp-0x6ae2 non-zero on a large majority of engaged frames, and its
    `sar 0x6` rung (>= 64 counts = friction >= 0.0625) must have a duty strictly between 0 and 1.
    A dead or a railed rung makes the flight uninterpretable -- say so rather than scoring bands.
H2  THE LEVER: engaged 6-9 Hz column-torque energy must FALL vs V88 on speed- and rate-matched
    windows, CI excluding 1.00. 🛑 The 32-38 Hz control band must NOT fall by as much.
H3  THE CONSTRAINT: 0.5-3 Hz LKAS command content must be UNCHANGED. V89 does not touch the command
    path at all, so this is a structural expectation, not a hope -- if it moves, the model of the
    chain is wrong and that is the headline.
H4  🛑 THE OPERATOR SCORES THE SYMPTOMS, IN HIS WORDS. Bands are the instrument, never the verdict.

🛑 HONEST LABEL. This is the FIRST build in the lineage to touch the plant model, and the dose
   direction rests on a 600-vs-6000 contrast that confounds friction MAGNITUDE with RELAY-NESS.
   K1 raises magnitude alone. **That the two act the same way is BELIEF, and it is exactly what
   this flight tests.** A null on H2 falsifies the friction account cleanly.
⚠ COST: more modelled Coulomb friction can make the wheel feel notchier or heavier on-centre. The
   instrument cannot see that. If it feels worse to drive, that outranks any band.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V89_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path(
    "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256_plain_image.bin"))
BASE_SHA = "96b1e018d2058984ada1ba4add7ce42516d5ed9cab65c7be7db294c3d0ca47b8"

CAVE_BASE, CAVE_LEN = 0xC4B34, 62
PROBE_LOAD_OFF, MAG_SAR_OFF = 4, 18
K1_ADDR, K1_OLD, K1_NEW = 0xC40D2, 102, 204
OLD_DISP, NEW_DISP = 0x6B98, 0x6AE2          # gp-relative, both negative
OLD_SHIFT, NEW_SHIFT = 8, 6
NEW_MAG_T = 1 << NEW_SHIFT                   # 64 counts = friction 0.0625

TWIN_HW1_ADDR = 0x55DF0                      # `ld.h -0x6b98[gp],r6` -- supplies our hw1 `2437`
TWIN_HW2_ADDR = 0x3BC04                      # `st.h r12,-0x6ae2[gp]` -- supplies our hw2 `1e95`

EDITS = [
    (K1_ADDR, 2, struct.pack("<H", K1_OLD), struct.pack("<H", K1_NEW),
     f"K1 modelled Coulomb friction: {K1_OLD} -> {K1_NEW} = {K1_NEW/K1_OLD:.3f}x "
     f"(friction = {K1_NEW/1024:.4f}*|model|)"),
]
CAVE_EDITS = [
    (CAVE_BASE + PROBE_LOAD_OFF, 2, struct.pack("<h", -OLD_DISP), struct.pack("<h", -NEW_DISP),
     "cave probe source: gp-0x6b98 -> gp-0x6ae2 (= the FRICTION term x 1024)"),
    (CAVE_BASE + MAG_SAR_OFF, 1, bytes([0xA0 | OLD_SHIFT]), bytes([0xA0 | NEW_SHIFT]),
     f"cave magnitude rung: sar 0x{OLD_SHIFT:x} -> sar 0x{NEW_SHIFT:x}, trips at +-{NEW_MAG_T}"),
]

VARIANT_TOKEN = "V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v89_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V89-{TAG}-0x{START:X}-0x{END:X}.rwd")

# Cells that must NOT move. Everything V88 froze, plus the friction family's own hazards.
FROZEN = {
    0xC4080: (2, "K0 pure-Coulomb arm -- the recorded NEVER-RAISE relay hazard, stays 0"),
    0xC40BC: (2, "friction relay gate -- 600. 6000 measured 2.3x WORSE; DO NOT restore it"),
    0xC40D0: (2, "friction EMA alpha -- stays 408 (16.7 Hz); V89 is single-variable in K1"),
    0xC40D4: (2, "command-branch EMA -- V86's FALSIFIED lever, stays 573"),
    0xC6468: (2, "model output gain -- SHARED, 5 readers, stays 2639"),
    0xC646E: (2, "damping gain -- unmeasured sizing figure, stays 1428"),
    0x3AA96: (1, "Lever B gate -- V88's, stays 0xFB"),
    0xC6446: (2, "Lever B arm -- V88's 5244, stays (this build is NOT a rate-lane build)"),
    0x3AB76: (1, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC407E: (2, "hard-fault interlock clamp -- Honda's 511"),
    0xD77DA: (2, "FactorC m26 Y[0] -- damper stays Honda 0"),
    0xD77EE: (2, "FactorC m27 Y[0] -- damper stays Honda 0"),
    0xC646C: (2, "shared sensor scale -- Honda 891"),
    0xC6CD0: (2, "private forward LKAS gain -- 3564 = 4.000x, NEVER lower"),
    0xC62EA: (2, "steer-to-zero -- 0"),
    0xC61F6: (2, "r24 deadzone -- 3, raising it cuts the WRONG way"),
    0xC63A0: (2, "INERT, no mechanism"),
}


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def assert_single_reader(buf):
    """🛑 The `hw2 = disp|1` trap: a naive scan for 0x50d2 returns a FALSE ZERO.  Scan BOTH."""
    disp = K1_ADDR - 0xBF000
    hits = []
    for cand in (disp, disp | 1):
        t = struct.pack("<H", cand)
        i = 0
        while True:
            i = bytes(buf).find(t, i, END)
            if i < 0:
                break
            if i >= 2 and i % 2 == 0:
                hw1 = struct.unpack_from("<H", buf, i - 2)[0]
                if (hw1 & 0x1F) == 5 and ((hw1 >> 5) & 0x3F) in range(0x38, 0x40):
                    hits.append(i - 2)
            i += 1
    hits = sorted(set(hits))
    assert hits == [0x3BAFE], f"🛑 0xC40D2 reader census is {[hex(h) for h in hits]}, expected " \
                              "exactly [0x3BAFE] -- the blast-radius claim is void"
    print(f"    ✅ 0x{K1_ADDR:05X}: exactly ONE tp-based access in the whole image, at 0x3BAFE "
          f"(`ld.hu 0x50d2[tp],r12`), inside FUN_0003b8f6. Zero writers.")


def assert_cave_halfwords(buf):
    """The new load is not hand-encoded: BOTH halfwords are already flying on this base."""
    hw1 = rd(buf, TWIN_HW1_ADDR, 2)
    hw2 = rd(buf, TWIN_HW2_ADDR + 2, 2)
    ours = hw1 + struct.pack("<h", -NEW_DISP)
    assert hw1 == bytes.fromhex("2437"), f"hw1 twin is {hw1.hex()}, expected 2437"
    assert hw2 == struct.pack("<h", -NEW_DISP), \
        f"hw2 twin at 0x{TWIN_HW2_ADDR:05X} is {hw2.hex()}, expected {(-NEW_DISP) & 0xFFFF:04x}"
    assert struct.unpack("<h", ours[2:])[0] == -NEW_DISP
    assert (-NEW_DISP & 0xFFFF) % 2 == 0, "ld.h needs an even displacement"
    print(f"    ✅ new cave load {ours.hex()} = hw1 `2437` (flown at 0x{TWIN_HW1_ADDR:05X}, "
          f"`ld.h ..[gp],r6`) + hw2 `{hw2.hex()}` (flown at 0x{TWIN_HW2_ADDR:05X}, the store to "
          "gp-0x6ae2). Only the COMBINATION is new; each halfword is already on the car.")


def assert_probe_target_free(buf):
    """gp-0x6ae2 must stay 1 writer / 0 readers -- reading it must not perturb anything."""
    disp = (-NEW_DISP) & 0xFFFF
    w, r = [], []
    for cand in (disp, disp | 1):
        t = struct.pack("<H", cand)
        i = 0
        while True:
            i = bytes(buf).find(t, i, END)
            if i < 0:
                break
            if i >= 2 and i % 2 == 0:
                hw1 = struct.unpack_from("<H", buf, i - 2)[0]
                op = (hw1 >> 5) & 0x3F
                if (hw1 & 0x1F) == 4 and op in range(0x38, 0x40):
                    (r if op in (0x38, 0x39, 0x3C, 0x3F) else w).append(i - 2)
            i += 1
    assert sorted(set(w)) == [0x3BC04], f"gp-0x6ae2 writers {[hex(x) for x in sorted(set(w))]}"
    assert not set(r), f"gp-0x6ae2 already has readers {[hex(x) for x in sorted(set(r))]}"
    print("    ✅ gp-0x6ae2 on the BASE: 1 writer (0x3BC04), 0 readers ⇒ blast-radius-zero probe.")


def assert_clamp_headroom():
    """The +/-10.0 friction clamp must stay far from the working point at the new K1."""
    bind = 10.0 * 1024.0 / K1_NEW
    assert bind > 40.0, f"the +/-10 clamp binds at |model| = {bind:.1f} -- too close"
    print(f"    ✅ GATE 2: the +/-10.0 clamp binds only at |model| >= {bind:.1f}; the model's own "
          f"bar arm is clamped at 15 and its command arm runs ~0.2-1.0 ⇒ ~{bind/1.0:.0f}x margin.")


def build():
    base = bytearray(Path(BASE_BIN).read_bytes())
    assert len(base) == 0x100000
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    assert base_sha == BASE_SHA, f"the V88 base is {base_sha}, expected {BASE_SHA}"
    assert walk_all_blocks(bytes(base)) == 0, "the V88 base's CRC chain does not verify"
    print("=" * 102)
    print("  V89 -- the FLOWN V88 + more MODELLED COULOMB FRICTION (0xC40D2), and a probe for it")
    print(f"    base {os.path.basename(BASE_BIN)}\n    sha256 {base_sha}")
    print("=" * 102)

    print("\n  STRUCTURE, asserted from the base image")
    assert u16(base, K1_ADDR) == K1_OLD, f"0xC40D2 is {u16(base, K1_ADDR)}, expected {K1_OLD}"
    print(f"    0x{K1_ADDR:05X} = {K1_OLD}  K1, virgin on all 88 builds")
    assert_single_reader(base)
    assert_cave_halfwords(base)
    assert_probe_target_free(base)
    assert_clamp_headroom()
    assert rd(base, CAVE_BASE + PROBE_LOAD_OFF - 2, 4) == bytes.fromhex("24376894"), \
        "the cave's probe load is not V88's `ld.h -0x6b98[gp],r6`"
    assert base[CAVE_BASE + MAG_SAR_OFF] == (0xA0 | OLD_SHIFT), "the cave's sar byte is not V88's"

    print("\n  FROZEN CELLS -- asserted unchanged on the base and again on the built image")
    for a, (w, why) in sorted(FROZEN.items()):
        v = u16(base, a) if w == 2 else base[a]
        print(f"    0x{a:05X} = {v if w == 2 else f'0x{v:02x}':<7} {why}")

    code = bytearray(base)
    attributed = set()
    print("\n  CONTROL EDITS")
    for a, w, pre, post, lbl in EDITS:
        got = rd(code, a, w)
        assert got == pre, f"0x{a:05X}: expected {pre.hex()}, found {got.hex()}"
        code[a:a + w] = post
        attributed.update(range(a, a + w))
        print(f"    0x{a:05X}  {pre.hex()} -> {post.hex()}   {lbl}")
    print("\n  INSTRUMENT EDITS (in place, inside the four-times-flown cave)")
    for a, w, pre, post, lbl in CAVE_EDITS:
        got = rd(code, a, w)
        assert got == pre, f"0x{a:05X}: expected {pre.hex()}, found {got.hex()}"
        code[a:a + w] = post
        attributed.update(range(a, a + w))
        print(f"    0x{a:05X}  {pre.hex()} -> {post.hex()}   {lbl}")

    for a, (w, why) in FROZEN.items():
        assert rd(code, a, w) == rd(base, a, w), f"🛑 FROZEN cell 0x{a:05X} moved -- {why}"
    print("    ✅ every FROZEN cell is byte-identical to the base after the edits")

    # ---- CRC ------------------------------------------------------------------------------------
    # 🛑 The blocks are NOT uniform 0x1000. Real map: blk1 spans 3 pages, blk2 four, blk47 six,
    # blk50 covers [0x013000,0x0C4FFC). Synthesising a uniform map fails 4/50 -- it did here on the
    # first run. Use the image's OWN block map via V53.owning_block / FF.crc_block_map.
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  CRC -- {len(blocks)} block(s) move")
    for blk in blocks:
        if any(blk[1] <= a < blk[1] + 4 for a in touched):
            raise SystemExit("an edit landed on a CRC trailer")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len(owners)} byte(s)")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the block the bootloader SKIPS (V40's brick)"
    assert not [a for a in attributed if a < START or a >= END], "an edit landed outside the region"
    print("\n    ✅ full 50-block chain: 50/50 PASS · 0 bytes into [0xC5000,0xC5FFC)")

    # ---- zero-unattributed full diff -------------------------------------------------------------
    by_addr = {}
    for a, w, pre, post, lbl in EDITS + CAVE_EDITS:
        for k in range(w):
            by_addr[a + k] = f"0x{a:05X}  {lbl}"
    runs, i = [], 0
    while i < len(code):
        if code[i] != base[i]:
            j = i
            while j < len(code) and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1
    attribute = lambda d: by_addr.get(d, "CRC trailer" if d in crc_only else None)  # noqa: E731
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V89 vs the FLOWN V88 base -- over the WHOLE 1 MiB image")
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, f"🛑 UNATTRIBUTED bytes vs V88: {[hex(x) for x in stray[:16]]}"
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    assert hashlib.sha256(bytes(rt)).hexdigest() == base_sha, "the round trip does not reproduce V88"
    print("    ⇒ ZERO unattributed bytes; restoring the attributed set reproduces V88 BIT-FOR-BIT.")

    # ---- value-anchored readback from the BUILT image --------------------------------------------
    print("\n  VALUE-ANCHORED VERIFICATION, read back from the BUILT image")
    assert u16(code, K1_ADDR) == K1_NEW
    print(f"    0x{K1_ADDR:05X} = {u16(code, K1_ADDR)}   friction = "
          f"{K1_NEW/1024:.4f}*|model|  ({K1_NEW/K1_OLD:.3f}x Honda)")
    got = rd(code, CAVE_BASE + PROBE_LOAD_OFF - 2, 4)
    print(f"    cave load = {got.hex()}  = `ld.h -0x{NEW_DISP:04X}[gp],r6` (friction x 1024)")
    assert got == bytes.fromhex("2437") + struct.pack("<h", -NEW_DISP)
    assert code[CAVE_BASE + MAG_SAR_OFF] == (0xA0 | NEW_SHIFT)
    print(f"    cave rung = sar 0x{NEW_SHIFT:x}  ⇒ b6 = (|friction*1024| >= {NEW_MAG_T}) "
          f"= (friction >= {NEW_MAG_T/1024:.4f})")

    # ---- .rwd ------------------------------------------------------------------------------------
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V89 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert u16(dec, K1_ADDR) == K1_NEW
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("\n    ✅ READBACK: the decoded .rwd payload is byte-identical to the built image; "
          "anchors and the 50/50 chain re-verified from it.")

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V89_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            shipped = Path(OUT).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha
            FF.assert_x31_checksum(shipped, "V89 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code)
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded and re-verified INDEPENDENTLY.")

    print(f"\n  V89 [{VARIANT_TOKEN}]")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 HONEST LABEL: the FIRST build in the lineage to touch the PLANT MODEL rather than")
    print("     the command or a lane that sums into it. The dose DIRECTION is measured (600 vs")
    print("     6000, +0.682 [+0.213, +1.166]); that K1 acts the same way as the gate is BELIEF,")
    print("     because the gate contrast confounds magnitude with relay-ness. A null on H2")
    print("     falsifies the friction account cleanly, and that is worth the flight.")
    print("  ⚠ COST: more modelled Coulomb friction can feel notchier or heavier on-centre. The")
    print("     instrument cannot see that. If it drives worse, that outranks every band.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    assert len(EDITS) == 1 and sum(w for _, w, _, _, _ in EDITS) == 2
    assert len(CAVE_EDITS) == 2 and sum(w for _, w, _, _, _ in CAVE_EDITS) == 3
    assert len({a for a, *_ in EDITS + CAVE_EDITS}) == 3, "duplicate address"
    build()
