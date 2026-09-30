"""
c1_images_and_cells.py -- V295 census, step 1: verify the four images, diff the code region, and read
every calibration cell that shapes the LKAS PID loop (FUN_00028ea6) on stock / V282 / V293 / V294.

Byte work only (Python, little-endian). Every address below was taken from the Ghidra DECOMPILE of
FUN_00028ea6 on the V294 program (/advC/_v294_..., spot-checked against the file at 0x28FA4, 0x29D76,
0xC63E0..0xC63EF) -- tp = 0xBF000, so tp+0x73E8 = 0xC63E8 (anchored: stock reads 923 there).

Run:  python c1_images_and_cells.py            (writes _scratch/out/c1_cells.json next to this file)
"""
import hashlib
import json
import os
import struct
from pathlib import Path

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
IMAGES = {
    "stock": ROOT / "stock_fw_dump" / "code.bin",
    "v282": ROOT / "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "v293": ROOT / "_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
    "v294": ROOT / "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
}
EXPECT_SHA = {
    "v294": "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85",
    "v293": "f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17",
    "v282": "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe",
}
TP = 0xBF000
SEL = 7          # the live variant selector (gp-0x674e), MEASURED on the wire (memory: record 11 TVCA4)
NREC = 28        # per-variant bank = 28 LE32 pointers, stride 4


def load():
    out = {}
    for k, p in IMAGES.items():
        b = p.read_bytes()
        h = hashlib.sha256(b).hexdigest()
        if k in EXPECT_SHA:
            assert h == EXPECT_SHA[k], (k, h)
        out[k] = (b, h)
    return out


def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]
def u8(b, a): return b[a]


# ---- scalar cells: (address, width/sign as READ BY THE CODE, what) -------------------------------------
# width/sign column = the load instruction the decompile shows (ld.h -> s16, ld.hu -> u16, ld.b/ld.bu -> byte)
SCALARS = [
    # demand side
    (0xC64F0, "u8",  "idx clamp +  (ld.bu tp+0x74f0)"),
    (0xC64F1, "u8",  "idx clamp -  (ld.bu tp+0x74f1)"),
    (0xC64B8, "u8",  "driver-override idx CUT threshold on gp-0x682f (|bar|>>5) (ld.bu tp+0x74b8)"),
    # feedback former
    (0xC613A, "u16", "rate producer Q15 scale (FUN_0003f776): x = pol*((raw*48*[C613A])>>15)"),
    (0xC63E8, "s16", "fb-lag pole a  (ld.h  tp+0x73e8 @0x28F8A)"),
    (0xC63EA, "u16", "fb-lag gain b  (ld.hu tp+0x73ea @0x28F86)"),
    (0xC62E6, "u16", "fb operand clamp C (ld.hu tp+0x72e6 x3)"),
    (0xC63E2, "u16", "sibling (torsion-bar) filter coef (tp+0x73e2) -> gp-0x3d34"),
    (0xC63E4, "u16", "sibling (torsion-bar) filter coef (tp+0x73e4) -> gp-0x3d34"),
    # PID
    (0xC62E4, "u16", "I deadband on E>>5 (ld.hu tp+0x72e4)"),
    (0xC63E6, "u16", "Ki (ld.hu tp+0x73e6)"),
    (0xC61BA, "u16", "I clamp cell: ICL = (v<<10)>>3 ; I>>7 bounded at v"),
    (0xC61BC, "u16", "P clamp (ld.hu tp+0x71bc)"),
    (0xC61B6, "u16", "D clamp (ld.hu tp+0x71b6)"),
    (0xC61BE, "u16", "sum clamp (ld.hu compare / ld.h assign)"),
    # post-PID
    (0xC63EC, "s16", "output-lag pole a (ld.h tp+0x73ec)"),
    (0xC63EE, "u16", "output-lag gain b (ld.hu tp+0x73ee)"),
    (0xC64A3, "u8",  "output gate arm (ld.b tp+0x74a3) ==1 arms the |y|<=thr / sign-flip gate while gp-0x6806==0"),
    (0xC61B8, "s16", "output gate threshold (ld.h tp+0x71b8)"),
    (0xC6CD0, "s16", "forward gain (ld.h tp+0x7cd0 on V57+/V282+ ; stock reads tp+0x746c)"),
    (0xC646C, "s16", "stock forward-gain cell (shared sensor-scale cal, 5 live readers)"),
    (0xC61B4, "u16", "lane output clamp (ld.hu tp+0x71b4) -> gp-0x6b38"),
    (0xC61B2, "u16", "forward clamp in FUN_0002b422 (tp+0x71b2) -> ep request array"),
    # engagement ramp cells (gp-0x69b0 state machine)
    (0xC62E8, "u16", "speed window hi (tp+0x72e8) for bVar2"),
    (0xC62EA, "u16", "speed window lo (tp+0x72ea) for bVar2"),
    (0xC63F2, "u16", "cmd-valid min on gp-0x69aa (tp+0x73f2)"),
    (0xC63F4, "u16", "ramp step (tp+0x73f4)"),
    (0xC63F6, "u16", "ramp step (tp+0x73f6)"),
    (0xC63F8, "s16", "ramp up step (tp+0x73f8)"),
    (0xC63FA, "u16", "ramp step (tp+0x73fa)"),
    (0xC63FC, "s16", "ramp up step (tp+0x73fc)"),
    # published scale factors gp-0x697e / gp-0x697c
    (0xC63DA, "u16", "gp-0x697e target (tp+0x73da) when gp-0x679e==1"),
    (0xC63DC, "u16", "gp-0x697e target (tp+0x73dc) otherwise"),
    (0xC63DE, "u16", "gp-0x697c target (tp+0x73de) when gp-0x679e==1"),
    (0xC63E0, "u16", "gp-0x697c target (tp+0x73e0) otherwise"),
    # dither addend gp-0x6b2c (gp-0x3d37 state machine, gated gp-0x6809==1)
    (0xC6288, "u16", "addend state-machine delay count (tp+0x7288)"),
    (0xC628A, "u16", "addend period count (tp+0x728a)"),
    (0xC64DE, "u8",  "addend half-period (tp+0x74de)"),
    # r24 sibling lane engaged arm
    (0xC6446, "u16", "r24 lane ENGAGED ARM (FUN_0003aa2c, tp+0x7446)"),
]

