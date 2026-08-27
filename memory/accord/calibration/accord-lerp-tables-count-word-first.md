# ★ LERP tables begin with a POINT-COUNT word — the base address is NOT the first X

**Verified 2026-07-28** on four tables by little-endian byte read, and confirmed against the walker's own
address arithmetic in `FUN_0003a382`.

```python
# layout at a table base B
count = u16le(img, B)                                   # number of knots
X     = [u16le(img, B + 2 + 2*i) for i in range(count)] # X row
Y     = [u16le(img, B + 2 + 2*count + 2*i) for i in range(count)]
```

For `B = 0xC6AF0`, `count = 5`, so:

| address | contents |
|---|---|
| `0xC6AF0` | **count = 5** |
| `0xC6AF2 .. 0xC6AFA` | X = 0, 3277, 3604, 19661, 32768 |
| `0xC6AFC` | **Y[0] = 32768** |
| `0xC6AFE` | **Y[1] = 32768** |
| `0xC6B00 .. 0xC6B04` | Y[2..4] = 0, 0, 0 |

**The firmware's own pointer arithmetic proves it** (`Y base = B + 12` for a 5-point table = 2 + 2×5):

```
0x3a636  movea 0x7af0,tp,r15   ; r15 = 0xC6AF0  (base)
0x3a63a  addi  0xc,r15,r13     ; r13 = 0xC6AFC  = &Y[0]
0x3a63e  addi  0x2,r15,ep      ; ep  = 0xC6AF2  = &X[0]
0x3a650  ld.hu 0x7afc,tp,r6    ; below first knot -> loads Y[0] directly
0x3a668  ld.hu 0x7b04,tp,r6    ; above last knot  -> loads Y[4]
```

Corroborated on three sibling tables: `0xD27BC` (count 4, X = 2240/3840/5120/8960), `0xD27F8` (count 4),
`0xD07BC` (count 4). The kit's `build_v53_tva.AUTHORITY_LERP_STOCK` already encodes it correctly as
`(5, 0,3277,3604,19661,32768, 32768,32768,0,0,0)`.

🛑 **Naming trap.** Prose in this kit says *"the `0xC6AF0` LERP"* and *"mute `0xC6AF0` Y[0]/Y[1]"*.
`0xC6AF0` names the **table**, not the value to edit. Writing there clobbers the point count and would
make the walker read a 0-point (or wrong-length) table. **The mute writes `0xC6AFC` and `0xC6AFE`.**
V56's builder asserts the count word and the whole X row are unchanged, specifically to catch this.

Related: [[feedback-explain-with-python-mirroring-decompiled-arithmetic]],
[[accord-damper-variant-row-vs-index-trap]] (the other "resolve the pointer before editing" rule).
