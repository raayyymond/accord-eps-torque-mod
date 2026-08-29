#!/usr/bin/env python3
r"""
V183 -- V181's FIX + A PROBE ON THE DAMPER'S HARD OFF-SWITCH.  Base = V181.  3 bytes.
        CAN 427 source gp-0x6abc -> gp-0x6ac0, and the packer shift sar 3 -> sar 4.

WHY A PROBE, AND WHY IT RIDES ON THE FIX RATHER THAN REPLACING IT
------------------------------------------------------------------
FUN_00034350 shows the base-assist damper is a five-factor product that is ** ZEROED OUTRIGHT ** when

    gp-0x6ac0 >= 0x32c9   (12993)     or   |gp-0x6abe| > 0x6590

`gp-0x6ac0` is the resolver / FOC electrical rate.  ** If that gate is never satisfied during engaged
creep ratcheting, then NO damper lever can ever work ** -- which would close the entire damper family
in one drive.  Neither `gp-0x6ac0` nor `gp-0x6a5e` is in the cached corpus, so this cannot be answered
from existing data; it needs telemetry.

This build carries V181's full fix unchanged, so the drive still tests the strongest available attack
on the ratchet.  The probe is free-riding: a null on the fix still buys the damper answer.

THE EDIT -- THE MOST PRECEDENTED CHANGE IN THE KIT
--------------------------------------------------
    0x55DF2   ld.h disp   0x9544 -> 0x9540      CAN 427 source gp-0x6abc -> gp-0x6ac0
    0x55E10   sar 0x3     a3     -> a4          packer shift >>3 -> >>4
** No cave change. **  V90/V92/V94/V108/V122 have all moved these two cells on-car.

WHY THE SHIFT MUST MOVE TOO -- SIZING THE PROBE AGAINST WHAT IT MUST SEE
------------------------------------------------------------------------
The packer is, from the disassembly:
    0x55E0A  movea 0x3ff, r0, r8      ; 1023 -> a 10-BIT field
    0x55E10  sar   0x3, r6            ; value >> 3
    => at >>3 the largest representable SOURCE value is 1023 * 8 = 8184.
** The gate I need to observe sits at 12993, ABOVE that. **  At >>3 the channel would saturate
before reaching the threshold and the probe would be worthless -- the V96 under-ranging failure.
    at >>4:  max source = 1023 * 16 = 16368  (comfortably above 12993)
             resolution  = 16 counts per LSB; the gate lands at field value 812.
=> the probe can resolve "above or below the gate" with ~2 % precision.  [GATE 3 satisfied.]

WHAT A NULL LICENSES -- written BEFORE the drive
-------------------------------------------------
  * field value stays >= 812 throughout engaged creep  -> the damper is HARD OFF whenever the ratchet
    is happening.  ** The entire damper family is closed, including V182's direction. **
  * field value is < 812 for a meaningful fraction      -> the damper CAN act; the gate is not the
    blocker, and FactorC/FactorE knots become worth sizing (after gp-0x6a5e is also characterised).
  * field pinned at 1023                                -> still saturating; the shift needs to go
    further and the drive says so unambiguously rather than silently.

COST
----
The 427 channel currently carries `gp-0x6abc`; that signal is lost for this drive.  Nothing in the
pending analysis depends on it.  The shift change also rescales 427 by 2x, so any historical
comparison of this channel must account for it -- which is why the tag records the shift.

RISK
----
Three bytes, two cells, both with repeated on-car precedent, no cave and no calibration change.  All
of V181's edits are asserted CARRIED, and the retracted V178/V182 cells are asserted UNTOUCHED.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

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
WRITE_MODE = os.environ.get("ACCORD_V183_WRITE", "").strip().lower()
BASE_NAME = "_v181_V181-V180BASE-W3.INERTIA.WEIGHT.1024.TO.512_plain_image.bin"
BASE_SHA = "49ca42da43e95f31fc90c4e7709b042d6ec02e3ca287b77146bd8af6c52d35c4"

SRC_CAL, SRC_OLD, SRC_NEW = 0x55DF2, 0x9544, 0x9540      # gp-0x6abc -> gp-0x6ac0
SAR_CAL, SAR_OLD, SAR_NEW = 0x55E10, 0xA3, 0xA4          # sar 3 -> sar 4
GATE = 0x32C9
FIELD_MAX = 0x3FF

CARRIED_U16 = {0xC407E: ("hard-fault interlock", 511),
               0xC40D2: ("K1 -> Honda (V177)", 102),
               0xC63A6: ("w[3] halved (V181)", 512),
               0xC60A8: ("V180 pole word lo", 0x3D71)}
CARRIED_B = {0xC40DC: ("accel alpha -> Honda (V179)", 22)}
UNTOUCHED_S16 = {0xD77DA: ("V182 cell -- must stay V158's", 429),
                 0xD77EE: ("V182 cell -- must stay V158's", 426)}

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def build():
    print("=" * 102)
    print("  V183 -- V181's FIX + a probe on the damper's hard OFF-switch   (base V181)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V181 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE TWO CELLS ARE WHERE THE DISASSEMBLY SAYS")
    got_src = struct.unpack_from("<H", base, SRC_CAL)[0]
    check(got_src == SRC_OLD,
          f"0x{SRC_CAL:05X} = {got_src:04X} = the 427 ld.h disp for gp-0x{0x10000-SRC_OLD:04X}")
    check(base[SAR_CAL] == SAR_OLD, f"0x{SAR_CAL:05X} = {base[SAR_CAL]:02X} = sar 0x3")
    check((SRC_NEW & 1) == 0, "the new displacement is EVEN, as ld.h requires")

    print("\n  [3] SIZING -- the probe must resolve a gate at %d" % GATE)
    for nm, sh in (("current >>3", 3), ("V183    >>4", 4)):
        mx = FIELD_MAX << sh
        print(f"      {nm}: max source = {FIELD_MAX} << {sh} = {mx:6d}   "
              f"resolution {1 << sh:2d}/LSB   gate at field {GATE >> sh:4d}   "
              f"{'SATURATES BELOW THE GATE' if mx < GATE else 'covers the gate'}")
    check((FIELD_MAX << 3) < GATE, "at >>3 the channel saturates below the gate -- shift MUST move")
    check((FIELD_MAX << 4) > GATE, "at >>4 the channel covers the gate [GATE 3 satisfied]")

    print("\n  [4] THE EDIT -- 3 bytes, no cave, no calibration")
    struct.pack_into("<H", code, SRC_CAL, SRC_NEW)
    code[SAR_CAL] = SAR_NEW
    attributed = set(range(SRC_CAL, SRC_CAL + 2)) | {SAR_CAL}
    print(f"      0x{SRC_CAL:05X}  {SRC_OLD:04X} -> {SRC_NEW:04X}   427 source "
          f"gp-0x{0x10000-SRC_OLD:04X} -> gp-0x{0x10000-SRC_NEW:04X}")
    print(f"      0x{SAR_CAL:05X}  {SAR_OLD:02X}   -> {SAR_NEW:02X}     packer sar 0x3 -> sar 0x4")
    check(struct.unpack_from("<H", code, SRC_CAL)[0] == SRC_NEW, "427 source repointed")
    check(code[SAR_CAL] == SAR_NEW, "packer shift updated")

    print("\n  [5] V181's FIX IS CARRIED, AND THE RETRACTED CELLS ARE UNTOUCHED")
    for off, (nm, want) in sorted(CARRIED_U16.items()):
        got = struct.unpack_from("<H", code, off)[0]
        check(got == want, f"0x{off:05X} {nm} CARRIED ({got})")
    for off, (nm, want) in sorted(CARRIED_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} CARRIED ({code[off]})")
    for off, (nm, want) in sorted(UNTOUCHED_S16.items()):
        got = struct.unpack_from("<h", code, off)[0]
        check(got == want, f"0x{off:05X} {nm} = {got} (V182's error not repeated)")

    print("\n  [6] CRC RECOMPUTATION")
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
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base")

    print("\n  [7] FULL BYTE DIFF vs V181")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) <= 3, f"{len(pay)} payload bytes (<= 3)")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change, the kit's only bricking class")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V183 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V183-V181BASE-PROBE.427.GP6AC0.SAR4"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v183_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V183_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print(f"  ** 427 now carries gp-0x6ac0 >> 4. The damper's OFF gate ({GATE}) lands at field "
          f"{GATE >> 4}. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