# ---- small inline LERP tables inside the 0xC6xxx page (tp-relative; X then Y) ------------------------
INLINE = [
    ("activity LERP (axis gp-0x6830)", 0xC6976, 4, "X at 0xC6976.., Y at 0xC697E.. (decompile: tp+0x7976/797c/797e/7984)"),
    ("gp-0x680a damper-mode LERP (axis |fb>>5| gp-0x6a34)", 0xC6712, 8, "X 0xC6712..0xC6720, Y 0xC6722..0xC6730"),
    ("dither addend LERP (axis speed gp-0x6a5e)", 0xC6736, 4, "X 0xC6736..0xC673C, Y 0xC673E..0xC6744"),
]

# ---- per-variant banks (pointer family of 28, selector 7). layout: +0 count?, X at +2, Y after X -------
BANKS = [
    ("LIM_speed (cmd clamp) 0xCB844", 0xCB844, 9),
    ("assist map 0xC9A88", 0xC9A88, 10),
    ("Kp 0xCB994", 0xCB994, 5),
    ("Kd 0xCB7D4", 0xCB7D4, 4),
    ("G override (bVar1: gp-0x6803==2) 0xCBA04", 0xCBA04, 4),
    ("G normal (sign(cmd)!=sign(bar) arm) 0xCB8B4", 0xCB8B4, 4),
    ("G override (bVar1) 0xCBA74", 0xCBA74, 4),
    ("G normal (sign(cmd)==sign(bar) arm) 0xCB924", 0xCB924, 4),
    ("taper A 0xCBB54 (axis gp-0x6830)", 0xCBB54, 6),
    ("taper B 0xCBC34 (axis gp-0x6830)", 0xCBC34, 6),
    ("taper C 0xCBAE4 (axis gp-0x682f)", 0xCBAE4, 6),
    ("taper D 0xCBBC4 (axis gp-0x682f)", 0xCBBC4, 6),
]


