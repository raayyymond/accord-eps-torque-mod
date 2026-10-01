"""
angle_signal_mirror.py -- byte-exact Python mirror of the EPS steering-angle signal gp-0x6a00 and its
1 kHz inputs, for the 2020 Accord EPS (39990-TVA-A160, Renesas V850E2, little-endian).

Trace note: docs/traces/TRACE-2026-09-30-angle-signal-gp6a00.md
Program used: stock code.bin (GhidraMCP), every function below is byte-identical in the V295 image
(checked by Python slice compare, see the trace note).

WHAT RUNS WHERE (EVIDENCE, see trace note section 1)
  task slot 0  FUN_0002214a  every tick (1 kHz)          -> FUN_0006bb08 (raw motor position snapshot)
                                                           -> FUN_0003bd7c @0x2224a  (gp-0x6cc4, gp-0x69d0,
                                                              gp-0x69d4, gp-0x69ca, gp-0x67fe)
                                                           -> FUN_00028ea6 @0x22522  (the LKAS rate PID)
  task slot 4  FUN_00022ca0  when (tick counter % 10) == 4 (100 Hz)
                                                           -> FUN_0003f776 @0x22de2  (gp-0x6a56, angle rate)
                                                           -> FUN_0003e6d8 @0x22e32  (gp-0x6a00, THIS signal)
                                                           -> FUN_000413ae @0x22e9c -> FUN_00040a50 (0x14A pack)
  Slot 0 has priority byte 6, slot 4 has priority byte 2 (TCB words at 0xBB924 / 0xBB9E4), and slot 0 is
  activated first in the same dispatcher pass (FUN_00014be4), so on an activation tick the PID runs
  BEFORE the angle is refreshed. The PID-side age of gp-0x6a00 is therefore 1..10 ticks (BELIEF on the
  upper end: assumes slot 4 reaches 0x22e32 before the next tick; it is preemptible).

All integer operations mirror V850E2 semantics: 32-bit wrap on mul/shl/add, arithmetic sar, divq
truncates toward zero, st.h keeps the low 16 bits, sxh sign-extends. Each line carries its address.
Constants are read little-endian from the image; tp = 0xBF000, so tp+0x7892 = 0xC6892.

Run:  python angle_signal_mirror.py            (stock image)
      python angle_signal_mirror.py v295       (V295 image)
"""
import os
import struct
import sys

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", r"C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMAGES = {
    "stock": ROOT + "/analysis-2020accord/stock_fw_dump/code.bin",
    "v295": ROOT + "/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE"
                   ".2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
}
TP = 0xBF000

# ---------------------------------------------------------------------------------------- integer helpers
def i32(x):
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x

def i16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x

