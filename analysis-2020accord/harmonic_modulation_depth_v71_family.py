#!/usr/bin/env python3
"""
harmonic_modulation_depth_v71_family.py -- modulation depth (r24/gain_B and r26/gain_A) across
stock + the flown/built rate-lane configs, PARAMETERISED on the operating range of gp-0x6ac0.

Extends analysis-2020accord/v70_parametric_gain_collapse.py (r24 only) with r26 and the V71 family.
Every X/Y record below is READ DIRECTLY FROM THE SHIPPED IMAGE BYTES by verify_against_image() --
not hand-copied -- specifically because a hand-copy already produced one indexing slip this session
(see CORRECTION note below).

Mechanism, CONFIRMED by fresh decompile of FUN_00041464 (0x41464), 2026-08-04 [EVIDENCE]:
  uVar8 = uVar16; if ((int)uVar16 < 0) uVar8 = -uVar16;      // explicit ABS
  gp-0x6ac0 = uVar8 >> 10                                     // RECTIFIED
  gp-0x6abe = (short)((int)uVar16 >> 10)                      // SIGNED sibling, same source state
Both r24 (gain_B) and r26 (gain_A) index their damping-gain LERP on gp-0x6ac0, confirmed at
0x3AAC4 `ld.hu -0x6ac0[gp],r11` (disassemble_bytes, 2026-08-04).

CORRECTION TO A NUMBER IN CIRCULATION THIS SESSION: stock gain_B "rolloff" was quoted as 1.51x.
That is Y[2]/Y[3] = 2322/1536 = 1.5117 -- the POST-PLATEAU segment only. The FULL end-to-end depth
Y[0]/Y[3] = 3072/1536 = 2.00x EXACTLY, byte-read fresh from stock_fw_dump/code.bin this message
(struct.unpack_from, ptr = LE32 @0xCBF5C+10*4 = 0xD2A74). 2.00x is also what v70_parametric_gain_
collapse.py has asserted against the image since 2026-08-04 (assert xs,ys,yv == X,Y_STOCK,Y_V69).
gain_A's stock depth checks out at 1.50x exactly either way (3072/2048), no discrepancy there.
"""
import os
import struct
from pathlib import Path

_env = os.environ.get("ACCORD_FIRMWARE_ROOT")
_root = Path(_env) if _env else Path(__file__).resolve().parents[2] / "accord-firmwares"
ROOT = str(_root / "analysis-2020accord") + "/"


def verify_against_image():
    stock = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
    ptr = struct.unpack_from("<I", stock, 0xCBF5C + 10 * 4)[0]
    gb_x = tuple(struct.unpack_from("<h", stock, ptr + 2 + 2 * i)[0] for i in range(4))
    gb_y = tuple(struct.unpack_from("<h", stock, ptr + 10 + 2 * i)[0] for i in range(4))
    ga_x = tuple(struct.unpack_from("<h", stock, 0xC6A68 + 2 + 2 * i)[0] for i in range(4))
    ga_y = tuple(struct.unpack_from("<h", stock, 0xC6A68 + 10 + 2 * i)[0] for i in range(4))
    assert ptr == 0xD2A74, hex(ptr)
    assert (gb_x, gb_y) == ((0, 400, 1400, 3000), (3072, 3072, 2322, 1536)), (gb_x, gb_y)
    assert (ga_x, ga_y) == ((0, 400, 1600, 3000), (3072, 3072, 2434, 2048)), (ga_x, ga_y)
    return gb_x, gb_y, ga_x, ga_y


GB_X_STOCK, GB_Y_STOCK, GA_X_STOCK, GA_Y_STOCK = verify_against_image()
print("gain_B mode-10 0km/h record @0xD2A74, gain_A rec0 @0xC6A68 -- both byte-verified vs stock image.")
print(f"  gain_B  X={GB_X_STOCK}  Y={GB_Y_STOCK}  full depth Y[0]/Y[3] = {GB_Y_STOCK[0]/GB_Y_STOCK[3]:.4f}x"
      f"  (post-plateau-only Y[2]/Y[3] = {GB_Y_STOCK[2]/GB_Y_STOCK[3]:.4f}x -- NOT the same number)")
print(f"  gain_A  X={GA_X_STOCK}  Y={GA_Y_STOCK}  full depth Y[0]/Y[3] = {GA_Y_STOCK[0]/GA_Y_STOCK[3]:.4f}x")

