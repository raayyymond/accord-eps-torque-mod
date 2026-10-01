# -*- coding: utf-8 -*-
"""r2a_listing.py -- the cave listing (address, bytes, instruction, the loop term) of every implementation, from the
same two-pass assembly r2a_bytes.py verifies.  ANALYSIS ONLY.  usage: python r2a_listing.py  (writes c2_cave_<impl>.lst)"""
import r2a_common as R
import ds_asm as A

for impl in R.IMPLS:
    tbl = R.tables()[impl]
    code, labels, lines = A.assemble(R.IMPLS[impl]["listing"], tbl)
    out = [f"{impl}: cave at {A.CAVE:#x}, {len(code)} bytes = {labels['TBL'] - A.CAVE} code + "
           f"{len(code) - (labels['TBL'] - A.CAVE)} table; entered by jarl 0xC4C00, r6 from 0x29D76 (r6 = 0x29D7A)"]
    for pc, lab, ins, bs, com in lines:
        if ins[0] == "half" and lab != "TBL":
            continue
        out.append(f"  {pc:#07x} {lab:6s} {bs:18s} {str(ins):40s} {com}")
    out.append("  table rows (X = gp-0x6a5e counts = 230.4 per m/s, G, S Q12): " +
               " ".join(f"({x}, {g}, {s})" for x, g, s in tbl))
    (R.HERE / f"c2_cave_{impl}.lst").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out) if impl in ("P2", "F2") else impl)
