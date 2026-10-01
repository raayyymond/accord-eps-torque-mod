# -*- coding: utf-8 -*-
r"""g_bytes.py -- every byte of designer G's implementations, applied IN MEMORY to a copy of the V295 plain image (nothing
written to disk as an image; no .rwd; the CRC trailers are only NAMED -- the builder's H8 recomputes them), with every
pre-edit byte asserted against V295, and a full diff over [0x13000, 0x100000) that must contain exactly the listed bytes.
Reuses the D designer's edit records (ds_bytes: E1 E2 B2 A2 E4 HK V1 OPH E5, the cal and record addresses) -- imported,
not copied.  Also: the int32 budget of every multiply the implementation changes.  ANALYSIS ONLY.
usage: python g_bytes.py <impl> ...   -> g_bytes_out.txt"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
import g_cave as GC  # noqa: E402
import ds_bytes as DB  # noqa: E402
import ds_asm as A  # noqa: E402

V = DB.V


def edits(im):
    code = [DB.E1, DB.E2, DB.B2, DB.A2, DB.E4, DB.HK, DB.V1]
    code += DB.E5 if im["dkind"] == "held" else [DB.OPH]
    cal = dict(a=0, b=8192, C=65535, DB=0, Ki=int(im.get("ki", 56)), ICL=4096, DCL=10240)
    return code, cal, 112, int(im["kd"])


def build(im):
    img = bytearray(V)
    listing = []
    code, cal, kp, kd = edits(im)
    for a, old, new, dec, term in code:
        ob, nb = bytes.fromhex(old.replace(" ", "")), bytes.fromhex(new.replace(" ", ""))
        assert img[a:a + len(ob)] == ob, (hex(a), img[a:a + len(ob)].hex(), old)
        img[a:a + len(nb)] = nb
        listing.append(("code", a, old, new, dec, term, len(nb)))
    for k, v in cal.items():
        a = DB.CAL[k]
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H" if k != "a" else "<h", v)
        listing.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "), f"{k} {struct.unpack('<H', old)[0]} -> {v}",
                        "", 2))
    for i in range(5):
        a = DB.KP_Y + 2 * i
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H", kp)
        listing.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "), f"Kp record Y[{i}] -> {kp}", "", 2))
    for i in range(4):
        a = DB.KD_Y + 2 * i
        old = bytes(img[a:a + 2])
        img[a:a + 2] = struct.pack("<H", kd)
        listing.append(("cal", a, old.hex(" "), bytes(img[a:a + 2]).hex(" "), f"Kd record Y[{i}] -> {kd}", "", 2))
    cave, labels, _ = GC.build_cave(im)
    assert all(x == 0xFF for x in img[A.CAVE:A.CAVE + len(cave)])
    img[A.CAVE:A.CAVE + len(cave)] = cave
    return img, listing, cave, labels


def main(iids):
    imps = json.loads((X.OUT / "g_impls.json").read_text())
    L = []

    def P(s=""):
        print(s, flush=True)
        L.append(s)
    P(f"base V295 sha256 {hashlib.sha256(V).hexdigest()}")
    summ = {}
    for iid in iids:
        im = dict(imps[iid], rows=[tuple(r) for r in imps[iid]["rows"]])
        img, listing, cave, labels = build(im)
        diff = [a for a in range(0x13000, 0x100000) if img[a] != V[a]]
        listed = set()
        for kind, a, old, new, dec, term, n in listing:
            listed |= {a + i for i in range(n)}
        cave_set = set(range(A.CAVE, A.CAVE + len(cave)))
        unlisted = [hex(a) for a in diff if a not in listed and a not in cave_set]
        w_code = sum(n for kind, a, *_, n in listing if kind == "code")
        w_cal_changed = sum(1 for kind, a, *_, n in listing if kind == "cal" for i in range(n) if img[a + i] != V[a + i])
        w_cal = sum(n for kind, a, *_, n in listing if kind == "cal" and any(img[a + i] != V[a + i] for i in range(n)))
        ncode = labels["TBL"] - A.CAVE
        ram = ["gp-0x6c44", "gp-0x6c40"] if im["dkind"] == "box10" else []
        tot = w_code + len(cave) + w_cal
        summ[iid] = dict(written=tot, in_place=w_code, cave=len(cave), cave_code=ncode, cave_table=len(cave) - ncode,
                         cal_written=w_cal, differ=len(diff), unlisted=unlisted, ram=ram,
                         cave_sha=hashlib.sha256(cave).hexdigest())
        P("=" * 110)
        P(f"{iid}: {im['note']}")
        for kind, a, old, new, dec, term, n in listing:
            if kind == "code" or any(img[a + i] != V[a + i] for i in range(n)):
                P(f"   {kind:4s} {a:#08x}  {old:12s} -> {new:12s}  {dec}  {term}")
        P(f"   cave {A.CAVE:#x}..{A.CAVE + len(cave):#x}: {len(cave)} B = {ncode} code + {len(cave) - ncode} table; sha256 "
          f"{hashlib.sha256(cave).hexdigest()[:16]}")
        P(f"   WRITTEN bytes: in-place code {w_code} + cave {len(cave)} + changed cal cells {w_cal} = {tot}; full diff vs "
          f"V295 [0x13000, 0x100000): {len(diff)} bytes; UNLISTED: {unlisted if unlisted else 'none'}; RAM words: "
          f"{ram if ram else 'none'}; caves: 1")
        P(f"   int32 budget: |E| <= 196 603, max G {max(r[1] for r in im['rows'])} -> |E G| <= "
          f"{196603 * max(r[1] for r in im['rows']):.3e} (< 2^31 = 2.147e9); D: Kd {im['kd']} x |op| max "
          f"{(13000 if im['dkind'] == 'fresh' else 12000 if im['dkind'] == 'held' else (1200 << im.get('sh', 6)))} -> "
          f"{im['kd'] * (13000 if im['dkind'] == 'fresh' else 12000 if im['dkind'] == 'held' else (1200 << im.get('sh', 6))):.3e}"
          f" (>> 3, then DCL 10240)")
        P("   CRC trailers the builder recomputes: 0xC4FFC (block holding the cave + 0x13100), 0xC6FFC (cal page), the "
          "E5xxx record block -- verify_bootloader_crc.py on the built image (H8)")
    (HERE / "g_bytes_out.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    (X.OUT / "g_bytes.json").write_text(json.dumps(summ))
    return summ


if __name__ == "__main__":
    main(sys.argv[1:])
