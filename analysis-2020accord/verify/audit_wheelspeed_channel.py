#!/usr/bin/env python3
"""verify/audit_wheelspeed_channel.py -- can the ABS wheel-speed message see a 50-150 Hz disturbance?

WHY. Every instrument this kit has used folds at ~50 Hz. Wheel speed is a rotational-velocity
measurement made by a DIFFERENT sensor (the ABS tone rings) on a DIFFERENT sample grid, and a
driveline or tyre-order vibration necessarily modulates it. Aliasing is not automatically fatal:
a KNOWN fold at a KNOWN rate still discriminates hypotheses, and -- the point of section 6 -- three
channels with three DIFFERENT sample rates fold a single true tone to three DIFFERENT places, which
over-determines it.

Honda `_honda_common.dbc`:
    BO_ 464 WHEEL_SPEEDS: 8 VSA
     SG_ WHEEL_SPEED_FL : 7|15@0+ (0.01,0) "kph"      <- big-endian, 15 bits, LSB = 0.01 kph
     SG_ WHEEL_SPEED_FR : 8|15@0+ ...
     SG_ WHEEL_SPEED_RL : 25|15@0+ ...
     SG_ WHEEL_SPEED_RR : 42|15@0+ ...

Everything below is MEASURED from the rlog. The decode is verified against `carState.vEgo` before
any conclusion is drawn from it.

Usage:  python verify/audit_wheelspeed_channel.py 4a 20 21 22 23 24 25
        python verify/audit_wheelspeed_channel.py 47 5 6 7
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {"4a": "75604b0a432fdc89_0000004a--346bf31d97",
          "47": "75604b0a432fdc89_00000047--3e0b6134c0"}
WHEEL_SPEEDS, ROUGH_WHEEL_SPEED = 0x1D0, 0x255
LSB_KPH = 0.01
KPH2MS = 1 / 3.6
# wheel circumference from this kit's own wheel-order-1 measurement (2.073-2.088 m); r = C/2pi
CIRC_M = 2.080
R_WHEEL = CIRC_M / (2 * np.pi)


def be_bits(d, start_bit, length):
    """DBC big-endian (Motorola) extraction, exactly as cereal/opendbc does it."""
    val = 0
    b = start_bit
    for _ in range(length):
        byte, bit = b // 8, b % 8
        val = (val << 1) | ((d[byte] >> bit) & 1)
        bit -= 1
        if bit < 0:
            b = (byte + 1) * 8 + 7
        else:
            b = byte * 8 + bit
    return val


def lattice(t):
    dt = np.diff(np.asarray(t, float))
    dt = dt[dt > 0]
    p = float(np.median(dt))
    for _ in range(6):
        k = np.round(dt / p)
        ok = (k >= 1) & (k <= 20) & (np.abs(dt / p - k) < 0.35)
        if ok.sum() < 8:
            break
        p = float(dt[ok].sum() / k[ok].sum())
    k = np.round(dt / p)
    ok = (k >= 1) & (k <= 20) & (np.abs(dt / p - k) < 0.35)
    return 1 / p, float(np.std((dt[ok] / p - k[ok]) * p)), float(1 - ok.sum() / k[ok].sum())


def extract(tag, segs, want_src=None):
    rows, vt, vv, srcs = [], [], [], {}
    rough = 0
    for s in segs:
        p = RLOGDIR / f"{ROUTES[tag]}--{s}--rlog.zst"
        if not p.exists():
            continue
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    a = int(m.address)
                    if a == WHEEL_SPEEDS:
                        src = int(m.src)
                        srcs[src] = srcs.get(src, 0) + 1
                        if want_src is not None and src != want_src:
                            continue
                        d = bytes(m.dat)
                        rows.append((tm, be_bits(d, 7, 15), be_bits(d, 8, 15),
                                     be_bits(d, 25, 15), be_bits(d, 42, 15)))
                    elif a == ROUGH_WHEEL_SPEED:
                        rough += 1
            elif w == "carState":
                vt.append(tm)
                vv.append(float(evt.carState.vEgo))
    return np.array(rows, float), np.array(vt), np.array(vv), srcs, rough


def main(tag, segs):
    print(__doc__.split("Usage:")[0].rstrip())
    A, vt, vv, srcs, rough = extract(tag, segs)
    print(f"\n=== route {tag} segments {segs} ===")
    print(f"0x{WHEEL_SPEEDS:03X} WHEEL_SPEEDS frames per src: {srcs}   "
          f"(all srcs carrying 0x1D0 are used; the device sees it on exactly one bus)")
    print(f"0x{ROUGH_WHEEL_SPEED:03X} ROUGH_WHEEL_SPEED frames: {rough} "
          f"(1 kph LSB -- 100x coarser, ignored)")
    if not len(A):
        print("NO FRAMES -- 0x1D0 absent from this route")
        return
    t = A[:, 0] - A[0, 0]
    cnt = A[:, 1:5]
    ms = cnt * LSB_KPH * KPH2MS

    f, jit, drop = lattice(t)
    print(f"\n1. RATE:  n={len(t)}  span {t[-1]:.1f} s  LATTICE {f:.4f} Hz  "
          f"jitter {1e3 * jit:.3f} ms  drop {100 * drop:.2f}%   => NYQUIST {f / 2:.4f} Hz")

    v = np.interp(t, vt - A[0, 0], vv)
    mean4 = ms.mean(axis=1)
    ok = v > 5
    r = np.corrcoef(mean4[ok], v[ok])[0, 1]
    sl = np.polyfit(v[ok], mean4[ok], 1)
    print(f"\n2. DECODE CHECK vs carState.vEgo (n={ok.sum()}): r = {r:.6f}   "
          f"mean(4 wheels) = {sl[0]:.4f}*vEgo + {sl[1]:+.4f}")
    print(f"   counts range {cnt.min():.0f}..{cnt.max():.0f} (15-bit field, max 32767) => "
          f"{'DECODE CONFIRMED' if r > 0.999 and 0.95 < sl[0] < 1.05 else 'DECODE SUSPECT'}")

    print(f"\n3. RESOLUTION:  LSB = {LSB_KPH} kph = {LSB_KPH * KPH2MS:.6f} m/s")
    print(f"   at the tyre (r = {R_WHEEL:.4f} m from C = {CIRC_M} m): "
          f"{LSB_KPH * KPH2MS / R_WHEEL:.6f} rad/s = {np.degrees(LSB_KPH * KPH2MS / R_WHEEL):.4f} deg/s")
    dcs = np.diff(cnt, axis=0).astype(int)
    hw = v[:-1] > 25
    for i, nm in enumerate(("FL", "FR", "RL", "RR")):
        u, c = np.unique(dcs[hw, i], return_counts=True)
        top = sorted(zip(u.tolist(), c.tolist()), key=lambda q: -q[1])[:5]
        gcd = int(np.gcd.reduce(np.abs(dcs[hw, i])[dcs[hw, i] != 0])) if (dcs[hw, i] != 0).any() else 0
        print(f"   {nm}: highway delta-count histogram {top}  |  GCD of non-zero deltas = {gcd}"
              f"  => effective LSB is {gcd}x nominal" if gcd else f"   {nm}: constant")

    print(f"\n4. NOISE FLOOR AND DETECTION THRESHOLD (highway, v > 25 m/s)")
    NW = 256
    runs = []
    m = v > 25
    i = 0
    while i < len(m):
        if not m[i]:
            i += 1
            continue
        j = i
        while j < len(m) and m[j]:
            j += 1
        if j - i >= NW:
            runs.append(slice(i, j))
        i = j
    if not runs:
        print("   no contiguous highway run >= 5.12 s")
        return
    fr = np.fft.rfftfreq(NW, 1 / f)
    print(f"   {len(runs)} contiguous runs, window {NW / f:.2f} s, bin {fr[1]:.4f} Hz")
    for i, nm in enumerate(("FL", "FR", "RL", "RR")):
        P, nw = None, 0
        for sl_ in runs:
            x = ms[sl_, i]
            x = x - np.convolve(x, np.ones(51) / 51, mode="same")     # kill the speed trend
            for k in range(1, len(x) // NW):                           # skip edge-tainted block 0
                w = x[k * NW:(k + 1) * NW] * np.hanning(NW)
                p = np.abs(np.fft.rfft(w)) ** 2
                P = p if P is None else P + p
                nw += 1
        if P is None or nw == 0:
            continue
        P /= nw
        # convert PSD to a single-tone amplitude scale: Hanning coherent gain 0.5, so a tone of
        # amplitude a gives peak power (a * NW * 0.5 / 2)^2
        amp = np.sqrt(P) / (NW * 0.5 / 2)
        band = (fr > 2) & (fr < 24)
        floor = float(np.median(amp[band]))
        pk = int(np.argmax(amp * band))
        det = 4 * floor / np.sqrt(nw)                                  # 4-sigma after averaging nw
        print(f"   {nm}: 2-24 Hz median tone-amplitude floor {floor * 1e3:.4f} mm/s "
              f"({np.degrees(floor / R_WHEEL):.5f} deg/s)   peak {fr[pk]:.2f} Hz "
              f"{amp[pk] / floor:.1f}x floor")
        print(f"       4-sigma detectable tone over {nw} windows ({nw * NW / f:.0f} s): "
              f"{det * 1e3:.4f} mm/s = {np.degrees(det / R_WHEEL):.5f} deg/s of wheel rate")
        for f0 in (60.0, 80.0, 120.0):
            th = np.degrees(det / R_WHEEL) / (2 * np.pi * f0)
            print(f"         a {f0:.0f} Hz torsional oscillation is detectable at angular "
                  f"amplitude >= {th * 1e3:.4f} milli-deg at the wheel")

    print(f"\n5. THE ALIAS MAP for fs = {f:.3f} Hz (this is what a >Nyquist tone becomes)")
    print(f"   {'true Hz':>9s} {'folds to':>10s}   note")
    for f0 in (30, 45, 49, 55, 60, 70, 80, 90, 99, 100, 110, 120, 125, 140, 149, 150):
        a = abs(f0 - f * round(f0 / f))
        note = ""
        if a < 0.6:
            note = "*** BLIND SPOT: folds onto DC, invisible"
        elif abs(a - f / 2) < 0.6:
            note = "folds onto Nyquist"
        print(f"   {f0:9.1f} {a:10.2f}   {note}")
    print("   => the fold has BLIND SPOTS at every multiple of the sample rate. A tone at 100.0 or")
    print("      150.0 Hz lands on DC and is structurally invisible in this channel, at any SNR.")

    print("\n6. WHY THREE SAMPLE RATES OVER-DETERMINE ONE TONE (the free experiment)")
    rates = {"wheel speed 0x1D0": f, "EPS CAN 0x14A/0x18F": 100.0000, "comma IMU": 101.0282}
    print(f"   {'true Hz':>8s} " + " ".join(f"{k:>21s}" for k in rates))
    for f0 in (55, 65, 75, 85, 95, 105, 115, 130, 145):
        cells = [abs(f0 - r * round(f0 / r)) for r in rates.values()]
        print(f"   {f0:8.1f} " + " ".join(f"{c:21.3f}" for c in cells))
    print("   The three columns are DIFFERENT functions of f0, so an observed triple (a1,a2,a3)")
    print("   pins f0 -- no firmware change, no hardware change. The 100.000 vs 101.028 Hz pair")
    print("   alone separates alias ORDER n, because their aliases differ by exactly n*1.028 Hz.")
    print("   🛑 THE CATCH, and it is decisive: this works ONLY IF SOMETHING ACTUALLY FOLDS. If the")
    print("   ABS module or the EPS low-passes before transmitting, or the IMU's analog anti-alias")
    print("   filter cuts below 50 Hz, there is nothing to fold and all three read the same null.")
    print("   Section 7 tests that directly.")

    print("\n7. IS THERE EVIDENCE OF FOLDING AT ALL? -- spectral shape approaching Nyquist")
    for i, nm in enumerate(("FL", "RR")):
        col = 0 if nm == "FL" else 3
        P, nw = None, 0
        for sl_ in runs:
            x = ms[sl_, col]
            x = x - np.convolve(x, np.ones(51) / 51, mode="same")
            for k in range(1, len(x) // NW):
                w = x[k * NW:(k + 1) * NW] * np.hanning(NW)
                p = np.abs(np.fft.rfft(w)) ** 2
                P = p if P is None else P + p
                nw += 1
        P /= nw
        lo = float(np.median(P[(fr > 3) & (fr < 8)]))
        hi = float(np.median(P[(fr > 20) & (fr < 24.5)]))
        print(f"   {nm}: PSD 20-24.5 Hz / 3-8 Hz = {hi / lo:.4f} "
              f"({10 * np.log10(hi / lo):+.1f} dB).  A channel that is properly anti-aliased and")
        print(f"       whose real content is low-frequency should be WELL BELOW 1. A ratio near or")
        print(f"       above 1 means broadband energy is present right up to the fold.")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "4a"
    segs = [int(x) for x in sys.argv[2:]] or [20, 21, 22, 23, 24, 25]
    main(tag, segs)
