"""ADV-D 3b: reachability of [0x2B070, 0x2B422) -- the routine whose tail at 0x2B418 copies T (gp-0x6b38) to gp-0x6b3c.
Same raw scanner as d3 (controls re-run)."""
exec(open("d3_callers.py").read().split("TW = [")[0])
for a, b in ((0x2B070, 0x2B422), (0x2A892, 0x2A93A), (0x2A93A, 0x2B070)):
    ins = [r for r in refs if a <= r[2] < b and not (a <= r[0] < b)]
    print("[0x%X,0x%X): transfers in from outside: %s" % (a, b, [(hex(r[0]), r[1], hex(r[2])) for r in ins]))
    ptr = [i for i in range(0, len(B) - 4, 2) if a <= struct.unpack_from("<I", B, i)[0] < b and struct.unpack_from("<I", B, i)[0] % 2 == 0]
    print("   even LE32 constants pointing inside: %s" % [(hex(p), hex(struct.unpack_from("<I", B, p)[0])) for p in ptr])
