---
name: accord-kd-is-one-knot-of-a-flat-lerp
description: 0xC6AE6 is Y[0] of a FOUR-knot Kd LERP on motor rate, not a scalar gain - and because stock Y is flat 2048 at all four knots, a one-knot edit converts a constant into a rate-dependent nonlinearity instead of cutting a gain. Kills V110 independently of the sign, and closes the Kd lever entirely.
metadata:
  node_type: memory
  type: reference
---

# `0xC6AE6` IS **ONE KNOT OF A FLAT FOUR-KNOT LERP** — NOT A SCALAR Kd

★★★★★ **EVIDENCE — orchestrator-confirmed from BOTH the images and the decompile**, 2026-08-27, after
`rezband` surfaced it. Not relayed on trust: I byte-diffed the images myself and decompiled `0x3A382`
myself, and the decompile added a correction the original report did not have.

## THE STRUCTURE — `FUN_0003a382` @ `0x3A382`, the sole reader
```
axis = *(u16*)(gp - 0x6ac0)                       # motor / resolver rate
X = (50, 400, 1500, 3000)  @ 0xC6ADE / E0 / E2 / E4
Y = (Y0, Y1,  Y2,   Y3  )  @ 0xC6AE6 / E8 / EA / EC        # ALL FOUR = 2048 in stock
  axis <=   50  ->  Y0 alone
  50  ..  400   ->  LERP(Y0, Y1)
  400 .. 1500   ->  LERP(Y1, Y2)          # Y0 is NEVER READ at or above axis 400
  1500 .. 3000  ->  LERP(Y2, Y3)
  axis >= 3000  ->  Y3
enable: axis < 0x32C9 (12,993)
then:   D = ((ERR[n] - ERR[n-1]) * Y_lerp) >> 10        # 0x3A836/38/44
```
🛑 **`0xC6ADE` IS X[0] OF THIS TABLE, NOT A SEPARATE "GATE" CAL.** The pointer walk starts
`puVar32` at `0xC6AE0` and reaches back with `puVar32[-1]`, so `0xC6ADE` is the table's first X knot and
the `*(tp+0x7ade) < axis` test is the ordinary below-table check. Anyone reading it as a standalone
threshold will mis-model the 50-400 segment.
⊕ Verified in the same decompile, so the D transfer is not taken on trust: `0xC644A = 1024` ⇒
`((x - state)*1024)>>10 + state = x`, **exact pass-through, D really is a bare differencer**; POL is
`*(char*)(gp-0x6752)` gated `(pol+1) < 3`.

## ⭐ WHY A ONE-KNOT EDIT IS **WORSE THAN INERT**, NOT MERELY INERT
Stock Y is **flat 2048 at all four knots**, so the LERP is currently a **CONSTANT**.
⇒ **A one-knot edit does not reduce a gain. It converts a constant into a rate-dependent function** —
introducing a nonlinearity that does not currently exist, at **2x the oscillation frequency**, inside a
loop already known to be marginally stable. That is a **describing-function** problem, not a linear gain
cut. **On a flat table, a one-knot edit is NEVER a gain change.**

## WHAT IT KILLED
**V110** (`0xC6AE6` 2048->1024) — byte-verified as exactly 5 bytes vs V109: `0xC6AE7 08->04` plus the
CRC trailer at `0xC6FFC-FF`, with `0xC6AE8`/`EA`/`EC` **all still 2048**. Its docstring called this
*"Kd, 2048 -> 1024"* and *"one reader, zero writers"*. **Both true of the bytes; the first is false of
the lever.** Corrected in place; the artifact stays on disk, parked, as the audit trail.

🛑 **AND THE KD LEVER AS A WHOLE IS CLOSED — do not rebuild it "properly".** The correct
four-knot form (all of `0xC6AE6/E8/EA/EC`, as `docs/review/GATE2-2026-08-11-cbe74-independent.md:150`
already recommended) is exactly what makes the measured cost real: rotating the firmware `H_D(f)`
through the MEASURED `arg Z(f)` over three drives gives **+0.039 of ratchet benefit at 6-9 Hz against
+0.115 (2.96x) at 18-22 Hz and +0.153 (3.92x) at 26-31 Hz** — the operator's own grinding bands.
See [[accord-rez-antidamping-replicated-three-drives]].

## 🛑🛑 THE GATE-1 LESSON — ADD IT TO THE GATE
The GATE-1 census counted **static tp-relative accesses** and found one reader. **That was CORRECT.**
But Y0 is *also* reached through a **walked pointer** (`puVar11++`) — the register-indirect form that
**operand-text search structurally cannot see**, the kit's oldest documented blind spot.

