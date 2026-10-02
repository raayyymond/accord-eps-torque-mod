# -*- coding: utf-8 -*-
r"""V299 rev 2 -- the angle loop with a TWO-LEVEL A3 cap, a raw-1229 hard freeze, no opposing clause and an
asymmetric integral bound.  BUILT ON V298 (the first firmware angle loop), 67 bytes, one 260-B cave re-laid in
place, no relink, 0 RAM, ONE CRC block.

BASE   V298 (_v298_V298-ANGLELOOP.C3REV2P...A16A_plain_image.bin, sha256 177abf04...) -- FLOWN (route 79).
DESIGN docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev2-2026-10-02.md (SECTION 1 = the byte table + cave_rev2;
       SECTION 11 = the build-round prerequisites, rwd plan, CRC plan).

=== EVERY BYTE V299 CHANGES vs V298 (67 = 62 cave-region + 1 F181 + 4 CRC trailer) ========================
  THE CAVE REGION (0xC4C00, 260 B; main CRC block [0x13000,0xC4FFC)):  the rev-2 span 0xC4C6A..0xC4CAB
    (the asymmetric bound + the two-level cap: shl 4/6, +1250, caps 4096 at v<=1382 / 6144 at 1382<v<=2880,
    shl 6 uncapped above 2880) re-laid in place (60 bytes differ from V298), PLUS the hard-freeze movea imm16
    at 0xC4C64-65 (512 -> 1229, 2 bytes).  All other cave bytes (table ptr, GB-P rows, op-skip, camera gate,
    FRZ/CAM/DONE tails) are byte-identical to V298.  The whole 260-B cave is overlaid and sha-frozen.
  IN-PLACE CODE (main CRC block): 0x1310D 41 -> 42  (F181 '39990-TVA,A16A' -> '...,A16B')
  CRC: one owning block only -- [0x13000,0xC4FFC); trailer 0xC4FFC f3 d8 7c 6b -> 95 3b dd 70.
  (The 0xC6000 and 0xE5000 cal/record blocks are UNCHANGED from V298.)

FLASH IS GATED on the operator naming the file and the bus -- this script writes files only, guarded.
"""
import contextlib
import hashlib
import io
import os
import struct
import sys
import zlib
from pathlib import Path

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import build_vfourframe_tva as FF                                                     # noqa: E402
import build_v53_tva as V53                                                           # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table         # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path, RWD_DIR, ANALYSIS_ROOT    # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END, CODE_END = 0x13000, 0x100000, 0xC0000
WRITE_MODE = os.environ.get("ACCORD_V299_WRITE", "").strip().lower()
MAX_PATH = 259

BASE_NAME = ("_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A"
             "_plain_image.bin")
BASE_SHA = "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"
V298_RWD_NAME = ("39990-TVA,A160-V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE"
                 ".A16A-0x13000-0x100000.rwd")
V298_RWD_SHA = "1a69b92760b8a9538b504b020076e5b025fed7af03b34800ecd05dd687ce960e"  # the V298 rwd on disk (asserted in main)

CAVE_BASE = 0xC4C00
CAVE_LEN = 260
EXP_IMG_SHA = "30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08"
EXP_CAVE_SHA = "e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608"
EXP_TRAILER = bytes.fromhex("953bdd70")
MAIN_BLOCK = (0x13000, 0xC4FFC)

# the frozen V299 rev-2 cave (260 B; the reviser's rev_bytes.py output, re-derived in-place; sha EXP_CAVE_SHA).
# Overlaid onto V298's cave region; the diff vs V298 is asserted to be exactly the rev-2 span + imm16 below.
CAVE_HEX = ("c282ba8124d742951a46c832206e9065ed41b305b6075055e447a3952906da4c0c00e96f0100ed41cb05e9470300b515"
            "e96f0700ed41c305094e0600a5fde96f0100ad41296f0400ed472002ac42e96f0300cd41e8872002a882e0c9e235e447"
            "99b0206ecd04ed41db2d244f0096e081ae058049e049ae05004ae447a395206e400bed419b15c44a094ee204206e6605"
            "ed41cb05206e0010b505206e0018ed49ed4f364bc505c64a094ee204246f3192aa6ae081ae058069e969ce05ce6e0080"
            "ca0d0032b607ba50008200d224373192a6328031b607aa506600ca029a0411043307b90588e70009f8020ff8930a3002"
            "2206c00f2c04460836188c080000ffff8c080000")
