"""Judge sketch (BELIEF until a builder H1s it): D1c's three edits WITHOUT the relink.
Replace V298's 16-B opposing block + the 4-B theta load (0xC4C6A..0xC4C7D, 20 B) by D1c's own 12 B
(ld.h -0x6a00 ; mov r9,r13 ; xor r16,r13 ; bge +4 ; mov 0,r9, bytes copied from D1c's listing) + 4 nops,
and the hard threshold imm16 512 -> 1229 at 0xC4C64. Counts changed bytes vs V298 and checks that D1c's
relinked flight hex carries the same 12-B sequence. Read-only. Prints wall time."""
import glob, hashlib, time
T0 = time.time()
img = glob.glob("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v298_*_plain_image.bin")[0]
b = open(img, "rb").read(); print("V298 sha", hashlib.sha256(b).hexdigest()[:8])
new = bytearray(b)
assert b[0xC4C62:0xC4C66] == bytes.fromhex("206e0002") and b[0xC4C6A:0xC4C6E] == bytes.fromhex("206e2c01")
assert b[0xC4C7A:0xC4C7E] == bytes.fromhex("244f0096")
new[0xC4C64:0xC4C66] = (1229).to_bytes(2, "little")
seq = bytes.fromhex("244f0096" "0968" "3069" "ae05" "004a") + bytes(8)
assert len(seq) == 20
new[0xC4C6A:0xC4C7E] = seq
diff = [i for i in range(len(b)) if b[i] != new[i]]
print("changed bytes (pre-CRC):", len(diff), "span", hex(diff[0]), "..", hex(diff[-1]))
hx = bytes.fromhex("".join(open("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/angle_loop/v299_design/D1-firmware-minimal/out/d1c_flight.hex").read().split()))
print("D1c flight hex len", len(hx), "| D1c 12-B seq at 0x6A:", hx[0x6A:0x76].hex(), "== mine:", hx[0x6A:0x76] == seq[:12])
print(f"wall {time.time()-T0:.2f} s")
