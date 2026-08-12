#!/usr/bin/env python3
r"""V93 — the decompiled arithmetic mirrored EXACTLY in integer Python, then the curves.

Standing operator instruction (CLAUDE.md, 2026-07-28): explain firmware with simple Python that
mirrors the decompiled arithmetic EXACTLY — integer `>>`, the real Q-format, the real branch
conditions, each line annotated with its instruction address, constants byte-read LITTLE-ENDIAN.
dB/Hz interpretation comes AFTER the code, never instead of it.

Every constant below is READ FROM THE IMAGE at run time. Nothing is typed in twice.

Emits `_cache_r78/v93_curves.json` for the diagrams.
"""
import json
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
FW = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
STOCK = (FW / "stock_fw_dump" / "code.bin").read_bytes()
V93 = (FW / "_v93_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75_plain_image.bin").read_bytes()
TP = 0xBF000
CNT_PER_KMH = 64.0                       # cal 0xC62EA = 320 ct ~ 5 km/h


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def sar(x, n):
    """Arithmetic shift right on a SIGNED 32-bit quantity — V850 `sar`. Python >> already floors."""
    return x >> n


def to_int32(x):
    """Low 32 bits, interpreted signed. This is what `mul rX,rY,r0` leaves in rY when r0 is
    discarded — and it is the ONLY place an overflow can appear in this lane."""
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


# =================================================================================================
# FUN_00041464 — how gp-0x6c2c is MADE.  This is the function that settles what the lever scales.
# =================================================================================================
class RateDeriv:
    """Mirrors 0x415B8..0x4164C.  State is `gp-0x359c` (filtered rate) and `gp-0x35a0` (EMA)."""

    SENTINEL = 0x7FFFFFFF

    def __init__(self, img):
        self.alpha_rate = struct.unpack_from("<H", img, TP + 0x743C)[0]   # 0xC643C
        self.alpha_a = struct.unpack_from("<H", img, TP + 0x50DC)[0]      # 0xC40DC
        self.filt = self.SENTINEL      # gp-0x359c
        self.ema_a = 0                 # gp-0x35a0

    def step(self, rate):
        # 0x415BE  addi 0x32c8,r15,r11 / 0x415C2 addi -0x6591,r11,r0 -> validity window ±13000
        if not (-13000 <= rate <= 13000):
            return None                                    # 0x415CE bc -> the invalid branch
        old = self.filt                                    # r7 = gp-0x359c, the PREVIOUS tick
        shifted = rate << 10                               # 0x415D4  shl 0xa,r28
        if old == self.SENTINEL:                           # 0x415D8  be -> first tick
            new = shifted                                  # 0x415EE  mov r28,r24
            old = new                                      # 0x415FE  mov r24,r7  (reset: diff = 0)
        else:
            # 0x415DE sub r7,r28 / 0x415E0 mul r10,r28,r0 / 0x415E6 sar 0x7,r28 / 0x415E8 add
            new = old + sar(to_int32((shifted - old) * self.alpha_rate), 7)
            if old > 0xCB2000:                             # 0x415FA cmp / 0x415FC ble
                old = new                                  # 0x415FE  reset path only
        d = new - old                                      # 0x41602  sub r7,r9   🛑 FIRST DIFFERENCE
        if d <= 0x7D000:                                   # 0x4160A cmp / 0x41610 bgt
            d = d << 5                                     # 0x41612  shl 0x5,r9        ×32
            d = max(d, -0xFA0000)                          # 0x4161A  cmovle            clamp
        else:
            d = 0xFA0000                                   # 0x4160C  movhi 0xfa,r0,r22
        # 0x41630 sub / 0x41632 mul / 0x4163A sar 0x6 / 0x41642 add / 0x41644 st.w
        self.ema_a = self.ema_a + sar(to_int32((d - self.ema_a) * self.alpha_a), 6)
        self.filt = new                                    # 0x41B56 tail: st.w r?, -0x359c
        return sar(self.ema_a, 9)                          # -> gp-0x6c2c


