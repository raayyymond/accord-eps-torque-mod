# -*- coding: utf-8 -*-
r"""adv_ig_v297_inputs.py -- ADVERSARY INTERLOCKS-GATES, V297.  READ-ONLY.  Writes nothing but stdout.

There is no V297 image.  This script (a) proves that from the filesystem, and (b) checks the builder's
two input claims from BYTES, independent of rb_build/e2_asm/ds_asm (no kit import):
  C1  C3B-F flight cave == C3B-F score cave (byte-identical), sha256[:12] == 9de9365fa952
  C2  C3B-P flight cave sha256[:12] == 9a10cdc4ec75, = score cave with a 4->6 B splice and NO relink:
      flight[:i] == score[:i]  and  flight[i+6:] == score[i+4:]  (pure +2 shift of everything after)
      => every absolute pointer into the post-splice region is stale by -2, every PC-relative branch
         located after the splice whose target is outside the shifted region lands +2.
  Positive control: the scanners below must find the score cave's own `mov imm32,r9` (hw1 0x0629) and a
  `jr disp32` (hw1 0x02E0) whose target is a known return (RET 0x29D7A / FRZ_RET 0x29D7E, ds_asm constants
  quoted here as numbers, not imported).
usage: python adv_ig_v297_inputs.py
"""
import hashlib, os, struct, glob
from pathlib import Path

KIT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")
FW = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares")
RB = KIT / "analysis-2020accord/studies/angle_loop/c3/rev2B"
CAVE, RET, FRZ_RET, SKIP = 0xC4C00, 0x29D7A, 0x29D7E, 0x2A164   # quoted from ds_asm.py / rb_build.py text

def hx(p): return bytes(int(t, 16) for t in Path(p).read_text().split())
def sh(b): return hashlib.sha256(b).hexdigest()

print("== F0: V297 artifacts on disk ==")
pats = [FW/"analysis-2020accord/_v297*", FW/"flashing-2020accord/rwd/*V297*", FW/"flashing-2020accord/rwd/*A16A*",
        FW/"flashing-2020accord/rwd/*REHEADERED*", KIT/"analysis-2020accord/builds/v108_plus/build_v297*"]
hits = [h for p in pats for h in glob.glob(str(p))]
print("  hits:", hits if hits else "NONE")

print("== F8: revert originals ==")
REC = {"_v295_*_plain_image.bin": "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed",
       "_v294_*_plain_image.bin": "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"}
for pat, want in REC.items():
    for f in glob.glob(str(FW/"analysis-2020accord"/pat)):
        print(f"  {Path(f).name[:40]}... {sh(Path(f).read_bytes())[:16]} {'OK' if sh(Path(f).read_bytes())==want else 'MISMATCH'}")
for pat, want in {"*V295-*.rwd": "f42a06bda5a737eb", "*V294-*.rwd": "a2b418f061160f66"}.items():
    for f in glob.glob(str(FW/"flashing-2020accord/rwd")+"/39990-TVA,A160-"+pat):
        print(f"  {Path(f).name[:40]}... {sh(Path(f).read_bytes())[:16]} {'OK' if sh(Path(f).read_bytes()).startswith(want) else 'MISMATCH'}")

def scan(code, base):
    """aligned-agnostic scan at every even offset; returns mov-imm32 r9 values and jr disp32 targets."""
    movs, jrs = [], []
    for o in range(0, len(code) - 5, 2):
        h1 = struct.unpack_from("<H", code, o)[0]
        if h1 == 0x0629:                                   # mov imm32, r9  (Format VI, reg2=0, op 110001)
            movs.append((base + o, struct.unpack_from("<I", code, o + 2)[0]))
        if h1 == 0x02E0:                                   # jr disp32 (Format VI, PC-relative)
            d = struct.unpack_from("<i", code, o + 2)[0]
            jrs.append((base + o, (base + o + d) & 0xFFFFFFFF))
    return movs, jrs

print("== C1/C2: cave hex ==")
F, Fs, P, Ps = (hx(RB/n) for n in ("c3b_cave_C3B-F.hex", "c3b_cave_C3B-F_score.hex", "c3b_cave_C3B-P.hex", "c3b_cave_C3B-P_score.hex"))
for n, b in (("F flight", F), ("F score", Fs), ("P flight", P), ("P score", Ps)):
    print(f"  {n:9s} {len(b):4d} B sha {sh(b)[:12]}")
print("  C1 F flight == F score:", F == Fs)
i = next(k for k in range(len(Ps)) if P[k] != Ps[k])
print(f"  C2 first diff at cave offset {i:#x} (pc {CAVE+i:#x}); prefix equal {P[:i]==Ps[:i]}; "
      f"tail is pure +2 shift {P[i+6:]==Ps[i+4:]}; len diff {len(P)-len(Ps)}")
print(f"     score[{i:#x}:+4] = {Ps[i:i+4].hex(' ')}   flight[{i:#x}:+6] = {P[i:i+6].hex(' ')}")
for n, b in (("P score", Ps), ("P flight", P), ("F flight", F)):
    movs, jrs = scan(b, CAVE)
    print(f"  {n}: mov imm32,r9 -> {[ (hex(a), hex(v)) for a,v in movs ]}")
    print(f"  {n}: jr disp32    -> {[ (hex(a), hex(t)) for a,t in jrs ]}")
# where does the table really sit?  The table is the tail of the cave after the code; the score cave's
# pointer value v_s locates it (offset v_s-CAVE); in flight the same bytes sit at +2.
ms, _ = scan(Ps, CAVE); mf, _ = scan(P, CAVE)
if ms and mf:
    vs, vf = ms[0][1], mf[0][1]
    off = vs - CAVE
    print(f"  table: score ptr {vs:#x} (offset {off:#x}); flight ptr {vf:#x}; flight table bytes actually at "
          f"{CAVE+off+2:#x}  -> ptr stale by {vf-(CAVE+off+2):+d}")
    print(f"     score bytes @ptr  : {Ps[off:off+8].hex(' ')}\n     flight bytes @ptr : {P[off:off+8].hex(' ')}"
          f"\n     flight bytes @ptr+2: {P[off+2:off+10].hex(' ')}")

print("== Format V jr disp22 (hw1 & 0xFFC0 == 0x0780, hw2 bit0 == 0, target even) ==")
def scan_jr22(code, base):
    out = []
    for o in range(0, len(code) - 3, 2):
        h1, h2 = struct.unpack_from("<HH", code, o)
        if (h1 & 0xFFC0) == 0x0780 and (h2 & 1) == 0:
            d = ((h1 & 0x3F) << 16) | h2
            if d & 0x200000: d -= 0x400000
            out.append((base + o, (base + o + d) & 0xFFFFFFFF))
    return out
KNOWN = {RET: "RET 0x29D7A", FRZ_RET: "FRZ_RET 0x29D7E", SKIP: "SKIP 0x2A164"}
for n, b in (("P score", Ps), ("P flight", P), ("F flight", F)):
    js = scan_jr22(b, CAVE)
    ext = [(hex(a), hex(t), KNOWN.get(t, "INTRA" if CAVE <= t < CAVE + len(b) else "??")) for a, t in js]
    print(f"  {n}: {ext}")
print("  positive control = the score cave must show at least one jr to RET/FRZ_RET (else this scan's null is void)")