def rd(b, a, w):
    return {"u8": u8, "s16": s16, "u16": u16}[w](b, a)


def rec(b, bank, n, sel):
    p = u32(b, bank + 4 * sel)
    X = [u16(b, p + 2 + 2 * i) for i in range(n)]
    Y = [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]
    return p, u16(b, p), X, Y


def main():
    imgs = load()
    out = {"sha256": {k: v[1] for k, v in imgs.items()}}
    print("SHA256:")
    for k, (_, h) in imgs.items():
        print(f"  {k:6s} {h}")

    # code-region diffs (never whole-file: 0xFF filler below 0x13000)
    print("\nCODE-REGION DIFF [0x13000, 0xC0000) and CAL [0xC0000, 0x100000):")
    diffs = {}
    for a_, b_ in (("stock", "v294"), ("v282", "v294"), ("v293", "v294")):
        A, B = imgs[a_][0], imgs[b_][0]
        code = [i for i in range(0x13000, 0xC0000) if A[i] != B[i]]
        cal = [i for i in range(0xC0000, 0x100000) if A[i] != B[i]]
        diffs[f"{a_}->{b_}"] = {"code": [hex(i) for i in code], "cal_count": len(cal)}
        print(f"  {a_}->{b_}: code bytes differ = {len(code)} at {[hex(i) for i in code]} ; cal bytes differ = {len(cal)}")
    out["diffs"] = diffs

    print("\nSCALAR CELLS (value as the code reads it):")
    print(f"  {'addr':8s} {'w':4s} " + " ".join(f"{k:>7s}" for k in imgs) + "  what")
    sc = {}
    for a, w, what in SCALARS:
        vals = {k: rd(imgs[k][0], a, w) for k in imgs}
        sc[hex(a)] = {"w": w, "what": what, **vals}
        print(f"  {a:#08x} {w:4s} " + " ".join(f"{vals[k]:7d}" for k in imgs) + f"  {what}")
    out["scalars"] = sc

    print("\nINLINE LERP TABLES (0xC6xxx page):")
    il = {}
    for name, x0, n, note in INLINE:
        row = {}
        for k in imgs:
            b = imgs[k][0]
            X = [u16(b, x0 + 2 * i) for i in range(n)]
            Y = [s16(b, x0 + 2 * n + 2 * i) for i in range(n)]
            row[k] = {"X": X, "Y": Y}
        il[name] = row
        print(f"  {name}: {note}")
        for k in imgs:
            print(f"     {k:6s} X={row[k]['X']} Y={row[k]['Y']}")
    out["inline"] = il

    print(f"\nPER-VARIANT BANKS, selector {SEL} (record ptr = LE32 at bank + 4*sel):")
    bk = {}
    for name, base, n in BANKS:
        row = {}
        for k in imgs:
            b = imgs[k][0]
            p, cnt, X, Y = rec(b, base, n, SEL)
            # all-28 census of Y (is the bank flat across variants?)
            ys = set()
            ptrs = set()
            for s in range(NREC):
                pp, _, _, YY = rec(b, base, n, s)
                ys.add(tuple(YY))
                ptrs.add(pp)
            row[k] = {"rec": hex(p), "count_hw": cnt, "X": X, "Y": Y, "distinct_Y_over_28": len(ys), "distinct_ptrs": len(ptrs)}
        bk[name] = row
        print(f"  {name}")
        for k in imgs:
            r = row[k]
            print(f"     {k:6s} rec {r['rec']} cnt {r['count_hw']:3d} X={r['X']} Y={r['Y']}  (28 recs: {r['distinct_ptrs']} ptrs, {r['distinct_Y_over_28']} distinct Y)")
    out["banks"] = bk

    od = Path(__file__).resolve().parent / "_scratch" / "out"
    od.mkdir(exist_ok=True)
    (od / "c1_cells.json").write_text(json.dumps(out, indent=1))
    print("\nwrote", od / "c1_cells.json")


if __name__ == "__main__":
    main()
