#!/usr/bin/env python3
"""V70 -- (1) the gain_B record-selection axis, exactly; (2) the rail; (3) the V70 two-knob question.

Mirrors FUN_0003ad74's FIRST half (0x3AD74-0x3AECC), which is the gain_B / r24 rebuilder -- NOT
gain_A. (The second half, 0x3AECC-0x3AFEE, is gain_A / r26 and writes gp-0x6e30 / gp-0x6e28 from
tp+0x7a68/7a7c/7a90/7aa4 = 0xC6A68/7C/90/A4.) There is no separate gain_B rebuilder.

Record selection, instruction by instruction:
  0x3AD76 ld.bu -0x67f4[gp],r10 ; cmp 0x1 ; bne     speed-valid flag
  0x3AD7E ld.hu -0x6a5e[gp],r1                      speed = voted vehicle speed (counts)
  0x3AD84 ld.hu 0x7314[tp],r1                       else fallback [0xC6314] = 5120 (= 80 km/h)
  0x3AD88 ld.bu 0x63fd[gp],r16                      mode byte
  0x3AD90/9C/A6 mov 0xcbf5c/0xcc044/0xcc12c,ep ; shl 0x2,r16 ; add ; sld.w
  0x3ADC2 ld.w 0xd214[r16],r15                      P3 via tp+0xD214 = 0xCC214
  0x3ADB0/B6/BC/CC st.w -> 0x0/0x4/0x8/0xc[sp]      FOUR record pointers on the stack
  0x3ADCA-0x3ADE6  k = first index with Xcross[k] > speed   (Xcross = 0xC6010)
  0x3ADEE cmp 0x3,r9 ; bnc 0x3AE6A                  (k-1) unsigned >= 3 -> COPY path
  0x3ADF8 ld.w -0x4[ep],r16                         LOW  record = stack[k-1]
  0x3AE00 sld.w 0x0[ep],r6                          HIGH record = stack[k]
  0x3AE12 sub r7,r11 / 0x3AE14 sub r7,r13           num = speed-Xcross[k-1] ; den = Xcross[k]-..[k-1]
  0x3AE1E-0x3AE66 per-point loop: X_ram[i], Y_ram[i] = lerp(LOW, HIGH)   <-- TWO records, no more
  0x3AE7A (k==0) copy P0 ; 0x3AEA4 (k==4) copy P3

Usage:  python v70_record_selection_and_rail.py
"""
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from v70_rate_lane_gain_model import (Build, ROOT, BUILDS, CLIP, DT_CLAMP,   # noqa: E402
                                      SPEED_CTS_PER_KMH, describing_fn, idiv_trunc)


def selected_records(b, speed_cts):
    """Which of P0..P3 the rebuilder actually reads, and with what weight. Mirrors 0x3ADCA-0x3AEA4."""
    k = 0
    while k <= 3 and b.cross[k] <= speed_cts:      # 0x3ADE4 cmp r11,r10 ; ble
        k += 1
    if k == 0:
        return ("copy", [0], None)                 # 0x3AE7A: P0 only
    if k > 3:
        return ("copy", [3], None)                 # 0x3AEA4: P3 only
    num = speed_cts - b.cross[k - 1]
    den = b.cross[k] - b.cross[k - 1]
    return ("lerp2", [k - 1, k], (num, den))       # exactly TWO records


