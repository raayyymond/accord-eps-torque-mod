#!/usr/bin/env python3
r"""build_v87_tva.py -- V87 = a MEASUREMENT build on a clean V38 base.

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
**Every control lever the V87 session examined is dead, blocked, or sized on a number nobody has ever
measured.** V87 stops guessing: it puts the delivered motor command `gp-0x6b98` onto a 10-bit CAN field
at 50 Hz, on a base stripped back to V38 plus the two mods the operator asked for.

🛑 **THIS BUILD IS NOT EXPECTED TO CHANGE HOW THE CAR FEELS AT 8 Hz.** It carries NO damping edit, NO
filter, and NO new authority. Judged as a ratchet fix it will read as a null, and that is by design.
What it buys is `|gp-0x6b98|`'s real amplitude, which four independent analyses named as the blocking
unknown: it sets the phase budget for ANY future filter (currently *assumed* at 120 counts, and the
answer moves 5x across the plausible range) and it discriminates the two live readings of the
resonance -- a passive structure being driven, versus a closed-loop pole. That fork decides whether a
filter helps or HURTS.

⚠ **FEEL CHANGES ARE REAL AND THEY COME FROM THE REBASE, NOT FROM AN 8 Hz LEVER.** V38 is 49 builds
back. Everything after it -- the friction relay (`0xC40BC` 600->6000, V85), Lever B, the engaged
low-speed damper (V86B) -- is GONE. The operator should expect the car to feel like V38 did, plus the
ratchet fix, plus steer-to-zero.

THE BASE -- V38, chosen by the operator
--------------------------------------------------------------------------------------------------
`_v38_plain_image.bin`. V38 is the last point in the lineage where the arc had a single well-understood
lever (the 4x forward LKAS gain). Everything since is confounded: the V38->V86B path silently reverted
levers at least three times, and the V87 session found the "1-6% of clamp" sizing figure that STATE.md
labels MEASURED is, in its own source memory, "(prior-session estimate)".

THE EDIT SET -- 6 control edits (11 bytes) + the flown 62-byte telemetry cave
--------------------------------------------------------------------------------------------------
  #  addr       w  from    to      what
  1  0x2A1F0    2  6c74    d07c    V57 repoint: forward LKAS reader tp+0x746C -> tp+0x7CD0
  2  0xC646C    2  3564    891     shared sensor scale BACK TO STOCK (un-confounds 4 feedback readers)
  3  0xC6CD0    2  65535   3564    private 4x forward LKAS gain (V57 style)
  4  0x454FE    1  ba      b5      V42 ratchet fix (Bcond BNE -> BR)
  5  0xC62EA    2  320     0       steer to zero
  6  0x55DF2    2  e893    6894    427 MOTOR_TORQUE source: gp-0x6c18 -> gp-0x6b98   <<< THE PROBE
  7  0x55C0E    4  2436e8ea 86ff26ef  jarl -> cave (330 byte-4 telemetry, lifted from V86B verbatim)
  8  0xC4B34   62  FF...   <cave>  the flown V86B probe cave, byte-for-byte

★ WHY EDIT #1-#3 TOGETHER: V38 puts the 4x in `0xC646C`, which is NOT "the LKAS gain" -- it is a
SHARED Q15 sensor scale with SIX readers: one forward (`0x2a1ee`, the LKAS setpoint path) and FOUR
feedback (`0x2b656`, `0x2c488`, `0x36686`, `0x3684a`). V38's 3564 therefore raised the feedback paths
too. V57 fixed that by repointing ONLY the forward reader at a private cell. V87 adopts the V57 form:
identical forward 4.000x, feedback back at Honda's 891. **Operator's explicit instruction.**

★ WHY EDIT #4 IS INCLUDED, and why it does NOT limit the LKAS rate (the operator asked exactly this):
stock, while `gp-0x67fa == 4`, the governor FORBIDS the command's magnitude from increasing and writes
the suppressed value back -- it re-runs a rate-interpolation block seeded from the OLD value, i.e. it
IS a rate limiter on the LKAS command, and it is cumulative across cycles. `0x454FE` `BA -> B5` turns
the Bcond nibble BNE into BR so the substitution block `[0x45500,0x455C4)` is unreachable. It REMOVES
a limiter; it does not add one. It matters most on exactly this base: stock demands at most 417 LKAS
counts, V38 demands 1782, so the ratchet is ~4x deeper here than on stock.

★ WHY EDIT #6 IS A DISPLACEMENT EDIT AND NOT A CAVE. `FUN_00055d80` packs 427 (`0x1AB`) as
    r6 = gp-0x6c18 ; FUN_00049a5a ; FUN_00049a78 (abs) ; FUN_00049a90(x*5>>3, 0, 0x3ff) ; pack
and calls the checksum `FUN_00057b24(gp-0x13cc, 3, 0x1ab)` LAST. Changing ONLY the source load's
displacement makes Honda's own abs / x5/8 / 10-bit clamp / pack / checksum chain run on our signal,
untouched. **Zero control-path effect: we change what a TRANSMIT packer READS, and write nothing.**
Resolution 0.625 counts/LSB up to 1637, saturating near the +-2000 rail => full resolution exactly in
the ratchet regime (~120 counts p-p). openpilot decodes it natively as MOTOR_TORQUE, no DBC change.
⊕ The real MOTOR_TORQUE is sacrificed. That is deliberate and operator-approved: the record shows it
is not a delivered-torque or cut anchor for openpilot, and it is |value| so it has no sign anyway.

GATE 1 -- RAM OWNERSHIP: **N/A for edits #1-#6** (three calibration halfwords, three in-place code
displacement/condition edits; no RAM, no new state). For the cave: it is the V86B payload byte-for-byte,
which has flown clean; it writes ONE byte, `gp-0x1514`, the established telemetry byte, and reads only
`gp-0x6b70` / `gp-0x67ab`.
GATE 2 -- CLOSED-LOOP STABILITY: **no loop is modified.** #1+#2+#3 preserve the forward gain EXACTLY
(4.000x before and after) while REMOVING gain from four feedback readers -- strictly less loop gain,
never more. #4 removes a magnitude clamp. #6 touches a TX packer. #5 widens a speed window. No pole,
no zero, no filter coefficient anywhere in the image moves.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V87_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path("_v38_plain_image.bin"))
STOCK_BIN = str(Path(BASE_BIN).parent / "stock_fw_dump" / "code.bin")

# ---- the flown V86B cave, lifted VERBATIM ----------------------------------------------------------
CAVE_BASE = 0xC4B34
CAVE_PAYLOAD = bytes.fromhex(
    "003a243790946032a305423a6032ae05483aa63241326132a305443aa43755986232a905413ac43a483a"
    "8437edeac636070007314437ecea2436e8ea7f00")
HOOK_ADDR, HOOK_FROM, HOOK_TO = 0x55C0E, bytes.fromhex("2436e8ea"), bytes.fromhex("86ff26ef")

# ---- control edits: (addr, width, expect_before, value_after, label) --------------------------------
EDITS = [
    (0x2A1F0, 2, bytes.fromhex("6c74"), bytes.fromhex("d07c"),
     "V57 repoint: forward LKAS reader tp+0x746C -> tp+0x7CD0"),
    (0xC646C, 2, struct.pack("<H", 3564), struct.pack("<H", 891),
     "shared sensor scale 3564 -> 891 (Honda stock; un-confounds 4 feedback readers)"),
    (0xC6CD0, 2, struct.pack("<H", 65535), struct.pack("<H", 3564),
     "private forward LKAS gain -> 3564 = 4.000x"),
    (0x454FE, 1, bytes.fromhex("ba"), bytes.fromhex("b5"),
     "V42 ratchet fix: Bcond BNE -> BR, state-4 magnitude clamp unreachable"),
    (0xC62EA, 2, struct.pack("<H", 320), struct.pack("<H", 0),
     "steer to zero: low-speed lockout 5.00 km/h -> 0 km/h"),
    (0x55DF2, 2, bytes.fromhex("e893"), bytes.fromhex("6894"),
     "427 MOTOR_TORQUE source: gp-0x6c18 -> gp-0x6b98  <<< THE PROBE"),
]

VARIANT_TOKEN = "V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v87_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V87-{TAG}-0x{START:X}-0x{END:X}.rwd")

# cells that must NOT move -- levers the operator excluded, and known traps
FROZEN = {
    0x3AA96: (1, "Lever B gate -- EXCLUDED by the operator, must stay stock c5"),
    0xC6446: (2, "Lever B arm -- EXCLUDED, must stay stock 512"),
    0xC40BC: (2, "V85 friction relay -- NOT on a V38 base, must stay stock 600"),
    0xC40D4: (2, "command EMA -- V86's FALSIFIED lever, must stay stock 573"),
    0xC63B4: (2, "8 Hz bandpass alpha -- REFUTED this session, must stay 51"),
    0xC63B8: (2, "8 Hz bandpass gain -- REFUTED this session, must stay 41"),
    0xC646E: (2, "INERTIA gain -- sizing figure is UNMEASURED, must stay 1428"),
    0xD77DA: (2, "FactorC m26 Y[0] -- V86B's engaged creep damper, must stay 0"),
    0xD77EE: (2, "FactorC m27 Y[0] -- V86B's engaged creep damper, must stay 0"),
}


def rd(buf, addr, w):
    return bytes(buf[addr:addr + w])


def build():
    base = bytearray(Path(BASE_BIN).read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    assert len(base) == len(stock) == 0x100000
    assert walk_all_blocks(bytes(base)) == 0, "the V38 base's CRC chain does not verify"
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    print("=" * 102)
    print("  V87 -- measurement build on a clean V38 base")
    print(f"    base {os.path.basename(BASE_BIN)}\n    sha256 {base_sha}")
    print("=" * 102)

    code = bytearray(base)
    attributed = set()

    # ---- control edits -----------------------------------------------------------------------------
    print("\n  CONTROL EDITS")
    for addr, w, pre, post, lbl in EDITS:
        got = rd(code, addr, w)
        assert got == pre, (f"0x{addr:05X}: expected {pre.hex()} on the V38 base, found {got.hex()} "
                            "-- the base is not what this script was written against")
        code[addr:addr + w] = post
        attributed.update(range(addr, addr + w))
        print(f"    0x{addr:05X} {w}B  {pre.hex():>8} -> {post.hex():<8}  {lbl}")

    # ---- cave + hook -------------------------------------------------------------------------------
    print("\n  TELEMETRY CAVE (V86B payload, byte-for-byte)")
    assert all(b == 0xFF for b in code[CAVE_BASE:CAVE_BASE + len(CAVE_PAYLOAD) + 8]), \
        "the cave region is not blank on the V38 base"
    code[CAVE_BASE:CAVE_BASE + len(CAVE_PAYLOAD)] = CAVE_PAYLOAD
    attributed.update(range(CAVE_BASE, CAVE_BASE + len(CAVE_PAYLOAD)))
    assert rd(code, HOOK_ADDR, 4) == HOOK_FROM, "hook site is not stock on the V38 base"
    code[HOOK_ADDR:HOOK_ADDR + 4] = HOOK_TO
    attributed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    print(f"    0x{CAVE_BASE:05X} {len(CAVE_PAYLOAD)}B  cave payload")
    print(f"    0x{HOOK_ADDR:05X}  4B  {HOOK_FROM.hex()} -> {HOOK_TO.hex()}  jarl 0x{CAVE_BASE:05X},lp")
    assert CAVE_PAYLOAD[-6:] == HOOK_FROM + bytes.fromhex("7f00"), \
        "the cave must end with the relocated hooked instruction then `jmp lp`"
    print("    ✅ cave tail is the relocated `movea -0x1518,gp,r6` + `jmp lp` -- flown idiom intact")

    # ---- frozen cells ------------------------------------------------------------------------------
    print("\n  FROZEN CELLS (must equal the V38 base)")
    for addr, (w, why) in sorted(FROZEN.items()):
        assert rd(code, addr, w) == rd(base, addr, w), f"0x{addr:05X} MOVED -- {why}"
        v = struct.unpack("<H", rd(code, addr, 2))[0] if w == 2 else code[addr]
        print(f"    0x{addr:05X} = {v:<6} unchanged   {why}")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  CRC -- {len(blocks)} block(s) move")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}"
              f"   owns {len(owners)} byte(s)")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the block the bootloader SKIPS (V40's brick)"
    assert not [a for a in attributed if a < START or a >= END], "an edit landed outside the region"
    print("    ✅ full 50-block chain: 50/50 PASS · 0 bytes into [0xC5000,0xC5FFC)")

    # ---- zero-unattributed full diff ---------------------------------------------------------------
    by_addr = {}
    for addr, w, pre, post, lbl in EDITS:
        for k in range(w):
            by_addr[addr + k] = f"CONTROL 0x{addr:05X}  {lbl}"
    for k in range(4):
        by_addr[HOOK_ADDR + k] = f"HOOK 0x{HOOK_ADDR:05X} -> cave"

    def attribute(d):
        if d in by_addr:
            return by_addr[d]
        if d in crc_only:
            return "CRC trailer"
        if CAVE_BASE <= d < CAVE_BASE + len(CAVE_PAYLOAD):
            return f"the CAVE @0x{CAVE_BASE:05X} ({len(CAVE_PAYLOAD)} B)"
        return None

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
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V87 vs the V38 base -- over the WHOLE 1 MiB image")
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, f"🛑 UNATTRIBUTED bytes vs V38: {[hex(x) for x in stray[:16]]}"
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    assert hashlib.sha256(bytes(rt)).hexdigest() == base_sha, "the round trip does not reproduce V38"
    print("    ⇒ ZERO unattributed bytes; restoring the attributed set reproduces V38 BIT-FOR-BIT.")

    # ---- value-anchored verification (NOT span-based) ----------------------------------------------
    print("\n  VALUE ANCHORS (read back from the BUILT image)")
    anchors = [
        (0xC646C, 2, 891, "shared sensor scale = Honda stock"),
        (0xC6CD0, 2, 3564, "private forward LKAS gain = 4.000x"),
        (0xC62EA, 2, 0, "steer to zero"),
        (0xC646E, 2, 1428, "INERTIA gain untouched"),
        (0xC63B8, 2, 41, "8 Hz bandpass gain untouched"),
        (0xC40BC, 2, 600, "friction relay at Honda stock (V85's lever absent)"),
    ]
    for addr, w, want, why in anchors:
        got = struct.unpack("<H", rd(code, addr, w))[0]
        assert got == want, f"0x{addr:05X} = {got}, expected {want}"
        print(f"    0x{addr:05X} = {got:<6} {why}")
    assert code[0x454FE] == 0xB5, "V42 ratchet fix not present"
    assert rd(code, 0x55DF2, 2) == bytes.fromhex("6894"), "427 probe displacement not present"
    assert rd(code, 0x2A1F0, 2) == bytes.fromhex("d07c"), "V57 repoint not present"
    assert code[0x3AA96] == 0xC5, "Lever B gate must be stock"
    print("    0x454FE = b5     V42 ratchet fix present")
    print("    0x55DF2 = 6894   427 MOTOR_TORQUE <- gp-0x6b98")
    print("    0x2A1F0 = d07c   V57 repoint present")
    print("    0x3AA96 = c5     Lever B stock (excluded)")
    print("    ⊕ forward LKAS gain is 3564/891 = 4.000x EXACTLY, same as V38 -- authority UNCHANGED")

    # ---- .rwd --------------------------------------------------------------------------------------
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V87 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert dec[0x454FE] == 0xB5 and rd(dec, 0x55DF2, 2) == bytes.fromhex("6894")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("\n    ✅ READBACK: the decoded .rwd payload is byte-identical to the built image; "
          "anchors and the 50/50 chain re-verified from it.")

    # ---- write -------------------------------------------------------------------------------------
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V87_WRITE=rwd to cut.")
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
            FF.assert_x31_checksum(shipped, "V87 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code)
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded and re-verified INDEPENDENTLY.")

    print(f"\n  V87 [{VARIANT_TOKEN}]")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 HONEST LABEL: a MEASUREMENT build. It carries NO damping edit, NO filter and NO new")
    print("     authority, so judged as a ratchet fix it WILL read as a null -- by design. Feel")
    print("     changes come from the V38 REBASE (49 builds of levers removed), not from an 8 Hz lever.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    assert len(CAVE_PAYLOAD) == 62, "cave payload must be V86B's 62 bytes"
    assert len(EDITS) == 6 and sum(w for _, w, _, _, _ in EDITS) == 11
    assert len({a for a, *_ in EDITS}) == 6, "duplicate control address"
    assert 0xC63B8 in FROZEN and 0xC646E in FROZEN, "the refuted/unmeasured cells must be frozen"
    assert "+" not in VARIANT_TOKEN and all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN)
    assert len(OUT) < 250


if __name__ == "__main__":
    _self_check()
    build()
