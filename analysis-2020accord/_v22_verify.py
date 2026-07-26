import sys, os, glob
from firmware_paths import RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from encode_eps import parse_x31, build_decode_table, OPS

f = glob.glob(os.path.join(str(RWD_DIR),
                           "39990-TVA,A160-V22-*0x13000-0x100000.rwd"))[0]
print("rwd:", os.path.basename(f))
info = parse_x31(open(f, "rb").read())
dec = build_decode_table((0xBF, 0x10, 0x9E), (OPS[0], OPS[0], OPS[4]))
plain = bytes(info["encs"][0]).translate(dec)
START = 0x13000


def show(a, n, want, tag):
    b = plain[a - START:a - START + n]
    got = " ".join(f"{x:02x}" for x in b)
    ok = "OK " if (want is None or b == bytes.fromhex(want.replace(" ", ""))) else "XX "
    print(f"  {ok}0x{a:05X}: {got:<30}  {tag}")


print("--- integer-side shl edits (low byte must be c9) ---")
show(0x42DAE, 2, "c9 4a", "shl 0x9,r9   [V21 upper IIR]")
show(0x42DCA, 2, "c9 5a", "shl 0x9,r11  [V21 upper bypass]")
show(0x42F16, 2, "c9 52", "shl 0x9,r10  [V22 gp-0x3578 lower]")
print("--- float redirect; neighbors must be UNCHANGED (no shift) ---")
show(0x4422C, 4, "ec 47 60 64", "PREV addf.s r12,r8,r12  UNCHANGED")
show(0x44230, 4, "88 07 90 0d", "jr 0xC4FC0  [redirect]")
show(0x44234, 4, "85 5f cb 74", "NEXT ld.bu 0x74ca,tp,r11  UNCHANGED")
print("--- code cave (20B) + descriptor UNCHANGED ---")
show(0xC4FC0, 20, "40 3e 00 40 e7 57 64 54 e7 67 64 64 e4 3f 9b 96 b7 07 64 f2", "cave")
show(0xC4FF0, 12, "01 01 01 01 00 00 c6 00 13 00 b2 00", "block descriptor UNCHANGED")

img = bytearray(b"\xff" * 0x100000)
img[START:0x100000] = plain
out = plain_image_path("_v22_plain_image.bin")
open(out, "wb").write(img)
print("wrote", out, len(img), "bytes")
