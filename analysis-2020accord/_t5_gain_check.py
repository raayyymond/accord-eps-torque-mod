#!/usr/bin/env python3
"""Task #5 step 1 -- INDEPENDENT re-derivation of the delivered r24 rate-lane multiplier vs stock,
as a function of rateKey (gp-0x6ac0) and vehicle speed, for stock/V62/V65/V67/V68/V69/V70.

Deliberately written from the instruction addresses, NOT by importing v70_rate_lane_gain_model.py,
so a slip in that file cannot propagate. The two are compared numerically at the end.

Everything is byte-read little-endian from each build's own image. gp = 0xFEDF8000, tp = 0xBF000.
"""
import struct
import sys
from pathlib import Path

FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
TP = 0xBF000
SAR_HW = 0x3AC20          # sar 0xa,r8 == 0x42AA ; sar 0x9,r8 == 0x42A9
GATE_BYTE = 0x3AA96       # 0xC5 -> gp-0x683c (0 writers, dead) ; 0xFB -> gp-0x6806 (LKAS gate)
ARM1, ARM2, ARM3 = TP + 0x7442, TP + 0x7446, TP + 0x7440
DZ = TP + 0x71F6
CNT = TP + 0x74FA
CROSS = TP + 0x7010                                   # 0xC6010 voted-speed breakpoints
PTRS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
MODE = 10
KMH_CTS = 64.0625                                     # gp-0x6a5e counts per km/h

BUILDS = ["stock", "v62", "v65", "v66", "v67", "v68", "v69", "v70"]


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def tdiv(n, d):
    q = abs(n) // abs(d)
    return -q if (n < 0) != (d < 0) else q


class B:
    def __init__(self, name):
        p = (FW / "stock_fw_dump" / "code.bin") if name == "stock" else (FW / f"_{name}_plain_image.bin")
        self.name, self.buf = name, p.read_bytes()
        b = self.buf
        hw = u16(b, SAR_HW)
        assert hw in (0x42AA, 0x42A9), f"{name}: sar hw = 0x{hw:04X}"
        self.sar = 10 if hw == 0x42AA else 9
        self.gate_live = b[GATE_BYTE] == 0xFB
        self.arm = [u16(b, ARM1), u16(b, ARM2), u16(b, ARM3)]
        self.dz, self.cthr = u16(b, DZ), b[CNT]
        self.cross = list(struct.unpack_from("<4h", b, CROSS))
        self.recs = [u32(b, p_ + 4 * MODE) for p_ in PTRS]
        self.X = [list(struct.unpack_from("<4h", b, r + 2)) for r in self.recs]
        self.Y = [list(struct.unpack_from("<4h", b, r + 0x0A)) for r in self.recs]

    def ram(self, sc):
        k = 0
        while k <= 3 and self.cross[k] <= sc:
            k += 1
        if k == 0:
            return self.X[0][:], self.Y[0][:]
        if k > 3:
            return self.X[3][:], self.Y[3][:]
        n, d = sc - self.cross[k - 1], self.cross[k] - self.cross[k - 1]
        lo, hi = k - 1, k
        return ([self.X[lo][i] + tdiv((self.X[hi][i] - self.X[lo][i]) * n, d) for i in range(4)],
                [self.Y[lo][i] + tdiv((self.Y[hi][i] - self.Y[lo][i]) * n, d) for i in range(4)])

    @staticmethod
    def lerp(X, Y, i):
        if i <= X[0]:
            return Y[0]
        if i >= X[3]:
            return Y[3]
        k = 0
        while i >= X[k + 1]:
            k += 1
        return Y[k] + tdiv((Y[k + 1] - Y[k]) * (i - X[k]), X[k + 1] - X[k])

    def gain(self, sc, rk, engaged=True, m671d=0, c671a=0):
        idx = 0 if rk >= 13001 else int(rk)
        if m671d:
            return self.arm[0]
        if self.gate_live and engaged:
            return self.arm[1]
        if c671a >= self.cthr:
            return self.arm[2]
        X, Y = self.ram(sc)
        return self.lerp(X, Y, idx)

    def slope(self, sc, rk, **kw):
        return self.gain(sc, rk, **kw) / (1 << self.sar)


