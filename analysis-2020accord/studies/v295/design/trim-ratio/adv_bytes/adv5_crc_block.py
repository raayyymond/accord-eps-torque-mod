# adv5_crc_block.py -- which CRC block holds 0xC63EA; was that block re-CRC'd on the FLOWN V294 (V293 -> V294 diff)?
import sys, zlib, io, contextlib, hashlib
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/lib")
import verify_bootloader_crc as V
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
v294 = open(FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
v293 = open(FW + "_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
print("sha V294", hashlib.sha256(v294).hexdigest()[:16], " V293", hashlib.sha256(v293).hexdigest()[:16])
for nm, img in (("V294", v294),):
    for bridge in (True, False):
        blks = [b for b in V._blocks(img, 0x13000, 0xED000, bridge) if b[0] != "OOB"]
        hit = [(s, s + l) for s, l in blks if s <= 0xC63EA < s + l]
        ok = all((zlib.crc32(img[s:s + l]) & 0xFFFFFFFF) == V.u32(img, s + l) for s, l in blks)
        print("%s %s: %d blocks, all CRC OK %s ; block(s) containing 0xC63EA: %s" % (
            nm, "BL walk (bridge)" if bridge else "full chain", len(blks), ok, ["[0x%X,0x%X) trailer @0x%X" % (a, b, b) for a, b in hit]))
diff = [i for i in range(0x13000, 0x100000) if v293[i] != v294[i]]
runs = []
for i in diff:
    if runs and i == runs[-1][1]:
        runs[-1][1] = i + 1
    else:
        runs.append([i, i + 1])
print("V293 -> V294 differing runs in [0x13000,0x100000): %d bytes in %d runs:" % (len(diff), len(runs)))
print("   ", ["0x%X-0x%X" % (a, b) for a, b in runs])
print("0xC63EA u16: V293 %d  V294 %d ; 964 = 0x%04X vs 567 = 0x%04X -> both bytes change" % (
    int.from_bytes(v293[0xC63EA:0xC63EC], "little"), int.from_bytes(v294[0xC63EA:0xC63EC], "little"), 964, 567))