CAVE = bytes.fromhex(CAVE_HEX)

# the rev-2 span and the hard-freeze imm16 (the ONLY bytes that differ from V298 inside the cave region)
SPAN_LO, SPAN_HI = 0xC4C6A, 0xC4CAB                  # the 66-B span (60 of its bytes differ from V298)
IMM16 = (0xC4C64, 0xC4C65)                           # movea 512 -> 1229 (the hard freeze)

# in-place code edits: (addr, V298 old, V299 new)
CODE_EDITS = [
    (0x1310D, "41", "42", "V1  F181 A16A -> A16B"),
]
VSTR_STOCK_ALT = b"39990-TVA-A110"
VSTR_A160 = b"39990-TVA,A160"
VSTR_A16A = b"39990-TVA,A16A"
VSTR_A16B = b"39990-TVA,A16B"

TAG = "V299-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3-2LVL.4096.6144.V2880.FRZ1229.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16B"
IMG_NAME = f"_v299_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
REVERT_V298_RWD = f"39990-TVA,A160-V298-REHEADERED-FOR-REVERT-FROM-V299-A16B-0x{START:X}-0x{END:X}.rwd"

OK, BAD = "[PASS]", "[FAIL]"


class Run:
    def __init__(self, quiet=False, collect=False):
        self.n = self.ok = 0
        self.census = {"S": 0, "C": 0, "V": 0, "T": 0}
        self.quiet, self.collect, self.failures = quiet, collect, []

    def check(self, cond, msg, kind="S"):
        self.n += 1
        self.census[kind] += 1
        cond = bool(cond)
        self.ok += cond
        if not self.quiet:
            print(f"      {OK if cond else BAD} [{kind}] {msg}")
        if not cond:
            self.failures.append((kind, msg))
            if not self.collect:
                raise SystemExit(f"ASSERTION FAILED: {msg}")

    def say(self, s=""):
        if not self.quiet:
            print(s)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def qwalk(fn, img):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(bytearray(img))