# =================================================================================================
# FUN_00036c12 — how gp-0x6b26 is MADE from gp-0x6c2c and the gain.
# =================================================================================================
def friction_gain(img, mode, speed_counts, g671a=0, g67f4=1):
    """The THREE gain sources, with the REAL branch conditions.  0x36C1E..0x36CB4."""
    if g671a >= 0xFF or g67f4 != 1:                        # 0x36C30 addi / 0x36C38 bc, 0x36C40 bne
        return s16(img, TP + 0x740C), "FALLBACK-1 (0xC640C)"
    if g671a >= img[TP + 0x74FD]:                          # 0x36C46 cmp / 0x36C48 bnc
        return s16(img, TP + 0x740A), "FALLBACK-2 (0xC640A)"
    rec = struct.unpack_from("<I", img, 0xCBE74 + mode * 4)[0]   # 0x36C4A..0x36C58
    n = s16(img, rec)
    X = [s16(img, rec + 2 + 2 * i) for i in range(n)]
    Y = [s16(img, rec + 8 + 2 * i) for i in range(n)]
    v = speed_counts
    if v <= X[0]:                                          # 0x36C6C  bgt
        return Y[0], f"LERP mode {mode} @X[0]"
    if v >= X[-1]:                                         # 0x36C78  bge
        return Y[-1], f"LERP mode {mode} @X[-1]"
    for i in range(1, n):                                  # 0x36C8A..0x36C92 the walk
        if v < X[i]:
            # 0x36C94..0x36CB0: (Y[i]-Y[i-1]) * (v-X[i-1]) / (X[i]-X[i-1]) + Y[i-1]  -- INTEGER divq
            return (Y[i] - Y[i - 1]) * (v - X[i - 1]) // (X[i] - X[i - 1]) + Y[i - 1], \
                   f"LERP mode {mode}"
    return Y[-1], f"LERP mode {mode}"


def b26(img, accel, gain):
    """0x36CBE..0x36CE4.  Returns (value, wrapped?)."""
    r14 = (accel + 0x7D00) & 0xFFFFFFFF                    # 0x36C26  addi 0x7d00,r9,r14
    r13 = 0 if r14 >= 0xFA01 else accel                    # 0x36C2C  cmovnc  -> ±32000 window
    r13 = sar(r13 * gain, 6)                               # 0x36CBE mulh / 0x36CC4 sar 0x6
    prod = r13 * 0x111                                     # 0x36CC6  mul r13,r6,r0 (HIGH DISCARDED)
    wrapped = not (-(1 << 31) <= prod < (1 << 31))
    r6 = sar(to_int32(prod), 0x12)                         # 0x36CCA  sar 0x12,r6
    clamp = s16(img, TP + 0x507E)                          # 0x36C34  ld.h 0x507e[tp] -> 0xC407E
    return max(-clamp, min(clamp, r6)), wrapped            # 0x36CCC..0x36CE2


