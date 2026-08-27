#!/usr/bin/env python3
"""V70 -- the r24 rate lane's EXACT gain, as a function of vehicle speed and rate, per build.

Mirrors the decompiled integer arithmetic of `FUN_0003aa2c` (the 1 kHz aggregator, task 1) and
`FUN_0003ad74` (the speed-interpolating B-bank table loader) instruction-for-instruction. Every
constant is byte-read little-endian from the image; nothing is taken from a design doc.

    gp = 0xFEDF8000    tp = 0xBF000        (tp+0x7446 = 0xC6446, anchored below)

THE LANE, hop by hop (addresses are stock `code.bin`; V850E2 has no delay slots)
------------------------------------------------------------------------------
  0x3AA94  ld.bu -0x683c[gp],r15        gate cell.  V67/V68 repoint this to -0x6806 (1-byte edit
                                        at 0x3AA96, 0xC5 <-> 0xFB).  gp-0x683c has 0 WRITERS.
  0x3AAA8  setfne lp                    lp = (gate != 0)
  0x3AA70  ld.bu -0x671a[gp],r12        oscillation-reversal counter
  0x3AA78  ld.bu 0x74fa[tp],r14         [0xC64FA] = 5
  0x3AA7C  cmp r14,r12 / bc             r2 = (counter >= 5)
  0x3AA9C  ld.h  -0x4f62[gp],r14        dt_raw  = torque-rate (the lane INPUT)
  0x3AAAC..0x3AAC0                      r1 = clamp(dt_raw, -0x1400, +0x1400)   (+/-5120)
  0x3AAC4  ld.hu -0x6ac0[gp],r11        rateKey = motor-resolver rate magnitude (u16)
  0x3AAC8  addi -0x32c9,r11,r0          CY <=> rateKey >= 13001
  0x3AACC  cmovc 0x0,r11,r13            r13 = CY ? 0 : rateKey     <-- FOLD to index 0 = MAX gain
  0x3ABA0  sxh r13
  0x3AB9C..0x3ABFA                      r10 = lerp4(Xram[gp-0x6e40..], Yram[gp-0x6e38..], r13)
                                        Xram/Yram are written every tick by FUN_0003ad74, which
                                        LINEARLY INTERPOLATES IN VEHICLE SPEED between two of the
                                        four mode-indexed records (mode 10 -> 0xD2A74 / 0xD2AB0 /
                                        0xD2AEC / 0xD2B28, via pointer arrays 0xCBF5C / 0xCC044 /
                                        0xCC12C / 0xCC214 at index mode*4).
  0x3ABFE  ld.hu 0x7442[tp],r10         ARM 1: gp-0x671d != 0  -> [0xC6442] = 1024
  0x3AC08  ld.hu 0x7446[tp],r10         ARM 2: gate       != 0 -> [0xC6446] = 512 stock / 5244 V67-68
  0x3AC12  ld.hu 0x7440[tp],r10         ARM 3: counter   >= 5  -> [0xC6440] = 2048
                                        ARM 4 (fallthrough)    -> the LERP above  <-- the DEFAULT
  0x3AC18  mul r10,r8,r0                r8 = dt * gain          (32-bit, high word discarded to r0)
  0x3AC20  sar 0xa,r8                   >> 10.  *** V62/V65 make this `sar 0x9` (>> 9) = x2 ***
  0x3AC24..0x3AC3C                      +/-3 deadzone, cal [0xC61F6] = 3
  0x3AC3E  mul r14,r6,r0                r14 = ld.b gp-0x6752 polarity
  0x3AC42..0x3AC54                      r24 = clamp(., -0x2000, +0x2000)   *** SATURATING +/-8192 ***
  0x3ACCA  add r24,r6                   into the aggregator sum
  0x3AD5A  st.h r24,-0x6ada[gp]         mirror to RAM (0 readers / 1 writer -- V69's probe bit6)

Usage:  python studies/sessions/v70/v70_rate_lane_gain_model.py
"""
import math
import struct
import sys
from pathlib import Path

ROOT = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
BUILDS = ("stock", "v62", "v65", "v66", "v67", "v68", "v69")

