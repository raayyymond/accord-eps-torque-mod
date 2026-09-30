"""b1_bytes.py -- ADV-B step 1: the built image, its diff, every cell of the LKAS chain read from the IMAGE, and the
x-operand scale chain in the bytes (who writes gp-0x69ea / gp-0x6a56, what 0x55B48 publishes).

Run: python b1_bytes.py > b1_bytes_out.txt
"""
import hashlib
import sys

from advb_lib import (IMG, RWD_V295, RWD_V295_SHA, gp_hits, find_v282, load, lerp_rec, rec, s16, scan, u16, u32,
                      u8)

b5, h5 = load("V295")
b4, h4 = load("V294")
print("V295 image sha256", h5, "len", len(b5))
print("V294 image sha256", h4)
rw = open(RWD_V295, "rb").read()
hr = hashlib.sha256(rw).hexdigest()
print("V295 rwd   sha256", hr, "len", len(rw), "MATCH" if hr == RWD_V295_SHA else "MISMATCH")

# ---- whole-file diff ----
d = [i for i in range(len(b5)) if b5[i] != b4[i]]
print("\n[1] whole-file diff V295 vs V294: %d bytes" % len(d))
for i in d:
    print("   0x%05X  %02x -> %02x" % (i, b4[i], b5[i]))
print("   code region [0x13000,0xC0000) differing bytes:", sum(1 for i in d if 0x13000 <= i < 0xC0000))

# ---- the CRC trailer: CRC32 of [0xC6000, 0xC6FFC) vs the stored LE32 ----
import zlib
blk = b5[0xC6000:0xC6FFC]
print("   zlib.crc32([0xC6000,0xC6FFC)) = 0x%08X ; stored LE32 @0xC6FFC = 0x%08X" % (zlib.crc32(blk), u32(b5, 0xC6FFC)))
blk4 = b4[0xC6000:0xC6FFC]
print("   (V294: crc 0x%08X stored 0x%08X)" % (zlib.crc32(blk4), u32(b4, 0xC6FFC)))

# ---- cells, read LE from each image ----
def cells(b):
    c = {}
    c["a (0xC63E8, ld.h)"] = s16(b, 0xC63E8)
    c["b (0xC63EA, ld.hu)"] = u16(b, 0xC63EA)
    c["C (0xC62E6)"] = u16(b, 0xC62E6)
    c["Ki (0xC63E6)"] = u16(b, 0xC63E6)
    c["deadband (0xC62E4)"] = u16(b, 0xC62E4)
    c["I clamp (0xC61BA)"] = u16(b, 0xC61BA)
    c["P clamp (0xC61BC)"] = u16(b, 0xC61BC)
    c["sum clamp (0xC61BE)"] = u16(b, 0xC61BE)
    c["D clamp (0xC61B6)"] = u16(b, 0xC61B6)
    c["lane clamp (0xC61B4)"] = u16(b, 0xC61B4)
    c["out-lag a (0xC63EC, ld.h)"] = s16(b, 0xC63EC)
    c["out-lag b (0xC63EE)"] = u16(b, 0xC63EE)
    c["fwd gain (0xC6CD0, s16)"] = s16(b, 0xC6CD0)
    c["idx clamp +/- (0xC64F0/1)"] = (u8(b, 0xC64F0), u8(b, 0xC64F1))
    r, X, Y = lerp_rec(b, 0xCB994, 5)
    c["Kp rec7 @0x%X X/Y" % r] = (X, Y)
    kp_all = set()
    for sel in range(28):
        rr = rec(b, 0xCB994, sel)
        kp_all.add(tuple(u16(b, rr + 12 + 2 * i) for i in range(5)))
    c["Kp Y over 28 records"] = sorted(kp_all)
    r, X, Y = lerp_rec(b, 0xCB7D4, 4)
    c["Kd rec7 @0x%X X/Y" % r] = (X, Y)
    r, X, Y = lerp_rec(b, 0xC9A88, 10)
    c["map rec7 @0x%X X/Y" % r] = (X, Y)
    r, X, Y = lerp_rec(b, 0xCBC34, 6)
    c["taper B rec7 X/Y"] = (X, Y)
    r, X, Y = lerp_rec(b, 0xCBBC4, 6)
    c["taper D rec7 X/Y"] = (X, Y)
    hw = u16(b, 0x29D76)
    c["0x29D76 hw / op / imm"] = ("%04x" % hw, (hw >> 5) & 0x3F, hw & 31)
    hw = u16(b, 0x28FA4)
    c["0x28FA4 hw / op"] = ("%04x" % hw, {0x0E: "add", 0x0C: "subr"}.get((hw >> 5) & 0x3F, "?"))
    c["0x2A1F0 (fwd gain displacement) bytes"] = b[0x2A1EC:0x2A1F4].hex()
    return c


c5, c4 = cells(b5), cells(b4)
print("\n[2] LKAS chain cells, V294 -> V295 (LE reads from each image)")
for k in c5:
    same = c5[k] == c4[k]
    print("   %-40s V294 %-40s V295 %-40s %s" % (k, str(c4[k])[:40], str(c5[k])[:40], "same" if same else "CHANGED"))

# ---- x chain in the bytes ----
print("\n[3] x-operand chain: raw scan of gp accesses (positive-controlled)")
S = scan(b5)
ctl = [("ld.h gp-0x69ea @0x55B48", 0x55B48, -0x69EA), ("x read gp-0x6a56 in the PID filter", None, -0x6A56)]
for nm, want_a, disp in ctl:
    hits = gp_hits(S, disp)
    print("   %s: %d hits" % (nm, len(hits)))
    for h in hits:
        print("      0x%05X %-9s r%-2d disp %s" % (h[0], h[2], h[4], hex(h[5])))
    if want_a is not None:
        assert any(h[0] == want_a for h in hits), "POSITIVE CONTROL FAILED: %s" % nm
# the tp-relative b reader (control of the tp base form)
tph = [h for h in S if h[3] == 5 and h[5] == 0x73EA]
print("   tp+0x73EA accesses:", [("0x%05X" % h[0], h[2]) for h in tph])
assert any(h[0] == 0x28F86 for h in tph)
print("   POSITIVE CONTROLS PASS (0x55B48 ld.h gp-0x69ea; 0x28F86 ld.hu tp+0x73EA)")
# other gp cells near 0x69ea that could be the source
for disp in (-0x69EC, -0x69EE, -0x69E8):
    hits = gp_hits(S, disp)
    print("   gp%s: %s" % (hex(disp), [("0x%05X" % h[0], h[2]) for h in hits]))

# V282 image(s)
print("\n[4] V282 images on disk:")
for p in find_v282():
    bb = open(p, "rb").read()
    print("   ", hashlib.sha256(bb).hexdigest()[:16], p.split("/")[-1][:110])
