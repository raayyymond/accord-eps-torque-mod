#!/usr/bin/env python3
"""V70 -- r26's liveness, its gain chain per build, the V67/V68 cost, and 0xC6444's blast radius.

WHY r26 IS LIVE (the chain, byte- and decompile-verified):
  FUN_00036022 @0x36068-0x3608C:
      gp-0x6bda = ( gp-0x6bf0 > 0 ? gp-0x6bd8 - gp-0x6bf0            <- upper envelope minus x
                                  : gp-0x6bf0 - gp-0x6bd6 )          <- x minus lower envelope
                  - ( gp-0x67fe == 2 ? 0 : [0xC614C] = 128 )
  FUN_00035d38: gp-0x6bd8 / gp-0x6bd6 are a rising PEAK-HOLD envelope of gp-0x6bf0, clamped to
      +/-[0xC614A] = +/-10048, default half-width [0xC6150]>>1 = 9390.
  ⇒ gp-0x6bda is a MARGIN-TO-OWN-PEAK, not a raw signal.
  gp-0x6bf0 = DRIVER ASSIST TORQUE (kit memory reference_accord_lerp_envelope_gating; hands-off is
      |gp-0x6bf0| <= 9216, cal 0xC6156 -- byte-verified 9216 here).
  FUN_000361c8: gp-0x6b5e = polarity * ((LERP_0xC66CC(gp-0x6bda) * [0xC63C2]=1024) >> 10)
      table 0xC66CC: n=5, X=[-384,-128,128,294,384], Y=[0,4762,4762,717,0]  -> 0 only at/outside +/-384
  FUN_0003aa2c @0x3AB2A-0x3AB34: r26 is KILLED iff (gp-0x6b5e != 0 AND r22 == 1); [0xC6138]=1 and
      gp-0x671a<5 always, so r22==1 always  ⇒  r26 LIVE  <=>  |gp-0x6bda| >= 384.
  ⇒ HANDS-OFF (gp-0x6bf0 ~ 0, envelope ~9390): gp-0x6bda ~ 9262, i.e. 24x the 384 threshold.
    r26 is LIVE, and most strongly live exactly in the hands-off creep condition.

r26's GAIN CHAIN (3-way priority -- NO gp-0x671d arm, unlike r24):
  0x3AB56 cmp r0,lp  / be / 0x3AB5E ld.hu 0x7444[tp],r8   ARM [0xC6444]=512   <- SAME `lp` as r24
  0x3AB64 cmp r0,r2  / be / 0x3AB68 ld.hu 0x743e[tp],r8   ARM [0xC643E]=1536
  else                                                     the gain_A LERP (0xC6A68/7C/90/A4)
  0x3AB6C mul r1,r6 / 0x3AB70 sar 0xa   stage1 = (dt * avg) >> 10
  0x3AB72 mul r8,r6 / 0x3AB76 sar 0xa   pre    = (stage1 * gain_A) >> 10     <- V62's site
  0x3AB7E mul * polarity ; 0x3AB82-94 clamp +/-0x2000 ; mirrored to gp-0x6adc @0x3AD4E

Usage:  python studies/sessions/v70/v70_r26_lane_and_c6444.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
from v70_rate_lane_gain_model import ROOT, BUILDS, SPEED_CTS_PER_KMH, idiv_trunc   # noqa: E402

TP = 0xBF000
GAIN_A_RECS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)   # tp+0x7a68/7a7c/7a90/7aa4
CROSS_X = 0xC6010
ARM_A_GATE, ARM_A_STATE = 0xC6444, 0xC643E
SAR_R26_STAGE2 = 0x3AB76                              # 0x32AA = sar 0xa, 0x32A9 = sar 0x9


class R26:
    def __init__(self, name, buf):
        self.name, self.buf = name, buf
        self.sar = 10 if struct.unpack_from("<H", buf, SAR_R26_STAGE2)[0] == 0x32AA else 9
        self.gate_live = buf[0x3AA96] == 0xFB
        self.arm_gate = struct.unpack_from("<H", buf, ARM_A_GATE)[0]
        self.arm_state = struct.unpack_from("<H", buf, ARM_A_STATE)[0]
        self.cross = list(struct.unpack_from("<4h", buf, CROSS_X))
        self.X = [list(struct.unpack_from("<4h", buf, r + 2)) for r in GAIN_A_RECS]
        self.Y = [list(struct.unpack_from("<4h", buf, r + 0x0A)) for r in GAIN_A_RECS]

    def ram_table(self, speed_cts):
        k = 0
        while k <= 3 and self.cross[k] <= speed_cts:
            k += 1
        if k == 0:
            return list(self.X[0]), list(self.Y[0])
        if k > 3:
            return list(self.X[3]), list(self.Y[3])
        num, den = speed_cts - self.cross[k - 1], self.cross[k] - self.cross[k - 1]
        lo, hi = k - 1, k
        return ([self.X[lo][i] + idiv_trunc((self.X[hi][i] - self.X[lo][i]) * num, den) for i in range(4)],
                [self.Y[lo][i] + idiv_trunc((self.Y[hi][i] - self.Y[lo][i]) * num, den) for i in range(4)])

    @staticmethod
    def lerp4(X, Y, idx):
        if idx <= X[0]:
            return Y[0]
        if idx >= X[3]:
            return Y[3]
        k = 0
        while idx >= X[k + 1]:
            k += 1
        return Y[k] + idiv_trunc((Y[k + 1] - Y[k]) * (idx - X[k]), X[k + 1] - X[k])

    def gain_a(self, speed_cts, rate_raw, engaged=True, counter671a=0):
        if (engaged if self.gate_live else False):
            return self.arm_gate
        if counter671a >= 5:
            return self.arm_state
        X, Y = self.ram_table(speed_cts)
        return self.lerp4(X, Y, 0 if rate_raw >= 13001 else rate_raw)

    def slope_per_avg(self, speed_cts, rate_raw, **kw):
        """d(r26)/d(dt) = (avg/1024) * gain_A / 2^sar.  Returned WITHOUT the avg factor."""
        return self.gain_a(speed_cts, rate_raw, **kw) / (1 << self.sar)


def scan_tp_disp16(buf, disp):
    """Every 4-byte tp-relative (reg1 = r5) access to tp+disp, per-opcode displacement rules."""
    forms = [("ld.b", 0x38, "d"), ("ld.h", 0x39, "e"), ("ld.w", 0x39, "o"), ("st.b", 0x3A, "d"),
             ("st.h", 0x3B, "e"), ("st.w", 0x3B, "o"), ("ld.bu", None, "bu"), ("ld.hu", 0x3F, "o")]
    out = []
    for mnem, op, kind in forms:
        hw2 = disp if kind == "d" else (disp & 0xFFFE) | (1 if kind in ("o", "bu") else 0)
        for o in ([0x3C | (disp & 1)] if op is None else [op]):
            for reg2 in range(32):
                if reg2 == 0 and not mnem.startswith("st"):
                    continue                                   # escape to the 6-byte form
                pat = struct.pack("<HH", (reg2 << 11) | (o << 5) | 5, hw2)
                i = buf.find(pat)
                while i >= 0:
                    if i % 2 == 0:
                        out.append((i, mnem, reg2, mnem.startswith("st"), "disp16"))
                    i = buf.find(pat, i + 1)
    return sorted(out)


def scan_tp_disp23(buf, disp):
    """The 6-byte extended-displacement tp-relative form."""
    out = []
    for a in range(0, len(buf) - 6, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        if (hw1 & 0x1F) != 5 or (hw1 >> 11) != 0:
            continue
        op = (hw1 >> 5) & 0x3F
        if op not in (0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F):
            continue
        hw2, hw3 = struct.unpack_from("<HH", buf, a + 2)
        d = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
        if d & 0x400000:
            d -= 0x800000
        if d == disp:
            out.append((a, f"op{op:02x}(ext)", hw2 >> 11, op in (0x3A, 0x3B), "disp23"))
    return sorted(out)


def main():
    imgs = {"stock": (ROOT / "stock_fw_dump" / "code.bin").read_bytes()}
    for v in ("v38", "v39", "v42", "v61", "v62", "v65", "v66", "v67", "v68", "v69"):
        imgs[v] = (ROOT / f"_{v}_plain_image.bin").read_bytes()
    R = {k: R26(k, v) for k, v in imgs.items()}
    S = imgs["stock"]

    print("=" * 104)
    print("ITEM 2 -- r26's DELIVERED GAIN vs STOCK  (the avg factor cancels in the ratio)")
    print("=" * 104)
    print("  gain_A LERP records (speed-blended by FUN_0003ad74's SECOND half, same Xcross 0xC6010):")
    for i, a in enumerate(GAIN_A_RECS):
        print(f"    rec{i} @0x{a:05X}  X={R['stock'].X[i]}  Y={R['stock'].Y[i]}")
    speeds = [0, 5, 10, 15, 20, 30, 40, 50, 60, 80, 100]
    scen = [("stock", "stock", dict(engaged=True)), ("V42 (killed)", "v42", dict(engaged=True)),
            ("V62 / V65", "v62", dict(engaged=True)), ("V66", "v66", dict(engaged=True)),
            ("V67/V68 ENGAGED", "v67", dict(engaged=True)),
            ("V67/V68 manual", "v67", dict(engaged=False)),
            ("V69 (eng == man)", "v69", dict(engaged=True))]
    for rate in (0, 600, 1206):
        print(f"\n  rateKey = {rate}   (x STOCK)")
        print(f"  {'build':18s}" + "".join(f"{k:>8d}" for k in speeds) + "   km/h")
        base = {k: R["stock"].slope_per_avg(int(round(k * SPEED_CTS_PER_KMH)), rate, engaged=True)
                for k in speeds}
        for lbl, bn, kw in scen:
            row = [R[bn].slope_per_avg(int(round(k * SPEED_CTS_PER_KMH)), rate, **kw) / base[k]
                   for k in speeds]
            print(f"  {lbl:18s}" + "".join(f"{v:8.3f}" for v in row))
        print(f"  {'-- stock gain_A':18s}"
              + "".join(f"{R['stock'].gain_a(int(round(k * SPEED_CTS_PER_KMH)), rate):8d}" for k in speeds))

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 104)
    print("ITEM 3 -- THE TOTAL RATE-LANE COST, parametric in a = avg/1024  (r24 + r26 sum at 0x3ACC8/CA)")
    print("=" * 104)
    print("  total slope = [ gain_B + a * gain_A ] / 2^sar        a = gp-0x69a4 / 1024, the ONE unknown")
    from v70_rate_lane_gain_model import Build
    Bm = {k: Build(k, v) for k, v in imgs.items()}
    for kmh in (0, 10, 50, 100):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        print(f"\n  {kmh:3d} km/h, rateKey 0   (x STOCK total)")
        print(f"    {'a =':22s}" + "".join(f"{a:>8.2f}" for a in (0.0, 0.25, 0.5, 0.85, 1.0, 1.5, 2.0, 3.0)))
        gB_s = Bm["stock"].gain(sc, 0, engaged=True)
        gA_s = R["stock"].gain_a(sc, 0, engaged=True)
        for lbl, bn, kw in scen:
            row = []
            for a in (0.0, 0.25, 0.5, 0.85, 1.0, 1.5, 2.0, 3.0):
                num = (Bm[bn].gain(sc, 0, **kw) + a * R[bn].gain_a(sc, 0, **kw)) / (1 << Bm[bn].sar)
                den = (gB_s + a * gA_s) / 1024
                row.append(num / den)
            print(f"    {lbl:22s}" + "".join(f"{v:8.3f}" for v in row))
    print("\n  crossover where V67/V68 ENGAGED total falls BELOW STOCK, solved per speed:")
    for kmh in (0, 5, 10, 20, 50, 100):
        sc = int(round(kmh * SPEED_CTS_PER_KMH))
        gB_s, gA_s = Bm["stock"].gain(sc, 0), R["stock"].gain_a(sc, 0)
        gB_v, gA_v = Bm["v67"].gain(sc, 0, engaged=True), R["v67"].gain_a(sc, 0, engaged=True)
        # (gB_v + a*gA_v) == (gB_s + a*gA_s)   ->   a = (gB_v - gB_s) / (gA_s - gA_v)
        a = (gB_v - gB_s) / (gA_s - gA_v) if gA_s != gA_v else float("inf")
        print(f"    {kmh:3d} km/h: gain_B {gB_s}->{gB_v}, gain_A {gA_s}->{gA_v}"
              f"   => below stock when a > {a:.3f}  (gp-0x69a4 > {a * 1024:.0f})")
    print("\n  V69 vs V62 total: (4+a)/(1+a) vs 2.000 at creep  =>  V69 > V62 iff a < 2.000,")
    print("  equal at a = 2.000, below for a > 2.000.  V69 total is >= stock for every a >= 0.")

    # ---------------------------------------------------------------------------------------
    print()
    print("=" * 104)
    print("ITEM 4 -- 0xC6444 BLAST RADIUS AND HISTORY")
    print("=" * 104)
    for disp, nm in ((0x7444, "0xC6444 r26 gate arm"), (0x7446, "0xC6446 r24 gate arm"),
                     (0x743E, "0xC643E r26 state arm"), (0x7440, "0xC6440 r24 state arm")):
        h16 = scan_tp_disp16(S, disp)
        h23 = scan_tp_disp23(S, disp)
        lit = []
        pat = struct.pack("<I", TP + disp)
        i = S.find(pat)
        while i >= 0:
            lit.append(i)
            i = S.find(pat, i + 1)
        print(f"  {nm:24s} disp16={len(h16)} disp23={len(h23)} LE32lit={len(lit)}  -> "
              + " ".join(f"0x{a:05X}:{m}" for a, m, r, st, f in h16 + h23))
    print("\n  float mirrors (V27 desync class), whole image:")
    for val in (512.0, 1536.0, 3072.0, 2560.0, 2664.0):
        pat = struct.pack("<f", val)
        hits, i = [], S.find(pat)
        while i >= 0:
            hits.append(i)
            i = S.find(pat, i + 1)
        aligned = [h for h in hits if h % 4 == 0 and 0xC4000 <= h < 0xD0000]
        print(f"    {val:8.1f} : {len(hits)} image-wide, {len(aligned)} 4-byte-aligned in "
              f"[0xC4000,0xD0000) -> {[hex(x) for x in aligned]}")
    print("\n  CRC block: 0xC6444 and 0xC6446 both live in block #48 [0x0C6000, 0x0C6FFC)")
    print("             => editing 0xC6444 moves the SAME CAL CRC 0xC6FFC and no other block.")
    print("\n  cross-build values:")
    for a, nm in ((ARM_A_GATE, "0xC6444"), (ARM_A_STATE, "0xC643E"), (0xC6446, "0xC6446")):
        print(f"    {nm}: " + "  ".join(f"{k}={struct.unpack_from('<H', imgs[k], a)[0]}"
                                        for k in imgs))


if __name__ == "__main__":
    sys.exit(main())
