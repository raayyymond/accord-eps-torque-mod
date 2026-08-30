# -*- coding: utf-8 -*-
r"""V232 -- THE NOTCH RE-AIMED AT THE BAND THE LANE ACTUALLY PUMPS IN. 16 BYTES ON V231.

THE MEASUREMENT THIS IS BUILT ON. `gp-0x6b86`, the notch's own lane, is flown on CAN 427 in ra4/ra5/ra6
(V104-V106). Its phase against WHEEL RATE, engaged and coherence-gated, says where it adds energy and
where it removes it. Sign mapping fixed by the kit's own b26 result ("+137/+139 deg vs wheel rate,
|cos| 0.73, i.e. +518/+565 counts of POSITIVE Re(Z)" for a lane it calls "a REAL 6-9 Hz DAMPER"), so
cos < 0 is damping and cos > 0 is pumping:

    band       median cos    verdict     route agreement
    6-9          -0.918      DAMPING     all 3 agree
    9-12         -0.989      DAMPING     all 3 agree
    12-15        -0.629      DAMPING     all 3 agree
    15-22        +0.551      PUMPING     DISAGREE -- the crossover
    22-30        +0.936      PUMPING     all 3 agree
    30-40        +0.821      PUMPING     all 3 agree

**A notch is only worth placing where the lane PUMPS.** Cutting where it damps removes damping -- the
mistake the operator aborted a drive over (V94).

THE GAP THIS FILLS. Honda centres the notch at 55.23 Hz, which is ABOVE the measured pumping band:

    Honda geometric-mean |H| over 22-40 Hz (where the lane pumps) : 0.6631  -> only a 1.51x cut
    Honda geometric-mean |H| over 44-65 Hz (where it is centred)  : 0.1070  -> a 9.35x cut

**Honda cuts the band it is centred on 6x harder than the band the lane actually pumps in.** And Honda's
placement is what is on the car today, so its 9.35x at 44-65 Hz has demonstrably NOT stopped the
grinding, while the mechanism-confirmed band sits under-treated at 1.51x.

THE GEOMETRY, from a sweep constrained by the measurement rather than by intuition:

    zeros 34.0 Hz, poles 28.0 Hz, r 0.920
      a8 = -1.79233932   ac = 0.84640000   b0 = -1.95453625   b4 = 0.84088355

                        Honda      V232      ratio     dphase   lane verdict
      6.00 Hz          0.9901    0.9842     0.994x      -2.1    DAMPS
      7.79 Hz          0.9831    0.9727     0.989x      -2.9    DAMPS
     10.50 Hz          0.9688    0.9477     0.978x      -4.4    DAMPS   <- cos -0.989 lives here
     13.50 Hz          0.9475    0.9067     0.957x      -6.4    DAMPS
     26.00 Hz          0.7866    0.4814     0.612x     -23.4    PUMPS
     30.00 Hz          0.7072    0.2459     0.348x     -31.1    PUMPS
     35.00 Hz          0.5888    0.0584     0.099x    +140.1    PUMPS

      pumping band 22-40 Hz : 5.06x cut   (Honda 1.51x)   ** 3.3x better on the energy source **
      damping band 6-15 Hz  : phase within 6.4 deg, magnitude within 4.3 %

The 6-15 Hz constraint is the one the earlier sweeps did not have. At 9-12 Hz the lane sits at
cos -0.989 -- near-perfect damping -- so ANY rotation there costs damping directly. V232 holds it to
-4.4 deg, which moves cos -0.989 to about -0.996: no loss.

WHAT IT COSTS, PLAINLY. It gives up Honda's 55 Hz cut, exactly as V228 does:

      45 Hz  1.63x louder than Honda      55 Hz  111x louder      65 Hz  3.28x louder

That band carries licensed LKAS-caused audio excess (50-60 Hz 2.13x, 60-72 Hz 2.22x, speed AND gear
matched over 6 routes). **So V232 pays the same price V228 pays -- the difference is that V232 buys
something measured for it, and V228 does not.** V228's 20.5 Hz notch sits at the damping/pumping
crossover and its skirt cuts the damping region; V232's sits inside the unanimous pumping region.

THIS IS NOT A STRICT IMPROVEMENT ON V231. It is the OTHER side of a one-biquad trade:

    V231   Honda's placement   cuts 44-65 Hz 9.35x (the audible band), pumping only 1.51x
    V232   re-aimed            cuts the pumping 5.06x, gives up the 55 Hz cut

Both leave the damping region intact. They differ in WHICH band they treat, and the honest position is
that the record does not say which matters more to the operator's symptom. **Drive V231 first** -- it is
closest to the car and carries the liveness probe -- and V232 second.

EVERYTHING ELSE IS V231, BYTE FOR BYTE, including the biquad-state probe on CAN 427, which V232 needs
even more than V231 does: its whole premise is that this filter runs.
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
WRITE_MODE = os.environ.get("ACCORD_V232_WRITE", "").strip().lower()

BASE_NAME = "_v231_V231-V229BASE-PROBE.BIQUAD.STATE_plain_image.bin"
BASE_SHA = "34a4400d3d848069890a7d2be298d4ba3118e86251421d535f2f534676cace37"

BIQ, BIQ_LEN = 0xC60A8, 16
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")
PROBE_HW2, SHIFT_OFF = 0x55DF2, 0x55E10
HW2_KEEP, SAR_KEEP = 0xC7EA, 0xA3          # V231's biquad-state probe -- CARRIED, asserted
# the re-aim: zeros 34.0 Hz, poles 28.0 Hz, r 0.920 -- bytes, never a re-derived decimal
REAIM_BIQ = bytes.fromhex("75e2e7bfacad583f3e2efabf8bf6433f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 13107
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
TAG = "V232-V231BASE-NOTCH.REAIMED.34HZ.PUMPING.BAND"

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


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def resp(b, fr, fs=1000.0):
    """|H| and phase from the ENCODED float32 in the image."""
    import cmath
    import math
    z = cmath.exp(2j * math.pi * fr / fs)
    h = (f32(b, BIQ + 12) * (z * z + f32(b, BIQ + 8) * z + 1.0)
         / (z * z + f32(b, BIQ) * z + f32(b, BIQ + 4)))
    return abs(h), math.degrees(cmath.phase(h))


def resp(b, fr, fs=1000.0):
    import cmath
    import math
    z = cmath.exp(2j * math.pi * fr / fs)
    h = (f32(b, BIQ + 12) * (z * z + f32(b, BIQ + 8) * z + 1.0)
         / (z * z + f32(b, BIQ) * z + f32(b, BIQ + 4)))
    return abs(h), math.degrees(cmath.phase(h))


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def gmean(b, lo, hi, n=160):
    import math
    return math.exp(sum(math.log(max(resp(b, lo + (hi - lo) * k / (n - 1.0))[0], 1e-6))
                        for k in range(n)) / n)


def build():
    print("=" * 102)
    print("  V232 -- THE NOTCH RE-AIMED AT THE MEASURED PUMPING BAND.  16 BYTES ON V231.")
    print("=" * 102)

    print("\n  [1] BASE = V231")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V231 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(bytes(base[BIQ:BIQ + BIQ_LEN]) == HONDA_BIQ, "base carries Honda's 55 Hz biquad")
    check(u16(base, PROBE_HW2) == HW2_KEEP, "base carries V231's biquad-state probe")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE ONE EDIT -- the biquad re-aimed")
    code[BIQ:BIQ + BIQ_LEN] = REAIM_BIQ
    attributed |= set(range(BIQ, BIQ + BIQ_LEN))
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == REAIM_BIQ, "biquad re-aimed, 16 bytes")

    print("\n  [3] THE RESPONSE, READ BACK OUT OF THE BUILT IMAGE")
    print("      %-10s %10s %10s %9s %9s  %s"
          % ("freq", "Honda", "V232", "ratio", "dphase", "lane"))
    for fr, v in ((6.0, "DAMPS"), (7.79, "DAMPS"), (10.5, "DAMPS"), (13.5, "DAMPS"),
                  (18.5, "crossover"), (26.0, "PUMPS"), (30.0, "PUMPS"), (35.0, "PUMPS"),
                  (55.0, "-")):
        ma, pa = resp(base, fr)
        mb, pb = resp(code, fr)
        print("      %7.2f Hz %10.4f %10.4f %8.3fx %8.1f\u00b0  %s"
              % (fr, ma, mb, mb / ma, pb - pa, v))

    print("\n  [4] THE MEASUREMENT-DERIVED GATES")
    pump_new, pump_old = 1 / gmean(code, 22, 40), 1 / gmean(base, 22, 40)
    check(pump_new > 3.0,
          f"pumping band 22-40 Hz cut {pump_new:.2f}x (Honda {pump_old:.2f}x) -- the point of the build")
    check(pump_new > 2.5 * pump_old, f"and that is {pump_new/pump_old:.1f}x better than Honda")
    for fr in (6.0, 7.79, 10.5, 13.5):
        ma, pa = resp(base, fr)
        mb, pb = resp(code, fr)
        check(abs(pb - pa) <= 8.0,
              f"{fr:5.2f} Hz phase moves only {pb-pa:+.1f} deg -- the lane DAMPS here, "
              f"rotation costs damping")
        check(mb / ma >= 0.94,
              f"{fr:5.2f} Hz magnitude {mb/ma:.3f} of Honda -- damping not cut")
    import numpy as np
    pk = max(resp(code, f)[0] for f in np.arange(0.5, 60.0, 0.25))
    check(pk <= 1.03, f"peak |H| over 0.5-60 Hz is {pk:.4f} -- no resonance introduced")
    check(abs(resp(code, 0.001)[0] - 1.0) < 1e-4, "DC gain 1.000000 -- no static drag added")
    import numpy as _np
    _floor = min(resp(code, f)[0] for f in _np.arange(0.25, 5.01, 0.25))
    check(_floor >= 0.99,
          f"0-5 Hz passband floor {_floor:.4f} >= 0.99 -- this NOTCHES, it does not turn the "
          f"base assist down. The first V232 cut failed this at 0.9892 and was re-cut.")

    print("\n  [5] THE COST, ASSERTED OPENLY RATHER THAN BURIED")
    m55n, m55o = resp(code, 55.0)[0], resp(base, 55.0)[0]
    check(m55n > m55o,
          f"55 Hz is {m55n/m55o:.0f}x LOUDER than Honda -- V232 GIVES UP the 55 Hz cut, "
          f"the same price V228 pays")

    print("\n  [6] EVERY OTHER LEVER AND THE PROBE ARE UNTOUCHED")
    check(u16(code, PROBE_HW2) == HW2_KEEP, "biquad-state probe CARRIED (this build needs it most)")
    check(code[SHIFT_OFF] == SAR_KEEP, "probe shift CARRIED")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B 0x{LEVER_B:05X} = {LEVER_B_VAL}")
    check(code[ALPHA2] == ALPHA2_VAL, f"0x{ALPHA2:05X} alpha2 = {ALPHA2_VAL}")
    check(u16(code, RESID_SCALE) == RESID_VAL, f"0x{RESID_SCALE:05X} = {RESID_VAL}")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- not the bricking class")
    for a, want in sorted(ARM_SITES.items()):
        check(bytes(code[a:a + len(bytes.fromhex(want))]).hex() == want, f"0x{a:05X} = {want}")
    check(code[ARM_CAL] == 1, f"0x{ARM_CAL:05X} = 1 (biquad enabled)")

    print("\n  [7] CRC RECOMPUTATION")
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

    print("\n  [8] FULL BYTE DIFF vs V231")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    _exp = sum(1 for i in range(BIQ_LEN) if HONDA_BIQ[i] != REAIM_BIQ[i])
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(all(BIQ <= a < BIQ + BIQ_LEN for a in pay),
          "every payload byte lies inside the biquad -- nothing else moved")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V232 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v232_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V232_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** THE FIRST NOTCH PLACEMENT CHOSEN FROM WHERE THE LANE PUMPS.                     **")
    print("  ** gp-0x6b86 measured on ra4/ra5/ra6: DAMPS 6-15 Hz (all 3 routes agree), PUMPS     **")
    print("  ** 22-40 Hz (all 3 agree). A notch belongs only where the lane pumps.               **")
    print("  ** Honda centres at 55.23 Hz and cuts 22-40 Hz only 1.51x, while cutting 44-65 Hz   **")
    print("  ** 9.35x -- and that 9.35x is on the car today and has NOT stopped the grinding.    **")
    print("  ** V232 cuts the pumping band 5.06x: 3.3x better on the measured energy source.     **")
    print("  ** The 6-15 Hz DAMPING region is held: phase within 6.4 deg, magnitude within 4.3 %.**")
    print("  ** At 9-12 Hz the lane sits at cos -0.989, so rotation there costs damping directly;**")
    print("  ** V232 moves it -4.4 deg, i.e. cos -0.989 -> about -0.996. No loss.                **")
    print("  ** COST, PLAINLY: 55 Hz goes 111x LOUDER -- it gives up Honda's HF cut, the SAME    **")
    print("  ** price V228 pays. The difference is that V232 buys something measured for it and  **")
    print("  ** V228 does not: V228's 20.5 Hz notch sits at the crossover and its skirt cuts the  **")
    print("  ** DAMPING region.                                                                  **")
    print("  ** NOT A STRICT IMPROVEMENT ON V231 -- it is the other side of a one-biquad trade.  **")
    print("  ** V231 cuts 44-65 Hz (audible, 2.1-2.2x LKAS excess); V232 cuts the pumping.       **")
    print("  ** The record does not say which matters more. DRIVE V231 FIRST, V232 SECOND.       **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