# ---- addresses, all byte-read; none hard-coded as values -----------------------------------------
TP = 0xBF000
GP = 0xFEDF8000
SAR_R24 = 0x3AC20                  # hw: 0x42AA = sar 0xa,r8 ; 0x42A9 = sar 0x9,r8
GATE_BYTE = 0x3AA96
ARM1, ARM2, ARM3 = TP + 0x7442, TP + 0x7446, TP + 0x7440    # 0xC6442 / 0xC6446 / 0xC6440
DEADZONE = TP + 0x71F6                                       # 0xC61F6
CNT_THRESH = TP + 0x74FA                                     # 0xC64FA
CROSS_X = TP + 0x7010                                        # 0xC6010, vehicle-speed breakpoints
PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)            # FUN_0003ad74 aiStack_14[1..3]+psStack_4
MODE = 10                                                    # PN 39990-TVA-A160 -> config index 10
CLIP = 0x2000                                                # +/-8192, the r24 saturating clamp
DT_CLAMP = 0x1400                                            # +/-5120, the input clamp @0x3AAAC
SPEED_CTS_PER_KMH = 64.0                                     # gp-0x6a5e scale (memory: voted speed)


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def idiv_trunc(n, d):
    """C integer division: truncate toward zero. V850 `divq` does the same."""
    q = abs(n) // abs(d)
    return -q if (n < 0) != (d < 0) else q


class Build:
    def __init__(self, name, buf):
        self.name = name
        self.buf = buf
        self.sar = 10 if u16(buf, SAR_R24) == 0x42AA else 9       # 0x42A9 == sar 0x9
        assert u16(buf, SAR_R24) in (0x42AA, 0x42A9), f"{name}: unexpected sar hw"
        self.gate_live = buf[GATE_BYTE] == 0xFB                    # 0xFB -> gp-0x6806, 0xC5 -> -0x683c
        self.arm1, self.arm2, self.arm3 = (u16(buf, a) for a in (ARM1, ARM2, ARM3))
        self.dz = u16(buf, DEADZONE)
        self.cross = list(struct.unpack_from("<4h", buf, CROSS_X))
        self.recs = [u32(buf, p + 4 * MODE) for p in PTR_ARRAYS]
        self.X = [list(struct.unpack_from("<4h", buf, r + 2)) for r in self.recs]
        self.Y = [list(struct.unpack_from("<4h", buf, r + 0x0A)) for r in self.recs]
        self.cnt = [s16(buf, r) for r in self.recs]

    # --- FUN_0003ad74: write the RAM LERP tables gp-0x6e40 (X) / gp-0x6e38 (Y) ---------------------
    def ram_table(self, speed_cts):
        k = 0
        while k <= 3 and self.cross[k] <= speed_cts:
            k += 1
        if k == 0:                                     # speed below Xcross[0]: copy record 0
            return list(self.X[0]), list(self.Y[0])
        if k > 3:                                      # speed at/above Xcross[3]: copy record 3
            return list(self.X[3]), list(self.Y[3])
        num = speed_cts - self.cross[k - 1]            # iVar7
        den = self.cross[k] - self.cross[k - 1]        # iVar10
        lo, hi = k - 1, k
        Xr = [self.X[lo][i] + idiv_trunc((self.X[hi][i] - self.X[lo][i]) * num, den) for i in range(4)]
        Yr = [self.Y[lo][i] + idiv_trunc((self.Y[hi][i] - self.Y[lo][i]) * num, den) for i in range(4)]
        return Xr, Yr

    # --- FUN_0003aa2c 0x3AB9C-0x3ABFA: 4-point piecewise-linear on the rate axis -------------------
    @staticmethod
    def lerp4(X, Y, idx):
        if idx <= X[0]:                                # 0x3ABAC cmp / 0x3ABB2 bgt not taken
            return Y[0]
        if idx >= X[3]:                                # 0x3ABBE cmp / 0x3ABC0 bge taken
            return Y[3]
        k = 0
        while idx >= X[k + 1]:                         # 0x3ABD2 loop
            k += 1
        return Y[k] + idiv_trunc((Y[k + 1] - Y[k]) * (idx - X[k]), X[k + 1] - X[k])

    # --- the 4-way priority gate @0x3ABFA-0x3AC16 --------------------------------------------------
    def gain(self, speed_cts, rate_raw, gate671d=0, counter671a=0, engaged=True):
        idx = 0 if rate_raw >= 13001 else rate_raw     # 0x3AAC8 fold; rateKey is u16
        if gate671d != 0:
            return self.arm1                           # 1024
        gate = (engaged if self.gate_live else False)  # gp-0x6806 when repointed; gp-0x683c has 0 writers
        if gate:
            return self.arm2                           # 512 stock / 5244 on V67-V68
        if counter671a >= self.buf[CNT_THRESH]:
            return self.arm3                           # 2048
        X, Y = self.ram_table(speed_cts)
        return self.lerp4(X, Y, idx)

    # --- the full lane, exactly as the instructions run it -----------------------------------------
    def lane_out(self, dt_raw, speed_cts, rate_raw, polarity=1, **kw):
        dt = max(-DT_CLAMP, min(DT_CLAMP, dt_raw))                    # 0x3AAAC-0x3AAC0
        g = self.gain(speed_cts, rate_raw, **kw)
        p = (dt * g) >> self.sar if dt * g >= 0 else -((-(dt * g)) >> self.sar)
        p = (dt * g) // (1 << self.sar) if False else _sar(dt * g, self.sar)   # arithmetic shift
        dz = self.dz
        r6 = p - dz if p > dz else (p + dz if p < -dz else 0)          # 0x3AC24-0x3AC3C
        v = r6 * polarity                                             # 0x3AC3E
        return max(-CLIP, min(CLIP, v))                               # 0x3AC42-0x3AC54

    def slope(self, speed_cts, rate_raw, **kw):
        """d(out)/d(dt) in the linear region = gain / 2^sar."""
        return self.gain(speed_cts, rate_raw, **kw) / (1 << self.sar)

    def rail_dt(self, speed_cts, rate_raw, **kw):
        """Smallest |dt_raw| at which the +/-8192 clip engages (None if unreachable)."""
        g = self.gain(speed_cts, rate_raw, **kw)
        need = (CLIP + self.dz) << self.sar            # |dt*g| must reach (8192+3)<<sar
        dt = math.ceil(need / g)
        return dt if dt <= DT_CLAMP else None


