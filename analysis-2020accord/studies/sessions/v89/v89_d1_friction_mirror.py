#!/usr/bin/env python3
"""studies/sessions/v89/v89_d1_friction_mirror.py -- FUN_0003b8f6's friction term, mirrored instruction for instruction.

Standing operator instruction (2026-07-28): explain firmware with Python that mirrors the decompiled
arithmetic EXACTLY -- real Q-format, real branch conditions, each line annotated with its
instruction address, constants byte-read little-endian. dB/Hz interpretation comes AFTER the code.

THE CHAIN (all four stages verified in Ghidra this session, decompile THEN assembly)

    FUN_0003b8f6  model + friction + damping   -> gp-0x6bfc   (and mirrors gp-0x6ae0 / gp-0x6ae2)
    FUN_0003bc20  plausibility  |x| <= 20000   -> gp-0x6bfe   (else 0x7fff sentinel)
    FUN_00038148  residual = MODEL - ACTUAL    -> gp-0x6b70 = sign(res) x LERP(|res|)
                  ACTUAL = EMA of six aggregator lanes (one of them is gp-0x6bd0, the DAMPER)
    -> FUN_00037fe6 -> gp-0x6ad6 -> PID -> motor        [chain per the record; not re-verified here]

=> this is a DISTURBANCE OBSERVER. `gp-0x6b70` is a correction driven by how far the plant MODEL
   disagrees with the assist actually being produced. If the model UNDER-states real Coulomb
   friction, the un-modelled friction lands in the residual and the observer chases it -- which is
   what a stick-slip ratchet looks like.

THE FRICTION TERM (0x3BAAE .. 0x3BB46)

    ratio    = clamp( polarity * gp_0x6abc * 12 / cal[0xC40BC] , -1, +1 )     # 0x3BAAE..0x3BAE4
    friction = clamp( EMA_a( |model| * ratio * K1/1024  +  ratio * K0/1024 ), -10, +10 )
               K1 = cal[0xC40D2] = 102     a = cal[0xC40D0]/4096 = 408/4096   # 0x3BAF6..0x3BB46
               K0 = cal[0xC4080] = 0       (pure Coulomb arm, OFF on every build)
    out      = clamp( (model - friction - damping) * cal[0xC6468], -20000, +20000 )   # 0x3BBBE..

BLAST RADIUS, byte-censused twice (the disp|1 trap: `ld.hu 0x50d2[tp]` encodes hw2 = 0x50d3)
    0xC40D2  ->  ONE reader, 0x3BAFE, inside this function.  ZERO writers.  Virgin on all 88 builds.
    gp-0x6ae2 = friction * 1024  ->  1 writer / 0 readers  ==  FREE probe, blast radius zero.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMG = sorted(FW.glob("_v88_*_plain_image.bin"))[0]
TP = 0xBF000


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


class Friction:
    """State-carrying mirror of the friction EMA at gp-0x362c."""

    def __init__(self, img, k1=None, k0=None, gate=None):
        self.K1 = k1 if k1 is not None else u16(img, TP + 0x50D2)   # 0x3BAFE ld.hu 0x50d2[tp]
        self.K0 = k0 if k0 is not None else u16(img, TP + 0x5080)   # 0x3BAF6 ld.hu 0x5080[tp]
        self.A = u16(img, TP + 0x50D0)                              # 0x3BB22 ld.hu 0x50d0[tp]
        self.GATE = gate if gate is not None else u16(img, TP + 0x50BC)   # 0x3BAB4
        self.state = 0.0                                            # gp-0x362c

    def step(self, model, g6abc, polarity):
        # 0x3BAAE mulh r1,r6 ; 0x3BAB0 mul 0xc,r6,r0   -> numerator
        num = polarity * g6abc * 12
        # 0x3BAC8/0x3BACC/0x3BAD0: (0.5*num) / (0.5*gate)  -- the 0.5s cancel exactly
        r = num / self.GATE if self.GATE else 0.0
        # 0x3BAD4..0x3BAE4  clamp to +/-1.0
        ratio = clamp(r, -1.0, 1.0)
        # 0x3BAE8..0x3BAF2  |model|
        amod = abs(model)
        # 0x3BB02..0x3BB16  raw = |model|*ratio*K1/1024 + ratio*K0/1024
        raw = amod * ratio * self.K1 / 1024.0 + ratio * self.K0 / 1024.0
        # 0x3BB1E..0x3BB2E  EMA: state += (raw - state) * A / 4096
        self.state = self.state + (raw - self.state) * self.A / 4096.0
        # 0x3BB32..0x3BB46  clamp +/-10.0
        return clamp(self.state, -10.0, 10.0)


def main():
    img = IMG.read_bytes()
    print(f"image: {IMG.name}\n")
    f = Friction(img)
    gain = u16(img, TP + 0x7468)
    print("CALS, little-endian from the built image")
    print(f"  0xC40D2 K1   (|model| arm)   = {f.K1:5d}   -> K1/1024 = {f.K1/1024:.4f}")
    print(f"  0xC4080 K0   (pure Coulomb)  = {f.K0:5d}   <- OFF on every build; the relay hazard")
    print(f"  0xC40D0 EMA  alpha           = {f.A:5d}   -> {f.A/4096:.4f}  (corner "
          f"{-1000*__import__('math').log(1-f.A/4096)/(2*3.141592653589793):.2f} Hz at 1 kHz)")
    print(f"  0xC40BC gate (ratio denom)   = {f.GATE:5d}   -> |gp-0x6abc| >= "
          f"{f.GATE/12:.1f} saturates the ratio")
    print(f"  0xC6468 model output gain    = {gain:5d}   (SHARED -- 5 readers, do not touch)\n")

    print("=" * 92)
    print("STEADY-STATE FRICTION vs the |model| it opposes, ratio saturated (|gp-0x6abc| >= 50)")
    print("=" * 92)
    doses = [102, 153, 204, 306, 408]
    print(f"  {'|model|':>9s} " + "".join(f"{'K1=%d' % k:>12s}" for k in doses)
          + "     (friction, and % of |model|)")
    for amod in (0.1, 0.2, 0.5, 1.0, 2.0, 5.0):
        row = ""
        for k in doses:
            fr = amod * 1.0 * k / 1024.0
            row += f"{fr:8.3f}({100*fr/amod:3.0f}%)"
        print(f"  {amod:9.2f} " + row)
    print(f"\n  the +/-10.0 clamp is reached only at |model| * K1/1024 = 10, i.e. |model| >= "
          f"{10*1024/204:.0f} at K1=204 -- unreachable (the model's own bar arm is clamped at 15).")

    print("\n" + "=" * 92)
    print("WHAT THE DOSE DOES TO THE OBSERVER RESIDUAL")
    print("=" * 92)
    print("  out = (model - friction - damping) * 2639,  and  residual = out_validated - ACTUAL")
    print("  With friction = k*|model| and damping held fixed, raising k by d shifts the model")
    print("  output by  -d*|model|*2639  counts, i.e. it moves the model TOWARD a plant that has")
    print("  more Coulomb friction -- which is the direction the measurement says helps.\n")
    for k in doses:
        d = (k - 102) / 1024.0
        print(f"    K1={k:3d} ({k/102:.2f}x)  extra modelled friction = {d:.4f}*|model|"
              f"  -> model output shifts by {-d*2639:8.1f} * |model| counts")

    print("\n" + "=" * 92)
    print("EMPIRICAL ANCHOR -- the only friction dose this car has ever flown")
    print("=" * 92)
    print("  0xC40BC 600 -> 6000 REDUCES |ratio| (saturation moves from |gp-0x6abc| >= 50 to >= 500)")
    print("  and therefore reduces friction. Measured (v89_c3, within-route, 235 blocks):")
    print("      gate  600 : engaged/manual 6-9 Hz = 2.89x [2.14,  3.92]")
    print("      gate 6000 : engaged/manual 6-9 Hz = 6.58x [3.19, 13.14]")
    print("      eng x FRIC6000 band contrast +0.682 [+0.213, +1.166], EXCLUDES 0")
    print("  => LESS friction, MORE ratchet. The gradient points UP, and K1 is the clean way up:")
    print("     it scales the |model| arm only, leaving the ratio's shape (and its relay-ness)")
    print("     untouched, so it is NOT the V80 flatten-into-a-relay class.")
    print("\n  🛑 The 600->6000 contrast confounds MAGNITUDE with RELAY-NESS. K1 raises magnitude")
    print("     alone. That the two act the same way is BELIEF, and it is what V89 tests.")


if __name__ == "__main__":
    main()
