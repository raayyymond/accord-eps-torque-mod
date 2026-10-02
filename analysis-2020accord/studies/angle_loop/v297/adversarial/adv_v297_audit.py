"""ADV BUILD-AUDIT V297 -- independent census + baseline checks.

Written by the V297 build-audit adversary, 2026-10-01.  INDEPENDENT BY CONSTRUCTION: imports nothing
from the kit (no encode_eps, no verify_bootloader_crc, no build_v29x module).  Only stdlib.

What it does (every check prints PASS/FAIL and a final tally):
  A. ARTIFACT CENSUS     -- every file in both repos whose name carries V297 / V296 / A16A /
                            REHEADERED; flashable .rwd count per build number V290..V299.
  B. ORIGINALS           -- sha256 of the V294 / V295 plain images and .rwds vs the RECORDED values
                            (docs/BUILD-LINEAGE-PART6-V291-ONWARD.md), and git blob == disk.
  C. RWD DECODE          -- own x31 parser + own cipher solver; decode each .rwd and compare to its
                            plain image over [0x13000,0x100000) bit-for-bit; file checksum trailer;
                            '/' header part strings vs the image's version string at 0x13100.
  D. CRC CHAIN           -- own replay of the linked-list CRC32 chain: with the 0xC6000->0x13000
                            bridge (bootloader, expect 49) and without (full chain, expect 50).
  E. V295 vs V294 DIFF   -- every differing byte in [0x13000,0x100000), classified.
  F. CAVE HEX            -- sha256 of the decoded bytes of the C3-rev2 cave hex files; flight==score.
Run:  python adv_v297_audit.py   (ACCORD_FIRMWARE_ROOT honoured, default below)
"""
import hashlib, itertools, os, re, struct, subprocess, sys, zlib

KIT = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod"
FW = os.environ.get("ACCORD_FIRMWARE_ROOT", r"C:\Users\dudei\Desktop\Projects\accord-firmwares")
IMG_DIR = os.path.join(FW, "analysis-2020accord")
RWD_DIR = os.path.join(FW, "flashing-2020accord", "rwd")

RECORDED = {  # docs/BUILD-LINEAGE-PART6-V291-ONWARD.md (V294 entry and V295 entry), docs/STATE.md
    "V294": {"img": "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85",
             "rwd": "a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a"},
    "V295": {"img": "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed",
             "rwd": "f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87"},
}

RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    return ok

def sha(b): return hashlib.sha256(b).hexdigest()
def u16(b, o): return b[o] | (b[o + 1] << 8)
def u32(b, o): return struct.unpack_from("<I", b, o)[0]

def find_one(dirpath, pattern):
    hits = [f for f in os.listdir(dirpath) if re.search(pattern, f)]
    return hits

