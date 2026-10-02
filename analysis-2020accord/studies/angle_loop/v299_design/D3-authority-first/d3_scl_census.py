# -*- coding: utf-8 -*-
r"""d3_scl_census.py -- implementation (b)'s consumer census, second method (Python LE byte scan of the V298 image):
every Format VII load/store whose base register is tp (r5, tp = 0xBF000) and whose disp16 points at the SCL cell 0xC61BE
(tp+0x71BE), the OCL cell 0xC61B4 (tp+0x71B4) and the PCL cell 0xC61BC (tp+0x71BC); plus any 32-bit absolute literal of
the three addresses (register-indirect bases built with movhi/movea).  ANALYSIS ONLY.  Wall time printed.
Format VII ld/st: hw0 = reg2<<11 | op6<<5 | reg1 ; hw1 = disp16 (bit 0 = sub-op for .h/.w).  op6: ld.b 0x38, ld.h/ld.w
0x39, st.b 0x3A, st.h/st.w 0x3B; ld.bu/ld.hu (Format VII ext) 0x3C-0x3F with bit 0 of disp carrying the opcode bit."""
import struct
import time

import numpy as np

import d3_common as D

t0 = time.time()
b = D.v298_image()
hw = np.frombuffer(b[:len(b) // 2 * 2], dtype="<u2").astype(np.int64)
out = []
for cell in (0xC61BE, 0xC61B4, 0xC61BC):
    disp = cell - 0xBF000
    i = np.arange(len(hw) - 1)
    reg1 = hw[i] & 0x1F
    op6 = (hw[i] >> 5) & 0x3F
    d = hw[i + 1] & 0xFFFE
    m = (reg1 == 5) & np.isin(op6, [0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F]) & (d == (disp & 0xFFFE))
    sites = [(int(k) * 2, int(op6[k]), int(hw[k] >> 11)) for k in np.flatnonzero(m)]
    lit = [k for k in range(0, len(b) - 3, 2) if struct.unpack_from("<I", b, k)[0] == cell]
    out.append((cell, sites, lit))
    print(f"cell 0x{cell:05X} (tp+0x{disp:04X}) value {D.u16(b, cell)}: tp-relative accesses at "
          + ", ".join(f"0x{a:05X} op6 0x{o:02X} r{r}" for a, o, r in sites)
          + f" | stores {sum(1 for _, o, _ in sites if o in (0x3A, 0x3B))} | 32-bit literals {lit}")
print(f"wall time {time.time() - t0:.1f} s")
