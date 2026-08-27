"""Independent byte anchor for the constants the monitor conclusions rest on."""
import os, struct
R=r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"
P={"stock":os.path.join(R,"stock_fw_dump","code.bin"),
   "V74":os.path.join(R,"_v74_engagedcols_x0_12_addonly_plain_image.bin"),
   "V75":os.path.join(R,"_v75_CY0.566-EX1.200_magprobe_plain_image.bin")}
B={k:open(v,'rb').read() for k,v in P.items()}
f32=lambda b,a: struct.unpack_from('<f',b,a)[0]
u16=lambda b,a: struct.unpack_from('<H',b,a)[0]

checks=[
 ("0xC74A4 Monitor-2 gate (claim: 0xEA => permanently off)", 0xC74A4, "u8"),
 ("0xC602C FUN_00045a20 tolerance (claim: float 5.0)",       0xC602C, "f32"),
 ("0xC6610 45a20 LERP X0 (claim 350.0)",                     0xC6610, "f32"),
 ("0xC6614 45a20 LERP X1 (claim 410.0)",                     0xC6614, "f32"),
 ("0xC6618 45a20 LERP Y0 (claim 5000.0)",                    0xC6618, "f32"),
 ("0xC661C 45a20 LERP Y1 (claim 400.0)",                     0xC661C, "f32"),
 ("0xC6554 float ceiling X0 (claim 300.0)",                  0xC6554, "f32"),
 ("0xC6558 float ceiling X1 (claim 800.0)",                  0xC6558, "f32"),
 ("0xC655C float ceiling Y0 (claim 0.5)",                    0xC655C, "f32"),
 ("0xC6560 float ceiling Y1 (claim 1.0)",                    0xC6560, "f32"),
 ("0xC6158 ceiling fallback (claim 512)",                    0xC6158, "u16"),
 ("0xC6206 STEP_FAST (claim 512)",                           0xC6206, "u16"),
 ("0xC6208 STEP_SLOW (claim 205)",                           0xC6208, "u16"),
 ("0xC531E step hysteresis thresh (claim 1062)",             0xC531E, "u16"),
 ("0xC63A0 damper weight into 2nd aggregator",               0xC63A0, "u16"),
 ("0xC407E friction self-clamp (stock 511 / built 850)",     0xC407E, "u16"),
 ("0xC6202 governor nominal ceiling (claim 4762)",           0xC6202, "u16"),
]
for label,addr,typ in checks:
    out, vals = [], []
    for k in ("stock","V74","V75"):
        b=B[k]
        v = b[addr] if typ=="u8" else (u16(b,addr) if typ=="u16" else f32(b,addr))
        vals.append(v)
        raw = " ".join(f"{x:02x}" for x in b[addr:addr+(1 if typ=='u8' else (2 if typ=='u16' else 4))])
        out.append(f"{k}={v!r:>12} [{raw}]")
    # compare the DECODED VALUES, not the formatted strings (the !r:>12 padding
    # differs by value width and made an earlier version flag everything).
    same = "" if len(set(vals))==1 else "   <<< DIFFERS ACROSS BUILDS"
    print(f"{label}\n   " + "  ".join(out) + same)
