# ★ V59 BUILT (UNFLASHED) — the boost-index DEPTH probe

**Type:** project · **Built 2026-07-30** over `_v58_plain_image.bin`

## What it measures — CAN `0x14A` byte4, 100 Hz
```
bit7 = 1                          LIVENESS (field == 0 => cave did not fire => VOID)
bit6 = (gp-0x6ba6 <  0)           the 0xFFFF FAULT SENTINEL from FUN_0003b66a
bit5 = ((gp-0x6ba6 >>  9) == 0)   index < 512
bit4 = ((gp-0x6ba6 >> 10) == 0)   index < 1024
bit3 = ((gp-0x6ba6 >> 11) == 0)   index < 2048
bits 2:0 = stock STEER_SENSOR_STATUS, preserved
```
A **thermometer**: bit5 ⇒ bit4 ⇒ bit3 in every valid frame, so a wrong build on the car is *detectable*
rather than silently plausible. Reading `gp-0x6ba6` **signed** is deliberate — it is a magnitude, so bit6
can only set on the `0xFFFF` sentinel, which tests the fault hypothesis free **and** disambiguates a
fault (−1 >> 9 = −1 ⇒ decodes as "≥ 2048") from the loudest normal reading.

## The question
`gp-0x6ba6 == |gp-0x6b9a|` indexes both boost amplitude LERPs. V58 showed the signed sibling crosses zero
at 20.93 Hz **only when LKAS applies** ⇒ the index is that signal rectified, sweeping the curve at ~2× the
mode frequency. **A sign bit carries no amplitude**, so the delivered swing is unknown:

`<512 ⇒ ≤1.12×` · `1024 ⇒ 1.27×` · `2048 ⇒ 1.58×` · `2529 ⇒ 1.75×` · `≥5120 ⇒ 2.00×`

⚠ **"Below 512" is WEAK, not inert** — the LERP interpolates from X = 0.

## Why a thermometer and not a binary field
The binding constraint is the **68-byte proven cave extent**, not bit width: fixed overhead 36 B + 10 B
per comparison ⇒ **3 comparisons max ⇒ 4 levels either way.** A uniform binary code is strictly worse —
the cell spans 0..32767, so a 4-bit code with no saturation logic (shift 11) gives 2048-count buckets and
puts X1/X2/X3 all in bucket 0; useful placement needs saturation, i.e. `BLE` or `cmov`, **neither pinned
in this image**. Note `movea 0x8,r7,r7` is an **add**, so the same pattern is already a unary counter (up
to 15 levels in 4 bits) — the upgrade path is paid in cave length and DTC-0x18 timing budget, not bits.

## Provenance
```
RWD    ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7
image  c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d
19 bytes off V58 (cave payload + MAIN CRC only; CAL CRC UNCHANGED = machine proof no cal moved)
86 off V38.  50/50 CRC.  RWD round-trips.  Cave re-disassembled from the built image.
GATE 1 inherited: same base 0xC4B34 / hook 0x55C0E / 68-byte extent as V55/V57/V58, all flown clean.
        Read-only, no new RAM, r6/r7 only.  NO new encoder and NO new condition code (BGE + BNE).
GATE 2 vacuous: writes nothing to any control path, changes no calibration byte.
```
The build **asserts what makes the probe interpretable**: both LERPs still resolve to `0xD28DC` (via
`0xca4f4`) and `0xD2888` (via `0xca23c`) **at the same mode**, and `tp+0x7498/0x7499` are both still 1.

Decoder `rlog-tools/probe/decode_v59_boostindex.py` — **hard-stops above 1% non-monotonic** rather than
reporting on a surviving subset (smoke-tested against a V58 log: correctly refuses at 56.2%).

## Route to drive
Parking-lot creep, **v ≤ 5 m/s** (the mode is creep-only), LKAS applying, wheel at a fixed 20–30°, and —
the thing route `2b` could not give — **sustained hands-off stretches ≥ 3 s**. Deliberate LKAS-on/off
passes at matched speed and angle. Plus a slow driver-torque ramp 0 → 2240 → 3000 → 0 for the override knee.

See [[accord-gp6ba6-is-the-boost-amplitude-index]], [[accord-sign-probe-needs-zero-crossings]],
[[accord-v58-drive-grinding-engagement-gated-creep-only]].
