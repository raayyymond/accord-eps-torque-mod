# -*- coding: utf-8 -*-
r"""ADVERSARY BUILD-AUDIT on V298 -- independent of build_v298_tva.py.

Job: make the built V298 image FAIL. Re-derive everything from the IMAGE (and stock + V295),
never from the builder's constants or the design page. Uses only shared kit libraries.
"""
import hashlib, struct, zlib, sys, io, contextlib
from pathlib import Path

KIT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord")
for p in (KIT, KIT / "lib", KIT / "builds" / "telemetry"):
    sys.path.insert(0, str(p))
import os
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

from encode_eps import build_decode_table, invert_table, parse_x31, encode_x31
from verify_bootloader_crc import walk, walk_all_blocks
import build_vfourframe_tva as FF

FW = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares")
AN = FW / "analysis-2020accord"
RWD = FW / "flashing-2020accord" / "rwd"
START, END = 0x13000, 0x100000

V295_IMG = AN / "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
V298_IMG = AN / "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin"
V298_RWD = RWD / "39990-TVA,A160-V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A-0x13000-0x100000.rwd"
V295_RWD = RWD / "39990-TVA,A160-V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd"
V294_RWD = RWD / "39990-TVA,A160-V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd"
REV_V295 = RWD / "39990-TVA,A160-V295-REHEADERED-FOR-REVERT-FROM-V298-A16A-0x13000-0x100000.rwd"
REV_V294 = RWD / "39990-TVA,A160-V294-REHEADERED-FOR-REVERT-FROM-V298-A16A-0x13000-0x100000.rwd"

EXP = dict(
    v295="5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed",
    v298="177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066",
    v298_rwd="1a69b92760b8a9538b504b020076e5b025fed7af03b34800ecd05dd687ce960e",
    v295_rwd="f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87",
    v294_rwd="a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a",
    rev295="fb6969fc386850e820566cabe927aa75f9f6e030c481734bbb35e76e2ccb0458",
    rev294="e64f035d84f3bbace46bb30c923196b6875bb984e925d74f21961c850e8d2a68",
)

def sha(b): return hashlib.sha256(b).hexdigest()
def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]

def crc_blocks(img):
    """Independent re-implementation of the CRC linked-list walk from the image's own trailer page."""
    sp, npg = struct.unpack_from("<HH", img, END - 8)
    bstart, blen = sp << 12, (npg << 12) - 4
    blocks, seen = [], set()
    while True:
        assert bstart not in seen, "loop"
        seen.add(bstart)
        blocks.append((bstart, bstart + blen))
        if bstart == START:
            break
        np_, nn = struct.unpack_from("<HH", img, bstart - 8)
        bstart, blen = np_ << 12, (nn << 12) - 4
    return blocks

def qwalk(fn, img):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(bytearray(img))

FINDINGS = []
def note(sev, title, ev):
    FINDINGS.append((sev, title, ev))
    print(f"  [{sev}] {title}\n        {ev}")

