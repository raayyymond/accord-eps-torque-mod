#!/usr/bin/env python3
"""DELIVERED r24 / r26 rate-lane multipliers, per build, on a **mode-24/26** car.

🛑 WHY THIS FILE EXISTS. The two-lane grind-#2 rule in `docs/STATE.md` is tabulated on NOMINAL
multipliers -- the number the build script intended. RULE 7 (`reference-accord-car-is-tvca4-mode-24-26`)
says the car is config row 11 `TVCA4`, modes **24 disengaged / 26 engaged**, so every mode-INDEXED edit
written at modes 0-5 / 10 / 11 / 12 / 14 delivered **byte-stock behaviour**. If the rule's x-axis is
nominal, it was fitted to the wrong x-values.

WHAT IS MODE-INDEXED AND WHAT IS NOT -- the whole point:
  gain_B (r24) FALLBACK LERP   mode-indexed via 0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214 at [mode*4]
  gain_A (r26) FALLBACK LERP   NOT indexed -- four hard-coded records 0xC6A68/0xC6A7C/0xC6A90/0xC6AA4
  the four gated ARMS          NOT indexed -- plain `ld.hu <disp>[tp]` scalars, and when the gate
                               fires they OVERRIDE the LERP unconditionally  => MODE-PROOF
  both `sar` sites             NOT indexed -- one instruction each, applies always => MODE-PROOF

THE LANE, mirroring the decompiled integer arithmetic (V850 is LE; `>>` is arithmetic):

  r24 / gain_B, FUN_0003aa2c
    0x3AA94  ld.bu -0x683c[gp],r15    gate cell. byte @0x3AA96: 0xC5 -> gp-0x683c (DEAD, 0 writers,
                                      reads 0 forever => UNGATED); 0xFB -> gp-0x6806 (the LKAS flag)
    0x3AAA8  setfne lp                lp = (gate != 0)   -- BOTH ladders branch on this
    0x3AAC8  addi -0x32c9,r11         rateKey >= 13001 folds the index to 0 (= MAX gain)
    0x3ABFA..0x3AC16   priority:  gp-0x671d != 0 -> 0xC6442(1024)
                                   gate     != 0 -> 0xC6446           <-- the V67/V68/V71C/V76 arm
                                   cnt >= [0xC64FA byte] -> 0xC6440(2048)
                                   else          -> lerp4(gain_B[mode], rateKey)   <-- mode-indexed
    0x3AC20  sar 0xa,r8               *** V62/V65/V71A: sar 0x9 = x2 ***

  r26 / gain_A, same function
    0x3AB56..0x3AB6C   priority:  gate != 0 -> 0xC6444                 <-- the V67/V68/V71C/V76 arm
                                   cnt >= 5 -> 0xC643E(1536)
                                   else     -> lerp4(gain_A, rateKey)  <-- NOT mode-indexed
    0x3AB76  sar 0xa                  *** V62/V65/V71A: sar 0x9 = x2 ***

⚠ The comparison is always **build-engaged vs stock-engaged at the SAME operating point**, because
that is what the car did versus what it would have done. In the manual arm a gated build is stock by
construction, which is why V71C's manual arm is the corpus's only within-route stock control.
"""
import struct
import sys
from pathlib import Path

FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")

TP, GP = 0xBF000, 0xFEDF8000
SAR_R24, SAR_R26 = 0x3AC20, 0x3AB76       # low byte carries the imm5 shift count
GATE_BYTE = 0x3AA96                        # 0xC5 = dead cell (ungated) / 0xFB = gp-0x6806
ARM_R24_MASK = TP + 0x7442                 # 0xC6442  gp-0x671d != 0   (outranks everything)
ARM_R24_GATE = TP + 0x7446                 # 0xC6446  gate != 0
ARM_R24_CNT = TP + 0x7440                  # 0xC6440  counter >= 5
ARM_R26_GATE = TP + 0x7444                 # 0xC6444  gate != 0
ARM_R26_CNT = TP + 0x743E                  # 0xC643E  counter >= 5
CNT_THRESH = TP + 0x74FA                   # 0xC64FA -- a BYTE cal = 5 (u16 reads 517: the V63 trap)
CROSS_X = TP + 0x7010                      # 0xC6010 vehicle-speed breakpoints, shared by both lanes
PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)     # gain_B, indexed [mode*4]
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)  # gain_A, hard-coded
MODE_MAN, MODE_ENG = 24, 26                # config row 11 TVCA4 -- e012 / e014
SPEED_CTS_PER_KMH = 64.0