# =================================================================================================
if __name__ == "__main__":
    OUT = {}
    print("=" * 96)
    print("  CONSTANTS, byte-read little-endian from the IMAGES (nothing typed twice)")
    print("=" * 96)
    for nm, a in (("0xC407E clamp", TP + 0x507E), ("0xC640A fallback-2", TP + 0x740A),
                  ("0xC640C fallback-1", TP + 0x740C), ("0xC643C rate EMA alpha", TP + 0x743C),
                  ("0xC40DC deriv EMA alpha", TP + 0x50DC)):
        print(f"    {nm:<26} stock {s16(STOCK, a):>7}   V93 {s16(V93, a):>7}")
    print(f"    {'0xC64FD fallback-2 gate':<26} stock {STOCK[TP+0x74FD]:>7}   "
          f"V93 {V93[TP+0x74FD]:>7}")

    # ---------------- 1. GAIN vs SPEED, every branch, both images -------------------------
    print("\n" + "=" * 96)
    print("  1. THE GAIN, vs SPEED — this is the whole lever")
    print("=" * 96)
    speeds = list(range(0, 121, 5))
    curves = {}
    for tag, img in (("stock", STOCK), ("V93", V93)):
        for mode in (24, 26):
            key = f"{tag}_m{mode}"
            curves[key] = [friction_gain(img, mode, int(k * CNT_PER_KMH))[0] for k in speeds]
        curves[f"{tag}_fb2"] = [s16(img, TP + 0x740A)] * len(speeds)
        curves[f"{tag}_fb1"] = [s16(img, TP + 0x740C)] * len(speeds)
    OUT["speeds_kmh"] = speeds
    OUT["gain_curves"] = curves
    print(f"    {'km/h':>5} {'stock m26':>10} {'V93 m26':>9} {'ratio':>7} | "
          f"{'stock m24':>10} {'V93 m24':>9} | {'fb2 s/V93':>13} {'fb1 s/V93':>13}")
    for i, k in enumerate(speeds):
        if k % 20:
            continue
        s26, n26 = curves["stock_m26"][i], curves["V93_m26"][i]
        s24, n24 = curves["stock_m24"][i], curves["V93_m24"][i]
        print(f"    {k:>5} {s26:>10} {n26:>9} {n26/s26:>7.3f} | {s24:>10} {n24:>9} | "
              f"{curves['stock_fb2'][i]:>6}/{curves['V93_fb2'][i]:<6} "
              f"{curves['stock_fb1'][i]:>6}/{curves['V93_fb1'][i]:<6}")

    # ---------------- 2. DELIVERED |gp-0x6b26| vs acceleration ----------------------------
    print("\n" + "=" * 96)
    print("  2. DELIVERED gp-0x6b26 vs gp-0x6c2c, at 50 km/h — the transfer, end to end")
    print("=" * 96)
    accels = list(range(0, 32001, 500))
    v_c = int(50 * CNT_PER_KMH)
    deliv = {}
    for tag, img in (("stock", STOCK), ("V93", V93)):
        g26 = friction_gain(img, 26, v_c)[0]
        deliv[tag] = [b26(img, a, g26)[0] for a in accels]
    OUT["accels"] = accels
    OUT["delivered"] = deliv
    print(f"    {'gp-0x6c2c':>10} {'stock b26':>10} {'V93 b26':>9} {'delta':>7}")
    for i, a in enumerate(accels):
        if a % 4000:
            continue
        print(f"    {a:>10} {deliv['stock'][i]:>10} {deliv['V93'][i]:>9} "
              f"{deliv['V93'][i]-deliv['stock'][i]:>7}")
    st_max, v93_max = max(map(abs, deliv["stock"])), max(map(abs, deliv["V93"]))
    print(f"\n    peak |b26| over the producer's FULL ±32000 range: stock {st_max}  V93 {v93_max}")
    print(f"    the ±{s16(STOCK, TP+0x507E)} clamp is reached by stock: "
          f"{st_max >= s16(STOCK, TP+0x507E)};  by V93: {v93_max >= s16(V93, TP+0x507E)}")
    OUT["peak_stock"], OUT["peak_v93"] = st_max, v93_max

    # ---------------- 3. OVERFLOW — the bound that capped V91 --------------------------
    print("\n" + "=" * 96)
    print("  3. INT32 WRAPAROUND in `mul r13,r6,r0` — V93 moves AWAY from it")
    print("=" * 96)
    for tag, img in (("stock", STOCK), ("V93", V93)):
        g = friction_gain(img, 26, 0)[0]           # worst case = Y[0], the largest magnitude
        lo = 1
        while lo < 10 ** 7 and not b26(img, min(lo, 32000), g)[1]:
            lo += 250
        wraps = b26(img, 32000, g)[1]
        print(f"    {tag:<6} worst gain {g:>7}   wraps within the producer's ±32000 window? "
              f"{wraps}")
    OUT["wrap_stock"] = b26(STOCK, 32000, friction_gain(STOCK, 26, 0)[0])[1]
    OUT["wrap_v93"] = b26(V93, 32000, friction_gain(V93, 26, 0)[0])[1]

    # ---------------- 4. THE RESONANCE-SHIFT FAMILY -----------------------------------
    print("\n" + "=" * 96)
    print("  4. WHAT IT DOES TO THE RESONANCE — as a FAMILY, because K/J is NOT measured")
    print("=" * 96)
    print("    (J + K)·alpha = T_driver  =>  omega_n = sqrt(k / (J + K))")
    print("    V93 takes K -> 0.25 K, so  omega_new/omega_old = sqrt((J+K)/(J+0.25K))")
    print("    r = K/J is UNKNOWN. The whole point of flying this is to MEASURE it.\n")
    rs = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0]
    fam = []
    F0 = 7.79                                   # the measured ratchet centre, route 4f
    for r in rs:
        ratio = ((1 + r) / (1 + 0.25 * r)) ** 0.5
        fam.append(dict(r=r, ratio=ratio, f_new=F0 * ratio))
        print(f"    K/J = {r:<5}  omega ratio {ratio:.4f}   7.79 Hz -> {F0*ratio:5.2f} Hz")
    OUT["resonance_family"] = fam
    OUT["f0"] = F0
    print("\n    🛑 PRE-REGISTERED READOUT: the ratchet's CENTRE FREQUENCY on the V93 drive is a")
    print("       DIRECT MEASUREMENT OF K/J. No shift => K/J ~ 0 => this lever is IRRELEVANT to")
    print("       the mode and the lane should be abandoned. A shift up => K/J is real and the")
    print("       size of the shift SIZES the next dose. Either way it is a decisive result.")

    (ROOT / "_cache_r78" / "v93_curves.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _cache_r78/v93_curves.json")