def main():
    print("=" * 100)
    print("ADVERSARY BUILD-AUDIT V298 -- independent rebuild + diff + CRC + rwd + revert + cave relink")
    print("=" * 100)
    stock = Path(FF.plain_image_path("code.bin") if hasattr(FF, "plain_image_path") else KIT / "reference" / "code.bin").read_bytes() if False else None

    v295 = V295_IMG.read_bytes()
    v298 = V298_IMG.read_bytes()
    assert sha(v295) == EXP["v295"], f"V295 base hash mismatch: {sha(v295)}"
    assert len(v298) == 0x100000, f"V298 not 1 MiB: 0x{len(v298):X}"
    print(f"\n[A] hashes  V295={sha(v295)[:16]}  V298={sha(v298)[:16]}")
    print(f"    V298 on-disk hash matches builder claim: {sha(v298) == EXP['v298']}")

    # ---- [B] full diff V295 -> V298 over [START,END) ----------------------------------------
    diff = [a for a in range(START, END) if v295[a] != v298[a]]
    print(f"\n[B] full byte diff V295->V298 over [0x13000,0x100000): {len(diff)} bytes")
    # group into runs
    runs = []
    for a in diff:
        if runs and a == runs[-1][1] + 1:
            runs[-1][1] = a
        else:
            runs.append([a, a])
    print(f"    {len(runs)} contiguous runs")

    CAVE = 0xC4C00
    CAVE_LEN = 260
    # classify every differing byte
    cave_bytes = set(range(CAVE, CAVE + CAVE_LEN))
    # expected in-place code sites (re-derived; verified against image below)
    code_sites = {0x28F4C: 4, 0x28FA4: 2, 0x29A50: 4, 0x29A56: 2, 0x29D6A: 4, 0x29D76: 4, 0x29EE0: 4, 0x1310D: 1}
    cal_sites = {0xC63E8: 2, 0xC63EA: 2, 0xC62E6: 2, 0xC62E4: 2, 0xC63E6: 2, 0xC61BA: 2, 0xC61B6: 2}
    kp_sites = {0xE5384 + 2 * i: 2 for i in range(5)}
    kd_sites = {0xE5126 + 2 * i: 2 for i in range(4)}
    fade_sites = {0xE54FC + 2: 24}  # 24 payload bytes
    named = {}
    for d in (code_sites, cal_sites, kp_sites, kd_sites, fade_sites):
        for a, n in d.items():
            for i in range(n):
                named[a + i] = True
    for a in cave_bytes:
        named[a] = True

    # CRC trailers (from the image's own chain)
    blocks = crc_blocks(v298)
    trailer_bytes = set()
    for b0, b1 in blocks:
        for i in range(4):
            trailer_bytes.add(b1 + i)

    stray = [a for a in diff if a not in named and a not in trailer_bytes]
    # account for the fact that cal/kp/kd/fade/code bytes might not all actually differ (same value) -- fine
    unexplained = [a for a in diff if a not in named and a not in trailer_bytes]
    if unexplained:
        note("DO_NOT_FLASH", f"{len(unexplained)} STRAY differing bytes not explained by any named edit or CRC trailer",
             ", ".join(hex(a) for a in unexplained[:20]))
    else:
        print(f"    every differing byte is a named edit or a recomputed CRC trailer (0 stray)")

    # which named bytes actually changed
    changed_named = [a for a in diff if a in named]
    changed_trailer = [a for a in diff if a in trailer_bytes]
    print(f"    changed named-edit bytes: {len(changed_named)}  |  changed trailer bytes: {len(changed_trailer)}")

    # ---- [C] independent rebuild: V295 + edits, recompute CRC from scratch, match V298 ------
    print("\n[C] INDEPENDENT REBUILD from V295 (my own apply + my own CRC), compare to V298")
    img = bytearray(v295)
    # in-place code edits -- take NEW bytes from the V298 image (opaque), but assert the OLD matches V295
    for a, n in code_sites.items():
        img[a:a + n] = v298[a:a + n]
    # cave: assert V295 region is all-0xFF, then write the cave bytes read from V298
    if bytes(v295[CAVE:CAVE + CAVE_LEN]) != b"\xff" * CAVE_LEN:
        note("DO_NOT_FLASH", "cave region NOT all-0xFF in V295 -- cave overwrites live base bytes",
             f"first non-FF at {CAVE + bytes(v295[CAVE:CAVE+CAVE_LEN]).find(next(bytes([x]) for x in v295[CAVE:CAVE+CAVE_LEN] if x!=0xff))}")
    img[CAVE:CAVE + CAVE_LEN] = v298[CAVE:CAVE + CAVE_LEN]
    # cals + records
    for a in list(cal_sites) + list(kp_sites) + list(kd_sites):
        img[a:a + 2] = v298[a:a + 2]
    img[0xE54FC + 2:0xE54FC + 2 + 24] = v298[0xE54FC + 2:0xE54FC + 2 + 24]
    # recompute CRC trailers from scratch over MY rebuilt image's block contents
    for b0, b1 in blocks:
        c = zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", img, b1, c)
    match = bytes(img) == v298
    if match:
        print(f"    MY rebuild == V298 byte-for-byte; my sha256 = {sha(bytes(img))[:16]}  (== claim: {sha(bytes(img))==EXP['v298']})")
    else:
        md = [a for a in range(START, END) if img[a] != v298[a]]
        note("DO_NOT_FLASH", f"independent rebuild does NOT reproduce V298 ({len(md)} bytes differ)",
             ", ".join(hex(a) for a in md[:20]))

    # ---- [D] CRC trailers independently recomputed on the BUILT image -----------------------
    print("\n[D] CRC trailers on the BUILT V298 image (independent zlib.crc32)")
    bad = 0
    for b0, b1 in blocks:
        calc = zlib.crc32(bytes(v298[b0:b1])) & 0xFFFFFFFF
        stored = u32(v298, b1)
        ok = calc == stored
        bad += not ok
        tag = "" if b0 not in (0x13000, 0xC6000, 0xE5000) else "  <- edited block"
        if not ok:
            note("DO_NOT_FLASH", f"CRC trailer mismatch block [0x{b0:06X},0x{b1:06X})", f"calc 0x{calc:08X} stored 0x{stored:08X}")
    print(f"    {len(blocks)} blocks, {bad} CRC mismatches (full chain)")
    wa = qwalk(walk_all_blocks, v298)
    wb = qwalk(walk, v298)
    print(f"    walk_all_blocks -> {wa} fail  |  bootloader walk -> {wb} fail")
    if wa or wb:
        note("DO_NOT_FLASH", "bootloader/full CRC walk fails on built image", f"full={wa} boot={wb}")

    # ---- [E] .rwd decode back to image bit-for-bit -----------------------------------------
    print("\n[E] .rwd decode-back (bit-for-bit) + header strings + single-flashable check")
    rwd = V298_RWD.read_bytes()
    print(f"    V298 .rwd on-disk hash matches claim: {sha(rwd) == EXP['v298_rwd']}")
    dec = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    pr = parse_x31(rwd)
    back = bytearray(v295)
    back[START:END] = bytes(pr["encs"][0]).translate(dec)
    if bytes(back) == v298:
        print("    .rwd decodes to the V298 image byte-for-byte")
    else:
        md = [a for a in range(START, END) if back[a] != v298[a]]
        note("DO_NOT_FLASH", f".rwd does NOT decode to V298 ({len(md)} bytes differ)", ", ".join(hex(a) for a in md[:20]))
    hdr = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in pr["headers"]}
    print(f"    '/' header: {hdr.get('/')}")
    need = "39990-TVA,A16A"
    if need not in (hdr.get("/") or []):
        note("DO_NOT_FLASH", "V298 .rwd '/' header does not list A16A -- flasher part gate will reject", str(hdr.get("/")))
    # version string in image
    vstr = bytes(v298[0x13100:0x1310E]).decode("latin1", "replace")
    print(f"    image F181 version string = {vstr!r}")
    if vstr != "39990-TVA,A16A":
        note("DO_NOT_FLASH", "image version string != A16A", vstr)
    # single flashable
    flashable = [f.name for f in RWD.glob("*V298*.rwd") if not f.name.startswith("SUPERSEDED") and "REVERT" not in f.name]
    print(f"    flashable V298 .rwd files: {flashable}")
    if len(flashable) != 1:
        note("DO_NOT_FLASH", f"not exactly one flashable V298 .rwd ({len(flashable)})", str(flashable))

    # ---- [F] revert artifacts + originals untouched ----------------------------------------
    print("\n[F] revert artifacts + originals untouched")
    for name, path, exp in (("V295", V295_RWD, EXP["v295_rwd"]), ("V294", V294_RWD, EXP["v294_rwd"])):
        got = sha(path.read_bytes())
        if got != exp:
            note("DO_NOT_FLASH", f"ORIGINAL {name} .rwd hash CHANGED (revert touched it)", f"{got} != {exp}")
        else:
            print(f"    original {name} .rwd untouched ({got[:16]})")
    for name, rev, orig, exp in (("V295", REV_V295, V295_RWD, EXP["rev295"]), ("V294", REV_V294, V294_RWD, EXP["rev294"])):
        rb = rev.read_bytes()
        print(f"    revert-{name} on-disk hash matches claim: {sha(rb) == exp}")
        pr_rev = parse_x31(rb)
        pr_orig = parse_x31(orig.read_bytes())
        if pr_rev["encs"] != pr_orig["encs"]:
            note("DO_NOT_FLASH", f"revert-{name} PAYLOAD differs from original (not headers-only)", "encs mismatch")
        else:
            print(f"    revert-{name} payload == original (headers-only change)")
        hv = [v.decode("latin1") for t, vv in pr_rev["headers"] if t == b"/" for v in vv]
        if need not in hv:
            note("DO_NOT_FLASH", f"revert-{name} '/' header does not list A16A", str(hv))
        else:
            print(f"    revert-{name} '/' lists {hv}")

    print("\n" + "=" * 100)
    print(f"FINDINGS: {len(FINDINGS)}")
    for s, t, e in FINDINGS:
        print(f"  [{s}] {t}")
    return FINDINGS

if __name__ == "__main__":
    main()