# ------------------------------------------------------------------ A. census
def census():
    print("\n=== A. ARTIFACT CENSUS ===")
    pat = re.compile(r"(?i)(v29[6-9]|a16a|reheadered)")  # r3: V298/V299 too (a V298 builder is live)
    hits = []
    for root in (KIT, FW):
        for b, ds, fs in os.walk(root):
            ds[:] = [d for d in ds if d not in (".git", "__pycache__", "rlogs", "ghidra_project")]
            for f in fs + ds:
                if pat.search(f):
                    hits.append(os.path.join(b, f))
    for h in hits:
        print("    name-hit:", h)
    # r3: a hit is UNEXPECTED if it is an ARTIFACT-CLASS file (image .bin / .rwd / .hex / build
    # script) anywhere, or ANY file outside the adversaries' study folders and _scratch\angle_loop.
    # (A parallel V298 builder's read-only _scratch probe and the V296 adversaries' notes are expected.)
    def expected(h):
        if re.search(r"(?i)\.(bin|rwd|hex)$|build_v29\d_tva\.py$", h):
            return False
        return bool(re.search(r"(?i)(studies[\\/]angle_loop[\\/]v29[6-9]([\\/]|$)"
                              r"|_scratch[\\/]angle_loop[\\/](adv-|v29\d-build))", h))
    unexpected = [h for h in hits if not expected(h)]
    for h in unexpected:
        print("    UNEXPECTED:", h)
    check("no V296/V297/A16A/REHEADERED artifact outside the adversaries' own study folders",
          not unexpected, f"{len(unexpected)} unexpected of {len(hits)} name hits")
    # flashable .rwd count per build number
    per = {}
    for f in os.listdir(RWD_DIR):
        m = re.search(r"-V(\d{2,3}[A-Z]?)-", f)
        if f.endswith(".rwd") and m and not re.search(r"(?i)superseded|do-not-flash|reheadered", f):
            per.setdefault(m.group(1), []).append(f)
    for n in ("294", "295", "296", "297", "298", "299"):
        print(f"    V{n}: {len(per.get(n, []))} flashable .rwd")
    check("V297 flashable .rwd count == 0 (nothing built)", len(per.get("297", [])) == 0)
    check("V296 flashable .rwd count == 0", len(per.get("296", [])) == 0)
    check("V295 flashable .rwd count == 1", len(per.get("295", [])) == 1)
    check("V294 flashable .rwd count == 1", len(per.get("294", [])) == 1)
    dup = {k: v for k, v in per.items() if len(v) > 1}
    check("no build number in rwd/ has >1 flashable .rwd", not dup,
          ", ".join(f"V{k}x{len(v)}" for k, v in sorted(dup.items())) or "none")
    sc = os.path.join(KIT, "analysis-2020accord", "builds", "v108_plus", "build_v297_tva.py")
    check("build_v297_tva.py absent", not os.path.exists(sc))
    imgs = [f for f in os.listdir(IMG_DIR) if re.match(r"(?i)_v29[67]_", f)]
    check("no _v296_/_v297_ plain image in accord-firmwares/analysis-2020accord", not imgs, str(imgs))
    return per

# ------------------------------------------------------------------ B. originals
def git_blob_matches(repo, rel):
    try:
        disk = subprocess.run(["git", "-C", repo, "hash-object", rel], capture_output=True,
                              text=True, check=True).stdout.strip()
        idx = subprocess.run(["git", "-C", repo, "ls-files", "-s", rel], capture_output=True,
                             text=True, check=True).stdout.split()
        return idx and idx[1] == disk, disk
    except Exception as e:  # noqa
        return False, repr(e)

def originals(per):
    print("\n=== B. ORIGINALS (revert path) ===")
    out = {}
    for tag in ("V294", "V295"):
        n = tag[1:]
        img = [f for f in os.listdir(IMG_DIR) if f.startswith(f"_v{n}_") and f.endswith("_plain_image.bin")]
        rwd = per.get(n, [])
        check(f"{tag}: exactly one plain image", len(img) == 1, str(len(img)))
        ib = open(os.path.join(IMG_DIR, img[0]), "rb").read()
        rb = open(os.path.join(RWD_DIR, rwd[0]), "rb").read()
        check(f"{tag}: plain image sha256 == recorded", sha(ib) == RECORDED[tag]["img"], sha(ib)[:16])
        check(f"{tag}: .rwd sha256 == recorded", sha(rb) == RECORDED[tag]["rwd"], sha(rb)[:16])
        for rel in (os.path.join("analysis-2020accord", img[0]),
                    os.path.join("flashing-2020accord", "rwd", rwd[0])):
            ok, h = git_blob_matches(FW, rel.replace("\\", "/"))
            check(f"{tag}: git blob == disk for {os.path.basename(rel)[:34]}...", ok, h[:12])
        out[tag] = (ib, rb, rwd[0])
    return out

# ------------------------------------------------------------------ C. rwd decode (own)
def parse_x31(raw):
    if raw[:3] != b"1\r\n":
        raise ValueError("not x31")
    i, headers = 3, []
    for _ in range(6):
        tag = raw[i:i + 3]; i += 3
        vals = []
        while raw[i:i + 3] != tag:
            e = raw.index(b"\r\n", i); vals.append(raw[i:e]); i = e + 2
        i += 3
        headers.append((chr(tag[0]), vals))
    body_end = len(raw) - 4
    chunks = []
    for j in range(i, body_end, 130):
        addr = (raw[j] << 12) | (raw[j + 1] << 4)
        chunks.append((addr, raw[j + 2:j + 130]))
    if (body_end - i) % 130:
        raise ValueError("payload not a whole number of 130-byte chunks")
    return headers, chunks, raw[:body_end], u32(raw, body_end)