⇒ **A GATE-1 census that counts ACCESSES to a cal cell cannot tell you whether the cell is a SCALAR
or ONE KNOT OF A TABLE. That requires reading the READER'S STRUCTURE.**
⇒ Practical form: **before editing any cal, decompile its reader and answer "is this cell used alone,
or interpolated against neighbours?" — and if it is a table, read all its knots and say which are
stock.** A neighbouring-cells dump is cheap and would have caught this in one command.

## 🛑🛑 THE TRAP IS ARMED ON **Ki** RIGHT NOW — and `BUILD-LINEAGE.md:397` already floats it
**Every LERP in `FUN_0003a382`, dumped from the V108 image and cross-read against the decompile
(orchestrator-verified, 2026-08-27).** `rezband` flagged the pattern; two of its four examples were
imprecise, so **use this table, not its summary:**

| Y knots @ | role (from the decompile, not the name) | axis | X knots | Y knots | shape |
|---|---|---|---|---|---|
| `0xC6AE6/E8/EA/EC` | **Kd** `D = (ERR−ERRp)·Y >> 10` | `gp-0x6ac0` | 50, 400, 1500, 3000 | 2048, 2048, 2048, 2048 | 🛑 **FLAT** |
| `0xC6B12/14/16/18` | **Ki** `acc += ERR·Y >> 10` | `gp-0x6ac0` | **0**, 400, 1500, 3000 | 98, 98, 98, 98 | 🛑 **FLAT** |
| `0xC6B26/28/2A/2C` | **Kp** EMA → `(ERR·Y >> 10)·32` | `gp-0x6ac0` | 0, 300, 2000, 4000 | 256, 256, **225**, **153** | ⚠ **SHAPED** |
| `0xC67B8/BA/BC/BE` | gainD, the PID output scale | `gp-0x671a` (byte) | 5, 10, 15 | 1024, 1024, 1024, **0** | ⚠ **SHAPED** |
| `0xC6798/9A/9C/9E` | second `gp-0x671a` arm | `gp-0x671a` (byte) | 5, 8, 10 | 5120, 5120, 5120, **0** | ⚠ **SHAPED** |
| `0xC67C8/CA/CC/CE` | limit arm | `gp-0x6a5e` | 128, 1280, 3200 | 0, 1024, 1024, 0 | ⚠ **SHAPED** |

⇒ **`Ki` is the real twin of `Kd`: flat 98 across all four knots, same axis, same walked pointer.**
A one-knot Ki edit has **exactly** this note's defect. `docs/BUILD-LINEAGE.md:397` already floats
**Kp/Ki as candidates**, so the next agent to size a Ki dose walks straight into it.
⚠ **`Kp` is NOT flat** — it is a genuine 3-segment schedule (256 → 225 → 153). A one-knot Kp edit is a
*different* trap: not "a constant becomes a nonlinearity", but "one segment of an existing schedule
moves". Less severe, still not a gain change. **Do not carry the flat-table argument onto Kp.**
⚠ The `gp-0x671a` and `gp-0x6a5e` tables end in a **0 knot** — they are shaped cut-offs, not scalars.

✅ **The genuine scalars in this function, read directly with no pointer walk** — safe to treat as gains:
`alphaD 0xC644A = 1024` (`tp+0x744a`, exact pass-through) · `alphaP 0xC6450 = 1024` (`tp+0x7450`) ·
the two slew cells `0xC644C`/`0xC644E = 32768` (`tp+0x744c`/`0x744e`).

## 🛑 THREE CORRECTIONS TO THE V110 BUILDER'S OWN TABLE, kept so they are not re-derived
1. **The `I → +296` row does NOT reproduce.** A free accumulator at `Ki = 98` gives `|H_I| = 1.956` at
   7.79 Hz — **32× the tabulated 0.0611.** The match was obtained by fitting a scalar, so that row is
   true *by construction* and proves nothing. Likely cause: the anti-windup clamp in the decompile
   (`iVar18` bounded by `iVar30`/`iVar29`) puts the effective integrator gain far below a free one —
   **BELIEF, unverified.** Harmless to the verdict (only D matters), but **do not cite the I row.**
   ✅ `P` and `D` DO reproduce non-circularly: `H_P = Kp/1024 = 0.2500`, `H_D = (Kd/1024)·|1−z⁻¹| =
   0.09788`, `|D|/|P| = 0.3915` — all straight out of the decompile.
2. **"gainD is flat unity at all three knots"** — true of the three it read; there is a **fourth knot
   = 0** above `gp-0x671a` = 15.
3. **`0xC6ADE` is X[0], not a gate cal** (see above).

Same blind spot as [[accord-gp4f60-two-encodings-enumeration-trap]] and
[[accord-v850-scan-traps-formatv-and-storezero]], in a new costume. Related:
[[accord-check-build-lineage-before-proposing-lever]] · [[feedback-decompile-first-then-assembly]]