# ---- the corpus. `img=None` means "stock code.bin". ---------------------------------------------
IMAGES = {
    "stock":  None,
    "V58":    "_v58_plain_image.bin",
    "V59":    "_v59_plain_image.bin",
    "V61":    "_v61_plain_image.bin",
    "V62":    "_v62_plain_image.bin",
    "V64":    "_v64_plain_image.bin",
    "V65":    "_v65_plain_image.bin",
    "V67":    "_v67_plain_image.bin",
    "V68":    "_v68_plain_image.bin",
    "V69":    "_v69_plain_image.bin",
    "V70":    "_v70_plain_image.bin",
    "V71A":   "_v71a_plain_image.bin",
    "V71B":   "_v71b_plain_image.bin",
    "V71C":   "_v71c_plain_image.bin",
    "V72":    "_v72_plain_image.bin",
    "V73":    "_v73_plain_image.bin",
    "V74":    "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "V75":    "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
    "V76":    "_v76_gate_fb_arm5244_gateprobe_plain_image.bin",
}
# Which route/cache each FLOWN build was measured on (None = never flown).
FLOWN = {"V58": "r2b", "V59": "r2c", "V61": "r31", "V62": "r37", "V64": "r35", "V65": "r3a+r3b",
         "V67": "r47", "V68": "v68", "V69": "r4f", "V70": "r50", "V71B": "r54", "V71C": "r58",
         "V72": "r59", "V73": "r5a", "V74": "r5d"}


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def idiv_trunc(n, d):
    """C / V850 `divq`: truncate toward zero."""
    q = abs(n) // abs(d)
    return -q if (n < 0) != (d < 0) else q


def _lerp4(X, Y, idx):
    """FUN_0003aa2c 0x3ABAC-0x3ABFA: 4-point piecewise-linear, truncating division."""
    if idx <= X[0]:
        return Y[0]
    if idx >= X[3]:
        return Y[3]
    k = 0
    while idx >= X[k + 1]:
        k += 1
    return Y[k] + idiv_trunc((Y[k + 1] - Y[k]) * (idx - X[k]), X[k + 1] - X[k])