def build(quiet=False, do_rwd=True, base_bytes=None, run=None):
    R = run if run is not None else Run(quiet)
    ck, say = R.check, R.say
    say("=" * 118)
    say("  V299 rev 2 -- two-level A3 cap + raw-1229 hard freeze + asymmetric bound (built on V298, one CRC block)")
    say("=" * 118)

    # [1] BASE = V298
    say("\n  [1] BASE = V298")
    base = bytes(base_bytes if base_bytes is not None else Path(plain_image_path(BASE_NAME)).read_bytes())
    ck(hashlib.sha256(base).hexdigest() == BASE_SHA, f"V298 base sha256 == {BASE_SHA[:16]}...", "S")
    ck(qwalk(walk_all_blocks, base) == 0, "base CRC chain 50/50  [entailed]", "V")
    ck(qwalk(walk, base) == 0, "base BOOTLOADER CRC replay 49/49  [entailed]", "V")

    # [2] THE CAVE -- sha-frozen; the diff vs V298's cave region is exactly the rev-2 span + the imm16
    say("\n  [2] THE CAVE -- sha-frozen rev-2 bytes; diff vs V298 = the span + imm16")
    ck(hashlib.sha256(CAVE).hexdigest() == EXP_CAVE_SHA, f"cave sha256 == {EXP_CAVE_SHA[:12]}... ({len(CAVE)} B)", "C")
    v298_cave = base[CAVE_BASE:CAVE_BASE + CAVE_LEN]
    cave_diff = {CAVE_BASE + i for i in range(CAVE_LEN) if CAVE[i] != v298_cave[i]}
    allowed = set(IMM16) | set(range(SPAN_LO, SPAN_HI + 1))
    ck(cave_diff <= allowed, f"every changed cave byte is in the imm16 or the span [{hex(SPAN_LO)},{hex(SPAN_HI)}]", "S")
    ck(len(cave_diff) == 62, f"exactly 62 cave bytes differ from V298 (got {len(cave_diff)})", "S")
    n_span = sum(1 for a in cave_diff if SPAN_LO <= a <= SPAN_HI)
    n_imm = sum(1 for a in cave_diff if a in IMM16)
    ck(n_span == 60 and n_imm == 2, f"of the 62: {n_span} in-span + {n_imm} imm16 (512->1229)", "S")
    ck(u16(CAVE, 0xC4C64 - CAVE_BASE) == 1229, "the new hard-freeze imm16 = 1229 (raw; wire 1200)", "S")
    ck(u16(CAVE, 0xC4C80 - CAVE_BASE) == 2880 and u16(CAVE, 0xC4C8E - CAVE_BASE) == 1382
       and u16(CAVE, 0xC4C96 - CAVE_BASE) == 4096 and u16(CAVE, 0xC4C9C - CAVE_BASE) == 6144,
       "the two-level cap immediates: v-gates 2880/1382, caps 4096/6144", "S")

    # [3] APPLY -- the cave overlay + the F181 byte
    say("\n  [3] APPLY")
    code = bytearray(base)
    attributed = set()

    def put(a, nb):
        code[a:a + len(nb)] = nb
        for i in range(len(nb)):
            if code[a + i] != base[a + i]:
                attributed.add(a + i)

    put(CAVE_BASE, CAVE)
    for a, old, new, nm in CODE_EDITS:
        ob, nb = bytes.fromhex(old.replace(" ", "")), bytes.fromhex(new.replace(" ", ""))
        ck(bytes(base[a:a + len(ob)]) == ob, f"code 0x{a:05X} base == {old} ({nm})", "S")
        put(a, nb)
    ck(attributed == cave_diff | {0x1310D}, f"attributed = {len(cave_diff)} cave + 1 F181 = {len(attributed)}", "S")

    # [4] CRC -- ONE owning block
    say("\n  [4] CRC -- one owning block, trailer recomputed")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in attributed})
    ck(set(blocks) == {MAIN_BLOCK}, f"attributed bytes own exactly the main CRC block: "
       f"{[(hex(s), hex(e)) for s, e in blocks]}", "S")
    b0, b1 = MAIN_BLOCK
    oldc, newc = u32(code, b1), zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    struct.pack_into("<I", code, b1, newc)
    say(f"      block [0x{b0:06X},0x{b1:06X})  trailer 0x{oldc:08X} -> 0x{newc:08X}")
    ck(bytes(code[b1:b1 + 4]) == EXP_TRAILER, f"trailer == {EXP_TRAILER.hex()}", "S")
    ck(qwalk(walk_all_blocks, bytes(code)) == 0, "built image CRC chain 50/50", "S")
    ck(qwalk(walk, bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (NRC 0x72 predictor)", "S")

    # [5] FULL BYTE DIFF vs V298 -- every differing offset attributed
    say("\n  [5] FULL BYTE DIFF vs V298 over [0x13000, 0x100000)")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    trailer_bytes = {b1 + i for i in range(4)}
    expected = set(attributed) | trailer_bytes
    stray = [hex(a) for a in diff if a not in expected]
    ck(not stray, f"every differing byte is an attributed edit or the recomputed CRC trailer ({len(stray)} stray)", "S")
    ck(set(diff) == expected and len(diff) == 67,
       f"the diff == 62 cave + 1 F181 + 4 trailer = 67 (got {len(diff)})", "S")

    # [6] READBACK on the BUILT image
    say("\n  [6] READBACK on the BUILT image")
    ck(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_LEN]) == CAVE, "the cave on the built image == the rev-2 bytes", "T")
    ck(u16(code, 0xC4C64) == 1229 and u16(code, 0xC4C80) == 2880 and u16(code, 0xC4C8E) == 1382
       and u16(code, 0xC4C96) == 4096 and u16(code, 0xC4C9C) == 6144,
       "hard freeze 1229 + two-level cap (2880/1382, 4096/6144) on the built image", "T")
    ck(bytes(code[0x13100:0x1310E]) == VSTR_A16B, f"F181 string on the built image == {VSTR_A16B.decode()}", "T")
    # the shared cals + GB-P table are UNCHANGED from V298
    ck(u16(code, 0xC63EA) == 8192 and u16(code, 0xC62E6) == 65535 and u16(code, 0xC63E6) == 40,
       "fb gain 8192 / clamp 65535 / Ki 40 unchanged from V298", "T")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ck(img_sha == EXP_IMG_SHA, f"PREDICTED image sha256 == {EXP_IMG_SHA[:12]}...", "C")

    rwd = rwd_sha = None
    if do_rwd:
        say("\n  [7] .rwd ENCODE (headers: '/' = A110, A160, A16A, A16B) + READBACK + non-circular cipher check")
        src = Path(FF.V38_RWD).read_bytes()
        ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches (container template)", "C")
        FF.assert_x31_checksum(src, "V38 source")
        info = parse_x31(src)
        headers = header_add(info["headers"], [VSTR_A16A, VSTR_A16B], R)
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        rwd = encode_x31(headers, info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
        FF.assert_x31_checksum(rwd, "V299 output")
        back = bytearray(base)
        back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
        ck(bytes(back) == bytes(code), "the .rwd decoded back is BYTE-IDENTICAL to the built image", "S")
        v38 = bytearray(base)
        v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
        ck(hashlib.sha256(bytes(v38[START:END])).hexdigest()
           == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
           "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")
        pr = parse_x31(rwd)
        got = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in pr["headers"]}
        ck(got.get("/") == [VSTR_STOCK_ALT.decode(), VSTR_A160.decode(), VSTR_A16A.decode(), VSTR_A16B.decode()],
           f"V299 .rwd '/' header lists {got.get('/')}", "S")
        rwd_sha = hashlib.sha256(rwd).hexdigest()

    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"both output paths fit {MAX_PATH} chars (image {len(str(out_i))}, rwd {len(str(out_r))})", "C")
    say("\n" + "=" * 118)
    say(f"  PREDICTED image SHA256 {img_sha}")
    if rwd_sha:
        say(f"  PREDICTED .rwd  SHA256 {rwd_sha}")
    say(f"  {R.ok}/{R.n} assertions -- census: {R.census['S']} substantive, {R.census['C']} constant-checks, "
        f"{R.census['V']} vacuous/entailed, {R.census['T']} tautological")
    say("=" * 118)
    return dict(code=bytes(code), base=base, rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha, tag=TAG,
                img_name=IMG_NAME, rwd_name=RWD_NAME, run=R, diff=diff)