_OPS = [lambda a, b: a ^ b, lambda a, b: a & b, lambda a, b: a | b, lambda a, b: a + b,
        lambda a, b: a - b, lambda a, b: a * b, lambda a, b: a // b, lambda a, b: a % b]

def solve_cipher(enc_all, keybytes, known):
    """Search (key order, op triple) for a bijective byte map under which `known` appears."""
    for ks in set(itertools.permutations(keybytes)):
        for oi in itertools.product(range(8), repeat=3):
            tbl = bytearray(256); ok = True
            for e in range(256):
                try:
                    tbl[e] = _OPS[oi[2]](_OPS[oi[1]](_OPS[oi[0]](e, ks[0]), ks[1]), ks[2]) & 0xFF
                except ZeroDivisionError:
                    ok = False; break
            if not ok or len(set(tbl)) != 256:
                continue
            if known in enc_all.translate(bytes(tbl)):
                return bytes(tbl), (ks, oi)
    return None, None

def rwd_decode(tag, ib, rb):
    print(f"\n=== C. {tag} .rwd DECODE (own parser + own cipher solver) ===")
    headers, chunks, body, trailer = parse_x31(rb)
    hd = {t: v for t, v in headers}
    print("    header tags:", [t for t, _ in headers])
    print("    '/' part strings:", hd.get("/"))
    check(f"{tag}: file checksum trailer == sum(body) & 0xFFFFFFFF",
          (sum(body) & 0xFFFFFFFF) == trailer, f"0x{trailer:08X}")
    key = bytes.fromhex(hd["&"][0].decode())
    enc_all = b"".join(c for _, c in chunks)
    # SCRIPT FIX r2: the image's own string is 39990-TVA,A160 (COMMA), read at 0x13100 below
    tbl, how = solve_cipher(enc_all, list(key), b"39990-TVA,A160")
    check(f"{tag}: cipher solved from '&' key {hd['&'][0].decode()}", tbl is not None, str(how))
    img = bytearray(b"\xFF" * len(ib))
    addrs = [a for a, _ in chunks]
    for a, c in chunks:
        img[a:a + 128] = c.translate(tbl)
    lo, hi = min(addrs), max(addrs) + 128
    print(f"    payload covers [0x{lo:X}, 0x{hi:X})  chunks={len(chunks)}  contiguous="
          f"{addrs == list(range(lo, hi, 128))}")
    check(f"{tag}: payload is [0x13000,0x100000) contiguous",
          lo == 0x13000 and hi == 0x100000 and addrs == list(range(lo, hi, 128)))
    same = img[0x13000:0x100000] == ib[0x13000:0x100000]
    nd = sum(1 for k in range(0x13000, 0x100000) if img[k] != ib[k]) if not same else 0
    check(f"{tag}: decoded .rwd == plain image over [0x13000,0x100000) bit-for-bit", same,
          f"{nd} differing bytes")
    vs = ib[0x13100:0x13110]
    print(f"    image version string @0x13100: {vs!r}  byte 0x1310D = 0x{ib[0x1310D]:02X}")
    parts = [p.decode(errors="replace") for p in hd.get("/", [])]
    img_part = re.search(rb"39990-TVA[-,]A16.", ib[0x13100:0x13120])  # SCRIPT FIX r2
    img_part = img_part.group(0).decode() if img_part else None
    check(f"{tag}: image part string {img_part} listed in the '/' header", img_part in parts, str(parts))
    return tbl

# ------------------------------------------------------------------ D. CRC chain (own)
def crc_chain(img, bridge, region=(0x13000, 0xED000)):
    rs, rl = region
    end = rs + rl
    bs, bl = u16(img, end - 8) << 12, (u16(img, end - 6) << 12) - 4
    res, bridged = [], False
    for _ in range(300):
        if bs < 0 or bs + bl + 4 > len(img):
            res.append((bs, bl, None)); break
        calc = zlib.crc32(img[bs:bs + bl]) & 0xFFFFFFFF
        res.append((bs, bl, calc == u32(img, bs + bl)))
        if bs == rs:
            break
        if bridge and bs == 0xC6000 and not bridged:
            bridged = True; bs, bl = rs, 0xB1FFC; continue
        nbs = u16(img, bs - 8) << 12
        if nbs == bs:
            break
        bs, bl = nbs, (u16(img, bs - 6) << 12) - 4
    return res

def crc_checks(tag, img):
    print(f"\n=== D. {tag} CRC CHAIN (own replay) ===")
    for bridge, want in ((True, 49), (False, 50)):
        r = crc_chain(img, bridge)
        n_ok = sum(1 for x in r if x[2])
        label = "bootloader walk (bridge)" if bridge else "full linked chain (no bridge)"
        check(f"{tag}: {label}: {n_ok}/{len(r)} pass, expect {want}/{want}",
              n_ok == len(r) == want and r[-1][0] == 0x13000)

# ------------------------------------------------------------------ E. V295 vs V294
def diff_v295_v294(i295, i294):
    print("\n=== E. V295 vs V294 full diff over [0x13000,0x100000) ===")
    d = [k for k in range(0x13000, 0x100000) if i295[k] != i294[k]]
    runs, s = [], None
    for k in d:
        if s is None or k != runs[-1][1] + 1:
            runs.append([k, k])
        else:
            runs[-1][1] = k
        s = k
    for a, b in runs:
        print(f"    diff run 0x{a:05X}..0x{b:05X}: V294 {i294[a:b+1].hex()} -> V295 {i295[a:b+1].hex()}")
    # classify: CRC trailer words of chain blocks
    trailers = set()
    for bs, bl, _ in crc_chain(i295, False) + crc_chain(i295, True):
        trailers.update(range(bs + bl, bs + bl + 4))
    unexplained = [k for k in d if k not in trailers and not (0xC63EA <= k < 0xC63EC)]
    b294, b295 = u16(i294, 0xC63EA), u16(i295, 0xC63EA)
    print(f"    cal 0xC63EA (u16 LE): V294 {b294} -> V295 {b295}")
    check("V295-V294 differ ONLY at 0xC63EA (u16) + CRC trailer words", not unexplained,
          f"{len(d)} bytes differ, {len(unexplained)} unexplained")
    check("0xC63EA: 567 -> 1050 (as recorded)", (b294, b295) == (567, 1050))

# ------------------------------------------------------------------ F. cave hex
def cave_hex():
    print("\n=== F. C3-rev2 cave hex files (decoded-bytes sha256) ===")
    base = os.path.join(KIT, "analysis-2020accord", "studies", "angle_loop", "c3")
    def rd(rel):
        t = open(os.path.join(base, rel)).read()
        return bytes.fromhex(re.sub(r"[^0-9a-fA-F]", "", t))
    F, Fs = rd(r"rev2B\c3b_cave_C3B-F.hex"), rd(r"rev2B\c3b_cave_C3B-F_score.hex")
    P, Ps = rd(r"rev2B\c3b_cave_C3B-P.hex"), rd(r"rev2B\c3b_cave_C3B-P_score.hex")
    for n, b in (("C3B-F flight", F), ("C3B-F score", Fs), ("C3B-P flight", P), ("C3B-P score", Ps)):
        print(f"    {n:14s} {len(b):4d} B  sha {sha(b)[:12]}")
    check("C3B-F flight == C3B-F score (no op-skip splice in the default fallback)", F == Fs)
    check("C3B-F sha 9de9365fa952 (design page)", sha(F).startswith("9de9365fa952"))
    check("C3B-P sha 9a10cdc4ec75 (design page)", sha(P).startswith("9a10cdc4ec75"))
    # the known defect, read as bytes: mov imm32,r9 = hw1 0x0629 (format VI), imm LE after it
    for n, b in (("C3B-P flight", P), ("C3B-P score", Ps), ("C3B-F", F)):
        for k in range(0, len(b) - 5, 2):
            if u16(b, k) == 0x0629:
                imm = u16(b, k + 2) | (u16(b, k + 4) << 16)
                print(f"    {n}: +0x{k:02X} bytes 29 06 -> mov imm32 0x{imm:06X}, r9 "
                      f"(cave base 0xC4C00 -> table offset +0x{imm - 0xC4C00:02X}, cave len 0x{len(b):02X})")
    # splice locator: the longest common prefix, then the flight tail vs the score tail shifted 2
    k = next(i for i in range(min(len(P), len(Ps))) if P[i] != Ps[i])
    print(f"    C3B-P flight vs score: first differing byte at +0x{k:02X}")
    tail_eq = [P[i + 2] == Ps[i] for i in range(k, len(Ps))]
    print(f"    after a 2-byte insert at +0x{k:02X}: {sum(tail_eq)}/{len(tail_eq)} tail bytes equal; "
          f"mismatch offsets (score) {[hex(k+i) for i, e in enumerate(tail_eq) if not e][:12]}")
    # jr disp22 (format V, reg2=0): hw1 & 0xFFC0 == 0x0780; target = pc + sext22; must be EVEN
    def jrs(b, base):
        out = []
        for k in range(0, len(b) - 3, 2):
            h1, h2 = u16(b, k), u16(b, k + 2)
            if (h1 & 0xFFC0) == 0x0780 and not (h2 & 1):
                d = ((h1 & 0x3F) << 16) | h2
                if d & 0x200000: d -= 0x400000
                out.append((k, base + k + d))
        return out
    for n, b in (("C3B-P flight", P), ("C3B-P score", Ps), ("C3B-F", F)):
        print(f"    {n}: jr sites (cave @0xC4C00) " +
              ", ".join(f"+0x{k:02X}->0x{t:05X}" for k, t in jrs(b, 0xC4C00) if 0 <= t < 0xC4000))
    # where does the 'G-table' tail sit?  score +0xC4.. vs flight +0xC6..
    check("C3B-P: score[+0xC4:] == flight[+0xC6:] (table moved +2 in flight)", Ps[0xC4:] == P[0xC6:],
          f"score tail {Ps[0xC4:0xCC].hex()} flight tail {P[0xC6:0xCE].hex()}")
    fl_ptr = u16(P, 0x1C + 2) | (u16(P, 0x1C + 4) << 16)
    check("KNOWN DEFECT REPRODUCED: C3B-P flight mov imm32 -> 0xC4CC4 while its table sits at 0xC4CC6",
          fl_ptr == 0xC4CC4 and Ps[0xC4:] == P[0xC6:], f"ptr 0x{fl_ptr:X}")
    return F, Fs, P, Ps

def main():
    print("ADV V297 build-audit -- independent script, stdlib only")
    per = census()
    orig = originals(per)
    for tag in ("V295", "V294"):
        ib, rb, _ = orig[tag]
        rwd_decode(tag, ib, rb)
        crc_checks(tag, ib)
    # NEGATIVE CONTROLS (r3): the CRC replay and the decode comparison must be ABLE to fail.
    print("\n=== NEGATIVE CONTROLS ===")
    mut = bytearray(orig["V295"][0]); mut[0xC4C00] ^= 0x01      # a byte inside the main block
    bad_bl = [x for x in crc_chain(mut, True) if x[2] is False]
    check("NEG-CTRL: 1-bit flip at 0xC4C00 -> bootloader walk reports a mismatch", len(bad_bl) == 1,
          f"{len(bad_bl)} failing block(s): " + ", ".join(f"0x{b[0]:X}" for b in bad_bl))
    mut2 = bytearray(orig["V295"][0]); mut2[0xC5100] ^= 0x01    # inside the bridge-skipped block
    bad_bl2 = [x for x in crc_chain(mut2, True) if x[2] is False]
    bad_full2 = [x for x in crc_chain(mut2, False) if x[2] is False]
    check("NEG-CTRL: flip at 0xC5100 -> bootloader walk BLIND (0) but full chain catches it (1)",
          len(bad_bl2) == 0 and len(bad_full2) == 1, f"BL {len(bad_bl2)}, full {len(bad_full2)}")
    check("NEG-CTRL: V294 image != V295 image under the same comparison used in C",
          orig["V294"][0][0x13000:0x100000] != orig["V295"][0][0x13000:0x100000])
    diff_v295_v294(orig["V295"][0], orig["V294"][0])
    cave_hex()
    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\nTALLY: {len(RESULTS)} checks, {len(RESULTS) - n_fail} pass, {n_fail} fail")
    return n_fail

if __name__ == "__main__":
    sys.exit(1 if main() else 0)