def main():
    Bs = {n: B(n) for n in BUILDS}
    st = Bs["stock"]
    print("=" * 112)
    print("STEP 1a -- what each image contains (byte-read LE, from each build's OWN image)")
    print("=" * 112)
    print(f"{'build':6s} {'sar':>5s} {'gate@0x3AA96':>13s} {'gate cell':>10s} "
          f"{'arm1':>6s} {'arm2':>6s} {'arm3':>6s} {'dz':>4s} {'cthr':>5s}  Y-rows (rate-axis gains)")
    for n in BUILDS:
        b = Bs[n]
        ed = "".join("*" if b.Y[i] != st.Y[i] else "." for i in range(4))
        print(f"{n:6s} {b.sar:5d} {'0x%02X' % b.buf[GATE_BYTE]:>13s} "
              f"{'gp-0x6806' if b.gate_live else 'gp-0x683c':>10s} "
              f"{b.arm[0]:6d} {b.arm[1]:6d} {b.arm[2]:6d} {b.dz:4d} {b.cthr:5d}  edited={ed}")
    print()
    for n in BUILDS:
        b = Bs[n]
        if n != "stock" and b.Y == st.Y and b.X == st.X:
            print(f"  {n:6s} rate-axis records BYTE-IDENTICAL to stock")
            continue
        for i in range(4):
            tag = "  <<<" if b.Y[i] != st.Y[i] or b.X[i] != st.X[i] else ""
            print(f"  {n:6s} rec{i} @0x{b.recs[i]:05X}  X={b.X[i]}  Y={b.Y[i]}{tag}")
    print(f"\n  cross axis 0xC6010 = {st.cross} counts = "
          f"{[round(c / KMH_CTS, 2) for c in st.cross]} km/h  (identical on all builds: "
          f"{all(Bs[n].cross == st.cross for n in BUILDS)})")

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 112)
    print("STEP 1b -- DELIVERED multiplier vs stock at CREEP 7.2 km/h, vs rateKey  (engaged=True)")
    print("=" * 112)
    sc = int(7.2 * KMH_CTS)
    rks = [0, 200, 400, 603, 800, 1000, 1126, 1206, 1400, 1500, 2000, 3000, 5000, 13001]
    print(f"{'build':12s}" + "".join(f"{r:>8d}" for r in rks))
    for n in ["stock", "v62", "v65", "v67", "v68", "v69", "v70"]:
        base = [st.slope(sc, r, engaged=True) for r in rks]
        row = [Bs[n].slope(sc, r, engaged=True) / base[i] for i, r in enumerate(rks)]
        print(f"{n:12s}" + "".join(f"{v:8.3f}" for v in row))
    print(f"{'stock ABS':12s}" + "".join(f"{st.slope(sc, r, engaged=True):8.3f}" for r in rks))

    print()
    print("  same table, MANUAL (engaged=False) -- only V67/V68 differ, their arm is gated")
    print(f"{'build':12s}" + "".join(f"{r:>8d}" for r in rks))
    for n in ["stock", "v62", "v67", "v68", "v69", "v70"]:
        base = [st.slope(sc, r, engaged=False) for r in rks]
        row = [Bs[n].slope(sc, r, engaged=False) / base[i] for i, r in enumerate(rks)]
        print(f"{n:12s}" + "".join(f"{v:8.3f}" for v in row))

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 112)
    print("STEP 1c -- the FULL surface: multiplier vs (speed, rateKey), engaged")
    print("=" * 112)
    for n in ["v62", "v67", "v69", "v70"]:
        print(f"\n  {n.upper()}  (rows = km/h, cols = rateKey counts)")
        print(f"    {'km/h':>5s}" + "".join(f"{r:>8d}" for r in rks))
        for kmh in (0, 3.2, 5, 7.2, 10, 14.4, 20, 30, 40, 50, 60, 80, 100):
            s = int(round(kmh * KMH_CTS))
            row = [Bs[n].slope(s, r, engaged=True) / st.slope(s, r, engaged=True) for r in rks]
            print(f"    {kmh:5.1f}" + "".join(f"{v:8.3f}" for v in row))

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 112)
    print("STEP 1d -- CROSS-CHECK against v70_rate_lane_gain_model.py (must agree exactly)")
    print("=" * 112)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import v70_rate_lane_gain_model as M
    imgs = {"stock": (FW / "stock_fw_dump" / "code.bin").read_bytes()}
    for v in ("v62", "v65", "v66", "v67", "v68", "v69"):
        imgs[v] = (FW / f"_{v}_plain_image.bin").read_bytes()
    MB = {k: M.Build(k, v) for k, v in imgs.items()}
    bad = 0
    for n in ("stock", "v62", "v65", "v67", "v68", "v69"):
        for kmh in (0, 5, 7.2, 10, 20, 50, 80):
            for r in rks:
                for eng in (True, False):
                    a = Bs[n].slope(int(round(kmh * KMH_CTS)), r, engaged=eng)
                    # the model file uses 64.0 counts/km/h, mine uses 64.0625 -- feed it the SAME counts
                    b = MB[n].slope(int(round(kmh * KMH_CTS)), r, engaged=eng)
                    if abs(a - b) > 1e-12:
                        bad += 1
                        if bad < 8:
                            print(f"  MISMATCH {n} {kmh} km/h rk={r} eng={eng}: mine={a} theirs={b}")
    print(f"  mismatches: {bad}  (0 == the leader's table is reproduced independently)")

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 112)
    print("STEP 1e -- OTHER cal cells the leader byte-checked, plus a FULL DIFF of every")
    print("            build against stock restricted to the calibration region, to look for")
    print("            anything else that tracks the V62/V67-vs-V69/V70 split.")
    print("=" * 112)
    named = {"0xC646C": 0xC646C, "0xC6CD0": 0xC6CD0, "0xC6440": 0xC6440, "0xC6442": 0xC6442,
             "0xC6444": 0xC6444, "0xC6446": 0xC6446, "0xD2006": 0xD2006, "0xC61F6": 0xC61F6,
             "0xC64FA": 0xC64FA, "0xC62EA": 0xC62EA, "0xC6316": 0xC6316, "0xC644A": 0xC644A,
             "0xC6564": 0xC6564, "0xC613A": 0xC613A}
    print(f"{'cell':10s}" + "".join(f"{n:>8s}" for n in BUILDS))
    for k, a in named.items():
        print(f"{k:10s}" + "".join(f"{u16(Bs[n].buf, a):8d}" for n in BUILDS))

    print("\n  BYTE DIFF vs stock over 0xC0000-0xD8000 (the cal region), per build:")
    for n in BUILDS[1:]:
        b = Bs[n].buf
        d = [i for i in range(0xC0000, 0xD8000) if b[i] != st.buf[i]]
        # collapse into runs
        runs = []
        for i in d:
            if runs and i == runs[-1][1] + 1:
                runs[-1][1] = i
            else:
                runs.append([i, i])
        print(f"    {n:6s} {len(d):5d} differing bytes in {len(runs)} runs: "
              + ", ".join(f"0x{a:05X}-0x{b_:05X}" for a, b_ in runs[:14])
              + (" ..." if len(runs) > 14 else ""))

    print("\n  BYTE DIFF vs stock over the whole CODE region 0x0-0xC0000, per build:")
    for n in BUILDS[1:]:
        b = Bs[n].buf
        d = [i for i in range(0x0, 0xC0000) if b[i] != st.buf[i]]
        runs = []
        for i in d:
            if runs and i == runs[-1][1] + 1:
                runs[-1][1] = i
            else:
                runs.append([i, i])
        print(f"    {n:6s} {len(d):5d} differing bytes in {len(runs)} runs: "
              + ", ".join(f"0x{a:05X}-0x{b_:05X}" for a, b_ in runs[:20])
              + (" ..." if len(runs) > 20 else ""))


if __name__ == "__main__":
    main()
