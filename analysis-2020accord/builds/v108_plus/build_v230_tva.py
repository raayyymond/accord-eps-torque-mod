# -*- coding: utf-8 -*-
r"""🛑 QUALIFIED AFTER BUILDING -- DRIVE V229 FIRST, NOT THIS.

After cutting this build I checked the record on the lane 0xC40DC shapes, and it is already
characterised. The chain has exactly ONE output --
  gp-0x4f50 -> FUN_00041464 -> gp-0x6c2c -> FUN_00036c12 [the 0xCBE74 LERP] -> gp-0x6b26 (+-511)
-- so a null there is a null on the lever. And:

  * a x1.5 DOSE ON THAT CELL MEASURED INERT at gp-0x6b26 itself: p50 0.988, every CI containing
    1.00, against a pre-registered 1.50 (r78/V91, r79/V92). Class T10, "the instrument is
    invariant to the lever": y = K*alpha where alpha is what K damps, so in a stable closed loop
    the product is invariant to K.
  * V94 CUT THE SAME CELL 6x AND THE OPERATOR ABORTED THE DRIVE -- which is what proves the cell
    reaches the car. Inert at small dose, bad at large dose, in the CUT direction.

CORRECTED 2026-08-30, later the same day. I first read the x1.5 null as "the lever is probably
inert". That is a MISREADING, and the record says so outright: "this was never a dead lever; it was an
UNMEASURABLE one. Do not file it FALSIFIED." y = K*alpha is invariant to K, but ALPHA -- the motion --
is not, and the dose was measured at y, the one quantity guaranteed not to move.

Measured against THE CAR (not against V229), V230 is 0.993 at 1 Hz, 0.746 at 7.79 Hz (-25 %) and
0.506 at 18.5 Hz (-49 %) in that lane.

=> THE LEVER DOES REACH THE CAR -- V94's 6x cut aborting a drive is the proof. It is merely
unmeasurable at its own output. Its direction matches that 6x cut and its magnitude is smaller. The
caution is therefore BETTER founded than when I wrote it, not weaker: this is not "probably a no-op",
it is "reaches the car, in the direction that once went badly".

The lane is also primarily a RATCHET lane -- measured on the three routes whose CAN 427 taps it,
it is 52.8 % 6-9 Hz (coherence 0.728 with wheel rate), 17.4 % 9-12, 10.9 % 15-22. Perturbing it in
the aborted-drive direction is not a small matter.

THIS BUILD IS KEPT ON THE SHELF, NOT RECOMMENDED. V229 is the lead: its lever is the notch, which
acts on gp-0x6b82 in FUN_000352b4 -- a different lane, never shown invariant, and a phase-shaping
device rather than a gain, so y = K*alpha does not directly apply.

The original rationale follows unchanged, as the record of why it was cut.

--------------------------------------------------------------------------------------------------

V230 -- V229 PLUS alpha2 = 3. THE FIRST BUILD TO CUT *BOTH* 15-22 Hz AND 55 Hz.

THE PROBLEM V229 COULD NOT SOLVE. There is exactly ONE biquad in this ECU. Honda uses it as a 55 Hz
notch (159x). Every build since V172 RELOCATED it to ~20 Hz to cut the grinding band, which VACATES the
55 Hz cut. One 2nd-order section cannot notch 18 Hz and 55 Hz -- the trade is structural, and V228 and
V229 sit on opposite sides of it:

    V228   4.9x at 18.5 Hz,   but 100x LOUDER than the car at 55 Hz
    V229   Honda's 159x at 55 Hz,   but no cut at all at 18.5 Hz

BUT THE BIQUAD IS NOT THE ONLY HF LEVER. `0xC40DC` (alpha2) is the EMA2 coefficient of a cascaded
bandpass in a DIFFERENT lane -- the one feeding `gp-0x6b26`:

    step = a1*(x - y1)          a1 = 37/128  (0xC643C >> 7)    high-pass
    acc  = 32*step
    sf  += a2*(acc - sf)        a2 = cal/64  (0xC40DC >> 6)    low-pass, DC gain 1 for ANY a2
    out  = sf >> 9

Because the low-pass has **DC gain 1 for every a2**, lowering the cal moves the corner without touching
the low-frequency response at all. It cuts monotonically at BOTH bands of interest:

    cal    1 Hz    3 Hz  |  18.5 Hz          55 Hz          corner
     22   1.000   1.000  |  1.000           1.000           67.0 Hz   Honda / V228 / V229
      8   0.999   0.991  |  0.782 (1.28x)   0.466 (2.14x)   21.3 Hz   the CAR
      5   0.997   0.975  |  0.595 (1.68x)   0.296 (3.37x)   12.9 Hz
   -> 3   0.992   0.932  |  0.396 (2.53x)   0.178 (5.62x)    7.6 Hz   THIS BUILD
      2   0.981   0.861  |  0.273 (3.66x)   0.118 (8.45x)    5.1 Hz

**So V230 keeps Honda's 159x notch at 55 Hz AND adds a 2.53x cut at 18.5 Hz, in a lane the notch never
touched.** That is both cuts at once, which no single biquad geometry can deliver.

WHY 3 AND NOT 2. The operator's standing directive is that no fix may add felt mass or friction to
deliberate steering. Hand-steering bandwidth is ~1-3 Hz. At cal 3 the lane is **0.992 at 1 Hz and 0.932
at 3 Hz** -- essentially untouched where he steers. Cal 2 buys 1.4x more at 18.5 Hz but costs 14 % at
3 Hz, four times the low-frequency cost for a modest gain. Cal 3 is where the curve turns.

GATE 1 IS THE CLEANEST IN THE KIT. `docs/BUILD-LINEAGE.md` on this cell: *"exactly ONE gp/tp access
image-wide, zero writers."* One reader at `0x41626`. This is a byte cal with no aliasing and no shared
consumer.

IT IS NOT NEW TERRITORY. The cal has been 22, 16, 14, 8, 5 and 2 across the build history (V124 8->5,
V138 5->2, V139 2->8, V179 8->22). **3 is inside the range already built.** None of V124-V179 was ever
flown -- the corpus stops at V122 -- so this lever is UNTESTED ON-CAR, not falsified.

AND IT SATISFIES THE LINEAGE CONSTRAINT TWICE OVER. On this exact cell: *"it must ship WITH the notch
revert or not at all -- across 54-74.5 Hz V105's coefficients leave the base-assist lane a
geometric-mean 5.15x (+14.2 dB) louder than Honda's."* V228 ships alpha2 = 22 (which passes MORE HF)
with a notch that no longer cuts 54-74 Hz -- both cells pushing the same way, exactly what the record
forbids. V230 has the notch revert AND moves alpha2 the quiet way.

🛑 WHAT IS **NOT** CLAIMED.
  * The 2.53x is a cut **in the gp-0x6b26 lane**, not in the delivered torque. The notch cuts a
    different signal (`gp-0x6b82`, inside `FUN_000352b4`). **These are PARALLEL lanes; their ratios do
    not multiply into a total**, and no total is asserted anywhere here.
  * `gp-0x6b26` is recorded as an INERTIA term. Whether cutting it at 3 Hz slightly RAISES or LOWERS
    apparent mass is **not established** -- only that the effect there is 6.8 %.
  * V230 confounds two changes against V228 (notch revert + alpha2). **V229 exists as the clean
    single-variable control** and should be driven if the cause matters.

RISK. V230's 18.5 Hz cut (2.53x, one lane) is smaller than V228's (4.9x, another lane). If the grinding
lives squarely at 15-22 Hz and in the notch's lane specifically, **V228 may still beat it there** --
while remaining 100x louder at 55 Hz. That is the honest residual.

EVERYTHING ELSE IS V229, BYTE FOR BYTE -- and V229 is V228 but for the biquad.
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
WRITE_MODE = os.environ.get("ACCORD_V230_WRITE", "").strip().lower()

BASE_NAME = "_v229_V229-V228BASE-HONDA.55HZ.NOTCH.RESTORED_plain_image.bin"
BASE_SHA = "078da4b1f22903a5364b54b0035790f0fac6453a4717e881290eefb15bc14a42"

ALPHA2 = 0xC40DC
ALPHA2_OLD, ALPHA2_NEW = 22, 3
ALPHA1 = 0xC643C                    # the shared EMA1 coeff, 37 -- ASSERTED, never touched

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
LEVER_B, LEVER_B_VAL = 0xC6446, 13107
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
TAG = "V230-V229BASE-ALPHA2.3-BOTH.CUTS"

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def lane(cal, f, fs=1000.0):
    """|H| of the gp-0x6b26 EMA bandpass at f, for a given 0xC40DC value."""
    import cmath
    import math
    a1 = 37 / 128.0
    a2 = cal / 64.0
    z = cmath.exp(2j * math.pi * f / fs)
    zi = 1 / z
    return abs((32 / 512.0) * a1 * (1 - zi) / (1 - (1 - a1) * zi) * a2 / (1 - (1 - a2) * zi))


def build():
    print("=" * 102)
    print("  V230 -- V229 + alpha2 = 3.  BOTH CUTS: Honda's 55 Hz notch AND 15-22 Hz.")
    print("=" * 102)

    print("\n  [1] BASE = V229")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V229 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(bytes(base[BIQ:BIQ + BIQ_LEN]) == HONDA_BIQ, "base carries Honda's 55 Hz biquad")
    check(base[ALPHA2] == ALPHA2_OLD, f"base 0x{ALPHA2:05X} = {ALPHA2_OLD} (Honda)")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- one byte")
    code[ALPHA2] = ALPHA2_NEW
    attributed.add(ALPHA2)
    check(code[ALPHA2] == ALPHA2_NEW, f"0x{ALPHA2:05X} alpha2 {ALPHA2_OLD} -> {ALPHA2_NEW}")
    check(u16(code, ALPHA1) == 37, f"0x{ALPHA1:05X} alpha1 = 37, UNTOUCHED (shared EMA1 coeff)")

    print("\n  [3] THE LANE RESPONSE, from the value in the built image")
    print("      %-9s %10s %10s %9s" % ("freq", "V229", "V230", "ratio"))
    for f in (1.0, 3.0, 6.0, 7.79, 10.5, 15.0, 18.5, 22.0, 31.0, 55.0, 65.0):
        a, b = lane(base[ALPHA2], f), lane(code[ALPHA2], f)
        print("      %6.2f Hz %10.6f %10.6f %8.3f" % (f, a, b, b / a))
    r1 = lane(code[ALPHA2], 1.0) / lane(base[ALPHA2], 1.0)
    r3 = lane(code[ALPHA2], 3.0) / lane(base[ALPHA2], 3.0)
    r18 = lane(code[ALPHA2], 18.5) / lane(base[ALPHA2], 18.5)
    r55 = lane(code[ALPHA2], 55.0) / lane(base[ALPHA2], 55.0)
    check(r1 > 0.98, f"1 Hz essentially untouched ({r1:.3f}) -- no added mass where he steers")
    check(r3 > 0.90, f"3 Hz cost is {100*(1-r3):.1f} %, inside the hand-steering band")
    check(r18 < 0.45, f"18.5 Hz cut {1/r18:.2f}x IN THIS LANE (the grinding band)")
    check(r55 < 0.25, f"55 Hz cut {1/r55:.2f}x IN THIS LANE, ON TOP of Honda's 159x notch")

    print("\n  [4] EVERY OTHER LEVER IS UNTOUCHED")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == HONDA_BIQ, "Honda's 55 Hz biquad still in place")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B 0x{LEVER_B:05X} = {LEVER_B_VAL} (V88's win)")
    check(u16(code, RESID_SCALE) == RESID_VAL, f"0x{RESID_SCALE:05X} = {RESID_VAL}")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change, not the bricking class")
    for a, want in sorted(ARM_SITES.items()):
        got = bytes(code[a:a + len(bytes.fromhex(want))]).hex()
        check(got == want, f"0x{a:05X} = {want} (V103 arming intact)")
    check(code[ARM_CAL] == 1, f"0x{ARM_CAL:05X} = 1 (biquad enabled)")

    print("\n  [5] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = u32(code, blk[1])
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block byte-identical to base")

    print("\n  [6] FULL BYTE DIFF vs V229")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    check(len(pay) == 1, f"{len(pay)} payload byte -- ONE, the alpha2 cal")
    check(pay == [ALPHA2], f"and it is 0x{ALPHA2:05X}")

    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V230 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v230_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [8] NOT WRITTEN -- set ACCORD_V230_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** ONE BYTE on V229. The first build to cut BOTH bands.                          **")
    print("  ** One biquad cannot notch 18 Hz AND 55 Hz -- V228 and V229 sit on opposite      **")
    print("  ** sides of that trade. But alpha2 is a SECOND HF lever in ANOTHER lane, and     **")
    print("  ** its low-pass has DC gain 1 for any value, so lowering it moves the corner     **")
    print("  ** WITHOUT touching low frequency: 0.992 at 1 Hz, 0.932 at 3 Hz.                 **")
    print("  ** V230 = Honda's 159x notch at 55 Hz + 2.53x at 18.5 Hz + 5.62x more at 55 Hz.  **")
    print("  ** GATE 1 is the cleanest in the kit: ONE reader (0x41626), ZERO writers.        **")
    print("  ** The cal has been 22/16/14/8/5/2 historically -- 3 is INSIDE the built range,  **")
    print("  ** and none of V124-V179 ever flew, so it is UNTESTED, not falsified.            **")
    print("  ** NOT CLAIMED: the 2.53x is IN THE gp-0x6b26 LANE, not in delivered torque.     **")
    print("  ** The notch cuts gp-0x6b82 in another function -- PARALLEL lanes, and their     **")
    print("  ** ratios do NOT multiply. No total is asserted.                                 **")
    print("  ** RISK: V230's 18.5 Hz cut (2.53x, one lane) is SMALLER than V228's (4.9x,      **")
    print("  ** another lane). If the grinding is squarely at 15-22 Hz in the NOTCH's lane,   **")
    print("  ** V228 may still beat it there -- while staying 100x louder at 55 Hz.           **")
    print("  ** V229 is the clean single-variable control if the CAUSE matters.               **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