def header_add(headers, strings, R):
    """Return a copy of the x31 headers with each of `strings` appended to '/' (supported parts) if absent, and
    a parallel '!' entry so the lists stay parallel."""
    out = []
    for tag, vals in headers:
        vals = list(vals)
        if tag == b"/":
            R.check(VSTR_A160 in vals, "source .rwd '/' lists A160 (the car's current part gate)", "C")
            for s in strings:
                if s not in vals:
                    vals.append(s)
        if tag == b"!" and len(vals) >= 1:
            for _ in strings:
                vals.append(vals[-1])
        out.append((tag, vals))
    return out


def main():
    base = Path(plain_image_path(BASE_NAME)).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise SystemExit("V298 base sha256 mismatch -- refusing to go further")
    _v298rwd = Path(RWD_DIR, V298_RWD_NAME)
    if _v298rwd.exists():
        assert hashlib.sha256(_v298rwd.read_bytes()).hexdigest() == V298_RWD_SHA, "V298 rwd on disk differs from the recorded sha"
        print("      [PASS] [S] V298 rwd on disk == recorded sha256 (1a69b927...)")
    r = build()
    print(f"\n  PREDICTION, before any write:  image {r['img_sha']}")
    if r["rwd_sha"]:
        print(f"                                 rwd   {r['rwd_sha']}")
    rr = r["run"]
    print(f"  census: {rr.census}  ({rr.ok}/{rr.n})")
    if WRITE_MODE == "rwd":
        print("\n  [8] WRITE -- guarded, re-hashed + decoded after")
        out_img, out_rwd = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
        # image may already exist (written by the golden-mirror step); verify it matches rather than refuse
        if out_img.exists():
            assert hashlib.sha256(out_img.read_bytes()).hexdigest() == r["img_sha"], "existing image differs!"
            print(f"      [PASS] image already on disk and matches: {out_img}")
        else:
            with open(out_img, "xb") as fh:
                fh.write(r["code"])
            print(f"      [PASS] image written: {out_img}")
        if out_rwd.exists():
            raise SystemExit(f"WRITE GUARD: a V299 rwd already exists ({out_rwd.name})")
        with open(out_rwd, "xb") as fh:
            fh.write(r["rwd"])
        assert hashlib.sha256(out_rwd.read_bytes()).hexdigest() == r["rwd_sha"]
        print(f"      [PASS] rwd written: {out_rwd}")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V299_WRITE=rwd to emit the files.")
    return r


if __name__ == "__main__":
    main()
