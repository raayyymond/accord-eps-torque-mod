# -*- coding: utf-8 -*-
r"""d4_gate1.py -- DESIGNER D4: GATE 1 (RAM ownership) census of the ONE new state word of implementation (b),
gp-0x6a32 (0xFEDF15CE, s16), ON THE V298 IMAGE (sha 177abf04...), byte-granular, every gp form the kit's V289 census
decodes (4-byte ld/st of every width, the ld.bu parity steal, Format VIII bit-ops, the 6-byte ext displacement form,
addi/movea materialisations), plus dword literals and movhi/low-half pairs, plus its .data boot value.
The scanner is build_v289_tva.gp_accesses (positive controls re-run here).  Ghidra xrefs are the second method
(reported in the design page).  Writes _scratch/v299_D4/gate1.txt.   usage: python d4_gate1.py   (< 10 s)
"""
import contextlib
import hashlib
import io
import os
import sys
import time
from pathlib import Path

T0 = time.time()
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[4]
sys.path.insert(0, str(KIT / "analysis-2020accord" / "builds" / "v108_plus"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
with contextlib.redirect_stdout(io.StringIO()):
    import build_v289_tva as B  # noqa: E402

IMG = Path(os.environ["ACCORD_FIRMWARE_ROOT"]) / "analysis-2020accord" / (
    "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin")
img = IMG.read_bytes()
sha = hashlib.sha256(img).hexdigest()
L = []


def P(s=""):
    print(s)
    L.append(s)


P("V298 image %s (%s)" % (IMG.name[:40], sha[:16]))
assert sha.startswith("177abf04"), sha
acc = B.gp_accesses(img)
P("gp-based accesses decoded in [0x%X, 0x%X): %d" % (B.START, B.END, len(acc)))
# positive controls (expected counts from the V289 census; the angle-loop edits change some -- printed, not asserted)
for d, w in ((-0x6CF8, 4), (-0x6A00, 2), (-0x4F60, 2), (-0x4F68, 2), (-0x6DD0, 4), (-0x1514, 1), (-0x6B4C, 2)):
    h = B.hits_in(acc, d, w)
    P("  control gp%+#07x (%d B): %d hits %s" % (d, w, len(h), [(hex(a), k) for a, k, _ in h][:10]))
P("\nTHE STATE WORD gp-0x6a32 (2 B) and its 8-byte neighbourhood:")
for d, w in ((-0x6A32, 2), (-0x6A34, 2), (-0x6A30, 2), (-0x6A36, 8)):
    h = B.hits_in(acc, d, w)
    P("  gp%+#07x (%d B): %d hits %s" % (d, w, len(h), [(hex(a), k, hex(dd & 0xFFFF)) for a, k, dd in h]))
lit, pairs = B.literal_and_movhi(img, -0x6A32)
P("  dword literal of 0x%08X: %s ; movhi/low-half pairs: %s" % ((B.GP_BASE - 0x6A32) & 0xFFFFFFFF, lit, pairs))
near = [(hex(a), hex(d & 0xFFFF)) for a, k, d, w in acc if k == "addi/movea" and -0x6A32 - 0x100 <= d <= -0x6A32 + 0x40]
P("  addi/movea materialising a gp base within [-0x100, +0x40] of the word: %s" % near)
bv, where = B.boot_value(img, -0x6A32, 2)
P("  boot value: %s (%s)" % (bv.hex() if bv else bv, where))
P("\nwall %.1f s" % (time.time() - T0))
(KIT / "_scratch" / "v299_D4" / "gate1.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
