"""
c4_function_cal_census.py -- every CALIBRATION reference inside FUN_00028ea6 (body 0x28EA6..0x2A30D, the LKAS
PID; Ghidra get_function_by_address on the V294 program) on the V294 image, so that no cal cell the PID
reads is left off the design-space list.  Method: the c2 scanner (positive-controlled there) restricted to
the body, tp-relative (tp = 0xBF000) accesses + absolute LE32 constants in [0xC0000, 0x100000) (the mov
imm32 bank bases), plus every gp-relative cell for completeness.  For each cal cell: its value on the four
images and every OTHER reader image-wide (so a cell shared with another function is flagged).

Run:  python c4_function_cal_census.py  -> _scratch/out/c4_function_cals.json
"""
import json
import struct
from pathlib import Path

from c1_images_and_cells import load
from c2_reader_census import scan, index, TP

LO, HI = 0x28EA6, 0x2A30E
TWIN = (0x2A30E, 0x2B422)          # the uncalled island (ghidrafill, 2026-09-13)


def main():
    imgs = load()
    b = imgs["v294"][0]
    ins = scan(b)
    ix = index(ins)
    body = [i for i in ins if LO <= i[0] < HI]
    tp_cells = {}
    for a, ln, m, r1, r2, d in body:
        if r1 == 5:
            tp_cells.setdefault(TP + d, []).append((hex(a), m))
    absk = {}
    for a in range(LO, HI - 4, 2):
        v = struct.unpack_from("<I", b, a)[0]
        h0 = b[a - 2] | b[a - 1] << 8 if a >= 2 else 0
        if 0xC0000 <= v < 0x100000 and (h0 & 0xFFE0) == 0x0620:     # mov imm32,reg  (hw0 = 0x0620|reg)
            absk.setdefault(v, []).append(hex(a - 2))
    gp_cells = sorted({-d for a, ln, m, r1, r2, d in body if r1 == 4})
    res = {"tp": {}, "abs": {}, "gp_count": len(gp_cells)}
    print(f"FUN_00028ea6 on V294: {len(body)} gp/tp/other-relative accesses decoded in the body; "
          f"{len(tp_cells)} distinct tp-relative cal cells; {len(absk)} mov-imm32 constants into the cal region; "
          f"{len(gp_cells)} distinct gp cells\n")
    print(f"{'cell':8s} {'w':6s} {'stock':>6s} {'v282':>6s} {'v293':>6s} {'v294':>6s}  in-body sites / readers OUTSIDE the body (twin island marked)")
    for cell in sorted(tp_cells):
        sites = tp_cells[cell]
        w = sites[0][1]
        fmt = {"ld.b": "<b", "ld.bu": "<B", "ld.h": "<h", "ld.hu": "<H", "ld.w": "<i"}.get(w, "<H")
        vals = [struct.unpack_from(fmt, imgs[k][0], cell)[0] for k in ("stock", "v282", "v293", "v294")]
        outside = [(hex(a), mm) for a, mm, ln in ix.get((5, cell - TP), []) if not (LO <= a < HI)]
        tag = []
        for a, mm in outside:
            ai = int(a, 16)
            tag.append(f"{a}{'(twin)' if TWIN[0] <= ai < TWIN[1] else ''}")
        res["tp"][hex(cell)] = {"load": w, "values": vals, "in_body": sites, "outside": tag}
        chg = " <-- differs" if len(set(vals)) > 1 else ""
        print(f"{cell:#08x} {w:6s} " + " ".join(f"{v:6d}" for v in vals) + f"  {len(sites)} in body; outside: {tag or '-'}{chg}")
    print("\nmov imm32 bank bases in the body (per-variant pointer families, 28 x LE32, selector gp-0x674e):")
    for v, sites in sorted(absk.items()):
        res["abs"][hex(v)] = sites
        print(f"   {v:#07x} at {sites}")
    (Path(__file__).resolve().parent / "_scratch" / "out").mkdir(exist_ok=True)
    (Path(__file__).resolve().parent / "_scratch" / "out" / "c4_function_cals.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
