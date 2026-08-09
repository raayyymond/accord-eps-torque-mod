#!/usr/bin/env python3
"""FUN_0003b8f6's FRICTION term: a Coulomb relay proportional to the delivered motor command.

Mirrors the decompiled arithmetic exactly, each line annotated with its instruction address.
Constants are read LITTLE-ENDIAN from the shipped images.  dB/Hz interpretation comes AFTER the code.

Chain (all inside FUN_0003b8f6 @0x3b8f6, task 1 = 1 kHz, sole caller FUN_0002214a @0x2240e):

    gate     : |gp-0x6b98| <= 0x2000  and  |gp-0x4f60| <= 0x6400  and  |gp-0x6abc| <= 13000
               and gp-0x6752 in {-1,0,1}          -- else the whole lane emits the 0x7FFF sentinel
    model    = EMA2(gp-0x6b98 * polarity / 1024, a=0xC40D4)        <- the DELIVERED MOTOR COMMAND
               + clamp(FIR(EMA2(gp-0x4f60/1024)) , +-15) * LERP(gp-0x6a10)/1024
    iVar20   = polarity * gp-0x6abc * 12                            @0x3bab0
    ratio    = clamp(iVar20 / cal(0xC40BC), +-1.0)                  @0x3bab4  <-- THE RELAY
    FRICTION = clamp(EMA(|model|*ratio*cal(0xC40D2)/1024 + cal(0xC4080)/1024*ratio,
                         a=cal(0xC40D0)/4096), +-10.0)
    gp-0x6bfc = clamp(cal(0xC6468) * (model - FRICTION - INERTIA), +-20000)

`ratio` saturates at |gp-0x6abc| = cal(0xC40BC)/12.  Stock 600/12 = 50, against an enable gate of
13000 => pinned at +-1 across 99.6% of its own valid input range.  That is sign(motor rate), not a
proportional gain.
"""
import struct
from pathlib import Path

ROOT = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMAGES = {
    "STOCK": ROOT / "stock_fw_dump" / "code.bin",
    "V38":   ROOT / "_v38_plain_image.bin",
    "V67":   ROOT / "_v67_plain_image.bin",
    "V81":   ROOT / "_v81_C407E.511-FRICTION.STOCK_plain_image.bin",
    "V84":   ROOT / "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin",
}
CALS = {                       # tp = 0xBF000
    0xC40BC: "ratio normalizer   (tp+0x50bc)",
    0xC40D0: "friction IIR alpha (tp+0x50d0)",
    0xC40D2: "friction scale     (tp+0x50d2)",
    0xC4080: "friction constant  (tp+0x5080)",
    0xC6468: "output scale       (tp+0x7468)",
    0xC646E: "INERTIA gain       (tp+0x746e)",
}
RATE_GATE = 13000              # |gp-0x6abc| enable bound, from the function's own entry test
MODEL_MAX = 8                  # gp-0x6b98 gate 0x2000 / 1024


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def describing_function(amp_counts, norm):
    """Fundamental-harmonic gain of clamp(x, +-1) driven by x = (12*R/norm)*sin(theta),
    normalised by the input scale so that a purely linear (viscous) term returns 1.0."""
    import math
    a = 12.0 * amp_counts / norm
    if a <= 1.0:
        return 1.0                                   # linear region: no distortion
    return (2.0 / math.pi) * (math.asin(1.0 / a) + (1.0 / a) * math.sqrt(1.0 - 1.0 / a ** 2))


def relay_index(norm):
    """The kit's relay metric: N(50)/N(500).  1.00 = viscous, larger = more relay-like."""
    return describing_function(50, norm) / describing_function(500, norm)


def main():
    print("=== calibration census (little-endian u16, read from the shipped images) ===")
    imgs = {k: v.read_bytes() for k, v in IMAGES.items() if v.exists()}
    names = list(imgs)
    print(f"{'cell':<38}" + "".join(f"{n:>9}" for n in names))
    for addr, label in CALS.items():
        vals = [str(u16(imgs[n], addr)) for n in names]
        flag = "" if len(set(vals)) == 1 else "   <-- DIFFERS"
        print(f"0x{addr:05X} {label:<29}" + "".join(f"{v:>9}" for v in vals) + flag)

    norm = u16(imgs["V84"], 0xC40BC)
    print(f"\n=== the relay, at the shipped value 0xC40BC = {norm} ===")
    sat = norm / 12.0
    print(f"ratio saturates at |gp-0x6abc| = {norm}/12 = {sat:.1f} counts")
    print(f"the function's own enable gate accepts |gp-0x6abc| <= {RATE_GATE}")
    print(f"=> LINEAR over {100.0*sat/RATE_GATE:.2f}% of the valid range; "
          f"a RELAY over {100.0*(1-sat/RATE_GATE):.2f}%")

    print("\n=== describing function N(R), and the kit's relay index N(50)/N(500) ===")
    print("reference points: Honda's viscous damper 1.00 (linear) | V75 1.45 | V80 bang-bang 3.27")
    print(f"\n{'0xC40BC':>9}{'sat @ counts':>14}" +
          "".join(f"{f'N({r})':>9}" for r in (25, 50, 100, 250, 500, 1000)) + f"{'RELAY IDX':>11}")
    for cand in (600, 1200, 3000, 6000, 12000, 24000, 65535):
        row = "".join(f"{describing_function(r, cand):>9.3f}" for r in (25, 50, 100, 250, 500, 1000))
        mark = "   <-- SHIPPED" if cand == norm else ""
        print(f"{cand:>9}{cand/12.0:>14.0f}" + row + f"{relay_index(cand):>11.2f}" + mark)

    print("\n=== size of the discontinuity at a velocity zero-crossing ===")
    scale = u16(imgs["V84"], 0xC6468)
    kf = u16(imgs["V84"], 0xC40D2) / 1024.0
    print(f"FRICTION = |model| * ratio * {u16(imgs['V84'], 0xC40D2)}/1024 "
          f"(+ constant {u16(imgs['V84'], 0xC4080)}/1024 * ratio), clamp +-10")
    print(f"gp-0x6bfc contribution = {scale} * FRICTION      (raw float multiply, NOT Q10 here)")
    print(f"\n{'|model|':>9}{'FRICTION':>11}{'counts in gp-0x6bfc':>21}{'p-p across sign flip':>23}")
    for m in (1, 2, 4, 6, MODEL_MAX):
        fr = min(m * kf, 10.0)
        print(f"{m:>9}{fr:>11.3f}{scale*fr:>21.0f}{2*scale*fr:>23.0f}")
    print(f"\n(|model| is bounded to ~{MODEL_MAX} by the function's own |gp-0x6b98| <= 0x2000 gate,"
          f"\n so FRICTION never reaches its +-10 clamp; the +-20000 clamp on gp-0x6bfc can bind.)")


if __name__ == "__main__":
    main()
