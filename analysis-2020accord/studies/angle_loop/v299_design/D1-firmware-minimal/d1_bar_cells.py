# -*- coding: utf-8 -*-
"""d1_bar_cells.py -- (1) the V298 image bytes at every cell D1 implementation (a) edits; (2) the proposed angle-mode
bar = (signed 0x1AB tap) / rail on route 79, vs the current bar's pinned share.  Wall < 2 s."""
import glob, os, struct, sys, time
from pathlib import Path
import numpy as np
t0 = time.time()
HERE = Path(__file__).resolve().parent
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
img = Path(sorted(glob.glob(os.path.join(ROOT, "analysis-2020accord", "_v298_*_plain_image.bin")))[0]).read_bytes()
for nm, a, n in (("hard movea", 0xC4C62, 4), ("opp movea", 0xC4C6A, 4), ("cap movea", 0xC4CA2, 4),
                 ("table row0 X,G,S", 0xC4CDA, 6), ("table row1", 0xC4CE0, 6), ("cave end", 0xC4CFC, 8)):
    print(f"  {nm:18s} {a:#x}: {img[a:a+n].hex(' ')}")
print("  row0 =", struct.unpack_from("<HHh", img, 0xC4CDA), " row1 =", struct.unpack_from("<HHh", img, 0xC4CE0))
print("  0xC4D04..0xC4D10 (after the cave):", img[0xC4D04:0xC4D10].hex(' '))
D = np.load(HERE.parents[4] / "analysis-2020accord" / "_scratch" / "cache" / "v280" / "r79_a1f5d2_al.npz")
fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
T = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
t1ab = D["t1ab"]
te4, req = D["te4"], D["req"]
j = np.clip(np.searchsorted(te4, t1ab) - 1, 0, len(te4) - 1)
eng = req[j] > 0.5
bar = np.clip(T / 2461.0, -1, 1)
a = np.abs(bar[eng])
print(f"proposed bar (|T|/2461) on r79 request-engaged 0x1AB frames (n {eng.sum()}): p50 {np.percentile(a,50):.3f} "
      f"p90 {np.percentile(a,90):.3f} p99 {np.percentile(a,99):.3f} max {a.max():.3f}; >= 0.9: {np.mean(a>=0.9)*100:.2f}%, "
      f">= 0.5: {np.mean(a>=0.5)*100:.2f}%  (current angle-mode bar: pinned >= 0.999 on 59.7% -- M5/judge)")
print(f"wall {time.time()-t0:.2f} s")
