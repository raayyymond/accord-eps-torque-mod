#!/usr/bin/env python3
r"""
V177 -- REVERT THE 10x MODELLED COULOMB FRICTION TO HONDA'S VALUE.  Base = V175.  ONE CELL, 2 bytes.
        The new fly-first candidate.  A RELAY that fires at every velocity reversal, at 10x stock.

WHY THIS EXISTS, AND WHY IT WAS MISSED FOR SO LONG
---------------------------------------------------
`0xC40D2` is K1, the gain on the modelled Coulomb friction in the plant model (`FUN_0003b8f6`):

    friction = |model| * sign(polarity * gp-0x6abc) * K1 / 1024        gp-0x6abc = motor rate

** It is a SIGN FUNCTION of motor velocity. **  So at every velocity reversal the term steps by

    step = 2 * |model| * K1 / 1024

    Honda  K1 =  102  ->  step = 0.199 * |model|
    V89    K1 =  204  ->  step = 0.398 * |model|      (flew; measured "delivered, but small")
    V122+  K1 = 1020  ->  step = 1.992 * |model|      <-- ON EVERY BUILD SINCE V122

    build history, read from the images:
      stock/V81/V87/V88   102     V89..V108   204     V122/V158/V173/V174/V175/V176   1020

V89 deliberately raised it to 204 and its own docstring PRE-REGISTERED the risk, which the polarity
memory then recorded verbatim:
    "Coulomb friction flips sign at every reversal, so larger K1 = a larger STEP at each reversal
     - notchiness on turn-in, not steady drag.  Transient, unmeasured."
** V122 then took it to 1020 -- five times the value that warning was written about -- and the
warning has still never been tested. **  At an 8 Hz oscillation the motor velocity reverses 16 times
a second, so a step of ~2x|model| is injected 16 times a second, synchronised to the mode.

THIS IS THE V80 FAILURE MODE IN A DIFFERENT LANE
-------------------------------------------------
V80 turned the base-assist damper into a relay and produced "the worst grinding ever"
([[accord-v80-damper-relay-and-grind1-inert]]).  A sign-flipping term at 10x gain inside the assist
path IS a relay, and a relay in a lightly damped loop is a textbook limit-cycle / ratchet source.
Unlike a linear gain, its describing function does not shrink with amplitude, which is exactly why it
can sustain a mode that linear analysis says should be damped.

THE DIRECTION IS RIGHT, AND THE SIGN IS ALREADY VERIFIED
---------------------------------------------------------
[[accord-friction-polarity-more-friction-is-more-assist]] establishes the nine-link chain: MORE
modelled friction -> LOWER target felt effort -> MORE assist -> LIGHTER.  So reverting K1:
  * REMOVES the large reversal step (the ratchet/stutter candidate);
  * costs a little of the steady lightness V89 was chasing.
** That is the trade, stated plainly: slightly heavier steady effort, in exchange for removing a
1.99x|model| step that fires at every single velocity reversal. **  Given the operator has named
eliminating the ratcheting and stuttering as the priority five times, that is the right side to err on
-- but it IS a feel change and he should be told before he drives it.

WHAT THIS BUILD IS, EXACTLY
----------------------------
V175 (assist-section poles 0.970/0.475 + the engaged apparent-inertia revert) with ONE more cell:
`0xC40D2` 1020 -> 102, Honda's own value, read from the stock image rather than typed.
** ONE cell, 2 bytes, so the drive can still attribute it. **

RISK
----
The lowest class this kit has: a single calibration cell returned to the value Honda ships, in a lane
whose polarity is verified nine ways and whose stock value has run on every car of this type.  It
cannot fault -- `0xC407E`, the hard-fault interlock, is untouched at 511 and this cell does not feed
it.  No cave, no code edit, no RAM claim.
NOT included, deliberately: `0xC40DC` (the acceleration EMA alpha, which V122 also moved 22 -> 8).
That changes the PHASE of the inertia term rather than its size, its direction is not established,
and folding it in here would cost the single-cell attribution.  It is logged as an open item.
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
WRITE_MODE = os.environ.get("ACCORD_V177_WRITE", "").strip().lower()

BASE_NAME = "_v175_V175-V173BASE-GP6B26.ENGAGED.Y.REVERT.HONDA_plain_image.bin"
BASE_SHA = "a4e0dc4254ad8559e0c7744277cbe609d3c4c7da90284bc145d035a0816ae357"

K1_CAL = 0xC40D2
K1_FLOWN = 1020                     # what V122 onward carries
ALPHA_A = 0xC40DC                   # V122 moved this 22 -> 8; NOT touched here, logged instead
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
W3_CAL, W3_VAL = 0xC63A6, 1024
HONDA_Y = (-9830, -5734, -1966)
ENGAGED_ROWS = {0xD7A5C: "mode 26 (ENGAGED)", 0xD7A6C: "mode 27 (ENGAGED)"}
BIQUAD = {0xC60A8: 0xBFB8F5C3, 0xC60AC: 0x3EEBE76D,
          0xC60B0: 0xBFF0BE0E, 0xC60B4: 0x3E074D3C}   # V173's section, asserted CARRIED

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
    print("  V177 -- MODELLED COULOMB FRICTION K1 REVERTED TO HONDA   (base V175)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V175 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] HONDA'S VALUE IS READ FROM THE STOCK IMAGE, NEVER TYPED")
    stock_p = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                                  "C:/Users/dudei/Desktop/Projects/accord-firmwares"),
                   "analysis-2020accord", "stock_fw_dump", "code.bin")
    stock = stock_p.read_bytes()
    k1_honda = u16(stock, K1_CAL)
    check(k1_honda == 102, f"stock 0x{K1_CAL:05X} = {k1_honda} -- VERIFIED from the image, not typed")
    check(u16(base, K1_CAL) == K1_FLOWN,
          f"base carries K1 = {K1_FLOWN} ({K1_FLOWN/k1_honda:.0f}x Honda) -- the thing being undone")

    print("\n  [3] THE RELAY STEP THIS REMOVES")
    for nm, k in (("Honda      ", k1_honda), ("V89        ", 204), ("FLOWN V122+", K1_FLOWN)):
        print(f"      K1 = {k:4d}  ->  reversal step = {2.0*k/1024:.3f} x |model|   {nm}")
    print(f"      at an 8 Hz oscillation the motor rate reverses ~16 times a second")

    print("\n  [4] THE EDIT -- ONE cell, 2 bytes")
    struct.pack_into("<H", code, K1_CAL, k1_honda)
    attributed = set(range(K1_CAL, K1_CAL + 2))
    print(f"      0x{K1_CAL:05X}  {K1_FLOWN} -> {u16(code, K1_CAL)}   K1 modelled Coulomb friction")

    print("\n  [5] EVERYTHING ELSE IS CARRIED, AND ASSERTED")
    check(u16(code, K1_CAL) == k1_honda, f"0x{K1_CAL:05X} is now Honda's {k1_honda}")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(u16(code, W3_CAL) == W3_VAL, f"0x{W3_CAL:05X} w[3] FROZEN at {W3_VAL}")
    check(base[ALPHA_A] == code[ALPHA_A],
          f"0x{ALPHA_A:05X} accel EMA alpha UNTOUCHED at {code[ALPHA_A]} "
          f"(V122 moved it 22->8; direction unestablished, logged as an open item)")
    for off, what in ENGAGED_ROWS.items():
        check(row(code, off) == HONDA_Y, f"0x{off:05X} {what} inertia revert CARRIED")
    for off, word in BIQUAD.items():
        check(struct.unpack_from("<I", code, off)[0] == word,
              f"0x{off:05X} V173's section coefficient CARRIED")

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
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [7] FULL BYTE DIFF vs V175 -- ZERO UNATTRIBUTED")
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
    check(payload == 2, f"{payload} payload bytes (exactly 2: ONE u16 cell)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V177 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V177-V175BASE-K1.COULOMB.REVERT.HONDA.102"
    img_out = plain_image_path(f"_v177_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V177_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** Removes a 1.99x|model| step that fires at EVERY motor-velocity reversal. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