def main():
    imgs = {"stock": (ROOT / "stock_fw_dump" / "code.bin").read_bytes()}
    for v in BUILDS[1:]:
        imgs[v] = (ROOT / f"_{v}_plain_image.bin").read_bytes()
    B = {k: Build(k, v) for k, v in imgs.items()}
    S, V69, V62, V67 = B["stock"], B["v69"], B["v62"], B["v67"]

    print("=" * 100)
    print("Q1 -- RECORD SELECTION: how many records participate, at what speed?")
    print("=" * 100)
    print(f"  Xcross (0xC6010) = {S.cross} counts = "
          f"{[c / SPEED_CTS_PER_KMH for c in S.cross]} km/h at 64 cts/km/h")
    print(f"  mode-10 records  = {[hex(r) for r in S.recs]}  (P0 P1 P2 P3)")
    print(f"  V69 edits P0 (0xD2A7E/80) and P1 (0xD2ABA/BC) ONLY.\n")
    print(f"  {'speed cts':>9s} {'km/h':>7s}  {'mode':6s} {'records read':16s} {'weight':>12s}")
    for sc in (-1, 0, 1, 320, 639, 640, 641, 1280, 3199, 3200, 3201, 5120, 6399, 6400, 6401, 9000):
        mode, recs, w = selected_records(S, sc)
        rl = " ".join(f"P{i}({S.recs[i]:#07x})" for i in recs)
        print(f"  {sc:9d} {sc / SPEED_CTS_PER_KMH:7.2f}  {mode:6s} {rl:34s} "
              f"{'' if w is None else f'{w[0]}/{w[1]}'}")

    print("\n  *** ASSERTION SWEEP: is V69's RAM gain_B table BIT-IDENTICAL to stock's? ***")
    first_ident = None
    for sc in range(0, 6500):
        same = S.ram_table(sc) == V69.ram_table(sc)
        if same and first_ident is None:
            first_ident = sc
        if not same:
            first_ident = None
    # find the lowest speed above which it is identical for ALL higher speeds
    lo = 6500
    for sc in range(6500, -1, -1):
        if S.ram_table(sc) == V69.ram_table(sc):
            lo = sc
        else:
            break
    print(f"    identical for every speed >= {lo} counts = {lo / SPEED_CTS_PER_KMH:.3f} km/h")
    print(f"    NOT identical at {lo - 1} counts ({(lo - 1) / SPEED_CTS_PER_KMH:.3f} km/h):")
    print(f"      stock Y = {S.ram_table(lo - 1)[1]}   V69 Y = {V69.ram_table(lo - 1)[1]}")
    print(f"    at {lo} counts: stock Y = {S.ram_table(lo)[1]}   V69 Y = {V69.ram_table(lo)[1]}")
    print(f"    ratio just below the boundary, rateKey 0: "
          f"{V69.slope(lo - 1, 0) / S.slope(lo - 1, 0):.6f}   at/above: "
          f"{V69.slope(lo, 0) / S.slope(lo, 0):.6f}")
    print(f"    speed fallback when gp-0x67f4 != 1: [0xC6314] = {struct.unpack_from('<h', S.buf, 0xC6314)[0]}"
          f" counts -> records {selected_records(S, 5120)[1]} => V69 == stock on the fallback too")

    # -------------------------------------------------------------------------------------------
    print()
    print("=" * 100)
    print("Q2 -- THE RAIL: smallest |dtorque| (gp-0x4f62) at which the +/-0x2000 clip engages")
    print("=" * 100)
    print("  Found by BRUTE-FORCE evaluation of the real integer chain (not a closed form):")
    print("  out = clip( dz3( (clamp(dt,+/-5120) * gain) >> sar ) * polarity , +/-8192 )")
    print("  the 3-count deadzone [0xC61F6] is subtracted BEFORE the clamp, so the rail needs")
    print("  (dt*gain)>>sar >= 8192 + 3 = 8195, i.e. 2 counts of |dt| more than a deadzone-free model.")

    def rail_brute(b, kmh, **kw):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        for dt in range(1, DT_CLAMP + 1):
            if b.lane_out(dt, sc, 0, **kw) >= CLIP:
                return dt
        return None

    rows = [("stock", "stock", dict(engaged=True)),
            ("V62 / V65", "v62", dict(engaged=True)),
            ("V66", "v66", dict(engaged=True)),
            ("V67/V68 ENGAGED", "v67", dict(engaged=True)),
            ("V67/V68 manual", "v67", dict(engaged=False)),
            ("V69 (eng == manual)", "v69", dict(engaged=True))]
    speeds = [0, 10, 20, 30, 40, 50, 60, 100]
    print(f"\n  {'build':22s}" + "".join(f"{k:>8d}" for k in speeds) + "   km/h")
    for lbl, bn, kw in rows:
        vals = []
        for kmh in speeds:
            r = rail_brute(B[bn], kmh, **kw)
            vals.append("never" if r is None else str(r))
        print(f"  {lbl:22s}" + "".join(f"{v:>8s}" for v in vals))
    print("\n  cross-check, deadzone-free closed form at 0 km/h (to show the +2):")
    for lbl, bn, kw in rows:
        g = B[bn].gain(0, 0, **kw)
        print(f"    {lbl:22s} gain={g:5d} sar={B[bn].sar}  with dz {math.ceil((CLIP + 3) * (1 << B[bn].sar) / g):5d}"
              f"   without dz {math.ceil(CLIP * (1 << B[bn].sar) / g):5d}")
    print("\n  reference amplitudes: repo max |dtorque| 839 | V68-route max 511 | 28 Hz burst 254")
    print("                        V61 grind medians 366 / p90 619 / p99 731")

    # -------------------------------------------------------------------------------------------
    print()
    print("=" * 100)
    print("Q2b -- DESCRIBING FUNCTION: where does V69 fall below V62, and below stock?")
    print("=" * 100)
    print("  (i) SATURATION ONLY (gain index held at its DC value, creep, rateKey = 0):")
    print(f"  {'A (dt cts)':>10s} {'stock':>9s} {'V62':>9s} {'V69':>9s} {'V69/V62':>9s} {'V69/stock':>10s}")
    for A in (254, 511, 731, 839, 1200, 1600, 2400, 3200, 5120, 8000, 16000):
        n_s = describing_fn(S.slope(0, 0), CLIP, A)
        n_62 = describing_fn(V62.slope(0, 0), CLIP, A)
        n_69 = describing_fn(V69.slope(0, 0), CLIP, A)
        print(f"  {A:10d} {n_s:9.3f} {n_62:9.3f} {n_69:9.3f} {n_69 / n_62:9.3f} {n_69 / n_s:10.3f}")
    print("  => NEVER below either. N(A) = (L/A)*u*f(1/u), u = K*A/L, is strictly increasing in K,")
    print("     so at equal amplitude a larger K always gives a larger N. All builds share the")
    print("     4L/(pi*A) asymptote; V69 approaches it from ABOVE.")

    print("\n  (ii) WITH THE RATE AXIS LIVE (gain index oscillates with the mode) -- this DOES cross.")

    def lane_df(b, A_dt, A_rk, kmh, phi, n=4096, **kw):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        acc = 0.0
        for i in range(n):
            th = 2.0 * math.pi * i / n
            acc += b.lane_out(int(round(A_dt * math.sin(th))), sc,
                              int(round(abs(A_rk * math.sin(th + phi)))), **kw) * math.sin(th)
        return (2.0 / n) * acc / A_dt

    for phi_lbl, phi in (("in-phase", 0.0), ("quadrature", math.pi / 2)):
        print(f"\n   creep (0 km/h), A_dt = 731 (V61 p99), gain index {phi_lbl}:")
        print(f"   {'A_rk':>6s} {'stock':>8s} {'V62':>8s} {'V69':>8s} {'V69/V62':>9s} {'V69/stock':>10s}")
        for A_rk in (0, 400, 700, 1000, 1100, 1200, 1300, 1400, 1600, 2000, 3000, 5000):
            n_s = lane_df(S, 731, A_rk, 0, phi, engaged=True)
            n_62 = lane_df(V62, 731, A_rk, 0, phi, engaged=True)
            n_69 = lane_df(V69, 731, A_rk, 0, phi, engaged=True)
            print(f"   {A_rk:6d} {n_s:8.3f} {n_62:8.3f} {n_69:8.3f} {n_69 / n_62:9.3f} {n_69 / n_s:10.3f}")

    # -------------------------------------------------------------------------------------------
    print()
    print("=" * 100)
    print("Q3 -- THE V70 TWO-KNOB QUESTION: with the gate RESTORED (0x3AA96 = 0xfb),")
    print("      does the arm govern ENGAGED and the surface govern MANUAL?")
    print("=" * 100)
    print("""  Instruction sequence 0x3AB9C-0x3AC18 (stock disasm, verbatim):
      0x3AB9C ld.h  -0x6e40[gp],r11     |
      0x3ABA4 movea -0x6e40,gp,ep       |  the LERP over the SPEED-BLENDED RAM table
      0x3ABAE movea -0x6e38,gp,r12      |  runs FIRST and UNCONDITIONALLY, result -> r10
      0x3ABB4..0x3ABF8  (lerp body)     |
      0x3ABFA cmp r0,r6 / be 0x3AC04
      0x3ABFE ld.hu 0x7442[tp],r10      <- ARM 1  [0xC6442]=1024  if gp-0x671d != 0   OVERWRITES r10
      0x3AC04 cmp r0,lp / be 0x3AC0E
      0x3AC08 ld.hu 0x7446[tp],r10      <- ARM 2  [0xC6446]       if GATE  != 0       OVERWRITES r10
      0x3AC0E cmp r0,r2  / be 0x3AC16
      0x3AC12 ld.hu 0x7440[tp],r10      <- ARM 3  [0xC6440]=2048  if gp-0x671a >= 5   OVERWRITES r10
      0x3AC16 mov r1,r8 / 0x3AC18 mul r10,r8,r0 / 0x3AC20 sar 0xa,r8

  Each arm is an unconditional OVERWRITE of r10 followed by `br 0x3AC16`; no arm blends with the
  LERP and no arm is skipped once taken. So r10 at 0x3AC18 is EXACTLY ONE of four values.""")
    print("\n  With 0x3AA96 = 0xfb (gate cell = gp-0x6806, LKAS-engaged, 16 writers / live):")
    print("    engaged & gp-0x671d == 0  ->  gain = [0xC6446]        LERP DISCARDED (surface INERT)")
    print("    manual  & gp-0x671d == 0  ->  arm2 skipped; arm3 needs gp-0x671a >= 5 which is")
    print("                                  0/186,321 (V67) and 0/53,991 (V68)  ->  gain = LERP")
    print("    gp-0x671d != 0            ->  gain = [0xC6442] = 1024 in BOTH cases (outranks all)")
    print("\n  Demonstration on the real chain, V69 image with the gate byte forced to 0xfb:")
    v70 = Build("v70sim", bytearray(imgs["v69"]))
    v70.buf = bytearray(v70.buf)
    v70.buf[0x3AA96] = 0xFB
    v70.gate_live = True
    v70.arm2 = 5244                                  # illustrative engaged dose
    print(f"  {'km/h':>5s} | {'stock':>7s} {'V70 ENGAGED (arm=5244)':>24s} {'V70 MANUAL (surface x4)':>25s}")
    for kmh in (0, 5, 10, 20, 30, 40, 50, 60, 100):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        st = S.slope(sc, 0)
        print(f"  {kmh:5d} | {st:7.3f} {v70.slope(sc, 0, engaged=True):9.3f}"
              f" ({v70.slope(sc, 0, engaged=True) / st:5.3f}x)      "
              f"{v70.slope(sc, 0, engaged=False):9.3f} ({v70.slope(sc, 0, engaged=False) / st:5.3f}x)")
    print("\n  and the surface knob is provably INERT on the engaged lane under gate=0xfb:")
    v70_flat = Build("v70flat", bytearray(imgs["stock"]))
    v70_flat.buf = bytearray(v70_flat.buf)
    v70_flat.buf[0x3AA96] = 0xFB
    v70_flat.gate_live = True
    v70_flat.arm2 = 5244
    same = all(v70.slope(int(round(k * SPEED_CTS_PER_KMH)), r, engaged=True)
               == v70_flat.slope(int(round(k * SPEED_CTS_PER_KMH)), r, engaged=True)
               for k in range(0, 121) for r in (0, 300, 603, 1206, 2000, 3000))
    print(f"    V69-surface + gate=fb  vs  STOCK-surface + gate=fb, engaged, "
          f"121 speeds x 6 rates: identical = {same}")


if __name__ == "__main__":
    sys.exit(main())