def divq(a, b):
    """V850E2 divq: signed quotient, truncated toward zero (remainder discarded, reg3 = r0)."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q

def mulh(a, b):
    """mulh reg1,reg2: low 16 bits of each, signed, 32-bit product."""
    return i16(a) * i16(b)


# ---------------------------------------------------------------------------------------- calibration
class Cal:
    def __init__(self, image="stock"):
        b = open(IMAGES[image], "rb").read()
        h = lambda off: struct.unpack_from("<h", b, TP + off)[0]
        H = lambda off: struct.unpack_from("<H", b, TP + off)[0]
        self.image = image
        self.X = [h(0x7892 + 2 * i) for i in range(8)]   # 0xC6892..0xC68A0  LERP X knots (int16)
        self.Y = [h(0x78A2 + 2 * i) for i in range(8)]   # 0xC68A2..0xC68B0  LERP Y knots (int16)
        self.k7432 = H(0x7432)                           # 0xC6432 = 900   (ld.hu)
        self.k713a = H(0x713A)                           # 0xC613A = 1159  (ld.hu)
        self.k74f2 = b[TP + 0x74F2]                      # 0xC64F2 = 128   (ld.bu, Q7 unity)
        self.k7358 = H(0x7358)                           # 0xC6358 = 2     (offset bleed per tick)
        self.k72a2 = H(0x72A2)                           # 0xC62A2 = 100   (FUN_0003e87a reset dwell)
        # anchor: V295 records b 0xC63EA 567->1050; stock reads 1560. Guards the tp offset.
        self.anchor_c63ea = H(0x73EA)


# ---------------------------------------------------------------------------------------- FUN_0003e600
def fun_3e600(x, cal, ram):
    """Odd-symmetric 8-knot LERP of (|x|*45)>>9. Side effect: writes gp-0x69dc (the LERP index)."""
    neg = x < 0                                    # 0x3E600 cmp r0,r6  (flags survive the mul)
    r6 = i32(x * 0x2D)                             # 0x3E602 mul 0x2d,r6,r0
    if neg:                                        # 0x3E606 blt 0x3E66C
        r6 = i32(0 - r6)                           # 0x3E66C subr r0,r6
    r6 = r6 >> 9                                   # 0x3E60C / 0x3E672 sar 0x9,r6
    ram["gp-0x69dc"] = i16(r6)                     # 0x3E60E / 0x3E674 st.h r6,-0x69dc[gp]
    X = i16(r6)                                    # 0x3E612 / 0x3E678 sxh r6
    Xs, Ys = cal.X, cal.Y
    if not X > Xs[0]:                              # 0x3E620 cmp r9,r6 ; bgt
        y = Ys[0]                                  # 0x3E624 ld.h 0x78a2[tp]
    elif X >= Xs[7]:                               # 0x3E62E cmp r7,r6 ; bge
        y = Ys[7]                                  # 0x3E63C ld.h 0x78b0[tp]
    else:
        k = 1                                      # 0x3E632.. walk: first knot with X < X[k]
        while X >= Xs[k]:
            k += 1
        dy = Ys[k] - Ys[k - 1]                     # 0x3E658 sub r16,r10
        dx = X - Xs[k - 1]                         # 0x3E65C sub r8,r6
        y = divq(i32(dy * dx), Xs[k] - Xs[k - 1]) + Ys[k - 1]   # 0x3E65E mul / 0x3E664 divq / 0x3E668 add
    if neg:
        y = 0 - y                                  # 0x3E6D0 mov r0,r10 ; sub r8,r10
    return i16(y)                                  # 0x3E6D4 sxh r10


# ---------------------------------------------------------------------------------------- FUN_0003bd7c
def fun_3bd7c_angle(ram, cal):
    """The angle portion of FUN_0003bd7c (task slot 0, every tick, phase mask 0xd38). 0x3BEE0-0x3C09E."""
    pol = ram["gp-0x6752"]
    r26 = ram["gp-0x4ee8"]                         # 0x3BEE4 ld.h -0x4ee8[gp],r26   (12-bit motor position)
    if ram["gp-0x3614"] == 1:                      # 0x3BEE8 cmp 0x1,r8
        r28 = i16(r26 - ram["gp-0x69d2"])          # 0x3BEF0 subr r26,r28 ; sxh
        if r28 + 0x800 < 0:                        # 0x3BEF4 addi 0x800,r28,r0 ; bge
            r28 = i16(r28 + 0x1000)                # 0x3BEFA
        elif r28 - 0x800 > 0:                      # 0x3BF02 addi -0x800,r28,r0 ; ble
            r28 = i16(r28 - 0x1000)                # 0x3BF08
        r28 = i32(r28 + ram["gp-0x6cc4"])          # 0x3BF12 add r16,r28
    else:
        if ram["gp-0x6772"] != 0:                  # 0x3BF2E FOC mode byte
            ram["gp-0x3614"] = 1                   # 0x3BF34
        r28 = 0                                    # 0x3BF38
    ram["gp-0x6cc4"] = r28                         # 0x3BF46 st.w (shadow gp-0x4d0c)
    ram["gp-0x69d2"] = r26                         # 0x3BF64 st.h
    if ram["gp-0x67fe"] in (1, 2):                 # 0x3BF7A / 0x3BF7E
        r10 = ram["gp-0x69d0"]                     # 0x3BF8A ld.h
        if not cal.k7358 > r10:                    # 0x3BF92 cmp r10,r16 ; bgt
            r10 = i16(r10 - cal.k7358)             # 0x3BF9A subr r10,r15 ; sxh   (bleed toward 0)
        elif -cal.k7358 < r10:                     # 0x3BFB4 cmp r10,r13 ; blt
            r10 = 0                                # 0x3BFEA st.h r0
        else:
            r10 = i16(r10 + cal.k7358)             # 0x3BFBC add r10,r11 ; sxh
        ram["gp-0x69d0"] = r10                     # 0x3BFA4 / 0x3BFC6 / 0x3BFEA
        r28 = i32(ram["gp-0x6cc4"] - r10)          # 0x3BFE2 sub r10,r28
        r26 = r28 >> 3                             # 0x3C00A sar 0x3,r26
        r26 = i32(r26 * cal.k713a)                 # 0x3C00C mul r9,r26,r0
        r26 = r26 >> 8                             # 0x3C014 sar 0x8,r26
        r26 = i32(r26 * cal.k7432)                 # 0x3C016 mul r7,r26,r0
        r26 = r26 >> 14                            # 0x3C022 sar 0xe,r26
        r26 = i32(r26 * pol)                       # 0x3C024 mul r16,r26,r0
        ram["gp-0x69d4"] = i16(r26)                # 0x3C030 st.h (sxh at 0x3C02C)
        r25 = ram["gp+0x6470"]                     # 0x3C072 ld.h 0x6470[gp],r25   (absolute baseline)
        if r25 == 0x7FFF:                          # 0x3C076 addi -0x7fff,r25,r0 ; cmove 0,r25,r25
            r25 = 0                                # NOTE: the -0x8000 "never established" sentinel is NOT excluded
        ram["gp-0x69ca"] = i16(i32(r25 + r26))     # 0x3C090 add r26,r25 ; 0x3C09A st.h (32-bit r26, not the sxh copy)
    else:
        ram["gp-0x69ca"] = 0                       # 0x3C12A
        ram["gp-0x69d4"] = 0                       # 0x3C148


# ---------------------------------------------------------------------------------------- FUN_0003e6d8
def fun_3e6d8(ram, cal):
    """The sole writer of gp-0x6a00 (task slot 4, 100 Hz). 0x3E6D8-0x3E75C."""
    r14 = ram["gp+0x6470"]                         # 0x3E6DC ld.h 0x6470[gp],r14
    if r14 != ram["gp-0x360a"]:                    # 0x3E6E4 cmp ; be 0x3E716  (only when the baseline changes)
        ram["gp-0x360a"] = r14                     # 0x3E6EC st.h
        r14 = i32(r14 << 16)                       # 0x3E6F0 shl 0x10,r14
        r14 = divq(r14, cal.k7432)                 # 0x3E6F2 divq r6,r14,r0
        r14 = i32(r14 << 9)                        # 0x3E6FA shl 0x9,r14
        r28 = ram["gp-0x6752"]                     # 0x3E6FC ld.b -0x6752[gp],r28
        r14 = divq(r14, cal.k713a)                 # 0x3E700 divq r15,r14,r0
        r6 = i32(r28 * r14)                        # 0x3E706 mul r14,r6,r0
        r10 = fun_3e600(r6, cal, ram)              # 0x3E70A jarl 0x3E600
        ram["gp-0x3608"] = i16(i32(r10 * r28))     # 0x3E70E mul r10,r28,r0 ; 0x3E712 st.h
    if ram["gp-0x67fe"] in (2, 1):                 # 0x3E716 ld.bu ; cmp 2 ; cmp 1
        r26 = ram["gp-0x69ca"]                     # 0x3E722 ld.h -0x69ca[gp],r26
        r16 = cal.k74f2                            # 0x3E726 ld.bu 0x74f2[tp],r16
        r8 = ram["gp-0x6cc4"]                      # 0x3E72A ld.w -0x6cc4[gp],r8
        r6 = ram["gp-0x69d0"]                      # 0x3E72E ld.h -0x69d0[gp],r6
        r26 = mulh(r16, r26)                       # 0x3E732 mulh r16,r26
        r6 = i32(r8 - r6)                          # 0x3E734 subr r8,r6
        r26 = r26 >> 7                             # 0x3E736 sar 0x7,r26
        r10 = fun_3e600(r6, cal, ram)              # 0x3E738 jarl 0x3E600
        r8 = ram["gp-0x6752"]                      # 0x3E73C ld.b
        r12 = ram["gp-0x3608"]                     # 0x3E740 ld.h
        r8 = i32(r10 * r8)                         # 0x3E744 mul r10,r8,r0
        r8 = i32(r8 + r26)                         # 0x3E748 add r26,r8
        r12 = i32(r12 + r8)                        # 0x3E74A add r8,r12
        ram["gp-0x4c8a"] = i16(r12)                # 0x3E74C st.h  (lockstep shadow)
    else:
        ram["gp-0x4c8a"] = 0                       # 0x3E752
        r12 = 0                                    # 0x3E756
    ram["gp-0x6a00"] = i16(r12)                    # 0x3E758 st.h r12,-0x6a00[gp]   (bytes 64 67 00 96)


# ---------------------------------------------------------------------------------------- FUN_00040a50
def pack_14a_angle(ram, cal):
    """STEER_ANGLE field written into gp-0x69ec (and identical gp-0x69ee). Healthy branches only."""
    if ram["gp-0x679c"] == 3 and ram["gp-0x35bc"] == 1:        # 0x40AD8 / 0x40AE2
        return i16(-ram["gp-0x6a00"])                            # 0x40B08.. mov r0,r26 ; sub r14,r26
    if ram["gp-0x679c"] == 3:
        ram["gp-0x35bc"] = 1                                      # first mode-3 pass: latch only, field HELD
        return ram.get("gp-0x69ec", 0)
    g = ram["gp-0x6ce0"]                                          # 0x40B64 ld.w  (relative accumulator)
    v = -i32((((((g >> 3) * cal.k713a) >> 8) * cal.k7432) >> 14) * ram["gp-0x6752"])
    ram["gp-0x35bc"] = 0
    return 15120 if v >= 0x3B11 else (-15120 if v < -0x3B10 else i16(v))   # clamp +-1512.0 deg


def wire_deg(field):
    """opendbc STEERING_SENSORS.STEER_ANGLE = field * -0.1 deg."""
    return -0.1 * field


# ---------------------------------------------------------------------------------------- scenario
def fresh_ram(pol=-1):
    return {"gp-0x6752": pol, "gp-0x4ee8": 0, "gp-0x3614": 1, "gp-0x69d2": 0, "gp-0x6cc4": 0,
            "gp-0x6772": 5, "gp-0x67fe": 2, "gp-0x69d0": 0, "gp-0x69d4": 0, "gp-0x69ca": 0,
            "gp+0x6470": 0, "gp-0x360a": -0x8000 + 1, "gp-0x3608": 0, "gp-0x4c8a": 0, "gp-0x6a00": 0,
            "gp-0x69dc": 0, "gp-0x679c": 3, "gp-0x35bc": 1, "gp-0x6ce0": 0}


def simulate(cal, motor_counts, engage_tick=None, phase0=0):
    """motor_counts[k] = unwrapped motor position (raw 12-bit counts) at tick k.
    Per tick: slot 0 runs (FUN_0003bd7c, then the PID read), then slot 4 if counter % 10 == 4."""
    ram = fresh_ram()
    ram["gp-0x6cc4"] = motor_counts[0]                             # steady state: accumulator already
    ram["gp-0x69d2"] = i16(motor_counts[0] & 0x0FFF)               # tracking, last snapshot = first sample
    ram["gp-0x4ee8"] = i16(motor_counts[0] & 0x0FFF)
    fun_3bd7c_angle(ram, cal); fun_3e6d8(ram, cal)                 # and one 100 Hz pass already done
    out = []
    held_from = 0
    for k, m in enumerate(motor_counts):
        ram["gp-0x4ee8"] = i16(m & 0x0FFF)                         # 12-bit snapshot (FUN_00065eda)
        fun_3bd7c_angle(ram, cal)                                  # 0x2224a
        pid_sees = ram["gp-0x6a00"]                                # what a cave at 0x22522+ would read
        probe = dict(ram)
        fun_3e6d8(probe, cal)                                      # what gp-0x6a00 WOULD be if recomputed now
        out.append((k, pid_sees, probe["gp-0x6a00"], ram["gp-0x69ca"], k - held_from,
                    engage_tick is not None and k == engage_tick))
        if (k + phase0) % 10 == 4:                                 # FUN_00014be4: c % 10 == 4 -> slot 4
            fun_3e6d8(ram, cal)                                    # 0x22e32
            held_from = k
    return out, ram


def main():
    img = sys.argv[1] if len(sys.argv) > 1 else "stock"
    cal = Cal(img)
    print(f"image={img}  X={cal.X}  Y={cal.Y}  900?={cal.k7432} 1159?={cal.k713a} 128?={cal.k74f2} "
          f"bleed={cal.k7358} reset_dwell={cal.k72a2} anchor 0xC63EA={cal.anchor_c63ea}")
    assert (cal.k7432, cal.k713a, cal.k74f2, cal.k7358) == (900, 1159, 128, 2)

    # ---- self-checks on FUN_0003e600
    ram = fresh_ram()
    for x in (0, 1, 1000, 8920, 21140, 49390, 130958, 400000):
        assert fun_3e600(x, cal, ram) == -fun_3e600(-x, cal, ram)
    assert fun_3e600(0, cal, ram) == 0

    # ---- scale: motor counts per 0.1 deg of gp-0x69d4 (linear part)
    print("linear scale: 1 count of gp-0x69ca (0.1 deg) = 1/(1159*900/(8*256*16384)) =",
          round(8 * 256 * 16384 / (1159 * 900), 4), "motor counts; 4096 counts/motor rev ->",
          round(4096 * 1159 * 900 / (8 * 256 * 16384) / 10, 3), "deg of wheel per motor rev")

    # ---- the VGR-shaped correction: local gain of gp-0x6a00 vs gp-0x69ca, segment by segment
    print("\ncorrection LERP segments (X = (|d|*45)>>9, d = motor counts):")
    for i in range(7):
        x0, x1, y0, y1 = cal.X[i], cal.X[i + 1], cal.Y[i], cal.Y[i + 1]
        d0, d1 = x0 * 512 / 45, x1 * 512 / 45
        lin0, lin1 = d0 * 1159 * 900 / (8 * 256 * 16384), d1 * 1159 * 900 / (8 * 256 * 16384)
        print(f"  |angle| {lin0/10:7.1f}..{lin1/10:7.1f} deg : correction {y0/10:+5.1f}..{y1/10:+5.1f} deg, "
              f"local gain of gp-0x6a00 / gp-0x69ca = {1 + (y1 - y0) / (lin1 - lin0):.3f}")

    # ---- staleness: what a 1 kHz cave at the PID sees, sinusoidal steering
    import math
    for f_hz, amp_deg in ((0.5, 30.0), (2.0, 5.0), (5.0, 2.0)):
        cpd = 8 * 256 * 16384 / (1159 * 900) * 10          # motor counts per degree
        mc = [int(round(-amp_deg * cpd * math.sin(2 * math.pi * f_hz * k / 1000.0))) for k in range(4000)]
        out, _ = simulate(cal, mc)
        errs = [abs(p - fr) for (k, p, fr, f, age, _) in out[200:]]
        ages = [age for (k, p, fr, f, age, _) in out[200:]]
        lag_ms = sum(ages) / len(ages)
        print(f"\n{f_hz} Hz, {amp_deg} deg: PID-side age of gp-0x6a00 = {min(ages)}..{max(ages)} ticks, "
              f"mean {lag_ms:.2f} ms -> {360*f_hz*lag_ms/1000:.1f} deg phase at {f_hz} Hz; "
              f"|held - fresh gp-0x6a00| max {max(errs)/10:.2f} deg "
              f"({100*max(errs)/(amp_deg*10):.1f} % of amplitude)")

    # ---- engage transient: nothing in the angle chain reads LKAS engagement
    mc = [int(round(-10.0 * 321.7)) for _ in range(40)]       # wheel parked at about +10 deg
    out, ram = simulate(cal, mc, engage_tick=23)
    print("\nengage at tick 23 (no angle-chain cell reads any LKAS engagement state):")
    for k, p, fr, f, age, eng in out[0:30]:
        print(f"  tick {k:2d}  held gp-0x6a00={p:5d}  fresh={fr:5d}  gp-0x69ca={f:5d}  age={age:2d}  "
              f"{'<- ENGAGE' if eng else ''}")
    ram["gp-0x679c"], ram["gp-0x35bc"] = 3, 1
    field = pack_14a_angle(ram, cal)
    print(f"  0x14A STEER_ANGLE field = {field} -> {wire_deg(field):+.1f} deg  (gp-0x6a00 = {ram['gp-0x6a00']})")

    # ---- sentinel hazards on the absolute baseline gp+0x6470
    print("\nbaseline sentinels (wheel at the same motor position):")
    for base in (0, 0x7FFF, -0x8000):
        r = fresh_ram(); r["gp+0x6470"] = base; r["gp-0x6cc4"] = 3217
        fun_3bd7c_angle(r, cal); fun_3e6d8(r, cal)
        print(f"  gp+0x6470={base:6d}: gp-0x69ca={r['gp-0x69ca']:6d}  gp-0x3608={r['gp-0x3608']:4d}  "
              f"gp-0x6a00={r['gp-0x6a00']:6d}")
    print("\nOK")


if __name__ == "__main__":
    main()