class Build:
    """One image's rate lane, every constant byte-read little-endian."""

    def __init__(self, name, buf):
        self.name, self.buf = name, buf
        self.sar24 = buf[SAR_R24] & 0x1F
        self.sar26 = buf[SAR_R26] & 0x1F
        self.gate_byte = buf[GATE_BYTE]
        assert self.gate_byte in (0xC5, 0xFB), f"{name}: gate byte 0x{self.gate_byte:02X}"
        self.gated = self.gate_byte == 0xFB
        self.arm24_mask = u16(buf, ARM_R24_MASK)
        self.arm24_gate = u16(buf, ARM_R24_GATE)
        self.arm24_cnt = u16(buf, ARM_R24_CNT)
        self.arm26_gate = u16(buf, ARM_R26_GATE)
        self.arm26_cnt = u16(buf, ARM_R26_CNT)
        self.cnt_thresh = buf[CNT_THRESH]
        self.cross = list(struct.unpack_from("<4h", buf, CROSS_X))
        self.recB = {}
        for m in (MODE_MAN, MODE_ENG, 10, 11):
            ptrs = [u32(buf, p + 4 * m) for p in PTR_ARRAYS]
            self.recB[m] = ([list(struct.unpack_from("<4h", buf, r + 2)) for r in ptrs],
                            [list(struct.unpack_from("<4h", buf, r + 0x0A)) for r in ptrs], ptrs)
        self.recA = ([list(struct.unpack_from("<4h", buf, r + 2)) for r in RATE_A_RECORDS],
                     [list(struct.unpack_from("<4h", buf, r + 0x0A)) for r in RATE_A_RECORDS],
                     list(RATE_A_RECORDS))

    # -- FUN_0003ad74: speed-interpolate the four records into the RAM LERP table ------------------
    def _ram_table(self, rec, speed_cts):
        X4, Y4, _ = rec
        k = 0
        while k <= 3 and self.cross[k] <= speed_cts:
            k += 1
        if k == 0:
            return list(X4[0]), list(Y4[0])
        if k > 3:
            return list(X4[3]), list(Y4[3])
        num, den = speed_cts - self.cross[k - 1], self.cross[k] - self.cross[k - 1]
        lo, hi = k - 1, k
        X = [X4[lo][i] + idiv_trunc((X4[hi][i] - X4[lo][i]) * num, den) for i in range(4)]
        Y = [Y4[lo][i] + idiv_trunc((Y4[hi][i] - Y4[lo][i]) * num, den) for i in range(4)]
        return X, Y

    def _idx(self, rate_key):
        return 0 if rate_key >= 13001 else rate_key      # 0x3AAC8 fold -> index 0 = MAX gain

    def gain24(self, speed_cts, rate_key, engaged, mask671d=0, cnt671a=0):
        if mask671d:
            return self.arm24_mask
        if self.gated and engaged:
            return self.arm24_gate
        if cnt671a >= self.cnt_thresh:
            return self.arm24_cnt
        mode = MODE_ENG if engaged else MODE_MAN
        X, Y = self._ram_table(self.recB[mode], speed_cts)
        return _lerp4(X, Y, self._idx(rate_key))

    def gain26(self, speed_cts, rate_key, engaged, cnt671a=0):
        if self.gated and engaged:
            return self.arm26_gate
        if cnt671a >= self.cnt_thresh:
            return self.arm26_cnt
        X, Y = self._ram_table(self.recA, speed_cts)
        return _lerp4(X, Y, self._idx(rate_key))

    # -- what the lane's SLOPE actually is, gain folded together with the shift -------------------
    def slope24(self, speed_cts, rate_key, engaged, **kw):
        return self.gain24(speed_cts, rate_key, engaged, **kw) / (1 << self.sar24)

    def slope26(self, speed_cts, rate_key, engaged, **kw):
        return self.gain26(speed_cts, rate_key, engaged, **kw) / (1 << self.sar26)


def load_all(names=None):
    out = {}
    for n, f in IMAGES.items():
        if names and n not in names:
            continue
        p = (FW / "stock_fw_dump" / "code.bin") if f is None else (FW / f)
        out[n] = Build(n, p.read_bytes())
    return out


def delivered(b, stock, speed_kmh, rate_key, engaged=True):
    """(r24 x, r26 x) delivered vs STOCK at the SAME operating point and the SAME arm."""
    sc = int(round(speed_kmh * SPEED_CTS_PER_KMH))
    s24 = stock.slope24(sc, rate_key, engaged)
    s26 = stock.slope26(sc, rate_key, engaged)
    return (b.slope24(sc, rate_key, engaged) / s24, b.slope26(sc, rate_key, engaged) / s26)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    B = load_all()
    st = B["stock"]
    print(f"{'build':6s} {'sar24':>5s} {'sar26':>5s} {'gate':>5s} {'C6446':>6s} {'C6444':>6s} "
          f"{'C6442':>6s} {'C6440':>6s} {'C643E':>6s}")
    for n, b in B.items():
        print(f"{n:6s} {b.sar24:5d} {b.sar26:5d} {'0x%02X' % b.gate_byte:>5s} {b.arm24_gate:6d} "
              f"{b.arm26_gate:6d} {b.arm24_mask:6d} {b.arm24_cnt:6d} {b.arm26_cnt:6d}")