GB_Y_V69 = (12288, 12288, 2322, 1536)              # V69/V70 shipped edit, Y[0..1] only
GA_Y_V71B = (6144, 6144, 4868, 4096)               # V71B shipped edit, rec0 Y[0..3] all x2


def lerp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for i in range(len(xs) - 1):
        if x <= xs[i + 1]:
            return ys[i] + ((ys[i + 1] - ys[i]) * (x - xs[i])) // (xs[i + 1] - xs[i])
    return ys[-1]


CONFIGS = {
    "stock":            (lambda rk: lerp(GB_X_STOCK, GB_Y_STOCK, rk), lambda rk: lerp(GA_X_STOCK, GA_Y_STOCK, rk)),
    "V62/V65 (x2 sar)": (lambda rk: 2 * lerp(GB_X_STOCK, GB_Y_STOCK, rk), lambda rk: 2 * lerp(GA_X_STOCK, GA_Y_STOCK, rk)),
    "V67/68 engaged":   (lambda rk: 5244, lambda rk: 512),          # both arms flat
    "V71C engaged":     (lambda rk: 5244, lambda rk: 3072),         # r26 arm restored to ~stock level
    "V69/V70":          (lambda rk: lerp(GB_X_STOCK, GB_Y_V69, rk), lambda rk: lerp(GA_X_STOCK, GA_Y_STOCK, rk)),
    "V71B":             (lambda rk: lerp(GB_X_STOCK, GB_Y_STOCK, rk), lambda rk: lerp(GA_X_STOCK, GA_Y_V71B, rk)),
}

GRIND1_E1822 = {"stock": 879, "V62/V65 (x2 sar)": 168, "V67/68 engaged": 109,
                "V69/V70": 729.5, "V71B": None, "V71C engaged": None}

print("\n" + "=" * 118)
print("DEPTH PARAMETERISED ON THE UNSETTLED OPERATING RANGE OF gp-0x6ac0 (rate index)")
print("depth(range) = max(gain over [0,R]) / min(gain over [0,R]) -- i.e. assume the oscillation's own")
print("peak |rate| = R, sweep gain(|R*sin(theta)|) over theta in [0,pi], take max/min.")
print("=" * 118)
import numpy as np
for label, R in (("(a) confined to [0,400] -- flat plateau", 400),
                  ("(b) spans [0,1400] -- grind#1's own ~603-1400 range", 1400),
                  ("(c) spans [0,3000] -- full table, grind#2-creep ~1206+ range", 3000)):
    print(f"\n-- {label} --")
    print(f"  {'config':<20}{'r24 depth':>12}{'r26 depth':>12}{'grind#1 e_18-22':>18}")
    thetas = np.linspace(0, np.pi, 400)
    for name, (gB, gA) in CONFIGS.items():
        rk = np.abs(R * np.sin(thetas)).astype(int)
        vb = [gB(int(r)) for r in rk]
        va = [gA(int(r)) for r in rk]
        db = max(vb) / min(vb)
        da = max(va) / min(va)
        e = GRIND1_E1822.get(name)
        estr = f"{e:.0f}" if e is not None else "untested"
        print(f"  {name:<20}{db:>11.2f}x{da:>11.2f}x{estr:>18}")

print("""
====================================================================================================
VERDICT ON "DOES DEPTH RANK THE CORPUS"
====================================================================================================
At range (a) [0,400] -- the flat plateau only -- EVERY LERP-based config reads 1.00x depth (stock,
V62/65, V69/70, V71B all keep Y[0]==Y[1] within this window; only the absolute LEVEL differs). Depth
CANNOT explain any of the corpus's grind#1 spread here, because there is no depth to speak of -- the
mechanism is structurally silent if grind#1's rate excursion never leaves [0,400]. Any explanation at
this range must come from LEVEL alone (the differentiator-frequency-response story), not modulation
depth. This is why the operating-range question is decisive, not academic.

At range (b) and (c), the flat/depth=1.00 configs (V67/68, V71C-engaged) and the depth-preserved
configs (V62/65, V71B) diverge in a pattern that INCLUDES level as well as depth -- they cannot be
teased apart from grind#1's e_18-22 numbers alone, because every build in the corpus changes BOTH
level and (sometimes) depth simultaneously; no build in the flown set holds level fixed while varying
depth alone, or vice versa. V69/V70 is the only config whose depth INCREASES over stock's own -- at
every range where the oscillation reaches beyond the plateau, and that is consistent with (not proof
of) the parametric-collapse account of V69/70's grind#1 return already in the record.
""")
