# ADVERSARY A — ARITHMETIC — V287

**Date:** 2026-09-06 · **Agent:** `advA` (subagent, adversarial pass) · **Surface:** ARITHMETIC
**Image under attack:** `_v287_V287-V282BASE-DCLAMP.2560-KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
**sha256** `a9745f003a90bca15c3bd434df053c2e7b6af50f898cdd82c52ffeac5854129d` (re-hashed by me; matches the brief)

**VERDICT: PASS — do not block the flash on arithmetic grounds.**
Two record corrections and one interpretability caveat below. None of them is a FAIL.

---

## 0. What a FAIL would have looked like — written BEFORE the derivation

I committed to these in advance. Any one of them would have returned **do not flash**:

1. `0xC61B6` is not the D clamp (it is the anti-windup ceiling, or the P clamp, or a cell in another lane).
2. The clamp is **asymmetric** — the negative limit is not `-2560`, e.g. an off-by-one from `blt` vs `ble`,
   or a `subr` that is skipped on one path, or a signed/unsigned load mismatch that inverts a limit.
3. **`E_prev` (`gp-0x6cf8`) is written from the CLAMPED D-path value.** That would make the clamp change
   the *next* tick's `ΔE`, the effect would compound across ticks, and every number in the record's mirror
   would be wrong.
4. The D result is **stored to a 16-bit cell before the sum**, so the clamp interacts with a truncation.
5. The clamp value is used as a **divisor, a shift count, or an index** anywhere.
6. The "amplitude-selective" claim is false at the bytes — a scaling between the clamp and the sum that
   moves the rail off `|ΔE| = 160`, a second D-like term, or D feeding something other than the sum.
7. A **reader of `0xC61B6` or of the D result outside `FUN_00028ea6` that is reachable**.
8. Any code byte differs between V282 and V287, contradicting "cal-only".

Result: **1–6 and 8 all FAIL to break the build. 7 is PARTIALLY TRUE and is correction C1 below** — three
extra readers exist, but the evidence says they are unreachable, so the build stands.

---

## 1. The delta, read from the image [EVIDENCE]

Whole-file byte diff V282 → V287, both 1,048,576 bytes:

| offset | V282 | V287 | what |
|---|---|---|---|
| `0xC61B7` | `0x28` | `0x0A` | high byte of the halfword at `0xC61B6`: **10240 → 2560** |
| `0xC6FFC..0xC6FFF` | `72 df ea 75` | `ac 6e f3 ac` | calibration-page trailer (CRC) |

**Five bytes. Zero code bytes.** `struct.unpack_from("<H", img, 0xC61B6)` reads 10240 in V282 and 2560 in
V287. The "cal-only, one halfword" claim is exact. FAIL-condition 8 does not fire.

Against **stock** `code.bin`, the only code difference anywhere in `FUN_00028ea6` is two bytes at
`0x2A1F0`: `0x746c → 0x7cd0`, the ×6 forward-gain repoint. It is present in V282 and V287 alike, so
**everything downstream of the PID is byte-identical between the two builds**.

**Address anchor** (guarding the recurring off-by-0x1000 tp trap): `tp = 0xBF000`, so `tp+0x71B6 = 0xC61B6`.
I anchored this independently rather than trusting it — `tp+0x71BC = 0xC61BC` holds 15360, and with the
selector-7 Kp of 248 the P term rails at `15360·256/248 = 15855`, which is the figure already in the record.
The neighbourhood reads: `0xC61B4` 3072, `0xC61B6` **2560**, `0xC61B8` 102, `0xC61BA` 10240, `0xC61BC` 15360,
`0xC61BE` 15360.

---

## 2. The exact integer mirror, re-derived from the bytes

Constants all read little-endian from the built image. Method: decompile first (per the standing rule),
then assembly only to pin each instruction. Full runnable mirror at
`C:/Users/dudei/AppData/Local/Temp/mirror_v287.py`.

```
E      = (sp << 5) - fb                    # 0x2AC6C-equivalent; 32-bit, NOT range-guarded
e5     = E >> 5                            # sar 0x5
e5     = clamp(e5,  ±cal(0xC62E4))         # the E clamp, feeds the integrator only
I      = (I >> 3) + ((e5 * Ki) >> 3)       # Ki = cal(0xC63E6) = 0  -> increment is 0
I      = clamp(I,   ±((cal(0xC61BA) << 10) >> 3))    # = ±1,310,720
P      = clamp((E * Kp) >> 8,  ±cal(0xC61BC))        # Kp = 248 flat, clamp 15360
prev   = E if abs(E_prev) > 768000 else E_prev       # cmovnc @0x29E7E -> first tick gives D = 0
dE     = E - prev                                    # RAW error difference, 32-bit
D      = clamp((dE * Kd) >> 3,  ±cal(0xC61B6))       # Kd = 128 flat, clamp 2560   <-- THE EDIT
sum    = (I >> 7) + P + D                            # full 32-bit, no truncation
g      = ((G1 * G2) & 0xFFFF) >> 8                   # andi/sar @0x2A0B8 ; G1 = 255, G2 = 90..255
out    = clamp((sum * g) >> 8,  ±cal(0xC61BE))       # = ±15360
--- then, outside the PID ---
lag    = first-order IIR on cal(0xC63EC)/cal(0xC63EE)
deadband on cal(0xC61B8) = 102, plus a zero-crossing test against gp-0x6b30
× engagement scale (Q15), × cal(gp-0x6752) = -1, × K6 = cal(0xC6CD0) = 5346
out2   = clamp(±cal(0xC61B4) = 3072, ... >> 15)   -> gp-0x6b38, the delivered lane torque
--- state written at the END of the tick ---
gp-0x6cf8 := E          # the RAW error. NOT the clamped D-path value.
gp-0x6dd0 := I
```

**Kd and Kp read from the image, not assumed.** The Kd LERP pointer array is at `0xCB7D4`, indexed by the
variant selector `<< 2`. For the live selector **7** the table is at `0x0E511C` with
`x = [0, 11, 22, 32]`, `y = [128, 128, 128, 128]` — **flat 128**. Kp for selector 7 is at `0x0E5378`,
flat **248**. Both match the record. (Selectors 2 and 5 carry Kd = 64, which would rail at `|ΔE| = 320`;
they are not the live slot.)

Because `Kd = 128`, `(ΔE·128) >> 3` is **exactly `ΔE·16`** — the arithmetic shift discards nothing, so
there is no round-toward-negative-infinity asymmetry to exploit here.

---

## 3. The attacks, one by one

### 3.1 Clamp semantics and the exact rail — FAIL-condition 2 does not fire [EVIDENCE]

The four instructions in `FUN_00028ea6`, byte-exact:

```
00029ee4: mul  r7,r8,r0          ; r8 = dE * Kd   (low 32 bits; r0 discards the high word)
00029ee8: ld.hu 0x71b6[tp],r10   ; r10 = 2560, ZERO-extended
00029eec: sar  0x3,r8            ; r8 = D
00029eee: cmp  r10,r8
00029ef0: ble  0x00029ef8        ; D <= +2560  ->  fall through to the negative test
00029ef2: ld.hu 0x71b6[tp],r8    ; else D = +2560
00029ef6: br   0x00029f08
00029ef8: ld.hu 0x71b6[tp],r7
00029efc: subr r0,r7             ; r7 = -2560
00029efe: cmp  r7,r8
00029f00: bge  0x00029f08        ; D >= -2560  ->  keep
00029f02: ld.hu 0x71b6[tp],r8
00029f06: subr r0,r8             ; D = -2560
```

- **Symmetric.** The negative limit is built by `subr r0,rN` from the *same* `ld.hu` of the *same* cell.
  There is no separate negative-limit cell to fall out of step, at any value.
- **Inclusive at both ends.** `ble` at `0x29EF0` falls through when `D <= +2560`, and `bge` at `0x29F00`
  keeps when `D >= -2560`. So `D = ±2560` **exactly** passes through unchanged. Verified numerically:
  `ΔE = 160 → D = 2560` (kept), `ΔE = 161 → 2576` clipped to 2560; likewise on the negative side.
- **All four loads are `ld.hu`** — unsigned, consistent. There is no `ld.h`/`ld.hu` mixture here, unlike
  `0xC61B4`, which is read by one `ld.h` among three `ld.hu` and does carry the latent wrong-sign defect
  the record already flags. V287 does not touch `0xC61B4`.
- Both 2560 and 10240 are below `0x8000`, so signed and unsigned interpretations coincide regardless.

**Rail: `|ΔE| = 2560·8/128 = 160`, versus 640 under V282. Exactly as claimed.**

### 3.2 `E_prev` is written from the UNCLAMPED error — FAIL-condition 3 does not fire [EVIDENCE]

This was the attack most likely to break the build, because if `gp-0x6cf8` took the clamped value the
clamp would feed forward into the next tick's `ΔE` and the whole mirror would be wrong.

`gp-0x6cf8` is written once per tick, by `st.w r16,-0x6cf8[gp]` at `0x2A18C`. I traced every write to `r16`
between the error computation and that store: the only ones are `mov 0x7fffffff,r16` at `0x2A0EA` and
`0x2A16C`, both on the **not-engaged** branch, and `ld.bu 0x74a3[tp],r16` at `0x2A198`, which is **after**
the store. On the engaged path `r16` holds `E` from `0x29EE0` (`mov r16,r8` / `sub r27,r8` computes `ΔE`)
straight through to `0x2A18C`. The clamp writes `r8`, `r7` and `r10` only, never `r16`.

**`E_prev` := the raw, unclamped `E`. The clamp is memoryless.** The record's per-tick mirror is right.

The disengaged branch stores `0x7FFFFFFF`, which the `±768000` guard at `0x29E62`/`0x29E68` then rejects on
the next tick, forcing `D = 0` on the first engaged tick. Re-engagement therefore never inherits a stale
derivative. Good, and unchanged by V287.

### 3.3 No 16-bit store before the sum — FAIL-condition 4 does not fire [EVIDENCE]

```
00029f18: sar 0x7,r2      ; r2 = I >> 7
00029f1e: add r9,r2       ; += P
00029f24: add r8,r2       ; += D          <- full 32-bit
00029f2a: mov r2,r22      ; telemetry copy
00029f2e: mov r8,r27      ; telemetry copy
```

The live sum stays in `r2` and reaches `mul r2,r12,r0` at `0x2A0BE` at full width. The `st.h` stores to
`gp-0x6b36` (D) and `gp-0x6b34` (sum) at `0x2A19C`/`0x2A1A2` are **16-bit telemetry copies made after the
fact**; nothing reads them back. `|D| ≤ 2560` fits `int16` under V287 and `|D| ≤ 10240` fits under V282, so
the truncation is inert for D in both builds either way.

**Overflow hunt.** `mul r7,r8,r0` keeps only the low 32 bits, so `ΔE·Kd` could in principle wrap. It needs
`|ΔE| ≥ 2^31/128 = 16,777,216`, against a setpoint bounded by a 16-bit store (`|32·sp| ≤ 1,048,544`) and an
`E_prev` guarded to `±768,000`. Unreachable in practice, **pre-existing, and identical in V282**. The same
applies to `mul r2,r12,r0`: peak `|sum|·g` is 7.2 M against `2^31`. In both cases the **smaller** clamp
strictly *reduces* the exposure, so V287 is monotonically safer here than the build it replaces.

### 3.4 The clamp value is never a divisor, a shift or an index — FAIL-condition 5 does not fire [EVIDENCE]

At all seven read sites in the image the loaded value goes only into `cmp`, `mov` or `subr r0`. No `divq`
consumes it, no `shl`/`sar` takes it as a count, and it never indexes a table. Contrast `0xC61BA`, which is
genuinely reshaped by `shl 0xa` / `sar 0x3` into `c·128` — that is the anti-windup ceiling, not this cell.

### 3.5 Amplitude selectivity holds exactly — FAIL-condition 6 does not fire [EVIDENCE]

The clamp is applied to `D` immediately after the `>> 3` and immediately before `add r8,r2`. **Nothing
scales `D` between the clamp and the sum**, so the rail sits at `|ΔE| = 160` regardless of anything
downstream. Verified over the full range: `D` is bit-identical between the 10240 and 2560 clamps for every
`|ΔE| ≤ 160`, and the first `|ΔE|` at which they differ is **161**.

`D` (register `r8`) has exactly **two** consumers before it is overwritten at `0x29F66`: `add r8,r2` into
the sum, and `mov r8,r27` for telemetry. There is no second D-like term and no third use.

---

## 4. Corrections the record must take

### C1. The reader census is INCOMPLETE — 7 sites in 2 functions, not 4 in 1 [EVIDENCE]

The record states, twice and as a GATE 1 PASS: *"4 live readers, all inside `FUN_00028ea6`."*

A positively-controlled raw byte scan of the V287 image (matching `hw2 & 0xFFFE == 0x71B6` with
`reg1 == r5 = tp`, which finds all four known sites, so its nulls are worth something) returns **seven**:

| site | function | role |
|---|---|---|
| `0x29EE8`, `0x29EF2`, `0x29EF8`, `0x29F02` | `FUN_00028ea6` | the live D clamp |
| `0x2ADD4`, `0x2ADDC`, `0x2ADEC` | **`FUN_0002a93a`** | a second, structurally identical D clamp |

`FUN_0002a93a` (`0x2A93A–0x2B06F`) is **a complete duplicate of the same LKAS rate PID**. It reads the same
cells — `0xC62E4`, `0xC63E6`, `0xC61BA`, the `0xCB994` Kp array, `0xC61BC`, `gp-0x6cf8`, the `0xCB7D4` Kd
array, **`0xC61B6`**, `0xC61BE` — and writes the same state and telemetry globals (`gp-0x6cf8`, `gp-0x6dd0`,
`gp-0x6b36`, `gp-0x6b34`, `gp-0x6b32`, `gp-0x6b2e`). It differs only in lacking the output lag, the
deadband and the ×6 tail. It sits inside the **`0x2A400–0x2B600` orphan region the record itself already
flagged** for the lag-pole cells `0xC63EC`/`0xC63EE`.

**Why this is not a FAIL.** Three independent lines say it is unreachable, and the arithmetic is identical
anyway:

- A `jarl` disp22 scan whose decoder I had to fix twice and then **validated against all three of the
  skill's positive controls** (`0x28EA6←0x22522`, `0x34350←0x23276`, `0x3AA2C←0x2291E`, 3/3 found) returns
  **no call and no `jr`** to `0x2A93A`. My first two decoders returned zero hits on the controls too —
  exactly the failure mode the skill warns about — which is why the controls are load-bearing here.
- The 32-bit literal `0x0002A93A` appears **nowhere** in the image, so no indirect call can construct its
  entry. (Control: the same scanner does find `0xCB7D4` and `0xCB994` as `mov` immediates.)
- Even if it did run, `0x2ADD4–0x2ADF0` is the **same `sar 3` / `ble` / `bge` / `subr` clamp** on the same
  cell, so the edit lands identically.

Residual, marked **BELIEF**: I cannot exclude a call through a base register computed at runtime. The
record's existing dispose-is-a-return argument covers a neighbouring block, not this one.

**Required edit:** the census sentence should read *"7 reader sites in 2 functions — 4 live in
`FUN_00028ea6`, 3 in the unreachable `FUN_0002a93a` duplicate inside the `0x2A400–0x2B600` orphan"*. The
GATE 1 conclusion survives; the stated count does not. This is the same class of error the record warns
about two paragraphs later, when it tells the build script to assert on the address rather than the value.

### C2. `D` and the PID sum are WRITE-ONLY in this image [EVIDENCE]

`gp-0x6b36` (the D term) and `gp-0x6b34` (the PID sum) each have exactly **two** access sites, and both are
`st.h` stores — one in `FUN_00028ea6`, one in the dead duplicate. **Neither cell is read anywhere in the
image**, and neither absolute RAM address appears as a 32-bit literal. (Same scanner, same controls: it
finds the known `gp-0x6b32` and `gp-0x6cf8` sites.)

So the telemetry cave does **not** observe `D` or the sum. The clamp's binding can only be inferred from
the delivered torque at `gp-0x6b38`/427. That matters for the pre-registered Q1 endpoint, which is phrased
as a residual against a 1 kHz mirror — the inference is indirect, and §5 says when it is blocked outright.

---

## 5. The one substantive caveat — the output clamp MASKS the edit on P-railed, same-sign ticks

Not a FAIL. It bounds what the drive can read out, so it belongs on the pre-registration.

Read from the image: `G1 = 255` flat, `G2` runs `255 → 90` (or `77` on the alternate table), so
`g = ((G1·G2) & 0xFFFF) >> 8` runs **254 down to 76**. No `& 0xFFFF` wrap occurs (`255·255 = 65025`).
With `Ki = 0` the integrator contributes nothing, so `sum = P + D`, bounded by `15360 + 2560 = 17920`
under V287 and `15360 + 10240 = 25600` under V282. The output clamp of 15360 binds at
`|sum| ≥ 15360·256/g`, i.e. at `|sum| ≥ 15481` when `g = 254` and only at `|sum| ≥ 51726` when `g = 76`.

Consequence, verified numerically:

| condition | V287 out | V282 out | |
|---|---|---|---|
| `E = 20000`, `ΔE = +400`, `g = 254` (P railed, D same sign) | 15360 | 15360 | **identical — masked** |
| `E = 16000`, `ΔE = +300`, `g = 254` | 15360 | 15360 | **identical — masked** |
| `E = 20000`, `ΔE = −400`, `g = 254` (P railed, D opposing) | 12700 | 8890 | differs, strongly |
| `E = 8000`, `ΔE = +400`, `g = 254` (P not railed) | 10229 | 14039 | differs |
| `E = 20000`, `ΔE = +400`, `g = 76` | 5320 | 6460 | differs |

**The edit is exactly invisible at the output whenever P is railed AND D carries the same sign as P AND
`g` is near unity.** On the rising edge of a command step, `E` and `ΔE` share a sign by construction — and
the record's own §B3 says the clamp binds *"almost exclusively on command-step ticks"*, while the P clamp
binds 0.00–18.4 % of ticks with p99 `|P|` reaching 36,874 and 60,496 in the two r39 bookmark episodes.
Those two populations overlap, and on the overlap V287 and V282 deliver **bit-identical torque**.

The edit stays readable on the decay side of every step, where `D` opposes `P` and the difference is large,
and everywhere `g` is well below unity. **Recommendation:** condition the pre-registered Q1 fraction on
`|P| < 15360` or on `sign(D) ≠ sign(P)`, rather than on `|ΔE| > 160` alone. Otherwise part of the predicted
2.1–17.6 % of binding ticks will show a null that is a masking artefact, not a falsification of the lever.

---

## 6. What I did not test

- **Units.** I derived the arithmetic in raw counts throughout. `ΔE` is in units of `E = 32·sp − fb`, so
  `|ΔE| = 160` is 5 setpoint counts per tick, not 160. Whether the record's physical framing of that is
  right is adversary D's surface, not mine, and I make no claim on it.
- **Closed-loop consequence.** Whether shrinking D helps or hurts the 20 Hz grind is a stability question.
  The record is itself candid that its open-loop mirror and its sensitivity frame disagree on the sign.
  Nothing in the arithmetic settles it, and I did not try to.
- **Reachability of `FUN_0002a93a` via a runtime-computed pointer** — see C1, marked BELIEF.
- The calibration-page CRC at `0xC6FFC` — that is the build-audit surface.

## 7. Method notes

Ghidra used decompile-first, then assembly only to confirm framed claims; `disassemble_bytes` never called
on undefined regions; **`save_program` not called**. Every load-bearing count and null was re-run as a raw
little-endian Python byte scan with a positive control, and two of my own scanners failed their controls
before they passed. Python = the `bin_decompile` env.
