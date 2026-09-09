"""
D2 control-flow scope check for the V289 adversarial pass (advD).
Byte-exact diff of V289 against its actual base image V282 (not stock) over [0x13000, 0x100000),
proving the entire declared-scope claim: the ONLY bytes V289 changes vs V282 are the hook, the
0x14A cave-exit redirect, the new tail body, the new cave body, two recomputed CRC trailers, and
the fb-pole cal cells. Everything else -- including the duplicate compiled region [0x2A30E,0x2B421)
-- is proved byte-identical, so whatever reachability verdict held for V282 carries over unchanged.
"""
V282 = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
V289 = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"

v282 = open(V282, "rb").read()
v289 = open(V289, "rb").read()
assert len(v282) == len(v289) == 0x100000

lo, hi = 0x13000, 0x100000
diffs = []
i = lo
while i < hi:
    if v282[i] != v289[i]:
        j = i
        while j < hi and v282[j] != v289[j]:
            j += 1
        diffs.append((i, j))
        i = j
    else:
        i += 1

print(f"diff runs (V282 vs V289, [0x{lo:x},0x{hi:x})): {len(diffs)}")
total = 0
for a, b in diffs:
    total += (b - a)
    print(f"  0x{a:x} - 0x{b:x}  len={b-a:3d}  old={v282[a:b].hex()}  new={v289[a:b].hex()}")
print(f"total changed bytes: {total}")

EXPECTED_RUNS = {
    (0x2a174, 0x2a178): "hook: ld.hu 0x73ee,tp,r7 -> jr 0xC4C00",
    (0xc4bd6, 0xc4bda): "0x14A cave-exit redirect: -> jr 0xC4BDC (tail)",
    (0xc4bdc, 0xc4bf8): "new tail body (28B)",
    (0xc4c00, 0xc4c0a): "new cave body part 1",
    (0xc4c0b, 0xc4c20): "new cave body part 2",
    (0xc4c21, 0xc4c8c): "new cave body part 3",
    (0xc4ffc, 0xc5000): "CRC trailer, block [0xC4000,0xC5000)",
    (0xc63e8, 0xc63e9): "fb pole cal a, low byte",
    (0xc63ea, 0xc63ec): "fb pole cal b",
    (0xc6ffc, 0xc7000): "CRC trailer, block [0xC6000,0xC7000)",
}
unexpected = [d for d in diffs if d not in EXPECTED_RUNS]
print()
if unexpected:
    print("UNEXPECTED DIFF RUNS (not in the declared scope):", unexpected)
else:
    print("VERDICT: every diff run matches the declared scope exactly. No other byte in "
          "[0x13000,0x100000) differs between V282 and V289.")
