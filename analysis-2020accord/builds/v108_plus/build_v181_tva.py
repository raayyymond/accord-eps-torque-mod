#!/usr/bin/env python3
r"""
V181 -- SPEND THE LAST LEVER: halve w[3], the weight on the omega^2 inertia lane.
        Base = V180.  ONE cell, 2 bytes.  0xC63A6  1024 -> 512.

WHY THIS IS THE MOST TARGETED LEVER IN THE KIT
-----------------------------------------------
FUN_00038148 sums six lanes.  w[3] = tp+0x73a6 = 0xC63A6 weights the gp-0x6b26 lane, and that lane
alone is K * ACCELERATION:
  * FUN_00036c12 is its SOLE writer (one st.h at 0x36CF0; re-verified with a scanner carrying no
    opcode whitelist and no disp-parity assumption, after two holes were found in the first one);
  * gp-0x6c2c is a FIRST DIFFERENCE of the EMA-filtered resolver rate (FUN_00041464 @0x41602);
  * the acceleration enters LINEARLY -- the 0xCBE74 LERP is indexed by gp-0x6a5e, a SCHEDULING
    variable, not by alpha.
=> its loop contribution scales as omega^2: ** at 8.17 Hz it is 66.7x its value at 1 Hz. **
Halving w[3] therefore removes loop gain 66.7x harder at the ratchet than in the LKAS band, and does
it with ** NO filter and NO added phase lag anywhere **.  That is precisely the operator's standing
constraint: no ratcheting AND no added apparent mass to LKAS.

WHY IT IS SAFE, AND WHY THE DIRECTION IS RIGHT
-----------------------------------------------
GATE 1  gp-0x6b26 has exactly ONE writer.  The gate in FUN_00038148 (|x| <= 1024) CANNOT close,
        because the writer clamps to +-511 via 0xC407E.  So w[3] is an unconditional multiplier.
GATE 2  The term is POSITIVE ACCELERATION FEEDBACK -- destabilising -- by the verified nine-link
        polarity chain (more modelled friction -> more assist; f' >= 0 everywhere).
        ** Reducing a destabilising positive-feedback term can only increase stability margin. **
        There is no magnitude or phase condition to satisfy: less of it is monotonically safer.
PRECEDENT  Its sibling 0xC63A0 (w[0]) was moved 1024 -> 2048 by V72 and back by V77, on-car and
        fault-free.  The weight family is proven movable.

THE HONEST STATEMENT OF THE RISK
---------------------------------
** This is the only edit in the current set that goes BELOW Honda's own configuration. **  V175 and
V179 restored this lane's GAIN and FILTER to Honda's; halving w[3] then takes the product to half of
Honda's.  Honda includes apparent-inertia compensation deliberately -- it makes the wheel lighter and
more responsive.  Removing half of it will make the wheel feel slightly HEAVIER -- but because the
term is omega^2-weighted, ** that weight appears at HIGH frequency, not at the ~1 Hz where LKAS and
the driver operate. **
[EVIDENCE] the omega^2 weighting, the sole writer, the always-open gate, the sibling precedent.
[BELIEF, structural] that halving is the right direction and the right size.

DOSE
----
1024 -> 512 is a single clean halving (Q10 x1.000 -> x0.500).  Deliberately NOT zero: zero deletes a
Honda function outright and leaves nowhere to go.  A half-dose keeps headroom if the drive says it
helped but did not cure.

WHAT THIS BUILD CARRIES  (all asserted, not assumed)
-----------------------------------------------------
V180 = poles 0.980/0.475 + K1 -> Honda 102 + engaged inertia Y -> Honda + accel alpha -> Honda 22.
Honda's 55.23 Hz notch (C_B0), the V31/V38 authority ladder, the V37 EME debounce disable and the
0xC407E hard-fault interlock are all untouched and asserted.
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
WRITE_MODE = os.environ.get("ACCORD_V181_WRITE", "").strip().lower()
BASE_NAME = "_v180_V180-V179BASE-POLE.0.980-ALL.THREE.HONDA.REVERTS_plain_image.bin"
BASE_SHA = "31505dc64def54da4100c48dc95b3ce5084af79cfe41304ea2ae4943e29856ef"

W3_CAL, W3_FLOWN, W3_NEW = 0xC63A6, 1024, 512
FROZEN_U16 = {0xC407E: ("hard-fault interlock", 511),
              0xC40D2: ("K1 Coulomb -> Honda (V177)", 102),
              0xC40BC: ("Coulomb ramp width", 3000),
              0xC61C0: ("V37 EME debounce disable", 0xFFFF),
              0xC63A0: ("w[0] damper weight", 1024),
              0xC63A2: ("w[1] viscous weight", 1024)}
FROZEN_B = {0xC40DC: ("accel EMA alpha -> Honda (V179)", 22)}
HONDA_Y = (-9830, -5734, -1966)
ENGAGED_ROWS = {0xD7A5C: "mode 26 (ENGAGED)", 0xD7A6C: "mode 27 (ENGAGED)"}
BIQUAD = {0xC60A8: 0xBFBA3D71, 0xC60AC: 0x3EEE5604,
          0xC60B0: 0xBFF0BE0E, 0xC60B4: 0x3DB466E4}      # V180's poles 0.980/0.475, notch kept
AUTHORITY = {0xC6598: 5.0, 0xC65C4: 5.0}                 # V31/V38 ladder -- V178's error, guarded

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(buf, off):
    return struct.unpack_from("<H", buf, off)[0]


def row(buf, off):
    return tuple(struct.unpack_from("<h", buf, off + 2 * i)[0] for i in range(3))


def build():
    print("=" * 102)
    print("  V181 -- w[3] HALVED: the omega^2 inertia-lane weight   (base V180)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V180 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE CELL, AND WHY IT IS UNCONDITIONAL")
    check(u16(base, W3_CAL) == W3_FLOWN,
          f"0x{W3_CAL:05X} w[3] = {W3_FLOWN} (Q10 x1.000) -- VIRGIN on every build to date")
    check(u16(base, 0xC407E) == 511,
          "0xC407E clamps gp-0x6b26 to +-511, inside the sum's +-1024 gate "
          "=> the gate can NEVER close, so w[3] multiplies EVERY frame")

    print("\n  [3] WHAT HALVING IT BUYS, BY FREQUENCY")
    print("      the lane is K * ACCELERATION, so its loop contribution scales as f^2:")
    for f in (0.5, 1.0, 3.0, 8.17, 21.0):
        print(f"        {f:5.2f} Hz   relative weight {(f/1.0)**2:8.2f}x   "
              f"halving removes {0.5*(f/1.0)**2:8.2f}x (vs 1 Hz)")
    print("      => 66.7x more effect at the ratchet than in the LKAS band, with ZERO added lag.")

    print("\n  [4] THE EDIT -- ONE cell, 2 bytes")
    struct.pack_into("<H", code, W3_CAL, W3_NEW)
    attributed = set(range(W3_CAL, W3_CAL + 2))
    print(f"      0x{W3_CAL:05X}  {W3_FLOWN} -> {u16(code, W3_CAL)}   "
          f"w[3], the gp-0x6b26 (inertia) lane weight   Q10 x1.000 -> x0.500")
    check(u16(code, W3_CAL) == W3_NEW, f"0x{W3_CAL:05X} is now {W3_NEW}")

    print("\n  [5] EVERYTHING V180 CARRIES, ASSERTED")
    for off, (nm, want) in sorted(FROZEN_U16.items()):
        check(u16(code, off) == want, f"0x{off:05X} {nm} FROZEN at {want}")
    for off, (nm, want) in sorted(FROZEN_B.items()):
        check(code[off] == want, f"0x{off:05X} {nm} FROZEN at {want}")
    for off, what in ENGAGED_ROWS.items():
        check(row(code, off) == HONDA_Y, f"0x{off:05X} {what} inertia revert CARRIED")
    for off, word in sorted(BIQUAD.items()):
        check(struct.unpack_from("<I", code, off)[0] == word,
              f"0x{off:05X} V180 section coefficient CARRIED ({word:08X})")
    for off, want in sorted(AUTHORITY.items()):
        got = struct.unpack_from("<f", code, off)[0]
        check(abs(got - want) < 1e-6,
              f"0x{off:05X} V31/V38 AUTHORITY LADDER INTACT at {got} (V178's error, guarded)")

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

    print("\n  [7] FULL BYTE DIFF vs V180")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    unattributed = [a for a in diff if a not in attributed]
    check(not unattributed, f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    # 1024 = 0x0400 and 512 = 0x0200 share a zero LOW byte, so the u16 write changes
    # only ONE byte.  Assert the range, and assert the VALUE separately (step [4]).
    check(1 <= len(pay) <= 2,
          f"{len(pay)} payload byte(s) -- one u16 cell; 0x0400->0x0200 touches only the high byte")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V181 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V181-V180BASE-W3.INERTIA.WEIGHT.1024.TO.512"
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v181_{tag}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V181_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** omega^2-weighted: 66.7x more effect at 8.17 Hz than at 1 Hz, with ZERO added lag. **")
    print("  ** The only edit that goes BELOW Honda. Expect slightly heavier HIGH-frequency feel. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
