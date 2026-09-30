"""ADV-bytes step 8 (e): is A1017 one build, cal-only, one byte + one CRC trailer?  IN MEMORY ONLY -- no image or rwd is
written (design phase).  Uses the kit's bootloader-walk replay (verify_bootloader_crc.walk / walk_all_blocks) as the
second method next to my own block lookup."""
import contextlib, io, os, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "lib")))
from verify_bootloader_crc import walk, walk_all_blocks, _blocks  # noqa: E402
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-"
       "FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
base = open(IMG, "rb").read()
def q(fn, img):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(img)
print("V294 base: BL walk fails %d, full chain fails %d" % (q(walk, base), q(walk_all_blocks, base)))
blocks = [b for b in _blocks(base, 0x13000, 0xED000, bridge=False) if b[0] != "OOB"]
owner = [(s, s + l) for s, l in blocks if s <= 0xC63E8 < s + l]
print("block(s) owning 0xC63E8 (full chain):", [(hex(a), hex(b)) for a, b in owner])
blocksBL = [b for b in _blocks(base, 0x13000, 0xED000, bridge=True) if b[0] != "OOB"]
print("covered by the BOOTLOADER walk too:", any(s <= 0xC63E8 < s + l for s, l in blocksBL))
e = bytearray(base)
struct.pack_into("<h", e, 0xC63E8, 1017)
b0, b1 = owner[0]
old = struct.unpack_from("<I", base, b1)[0]
new = zlib.crc32(bytes(e[b0:b1])) & 0xFFFFFFFF
struct.pack_into("<I", e, b1, new)
print("trailer 0x%X: 0x%08X -> 0x%08X" % (b1, old, new))
print("edited (in memory): BL walk fails %d, full chain fails %d" % (q(walk, bytes(e)), q(walk_all_blocks, bytes(e))))
diff = [i for i in range(0x13000, 0x100000) if base[i] != e[i]]
print("differing bytes in [0x13000,0x100000): %d -> %s" % (len(diff), [(hex(i), "%02X->%02X" % (base[i], e[i])) for i in diff]))
print("code region [0x13000,0xC0000) bytes changed:", sum(1 for i in diff if i < 0xC0000))
# V294's own edit of this same page (precedent that the page's CRC path is exercised and flew)
v293 = open(IMG.replace("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP",
                        "_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP"), "rb").read()
pg = [i for i in range(b0, b1 + 4) if v293[i] != base[i]]
print("V293 -> V294 differences inside this block + trailer:", [hex(i) for i in pg])