def _sar(x, n):
    """V850 `sar` = arithmetic right shift; Python >> on a negative int is already arithmetic."""
    return x >> n


def describing_fn(K, L, A):
    """Sinusoidal-input describing function of a symmetric saturation, slope K, limit L."""
    if K * A <= L:
        return K
    r = L / (K * A)
    return K * (2.0 / math.pi) * (math.asin(r) + r * math.sqrt(1.0 - r * r))


def main():
    imgs = {}
    imgs["stock"] = (ROOT / "stock_fw_dump" / "code.bin").read_bytes()
    for v in BUILDS[1:]:
        imgs[v] = (ROOT / f"_{v}_plain_image.bin").read_bytes()
    B = {k: Build(k, v) for k, v in imgs.items()}

    print("=" * 108)
    print("PART 0 -- what each image actually contains (all byte-read LE)")
    print("=" * 108)
    print(f"{'build':7s} {'sar@0x3AC20':>12s} {'gate@0x3AA96':>13s} {'gate cell':>11s} "
          f"{'arm1 C6442':>11s} {'arm2 C6446':>11s} {'arm3 C6440':>11s} {'dz C61F6':>9s}")
    for n in BUILDS:
        b = B[n]
        print(f"{n:7s} {'sar 0x%x' % b.sar:>12s} {'0x%02X' % b.buf[GATE_BYTE]:>13s} "
              f"{'gp-0x6806' if b.gate_live else 'gp-0x683c':>11s} "
              f"{b.arm1:11d} {b.arm2:11d} {b.arm3:11d} {b.dz:9d}")
    s = B["stock"]
    print(f"\n  mode-{MODE} record pointers (FUN_0003ad74, arrays "
          f"{', '.join('0x%05X' % p for p in PTR_ARRAYS)} at index mode*4):")
    for i, r in enumerate(s.recs):
        print(f"    P{i} -> 0x{r:05X}  cnt={s.cnt[i]}  X={s.X[i]}  Y={s.Y[i]}")
    print(f"  V69 same records:")
    for i, r in enumerate(B['v69'].recs):
        tag = "  <<< EDITED" if B['v69'].Y[i] != s.Y[i] else ""
        print(f"    P{i} -> 0x{r:05X}  cnt={B['v69'].cnt[i]}  X={B['v69'].X[i]}  "
              f"Y={B['v69'].Y[i]}{tag}")
    print(f"  vehicle-speed cross axis 0xC6010 = {s.cross} counts "
          f"= {[round(c / SPEED_CTS_PER_KMH, 2) for c in s.cross]} km/h")

    # ------------------------------------------------------------------------------------------
    speeds = [0, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100]
    scenarios = [
        ("stock", "stock", dict(engaged=True)),
        ("V62", "v62", dict(engaged=True)),
        ("V65", "v65", dict(engaged=True)),
        ("V66", "v66", dict(engaged=True)),
        ("V67 engaged", "v67", dict(engaged=True)),
        ("V67 manual", "v67", dict(engaged=False)),
        ("V68 engaged", "v68", dict(engaged=True)),
        ("V68 manual", "v68", dict(engaged=False)),
        ("V69 engaged", "v69", dict(engaged=True)),
        ("V69 manual", "v69", dict(engaged=False)),
    ]

    for rate in (0, 400, 700, 900, 1200, 1500, 3000, 13001):
        print()
        print("=" * 108)
        seg = ("FLAT segment Y[0]==Y[1]" if rate <= 400 else
               "FOLD -> index 0 (MAX gain)" if rate >= 13001 else
               "interpolated on the rate axis")
        print(f"PART 1 -- rate-lane gain as a MULTIPLE OF STOCK   |  rateKey (gp-0x6ac0) = {rate}"
              f"   [{seg}]")
        print(f"   ({rate} counts = {rate / 4.7121:.1f} deg/s on repo scale A, "
              f"{rate / 0.58901:.0f} deg/s on scale B)")
        print("=" * 108)
        hdr = f"{'scenario':14s}" + "".join(f"{k:>8d}" for k in speeds)
        print(hdr.replace("scenario", "scenario  km/h"))
        base = {}
        for kmh in speeds:
            sc = int(round(kmh * SPEED_CTS_PER_KMH))
            base[kmh] = B["stock"].slope(sc, rate, engaged=True)
        for label, bn, kw in scenarios:
            row = []
            for kmh in speeds:
                sc = int(round(kmh * SPEED_CTS_PER_KMH))
                row.append(B[bn].slope(sc, rate, **kw) / base[kmh])
            print(f"{label:14s}" + "".join(f"{v:8.3f}" for v in row))
        print(f"{'-- stock abs':14s}" + "".join(f"{base[k]:8.3f}" for k in speeds)
              + "   (absolute slope, counts-out per count-of-dt)")

    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 108)
    print("PART 2 -- SATURATION: smallest |dt_raw| (gp-0x4f62) that engages the +/-8192 clip")
    print("=" * 108)
    print("   repo-recorded max |dtorque| = 839 ; the two V68 routes measured 511 ;"
          " the 28 Hz burst itself 254")
    print(f"{'scenario':14s}" + "".join(f"{k:>8d}" for k in speeds))
    for label, bn, kw in scenarios:
        row = []
        for kmh in speeds:
            sc = int(round(kmh * SPEED_CTS_PER_KMH))
            r = B[bn].rail_dt(sc, 0, **kw)
            row.append("  never" if r is None else f"{r:7d}")
        print(f"{label:14s}" + "".join(f"{v:>8s}" for v in row))
    print("   (rateKey = 0, i.e. the flat segment = the worst case = the largest gain)")

    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 108)
    print("PART 3 -- DESCRIBING-FUNCTION gain of the r24 lane vs oscillation amplitude, at CREEP")
    print("=" * 108)
    print("   static nonlinearity => zero phase; N(A) is the equivalent LINEAR gain seen by a")
    print("   sinusoid of amplitude A in dt (gp-0x4f62 counts).  L = 8192.")
    amps = [100, 254, 366, 511, 619, 731, 839, 1200, 1600, 2400, 3200, 5120]
    cases = [("stock", "stock", dict(engaged=True)),
             ("V62 (x2)", "v62", dict(engaged=True)),
             ("V67 engaged", "v67", dict(engaged=True)),
             ("V69 (x4)", "v69", dict(engaged=True))]
    print(f"{'A (dt counts)':14s}" + "".join(f"{a:>9d}" for a in amps))
    Ns = {}
    for label, bn, kw in cases:
        K = B[bn].slope(0, 0, **kw)
        Ns[label] = [describing_fn(K, CLIP, a) for a in amps]
        print(f"{label:14s}" + "".join(f"{v:9.3f}" for v in Ns[label]))
    print(f"{'V69 / V62':14s}" + "".join(f"{Ns['V69 (x4)'][i] / Ns['V62 (x2)'][i]:9.3f}"
                                         for i in range(len(amps))))
    print(f"{'V69 / stock':14s}" + "".join(f"{Ns['V69 (x4)'][i] / Ns['stock'][i]:9.3f}"
                                           for i in range(len(amps))))
    print("\n   asymptote as A -> inf: N -> 4L/(pi*A), IDENTICAL for every build "
          "(saturation, not gain, dominates)")
    print("   monotonicity: N(A) = (L/A)*u*f(1/u) with u = K*A/L is strictly increasing in K,")
    print("   so a LARGER K never yields a SMALLER N at the same A.")

    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 108)
    print("PART 4 -- the rate-axis SHAPE: V69's boost decays with rateKey, V62's did not")
    print("=" * 108)
    rates = [0, 200, 400, 500, 700, 900, 1100, 1300, 1400, 1500, 2000, 2500, 3000, 4000]
    for kmh in (0, 5, 10, 20, 30):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        print(f"\n  vehicle speed {kmh:3d} km/h ({sc} counts)")
        print(f"    {'rateKey':10s}" + "".join(f"{r:>8d}" for r in rates))
        st = [B["stock"].slope(sc, r, engaged=True) for r in rates]
        print(f"    {'stock abs':10s}" + "".join(f"{v:8.3f}" for v in st))
        for label, bn, kw in (("V62 xStock", "v62", dict(engaged=True)),
                              ("V67 xStock", "v67", dict(engaged=True)),
                              ("V69 xStock", "v69", dict(engaged=True))):
            row = [B[bn].slope(sc, r, **kw) / st[i] for i, r in enumerate(rates)]
            print(f"    {label:10s}" + "".join(f"{v:8.3f}" for v in row))

    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 108)
    print("PART 5 -- END-TO-END lane output, integer-exact, at a few operating points")
    print("=" * 108)
    print(f"{'dt':>6s} {'speed':>6s} {'rate':>6s} | " +
          " ".join(f"{n:>9s}" for n, _, _ in scenarios[:1] + scenarios[1:]))
    for dt, kmh, rate in ((100, 0, 0), (254, 0, 100), (511, 5, 300), (839, 5, 300),
                          (839, 5, 900), (839, 5, 1500), (1400, 10, 200), (3218, 5, 400),
                          (511, 60, 300), (839, 90, 300)):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        outs = [B[bn].lane_out(dt, sc, rate, **kw) for _, bn, kw in scenarios]
        print(f"{dt:6d} {kmh:6d} {rate:6d} | " + " ".join(f"{o:9d}" for o in outs))
    print("   columns: " + ", ".join(n for n, _, _ in scenarios))

    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 108)
    print("PART 6 -- the RATE-AXIS describing function: V69's gain is AMPLITUDE-DEPENDENT, V62's was not")
    print("=" * 108)
    print("""   During an oscillation at f, BOTH the lane input dt (gp-0x4f62) and the gain index
   rateKey (gp-0x6ac0, |motor rate|) oscillate at f. At a resonance they are near-quadrature-or-phase
   locked; the physically-forced case is that the gain index is LARGE exactly when the lane input is
   large. V69's gain FALLS with rateKey, so its effective gain FALLS with oscillation amplitude --
   the classic destabilising (negative-slope) describing function. V62's `sar` edit was a constant
   factor: amplitude-INDEPENDENT by construction.

   Model, mirroring the instructions: dt(t) = A_dt*sin(wt) [clamped +/-5120 @0x3AAAC];
   rateKey(t) = A_rk*|sin(wt + phi)| [ld.hu, so unsigned = a magnitude]; the lane runs the real
   integer chain each sample and the fundamental is extracted by a Fourier integral.
   phi = 0 is the in-phase (worst) case; phi = pi/2 is quadrature. Both shown.""")

    def lane_df(b, A_dt, A_rk, kmh, phi, kw, n=2048):
        """Fundamental-component gain N = (2/(pi*A)) * integral(out(t)*sin(wt) dt) / A_dt."""
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        acc = 0.0
        for i in range(n):
            th = 2.0 * math.pi * i / n
            dt = int(round(A_dt * math.sin(th)))
            rk = int(round(abs(A_rk * math.sin(th + phi))))
            acc += b.lane_out(dt, sc, rk, **kw) * math.sin(th)
        return (2.0 / n) * acc / A_dt

    for kmh in (0, 5, 10):
        for phi_lbl, phi in (("in-phase", 0.0), ("quadrature", math.pi / 2)):
            print(f"\n  speed {kmh} km/h, gain index {phi_lbl}; "
                  f"columns = rateKey amplitude A_rk (counts)")
            arks = [0, 200, 400, 700, 1000, 1400, 2000, 3000, 5000]
            print(f"    {'A_dt':>6s} {'build':10s}" + "".join(f"{a:>9d}" for a in arks))
            for A_dt in (366, 511, 731, 1200):
                rows = {}
                for lbl, bn, kw in (("stock", "stock", dict(engaged=True)),
                                    ("V62", "v62", dict(engaged=True)),
                                    ("V69", "v69", dict(engaged=True))):
                    rows[lbl] = [lane_df(B[bn], A_dt, a, kmh, phi, kw) for a in arks]
                for lbl in ("stock", "V62", "V69"):
                    print(f"    {A_dt:6d} {lbl:10s}" + "".join(f"{v:9.3f}" for v in rows[lbl]))
                print(f"    {'':6s} {'V69/V62':10s}"
                      + "".join(f"{rows['V69'][i] / rows['V62'][i]:9.3f}" for i in range(len(arks))))

    # ------------------------------------------------------------------------------------------
    print()
    print("=" * 108)
    print("PART 7 -- WHERE IS V69 WEAKER THAN V62?  (static gain ratio V69/V62, no oscillation model)")
    print("=" * 108)
    print("   < 1.000 => V69 delivers LESS rate-lane damping than the build that fixed grind #1.")
    print("   STATE.md measured operating points: grind #1 rateKey ~603 | creep grind #2 ~1206 |")
    print("   highway ~141-198.  Marked * below.")
    rates = [0, 200, 400, 603, 800, 1000, 1206, 1400, 1500, 2000, 3000]
    print(f"    {'km/h':>5s}" + "".join(f"{r:>8d}" for r in rates))
    for kmh in (0, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        row = [B["v69"].slope(sc, r, engaged=True) / B["v62"].slope(sc, r, engaged=True) for r in rates]
        print(f"    {kmh:5d}" + "".join(f"{v:8.3f}" for v in row))
    print(f"\n    same, V69 / V67-engaged (the build actually on the car before V69):")
    print(f"    {'km/h':>5s}" + "".join(f"{r:>8d}" for r in rates))
    for kmh in (0, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        row = [B["v69"].slope(sc, r, engaged=True) / B["v67"].slope(sc, r, engaged=True) for r in rates]
        print(f"    {kmh:5d}" + "".join(f"{v:8.3f}" for v in row))


if __name__ == "__main__":
    sys.exit(main())
