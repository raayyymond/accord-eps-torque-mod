# -*- coding: utf-8 -*-
"""s15_candidate_spec.py -- the recommendation as a byte-level SPEC (no image is built): every Kp record of bank 0xCB994
on the V294 image, its current X/Y, the proposed X/Y, and the little-endian bytes of the 20-byte X+Y block at rec+2..rec+0x15.
The count word (rec+0) is unchanged (5).  Page CRCs are the builder's job (five 4 KB pages hold the 28 records).
ANALYSIS ONLY -- writes a JSON spec, never an image."""
import hashlib, json, os
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IMG = FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
X_NEW = (0, 8, 54, 100, 208)
Y_NEW = (1248, 1248, 1104, 960, 960)
b = open(IMG, "rb").read()
sha = hashlib.sha256(b).hexdigest()
assert sha == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
u16 = lambda a: int.from_bytes(b[a:a + 2], "little")
u32 = lambda a: int.from_bytes(b[a:a + 4], "little")
recs = []
for s in range(28):
    p = u32(0xCB994 + 4 * s)
    assert u16(p) == 5
    X = [u16(p + 2 + 2 * k) for k in range(5)]
    Y = [u16(p + 12 + 2 * k) for k in range(5)]
    new = b"".join(v.to_bytes(2, "little") for v in X_NEW + Y_NEW)
    recs.append(dict(slot=s, rec="0x%05X" % p, xy_block="0x%05X..0x%05X" % (p + 2, p + 0x15), X_v294=X, Y_v294=Y,
                     X_new=list(X_NEW), Y_new=list(Y_NEW), bytes_v294=b[p + 2:p + 22].hex(), bytes_new=new.hex(),
                     n_bytes_changed=sum(1 for i in range(20) if b[p + 2 + i] != new[i]), page="0x%X" % (p & ~0xFFF)))
spec = dict(name="V295 p-gain lens: R1.3_8_100 (regressive Kp schedule)", base_image_sha256=sha, bank="0xCB994 (28 LE32 record pointers, live selector 7 -> 0xE5378)",
            record_layout="u16 count @rec+0 (unread by the LERP) | X[5] u16 @rec+2..+0xB | Y[5] u16 @rec+0xC..+0x15 (decompile of FUN_00028ea6, code.bin)",
            lerp="0x29DC6 mov 0xcb994 .. 0x29E2C divq (SIGNED) .. 0x29E32 zxh -> Kp; falling segments are signed-exact (trunc toward zero)",
            records=recs, pages=sorted(set(r["page"] for r in recs)), total_payload_bytes_changed=sum(r["n_bytes_changed"] for r in recs),
            unchanged="every other cell: map 0xC9A88, fb a/b/C, Kd/Ki, clamps, output lag, both opcodes (0x28FA4 subr, 0x29D76 shl 2)")
json.dump(spec, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "V295_p-gain_candidate_spec.json"), "w"), indent=1)
print("records", len(recs), "pages", spec["pages"], "payload bytes changed", spec["total_payload_bytes_changed"])
print(recs[7])
